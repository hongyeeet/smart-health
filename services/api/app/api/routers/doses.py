"""Today's doses (Home, prd F4) and the answers to them:

  GET  /doses/today             what is due now, what was not confirmed, and the next dose
  POST /doses/{id}/taken        "Taken" (only while the dose's window is open)
  POST /doses/{id}/untaken      "I did not take it after all": back to waiting, and the pill goes back on the stock
  POST /doses/{id}/reason       "Why was it not confirmed?": a reason and an optional note, for a dose past its window

See app/services/dose_store.py for the rules. Nothing here gives dose advice: the amount is the person's own label.
"""
from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from psycopg.rows import tuple_row

from app.core.errors import InvalidTransition, NotFound, ValidationFailed
from app.db import logstore
from app.schemas.doses import DoseOut, DoseResult, DosesToday, NextDoseOut, ReasonIn
from app.services import dose_store as store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/doses", tags=["doses"])


def _now() -> datetime:
    return datetime.now(store.TZ)


def _fail(e: Exception) -> HTTPException:
    if isinstance(e, NotFound):
        return HTTPException(404, str(e))
    if isinstance(e, InvalidTransition):
        return HTTPException(409, str(e))
    return HTTPException(422, str(e))


@router.get("/today", response_model=DosesToday, response_model_by_alias=True)
async def doses_today() -> DosesToday:
    return await run_in_threadpool(_today)


def _today() -> DosesToday:
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        d = store.today(conn, str(logstore.current_user()), _now())
    return DosesToday(has_medicines=d["has_medicines"], due=[DoseOut(**x) for x in d["due"]], unconfirmed=[DoseOut(**x) for x in d["unconfirmed"]],
                      taken_today=d["taken_today"], next=NextDoseOut(**d["next"]) if d["next"] else None)


@router.post("/{dose_id}/taken", response_model=DoseResult, response_model_by_alias=True)
async def dose_taken(dose_id: str) -> DoseResult:
    return await run_in_threadpool(_taken, dose_id)


def _taken(dose_id: str) -> DoseResult:
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        try:
            status = store.mark_taken(conn, str(logstore.current_user()), dose_id, _now())
        except (NotFound, InvalidTransition) as e:
            raise _fail(e) from None
    logger.info("dose marked taken")
    return DoseResult(status=status)  # type: ignore[arg-type]


@router.post("/{dose_id}/untaken", response_model=DoseResult, response_model_by_alias=True)
async def dose_untaken(dose_id: str) -> DoseResult:
    return await run_in_threadpool(_untaken, dose_id)


def _untaken(dose_id: str) -> DoseResult:
    """"I did not take it after all": the dose waits for an answer again and the pill goes back on the stock."""
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        try:
            status = store.mark_untaken(conn, str(logstore.current_user()), dose_id, _now())
        except (NotFound, InvalidTransition) as e:
            raise _fail(e) from None
    logger.info("dose marked not taken")
    return DoseResult(status=status)  # type: ignore[arg-type]


@router.post("/{dose_id}/reason", response_model=DoseResult, response_model_by_alias=True)
async def dose_reason(dose_id: str, body: ReasonIn) -> DoseResult:
    return await run_in_threadpool(_reason, dose_id, body)


def _reason(dose_id: str, body: ReasonIn) -> DoseResult:
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        try:
            status = store.save_reason(conn, str(logstore.current_user()), dose_id, body.reason, body.note, _now())
        except (NotFound, InvalidTransition, ValidationFailed) as e:
            raise _fail(e) from None
    logger.info("dose reason saved reason=%s", body.reason)           # an enum, never the note
    return DoseResult(status=status)  # type: ignore[arg-type]
