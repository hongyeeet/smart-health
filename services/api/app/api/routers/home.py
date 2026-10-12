"""GET /home/banner: the one food banner on Home (docs/specs/app-flow-and-features.md 4B).

Two things can go in the banner, and the web app shows at most one of them:
  - `meal`: the mealtime that is open right now and not logged yet (the same rule as the Log tile and the meal reminder in
    app/db/logstore.py, so the banner and the reminder never disagree). Null outside a mealtime window or once it is logged.
  - `flag`: a food habit the person keeps eating that is high in salt or sugar (the same habits as GET /nutrition/flags, judged
    against the same thresholds in app/core/config.py). Null when no habit is flagged.
Numbers and the choice are made in code; the web app writes the words. Nothing here is a reminder, so it is not stored.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from app.core.config import settings
from app.db import logstore, nutritionstore

router = APIRouter(prefix="/home", tags=["home"])
logger = logging.getLogger(__name__)

CACHE_SECONDS = 60          # the banner for one person is reused this long; a meal or workout logged by that person ends it at once
PENDING_RETRY_SECONDS = 5   # while food types are still being worked out, ask again after this long
FOOD_TYPE_BUDGET = 1.2      # seconds the first look may wait for the food types before it answers without a flag
_cache: dict[str, tuple[float, int, dict]] = {}


def _meal_due_now() -> str | None:
    """The meal key ('breakfast', 'lunch' or 'dinner') when a mealtime is open and that meal is not logged yet."""
    p = logstore.progress()
    meals = next(i for i in p["items"] if i["key"] == "meals")
    if meals["status"] != "due":
        return None
    now = datetime.now(logstore.TZ)
    h = now.hour + now.minute / 60
    for start, end, key, _label in logstore.MEAL_WINDOWS:
        if start <= h < end:
            return key
    return None


def _food_flag() -> dict | None:
    """The first food habit (heaviest first, as GET /nutrition/flags orders them) that is high in salt or sugar.
    The catch-all "other" type is left out: "your other food" is not a thing the person can act on."""
    for habit in nutritionstore.food_habits(logstore.current_user(), swaps=False, classify_budget=FOOD_TYPE_BUDGET):
        if habit["type"] == "other":
            continue
        avg = habit["avg"]
        if (avg.get("sodium_mg") or 0) >= settings.habit_sodium_mg:
            kind = "salt"
        elif (avg.get("sugar_g") or 0) >= settings.habit_sugar_g:
            kind = "sugar"
        else:
            continue
        return {"kind": kind, "type": habit["type"], "label": habit["label"], "n": habit["n"]}
    return None


def build_banner() -> tuple[dict, bool]:
    """The banner, and whether it is complete. It is not complete while the food types are still being worked out."""
    complete = True
    with logstore.one_connection():
        meal = _meal_due_now()
        try:
            flag = _food_flag()
        except nutritionstore.HabitsPending:
            flag, complete = None, False
        except Exception:
            logger.exception("home banner: food flag unavailable")
            flag = None
    return {"meal": meal, "flag": flag}, complete


def cached_banner(now: float | None = None) -> dict:
    """The banner for the current person, reused for CACHE_SECONDS and until that person logs something (logstore.log_epoch)."""
    now = time.monotonic() if now is None else now
    key = logstore.current_user_key()
    epoch = logstore.log_epoch(key)
    hit = _cache.get(key)
    if hit and hit[1] == epoch and now < hit[0]:
        return hit[2]
    out, complete = build_banner()
    _cache[key] = (now + (CACHE_SECONDS if complete else PENDING_RETRY_SECONDS), epoch, out)
    return out


@router.get("/banner")
async def banner() -> dict:
    return await run_in_threadpool(cached_banner)
