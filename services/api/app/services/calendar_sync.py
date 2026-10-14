"""Puts a medicine's dose times on Google Calendar through a Workato recipe (prd F4, docs/specs/f4-calendar.md, D-074).

After a medicine is saved the app queues a sync for it (one row in `calendar_syncs`) and a background job makes one calendar event per
dose time per day for the next 14 days, one at a time, saving progress after each so the loading page can show "12 of 28". Every day the
next 14 days are topped up (`top_up_all`). The calendar's default reminder (set to "at the time of the event") gives the notification. Rules:

  - an only-when-needed medicine has no dose times, so it gets no events (skipped)
  - events are made from the person's own saved label: the title says what to take ("CRESTOR, 1 Tab"), never a dose the label did not give
  - nothing is made twice: a retry only makes the dose times that have no event yet
  - if Workato is not set up the sync is skipped and the app carries on; a failure never stops the medicine from being saved
  - only the medicine's name and amount go out, never a patient name, ID or note; event ids and counts only go in the event log
  - an event that is no longer right is taken off the calendar again, then made again if it still belongs: a removed medicine, a shortened
    course, a dose time that is gone, or a time that moved (the learned time changed). The remove recipe finds the event by its exact title and
    time window, so nothing else on the calendar is touched. Without the remove recipe, old events stay as they are (and no second one is made)

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

from app.agents import dose_timing
from app.core.errors import ExternalServiceError, NotFound
from app.db import logstore
from app.integrations.workato import CalendarEvent
from app.services.dose_store import dose_title

logger = logging.getLogger(__name__)
TZ = ZoneInfo("Asia/Singapore")
EVENT_MINUTES = 15                       # how long the calendar event lasts
DAYS = 14                                # how many days ahead have events (topped up every day)
RECENT = timedelta(minutes=3)            # a sync that was updated this recently and is running is not started a second time
_locks: dict[str, threading.Lock] = {}
_guard = threading.Lock()


class EventMaker(Protocol):
    @property
    def configured(self) -> bool: ...
    def create_event(self, payload: dict[str, Any]) -> CalendarEvent: ...
    @property
    def remove_configured(self) -> bool: ...
    def remove_event(self, payload: dict[str, Any]) -> None: ...


def _lock_for(med_id: str) -> threading.Lock:
    with _guard:
        return _locks.setdefault(med_id, threading.Lock())


def _until(end: date) -> str:
    """The last day of the repeat, as the calendar wants it: the end of that day in Singapore, written in UTC."""
    return datetime.combine(end, time(23, 59, 59), tzinfo=TZ).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def learned_offset(conn: psycopg.Connection, user_id: str, med_id: str, now: datetime) -> int:
    """Minutes after the dose time at which this person usually takes the medicine (0, 15, 30 or 45), from their own taken doses.

    It is the dose-timing agent's preferred offset (agents/dose_timing.py): the one nearest the usual delay of the last 30 doses that were
    taken after their set time, once there are 7 of them, else 0 (the label's own time). Nothing is tried or learned here, and the
    dose window the reminders obey (the dose time to 60 minutes after it) always holds. Only reads."""
    rows = conn.execute(
        "select scheduled_at, taken_at from medication_log where user_id = %s and medication_id = %s and schedule_id is not null "
        "and status = 'taken' and taken_at is not null and taken_at > scheduled_at and scheduled_at > %s order by scheduled_at desc limit 200",
        (user_id, med_id, now - timedelta(days=dose_timing.HISTORY_DAYS))).fetchall()
    return dose_timing.learned_offset(dose_timing.usable_delays((r[0], r[1]) for r in rows))


def plan(conn: psycopg.Connection, user_id: str, med_id: str, now: datetime) -> list[dict[str, Any]]:
    """The events to make for a medicine: one per dose time per day for the next DAYS days, in time order.

    Each event sits at the dose time plus the person's learned offset (`learned_offset`), so a person who usually takes it a little after the
    label's time is reminded then. The payload has the shape of the Workato recipe's fields (summary, description, start and end with dateTime and timeZone), so the recipe's
    "Create event" step can use them as they are. A day that is past, before the medicine starts or after its end date gets no event."""
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
    learned = learned_offset(conn, user_id, med_id, now)
    events = []
    for sid, t, qty, meal in conn.execute(
            "select id, dose_time, quantity, meal_relation::text from medication_schedule where medication_id = %s and user_id = %s "
            "and deleted_at is null and dose_time is not null order by dose_time", (med_id, user_id)).fetchall():
        title = dose_title(name, strength, kind, directions, qty)
        for offset in range(DAYS):
            day = today + timedelta(days=offset)
            if day < first_day or (end_date and day > end_date):
                continue
            at = datetime.combine(day, t, tzinfo=TZ) + timedelta(minutes=learned)      # the person's own usual time, not only the label's
            if at <= now:
                continue                                    # that time has passed today
            events.append({
                "request_id": f"{med_id}:{sid}:{day.isoformat()}", "source": "smart-health", "schedule_id": str(sid), "date": day.isoformat(),
                "time": t.strftime("%H:%M"), "offset_min": learned, "summary": f"Take {title}",
                "description": f"{title}{', with food' if meal != 'na' else ''}. From your Smart Health medicine list.",
                "start": {"dateTime": at.isoformat(), "timeZone": "Asia/Singapore"},
                "end": {"dateTime": (at + timedelta(minutes=EVENT_MINUTES)).isoformat(), "timeZone": "Asia/Singapore"},
            })
    events.sort(key=lambda e: (e["date"], e["time"]))
    return events


def _key(e: dict[str, Any]) -> tuple[str, str]:
    """An event is one dose time on one day."""
    return str(e.get("schedule_id")), str(e.get("date"))


def _start_of(e: dict[str, Any]) -> str:
    """When a stored event starts. Events made before the learned time existed carry only the dose time, at which they were made."""
    return str(e.get("start") or f"{e['date']}T{e['time']}:00+08:00")


def stale_events(stored: list[dict[str, Any]], planned: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    """The stored events that are still to come but are no longer right: the plan has no event for that dose time and day any more (the
    medicine was removed, the course ended, the dose time is gone), or it now starts at another time. Events whose time has passed are left."""
    want = {_key(p): datetime.fromisoformat(p["start"]["dateTime"]) for p in planned}
    out = []
    for e in stored:
        start = datetime.fromisoformat(_start_of(e))
        if start <= now:
            continue
        if want.get(_key(e)) != start:
            out.append(e)
    return out


def _summary_for(conn: psycopg.Connection, med_id: str, schedule_id: str) -> str | None:
    """The title an event of this dose time was made with ("Take CRESTOR, 1 Tab"), worked out again for events made before titles were kept.
    Reads a removed medicine too (its rows stay)."""
    r = conn.execute("select m.name, m.strength, m.kind::text, m.description, s.quantity from medication_schedule s join medications m on m.id = s.medication_id "
                     "where s.id = %s and m.id = %s", (schedule_id, med_id)).fetchone()
    return None if r is None else f"Take {dose_title(r[0], r[1], r[2], r[3], r[4])}"


def allowed(conn: psycopg.Connection, user_id: str) -> bool:
    """Whether the person has agreed to calendar reminders (the consent "calendar_access" is on). Without it nothing goes to any calendar."""
    return conn.execute("select 1 from consents where user_id = %s and kind::text = 'calendar_access' and revoked_at is null limit 1", (user_id,)).fetchone() is not None


def queue(conn: psycopg.Connection, user_id: str, med_id: str, *, configured: bool, now: datetime | None = None, consent: bool = True) -> tuple[str, bool]:
    """Make (or refresh) the medicine's sync row. Returns (sync id, whether a background run should be started)."""
    now = now or datetime.now(TZ)
    events = plan(conn, user_id, med_id, now)
    old = conn.execute("select id, status, events, updated_at from calendar_syncs where medication_id = %s and user_id = %s", (med_id, user_id)).fetchone()
    stale = stale_events(list(old[2] or []) if old else [], events, now)
    gone = {_key(e) for e in stale}
    made = {_key(e) for e in (old[2] if old else [])} - gone
    done = sum(1 for e in events if _key(e) in made)
    if not events and not stale:
        status, reason = "skipped", "as_needed"
    elif not events or stale:
        status, reason = ("queued", None) if consent and configured else (("skipped", "no_consent") if not consent else ("skipped", "not_configured"))
    elif not consent:
        status, reason = "skipped", "no_consent"
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


def queue_cleanup(conn: psycopg.Connection, user_id: str, med_id: str) -> tuple[str, bool] | None:
    """After a medicine was removed: queue a run that takes its events that are still to come off the calendar. None when none were ever made.
    The calendar consent is not asked: the events were made with it, and the person has just removed the medicine."""
    row = conn.execute("select id, events from calendar_syncs where medication_id = %s and user_id = %s", (med_id, user_id)).fetchone()
    if row is None or not row[1]:
        return None
    conn.execute("update calendar_syncs set status = 'queued', reason = null, error_code = null, finished_at = null, updated_at = now() where id = %s", (row[0],))
    return str(row[0]), True


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
        today = now_fn().astimezone(TZ).date().isoformat()
        events = [e for e in events if str(e.get("date", today)) >= today]       # days that are over are not kept
        try:
            todo = plan(conn, user_id, med_id, now_fn())
        except NotFound:
            todo = []                                        # the medicine was removed: nothing is made, what is still to come is taken off
        stale = stale_events(events, todo, now_fn())
        for e in stale:                                      # the title an event was made with, for events made before titles were kept
            if not e.get("summary"):
                e["summary"] = _summary_for(conn, med_id, str(e.get("schedule_id"))) or ""
        conn.execute("update calendar_syncs set status = 'running', attempts = attempts + 1, events_total = %s, error_code = null, updated_at = now() "
                     "where id = %s", (len(todo), sync_id))
    with _lock_for(med_id):
        failed = 0
        removed = 0
        last_error: str | None = None
        for e in stale:                                      # first take off what is no longer right, so a moved event is not there twice
            if not client.remove_configured or not e.get("summary"):
                logger.warning("calendar event not removed: %s", "remove recipe not set up" if not client.remove_configured else "title unknown")
                continue
            start = _start_of(e)
            end = (datetime.fromisoformat(start) + timedelta(minutes=EVENT_MINUTES)).isoformat()
            try:
                client.remove_event({"request_id": f"{med_id}:{e.get('schedule_id')}:{e.get('date')}", "source": "smart-health", "summary": e["summary"],
                                     "start": {"dateTime": start, "timeZone": "Asia/Singapore"}, "end": {"dateTime": end, "timeZone": "Asia/Singapore"}})
            except ExternalServiceError as err:
                failed += 1
                last_error = err.code
                logger.warning("calendar event not removed: %s", err.code)
                continue
            events.remove(e)
            removed += 1
            with _tx() as conn:
                conn.row_factory = tuple_row
                conn.execute("update calendar_syncs set events = %s, updated_at = now() where id = %s", (Jsonb(events), sync_id))
        made = {_key(e) for e in events}
        for ev in todo:
            if _key(ev) in made:
                continue
            try:
                result = client.create_event(ev)
            except ExternalServiceError as e:
                failed += 1
                last_error = e.code
                logger.warning("calendar event not made: %s", e.code)
                continue
            events.append({"schedule_id": ev["schedule_id"], "date": ev["date"], "time": ev["time"], "event_id": result.event_id or ev["request_id"],
                           "start": ev["start"]["dateTime"], "summary": ev["summary"]})
            made.add(_key(ev))
            with _tx() as conn:                                  # progress is saved after every event so the loading page can show it
                conn.row_factory = tuple_row
                conn.execute("update calendar_syncs set events = %s, events_done = %s, updated_at = now() where id = %s", (Jsonb(events), len(made), sync_id))
        with _tx() as conn:
            conn.row_factory = tuple_row
            ok = failed == 0
            conn.execute("update calendar_syncs set status = %s, error_code = %s, finished_at = now(), updated_at = now() where id = %s",
                         ("done" if ok else "failed", None if ok else last_error, sync_id))
            conn.execute("insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'agent', 'calendar.sync.finished', "
                         "'calendar_syncs', %s, %s)", (user_id, sync_id, Jsonb({"status": "done" if ok else "failed", "events": len(made), "removed": removed, "failed": failed,
                                                                              "error_code": last_error})))
    logger.info("calendar sync finished events=%d failed=%d", len(made), failed)


def top_up_all(client: EventMaker, *, now_fn: Callable[[], datetime] = lambda: datetime.now(TZ)) -> dict[str, int]:
    """Every day: for each person the scheduler serves (Mr Tan too: a calendar event is sent out and only a sync row is kept in his record) who has
    agreed to calendar reminders, make the events for the next DAYS days that are not there yet. Returns counts. Never raises; one medicine failing does not stop the others."""
    out = {"people": 0, "medicines": 0, "events": 0, "failed": 0}
    if not client.configured:
        return out
    try:
        from app.services import scheduler

        keys = scheduler._users()
    except Exception:   # noqa: BLE001
        logger.exception("calendar top-up could not read the people it serves")
        return out
    for key in keys:
        try:
            user = logstore.user_id_for_key(key)
        except KeyError:
            continue
        try:
            with _tx() as conn:
                conn.row_factory = tuple_row
                if not allowed(conn, str(user)):
                    continue
                meds_ = [str(r[0]) for r in conn.execute(
                    "select m.id from medications m where m.user_id = %s and m.deleted_at is null and m.as_needed is not true "
                    "and exists (select 1 from medication_schedule s where s.medication_id = m.id and s.deleted_at is null and s.dose_time is not null)",
                    (str(user),)).fetchall()]
            out["people"] += 1
            for med_id in meds_:
                try:
                    with _tx() as conn:
                        conn.row_factory = tuple_row
                        sync_id, go = queue(conn, str(user), med_id, configured=True, now=now_fn())
                    if go:
                        run(sync_id, client, now_fn=now_fn)
                        out["medicines"] += 1
                except Exception:   # noqa: BLE001
                    out["failed"] += 1
                    logger.exception("calendar top-up failed for one medicine")
        except Exception:   # noqa: BLE001
            logger.exception("calendar top-up failed for one person")
    logger.info("calendar top-up %s", out)
    return out

