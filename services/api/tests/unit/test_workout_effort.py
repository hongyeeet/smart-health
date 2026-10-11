from datetime import datetime, timedelta, timezone

from app.services.workout_effort import (
    BETA_BLOCKER_NOTE,
    ExerciseEntry,
    SetEntry,
    Sample,
    band_for_percent,
    effort_between,
    exercise_efforts,
    exercise_volume_kg,
    max_heart_rate,
    sampling_interval_s,
    session_volume_kg,
    takes_beta_blocker,
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


def test_one_minute_data_with_full_coverage_shows_the_label():
    e = effort_between(steady(120, 20), T0, T0 + timedelta(minutes=20), AGE)
    assert e.quality == "ok" and e.intensity == "moderate"
    assert sum(e.minutes_in_band.values()) == 21  # 21 samples from minute 0 to minute 20, one minute each


def test_five_minute_data_with_full_coverage_shows_the_label():
    five_min = steady(120, 20, every_s=300)  # watch readings are 5-minute buckets: 5 samples over 20 minutes
    e = effort_between(five_min, T0, T0 + timedelta(minutes=20), AGE)
    assert e.quality == "ok" and e.intensity == "moderate" and e.note is None
    assert sum(e.minutes_in_band.values()) == 25  # each 5-minute sample counts as 5 minutes, not 1


def test_five_minute_data_with_a_gap_is_insufficient():
    gap = [Sample(T0 + timedelta(minutes=m), 120.0) for m in (0, 5, 10)]  # 30-minute window, the last 20 minutes missing
    e = effort_between(gap, T0, T0 + timedelta(minutes=30), AGE)
    assert e.quality == "insufficient" and e.intensity is None and e.avg_hr == 120


def test_sampling_interval_is_measured_and_bounded():
    assert sampling_interval_s(steady(120, 20, every_s=300)) == 300
    assert sampling_interval_s(steady(120, 10, every_s=30)) == 60  # faster than a minute is kept at 60 seconds
    assert sampling_interval_s([Sample(T0 + timedelta(minutes=15 * i), 120.0) for i in range(4)]) == 600  # slower is kept at 600


def test_too_few_samples_fall_back_to_one_minute():
    two = [Sample(T0, 120.0), Sample(T0 + timedelta(minutes=5), 120.0)]
    assert sampling_interval_s(two) == 60
    e = effort_between(two, T0, T0 + timedelta(minutes=20), AGE)  # 20 expected at one minute, 2 found
    assert e.quality == "insufficient" and e.intensity is None


def test_beta_blocker_blocks_the_intensity_label():
    e = effort_between(steady(120, 20), T0, T0 + timedelta(minutes=20), AGE, beta_blocker=True)
    assert e.intensity is None and e.quality == "insufficient" and "reliable" in (e.note or "")


def test_beta_blocker_still_shows_heart_rate_numbers():
    e = effort_between(steady(120, 20), T0, T0 + timedelta(minutes=20), AGE, beta_blocker=True)
    assert e.avg_hr == 120 and e.max_hr == 120 and e.intensity is None
    assert e.note == BETA_BLOCKER_NOTE
    per = exercise_efforts([ExerciseEntry("Squat", [SetEntry(10, 40.0, T0 + timedelta(minutes=5))])], steady(120, 20), AGE, beta_blocker=True)
    assert per["Squat"].avg_hr == 120 and per["Squat"].intensity is None


def test_beta_blocker_names_match_whole_words_in_any_case():
    assert takes_beta_blocker(["Metoprolol 50 mg"])
    assert takes_beta_blocker(["Bisoprolol fumarate 5 mg"])
    assert takes_beta_blocker(["NEBIVOLOL"])
    assert takes_beta_blocker(["Amlodipine 5 mg", "Propranolol 40 mg"])
    assert takes_beta_blocker(["Carvedilol, Metformin"])


def test_medicines_that_are_not_beta_blockers_do_not_trigger_the_rule():
    assert not takes_beta_blocker([])
    assert not takes_beta_blocker(["Amlodipine 5 mg", "Atorvastatin 20 mg", "Fish oil", "Herbal tonic (label not readable)", ""])
    assert not takes_beta_blocker(["Metoprololol 25 mg"])  # not a whole-word match


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
