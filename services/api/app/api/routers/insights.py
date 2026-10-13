"""The Insights tab (screens C1 to C6 and C8):

  GET /insights/overview|glucose|food|activity|sleep|medication?days=7|30|90   (medication also takes ?month=YYYY-MM, the calendar)
  GET /insights/timeline?days=7|30|90   (the overview charts on one time axis: app/services/insights_timeline.py)
  GET /insights/overview/days?from=YYYY-MM-DD&to=YYYY-MM-DD   (the overview calendar, at most 92 days)
  GET /insights/sprint
  GET /insights/heart?days=7|30|90         (heart rate and SpO2, C4 and C5; app/services/insights_heart.py)
  GET /insights/blood-pressure?days=7|30|90  (C5; manual readings)

Read-only. Every number is computed in code from the person's stored data (app/services/insights.py); no model is called.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.db import logstore
from app.schemas import insights as S
from app.schemas import insights_heart as HS
from app.services import insights as svc
from app.services import insights_heart as heart_svc
from app.services import insights_timeline as tl_svc

router = APIRouter(prefix="/insights", tags=["insights"])


def _days(days: int) -> int:
    if days not in svc.ALLOWED_DAYS:
        raise HTTPException(422, f"days must be one of {list(svc.ALLOWED_DAYS)}")
    return days


async def _run(fn: Callable[..., dict[str, Any]], *args: Any) -> dict[str, Any]:
    user = str(logstore.current_user())

    def work() -> dict[str, Any]:
        with logstore.tx() as conn:
            return fn(conn, user, *args)

    return await run_in_threadpool(work)


def _today():
    return datetime.now(svc.TZ).date()


@router.get("/overview", response_model=S.Overview, response_model_by_alias=True)
async def overview(days: int = Query(7)):
    return S.Overview.model_validate(await _run(svc.overview, _days(days), _today()))


@router.get("/timeline", response_model=S.Timeline, response_model_by_alias=True)
async def timeline(days: int = Query(7)):
    return S.Timeline.model_validate(await _run(tl_svc.timeline, _days(days), _today()))


@router.get("/overview/days", response_model=S.OverviewDays, response_model_by_alias=True)
async def overview_days(from_: date = Query(alias="from"), to: date = Query(...)):
    if to < from_:
        raise HTTPException(422, "to must be on or after from")
    if (to - from_).days + 1 > svc.MAX_DAY_RANGE:
        raise HTTPException(422, f"at most {svc.MAX_DAY_RANGE} days at a time")
    return S.OverviewDays.model_validate(await _run(svc.overview_days, from_, to, _today()))


@router.get("/glucose", response_model=S.GlucoseInsights, response_model_by_alias=True)
async def glucose(days: int = Query(30)):
    return S.GlucoseInsights.model_validate(await _run(svc.glucose, _days(days), _today()))


@router.get("/food", response_model=S.FoodInsights, response_model_by_alias=True)
async def food(days: int = Query(30)):
    return S.FoodInsights.model_validate(await _run(svc.food, _days(days), _today()))


@router.get("/activity", response_model=S.ActivityInsights, response_model_by_alias=True)
async def activity(days: int = Query(30)):
    return S.ActivityInsights.model_validate(await _run(svc.activity, _days(days), _today()))


@router.get("/sleep", response_model=S.SleepInsights, response_model_by_alias=True)
async def sleep(days: int = Query(30)):
    return S.SleepInsights.model_validate(await _run(svc.sleep, _days(days), _today()))


@router.get("/medication", response_model=S.MedicationInsights, response_model_by_alias=True)
async def medication(days: int = Query(30), month: str | None = Query(None, description="YYYY-MM or \"latest\": one calendar month (the app's calendar); without it, the last `days` days")):
    if month is not None:
        if month != "latest" and not re.fullmatch(r"20\d\d-(0[1-9]|1[0-2])", month):
            raise HTTPException(422, "month must look like 2026-10, or be the word latest")
        return S.MedicationInsights.model_validate(await _run(svc.medication_month, None if month == "latest" else month, _today(), datetime.now(svc.TZ)))
    return S.MedicationInsights.model_validate(await _run(svc.medication, _days(days), _today(), datetime.now(svc.TZ)))


@router.get("/sprint", response_model=S.SensorRun, response_model_by_alias=True)
async def sensor_run():
    return S.SensorRun.model_validate(await _run(svc.sensor_run, _today()))


@router.get("/heart", response_model=HS.HeartInsights, response_model_by_alias=True)
async def heart(days: int = Query(30)):
    return HS.HeartInsights.model_validate(await _run(heart_svc.heart, _days(days), _today()))


@router.get("/blood-pressure", response_model=HS.BloodPressureInsights, response_model_by_alias=True)
async def blood_pressure(days: int = Query(30)):
    return HS.BloodPressureInsights.model_validate(await _run(heart_svc.blood_pressure, _days(days), _today()))
