"""POST /workouts (save a live strength session), GET /workouts/week (this week's progress and recent sessions).

The session is stored as a `bronze_exercise` row, then `exercise_logs` with its `exercise_sets`, then the Gold timeline.
Every number in the summary is computed here in code (rules.md 1); the model writes no numbers.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import Field

from app.db import logstore
from app.schemas.log import Camel, WorkoutInput
from app.services.workout_effort import ExerciseEntry, Sample, SetEntry, effort_between, exercise_efforts, exercise_volume_kg, session_volume_kg, takes_beta_blocker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workouts", tags=["workouts"])


class SetIn(Camel):
    id: str
    reps: int = Field(ge=1, le=200)
    weight_kg: float | None = Field(None, ge=0)
    done_at: datetime


class ExerciseIn(Camel):
    id: str
    name: str = Field(min_length=1, max_length=80)
    sets: list[SetIn]


class SessionIn(Camel):
    id: str
    started_at: datetime
    ended_at: datetime | None = None
    exercises: list[ExerciseIn]
    felt: str | None = None
    note: str | None = None
    # how hard it felt, 1 (very light) to 5 (all-out). Optional: null is "not rated" and nothing is filled in. Until
    # migration 0036 is applied, exercise_logs.intensity is NOT NULL and _save refuses a session with no rating.
    intensity: int | None = Field(None, ge=1, le=5)


class ExerciseOut(Camel):
    name: str
    sets: int
    volume_kg: float
    avg_hr: float | None


class EffortOut(Camel):
    avg_hr: float | None
    max_hr: float | None
    intensity: str | None
    minutes_in_band: dict[str, float]
    quality: str
    note: str | None = None
    # True when the person takes a beta-blocker: heart-rate numbers are shown, no effort label is
    beta_blocker: bool = False


class SummaryOut(Camel):
    id: str
    duration_s: int
    sets_n: int
    volume_kg: float
    exercises: list[ExerciseOut]
    effort: EffortOut
    glucose_change2h: float | None = Field(None, alias="glucoseChange2h")
    narrative: str | None = None


def _save(s: SessionIn) -> SummaryOut:
    if s.intensity is None and not logstore.rating_optional():
        raise HTTPException(status_code=422, detail=logstore.RATING_REQUIRED)
    end = s.ended_at or datetime.now(timezone.utc)
    secs = max(60, int((end - s.started_at).total_seconds()))
    minutes = max(1, round(secs / 60))
    entries = [
        ExerciseEntry(e.name, [SetEntry(x.reps, x.weight_kg, x.done_at) for x in e.sets]) for e in s.exercises if e.sets
    ]
    sets_rows, order = [], 0
    for e in s.exercises:
        if not e.sets:
            continue
        order += 1
        for n, x in enumerate(e.sets, start=1):
            sets_rows.append({"exercise": e.name, "exercise_order": order, "set_no": n, "reps": x.reps, "weight_kg": x.weight_kg, "performed_at": x.done_at})
    felt = logstore.FELT_TO_FEELING.get(s.felt or "")
    wi = WorkoutInput(type="strength", activity="Strength session", intensity=s.intensity, start_at=s.started_at, minutes=minutes, feeling=felt)
    logstore.create_workout(wi, sets=sets_rows, note=(s.note or "Strength session"), payload=s.model_dump(mode="json", by_alias=True))

    samples, age = logstore.heart_rate_and_age(s.started_at, end)
    beta = takes_beta_blocker(logstore.active_medicine_names())
    if samples and age:
        sm = [Sample(a, b) for a, b in samples]
        overall = effort_between(sm, s.started_at, end, age, beta_blocker=beta)
        per = exercise_efforts(entries, sm, age, beta_blocker=beta)
    else:
        overall, per = None, {}
    return SummaryOut(
        id=s.id, duration_s=secs, sets_n=sum(len(e.sets) for e in entries), volume_kg=session_volume_kg(entries),
        exercises=[
            ExerciseOut(name=e.name, sets=len(e.sets), volume_kg=exercise_volume_kg(e.sets), avg_hr=(per[e.name].avg_hr if e.name in per else None))
            for e in entries
        ],
        effort=EffortOut(
            avg_hr=overall.avg_hr if overall else None, max_hr=overall.max_hr if overall else None, intensity=overall.intensity if overall else None,
            minutes_in_band=overall.minutes_in_band if overall else {}, quality=overall.quality if overall else "insufficient",
            note=(overall.note if overall else "No watch heart rate for this session, so effort is not shown."), beta_blocker=beta,
        ),
    )


@router.post("", response_model=SummaryOut, response_model_by_alias=True)
async def save_session(session: SessionIn) -> SummaryOut:
    return await run_in_threadpool(_save, session)


@router.get("/week")
async def week() -> dict:
    return await run_in_threadpool(logstore.week_workouts)
