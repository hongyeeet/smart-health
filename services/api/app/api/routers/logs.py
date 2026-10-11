"""POST /logs, GET /logs/recent, DELETE /logs/{id}, GET /logs/today, GET /logs/context,
GET and PUT /logs/blood-pressure/{id} (read one reading, edit it).

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
    BloodPressureEntry, BloodPressureInput, CheckinInput, LogContext, LogFlag, LogInput, LogProgress, LogResult, LogSwap, MealInput,
    RecentEntry, SymptomInput, WorkoutInput,
)
from app.services import diet_days

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/logs", tags=["logs"])

RED_FLAG_SYMPTOMS = {
    "Chest pain", "Confusion", "Fainting", "Breathlessness at rest", "Sudden vision loss or a curtain across my vision",
}


BP_DUPLICATE = "You already have a reading saved at that time. Change the time, or edit the reading that is there."
# one plain line on the Saved screen when a workout has no effort rating (the counting rule is unchanged: such a workout adds 0 active minutes)
UNRATED_NOTE = "No effort rating was given, so this workout is not counted toward your active minutes."


def _clock(dt) -> str:
    return dt.astimezone(logstore.TZ).strftime("%I:%M %p").lstrip("0").lower()


def _bp_result(i: BloodPressureInput, saved: dict) -> LogResult:
    pulse = f", pulse {i.pulse}" if i.pulse is not None else ""
    return LogResult(
        id=saved["id"], kind="blood_pressure", title="Blood pressure saved", landed_in="Sleep and stress insights and your doctor brief",
        day=saved["day"], related="C5", detail=f"{i.systolic} over {i.diastolic} mmHg{pulse}.",
        lines=[f"Taken at {_clock(saved['measured_at'])}.", "It will appear in your doctor brief."],
    )


@router.post("", response_model=LogResult, response_model_by_alias=True)
async def create_log(input: LogInput) -> LogResult:
    return await run_in_threadpool(_create, input)


def _create(i) -> LogResult:
    if isinstance(i, BloodPressureInput):
        try:
            saved = logstore.create_blood_pressure(i)
        except logstore.DuplicateReading:
            raise HTTPException(status_code=409, detail=BP_DUPLICATE)
        return _bp_result(i, saved)
    if isinstance(i, MealInput):
        saved = logstore.create_meal(i)
        carbs = f", about {round(i.carbs_g)} g carbs" if i.carbs_g is not None else ""
        flags = flags_for(i.carbs_g, i.sugar_g, i.sodium_mg)
        salty = "high_salt" in flags
        # a meal typed in by hand (no photo) is the person's own numbers, never called an estimate
        typed = i.analysis_id is None
        if typed:
            numbers_line = "These are your own numbers."
        else:
            numbers_line = "Nutrients are estimates" + (" until you confirm them." if not i.edited else ", with your changes.")
        basis = "in your numbers" if typed else "estimated"
        return LogResult(
            id=saved["id"], kind="meal", title="Meal saved", landed_in="Your day", day=saved["day"], related="C3",
            detail=f"{i.name}{carbs}.",
            lines=[
                f"Eaten {_clock(i.start_at)} to {_clock(i.end_at)}.",
                numbers_line,
                "Your glucose rise will come from the sensor in about 2 hours.",
            ],
            flag=LogFlag(text=f"High salt {basis} for this meal.", level="info") if salty else (LogFlag(text=f"High sugar {basis} for this meal.", level="info") if "high_sugar" in flags else None),
            swap=LogSwap(text="Another idea: Ask for the soup or gravy on the side next time.", source="Team-written tip, not medical advice") if salty else None,
        )
    if isinstance(i, WorkoutInput):
        if i.intensity is None and not logstore.rating_optional():
            raise HTTPException(status_code=422, detail=logstore.RATING_REQUIRED)
        saved = logstore.create_workout(i)
        wk = logstore.progress()
        rated = f", {logstore.INTENSITY_WORD[i.intensity].lower()}" if i.intensity is not None else ""
        lines = [f"This week: {wk['week_activity_min']} of {wk['week_activity_goal']} active minutes, {wk['week_strength_sessions']} of {wk['week_strength_goal']} strength sessions."]
        if i.intensity is None:
            lines.append(UNRATED_NOTE)
        return LogResult(
            id=saved["id"], kind="workout", title="Added to your day", landed_in="Your day and Activity insights", day=saved["day"], related="C4",
            detail=f"{i.activity or logstore.EXERCISE_WORD[i.type]}, {i.minutes} minutes{rated}.",
            lines=lines,
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
    # only the answers the person gave are named
    text = ", ".join(f"{label} {v}" for label, v in (("Mood", i.mood), ("stress", i.stress), ("sleep quality", i.sleep), ("energy", i.energy)) if v is not None)
    return LogResult(
        id=saved["id"], kind="checkin", title="Check-in saved", landed_in="Sleep and stress insights", day=saved["day"], related="C5",
        detail=text[:1].upper() + text[1:] + ".",
    )


@router.get("/recent", response_model=list[RecentEntry], response_model_by_alias=True)
async def list_recent() -> list[dict]:
    return await run_in_threadpool(_recent)


def _recent() -> list[dict]:
    """The newest entries of every kind. A meal also carries its macros and sensor response (`meal`), so one request fills the list."""
    entries = logstore.recent()
    details = diet_days.meal_details([e["id"] for e in entries if e["kind"] == "meal"])
    for e in entries:
        e["meal"] = details.get(e["id"]) if e["kind"] == "meal" else None
    return entries


@router.get("/today", response_model=LogProgress, response_model_by_alias=True)
async def today() -> dict:
    return await run_in_threadpool(logstore.progress)


@router.get("/context", response_model=LogContext, response_model_by_alias=True)
async def context() -> dict:
    return {"glucose": await run_in_threadpool(logstore.glucose_context)}


@router.get("/blood-pressure/{entry_id}", response_model=BloodPressureEntry, response_model_by_alias=True)
async def get_blood_pressure(entry_id: str) -> dict:
    found = await run_in_threadpool(logstore.get_blood_pressure, entry_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return found


@router.put("/blood-pressure/{entry_id}", response_model=LogResult, response_model_by_alias=True)
async def update_blood_pressure(entry_id: str, input: BloodPressureInput) -> LogResult:
    return await run_in_threadpool(_update_bp, entry_id, input)


def _update_bp(entry_id: str, i: BloodPressureInput) -> LogResult:
    try:
        saved = logstore.update_blood_pressure(entry_id, i)
    except logstore.DuplicateReading:
        raise HTTPException(status_code=409, detail=BP_DUPLICATE)
    except ValueError:
        saved = None
    if saved is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return _bp_result(i, saved)


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(entry_id: str) -> None:
    try:
        found = await run_in_threadpool(logstore.delete_entry, entry_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not found:
        raise HTTPException(status_code=404, detail="Entry not found")
