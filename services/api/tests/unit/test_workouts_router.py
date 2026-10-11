"""The save rules: the rating is optional once migration 0036 is applied and required before it (never a default), the beta-blocker
rule reads the person's live medicines, and the quick log saves a workout with or without a rating.

No database: the logstore calls are replaced with stubs, so these run anywhere. The deleted-medicine rule is in tests/db.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.routers import logs as L
from app.api.routers import workouts as W
from app.db import logstore
from app.schemas.log import WorkoutInput
from app.services.workout_effort import BETA_BLOCKER_NOTE

T0 = datetime(2026, 10, 2, 18, 0, tzinfo=timezone.utc)
AGE = 51.0  # max heart rate about 172, so 120 bpm is about 70%: moderate
STEADY = [(T0 + timedelta(seconds=60 * i), 120.0) for i in range(21)]
MEDS: dict[str, list[str]] = {"names": []}
NULLABLE: dict[str, bool] = {"yes": False}  # False: migration 0036 not applied, the rating is still required


def session(**over) -> W.SessionIn:
    d = dict(
        id="s1",
        startedAt=T0.isoformat(),
        endedAt=(T0 + timedelta(minutes=20)).isoformat(),
        exercises=[{"id": "e1", "name": "Squat", "sets": [{"id": "x1", "reps": 10, "weightKg": 40, "doneAt": (T0 + timedelta(minutes=5)).isoformat()}]}],
        intensity=4,
    )
    d.update(over)
    return W.SessionIn.model_validate(d)


@pytest.fixture()
def stub(monkeypatch):
    saved: dict = {}

    def create_workout(i, sets=None, note=None, payload=None):
        saved["intensity"] = i.intensity
        saved["sets"] = sets
        return {"id": "w1", "day": "2026-10-02", "end": T0}

    MEDS["names"] = []
    NULLABLE["yes"] = False
    monkeypatch.setattr(logstore, "create_workout", create_workout)
    monkeypatch.setattr(logstore, "heart_rate_and_age", lambda start, end: (STEADY, AGE))
    monkeypatch.setattr(logstore, "active_medicine_names", lambda: list(MEDS["names"]))
    monkeypatch.setattr(logstore, "rating_optional", lambda c=None: NULLABLE["yes"])
    return saved


def test_the_model_takes_no_rating_and_never_fills_one_in():
    bare = {"id": "s1", "startedAt": T0.isoformat(), "exercises": []}
    assert W.SessionIn.model_validate(bare).intensity is None
    assert W.SessionIn.model_validate({**bare, "intensity": None}).intensity is None
    with pytest.raises(ValidationError):
        W.SessionIn.model_validate({**bare, "intensity": 0})
    with pytest.raises(ValidationError):
        W.SessionIn.model_validate({**bare, "intensity": 6})


def test_the_rating_given_is_the_rating_stored(stub):
    W._save(session(intensity=2))
    assert stub["intensity"] == 2


def test_before_migration_0036_a_session_without_a_rating_is_refused_and_nothing_is_written(stub):
    with pytest.raises(HTTPException) as err:
        W._save(session(intensity=None))
    assert err.value.status_code == 422
    assert err.value.detail == "Pick a number from 1 to 5 to save this workout."
    assert stub == {}  # create_workout was never called


def test_after_migration_0036_a_session_without_a_rating_is_saved_as_not_rated(stub):
    NULLABLE["yes"] = True
    out = W._save(session(intensity=None))
    assert stub["intensity"] is None
    assert out.effort.quality == "ok" and out.effort.intensity == "moderate"  # effort still computed from the heart rate


def test_five_minute_watch_data_with_full_coverage_gives_a_label(stub, monkeypatch):
    five_min = [(T0 + timedelta(minutes=5 * i), 120.0) for i in range(5)]  # the real watch cadence
    monkeypatch.setattr(logstore, "heart_rate_and_age", lambda start, end: (five_min, AGE))
    out = W._save(session())
    assert out.effort.quality == "ok" and out.effort.intensity == "moderate"


def test_quick_log_workout_without_a_rating_before_migration_0036_is_refused(monkeypatch):
    monkeypatch.setattr(logstore, "rating_optional", lambda c=None: False)
    with pytest.raises(HTTPException) as err:
        L._create(WorkoutInput(type="walking", intensity=None, start_at=T0, minutes=30))
    assert err.value.status_code == 422 and err.value.detail == "Pick a number from 1 to 5 to save this workout."


def test_quick_log_workout_without_a_rating_after_migration_0036_is_saved_untouched(monkeypatch):
    seen = {}

    def create_workout(i, sets=None, note=None, payload=None):
        seen["intensity"], seen["feeling"] = i.intensity, i.feeling
        return {"id": "w2", "day": "2026-10-02", "end": T0}

    monkeypatch.setattr(logstore, "rating_optional", lambda c=None: True)
    monkeypatch.setattr(logstore, "create_workout", create_workout)
    monkeypatch.setattr(logstore, "progress", lambda: {"week_activity_min": 0, "week_activity_goal": 150, "week_strength_sessions": 0, "week_strength_goal": 2})
    res = L._create(WorkoutInput(type="walking", intensity=None, feeling=None, start_at=T0, minutes=30))
    assert seen == {"intensity": None, "feeling": None}  # no 3, no 4: neither a rating nor a feeling is filled in
    assert res.detail == "Walk, 30 minutes."


def test_beta_blocker_keeps_heart_rate_numbers_and_drops_the_label(stub):
    MEDS["names"] = ["Metoprolol 50 mg", "Amlodipine 5 mg"]
    out = W._save(session())
    assert out.effort.beta_blocker is True
    assert out.effort.intensity is None
    assert out.effort.avg_hr == 120 and out.effort.max_hr == 120
    assert out.effort.note == BETA_BLOCKER_NOTE
    assert out.exercises[0].avg_hr == 120


def test_without_a_beta_blocker_the_estimate_label_is_given(stub):
    MEDS["names"] = ["Amlodipine 5 mg", "Atorvastatin 20 mg"]
    out = W._save(session())
    assert out.effort.beta_blocker is False
    assert out.effort.quality == "ok" and out.effort.intensity == "moderate"


def test_too_few_heart_rate_samples_keep_no_label(stub, monkeypatch):
    two = [(T0, 120.0), (T0 + timedelta(minutes=5), 120.0)]  # fewer than 3 samples: the 1-minute fallback expects 20
    monkeypatch.setattr(logstore, "heart_rate_and_age", lambda start, end: (two, AGE))
    out = W._save(session())
    assert out.effort.quality == "insufficient" and out.effort.intensity is None
    assert out.effort.beta_blocker is False


def test_no_watch_heart_rate_says_so_and_gives_no_label(stub, monkeypatch):
    monkeypatch.setattr(logstore, "heart_rate_and_age", lambda start, end: ([], AGE))
    out = W._save(session())
    assert out.effort.intensity is None and out.effort.avg_hr is None
    assert out.effort.note == "No watch heart rate for this session, so effort is not shown."
