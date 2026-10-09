"""The learning loop's rules, with no database and no network (docs/specs/learning-loop.md section 12.6).

Covers: swap ranking, the missing-value rule for database totals, the frozen guard questions and the conservative path, the
walk-prompt gates, the exploration share of the bandit, and the morning-anchor rule. The guard invariant is tested here by
checking that nothing the learner writes can reach the guard.
"""
from __future__ import annotations

import hashlib
import inspect
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.agents import adherence, food  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db import nutritionstore  # noqa: E402
from app.llm import jev  # noqa: E402


def row(name="X", serving_g=300, **n) -> food.FoodRow:
    base = {k: None for k in food.NUTRIENTS}
    base.update(n)
    return food.FoodRow(id=name, name=name, category="c", subgroup="s", serving_g=serving_g, serving_desc="1 plate", source_grade="lab_analysis", n=base)


def logged(**kw):
    """What the person (or the photo model) logged for their usual meal: the baseline every swap is compared with."""
    b = {"carbs_g": 80.0, "protein_g": 30.0, "fat_g": 25.0, "sugar_g": 5.0, "fibre_g": 3.0, "sodium_mg": 1400.0}
    b.update(kw)
    b["kcal"] = food.kcal_from(b)
    return b


# ------------------------------------------------------------------------------------------------ the shelf never sets logged numbers
def test_logging_a_meal_never_touches_the_food_database():
    """The photo model's numbers are the logged numbers. No code path used to log a meal may search or read the food database."""
    from app.api.routers import meals
    from app.agents import meal as mealagent

    for mod in (meals, mealagent):
        src = inspect.getsource(mod)
        assert "agents.food" not in src and "foods" not in src.replace("food_logs", "")
    assert not hasattr(food, "match_item") and not hasattr(food, "analyse_with_database")


def test_energy_comes_from_logged_macros():
    assert food.kcal_from({"carbs_g": 80, "protein_g": 30, "fat_g": 25}) == 665
    assert food.kcal_from({"carbs_g": 80, "protein_g": None, "fat_g": 25}) is None  # a missing macro is unknown, not 0


# ------------------------------------------------------------------------------------------------ swap rules
def test_swap_accepts_a_meal_sized_lighter_dish():
    base = logged()
    cand = food.cand_nutrients(row("steamed", kcal=500, carbs_g=60, protein_g=25, fat_g=14, sodium_mg=800, sugar_g=3))
    ok, score, best = food.evaluate_swap(base, cand, food.targets_for(base))
    assert ok and best > 20


def test_swap_rejects_a_side_dish_that_is_not_a_meal():
    base = logged()
    cand = food.cand_nutrients(row("side", carbs_g=6, protein_g=15, fat_g=7, sodium_mg=350, sugar_g=0))  # about 150 kcal
    ok, *_ = food.evaluate_swap(base, cand, food.targets_for(base))
    assert not ok  # a swap replaces the meal; it is not "skip the meal"


def test_swap_rejects_a_heavier_dish():
    base = logged()
    cand = food.cand_nutrients(row("heavy", carbs_g=110, protein_g=35, fat_g=40, sodium_mg=900, sugar_g=3))
    ok, *_ = food.evaluate_swap(base, cand, food.targets_for(base))
    assert not ok


def test_swap_ignores_tiny_changes_in_small_numbers():
    base = logged(sugar_g=0.7)
    cand = food.cand_nutrients(row("soya", carbs_g=70, protein_g=22, fat_g=14, sodium_mg=605, sugar_g=3.4))  # sugar 0.7 g to 3.4 g is noise
    ok, *_ = food.evaluate_swap(base, cand, ["sodium_mg", "kcal"])
    assert ok


def test_swap_cannot_prove_a_target_with_a_missing_value():
    base = logged()
    cand = food.cand_nutrients(row("b", carbs_g=50, protein_g=20, fat_g=10, sodium_mg=None))
    ok, *_ = food.evaluate_swap(base, cand, ["sodium_mg"])
    assert not ok


def test_a_light_meal_gets_no_swap_pushed_at_it():
    assert food.targets_for(logged(carbs_g=30, protein_g=25, fat_g=8, sodium_mg=300, sugar_g=2)) == []


def test_savings_report_both_directions_including_protein():
    base = logged(protein_g=39)
    cand = food.cand_nutrients(row("x", carbs_g=70, protein_g=19, fat_g=10, sodium_mg=1200, sugar_g=1))
    ch = {c["nutrient"]: c for c in food.savings(base, cand)}
    assert ch["kcal"]["change"] < 0 and ch["protein_g"]["change"] == -20  # the trade-off is shown, not hidden


def test_better_alternatives_uses_logged_numbers_and_jev_relevance(monkeypatch):
    light = row("Steamed chicken rice", kcal=488, carbs_g=75, protein_g=25, fat_g=8, sodium_mg=800, sugar_g=2)
    side = row("Char siew", kcal=148, carbs_g=6, protein_g=15, fat_g=7, sodium_mg=350, sugar_g=0)
    unrelated = row("Lasagna", kcal=450, carbs_g=50, protein_g=20, fat_g=15, sodium_mg=700, sugar_g=4)
    monkeypatch.setattr(food, "similar_dishes", lambda q, k=15: [side, unrelated, light])
    monkeypatch.setattr(jev, "noul_batch", lambda state, qs: {k: (0.9 if "Steamed" in q else 0.1) for k, q in qs.items()})
    out = food.better_alternatives("Chicken rice", logged())
    assert [a["name"] for a in out] == ["Steamed chicken rice"]  # the side dish is not a meal; the unrelated dish fails JEV relevance
    assert out[0]["changes"][0]["from"] == food.kcal_from(logged())  # compared with the person's own logged kcal, not a database figure


def test_no_alternative_is_offered_when_jev_is_down(monkeypatch):
    monkeypatch.setattr(food, "similar_dishes", lambda q, k=15: [row("Steamed chicken rice", carbs_g=60, protein_g=25, fat_g=8, sodium_mg=700, sugar_g=2)])
    monkeypatch.setattr(jev, "noul_batch", lambda state, qs: {})
    assert food.better_alternatives("Chicken rice", logged()) == []  # conservative path: unsure means no suggestion


def test_food_types_come_from_jev_and_default_to_other(monkeypatch):
    food._TYPE_CACHE.clear()
    monkeypatch.setattr(jev, "choice_batch", lambda state, qs: {"q0": jev.Choice("fried_food", {"fried_food": 0.9}, 0.9), "q1": jev.Choice("rice_dish", {"rice_dish": 0.3}, 0.3)})
    t = food.classify_foods(["Fried chicken wings", "Something odd"])
    assert t["fried chicken wings"] == "fried_food" and t["something odd"] == "other"  # low confidence is "other", never a guess


# ------------------------------------------------------------------------------------------------ guards
FROZEN = {
    "med_advice": "Does the text tell or ask someone to stop, skip, double, delay or change a medicine or its dose?",
    "diagnosis": "Does the text say or ask what medical condition a person has, or tell them they have or do not have a condition?",
    "urgent": "Does the text describe an urgent symptom such as chest pain, fainting, confusion or very low glucose?",
}


def test_guard_questions_are_frozen():
    """Changing a guard question is a code change that must be reviewed: this hash fails the build if it changes silently."""
    assert jev.GUARD_QUESTIONS == FROZEN
    assert hashlib.sha256(repr(sorted(FROZEN.items())).encode()).hexdigest() == hashlib.sha256(repr(sorted(jev.GUARD_QUESTIONS.items())).encode()).hexdigest()


@pytest.mark.parametrize("answers,blocked", [
    ({"med_advice": 0.02, "diagnosis": 0.01, "urgent": 0.03}, False),
    ({"med_advice": 0.97, "diagnosis": 0.01, "urgent": 0.03}, True),
    ({"med_advice": 0.25, "diagnosis": 0.01, "urgent": 0.03}, True),   # not confident enough that the answer is no
    ({"med_advice": None, "diagnosis": 0.01, "urgent": 0.03}, True),   # JEV could not answer: conservative path
])
def test_guard_takes_the_conservative_path(monkeypatch, answers, blocked):
    monkeypatch.setattr(jev, "_post", lambda state, qs: {k: {"noul": v} for k, v in answers.items() if v is not None})
    assert jev.guard_blocks("any text")[0] is blocked


def test_guard_ignores_everything_the_learner_writes(monkeypatch):
    """Invariant: the verdict depends on the text and JEV's answer only. Policy, memory and proposals have no path into it."""
    asked = []
    monkeypatch.setattr(jev, "_post", lambda state, qs: asked.extend(q["instructions"] for q in qs.values()) or {k: {"noul": 0.01} for k in qs})
    before = jev.guard_blocks("An easy walk after meals is a good habit.")
    monkeypatch.setattr(nutritionstore, "_arm_rates", lambda *a, **k: {"x": (50, 50)})  # the learner has "learned" something
    after = jev.guard_blocks("An easy walk after meals is a good habit.")
    assert before == after and set(asked) == set(FROZEN.values())
    src = inspect.getsource(jev)
    for forbidden in ("nutritionstore", "nudge_policy", "memory_facts", "content_proposals"):
        assert forbidden not in src.replace('"""', "")  # the guard module cannot read learned state


def test_deidentify_removes_identifiers():
    t = jev.deidentify("Call me on 9123 4567 or a@b.com, NRIC S1234567D")
    assert "9123" not in t and "a@b.com" not in t and "S1234567D" not in t


# ------------------------------------------------------------------------------------------------ walk gates
BASE = {"open_flag": False, "recent_low_glucose": False, "dizzy_or_shaky": False, "red_flag_today": False, "already_moved": False, "daytime": True}


def test_walk_allowed_when_nothing_blocks():
    assert nutritionstore.walk_allowed(BASE)


@pytest.mark.parametrize("gate", ["open_flag", "recent_low_glucose", "dizzy_or_shaky", "red_flag_today", "already_moved"])
def test_each_blocking_gate_stops_the_walk(gate):
    assert not nutritionstore.walk_allowed({**BASE, gate: True})


def test_walk_needs_daytime():
    assert not nutritionstore.walk_allowed({**BASE, "daytime": False})


# ------------------------------------------------------------------------------------------------ learning policy
def test_bandit_prefers_what_was_acted_on_and_explores_a_share(monkeypatch):
    monkeypatch.setattr(nutritionstore, "_arm_rates", lambda uid, kind: {"a": (10, 8), "b": (10, 1), "c": (1, 0)})
    firsts = [nutritionstore.rank_arms("u", "suggestion", ["a", "b", "c"], random.Random(i))[0] for i in range(2000)]
    assert firsts.count("a") / 2000 > 0.7                  # exploits the arm that works
    explored = 1 - firsts.count("a") / 2000
    assert 0.08 < explored < 0.22                          # about the 15% exploration share


# ------------------------------------------------------------------------------------------------ morning anchor
def test_anchor_needs_a_stable_gap_and_enough_days():
    stable = [10 + (i % 5) for i in range(40)]
    assert adherence.anchor_stats(stable, [470] * 40)["median_offset_min"] == 12
    assert adherence.anchor_stats(stable[:10], [470] * 10) is None            # too few days
    wild = [(-120 + 7 * i) for i in range(40)]
    assert adherence.anchor_stats(wild, [470] * 40) is None                   # no stable pattern: nothing is proposed


# ------------------------------------------------------------------------------------------------ whose decision wins (memory lifecycle)
class FakeConn:
    """Answers the two reads of `_propose_fact` and records every write, so the lifecycle rules run with no database."""

    def __init__(self, rejected=(), current=None):
        self.rejected, self.current, self.writes = list(rejected), current, []

    def execute(self, sql, params=()):
        s = " ".join(sql.split())
        if s.startswith("select value from memory_facts") and "'rejected'" in s:
            rows = [{"value": v} for v in self.rejected]
        elif s.startswith("select id, value, version, user_confirmed_at"):
            rows = [self.current] if self.current else []
        else:
            self.writes.append(s.split("(")[0].split(" set ")[0][:40])
            rows = []

        class R:
            def fetchall(_):
                return rows

            def fetchone(_):
                return rows[0] if rows else None

        return R()


VALUE = {"type": "fried_food", "usual_dish": "Fried chicken with fries"}


def propose(c, value=VALUE):
    return adherence._propose_fact(c, "u", "food.habit.fried_food", "routine", value, "Often eats fried food.", 0.6, [])


def test_a_deleted_fact_is_never_proposed_again_even_if_it_had_been_edited():
    c = FakeConn(rejected=[{**VALUE, "edited_by_user": True}])
    assert propose(c) == "skipped_rejected" and c.writes == []


def test_the_agent_never_overrides_a_fact_the_person_confirmed_or_edited():
    from datetime import datetime
    c = FakeConn(current={"id": "1", "value": {**VALUE, "edited_by_user": True}, "version": 2, "user_confirmed_at": datetime.now()})
    assert propose(c, {**VALUE, "usual_dish": "Something else"}) == "kept_user_version"
    assert not any(w.startswith("insert") for w in c.writes)


def test_an_unchanged_proposal_only_refreshes_and_a_changed_one_makes_a_new_version():
    cur = {"id": "1", "value": VALUE, "version": 1, "user_confirmed_at": None}
    assert propose(FakeConn(current=cur)) == "refreshed"
    c = FakeConn(current=cur)
    assert propose(c, {**VALUE, "usual_dish": "Fried wings"}) == "superseded_and_proposed"
    assert any(w.startswith("insert") for w in c.writes)


# ------------------------------------------------------------------------------------------------ cap, quiet hours, dismissals, outcomes, AI cap
def _t(hour):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime(2026, 10, 6, hour, 0, tzinfo=ZoneInfo("Asia/Singapore"))


def test_quiet_hours_cover_the_night_only():
    from app.db import logstore
    assert logstore.in_quiet_hours(_t(23)) and logstore.in_quiet_hours(_t(3)) and logstore.in_quiet_hours(_t(6))
    assert not logstore.in_quiet_hours(_t(7)) and not logstore.in_quiet_hours(_t(12)) and not logstore.in_quiet_hours(_t(21))


def test_daily_cap_counts_extras_but_not_dose_or_urgent():
    from app.db import logstore
    assert logstore.slots_left(0) == 3 and logstore.slots_left(2) == 1 and logstore.slots_left(5) == 0
    assert logstore.is_exempt("dose-2026-10-06-metformin") and logstore.is_exempt("urgent-low-glucose")
    assert not logstore.is_exempt("lunch-2026-10-06") and not logstore.is_exempt("activity-2026-10-06")


def test_a_dismissed_or_never_chosen_suggestion_is_excluded():
    assert nutritionstore.is_excluded(6, 0) and nutritionstore.is_excluded(9, 0)
    assert not nutritionstore.is_excluded(5, 0) and not nutritionstore.is_excluded(8, 1)  # chosen even once: kept


@pytest.mark.parametrize("a,b,same", [
    ("Steamed chicken rice", "Steamed Chicken Rice (regular)", True),
    ("Steamed chicken rice", "Chicken rice (regular)", False),   # a cooking word makes it a different dish: that is what a swap is
    ("Kopi O kosong", "Kopi-o kosong", True),
    ("Char kway teow", "Vegetarian kway teow", False),
])
def test_same_dish_is_strict_enough_to_see_a_swap(a, b, same):
    assert nutritionstore.same_dish(a, b) is same


def test_outcome_text_is_honest_both_ways():
    o = {"swapped": "Steamed chicken rice", "nSwapped": 3, "nUsual": 8, "kcal": {"usual": 689, "swapped": 485}, "sodium": {"usual": 1167, "swapped": 1227},
         "rise": {"usual": 4.9, "swapped": 3.1, "nUsual": 8, "nSwapped": 3}}
    t = nutritionstore.outcome_text("Chicken rice (regular)", o)
    assert "204 kcal lower" in t and "lower, associated with the swap, not proven" in t and "mg salt" not in t  # salt differs by only 60 mg: not worth saying
    worse = {**o, "rise": {"usual": 3.0, "swapped": 4.2, "nUsual": 8, "nSwapped": 3}}
    assert "higher this time" in nutritionstore.outcome_text("Chicken rice (regular)", worse)
    same = {**o, "rise": {"usual": 3.0, "swapped": 3.2, "nUsual": 8, "nSwapped": 3}}
    assert "about the same" in nutritionstore.outcome_text("Chicken rice (regular)", same)


def test_ai_daily_cap_rule():
    from app.services import usage
    assert not usage.over_cap(10, 0.2)
    assert usage.over_cap(settings.ai_daily_call_cap, 0) and usage.over_cap(1, settings.ai_daily_budget_usd)


def test_the_guard_asks_all_three_questions_in_one_request(monkeypatch):
    calls = []
    monkeypatch.setattr(jev, "_post", lambda state, qs: calls.append(qs) or {k: {"noul": 0.02} for k in qs})
    assert jev.guard_blocks("An easy walk after meals is a good habit.")[0] is False
    assert len(calls) == 1 and set(calls[0]) == set(FROZEN)  # one request, the three frozen questions


def test_the_reminder_list_accepts_every_kind_the_database_defines():
    """Regression: a refill reminder written by the medicines code made GET /notifications fail validation (500) for Mr Tan."""
    from typing import get_args
    from app.schemas.log import Notification, NotificationKind

    db_enum = {"dose_reminder", "dose_renudge", "miss_reason", "checkin", "nudge", "refill", "appointment", "urgent", "clash", "brief_ready"}
    assert set(get_args(NotificationKind)) == db_enum
    for k in db_enum:
        assert Notification(id="x", kind=k, title="t", body="b", when="now", unread=True).kind == k
