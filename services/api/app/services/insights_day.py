"""One day for the Insights drill-down (GET /insights/day?date=YYYY-MM-DD): the day's glucose, heart rate, SpO2 and steps every 5 minutes on one clock, the
hourly baseline (the person's own average for each hour over the 14 days before), what was logged (meals with their macros and measured glucose rise,
doses, symptoms, blood pressure, mood, exercise), the day's totals, and two ideas for tomorrow (a lighter meal from the person's own history; a walk, when
no exercise was logged).

Everything is read from the person's own stored data; no model is called. A rise after a meal is the one stored in `meal_response`; the minute of its peak is
found in the 5-minute glucose series (the highest reading in the 2 hours after the meal). Nothing here is a verdict: the screen words how far a reading is
from the baseline, and the ideas are offered as things to try, from the person's own records, never as medical advice.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import psycopg

from app.services import day as D
from app.services import insights as base
from app.services.insights_timeline import MIN_BASELINE_DAYS, _hourly, _r, merge_events

POINTS = 288                  # one point every 5 minutes
BASELINE_DAYS = 14
PEAK_WINDOW_MIN = 120         # a meal's rise is read over the 2 hours after it
SWAP_CARB_SHARE = 0.75        # a lighter meal has at most this share of the day's heaviest meal's carbs
MIN_SWAP_LOGS = 2             # the swap must be a meal the person has logged at least twice
MIN_PATTERN_PAIRS = 5


def peak_after(glucose: list[float | None], minute: int, window: int = PEAK_WINDOW_MIN) -> tuple[int, float] | None:
    """(minute, value) of the highest glucose reading from `minute` to `window` minutes later; None when there is no reading in that time."""
    a = max(0, minute // 5)
    b = min(len(glucose) - 1, (minute + window) // 5)
    best: tuple[int, float] | None = None
    for k in range(a, b + 1):
        v = glucose[k]
        if v is not None and (best is None or v > best[1]):
            best = (k * 5, float(v))
    return best


def _bounds(d: date) -> tuple[datetime, datetime]:
    return datetime.combine(d, datetime.min.time(), base.TZ), datetime.combine(d + timedelta(days=1), datetime.min.time(), base.TZ)


def _neighbours(conn: psycopg.Connection[Any], user: str, d: date) -> dict[str, str | None]:
    r = conn.execute(
        """select (select max(local_date) from timeline_5min where user_id=%s and local_date < %s and glucose_mmol is not null) prev,
                  (select min(local_date) from timeline_5min where user_id=%s and local_date > %s and glucose_mmol is not null) nxt,
                  (select max(local_date) from timeline_5min where user_id=%s and glucose_mmol is not null) latest,
                  (select min(local_date) from timeline_5min where user_id=%s and glucose_mmol is not null) earliest""",
        (user, d, user, d, user, user),
    ).fetchone() or {}
    return {"prev": r["prev"].isoformat() if r.get("prev") else None, "next": r["nxt"].isoformat() if r.get("nxt") else None,
            "latest": r["latest"].isoformat() if r.get("latest") else None, "earliest": r["earliest"].isoformat() if r.get("earliest") else None}


def swap_idea(conn: psycopg.Connection[Any], user: str, meals: list[dict[str, Any]], before: datetime) -> dict[str, Any] | None:
    """The day's heaviest meal (by carbs) and a lighter meal of the same kind the person has logged before (at least twice), lowest measured rise first."""
    heavy = max((m for m in meals if m.get("carbsG") is not None), key=lambda m: m["carbsG"], default=None)
    if not heavy or not heavy["carbsG"]:
        return None
    r = conn.execute(
        """select min(f.food) food, avg(f.carbs_g) carbs, avg(m.rise_mmol) rise, count(*) n
           from food_logs f left join meal_response m on m.food_log_id=f.id
           where f.user_id=%s and f.deleted_at is null and f.meal_type::text=%s and f.start_at < %s and f.carbs_g is not null and lower(f.food) <> lower(%s)
           group by lower(f.food) having count(*) >= %s and avg(f.carbs_g) <= %s
           order by avg(m.rise_mmol) nulls last, avg(f.carbs_g) limit 1""",
        (user, heavy["type"], before, heavy["food"], MIN_SWAP_LOGS, float(heavy["carbsG"]) * SWAP_CARB_SHARE),
    ).fetchone()
    if not r:
        return None
    return {"fromFood": heavy["food"], "fromCarbsG": _r(heavy["carbsG"], 0), "toFood": r["food"], "toCarbsG": _r(r["carbs"], 0), "mealType": heavy["type"]}


def walk_idea(conn: psycopg.Connection[Any], user: str) -> dict[str, Any]:
    """Shown only when no exercise was logged. Carries what Smart Health has learnt about walks, confirmed or not, when it has learnt something."""
    r = conn.execute(
        "select pattern_key, n_pairs, median_delta, status::text st from pattern_candidates where user_id=%s and pattern_key='evening_walk__next_morning_fasting' and status not in ('dismissed','rejected','retired') limit 1",
        (user,),
    ).fetchone()
    learned = None
    if r and int(r["n_pairs"] or 0) >= MIN_PATTERN_PAIRS and r["median_delta"] is not None and float(r["median_delta"]) < 0:
        learned = {"lowerBy": _r(abs(float(r["median_delta"])), 1), "days": int(r["n_pairs"]), "confirmed": r["st"] in ("confirmed", "accepted", "active")}
    return {"learned": learned}


def day_view(conn: psycopg.Connection[Any], user: str, d: date, today: date) -> dict[str, Any]:
    lo, hi = _bounds(d)
    series: dict[str, list[Any]] = {"glucose": [None] * POINTS, "heart": [None] * POINTS, "spo2": [None] * POINTS, "steps": [0] * POINTS}
    rows = conn.execute(
        """select bucket_start, glucose_mmol, heart_rate_bpm, spo2_pct, steps, systolic_mmhg, diastolic_mmhg, exercise_type::text exercise_type,
                  symptom_type::text symptom_type, symptom_severity, mood, stress_self, dose_status::text dose_status, medication_names
           from timeline_5min where user_id=%s and bucket_start>=%s and bucket_start<%s order by bucket_start""",
        (user, lo, hi),
    ).fetchall()
    ev_rows: list[dict[str, Any]] = []
    symptoms: list[dict[str, Any]] = []
    doses: list[dict[str, Any]] = []
    bp: list[dict[str, Any]] = []
    for r in rows:
        k = int((r["bucket_start"] - lo).total_seconds() // 300)
        m = k * 5
        if 0 <= k < POINTS:
            series["glucose"][k] = _r(r["glucose_mmol"], 1)
            series["heart"][k] = _r(r["heart_rate_bpm"], 0)
            series["spo2"][k] = _r(r["spo2_pct"], 1)
            series["steps"][k] = int(r["steps"] or 0)
        if r["systolic_mmhg"] is not None and r["diastolic_mmhg"] is not None:
            bp.append({"m": m, "systolic": int(r["systolic_mmhg"]), "diastolic": int(r["diastolic_mmhg"])})
        if r["dose_status"]:
            name = (r["medication_names"] or "").strip()
            if not any(x["m"] == m and x["name"] == name for x in doses):
                doses.append({"m": m, "status": r["dose_status"], "name": name})
        if r["symptom_type"]:
            last = symptoms[-1] if symptoms else None
            if last and last["type"] == r["symptom_type"] and m - last["m1"] <= 30:
                last["m1"] = m
            else:
                symptoms.append({"m": m, "m1": m, "type": r["symptom_type"], "severity": int(r["symptom_severity"]) if r["symptom_severity"] is not None else None})
        ev_rows.append({"m": m, "exercise_type": r["exercise_type"], "symptom_type": r["symptom_type"], "mood": r["mood"], "stress_self": r["stress_self"]})
    ev = merge_events(ev_rows)

    # meals: from the food log with the measured rise; the minute of the peak is read from the 5-minute series
    meals: list[dict[str, Any]] = []
    for f in conn.execute(
        """select f.start_at, f.meal_type::text meal_type, f.food, f.carbs_g, f.protein_g, f.fat_g, f.sugar_g, f.sodium_mg, mr.rise_mmol, mr.peak_glucose_mmol
           from food_logs f left join meal_response mr on mr.food_log_id=f.id
           where f.user_id=%s and f.deleted_at is null and f.start_at>=%s and f.start_at<%s order by f.start_at""",
        (user, lo, hi),
    ):
        t = f["start_at"].astimezone(base.TZ)
        m = t.hour * 60 + t.minute
        pk = peak_after(series["glucose"], m)
        meals.append({
            "m": m, "type": f["meal_type"], "food": (f["food"] or "")[:80], "carbsG": _r(f["carbs_g"], 0), "sugarG": _r(f["sugar_g"], 0), "sodiumMg": _r(f["sodium_mg"], 0),
            "kcal": D.kcal(f["carbs_g"], f["protein_g"], f["fat_g"]), "riseMmol": _r(f["rise_mmol"], 1),
            "peakMmol": _r(f["peak_glucose_mmol"], 1) if f["peak_glucose_mmol"] is not None else (_r(pk[1], 1) if pk else None), "peakM": pk[0] if pk else None,
        })

    # the baseline: the 14 days before this day, hour by hour (no baseline with fewer than MIN_BASELINE_DAYS days behind it)
    hourly = _hourly(conn, user, lo - timedelta(days=BASELINE_DAYS), lo)
    ok = hourly["days"] >= MIN_BASELINE_DAYS
    bpb = conn.execute(
        "select avg(systolic_mmhg) s, count(systolic_mmhg) n from timeline_5min where user_id=%s and bucket_start>=%s and bucket_start<%s and systolic_mmhg is not null",
        (user, lo - timedelta(days=BASELINE_DAYS), lo),
    ).fetchone() or {}
    bds = base._daily(conn, user, d - timedelta(days=BASELINE_DAYS), d - timedelta(days=1))
    b_steps = base._mean([float(v["steps_total"]) for v in bds.values() if v.get("steps_total") is not None])
    baseline = {
        "available": ok,
        "glucose": hourly["glucose"]["mean"] if ok else [None] * 24,
        "heart": hourly["heart"]["mean"] if ok else [None] * 24,
        "spo2": hourly["spo2"]["mean"] if ok else [None] * 24,
        "bpSystolic": _r(bpb.get("s"), 0) if ok and int(bpb.get("n") or 0) >= 3 else None,
        "stepsPerDay": round(b_steps) if ok and b_steps is not None else None,
    }

    # the day's totals
    sm = base._daily(conn, user, d, d).get(d, {})

    def stat(key: str, nd: int) -> dict[str, float | None]:
        v = [float(x) for x in series[key] if x is not None]
        return {"avg": _r(sum(v) / len(v), nd) if v else None, "min": _r(min(v), nd) if v else None, "max": _r(max(v), nd) if v else None}

    steps_total = sm.get("steps_total")
    totals = {
        "glucose": stat("glucose", 1), "heart": stat("heart", 0), "spo2": stat("spo2", 1),
        "steps": int(steps_total) if steps_total is not None else (sum(series["steps"]) or None),
        "kcal": D.kcal(sm.get("carbs_g"), sm.get("protein_g"), sm.get("fat_g")) if (sm.get("meals_n") or 0) > 0 else None,
        "carbsG": _r(sm.get("carbs_g"), 0) if (sm.get("meals_n") or 0) > 0 else None,
        "sugarG": _r(sm.get("sugar_g"), 0) if (sm.get("meals_n") or 0) > 0 else None,
        "sodiumMg": _r(sm.get("sodium_mg"), 0) if (sm.get("meals_n") or 0) > 0 else None,
        "meals": int(sm.get("meals_n") or 0),
        "dosesScheduled": int(sm.get("doses_scheduled") or 0), "dosesTaken": int(sm.get("doses_taken") or 0), "dosesMissed": int(sm.get("doses_missed") or 0),
        "sleepHours": _r(sm.get("sleep_hours"), 1),
    }
    has_data = any(v is not None for v in series["glucose"] + series["heart"]) or bool(meals or doses)

    p = conn.execute("select work_days, work_start, work_end from user_profile where user_id=%s", (user,)).fetchone() or {}
    work_days = sorted(int(x) for x in (p.get("work_days") or []))
    ideas = {"swap": swap_idea(conn, user, meals, lo), "walk": walk_idea(conn, user) if not ev["exercise"] else None}
    nb = _neighbours(conn, user, d)
    return {
        "date": d.isoformat(), "has_data": has_data, "prev_date": nb["prev"], "next_date": nb["next"], "latest_date": nb["latest"], "earliest_date": nb["earliest"],
        "weekday": d.isoweekday(), "work_set": bool(work_days and p.get("work_start") and p.get("work_end")), "work_days": work_days,
        "series": series, "baseline": baseline, "totals": totals, "meals": meals, "doses": doses, "symptoms": symptoms, "bp": bp, "mood": ev["mood"], "exercise": ev["exercise"],
        "ideas": ideas,
    }
