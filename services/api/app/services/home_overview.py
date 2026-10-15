"""GET /home/overview: everything the new Home page shows in one read (docs/specs/home-overview.md).

Read only. Nothing is written for Mr Tan; for other people the only write is the one the Home dose banner already makes (today's dose
rows, `dose_store.ensure_rows`). No model is called. Every number is a count, a mean or a percentile of the person's own stored data.

Two layers, so the rules are tested without a database:
  - pure builders (`range_status`, `build_plan`, `build_glucose`, ...) take plain rows and return plain dicts;
  - `load_and_build` reads the rows with ONE connection and calls them.

A status only compares the person with THEIR OWN usual range (p25 to p75 of their daily values over the 60 days before the 7-day
window). It never says a value is good or bad. A value that is not known is None, never 0.
"""
from __future__ import annotations

import time as _time
from datetime import date, datetime, time, timedelta
from typing import Any

from psycopg.rows import tuple_row

from app.core.config import settings
from app.db import logstore
from app.services import diet_days
from app.services import dose_store
from app.services import insights as I
from app.services import insights_heart as IH

TZ = logstore.TZ
WINDOW_DAYS = 7                     # the KPI window and the chart
MIN_WINDOW_DAYS = 3                 # fewest days with data in the window before a status is given (same minimum as Insights)
MIN_PRIOR_DAYS = 7                  # fewest days with data in the 60 days before the window
DOSE_WINDOW_MIN = I.LATE_AFTER_MIN  # a dose is due from its time to this many minutes after it: the same constant as agents/dose_timing.WINDOW_MIN
HIGH_MEALS_FOR_HIGH = 2             # a nutrient is "high" when at least this many meals in the 7 days are over the meal limit (placeholder)
MEAL_TYPES = {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner"}


def _r(x: float | None, digits: int = 1) -> float | None:
    return None if x is None else round(float(x), digits)


def _mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def _clock12(t: time) -> str:
    return t.strftime("%I:%M %p").lstrip("0").lower()


def _days(end: date) -> list[date]:
    """The 7 dates of the window, oldest first, ending on `end`."""
    return [end - timedelta(days=WINDOW_DAYS - 1 - i) for i in range(WINDOW_DAYS)]


def _prior_bounds(end: date) -> tuple[date, date]:
    """The 60 days BEFORE the 7-day window."""
    start = end - timedelta(days=WINDOW_DAYS - 1)
    return start - timedelta(days=I.BASELINE_DAYS), start - timedelta(days=1)


# ───────────────────────────────────────────────────────────────── status (pure)
def range_status(window: list[float], prior: list[float], digits: int = 1) -> dict[str, Any]:
    """Compare the 7-day value (the mean of `window`, the daily values that exist) with the person's own usual range (p25 to p75 of
    `prior`, the daily values of the 60 days before). `unknown` unless there are at least 3 window days and 7 prior days."""
    usual = None
    if len(prior) >= MIN_PRIOR_DAYS:
        usual = (I._percentile(prior, 0.25), I._percentile(prior, 0.75), I._median(prior))
    out: dict[str, Any] = {"state": "unknown", "usual_low": None, "usual_high": None, "usual_median": None, "delta": None}
    if usual is None:
        return out
    out.update(usual_low=_r(usual[0], digits), usual_high=_r(usual[1], digits), usual_median=_r(usual[2], digits))
    if len(window) < MIN_WINDOW_DAYS:
        return out
    value = sum(window) / len(window)
    out["state"] = "within" if usual[0] <= value <= usual[1] else "above" if value > usual[1] else "below"
    out["delta"] = _r(value - usual[2], digits)
    return out


def unknown_status() -> dict[str, Any]:
    return range_status([], [])


def _values(by_day: dict[date, float | None], lo: date, hi: date) -> list[float]:
    return [v for d, v in by_day.items() if lo <= d <= hi and v is not None]


def _series(by_day: dict[date, float | None], days: list[date], digits: int = 1) -> list[float | None]:
    return [_r(by_day.get(d), digits) for d in days]


# ───────────────────────────────────────────────────────────────── the KPI cards (pure)
def build_glucose(daily: dict[date, dict[str, Any]], end: date) -> dict[str, Any] | None:
    """Value = the daily mean of the latest day with sensor data (`end`). Status = the 7-day mean against the usual daily means."""
    row = daily.get(end)
    if not row or row.get("glucose_mean_mmol") is None:
        return None
    by_day = {d: I._f(r.get("glucose_mean_mmol")) for d, r in daily.items()}
    lo, hi = _prior_bounds(end)
    days = _days(end)
    return {
        "value": _r(by_day[end]), "unit": "mmol/L", "day": end.isoformat(),
        "in_range_pct": _r(I._f(row.get("tir_pct")), 0),
        "spark": _series(by_day, days),
        "status": range_status(_values(by_day, days[0], end), _values(by_day, lo, hi)),
    }


def build_steps(daily: dict[date, dict[str, Any]], end: date) -> dict[str, Any] | None:
    row = daily.get(end)
    if not row or row.get("steps_total") is None:
        return None
    by_day = {d: I._f(r.get("steps_total")) for d, r in daily.items()}
    lo, hi = _prior_bounds(end)
    days = _days(end)
    win = _values(by_day, days[0], end)
    return {
        "avg": _r(_mean(win), 0), "spark": _series(by_day, days, 0),
        "status": range_status(win, _values(by_day, lo, hi), 0),
    }


def nutrient(meals: list[dict[str, Any]], key: str, limit: float) -> dict[str, Any]:
    """Salt or sugar over the meals of the last 7 days. `unknown` when no meal has the value; otherwise `high` once enough meals are over
    the meal limit (the same limits as the Food insights and /nutrition/flags). A meal without the value is not counted as over."""
    known = [m[key] for m in meals if m.get(key) is not None]
    if not known:
        return {"state": "unknown", "high_meals": None, "meals": len(meals)}
    over = sum(1 for v in known if float(v) >= limit)
    return {"state": "high" if over >= HIGH_MEALS_FOR_HIGH else "ok", "high_meals": over, "meals": len(meals)}


def build_calories(diet: list[dict[str, Any]], end: date) -> dict[str, Any] | None:
    """`diet` is `diet_days.summarise_days` output covering the 60 days before the window and the window. Calories = the mean daily
    energy of the days that have a logged meal (a day with an unknown meal value is left out)."""
    if not any(d["meals"] for d in diet):
        return None
    by_day: dict[date, float | None] = {date.fromisoformat(d["date"]): d["totals"]["kcal"] for d in diet}
    lo, hi = _prior_bounds(end)
    days = _days(end)
    win = _values(by_day, days[0], end)
    window_meals = [m for d in diet if days[0].isoformat() <= d["date"] <= end.isoformat() for m in d["meal_list"]]
    return {
        "avg_kcal": _r(_mean(win), 0),
        "sugar": nutrient(window_meals, "sugar_g", settings.meal_high_sugar_g),
        "salt": nutrient(window_meals, "sodium_mg", settings.meal_high_sodium_mg),
        "spark": _series(by_day, days, 0),
        "status": range_status(win, _values(by_day, lo, hi), 0),
    }


def build_heart(rows: list[dict[str, Any]], daily: dict[date, dict[str, Any]], prior_hr: dict[date, float], prior_o2: dict[date, float],
                end: date) -> dict[str, Any] | None:
    """`rows` = the watch buckets of the 7 days ending `end` (the heart insight's own input). The values are the heart insight's 7-day
    averages; the usual range is the person's daily watch averages over the 60 days before."""
    s = IH.summarize(rows, daily, end, WINDOW_DAYS)
    if not s["has_data"]:
        return None
    lo, hi = _prior_bounds(end)
    start = end - timedelta(days=WINDOW_DAYS - 1)
    win_hr = [float(d["avg"]) for d in s["days"] if d["avg"] is not None]
    win_o2 = _values(_o2_by_day(rows, start, end), start, end)
    hr_status = range_status(win_hr, _values(prior_hr, lo, hi))
    o2_status = range_status(win_o2, _values(prior_o2, lo, hi))
    return {"bpm": s["heart_rate"]["avg"], "resting_bpm": s["heart_rate"]["resting_avg"], "spo2": s["spo2"]["avg"],
            "status": hr_status, "spo2_status": o2_status}


def _o2_by_day(rows: list[dict[str, Any]], lo: date, hi: date) -> dict[date, float | None]:
    acc: dict[date, list[float]] = {}
    for w in rows:
        d = w["recorded_at"].astimezone(TZ).date()
        if lo <= d <= hi and w.get("spo2_pct") is not None:
            acc.setdefault(d, []).append(float(w["spo2_pct"]))
    return {d: _mean(v) for d, v in acc.items()}


def build_chart(chart_end: date, daily: dict[date, dict[str, Any]], diet: list[dict[str, Any]], hr_by_day: dict[date, float]) -> dict[str, Any]:
    days = _days(chart_end)
    kcal = {date.fromisoformat(d["date"]): d["totals"]["kcal"] for d in diet}
    return {
        "days": [d.isoformat() for d in days],
        "glucose": _series({d: I._f(r.get("glucose_mean_mmol")) for d, r in daily.items()}, days),
        "steps": _series({d: I._f(r.get("steps_total")) for d, r in daily.items()}, days, 0),
        "calories": _series(kcal, days, 0),
        "heart_rate": _series(hr_by_day, days),
    }


# ───────────────────────────────────────────────────────────────── today's plan (pure)
def _meal_status(start: float, end: float, hour: float, logged: bool) -> str:
    if logged:
        return "done"
    if hour < start:
        return "later"
    return "due" if hour < end else "missed"


def _dose_status(row_status: str | None, at: datetime, now: datetime) -> str:
    """taken = done; answered missed = missed; otherwise by the clock: before the dose time later, from the dose time to +60 minutes
    due (dose_timing.in_window), after that missed (not answered)."""
    if row_status == "taken":
        return "done"
    if row_status == "missed":
        return "missed"
    if now < at:
        return "later"
    return "due" if now <= at + timedelta(minutes=DOSE_WINDOW_MIN) else "missed"


def _step_state(items: list[dict[str, Any]]) -> str:
    states = [i["status"] for i in items]
    if all(s == "done" for s in states):
        return "done"
    if "due" in states:
        return "now"
    if "later" in states:
        return "later"
    return "missed"


def build_plan(today: date, now: datetime, logged_meals: set[str], doses: list[dict[str, Any]]) -> dict[str, Any]:
    """Today's meals and medicines in time order, items that share a clock time grouped in one step.

    `logged_meals` = meal types logged today. `doses` = rows with `time` (clock time), `title`, `status` (the dose row's status, or None
    when there is no row), `id` (the row id or None). Meals sit at the start of their mealtime window (the same windows as the meal
    reminder); a meal is due while its window is open and it is not logged. Items: meals first, then medicines."""
    now = now.astimezone(TZ)
    hour = now.hour + now.minute / 60
    by_time: dict[time, list[dict[str, Any]]] = {}
    for start, end, key, _label in logstore.MEAL_WINDOWS:
        t = time(int(start), int(round((start % 1) * 60)))
        by_time.setdefault(t, []).append({"kind": "meal", "title": MEAL_TYPES[key], "status": _meal_status(start, end, hour, key in logged_meals),
                                          "dose_id": None, "meal_type": key})
    for d in sorted(doses, key=lambda d: (d["time"], d["title"].lower())):
        at = datetime.combine(today, d["time"], TZ)
        status = _dose_status(d.get("status"), at, now)
        answered = d.get("status") in ("taken", "missed")
        by_time.setdefault(d["time"].replace(second=0, microsecond=0), []).append(
            {"kind": "dose", "title": d["title"], "status": status, "dose_id": None if answered else d.get("id"), "meal_type": None})
    steps = []
    for t in sorted(by_time):
        items = sorted(by_time[t], key=lambda i: i["kind"] != "meal")           # stable: meals first, doses keep their order
        steps.append({"time": t.strftime("%H:%M"), "label": _clock12(t), "state": _step_state(items), "items": items})
    now_idx = next((i for i, s in enumerate(steps) if s["state"] == "now"), None)
    if now_idx is None:
        now_idx = next((i for i, s in enumerate(steps) if s["state"] == "later"), None)
    flat = [i for s in steps for i in s["items"]]
    return {"date": today.isoformat(), "done": sum(1 for i in flat if i["status"] == "done"), "total": len(flat), "now_index": now_idx, "steps": steps}


def dose_label(name: str, strength: str | None) -> str:
    """'Metformin 500 mg': the person's own label (the strength is added only when the name does not already hold it)."""
    n = " ".join((name or "").split())
    s = " ".join((strength or "").split())
    return n if not s or s.lower() in n.lower() else f"{n} {s}"


# ───────────────────────────────────────────────────────────────── reading the rows
def _plan_doses(conn: Any, user: str, now: datetime) -> list[dict[str, Any]]:
    """The scheduled (not as-needed), current medicines with their dose row for today. Today's rows are made for other people (as the
    dose banner does); for Mr Tan nothing is made and a dose without a row is worked out from the clock."""
    if not logstore.is_read_only(user):
        old = conn.row_factory
        conn.row_factory = tuple_row                      # dose_store.ensure_rows unpacks plain tuples
        try:
            dose_store.ensure_rows(conn, user, now)
        finally:
            conn.row_factory = old
    today = now.astimezone(TZ).date()
    lo = datetime.combine(today, time(0), TZ)
    rows = conn.execute(
        """select s.dose_time, s.created_at, m.name, m.strength, l.id lid, l.status::text lstatus
           from medication_schedule s join medications m on m.id = s.medication_id
                left join medication_log l on l.schedule_id = s.id and l.scheduled_at >= %s and l.scheduled_at < %s
           where s.user_id = %s and s.deleted_at is null and m.deleted_at is null and s.dose_time is not null and m.as_needed is not true
                 and (m.end_date is null or m.end_date >= %s)""",
        (lo, lo + timedelta(days=1), user, today)).fetchall()
    out = []
    for r in rows:
        at = datetime.combine(today, r["dose_time"], TZ)
        if r["lid"] is None and at < r["created_at"]:      # the medicine did not exist yet at that time
            continue
        out.append({"time": r["dose_time"], "title": dose_label(r["name"], r["strength"]), "status": r["lstatus"],
                    "id": str(r["lid"]) if r["lid"] is not None else None})
    return out


def _logged_meal_types(conn: Any, user: str, today: date) -> set[str]:
    rows = conn.execute(
        "select distinct meal_type::text mt from food_logs where user_id=%s and deleted_at is null and (start_at at time zone 'Asia/Singapore')::date = %s",
        (user, today)).fetchall()
    return {r["mt"] for r in rows if r["mt"] in MEAL_TYPES}


def load_plan(conn: Any, user: str, now: datetime) -> dict[str, Any]:
    today = now.astimezone(TZ).date()
    return build_plan(today, now, _logged_meal_types(conn, user, today), _plan_doses(conn, user, now))


def _watch_daily(conn: Any, user: str, lo: date, hi: date) -> tuple[dict[date, float], dict[date, float]]:
    """Each day's average watch heart rate and SpO2 from `lo` to `hi` (a day without readings is missing, not 0)."""
    rows = conn.execute(
        """select (recorded_at at time zone 'Asia/Singapore')::date d, avg(heart_rate_bpm) hr, avg(spo2_pct) o2 from watch_readings
           where user_id=%s and recorded_at >= %s and recorded_at < %s group by 1""",
        (user, datetime.combine(lo, time(0), TZ), datetime.combine(hi + timedelta(days=1), time(0), TZ))).fetchall()
    return ({r["d"]: float(r["hr"]) for r in rows if r["hr"] is not None}, {r["d"]: float(r["o2"]) for r in rows if r["o2"] is not None})


def load_kpis(conn: Any, user: str, today: date) -> dict[str, Any]:
    """The four cards, the chart and `as_of`. Each card ends on the latest day with ITS OWN data (Insights' rule); the chart and the
    food card end on the overall latest day."""
    g_end = I.anchor(conn, user, today, "glucose")
    s_end = I.anchor(conn, user, today, "steps")
    all_end = I.anchor(conn, user, today)
    last_watch = IH._last_watch_day(conn, user, today)
    h_end = last_watch or all_end
    ends = [g_end, s_end, all_end, h_end]
    lo = min(_prior_bounds(e)[0] for e in ends)
    daily = I._daily(conn, user, lo, max(ends))
    diet = diet_days.progress_days(_prior_bounds(all_end)[0], all_end)["days"]
    hr_by_day, o2_by_day = _watch_daily(conn, user, min(_prior_bounds(h_end)[0], _days(all_end)[0]), max(h_end, all_end))
    heart = None
    if last_watch:
        rows = IH._watch(conn, user, h_end - timedelta(days=WINDOW_DAYS - 1), h_end)
        heart = build_heart(rows, daily, hr_by_day, o2_by_day, h_end)
    glucose, steps, calories = build_glucose(daily, g_end), build_steps(daily, s_end), build_calories(diet, all_end)
    shown = [d for d, k in ((g_end, glucose), (s_end, steps), (all_end, calories), (h_end, heart)) if k is not None]
    return {"as_of": max(shown).isoformat() if shown else None, "glucose": glucose, "steps": steps, "calories": calories, "heart": heart,
            "chart": build_chart(all_end, daily, diet, hr_by_day)}


CACHE_SECONDS = 20          # the four cards and the chart for one person are reused this long; a meal logged by that person ends it at once
_kpi_cache: dict[str, tuple[float, int, dict[str, Any]]] = {}


def overview(now: datetime | None = None, clock: float | None = None) -> dict[str, Any]:
    """The whole overview for the current person with ONE connection. The cards and chart are cached for CACHE_SECONDS and until that
    person logs something (logstore.log_epoch, as the banner does). The plan is always read fresh: a dose marked taken must show at once.
    `clock` is a monotonic time for tests."""
    now = now or datetime.now(TZ)
    t = _time.monotonic() if clock is None else clock
    key = logstore.current_user_key()
    epoch = logstore.log_epoch(key)
    user = str(logstore.current_user())
    hit = _kpi_cache.get(key)
    with logstore.one_connection() as conn:
        if hit and hit[1] == epoch and t < hit[0]:
            kpis = hit[2]
        else:
            kpis = load_kpis(conn, user, now.astimezone(TZ).date())
            _kpi_cache[key] = (t + CACHE_SECONDS, epoch, kpis)
        plan = load_plan(conn, user, now)
    return {"plan": plan, **kpis}
