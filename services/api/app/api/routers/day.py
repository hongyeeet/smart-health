"""The Day view (screens D1 and D2):

  GET /day/dates?days=90     the days with data, newest first, for the date arrows
  GET /day/{date}            one whole day (YYYY-MM-DD); a day with no data returns hasData false, not an error

Read-only. The logic is in app/services/day.py. A malformed date is a 422 from FastAPI's own parsing.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool

from app.db import logstore
from app.schemas import day as S
from app.services import day as svc
from app.services import insights as I

router = APIRouter(prefix="/day", tags=["day"])


async def _run(fn: Callable[..., dict[str, Any]], *args: Any) -> dict[str, Any]:
    user = str(logstore.current_user())

    def work() -> dict[str, Any]:
        with logstore.tx() as conn:
            return fn(conn, user, *args)

    return await run_in_threadpool(work)


def _today() -> date:
    return datetime.now(I.TZ).date()


# Declared before /{day} so that "dates" is never read as a date.
@router.get("/dates", response_model=S.DayDates, response_model_by_alias=True)
async def dates(days: int = Query(90, ge=1, le=366)):
    return S.DayDates.model_validate(await _run(svc.day_dates, _today(), days))


@router.get("/{day}", response_model=S.DayView, response_model_by_alias=True)
async def day(day: date):
    return S.DayView.model_validate(await _run(svc.day_view, day, _today()))
