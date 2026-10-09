"""POST /scans, GET /scans/{id}, POST /scans/{id}/confirm (architecture.md 4.1 and 7, docs/specs/f2-scan.md).

  1. POST /scans (photo): black out identity, read it with the vision model, score every field, store the blacked-out photo and the
     scan row, and return what was read. `reviewMode` is "confirm" (one medicine, every field clear) or "manual" (the person types the
     form: unreadable, a low-confidence field, a missing required field, or several medicines).
  2. GET /scans/{id}: the same result again (the review screen reloads).
  3. POST /scans/{id}/confirm: the values the person checked, with their edits and chosen dose times, saved in one transaction.
     Nothing is saved before this call.

A photo that was refused before anything was sent (not a photo, no readable text) is not stored anywhere; its result lives in memory for
a short time so the screen can still show why. The model's answer is never saved as a medicine by itself.
"""
from __future__ import annotations

import logging
import uuid
from collections import OrderedDict

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from psycopg.rows import tuple_row

from app.agents import clash_pipeline, scan_pipeline
from app.api.routers.calendar import schedule_sync
from app.api.routers.medications import datetime_today, medication_out
from app.core.errors import (
    ExternalServiceError,
    InvalidTransition,
    NotFound,
    ValidationFailed,
)
from app.db import logstore
from app.schemas.medicine_scan import ScanOutcome
from app.schemas.medicines import MedicationOut
from app.schemas.scan import (
    ScanConfirmRequest,
    ScanFieldSchema,
    ScanResult,
    ScanScheduleItem,
    ScanStatus,
)
from app.services import scan_api
from app.services.scan_store import confirm_medication, outcome_json, save_scan

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scans", tags=["scans"])

_unsaved: OrderedDict[str, dict] = OrderedDict()      # refused photos: nothing was stored, only the explanation is kept briefly
_UNSAVED_MAX = 200


def to_result(scan_id: str, status: str, extraction: dict | None, error: str | None = None, model_id: str | None = None) -> ScanResult:
    """The shape the app reads, from a stored scan. A field the model left empty is never invented."""
    mode, reasons = scan_api.review_mode(extraction)
    fields = scan_api.api_fields(extraction)
    name = next((f["value"] for f in fields if f["key"] == "name" and f["value"]), "")
    item = scan_api.first_item(extraction)
    return ScanResult(
        scanId=scan_id, itemType=(item or {}).get("item_type") or "unknown",
        status=ScanStatus.failed if status == "failed" else ScanStatus.extracted,
        drug=name, fields=[ScanFieldSchema(**f) for f in fields],
        schedule=[ScanScheduleItem(**s) for s in scan_api.api_schedule(extraction)],
        modelId=model_id, error=error, reviewMode=mode, reasons=reasons, asNeeded=scan_api.is_as_needed(extraction),
        symptomHint=scan_api.symptom_hint(extraction),
        notice=scan_api.reason_text(reasons) if mode == "manual" else None,
    )


@router.post("", response_model=ScanResult, response_model_by_alias=True)
async def upload_scan(file: UploadFile = File(...)) -> ScanResult:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    image = await file.read()
    if not image:
        raise HTTPException(status_code=400, detail="Empty image")
    return await run_in_threadpool(_upload, image)


def _upload(image: bytes) -> ScanResult:
    user = str(logstore.current_user())
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        outcome, masked = scan_pipeline.run(image, conn, user)
        extraction = outcome_json(outcome)
        if masked is None:                                   # refused before anything left the machine: store nothing
            return _remember_unsaved(outcome, extraction)
        try:
            scan_id = save_scan(conn, user, masked, outcome)
        except ExternalServiceError as e:                    # storage down: do not pretend it was saved
            logger.warning("scan could not be stored: %s", e.code)
            failed = ScanOutcome(status="failed", review_mode="manual", reasons=["service_unavailable"])
            return _remember_unsaved(failed, outcome_json(failed))
    logger.info("scan stored status=%s mode=%s reasons=%s items=%d", outcome.status, outcome.review_mode, outcome.reasons, len(outcome.items))
    return to_result(scan_id, outcome.status, extraction, model_id=outcome.model_id)


def _remember_unsaved(outcome: ScanOutcome, extraction: dict) -> ScanResult:
    scan_id = str(uuid.uuid4())
    _unsaved[scan_id] = {"status": outcome.status, "extraction": extraction, "model": outcome.model_id}
    while len(_unsaved) > _UNSAVED_MAX:
        _unsaved.popitem(last=False)
    return to_result(scan_id, outcome.status, extraction, model_id=outcome.model_id)


@router.get("/{scan_id}", response_model=ScanResult, response_model_by_alias=True)
async def get_scan(scan_id: str) -> ScanResult:
    return await run_in_threadpool(_get, scan_id)


def _get(scan_id: str) -> ScanResult:
    if scan_id in _unsaved:
        u = _unsaved[scan_id]
        return to_result(scan_id, u["status"], u["extraction"], model_id=u["model"])
    row = _find(scan_id)
    return to_result(scan_id, row[0], row[1], error=row[2])


def _find(scan_id: str) -> tuple:
    try:
        uuid.UUID(scan_id)
    except ValueError:
        raise HTTPException(404, "Scan not found") from None
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        row = conn.execute("select status::text, extraction, error from prescription_scans where id = %s and user_id = %s",
                           (scan_id, str(logstore.current_user()))).fetchone()
    if row is None:
        raise HTTPException(404, "Scan not found")
    return row


@router.post("/{scan_id}/confirm", response_model=MedicationOut, response_model_by_alias=True)
async def confirm_scan(scan_id: str, body: ScanConfirmRequest, background: BackgroundTasks) -> MedicationOut:
    user = str(logstore.current_user())
    out = await run_in_threadpool(_confirm, scan_id, body)
    background.add_task(clash_pipeline.check_user, user)      # the clash check studies every saved medicine again, after the response
    await run_in_threadpool(schedule_sync, background, user, out.id)     # and the calendar reminders are made after it
    return out


def _confirm(scan_id: str, body: ScanConfirmRequest) -> MedicationOut:
    user = str(logstore.current_user())
    if scan_id in _unsaved:
        raise HTTPException(409, "This photo was not saved. Please type the medicine in.")
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        row = conn.execute("select status::text, extraction from prescription_scans where id = %s and user_id = %s", (scan_id, user)).fetchone() \
            if _is_uuid(scan_id) else None
        if row is None:
            raise HTTPException(404, "Scan not found")
        if scan_api.review_mode(row[1])[0] == "manual":       # D-064: a scan that needs typing is completed by the typed form, never by a tap
            raise HTTPException(409, "This label needs to be typed in. Please use the form.")
        today = datetime_today()
        try:
            entry = scan_api.build_confirmed(row[1], body.fields, body.times, body.kind, today, body.as_needed)
            med_id = confirm_medication(conn, user, entry, scan_id=scan_id)
        except ValidationFailed as e:
            raise HTTPException(422, str(e)) from None
        except NotFound as e:
            raise HTTPException(404, str(e)) from None
        except InvalidTransition as e:
            raise HTTPException(409, str(e)) from None
        out = medication_out(conn, med_id, entry, today, source="scan")
    logger.info("scan confirmed doses=%d edited=%d", len(entry.doses), len(body.fields))     # counts only, never values
    return out


def _is_uuid(v: str) -> bool:
    try:
        uuid.UUID(v)
    except ValueError:
        return False
    return True

