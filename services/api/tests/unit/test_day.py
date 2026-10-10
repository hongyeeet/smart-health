"""Day view: the pure parts (time of day, the 5-minute series and its gaps, sleep bands, meal and dose wording, symptom glucose)."""
from datetime import date, datetime, timedelta, timezone

from app.services import day as D

SG = timezone(timedelta(hours=8))


def at(h: int, m: int = 0) -> datetime:
    return datetime(2026, 9, 30, h, m, tzinfo=SG)


def test_minute_of_uses_singapore_time_not_utc():
    utc = datetime(2026, 9, 30, 0, 5, tzinfo=timezone.utc)   # 08:05 in Singapore
    assert D.minute_of(utc) == 8 * 60 + 5
    assert D.clock(D.minute_of(utc)) == "08:05"


def test_series_is_288_slots_and_a_missing_slot_is_a_gap_not_a_zero():
    rows = [{"bucket_start": datetime(2026, 9, 30, 0, 5, tzinfo=timezone.utc), "glucose_mmol": 6.1, "heart_rate_bpm": 80, "steps": 0, "sleep_minutes": 0}]
    series = D.build_series(rows)
    assert len(series) == 288
    assert series[97]["glucose_mmol"] == 6.1                 # 08:05 is slot 97
    assert series[98]["glucose_mmol"] is None and series[98]["heart_rate_bpm"] is None and series[98]["steps"] is None


def test_sleep_bands_are_runs_of_asleep_slots_and_end_after_the_last_one():
    rows = [{"bucket_start": at(0, m), "glucose_mmol": None, "heart_rate_bpm": None, "steps": None, "sleep_minutes": 5 if m < 30 else 0} for m in range(0, 60, 5)]
    rows += [{"bucket_start": at(23, 50), "glucose_mmol": None, "heart_rate_bpm": None, "steps": None, "sleep_minutes": 5}]
    bands = D.sleep_bands(D.build_series(rows))
    assert bands == [{"start_minute": 0, "end_minute": 30}, {"start_minute": 1430, "end_minute": 1435}]


def test_sleep_band_running_to_midnight_is_kept():
    rows = [{"bucket_start": at(23, 55), "glucose_mmol": None, "heart_rate_bpm": None, "steps": None, "sleep_minutes": 5}]
    assert D.sleep_bands(D.build_series(rows)) == [{"start_minute": 1435, "end_minute": 1440}]


def test_kcal_needs_all_three_macros():
    assert D.kcal(66, 22, 42) == round(4 * 66 + 4 * 22 + 9 * 42)
    assert D.kcal(66, None, 42) is None
    assert D.kcal(None, 22, 42) is None


def test_meal_flags_only_when_recorded_and_over_the_placeholder_line():
    assert D.meal_flags(None, None) == []
    # the same limits Home, Food and Insights use (settings), so a meal is flagged the same everywhere
    salt, sugar = D.settings.meal_high_sodium_mg, D.settings.meal_high_sugar_g
    assert D.meal_flags(salt - 1, sugar - 1) == []
    assert D.meal_flags(salt, sugar) == ["salt", "sugar"]


def test_dose_state_late_is_more_than_an_hour_after_the_scheduled_time():
    s = at(8)
    assert D.dose_state("taken", s, s + timedelta(minutes=60)) == "taken"
    assert D.dose_state("taken", s, s + timedelta(minutes=61)) == "late"
    assert D.dose_state("pending", s, None) == "not_confirmed"
    assert D.dose_state("missed", s, None) == "missed"
    assert D.dose_state("skipped", s, None) == "missed"


def test_worst_dose_state_in_a_group():
    assert D.worst_dose_state(["taken", "late"]) == "late"
    assert D.worst_dose_state(["taken", "missed", "not_confirmed"]) == "missed"


def test_dose_outcome_counts_only():
    assert D.dose_outcome(["taken", "taken"]) == "2 doses at this time: 2 taken on time."
    assert D.dose_outcome(["taken", "missed"]) == "2 doses at this time: 1 taken on time; 1 missed."


def test_dose_row_says_how_late_and_why_missed():
    s = at(8)
    late = D.dose_row("Metformin 500 mg", "late", s, s + timedelta(minutes=95), None, "taken")
    assert late == {"label": "Metformin 500 mg", "value": "Taken at 09:35, 1 h 35 min late"}
    missed = D.dose_row("Fish oil", "missed", s, None, "away_from_home", "missed")
    assert missed["value"] == "Missed, reason: Away from home"
    skipped = D.dose_row("Fish oil", "missed", s, None, None, "skipped")
    assert skipped["value"] == "Skipped"


def test_meal_outcome_compares_with_own_median_for_the_same_kind():
    own = [1.0, 2.0, 3.0, 4.0, 5.0]                           # median 3.0
    assert D.meal_outcome(4.5, own, "lunch") == (
        "Two hours after this meal your glucose rose 4.5 mmol/L, more than your usual for lunch (median 3.0).")
    assert D.meal_outcome(1.0, own, "lunch") == (
        "Two hours after this meal your glucose rose 1.0 mmol/L, less than your usual for lunch (median 3.0).")
    assert D.meal_outcome(3.3, own, "lunch") == (
        "Two hours after this meal your glucose rose 3.3 mmol/L, about the same as your usual for lunch (median 3.0).")


def test_meal_outcome_with_fewer_than_five_own_meals_says_not_enough():
    text = D.meal_outcome(3.4, [1.0, 2.0, 3.0, 4.0], "lunch")
    assert "not enough meals of this kind yet to compare" in text
    assert "median" not in text


def test_meal_outcome_without_a_reading_says_so():
    assert "no glucose reading" in D.meal_outcome(None, [1.0] * 6, "dinner")


def test_workout_and_symptom_wording_never_invents_a_value():
    assert D.workout_outcome(None, None, None, None) == "No heart rate or glucose was recorded for this session."
    assert D.workout_outcome(8.0, 6.4, 112, 135) == (
        "Average heart rate 112 beats a minute, peak 135. Glucose went from 8.0 to a lowest of 6.4 mmol/L during the session.")
    assert D.symptom_outcome(None) == "There is no glucose reading close to this time."
    assert D.symptom_outcome(6.84) == "Your glucose was 6.8 mmol/L at about this time."


def test_glucose_near_a_symptom_uses_the_closest_reading_within_15_minutes():
    rows = [
        {"bucket_start": at(9, 0), "glucose_mmol": 5.0, "heart_rate_bpm": None, "steps": None, "sleep_minutes": 0},
        {"bucket_start": at(9, 10), "glucose_mmol": 6.0, "heart_rate_bpm": None, "steps": None, "sleep_minutes": 0},
        {"bucket_start": at(9, 30), "glucose_mmol": 9.0, "heart_rate_bpm": None, "steps": None, "sleep_minutes": 0},
    ]
    series = D.build_series(rows)
    assert D.glucose_near(series, 9 * 60 + 15) == 6.0      # 9:10 is 5 minutes away, 9:00 is 15
    assert D.glucose_near(series, 9 * 60 + 10) == 6.0
    assert D.glucose_near(series, 12 * 60) is None


def test_neighbours_are_the_closest_days_with_data_either_side():
    days = [date(2026, 9, 28), date(2026, 9, 30), date(2026, 10, 2)]
    assert D.neighbours(days, date(2026, 9, 30)) == ("2026-09-28", "2026-10-02")
    assert D.neighbours(days, date(2026, 10, 5)) == ("2026-10-02", None)
    assert D.neighbours([], date(2026, 9, 30)) == (None, None)


def test_has_data_is_false_for_an_empty_day_and_true_with_any_reading():
    empty = D.build_series([])
    assert D.has_data(empty, [], []) is False
    assert D.has_data(empty, [{"kind": "dose", "status": "not_confirmed"}], []) is False
    assert D.has_data(empty, [{"kind": "meal", "status": None}], []) is True
    assert D.has_data(D.build_series([{"bucket_start": at(9), "glucose_mmol": 5.0, "heart_rate_bpm": None, "steps": None, "sleep_minutes": 0}]), [], []) is True
