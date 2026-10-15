"""The urgent low-glucose alert (screen J1).

No model is involved. A reading counts only when it is a quality-ok reading no older than 20 minutes; with no such reading there is no
alert (never a guess). The tier limits are placeholders from the owner (2026-10-03), mirrored from appConfig.hypoTiers, pending
clinical review.

State lives in one `notifications` row per alert (kind 'urgent', payload role 'alert'). Escalation adds a second row
(role 'contact', delivery_to 'contact') that the orchestrator's dispatcher sends; this module never sends anything.
"""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import psycopg

from app.agents.trace import audit
from app.services import texts

logger = logging.getLogger(__name__)
TZ = ZoneInfo("Asia/Singapore")

# Mirrors appConfig.hypoTiers and appConfig.emergencyNumber (apps/web/src/config/app.ts). Placeholders, not clinical advice.
LOW_BELOW = 4.0
VERY_LOW_BELOW = 3.0
RECHECK_MINUTES = 15
CONTACT_AFTER_MINUTES = 5
FRESH_MINUTES = 20
EMERGENCY_NUMBER = "995"

# The table only allows 'push', 'local' and 'in_app' as a channel, so the contact request uses 'in_app'; delivery_to='contact' is what
# tells the dispatcher to email it.
CONTACT_CHANNEL = "in_app"
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ----------------------------------------------------------------------------------------------- pure logic
def tier_for(value: float | None) -> str:
    """'very_low' below 3.0, 'low' below 4.0, otherwise 'none'. No value means 'none'."""
    if value is None:
        return "none"
    if value < VERY_LOW_BELOW:
        return "very_low"
    if value < LOW_BELOW:
        return "low"
    return "none"


def is_fresh(at: datetime | None, now: datetime) -> bool:
    """Not older than 20 minutes. A time in the future (a clock fault) does not count."""
    if at is None:
        return False
    age = now - at
    return timedelta(minutes=-1) <= age <= timedelta(minutes=FRESH_MINUTES)


def counting_reading(reading: dict | None, now: datetime) -> dict | None:
    """The reading if it can raise an alert: quality ok, fresh, and below the low limit. Otherwise None."""
    if not reading or not reading.get("quality_ok", True) or not is_fresh(reading.get("at"), now):
        return None
    return reading if tier_for(reading["value"]) != "none" else None


def _worse(a: str, b: str) -> str:
    order = {"none": 0, "low": 1, "very_low": 2}
    return a if order[a] >= order[b] else b


def resolve(now: datetime, reading: dict | None, alert: dict | None) -> dict[str, Any]:
    """The current alert from the latest reading and the latest stored alert (both may be None).

    reading: {at, value, quality_ok}. alert: {id, since, tier, value, demo, ack_at, recheck_at, escalated_at, email_queued}.
    Returns {tier, value, since, status, id, demo, recheck_at, contact_after, ack_at, escalated_at, email_queued}.
    """
    none = {"tier": "none", "value": None, "since": None, "status": "none", "id": None, "demo": False, "recheck_at": None,
            "contact_after": None, "escalated": False, "email_queued": False, "note": None}
    live_reading = counting_reading(reading, now)
    if alert:
        acked = alert.get("ack_at") is not None
        if acked:
            live = alert["recheck_at"] is not None and now <= alert["recheck_at"]
        else:
            live = timedelta(minutes=-1) <= now - alert["since"] <= timedelta(minutes=FRESH_MINUTES)
        if live and not alert["demo"] and reading and reading.get("quality_ok", True) and reading["at"] > alert["since"] \
                and is_fresh(reading["at"], now) and tier_for(reading["value"]) == "none":
            live = False  # a newer, fresh reading is back in range
        if live:
            tier, value = alert["tier"], alert["value"]
            if not alert["demo"] and live_reading and live_reading["at"] > alert["since"] and tier_for(live_reading["value"]) != "none":
                tier = _worse(tier, tier_for(live_reading["value"]))
                if tier != alert["tier"]:
                    value = live_reading["value"]  # it got worse: show the newer number
            status = "acknowledged" if acked else ("escalated" if alert.get("escalated_at") else "active")
            return {**none, "tier": tier, "value": value, "since": alert["since"], "status": status, "id": alert["id"], "demo": alert["demo"],
                    "recheck_at": alert["recheck_at"] if acked else None,
                    "contact_after": alert["since"] + timedelta(minutes=CONTACT_AFTER_MINUTES) if status == "active" else None,
                    "escalated": bool(alert.get("escalated_at")), "email_queued": bool(alert.get("email_queued")), "note": alert.get("note")}
        # an old alert is over; a reading counts again only if it came after that alert started
        if live_reading and live_reading["at"] <= alert["since"]:
            live_reading = None
    if live_reading:
        since = live_reading["at"]
        return {**none, "tier": tier_for(live_reading["value"]), "value": live_reading["value"], "since": since, "status": "active",
                "contact_after": since + timedelta(minutes=CONTACT_AFTER_MINUTES)}
    return none


def contact_message(name: str | None, value: float, at: datetime, demo: bool, lang: str = "en") -> tuple[str, str]:
    """The fixed wording of the email to the emergency contact. No advice beyond checking in and the emergency number.
    `lang` is the PERSON's language (the contact is told about the person); the English text is the source."""
    who = (name or "").strip() or texts.tr(lang, "urgent.contact.unnamed")
    clock = at.astimezone(TZ).strftime("%H:%M")
    body = texts.tr(lang, "urgent.contact.body", who=who, value=f"{value:.1f}", clock=clock, number=EMERGENCY_NUMBER)
    title = texts.tr(lang, "urgent.contact.title", who=who)
    if demo:
        return texts.tr(lang, "urgent.demo.title", title=title), texts.tr(lang, "urgent.demo.body", body=body)
    return title, body


def valid_email(email: str | None) -> bool:
    return bool(email) and bool(_EMAIL.match(email.strip()))


# ----------------------------------------------------------------------------------------------- database
_cols = {"ok": False, "checked": 0.0}


def delivery_columns_exist(conn: psycopg.Connection) -> bool:
    """Whether migration 0031 is applied. A yes is remembered for good; a no is re-checked at most once a minute."""
    if _cols["ok"]:
        return True
    if time.monotonic() - _cols["checked"] < 60:
        return False
    _cols["checked"] = time.monotonic()
    n = conn.execute(
        "select count(*) n from information_schema.columns where "
        "(table_name='notifications' and column_name in ('delivery_status','delivery_to')) or (table_name='user_profile' and column_name='emergency_contact_email')"
    ).fetchone()["n"]
    _cols["ok"] = n == 3
    return _cols["ok"]


def load_reading(conn: psycopg.Connection, user: Any) -> dict | None:
    r = conn.execute("select recorded_at, glucose_mmol, quality_ok from cgm_readings where user_id=%s and quality_ok order by recorded_at desc limit 1", (user,)).fetchone()
    return {"at": r["recorded_at"], "value": float(r["glucose_mmol"]), "quality_ok": r["quality_ok"]} if r else None


def _dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


def load_alert(conn: psycopg.Connection, user: Any) -> dict | None:
    r = conn.execute(
        "select id, payload from notifications where user_id=%s and kind='urgent' and payload->>'role'='alert' order by scheduled_for desc limit 1", (user,)
    ).fetchone()
    if not r:
        return None
    p = r["payload"]
    return {"id": str(r["id"]), "since": _dt(p["since"]), "tier": p["tier"], "value": float(p["value"]), "demo": bool(p.get("demo")),
            "ack_at": _dt(p.get("ackAt")), "recheck_at": _dt(p.get("recheckAt")), "escalated_at": _dt(p.get("escalatedAt")), "email_queued": bool(p.get("emailQueued")),
            "note": p.get("escalationNote")}


def _extra_contacts(conn: psycopg.Connection, user: Any) -> list[dict[str, Any]]:
    """The contacts added after the first (migration 0038), oldest first. [] while the table is not there yet."""
    if not conn.execute("select to_regclass('public.extra_emergency_contacts') t").fetchone()["t"]:
        return []
    rows = conn.execute(
        "select name, phone, email from extra_emergency_contacts where user_id=%s and deleted_at is null order by created_at, id", (user,)
    ).fetchall()
    out = []
    for r in rows:
        email = (r["email"] or "").strip() or None
        out.append({"name": (r["name"] or "").strip() or None, "phone": (r["phone"] or "").strip() or None, "email": email if valid_email(email) else None})
    return out


def load_contact(conn: psycopg.Connection, user: Any) -> dict[str, Any]:
    """The first contact (user_profile) plus `others`: every contact added later. The screen offers a phone or an email if ANY contact has one."""
    email_col = "emergency_contact_email" if delivery_columns_exist(conn) else "null::text"
    r = conn.execute(
        f"select display_name, emergency_contact_name n, emergency_contact_phone ph, {email_col} em from user_profile where user_id=%s", (user,)
    ).fetchone()
    others = _extra_contacts(conn, user)
    if not r:
        return {"person": None, "name": None, "phone": None, "email": None, "others": others}
    phone = (r["ph"] or "").strip() or None
    email = (r["em"] or "").strip() or None
    return {"person": r["display_name"], "name": (r["n"] or "").strip() or None, "phone": phone, "email": email if valid_email(email) else None, "others": others}


def contact_emails(contact: dict[str, Any]) -> list[tuple[str | None, str]]:
    """Every (name, email) the alert should be sent to: the first contact, then the others. Contacts without a usable email are left out."""
    people = [contact, *contact.get("others", [])]
    return [(c["name"], c["email"]) for c in people if c.get("email")]


def insert_contact_request(conn: psycopg.Connection, user: Any, alert_id: str, title: str, body: str, fields: dict[str, Any], suffix: str = "") -> None:
    """The only SQL that touches the 0031 columns. Call it only when delivery_columns_exist() is true. `suffix` tells the contacts apart."""
    payload = {"key": f"urgent-{alert_id}-contact{suffix}", "role": "contact", "title": title, "body": body, "to": "J1", **fields}
    # acted_at is set so the person does not see their contact's email text in their own notification list
    conn.execute(
        "insert into notifications (user_id, kind, scheduled_for, acted_at, action, channel, payload, delivery_status, delivery_to) "
        "values (%s,'urgent'::notification_kind,now(),now(),'contact_email',%s,%s::jsonb,'pending','contact')",
        (user, CONTACT_CHANNEL, json.dumps(payload, default=str)),
    )


def _insert_alert(conn: psycopg.Connection, user: Any, tier: str, value: float, since: datetime, demo: bool) -> str:
    aid = str(uuid.uuid4())
    lang = texts.person_language(user, conn=conn)
    title = texts.tr(lang, "urgent.demo_prefix") if demo else ""
    title += texts.tr(lang, "urgent.title.very_low" if tier == "very_low" else "urgent.title.low")
    payload = {"key": f"urgent-{aid}", "role": "alert", "title": title, "body": texts.tr(lang, "urgent.alert_body", value=f"{value:.1f}"), "to": "J1",
               "tier": tier, "value": value, "demo": demo, "since": since.isoformat()}
    conn.execute(
        "insert into notifications (id, user_id, kind, scheduled_for, sent_at, channel, payload) values (%s,%s,'urgent'::notification_kind,now(),now(),'in_app',%s::jsonb)",
        (aid, user, json.dumps(payload)),
    )
    if delivery_columns_exist(conn):
        conn.execute("update notifications set delivery_status='skipped', delivery_to='person' where id=%s", (aid,))
    return aid


def _patch(conn: psycopg.Connection, aid: str, **fields: Any) -> None:
    conn.execute("update notifications set payload = payload || %s::jsonb where id=%s", (json.dumps(fields, default=str), aid))


def view(state: dict[str, Any], contact: dict[str, Any], now: datetime) -> dict[str, Any]:
    """The response shape: the resolved state plus what the screen needs to offer (contact, channels)."""
    since = state["since"]
    return {
        "id": state["id"], "status": state["status"], "tier": state["tier"], "value": state["value"], "since": since,
        "age_minutes": max(0, int((now - since).total_seconds() // 60)) if since else None,
        "recheck_at": state["recheck_at"], "contact_after": state["contact_after"], "demo": state["demo"],
        "has_contact": bool(contact["name"] or contact["phone"] or contact["email"] or contact.get("others")),
        "contact_name": contact["name"] or next((o["name"] for o in contact.get("others", []) if o.get("name")), None),
        "contact_phone": contact["phone"] or next((o["phone"] for o in contact.get("others", []) if o.get("phone")), None),
        "channels": {"phone": bool(contact["phone"] or any(o.get("phone") for o in contact.get("others", []))), "email": bool(contact_emails(contact))},
        "email_queued": state["email_queued"], "escalated": state["escalated"], "escalation_note": state.get("note"),
        "emergency_number": EMERGENCY_NUMBER, "recheck_minutes": RECHECK_MINUTES, "contact_after_minutes": CONTACT_AFTER_MINUTES,
    }


def get_state(conn: psycopg.Connection, user: Any, now: datetime) -> dict[str, Any]:
    state = resolve(now, load_reading(conn, user), load_alert(conn, user))
    return view(state, load_contact(conn, user), now)


class NoAlert(Exception):
    """There is no active alert to act on."""


def _current(conn: psycopg.Connection, user: Any, now: datetime) -> dict[str, Any]:
    state = resolve(now, load_reading(conn, user), load_alert(conn, user))
    if state["tier"] == "none":
        raise NoAlert()
    if state["id"] is None:  # a real reading with no stored alert yet: store it now so the action has something to record against
        state["id"] = _insert_alert(conn, user, state["tier"], state["value"], state["since"], False)
        state["_new"] = True
    return state


def simulate(conn: psycopg.Connection, user: Any, value: float, now: datetime) -> tuple[dict, list[tuple]]:
    tier = tier_for(value)
    if tier == "none":
        raise ValueError(f"A demo alert needs a value below {LOW_BELOW}")
    aid = _insert_alert(conn, user, tier, value, now, True)
    events = [("urgent.demo_alert_created", aid, {"tier": tier, "value": value, "demo": True})]
    return get_state(conn, user, now), events


def acknowledge(conn: psycopg.Connection, user: Any, now: datetime) -> tuple[dict, list[tuple]]:
    state = _current(conn, user, now)
    recheck = now + timedelta(minutes=RECHECK_MINUTES)
    _patch(conn, state["id"], ackAt=now.isoformat(), recheckAt=recheck.isoformat())
    conn.execute("update notifications set acted_at=now(), action='acknowledged' where id=%s", (state["id"],))
    events = [("urgent.alert_created", state["id"], {"tier": state["tier"], "value": state["value"], "demo": state["demo"]})] if state.get("_new") else []
    events.append(("urgent.acknowledged", state["id"], {"tier": state["tier"], "value": state["value"], "demo": state["demo"], "recheckAt": recheck.isoformat()}))
    return get_state(conn, user, now), events


def escalate(conn: psycopg.Connection, user: Any, now: datetime) -> tuple[dict, list[tuple]]:
    state = _current(conn, user, now)
    aid = state["id"]
    events = [("urgent.alert_created", aid, {"tier": state["tier"], "value": state["value"], "demo": state["demo"]})] if state.get("_new") else []
    if state["escalated"]:  # already done: do not queue a second email
        return get_state(conn, user, now), events
    contact = load_contact(conn, user)
    title, body = contact_message(contact["person"], state["value"], state["since"], state["demo"], texts.person_language(user, conn=conn))
    queued, reason = False, None
    targets = contact_emails(contact)
    if not targets:
        reason = "no_contact_email"
    elif not delivery_columns_exist(conn):
        reason = "email_not_ready"
    else:
        for i, (cname, cemail) in enumerate(targets):       # one email request per contact
            insert_contact_request(conn, user, aid, title, body, {
                "tier": state["tier"], "value": state["value"], "demo": state["demo"], "contactName": cname, "contactEmail": cemail}, suffix="" if i == 0 else f"-{i + 1}")
        queued = True
    if queued:
        _patch(conn, aid, escalatedAt=now.isoformat(), emailQueued=True, escalationNote=None)
    else:   # nobody was told: the alert is not marked escalated, and the reason is kept so the screen can say so
        _patch(conn, aid, emailQueued=False, escalationNote=reason, escalationTriedAt=now.isoformat())
    events.append(("urgent.escalated", aid, {"tier": state["tier"], "value": state["value"], "demo": state["demo"], "emailQueued": queued, "reason": reason}))
    if queued:
        events.append(("urgent.contact_email_requested", aid, {"demo": state["demo"], "contactName": targets[0][0], "contacts": len(targets)}))  # the address itself is not logged
    return get_state(conn, user, now), events


def record(user: Any, events: list[tuple]) -> None:
    """Write the audit trail once the change has committed."""
    for event, aid, payload in events:
        audit(user, "user", event, "notifications", aid, payload)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
