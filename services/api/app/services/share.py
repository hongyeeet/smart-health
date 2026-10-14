"""Sharing the doctor report by link (prd F12, flow.md step 4): create, list, revoke, and the public read.

A share is a random token. Only its sha256 hash is stored, so a database read cannot be used to open a link. The token is shown
once, when the link is made. A link opens the same report the person sees on L1 and L3, for the period chosen when the link was
made, and only until it expires or is turned off. Each view writes one `brief_share_access` row.

Storage: `brief_shares` needs a `briefs` row (its `brief_id` is required). Each share gets one `briefs` row holding its period and
`data = {"days": N}`; the owner and the period are read from there when the link is opened.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb

from app.services import care, doctor_report
from app.services import insights_timeline
from app.services.me_settings import set_consent

ALLOWED_HOURS = (24, 72, 168)
TOKEN_BYTES = 24                         # secrets.token_urlsafe(24) gives 32 characters
MAX_TOKEN_LENGTH = 128                   # anything longer cannot be one of ours; reject it before the database is asked
# One message for wrong, expired and turned-off links, so a link cannot be probed for which case it is.
NOT_AVAILABLE = "This link has expired or was turned off."


def new_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def expires_at(now: datetime, hours: int) -> datetime:
    return now + timedelta(hours=hours)


def is_open(expires: datetime, revoked: datetime | None, now: datetime) -> bool:
    """A link is open until it is turned off or its expiry time passes (the expiry instant itself is already closed)."""
    return revoked is None and now < expires


def status(expires: datetime, revoked: datetime | None, now: datetime) -> str:
    if revoked is not None:
        return "revoked"
    return "active" if now < expires else "expired"


# ----------------------------------------------------------------------------------------------- database
def ensure_consent(conn: Any, user: UUID) -> UUID:
    """The sheet says what is shared, so a share needs an active brief_sharing consent. One is granted if there is none."""
    row = conn.execute(
        "select id from consents where user_id = %s and kind = 'brief_sharing' and revoked_at is null", (user,)
    ).fetchone()
    if row is None:
        set_consent(conn, user, "brief_sharing", True)
        row = conn.execute(
            "select id from consents where user_id = %s and kind = 'brief_sharing' and revoked_at is null", (user,)
        ).fetchone()
    return row["id"]


def create_share(conn: Any, user: UUID, days: int, hours: int, now: datetime) -> dict[str, Any]:
    """Make a link. Returns the token (once) and the expiry. The caller must not store or log the token."""
    inputs = doctor_report.load(conn, str(user), days, now)
    consent_id = ensure_consent(conn, user)
    brief = conn.execute(
        "insert into briefs (user_id, period_start, period_end, status, data) "
        "values (%s, %s, %s, 'ready', %s) returning id",
        (user, inputs.start, inputs.end, Jsonb({"days": days, "source": "share"})),
    ).fetchone()
    token = new_token()
    expires = expires_at(now, hours)
    share = conn.execute(
        "insert into brief_shares (brief_id, token_hash, expires_at, consent_id) values (%s, %s, %s, %s) returning id, created_at",
        (brief["id"], hash_token(token), expires, consent_id),
    ).fetchone()
    return {"id": share["id"], "token": token, "expires_at": expires, "days": days, "hours": hours, "created_at": share["created_at"]}


def list_shares(conn: Any, user: UUID, now: datetime) -> list[dict[str, Any]]:
    rows = conn.execute(
        "select s.id, s.created_at, s.expires_at, s.revoked_at, b.data->>'days' as days, "
        "count(a.id) as view_count, max(a.accessed_at) as last_viewed_at "
        "from brief_shares s join briefs b on b.id = s.brief_id "
        "left join brief_share_access a on a.brief_share_id = s.id "
        "where b.user_id = %s group by s.id, b.id order by s.created_at desc, s.id",
        (user,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "days": int(r["days"]),
            "created_at": r["created_at"],
            "expires_at": r["expires_at"],
            "revoked_at": r["revoked_at"],
            "status": status(r["expires_at"], r["revoked_at"], now),
            "view_count": int(r["view_count"]),
            "last_viewed_at": r["last_viewed_at"],
        }
        for r in rows
    ]


def revoke_share(conn: Any, user: UUID, share_id: UUID, now: datetime) -> dict[str, Any] | None:
    """Turn a link off. Revoking one that is already off keeps its first revoke time. None when it is not this person's."""
    row = conn.execute(
        "select s.id, s.expires_at, s.revoked_at from brief_shares s join briefs b on b.id = s.brief_id "
        "where s.id = %s and b.user_id = %s for update of s",
        (share_id, user),
    ).fetchone()
    if row is None:
        return None
    revoked = row["revoked_at"] or now
    if row["revoked_at"] is None:
        conn.execute("update brief_shares set revoked_at = %s where id = %s", (now, share_id))
    return {"id": row["id"], "expires_at": row["expires_at"], "revoked_at": revoked, "status": status(row["expires_at"], revoked, now)}


def find_share(conn: Any, token: str) -> dict[str, Any] | None:
    """The share row for a token, by its hash. Does not check whether it is still open (see `is_open`)."""
    if not token or len(token) > MAX_TOKEN_LENGTH:
        return None
    row = conn.execute(
        "select s.id, s.expires_at, s.revoked_at, b.user_id, b.data->>'days' as days "
        "from brief_shares s join briefs b on b.id = s.brief_id where s.token_hash = %s",
        (hash_token(token),),
    ).fetchone()
    return dict(row) if row else None


def open_share(conn: Any, token: str, now: datetime) -> dict[str, Any] | None:
    """The share for a token if it is open, else None. Wrong, expired and turned-off links all come back as None."""
    row = find_share(conn, token)
    if row is None or not is_open(row["expires_at"], row["revoked_at"], now):
        return None
    return row


def public_report(conn: Any, token: str, user_agent: str | None, now: datetime) -> dict[str, Any] | None:
    """The report a doctor sees through a link, for the owner of the link. Writes one access row. None when the link is not open."""
    row = open_share(conn, token, now)
    if row is None:
        return None
    conn.execute(
        "insert into brief_share_access (brief_share_id, accessed_at, user_agent) values (%s, %s, %s)",
        (row["id"], now, (user_agent or "")[:200] or None),
    )
    return doctor_report.read(conn, str(row["user_id"]), int(row["days"]), now)


def context(conn: Any, user: UUID, now: datetime) -> dict[str, Any]:
    """What the L1 brief shows next to the findings: open doctor questions and the next appointment, by the one rule in
    `care.next_appointment` (the same rule K3 uses)."""
    questions = conn.execute(
        "select id, text from doctor_questions where user_id = %s and status = 'open' order by created_at, id", (user,)
    ).fetchall()
    return {
        "questions": [{"id": q["id"], "text": q["text"]} for q in questions],
        "next_appointment": care.next_appointment(conn, str(user), now),
    }


def public_extras(conn: Any, token: str, now: datetime) -> dict[str, Any] | None:
    """The chart data, what the app learnt and the next visit for a link's owner and period, so the shared page can show the same
    four charts, filters and patterns as the printed brief. Read only; None when the link is not open (the report call writes the access row)."""
    from app.db import memorystore
    from app.db.logstore import TZ

    row = open_share(conn, token, now)
    if row is None:
        return None
    user = row["user_id"]
    days = int(row["days"])
    timeline = insights_timeline.timeline(conn, str(user), days, now.astimezone(TZ).date(), None)
    groups = memorystore.list_facts(user)["groups"]
    learned = [{"statement": f["statement"], "why": f["why"], "confirmed": bool(f["confirmed"])} for g in groups for f in g["facts"]]
    learned.sort(key=lambda x: not x["confirmed"])
    return {"timeline": timeline, "learned": learned, "next_appointment": care.next_appointment(conn, str(user), now)}
