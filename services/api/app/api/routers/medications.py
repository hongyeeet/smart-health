"""GET and POST /medications: the Meds page (H1) and adding a medicine by hand (H8). The scan path (H2 to H4) saves through the same function.

The save is `app/services/scan_store.confirm_medication`: Bronze entry, the medicine, its dose times and the event log in one
transaction. The drug-list link is chosen by a name match in code, never by the client. Nothing here gives dose advice.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, time
from decimal import Decimal
from math import floor
from typing import Any, Literal

import psycopg
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.concurrency import run_in_threadpool
from psycopg.rows import tuple_row

from app.agents import clash_pipeline
from app.api.routers.calendar import schedule_sync
from app.core.errors import InvalidTransition, NotFound
from app.db import logstore
from app.schemas.medicine_scan import ConfirmedMedication, DoseTime
from app.schemas.medicines import MedicationOut, NewMedicationIn, Refill
from app.services.scan_store import confirm_medication

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/medications", tags=["medications"])

def clock12(t: time) -> str:
    """08:00 -> '8:00 am', as the app shows times."""
    return t.strftime("%I:%M %p").lstrip("0").lower()


def refill_for(total: int | None, per_day: Decimal, start: date, source: str, today: date, pack_start: date | None = None) -> Refill | None:
    """How long the supply should last, assuming every dose since the start date was taken (F4 will use the real dose log).

    The count starts on `pack_start` (the day the pack in hand was started) when it is known, otherwise on the start date. The simulated
    demo medicines hold a placeholder total (data-model-v2.md): unless they were given a pack start date they get no estimate, not a wrong one.
    """
    if total is None or per_day <= 0 or (source == "demo_dataset" and pack_start is None):     # no real total: no estimate, never a guess
        return None
    left = max(Decimal(0), Decimal(total) - per_day * max(0, (today - (pack_start or start)).days))
    return Refill(days_left=floor(left / per_day), units_left=floor(left))


def badge_for(kind: str) -> Literal["not_checked"] | None:
    """Supplements and herbal products are never checked for interactions, so they say so, never 'safe' (rules.md 1, rule 7).
    Nothing is matched to a medicine list yet: understanding the medicine, and any interaction check, comes later (F5)."""
    return "not_checked" if kind in ("supplement", "tcm") else None


def to_confirmed(body: NewMedicationIn) -> ConfirmedMedication:
    return ConfirmedMedication(
        name=body.name.strip(), kind=body.kind, strength=(body.strength or "").strip() or None,
        doses=[DoseTime(dose_time=d.time, quantity=d.quantity, meal_relation=d.meal_relation) for d in body.doses],
        directions=(body.directions or "").strip() or None, total_quantity=body.total_quantity, start_date=body.start_date,
    )


def list_medications(conn: psycopg.Connection, user_id: str, today: date) -> list[MedicationOut]:
    """The person's current medicines, oldest first, as the Meds page shows them."""
    meds = conn.execute(
        "select id, name, strength, kind::text, total_quantity, start_date, source::text, pack_started_on "
        "from medications where user_id = %s and deleted_at is null order by created_at, name", (user_id,)).fetchall()
    doses: dict[Any, list[tuple[time | None, Decimal, str]]] = defaultdict(list)
    for mid, t, q, rel in conn.execute(
            "select medication_id, dose_time, quantity, meal_relation::text from medication_schedule "
            "where user_id = %s and deleted_at is null order by dose_time", (user_id,)):
        doses[mid].append((t, q, rel))
    out = []
    for mid, name, strength, kind, total, start, source, pack_start in meds:
        ds = doses.get(mid, [])
        as_needed = any(t is None for t, _, _ in ds)
        per_day = Decimal(0) if as_needed else sum((q for _, q, _ in ds), Decimal(0))    # how much is used when needed is not known
        out.append(MedicationOut(
            id=str(mid), name=name, strength=strength or "Strength not entered", kind=kind, as_needed=as_needed,
            times=[clock12(t) for t, _, _ in ds if t is not None], with_food=any(rel != "na" for _, _, rel in ds),
            badge=badge_for(kind), refill=refill_for(total, per_day, start or today, source, today, pack_start),
        ))
    return out


def medication_out(conn: psycopg.Connection, med_id: str, entry: ConfirmedMedication, today: date, source: str = "manual") -> MedicationOut:
    """A saved medicine as the app shows it."""
    per_day = Decimal(0) if entry.as_needed else sum((d.quantity for d in entry.doses), Decimal(0))
    return MedicationOut(
        id=med_id, name=entry.name, strength=entry.strength or "Strength not entered", kind=entry.kind, as_needed=entry.as_needed,
        times=[clock12(d.dose_time) for d in entry.doses if d.dose_time is not None], with_food=any(d.meal_relation != "na" for d in entry.doses),
        badge=badge_for(entry.kind),
        refill=refill_for(entry.total_quantity, per_day, entry.start_date or today, source, today),
    )


def create_medication(conn: psycopg.Connection, user_id: str, body: NewMedicationIn, today: date | None = None) -> MedicationOut:
    """Save and return the medicine as the app shows it. The caller owns the transaction. With `scan_id`, the typed form completes that scan."""
    entry = to_confirmed(body)
    med_id = confirm_medication(conn, user_id, entry, scan_id=body.scan_id)
    return medication_out(conn, med_id, entry, today or date.today())


@router.get("", response_model=list[MedicationOut], response_model_by_alias=True)
async def get_medications() -> list[MedicationOut]:
    return await run_in_threadpool(_list)


def _list() -> list[MedicationOut]:
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        return list_medications(conn, str(logstore.current_user()), datetime_today())


@router.post("", response_model=MedicationOut, response_model_by_alias=True)
async def add_medication(body: NewMedicationIn, background: BackgroundTasks) -> MedicationOut:
    user = str(logstore.current_user())
    out = await run_in_threadpool(_add, body)
    background.add_task(clash_pipeline.check_user, user)      # the clash check studies every saved medicine again, after the response
    await run_in_threadpool(schedule_sync, background, user, out.id)     # and the calendar reminders are made after it
    return out


def _add(body: NewMedicationIn) -> MedicationOut:
    with logstore.tx() as conn:
        conn.row_factory = tuple_row        # the shared save code reads rows by position
        try:
            out = create_medication(conn, str(logstore.current_user()), body, datetime_today())
        except NotFound as e:
            raise HTTPException(404, str(e)) from None
        except InvalidTransition as e:
            raise HTTPException(409, str(e)) from None
    logger.info("medication added kind=%s doses=%d", body.kind, len(body.doses))   # ids and counts only, never names
    return out


def datetime_today() -> date:
    """Today's date in the person's timezone (Singapore), not the server's."""
    return datetime.now(logstore.TZ).date()
