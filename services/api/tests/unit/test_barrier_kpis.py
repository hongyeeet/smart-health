"""K2 "What gets in the way" KPI row: the pure shaping of the numbers (no data gives None, a real zero stays zero)."""
from datetime import date

from app.services import barrier_kpis as K
from app.db.logstore import APP_USER, MR_TAN_USER
from app.db.memorystore import HIDDEN_FACT_KEYS, hidden_keys

TODAY = date(2026, 10, 11)  # a Sunday


def test_no_data_at_all_gives_none_for_the_numbers_that_need_data():
    s = K.summarise(TODAY, {"scheduled": 0, "missed": 0}, {"confirmed": 0, "on_time": 0, "missed": 0}, [], {"active": 0, "proposed": 0})
    assert s["missedThisWeek"] is None
    assert s["onTimePct"] is None
    assert s["topReason"] is None
    assert s["confirmedDoses"] == 0
    # a count of confirmed ideas is a real count, so zero stays zero
    assert s["confirmedBarriers"] == 0 and s["waitingBarriers"] == 0


def test_a_week_with_doses_and_no_misses_is_zero_not_a_dash():
    s = K.summarise(TODAY, {"scheduled": 14, "missed": 0}, {"confirmed": 0, "on_time": 0, "missed": 0}, [], {"active": 0, "proposed": 0})
    assert s["missedThisWeek"] == 0
    assert s["scheduledThisWeek"] == 14


def test_on_time_share_is_over_confirmed_doses_only():
    s = K.summarise(TODAY, {"scheduled": 4, "missed": 1}, {"confirmed": 20, "on_time": 15, "missed": 5}, [], {"active": 2, "proposed": 1})
    assert s["onTimePct"] == 75
    assert s["confirmedDoses"] == 20
    assert s["missedThisWeek"] == 1
    assert s["confirmedBarriers"] == 2 and s["waitingBarriers"] == 1


def test_top_reason_is_the_most_common_with_its_label_and_the_missed_total():
    reasons = [{"key": "forgot", "n": 9}, {"key": "ran_out", "n": 4}, {"key": "felt_fine", "n": 2}]
    s = K.summarise(TODAY, {"scheduled": 7, "missed": 2}, {"confirmed": 30, "on_time": 20, "missed": 15}, reasons, {"active": 0, "proposed": 0})
    assert s["topReason"] == {"key": "forgot", "label": "Forgot", "count": 9, "missed": 15}


def test_a_tie_for_top_reason_is_broken_by_key_so_the_answer_is_stable():
    reasons = [{"key": "side_effects", "n": 3}, {"key": "cost", "n": 3}]
    s = K.summarise(TODAY, {"scheduled": 1, "missed": 0}, {"confirmed": 6, "on_time": 6, "missed": 6}, reasons, {"active": 0, "proposed": 0})
    assert s["topReason"]["key"] == "cost"


def test_week_starts_on_monday():
    s = K.summarise(TODAY, {"scheduled": 0, "missed": 0}, {"confirmed": 0, "on_time": 0, "missed": 0}, [], {})
    assert s["weekStart"] == "2026-10-05"


def test_the_hidden_running_out_idea_is_excluded_from_the_barrier_counts():
    assert "barrier.ran_out" in HIDDEN_FACT_KEYS


def test_the_running_out_idea_is_hidden_for_mr_tan_only():
    assert hidden_keys(MR_TAN_USER) == ["barrier.ran_out"]
    assert hidden_keys(APP_USER) == []
    assert hidden_keys("person-0123456789ab") == []
