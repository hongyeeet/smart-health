"""K10 Diet tracking calendar: the day totals (pure), including a day with unknown values, a day with no meals and a user with no data."""
from datetime import date, datetime

import pytest

from app.db.logstore import TZ
from app.services import diet_days as DD

D1, D2, D3 = date(2026, 10, 9), date(2026, 10, 10), date(2026, 10, 11)


def meal(day: date, hour: int, *, carbs=60, protein=20, fat=15, sugar=3, fibre=4, sodium=900, name="Chicken rice", mid="m1") -> dict:
    return {"id": mid, "local_day": day, "start_at": datetime(day.year, day.month, day.day, hour, 30, tzinfo=TZ), "meal_type": "lunch", "food": name,
            "carbs_g": carbs, "protein_g": protein, "fat_g": fat, "sugar_g": sugar, "fibre_g": fibre, "sodium_mg": sodium}


def by_date(days: list[dict]) -> dict[str, dict]:
    return {d["date"]: d for d in days}


def test_totals_add_up_when_every_meal_has_every_value():
    rows = [meal(D2, 8, mid="a"), meal(D2, 13, carbs=40, protein=30, fat=10, sugar=5, fibre=6, sodium=500, mid="b")]
    d = by_date(DD.summarise_days(rows, D2, D2))[D2.isoformat()]
    assert d["meals"] == 2
    assert d["totals"]["carbs_g"] == 100.0
    assert d["totals"]["protein_g"] == 50.0
    assert d["totals"]["fat_g"] == 25.0
    assert d["totals"]["sugar_g"] == 8.0
    assert d["totals"]["fibre_g"] == 10.0
    assert d["totals"]["sodium_mg"] == 1400.0
    # 4 x 100 + 4 x 50 + 9 x 25 = 825 kcal, the same rule the Day view uses
    assert d["totals"]["kcal"] == 825


def test_a_day_with_an_unknown_value_keeps_the_known_totals_and_marks_the_unknown_one_unknown():
    rows = [meal(D2, 8, mid="a"), meal(D2, 13, protein=None, mid="b")]
    d = by_date(DD.summarise_days(rows, D2, D2))[D2.isoformat()]
    assert d["meals"] == 2
    assert d["totals"]["protein_g"] is None          # one meal does not know its protein, so the day's protein is unknown
    assert d["totals"]["kcal"] is None               # energy needs all three macros, so it is unknown too
    assert d["totals"]["carbs_g"] == 120.0           # every meal knows its carbohydrate
    assert d["totals"]["sodium_mg"] == 1800.0
    assert d["meal_list"][1]["protein_g"] is None and d["meal_list"][1]["kcal"] is None
    assert d["meal_list"][0]["kcal"] == 455


def test_a_day_with_no_meals_is_kept_with_empty_totals_not_zero():
    rows = [meal(D2, 8)]
    days = DD.summarise_days(rows, D1, D3)
    assert [x["date"] for x in days] == [D1.isoformat(), D2.isoformat(), D3.isoformat()]
    empty = by_date(days)[D1.isoformat()]
    assert empty["meals"] == 0 and empty["meal_list"] == []
    assert all(v is None for v in empty["totals"].values())


def test_a_user_with_no_data_gets_every_day_empty():
    days = DD.summarise_days([], D1, D3)
    assert len(days) == 3
    assert all(d["meals"] == 0 and d["meal_list"] == [] and all(v is None for v in d["totals"].values()) for d in days)


def test_meals_are_grouped_by_singapore_day_and_listed_in_time_order():
    late = meal(D2, 20, mid="late", name="Supper")
    early = meal(D2, 7, mid="early", name="Porridge")
    d = by_date(DD.summarise_days([late, early], D2, D2))[D2.isoformat()]
    assert [m["name"] for m in d["meal_list"]] == ["Porridge", "Supper"]
    assert d["meal_list"][0]["when"] == "7:30 am"
    assert d["meal_list"][1]["when"] == "8:30 pm"


def test_the_range_is_inclusive_and_empty_days_are_not_dropped():
    days = DD.summarise_days([], D2, D2)
    assert len(days) == 1 and days[0]["date"] == "2026-10-10"


def test_a_range_longer_than_the_limit_or_backwards_is_refused_before_any_query():
    with pytest.raises(ValueError):
        DD.progress_days(date(2026, 1, 1), date(2026, 4, 3))    # 93 days, one more than the limit
    with pytest.raises(ValueError):
        DD.progress_days(D3, D1)                                 # end before start


def test_a_full_month_and_the_insights_90_day_period_fit_in_one_request():
    assert DD.MAX_RANGE_DAYS >= 90
    days = DD.summarise_days([], date(2026, 10, 1), date(2026, 10, 31))
    assert len(days) == 31


def test_a_meal_in_the_recent_list_has_its_macros_flags_and_sensor_response():
    m = meal(D2, 13, sodium=1200, sugar=30, mid="m9")
    m.update({"pre_glucose_mmol": 6.1, "peak_glucose_mmol": 9.4, "minutes_to_peak": 50, "rise_mmol": 2.3})
    d = DD.meal_detail(m)
    assert d["id"] == "m9" and d["when"] == "1:30 pm" and d["name"] == "Chicken rice"
    assert d["kcal"] == 455 and d["carbs_g"] == 60.0 and d["fibre_g"] == 4.0 and d["sodium_mg"] == 1200
    assert d["flags"] == ["salt", "sugar"]
    assert d["response"] == {"pre_mmol": 6.1, "peak_mmol": 9.4, "minutes_to_peak": 50, "rise_mmol": 2.3}


def test_a_meal_without_sensor_data_has_no_response_and_unknown_macros_stay_none():
    m = meal(D2, 13, protein=None, fibre=None, name="", mid="m10")
    m.update({"pre_glucose_mmol": None, "peak_glucose_mmol": None, "minutes_to_peak": None, "rise_mmol": None})
    d = DD.meal_detail(m)
    assert d["response"] is None
    assert d["name"] is None
    assert d["protein_g"] is None and d["fibre_g"] is None and d["kcal"] is None
    assert d["flags"] == []


def test_a_partly_known_sensor_response_keeps_the_known_values():
    m = meal(D2, 13, mid="m11")
    m.update({"pre_glucose_mmol": None, "peak_glucose_mmol": 8.0, "minutes_to_peak": None, "rise_mmol": None})
    assert DD._response(m) == {"pre_mmol": None, "peak_mmol": 8.0, "minutes_to_peak": None, "rise_mmol": None}


def test_no_meal_ids_means_no_query():
    assert DD.meal_details([]) == {}

