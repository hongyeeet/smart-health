"""The offset the calendar uses: the dose-timing agent's preferred offset, fixed ahead of the day."""
from app.agents import dose_timing as d


def test_no_offset_without_enough_history():
    assert d.learned_offset([]) == 0
    assert d.learned_offset([40.0] * (d.PRIOR_MIN_DOSES - 1)) == 0


def test_the_offset_is_the_menu_step_nearest_the_usual_delay_minus_the_cushion():
    assert d.learned_offset([8.0] * 7) == 0           # 8 - 10 is below the menu: the first step
    assert d.learned_offset([25.0] * 7) == 15
    assert d.learned_offset([38.0] * 7) == 30
    assert d.learned_offset([90.0] * 7) == 45         # never past the last step, so it stays inside the dose window


def test_it_uses_the_median_so_one_late_dose_does_not_move_it():
    assert d.learned_offset([10, 10, 12, 11, 9, 10, 300]) == 0


def test_the_offset_is_always_one_of_the_menu_and_inside_the_window():
    for delay in range(1, 200, 7):
        o = d.learned_offset([float(delay)] * 8)
        assert o in d.MENU and o < d.WINDOW_MIN
