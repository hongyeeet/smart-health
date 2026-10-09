"""Puts a medicine's dose times on Google Calendar through a Workato recipe (prd F4, docs/specs/f4-calendar.md, D-074).

After a medicine is saved the app queues a sync for it (one row in `calendar_syncs`) and a background job makes one repeating calendar
event per dose time, one at a time, saving progress after each so the loading page can show "2 of 3". The event carries a reminder at the dose
time, so the phone's calendar app gives the notification. Rules:

  - an only-when-needed medicine has no dose times, so it gets no events (skipped)
  - events are made from the person's own saved label: the title says what to take ("CRESTOR, 1 Tab"), never a dose the label did not give
  - nothing is made twice: a retry only makes the dose times that have no event yet
  - if Workato is not set up the sync is skipped and the app carries on; a failure never stops the medicine from being saved
  - only the medicine's name and amount go out, never a patient name, ID or note; event ids and counts only go in the event log

The Workato call itself is in `app/integrations/workato.py`.
"""
from __future__ import annotations

import logging
import threading
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Callable, Protocol
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb

from app.core.errors import ExternalServiceError, NotFound
from app.db import logstore
from app.integrations.workato import CalendarEvent
from app.services.dose_store import dose_title

logger = logging.getLogger(__name__)
TZ = ZoneInfo("Asia/Singapore")
EVENT_MINUTES = 15                       # how long the calendar event lasts
RECENT = timedelta(minutes=3)            # a sync that was updated this recently and is running is not started a second time
_locks: dict[str, threading.Lock] = {}
_guard = threading.Lock()


class EventMaker(Protocol):
    @property
    def configured(self) -> bool: ...
    def create_event(self, payload: dict[str, Any]) -> CalendarEvent: ...


def _lock_for(med_id: str) -> threading.Lock:
    with _guard:
        return _locks.setdefault(med_id, threading.Lock())


def _until(end: date) -> str:
    """The last day of the repeat, as the calendar wants it: the end of that day in Singapore, written in UTC."""
    return datetime.combine(end, time(23, 59, 59), tzinfo=TZ).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def plan(conn: psycopg.Connection, user_id: str, med_id: str, now: datetime) -> list[dict[str, Any]]:
    """The events to make for a medicine: one repeating event per dose time, in time order."""
    try:
        med = conn.execute("select name, strength, kind::text, description, start_date, end_date from medications "
                           "where id = %s and user_id = %s and deleted_at is null", (med_id, user_id)).fetchone()
    except psycopg.errors.InvalidTextRepresentation:
        conn.rollback()
        raise NotFound("Medicine not found") from None
    if med is None:
        raise NotFound("Medicine not found")
    name, strength, kind, directions, start_date, end_date = med
    today = now.astimezone(TZ).date()
    first_day = max(start_date or today, today)
    if end_date and end_date < first_day:
        return []                                            # a finished course: nothing is left to remind about
    events = []
    for sid, t, qty, meal in conn.execute(
            "select id, dose_time, quantity, meal_relation::text from medication_schedule where medication_id = %s and user_id = %s "
            "and deleted_at is null and dose_time is not null order by dose_time", (med_id, user_id)).fetchall():
        at = datetime.combine(first_day, t, tzinfo=TZ)
        if at <= now:
            at += timedelta(days=1)                         # today's time has passed: the first reminder is tomorrow
        title = dose_title(name, strength, kind, directions, qty)
        rrule = "RRULE:FREQ=DAILY" + (f";UNTIL={_until(end_date)}" if end_date else "")
        events.append({
            "request_id": f"{med_id}:{sid}", "source": "smart-health", "schedule_id": str(sid), "time": t.strftime("%H:%M"),
            "title": f"Take {title}", "description": f"{title}{', with food' if meal != 'na' else ''}. From your Smart Health medicine list.",
            "start": at.isoformat(), "end": (at + timedelta(minutes=EVENT_MINUTES)).isoformat(), "timezone": "Asia/Singapore",
            "recurrence": rrule, "reminder_minutes": 0,
        })
    return events


def queue(conn: psycopg.Connection, user_id: str, med_id: str, *, configured: bool, now: datetime | None = None) -> tuple[str, bool]:
    """Make (or refresh) the medicine's sync row. Returns (sync id, whether a background run should be started)."""
    now = now or datetime.now(TZ)
    events = plan(conn, user_id, med_id, now)
    old = conn.execute("select id, status, events, updated_at from calendar_syncs where medication_id = %s and user_id = %s", (med_id, user_id)).fetchone()
    made = {e["schedule_id"] for e in (old[2] if old else [])}
    done = sum(1 for e in events if e["schedule_id"] in made)
    if not events:
        status, reason = "skipped", "as_needed"
    elif not configured:
        status, reason = "skipped", "not_configured"
    elif done == len(events):
        status, reason = "done", None
    else:
        status, reason = "queued", None
    if old and old[1] == "running" and now - old[3].astimezone(TZ) < RECENT:
        return str(old[0]), False                            # already running: do not start it twice
    row = conn.execute(
        """insert into calendar_syncs (user_id, medication_id, status, reason, events_total, events_done)
           values (%s, %s, %s, %s, %s, %s)
           on conflict (medication_id) do update set status = excluded.status, reason = excluded.reason, events_total = excluded.events_total,
             events_done = excluded.events_done, error_code = null, finished_at = case when excluded.status in ('done', 'skipped') then now() else null end,
             updated_at = now()
           returning id""", (user_id, med_id, status, reason, len(events), done)).fetchone()
    if row is None:
        raise RuntimeError("the database returned no row for an insert")
    return str(row[0]), status == "queued"


def owns(conn: psycopg.Connection, user_id: str, med_id: str) -> None:
    """Raise NotFound unless the medicine is the person's own."""
    try:
        row = conn.execute("select 1 from medications where id = %s and user_id = %s and deleted_at is null", (med_id, user_id)).fetchone()
    except psycopg.errors.InvalidTextRepresentation:
        conn.rollback()
        raise NotFound("Medicine not found") from None
    if row is None:
        raise NotFound("Medicine not found")


def status(conn: psycopg.Connection, user_id: str, med_id: str) -> dict[str, Any] | None:
    r = conn.execute("select status, reason, events_done, events_total, error_code from calendar_syncs where medication_id = %s and user_id = %s",
                     (med_id, user_id)).fetchone()
    return None if r is None else {"status": r[0], "reason": r[1], "events_done": r[2], "events_total": r[3], "error_code": r[4]}


def _tx() -> Any:
    return logstore.tx()


def run(sync_id: str, client: EventMaker, *, now_fn: Callable[[], datetime] = lambda: datetime.now(TZ)) -> None:
    """Make the missing events, one dose time at a time. Never raises: this runs in the background after the medicine was already saved."""
    try:
        _run(sync_id, client, now_fn)
    except Exception:   # noqa: BLE001 - a background job must never take the app down
        logger.exception("calendar sync crashed")
        try:
            with _tx() as conn:
                conn.row_factory = tuple_row
                conn.execute("update calendar_syncs set status = 'failed', error_code = 'error', finished_at = now(), updated_at = now() where id = %s", (sync_id,))
        except Exception:   # noqa: BLE001
            logger.exception("calendar sync could not record its own failure")


def _run(sync_id: str, client: EventMaker, now_fn: Callable[[], datetime]) -> None:
    with _tx() as conn:
        conn.row_factory = tuple_row
        row = conn.execute("select user_id, medication_id, events from calendar_syncs where id = %s", (sync_id,)).fetchone()
        if row is None:
            return
        user_id, med_id, events = str(row[0]), str(row[1]), list(row[2] or [])
        todo = plan(conn, user_id, med_id, now_fn())
        conn.execute("update calendar_syncs set status = 'running', attempts = attempts + 1, events_total = %s, error_code = null, updated_at = now() "
                     "where id = %s", (len(todo), sync_id))
    with _lock_for(med_id):
        made = {e["schedule_id"] for e in events}
        failed = 0
        last_error: str | None = None
        for ev in todo:
            if ev["schedule_id"] in made:
                continue
            try:
                result = client.create_event(ev)
            except ExternalServiceError as e:
                failed += 1
                last_error = e.code
                logger.warning("calendar event not made: %s", e.code)
                continue
            events.append({"schedule_id": ev["schedule_id"], "time": ev["time"], "event_id": result.event_id})
            made.add(ev["schedule_id"])
            with _tx() as conn:                                  # progress is saved after every event so the loading page can show it
                conn.row_factory = tuple_row
                conn.execute("update calendar_syncs set events = %s, events_done = %s, updated_at = now() where id = %s", (Jsonb(events), len(made), sync_id))
        with _tx() as conn:
            conn.row_factory = tuple_row
            ok = failed == 0
            conn.execute("update calendar_syncs set status = %s, error_code = %s, finished_at = now(), updated_at = now() where id = %s",
                         ("done" if ok else "failed", None if ok else last_error, sync_id))
            conn.execute("insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'agent', 'calendar.sync.finished', "
                         "'calendar_syncs', %s, %s)", (user_id, sync_id, Jsonb({"status": "done" if ok else "failed", "events": len(made), "failed": failed,
                                                                              "error_code": last_error})))
    logger.info("calendar sync finished events=%d failed=%d", len(made), failed)
