"""Onboarding answers saved to the database (screens A3, A4 and A6): the profile, the data-processing consent and the completion event.

The checks are pure functions (unit-tested with fakes). The SQL is small and runs inside the caller's transaction.
Only the columns the request sent are written, so a missing field never blanks a stored value.
The chat setup (A4) only reads an answer and checks it; it never writes. The screen saves through the same PUT as the form.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, time
from typing import Any, Callable, Mapping

import psycopg
from pydantic import BaseModel

from app.core.config import settings
from app.llm import gateway
from app.llm.jev import deidentify
from app.services import usage

logger = logging.getLogger(__name__)

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


# ------------------------------------------------------------------ chat setup (A4): read one answer, check it, never save it
@dataclass(frozen=True)
class ChatStep:
    """One question of the chat. `field` is the name the form and the answers store use; `column` is where the profile keeps it."""

    id: str
    field: str
    column: str | None
    kind: str                                   # text, year, number, email, phone, choice, or none (answered on screen, never read here)
    ask: str
    choices: tuple[tuple[str, tuple[str, ...]], ...] = ()
    limits: tuple[int, int] | None = None       # the same ranges as the profile request (ProfileIn)
    optional: bool = False


# The order follows the form (A3). Safety check and reminders come last, as on the form.
CHAT_STEPS: tuple[ChatStep, ...] = (
    ChatStep("name", "name", "display_name", "text", "What should we call you?"),
    ChatStep("birthYear", "birthYear", "birth_year", "year", "What year were you born? Four digits, like 1968."),
    ChatStep(
        "gender", "gender", "gender", "choice", "How do you describe your gender? You can skip this.",
        choices=(
            ("female", ("woman", "girl")),
            ("male", ("man", "boy")),
            ("other", ()),
            ("prefer_not_to_say", ("prefer not", "rather not")),
        ),
        optional=True,
    ),
    ChatStep(
        "hasDiabetes", "hasDiabetes", "has_diabetes", "choice", "Do you have type 2 diabetes? Say yes, or not sure.",
        choices=(("yes", ("yes", "yeah", "yep", "i do")), ("not_sure", ("not sure", "unsure", "dunno", "don't know", "maybe"))),
    ),
    ChatStep("heightCm", "heightCm", "height_cm", "number", "What is your height in cm? Say a number, like 168.", limits=(100, 250), optional=True),
    ChatStep("weightKg", "weightKg", "weight_kg", "number", "And your weight in kg, like 72.", limits=(25, 300), optional=True),
    ChatStep(
        "workType", "workType", "work_type", "choice", "What is your work like? Mostly sitting, standing, physical, a mix, shifts, or not working?",
        choices=(
            ("desk", ("mostly sitting", "office")),
            ("standing", ("mostly standing",)),
            ("physical", ("physical work", "manual", "labour", "labor")),
            ("mixed", ("a mix", "both")),
            ("shift", ("shifts", "nights", "night shift")),
            ("not_working", ("retired", "not working", "unemployed", "homemaker")),
        ),
        optional=True,
    ),
    ChatStep("redFlags", "redFlags", None, "none", "Is any of this happening right now? Tick what applies."),
    ChatStep("contactName", "contactName", "emergency_contact_name", "text", "Who should we contact in an emergency? Their name, please."),
    ChatStep("contactRelation", "contactRelation", "emergency_contact_relation", "text", "How are they to you? For example, wife, son or friend."),
    ChatStep("contactPhone", "contactPhone", "emergency_contact_phone", "phone", "What is their mobile number? For example +65 9123 4567."),
    ChatStep("contactEmail", "contactEmail", "emergency_contact_email", "email", "Their email, if you have it. You can skip this.", optional=True),
    ChatStep("reminderEmail", "reminderEmail", None, "email", "Which email should reminders go to? A Gmail address works. You can skip this.", optional=True),
)
STEP_BY_ID = {s.id: s for s in CHAT_STEPS}
STEP_BY_FIELD = {s.field: s for s in CHAT_STEPS}
FALLBACK_REPLY = "I could not read that answer. Try again in a few words, or answer it on the form."
EXTRACT_FIELDS = {
    "name": "name", "birth_year": "birthYear", "gender": "gender", "has_diabetes": "hasDiabetes", "height_cm": "heightCm",
    "weight_kg": "weightKg", "work_type": "workType", "contact_name": "contactName", "contact_relation": "contactRelation",
}
_NUMBER = re.compile(r"(?:about |around |i am |i'm |it is |it's |my |is )?(\d{2,3}(?:\.\d{1,2})?)\s*(?:cm|kg|kilos|kilograms|centimetres|centimeters)?", re.I)
_EMAIL_IN_TEXT = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_IN_TEXT = re.compile(r"\+?\d[\d\s-]{6,18}\d")


def chat_step(step_id: str) -> ChatStep:
    step = STEP_BY_ID.get(step_id)
    if step is None:
        raise OnboardingError(f"'{step_id}' is not a question of the chat setup.")
    return step


def _has_phrase(norm: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z]){re.escape(phrase)}(?![a-z])", norm) is not None


def _choice(step: ChatStep, norm: str) -> str | None:
    """The one choice whose words appear in the answer. Several matches, or none, is not guessed."""
    hits = [value for value, words in step.choices if any(_has_phrase(norm, w) for w in (value.replace("_", " "), *words))]
    return hits[0] if len(hits) == 1 else None


def canonical(step: ChatStep, text: str) -> str | None:
    """Read one answer with plain rules (no model). Returns the value as the form stores it, or None when the rules cannot tell."""
    t = " ".join(text.split())
    if not t:
        return None
    norm = t.lower().rstrip(".!")
    if step.kind == "text":
        if len(t) > 100 or re.search(r"[\d@]", t):
            return None
        m = re.match(r"(?:my name is|i am|i'm|call me|this is|it's)\s+(.+)$", t, re.I)
        return (m.group(1) if m else t).strip(" .,") or None
    if step.kind == "year":
        m = re.fullmatch(r"(?:born in |i was born in |year )?((?:19|20)\d{2})", norm)
        return m.group(1) if m else None
    if step.kind == "number":
        m = _NUMBER.fullmatch(norm)
        return m.group(1) if m else None
    if step.kind == "email":
        found = _EMAIL_IN_TEXT.findall(t)
        return found[0] if len(found) == 1 else None
    if step.kind == "phone":
        m = _PHONE_IN_TEXT.search(t)
        if m and 8 <= len(re.sub(r"\D", "", m.group(0))) <= 15:
            return m.group(0).strip()
        return None
    if step.kind == "choice":
        return _choice(step, norm)
    return None


def _check(step: ChatStep, value: str, labels: Mapping[str, frozenset[str]], this_year: int) -> str | None:
    """Why a read value cannot be used, or None. Profile columns go through check_profile, the same gate the save uses."""
    if step.limits and not step.limits[0] <= float(value) <= step.limits[1]:
        return f"Enter a number from {step.limits[0]} to {step.limits[1]}."
    if step.column is None:
        return None if (step.kind != "email" or EMAIL.match(value)) else "That does not look like an email address."
    stored = int(value) if step.kind == "year" else value
    problems = check_profile({step.column: stored}, labels, this_year)
    return problems[0] if problems else None


def _next_id(step_id: str) -> str | None:
    ids = [s.id for s in CHAT_STEPS]
    i = ids.index(step_id)
    return ids[i + 1] if i + 1 < len(ids) else None


class ChatExtraction(BaseModel):
    """What the model may fill from one message. Every field is optional: null means the person did not state it."""

    name: str | None = None
    birth_year: str | None = None
    gender: str | None = None
    has_diabetes: str | None = None
    height_cm: str | None = None
    weight_kg: str | None = None
    work_type: str | None = None
    contact_name: str | None = None
    contact_relation: str | None = None


CHAT_PROMPT = """You fill in a health app's profile from one message a person typed in answer to a question.
Fill ONLY the fields the person clearly stated. Use null for anything not stated or unclear.
Never guess. Never work out one value from another (for example, do not turn an age into a birth year). Never give advice.
Allowed values:
- gender: female, male, other, prefer_not_to_say
- has_diabetes: yes, not_sure
- work_type: desk, standing, physical, mixed, shift, not_working
- birth_year: four digits. height_cm and weight_kg: a number only, in cm or kg.
- name, contact_name, contact_relation: the words the person used.
The question being answered: {ask}
Message: "{message}"
"""


def model_extract(text: str, step: ChatStep) -> dict[str, str] | None:
    """The fields the model reads from one message, keyed as the form names them. None when the model cannot answer (no key, cap reached, an error)."""
    try:
        from google.genai import types

        client = gateway._client()
        if not usage.allowed("vertex_chat"):
            return None
        resp = client.models.generate_content(
            model=settings.llm_vision_model,
            contents=CHAT_PROMPT.format(ask=step.ask, message=deidentify(text)),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ChatExtraction,
                temperature=0,
                http_options=types.HttpOptions(timeout=settings.llm_timeout_s * 1000),
            ),
        )
        um = getattr(resp, "usage_metadata", None)
        usage.record("vertex_chat", getattr(um, "prompt_token_count", 0) or 0, getattr(um, "candidates_token_count", 0) or 0)
        parsed = resp.parsed if isinstance(resp.parsed, ChatExtraction) else ChatExtraction.model_validate_json(resp.text or "")
    except Exception as e:  # no key, quota, network or a bad shape: the person is asked again or sent to the form
        logger.warning("chat answer not read by the model: %s", type(e).__name__)
        return None
    return {EXTRACT_FIELDS[k]: v for k, v in parsed.model_dump().items() if v}


def answer_step(
    step_id: str,
    text: str,
    labels: Mapping[str, frozenset[str]],
    this_year: int,
    extract: Callable[[str, ChatStep], dict[str, str] | None] | None = None,
) -> dict[str, Any]:
    """Read the person's answer to one question. Plain rules first; the model only for sentences the rules cannot read.

    Nothing is written. Every value goes through the same checks as the profile save, and an unknown choice is not guessed:
    it comes back as not understood with the question asked again.
    """
    step = chat_step(step_id)
    text = " ".join((text or "").split())[:1000]
    fields: dict[str, str] = {}
    understood = False
    reply = step.ask
    if step.kind == "none" or not text:
        return {"fields": fields, "understood": False, "next_step": step.id, "reply": reply}

    simple = canonical(step, text)
    if simple is not None:
        problem = _check(step, simple, labels, this_year)
        if problem is None:
            fields[step.field], understood = simple, True
        else:
            reply = problem
    else:
        got = (model_extract if extract is None else extract)(text, step)
        if got is None:
            reply = FALLBACK_REPLY
        else:
            problems: dict[str, str] = {}
            for key, raw in got.items():
                other = STEP_BY_FIELD.get(key)
                value = canonical(other, raw) if other and other.kind != "none" else None
                if value is None:
                    continue
                problem = _check(other, value, labels, this_year)
                if problem is None:
                    fields[key] = value
                else:
                    problems[key] = problem
            understood = step.field in fields
            if not understood and step.field in problems:
                reply = problems[step.field]

    if understood:
        nxt = _next_id(step.id)
        reply = f"Thanks, {fields['name']}." if step.field == "name" else "Got it."
        return {"fields": fields, "understood": True, "next_step": nxt, "reply": reply}
    return {"fields": fields, "understood": False, "next_step": step.id, "reply": reply}
