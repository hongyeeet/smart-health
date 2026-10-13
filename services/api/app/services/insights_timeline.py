"""The Insights overview timeline (GET /insights/timeline?days=7|30|90): the person's glucose, heart rate, SpO2, blood pressure, steps and logs
laid on ONE shared time axis, so a marker that moves along it can read every chart at the same moment.

Everything is read from `timeline_5min` (the Gold 5-minute table), averaged into buckets (7 days: 30 minutes; 30 and 90 days: a day).
Times in the answer are minutes since local midnight of the first day (`m`), so the screen needs no clock maths.

The BASELINE is the person's own average for each hour of the day over the 60 days before the period (24 numbers per measure), and one fixed
number for blood pressure (readings are too few to split by hour). The USUAL range is the middle half (25th to 75th percentile) of the same
hours. A baseline needs at least MIN_BASELINE_DAYS days behind it; with fewer days before the period it is the first 30 days of the period
(`source` says which), and with fewer than that it is unavailable and the screen says so. `compare` sets the period's average and its most
recent days against the baseline and gives a slope per week, so a drift is visible; it is a number, never a verdict.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import psycopg

from app.services import day as D
from app.services import insights as base

STEP_MIN = {7: 30, 30: 1440, 90: 1440}   # 7 days: every half hour; 30 and 90 days: one point a day, so a drift is easy to see
FIRST_DAYS = 30                  # with too few days before the period, the baseline is the first 30 days of the period
BASELINE_DAYS = 60
MIN_BASELINE_DAYS = 7
MIN_BP_READINGS = 3
MEAL_GAP_MIN = 30
EXERCISE_GAP_MIN = 10


def _r(x: Any, n: int = 2) -> float | None:
    return None if x is None else round(float(x), n)


# ───────────────────────────────────────────────────────────────── pure helpers (tested)
def merge_events(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Turn 5-minute rows (each with `m`, the minute since the period start) into events: a meal logged twice within 30 minutes with the same
    food is one meal; neighbouring exercise rows of one type are one span; a symptom noted again within 30 minutes is one; a missed dose
    marked within 5 minutes of the last is one."""
    meals: list[dict[str, Any]] = []
    exercise: list[dict[str, Any]] = []
    symptoms: list[dict[str, Any]] = []
    missed: list[int] = []
    mood: list[dict[str, Any]] = []
    for r in rows:
        m = r["m"]
        if r.get("meal_type"):
            prev = meals[-1] if meals else None
            if not (prev and prev["type"] == r["meal_type"] and prev["food"] == (r.get("food") or "") and m - prev["m"] <= MEAL_GAP_MIN):
                meals.append({"m": m, "type": r["meal_type"], "food": (r.get("food") or "")[:60]})
        if r.get("exercise_type"):
            prev = exercise[-1] if exercise else None
            if prev and prev["type"] == r["exercise_type"] and m - prev["m1"] <= EXERCISE_GAP_MIN:
                prev["m1"] = m + 5
            else:
                exercise.append({"m0": m, "m1": m + 5, "type": r["exercise_type"]})
        if r.get("symptom_type"):
            if not any(s["type"] == r["symptom_type"] and m - s["m"] <= MEAL_GAP_MIN for s in symptoms[-3:]):
                symptoms.append({"m": m, "type": r["symptom_type"]})
        if r.get("dose_status") == "missed" and not (missed and m - missed[-1] <= 5):
            missed.append(m)
        if r.get("mood") is not None and not (mood and mood[-1]["m"] == m):
            mood.append({"m": m, "mood": int(r["mood"]), "stress": int(r["stress_self"]) if r.get("stress_self") is not None else None})
    return {"meals": meals, "exercise": exercise, "symptoms": symptoms, "missed": [{"m": m} for m in missed], "mood": mood}


def slope_per_week(values: list[float | None], min_points: int = 5) -> float | None:
    """Least-squares slope of one value a day, per 7 days. None with fewer than `min_points` days that have a value."""
    pts = [(i, float(v)) for i, v in enumerate(values) if v is not None]
    if len(pts) < min_points:
        return None
    n = len(pts)
    mx = sum(i for i, _ in pts) / n
    my = sum(v for _, v in pts) / n
    den = sum((i - mx) ** 2 for i, _ in pts)
    return None if den == 0 else 7 * sum((i - mx) * (v - my) for i, v in pts) / den


def _avg(xs: list[float | None]) -> float | None:
    p = [float(x) for x in xs if x is not None]
    return sum(p) / len(p) if p else None


def slope_per_week(values: list[float | None], min_points: int = 5) -> float | None:
    """Least-squares slope of one value a day, per 7 days. None with fewer than `min_points` days that have a value."""
    pts = [(i, float(v)) for i, v in enumerate(values) if v is not None]
    if len(pts) < min_points:
        return None
    n = len(pts)
    mx = sum(i for i, _ in pts) / n
    my = sum(v for _, v in pts) / n
    den = sum((i - mx) ** 2 for i, _ in pts)
    return None if den == 0 else 7 * sum((i - mx) * (v - my) for i, v in pts) / den


def _avg(xs: list[float | None]) -> float | None:
    p = [float(x) for x in xs if x is not None]
    return sum(p) / len(p) if p else None


def gmi(mean_mmol: float | None) -> float | None:
    """Estimated A1c from the average glucose (the published GMI formula, mean in mg/dL)."""
    return None if mean_mmol is None else round(3.31 + 0.02392 * mean_mmol * 18.016, 1)


# ───────────────────────────────────────────────────────────────── queries
def _hourly(conn: psycopg.Connection[Any], user: str, lo: datetime, hi: datetime) -> dict[str, Any]:
    """Per hour of day (0 to 23): average, 25th and 75th percentile of glucose, heart rate and SpO2, over [lo, hi). Plus the days behind it."""
    out: dict[str, Any] = {"days": 0}
    rows = conn.execute(
        """select extract(hour from bucket_start at time zone 'Asia/Singapore')::int h,
                  avg(glucose_mmol) g, percentile_cont(0.25) within group (order by glucose_mmol) g25, percentile_cont(0.75) within group (order by glucose_mmol) g75,
                  avg(heart_rate_bpm) hr, percentile_cont(0.25) within group (order by heart_rate_bpm) hr25, percentile_cont(0.75) within group (order by heart_rate_bpm) hr75,
                  avg(spo2_pct) sp, percentile_cont(0.25) within group (order by spo2_pct) sp25, percentile_cont(0.75) within group (order by spo2_pct) sp75
           from timeline_5min where user_id=%s and bucket_start>=%s and bucket_start<%s group by 1""",
        (user, lo, hi),
    ).fetchall()
    cols = {"glucose": ("g", "g25", "g75"), "heart": ("hr", "hr25", "hr75"), "spo2": ("sp", "sp25", "sp75")}
    by_h = {int(r["h"]): r for r in rows}
    for key, (a, l, h) in cols.items():
        out[key] = {
            "mean": [_r(by_h[i][a]) if i in by_h else None for i in range(24)],
            "lo": [_r(by_h[i][l]) if i in by_h else None for i in range(24)],
            "hi": [_r(by_h[i][h]) if i in by_h else None for i in range(24)],
        }
    d = conn.execute(
        "select count(distinct (bucket_start at time zone 'Asia/Singapore')::date) n from timeline_5min where user_id=%s and bucket_start>=%s and bucket_start<%s and (glucose_mmol is not null or heart_rate_bpm is not null)",
        (user, lo, hi),
    ).fetchone()
    out["days"] = int(d["n"]) if d else 0
    return out


def _daily_usual(conn: psycopg.Connection[Any], user: str, lo: datetime, hi: datetime) -> dict[str, Any]:
    """The usual range of the person's DAILY averages (25th to 75th percentile, and their mean) over [lo, hi), for the one-point-a-day views."""
    r = conn.execute(
        """with d as (select local_date, avg(glucose_mmol) g, avg(heart_rate_bpm) h, avg(spo2_pct) s from timeline_5min
                      where user_id=%s and bucket_start>=%s and bucket_start<%s group by 1)
           select avg(g) g, percentile_cont(0.25) within group (order by g) g25, percentile_cont(0.75) within group (order by g) g75,
                  avg(h) h, percentile_cont(0.25) within group (order by h) h25, percentile_cont(0.75) within group (order by h) h75,
                  avg(s) s, percentile_cont(0.25) within group (order by s) s25, percentile_cont(0.75) within group (order by s) s75 from d""",
        (user, lo, hi),
    ).fetchone() or {}
    return {k: {"mean": _r(r.get(a)), "lo": _r(r.get(a + "25")), "hi": _r(r.get(a + "75"))} for k, a in (("glucose", "g"), ("heart", "h"), ("spo2", "s"))}


def timeline(conn: psycopg.Connection[Any], user: str, days: int, today: date, end_on: date | None = None) -> dict[str, Any]:
    latest = base.anchor(conn, user, today)
    end = min(end_on, latest) if end_on else latest
    first = conn.execute("select min(local_date) d from timeline_5min where user_id=%s", (user,)).fetchone() or {}
    start, _ = base.window(end, days)
    lo = datetime.combine(start, datetime.min.time(), base.TZ)
    hi = datetime.combine(end + timedelta(days=1), datetime.min.time(), base.TZ)
    step = STEP_MIN[days]
    n = days * 1440 // step

    keys = ("glucose", "glucoseMin", "glucoseMax", "heart", "heartMin", "heartMax", "spo2", "spo2Min", "spo2Max", "steps")
    series: dict[str, list[Any]] = {k: [None] * n for k in keys}
    for r in conn.execute(
        """select floor(extract(epoch from bucket_start - %s) / %s)::int k, avg(glucose_mmol) g, min(glucose_mmol) gmin, max(glucose_mmol) gmax,
                  avg(heart_rate_bpm) h, min(heart_rate_bpm) hmin, max(heart_rate_bpm) hmax, avg(spo2_pct) s, min(spo2_pct) smin, max(spo2_pct) smax, sum(steps) st
           from timeline_5min where user_id=%s and bucket_start>=%s and bucket_start<%s group by 1""",
        (lo, step * 60, user, lo, hi),
    ):
        k = int(r["k"])
        if 0 <= k < n:
            for key, col, nd in (("glucose", "g", 1), ("glucoseMin", "gmin", 1), ("glucoseMax", "gmax", 1), ("heart", "h", 0), ("heartMin", "hmin", 0), ("heartMax", "hmax", 0), ("spo2", "s", 1), ("spo2Min", "smin", 1), ("spo2Max", "smax", 1)):
                series[key][k] = _r(r[col], nd)
            series["steps"][k] = int(r["st"]) if r["st"] is not None else None

    # blood pressure readings and the logs, as minutes since the period start
    ev_rows: list[dict[str, Any]] = []
    bp: list[dict[str, Any]] = []
    for r in conn.execute(
        """select bucket_start, systolic_mmhg, diastolic_mmhg, meal_type::text meal_type, food, exercise_type::text exercise_type, symptom_type::text symptom_type,
                  dose_status::text dose_status, mood, stress_self
           from timeline_5min where user_id=%s and bucket_start>=%s and bucket_start<%s
             and (systolic_mmhg is not null or meal_type is not null or exercise_type is not null or symptom_type is not null or dose_status='missed' or mood is not null)
           order by bucket_start""",
        (user, lo, hi),
    ):
        m = int((r["bucket_start"] - lo).total_seconds() // 60)
        if r["systolic_mmhg"] is not None and r["diastolic_mmhg"] is not None and not (bp and bp[-1]["m"] == m):
            bp.append({"m": m, "systolic": int(r["systolic_mmhg"]), "diastolic": int(r["diastolic_mmhg"])})
        ev_rows.append({**dict(r), "m": m})
    events = merge_events(ev_rows)

    # the baseline: the 60 days before the period; with fewer than MIN_BASELINE_DAYS of them, the first 30 days of the period ("start"), or the
    # whole period when it is shorter ("period"). `source` says which, so the screen can word it.
    b_lo, b_hi = lo - timedelta(days=BASELINE_DAYS), lo
    hourly = _hourly(conn, user, b_lo, b_hi)
    source = "before"
    if hourly["days"] < MIN_BASELINE_DAYS:
        own_hi = min(hi, lo + timedelta(days=FIRST_DAYS))
        own = _hourly(conn, user, lo, own_hi)
        if own["days"] >= MIN_BASELINE_DAYS:
            hourly, b_lo, b_hi = own, lo, own_hi
            source = "start" if days > FIRST_DAYS else "period"
    enough = hourly["days"] >= MIN_BASELINE_DAYS
    bpb = conn.execute(
        "select avg(systolic_mmhg) s, avg(diastolic_mmhg) d, count(systolic_mmhg) n from timeline_5min where user_id=%s and bucket_start>=%s and bucket_start<%s and systolic_mmhg is not null",
        (user, b_lo, b_hi),
    ).fetchone() or {}
    bp_n = int(bpb.get("n") or 0)
    dusual = _daily_usual(conn, user, b_lo, b_hi) if enough else {k: {"mean": None, "lo": None, "hi": None} for k in ("glucose", "heart", "spo2")}
    baseline: dict[str, Any] = {
        "days": hourly["days"],
        "source": source,
        "from": b_lo.astimezone(base.TZ).date().isoformat(),
        "to": (b_hi - timedelta(days=1)).astimezone(base.TZ).date().isoformat(),
        "available": enough,
        "bpAvailable": bp_n >= MIN_BP_READINGS,
        "bpSystolic": _r(bpb.get("s"), 0) if bp_n >= MIN_BP_READINGS else None,
        "bpDiastolic": _r(bpb.get("d"), 0) if bp_n >= MIN_BP_READINGS else None,
        "bpReadings": bp_n,
        "daily": dusual,
    }
    for key in ("glucose", "heart", "spo2"):
        baseline[key] = hourly[key] if enough else {"mean": [None] * 24, "lo": [None] * 24, "hi": [None] * 24}

    # one row per day: the averages and ranges, blood pressure, steps, and what was eaten (from the day's summary)
    ds = base._daily(conn, user, start, end)
    by_day: dict[date, dict[str, Any]] = {}
    for r in conn.execute(
        """select local_date d, avg(glucose_mmol) g, min(glucose_mmol) gmin, max(glucose_mmol) gmax, avg(heart_rate_bpm) h, min(heart_rate_bpm) hmin, max(heart_rate_bpm) hmax,
                  avg(spo2_pct) s, min(spo2_pct) smin, max(spo2_pct) smax, avg(systolic_mmhg) sy, avg(diastolic_mmhg) di, count(systolic_mmhg) bpn, sum(steps) st
           from timeline_5min where user_id=%s and local_date between %s and %s group by 1""",
        (user, start, end),
    ):
        by_day[r["d"]] = dict(r)
    day_rows: list[dict[str, Any]] = []
    for i in range(days):
        d = start + timedelta(days=i)
        a = by_day.get(d, {})
        sm = ds.get(d, {})
        ate = (sm.get("meals_n") or 0) > 0
        kcal = D.kcal(sm.get("carbs_g"), sm.get("protein_g"), sm.get("fat_g")) if ate else None
        day_rows.append({
            "date": d.isoformat(),
            "glucose": {"avg": _r(a.get("g"), 1), "min": _r(a.get("gmin"), 1), "max": _r(a.get("gmax"), 1)},
            "heart": {"avg": _r(a.get("h"), 0), "min": _r(a.get("hmin"), 0), "max": _r(a.get("hmax"), 0)},
            "spo2": {"avg": _r(a.get("s"), 1), "min": _r(a.get("smin"), 1), "max": _r(a.get("smax"), 1)},
            "systolic": _r(a.get("sy"), 0) if a.get("bpn") else None,
            "diastolic": _r(a.get("di"), 0) if a.get("bpn") else None,
            "steps": int(a["st"]) if a.get("st") is not None else (int(sm["steps_total"]) if sm.get("steps_total") is not None else None),
            "kcal": int(kcal) if kcal is not None else None,
            "sugar_g": _r(sm.get("sugar_g"), 0) if ate else None,
            "sodium_mg": _r(sm.get("sodium_mg"), 0) if ate else None,
            "meals": int(sm.get("meals_n") or 0),
            "missed": int(sm.get("doses_missed") or 0),
            "symptoms": int(sm.get("symptoms_n") or 0),
        })

    # the period set against the baseline: the average of the whole period, of its most recent days, and the drift per week
    recent_n = 30 if days >= 90 else 7
    comp: dict[str, Any] = {"recent_days": min(recent_n, days)}
    for key in ("glucose", "heart", "spo2"):
        vals = [r[key]["avg"] for r in day_rows]
        comp[key] = {"baseline": dusual[key]["mean"] if enough else None, "period": _r(_avg(vals), 1), "recent": _r(_avg(vals[-recent_n:]), 1), "slope_per_week": _r(slope_per_week(vals), 2)}
    sys_vals = [r["systolic"] for r in day_rows]
    comp["bp"] = {"baseline": baseline["bpSystolic"], "period": _r(_avg(sys_vals), 0), "recent": _r(_avg(sys_vals[-recent_n:]), 0), "slope_per_week": _r(slope_per_week(sys_vals, 3), 1)}

    # the work hours the person gave at set-up (1 = Monday ... 7 = Sunday)
    p = conn.execute("select work_days, work_start, work_end from user_profile where user_id=%s", (user,)).fetchone() or {}
    ws, we = p.get("work_start"), p.get("work_end")
    work = {
        "days": sorted(int(d) for d in (p.get("work_days") or [])),
        "start": ws.strftime("%H:%M") if ws else None,
        "end": we.strftime("%H:%M") if we else None,
    }
    work["set"] = bool(work["days"] and work["start"] and work["end"])

    # what the values show
    g = conn.execute(
        "select avg(glucose_mmol) mean, stddev_samp(glucose_mmol) sd, count(glucose_mmol) n from timeline_5min where user_id=%s and bucket_start>=%s and bucket_start<%s",
        (user, lo, hi),
    ).fetchone() or {}
    mean = float(g["mean"]) if g.get("mean") is not None else None
    cv = round(100 * float(g["sd"]) / mean) if mean and g.get("sd") is not None else None
    steps = base._mean([float(v["steps_total"]) for v in ds.values() if v.get("steps_total") is not None])
    taken = sum(v.get("doses_taken") or 0 for v in ds.values())
    sched = sum(v.get("doses_scheduled") or 0 for v in ds.values())
    values = {
        "avgGlucose": _r(mean, 1),
        "gmi": gmi(mean),
        "cv": cv,
        "stepsPerDay": round(steps) if steps is not None else None,
        "dosesTakenPct": round(100 * taken / sched) if sched else None,
        "sensorWornPct": min(100, round(100 * int(g.get("n") or 0) / (days * 288))) if g.get("n") else None,
    }

    has = any(v is not None for v in series["glucose"] + series["heart"] + series["spo2"] + series["steps"]) or bool(bp or events["meals"])
    return {
        "period": {**base._period(end, days, has), "bucketMinutes": step, "buckets": n, "latest": latest.isoformat(), "earliest": first["d"].isoformat() if first.get("d") else None},
        "series": series,
        "baseline": baseline,
        "bp": bp,
        "events": events,
        "work": work,
        "values": values,
        "day_rows": day_rows,
        "compare": comp,
    }
