"""Glucose feedback: what the person's own sensor shows after a habit they chose to change (LL6), shown as an observation, never advice.

Two sources. (a) A swap: the person accepted a lighter-dish suggestion, so the rise after meals of that dish kind is compared before
and after they began choosing it (matched meals with a sensor rise, at least 5 on each side). (b) An evening walk: the nightly
finding in pattern_candidates, when it has at least 5 pairs.
What it does: proposes one memory fact per observation, as `proposed` only, with a fixed template and the person's own numbers.
What it will not do: say a habit caused anything ("associated with" is never used either), advise, or judge a food. Thresholds (5 meals,
5 pairs, the 0.5 mmol/L band) are placeholders pending clinical review.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.agents import food as foodagent
from app.agents.adherence import _propose_fact
from app.agents.trace import audit
from app.db.logstore import tx
from app.db.nutritionstore import guarded, same_dish
from app.services.insights import MIN_PATTERN_PAIRS

logger = logging.getLogger(__name__)
MIN_MEALS = 5                       # matched meals with a sensor rise, on each side of the switch
SIMILAR_BAND = 0.5                  # mmol/L: a smaller difference is reported as about the same
WALK_PATTERN = "evening_walk__next_morning_fasting"
DEAD_STATUSES = ("dismissed", "rejected", "retired")
NOT_PLACED = ("other",)             # a meal JEV could not place with confidence is not compared


def _confidence(n: int) -> float:
    return round(min(0.9, 0.4 + 0.02 * n), 2)


def _direction(diff: float) -> str:
    if abs(diff) < SIMILAR_BAND:
        return "same"
    return "lower" if diff < 0 else "higher"


# ----------------------------------------------------------------------------- pure rules
def pattern_is_live(status: str | None) -> bool:
    """Pure rule: a finding the person dismissed, rejected or that was retired is not shown or proposed again."""
    return (status or "open") not in DEAD_STATUSES


def acted_swap_ids(policy_rows: list[dict[str, Any]]) -> list[str]:
    """Pure rule: the lighter dishes the person chose at least once. A dismissed suggestion has no acts and is left out."""
    return [r["arm_key"][len("swap:"):] for r in policy_rows if r["arm_key"].startswith("swap:") and int(r["acts"] or 0) > 0]


def split_by_anchor(meals: list[tuple[datetime, float]], anchor: datetime) -> tuple[list[float], list[float]]:
    """Pure rule: rises before the first time the lighter dish was logged, and from that time on."""
    before = [r for t, r in meals if t < anchor]
    after = [r for t, r in meals if t >= anchor]
    return before, after


def swap_observation(dish: str, kind_label: str, before: list[float], after: list[float]) -> dict[str, Any] | None:
    """Pure rule: the comparison of the rise for this dish kind, or None below 5 meals on either side."""
    if len(before) < MIN_MEALS or len(after) < MIN_MEALS:
        return None
    diff = sum(after) / len(after) - sum(before) / len(before)
    d = _direction(diff)
    nb, na = len(before), len(after)
    if d == "same":
        text = f"After you switched to {dish}, your glucose rise after {kind_label} was about the same (based on {nb} meals before and {na} after). This is an observation from your data, not proof."
    else:
        text = f"After you switched to {dish}, your glucose rose {abs(diff):.1f} mmol/L {'less' if d == 'lower' else 'more'} on average after {kind_label} (based on {nb} meals before and {na} after). This is an observation from your data, not proof."
    return {"dish": dish, "kind": kind_label, "n_before": nb, "n_after": na, "diff": round(diff, 2), "direction": d, "text": text}


def walk_observation(median_delta: float, n_pairs: int) -> dict[str, Any] | None:
    """Pure rule: the evening-walk finding in the Insights wording, or None below the nightly job's minimum of pairs."""
    if n_pairs < MIN_PATTERN_PAIRS:
        return None
    d = _direction(median_delta)
    if d == "same":
        text = f"On mornings after an evening walk, your fasting glucose was about the same (based on {n_pairs} evenings). This is an observation from your data, not proof."
    else:
        text = f"On mornings after an evening walk, your fasting glucose was {abs(median_delta):.1f} mmol/L {d} (based on {n_pairs} evenings). This is an observation from your data, not proof."
    return {"n": n_pairs, "direction": d, "delta": round(median_delta, 2), "text": text}


# ----------------------------------------------------------------------------- reading the rows
def _swap_observations(user_id) -> list[dict[str, Any]]:
    with tx() as c:
        policy = c.execute("select arm_key, acts from nudge_policy where user_id=%s and arm_kind='suggestion' and arm_key like %s", (user_id, "swap:%")).fetchall()
    ids = acted_swap_ids(policy)
    if not ids:
        return []
    with tx() as c:
        dishes = c.execute("select id::text id, name from foods where id::text = any(%s)", (ids,)).fetchall()
        meals = c.execute(
            """select f.food, f.start_at, m.rise_mmol rise from food_logs f join meal_response m on m.food_log_id = f.id
               where f.user_id=%s and f.deleted_at is null and m.rise_mmol is not null order by f.start_at""",
            (user_id,),
        ).fetchall()
    names = [d["name"] for d in dishes]
    types = foodagent.classify_foods([m["food"] for m in meals] + names)
    out = []
    for d in dishes:
        anchor_rows = [m["start_at"] for m in meals if same_dish(m["food"], d["name"])]
        if not anchor_rows:
            continue
        kind = types.get(foodagent.normalise(d["name"]), "other")
        if kind in NOT_PLACED:
            continue
        of_kind = [(m["start_at"], float(m["rise"])) for m in meals if types.get(foodagent.normalise(m["food"]), "other") == kind]
        before, after = split_by_anchor(of_kind, min(anchor_rows))
        o = swap_observation(d["name"], foodagent.TYPE_LABEL.get(kind, kind), before, after)
        if o:
            out.append({**o, "foodId": d["id"], "type": kind})
    return out


def _walk_observation(user_id) -> dict[str, Any] | None:
    with tx() as c:
        rows = c.execute(
            "select pattern_key, n_pairs, median_delta, status from pattern_candidates where user_id=%s and pattern_key=%s order by n_pairs desc",
            (user_id, WALK_PATTERN),
        ).fetchall()
    live = [r for r in rows if pattern_is_live(r["status"]) and r["median_delta"] is not None]
    if not live:
        return None
    return walk_observation(float(live[0]["median_delta"]), int(live[0]["n_pairs"] or 0))


# ----------------------------------------------------------------------------- reflection
def run(user_id, write: bool = False) -> dict[str, Any]:
    """Compute the observations and, with write=True, propose each as a memory fact. Returns a report either way."""
    swaps = _swap_observations(user_id)
    walk = _walk_observation(user_id)
    report: dict[str, Any] = {
        "swaps": [{"dish": o["dish"], "n_before": o["n_before"], "n_after": o["n_after"], "direction": o["direction"]} for o in swaps],
        "walk": {"n": walk["n"], "direction": walk["direction"]} if walk else None,
        "proposals": [],
    }
    items: list[tuple[str, str, dict, str, float, list]] = []
    for o in swaps:
        items.append((f"food.swap.{o['foodId']}", "food_response", {"type": o["type"], "direction": o["direction"]}, o["text"],
                      _confidence(o["n_before"] + o["n_after"]), [{"table": "food_logs", "n_before": o["n_before"], "n_after": o["n_after"]}, {"table": "meal_response", "column": "rise_mmol"}]))
    if walk:
        items.append(("activity.walk.evening_fasting", "routine", {"direction": walk["direction"]}, walk["text"], _confidence(walk["n"]),
                      [{"table": "pattern_candidates", "pattern_key": WALK_PATTERN, "n_pairs": walk["n"]}]))
    for key, cat, value, text, conf, refs in items:
        entry: dict[str, Any] = {"key": key, "statement": text, "confidence": conf, "guard": "not_checked", "result": "dry_run"}
        if write:
            # the guard logs its decision, so it is asked only when a fact is actually proposed
            entry["guard"] = "pass" if guarded(user_id, text, f"glucose_feedback:{key}") else "blocked"
            if entry["guard"] == "pass":
                with tx() as c:
                    entry["result"] = _propose_fact(c, user_id, key, cat, value, text, conf, refs)
                if entry["result"] in ("proposed", "superseded_and_proposed"):
                    audit(user_id, "agent", "memory.fact_proposed", "memory_facts", None, {"key": key, "result": entry["result"]})
        report["proposals"].append(entry)
    return report


def nudges(user_id, now: datetime, have_keys: set[str], max_new: int) -> list[tuple[str, str, str, str, str, datetime]]:
    """Nothing here: the observations are shown in What Smart Health has learned, not as reminders."""
    return []
