"""The medicine warehouse (screen H1, "My stock"): how many of each regular medicine are left, and the two changes the person makes.

  GET  /medications/stock          every live, regular medicine: the count, days left at the usual dose, status
  POST /medications/{id}/stock     {"add": n} (I bought more) or {"set": n} (Change the number); n from 0 to 10000

See app/services/medication_stock.py for the rules. While migration 0032 is not applied, GET answers ready: false with no items and
POST answers 503 with a plain sentence: nothing else in the app is affected.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from psycopg.rows import tuple_row

from app.core.errors import InvalidTransition, NotFound, ValidationFailed
from app.db import logstore
from app.schemas.med_stock import StockIn, StockListOut, StockOut
from app.services import medication_stock
from app.services.dose_store import dose_unit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/medications", tags=["medications"])


def _now() -> datetime:
    return datetime.now(logstore.TZ)


def _out(r: dict) -> StockOut:
    """One row as the screen shows it. The unit is the stored one, or the usual one for the medicine's type."""
    unit = r["stock_unit"] or medication_stock.stock_unit_for(dose_unit(r["kind"], r["description"]))
    count = r["stock_count"]
    return StockOut(
        id=str(r["id"]), name=r["name"], strength=r["strength"] or "Strength not entered",
        stock_count=float(count) if count is not None else None, stock_unit=unit,       # the unit is known even before a count is set (the pop-up asks "how many tablets")
        days_left=r["days_left"], status=r["status"], updated_at=r["updated_at"],
        full_count=float(r["full_count"]) if r["full_count"] is not None else None, pack_size=r["pack_size"],
    )


@router.get("/stock", response_model=StockListOut, response_model_by_alias=True)
async def get_stock() -> StockListOut:
    return await run_in_threadpool(_stock)


def _stock() -> StockListOut:
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        if not medication_stock.stock_ready(conn):
            return StockListOut(ready=False, items=[])
        rows = medication_stock.stock_list(conn, str(logstore.current_user()))
    return StockListOut(ready=True, items=[_out(r) for r in rows])


@router.post("/{med_id}/stock", response_model=StockOut, response_model_by_alias=True)
async def change_stock(med_id: str, body: StockIn) -> StockOut:
    return await run_in_threadpool(_change, med_id, body)


def _change(med_id: str, body: StockIn) -> StockOut:
    try:
        uuid.UUID(med_id)
    except ValueError:
        raise HTTPException(404, "Medicine not found") from None
    user = str(logstore.current_user())
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        if not medication_stock.stock_ready(conn):
            raise HTTPException(503, medication_stock.NOT_READY)
        try:
            if body.set_count is not None:
                medication_stock.set_count(conn, user, med_id, body.set_count, _now())
                kind = "set"
            else:
                medication_stock.add_count(conn, user, med_id, body.add, _now())
                kind = "add"
            row = medication_stock.stock_list(conn, user, med_id)
        except NotFound as e:
            raise HTTPException(404, str(e)) from None
        except InvalidTransition as e:
            raise HTTPException(409, str(e)) from None
        except ValidationFailed as e:
            raise HTTPException(422, str(e)) from None
        if not row:
            raise HTTPException(404, "Medicine not found")
    logger.info("medication stock changed kind=%s", kind)            # counts and kinds only, never the name
    return _out(row[0])
