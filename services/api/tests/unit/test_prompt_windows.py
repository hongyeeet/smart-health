"""When each log is "due": mood and sleep only in the morning, meals around mealtimes, a workout in the late afternoon and
evening, symptoms never. Also: which person a request acts as. No database needed: the connection and the day's counts are
stubbed, and the clock is set per case.
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db import logstore  # noqa: E402

TZ = logstore.TZ


class _Rows:
    def __init__(self, one=None, many=None):
        self._one, self._many = one, many

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._many or []


class _Conn:
    def execute(self, sql, params=None):
        return _Rows(one={"mod_min": 0, "strength": 0}, many=[])


@contextmanager
def _tx():
    yield _Conn()


def _progress_at(monkeypatch, hour: int, minute: int = 0, meals: int = 0, checkin: int = 0, workout: int = 0, mod_min: int = 0):
    class _Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 6, hour, minute, tzinfo=TZ)

    class _Conn2(_Conn):
        def execute(self, sql, params=None):
            return _Rows(one={"mod_min": mod_min, "strength": 0}, many=[])

    @contextmanager
    def tx2():
        yield _Conn2()

    monkeypatch.setattr(logstore, "datetime", _Clock)
    monkeypatch.setattr(logstore, "tx", tx2)
    monkeypatch.setattr(logstore, "_day_counts", lambda c, d: {"meals": meals, "checkin": checkin, "workout": workout, "symptom": 0})
    p = logstore.progress()
    return {i["key"]: i for i in p["items"]}, p


def due(items):
    return sorted(k for k, i in items.items() if i["status"] == "due")


def test_early_morning_nothing_is_due(monkeypatch):
    items, p = _progress_at(monkeypatch, 5, 30)
    assert due(items) == []
    assert items["checkin"]["hint"] == "Opens at 6 am"


def test_morning_asks_for_breakfast_and_the_sleep_checkin(monkeypatch):
    items, p = _progress_at(monkeypatch, 8)
    assert due(items) == ["checkin", "meals"]
    assert "breakfast" in items["meals"]["prompt"]
    assert items["checkin"]["prompt"].startswith("How did you sleep")
    assert p["next_up"]["key"] == "meals"


def test_checkin_is_morning_only(monkeypatch):
    # still not logged at midday, in the afternoon and at night: it must never be flagged again that day
    for h in (11, 12, 15, 18, 21, 23):
        items, _ = _progress_at(monkeypatch, h, 30)
        assert items["checkin"]["status"] == "later", h
        assert items["checkin"]["prompt"] is None
    items, _ = _progress_at(monkeypatch, 15)
    assert "morning" in items["checkin"]["hint"].lower()


def test_checkin_done_in_the_morning_is_not_due(monkeypatch):
    items, _ = _progress_at(monkeypatch, 8, checkin=1)
    assert items["checkin"]["status"] == "done"


def test_meals_are_due_only_around_mealtimes(monkeypatch):
    assert "meals" in due(_progress_at(monkeypatch, 8)[0])           # breakfast window
    assert "meals" not in due(_progress_at(monkeypatch, 10, 45)[0])  # between breakfast and lunch
    assert "meals" in due(_progress_at(monkeypatch, 12)[0])          # lunch window
    assert "meals" not in due(_progress_at(monkeypatch, 15)[0])      # mid-afternoon
    assert "meals" in due(_progress_at(monkeypatch, 19)[0])          # dinner window
    assert "meals" not in due(_progress_at(monkeypatch, 22)[0])      # late night


def test_a_meal_already_logged_for_the_window_is_not_asked_for_again(monkeypatch):
    assert "meals" not in due(_progress_at(monkeypatch, 8, meals=1)[0])   # breakfast done
    assert "meals" in due(_progress_at(monkeypatch, 12, meals=1)[0])      # lunch still to log
    assert "meals" not in due(_progress_at(monkeypatch, 12, meals=2)[0])  # lunch done
    assert "meals" in due(_progress_at(monkeypatch, 19, meals=2)[0])      # dinner still to log
    assert _progress_at(monkeypatch, 19, meals=3)[0]["meals"]["status"] == "done"


def test_workout_is_an_evening_prompt_and_only_while_the_week_is_open(monkeypatch):
    assert "workout" not in due(_progress_at(monkeypatch, 9)[0])
    assert "workout" not in due(_progress_at(monkeypatch, 15)[0])
    assert "workout" in due(_progress_at(monkeypatch, 17)[0])
    assert "workout" not in due(_progress_at(monkeypatch, 21, 30)[0])
    assert "workout" not in due(_progress_at(monkeypatch, 17, mod_min=200)[0])  # weekly goal already met
    assert "workout" not in due(_progress_at(monkeypatch, 17, workout=1)[0])


def test_symptoms_are_never_prompted(monkeypatch):
    for h in range(0, 24):
        assert _progress_at(monkeypatch, h)[0]["symptom"]["status"] == "later"


def test_next_up_skips_things_whose_time_has_passed(monkeypatch):
    # 22:00, nothing logged: the morning check-in and the (closed) workout window are not offered as "next"
    _, p = _progress_at(monkeypatch, 22)
    assert p["next_up"]["key"] == "meals"
    _, p = _progress_at(monkeypatch, 22, meals=3, workout=1)
    assert p["next_up"] is None


def test_unknown_user_is_rejected_and_known_ones_switch():
    assert logstore.set_user(None) == "mr-tan"                                         # no header means Mr Tan's example record
    assert logstore.current_user() == logstore.MR_TAN_USER
    assert logstore.set_user("Mr-Tan") == "mr-tan"
    assert logstore.set_user("person-0123456789ab") == "person-0123456789ab"
    assert logstore.current_user() == logstore.person_id("person-0123456789ab")
    with pytest.raises(KeyError):
        logstore.set_user("someone-else")
    logstore.set_user("person-0123456789ab")
