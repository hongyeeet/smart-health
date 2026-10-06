"""GET /nutrition/flags, GET /nutrition/lunch, POST /nutrition/suggestions/accept.

Food habits and lunch ideas for the person the request acts as (X-User). Numbers come from the person's own logged meals and the
Singapore food database (only as a shelf of lighter dishes), in code; see app/db/nutritionstore.py. Lunch texts and flag texts are templates, not model writing.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.db import logstore, nutritionstore

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/flags")
async def flags() -> list[dict]:
    """Food habits the memory loop noticed, each with lighter dishes to try next time, compared with the person's own logged numbers."""
    uid = logstore.current_user()

    def run():
        out = nutritionstore.food_habits(uid)
        for f in out:
            f["text"] = nutritionstore.habit_text(f)
        return out

    return await run_in_threadpool(run)


@router.get("/lunch")
async def lunch() -> dict:
    uid = logstore.current_user()

    def run():
        start, end = nutritionstore.lunch_window(uid)
        return {"windowStart": f"{start // 60:02d}:{start % 60:02d}", "windowEnd": f"{end // 60 % 24:02d}:{end % 60:02d}", "options": nutritionstore.lunch_options(uid)}

    return await run_in_threadpool(run)


class Accept(BaseModel):
    key: str
    kind: str = "suggestion"


@router.post("/suggestions/dismiss", status_code=204)
async def dismiss(body: Accept) -> None:
    """"Not for me": the suggestion is not shown again."""
    uid = logstore.current_user()
    await run_in_threadpool(nutritionstore.policy_reject, uid, body.kind if body.kind in ("suggestion", "activity") else "suggestion", body.key)


@router.post("/suggestions/accept", status_code=204)
async def accept(body: Accept) -> None:
    """The person chose this suggestion: the learning policy counts it as acted on, so it is shown more."""
    uid = logstore.current_user()
    await run_in_threadpool(nutritionstore.policy_act, uid, body.kind if body.kind in ("suggestion", "activity") else "suggestion", body.key)
