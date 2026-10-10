"""Where the learning-loop modules plug into the orchestrator and the notification list. One place, so each module is its own file.

  dose_nudges  dose reminders inside their window: exempt from the daily cap and quiet hours (keys start with "dose-")
  extra_nudges everything else a module wants to say: counts towards the cap and waits for quiet hours to end
  reflect      the nightly step of every module; a module that fails never stops the others
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.agents import barrier_actions, dose_timing, glucose_feedback, preventive

logger = logging.getLogger(__name__)
REFLECTORS = {"dose_timing": dose_timing, "barrier_actions": barrier_actions, "preventive": preventive, "glucose_feedback": glucose_feedback}
Row = tuple[str, str, str, str, str, datetime]


def _is_dose(row: Row) -> bool:
    return row[0].startswith("dose-")


def dose_nudges(user_id: Any, now: datetime, have_keys: set[str]) -> list[Row]:
    out: list[Row] = []
    for name, mod in (("dose_timing", dose_timing), ("barrier_actions", barrier_actions)):
        try:
            out += [r for r in mod.nudges(user_id, now, have_keys, 99) if _is_dose(r)]   # an anchored dose reminder is a dose reminder
        except Exception:
            logger.exception("%s dose reminders failed; the other reminders are unaffected", name)
    return out


def extra_nudges(user_id: Any, now: datetime, have_keys: set[str], max_new: int) -> list[Row]:
    out: list[Row] = []
    for name, mod in (("barrier_actions", barrier_actions), ("preventive", preventive), ("glucose_feedback", glucose_feedback)):
        if len(out) >= max_new:
            break
        try:
            out += [r for r in mod.nudges(user_id, now, have_keys, max_new - len(out)) if not _is_dose(r)]
        except Exception:
            logger.exception("%s nudges failed; the other reminders are unaffected", name)
    return out[:max_new]


def reflect(user_id: Any, write: bool) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, mod in REFLECTORS.items():
        try:
            out[name] = mod.run(user_id, write=write)
        except Exception as e:
            logger.exception("%s reflection failed", name)
            out[name] = {"error": type(e).__name__}
    return out
