"""K10 baseline (first two full weeks) and the comparison kept for older clients. Pure functions in memorystore."""
from app.db import memorystore as M
from app.services.day import kcal


def week(start: str, meals: int, kcal_=None, sodium=None, doses=None, on_time=None) -> dict:
    return {"weekStart": start, "meals": meals, "avgKcal": kcal_, "avgSodium": sodium, "doses": doses, "onTimePct": on_time}


def test_no_baseline_until_two_full_weeks():
    assert M.baseline([]) is None
    assert M.baseline([week("2026-09-07", 9, 600, 500, 14, 80)]) is None


def test_baseline_uses_the_first_two_full_weeks_only():
    full = [week("2026-09-07", 9, 600, 500, 14, 80), week("2026-09-14", 7, 800, 700, 10, 60), week("2026-09-21", 9, 1200, 900, 14, 20)]
    b = M.baseline(full)
    assert b["weeks"] == ["2026-09-07", "2026-09-14"]
    assert b["meals"] == 16
    assert b["doses"] == 24
    assert b["avgKcal"] == 700.0
    assert b["avgSodium"] == 600.0
    assert b["onTimePct"] == 70.0


def test_a_missing_dose_share_is_unknown_not_zero():
    full = [week("2026-09-07", 9, 600, 500, None, None), week("2026-09-14", 7, 800, 700, None, None)]
    b = M.baseline(full)
    assert b["doses"] is None and b["onTimePct"] is None
    assert b["avgKcal"] == 700.0


def test_one_week_with_no_salt_recorded_does_not_pull_the_average_to_zero():
    full = [week("2026-09-07", 9, 600, None, 14, 80), week("2026-09-14", 7, 800, 700, 10, 60)]
    assert M.baseline(full)["avgSodium"] == 700.0


def test_compare_needs_four_full_weeks_and_is_kept_for_older_clients():
    assert M.compare([week("a", 5, 1)] * 3) is None
    c = M.compare([week("a", 5, 600), week("b", 5, 800), week("c", 5, 1000), week("d", 5, 1200)])
    assert c["avgKcal"] == {"first": 700.0, "latest": 1100.0}
    assert c["firstWeeks"] == ["a", "b"] and c["latestWeeks"] == ["c", "d"]


def test_kcal_is_unknown_when_any_macro_is_unknown():
    assert kcal(60, 20, 15) == 455
    assert kcal(60, None, 15) is None
