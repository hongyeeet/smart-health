"""The "What gets in the way" dashboard row on K2: a few numbers from the database, each with its window. Read only.

Sources: `medication_log` (one row per scheduled dose, with `status` and `miss_reason`) for the doses, and `memory_facts` for the
barrier ideas the person has confirmed or that are still waiting. A number with nothing behind it is None, which the screen shows as
a dash with "No data yet". Zero is a real count and is shown as zero.
The on-time rule (taken within 60 minutes after the dose time) is the one `adherence.on_time_by_week` uses.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from app.db.logstore import TZ, current_user, tx
from app.db.memorystore import hidden_keys
from app.services.insights import MISS_LABELS

WINDOW_DAYS = 30
ON_TIME_MINUTES = 60


def _midnight(d: date) -> datetime:
    return datetime.combine(d, time.min, TZ)


def summarise(today: date, week: dict[str, int], window: dict[str, int], reasons: list[dict[str, Any]], facts: dict[str, int]) -> dict[str, Any]:
    """Pure: the KPI numbers from the raw counts. `week` has scheduled and missed; `window` has confirmed (taken or missed), on_time and
    missed for the last WINDOW_DAYS days; `reasons` is [{key, n}] for missed doses with a reason; `facts` has active and proposed."""
    scheduled, missed_week = week.get("scheduled", 0), week.get("missed", 0)
    confirmed, on_time = window.get("confirmed", 0), window.get("on_time", 0)
    reason_total = sum(r["n"] for r in reasons)
    top = None
    if reasons:
        best = min(reasons, key=lambda r: (-r["n"], r["key"]))
        top = {"key": best["key"], "label": MISS_LABELS.get(best["key"], best["key"]), "count": best["n"], "missed": reason_total}
    return {
        "windowDays": WINDOW_DAYS,
        "weekStart": (today - timedelta(days=today.weekday())).isoformat(),
        "scheduledThisWeek": scheduled,
        "missedThisWeek": missed_week if scheduled else None,
        "confirmedDoses": confirmed,
        "onTimePct": round(100 * on_time / confirmed) if confirmed else None,
        "topReason": top,
        "confirmedBarriers": facts.get("active", 0),
        "waitingBarriers": facts.get("proposed", 0),
    }


def summary() -> dict[str, Any]:
    uid = current_user()
    today = datetime.now(TZ).date()
    week_start = today - timedelta(days=today.weekday())
    week_lo, week_hi = _midnight(week_start), _midnight(week_start + timedelta(days=7))
    win_lo, win_hi = _midnight(today - timedelta(days=WINDOW_DAYS - 1)), _midnight(today + timedelta(days=1))
    # Doses from medicines that were deleted, or that are only taken when needed, are not part of the schedule.
    scope = """join medications m on m.id = l.medication_id and m.deleted_at is null and not coalesce(m.as_needed, false)
               where l.user_id=%s"""
    with tx() as c:
        w = c.execute(
            f"""select count(*) scheduled, count(*) filter (where l.status='missed') missed from medication_log l {scope}
                and l.scheduled_at >= %s and l.scheduled_at < %s""",
            (uid, week_lo, week_hi),
        ).fetchone()
        o = c.execute(
            f"""select count(*) filter (where l.status in ('taken','missed')) confirmed,
                       count(*) filter (where l.status='taken' and l.taken_at - l.scheduled_at <= interval '{ON_TIME_MINUTES} minutes') on_time,
                       count(*) filter (where l.status='missed') missed
                from medication_log l {scope} and l.scheduled_at >= %s and l.scheduled_at < %s""",
            (uid, win_lo, win_hi),
        ).fetchone()
        reasons = c.execute(
            f"""select l.miss_reason::text key, count(*) n from medication_log l {scope}
                and l.status='missed' and l.miss_reason is not null and l.scheduled_at >= %s and l.scheduled_at < %s
                group by 1 order by n desc, key""",
            (uid, win_lo, win_hi),
        ).fetchall()
        f = c.execute(
            """select count(*) filter (where status='active') active, count(*) filter (where status='proposed') proposed
               from memory_facts where user_id=%s and category::text='barrier' and key <> all(%s)""",
            (uid, hidden_keys(uid)),
        ).fetchone()
    return summarise(
        today,
        {"scheduled": int(w["scheduled"]), "missed": int(w["missed"] or 0)},
        {"confirmed": int(o["confirmed"]), "on_time": int(o["on_time"]), "missed": int(o["missed"] or 0)},
        [{"key": r["key"], "n": int(r["n"])} for r in reasons],
        {"active": int(f["active"]), "proposed": int(f["proposed"])},
    )
