"""GET /memory/facts, POST /memory/facts/{id}/action, GET /memory/digest, GET /memory/audit, GET /memory/progress,
GET /memory/progress/days, GET /memory/barriers/summary.

"What Equinox has learned" (PRD F16): the person sees every fact the agent proposed, with why, and can confirm, edit or delete it.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.db import memorystore
from app.schemas.barriers import BarrierSummary
from app.schemas.diet import DietDays
from app.services import barrier_kpis, diet_days

router = APIRouter(prefix="/memory", tags=["memory"])


class FactAction(BaseModel):
    action: Literal["confirm", "edit", "delete"]
    text: str | None = Field(None, max_length=300)


@router.get("/facts")
async def facts() -> dict:
    return await run_in_threadpool(memorystore.list_facts)


@router.post("/facts/{fact_id}/action")
async def fact_action(fact_id: str, body: FactAction) -> dict:
    try:
        return await run_in_threadpool(memorystore.act, fact_id, body.action, body.text)
    except (memorystore.NotFound, ValueError) as e:
        if isinstance(e, memorystore.NotFound):
            raise HTTPException(status_code=404, detail="That fact was not found.")
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/digest")
async def digest(days: int = 7) -> dict:
    return await run_in_threadpool(memorystore.digest, max(1, min(days, 31)))


@router.get("/audit")
async def audit(limit: int = 15) -> list[dict]:
    return await run_in_threadpool(memorystore.audit_trail, max(1, min(limit, 50)))


@router.get("/usage")
async def ai_usage() -> dict:
    from app.services import usage

    return await run_in_threadpool(usage.today)


@router.get("/progress")
async def progress() -> dict:
    return await run_in_threadpool(memorystore.progress)


@router.get("/progress/days", response_model=DietDays, response_model_by_alias=True)
async def progress_days(start: date = Query(..., alias="from"), end: date = Query(..., alias="to")) -> DietDays:
    """Diet tracking calendar: each Singapore day from `from` to `to` (inclusive, at most 92 days) with its meals and macro totals."""
    try:
        return DietDays.model_validate(await run_in_threadpool(diet_days.progress_days, start, end))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/barriers/summary", response_model=BarrierSummary, response_model_by_alias=True)
async def barrier_summary() -> BarrierSummary:
    """The numbers for the "What gets in the way" row on K2: missed doses this week, on-time share, top reason, confirmed barrier ideas."""
    return BarrierSummary.model_validate(await run_in_threadpool(barrier_kpis.summary))
