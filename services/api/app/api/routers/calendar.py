"""Calendar reminders for a medicine (prd F4, docs/specs/f4-calendar.md):

  GET  /medications/{id}/calendar         how far the reminders are (the loading page polls this after a medicine is saved)
  POST /medications/{id}/calendar/retry   make the reminders that are missing (also for a medicine saved before this existed)

The reminders are made in the background by a Workato recipe, one repeating Google Calendar event per dose time. A failure here never stops
a medicine from being saved: the medicine is already in the database before any of this starts.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.concurrency import run_in_threadpool
from psycopg.rows import tuple_row

from app.core.errors import NotFound
from app.db import logstore
from app.integrations.workato import WorkatoClient
from app.schemas.calendar import CalendarStatus
from app.services import calendar_sync as sync

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/medications", tags=["calendar"])

MESSAGES = {
    "none": "No calendar reminders have been added for this medicine yet.",
    "queued": "Getting ready to add your reminders to Google Calendar…",
    "running": "Adding your reminders to Google Calendar…",
    "done": "Your reminders are on your calendar.",
    "failed": "We could not add all your reminders just now. You can try again.",
    "skipped": "No calendar reminders were added.",
    "skipped:as_needed": "This medicine is only taken when needed, so there are no reminders to add.",
    "skipped:not_configured": "Calendar reminders are not set up yet, so none were added. Your medicine is saved.",
}


def to_status(s: dict[str, Any] | None) -> CalendarStatus:
    if s is None:
        return CalendarStatus(status="none", message=MESSAGES["none"], can_retry=True)
    key = f"{s['status']}:{s['reason']}" if s["status"] == "skipped" and s["reason"] else s["status"]
    return CalendarStatus(status=s["status"], message=MESSAGES.get(key, MESSAGES[s["status"]]), events_done=s["events_done"],
                          events_total=s["events_total"], can_retry=s["status"] in ("failed", "none"), reason=s["reason"])


def schedule_sync(background: BackgroundTasks, user: str, med_id: str) -> None:
    """Queue the reminders for a medicine and start them after the response. Never raises: the medicine is already saved."""
    try:
        client = WorkatoClient.from_settings()
        with logstore.tx() as conn:
            conn.row_factory = tuple_row
            sync_id, go = sync.queue(conn, user, med_id, configured=client.configured)
        if go:
            background.add_task(sync.run, sync_id, client)
    except Exception:   # noqa: BLE001 - calendar problems must never undo or hide a saved medicine
        logger.exception("could not queue calendar reminders")


@router.get("/{med_id}/calendar", response_model=CalendarStatus, response_model_by_alias=True)
async def get_calendar(med_id: str) -> CalendarStatus:
    return await run_in_threadpool(_status, str(logstore.current_user()), med_id)


def _status(user: str, med_id: str) -> CalendarStatus:
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        try:
            sync.owns(conn, user, med_id)
        except NotFound as e:
            raise HTTPException(404, str(e)) from None
        return to_status(sync.status(conn, user, med_id))


@router.post("/{med_id}/calendar/retry", response_model=CalendarStatus, response_model_by_alias=True)
async def retry_calendar(med_id: str, background: BackgroundTasks) -> CalendarStatus:
    user = str(logstore.current_user())
    await run_in_threadpool(_status, user, med_id)                          # 404 for someone else's medicine
    await run_in_threadpool(schedule_sync, background, user, med_id)
    return await run_in_threadpool(_status, user, med_id)
