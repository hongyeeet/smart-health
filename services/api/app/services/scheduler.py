"""The scheduler: what runs without anyone opening the app (docs/specs/learning-loop.md 12.4).

  every minute   the reminder tick: which logs are due now, lunch ideas, the high-salt prompt (quiet: only changes are traced)
  every minute   the email dispatcher: the reminders that are also emails, sent through the Workato recipe
  nightly 02:00  the reflection: barriers, anchors and food habits, proposed as facts (never activated)
Both go through the orchestrator, so they are routed, guarded and logged like any other event. They run for the people named in
`scheduler_users` (default: Mr Tan, who has the six months of history the agent learns from) and for every person who started with
"Start as new person" and finished set-up (`scheduler_persons`), who the jobs address by user id (`logstore.internal_key`).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

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
    """The people the jobs serve: the configured ones, then everyone who finished set-up (a profile exists), by user id. Never raises."""
    keys = [u.strip() for u in settings.scheduler_users.split(",") if u.strip()]
    if settings.scheduler_persons:
        try:
            with tx() as c:
                rows = c.execute("select u.id from users u where coalesce(u.is_demo, false) = false and u.id <> %s "
                                 "and exists (select 1 from user_profile p where p.user_id = u.id) order by u.created_at", (logstore.MR_TAN_USER,)).fetchall()
            keys += [logstore.internal_key(r["id"]) for r in rows]
        except Exception:   # noqa: BLE001 - the people already named still get their jobs
            logger.exception("the scheduler could not list the people who finished set-up")
    return keys


def tick() -> None:
    for key in _users():
        try:
            orchestrator.run_event(key, "tick", quiet=True)
        except Exception:
            logger.exception("tick failed for %s", key)


def emails() -> None:
    """Send the reminder emails that are due (docs/specs/email-notifications.md). Cheap when the recipe is not set up: it returns at once."""
    from app.integrations.workato_email import WorkatoEmail
    from app.services import notify_email

    try:
        sender = WorkatoEmail.from_settings()
        if sender.configured:
            notify_email.dispatch(sender)
    except Exception:
        logger.exception("email dispatch failed")


def food_pictures() -> None:
    """Make the dish pictures that are waiting (at most 3 a minute; docs/specs/menu.md). Cheap when nothing is waiting."""
    try:
        from app.services import food_images

        food_images.generate_pending(limit=3)
    except Exception:   # noqa: BLE001 - a picture problem never stops the other jobs
        logger.exception("dish pictures job crashed")


def calendar_top_up() -> None:
    """Every day: the next 14 days of medicine reminders on Google Calendar for the people who agreed to them (services/calendar_sync.py)."""
    try:
        from app.integrations.workato import WorkatoClient
        from app.services import calendar_sync

        calendar_sync.top_up_all(WorkatoClient.from_settings())
    except Exception:   # noqa: BLE001 - a calendar problem never stops the other jobs
        logger.exception("the daily calendar top-up crashed")


def warm_review() -> None:
    """Fill the reviewer queue's cache for the people the scheduler serves, so the screen opens at once (the first lookup takes about 25 seconds)."""
    from app.services import review

    for key in _users():
        try:
            logstore.set_user(key, internal=True)
            uid = str(logstore.current_user())
            with tx() as c:
                dishes = review.logged_dishes(c, uid)
            review.build_queue(dishes, {}, 20)
        except Exception:
            logger.exception("warming the review queue failed for %s", key)
    try:
        with tx() as c:
            sample = review.sample_dishes(c)
        review.build_queue(sample, {}, 20)
    except Exception:
        logger.exception("warming the sample review queue failed")


def nightly_done_today(key: str) -> bool:
    logstore.set_user(key, internal=True)
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
    _scheduler.add_job(emails, IntervalTrigger(seconds=60), id="emails", max_instances=1, coalesce=True)
    _scheduler.add_job(food_pictures, IntervalTrigger(seconds=60), id="food_pictures", max_instances=1, coalesce=True)
    _scheduler.add_job(nightly, CronTrigger(hour=2, minute=0, timezone="Asia/Singapore"), id="nightly", max_instances=1, coalesce=True)
    _scheduler.add_job(calendar_top_up, CronTrigger(hour=3, minute=0, timezone="Asia/Singapore"), id="calendar_top_up", max_instances=1, coalesce=True)
    _scheduler.add_job(calendar_top_up, id="calendar_top_up_start", next_run_time=datetime.now(TZ) + timedelta(seconds=90), max_instances=1)   # after a restart
    _scheduler.add_job(warm_review, id="warm_review", next_run_time=datetime.now(TZ) + timedelta(seconds=30), max_instances=1)
    _scheduler.add_job(lambda: nightly(catch_up=True), id="nightly_catch_up", next_run_time=datetime.now(TZ), max_instances=1)  # after a restart
    _scheduler.start()
    logger.info("scheduler started for %s", _users())


def stop() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
