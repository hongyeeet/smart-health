"""Database side of the medicine scan (prd F2, flow J2). Plain SQL through a psycopg connection: the caller owns the
transaction (commit or roll back). Deterministic, no model calls.

Flow:  save_scan()          masked photo -> Bronze row + prescription_scans row (status needs_review or failed)
       confirm_medication() what the USER confirmed or typed -> bronze_medication, medications, medication_schedule, scan
                            status confirmed, event_log: one transaction, all or nothing.
The model's answer is only ever stored in `prescription_scans.extraction`; it never becomes a medication by itself.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Callable, Mapping

import psycopg
from psycopg.types.json import Jsonb

from app.core.errors import InvalidTransition, NotFound, ValidationFailed
from app.schemas.medicine_scan import ConfirmedMedication, ScanOutcome
from app.services.scan_privacy import MaskResult

Uploader = Callable[[str, bytes, str], None]
# scan_status is: uploaded, extracting, needs_review, confirmed, rejected, failed
CONFIRMABLE = ("needs_review", "failed")        # a failed scan can still be completed by typing it in


def _one(conn: psycopg.Connection, sql: str, params: tuple[Any, ...]) -> tuple[Any, ...]:
    row = conn.execute(sql, params).fetchone()
    if row is None:
        raise RuntimeError("the database returned no row for an insert")
    return row


def _checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _event(conn: psycopg.Connection, user_id: str, event: str, table: str, entity_id: Any, payload: Mapping[str, Any], actor: str = "user",
           agent_run_id: Any = None) -> None:
    """Append to the event log. Payloads hold ids, counts and enums only, never names or health values (rules.md section 3)."""
    conn.execute("insert into event_log (user_id, actor, event, entity_table, entity_id, payload, agent_run_id) values (%s, %s, %s, %s, %s, %s, %s)",
                 (user_id, actor, event, table, entity_id, Jsonb(dict(payload)), agent_run_id))


def outcome_json(outcome: ScanOutcome) -> dict[str, Any]:
    return {
        "review_mode": outcome.review_mode, "reasons": outcome.reasons, "mask_summary": outcome.mask_summary,
        "items": [{
            "item_type": it.item_type, "min_confidence": it.min_confidence,
            "ingredients": [i.model_dump() for i in it.ingredients],
            "fields": {k: f.model_dump() for k, f in it.fields.items() if f.value is not None},
        } for it in outcome.items],
    }


def save_scan(conn: psycopg.Connection, user_id: str, masked: MaskResult | None, outcome: ScanOutcome, *, uploader: Uploader | None = None) -> str:
    """Store the masked photo as the Bronze original and record the extraction. Repeat-safe: the same photo returns the same scan.

    Nothing identifying is stored: the photo is the blacked-out copy, and the answer was scrubbed before scoring.
    """
    if masked is None:
        raise ValidationFailed("there is no photo to store", code="no_photo")
    checksum = _checksum(masked.image)
    key = f"{user_id}/medications/{checksum}.jpg"
    existing = conn.execute("select id from prescription_scans where user_id = %s and image_key = %s", (user_id, key)).fetchone()
    if existing:
        return str(existing[0])
    if uploader is None:
        from app.integrations.storage import upload_object
        uploader = upload_object
    uploader(key, masked.image, masked.mime_type)
    bronze_id = _one(
        conn, "insert into bronze_medication (user_id, source, payload, object_key, checksum, processing_status) values (%s, 'scan', %s, %s, %s, 'processed') "
        "on conflict (user_id, checksum) do update set checksum = excluded.checksum returning id",
        (user_id, Jsonb({"kind": "prescription_scan_upload", "masked": True, "mask_summary": outcome.mask_summary}), key, checksum))[0]
    run_id = _one(conn,
        "insert into agent_runs (user_id, agent, trigger, model_id, prompt_version, status, input_tokens, output_tokens, latency_ms, finished_at) "
        "values (%s, 'scan_extractor', 'scan', %s, %s, %s, %s, %s, %s, now()) returning id",
        (user_id, outcome.model_id, outcome.prompt_version, "ok" if outcome.status == "needs_review" else "error",
         outcome.input_tokens, outcome.output_tokens, outcome.latency_ms))[0]
    item_type = outcome.items[0].item_type if len(outcome.items) == 1 else None
    scan_id = _one(
        conn, "insert into prescription_scans (user_id, image_key, status, extraction, model_id, agent_run_id, error, item_type, quality_ok, prompt_version) "
        "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id",
        (user_id, key, outcome.status, Jsonb(outcome_json(outcome)), outcome.model_id, run_id,
         ",".join(outcome.reasons) if outcome.status == "failed" else None, item_type,
         "unreadable" not in outcome.reasons and "ocr_empty" not in outcome.reasons, outcome.prompt_version))[0]
    _event(conn, user_id, "scan.image.uploaded", "prescription_scans", scan_id, {"bronze_id": str(bronze_id)})
    _event(conn, user_id, "scan.extraction.completed", "prescription_scans", scan_id,
           {"items_n": len(outcome.items), "min_confidence": min((i.min_confidence for i in outcome.items), default=0.0),
            "review_mode": outcome.review_mode, "reasons": outcome.reasons}, actor="agent", agent_run_id=run_id)
    return str(scan_id)


def build_review(extraction: Mapping[str, Any] | None, entry: ConfirmedMedication) -> dict[str, Any]:
    """Which fields did the user change from what the scan read? Stored so accuracy per field can be reported later (E3-3)."""
    out: dict[str, Any] = {"fields": {}}
    items = (extraction or {}).get("items") or []
    read = items[0]["fields"] if len(items) == 1 else {}
    final = {"name": entry.name, "strength": entry.strength, "directions": entry.directions, "prescriber": entry.prescriber,
             "start_date": entry.start_date.isoformat() if entry.start_date else None,
             "total_quantity": str(entry.total_quantity) if entry.total_quantity is not None else None,
             "times_per_day": None if entry.as_needed else str(len(entry.doses)),
             "when_to_take": "as_needed" if entry.as_needed else None}
    for k, v in final.items():
        scanned = (read.get(k) or {}).get("value")
        out["fields"][k] = {"scanned": scanned, "confirmed": v, "changed": (scanned or None) != (v or None)}
    out["changed_count"] = sum(1 for f in out["fields"].values() if f["changed"])
    out["multiple_items_on_photo"] = len(items) > 1
    return out


def confirm_medication(conn: psycopg.Connection, user_id: str, entry: ConfirmedMedication, *, scan_id: str | None = None) -> str:
    """Save one confirmed medicine and its dose times, in the caller's transaction. Returns the new medication id.

    With a scan: the scan must be needs_review (or failed, when the user typed the form after a failed read). Without one: manual entry.
    The medicine is saved exactly as the person confirmed it. It is not matched to any medicine list: understanding the medicine
    (and linking it to `drug_reference` for interaction checks) comes later and never blocks a save.
    """
    scan = None
    if scan_id:
        scan = conn.execute("select status, extraction from prescription_scans where id = %s and user_id = %s for update", (scan_id, user_id)).fetchone()
        if scan is None:
            raise NotFound("scan not found", code="scan_not_found")
        if scan[0] not in CONFIRMABLE:
            raise InvalidTransition(f"a scan that is {scan[0]} cannot be confirmed", code="scan_not_confirmable")
    source = "scan" if scan_id else "manual"
    payload = {"kind": "medication_confirmed", "scan_id": scan_id, "name": entry.name, "medication_kind": entry.kind, "strength": entry.strength,
               "doses": [{"dose_time": d.dose_time.isoformat() if d.dose_time else None, "quantity": str(d.quantity), "meal_relation": d.meal_relation}
                         for d in entry.doses],
               "directions": entry.directions, "prescriber": entry.prescriber,
               "start_date": entry.start_date.isoformat() if entry.start_date else None, "total_quantity": entry.total_quantity}
    checksum = _checksum(json.dumps(payload, sort_keys=True).encode())
    bronze_id = _one(
        conn, "insert into bronze_medication (user_id, source, payload, checksum, processing_status) values (%s, %s, %s, %s, 'processed') "
        "on conflict (user_id, checksum) do update set checksum = excluded.checksum returning id",
        (user_id, source, Jsonb(payload), checksum))[0]
    description = entry.directions
    med_id = _one(
        conn, "insert into medications (user_id, name, kind, strength, frequency, description, start_date, source, bronze_id, total_quantity) "
        "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id",
        (user_id, entry.name, entry.kind, entry.strength, len(entry.doses), description, entry.start_date or date.today(), source, bronze_id,
         entry.total_quantity))[0]
    for d in entry.doses:
        conn.execute("insert into medication_schedule (user_id, medication_id, dose_time, quantity, meal_relation) values (%s, %s, %s, %s, %s)",
                     (user_id, med_id, d.dose_time, d.quantity, d.meal_relation))
    if scan_id and scan is not None:
        review = build_review(scan[1], entry)
        conn.execute("update prescription_scans set status = 'confirmed', extraction_review = %s where id = %s", (Jsonb(review), scan_id))
        _event(conn, user_id, "scan.confirmed", "prescription_scans", scan_id, {"changed_count": review["changed_count"]})
    _event(conn, user_id, "medication.created", "medications", med_id, {"kind": entry.kind, "source": source})
    _event(conn, user_id, "dose.schedule.generated", "medications", med_id, {"doses_n": len(entry.doses)})
    return str(med_id)


def reject_scan(conn: psycopg.Connection, user_id: str, scan_id: str) -> None:
    """The user discards the scan and chooses not to save it."""
    row = conn.execute("select status from prescription_scans where id = %s and user_id = %s for update", (scan_id, user_id)).fetchone()
    if row is None:
        raise NotFound("scan not found", code="scan_not_found")
    if row[0] not in CONFIRMABLE:
        raise InvalidTransition(f"a scan that is {row[0]} cannot be rejected", code="scan_not_rejectable")
    conn.execute("update prescription_scans set status = 'rejected' where id = %s", (scan_id,))
    _event(conn, user_id, "scan.rejected", "prescription_scans", scan_id, {})
