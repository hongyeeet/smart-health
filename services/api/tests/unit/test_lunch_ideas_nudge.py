"""The lunch-ideas reminder (and its email): due only inside the lunch window with no lunch logged, only with ideas that pass the guard."""
from datetime import datetime

import pytest

from app.db import nutritionstore as ns

TZ = ns.TZ
NOON = datetime(2026, 10, 14, 12, 0, tzinfo=TZ)
IDEAS = [{"name": "Brown rice, steamed chicken", "key": "a"}, {"name": "Chicken rice, less rice", "key": "b"}]


@pytest.fixture
def setup(monkeypatch):
    tried = []
    monkeypatch.setattr(ns, "lunch_window", lambda uid: (690, 810))                 # 11:30 to 13:30
    monkeypatch.setattr(ns, "lunch_options", lambda uid, *a, **k: IDEAS)
    monkeypatch.setattr(ns, "guarded", lambda uid, text, rule: True)
    monkeypatch.setattr(ns, "policy_try", lambda uid, kind, key: tried.append((kind, key)))
    monkeypatch.setattr(ns.texts, "person_language", lambda uid: "en")
    return tried


def test_ideas_are_due_inside_the_lunch_window(setup):
    key, kind, title, body, route, until = ns.lunch_ideas_nudge("u", set(), 0, NOON)
    assert key == "lunch-2026-10-14" and kind == "nudge" and route == "E8"
    assert title == "Lunch ideas for you" and body == "Ideas that suit you: Brown rice, steamed chicken, Chicken rice, less rice."
    assert until.hour == 13 and until.minute == 30
    assert setup == [("suggestion", "a"), ("suggestion", "b")]                       # each idea named is counted as tried


@pytest.mark.parametrize("when", [datetime(2026, 10, 14, 11, 0, tzinfo=TZ), datetime(2026, 10, 14, 14, 0, tzinfo=TZ)])
def test_nothing_outside_the_lunch_window(setup, when):
    assert ns.lunch_ideas_nudge("u", set(), 0, when) is None and setup == []


def test_nothing_when_lunch_is_already_logged_or_the_reminder_is_already_stored(setup):
    assert ns.lunch_ideas_nudge("u", set(), 1, NOON) is None
    assert ns.lunch_ideas_nudge("u", {"lunch-2026-10-14"}, 0, NOON) is None


def test_nothing_when_there_are_no_ideas_or_the_guard_blocks_the_text(setup, monkeypatch):
    monkeypatch.setattr(ns, "lunch_options", lambda uid, *a, **k: [])
    assert ns.lunch_ideas_nudge("u", set(), 0, NOON) is None
    monkeypatch.setattr(ns, "lunch_options", lambda uid, *a, **k: IDEAS)
    monkeypatch.setattr(ns, "guarded", lambda uid, text, rule: False)
    assert ns.lunch_ideas_nudge("u", set(), 0, NOON) is None and setup == []


def test_nutrition_nudges_still_returns_the_lunch_ideas_first(setup, monkeypatch):
    monkeypatch.setattr(ns, "salt_nudge", lambda *a, **k: None)
    out = ns.nutrition_nudges("u", set(), 0, NOON, max_new=5)
    assert [o[0] for o in out] == ["lunch-2026-10-14"]
    assert ns.nutrition_nudges("u", set(), 0, NOON, max_new=0) == []
