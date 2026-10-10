"""The Day view (screens D1 and D2): one day on one clock, read from the person's stored data.

The series come from timeline_5min (one row per 5 minutes; a null glucose or heart rate is a gap, never filled in). Each marker is one
row of its own table: meals (food_logs, with meal_response), doses (medication_log, grouped by scheduled time), workouts (exercise_logs,
with exercise_response) and symptoms (symptom_logs). Mood and stress check-ins (wellbeing_logs) are dots, not markers.

Every outcome sentence is worded from numbers already on the screen. A comparison is "associated with" at most, and a comparison with
too few meals of the same kind says so. The thresholds for a salty or sugary meal are placeholders pending clinical review.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

import psycopg

from app.core.config import settings

from app.services import insights as I

TZ = I.TZ
STEP = 5                                # minutes per bucket
SLOTS = list(range(0, 24 * 60, STEP))  # 288 slots, the full day
MIN_MEALS_TO_COMPARE = 5               # fewer own meals of the same kind than this, and the comparison is not shown
USUAL_BAND_MMOL = 0.5                  # within half a mmol/L of the usual median is "about the same as your usual"
SALT_FLAG_MG = settings.meal_high_sodium_mg    # the same limits Home, Food and Insights use, so a meal is flagged the same everywhere
SUGAR_FLAG_G = settings.meal_high_sugar_g
SYMPTOM_GLUCOSE_WINDOW = timedelta(minutes=15)
DOSE_RANK = {"missed": 3, "not_confirmed": 2, "late": 1, "taken": 0}

MEAL_LABELS = {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner", "snack": "Snack", "drink": "Drink"}
SYMPTOM_LABELS = {
    "thirst": "More thirsty than usual", "frequent_urination": "Passing more urine", "numbness": "Numbness", "tingling": "Tingling",
    "blurred_vision": "Blurred vision", "fatigue": "Tiredness", "dizziness": "Dizziness", "headache": "Headache", "shaky_sweaty": "Shaky or sweaty",
}


# ───────────────────────────────────────────────────────────────── pure helpers
def clock(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"


def minute_of(ts: datetime) -> int:
    """Minutes after local midnight in Singapore, rounded down to the 5-minute slot for series use."""
    local = ts.astimezone(TZ)
    return local.hour * 60 + local.minute


def _slot(minute: int) -> int:
    return minute - minute % STEP


def _num(x: Any) -> float | None:
    return None if x is None else float(x)


def _not_recorded() -> str:
    return "Not recorded"


def build_series(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The full day as 288 slots. Slots with no row stay empty, so the chart shows a gap and never a joined line."""
    by: dict[int, dict[str, Any]] = {}
    for r in rows:
        by[_slot(minute_of(r["bucket_start"]))] = r
    out = []
    for m in SLOTS:
        r = by.get(m, {})
        out.append({
            "minute": m,
            "glucose_mmol": _num(r.get("glucose_mmol")),
            "heart_rate_bpm": r.get("heart_rate_bpm"),
            "steps": r.get("steps"),
            "sleep_minutes": r.get("sleep_minutes") or 0,
        })
    return out


def sleep_bands(series: list[dict[str, Any]]) -> list[dict[str, int]]:
    """Runs of consecutive slots that were asleep (sleep_minutes above zero). A run ends at the last asleep slot plus one step."""
    bands: list[dict[str, int]] = []
    start: int | None = None
    last = 0
    for p in series:
        if p["sleep_minutes"] > 0:
            if start is None:
                start = p["minute"]
            last = p["minute"] + STEP
        elif start is not None:
            bands.append({"start_minute": start, "end_minute": last})
            start = None
    if start is not None:
        bands.append({"start_minute": start, "end_minute": last})
    return bands


def kcal(carbs: Any, protein: Any, fat: Any) -> int | None:
    """Energy from the three macros (4, 4 and 9 kcal a gram). None unless all three are recorded."""
    if carbs is None or protein is None or fat is None:
        return None
    return round(4 * float(carbs) + 4 * float(protein) + 9 * float(fat))


def meal_flags(sodium_mg: Any, sugar_g: Any) -> list[str]:
    flags = []
    if sodium_mg is not None and float(sodium_mg) >= SALT_FLAG_MG:
        flags.append("salt")
    if sugar_g is not None and float(sugar_g) >= SUGAR_FLAG_G:
        flags.append("sugar")
    return flags


def dose_state(status: str, scheduled_at: datetime | None, taken_at: datetime | None) -> str:
    """taken, late (more than an hour after its time), not_confirmed (still pending), or missed (missed or skipped)."""
    if status == "taken":
        if scheduled_at and taken_at and taken_at - scheduled_at > timedelta(minutes=I.LATE_AFTER_MIN):
            return "late"
        return "taken"
    if status == "pending":
        return "not_confirmed"
    return "missed"


def worst_dose_state(states: list[str]) -> str:
    return max(states, key=lambda s: DOSE_RANK[s])


def meal_outcome(rise: float | None, own_rises: list[float], meal_type: str) -> str:
    """One sentence for a meal. The comparison uses the person's other meals of the same kind, never this one."""
    if rise is None:
        return "There is no glucose reading two hours after this meal, so it cannot be compared yet."
    if rise < 0:
        return f"Two hours after this meal your glucose was {abs(rise):.1f} mmol/L lower than before it."
    if len(own_rises) < MIN_MEALS_TO_COMPARE:
        return (f"Two hours after this meal your glucose rose {rise:.1f} mmol/L. "
                "There are not enough meals of this kind yet to compare.")
    median = statistics.median(own_rises)
    diff = rise - median
    if diff > USUAL_BAND_MMOL:
        phrase = "more than"
    elif diff < -USUAL_BAND_MMOL:
        phrase = "less than"
    else:
        phrase = "about the same as"
    return (f"Two hours after this meal your glucose rose {rise:.1f} mmol/L, {phrase} your usual for "
            f"{meal_type} (median {median:.1f}).")


def minutes_phrase(mins: int) -> str:
    """90 to "1 h 30 min", 20 to "20 min"."""
    h, m = divmod(mins, 60)
    return f"{h} h {m} min" if h else f"{m} min"


def dose_row(name: str, state: str, scheduled_at: datetime, taken_at: datetime | None, reason: str | None, status: str) -> dict[str, str]:
    if state == "taken":
        value = f"Taken at {clock(minute_of(taken_at))}" if taken_at else "Taken"
    elif state == "late":
        late_by = int((taken_at - scheduled_at).total_seconds() // 60)
        value = f"Taken at {clock(minute_of(taken_at))}, {minutes_phrase(late_by)} late"
    elif state == "not_confirmed":
        value = "Not confirmed yet"
    else:
        value = "Skipped" if status == "skipped" else "Missed"
        if reason:
            value += f", reason: {I.MISS_LABELS.get(reason, reason)}"
    return {"label": name, "value": value}


def dose_outcome(states: list[str]) -> str:
    """Counts only, so it never says a dose was 'effective' or 'needed'."""
    n = len(states)
    parts = []
    for key, words in (("taken", "taken on time"), ("late", "taken late"), ("not_confirmed", "not confirmed yet"), ("missed", "missed")):
        k = states.count(key)
        if k:
            parts.append(f"{k} {words}")
    return f"{n} dose{'s' if n != 1 else ''} at this time: " + "; ".join(parts) + "."


def workout_outcome(glucose_before: float | None, glucose_lowest: float | None, hr_avg: int | None, hr_peak: int | None) -> str:
    parts = []
    if hr_avg is not None:
        hr = f"Average heart rate {hr_avg} beats a minute"
        parts.append(hr + (f", peak {hr_peak}." if hr_peak is not None else "."))
    if glucose_before is not None and glucose_lowest is not None:
        parts.append(f"Glucose went from {glucose_before:.1f} to a lowest of {glucose_lowest:.1f} mmol/L during the session.")
    return " ".join(parts) if parts else "No heart rate or glucose was recorded for this session."


def symptom_outcome(glucose: float | None) -> str:
    if glucose is None:
        return "There is no glucose reading close to this time."
    return f"Your glucose was {glucose:.1f} mmol/L at about this time."


def glucose_near(series: list[dict[str, Any]], minute: int) -> float | None:
    """The nearest sensor reading within 15 minutes, or None. Used to say what the glucose was next to a symptom."""
    best: tuple[int, float] | None = None
    for p in series:
        if p["glucose_mmol"] is None:
            continue
        gap = abs(p["minute"] - minute)
        if gap <= SYMPTOM_GLUCOSE_WINDOW.total_seconds() / 60 and (best is None or gap < best[0]):
            best = (gap, p["glucose_mmol"])
    return best[1] if best else None


def neighbours(days: list[date], day: date) -> tuple[str | None, str | None]:
    """The closest day with data before and after `day` (days is any order)."""
    before = max((d for d in days if d < day), default=None)
    after = min((d for d in days if d > day), default=None)
    return (before.isoformat() if before else None, after.isoformat() if after else None)


def has_data(series: list[dict[str, Any]], markers: list[dict[str, Any]], moods: list[dict[str, Any]]) -> bool:
    """A day with only scheduled doses still waiting for a tap is not data yet (it is the same rule as the date list)."""
    recorded = [m for m in markers if not (m["kind"] == "dose" and m["status"] == "not_confirmed")]
    return bool(recorded or moods or any(p["glucose_mmol"] is not None or p["heart_rate_bpm"] is not None or p["steps"] is not None or p["sleep_minutes"] for p in series))


# ───────────────────────────────────────────────────────────────── loads (SQL)
SG_DATE = "(%s at time zone 'Asia/Singapore')::date"


def dated(conn: psycopg.Connection[Any], user: str, lo: date, hi: date) -> list[date]:
    """Every day in [lo, hi] that has glucose, heart rate or steps, or any meal, dose, workout, symptom or check-in."""
    rows = conn.execute(
        f"""select distinct d from (
              select local_date d from timeline_5min where user_id=%(u)s and (glucose_mmol is not null or heart_rate_bpm is not null or steps is not null)
              union select {SG_DATE % 'start_at'} from food_logs where user_id=%(u)s and deleted_at is null
              union select {SG_DATE % 'scheduled_at'} from medication_log where user_id=%(u)s and status <> 'pending'
              union select {SG_DATE % 'start_at'} from exercise_logs where user_id=%(u)s and deleted_at is null
              union select {SG_DATE % 'occurred_at'} from symptom_logs where user_id=%(u)s and deleted_at is null
              union select {SG_DATE % 'recorded_at'} from wellbeing_logs where user_id=%(u)s and deleted_at is null
            ) t where d between %(lo)s and %(hi)s order by d""",
        {"u": user, "lo": lo, "hi": hi},
    ).fetchall()
    return [r["d"] for r in rows]


def _timeline(conn: psycopg.Connection[Any], user: str, day: date) -> list[dict[str, Any]]:
    return conn.execute(
        "select bucket_start, glucose_mmol, heart_rate_bpm, steps, sleep_minutes from timeline_5min where user_id=%s and local_date=%s",
        (user, day),
    ).fetchall()


def _meals(conn: psycopg.Connection[Any], user: str, day: date) -> list[dict[str, Any]]:
    return conn.execute(
        f"""select f.id, f.start_at, f.meal_type, f.food, f.carbs_g, f.protein_g, f.fat_g, f.sugar_g, f.sodium_mg,
                   mr.pre_glucose_mmol, mr.glucose_2h_mmol, mr.rise_mmol
            from food_logs f left join meal_response mr on mr.food_log_id = f.id
            where f.user_id=%s and f.deleted_at is null and {SG_DATE % 'f.start_at'} = %s
            order by f.start_at""",
        (user, day),
    ).fetchall()


def _own_rises(conn: psycopg.Connection[Any], user: str) -> list[dict[str, Any]]:
    return conn.execute(
        """select f.id, f.meal_type, mr.rise_mmol from food_logs f join meal_response mr on mr.food_log_id = f.id
           where f.user_id=%s and f.deleted_at is null and mr.rise_mmol is not null""",
        (user,),
    ).fetchall()


def _doses(conn: psycopg.Connection[Any], user: str, day: date) -> list[dict[str, Any]]:
    return conn.execute(
        f"""select ml.id, ml.scheduled_at, ml.taken_at, ml.status, ml.miss_reason, m.name
            from medication_log ml join medications m on m.id = ml.medication_id
            where ml.user_id=%s and m.deleted_at is null and ml.scheduled_at is not null and {SG_DATE % 'ml.scheduled_at'} = %s
            order by ml.scheduled_at, m.name""",
        (user, day),
    ).fetchall()


def _workouts(conn: psycopg.Connection[Any], user: str, day: date) -> list[dict[str, Any]]:
    return conn.execute(
        f"""select e.id, e.start_at, e.end_at, e.type, e.intensity, er.hr_avg_bpm, er.hr_peak_bpm,
                   er.glucose_pre_mmol, er.glucose_min_during_mmol
            from exercise_logs e left join exercise_response er on er.exercise_log_id = e.id
            where e.user_id=%s and e.deleted_at is null and {SG_DATE % 'e.start_at'} = %s
            order by e.start_at""",
        (user, day),
    ).fetchall()


def _symptoms(conn: psycopg.Connection[Any], user: str, day: date) -> list[dict[str, Any]]:
    return conn.execute(
        f"""select id, occurred_at, symptom_type, severity, duration_min from symptom_logs
            where user_id=%s and deleted_at is null and {SG_DATE % 'occurred_at'} = %s order by occurred_at""",
        (user, day),
    ).fetchall()


def _moods(conn: psycopg.Connection[Any], user: str, day: date) -> list[dict[str, Any]]:
    return conn.execute(
        f"""select id, recorded_at, mood, stress_self, energy from wellbeing_logs
            where user_id=%s and deleted_at is null and {SG_DATE % 'recorded_at'} = %s order by recorded_at""",
        (user, day),
    ).fetchall()


def _sleep_hours(conn: psycopg.Connection[Any], user: str, day: date) -> float | None:
    r = conn.execute("select sleep_hours from daily_summary where user_id=%s and local_date=%s", (user, day)).fetchone()
    return _num(r["sleep_hours"]) if r else None


# ───────────────────────────────────────────────────────────────── the screen
def _meal_marker(m: dict[str, Any], own: list[dict[str, Any]]) -> dict[str, Any]:
    minute = minute_of(m["start_at"])
    mt = m["meal_type"]
    rise = _num(m["rise_mmol"])
    others = [float(o["rise_mmol"]) for o in own if o["meal_type"] == mt and o["id"] != m["id"]]
    k = kcal(m["carbs_g"], m["protein_g"], m["fat_g"])
    rows = [
        {"label": "Carbohydrate", "value": f"{float(m['carbs_g']):.0f} g" if m["carbs_g"] is not None else _not_recorded()},
        {"label": "Energy", "value": f"{k} kcal" if k is not None else _not_recorded()},
        {"label": "Protein", "value": f"{float(m['protein_g']):.0f} g" if m["protein_g"] is not None else _not_recorded()},
        {"label": "Fat", "value": f"{float(m['fat_g']):.0f} g" if m["fat_g"] is not None else _not_recorded()},
        {"label": "Sugar", "value": f"{float(m['sugar_g']):.0f} g" if m["sugar_g"] is not None else _not_recorded()},
        {"label": "Sodium", "value": f"{float(m['sodium_mg']):.0f} mg" if m["sodium_mg"] is not None else _not_recorded()},
        {"label": "Glucose before", "value": f"{float(m['pre_glucose_mmol']):.1f} mmol/L" if m["pre_glucose_mmol"] is not None else _not_recorded()},
        {"label": "Glucose two hours after", "value": f"{float(m['glucose_2h_mmol']):.1f} mmol/L" if m["glucose_2h_mmol"] is not None else "No reading"},
    ]
    return {
        "id": str(m["id"]), "kind": "meal", "minute": minute, "end_minute": None, "clock": clock(minute),
        "title": MEAL_LABELS.get(mt, mt.capitalize()), "subtitle": m["food"] or None, "status": None,
        "flags": meal_flags(m["sodium_mg"], m["sugar_g"]), "rows": rows,
        "outcome": meal_outcome(rise, others, mt),
    }


def _dose_markers(doses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Doses due at the same time share one marker, so a crowded time is one tap, not three overlapping icons."""
    groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for d in doses:
        groups[minute_of(d["scheduled_at"])].append(d)
    out = []
    for minute, items in sorted(groups.items()):
        states = [dose_state(d["status"], d["scheduled_at"], d["taken_at"]) for d in items]
        rows = [dose_row(d["name"], s, d["scheduled_at"], d["taken_at"], d["miss_reason"], d["status"]) for d, s in zip(items, states)]
        out.append({
            "id": str(items[0]["id"]), "kind": "dose", "minute": minute, "end_minute": None, "clock": clock(minute),
            "title": "Medicines", "subtitle": f"Due at {clock(minute)}", "status": worst_dose_state(states),
            "flags": [], "rows": rows, "outcome": dose_outcome(states),
        })
    return out


def _workout_marker(w: dict[str, Any]) -> dict[str, Any]:
    minute = minute_of(w["start_at"])
    end = minute_of(w["end_at"]) if w["end_at"] else None
    if end is not None and end <= minute:
        end = None
    label = I.EXERCISE_LABELS.get(w["type"], str(w["type"]).replace("_", " ").capitalize())
    rows = [{"label": "Type", "value": label}]
    if w["intensity"] is not None:
        rows.append({"label": "Intensity", "value": str(w["intensity"])})
    rows.append({"label": "Length", "value": f"{end - minute} min" if end is not None else _not_recorded()})
    if w["hr_avg_bpm"] is not None:
        rows.append({"label": "Average heart rate", "value": f"{w['hr_avg_bpm']} beats a minute"})
    if w["hr_peak_bpm"] is not None:
        rows.append({"label": "Peak heart rate", "value": f"{w['hr_peak_bpm']} beats a minute"})
    return {
        "id": str(w["id"]), "kind": "workout", "minute": minute, "end_minute": end, "clock": clock(minute),
        "title": label, "subtitle": f"Intensity {w['intensity']}" if w["intensity"] is not None else None, "status": None,
        "flags": [], "rows": rows,
        "outcome": workout_outcome(_num(w["glucose_pre_mmol"]), _num(w["glucose_min_during_mmol"]), w["hr_avg_bpm"], w["hr_peak_bpm"]),
    }


def _symptom_marker(s: dict[str, Any], series: list[dict[str, Any]]) -> dict[str, Any]:
    minute = minute_of(s["occurred_at"])
    label = SYMPTOM_LABELS.get(s["symptom_type"], str(s["symptom_type"]).replace("_", " ").capitalize())
    rows = [{"label": "Severity", "value": str(s["severity"])}] if s["severity"] is not None else []
    rows.append({"label": "Lasted", "value": f"{s['duration_min']} min" if s["duration_min"] is not None else _not_recorded()})
    return {
        "id": str(s["id"]), "kind": "symptom", "minute": minute, "end_minute": None, "clock": clock(minute),
        "title": label, "subtitle": None, "status": None, "flags": [], "rows": rows,
        "outcome": symptom_outcome(glucose_near(series, _slot(minute))),
    }


def day_view(conn: psycopg.Connection[Any], user: str, day: date, today: date) -> dict[str, Any]:
    lo, hi = I._targets(conn, user)
    series = build_series(_timeline(conn, user, day))
    own = _own_rises(conn, user)
    markers = [_meal_marker(m, own) for m in _meals(conn, user, day)]
    markers += _dose_markers(_doses(conn, user, day))
    markers += [_workout_marker(w) for w in _workouts(conn, user, day)]
    markers += [_symptom_marker(s, series) for s in _symptoms(conn, user, day)]
    markers.sort(key=lambda mk: (mk["minute"], mk["kind"]))
    moods = [{
        "id": str(r["id"]), "minute": minute_of(r["recorded_at"]), "clock": clock(minute_of(r["recorded_at"])),
        "mood": r["mood"], "stress_self": r["stress_self"], "energy": r["energy"],
    } for r in _moods(conn, user, day)]
    sleep = sleep_bands(series)
    before, after = neighbours(dated(conn, user, day - timedelta(days=366), today), day)
    # sleep_minutes was only needed to build the bands; the chart gets the bands, not the raw field.
    points = [{k: v for k, v in p.items() if k != "sleep_minutes"} for p in series]
    return {
        "date": day.isoformat(),
        "label": f"{day:%A} {day.day} {day:%B %Y}",
        "has_data": has_data(series, markers, moods),
        "prev_date": before,
        "next_date": after,
        "target_low": lo,
        "target_high": hi,
        "sleep_hours": _sleep_hours(conn, user, day),
        "series": points,
        "sleep": sleep,
        "markers": markers,
        "mood": moods,
    }


def day_dates(conn: psycopg.Connection[Any], user: str, today: date, days: int) -> dict[str, Any]:
    dates = dated(conn, user, today - timedelta(days=days - 1), today)
    dates.sort(reverse=True)
    # open on the latest day with a decent sensor record (at least half the day), so the first view is not a nearly empty last day;
    # with no such day, fall back to the latest day that has any data
    full = conn.execute("select max(local_date) d from daily_summary where user_id = %s and local_date <= %s and coalesce(cgm_coverage_pct, 0) >= 50", (user, today)).fetchone()
    latest = full["d"] if full and full["d"] else I.anchor(conn, user, today)
    return {"latest_date": latest.isoformat(), "dates": [d.isoformat() for d in dates]}
