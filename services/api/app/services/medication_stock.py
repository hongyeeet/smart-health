"""The medicine warehouse (stock tracker, docs/specs/implementation-plan-2026-10-11.md section 4.3): how many tablets, capsules or doses
of each regular medicine are left in hand.

Rules (Joely, 2026-10-11):
  - The count starts from the pack size when a medicine is saved from a scan or by hand (`total_quantity`). It is never guessed:
    no pack size, no count ("Not set yet", never 0).
  - It goes down by the dose's amount each time a dose is marked Taken, in the same transaction as the dose, and never below 0.
    The amount is the schedule's amount for that dose (1 only when the schedule has none).
  - A dose that is taken back adds back exactly what it took off (the amount is read from the event log for that dose).
  - By hand: "I bought more" adds, "Change the number" sets. Every change is written to event_log with ids and counts only.
  - As-needed medicines are not tracked.
  - Until migration 0032 is applied, `stock_ready` is False and every function here does nothing. The screen then says
    "Stock tracking is being set up." and the rest of the app is unaffected.

Nothing here gives advice. "Running low" states a fact about the count only. The functions take tuple rows (the routers set that).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo
from decimal import Decimal
from math import floor
from typing import Any, Mapping

import psycopg
from psycopg.types.json import Jsonb

from app.core.errors import InvalidTransition, NotFound, ValidationFailed

# The owner may change this. A regular medicine with this many whole days of supply left (or fewer) shows as "Running low".
LOW_STOCK_DAYS = 7
MAX_COUNT = Decimal(10000)
NOT_READY = "Stock tracking is being set up."
EVENT_SET = "medication.stock.set"        # {"count": n}: the number was typed in, or the start value from the pack size
EVENT_ADDED = "medication.stock.added"    # {"delta": n}: bought more
EVENT_DOSE = "medication.stock.dose"      # {"delta": n}: negative when a dose was taken, positive when it was taken back
# What stock_count counts, in words, by the label of one dose (dose_store.dose_unit). Anything else is "doses".
STOCK_UNIT = {"Tab": "tablets", "Capsule": "capsules", "Dose": "doses", "ml": "ml", "Sachet": "sachets", "Drop": "drops",
              "Puff": "puffs", "Patch": "patches", "Teaspoon": "teaspoons", "Spoonful": "spoonfuls"}

_ready = False


def _first(row: Any) -> Any:
    """The first value of a row, whether the connection gives tuples or dicts."""
    return next(iter(row.values())) if isinstance(row, Mapping) else row[0]


def stock_ready(conn: psycopg.Connection) -> bool:
    """Whether migration 0032 is applied (the three stock columns exist). Found once and remembered; a 'not yet' is checked again."""
    global _ready
    if not _ready:
        n = _first(conn.execute(
            "select count(*) from information_schema.columns where table_schema = 'public' and table_name = 'medications' "
            "and column_name in ('stock_count', 'stock_unit', 'stock_updated_at')").fetchone())
        _ready = int(n) == 3
    return _ready


def reset_stock_cache() -> None:
    global _ready
    _ready = False


# ------------------------------------------------------------------ pure rules (no database)
def dose_amount(quantity: Decimal | None) -> Decimal:
    """What one dose takes off the stock: the schedule's amount for that dose. 1 only when the schedule has no amount."""
    if quantity is None or quantity <= 0:
        return Decimal(1)
    return Decimal(quantity)


def days_left_of(stock: Decimal | None, per_day: Decimal | None) -> int | None:
    """Whole days of supply at the usual dose: the count divided by the doses per day, rounded down. None when either is unknown."""
    if stock is None or per_day is None or per_day <= 0:
        return None
    return floor(stock / per_day)


def status_of(stock: Decimal | None, days: int | None) -> str:
    """ok | low | out | unknown. 'Not set yet' is unknown; a count of 0 is out; 7 days or fewer is low (LOW_STOCK_DAYS)."""
    if stock is None:
        return "unknown"
    if stock <= 0:
        return "out"
    if days is None:
        return "unknown"
    return "low" if days <= LOW_STOCK_DAYS else "ok"


def count_after_dose(stock: Decimal | None, amount: Decimal, as_needed: bool) -> Decimal | None:
    """The count after one dose is taken: down by the amount, never below 0. None when nothing changes: no count is set (null is not
    zero), or the medicine is taken only when needed."""
    if stock is None or as_needed:
        return None
    return max(Decimal(0), stock - amount)


def count_after_untake(stock: Decimal | None, back: Decimal, as_needed: bool) -> Decimal | None:
    """The count after a taken dose is taken back: up by what it took off, never above MAX_COUNT. None when nothing changes."""
    if stock is None or as_needed:
        return None
    return min(MAX_COUNT, stock + back)


def stock_unit_for(dose_label: str) -> str:
    return STOCK_UNIT.get(dose_label, "doses")


def check_amount(n: Decimal) -> Decimal:
    """A number typed in: from 0 to 10000, and not a special value."""
    if not n.is_finite() or n < 0 or n > MAX_COUNT:
        raise ValidationFailed("Please enter a number from 0 to 10000.")
    return n


# ------------------------------------------------------------------ database
def _event(conn: psycopg.Connection, user_id: str, event: str, table: str, entity_id: Any, payload: dict[str, Any]) -> None:
    """Ids and counts only: never a name, a strength or a note (rules.md section 3)."""
    conn.execute("insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'user', %s, %s, %s, %s)",
                 (user_id, event, table, entity_id, Jsonb(payload)))


def _locked(conn: psycopg.Connection, user_id: str, med_id: Any) -> tuple[Any, ...] | None:
    """(stock_count, as_needed, total_quantity) of one live medicine, locked for this transaction. None when it is not the person's."""
    return conn.execute(
        "select stock_count, as_needed is true, total_quantity from medications where id = %s and user_id = %s and deleted_at is null for update",
        (med_id, user_id)).fetchone()


def count_of(conn: psycopg.Connection, med_id: Any) -> Decimal | None:
    """The count of one medicine, or None when it is not set (or the columns are not there yet)."""
    if not stock_ready(conn):
        return None
    row = conn.execute("select stock_count from medications where id = %s", (med_id,)).fetchone()
    return row[0] if row else None


def dose_taken(conn: psycopg.Connection, user_id: str, med_id: Any, dose_id: Any, quantity: Decimal | None, now: datetime) -> None:
    """Called in the same transaction that marks a dose Taken (dose_store). Takes the dose's amount off the stock."""
    if not stock_ready(conn):
        return
    row = _locked(conn, user_id, med_id)
    if row is None:
        return
    stock, as_needed, _ = row
    new = count_after_dose(stock, dose_amount(quantity), bool(as_needed))
    if new is None:
        return
    conn.execute("update medications set stock_count = %s, stock_updated_at = %s where id = %s", (new, now, med_id))
    _event(conn, user_id, EVENT_DOSE, "medication_log", dose_id, {"delta": float(new - stock)})


def dose_untaken(conn: psycopg.Connection, user_id: str, med_id: Any, dose_id: Any, now: datetime) -> None:
    """The reverse of dose_taken: adds back what that dose took off, as recorded for it. Nothing is added when the last change
    recorded for the dose was not a take, so calling it twice adds only once."""
    if not stock_ready(conn):
        return
    last = conn.execute(
        "select payload->>'delta' from event_log where user_id = %s and event = %s and entity_table = 'medication_log' and entity_id = %s "
        "order by id desc limit 1", (user_id, EVENT_DOSE, dose_id)).fetchone()
    if last is None or _first(last) is None or Decimal(str(_first(last))) >= 0:
        return
    back = -Decimal(str(_first(last)))
    row = _locked(conn, user_id, med_id)
    if row is None:
        return
    stock, as_needed, _ = row
    new = count_after_untake(stock, back, bool(as_needed))
    if new is None:
        return
    conn.execute("update medications set stock_count = %s, stock_updated_at = %s where id = %s", (new, now, med_id))
    _event(conn, user_id, EVENT_DOSE, "medication_log", dose_id, {"delta": float(new - stock)})


def refill_cycles(conn: psycopg.Connection, user_id: str, med_ids: list[Any]) -> dict[str, str]:
    """For each medicine, the day its current supply began: the last time its count was set or more was bought (from the event log),
    or "first" when there has been none. The refill reminder's key holds this, so a medicine is reminded once per supply: missing
    doses moves the run-out date, but it does not start a new cycle."""
    out = {str(m): "first" for m in med_ids}
    if not med_ids:
        return out
    for mid, day in conn.execute(
            "select entity_id, (max(occurred_at) at time zone 'Asia/Singapore')::date from event_log where user_id = %s "
            "and entity_table = 'medications' and event in (%s, %s) and entity_id = any(%s) group by entity_id",
            (user_id, EVENT_SET, EVENT_ADDED, [m if isinstance(m, uuid.UUID) else uuid.UUID(str(m)) for m in med_ids])).fetchall():
        out[str(mid)] = day.isoformat()
    return out


def refill_key(med_id: Any, cycle: str) -> str:
    return f"refill-{med_id}-{cycle}"


def set_start_count(conn: psycopg.Connection, user_id: str, med_id: Any, count: int, unit: str, now: datetime) -> None:
    """The start value when a medicine is saved from a scan or by hand, from its pack size. The caller only calls it when the pack size is known."""
    if not stock_ready(conn):
        return
    conn.execute("update medications set stock_count = %s, stock_unit = %s, stock_updated_at = %s where id = %s and user_id = %s",
                 (Decimal(count), unit, now, med_id, user_id))
    _event(conn, user_id, EVENT_SET, "medications", med_id, {"count": count})


def set_count(conn: psycopg.Connection, user_id: str, med_id: Any, count: Decimal, now: datetime) -> None:
    """"Change the number": the exact count, typed in."""
    row = _locked(conn, user_id, med_id)
    if row is None or row[1]:
        raise NotFound("Medicine not found")
    check_amount(count)
    conn.execute("update medications set stock_count = %s, stock_updated_at = %s where id = %s", (count, now, med_id))
    _event(conn, user_id, EVENT_SET, "medications", med_id, {"count": float(count)})


def add_count(conn: psycopg.Connection, user_id: str, med_id: Any, amount: Decimal, now: datetime) -> None:
    """"I bought more": adds to the count. Needs a count to add to, so the person sets the number first when it is not set."""
    row = _locked(conn, user_id, med_id)
    if row is None or row[1]:
        raise NotFound("Medicine not found")
    check_amount(amount)
    stock = row[0]
    if stock is None:
        raise InvalidTransition("Set how many you have first, then add what you bought.")
    new = stock + amount
    if new > MAX_COUNT:
        raise ValidationFailed("That would be more than 10000. Please check the number.")
    conn.execute("update medications set stock_count = %s, stock_updated_at = %s where id = %s", (new, now, med_id))
    _event(conn, user_id, EVENT_ADDED, "medications", med_id, {"delta": float(amount)})


def stock_list(conn: psycopg.Connection, user_id: str, med_id: Any = None, today: date | None = None) -> list[dict[str, Any]]:
    """Every live, regular medicine of the person (or one of them) that has not ended: the count, the days left at the usual dose, and the status.
    A medicine whose end date is before today is left out ("My stock" is what the person has to take). A pack size with no count stays unknown.
    'full_count' is the last amount the person set or bought, the full mark of the bar; None when there is none yet."""
    only = "and m.id = %s" if med_id is not None else ""
    today = today or datetime.now(ZoneInfo("Asia/Singapore")).date()
    params: tuple[Any, ...] = (user_id, today, med_id) if med_id is not None else (user_id, today)
    rows = conn.execute(
        "select m.id, m.name, m.strength, m.kind::text, m.description, m.total_quantity, m.stock_count, m.stock_unit, m.stock_updated_at, "
        "coalesce((select sum(s.quantity) from medication_schedule s where s.medication_id = m.id and s.deleted_at is null), 0) "
        "from medications m where m.user_id = %s and m.deleted_at is null and m.as_needed is not true and (m.end_date is null or m.end_date >= %s) "
        "and not exists (select 1 from medication_schedule s where s.medication_id = m.id and s.deleted_at is null and s.dose_time is null) "
        f"{only} order by m.created_at, m.name", params).fetchall()
    # the last set or bought amount of each medicine, from the event log (ids and counts are all it holds)
    full: dict[Any, Decimal] = {}
    for mid, event, payload in conn.execute(
            "select distinct on (entity_id) entity_id, event, payload from event_log where user_id = %s and entity_table = 'medications' "
            "and event in (%s, %s) and entity_id is not null order by entity_id, id desc", (user_id, EVENT_SET, EVENT_ADDED)).fetchall():
        value = payload.get("count") if event == EVENT_SET else payload.get("delta")
        if value is not None:
            full[mid] = Decimal(str(value))
    out = []
    for mid, name, strength, kind, description, pack, stock, unit, updated, per_day in rows:
        per_day = Decimal(per_day)
        days = days_left_of(stock, per_day)
        out.append({"id": mid, "name": name, "strength": strength, "kind": kind, "description": description, "pack_size": pack,
                    "stock_count": stock, "stock_unit": unit, "updated_at": updated, "per_day": per_day, "days_left": days,
                    "status": status_of(stock, days), "full_count": full.get(mid) if full.get(mid, 0) > 0 else None})
    return out
