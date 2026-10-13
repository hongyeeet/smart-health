"""Meal ideas for lunch and dinner (nutritionstore.meal_options / meal_window, GET /nutrition/meal-ideas). Stubbed rows, no database."""
from __future__ import annotations

import contextlib
import random
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers import nutrition as route
from app.db import logstore, nutritionstore as ns

VERDICT_WORDS = re.compile(r"\b(because|should|good|bad|healthy|unhealthy|normal|abnormal)\b", re.I)


class Fake:
    """Answers each query by a marker in its SQL; remembers the SQL and parameters."""

    def __init__(self, answers):
        self.answers, self.seen = answers, []

    def execute(self, sql, params=None):
        self.seen.append((sql, params))
        for marker, rows in self.answers.items():
            if marker in sql:
                return _Rows(rows)
        return _Rows([])


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


def _install(monkeypatch, answers):
    c = Fake(answers)

    @contextlib.contextmanager
    def tx():
        yield c

    monkeypatch.setattr(ns, "tx", tx)
    monkeypatch.setattr(ns, "food_habits", lambda uid, **k: [])
    monkeypatch.setattr(ns, "excluded_keys", lambda *a, **k: set())
    monkeypatch.setattr(ns, "rank_arms", lambda uid, kind, keys, rng=None: list(keys))
    monkeypatch.setattr(ns.texts, "person_language", lambda uid: "en")
    return c


def _own(key, rise, n=3):
    return {"key": key, "food": key.title(), "n": n, "rise": rise, "carbs": 50.0, "sodium": 800.0}


def _answers(own, med=3.0, recent=()):
    return {"percentile_cont": [{"m": med}], "lower(food) k": [{"k": k} for k in recent], "group by 1": own, "from foods": []}


def test_dinner_own_tier_uses_the_dinner_meal_type_and_says_why_from_the_persons_numbers(monkeypatch):
    c = _install(monkeypatch, _answers([_own("fish soup", 1.8, 4), _own("laksa", 4.2), _own("steamed fish rice", 2.5)], med=3.0))
    out = ns.meal_options("u", "dinner")
    own_sql = next(s for s, _ in c.seen if "group by 1" in s)
    assert "f.meal_type=%s" in own_sql and ("u", "dinner") == next(p for s, p in c.seen if "group by 1" in s)
    assert [o["name"] for o in out] == ["Fish Soup", "Steamed Fish Rice"]            # laksa rose above the median: not offered
    assert all(o["source"] == "own" for o in out)
    assert out[0]["why"] == "After this dinner your glucose rose 1.8 mmol/L on average (you had it 4 times), less than after your typical meal (3.0)."


def test_dinners_eaten_in_the_last_two_days_are_left_out(monkeypatch):
    _install(monkeypatch, _answers([_own("fish soup", 1.8), _own("steamed fish rice", 2.5)], recent=("fish soup",)))
    assert [o["name"] for o in ns.meal_options("u", "dinner")] == ["Steamed Fish Rice"]


def test_no_typical_meal_yet_means_no_own_tier(monkeypatch):
    _install(monkeypatch, _answers([_own("fish soup", 1.8)], med=None))
    assert ns.meal_options("u", "dinner") == []                                         # unknown stays unknown


def test_fewer_than_five_dinners_gives_the_default_window(monkeypatch):
    _install(monkeypatch, {"from food_logs": [{"m": 19 * 60}] * 4})
    assert ns.meal_window("u", "dinner") == (18 * 60, 20 * 60)
    _install(monkeypatch, {"from food_logs": []})
    assert ns.meal_window("u", "dinner") == (18 * 60, 20 * 60)


def test_the_dinner_window_is_the_median_minus_30_to_plus_90_with_a_16_00_floor(monkeypatch):
    _install(monkeypatch, {"from food_logs": [{"m": m} for m in (19 * 60, 19 * 60 + 30, 20 * 60, 18 * 60 + 30, 19 * 60 + 15)]})
    assert ns.meal_window("u", "dinner") == (19 * 60 + 15 - 30, 19 * 60 + 15 + 90)
    _install(monkeypatch, {"from food_logs": [{"m": 16 * 60 + 10}] * 5})               # median 16:10: start would be 15:40
    assert ns.meal_window("u", "dinner") == (16 * 60, 16 * 60 + 10 + 90)


def test_lunch_window_and_options_are_unchanged(monkeypatch):
    _install(monkeypatch, {"from food_logs": [{"m": 12 * 60 + 15}] * 3})
    assert ns.lunch_window("u") == (11 * 60 + 30, 13 * 60 + 30)                          # the old default
    _install(monkeypatch, {"from food_logs": [{"m": 12 * 60 + 30}] * 5})
    assert ns.lunch_window("u") == (12 * 60, 14 * 60)
    _install(monkeypatch, {"from food_logs": [{"m": 10 * 60}] * 5})
    assert ns.lunch_window("u") == (10 * 60, 11 * 60 + 30)                               # floor at 10:00 for lunch
    c = _install(monkeypatch, _answers([_own("chicken rice", 1.5, 2)]))
    out = ns.lunch_options("u")
    assert out[0]["why"].startswith("After this lunch your glucose rose 1.5 mmol/L")
    assert ("u", "lunch") == next(p for s, p in c.seen if "group by 1" in s)
    shelf = next(s for s, _ in c.seen if "from foods" in s)
    assert "kcal between 350 and 600" in shelf and "breakfast" not in shelf


def test_the_dinner_shelf_is_lighter_and_has_no_breakfast_dishes(monkeypatch):
    c = _install(monkeypatch, _answers([]))
    ns.meal_options("u", "dinner")
    shelf = next(s for s, _ in c.seen if "from foods" in s)
    assert "kcal between 300 and 550" in shelf and "breakfast" in shelf and "porridge" in shelf
    assert "carbs_g <= 60" in shelf and "sodium_mg <= 900" in shelf and "'hawker' = any(flags)" in shelf


def test_lunch_and_dinner_wrappers_only_accept_those_meals():
    with pytest.raises(ValueError):
        ns.meal_options("u", "breakfast")
    with pytest.raises(ValueError):
        ns.meal_window("u", "snack")


def test_no_verdict_words_in_any_why(monkeypatch):
    _install(monkeypatch, _answers([_own("fish soup", 1.8), _own("steamed fish rice", 2.5)]))
    monkeypatch.setattr(ns, "food_habits", lambda uid, **k: [{"topDish": "Chicken rice", "alternatives": [
        {"foodId": "f1", "name": "Fish soup bee hoon", "serving": "1 bowl", "sourceGrade": "A", "changes": [{"nutrient": "carbs_g", "to": 40}, {"nutrient": "sodium_mg", "to": 700}]}]}])
    monkeypatch.setattr(ns, "saving_phrase", lambda alt, lang="en": "has less salt (700 mg) than your usual")
    out = ns.meal_options("u", "dinner", limit=5, rng=random.Random(1))
    assert {o["source"] for o in out} == {"swap", "own"}
    for o in out:
        assert not VERDICT_WORDS.search(o["why"]), o["why"]
    for key in ("lunch.why_swap", "lunch.why_general"):
        assert not VERDICT_WORDS.search(ns.texts.tr("en", key, dish="x", saving="y", carbs=1, salt=2))


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(route.router)
    calls = []

    @contextlib.contextmanager
    def one():
        yield

    monkeypatch.setattr(logstore, "one_connection", one)
    monkeypatch.setattr(ns, "meal_window", lambda uid, meal: calls.append(("window", meal)) or ((18 * 60, 20 * 60) if meal == "dinner" else (11 * 60 + 30, 13 * 60 + 30)))
    monkeypatch.setattr(ns, "meal_options", lambda uid, meal, *a, **k: calls.append(("options", meal)) or [{"key": "own:x", "name": "X", "source": "own", "why": "w"}])
    yield TestClient(app), calls
    logstore.set_user("demo")


def test_the_route_returns_the_lunch_shape_plus_the_meal(client):
    c, calls = client
    r = c.get("/nutrition/meal-ideas", params={"meal": "dinner"})
    assert r.status_code == 200
    assert r.json() == {"meal": "dinner", "windowStart": "18:00", "windowEnd": "20:00", "options": [{"key": "own:x", "name": "X", "source": "own", "why": "w"}]}
    assert c.get("/nutrition/meal-ideas", params={"meal": "lunch"}).json()["windowStart"] == "11:30"


def test_the_route_rejects_any_other_meal_and_a_missing_one(client):
    c, calls = client
    for bad in ({"meal": "breakfast"}, {"meal": "Dinner "}, {"meal": ""}, {}):
        assert c.get("/nutrition/meal-ideas", params=bad).status_code == 422
    assert calls == []


def test_the_route_is_read_only_for_mr_tan(client, monkeypatch):
    c, calls = client
    writes = []
    monkeypatch.setattr(ns, "policy_try", lambda *a, **k: writes.append(a))
    monkeypatch.setattr(ns, "policy_act", lambda *a, **k: writes.append(a))
    monkeypatch.setattr(ns, "guarded", lambda *a, **k: writes.append(a))
    logstore.set_user("mr-tan")
    assert c.get("/nutrition/meal-ideas", params={"meal": "dinner"}).status_code == 200
    assert writes == []
