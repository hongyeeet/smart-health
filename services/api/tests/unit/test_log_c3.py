"""Log fixes (C3): a check-in may leave questions unanswered, a typed kcal is kept and preferred, a workout with no rating says so,
a typed meal is "your numbers" and never "estimated", and the lunch reminder has one stable slot a day.

No database: the logstore calls are replaced with stubs, so these run anywhere.
"""
from datetime import date, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.api.routers import logs as L
from app.db import logstore
from app.db.logstore import TZ
from app.schemas.log import CheckinInput, MealInput, WorkoutInput
from app.services import diet_days as DD

T0 = datetime(2026, 10, 11, 12, 0, tzinfo=TZ)


@pytest.fixture()
def stubs(monkeypatch):
    saved: dict = {}

    def create_checkin(i):
        saved["checkin"] = i.model_dump(mode="json", by_alias=True)
        return {"id": "c1", "day": "2026-10-11"}

    def create_meal(i):
        saved["meal"] = i
        return {"id": "m1", "day": "2026-10-11", "meal_type": "lunch"}

    def create_workout(i, sets=None, note=None, payload=None):
        saved["workout"] = i
        return {"id": "w1", "day": "2026-10-11"}

    monkeypatch.setattr(logstore, "create_checkin", create_checkin)
    monkeypatch.setattr(logstore, "create_meal", create_meal)
    monkeypatch.setattr(logstore, "create_workout", create_workout)
    monkeypatch.setattr(logstore, "progress", lambda: {"week_activity_min": 40, "week_activity_goal": 150, "week_strength_sessions": 0, "week_strength_goal": 2})
    monkeypatch.setattr(logstore, "rating_optional", lambda c=None: True)
    return saved


# ---------------------------------------------------------------- 1. mood and sleep: no default answers
def test_a_check_in_with_one_answer_is_valid_and_the_others_stay_unanswered():
    i = CheckinInput.model_validate({"mood": 4})
    assert (i.mood, i.stress, i.sleep, i.energy) == (4, None, None, None)


def test_a_check_in_with_no_answer_is_refused():
    with pytest.raises(ValidationError):
        CheckinInput.model_validate({})
    with pytest.raises(ValidationError):
        CheckinInput.model_validate({"mood": None, "stress": None, "sleep": None, "energy": None})


def test_a_partial_check_in_saves_null_for_the_unanswered_and_names_only_the_answers(stubs):
    out = L._create(CheckinInput.model_validate({"stress": 4}))
    assert stubs["checkin"]["stress"] == 4 and stubs["checkin"]["mood"] is None and stubs["checkin"]["energy"] is None
    assert out.detail == "Stress 4."


def test_a_full_check_in_still_names_all_four(stubs):
    out = L._create(CheckinInput.model_validate({"mood": 3, "stress": 4, "sleep": 2, "energy": 3}))
    assert out.detail == "Mood 3, stress 4, sleep quality 2, energy 3."


# ---------------------------------------------------------------- 3. typed kcal is kept and preferred
def meal(**over) -> dict:
    d = {"id": "f1", "local_day": date(2026, 10, 11), "start_at": datetime(2026, 10, 11, 13, 30, tzinfo=TZ), "meal_type": "lunch",
         "food": "Chicken rice", "carbs_g": None, "protein_g": None, "fat_g": None, "sugar_g": None, "fibre_g": None, "sodium_mg": None,
         "estimated_by": "user", "typed_kcal": None, "pre_glucose_mmol": None, "peak_glucose_mmol": None, "minutes_to_peak": None, "rise_mmol": None}
    d.update(over)
    return d


def test_a_typed_kcal_is_used_when_the_macros_are_incomplete():
    # 500 kcal typed, fat left blank: the 4, 4, 9 rule cannot run, so the typed value is the number
    d = DD.meal_detail(meal(carbs_g=50, protein_g=20, fat_g=None, typed_kcal="500.0"))
    assert d["kcal"] == 500
    assert d["numbers_from"] == "you"


def test_a_typed_kcal_wins_over_the_rule_when_the_macros_are_complete():
    d = DD.meal_detail(meal(carbs_g=60, protein_g=20, fat_g=15, typed_kcal="600"))
    assert d["kcal"] == 600


def test_without_a_typed_kcal_the_rule_still_runs_and_a_blank_stays_unknown():
    assert DD.meal_detail(meal(carbs_g=60, protein_g=20, fat_g=15))["kcal"] == 455
    d = DD.meal_detail(meal(carbs_g=60, protein_g=20, fat_g=None))
    assert d["kcal"] is None and d["numbers_from"] == "you"


def test_a_photo_meal_ignores_a_kcal_in_a_bronze_row_that_is_not_the_person_own():
    d = DD.meal_detail(meal(estimated_by="llm_photo", carbs_g=60, protein_g=20, fat_g=15, typed_kcal="999"))
    assert d["kcal"] == 455 and d["numbers_from"] == "estimate"


def test_a_day_total_uses_the_typed_kcal_and_the_rule_for_the_rest():
    rows = [
        meal(id="a", carbs_g=60, protein_g=20, fat_g=15, estimated_by="llm_photo"),          # 455 by the rule
        meal(id="b", carbs_g=50, protein_g=20, fat_g=None, typed_kcal="500.0"),               # 500 typed
    ]
    day = DD.summarise_days(rows, date(2026, 10, 11), date(2026, 10, 11))[0]
    assert day["totals"]["kcal"] == 955
    assert [m["numbers_from"] for m in day["meal_list"]] == ["estimate", "you"]
    assert day["meal_list"][1]["kcal"] == 500


def test_the_meal_row_keeps_the_typed_kcal_in_the_bronze_payload(stubs):
    m = MealInput.model_validate({"name": "Chicken rice", "startAt": T0.isoformat(), "endAt": (T0 + timedelta(minutes=20)).isoformat(),
                                  "kcal": 500, "carbsG": 50, "proteinG": 20, "edited": True, "valuesFrom": "user"})
    out = L._create(m)
    assert stubs["meal"].kcal == 500
    assert out.lines[1] == "These are your own numbers."


# ---------------------------------------------------------------- 3. typed meals are "your numbers", never "estimated"
def test_a_typed_meal_is_never_called_an_estimate(stubs):
    m = MealInput.model_validate({"name": "Hawker plate", "startAt": T0.isoformat(), "endAt": (T0 + timedelta(minutes=20)).isoformat(),
                                  "carbsG": 80, "sodiumMg": 5000, "valuesFrom": "user", "edited": True})
    out = L._create(m)
    text = " ".join([out.detail, *out.lines, out.flag.text if out.flag else ""]).lower()
    assert "estimate" not in text
    assert out.flag is not None and out.flag.text == "High salt in your numbers for this meal."
    assert out.swap is not None and out.swap.text.startswith("Another idea: ")


def test_a_photo_meal_still_says_estimates(stubs):
    m = MealInput.model_validate({"name": "Chicken rice", "startAt": T0.isoformat(), "endAt": (T0 + timedelta(minutes=20)).isoformat(),
                                  "carbsG": 80, "analysisId": "7b1f0c9e-1d2a-4b3c-8d4e-5f6a7b8c9d0e"})
    out = L._create(m)
    assert out.lines[1] == "Nutrients are estimates until you confirm them."


# ---------------------------------------------------------------- 4. unrated workouts say so
def workout(**over) -> dict:
    d = {"type": "walking", "activity": "Brisk walk", "startAt": T0.isoformat(), "minutes": 30}
    d.update(over)
    return d


def test_an_unrated_workout_says_it_is_not_counted_on_the_saved_screen(stubs):
    out = L._create(WorkoutInput.model_validate(workout(intensity=None)))
    assert L.UNRATED_NOTE in out.lines
    assert out.lines[-1] == "No effort rating was given, so this workout is not counted toward your active minutes."


def test_a_rated_workout_has_no_such_line(stubs):
    out = L._create(WorkoutInput.model_validate(workout(intensity=3)))
    assert L.UNRATED_NOTE not in out.lines


# ---------------------------------------------------------------- 7. the lunch reminder: one slot, a stable time
def test_the_lunch_slot_is_one_key_for_both_writers():
    from app.db.logstore import lunch_slot_keys

    assert lunch_slot_keys("2026-10-11") == {"meal-2-2026-10-11", "lunch-2026-10-11"}


def test_the_lunch_reminder_time_is_the_start_of_its_window_whenever_it_is_written():
    from app.db.logstore import reminder_time

    day = date(2026, 10, 11)
    at_1130 = reminder_time("meal-2-2026-10-11", day, 11 * 60 + 30)
    assert at_1130 == datetime(2026, 10, 11, 11, 30, tzinfo=TZ)
    assert reminder_time("lunch-2026-10-11", day, 11 * 60 + 30) == at_1130
    assert reminder_time("meal-1-2026-10-11", day, 0) == datetime(2026, 10, 11, 7, 0, tzinfo=TZ)
    assert reminder_time("checkin-2026-10-11", day, 0) == datetime(2026, 10, 11, 6, 0, tzinfo=TZ)


def test_reminders_without_a_fixed_time_are_not_given_one():
    from app.db.logstore import reminder_time

    assert reminder_time("dose-abc-2026-10-11", date(2026, 10, 11), 0) is None
    assert reminder_time("activity-2026-10-11", date(2026, 10, 11), 0) is None
