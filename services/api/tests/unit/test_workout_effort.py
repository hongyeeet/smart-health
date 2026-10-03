from datetime import datetime, timedelta, timezone

from app.services.workout_effort import (
    ExerciseEntry,
    SetEntry,
    Sample,
    band_for_percent,
    effort_between,
    exercise_efforts,
    exercise_volume_kg,
    max_heart_rate,
    session_volume_kg,
)

T0 = datetime(2026, 10, 2, 18, 0, tzinfo=timezone.utc)
AGE = 51  # max heart rate about 172


def steady(bpm: float, minutes: int, every_s: int = 60) -> list[Sample]:
    return [Sample(T0 + timedelta(seconds=i * every_s), bpm) for i in range(0, minutes * 60 // every_s + 1)]


def test_max_heart_rate_is_an_estimate_from_age():
    assert round(max_heart_rate(51), 1) == 172.3


def test_band_edges():
    assert band_for_percent(40) == "rest_or_very_light"
    assert band_for_percent(57) == "light"
    assert band_for_percent(64) == "moderate"
    assert band_for_percent(77) == "vigorous"
    assert band_for_percent(96) == "near_maximal"


def test_light_moderate_and_vigorous_sessions():
    end = T0 + timedelta(minutes=20)
    assert effort_between(steady(100, 20), T0, end, AGE).intensity == "light"      # 58%
    assert effort_between(steady(120, 20), T0, end, AGE).intensity == "moderate"   # 70%
    assert effort_between(steady(150, 20), T0, end, AGE).intensity == "vigorous"   # 87%


def test_no_heart_rate_means_unknown_not_zero():
    e = effort_between([], T0, T0 + timedelta(minutes=20), AGE)
    assert e.avg_hr is None and e.intensity is None and e.quality == "insufficient"


def test_sparse_heart_rate_is_insufficient():
    sparse = steady(120, 20, every_s=300)  # one sample every 5 minutes: about 20% coverage
    e = effort_between(sparse, T0, T0 + timedelta(minutes=20), AGE)
    assert e.quality == "insufficient" and e.intensity is None and e.avg_hr is not None


def test_beta_blocker_blocks_the_intensity_label():
    e = effort_between(steady(120, 20), T0, T0 + timedelta(minutes=20), AGE, beta_blocker=True)
    assert e.intensity is None and e.quality == "insufficient" and "reliable" in (e.note or "")


def test_empty_window_is_insufficient():
    e = effort_between(steady(120, 20), T0, T0, AGE)
    assert e.quality == "insufficient"


def test_volume_counts_weighted_sets_only():
    sets = [SetEntry(10, 40.0), SetEntry(8, 45.0), SetEntry(12, None)]
    assert exercise_volume_kg(sets) == 10 * 40.0 + 8 * 45.0
    assert session_volume_kg([ExerciseEntry("Squat", sets), ExerciseEntry("Row", [SetEntry(10, 30.0)])]) == 1060.0


def test_per_exercise_effort_uses_each_exercises_own_time():
    low = steady(100, 5)
    high = [Sample(T0 + timedelta(minutes=10, seconds=i * 60), 150) for i in range(0, 6)]
    squat = ExerciseEntry("Squat", [SetEntry(10, 40.0, T0 + timedelta(minutes=2))])
    deadlift = ExerciseEntry("Deadlift", [SetEntry(5, 80.0, T0 + timedelta(minutes=12))])
    out = exercise_efforts([squat, deadlift], low + high, AGE)
    assert out["Squat"].avg_hr == 100 and out["Deadlift"].avg_hr == 150
    assert exercise_efforts([ExerciseEntry("Plank", [SetEntry(1, None)])], low, AGE)["Plank"].quality == "insufficient"
