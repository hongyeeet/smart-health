"""The doctor report (prd F12, docs/specs/f12-doctor-report.md):

  GET /brief/report?days=14     the numbers for the printable "Diabetes monitoring report" (7, 14, 30 or 90 days)

Read-only. Every number is computed in code from the person's stored data; no model is called. The person sees exactly what
the doctor sees: there is one report and this is it.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.db import logstore
from app.schemas.brief import DoctorReport
from app.services import doctor_report

router = APIRouter(prefix="/brief", tags=["brief"])


@router.get("/report", response_model=DoctorReport, response_model_by_alias=True)
async def get_report(days: int = Query(14)) -> DoctorReport:
    if days not in doctor_report.ALLOWED_DAYS:
        raise HTTPException(422, f"days must be one of {list(doctor_report.ALLOWED_DAYS)}")
    return await run_in_threadpool(_report, str(logstore.current_user()), days)


def _report(user: str, days: int) -> DoctorReport:
    with logstore.tx() as conn:
        inputs = doctor_report.load(conn, user, days, datetime.now(timezone.utc))
    return DoctorReport.model_validate(doctor_report.build(inputs))
