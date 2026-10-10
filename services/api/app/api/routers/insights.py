"""The Insights tab (screens C1 to C6 and C8):

  GET /insights/overview|glucose|food|activity|sleep|medication?days=7|30|90
  GET /insights/sprint

Read-only. Every number is computed in code from the person's stored data (app/services/insights.py); no model is called.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.db import logstore
from app.schemas import insights as S
from app.services import insights as svc

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
async def medication(days: int = Query(30)):
    return S.MedicationInsights.model_validate(await _run(svc.medication, _days(days), _today(), datetime.now(svc.TZ)))


@router.get("/sprint", response_model=S.SensorRun, response_model_by_alias=True)
async def sensor_run():
    return S.SensorRun.model_validate(await _run(svc.sensor_run, _today()))
