"""Nutrition and activity learning, database side (docs/specs/learning-loop.md LL1, LL4, LL5, LL9).

Everything here is code over the person's own data and the Singapore food database. The model writes no numbers and chooses no
food. A nudge text is a fixed template filled with those numbers, and it passes the output guard (frozen JEV questions) before it
is stored. Functions take the user id so the same logic runs on the app's demo user and on Mr Tan's replay.
"""
from __future__ import annotations

import json
import logging
import random
import statistics
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.agents import food as foodagent
from app.core.config import settings
from app.db.logstore import TZ, current_user, tx
from app.llm import jev

logger = logging.getLogger(__name__)
EXPLORE = 0.15  # share of suggestions that are tried even if others look better (spec: 15% exploration)


def _f(v: Any) -> float | None:
    return float(v) if v is not None else None


# ----------------------------------------------------------------------------- learning policy (bandit state)
def policy_try(user_id, kind: str, key: str) -> None:
    with tx() as c:
        c.execute(
            """insert into nudge_policy (user_id, arm_kind, arm_key, tries, last_tried_at) values (%s,%s,%s,1,now())
               on conflict (user_id, arm_kind, arm_key) do update set tries = nudge_policy.tries + 1, last_tried_at = now(), updated_at = now()""",
            (user_id, kind, key),
        )


def policy_act(user_id, kind: str, key: str) -> None:
    with tx() as c:
        c.execute(
            """insert into nudge_policy (user_id, arm_kind, arm_key, tries, acts, last_tried_at) values (%s,%s,%s,1,1,now())
               on conflict (user_id, arm_kind, arm_key) do update set acts = least(nudge_policy.acts + 1, greatest(nudge_policy.tries, nudge_policy.acts + 1)),
                 tries = greatest(nudge_policy.tries, nudge_policy.acts + 1), updated_at = now()""",
            (user_id, kind, key),
        )


def _arm_rates(user_id, kind: str) -> dict[str, tuple[int, int]]:
    with tx() as c:
        rows = c.execute("select arm_key, tries, acts from nudge_policy where user_id=%s and arm_kind=%s", (user_id, kind)).fetchall()
    return {r["arm_key"]: (r["tries"], r["acts"]) for r in rows}


def rank_arms(user_id, kind: str, keys: list[str], rng: random.Random | None = None) -> list[str]:
    """Order options by smoothed act rate; with 15% probability the first place goes to a less-tried option (exploration)."""
    rng = rng or random
    rates = _arm_rates(user_id, kind)
    score = {k: ((rates.get(k, (0, 0))[1] + 1) / (rates.get(k, (0, 0))[0] + 2)) for k in keys}
    ordered = sorted(keys, key=lambda k: score[k], reverse=True)
    if len(ordered) > 1 and rng.random() < EXPLORE:
        least = min(ordered, key=lambda k: rates.get(k, (0, 0))[0])
        ordered.remove(least)
        ordered.insert(0, least)
    return ordered


# ----------------------------------------------------------------------------- guards
def guarded(user_id, text: str, rule: str) -> bool:
    """Run the frozen guard questions on a drafted text. True if it may be shown. Every check is written to guardrail_events."""
    blocked, res = jev.guard_blocks(text)
    verdict = "pass"
    if blocked:
        verdict = "blocked_med_advice" if (res.get("med_advice") is None or (res.get("med_advice") or 0) >= 1 - settings.jev_guard_floor) else (
            "blocked_diagnosis" if (res.get("diagnosis") or 0) >= 1 - settings.jev_guard_floor else ("urgent" if (res.get("urgent") or 0) >= 1 - settings.jev_guard_floor else "blocked_other"))
    try:
        with tx() as c:
            c.execute(
                "insert into guardrail_events (user_id, stage, verdict, rule_id, excerpt) values (%s,'output',%s::guard_verdict,%s,%s)",
                (user_id, verdict, f"{rule}@{jev.GUARD_VERSION}", text[:200]),
            )
    except Exception:
        logger.exception("could not log the guard decision")
    return not blocked


# ----------------------------------------------------------------------------- "Not for me" and closing the loop on swaps
DISMISS_AFTER = 6  # shown this many times and never chosen: stop showing it


def is_excluded(tries: int, acts: int) -> bool:
    """Pure rule: a suggestion shown many times and never chosen, or one the person dismissed, is not shown again."""
    return acts == 0 and tries >= DISMISS_AFTER


def excluded_keys(user_id, kind: str = "suggestion") -> set[str]:
    return {k for k, (t, a) in _arm_rates(user_id, kind).items() if is_excluded(t, a)}


def policy_reject(user_id, kind: str, key: str) -> None:
    """The person said "not for me": the suggestion is hidden from now on, and the learner counts it as tried and not chosen."""
    with tx() as c:
        c.execute(
            """insert into nudge_policy (user_id, arm_kind, arm_key, tries, acts, last_tried_at) values (%s,%s,%s,%s,0,now())
               on conflict (user_id, arm_kind, arm_key) do update set tries = greatest(nudge_policy.tries, %s), acts = 0, updated_at = now()""",
            (user_id, kind, key, DISMISS_AFTER, DISMISS_AFTER),
        )
    from app.agents.trace import audit

    audit(user_id, "user", "suggestion.dismissed", "nudge_policy", None, {"kind": kind, "key": key})


_SAME_NOISE = {"with", "and", "the", "of", "a", "set", "regular", "large", "small", "extra", "plate", "bowl", "home", "no", "less", "more"}


def same_dish(a: str, b: str) -> bool:
    """Pure rule: do two meal names describe the same dish? Used only to see whether the person had the suggested dish. It is never
    used to give a logged meal any numbers."""
    ta = {w for w in foodagent.normalise(a).split() if w not in _SAME_NOISE}
    tb = {w for w in foodagent.normalise(b).split() if w not in _SAME_NOISE}
    if not ta or not tb:
        return False
    # nearly all the words must agree both ways: a cooking word such as "steamed" or "vegetarian" makes it a different dish
    return len(ta & tb) / len(ta | tb) >= 0.75


def swap_outcome(user_id, usual: str, suggested: list[str], anchor: datetime | None = None, days: int = 60) -> dict[str, Any] | None:
    """Did the person have a suggested dish since, and how did it compare with their usual one? Their own logged numbers, and their own
    measured rise when a sensor was worn (needs at least 2 meals of each). Association only, never a cause."""
    with tx() as c:
        if anchor is None:
            anchor = c.execute("select coalesce(max(start_at), now()) a from food_logs where user_id=%s and deleted_at is null", (user_id,)).fetchone()["a"]
        rows = c.execute(
            """select f.food, f.carbs_g, f.protein_g, f.fat_g, f.sodium_mg, m.rise_mmol rise
               from food_logs f left join meal_response m on m.food_log_id = f.id
               where f.user_id=%s and f.deleted_at is null and f.start_at > %s - make_interval(days => %s) and f.start_at <= %s""",
            (user_id, anchor, days, anchor),
        ).fetchall()
    use = [r for r in rows if same_dish(r["food"], usual)]
    sug = [r for r in rows if any(same_dish(r["food"], s) for s in suggested) and not same_dish(r["food"], usual)]
    if not use or not sug:
        return None

    def avg(rs: list[dict], k: str) -> float | None:
        v = [float(r[k]) for r in rs if r[k] is not None]
        return round(sum(v) / len(v), 1) if v else None

    def kcal(rs: list[dict]) -> float | None:
        return foodagent.kcal_from({k: avg(rs, k) for k in ("carbs_g", "protein_g", "fat_g")})

    name = max({r["food"] for r in sug}, key=lambda f: sum(1 for r in sug if r["food"] == f))
    ru, rs_ = [r for r in use if r["rise"] is not None], [r for r in sug if r["rise"] is not None]
    rise = {"usual": avg(ru, "rise"), "swapped": avg(rs_, "rise"), "nUsual": len(ru), "nSwapped": len(rs_)} if len(ru) >= 2 and len(rs_) >= 2 else None
    return {"swapped": name, "nSwapped": len(sug), "nUsual": len(use), "kcal": {"usual": kcal(use), "swapped": kcal(sug)},
            "sodium": {"usual": avg(use, "sodium_mg"), "swapped": avg(sug, "sodium_mg")}, "rise": rise}


def outcome_text(usual: str, o: dict[str, Any]) -> str:
    """The outcome as a fixed template. Honest when nothing changed or it went the other way."""
    s = f"Since then you have had {o['swapped']} {o['nSwapped']} {'time' if o['nSwapped'] == 1 else 'times'}."
    ku, ks = o["kcal"]["usual"], o["kcal"]["swapped"]
    if ku is not None and ks is not None:
        d = round(ks - ku)
        s += f" Your logged meals were about {abs(d):,} kcal {'lower' if d < 0 else 'higher' if d > 0 else 'the same'}"
        nu, ns_ = o["sodium"]["usual"], o["sodium"]["swapped"]
        if nu is not None and ns_ is not None and abs(ns_ - nu) >= 100:
            s += f" and {abs(round(ns_ - nu)):,} mg salt {'lower' if ns_ < nu else 'higher'}"
        s += f" than your {usual}."
    r = o["rise"]
    if r and r["usual"] is not None and r["swapped"] is not None:
        diff = round(r["swapped"] - r["usual"], 1)
        s += f" Your glucose rose {r['swapped']} on average after it, against {r['usual']} after {usual} ({r['nSwapped']} and {r['nUsual']} meals), " + (
            "about the same." if abs(diff) < 0.5 else ("lower, associated with the swap, not proven." if diff < 0 else "higher this time."))
    return s


# ----------------------------------------------------------------------------- food habit (LL4): the memory loop notices, the shelf offers
_MACROS = ("carbs_g", "protein_g", "fat_g", "sugar_g", "fibre_g", "sodium_mg")


def _logged_baseline(rows: list[dict]) -> dict[str, float | None]:
    """The person's own logged average for a set of meal rows (weighted by how often each was eaten). These are the numbers the
    photo model or the person logged; the food database plays no part in them."""
    out: dict[str, float | None] = {}
    for k in _MACROS:
        pairs = [(float(r[k]), int(r["n"])) for r in rows if r[k] is not None]
        out[k] = round(sum(v * n for v, n in pairs) / sum(n for _, n in pairs), 1) if pairs else None
    out["kcal"] = foodagent.kcal_from(out)
    return out


def food_habits(user_id, anchor: datetime | None = None, days: int = 14) -> list[dict[str, Any]]:
    """A type of food the person keeps eating, and lighter dishes to try next time.

    Steps: group the last two weeks of meals by food type (JEV labels each distinct meal name), keep a type eaten at least
    `food_flag_min_meals` times whose logged average is high in calories, salt or sugar, then ask the shelf (the Singapore food
    database) for similar dishes that would save something compared with the person's OWN logged numbers for their usual dish.
    """
    with tx() as c:
        if anchor is None:
            anchor = c.execute("select coalesce(max(start_at), now()) a from food_logs where user_id=%s and deleted_at is null", (user_id,)).fetchone()["a"]
        rows = c.execute(
            """select min(f.food) food, count(*) n, avg(f.carbs_g) carbs_g, avg(f.protein_g) protein_g, avg(f.fat_g) fat_g, avg(f.sugar_g) sugar_g,
                      avg(f.fibre_g) fibre_g, avg(f.sodium_mg) sodium_mg, avg(m.rise_mmol) rise
               from food_logs f left join meal_response m on m.food_log_id = f.id
               where f.user_id=%s and f.deleted_at is null and f.start_at > %s - make_interval(days => %s) and f.start_at <= %s
               group by lower(f.food)""",
            (user_id, anchor, days, anchor),
        ).fetchall()
        med = c.execute("select percentile_cont(0.5) within group (order by rise_mmol) m from meal_response where user_id=%s and rise_mmol is not null", (user_id,)).fetchone()["m"]
    if not rows:
        return []
    types = foodagent.classify_foods([r["food"] for r in rows])
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(types[foodagent.normalise(r["food"])], []).append(r)
    out = []
    for t, rs in groups.items():
        n = sum(int(r["n"]) for r in rs)
        if t in ("vegetables_or_fruit",) or n < settings.food_flag_min_meals:
            continue
        avg = _logged_baseline(rs)
        high = (avg["kcal"] or 0) >= settings.habit_kcal or (avg["sodium_mg"] or 0) >= settings.habit_sodium_mg or (avg["sugar_g"] or 0) >= settings.habit_sugar_g
        if not high:
            continue
        # the dish to offer a swap for: the heaviest one eaten more than once (by the person's own logged calories and salt)
        def load(r):
            b = _logged_baseline([r])
            return (b["kcal"] or 0) / settings.habit_kcal + (b["sodium_mg"] or 0) / settings.habit_sodium_mg

        repeated = [r for r in rs if int(r["n"]) >= 2] or rs
        top = max(repeated, key=load)
        rises = [(float(r["rise"]), int(r["n"])) for r in rs if r["rise"] is not None]
        rise = round(sum(v * k for v, k in rises) / sum(k for _, k in rises), 1) if rises else None
        skip = excluded_keys(user_id)
        alts = [a for a in foodagent.better_alternatives(top["food"], _logged_baseline([top])) if f"swap:{a['foodId']}" not in skip]
        outcome = swap_outcome(user_id, top["food"], [a["name"] for a in alts], anchor)
        out.append({
            "type": t, "label": foodagent.TYPE_LABEL[t], "n": n, "dishes": sorted((r["food"] for r in rs), key=lambda x: x)[:6], "topDish": top["food"], "topDishN": int(top["n"]), "topAvg": {k: v for k, v in _logged_baseline([top]).items()},
            "avg": {k: avg[k] for k in ("kcal", *_MACROS)}, "meanRise": rise, "medianRise": round(float(med), 1) if med is not None else None,
            "alternatives": alts, "outcome": outcome, "outcomeText": outcome_text(top["food"], outcome) if outcome else None,
        })
    out.sort(key=lambda h: (h["avg"]["kcal"] or 0) * h["n"], reverse=True)
    return out


def saving_phrase(alt: dict[str, Any]) -> str:
    """'saves about 230 kcal and 600 mg salt; protein 31 g to 22 g' from the compared numbers. Code, not model."""
    ch = {c["nutrient"]: c for c in alt["changes"]}
    parts = []
    for k, label, unit in (("kcal", "kcal", ""), ("sodium_mg", "mg salt", ""), ("carbs_g", "g carbs", ""), ("sugar_g", "g sugar", "")):
        c = ch.get(k)
        if c and c["change"] < 0 and abs(c["change"]) >= foodagent._MIN_ABS.get(k, 0):
            parts.append(f"{abs(round(c['change'])):,} {label}")
    parts = parts[:3]
    s = ("saves about " + (", ".join(parts[:-1]) + " and " + parts[-1] if len(parts) > 1 else parts[0])) if parts else "is lighter"
    p = ch.get("protein_g")
    if p and abs(p["change"]) >= 3:
        s += f"; protein goes from {round(p['from'])} g to {round(p['to'])} g"
    return s


def habit_text(h: dict[str, Any]) -> str:
    """The habit as a fixed template filled with the person's own logged numbers. Never says a food is bad."""
    a = h["avg"]
    s = f"You have had {h['label']} {h['n']} times in the last 2 weeks, about {round(a['kcal'] or 0):,} kcal and {round(a['sodium_mg'] or 0):,} mg salt each (from your logged meals)."
    if h["alternatives"]:
        alt = h["alternatives"][0]
        t = h["topAvg"]
        s += f" Your {h['topDish']} ({h['topDishN']} times, about {round(t['kcal'] or 0):,} kcal) is the heaviest. Next time, try {alt['name']} instead: it {saving_phrase(alt)}."
    return s


def reflect_habits(user_id, write: bool = False) -> list[dict[str, Any]]:
    """The memory side of the habit loop: propose what the person keeps eating as a memory fact (never activated by the agent).

    The fact value holds the type and the usual dish only, so it is not re-versioned every night as the count moves; the count and
    the average live in the evidence. Rejected facts are not proposed again; a changed usual dish supersedes the old version.
    """
    from app.agents.adherence import _propose_fact

    out = []
    for h in food_habits(user_id):
        text = f"Often eats {h['label']}: {h['n']} meals in the last 2 weeks, about {round(h['avg']['kcal'] or 0):,} kcal each. The heaviest is {h['topDish']}."
        entry: dict[str, Any] = {"key": f"food.habit.{h['type']}", "statement": text, "guard": "pass" if guarded(user_id, text, f"food_habit:{h['type']}") else "blocked", "result": "dry_run"}
        if entry["guard"] == "pass" and write:
            with tx() as c:
                entry["result"] = _propose_fact(
                    c, user_id, entry["key"], "routine", {"type": h["type"], "usual_dish": h["topDish"]}, text, min(0.9, 0.4 + 0.04 * h["n"]),
                    [{"table": "food_logs", "food_type": h["type"], "meals": h["n"], "window_days": 14}],
                )
        out.append(entry)
    return out


# ----------------------------------------------------------------------------- lunch suggestions (LL5)
def lunch_window(user_id) -> tuple[int, int]:
    """Minutes since midnight: (nudge time, window end). Learned from when lunches are logged; default 12:00 to 13:30."""
    with tx() as c:
        rows = c.execute(
            """select (extract(hour from start_at at time zone 'Asia/Singapore') * 60 + extract(minute from start_at at time zone 'Asia/Singapore'))::int m
               from food_logs where user_id=%s and meal_type='lunch' and deleted_at is null order by start_at desc limit 20""",
            (user_id,),
        ).fetchall()
    if len(rows) >= 5:
        med = int(statistics.median(r["m"] for r in rows))
        return max(10 * 60, med - 30), med + 90
    return 12 * 60 - 30, 13 * 60 + 30


def lunch_options(user_id, limit: int = 3, rng: random.Random | None = None) -> list[dict[str, Any]]:
    now = datetime.now(TZ)
    opts: list[dict[str, Any]] = []
    with tx() as c:
        med = c.execute("select percentile_cont(0.5) within group (order by rise_mmol) m from meal_response where user_id=%s and rise_mmol is not null", (user_id,)).fetchone()["m"]
        recent = {r["k"] for r in c.execute("select lower(food) k from food_logs where user_id=%s and deleted_at is null and start_at > now() - interval '2 days'", (user_id,)).fetchall()}
        own = c.execute(
            """select lower(f.food) key, min(f.food) food, count(*) n, avg(m.rise_mmol) rise, avg(f.carbs_g) carbs, avg(f.sodium_mg) sodium
               from food_logs f join meal_response m on m.food_log_id=f.id
               where f.user_id=%s and f.deleted_at is null and f.meal_type='lunch' and f.start_at > now() - interval '60 days' and m.rise_mmol is not null
               group by 1 having count(*) >= 2 order by avg(m.rise_mmol)""",
            (user_id,),
        ).fetchall()
    # tier 1: the person's own lunches with a lower measured rise than their typical meal
    for r in own:
        if med is not None and float(r["rise"]) < float(med) and r["key"] not in recent:
            opts.append({"key": f"own:{r['key']}", "name": r["food"], "source": "own", "why": f"After this lunch your glucose rose {float(r['rise']):.1f} mmol/L on average (you had it {int(r['n'])} times), less than after your typical meal ({float(med):.1f}).",
                         "carbs": _f(r["carbs"]), "sodium": _f(r["sodium"])})
    # tier 0: the habit the memory loop noticed, with a lighter dish to have instead (compared with the person's own logged numbers)
    try:
        habits = food_habits(user_id)
    except Exception:
        logger.exception("food habits unavailable; lunch ideas continue without the swap tier")
        habits = []
    for h in habits:
        for alt in h["alternatives"][:1]:
            opts.append({"key": f"swap:{alt['foodId']}", "name": alt["name"], "source": "swap", "serving": alt["serving"], "grade": alt["sourceGrade"],
                         "why": f"Instead of your usual {h['topDish']}: it {saving_phrase(alt)}.",
                         "carbs": next((c["to"] for c in alt["changes"] if c["nutrient"] == "carbs_g"), None),
                         "sodium": next((c["to"] for c in alt["changes"] if c["nutrient"] == "sodium_mg"), None)})
    # tier 3: no history yet, so general options from the database, clearly labelled as not personal
    if len(opts) < limit:
        with tx() as c:
            rows = c.execute(
                f"select {foodagent._COLS} from foods where source=%s and subgroup in ('Rice-based dishes', 'Noodle/Pasta-based dishes', 'Soup-based dishes') "
                "and kcal between 350 and 600 and carbs_g <= 60 and sodium_mg <= 900 and sodium_mg is not null and protein_g >= 15 and name not ilike '%%raw%%' and 'hawker' = any(flags) "
                "order by (sodium_mg / 900.0 + carbs_g / 60.0 - coalesce(fibre_g, 0) / 10.0) limit 30",
                (foodagent.SOURCE,),
            ).fetchall()
        for r in rows:
            f = foodagent._row(r)
            opts.append({"key": f"db:{f.id}", "name": f.name, "source": "general", "serving": f.serving_desc, "grade": f.source_grade,
                         "why": f"About {round(f.n['carbs_g'])} g carbs and {round(f.n['sodium_mg'])} mg salt per serving. A general idea from the food database, not personalised yet.",
                         "carbs": f.n["carbs_g"], "sodium": f.n["sodium_mg"]})
    gone = excluded_keys(user_id)
    seen, uniq = set(), []
    for o in opts:
        if o["key"] in gone:
            continue
        if o["name"].lower() not in seen:
            seen.add(o["name"].lower())
            uniq.append(o)
    # within a tier the learned act rate decides; 15% of the time a less-tried option goes first
    order = rank_arms(user_id, "suggestion", [o["key"] for o in uniq], rng)
    rank = {k: i for i, k in enumerate(order)}
    tier = {"swap": 0, "own": 1, "general": 2}
    uniq.sort(key=lambda o: (tier[o["source"]], rank[o["key"]]))
    return uniq[:limit]


# ----------------------------------------------------------------------------- salt day: swap first, gentle activity second (LL9)
RED_FLAGS = ("Chest pain", "Confusion", "Fainting", "Breathlessness at rest", "Sudden vision loss")


def walk_allowed(gates: dict[str, bool]) -> bool:
    """Pure rule: the gentle walk prompt is allowed only if no blocking gate is set and it is daytime (docs LL9)."""
    return bool(gates.get("daytime")) and not any(v for k, v in gates.items() if k != "daytime")


def salt_state(user_id, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(TZ)
    today = now.astimezone(TZ).date()
    with tx() as c:
        meals = c.execute(
            """select food, sodium_mg, carbs_g, protein_g, fat_g, sugar_g, fibre_g, end_at from food_logs where user_id=%s and deleted_at is null and sodium_mg is not null
               and (start_at at time zone 'Asia/Singapore')::date=%s order by end_at desc""",
            (user_id, today),
        ).fetchall()
        flags = c.execute("select 1 from clinical_flags where user_id=%s and status='open' and severity in ('urgent','review') limit 1", (user_id,)).fetchone()
        low = c.execute("select 1 from cgm_readings where user_id=%s and recorded_at > %s - interval '2 hours' and glucose_mmol < 3.9 limit 1", (user_id, now)).fetchone()
        sym = c.execute(
            """select symptom_type::text t, note from symptom_logs where user_id=%s and deleted_at is null and occurred_at > %s - interval '3 hours'""",
            (user_id, now),
        ).fetchall()
        sick = c.execute("select note from symptom_logs where user_id=%s and deleted_at is null and (occurred_at at time zone 'Asia/Singapore')::date=%s", (user_id, today)).fetchall()
        moved = c.execute(
            "select 1 from exercise_logs where user_id=%s and deleted_at is null and (start_at at time zone 'Asia/Singapore')::date=%s and end_at - start_at >= interval '10 minutes' limit 1",
            (user_id, today),
        ).fetchone()
    day_total = sum(float(m["sodium_mg"]) for m in meals)
    worst = max(meals, key=lambda m: float(m["sodium_mg"]), default=None)
    gates = {
        "open_flag": bool(flags),
        "recent_low_glucose": bool(low),
        "dizzy_or_shaky": any(s["t"] in ("shaky_sweaty", "dizziness") for s in sym),
        "red_flag_today": any((s["note"] or "").startswith(RED_FLAGS) for s in sick),
        "already_moved": bool(moved),
        "daytime": 7 <= now.astimezone(TZ).hour < 21,
    }
    high_meal = worst is not None and float(worst["sodium_mg"]) >= settings.meal_high_sodium_mg
    high_day = day_total >= settings.day_high_sodium_mg
    mins_since = (now - worst["end_at"]).total_seconds() / 60 if worst else None
    return {"day_total": day_total, "worst": worst, "high": high_meal or high_day, "mins_since": mins_since, "gates": gates, "allowed": walk_allowed(gates)}


def salt_nudge(user_id, now: datetime | None = None) -> dict[str, Any] | None:
    """The activity prompt for a high-salt day, or None. The swap for next time always comes first; the walk is gated."""
    s = salt_state(user_id, now)
    if not s["high"] or s["worst"] is None or s["mins_since"] is None or not (20 <= s["mins_since"] <= 180):
        return None
    worst = s["worst"]
    swap = ""
    base = {k: (float(worst[k]) if worst[k] is not None else None) for k in _MACROS}
    alts = foodagent.better_alternatives(worst["food"], base, limit=1, extra_targets={"sodium_mg"})
    if alts:
        swap = f" Next time, try {alts[0]['name']}: it {saving_phrase(alts[0])}."
    body = f"That meal was high in salt (about {round(float(worst['sodium_mg'])):,} mg).{swap}"
    if s["allowed"]:
        body += " For now, an easy 10-minute walk is a good habit after meals. If you are unsure, check with your doctor."
    return {"title": "A salty meal today" if not s["allowed"] else "A short walk after that meal?", "body": body, "walk": s["allowed"], "gates": s["gates"]}


# ----------------------------------------------------------------------------- the nudges the notification list should hold now
def nutrition_nudges(user_id, have: set[str], meals_today_lunch: int, now: datetime | None = None, max_new: int = 99) -> list[tuple[str, str, str, str, str, datetime]]:
    """(key, kind, title, body, route, valid until) for keys not already stored. Texts are templates, guarded before they are returned."""
    now = now or datetime.now(TZ)
    today = now.astimezone(TZ).date().isoformat()
    out: list[tuple[str, str, str, str, str, datetime]] = []
    mins = now.astimezone(TZ).hour * 60 + now.astimezone(TZ).minute
    start, end = lunch_window(user_id)
    lk = f"lunch-{today}"
    if len(out) < max_new and lk not in have and start <= mins <= end and meals_today_lunch == 0:
        opts = lunch_options(user_id)
        if opts:
            body = "Ideas that suit you: " + ", ".join(o["name"] for o in opts[:3]) + "."
            if guarded(user_id, body, "lunch_ideas"):
                out.append((lk, "nudge", "Lunch ideas for you", body, "E8", now.astimezone(TZ).replace(hour=end // 60 % 24, minute=end % 60, second=0, microsecond=0)))
                for o in opts:
                    policy_try(user_id, "suggestion", o["key"])
    ak = f"activity-{today}"
    if len(out) < max_new and ak not in have:
        n = salt_nudge(user_id, now)
        if n and guarded(user_id, n["body"], "salt_activity"):
            out.append((ak, "nudge", n["title"], n["body"], "F1" if n["walk"] else "E2", now + timedelta(hours=3)))
            if n["walk"]:
                policy_try(user_id, "activity", "walk_after_salty_meal")
    return out
