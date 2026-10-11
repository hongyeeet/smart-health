"""The Me care screens (K3 Care plan, K7 Plan an appointment, K4 Connected sources).

Pure rules first (unit-tested), then the small SQL functions the router runs in one transaction. A preventive check is due or overdue
only by its stored next date; nothing here says what a person should do about it. Thresholds (30 days, 24 hours) are placeholders
pending clinical review and are never shown as advice.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import psycopg

from app.core.errors import InvalidTransition, NotFound, ValidationFailed
from psycopg.types.json import Jsonb

TZ = ZoneInfo("Asia/Singapore")
DUE_SOON_DAYS = 30
FRESH_HOURS = 24

KIND_LABELS = {
    "gp_review": "GP review",
    "diabetes_review": "Diabetes review",
    "eye_screening": "Eye screening",
    "foot_screening": "Foot check",
    "kidney_test": "Kidney test",
    "hba1c_test": "HbA1c blood test",
    "vaccination": "Vaccination",
    "dental": "Dental check",
    "other": "Other visit",
}
# Visits: the kinds a person can log now. Old visits of a removed kind (vaccination, dental) keep their old label in KIND_LABELS.
APPOINTMENT_KIND_LABELS = {
    "gp_review": "GP review",
    "diabetes_review": "Diabetes review",
    "eye_screening": "Eye screening",
    "foot_screening": "Foot check",
    "kidney_test": "Kidney test",
    "hba1c_test": "Blood test",
    "other": "Other visit",
}
NEW_APPOINTMENT_KINDS = tuple(APPOINTMENT_KIND_LABELS)   # the kinds the Log an appointment form offers
# The order the checks are listed in on K3 (the same order the team wrote them down).
PREVENTIVE_ORDER = ["eye_screening", "foot_screening", "kidney_test", "hba1c_test", "vaccination", "diabetes_review"]
ORIGIN_LABELS = {
    "user": "Added by you",
    "refused_chat": "From your chat",
    "checkin": "From your check-in",
    "agent_suggested": "Suggested by Smart Health",
}
# A question marked done is stored as "asked" (the table's status check has no "done"); "open" is on the list, "archived" is removed.
DONE_STATUS = "asked"
OPEN_STATUS = "open"
SUGGESTED_BECAUSE = {"overdue": "Suggested because it is overdue.", "due_soon": "Suggested because it is due soon."}
SOURCE_LABELS = {"cgm": "Glucose sensor", "watch": "Watch", "camera": "Photo camera"}

APPT_COLS = "id, kind, status, scheduled_for, location, suggested_reason, confirmed_by_user_at"


# ───────────────────────────────────────────────────────────────── pure helpers
def _day(d: date) -> str:
    return f"{d.day} {d:%b} {d.year}"


def _clock(dt: datetime) -> str:
    h = dt.hour % 12 or 12
    return f"{h}:{dt.minute:02d} {'am' if dt.hour < 12 else 'pm'}"


def _local(dt: datetime) -> datetime:
    return dt.astimezone(TZ)


def _aware(dt: datetime) -> datetime:
    """A naive time from the form is Singapore time."""
    return dt if dt.tzinfo else dt.replace(tzinfo=TZ)


def today_sg(now: datetime) -> date:
    return _local(now).date()


def preventive_status(next_due_on: date | None, today: date) -> str:
    """ok, due_soon, overdue or unknown, from the stored next date only."""
    if next_due_on is None:
        return "unknown"
    if next_due_on < today:
        return "overdue"
    if (next_due_on - today).days <= DUE_SOON_DAYS:
        return "due_soon"
    return "ok"


def preventive_detail(status: str, last_done_on: date | None, next_due_on: date | None) -> str:
    """One plain line: what is on record, nothing more."""
    last = f"Last done {_day(last_done_on)}." if last_done_on else "No date for the last one on record."
    if next_due_on is None:
        return f"{last} No next date on record." if last_done_on else "No date on record yet."
    if status == "overdue":
        return f"{last} Was due {_day(next_due_on)}."
    return f"{last} Next due {_day(next_due_on)}."


def scheduled_label(dt: datetime) -> str:
    local = _local(dt)
    return f"{local:%a} {local.day} {local:%b}, {_clock(local)}"


def short_when(dt: datetime) -> str:
    local = _local(dt)
    return f"{local.day} {local:%b} {local:%H:%M}"


def suggested_text(reason: Any) -> str | None:
    if not isinstance(reason, dict):
        return None
    return SUGGESTED_BECAUSE.get(str(reason.get("due")), "Suggested by Smart Health.")


def freshness(last_at: datetime | None, now: datetime) -> str:
    if last_at is None:
        return "none"
    return "up_to_date" if now - last_at <= timedelta(hours=FRESH_HOURS) else "old"


def source_row(key: str, model: str | None, last_at: datetime | None, now: datetime) -> dict[str, Any]:
    """One feed: connected or not, when the last data came, and a plain note. Connecting is not available yet."""
    label = SOURCE_LABELS[key]
    if key == "camera":
        return {"key": key, "label": label, "model": None, "status": "on_device", "status_label": "On this device",
                "last_data_at": None, "freshness": "none",
                "note": "Meal photos and medicine labels use this device's camera. There is nothing to connect."}
    if not model:
        return {"key": key, "label": label, "model": None, "status": "not_connected", "status_label": "Not connected",
                "last_data_at": None, "freshness": "none",
                "note": f"Connecting a {label.lower()} is not available yet."}
    fresh = freshness(last_at, now)
    if last_at is None:
        return {"key": key, "label": label, "model": model, "status": "connected_no_data", "status_label": "Connected, no data yet",
                "last_data_at": None, "freshness": "none", "note": "Readings will show here once they arrive."}
    note = "Up to date." if fresh == "up_to_date" else "No new data for more than a day."
    return {"key": key, "label": label, "model": model, "status": "connected", "status_label": f"Connected, last data {short_when(last_at)}",
            "last_data_at": last_at, "freshness": fresh, "note": note}


def _kind_label(kind: str) -> str:
    return KIND_LABELS[kind]


def _visit_kind_label(kind: str) -> str:
    return APPOINTMENT_KIND_LABELS.get(kind) or KIND_LABELS[kind]


def appointment_out(row: dict[str, Any]) -> dict[str, Any]:
    when = row["scheduled_for"]
    return {
        "id": str(row["id"]),
        "kind": row["kind"],
        "kind_label": _visit_kind_label(row["kind"]),
        "status": row["status"],
        "scheduled_for": when,
        "scheduled_label": scheduled_label(when) if when else None,
        "location": row["location"],
        "suggested_reason": suggested_text(row["suggested_reason"]),
        "confirmed_at": row["confirmed_by_user_at"],
    }


def question_out(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "text": row["text"],
        "origin": row["origin"],
        "origin_label": ORIGIN_LABELS.get(row["origin"] or "", "Saved"),
        "status": row["status"],
        "created_at": row["created_at"],
        "can_remove": row["status"] in (OPEN_STATUS, DONE_STATUS),   # both are on the list; archived ones are not returned
    }


# ───────────────────────────────────────────────────────────────── one rule for "next appointment"
def is_next_visit(status: str, scheduled_for: datetime | None, now: datetime) -> bool:
    """THE rule for the next appointment, used by K3 and the L1 brief: a visit the person confirmed (planned, so not cancelled,
    missed or completed) whose time has not passed yet. A visit whose time has passed is not next; it is listed as Past."""
    return status == "planned" and scheduled_for is not None and scheduled_for >= now


def pick_next_visit(rows: list[dict[str, Any]], now: datetime) -> dict[str, Any] | None:
    """The earliest visit that is next under `is_next_visit`, or None when there is none."""
    due = [r for r in rows if is_next_visit(r["status"], r["scheduled_for"], now)]
    return min(due, key=lambda r: (r["scheduled_for"], str(r["id"]))) if due else None


def split_visits(rows: list[dict[str, Any]], now: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """From the live rows (planned and suggested): the upcoming visits, and the earlier ones (planned, time passed, newest first).
    An earlier visit is returned with status "past", so it is never shown as Planned."""
    upcoming = [appointment_out(r) for r in rows if r["scheduled_for"] is None or r["scheduled_for"] >= now]
    past = sorted((r for r in rows if r["status"] == "planned" and r["scheduled_for"] is not None and r["scheduled_for"] < now),
                  key=lambda r: r["scheduled_for"], reverse=True)
    return upcoming, [{**appointment_out(r), "status": "past"} for r in past]


def next_appointment(conn: psycopg.Connection, user_id: str, now: datetime) -> dict[str, Any] | None:
    """The next appointment for one person under the one rule above. The L1 brief (share.context) and K3 both use this."""
    rows = conn.execute(f"select {APPT_COLS} from appointments where user_id = %s and status = 'planned'", (user_id,)).fetchall()
    row = pick_next_visit(rows, now)
    return appointment_out(row) if row else None


# ───────────────────────────────────────────────────────────────── K3 Care plan
def load_plan(conn: psycopg.Connection, user_id: str, now: datetime) -> dict[str, Any]:
    today = today_sg(now)
    live = _live_rows(conn, user_id)
    upcoming, earlier = split_visits(live, now)
    next_row = pick_next_visit(live, now)
    next_visit = appointment_out(next_row) if next_row else None

    prev_rows = conn.execute(
        """select i.kind, s.last_done_on, s.next_due_on
           from preventive_items i
           left join patient_preventive_status s on s.preventive_item_id = i.id and s.user_id = %s""",
        (user_id,),
    ).fetchall()
    prev_rows.sort(key=lambda r: PREVENTIVE_ORDER.index(r["kind"]) if r["kind"] in PREVENTIVE_ORDER else len(PREVENTIVE_ORDER))
    preventive = []
    for r in prev_rows:
        status = preventive_status(r["next_due_on"], today)
        preventive.append({
            "kind": r["kind"], "label": _kind_label(r["kind"]), "status": status,
            "last_done_on": r["last_done_on"], "next_due_on": r["next_due_on"],
            "detail": preventive_detail(status, r["last_done_on"], r["next_due_on"]),
        })

    # Open questions newest first, then the done ones (newest first).
    questions = [question_out(r) for r in conn.execute(
        """select id, text, origin, status, created_at from doctor_questions
           where user_id = %s and status in ('open', 'asked') order by (status = 'open') desc, created_at desc""",
        (user_id,),
    ).fetchall()]
    return {"next_appointment": next_visit, "upcoming": upcoming, "earlier": earlier, "preventive": preventive, "questions": questions}


def add_question(conn: psycopg.Connection, user_id: str, text: str) -> dict[str, Any]:
    row = conn.execute(
        """insert into doctor_questions (user_id, text, origin, status) values (%s, %s, 'user', 'open')
           returning id, text, origin, status, created_at""",
        (user_id, text),
    ).fetchone()
    return question_out(row)


def archive_question(conn: psycopg.Connection, user_id: str, question_id: str) -> dict[str, str]:
    """Soft remove: the row stays, marked archived. An open or done question can be taken off the list; a removed one cannot."""
    row = conn.execute("select status from doctor_questions where id = %s and user_id = %s", (question_id, user_id)).fetchone()
    if row is None:
        raise NotFound("That question is not on your list.")
    if row["status"] not in (OPEN_STATUS, DONE_STATUS):
        raise InvalidTransition("That question has already been removed.")
    conn.execute("update doctor_questions set status = 'archived' where id = %s and user_id = %s", (question_id, user_id))
    return {"id": question_id, "status": "archived"}


def set_question_done(conn: psycopg.Connection, user_id: str, question_id: str, done: bool) -> dict[str, Any]:
    """Mark a question done (status asked) or put it back on the open list. Ids only in the event log."""
    row = conn.execute(
        "select status from doctor_questions where id = %s and user_id = %s", (question_id, user_id)
    ).fetchone()
    if row is None:
        raise NotFound("That question is not on your list.")
    if row["status"] not in (OPEN_STATUS, DONE_STATUS):
        raise InvalidTransition("That question has already been removed.")
    target = DONE_STATUS if done else OPEN_STATUS
    if row["status"] != target:
        conn.execute("update doctor_questions set status = %s where id = %s and user_id = %s", (target, question_id, user_id))
        conn.execute(
            "insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'user', %s, 'doctor_questions', %s, %s)",
            (user_id, "doctor_question.done" if done else "doctor_question.reopened", question_id, Jsonb({})),
        )
    out = conn.execute(
        "select id, text, origin, status, created_at from doctor_questions where id = %s and user_id = %s", (question_id, user_id)
    ).fetchone()
    return question_out(out)


# ───────────────────────────────────────────────────────────────── K7 Plan an appointment
def _live_rows(conn: psycopg.Connection, user_id: str) -> list[dict[str, Any]]:
    """Visits still open: planned or suggested. Cancelled, missed and completed ones are not live."""
    return conn.execute(
        f"""select {APPT_COLS} from appointments where user_id = %s and status in ('planned', 'suggested')
            order by scheduled_for nulls last, created_at""",
        (user_id,),
    ).fetchall()


def list_appointments(conn: psycopg.Connection, user_id: str, now: datetime) -> list[dict[str, Any]]:
    """The visits still to come (K7 list). A visit whose time has passed is not here; K3 lists it under Earlier visits."""
    upcoming, _ = split_visits(_live_rows(conn, user_id), now)
    return upcoming


def add_appointment(conn: psycopg.Connection, user_id: str, kind: str, scheduled_for: datetime,
                    suggested_id: str | None, now: datetime) -> dict[str, Any]:
    """Save a visit the person has confirmed. A suggested visit is confirmed in place, so there is one row per visit.
    A new visit must be one of the kinds the form offers; a suggested one may keep its older kind. The place is no longer asked."""
    when = _aware(scheduled_for)
    if when <= now:
        raise ValidationFailed("Pick a time in the future.")
    if suggested_id:
        row = conn.execute("select status, kind from appointments where id = %s and user_id = %s", (suggested_id, user_id)).fetchone()
        if row is None:
            raise NotFound("That visit is not on your list.")
        if row["status"] != "suggested":
            raise InvalidTransition("That visit is already confirmed or closed.")
        if kind not in NEW_APPOINTMENT_KINDS and kind != row["kind"]:
            raise ValidationFailed("Pick a kind of visit from the list.")
        out = conn.execute(
            f"""update appointments set kind = %s, status = 'planned', scheduled_for = %s,
                   confirmed_by_user_at = now(), updated_at = now()
                where id = %s and user_id = %s returning {APPT_COLS}""",
            (kind, when, suggested_id, user_id),
        ).fetchone()
    else:
        if kind not in NEW_APPOINTMENT_KINDS:
            raise ValidationFailed("Pick a kind of visit from the list.")
        out = conn.execute(
            f"""insert into appointments (user_id, kind, status, scheduled_for, confirmed_by_user_at)
                values (%s, %s, 'planned', %s, now()) returning {APPT_COLS}""",
            (user_id, kind, when),
        ).fetchone()
    return appointment_out(out)


def cancel_appointment(conn: psycopg.Connection, user_id: str, appointment_id: str) -> dict[str, Any]:
    """Sets the status to cancelled; the row stays so the history is kept."""
    row = conn.execute("select status from appointments where id = %s and user_id = %s", (appointment_id, user_id)).fetchone()
    if row is None:
        raise NotFound("That visit is not on your list.")
    if row["status"] not in ("planned", "suggested"):
        raise InvalidTransition("This visit is already closed.")
    out = conn.execute(
        f"update appointments set status = 'cancelled', updated_at = now() where id = %s and user_id = %s returning {APPT_COLS}",
        (appointment_id, user_id),
    ).fetchone()
    return appointment_out(out)


# ───────────────────────────────────────────────────────────────── K4 Connected sources
def load_sources(conn: psycopg.Connection, user_id: str, now: datetime) -> dict[str, Any]:
    profile = conn.execute("select cgm_model, watch_model from user_profile where user_id = %s", (user_id,)).fetchone() or {}
    cgm_last = conn.execute("select max(recorded_at) as last from cgm_readings where user_id = %s", (user_id,)).fetchone()["last"]
    watch_last = conn.execute("select max(recorded_at) as last from watch_readings where user_id = %s", (user_id,)).fetchone()["last"]
    return {"sources": [
        source_row("cgm", profile.get("cgm_model"), cgm_last, now),
        source_row("watch", profile.get("watch_model"), watch_last, now),
        source_row("camera", None, None, now),
    ]}
