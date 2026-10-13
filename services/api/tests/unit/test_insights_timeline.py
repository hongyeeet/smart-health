from app.services.insights_timeline import gmi, merge_events


def row(m, **kw):
    return {"m": m, "meal_type": None, "food": None, "exercise_type": None, "symptom_type": None, "dose_status": None, "mood": None, "stress_self": None, **kw}


def test_same_meal_logged_twice_is_one():
    ev = merge_events([row(100, meal_type="lunch", food="Fish soup"), row(105, meal_type="lunch", food="Fish soup"), row(400, meal_type="dinner", food="Rice")])
    assert [m["type"] for m in ev["meals"]] == ["lunch", "dinner"]


def test_two_dinners_with_different_food_stay_two():
    ev = merge_events([row(100, meal_type="dinner", food="Soup"), row(102, meal_type="dinner", food="Economy rice")])
    assert len(ev["meals"]) == 2


def test_exercise_rows_join_into_one_span():
    ev = merge_events([row(60, exercise_type="walking"), row(65, exercise_type="walking"), row(70, exercise_type="walking"), row(300, exercise_type="walking")])
    assert ev["exercise"] == [{"m0": 60, "m1": 75, "type": "walking"}, {"m0": 300, "m1": 305, "type": "walking"}]


def test_missed_dose_marked_close_together_counts_once():
    ev = merge_events([row(10, dose_status="missed"), row(12, dose_status="missed"), row(200, dose_status="missed"), row(9, dose_status="taken")])
    assert [x["m"] for x in ev["missed"]] == [10, 200]


def test_mood_and_symptoms():
    ev = merge_events([row(5, symptom_type="thirst"), row(20, symptom_type="thirst"), row(500, symptom_type="thirst"), row(30, mood=3, stress_self=4)])
    assert len(ev["symptoms"]) == 2 and ev["mood"] == [{"m": 30, "mood": 3, "stress": 4}]


def test_gmi():
    assert gmi(9.1) == 7.2
    assert gmi(None) is None


def test_slope_per_week():
    from app.services.insights_timeline import slope_per_week

    assert round(slope_per_week([1, 2, 3, 4, 5, 6, 7]), 6) == 7.0
    assert slope_per_week([1, None, 3, None, 5]) is None   # fewer than 5 days with a value
    assert slope_per_week([5, 5, 5, 5, 5]) == 0
