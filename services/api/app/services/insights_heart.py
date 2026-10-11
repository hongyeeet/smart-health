"""Heart rate, SpO2 and blood pressure for Insights C4 (Activity) and C5 (Sleep and stress).

Read-only, and every number is computed in code from stored data (the same rule as app/services/insights.py; no model is called).
The rules match the doctor brief so the two never disagree:
- Watch readings come from `watch_readings`: one row per 5-minute bucket with heart rate, SpO2, steps and minutes asleep.
- A night belongs to the morning it ends on, and a bucket counts as asleep from SLEEP_BUCKET_MIN minutes: the brief's own rule
  (doctor_report._nights), reused and not copied.
- Resting heart rate per day is `daily_summary.resting_hr_bpm`, the daily summary the other tabs already read.
- Blood pressure is `recent_bp`, the same read the brief uses.

The period of this block ends on its OWN last day of watch data (today when there is none), not on the end the other Insights
tabs use. So a person whose watch data stops earlier still sees their last days of watch data. The screen says so when the end
day is earlier than today or than the other tabs' end day.

Unknown stays unknown: a day without watch data is a gap (None), never zero. SpO2 from a wrist watch is less accurate than a
fingertip meter; the screen says so. Nothing here says whether a value is normal, high or low.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

import psycopg

from app.services import insights as I
from app.services.blood_pressure import recent_bp
from app.services.doctor_report import Inputs, _nights

BP_MAX_READINGS = 30  # the table shows the newest readings; the count uses all of them


def _r1(x: float | None) -> float | None:
    return None if x is None else round(x, 1)


def _mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def pick_end(watch_last: date | None, today: date, other_end: date) -> tuple[date, bool]:
    """The end day of this block: its last watch day, or today when there is none. The second value is True when the screen
    should say "Showing your watch data up to ...": the end day is earlier than today, or earlier than the other tabs' end day."""
    end = watch_last or today
    return end, end < today or end < other_end


def _last_watch_day(conn: psycopg.Connection[Any], user: str, today: date) -> date | None:
    """The local day of the newest watch reading on or before `today`, or None when there is none."""
    before = datetime.combine(today + timedelta(days=1), datetime.min.time(), I.TZ)
    row = conn.execute("select max(recorded_at) t from watch_readings where user_id=%s and recorded_at < %s", (user, before)).fetchone()
    return row["t"].astimezone(I.TZ).date() if row and row["t"] else None


def period_end(conn: psycopg.Connection[Any], user: str, today: date) -> tuple[date, bool, date | None]:
    """(end day, show the "up to" line, last watch day). Used by both the heart block and blood pressure."""
    last = _last_watch_day(conn, user, today)
    end, note = pick_end(last, today, I.anchor(conn, user, today))
    return end, note, last


def _watch(conn: psycopg.Connection[Any], user: str, lo: date, hi: date) -> list[dict[str, Any]]:
    """Watch buckets for the period. Starts a day early: the night that began the evening before `lo` belongs to `lo`."""
    a = datetime.combine(lo - timedelta(days=1), datetime.min.time(), I.TZ)
    b = datetime.combine(hi + timedelta(days=1), datetime.min.time(), I.TZ)
    return [dict(r) for r in conn.execute(
        "select recorded_at, heart_rate_bpm, spo2_pct, sleep_minutes from watch_readings "
        "where user_id=%s and recorded_at >= %s and recorded_at < %s order by recorded_at", (user, a, b))]


def summarize(rows: list[dict[str, Any]], daily: dict[date, dict[str, Any]], end: date, days: int) -> dict[str, Any]:
    """The heart and SpO2 numbers for one period, from the watch buckets and the daily summary. Pure: no database.

    `rows` are watch buckets (recorded_at, heart_rate_bpm, spo2_pct, sleep_minutes); `daily` is daily_summary keyed by local date.
    """
    start, _ = I.window(end, days)
    inp = Inputs(now=datetime.now(I.TZ), tz=I.TZ, start=start, end=end, watch=rows)
    nights = _nights(inp)                                   # {"hr": {morning: [bpm]}, "o2": {morning: [pct]}}, asleep buckets only
    hr_day: dict[date, list[float]] = defaultdict(list)
    o2_day: dict[date, list[float]] = defaultdict(list)
    for w in rows:
        d = w["recorded_at"].astimezone(I.TZ).date()
        if not start <= d <= end:
            continue
        if w.get("heart_rate_bpm") is not None:
            hr_day[d].append(float(w["heart_rate_bpm"]))
        if w.get("spo2_pct") is not None:
            o2_day[d].append(float(w["spo2_pct"]))

    hr_all = [x for v in hr_day.values() for x in v]
    o2_all = [x for v in o2_day.values() for x in v]
    asleep_hr = [x for v in nights["hr"].values() for x in v]
    asleep_o2 = [x for v in nights["o2"].values() for x in v]
    resting = [float(daily[d]["resting_hr_bpm"]) for d in (start + timedelta(days=k) for k in range(days))
               if d in daily and daily[d].get("resting_hr_bpm") is not None]

    series = []
    for k in range(days):
        d = start + timedelta(days=k)
        dr = daily.get(d, {})
        series.append({
            "date": d.isoformat(),
            "avg": _r1(_mean(hr_day[d])) if hr_day.get(d) else None,
            "resting": _r1(float(dr["resting_hr_bpm"])) if dr.get("resting_hr_bpm") is not None else None,
            "asleep": _r1(_mean(nights["hr"][d])) if nights["hr"].get(d) else None,
        })

    has = bool(hr_all or o2_all)
    return {
        "period": I._period(end, days, has),
        "has_data": has,
        "days_with_data": len(set(hr_day) | set(o2_day)),
        "heart_rate": {
            "avg": _r1(_mean(hr_all)),
            "high": round(max(hr_all)) if hr_all else None,
            "low": round(min(hr_all)) if hr_all else None,
            "resting_avg": _r1(_mean(resting)),
            "asleep_avg": _r1(_mean(asleep_hr)),
        },
        "spo2": {
            "avg": _r1(_mean(o2_all)),
            "low": _r1(min(o2_all)) if o2_all else None,
            "asleep_avg": _r1(_mean(asleep_o2)),
            "asleep_low": _r1(min(asleep_o2)) if asleep_o2 else None,
        },
        "days": series,
    }


def heart(conn: psycopg.Connection[Any], user: str, days: int, today: date) -> dict[str, Any]:
    """C4 and C5: heart rate and SpO2 for the period, ending on the person's last day of watch data (today if none)."""
    end, note, last = period_end(conn, user, today)
    start, _ = I.window(end, days)
    rows = _watch(conn, user, start, end)
    daily = I._daily(conn, user, start, end)
    out = summarize(rows, daily, end, days)
    out["watch_end"] = last.isoformat() if last else None
    out["end_note"] = note
    return out


def blood_pressure(conn: psycopg.Connection[Any], user: str, days: int, today: date) -> dict[str, Any]:
    """C5: manual blood pressure readings from the same `days`-day period as the heart block (it ends on the same day), newest
    first. A reading logged after that end day is still listed, so the newest reading is never hidden. `latest` is its date."""
    end, _, _ = period_end(conn, user, today)
    start = end - timedelta(days=days - 1)
    span = (today - start).days + 1                          # recent_bp counts back from now
    rows = [r for r in recent_bp(conn, uuid.UUID(str(user)), span) if r["measured_at"].astimezone(I.TZ).date() >= start]
    readings = []
    for r in rows[:BP_MAX_READINGS]:
        local = r["measured_at"].astimezone(I.TZ)
        readings.append({
            "date": local.date().isoformat(), "time": local.strftime("%H:%M"),
            "systolic": int(r["systolic"]), "diastolic": int(r["diastolic"]), "pulse": None if r.get("pulse") is None else int(r["pulse"]),
        })
    return {"count": len(rows), "latest": readings[0]["date"] if readings else None, "readings": readings}
