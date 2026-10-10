"""The Me settings screens: language (K5), consents (K6), the data download and the deletion request (K8), the emergency contact (K9).

The pure parts (what a valid phone or email is, how a contact is cleaned, what goes in the export, when a deletion is promised) are
unit-tested with no database. The SQL functions take a connection so the router runs them in one transaction, and so a check can run
them inside a transaction that is rolled back. Consents, the deletion request and the contact changes are written to `event_log`,
which is append-only: it never stores the contact's details, a medicine name or any free text.

`user_profile.emergency_contact_email` and `notification_email` come from migration 0031. Until it is applied the columns are
detected once and the contact screen says that email is not set up yet; nothing else breaks.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

KINDS = ("data_processing", "brief_sharing", "calendar_access", "caregiver_view", "research_use")
CONSENT_VERSION = "v1"             # the consent text version; matches the rows already in the database
DELETE_CONFIRM = "DELETE"
DELETE_PROMISE_DAYS = 30
DEFAULT_LANGUAGE = "en"

PHONE_RE = re.compile(r"\+?\d{7,15}")
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

# The export: one query per section. Deleted rows are left out; the doses table has no soft delete.
EXPORT_SECTIONS: dict[str, str] = {
    "meals": "select start_at, end_at, meal_type, food, protein_g, carbs_g, fat_g, sugar_g, fibre_g, sodium_mg, estimated_by "
             "from food_logs where user_id=%s and deleted_at is null order by start_at",
    "workouts": "select start_at, end_at, type, intensity, feeling, note from exercise_logs "
                "where user_id=%s and deleted_at is null order by start_at",
    "symptoms": "select occurred_at, symptom_type, severity, duration_min, note from symptom_logs "
                "where user_id=%s and deleted_at is null order by occurred_at",
    "checkins": "select recorded_at, mood, stress_self, sleep_quality, energy from wellbeing_logs "
                "where user_id=%s and deleted_at is null order by recorded_at",
    "medicines": "select name, kind, strength, description, start_date, end_date, total_quantity, pack_started_on, as_needed "
                 "from medications where user_id=%s and deleted_at is null order by created_at",
    "doses": "select l.scheduled_at, l.taken_at, l.status, l.miss_reason, l.miss_note, m.name as medicine "
             "from medication_log l join medications m on m.id = l.medication_id where l.user_id=%s order by l.scheduled_at",
}
PROFILE_COLUMNS = (
    "display_name", "birth_year", "language", "has_diabetes", "gender", "race", "height_cm", "weight_kg", "work_type", "work_days",
    "work_start", "work_end", "watch_model", "cgm_model", "timezone", "glucose_target_low", "glucose_target_high",
    "allergies_note", "conditions_note", "emergency_contact_name", "emergency_contact_relation", "emergency_contact_phone",
)
OPTIONAL_PROFILE_COLUMNS = ("emergency_contact_email", "notification_email", "email_opt_in")


class ProfileMissing(Exception):
    """The person has no profile row yet (setup not finished), so there is nothing to save to."""


class EmailNotSupported(Exception):
    """An email was given for the emergency contact but the column is not there yet (migration 0031 not applied)."""


# ───────────────────────────────────────────────────────────────── pure rules
def _text(raw: str | None) -> str | None:
    s = (raw or "").strip()
    return s or None


def clean_phone(raw: str | None) -> str | None:
    """Spaces and dashes are removed first, so "+65 5550 0142" is accepted. Then digits with an optional leading plus, 7 to 15 digits."""
    s = re.sub(r"[ \-]", "", (raw or "").strip())
    if not s:
        return None
    if not PHONE_RE.fullmatch(s):
        raise ValueError("Check the phone number. Use digits only, with an optional + at the start (7 to 15 digits).")
    return s


def clean_email(raw: str | None) -> str | None:
    s = _text(raw)
    if s is None:
        return None
    if len(s) > 254 or not EMAIL_RE.fullmatch(s):
        raise ValueError("Check the email address. It should look like name@example.com.")
    return s


def clean_contact(name: str | None, relation: str | None, phone: str | None, email: str | None) -> dict[str, str | None]:
    """Every field is optional, and an empty contact clears the saved one. A contact with details needs a name and a way to reach them."""
    out = {"name": _text(name), "relation": _text(relation), "phone": clean_phone(phone), "email": clean_email(email)}
    if not any(out.values()):
        return out
    if not out["name"]:
        raise ValueError("Add the name of your emergency contact.")
    if not (out["phone"] or out["email"]):
        raise ValueError("Add a phone number or an email address, so we can reach this person.")
    return out


def deletion_promise(requested_at: datetime) -> datetime:
    return requested_at + timedelta(days=DELETE_PROMISE_DAYS)


def _plain(row: dict[str, Any]) -> dict[str, Any]:
    """Make a row JSON-ready: numbers stay numbers, dates become ISO text, ids become text."""
    out: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            v = float(v)
        elif isinstance(v, (datetime, date, time)):
            v = v.isoformat()
        elif isinstance(v, UUID):
            v = str(v)
        out[k] = v
    return out


def build_export(profile: dict[str, Any] | None, sections: dict[str, list[dict[str, Any]]], consents: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    """The file the person downloads. `counts` is computed from the sections, so it always matches what is in the file."""
    return {
        "format": "smart-health-export",
        "format_version": 1,
        "exported_at": now.isoformat(),
        "profile": profile,
        "consents": consents,
        "counts": {k: len(v) for k, v in sections.items()},
        **sections,
    }


# ───────────────────────────────────────────────────────────────── column checks (detected once, then cached)
_COLUMNS: dict[str, frozenset[str]] = {}


def _columns(conn: Any, table: str) -> frozenset[str]:
    if table not in _COLUMNS:
        rows = conn.execute("select column_name from information_schema.columns where table_schema='public' and table_name=%s", (table,)).fetchall()
        _COLUMNS[table] = frozenset(r["column_name"] for r in rows)
    return _COLUMNS[table]


def reset_column_cache() -> None:
    _COLUMNS.clear()


def has_contact_email(conn: Any) -> bool:
    return "emergency_contact_email" in _columns(conn, "user_profile")


# ───────────────────────────────────────────────────────────────── language (K5)
def get_language(conn: Any, user: UUID) -> str:
    row = conn.execute("select language from user_profile where user_id=%s", (user,)).fetchone()
    return row["language"] if row else DEFAULT_LANGUAGE


def set_language(conn: Any, user: UUID, code: str) -> str:
    cur = conn.execute("update user_profile set language=%s::locale_code, updated_at=now() where user_id=%s", (code, user))
    if cur.rowcount == 0:
        raise ProfileMissing()
    return code


# ───────────────────────────────────────────────────────────────── consents (K6)
def _event(conn: Any, user: UUID, event: str, entity_table: str, entity_id: UUID | None, payload: dict[str, Any]) -> None:
    conn.execute(
        "insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'user', %s, %s, %s, %s::jsonb)",
        (user, event, entity_table, entity_id, json.dumps(payload)),
    )


def list_consents(conn: Any, user: UUID) -> dict[str, list[dict[str, Any]]]:
    rows = conn.execute(
        "select id, kind::text as kind, version, granted_at, revoked_at from consents where user_id=%s order by granted_at desc, id desc",
        (user,),
    ).fetchall()
    active = {r["kind"]: r for r in rows if r["revoked_at"] is None}
    consents = []
    for k in KINDS:
        a = active.get(k)
        consents.append({"kind": k, "granted": a is not None, "version": a["version"] if a else None, "granted_at": a["granted_at"] if a else None})
    history = [{"kind": r["kind"], "version": r["version"], "granted_at": r["granted_at"], "revoked_at": r["revoked_at"]} for r in rows]
    return {"consents": consents, "history": history}


def set_consent(conn: Any, user: UUID, kind: str, granted: bool) -> dict[str, list[dict[str, Any]]]:
    """A grant inserts a row; a revoke sets revoked_at on the active row. Old rows stay, so the history is kept."""
    active = conn.execute(
        "select id from consents where user_id=%s and kind=%s::consent_kind and revoked_at is null", (user, kind)
    ).fetchone()
    if granted and not active:
        row = conn.execute(
            "insert into consents (user_id, kind, version, granted_at) values (%s, %s::consent_kind, %s, now()) returning id",
            (user, kind, CONSENT_VERSION),
        ).fetchone()
        _event(conn, user, "consent.granted", "consents", row["id"], {"kind": kind, "version": CONSENT_VERSION})
    elif not granted and active:
        conn.execute("update consents set revoked_at=now() where id=%s", (active["id"],))
        _event(conn, user, "consent.revoked", "consents", active["id"], {"kind": kind, "version": CONSENT_VERSION})
        if kind == "brief_sharing":
            # withdrawing consent to share must stop every link that is still live, not only stop new ones
            n = conn.execute(
                "update brief_shares set revoked_at = now() where revoked_at is null and brief_id in (select id from briefs where user_id = %s)", (user,)
            ).rowcount
            if n:
                _event(conn, user, "brief.shares_revoked_with_consent", "brief_shares", None, {"count": n})
    return list_consents(conn, user)


# ───────────────────────────────────────────────────────────────── export and deletion request (K8)
def export_for(conn: Any, user: UUID, now: datetime) -> dict[str, Any]:
    profile_cols = list(PROFILE_COLUMNS) + [c for c in OPTIONAL_PROFILE_COLUMNS if c in _columns(conn, "user_profile")]
    prof = conn.execute(f"select {', '.join(profile_cols)} from user_profile where user_id=%s", (user,)).fetchone()
    sections = {name: [_plain(r) for r in conn.execute(sql, (user,)).fetchall()] for name, sql in EXPORT_SECTIONS.items()}
    consents = [_plain(c) for c in list_consents(conn, user)["history"]]
    return build_export(_plain(prof) if prof else None, sections, consents, now)


def request_deletion(conn: Any, user: UUID, confirm: str) -> dict[str, Any]:
    """Records the request in event_log. Deletes nothing: a person will process it within 30 days. A second request does not add a row."""
    if confirm != DELETE_CONFIRM:
        raise ValueError("To confirm, type DELETE in capital letters.")
    row = conn.execute(
        "select occurred_at from event_log where user_id=%s and event='account.deletion.requested' order by id desc limit 1", (user,)
    ).fetchone()
    if row:
        requested = row["occurred_at"]
    else:
        # the time comes from the database (the event's own timestamp), so a repeat request reads back the same value
        ins = conn.execute(
            "insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'user', 'account.deletion.requested', 'users', %s, %s::jsonb) returning occurred_at",
            (user, user, json.dumps({"process_within_days": DELETE_PROMISE_DAYS})),
        ).fetchone()
        requested = ins["occurred_at"]
    return {"status": "received", "requested_at": requested, "process_by": deletion_promise(requested)}


# ───────────────────────────────────────────────────────────────── emergency contact (K9)
def get_contact(conn: Any, user: UUID) -> dict[str, Any]:
    email_ok = has_contact_email(conn)
    cols = "emergency_contact_name, emergency_contact_relation, emergency_contact_phone" + (", emergency_contact_email" if email_ok else "")
    row = conn.execute(f"select {cols} from user_profile where user_id=%s", (user,)).fetchone()
    if not row:
        return {"name": None, "relation": None, "phone": None, "email": None, "email_supported": email_ok}
    return {
        "name": row["emergency_contact_name"],
        "relation": row["emergency_contact_relation"],
        "phone": row["emergency_contact_phone"],
        "email": row.get("emergency_contact_email") if email_ok else None,
        "email_supported": email_ok,
    }


def save_contact(conn: Any, user: UUID, name: str | None, relation: str | None, phone: str | None, email: str | None) -> dict[str, Any]:
    data = clean_contact(name, relation, phone, email)
    email_ok = has_contact_email(conn)
    if data["email"] and not email_ok:
        raise EmailNotSupported()
    # Only the columns that exist are written, so the same code works before and after migration 0031.
    sets = ["emergency_contact_name=%s", "emergency_contact_relation=%s", "emergency_contact_phone=%s"]
    vals: list[Any] = [data["name"], data["relation"], data["phone"]]
    if email_ok:
        sets.append("emergency_contact_email=%s")
        vals.append(data["email"])
    cur = conn.execute(f"update user_profile set {', '.join(sets)}, updated_at=now() where user_id=%s", (*vals, user))
    if cur.rowcount == 0:
        raise ProfileMissing()
    _event(conn, user, "contact.updated", "user_profile", user, {"has_phone": bool(data["phone"]), "has_email": bool(data["email"])})
    return get_contact(conn, user)
