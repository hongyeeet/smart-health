"""GET /home/banner: which one food banner Home may show (app/api/routers/home.py). Stubs stand in for the database."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.api.routers import home
from app.core.config import settings
from app.db import logstore

TZ = ZoneInfo("Asia/Singapore")


def progress_with(status: str) -> dict:
    return {"items": [{"key": "meals", "status": status}]}


def habit(kind_avg: dict, n: int = 5, type_: str = "noodles") -> dict:
    avg = {"kcal": 500, "carbs_g": 60, "protein_g": 15, "fat_g": 12, "sugar_g": 3, "fibre_g": 2, "sodium_mg": 300}
    avg.update(kind_avg)
    return {"type": type_, "label": "Noodles", "n": n, "avg": avg}


@pytest.mark.parametrize(
    ("hour", "minute", "expected"),
    [(8, 0, "breakfast"), (12, 30, "lunch"), (19, 0, "dinner"), (15, 0, None), (23, 0, None)],
)
def test_meal_due_only_inside_a_mealtime_window(monkeypatch, hour, minute, expected):
    monkeypatch.setattr(home.logstore, "progress", lambda: progress_with("due"))
    monkeypatch.setattr(home, "datetime", type("D", (), {"now": staticmethod(lambda tz=None: datetime(2026, 10, 11, hour, minute, tzinfo=TZ))}))
    assert home._meal_due_now() == expected


def test_no_meal_banner_once_the_meal_is_logged(monkeypatch):
    monkeypatch.setattr(home.logstore, "progress", lambda: progress_with("done"))
    assert home._meal_due_now() is None


def test_no_meal_banner_when_the_meal_is_later(monkeypatch):
    monkeypatch.setattr(home.logstore, "progress", lambda: progress_with("later"))
    assert home._meal_due_now() is None


def test_high_salt_habit_is_flagged(monkeypatch):
    monkeypatch.setattr(home.nutritionstore, "food_habits", lambda uid: [habit({"sodium_mg": settings.habit_sodium_mg + 1})])
    monkeypatch.setattr(home.logstore, "current_user", lambda: "u")
    assert home._food_flag() == {"kind": "salt", "type": "noodles", "label": "Noodles", "n": 5}


def test_high_sugar_habit_is_flagged(monkeypatch):
    monkeypatch.setattr(home.nutritionstore, "food_habits", lambda uid: [habit({"sugar_g": settings.habit_sugar_g + 5})])
    monkeypatch.setattr(home.logstore, "current_user", lambda: "u")
    assert home._food_flag()["kind"] == "sugar"


def test_calorie_only_habit_is_not_a_salt_or_sugar_flag(monkeypatch):
    monkeypatch.setattr(home.nutritionstore, "food_habits", lambda uid: [habit({"kcal": settings.habit_kcal + 400})])
    monkeypatch.setattr(home.logstore, "current_user", lambda: "u")
    assert home._food_flag() is None


def test_catch_all_other_food_is_not_flagged(monkeypatch):
    monkeypatch.setattr(home.nutritionstore, "food_habits", lambda uid: [habit({"sodium_mg": settings.habit_sodium_mg + 1}, type_="other")])
    monkeypatch.setattr(home.logstore, "current_user", lambda: "u")
    assert home._food_flag() is None


def test_first_flagged_habit_wins(monkeypatch):
    habits = [habit({"kcal": 900}, type_="rice"), habit({"sodium_mg": settings.habit_sodium_mg + 1}, type_="noodles")]
    monkeypatch.setattr(home.nutritionstore, "food_habits", lambda uid: habits)
    monkeypatch.setattr(home.logstore, "current_user", lambda: "u")
    assert home._food_flag()["type"] == "noodles"


def test_banner_is_empty_when_nothing_to_say(monkeypatch):
    monkeypatch.setattr(home.logstore, "progress", lambda: progress_with("later"))
    monkeypatch.setattr(home.nutritionstore, "food_habits", lambda uid: [])
    monkeypatch.setattr(home.logstore, "current_user", lambda: "u")
    import asyncio

    assert asyncio.run(home.banner()) == {"meal": None, "flag": None}


def test_meal_windows_match_the_reminder_windows():
    # the banner must use the same windows as the meal reminder (logstore.notifications), never its own copy
    assert [w[2] for w in logstore.MEAL_WINDOWS] == ["breakfast", "lunch", "dinner"]
