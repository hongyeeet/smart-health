"""Insights: the pure parts (bands, metrics, drift, food ranking, dose cells, week grid, changes, finding wording)."""
import re
import uuid
from datetime import date, datetime, timedelta, timezone

from app.services import insights as I

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)


def test_bands_add_up_and_edges_belong_to_in_range():
    vals = [2.5, 3.0, 3.9, 5.0, 10.0, 10.1, 13.9, 14.0]
    pcts = {b["key"]: b["pct"] for b in I.band_pcts(vals)}
    assert pcts["very_low"] == 12.5          # 2.5
    assert pcts["low"] == 12.5               # 3.0 (not below 3.0)
    assert pcts["in_range"] == 37.5          # 3.9, 5.0, 10.0
    assert pcts["high"] == 25.0              # 10.1, 13.9
    assert pcts["very_high"] == 12.5         # 14.0
    assert round(sum(pcts.values()), 1) == 100.0


def test_bands_with_no_readings_are_zero_not_an_error():
    assert all(b["pct"] == 0.0 for b in I.band_pcts([]))


def test_glucose_metrics():
    m = I.glucose_metrics([8.0, 10.0, 12.0], days=1)
    assert m["mean"] == 10.0 and m["readings"] == 3
    assert m["gmi"] == round(3.31 + 0.02392 * 10.0 * 18.0182, 1)
    assert m["cv"] == round(100 * 1.6329931618554521 / 10.0)
    assert I.glucose_metrics([], 7)["mean"] is None and I.glucose_metrics([], 7)["readings"] == 0


def test_coverage_never_exceeds_100():
    assert I.glucose_metrics([6.0] * 400, days=1)["coverage"] == 100.0


def test_drift_counts_recent_weeks_without_a_break():
    assert I.drift_weeks([7.0, 8.5, 8.6, 8.8], 8.0) == 3
    assert I.drift_weeks([9.0, 9.0, 7.0, 8.5], 8.0) == 1
    assert I.drift_weeks([9.0, 9.0, None, 9.0], 8.0) == 1       # a week with too little data breaks the run
    assert I.drift_weeks([7.0, 7.5], 8.0) == 0


def test_food_ranking_needs_two_sightings_and_sorts_gentlest_first():
    rows = [{"food": "Chicken rice", "rise": 5.0}, {"food": "chicken  rice", "rise": 6.0}, {"food": "Fish soup", "rise": 1.0},
            {"food": "Fish soup", "rise": 2.0}, {"food": "Fish soup", "rise": 1.5}, {"food": "Laksa", "rise": 7.0}, {"food": "Kopi", "rise": None}]
    ranked, learning = I.food_responses(rows)
    assert [r["name"] for r in ranked] == ["Fish soup", "Chicken rice"]
    assert ranked[0] == {"name": "Fish soup", "n": 3, "median_rise": 1.5, "low": 1.0, "high": 2.0}
    assert learning == ["Laksa"]                    # seen once: not ranked; a meal with no rise is ignored


def _dose(status, sched_h, taken_h=None):
    base = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
    return {"status": status, "scheduled_at": base + timedelta(hours=sched_h), "taken_at": base + timedelta(hours=taken_h) if taken_h is not None else None}


def test_dose_cell_takes_the_worst_thing_that_happened():
    assert I.dose_cell([], NOW) == "none"
    assert I.dose_cell([_dose("taken", 8, 8.2)], NOW) == "taken"
    assert I.dose_cell([_dose("taken", 8, 9.5)], NOW) == "late"                     # more than an hour after its time
    assert I.dose_cell([_dose("taken", 8, 8), _dose("missed", 20)], NOW) == "missed"
    assert I.dose_cell([_dose("taken", 8, 8), _dose("pending", 20)], NOW) == "unconfirmed"   # window passed, nobody answered
    assert I.dose_cell([_dose("pending", 8)], datetime(2026, 10, 1, 8, 30, tzinfo=timezone.utc)) == "none"  # still inside its window


def test_day_grid_levels_and_dashes():
    end = date(2026, 10, 2)
    daily = {end: {"tir_pct": 72, "meals_n": 3, "exercise_min": 60, "sleep_hours": 7.5, "stress_self_avg": 4.0, "doses_scheduled": 4, "doses_taken": 2}}
    days = [end - timedelta(days=1), end]
    rows = {r["key"]: r["cells"] for r in I.measure_grid(daily, days, {"meals": {end: 3.0}, "activity": {end: 60.0}})}
    assert len(rows["glucose"]) == 2 and rows["glucose"][-1]["date"] == "2026-10-02"
    last = {k: v[-1] for k, v in rows.items()}
    assert last["glucose"]["level"] == 4 and last["glucose"]["label"] == "72%"
    assert last["meals"]["level"] == 3 and last["activity"]["level"] == 4
    assert last["sleep"]["level"] == 4 and last["stress"]["level"] == 4
    assert last["doses"]["label"] == "50%" and last["doses"]["level"] == 2
    assert all(c["label"] == "–" and c["level"] == 0 and c["value"] is None for c in (rows["glucose"][0], rows["meals"][0], rows["doses"][0]))   # no row for the day: a dash, never zero


def test_day_grid_stored_zero_without_a_log_is_a_dash_and_a_logged_zero_is_zero():
    end = date(2026, 10, 2)
    stored = {end: {"meals_n": 0, "exercise_min": 0}}                    # the daily row carries 0 for every day, logged or not
    rows = {r["key"]: r["cells"] for r in I.measure_grid(stored, [end], {})}
    assert rows["meals"][0]["label"] == "–" and rows["meals"][0]["value"] is None
    assert rows["activity"][0]["label"] == "–" and rows["activity"][0]["value"] is None
    rows = {r["key"]: r["cells"] for r in I.measure_grid(stored, [end], {"meals": {end: 2.0}, "activity": {end: 0.0}})}
    assert rows["meals"][0]["label"] == "2" and rows["meals"][0]["value"] == 2.0
    assert rows["activity"][0]["label"] == "0" and rows["activity"][0]["value"] == 0.0   # logged, and it adds to zero minutes


def test_changes_name_every_measure_with_its_direction():
    cur = {"fasting": 9.2, "tir": 45.0, "steps": 4000.0, "exercise": 20.0, "sleep": 6.5, "stress": 4.0, "doses": 80.0}
    prev = {"fasting": 7.8, "tir": 71.0, "steps": 8000.0, "exercise": 20.0, "sleep": 6.6, "stress": 3.9, "doses": 78.0}
    out = {c["id"]: c for c in I.changes(cur, prev)}
    assert set(out) == {"tir", "fasting", "steps", "exercise", "sleep", "stress", "doses"}
    assert out["tir"]["direction"] == "down" and out["tir"]["delta"] == -26.0 and out["tir"]["to"] == "C2"
    assert out["fasting"]["direction"] == "up" and out["fasting"]["delta"] == 1.4
    assert out["steps"]["direction"] == "down" and out["steps"]["to"] == "C4"
    assert out["exercise"]["direction"] == "same"
    assert out["sleep"]["direction"] == "same" and out["stress"]["direction"] == "same"     # 0.1 and 0.1 are inside the threshold
    assert out["doses"]["direction"] == "same"                                             # 2 points is inside 10


def test_changes_never_invent_a_move_and_say_none_when_a_period_has_no_value():
    out = {c["id"]: c for c in I.changes({"fasting": None}, {"fasting": 7.0})}
    assert out["fasting"]["direction"] == "none" and out["fasting"]["delta"] is None
    same = {"tir": 60.0, "fasting": 7.0, "steps": 5000.0, "exercise": 50.0, "sleep": 7.0, "stress": 2.0, "doses": 90.0}
    assert all(c["direction"] == "same" for c in I.changes(same, same))
    exercise = {c["id"]: c for c in I.changes({"exercise": 120.0}, {"exercise": 0.0})}["exercise"]
    assert exercise["direction"] == "up"                                                   # from nothing is a real change, not "about the same"


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def __iter__(self):
        return iter(self.rows)

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class _FakeConn:
    """Answers each query from the rows given for the table it reads (`from <table>`), so the insights reads can be checked without a
    database. Unknown tables give no rows. The SQL itself is not run: the rows are already the result of the query."""

    def __init__(self, daily=None, food=None, workouts=None, meds=None, med_logs=None):
        self.tables = {"daily_summary": daily or [], "food_logs": food or [], "exercise_logs": workouts or [],
                       "medications": meds or [], "medication_log": med_logs or []}

    def execute(self, sql, *args, **kwargs):
        for name, rows in self.tables.items():
            if re.search(rf"\bfrom {name}\b", sql):
                return _Rows(rows)
        return _Rows([])


def test_findings_need_enough_pairs_and_are_worded_as_associations():
    rows = [
        {"pattern_key": "evening_walk__next_morning_fasting", "n_pairs": 28, "median_delta": -0.71},
        {"pattern_key": "short_sleep__fasting_glucose", "n_pairs": 4, "median_delta": 0.68},      # too few pairs
        {"pattern_key": "unknown_key", "n_pairs": 50, "median_delta": 1.0},                         # no wording: not shown
    ]
    out = I.patterns_for(rows)
    assert [p["key"] for p in out] == ["evening_walk__next_morning_fasting"]
    assert "0.7 mmol/L lower" in out[0]["text"] and out[0]["n"] == 28 and out[0]["to"] == "C4"
    assert not any(w in out[0]["text"].lower() for w in ("because", "caused", "due to"))
    assert I.patterns_for(rows, "C3") == []


def test_period_label_and_window():
    s, e = I.window(date(2026, 10, 2), 7)
    assert (s, e) == (date(2026, 9, 26), date(2026, 10, 2))
    assert I._label(s, e, 7) == "26 Sep to 2 Oct 2026 (7 days)"


def test_overview_days_with_stored_data_fills_only_the_days_that_have_a_row():
    rows = [{"local_date": date(2026, 9, 30), "tir_pct": 62.0, "meals_n": 0, "exercise_min": 0, "sleep_hours": 6.5, "stress_self_avg": 2.0, "doses_scheduled": 2, "doses_taken": 2}]
    out = I.overview_days(_FakeConn(rows), "u", date(2026, 9, 29), date(2026, 10, 1), date(2026, 10, 11))
    by = {r["key"]: r["cells"] for r in out["rows"]}
    assert [c["label"] for c in by["glucose"]] == ["–", "62%", "–"]          # 29 and 1 have no row: dashes
    assert by["doses"][1]["label"] == "100%" and by["doses"][1]["level"] == 4
    assert by["sleep"][1]["label"] == "6.5"


def test_overview_meals_and_active_minutes_are_a_dash_on_a_day_with_no_log():
    # 30 Sep: a stored row with 0 meals and 0 minutes, but no meal or workout logged. 1 Oct: two meals and a 25 minute walk.
    daily = [{"local_date": date(2026, 9, 30), "meals_n": 0, "exercise_min": 0}, {"local_date": date(2026, 10, 1), "meals_n": 2, "exercise_min": 25}]
    food = [{"d": date(2026, 10, 1), "n": 2}]
    workouts = [{"d": date(2026, 10, 1), "mins": 25.0}]
    out = I.overview_days(_FakeConn(daily, food, workouts), "u", date(2026, 9, 29), date(2026, 10, 1), date(2026, 10, 11))
    by = {r["key"]: r["cells"] for r in out["rows"]}
    assert [c["label"] for c in by["meals"]] == ["–", "–", "2"]              # 30 Sep has a row of zero but no log: a dash
    assert [c["label"] for c in by["activity"]] == ["–", "–", "25"]
    assert by["meals"][2]["value"] == 2.0 and by["activity"][2]["level"] == 2


def test_overview_logged_workout_with_zero_minutes_is_a_zero_not_a_dash():
    workouts = [{"d": date(2026, 9, 30), "mins": 0.0}]
    out = I.overview_days(_FakeConn([], [], workouts), "u", date(2026, 9, 29), date(2026, 9, 30), date(2026, 10, 11))
    by = {r["key"]: r["cells"] for r in out["rows"]}
    assert by["activity"][0]["label"] == "–" and by["activity"][1]["label"] == "0" and by["activity"][1]["value"] == 0.0


def test_overview_days_takes_at_most_92_days_and_never_goes_past_today():
    today = date(2026, 10, 11)
    full = I.overview_days(_FakeConn(), "u", date(2026, 7, 12), date(2026, 10, 11), today)   # 92 days inclusive
    assert len(full["rows"][0]["cells"]) == 92 and full["start"] == "2026-07-12" and full["end"] == "2026-10-11"
    future = I.overview_days(_FakeConn(), "u", date(2026, 10, 9), date(2026, 10, 20), today)
    assert future["end"] == "2026-10-11" and future["today"] == "2026-10-11"
    assert [c["date"] for c in future["rows"][0]["cells"]] == ["2026-10-09", "2026-10-10", "2026-10-11"]
    assert all(c["date"] <= "2026-10-11" for r in future["rows"] for c in r["cells"])


def test_overview_days_route_refuses_ranges_over_92_days_or_backwards_before_reading_the_database():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    too_long = client.get("/api/v1/insights/overview/days", params={"from": "2026-07-11", "to": "2026-10-11"}, headers={"X-User": "demo"})
    backwards = client.get("/api/v1/insights/overview/days", params={"from": "2026-10-11", "to": "2026-10-01"}, headers={"X-User": "demo"})
    assert too_long.status_code == 422 and "92" in too_long.text
    assert backwards.status_code == 422


def test_activity_bands_leave_out_unrated_sessions_and_never_count_them_as_moderate():
    rows = [{"mins": 30, "intensity": 2}, {"mins": 20, "intensity": 3}, {"mins": 40, "intensity": None}, {"mins": 10, "intensity": 5}]
    assert I._minutes_rated(rows, 3) == 30        # moderate or harder: 20 + 10, the unrated 40 is not in it
    assert I._minutes_rated(rows, 3, 3) == 20     # moderate only
    assert I._minutes_rated(rows, 1, 2) == 30     # light
    assert I._minutes_rated(rows, 4) == 10        # vigorous
    assert I._minutes_rated([{"mins": 45, "intensity": None}], 3) == 0


def _w(d, mins, rating):
    return {"d": d, "mins": mins, "intensity": rating}


END = date(2026, 10, 12)                      # a Monday


def test_seven_days_give_seven_daily_bars_with_the_three_efforts_apart():
    rows = [_w(date(2026, 10, 12), 30, 2), _w(date(2026, 10, 12), 20, 3), _w(date(2026, 10, 10), 15, 5), _w(date(2026, 10, 10), 40, None)]
    unit, bars = I.activity_bars(rows, END, 7)
    assert unit == "day" and len(bars) == 7
    assert [b["first_day"] for b in bars][0] == "2026-10-06" and bars[-1]["first_day"] == "2026-10-12"
    last, sat = bars[-1], bars[4]
    assert (last["light"], last["moderate"], last["vigorous"]) == (30, 20, 0)
    assert (sat["light"], sat["moderate"], sat["vigorous"]) == (0, 0, 15)         # the unrated 40 minutes are in no bar
    assert bars[0]["light"] == bars[0]["moderate"] == bars[0]["vigorous"] == 0      # a day with no workout is 0
    assert not any(b["partial"] for b in bars)


def test_thirty_days_give_the_last_four_calendar_weeks_and_the_newest_is_partial():
    rows = [_w(date(2026, 9, 22), 60, 3), _w(date(2026, 10, 4), 30, 4), _w(date(2026, 10, 5), 25, 1), _w(date(2026, 10, 12), 10, 3)]
    unit, bars = I.activity_bars(rows, END, 30)
    assert unit == "week" and [b["label"] for b in bars] == ["Week of 21 Sep", "Week of 28 Sep", "Week of 5 Oct", "Week of 12 Oct"]
    assert [(b["light"], b["moderate"], b["vigorous"]) for b in bars] == [(0, 60, 0), (0, 0, 30), (25, 0, 0), (0, 10, 0)]
    assert [b["partial"] for b in bars] == [False, False, False, True]
    assert bars[-1]["last_day"] == "2026-10-12"                                    # a running week ends on the last day with data


def test_ninety_days_give_the_last_three_calendar_months_across_a_year_end():
    unit, bars = I.activity_bars([_w(date(2025, 12, 31), 50, 3), _w(date(2026, 1, 3), 20, 4)], date(2026, 1, 15), 90)
    assert unit == "month" and [b["label"] for b in bars] == ["Nov", "Dec", "Jan"]
    assert [(b["moderate"], b["vigorous"]) for b in bars] == [(0, 0), (50, 0), (0, 20)]
    assert [b["partial"] for b in bars] == [False, False, True]
    unit, full = I.activity_bars([], date(2026, 10, 31), 90)
    assert [b["partial"] for b in full] == [False, False, False]                   # the month is over on its last day


def test_workout_row_accepts_an_unrated_session():
    from app.schemas.insights import WorkoutRow
    row = WorkoutRow(id="w1", date="2 Oct", label="Strength", type="strength", intensity=None, minutes=40, glucose_change_2h=None)
    assert row.intensity is None


# ── Medication (C6): prescription medicines only count towards adherence and reasons ──
MED_CREST, MED_FISH = uuid.UUID(int=1), uuid.UUID(int=2)


def _med_log(med, day, hour, status, taken_hour=None, reason=None):
    sched = datetime(2026, 10, day, hour, 0, tzinfo=timezone.utc)
    taken = datetime(2026, 10, day, taken_hour, 0, tzinfo=timezone.utc) if taken_hour is not None else None
    return {"medication_id": med, "scheduled_at": sched, "taken_at": taken, "status": status, "reason": reason}


def _meds():
    return [{"id": MED_CREST, "name": "CRESTOR", "frequency": 1, "kind": "prescription"},
            {"id": MED_FISH, "name": "Fish oil", "frequency": 1, "kind": "supplement"}]


def test_medication_nothing_answered_is_no_percent_not_zero():
    # three doses whose window has passed, nobody answered: "0 of 3, 3 not confirmed" must not become 0%
    logs = [_med_log(MED_CREST, d, 8, "pending") for d in (1, 2, 3)]
    out = I.medication(_FakeConn(meds=_meds()[:1], med_logs=logs), "u", 30, date(2026, 10, 3), datetime(2026, 10, 4, 12, tzinfo=timezone.utc))
    row = out["meds"][0]
    assert row["counted"] is True and row["taken"] == 0 and row["scheduled"] == 3 and row["unconfirmed"] == 3
    assert row["adherence_pct"] is None
    assert out["adherence_pct"] is None and out["unconfirmed"] == 3 and out["taken"] == 0 and out["missed"] == 0


def test_medication_percent_counts_only_prescription_medicines_and_reasons_too():
    logs = [_med_log(MED_CREST, 1, 8, "taken", 8), _med_log(MED_CREST, 2, 8, "missed", reason="forgot"),
            _med_log(MED_CREST, 3, 8, "taken", 8), _med_log(MED_CREST, 4, 8, "missed", reason="away_from_home"),
            _med_log(MED_FISH, 1, 8, "missed", reason="felt_fine"), _med_log(MED_FISH, 2, 8, "missed", reason="felt_fine"),
            _med_log(MED_FISH, 3, 8, "taken", 8)]
    out = I.medication(_FakeConn(meds=_meds(), med_logs=logs), "u", 30, date(2026, 10, 4), NOW)
    crest, fish = out["meds"]
    assert crest["counted"] is True and crest["adherence_pct"] == 50 and crest["taken"] == 2 and crest["missed"] == 2 and crest["scheduled"] == 4
    assert fish["counted"] is False and fish["adherence_pct"] is None and fish["taken"] is None and fish["scheduled"] is None
    assert len(fish["cells"]) == out["shown_days"] == 30                                          # still listed with its day-by-day grid
    assert out["taken"] == 2 and out["missed"] == 2 and out["scheduled"] == 4 and out["adherence_pct"] == 50   # the medicines not counted
    assert out["reasons"] == [{"key": "forgot", "label": "Forgot", "count": 1}, {"key": "away_from_home", "label": "Away from home", "count": 1}]


def test_medication_reasons_leave_out_non_prescription_misses():
    logs = [_med_log(MED_CREST, 1, 8, "missed", reason="cost")] + [_med_log(MED_FISH, d, 8, "missed", reason="felt_fine") for d in range(1, 4)]
    out = I.medication(_FakeConn(meds=_meds(), med_logs=logs), "u", 30, date(2026, 10, 4), NOW)
    assert out["reasons"] == [{"key": "cost", "label": "Cost", "count": 1}]


def test_medication_with_only_non_prescription_items_has_no_adherence():
    logs = [_med_log(MED_FISH, 1, 8, "taken", 8)]
    out = I.medication(_FakeConn(meds=_meds(), med_logs=logs), "u", 30, date(2026, 10, 2), NOW)
    assert out["adherence_pct"] is None and out["scheduled"] == 0 and out["meds"][0]["adherence_pct"] is None


def test_the_sleep_response_has_the_average_and_the_short_nights_but_no_usual():
    from app.schemas.insights import SleepInsights
    fields = set(SleepInsights.model_fields)
    assert "sleep_baseline" not in fields                    # "your usual" was removed from the page on 2026-10-12
    assert {"sleep_avg", "short_nights", "stress_avg", "mood_avg", "high_stress_days", "logged_days", "days", "patterns"} <= fields
