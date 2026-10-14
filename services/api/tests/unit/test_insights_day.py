from app.services.insights_day import peak_after


def test_peak_is_the_highest_reading_in_the_two_hours_after_the_meal():
    g = [None] * 288
    for k, v in {88: 9.0, 90: 12.5, 96: 16.1, 104: 15.0, 130: 18.0}.items():   # 88 = 7:20 am; 130 = 10:50 am, beyond two hours of a 7:20 meal
        g[k] = v
    assert peak_after(g, 7 * 60 + 20) == (96 * 5, 16.1)


def test_no_reading_in_the_window_is_no_peak():
    assert peak_after([None] * 288, 600) is None


def test_the_window_stops_at_the_end_of_the_day():
    g = [None] * 288
    g[287] = 11.0
    assert peak_after(g, 23 * 60 + 30) == (287 * 5, 11.0)
