"""Glucose feedback: the observations from the person's own sensor, with no database and no network.

Covers: the 5-meal rule on each side (both sides), the 0.5 mmol/L band (both sides), the 5-pair rule for the walk finding (both
sides), dismissed findings and dismissed suggestions left out, a meal JEV cannot place left out, the wording (an observation, never
a cause or advice), and the empty cases.
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.agents import glucose_feedback as G  # noqa: E402
from app.db.logstore import TZ  # noqa: E402

T0 = datetime(2026, 9, 1, 8, 0, tzinfo=TZ)
ANCHOR = datetime(2026, 9, 20, 12, 0, tzinfo=TZ)


def swap(before, after, dish="Steamed chicken rice", kind="rice dishes"):
    return G.swap_observation(dish, kind, before, after)


# ------------------------------------------------------------------------------------------------ the 5-meal rule
def test_four_meals_before_is_not_enough():
    assert swap([5.0] * 4, [4.0] * 5) is None


def test_four_meals_after_is_not_enough():
    assert swap([5.0] * 5, [4.0] * 4) is None


def test_five_on_each_side_is_enough():
    o = swap([5.0] * 5, [4.0] * 5)
    assert o is not None and o["n_before"] == 5 and o["n_after"] == 5


def test_empty_sides_give_nothing():
    assert swap([], []) is None
    assert G.walk_observation(-0.7, 0) is None


# ------------------------------------------------------------------------------------------------ the 0.5 mmol/L band
def test_a_difference_under_the_band_is_about_the_same():
    o = swap([5.0] * 5, [4.6] * 5)  # -0.4
    assert o["direction"] == "same"
    assert "about the same" in o["text"] and " less " not in o["text"]


def test_a_difference_of_exactly_the_band_counts_as_lower():
    o = swap([5.0] * 5, [4.5] * 5)  # -0.5
    assert o["direction"] == "lower"
    assert "rose 0.5 mmol/L less on average" in o["text"]


def test_a_rise_that_is_higher_after_the_switch_is_said_plainly():
    o = swap([5.0] * 5, [6.0] * 5)
    assert o["direction"] == "higher"
    assert "rose 1.0 mmol/L more on average" in o["text"]


# ------------------------------------------------------------------------------------------------ wording
def test_swap_wording_is_the_template_with_the_numbers():
    o = swap([6.0, 6.0, 6.0, 6.0, 6.0, 6.0], [4.0] * 5)
    assert o["text"] == ("After you switched to Steamed chicken rice, your glucose rose 2.0 mmol/L less on average after rice dishes "
                         "(based on 6 meals before and 5 after). This is an observation from your data, not proof.")


@pytest.mark.parametrize("delta", [-1.2, -0.4, 0.0, 0.7])
def test_no_wording_says_cause_or_advice(delta):
    texts = [swap([5.0] * 5, [5.0 + delta] * 5)["text"], G.walk_observation(delta, 9)["text"]]
    for text in texts:
        low = text.lower()
        for banned in ("because", "caused", "cause", "associated", "should", "try", "instead", "better", "worse"):
            assert banned not in low, text
        assert text.endswith("This is an observation from your data, not proof.")


# ------------------------------------------------------------------------------------------------ the walk finding (5 pairs)
def test_four_pairs_of_walks_is_not_enough():
    assert G.walk_observation(-0.71, 4) is None


def test_five_pairs_of_walks_is_enough():
    o = G.walk_observation(-0.71, 5)
    assert o["text"] == ("On mornings after an evening walk, your fasting glucose was 0.7 mmol/L lower (based on 5 evenings). "
                         "This is an observation from your data, not proof.")


def test_a_walk_difference_under_the_band_is_about_the_same():
    assert "about the same" in G.walk_observation(0.2, 28)["text"]


def test_a_walk_difference_of_exactly_the_band_counts_as_higher():
    assert "0.5 mmol/L higher" in G.walk_observation(0.5, 28)["text"]


# ------------------------------------------------------------------------------------------------ pure selection rules
def test_a_dismissed_or_rejected_or_retired_finding_is_not_live():
    assert G.pattern_is_live(None) and G.pattern_is_live("open")
    assert not any(G.pattern_is_live(s) for s in ("dismissed", "rejected", "retired"))


def test_only_suggestions_the_person_acted_on_are_compared():
    rows = [{"arm_key": "swap:a", "acts": 2}, {"arm_key": "swap:b", "acts": 0}, {"arm_key": "walk_after_salty_meal", "acts": 3}]
    assert G.acted_swap_ids(rows) == ["a"]


def test_the_switch_point_belongs_to_the_after_side():
    meals = [(ANCHOR - timedelta(hours=1), 5.0), (ANCHOR, 4.0), (ANCHOR + timedelta(hours=1), 3.0)]
    before, after = G.split_by_anchor(meals, ANCHOR)
    assert before == [5.0] and after == [4.0, 3.0]


# ------------------------------------------------------------------------------------------------ reading the rows (fake database)
class FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class FakeConn:
    def __init__(self, answers):
        self.answers = answers

    def execute(self, sql, params=None):
        for word, rows in self.answers.items():
            if word in sql:
                return FakeCursor(rows)
        raise AssertionError(f"no fake for: {sql[:60]}")


def fake_tx(answers):
    @contextmanager
    def _tx():
        yield FakeConn(answers)
    return _tx


def _meals(food, n, rise, start):
    return [{"food": food, "start_at": start + timedelta(days=i), "rise": rise} for i in range(n)]


def _swap_answers(lighter_meals, usual_meals, policy_acts=1):
    return {
        "nudge_policy": [{"arm_key": "swap:f1", "acts": policy_acts}],
        "from foods": [{"id": "f1", "name": "Steamed chicken rice"}],
        "food_logs": usual_meals + lighter_meals,
    }


def _rice_types(names):
    return {G.foodagent.normalise(n): "rice_dish" for n in names}


def test_a_swap_is_compared_from_the_first_lighter_meal(monkeypatch):
    usual = _meals("chicken rice", 6, 3.0, T0)
    lighter = _meals("Steamed chicken rice", 5, 2.0, ANCHOR)
    monkeypatch.setattr(G, "tx", fake_tx(_swap_answers(lighter, usual)))
    monkeypatch.setattr(G.foodagent, "classify_foods", _rice_types)
    out = G._swap_observations("someone")
    assert len(out) == 1
    assert out[0]["n_before"] == 6 and out[0]["n_after"] == 5 and out[0]["direction"] == "lower"
    assert out[0]["foodId"] == "f1" and out[0]["type"] == "rice_dish"


def test_a_dish_the_person_never_accepted_is_not_compared(monkeypatch):
    usual = _meals("chicken rice", 6, 3.0, T0)
    lighter = _meals("Steamed chicken rice", 5, 2.0, ANCHOR)
    answers = _swap_answers(lighter, usual, policy_acts=0)  # dismissed: no acts
    monkeypatch.setattr(G, "tx", fake_tx(answers))
    monkeypatch.setattr(G.foodagent, "classify_foods", lambda names: pytest.fail("no accepted swap, so no classification"))
    assert G._swap_observations("someone") == []


def test_a_meal_JEV_could_not_place_is_not_compared(monkeypatch):
    usual = _meals("chicken rice", 6, 3.0, T0)
    lighter = _meals("Steamed chicken rice", 5, 2.0, ANCHOR)
    monkeypatch.setattr(G, "tx", fake_tx(_swap_answers(lighter, usual)))
    monkeypatch.setattr(G.foodagent, "classify_foods", lambda names: {G.foodagent.normalise(n): "other" for n in names})
    assert G._swap_observations("someone") == []


def test_too_few_meals_on_one_side_gives_no_swap(monkeypatch):
    usual = _meals("chicken rice", 4, 3.0, T0)
    lighter = _meals("Steamed chicken rice", 5, 2.0, ANCHOR)
    monkeypatch.setattr(G, "tx", fake_tx(_swap_answers(lighter, usual)))
    monkeypatch.setattr(G.foodagent, "classify_foods", _rice_types)
    assert G._swap_observations("someone") == []


def test_the_walk_row_is_read_only_when_live(monkeypatch):
    rows = [{"pattern_key": G.WALK_PATTERN, "n_pairs": 28, "median_delta": -0.71, "status": "dismissed"},
            {"pattern_key": G.WALK_PATTERN, "n_pairs": 20, "median_delta": -0.5, "status": "open"}]
    monkeypatch.setattr(G, "tx", fake_tx({"pattern_candidates": rows}))
    assert G._walk_observation("someone")["n"] == 20
    monkeypatch.setattr(G, "tx", fake_tx({"pattern_candidates": rows[:1]}))
    assert G._walk_observation("someone") is None


# ------------------------------------------------------------------------------------------------ run(): proposals and empty cases
def test_empty_run_reports_nothing(monkeypatch):
    monkeypatch.setattr(G, "_swap_observations", lambda u: [])
    monkeypatch.setattr(G, "_walk_observation", lambda u: None)
    assert G.run("someone", write=False) == {"swaps": [], "walk": None, "proposals": []}


def test_dry_run_asks_no_guard_and_writes_nothing(monkeypatch):
    monkeypatch.setattr(G, "_swap_observations", lambda u: [])
    monkeypatch.setattr(G, "_walk_observation", lambda u: G.walk_observation(-0.71, 28))
    monkeypatch.setattr(G, "guarded", lambda *a: pytest.fail("a dry run must not log a guard decision"))
    rep = G.run("someone", write=False)
    assert rep["walk"] == {"n": 28, "direction": "lower"}
    assert rep["proposals"][0]["result"] == "dry_run" and rep["proposals"][0]["guard"] == "not_checked"


def test_write_proposes_each_observation_as_a_fact(monkeypatch):
    sw = swap([6.0] * 6, [4.0] * 5)
    sw.update({"foodId": "f1", "type": "rice_dish"})
    monkeypatch.setattr(G, "_swap_observations", lambda u: [sw])
    monkeypatch.setattr(G, "_walk_observation", lambda u: G.walk_observation(-0.71, 28))
    monkeypatch.setattr(G, "guarded", lambda u, text, rule: True)
    monkeypatch.setattr(G, "audit", lambda *a, **k: None)
    seen = []

    def fake_propose(c, user_id, key, cat, value, text, conf, refs):
        seen.append((key, cat, value))
        return "proposed"

    monkeypatch.setattr(G, "_propose_fact", fake_propose)

    @contextmanager
    def _tx():
        yield None

    monkeypatch.setattr(G, "tx", _tx)
    rep = G.run("someone", write=True)
    assert seen == [("food.swap.f1", "food_response", {"type": "rice_dish", "direction": "lower"}),
                    ("activity.walk.evening_fasting", "routine", {"direction": "lower"})]
    assert [p["result"] for p in rep["proposals"]] == ["proposed", "proposed"]


def test_a_blocked_observation_is_not_stored(monkeypatch):
    monkeypatch.setattr(G, "_swap_observations", lambda u: [])
    monkeypatch.setattr(G, "_walk_observation", lambda u: G.walk_observation(-0.71, 28))
    monkeypatch.setattr(G, "guarded", lambda u, text, rule: False)
    monkeypatch.setattr(G, "_propose_fact", lambda *a: pytest.fail("blocked text must not be stored"))

    @contextmanager
    def _tx():
        yield None

    monkeypatch.setattr(G, "tx", _tx)
    rep = G.run("someone", write=True)
    assert rep["proposals"][0]["guard"] == "blocked"


def test_confidence_grows_with_evidence_and_is_capped():
    assert G._confidence(0) == 0.4
    assert G._confidence(5) == 0.5
    assert G._confidence(500) == 0.9


def test_nudges_returns_nothing_here():
    assert G.nudges("someone", T0, set(), 5) == []
