"""Barrier to action and morning anchoring: turn what gets in the way of doses into one small, confirmable change, and find the routine a dose can be tied to.

Placeholder wired into app/agents/hooks.py. Replace the bodies; keep the two function signatures.
  run(user_id, write)                          the nightly/reflection step: returns a small dict that is stored in the agent trace
  nudges(user_id, now, have_keys, max_new)     returns notification rows not already stored: (key, kind, title, body, route, valid_until)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


def run(user_id: Any, write: bool = False) -> dict[str, Any]:
    return {"skipped": "not built yet"}


def nudges(user_id: Any, now: datetime, have_keys: set[str], max_new: int) -> list[tuple[str, str, str, str, str, datetime]]:
    return []
