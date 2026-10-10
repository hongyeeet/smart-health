"""Reminder emails (docs/specs/email-notifications.md).

Every notification is written to `notifications` first, for the app. A dispatcher then decides, row by row, whether it is also an email and
sends it through the Workato email recipe. The decision is a pure function (`decide`) so each rule can be tested:

  - only some kinds are emails (a meal, check-in, workout or lunch nudge, a refill, an appointment, an urgent alert);
  - the person needs an address and must not have turned emails off (an urgent alert goes to the EMERGENCY CONTACT's address instead);
  - a reminder that expired, or was already done in the app, is not sent late;
  - at most `email_daily_cap` reminder emails per person per day, and none in quiet hours (an urgent alert is exempt from both);
  - a send that fails is retried on the next minute up to `email_max_attempts`, then left as failed.

Each row ends as 'sent', 'failed' or 'skipped' with a short reason, and is never tried again, so nothing is sent twice. Addresses and tokens are
never logged. With no webhook configured nothing is sent and nothing is lost: rows stay pending until they expire.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Protocol

from app.core.config import settings
from app.db.logstore import TZ, in_quiet_hours, tx

logger = logging.getLogger(__name__)

ELIGIBLE_KINDS = {"nudge", "checkin", "refill", "appointment", "urgent"}
STALE_AFTER = {"urgent": timedelta(hours=2)}          # a row with no expiry is not sent after this long
DEFAULT_STALE = timedelta(hours=6)
BATCH = 25

# where the button in an email opens the app (route id from the notification's `to`)
PATHS = {"E2": "/log/meal", "E5": "/log/checkin", "F1": "/log/workout", "E8": "/log/ideas", "B1": "/", "H1": "/meds", "J1": "/urgent", "K3": "/me/care", "L1": "/brief"}
BUTTON = {"E2": "Log my meal", "E5": "Start my check-in", "F1": "Log a workout", "E8": "See my lunch ideas", "H1": "Open my medicines", "J1": "Open Smart Health", "K3": "Open my care plan"}

_EMAIL = re.compile(r"^[^@\s,;<>()\[\]\\\"]+@[^@\s,;<>()\[\]\\\"]+\.[^@\s,;<>()\[\]\\\"]+$")


def is_valid_email(value: str | None) -> bool:
    return bool(value) and len(value) <= 254 and bool(_EMAIL.match(value))  # type: ignore[arg-type]


class Sender(Protocol):
    @property
    def configured(self) -> bool: ...
    def send(self, message: dict[str, Any]) -> None: ...


# ───────────────────────────────────────────────────────────────── unsubscribe links
def _sign(user_id: str) -> str:
    return hmac.new(settings.notify_secret.encode(), user_id.encode(), hashlib.sha256).hexdigest()[:32]


def unsubscribe_token(user_id: str) -> str | None:
    return f"{user_id}.{_sign(user_id)}" if settings.notify_secret else None


def verify_unsubscribe(token: str) -> str | None:
    """The user id the token was made for, or None. Constant-time compare."""
    if not settings.notify_secret or "." not in token:
        return None
    user_id, sig = token.rsplit(".", 1)
    return user_id if hmac.compare_digest(sig, _sign(user_id)) else None


def unsubscribe_link(user_id: str) -> str | None:
    t = unsubscribe_token(user_id)
    return f"{settings.api_public_url.rstrip('/')}/api/v1/notify/unsubscribe?t={t}" if t and settings.api_public_url else None


# ───────────────────────────────────────────────────────────────── the decision (pure)
@dataclass(frozen=True)
class Row:
    id: str
    user_id: str
    kind: str
    scheduled_for: datetime
    acted_at: datetime | None
    payload: dict[str, Any]
    attempts: int
    delivery_to: str
    name: str | None
    email: str | None
    opt_in: bool
    contact_name: str | None
    contact_email: str | None


def recipient(row: Row) -> str | None:
    if row.delivery_to == "contact":
        return row.contact_email if is_valid_email(row.contact_email) else None
    return row.email if row.opt_in and is_valid_email(row.email) else None


def decide(row: Row, now: datetime, sent_today: int) -> tuple[str, str]:
    """('send' | 'skip' | 'wait', reason). 'wait' leaves the row pending (quiet hours: try again later, if it has not expired)."""
    urgent = row.kind == "urgent"
    if row.kind not in ELIGIBLE_KINDS:
        return "skip", "not an email kind"
    # "done in the app" only means something for the person's own reminder; a contact's email row is made already-acted so it stays out of the person's list
    if row.acted_at is not None and row.delivery_to != "contact":
        return "skip", "already done in the app"
    until = row.payload.get("until")
    try:
        expired = bool(until) and now >= datetime.fromisoformat(str(until))
    except ValueError:
        expired = False
    if expired:
        return "skip", "expired"
    if not until and now - row.scheduled_for > STALE_AFTER.get(row.kind, DEFAULT_STALE):
        return "skip", "too old to send"
    if recipient(row) is None:
        return "skip", "no address to send to" if row.delivery_to == "contact" or row.opt_in else "emails turned off"
    if not urgent:
        if sent_today >= settings.email_daily_cap:
            return "skip", "daily email limit reached"
        if in_quiet_hours(now):
            return "wait", "quiet hours"
    return "send", ""


# ───────────────────────────────────────────────────────────────── the message
def _subject(row: Row) -> str:
    key, title = str(row.payload.get("key", "")), str(row.payload.get("title", "")).strip()
    if row.kind == "urgent":
        return f"Please check on {row.contact_name or 'your contact'}: possible low glucose"
    if key.startswith("meal-"):
        return f"{title}? One photo is all it takes"
    if key.startswith("checkin-"):
        return "How did you sleep? It takes thirty seconds"
    if key.startswith("workout-"):
        return "A short walk counts today"
    if key.startswith("lunch-"):
        return "Lunch ideas picked for you"
    return title or "A reminder from Smart Health"


def build_message(row: Row) -> dict[str, Any]:
    """The payload the Workato recipe turns into one email. Plain text and HTML are both sent, so the recipe can use either."""
    p = row.payload
    title, body = str(p.get("title", "")).strip(), str(p.get("body", "")).strip()
    to_route = str(p.get("to") or "B1")
    link = settings.app_base_url.rstrip("/") + PATHS.get(to_route, "/")
    greeting = "Hi," if row.delivery_to == "contact" else f"Hi {row.name}," if row.name else "Hi,"
    button = BUTTON.get(to_route, "Open Smart Health")
    unsub = unsubscribe_link(row.user_id) if row.delivery_to != "contact" else None
    if row.delivery_to == "contact":
        foot = "You are getting this because someone added you as their emergency contact in Smart Health."
    else:
        foot = "You are getting this because you turned on reminder emails. You can turn them off any time in Me, then Privacy."
    text = "\n\n".join(x for x in (greeting, title, body, f"{button}: {link}", foot, f"Unsubscribe: {unsub}" if unsub else "") if x)
    esc = html.escape
    page = f"""<!doctype html><html><body style="margin:0;background:#F6F4EE;font-family:Arial,Helvetica,sans-serif;color:#16201B">
<span style="display:none;max-height:0;overflow:hidden">{esc(body[:110])}</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" style="max-width:520px;background:#FFFEFB;border:1px solid #E1DDD0;border-radius:16px" cellpadding="0" cellspacing="0"><tr><td style="padding:28px 24px">
<p style="margin:0 0 4px;font-size:14px;color:#46524B">Smart Health</p>
<p style="margin:0 0 16px;font-size:16px">{esc(greeting)}</p>
<h1 style="margin:0 0 8px;font-size:24px;line-height:1.25;font-weight:600">{esc(title)}</h1>
<p style="margin:0 0 24px;font-size:17px;line-height:1.45;color:#46524B">{esc(body)}</p>
<a href="{esc(link)}" style="display:inline-block;background:#1D4A3C;color:#FBFAF5;text-decoration:none;font-weight:bold;font-size:17px;padding:14px 24px;border-radius:12px">{esc(button)}</a>
<p style="margin:28px 0 0;font-size:13px;line-height:1.4;color:#5F6B64">{esc(foot)}{f' <a href="{esc(unsub)}" style="color:#5F6B64">Unsubscribe</a>.' if unsub else ''}</p>
</td></tr></table></td></tr></table></body></html>"""
    return {
        "to": recipient(row), "toName": (row.contact_name if row.delivery_to == "contact" else row.name) or "",
        "subject": _subject(row), "preheader": body[:110], "text": text, "html": page,
        "tags": {"kind": row.kind, "key": str(p.get("key", "")), "audience": row.delivery_to},
        "idempotencyKey": row.id,
    }


# ───────────────────────────────────────────────────────────────── columns (the migration may not be applied yet)
_has_columns: bool | None = None


def columns_ready(conn: Any = None) -> bool:
    global _has_columns
    if _has_columns:
        return True
    with tx() as c:
        n = c.execute("select count(*) n from information_schema.columns where (table_name='notifications' and column_name='delivery_status') "
                      "or (table_name='user_profile' and column_name in ('notification_email','email_opt_in'))").fetchone()["n"]
    _has_columns = n >= 3
    return _has_columns


# ───────────────────────────────────────────────────────────────── the dispatcher
_COLS = """n.id, n.user_id, n.kind::text kind, n.scheduled_for, n.acted_at, n.payload, n.delivery_attempts, n.delivery_to,
           p.display_name, p.notification_email, p.email_opt_in, p.emergency_contact_name, p.emergency_contact_email"""


def _row(r: dict[str, Any]) -> Row:
    return Row(str(r["id"]), str(r["user_id"]), r["kind"], r["scheduled_for"], r["acted_at"], r["payload"] or {}, int(r["delivery_attempts"] or 0), r["delivery_to"] or "person",
               r["display_name"], r["notification_email"], True if r["email_opt_in"] is None else bool(r["email_opt_in"]), r["emergency_contact_name"], r["emergency_contact_email"])


def dispatch(sender: Sender, now_fn: Callable[[], datetime] = lambda: datetime.now(TZ)) -> dict[str, int]:
    """One pass over the pending rows. Returns counts by outcome. Safe to run every minute and from more than one process."""
    out = {"sent": 0, "failed": 0, "skipped": 0, "waiting": 0, "retry": 0}
    if not sender.configured or not columns_ready():
        return out
    with tx() as c:
        ids = [r["id"] for r in c.execute("select id from notifications where delivery_status = 'pending' order by scheduled_for limit %s", (BATCH,)).fetchall()]
    for nid in ids:
        try:
            _one(nid, sender, now_fn, out)
        except Exception:                                    # one bad row must not stop the others
            logger.exception("email dispatch failed for one notification")
    if any(out.values()):
        logger.info("email dispatch: %s", out)
    return out


def _one(nid: Any, sender: Sender, now_fn: Callable[[], datetime], out: dict[str, int]) -> None:
    from app.core.errors import DomainError

    with tx() as c:
        r = c.execute(f"select {_COLS} from notifications n left join user_profile p on p.user_id = n.user_id "
                      "where n.id = %s and n.delivery_status = 'pending' for update of n skip locked", (nid,)).fetchone()
        if not r:
            return                                           # someone else took it, or it was already handled
        row, now = _row(r), now_fn()
        sent_today = c.execute(
            "select count(*) n from notifications where user_id = %s and delivery_to = 'person' and delivery_status = 'sent' "
            "and (delivered_at at time zone 'Asia/Singapore')::date = %s", (r["user_id"], now.astimezone(TZ).date())).fetchone()["n"]
        verdict, reason = decide(row, now, int(sent_today))
        if verdict == "wait":
            out["waiting"] += 1
            return
        if verdict == "skip":
            c.execute("update notifications set delivery_status = 'skipped', delivery_error = %s where id = %s", (reason, nid))
            out["skipped"] += 1
            return
        try:
            sender.send(build_message(row))
        except DomainError as e:
            attempts = row.attempts + 1
            final = attempts >= settings.email_max_attempts or e.code == "workato_refused"
            c.execute("update notifications set delivery_attempts = %s, delivery_status = %s, delivery_error = %s where id = %s",
                      (attempts, "failed" if final else "pending", e.code, nid))
            out["failed" if final else "retry"] += 1
            return
        c.execute("update notifications set delivery_status = 'sent', delivered_at = %s, delivery_attempts = %s, delivery_error = null where id = %s",
                  (now, row.attempts + 1, nid))
        out["sent"] += 1
