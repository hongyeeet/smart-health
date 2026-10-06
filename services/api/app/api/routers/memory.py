"""GET /memory/facts, POST /memory/facts/{id}/action, GET /memory/digest, GET /memory/audit, GET /memory/progress.

"What Smart Health has learned" (PRD F16): the person sees every fact the agent proposed, with why, and can confirm, edit or delete it.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.db import memorystore

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
