"""POST /logs, GET /logs/recent, DELETE /logs/{id}, GET /logs/today, GET /logs/context.

Every entry is written to the database (Bronze, Silver, then the Gold timeline and daily summary); see app/db/logstore.py.
Red-flag symptoms are saved and then sent to the urgent screen (tier 2). There is no glucose log: the CGM supplies glucose.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.agents.meal import flags_for
from app.db import logstore
from app.schemas.log import (
    CheckinInput, LogContext, LogFlag, LogInput, LogProgress, LogResult, LogSwap, MealInput, RecentEntry, SymptomInput, WorkoutInput,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/logs", tags=["logs"])

RED_FLAG_SYMPTOMS = {
    "Chest pain", "Confusion", "Fainting", "Breathlessness at rest", "Sudden vision loss or a curtain across my vision",
}


def _clock(dt) -> str:
    return dt.astimezone(logstore.TZ).strftime("%I:%M %p").lstrip("0").lower()


@router.post("", response_model=LogResult, response_model_by_alias=True)
async def create_log(input: LogInput) -> LogResult:
    return await run_in_threadpool(_create, input)


def _create(i) -> LogResult:
    if isinstance(i, MealInput):
        saved = logstore.create_meal(i)
        carbs = f", about {round(i.carbs_g)} g carbs" if i.carbs_g is not None else ""
        flags = flags_for(i.carbs_g, i.sugar_g, i.sodium_mg)
        salty = "high_salt" in flags
        return LogResult(
            id=saved["id"], kind="meal", title="Meal saved", landed_in="Your day", day=saved["day"], related="C3",
            detail=f"{i.name}{carbs}.",
            lines=[
                f"Eaten {_clock(i.start_at)} to {_clock(i.end_at)}.",
                "Nutrients are estimates" + (" until you confirm them." if not i.edited else ", with your changes."),
                "Your glucose rise will come from the sensor in about 2 hours.",
            ],
            flag=LogFlag(text="High salt estimated for this meal.", level="info") if salty else (LogFlag(text="High sugar estimated for this meal.", level="info") if "high_sugar" in flags else None),
            swap=LogSwap(text="Ask for the soup or gravy on the side next time.", source="Team-written tip, not medical advice") if salty else None,
        )
    if isinstance(i, WorkoutInput):
        saved = logstore.create_workout(i)
        wk = logstore.progress()
        return LogResult(
            id=saved["id"], kind="workout", title="Added to your day", landed_in="Your day and Activity insights", day=saved["day"], related="C4",
            detail=f"{i.activity or logstore.EXERCISE_WORD[i.type]}, {i.minutes} minutes, {logstore.INTENSITY_WORD[i.intensity].lower()}.",
            lines=[f"This week: {wk['week_activity_min']} of {wk['week_activity_goal']} active minutes, {wk['week_strength_sessions']} of {wk['week_strength_goal']} strength sessions."],
        )
    if isinstance(i, SymptomInput):
        saved = logstore.create_symptom(i)
        red = i.label in RED_FLAG_SYMPTOMS
        dur = f" for {i.duration_min} min" if i.duration_min else ""
        return LogResult(
            id=saved["id"], kind="symptom", title="Symptom saved", landed_in="Your day and your doctor brief", day=saved["day"], related="C2",
            detail=f"{i.label}, strength {i.severity} of 5{dur}.",
            lines=["Saved with the time and length you gave.", "This will appear in your doctor brief. You can see everything the doctor sees."],
            urgent=red, urgent_tier=2 if red else None,
        )
    assert isinstance(i, CheckinInput)
    saved = logstore.create_checkin(i)
    return LogResult(
        id=saved["id"], kind="checkin", title="Check-in saved", landed_in="Sleep and stress insights", day=saved["day"], related="C5",
        detail=f"Mood {i.mood}, stress {i.stress}, sleep quality {i.sleep}, energy {i.energy}.",
    )


@router.get("/recent", response_model=list[RecentEntry], response_model_by_alias=True)
async def list_recent() -> list[dict]:
    return await run_in_threadpool(logstore.recent)


@router.get("/today", response_model=LogProgress, response_model_by_alias=True)
async def today() -> dict:
    return await run_in_threadpool(logstore.progress)


@router.get("/context", response_model=LogContext, response_model_by_alias=True)
async def context() -> dict:
    return {"glucose": await run_in_threadpool(logstore.glucose_context)}


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(entry_id: str) -> None:
    try:
        found = await run_in_threadpool(logstore.delete_entry, entry_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not found:
        raise HTTPException(status_code=404, detail="Entry not found")
