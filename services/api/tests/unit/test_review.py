"""The reviewer screen's pure rules (app/services/review.py): key stability, verdict and comment checks, latest rating wins, the score
and its thresholds, and how the queue is built. No database and no network: the suggestion search is a fake."""
from __future__ import annotations

import pytest

from app.services import review as R


def ev(key, verdict, comment=None):
    return {"payload": {"suggestionKey": key, "verdict": verdict, "comment": comment}}


def ratings_of(n_reasonable, n_not=0, n_unsafe=0):
    """A dict of latest ratings with the given counts (unsafe ones carry a comment, as the rules require)."""
    out = {}
    for i in range(n_reasonable):
        out[f"r{i}"] = {"verdict": "reasonable", "comment": None}
    for i in range(n_not):
        out[f"n{i}"] = {"verdict": "not_reasonable", "comment": None}
    for i in range(n_unsafe):
        out[f"u{i}"] = {"verdict": "unsafe", "comment": "why"}
    return out


# ───────────────────────────────────────────────────────────────── keys
def test_suggestion_key_is_stable_and_ignores_case_and_spacing():
    a = R.suggestion_key("Chicken rice (regular)", "Roast chicken")
    assert a == R.suggestion_key("  chicken   RICE (regular) ", "roast  chicken")
    assert len(a) == 16


def test_suggestion_key_changes_with_either_dish_and_with_order():
    base = R.suggestion_key("Char kway teow", "Vegetarian kway teow")
    assert base != R.suggestion_key("Char kway teow", "Beef ball kway teow soup")
    assert base != R.suggestion_key("Vegetarian kway teow", "Char kway teow")
    assert base == R.suggestion_key("Char kway teow", "vegetarian kway teow!!")  # punctuation is normalised away


# ───────────────────────────────────────────────────────────────── verdicts and comments
@pytest.mark.parametrize("verdict", ["reasonable", "not_reasonable"])
def test_plain_verdicts_need_no_comment(verdict):
    assert R.check_rating(verdict, None) == (verdict, None)
    assert R.check_rating(verdict, "   ") == (verdict, None)


def test_unsafe_needs_a_comment_saying_why():
    with pytest.raises(ValueError, match="comment"):
        R.check_rating("unsafe", None)
    with pytest.raises(ValueError):
        R.check_rating("unsafe", "   ")
    assert R.check_rating("unsafe", " Adds sugar to a diabetic meal ") == ("unsafe", "Adds sugar to a diabetic meal")


def test_unknown_verdict_is_refused():
    for bad in ("good", "Reasonable", "", "safe"):
        with pytest.raises(ValueError):
            R.check_rating(bad, None)


def test_comment_limit_is_300_characters_on_both_sides():
    assert R.check_rating("not_reasonable", "x" * 300) == ("not_reasonable", "x" * 300)
    with pytest.raises(ValueError):
        R.check_rating("not_reasonable", "x" * 301)


# ───────────────────────────────────────────────────────────────── latest rating wins
def test_latest_rating_per_suggestion_wins():
    events = [ev("a", "not_reasonable"), ev("b", "reasonable"), ev("a", "reasonable", None)]
    out = R.latest_ratings(events)
    assert out == {"a": {"verdict": "reasonable", "comment": None}, "b": {"verdict": "reasonable", "comment": None}}


def test_an_unsafe_rating_can_be_changed_later():
    out = R.latest_ratings([ev("a", "unsafe", "x"), ev("a", "reasonable")])
    assert out["a"]["verdict"] == "reasonable"


def test_malformed_events_are_skipped_not_guessed():
    events = [{"payload": {}}, {"payload": {"suggestionKey": "a", "verdict": "maybe"}}, {"payload": {"suggestionKey": 5, "verdict": "reasonable"}}, {}]
    assert R.latest_ratings(events) == {}


# ───────────────────────────────────────────────────────────────── score and thresholds
def test_too_few_ratings_gives_no_result_below_20():
    s = R.score(ratings_of(19))
    assert s["status"] == "too_few" and s["rated"] == 19


def test_exactly_20_ratings_is_enough():
    assert R.score(ratings_of(20))["status"] == "met"
    assert R.score(ratings_of(19, 1))["status"] == "met"  # 19 of 20 is 95%
    assert R.score(ratings_of(16, 4))["status"] == "not_met"  # 80%


def test_exactly_85_percent_passes():
    s = R.score(ratings_of(17, 3))
    assert s["reasonable_share"] == 0.85
    assert s["status"] == "met"


def test_just_under_85_percent_fails():
    # 84 of 100 is 84%, one short of the target
    s = R.score(ratings_of(84, 16))
    assert s["status"] == "not_met" and s["reasonable_share"] == 0.84
    assert R.score(ratings_of(85, 15))["status"] == "met"


def test_one_unsafe_fails_even_when_the_share_is_high():
    s = R.score(ratings_of(19, 0, 1))
    assert s["reasonable_share"] == 0.95
    assert s["unsafe"] == 1 and s["status"] == "not_met"


def test_counts_and_target_are_reported():
    s = R.score(ratings_of(10, 7, 3))
    assert s["counts"] == {"reasonable": 10, "not_reasonable": 7, "unsafe": 3}
    assert s["rated"] == 20 and s["target"] == 0.85 and s["min_ratings"] == 20


def test_nothing_rated_has_no_share():
    s = R.score({})
    assert s["reasonable_share"] is None and s["status"] == "too_few"


# ───────────────────────────────────────────────────────────────── queue
def _alt(name, serving="1 plate", kcal=400, sodium=600):
    return {
        "name": name, "serving": serving,
        "changes": [
            {"nutrient": "kcal", "from": 600.0, "to": float(kcal), "change": float(kcal - 600)},
            {"nutrient": "sodium_mg", "from": 1200.0, "to": float(sodium), "change": float(sodium - 1200)},
            {"nutrient": "protein_g", "from": 20.0, "to": 25.0, "change": 5.0},
        ],
    }


def _dish(name, times=3):
    return {"name": name, "times": times, "base": {"kcal": 600.0, "protein_g": 20.0, "carbs_g": 80.0, "fat_g": 18.0, "sugar_g": 2.0, "sodium_mg": 1200.0}}


def test_queue_collects_up_to_the_limit_and_attaches_my_rating():
    alts = {"Chicken rice": [_alt("Roast chicken"), _alt("Steamed chicken")], "Laksa": [_alt("Laksa lite")]}
    fake = lambda name, base, limit: alts.get(name, [])[:limit]
    rated = {R.suggestion_key("Chicken rice", "Roast chicken"): {"verdict": "unsafe", "comment": "x"}}
    items = R.build_queue([_dish("Chicken rice"), _dish("Laksa")], rated, limit=2, suggest=fake, phrase=lambda a: f"saves {a['name']}")
    assert [i["suggested"]["name"] for i in items] == ["Roast chicken", "Steamed chicken"]
    assert items[0]["my_rating"] == {"verdict": "unsafe", "comment": "x"}
    assert items[1]["my_rating"] is None
    assert items[0]["change"] == "saves Roast chicken"


def test_queue_shows_logged_numbers_and_the_suggested_numbers():
    fake = lambda name, base, limit: [_alt("Roast chicken", kcal=350, sodium=500)]
    it = R.build_queue([_dish("Chicken rice", times=4)], {}, 5, suggest=fake, phrase=lambda a: "")[0]
    assert it["usual"]["times_logged"] == 4 and it["usual"]["kcal"] == 600.0 and it["usual"]["sodium_mg"] == 1200.0
    assert it["suggested"]["kcal"] == 350.0 and it["suggested"]["sodium_mg"] == 500.0 and it["suggested"]["serving"] == "1 plate"
    assert it["suggested"]["fat_g"] is None  # not compared, so shown as a gap, not zero


def test_queue_drops_a_repeated_suggestion():
    fake = lambda name, base, limit: [_alt("Roast chicken"), _alt("Roast chicken")]
    items = R.build_queue([_dish("Chicken rice")], {}, 5, suggest=fake, phrase=lambda a: "")
    assert len(items) == 1


def test_queue_message_says_why_it_is_empty():
    assert "eaten 2 times" in R.queue_message("mine", [], [], 20)
    assert "no lighter swap" in R.queue_message("mine", [_dish("Laksa")], [], 20).lower()
    assert R.queue_message("mine", [_dish("Laksa")], [{}] * 20, 20) is None
    assert R.queue_message("sample", [_dish("X")], [], 20).startswith("No lighter swaps")
    assert R.queue_message("sample", [_dish("X")], [{}], 20) is None


def test_minimum_logs_constant_is_two():
    # one meal is not a habit: a dish must be logged at least this many times to get a swap
    assert R.MIN_TIMES_LOGGED == 2
