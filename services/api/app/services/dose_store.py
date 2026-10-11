"""Today's doses (prd F4 and screens B1 and H7): what is due now, what is next, and what was not confirmed.

One row of `medication_log` per scheduled dose. A dose has a window of 2 hours either side of its time (configurable per medicine later):

    before the window opens   upcoming: shown only as "next"
    window open               due now: the person can tap Taken
    window closed, no answer  unconfirmed: it stays `pending` and is shown as not confirmed, with a "Tell us why" prompt
    Taken                     status taken at the moment of the tap (it counts as late when that was over 60 minutes after the time)
    a reason                  "I took it, forgot to log" -> taken; every other reason -> missed, with the reason (and note) stored

Rows are made for today and tomorrow when the app asks. A dose is never made up for a time that was already over before anyone could
act on it (its window had closed, or the medicine did not exist yet), so nothing is ever called missed without a chance to answer.
Nothing here gives dose advice: the amount is the person's own label. Event payloads hold ids and enums only, never names or notes
(rules.md section 3).
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import psycopg
from psycopg.types.json import Jsonb

from app.core.errors import InvalidTransition, NotFound, ValidationFailed
from app.services import medication_stock

TZ = ZoneInfo("Asia/Singapore")
WINDOW = timedelta(hours=2)
LOOKBACK = timedelta(days=2)            # an unanswered dose older than this is no longer asked about
REASONS = ("forgot", "side_effects", "ran_out", "felt_fine", "cost", "away_from_home", "other")
TOOK_IT = "took_it"                      # not a reason it was missed: "I took it, I just forgot to log it"

STRENGTH_TAIL = re.compile(r"[\s,\-]*\d+(?:[.,]\d+)?\s?(?:mg|mcg|µg|g|ml|iu|%)(?:\s?/\s?\d*\s?(?:ml|g|mg|tab\w*))?\s*$", re.I)
UNIT_IN_DIRECTIONS = re.compile(r"\b(tab(?:let)?s?(?:/s)?|cap(?:sule)?s?(?:/s)?|ml|sachets?|drops?|puffs?|patch(?:es)?|teaspoons?|spoonfuls?)\b", re.I)
UNIT_WORD = {"tab": "Tab", "cap": "Capsule", "ml": "ml", "sach": "Sachet", "drop": "Drop", "puff": "Puff", "patc": "Patch", "teas": "Teaspoon", "spoo": "Spoonful"}
KIND_UNIT = {"prescription": "Tab", "otc": "Tab", "supplement": "Capsule", "tcm": "Dose"}


def short_name(name: str, strength: str | None) -> str:
    """The medicine's name without its strength: 'Metformin 500 mg' -> 'Metformin'. The strength is not what the person needs at dose time."""
    n = " ".join(name.split())
    if strength:
        n = re.sub(re.escape(" ".join(strength.split())), "", n, flags=re.I).strip(" ,-")
    n = STRENGTH_TAIL.sub("", n).strip(" ,-")
    return n or " ".join(name.split())


def dose_unit(kind: str, directions: str | None) -> str:
    """What one dose is counted in. The label's own wording when it has one ('Take 1 tab/s'), otherwise the usual unit for the type."""
    m = UNIT_IN_DIRECTIONS.search(directions or "")
    if m:
        word = m.group(1).lower()
        for prefix, label in UNIT_WORD.items():
            if word.startswith(prefix):
                return label
    return KIND_UNIT.get(kind, "Dose")


def amount_text(quantity: Decimal) -> str:
    return format(quantity.normalize(), "f")


def dose_title(name: str, strength: str | None, kind: str, directions: str | None, quantity: Decimal) -> str:
    """'Metformin, 1 Tab': what the person needs to take, not how strong it is."""
    unit = dose_unit(kind, directions)
    plural = "s" if quantity > 1 and unit != "ml" else ""
    return f"{short_name(name, strength)}, {amount_text(quantity)} {unit}{plural}"


def clock12(t: time) -> str:
    return t.strftime("%I:%M %p").lstrip("0").lower()


def period_word(hour: int) -> str:
    return "morning" if hour < 12 else "afternoon" if hour < 17 else "evening" if hour < 21 else "night"


def day_phrase(sched: datetime, now: datetime) -> str:
    """'Yesterday's evening dose', 'This morning's dose', "Monday's morning dose"."""
    local, today = sched.astimezone(TZ), now.astimezone(TZ).date()
    p = period_word(local.hour)
    if local.date() == today:
        return f"This {p}'s dose"
    if local.date() == today - timedelta(days=1):
        return f"Yesterday's {p} dose"
    return f"{local.strftime('%A')}'s {p} dose"


def when_phrase(sched: datetime, now: datetime) -> str:
    local, today = sched.astimezone(TZ), now.astimezone(TZ).date()
    day = "today" if local.date() == today else "tomorrow" if local.date() == today + timedelta(days=1) else local.strftime("%A")
    return f"{day} at {clock12(local.timetz().replace(tzinfo=None))}"


def _local(day: date, t: time) -> datetime:
    return datetime.combine(day, t, tzinfo=TZ)


def ensure_rows(conn: psycopg.Connection, user_id: str, now: datetime) -> int:
    """Make the dose rows for today and tomorrow (once; repeats change nothing). Returns how many were new."""
    today = now.astimezone(TZ).date()
    made = 0
    sched = conn.execute(
        "select s.id, s.medication_id, s.dose_time, s.created_at from medication_schedule s join medications m on m.id = s.medication_id "
        "where s.user_id = %s and s.deleted_at is null and m.deleted_at is null and s.dose_time is not null and m.as_needed is not true "
        "and (m.end_date is null or m.end_date >= %s)", (user_id, today)).fetchall()
    for sid, mid, t, created in sched:
        for day in (today, today + timedelta(days=1)):
            at = _local(day, t)
            if at < created or at + WINDOW < now:     # before the medicine existed, or already over before anyone could answer
                continue
            made += conn.execute(
                "insert into medication_log (user_id, medication_id, schedule_id, scheduled_at, status, source) "
                "values (%s, %s, %s, %s, 'pending', 'manual') on conflict (schedule_id, scheduled_at) do nothing",
                (user_id, mid, sid, at)).rowcount
    return made


def today(conn: psycopg.Connection, user_id: str, now: datetime) -> dict[str, Any]:
    """What the Home page shows: doses due now, doses not confirmed, the next dose, and whether today's are done."""
    ensure_rows(conn, user_id, now)
    has = conn.execute("select 1 from medication_schedule s join medications m on m.id = s.medication_id where s.user_id = %s and s.deleted_at is null "
                       "and m.deleted_at is null and s.dose_time is not null and m.as_needed is not true limit 1", (user_id,)).fetchone()
    rows = conn.execute(
        "select l.id, l.status::text, l.scheduled_at, l.taken_at, s.quantity, s.meal_relation::text, m.name, m.strength, m.kind::text, m.description "
        "from medication_log l join medication_schedule s on s.id = l.schedule_id join medications m on m.id = l.medication_id "
        "where l.user_id = %s and m.deleted_at is null and m.as_needed is not true and l.scheduled_at between %s and %s order by l.scheduled_at",
        (user_id, now - LOOKBACK - timedelta(hours=1), now + timedelta(days=2))).fetchall()
    due: list[dict[str, Any]] = []
    unconfirmed: list[dict[str, Any]] = []
    upcoming: list[tuple[datetime, str]] = []
    taken_today = 0
    local_today = now.astimezone(TZ).date()
    for lid, status, at, taken_at, qty, meal, name, strength, kind, directions in rows:
        title = dose_title(name, strength, kind, directions, qty)
        item = {"id": str(lid), "title": title, "time": clock12(at.astimezone(TZ).timetz().replace(tzinfo=None)), "with_food": meal != "na",
                "when_label": day_phrase(at, now)}
        if status == "taken" and taken_at is not None and taken_at.astimezone(TZ).date() == local_today:
            taken_today += 1
        if status != "pending":
            continue
        if now < at - WINDOW:
            upcoming.append((at, title))
        elif now <= at + WINDOW:
            due.append(item)
        elif now - at <= LOOKBACK:
            unconfirmed.append(item)
    unconfirmed.reverse()                                # most recent first
    nxt = min(upcoming, default=None)
    return {"has_medicines": bool(has), "due": due, "unconfirmed": unconfirmed[:3], "taken_today": taken_today,
            "next": {"title": nxt[1], "when": when_phrase(nxt[0], now)} if nxt else None}


def _load(conn: psycopg.Connection, user_id: str, dose_id: str) -> tuple[Any, ...]:
    try:
        row = conn.execute(
            "select l.id, l.status::text, l.scheduled_at, l.medication_id, m.name, m.strength from medication_log l "
            "join medications m on m.id = l.medication_id where l.id = %s and l.user_id = %s and l.schedule_id is not null for update of l",
            (dose_id, user_id)).fetchone()
    except psycopg.errors.InvalidTextRepresentation:
        conn.rollback()
        raise NotFound("Dose not found") from None
    if row is None:
        raise NotFound("Dose not found")
    return row


def _event(conn: psycopg.Connection, user_id: str, event: str, dose_id: Any, payload: dict[str, Any]) -> None:
    conn.execute("insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'user', %s, 'medication_log', %s, %s)",
                 (user_id, event, dose_id, Jsonb(payload)))


def _stock_taken(conn: psycopg.Connection, user_id: str, lid: Any, mid: Any, now: datetime) -> None:
    """The medicine's stock goes down by this dose's amount, in the same transaction (plan 4.3). See medication_stock.dose_taken."""
    if not medication_stock.stock_ready(conn):
        return
    q = conn.execute("select s.quantity from medication_log l left join medication_schedule s on s.id = l.schedule_id where l.id = %s", (lid,)).fetchone()
    medication_stock.dose_taken(conn, user_id, mid, lid, q[0] if q else None, now)


def mark_taken(conn: psycopg.Connection, user_id: str, dose_id: str, now: datetime) -> str:
    """The person says they took it, now. Only while the dose's window is open; saying it twice changes nothing (and takes nothing off the stock twice)."""
    lid, status, at, mid, _name, _strength = _load(conn, user_id, dose_id)
    if status == "taken":
        return "taken"
    if status != "pending":
        raise InvalidTransition("This dose has already been answered.")
    if now < at - WINDOW:
        raise InvalidTransition("It is not time for this dose yet.")
    conn.execute("update medication_log set status = 'taken', taken_at = %s where id = %s", (now, lid))
    late = now - at > timedelta(minutes=60)
    _event(conn, user_id, "dose.taken", lid, {"medication_id": str(mid), "late": late})
    _stock_taken(conn, user_id, lid, mid, now)
    return "taken"


def save_reason(conn: psycopg.Connection, user_id: str, dose_id: str, reason: str, note: str | None, now: datetime) -> str:
    """The answer to 'Why was it not confirmed?'. Only for a dose that is still pending and past its window."""
    if reason not in (*REASONS, TOOK_IT):
        raise ValidationFailed("Please choose one of the reasons.")
    lid, status, at, mid, name, strength = _load(conn, user_id, dose_id)
    if status != "pending":
        raise InvalidTransition("This dose has already been answered.")
    if now <= at + WINDOW:
        raise InvalidTransition("This dose can still be taken.")
    note = (note or "").strip()[:500] or None
    if reason == TOOK_IT:
        conn.execute("update medication_log set status = 'taken', taken_at = scheduled_at, miss_note = %s where id = %s", (note, lid))
        _stock_taken(conn, user_id, lid, mid, now)          # "I took it" is a dose taken, so it comes off the stock too
        out = "taken"
    else:
        conn.execute("update medication_log set status = 'missed', miss_reason = %s, miss_note = %s where id = %s", (reason, note, lid))
        out = "missed"
    _event(conn, user_id, "dose.reason.saved", lid, {"medication_id": str(mid), "reason": reason, "status": out, "has_note": bool(note)})
    if reason == "side_effects":                         # "A question will also be added to your list when you save."
        conn.execute("insert into doctor_questions (user_id, text, origin, status) values (%s, %s, 'agent_suggested', 'open')",
                     (user_id, f"I missed a dose of {short_name(name, strength)} because of side effects. Can we talk about them?"))
    return out
