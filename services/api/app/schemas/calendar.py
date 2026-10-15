"""API shapes for the calendar reminders of a medicine (the loading page after a medicine is saved). camelCase on the wire."""
from __future__ import annotations

from typing import Literal

from app.schemas.medicines import Camel


class CalendarStatus(Camel):
    # none: no sync was ever started for this medicine; queued and running: being made; done; failed: can be retried; skipped: nothing to do
    status: Literal["none", "queued", "running", "done", "failed", "skipped"]
    message: str                      # plain words for the loading page
    events_done: int = 0
    events_total: int = 0
    can_retry: bool = False
    reason: Literal["as_needed", "not_configured"] | None = None
