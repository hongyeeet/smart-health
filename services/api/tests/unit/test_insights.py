"""Insights: the pure parts (bands, metrics, drift, food ranking, dose cells, week grid, changes, finding wording)."""
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


def test_week_grid_levels_and_blanks():
    end = date(2026, 10, 2)
    daily = {end: {"tir_pct": 72, "meals_n": 3, "exercise_min": 60, "sleep_hours": 7.5, "stress_self_avg": 4.0, "doses_scheduled": 4, "doses_taken": 2}}
    rows = {r["key"]: r["cells"] for r in I.week_grid(daily, end)}
    assert len(rows["glucose"]) == 7 and rows["glucose"][-1]["date"] == "2026-10-02"
    last = {k: v[-1] for k, v in rows.items()}
    assert last["glucose"]["level"] == 4 and last["glucose"]["label"] == "72%"
    assert last["meals"]["level"] == 3 and last["activity"]["level"] == 4
    assert last["sleep"]["level"] == 4 and last["stress"]["level"] == 4
    assert last["doses"]["label"] == "50%" and last["doses"]["level"] == 2
    assert rows["glucose"][0]["label"] == "–" and rows["glucose"][0]["level"] == 0       # no sensor data: blank, never zero
    assert rows["meals"][0]["label"] == "0"                                               # nothing stored for the day: nothing logged


def test_changes_pick_the_biggest_three_and_stay_quiet_when_nothing_moved():
    cur = {"fasting": 9.2, "tir": 45.0, "steps": 4000.0, "exercise": 20.0, "sleep": 6.5, "stress": 4.0, "doses": 80.0}
    prev = {"fasting": 7.8, "tir": 71.0, "steps": 8000.0, "exercise": 20.0, "sleep": 6.6, "stress": 3.9, "doses": 78.0}
    out = I.changes(cur, prev, 7)
    assert [c["id"] for c in out] == ["tir", "steps", "fasting"]
    assert "1.4 higher" in out[2]["text"] and out[2]["to"] == "C2"
    assert I.changes(prev, prev, 7) == []
    assert I.changes({"fasting": None}, {"fasting": 7.0}, 7) == []                         # missing data never invents a change


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
