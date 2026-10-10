"""Onboarding answers saved to the database (screens A3 and A6): the profile, the data-processing consent and the completion event.

The checks are pure functions (unit-tested with fakes). The SQL is small and runs inside the caller's transaction.
Only the columns the request sent are written, so a missing field never blanks a stored value.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, time
from typing import Any, Mapping

import psycopg

ENUM_FIELDS = {"language": "locale_code", "has_diabetes": "yes_no_unsure", "gender": "gender_type", "work_type": "work_type"}
# Columns that may not be sent as null: the person must give them, and a blank would break the profile.
NOT_NULL = frozenset({"display_name", "language", "has_diabetes", "birth_year"})
# Written by the save. user_id and bronze_id are set by the service itself.
WRITABLE = (
    "display_name", "language", "has_diabetes", "birth_year", "gender", "race", "height_cm", "weight_kg", "work_type", "work_days",
    "work_start", "work_end", "emergency_contact_name", "emergency_contact_phone", "emergency_contact_relation", "watch_model",
    "cgm_model", "allergies_note", "conditions_note",
)
TIME_FIELDS = frozenset({"work_start", "work_end"})
EMAIL_COLUMN = "emergency_contact_email"
ADULT_AGE = 18                                  # prd section 3: adults only
CONSENT = "data_processing"
CONSENT_VERSION = "v1"
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
CLOCK = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

_email_column: bool | None = None               # cached once per process (see email_column_present)


class OnboardingError(ValueError):
    """A request the database cannot take. The router turns it into a 422 with this plain message."""


# ------------------------------------------------------------------ pure checks (unit-tested)
def unknown_choice_messages(values: Mapping[str, Any], labels: Mapping[str, frozenset[str]]) -> list[str]:
    """One plain message for each enum field whose value is not a database choice."""
    out = []
    for field, enum in ENUM_FIELDS.items():
        value = values.get(field)
        if value is None or value in labels.get(enum, frozenset()):
            continue
        choices = ", ".join(sorted(labels.get(enum, frozenset())))
        out.append(f"{field.replace('_', ' ')} '{value}' is not a choice Smart Health knows. Choose one of: {choices}.")
    return out


def check_profile(values: Mapping[str, Any], labels: Mapping[str, frozenset[str]], this_year: int) -> list[str]:
    """Everything wrong with the fields the request sent. An empty list means the save may go ahead."""
    problems = [f"{f.replace('_', ' ')} cannot be blank." for f in sorted(NOT_NULL) if f in values and values[f] is None]
    problems += unknown_choice_messages(values, labels)
    birth = values.get("birth_year")
    if birth is not None and birth > this_year - ADULT_AGE:
        problems.append("Smart Health is for adults aged 18 or older.")
    days = values.get("work_days")
    if days is not None and any(d not in range(1, 8) for d in days):
        problems.append("work days must be numbers from 1 (Monday) to 7 (Sunday).")
    for f in TIME_FIELDS:
        v = values.get(f)
        if v is not None and not CLOCK.match(v):
            problems.append(f"{f.replace('_', ' ')} must be a time like 07:30.")
    email = values.get(EMAIL_COLUMN)
    if email and not EMAIL.match(email):
        problems.append("The emergency contact email must look like name@example.com.")
    return problems


def normalise(values: Mapping[str, Any]) -> dict[str, Any]:
    """The values as the database takes them: work days sorted and unique, a blank optional text stored as null."""
    out = {k: (None if v == "" and k not in NOT_NULL else v) for k, v in values.items()}
    if out.get("work_days") is not None:
        out["work_days"] = sorted(set(out["work_days"]))
    return out


def completion_problems(profile_exists: bool) -> list[str]:
    return [] if profile_exists else ["Save your answers before you finish setup."]


def clock_text(t: time | None) -> str | None:
    return t.strftime("%H:%M") if t is not None else None


# ------------------------------------------------------------------ database facts (cached or read per call)
def email_column_present(conn: psycopg.Connection) -> bool:
    """Whether migration 0031 has added emergency_contact_email. Looked up once and then cached."""
    global _email_column
    if _email_column is None:
        row = conn.execute(
            "select 1 from information_schema.columns where table_schema = 'public' and table_name = 'user_profile' and column_name = %s",
            (EMAIL_COLUMN,),
        ).fetchone()
        _email_column = row is not None
    return _email_column


def reset_email_column_cache() -> None:
    global _email_column
    _email_column = None


def enum_labels(conn: psycopg.Connection) -> dict[str, frozenset[str]]:
    rows = conn.execute(
        "select t.typname, e.enumlabel from pg_type t join pg_enum e on e.enumtypid = t.oid "
        "where t.typname::text = any(%s) order by t.typname, e.enumsortorder",
        (list(set(ENUM_FIELDS.values())),),
    ).fetchall()
    out: dict[str, set[str]] = {}
    for r in rows:
        out.setdefault(r["typname"], set()).add(r["enumlabel"])
    return {k: frozenset(v) for k, v in out.items()}


# ------------------------------------------------------------------ reads and writes
def load(conn: psycopg.Connection, user: Any) -> dict[str, Any]:
    has_email = email_column_present(conn)
    email_sql = f", {EMAIL_COLUMN}" if has_email else ""
    row = conn.execute(
        f"select display_name, language, has_diabetes, birth_year, gender, race, height_cm, weight_kg, work_type, work_days, "
        f"work_start, work_end, emergency_contact_name, emergency_contact_phone, emergency_contact_relation, watch_model, cgm_model, "
        f"allergies_note, conditions_note, updated_at{email_sql} from user_profile where user_id = %s",
        (user,),
    ).fetchone()
    consent = conn.execute(
        "select 1 from consents where user_id = %s and kind = %s and revoked_at is null limit 1", (user, CONSENT)
    ).fetchone()
    profile = None
    if row is not None:
        profile = dict(row)
        profile["work_start"] = clock_text(profile["work_start"])
        profile["work_end"] = clock_text(profile["work_end"])
        profile["work_days"] = list(profile["work_days"] or [])
        profile.setdefault(EMAIL_COLUMN, None)
    return {"profile": profile, "data_consent": consent is not None, "email_column": has_email}


def save_profile(conn: psycopg.Connection, user: Any, sent: Mapping[str, Any], labels: Mapping[str, frozenset[str]], this_year: int) -> dict[str, Any]:
    """Upsert the profile with the fields the request sent. Returns the stored state plus the fields that could not be stored."""
    values = dict(sent)
    not_saved: list[str] = []
    if EMAIL_COLUMN in values and not email_column_present(conn):
        values.pop(EMAIL_COLUMN)
        not_saved.append("emergencyContactEmail")
    problems = check_profile(values, labels, this_year)
    existing = conn.execute("select 1 from user_profile where user_id = %s", (user,)).fetchone()
    if existing is None:
        missing = [f for f in ("birth_year", "has_diabetes") if values.get(f) is None]
        if missing:
            problems.append("Enter " + " and ".join(f.replace("_", " ") for f in missing) + " to finish setup.")
        values.setdefault("display_name", "")
    if problems:
        raise OnboardingError(" ".join(problems))

    values = normalise(values)
    body = json.dumps(sent, sort_keys=True, default=str)     # the request as received, before any change
    bronze_id = conn.execute(
        "insert into bronze_profile (user_id, source, payload, checksum) values (%s, 'manual', %s::jsonb, %s) "
        "on conflict (user_id, checksum) do update set processing_status = bronze_profile.processing_status returning id",
        (user, body, hashlib.sha256(body.encode()).hexdigest()),
    ).fetchone()["id"]
    conn.execute("update bronze_profile set processing_status = 'processed' where id = %s", (bronze_id,))

    cols = [c for c in WRITABLE if c in values] + ([EMAIL_COLUMN] if EMAIL_COLUMN in values else [])
    marks = [f"%s::time" if c in TIME_FIELDS else "%s::smallint[]" if c == "work_days" else "%s" for c in cols]
    params = [values[c] for c in cols]
    if existing is None:
        conn.execute(
            f"insert into user_profile (user_id, bronze_id, {', '.join(cols)}) values (%s, %s, {', '.join(marks)})",
            (user, bronze_id, *params),
        )
    else:
        # An UPDATE, not an upsert: an insert row would fail the NOT NULL check on the columns this request did not send.
        conn.execute(
            f"update user_profile set {', '.join(f'{c} = {m}' for c, m in zip(cols, marks))}, bronze_id = %s where user_id = %s",
            (*params, bronze_id, user),
        )
    out = load(conn, user)
    out["not_saved"] = not_saved
    return out


def complete(conn: psycopg.Connection, user: Any, now: datetime) -> dict[str, Any]:
    """Record the data-processing consent if none is active, and write the completion event."""
    exists = conn.execute("select 1 from user_profile where user_id = %s", (user,)).fetchone() is not None
    problems = completion_problems(exists)
    if problems:
        raise OnboardingError(" ".join(problems))
    active = conn.execute(
        "select 1 from consents where user_id = %s and kind = %s and revoked_at is null limit 1", (user, CONSENT)
    ).fetchone()
    recorded = active is None
    if recorded:
        conn.execute(
            "insert into consents (user_id, kind, version, granted_at) values (%s, %s, %s, %s)",
            (user, CONSENT, CONSENT_VERSION, now),
        )
    conn.execute(
        "insert into event_log (user_id, actor, event, entity_table, entity_id, payload) "
        "values (%s, 'user', 'onboarding_completed', 'user_profile', %s, %s::jsonb)",
        (user, user, json.dumps({"consent_recorded": recorded})),
    )
    return {"consent_recorded": recorded, "completed_at": now}
