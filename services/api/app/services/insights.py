"""The Insights tab (docs/specs/prd.md, mockup section C): trends over 7, 30 or 90 days, computed from the person's stored data.

No model is called. Each number is a count, a mean, a median or a share, so it can be checked against the tables by hand. The period
ends on the latest day that has any data (today if there is none), the same rule the doctor report uses, so a loaded demo patient
whose data stops earlier still sees a full period. A finding that compares two things is worded "associated with" and labelled
unverified on the screen; the numbers come from `pattern_candidates`, which the nightly job fills and which needs enough pairs.
"""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import psycopg

from app.core.config import settings

TZ = ZoneInfo("Asia/Singapore")
ALLOWED_DAYS = (7, 30, 90)
LOW, HIGH, VERY_LOW, VERY_HIGH = 3.9, 10.0, 3.0, 13.9
GOAL_MODERATE_MIN, GOAL_STRENGTH = 150, 2
LATE_AFTER_MIN = 60                 # a dose taken more than an hour after its time counts as late (the dose window ends there)
MIN_PATTERN_PAIRS = 5               # prd F10: a finding needs at least 5 matched events
SHORT_NIGHT_H = 6.0
BASELINE_DAYS = 60
SHOWN_MED_DAYS = 30                 # the dose grid stays readable on a phone

EXERCISE_LABELS = {
    "strength": "Strength", "walking": "Walking", "running": "Running", "cycling": "Cycling", "swimming": "Swimming", "hiit": "HIIT",
    "sports": "Sports", "yoga_pilates": "Yoga or Pilates", "stretching_mobility": "Stretching", "dance": "Dance",
    "household_gardening": "Housework or gardening", "other": "Other",
}
MISS_LABELS = {
    "forgot": "Forgot", "away_from_home": "Away from home", "felt_fine": "Felt fine", "ran_out": "Ran out", "side_effects": "Side effects",
    "cost": "Cost", "other": "Other",
}


# ───────────────────────────────────────────────────────────────── small helpers (pure)
def _minutes_rated(rows: list[dict[str, Any]], lo: int, hi: int | None = None) -> float:
    """Minutes of sessions whose effort rating is from lo to hi (hi None: no upper limit). An unrated session (null) counts nowhere."""
    return sum(float(r["mins"]) for r in rows if r["intensity"] is not None and r["intensity"] >= lo and (hi is None or r["intensity"] <= hi))


def _f(x: Any) -> float | None:
    return None if x is None else float(x)


def _r1(x: float | None) -> float | None:
    return None if x is None else round(x, 1)


def _mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def _median(xs: list[float]) -> float | None:
    return statistics.median(xs) if xs else None


def _percentile(xs: list[float], p: float) -> float:
    s = sorted(xs)
    k = (len(s) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def _short(d: date) -> str:
    return f"{d.day} {d.strftime('%b')}"


def _label(start: date, end: date, days: int) -> str:
    return f"{_short(start)} to {_short(end)} {end.year} ({days} days)"


def window(end: date, days: int) -> tuple[date, date]:
    return end - timedelta(days=days - 1), end


def band_pcts(values: list[float], low: float = LOW, high: float = HIGH) -> list[dict[str, Any]]:
    """Share of readings in each band. Edges: below very low, very low to low, low to high (in range), high to very high, above."""
    n = len(values)

    def pct(k: int) -> float:
        return round(100.0 * k / n, 1) if n else 0.0

    return [
        {"key": "very_high", "label": f"Very high, above {VERY_HIGH}", "pct": pct(sum(v > VERY_HIGH for v in values))},
        {"key": "high", "label": f"High, {high} to {VERY_HIGH}", "pct": pct(sum(high < v <= VERY_HIGH for v in values))},
        {"key": "in_range", "label": f"In range, {low} to {high}", "pct": pct(sum(low <= v <= high for v in values))},
        {"key": "low", "label": f"Low, {VERY_LOW} to {low}", "pct": pct(sum(VERY_LOW <= v < low for v in values))},
        {"key": "very_low", "label": f"Very low, below {VERY_LOW}", "pct": pct(sum(v < VERY_LOW for v in values))},
    ]


def glucose_metrics(values: list[float], days: int) -> dict[str, Any]:
    n = len(values)
    if not n:
        return {"mean": None, "gmi": None, "cv": None, "coverage": None, "readings": 0}
    mean = sum(values) / n
    sd = statistics.pstdev(values) if n > 1 else 0.0
    return {
        "mean": _r1(mean),
        "gmi": _r1(3.31 + 0.02392 * (mean * 18.0182)),
        "cv": round(100.0 * sd / mean) if mean else None,
        "coverage": min(100.0, round(100.0 * n / (days * 288), 0)),
        "readings": n,
    }


def drift_weeks(weekly_fasting: list[float | None], p75: float) -> int:
    """How many of the most recent weeks, counted back without a break, had a median fasting glucose above the person's usual range."""
    weeks = 0
    for v in reversed(weekly_fasting):
        if v is None or v <= p75:
            break
        weeks += 1
    return weeks


def food_responses(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Group meal responses by food. Foods seen at least twice are ranked gentlest to spikiest by the median rise; foods seen once are
    only listed as still learning (prd F8: fewer than 2 observations are not ranked)."""
    by: dict[str, list[float]] = defaultdict(list)
    names: dict[str, Counter[str]] = defaultdict(Counter)
    for r in rows:
        if r.get("rise") is None or not r.get("food"):
            continue
        key = " ".join(str(r["food"]).lower().split())
        by[key].append(float(r["rise"]))
        names[key][str(r["food"]).strip()] += 1
    ranked, learning = [], []
    for key, rises in by.items():
        name = names[key].most_common(1)[0][0]
        if len(rises) >= 2:
            ranked.append({"name": name, "n": len(rises), "median_rise": round(statistics.median(rises), 1), "low": round(min(rises), 1), "high": round(max(rises), 1)})
        else:
            learning.append(name)
    ranked.sort(key=lambda x: (x["median_rise"], x["name"]))
    return ranked, sorted(learning)


def dose_cell(statuses: list[dict[str, Any]], now: datetime) -> str:
    """One day's cell for one medicine: the worst thing that happened that day. missed, then unconfirmed, then late, then taken."""
    if not statuses:
        return "none"
    kinds = set()
    for s in statuses:
        st, sched, taken = s["status"], s["scheduled_at"], s["taken_at"]
        if st == "taken":
            late = sched and taken and (taken - sched) > timedelta(minutes=LATE_AFTER_MIN)
            kinds.add("late" if late else "taken")
        elif st == "missed":
            kinds.add("missed")
        elif sched and sched < now - timedelta(minutes=LATE_AFTER_MIN):
            kinds.add("unconfirmed")        # the window has passed and nobody answered
        # a dose still to come is not shown
    for k in ("missed", "unconfirmed", "late", "taken"):
        if k in kinds:
            return k
    return "none"


# ── The day grid (the overview calendar) ──
def _level(row: str, v: float | None) -> int:
    if v is None:
        return 0
    cuts = {
        "glucose": (40, 55, 70),          # percent of the day in range
        "meals": (1, 2, 3),               # meals logged
        "activity": (15, 30, 45),         # active minutes
        "sleep": (5.5, 6.5, 7.5),         # hours
        "stress": (1.5, 2.5, 3.5),        # 1 to 5 self rating
        "doses": (50, 75, 100),           # percent of doses taken
    }[row]
    if row == "meals":
        return 0 if v == 0 else min(4, int(v))
    if row == "activity" and v == 0:
        return 0
    return 1 + sum(v >= c for c in cuts) if row != "stress" else 1 + sum(v > c for c in cuts)


def measure_grid(daily: dict[date, dict[str, Any]], days: list[date], logged: dict[str, dict[date, float]]) -> list[dict[str, Any]]:
    """One cell per day for each measure. A day with no stored value is a dash (no data), never zero.

    Meals and active minutes come from the logs (`logged`: date to count or minutes, only for days with a log), because the stored
    daily row carries a 0 for every day, logged or not. So a day with no meal log is a dash, and a day whose logged workouts add to
    zero minutes is a real 0."""
    def from_row(column: str) -> Any:
        return lambda d, row: _f(row.get(column))

    def from_log(key: str) -> Any:
        return lambda d, row: _f(logged.get(key, {}).get(d))

    spec = [
        ("glucose", lambda d, row: _f(row.get("tir_pct")), lambda v: f"{v:.0f}%"),
        ("meals", from_log("meals"), lambda v: f"{v:.0f}"),
        ("activity", from_log("activity"), lambda v: f"{v:.0f}"),
        ("sleep", from_row("sleep_hours"), lambda v: f"{v:.1f}"),
        ("stress", from_row("stress_self_avg"), lambda v: f"{v:.1f}"),
        ("doses", lambda d, row: (100.0 * row["doses_taken"] / row["doses_scheduled"]) if row.get("doses_scheduled") else None, lambda v: f"{v:.0f}%"),
    ]
    rows = []
    for key, get, fmt in spec:
        cells = []
        for d in days:
            v = get(d, daily.get(d, {}))
            cells.append({"date": d.isoformat(), "value": _r1(v), "label": "–" if v is None else fmt(v), "level": _level(key, v)})
        rows.append({"key": key, "cells": cells})
    return rows


# ── "What changed" ──
CHANGE_RULES: list[tuple[str, str, str, Any]] = [
    # id, screen the line opens, unit (the screen writes the words), moved when ...
    ("tir", "C2", "points", lambda c, p: abs(c - p) >= 5),
    ("fasting", "C2", "mmol", lambda c, p: abs(c - p) >= 0.5),
    ("steps", "C4", "steps", lambda c, p: abs(c - p) >= 0.15 * p if p else abs(c - p) > 0),
    ("exercise", "C4", "minutes", lambda c, p: abs(c - p) >= 20 and (abs(c - p) >= 0.3 * p if p else True)),
    ("sleep", "C5", "hours", lambda c, p: abs(c - p) >= 0.5),
    ("stress", "C5", "score", lambda c, p: abs(c - p) >= 0.5),
    ("doses", "C6", "points", lambda c, p: abs(c - p) >= 10),
]


def changes(cur: dict[str, float | None], prev: dict[str, float | None]) -> list[dict[str, Any]]:
    """Every measure against the same number of days before, with the direction it moved. A measure with no value in either
    period is "none" and is never called unchanged. The screen writes the sentence, so it names both ranges and never says good or bad."""
    out = []
    for key, to, unit, moved in CHANGE_RULES:
        c, p = cur.get(key), prev.get(key)
        if c is None or p is None:
            direction = "none"
        elif not moved(c, p):
            direction = "same"
        else:
            direction = "up" if c > p else "down"
        out.append({
            "id": key, "to": to, "unit": unit, "direction": direction,
            "current": _r1(c), "previous": _r1(p), "delta": _r1(c - p) if c is not None and p is not None else None,
        })
    return out


# ── Findings from pattern_candidates ──
PATTERN_ROUTE = {
    "high_stress_day__hrv": "C5", "sweet_drink__rise": "C3", "missed_evening_dose__post_dinner_rise": "C6",
    "evening_walk__next_morning_fasting": "C4", "high_carb_meal__rise": "C3", "short_sleep__fasting_glucose": "C5",
}


def pattern_text(key: str, delta: float) -> str | None:
    d = abs(delta)
    hi = delta > 0
    if key == "evening_walk__next_morning_fasting":
        return f"On mornings after an evening walk, your fasting glucose was {d:.1f} mmol/L {'higher' if hi else 'lower'}."
    if key == "short_sleep__fasting_glucose":
        return f"After nights of under 6 hours of sleep, your fasting glucose was {d:.1f} mmol/L {'higher' if hi else 'lower'}."
    if key == "high_carb_meal__rise":
        return f"Meals with 60 g or more of net carbohydrate had a glucose rise {d:.1f} mmol/L {'bigger' if hi else 'smaller'} than meals under 40 g."
    if key == "sweet_drink__rise":
        return f"After sweet drinks, your glucose rose {d:.1f} mmol/L {'more' if hi else 'less'} than after other meals."
    if key == "missed_evening_dose__post_dinner_rise":
        return f"On days the evening dose was missed, the rise after dinner was {d:.1f} mmol/L {'bigger' if hi else 'smaller'}."
    if key == "high_stress_day__hrv":
        return f"On high-stress days, your overnight heart-rate variability was {d:.0f} ms {'higher' if hi else 'lower'}."
    return None


def patterns_for(rows: list[dict[str, Any]], tab: str | None = None) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        if int(r["n_pairs"] or 0) < MIN_PATTERN_PAIRS or r["median_delta"] is None:
            continue
        text = pattern_text(r["pattern_key"], float(r["median_delta"]))
        to = PATTERN_ROUTE.get(r["pattern_key"])
        if text and to and (tab is None or to == tab):
            out.append({"key": r["pattern_key"], "text": text, "n": int(r["n_pairs"]), "to": to})
    return out


# ───────────────────────────────────────────────────────────────── reading the rows
def anchor(conn: psycopg.Connection[Any], user: str, today: date) -> date:
    r = conn.execute(
        """select max(local_date) d from daily_summary where user_id=%s and local_date<=%s and
           (glucose_mean_mmol is not null or meals_n>0 or exercise_sessions_n>0 or doses_scheduled>0 or mood_avg is not null or steps_total is not null)""",
        (user, today),
    ).fetchone()
    return (r["d"] if r and r["d"] else today)


def _period(end: date, days: int, has_data: bool) -> dict[str, Any]:
    start, end = window(end, days)
    return {"start": start.isoformat(), "end": end.isoformat(), "days": days, "label": _label(start, end, days), "has_data": has_data}


def _daily(conn: psycopg.Connection[Any], user: str, lo: date, hi: date) -> dict[date, dict[str, Any]]:
    rows = conn.execute("select * from daily_summary where user_id=%s and local_date between %s and %s", (user, lo, hi)).fetchall()
    return {r["local_date"]: dict(r) for r in rows}


def _fasting(conn: psycopg.Connection[Any], user: str, lo: date, hi: date) -> dict[date, float]:
    """Glucose 05:00 to 07:00 local, the same definition the nightly job uses for its findings."""
    rows = conn.execute(
        """select (recorded_at at time zone 'Asia/Singapore')::date d, avg(glucose_mmol) g from cgm_readings
           where user_id=%s and quality_ok and recorded_at >= %s and recorded_at < %s
             and extract(hour from recorded_at at time zone 'Asia/Singapore') in (5, 6) group by 1""",
        (user, datetime.combine(lo, datetime.min.time(), TZ), datetime.combine(hi + timedelta(days=1), datetime.min.time(), TZ)),
    ).fetchall()
    return {r["d"]: float(r["g"]) for r in rows}


def _patterns(conn: psycopg.Connection[Any], user: str) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute(
        "select pattern_key, n_pairs, median_delta from pattern_candidates where user_id=%s and status not in ('dismissed','rejected','retired') order by n_pairs desc", (user,))]


def _bounds(d: date) -> tuple[datetime, datetime]:
    return datetime.combine(d, datetime.min.time(), TZ), datetime.combine(d + timedelta(days=1), datetime.min.time(), TZ)


def _targets(conn: psycopg.Connection[Any], user: str) -> tuple[float, float]:
    p = conn.execute("select glucose_target_low, glucose_target_high from user_profile where user_id=%s", (user,)).fetchone()
    lo = float(p["glucose_target_low"]) if p and p["glucose_target_low"] is not None else LOW
    hi = float(p["glucose_target_high"]) if p and p["glucose_target_high"] is not None else HIGH
    return lo, hi


def _cgm(conn: psycopg.Connection[Any], user: str, start: date, end: date) -> list[float]:
    lo, hi = _bounds(start)[0], _bounds(end)[1]
    return [float(r["g"]) for r in conn.execute(
        "select glucose_mmol g from cgm_readings where user_id=%s and quality_ok and recorded_at >= %s and recorded_at < %s", (user, lo, hi))]


def _avg(daily: dict[date, dict[str, Any]], col: str, lo: date, hi: date) -> float | None:
    return _mean([float(v[col]) for d, v in daily.items() if lo <= d <= hi and v.get(col) is not None])


# ───────────────────────────────────────────────────────────────── the screens
def overview(conn: psycopg.Connection[Any], user: str, days: int, today: date) -> dict[str, Any]:
    end = anchor(conn, user, today)
    start, _ = window(end, days)
    p_start, p_end = window(start - timedelta(days=1), days)
    daily = _daily(conn, user, p_start, end)
    fasting = _fasting(conn, user, p_start, end)
    in_cur = {d: v for d, v in daily.items() if start <= d <= end}
    has = any(v.get("glucose_mean_mmol") is not None or v.get("meals_n") or v.get("exercise_sessions_n") or v.get("doses_scheduled") or v.get("mood_avg") is not None for v in in_cur.values())

    def agg(lo: date, hi: date) -> dict[str, float | None]:
        taken = sum(v["doses_taken"] or 0 for d, v in daily.items() if lo <= d <= hi)
        sched = sum(v["doses_scheduled"] or 0 for d, v in daily.items() if lo <= d <= hi)
        f = [g for d, g in fasting.items() if lo <= d <= hi]
        return {
            "fasting": _mean(f) if len(f) >= 3 else None, "tir": _avg(daily, "tir_pct", lo, hi), "steps": _avg(daily, "steps_total", lo, hi),
            "exercise": float(sum(v["exercise_min"] or 0 for d, v in daily.items() if lo <= d <= hi)) if any(lo <= d <= hi for d in daily) else None,
            "sleep": _avg(daily, "sleep_hours", lo, hi), "stress": _avg(daily, "stress_self_avg", lo, hi), "doses": (100.0 * taken / sched) if sched else None,
        }

    return {
        "period": _period(end, days, has),
        "changes": changes(agg(start, end), agg(p_start, p_end)) if has else [],
        "patterns": patterns_for(_patterns(conn, user))[:3],
    }


MAX_DAY_RANGE = 92


def _logged_per_day(conn: psycopg.Connection[Any], user: str, lo: date, hi: date) -> dict[str, dict[date, float]]:
    """Meals logged (count) and workout minutes (sum) per local day, only for days that have a log."""
    lo_b, hi_b = _bounds(lo)[0], _bounds(hi)[1]
    meals = conn.execute(
        """select (start_at at time zone 'Asia/Singapore')::date d, count(*) n from food_logs
           where user_id=%s and deleted_at is null and start_at >= %s and start_at < %s group by 1""", (user, lo_b, hi_b)).fetchall()
    workouts = conn.execute(
        """select (start_at at time zone 'Asia/Singapore')::date d, coalesce(sum(extract(epoch from end_at - start_at)/60), 0) mins from exercise_logs
           where user_id=%s and deleted_at is null and start_at >= %s and start_at < %s group by 1""", (user, lo_b, hi_b)).fetchall()
    return {"meals": {r["d"]: float(r["n"]) for r in meals}, "activity": {r["d"]: float(round(float(r["mins"]))) for r in workouts}}


def overview_days(conn: psycopg.Connection[Any], user: str, lo: date, hi: date, today: date) -> dict[str, Any]:
    """The overview calendar: one cell per day, from `lo` to `hi`. Days after today are never returned (no future data)."""
    hi = min(hi, today)
    days = [lo + timedelta(days=i) for i in range((hi - lo).days + 1)] if lo <= hi else []
    daily = _daily(conn, user, lo, hi) if days else {}
    logged = _logged_per_day(conn, user, lo, hi) if days else {}
    return {"start": lo.isoformat(), "end": hi.isoformat(), "today": today.isoformat(), "rows": measure_grid(daily, days, logged)}


def glucose(conn: psycopg.Connection[Any], user: str, days: int, today: date) -> dict[str, Any]:
    end = anchor(conn, user, today)
    start, _ = window(end, days)
    low, high = _targets(conn, user)
    values = _cgm(conn, user, start, end)
    daily = _daily(conn, user, start, end)
    fasting_all = _fasting(conn, user, start - timedelta(days=BASELINE_DAYS), end)
    prior = [g for d, g in fasting_all.items() if d < start]
    baseline = ({"p25": round(_percentile(prior, 0.25), 1), "p50": round(_percentile(prior, 0.5), 1), "p75": round(_percentile(prior, 0.75), 1), "n": len(prior)} if len(prior) >= 7 else None)
    drift = None
    if baseline:
        weekly: list[float | None] = []
        for k in range(5, -1, -1):                      # six weeks, oldest first, ending at the period end
            hi_d = end - timedelta(days=7 * k)
            w = [g for d, g in fasting_all.items() if hi_d - timedelta(days=6) <= d <= hi_d]
            weekly.append(statistics.median(w) if len(w) >= 3 else None)
        n = drift_weeks(weekly, baseline["p75"])
        if n >= 2:
            drift = {"weeks": n, "text": f"Your morning glucose has been above your usual range for about {n} weeks."}
    series = [{"date": d.isoformat(), "mean": _r1(_f(daily.get(d, {}).get("glucose_mean_mmol"))), "tir": _r1(_f(daily.get(d, {}).get("tir_pct"))),
               "fasting": _r1(fasting_all.get(d))} for d in (start + timedelta(days=i) for i in range(days))]
    ev = conn.execute(
        """select count(*) filter (where event_type::text='spike') sp, count(*) filter (where event_type::text='low') lw,
                  count(*) filter (where event_type::text='sustained_high') sh from glucose_events where user_id=%s and started_at >= %s and started_at < %s""",
        (user, _bounds(start)[0], _bounds(end)[1])).fetchone()
    return {
        "period": _period(end, days, bool(values)), "has_data": bool(values), "bands": band_pcts(values, low, high), "days": series, "baseline": baseline, "drift": drift,
        "metrics": glucose_metrics(values, days), "events": {"spikes": ev["sp"], "lows": ev["lw"], "sustained_high": ev["sh"]}, "low": low, "high": high,
        "patterns": patterns_for(_patterns(conn, user), "C2"),
    }


def food(conn: psycopg.Connection[Any], user: str, days: int, today: date) -> dict[str, Any]:
    end = anchor(conn, user, today)
    start, _ = window(end, days)
    lo, hi = _bounds(start)[0], _bounds(end)[1]
    rows = conn.execute(
        """select f.id, f.start_at, f.food, f.meal_type::text mt, f.carbs_g, f.protein_g, f.fat_g, f.sugar_g, f.sodium_mg, m.rise_mmol
           from food_logs f left join meal_response m on m.food_log_id = f.id
           where f.user_id=%s and f.deleted_at is null and f.start_at >= %s and f.start_at < %s order by f.start_at desc""", (user, lo, hi)).fetchall()
    daily = _daily(conn, user, start, end)

    def kcal(r: dict[str, Any]) -> int | None:
        if r["carbs_g"] is None or r["protein_g"] is None or r["fat_g"] is None:
            return None
        return round(4 * float(r["carbs_g"]) + 4 * float(r["protein_g"]) + 9 * float(r["fat_g"]))

    meals, salt, sugar = [], 0, 0
    for r in rows:
        flags = []
        if r["sodium_mg"] is not None and float(r["sodium_mg"]) >= settings.meal_high_sodium_mg:
            flags.append("high_salt")
            salt += 1
        if r["sugar_g"] is not None and float(r["sugar_g"]) >= settings.meal_high_sugar_g:
            flags.append("high_sugar")
            sugar += 1
        if len(meals) < 15:
            when = r["start_at"].astimezone(TZ)
            meals.append({"id": str(r["id"]), "when": f"{_short(when.date())}, {when.strftime('%I:%M %p').lstrip('0').lower()}", "name": r["food"], "meal_type": r["mt"],
                          "kcal": kcal(r), "carbs_g": _f(r["carbs_g"]), "sugar_g": _f(r["sugar_g"]), "sodium_mg": _f(r["sodium_mg"]), "flags": flags, "rise": _r1(_f(r["rise_mmol"]))})
    ranked, learning = food_responses([{"food": r["food"], "rise": r["rise_mmol"]} for r in rows])
    with_meals = [v for v in daily.values() if (v.get("meals_n") or 0) > 0]
    kc = [4 * float(v["carbs_g"] or 0) + 4 * float(v["protein_g"] or 0) + 9 * float(v["fat_g"] or 0) for v in with_meals]
    so = [float(v["sodium_mg"]) for v in with_meals if v.get("sodium_mg") is not None]
    return {
        "period": _period(end, days, bool(rows)),
        "totals": {"meals": len(rows), "avg_kcal_per_day": round(_mean(kc)) if kc else None, "avg_sodium_per_day": round(_mean(so)) if so else None, "high_salt_meals": salt, "high_sugar_meals": sugar},
        "meals": meals, "responses": ranked, "still_learning": learning[:8], "patterns": patterns_for(_patterns(conn, user), "C3"),
    }


def activity(conn: psycopg.Connection[Any], user: str, days: int, today: date) -> dict[str, Any]:
    end = anchor(conn, user, today)
    start, _ = window(end, days)
    wk_start = end - timedelta(days=end.weekday())
    four = wk_start - timedelta(weeks=3)
    rows = conn.execute(
        """select e.id, e.start_at, e.type::text t, e.intensity, extract(epoch from e.end_at - e.start_at)/60 mins, r.glucose_pre_mmol pre, r.glucose_2h_mmol g2
           from exercise_logs e left join exercise_response r on r.exercise_log_id = e.id
           where e.user_id=%s and e.deleted_at is null and e.start_at >= %s and e.start_at < %s order by e.start_at desc""",
        (user, _bounds(min(start, four))[0], _bounds(end)[1])).fetchall()
    for r in rows:
        r["d"] = r["start_at"].astimezone(TZ).date()
    wk = [r for r in rows if r["d"] >= wk_start]
    weeks = []
    for k in range(3, -1, -1):
        ws = wk_start - timedelta(weeks=k)
        inw = [r for r in rows if ws <= r["d"] < ws + timedelta(days=7)]
        weeks.append({"label": f"Week of {_short(ws)}",
                      "light": round(_minutes_rated(inw, 1, 2)), "moderate": round(_minutes_rated(inw, 3, 3)),
                      "vigorous": round(_minutes_rated(inw, 4))})
    inp = [r for r in rows if start <= r["d"] <= end]
    mix: dict[str, dict[str, Any]] = {}
    for r in inp:
        m = mix.setdefault(r["t"], {"type": r["t"], "label": EXERCISE_LABELS.get(r["t"], r["t"]), "count": 0, "minutes": 0})
        m["count"] += 1
        m["minutes"] += round(float(r["mins"]))
    workouts = [{"id": str(r["id"]), "date": _short(r["d"]), "label": EXERCISE_LABELS.get(r["t"], r["t"]), "type": r["t"], "intensity": r["intensity"], "minutes": round(float(r["mins"])),
                 "glucose_change_2h": _r1(float(r["g2"]) - float(r["pre"])) if r["g2"] is not None and r["pre"] is not None else None} for r in inp[:8]]
    base_lo = start - timedelta(days=BASELINE_DAYS)
    daily = _daily(conn, user, base_lo, end)
    steps = [{"date": (start + timedelta(days=i)).isoformat(), "steps": (int(daily[d]["steps_total"]) if (d := start + timedelta(days=i)) in daily and daily[d].get("steps_total") is not None else None)} for i in range(days)]
    s_in = [s["steps"] for s in steps if s["steps"] is not None]
    s_prior = [float(v["steps_total"]) for d, v in daily.items() if d < start and v.get("steps_total") is not None]
    return {
        "period": _period(end, days, bool(inp) or bool(s_in)),
        "moderate_min": round(_minutes_rated(wk, 3)), "moderate_goal": GOAL_MODERATE_MIN,
        "strength": sum(r["t"] == "strength" for r in wk), "strength_goal": GOAL_STRENGTH,
        "weeks": weeks, "mix": sorted(mix.values(), key=lambda m: -m["count"]), "workouts": workouts,
        "steps": steps, "steps_avg": round(_mean([float(s) for s in s_in])) if s_in else None, "steps_baseline": round(statistics.median(s_prior)) if len(s_prior) >= 7 else None,
        "patterns": patterns_for(_patterns(conn, user), "C4"),
    }


def sleep(conn: psycopg.Connection[Any], user: str, days: int, today: date) -> dict[str, Any]:
    end = anchor(conn, user, today)
    start, _ = window(end, days)
    daily = _daily(conn, user, start - timedelta(days=BASELINE_DAYS), end)
    series = []
    for i in range(days):
        d = start + timedelta(days=i)
        v = daily.get(d, {})
        series.append({"date": d.isoformat(), "hours": _r1(_f(v.get("sleep_hours"))), "mood": _r1(_f(v.get("mood_avg"))), "stress": _r1(_f(v.get("stress_self_avg"))), "energy": _r1(_f(v.get("energy_avg")))})
    hours = [s["hours"] for s in series if s["hours"] is not None]
    stress = [s["stress"] for s in series if s["stress"] is not None]
    mood = [s["mood"] for s in series if s["mood"] is not None]
    prior = [float(v["sleep_hours"]) for d, v in daily.items() if d < start and v.get("sleep_hours") is not None]
    return {
        "period": _period(end, days, bool(hours) or bool(stress)), "days": series, "sleep_avg": _r1(_mean(hours)), "sleep_baseline": _r1(_mean(prior)) if len(prior) >= 7 else None,
        "short_nights": sum(h < SHORT_NIGHT_H for h in hours), "stress_avg": _r1(_mean(stress)), "mood_avg": _r1(_mean(mood)), "high_stress_days": sum(s >= 4 for s in stress), "logged_days": len(stress),
        "patterns": patterns_for(_patterns(conn, user), "C5"),
    }


def medication(conn: psycopg.Connection[Any], user: str, days: int, today: date, now: datetime) -> dict[str, Any]:
    end = anchor(conn, user, today)
    start, _ = window(end, days)
    shown = min(days, SHOWN_MED_DAYS)
    dates = [start + timedelta(days=days - shown + i) for i in range(shown)]
    meds = [dict(r) for r in conn.execute(
        "select id, name, frequency, kind::text kind from medications where user_id=%s and deleted_at is null and not coalesce(as_needed, false) order by name", (user,))]
    logs = conn.execute(
        """select medication_id, scheduled_at, taken_at, status::text status, miss_reason::text reason from medication_log
           where user_id=%s and coalesce(scheduled_at, taken_at) >= %s and coalesce(scheduled_at, taken_at) < %s""", (user, _bounds(start)[0], _bounds(end)[1])).fetchall()
    prescribed = {m["id"] for m in meds if m["kind"] == "prescription"}      # adherence and reasons count prescription medicines only
    by: dict[Any, dict[date, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    reasons: Counter[str] = Counter()
    for r in logs:
        d = (r["scheduled_at"] or r["taken_at"]).astimezone(TZ).date()
        by[r["medication_id"]][d].append(dict(r))
        if r["status"] == "missed" and r["reason"] and r["medication_id"] in prescribed:
            reasons[r["reason"]] += 1
    rows, taken_all, missed_all, sched_all, unconf_all = [], 0, 0, 0, 0
    for m in meds:
        per = by.get(m["id"], {})
        flat = [x for v in per.values() for x in v]
        if not flat:
            continue
        counts = m["id"] in prescribed
        taken = sum(x["status"] == "taken" for x in flat)
        missed = sum(x["status"] == "missed" for x in flat)
        unconf = sum(x["status"] == "pending" and bool(x["scheduled_at"]) and x["scheduled_at"] < now - timedelta(minutes=LATE_AFTER_MIN) for x in flat)
        scheduled = taken + missed + unconf
        if counts:
            taken_all += taken
            missed_all += missed
            sched_all += scheduled
            unconf_all += unconf
        # No percent until a dose has been answered (taken or missed): 0 of 3 with nothing answered is "not confirmed yet", not 0%.
        rows.append({"id": str(m["id"]), "name": m["name"], "regimen": {1: "Once a day", 2: "Twice a day", 3: "Three times a day"}.get(m["frequency"], f"{m['frequency']} times a day" if m["frequency"] else "As scheduled"),
                     "counted": counts, "taken": taken if counts else None, "missed": missed if counts else None,
                     "unconfirmed": unconf if counts else None, "scheduled": scheduled if counts else None,
                     "adherence_pct": round(100 * taken / scheduled) if counts and taken + missed else None,
                     "cells": [dose_cell(per.get(d, []), now) for d in dates]})
    return {
        "period": _period(end, days, bool(rows)), "dates": [d.isoformat() for d in dates], "meds": rows,
        "taken": taken_all, "missed": missed_all, "scheduled": sched_all, "unconfirmed": unconf_all,
        "adherence_pct": round(100 * taken_all / sched_all) if sched_all and taken_all + missed_all else None,
        "reasons": [{"key": k, "label": MISS_LABELS.get(k, k), "count": c} for k, c in reasons.most_common()],
        "patterns": patterns_for(_patterns(conn, user), "C6"), "shown_days": shown,
    }


def sensor_run(conn: psycopg.Connection[Any], user: str, today: date) -> dict[str, Any]:
    """C8. There is no stored "sprint" yet (the sensor connection is not built), so this summarises the last 14 days of sensor data."""
    end = anchor(conn, user, today)
    start, _ = window(end, 14)
    values = _cgm(conn, user, start, end)
    low, high = _targets(conn, user)
    daily = _daily(conn, user, start, end)
    worn = sum(1 for v in daily.values() if (v.get("cgm_coverage_pct") or 0) >= 50)
    rows = conn.execute(
        """select f.food, m.rise_mmol rise from food_logs f join meal_response m on m.food_log_id=f.id
           where f.user_id=%s and f.deleted_at is null and f.start_at >= %s and f.start_at < %s""", (user, _bounds(start)[0], _bounds(end)[1])).fetchall()
    ranked, _ = food_responses([dict(r) for r in rows])
    pick = lambda xs: [{"name": x["name"], "median_rise": x["median_rise"], "n": x["n"]} for x in xs[:3]]
    return {
        "period": _period(end, 14, bool(values)), "status": "none" if not values else ("complete" if worn >= 10 else "partial"), "days_worn": worn, "of": 14,
        "metrics": glucose_metrics(values, 14), "bands": band_pcts(values, low, high), "gentlest": pick(ranked), "spikiest": pick(list(reversed(ranked))),
    }
