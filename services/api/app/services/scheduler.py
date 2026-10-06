"""The scheduler: what runs without anyone opening the app (docs/specs/learning-loop.md 12.4).

  every minute   the reminder tick: which logs are due now, lunch ideas, the high-salt prompt (quiet: only changes are traced)
  nightly 02:00  the reflection: barriers, anchors and food habits, proposed as facts (never activated)
Both go through the orchestrator, so they are routed, guarded and logged like any other event. They run for the people named in
`scheduler_users` (default: the demo user only, so Mr Tan's record is never written to by a timer).
"""
from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.agents import orchestrator
from app.core.config import settings
from app.db import logstore
from app.db.logstore import TZ, tx

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


def _users() -> list[str]:
    return [u.strip() for u in settings.scheduler_users.split(",") if u.strip()]


def tick() -> None:
    for key in _users():
        try:
            orchestrator.run_event(key, "tick", quiet=True)
        except Exception:
            logger.exception("tick failed for %s", key)


def nightly_done_today(key: str) -> bool:
    logstore.set_user(key)
    with tx() as c:
        return bool(c.execute(
            "select 1 from agent_runs where user_id=%s and trigger='nightly' and status='ok' and (started_at at time zone 'Asia/Singapore')::date=%s limit 1",
            (logstore.current_user(), datetime.now(TZ).date()),
        ).fetchone())


def nightly(catch_up: bool = False) -> None:
    for key in _users():
        try:
            if nightly_done_today(key):
                continue
            if catch_up and datetime.now(TZ).hour < 2:
                continue  # before the first 02:00 of the day there is nothing to catch up
            orchestrator.run_event(key, "nightly", write=True)
        except Exception:
            logger.exception("nightly reflection failed for %s", key)


def start() -> None:
    global _scheduler
    if not settings.scheduler_enabled or _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler(timezone="Asia/Singapore")
    _scheduler.add_job(tick, IntervalTrigger(seconds=60), id="tick", max_instances=1, coalesce=True)
    _scheduler.add_job(nightly, CronTrigger(hour=2, minute=0, timezone="Asia/Singapore"), id="nightly", max_instances=1, coalesce=True)
    _scheduler.add_job(lambda: nightly(catch_up=True), id="nightly_catch_up", next_run_time=datetime.now(TZ), max_instances=1)  # after a restart
    _scheduler.start()
    logger.info("scheduler started for %s", _users())


def stop() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
