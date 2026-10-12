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
from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo

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
    # migration 0032 (written only once it is applied; see history_ready)
    "diagnosed_year", "care_setting", "healthier_sg", "hypo_last_3m",
)
ONBOARDING = "onboarding"                       # entry_source of every row written from onboarding: the marker a save replaces
ZONE = ZoneInfo("Asia/Singapore")               # lab dates are stored at noon here, so they keep their day in every timezone
GENDERS_ACCEPTED = ("male", "female")           # the only choices now; other answers are refused with a plain message
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


NAME_MAX = 100
PHONE_SHAPE = re.compile(r"^\+?[\d\s()\-]+$")


def name_problem(value: Any) -> str | None:
    """Why a display name cannot be used, or None. The same rule as the chat setup: some letters, no digits and no @ (so an ID number
    such as an NRIC is refused), at most 100 characters."""
    t = " ".join(str(value).split())
    if not t:
        return "Enter the name you would like us to call you."
    if len(t) > NAME_MAX or re.search(r"[\d@]", t):
        return "Enter a name you would like us to call you, without numbers (an ID number is not a name)."
    return None


def phone_problem(value: Any) -> str | None:
    """Why a mobile number cannot be used, or None: only digits, spaces, brackets, dashes and a leading +, with 7 to 15 digits."""
    t = str(value).strip()
    if not PHONE_SHAPE.match(t) or not 7 <= len(re.sub(r"\D", "", t)) <= 15:
        return "Enter a mobile number with digits, like +65 9123 4567."
    return None


def check_profile(
    values: Mapping[str, Any], labels: Mapping[str, frozenset[str]], this_year: int, today: date | None = None
) -> list[str]:
    """Everything wrong with the fields the request sent. An empty list means the save may go ahead."""
    problems = [f"{f.replace('_', ' ')} cannot be blank." for f in sorted(NOT_NULL) if f in values and values[f] is None]
    # gender is checked by its own rule below, so a value the database enum allows but the form no longer does gets one clear message
    problems += unknown_choice_messages({k: v for k, v in values.items() if k != "gender"}, labels)
    gender = values.get("gender")
    if gender is not None and gender not in GENDERS_ACCEPTED:
        problems.append(f"gender '{gender}' is not a choice Smart Health knows. Choose male or female.")
    problems += history_problems(values, today or date(this_year, 12, 31))
    if values.get("display_name") is not None and (p := name_problem(values["display_name"])):
        problems.append(p)
    if values.get("emergency_contact_phone") and (p := phone_problem(values["emergency_contact_phone"])):
        problems.append(p)
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


# ------------------------------------------------------------------ history (migration 0032): pure checks and plans (unit-tested)
# Request fields for the onboarding history, and the names the response and `notSaved` use for them.
HISTORY_NAMES = {
    "waist_cm": "waistCm", "diagnosed_year": "diagnosedYear", "care_setting": "careSetting", "healthier_sg": "healthierSg",
    "hypo_last3m": "hypoLast3m", "hypo_awareness": "hypoAwareness", "hypo_needed_help": "hypoNeededHelp", "conditions": "conditions",
    "other_condition": "otherCondition", "allergies": "allergies", "eye_check": "eyeCheck", "foot_check": "footCheck",
    "lab_date": "labDate", "hba1c": "hba1c", "hba1c_unit": "hba1cUnit", "fasting_glucose": "fastingGlucose",
    "glucose_unit": "glucoseUnit", "fasting_insulin": "fastingInsulin",
}
HISTORY_FIELDS = frozenset(HISTORY_NAMES)
LAB_KEYS = ("hba1c", "fasting_glucose", "fasting_insulin")
LAB_DATE = "lab_date"
CHECK_ITEMS = {"eye_check": "eye_screening", "foot_check": "foot_screening"}          # request field -> preventive_items.kind
CHECK_STATUS = {"within_year": "ok", "over_year": "overdue", "never_unsure": "unknown"}  # the answer -> patient_preventive_status.status
CARE_SETTINGS = frozenset({"polyclinic", "gp", "hospital", "none"})
HEALTHIER_SG = frozenset({"yes", "no", "unsure"})
HYPO_3M = frozenset({"0", "1-2", "3+", "unsure"})
AWARENESS = frozenset(str(n) for n in range(1, 8))
YES_NO = frozenset({"yes", "no"})
CONDITION_NAMES = {
    "hypertension": "High blood pressure", "high_cholesterol": "High cholesterol", "kidney": "Kidney disease",
    "heart": "Heart disease or a past heart attack", "stroke": "Stroke or mini-stroke", "heart_failure": "Heart failure",
    "eye": "Diabetic eye disease", "nerve": "Nerve problems in the feet", "foot_ulcer": "A past foot ulcer or amputation",
    "sleep_apnoea": "Sleep apnoea", "fatty_liver": "Fatty liver", "anaemia": "Anaemia or thalassaemia",
}
HBA1C_RANGE = {"%": (Decimal(4), Decimal(20)), "mmol/mol": (Decimal(20), Decimal(195))}
GLUCOSE_RANGE = {"mmol/L": (Decimal(1), Decimal(35)), "mg/dL": (Decimal(18), Decimal(630))}
INSULIN_RANGE = (Decimal("0.1"), Decimal(1000))
HBA1C_IFCC_DIVISOR = Decimal("10.929")          # the same conversion the form shows: % = mmol/mol / 10.929 + 2.15


def _choice_problem(name: str, value: Any, choices: frozenset[str]) -> str | None:
    if value is None or value in choices:
        return None
    return f"{name} '{value}' is not a choice Smart Health knows. Choose one of: {', '.join(sorted(choices))}."


def _range_problem(label: str, value: Any, bounds: tuple[Decimal, Decimal], unit: str) -> list[str]:
    low, high = bounds
    v = Decimal(str(value))
    return [] if low <= v <= high else [f"{label} must be between {low:g} and {high:g} {unit}."]


def history_problems(values: Mapping[str, Any], today: date) -> list[str]:
    """Everything wrong with the history answers the request sent. Only keys that were sent are checked."""
    out = [
        p for p in (
            _choice_problem("care setting", values.get("care_setting"), CARE_SETTINGS),
            _choice_problem("Healthier SG", values.get("healthier_sg"), HEALTHIER_SG),
            _choice_problem("hypos in the last 3 months", values.get("hypo_last3m"), HYPO_3M),
            _choice_problem("hypo awareness", values.get("hypo_awareness"), AWARENESS),
            _choice_problem("needed help with a hypo", values.get("hypo_needed_help"), YES_NO),
            _choice_problem("eye check", values.get("eye_check"), frozenset(CHECK_STATUS)),
            _choice_problem("foot check", values.get("foot_check"), frozenset(CHECK_STATUS)),
        ) if p
    ]
    dy = values.get("diagnosed_year")
    if dy is not None:
        if not 1900 <= dy <= today.year:
            out.append("The year you were told you have diabetes must be four digits, and not in the future.")
        elif values.get("birth_year") is not None and dy < values["birth_year"]:
            out.append("The year you were told you have diabetes cannot be before the year you were born.")
    if values.get("waist_cm") is not None and not 40 <= Decimal(str(values["waist_cm"])) <= 200:
        out.append("Waist must be between 40 and 200 cm.")
    if any(k in values for k in (*LAB_KEYS, LAB_DATE)):
        lab_date = values.get(LAB_DATE)
        if lab_date is not None and lab_date > today:
            out.append("The date of the blood test cannot be in the future.")
        if lab_date is None and any(values.get(k) is not None for k in LAB_KEYS):
            out.append("Enter the date of your blood test.")
        if values.get("hba1c") is not None:
            unit = values.get("hba1c_unit")
            if unit not in HBA1C_RANGE:
                out.append("Choose the unit for HbA1c: % or mmol/mol.")
            else:
                out += _range_problem("HbA1c", values["hba1c"], HBA1C_RANGE[unit], unit)
        if values.get("fasting_glucose") is not None:
            unit = values.get("glucose_unit")
            if unit not in GLUCOSE_RANGE:
                out.append("Choose the unit for fasting glucose: mmol/L or mg/dL.")
            else:
                out += _range_problem("Fasting glucose", values["fasting_glucose"], GLUCOSE_RANGE[unit], unit)
        if values.get("fasting_insulin") is not None:
            out += _range_problem("Fasting insulin", values["fasting_insulin"], INSULIN_RANGE, "µIU/mL")
    for code in values.get("conditions") or []:
        if code != "none" and code not in CONDITION_NAMES:
            out.append(f"'{code}' is not a condition Smart Health knows.")
    return out


def waist_value(value: Any) -> Decimal:
    """The waist as the database keeps it (one decimal place), so the same number saved again is recognised as unchanged."""
    return Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def waist_changed(latest: Any, new: Decimal) -> bool:
    """A waist row is written only when the value differs from the latest saved one, or when there is none yet."""
    return latest is None or Decimal(str(latest)) != new


def hba1c_percent(value: Any, unit: str) -> Decimal:
    """HbA1c on the percentage scale the database keeps. A value given in mmol/mol is converted with the form's own formula."""
    v = Decimal(str(value))
    if unit == "%":
        return v
    return (v / HBA1C_IFCC_DIVISOR + Decimal("2.15")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def condition_rows(codes: list[str] | None, other: str | None) -> list[tuple[str, str | None]]:
    """(name, code) for each condition: one row per code (none is not a condition), then the free-text other condition with no code."""
    rows = [(CONDITION_NAMES[c], c) for c in dict.fromkeys(codes or []) if c != "none"]
    text = (other or "").strip()
    if text:
        rows.append((text, None))
    return rows


def allergy_rows(items: list[Mapping[str, Any]] | None) -> list[tuple[str, str | None]]:
    """(substance, reaction) for each allergy with a name. A blank reaction is stored as null."""
    rows = []
    for item in items or []:
        substance = (item.get("substance") or "").strip()
        if substance:
            rows.append((substance, (item.get("reaction") or "").strip() or None))
    return rows


def lab_rows(values: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The lab values sent, each with the unit it is stored in (HbA1c always in %; fasting insulin in mcU/mL, the same unit as µIU/mL)."""
    rows: list[dict[str, Any]] = []
    if values.get("hba1c") is not None:
        rows.append({"test": "hba1c", "value": hba1c_percent(values["hba1c"], values["hba1c_unit"]), "unit": "%"})
    if values.get("fasting_glucose") is not None:
        rows.append({"test": "fasting_glucose", "value": Decimal(str(values["fasting_glucose"])), "unit": values["glucose_unit"]})
    if values.get("fasting_insulin") is not None:
        rows.append({"test": "fasting_insulin", "value": Decimal(str(values["fasting_insulin"])), "unit": "mcU/mL"})
    return rows


def device_label(value: Any) -> str | None:
    """The watch or sensor code to store. 'none' and a null both mean no device."""
    return None if value in (None, "", "none") else value


# The names a person reads for the device codes (the same names as the onboarding choices). Unknown codes are title-cased.
DEVICE_NAMES = {
    "libre": "Abbott FreeStyle Libre", "dexcom": "Dexcom", "apple": "Apple Watch", "garmin": "Garmin",
    "samsung": "Samsung Galaxy Watch", "fitbit": "Fitbit", "xiaomi": "Xiaomi", "other": "Other", "none": "None",
}


def device_display_name(code: str) -> str:
    return DEVICE_NAMES.get(code.lower(), code.replace("_", " ").title())


def hypo_patch(values: Mapping[str, Any]) -> dict[str, Any]:
    """The low glucose keys that were sent, for merging into user_profile.hypo_symptoms (keys left out are kept)."""
    patch: dict[str, Any] = {}
    if "hypo_awareness" in values:
        patch["awareness"] = values["hypo_awareness"]
    if "hypo_needed_help" in values:
        patch["needed_help_12m"] = values["hypo_needed_help"]
    return patch


def empty_history() -> dict[str, Any]:
    """The history answers as the form expects them when nothing is saved (or the migration is not applied)."""
    return {
        "waist_cm": None, "diagnosed_year": None, "care_setting": None, "healthier_sg": None, "hypo_last3m": None,
        "hypo_awareness": None, "hypo_needed_help": None, "conditions": [], "other_condition": None, "allergies": [],
        "eye_check": None, "foot_check": None, "lab_date": None, "hba1c": None, "hba1c_unit": None,
        "fasting_glucose": None, "glucose_unit": None, "fasting_insulin": None,
    }


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


# Migration 0032 is applied when the history columns and tables exist and 'onboarding' is an entry_source value.
HISTORY_READY_SQL = (
    "select exists (select 1 from pg_attribute where attrelid = 'public.user_profile'::regclass and attname = 'hypo_symptoms' "
    "and not attisdropped) and to_regclass('public.conditions') is not null and to_regclass('public.allergies') is not null "
    "and to_regclass('public.devices') is not null and to_regclass('public.body_measurements') is not null "
    "and exists (select 1 from pg_enum e join pg_type t on t.oid = e.enumtypid "
    "where t.typname = 'entry_source' and e.enumlabel = 'onboarding') as ready"
)
_history_ready = False


def history_ready(conn: psycopg.Connection) -> bool:
    """Whether migration 0032 is applied. Found once, then remembered: a 'not yet' is checked again on the next call."""
    global _history_ready
    if not _history_ready:
        row = conn.execute(HISTORY_READY_SQL).fetchone()
        _history_ready = bool(row and row.get("ready"))
    return _history_ready


def reset_history_cache() -> None:
    global _history_ready
    _history_ready = False


def _soft_delete(conn: psycopg.Connection, table: str, user: Any, extra: str = "", params: tuple = ()) -> None:
    """Hide this person's rows that came from onboarding (soft delete, the rule for every table). `table` and `extra` are constants here."""
    conn.execute(
        f"update {table} set deleted_at = now() where user_id = %s and source = %s and deleted_at is null {extra}",
        (user, ONBOARDING, *params),
    )


def _bronze_lab(conn: psycopg.Connection, user: Any, payload: Mapping[str, Any]) -> Any:
    """The raw lab section as received (lineage for lab_results). The same section saved again reuses the same row."""
    body = json.dumps(payload, sort_keys=True)
    bronze_id = conn.execute(
        "insert into bronze_lab (user_id, source, payload, checksum) values (%s, %s, %s::jsonb, %s) "
        "on conflict (user_id, checksum) do update set processing_status = bronze_lab.processing_status returning id",
        (user, ONBOARDING, body, hashlib.sha256(body.encode()).hexdigest()),
    ).fetchone()["id"]
    conn.execute("update bronze_lab set processing_status = 'processed' where id = %s", (bronze_id,))
    return bronze_id


def _save_history(conn: psycopg.Connection, user: Any, bronze_id: Any, v: Mapping[str, Any]) -> None:
    """Write the history answers that were sent (migration 0032 applied). Each part replaces only its own onboarding rows.

    A key left out is not touched. A key sent as null or an empty list clears that part. Rows written from onboarding are
    soft deleted before the new ones are inserted, so saving the same answers twice leaves one copy of each.
    """
    if "waist_cm" in v:
        if v["waist_cm"] is None:
            _soft_delete(conn, "body_measurements", user, "and waist_cm is not null")
        else:
            new = waist_value(v["waist_cm"])
            latest = conn.execute(
                "select waist_cm from body_measurements where user_id = %s and source = %s and deleted_at is null "
                "and waist_cm is not null order by measured_at desc limit 1",
                (user, ONBOARDING),
            ).fetchone()
            if waist_changed(latest["waist_cm"] if latest else None, new):
                # clock_timestamp, not now(): now() is the start of the transaction, so two saves in one transaction would tie
                conn.execute(
                    "insert into body_measurements (user_id, measured_at, waist_cm, source, bronze_id) values (%s, clock_timestamp(), %s, %s, %s)",
                    (user, new, ONBOARDING, bronze_id),
                )
    if "conditions" in v:
        _soft_delete(conn, "conditions", user, "and code is not null")
        for name, code in condition_rows(v["conditions"], None):
            conn.execute(
                "insert into conditions (user_id, name, code, source, bronze_id) values (%s, %s, %s, %s, %s)",
                (user, name, code, ONBOARDING, bronze_id),
            )
    if "other_condition" in v:
        _soft_delete(conn, "conditions", user, "and code is null")
        for name, _ in condition_rows([], v["other_condition"]):
            conn.execute(
                "insert into conditions (user_id, name, code, source, bronze_id) values (%s, %s, null, %s, %s)",
                (user, name, ONBOARDING, bronze_id),
            )
    if "allergies" in v:
        _soft_delete(conn, "allergies", user)
        for substance, reaction in allergy_rows(v["allergies"]):
            conn.execute(
                "insert into allergies (user_id, substance, reaction, source, bronze_id) values (%s, %s, %s, %s, %s)",
                (user, substance, reaction, ONBOARDING, bronze_id),
            )
    for field, item in CHECK_ITEMS.items():
        if field in v:
            conn.execute(
                "insert into patient_preventive_status (user_id, preventive_item_id, status) "
                "select %s, i.id, %s from preventive_items i where i.kind = %s "
                "on conflict (user_id, preventive_item_id) do update set status = excluded.status",
                (user, CHECK_STATUS.get(v[field], "unknown"), item),
            )
    lab_keys = [k for k in LAB_KEYS if k in v]
    if lab_keys:
        payload = {k: (None if v[k] is None else str(v[k])) for k in (LAB_DATE, *LAB_KEYS, "hba1c_unit", "glucose_unit") if k in v}
        lab_bronze = _bronze_lab(conn, user, payload)
        taken = datetime.combine(v[LAB_DATE], time(12, 0), tzinfo=ZONE) if v.get(LAB_DATE) else None
        rows = {r["test"]: r for r in lab_rows(v)}
        for key in lab_keys:
            _soft_delete(conn, "lab_results", user, "and test = %s", (key,))
            row = rows.get(key)
            if row is not None:
                conn.execute(
                    "insert into lab_results (user_id, measured_at, test, value, unit, source, bronze_id) "
                    "values (%s, %s, %s, %s, %s, %s, %s)",
                    (user, taken, key, row["value"], row["unit"], ONBOARDING, lab_bronze),
                )
    elif v.get(LAB_DATE) is not None:
        conn.execute(
            "update lab_results set measured_at = %s where user_id = %s and source = %s and deleted_at is null",
            (datetime.combine(v[LAB_DATE], time(12, 0), tzinfo=ZONE), user, ONBOARDING),
        )
    for field, kind in (("watch_model", "watch"), ("cgm_model", "cgm")):
        if field in v:
            _soft_delete(conn, "devices", user, "and kind = %s", (kind,))
            label = device_label(v[field])
            if label:
                conn.execute(
                    "insert into devices (user_id, kind, label, source, bronze_id) values (%s, %s, %s, %s, %s)",
                    (user, kind, label, ONBOARDING, bronze_id),
                )
    patch = hypo_patch(v)
    if patch:
        conn.execute(
            "update user_profile set hypo_symptoms = coalesce(hypo_symptoms, '{}'::jsonb) || %s::jsonb where user_id = %s",
            (json.dumps(patch), user),
        )


def load_history(conn: psycopg.Connection, user: Any) -> dict[str, Any]:
    """The history answers for the form. Only rows written from onboarding, not deleted. HbA1c comes back in %."""
    out = empty_history()
    row = conn.execute(
        "select diagnosed_year, care_setting, healthier_sg, hypo_last_3m, hypo_symptoms from user_profile where user_id = %s", (user,)
    ).fetchone()
    if row:
        out.update(diagnosed_year=row["diagnosed_year"], care_setting=row["care_setting"], healthier_sg=row["healthier_sg"],
                   hypo_last3m=row["hypo_last_3m"])
        symptoms = row["hypo_symptoms"] or {}
        out["hypo_awareness"] = symptoms.get("awareness")
        out["hypo_needed_help"] = symptoms.get("needed_help_12m")
    waist = conn.execute(
        "select waist_cm from body_measurements where user_id = %s and source = %s and deleted_at is null and waist_cm is not null "
        "order by measured_at desc limit 1",
        (user, ONBOARDING),
    ).fetchone()
    out["waist_cm"] = waist["waist_cm"] if waist else None
    out["conditions"] = [r["code"] for r in conn.execute(
        "select code from conditions where user_id = %s and source = %s and deleted_at is null and code is not null order by name",
        (user, ONBOARDING),
    ).fetchall()]
    others = conn.execute(
        "select name from conditions where user_id = %s and source = %s and deleted_at is null and code is null order by name",
        (user, ONBOARDING),
    ).fetchall()
    out["other_condition"] = ", ".join(r["name"] for r in others) or None
    out["allergies"] = [{"substance": r["substance"], "reaction": r["reaction"]} for r in conn.execute(
        "select substance, reaction from allergies where user_id = %s and source = %s and deleted_at is null order by substance",
        (user, ONBOARDING),
    ).fetchall()]
    statuses = {r["kind"]: r["status"] for r in conn.execute(
        "select i.kind, s.status from patient_preventive_status s join preventive_items i on i.id = s.preventive_item_id "
        "where s.user_id = %s and i.kind = any(%s)",
        (user, list(CHECK_ITEMS.values())),
    ).fetchall()}
    answer_for = {status: answer for answer, status in CHECK_STATUS.items()}
    out["eye_check"] = answer_for.get(statuses.get("eye_screening"))
    out["foot_check"] = answer_for.get(statuses.get("foot_screening"))
    labs = conn.execute(
        "select test, value, unit, (measured_at at time zone 'Asia/Singapore')::date as taken_on from lab_results "
        "where user_id = %s and source = %s and deleted_at is null order by measured_at desc",
        (user, ONBOARDING),
    ).fetchall()
    if labs:
        out["lab_date"] = max(r["taken_on"] for r in labs)
    latest: dict[str, Any] = {}
    for r in labs:
        latest.setdefault(r["test"], r)
    if "hba1c" in latest:
        out["hba1c"], out["hba1c_unit"] = latest["hba1c"]["value"], latest["hba1c"]["unit"]
    if "fasting_glucose" in latest:
        out["fasting_glucose"], out["glucose_unit"] = latest["fasting_glucose"]["value"], latest["fasting_glucose"]["unit"]
    if "fasting_insulin" in latest:
        out["fasting_insulin"] = latest["fasting_insulin"]["value"]
    return out


def onboarding_report_fields(conn: psycopg.Connection, user: Any) -> dict[str, Any]:
    """The onboarding answers the doctor report may show, and nothing else: waist, diagnosed year, care setting, conditions,
    allergies, the last lab results and devices.

    A read only: nothing is written. Only rows written from onboarding (source 'onboarding') that are not deleted are read, so
    answers entered on other screens never reach the report through this function. Before migration 0032 every field is empty.
    """
    out: dict[str, Any] = {
        "waist": None, "diagnosed_year": None, "care_setting": None, "conditions": [], "allergies": [], "labs": [], "devices": [],
    }
    if not history_ready(conn):
        return out
    prof = conn.execute("select diagnosed_year, care_setting from user_profile where user_id = %s", (user,)).fetchone()
    if prof:
        out["diagnosed_year"], out["care_setting"] = prof["diagnosed_year"], prof["care_setting"]
    waist = conn.execute(
        "select waist_cm, (measured_at at time zone 'Asia/Singapore')::date as measured_on from body_measurements "
        "where user_id = %s and source = %s and deleted_at is null and waist_cm is not null order by measured_at desc limit 1",
        (user, ONBOARDING),
    ).fetchone()
    if waist:
        out["waist"] = {"cm": float(waist["waist_cm"]), "measured_on": waist["measured_on"].isoformat()}
    out["conditions"] = [
        {"name": r["name"], "code": r["code"]}
        for r in conn.execute(
            "select name, code from conditions where user_id = %s and source = %s and deleted_at is null order by name",
            (user, ONBOARDING),
        ).fetchall()
    ]
    out["allergies"] = [
        {"substance": r["substance"], "reaction": r["reaction"]}
        for r in conn.execute(
            "select substance, reaction from allergies where user_id = %s and source = %s and deleted_at is null order by substance",
            (user, ONBOARDING),
        ).fetchall()
    ]
    out["labs"] = [
        {"test": r["test"], "value": float(r["value"]), "unit": r["unit"], "taken_on": r["taken_on"].isoformat()}
        for r in conn.execute(
            "select distinct on (test) test, value, unit, (measured_at at time zone 'Asia/Singapore')::date as taken_on "
            "from lab_results where user_id = %s and source = %s and deleted_at is null order by test, measured_at desc",
            (user, ONBOARDING),
        ).fetchall()
    ]
    out["devices"] = [
        {"kind": r["kind"], "label": device_display_name(r["label"]) if r["label"] else None}
        for r in conn.execute(
            "select kind, label from devices where user_id = %s and source = %s and deleted_at is null order by kind",
            (user, ONBOARDING),
        ).fetchall()
    ]
    return out


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
    ready = history_ready(conn)
    return {
        "profile": profile, "data_consent": consent is not None, "email_column": has_email,
        "history_ready": ready, "history": load_history(conn, user) if ready else empty_history(),
    }


def save_profile(
    conn: psycopg.Connection, user: Any, sent: Mapping[str, Any], labels: Mapping[str, frozenset[str]], this_year: int,
    today: date | None = None,
) -> dict[str, Any]:
    """Upsert the profile with the fields the request sent. Returns the stored state plus the fields that could not be stored.

    History answers and devices are written only when migration 0032 is applied. Before that, the history answers are not
    checked or written and are named in `notSaved`; the rest of the save goes ahead as before.
    """
    values = dict(sent)
    not_saved: list[str] = []
    if EMAIL_COLUMN in values and not email_column_present(conn):
        values.pop(EMAIL_COLUMN)
        not_saved.append("emergencyContactEmail")
    history_sent = [k for k in values if k in HISTORY_FIELDS]
    device_sent = any(k in values for k in ("watch_model", "cgm_model"))
    ready = history_ready(conn) if (history_sent or device_sent) else False
    if history_sent and not ready:
        not_saved += [HISTORY_NAMES[k] for k in history_sent]
        for k in history_sent:
            values.pop(k)
    existing = conn.execute("select 1 from user_profile where user_id = %s", (user,)).fetchone()
    checked = values
    if existing is not None and values.get("diagnosed_year") is not None and "birth_year" not in values:
        # a diagnosis year sent alone is still checked against the birth year already saved
        saved = conn.execute("select birth_year from user_profile where user_id = %s", (user,)).fetchone()
        if saved and saved["birth_year"]:
            checked = {**values, "birth_year": saved["birth_year"]}
    problems = check_profile(checked, labels, this_year, today)
    if existing is None:
        missing = [f for f in ("birth_year", "has_diabetes") if values.get(f) is None]
        if missing:
            problems.append("Enter " + " and ".join(f.replace("_", " ") for f in missing) + " to finish setup.")
        values.setdefault("display_name", "")
    if problems:
        raise OnboardingError(" ".join(problems))

    values = normalise(values)
    if "hypo_last3m" in values:                                   # the request name; the column is hypo_last_3m
        values["hypo_last_3m"] = values.pop("hypo_last3m")
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
        sets = [f"{c} = {m}" for c, m in zip(cols, marks)] + ["bronze_id = %s"]     # bronze_id is always set, so the list is never empty
        conn.execute(f"update user_profile set {', '.join(sets)} where user_id = %s", (*params, bronze_id, user))
    if ready:
        _save_history(conn, user, bronze_id, values)
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
    # the completion event is written once: a second call (a double tap, a reload) adds nothing
    already = conn.execute("select 1 from event_log where user_id = %s and event = 'onboarding_completed' limit 1", (user,)).fetchone()
    if already is None:
        conn.execute(
            "insert into event_log (user_id, actor, event, entity_table, entity_id, payload) "
            "values (%s, 'user', 'onboarding_completed', 'user_profile', %s, %s::jsonb)",
            (user, user, json.dumps({"consent_recorded": recorded})),
        )
    return {"consent_recorded": recorded, "completed_at": now}


# ------------------------------------------------------------------ chat setup (A4): read one answer, check it, never save it
# The questions follow the form pages in order: Welcome, eligibility, about you, diabetes history, low glucose, other conditions and
# checks, lab results, devices, the work week and the emergency contact. Medicines are not asked here: the screen points to Scan a label.
# A step's id is also the name the answers store and the form use, so an answer fills the same form field. The plain rules read the
# words; the model only reads sentences the rules cannot. Every value then goes through the same checks as the form and the save.
WORKING = frozenset({"desk", "standing", "physical", "mixed", "shift"})          # the work types that have work days and hours
SKIP_WORDS = frozenset({
    "skip", "skip this", "skip this question", "i do not know", "i don't know", "i dont know", "do not know", "don't know", "dont know",
})
NONE_WORDS = frozenset({"none", "no", "nothing", "no allergies", "no known allergies", "i have none", "not applicable"})
FALLBACK_REPLY = "I could not read that answer. Try again in a few words, or answer it on the form."
NEEDED_REPLY = "This one is needed to finish setup. Answer it here, or on the form."
UNIT_HINT = {"hba1c": "Say the unit too, like 7.2% or 55 mmol/mol.", "fastingGlucose": "Say the unit too, like 7.4 mmol/L or 133 mg/dL."}
# The answer's store name -> the name history_problems checks it under (the same checks the save runs)
HISTORY_CHECK = {
    "waistCm": "waist_cm", "diagnosedYear": "diagnosed_year", "careSetting": "care_setting", "healthierSg": "healthier_sg",
    "hypo3m": "hypo_last3m", "severeHypo": "hypo_needed_help", "gold": "hypo_awareness", "conditions": "conditions",
    "eyeCheck": "eye_check", "footCheck": "foot_check", "labDate": "lab_date", "hba1c": "hba1c",
    "fastingGlucose": "fasting_glucose", "fastingInsulin": "fasting_insulin",
}
LAB_CHECK = ("hba1c", "fastingGlucose", "fastingInsulin")                       # answers that need the blood test date
_NUMBER = re.compile(r"(?:about |around |it is |it's |my |is |i am |i'm )?(\d{1,4}(?:\.\d{1,2})?)\s*([a-zµμ%/]+)?")
_CM = frozenset({"cm", "centimetre", "centimetres", "centimeter", "centimeters"})
_KG = frozenset({"kg", "kgs", "kilo", "kilos", "kilogram", "kilograms"})
_INSULIN_UNITS = frozenset({"µiu/ml", "μiu/ml", "uiu/ml", "miu/ml", "mciu/ml", "mcu/ml", "µu/ml", "iu/ml", "ui/ml"})
_HBA1C_UNITS = {"%": "%", "percent": "%", "mmol/mol": "mmol/mol", "mmol": "mmol/mol"}
_GLUCOSE_UNITS = {"mmol/l": "mmol/L", "mmol": "mmol/L", "mg/dl": "mg/dL", "mg": "mg/dL"}
_EMAIL_IN_TEXT = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_IN_TEXT = re.compile(r"\+?\d[\d\s-]{1,18}\d")
# the condition codes the form uses, with the words a person might use for each; "none" stands alone
CONDITION_WORDS = (
    ("hypertension", ("high blood pressure", "hypertension", "high bp")),
    ("high_cholesterol", ("high cholesterol", "cholesterol")),
    ("kidney", ("kidney",)),
    ("heart", ("heart disease", "heart attack", "heart problem")),
    ("stroke", ("stroke", "mini stroke", "mini-stroke")),
    ("heart_failure", ("heart failure",)),
    ("eye", ("diabetic eye", "eye disease", "retinopathy", "eye problem")),
    ("nerve", ("nerve problem", "nerve problems", "numbness", "neuropathy", "tingling")),
    ("foot_ulcer", ("foot ulcer", "amputation", "amputated")),
    ("sleep_apnoea", ("sleep apnoea", "sleep apnea")),
    ("fatty_liver", ("fatty liver",)),
    ("anaemia", ("anaemia", "anemia", "thalassaemia", "thalassemia")),
    ("none", ("none", "none of these", "nothing", "no", "no conditions")),
)
_DAY_NAMES = {
    "monday": 1, "mon": 1, "tuesday": 2, "tues": 2, "tue": 2, "wednesday": 3, "wed": 3, "thursday": 4, "thurs": 4, "thur": 4, "thu": 4,
    "friday": 5, "fri": 5, "saturday": 6, "sat": 6, "sunday": 7, "sun": 7,
}
_DAY = "|".join(sorted(_DAY_NAMES, key=len, reverse=True))
_DAY_RANGE = re.compile(rf"\b({_DAY})\s*(?:to|-|till|until|through)\s*({_DAY})\b")
_DAY_WORD = re.compile(rf"\b({_DAY})\b")
_MONTH_NAMES = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december")


@dataclass(frozen=True)
class ChatStep:
    """One question of the chat. `id` is the store name of the answer it fills; `kind` says how the plain rules read the words."""

    id: str
    kind: str                                  # text, free, year, number, scale, email, phone, date, time, days, choice, multi, allergy
    ask: str
    choices: tuple[tuple[str, tuple[str, ...]], ...] = ()
    optional: bool = False                     # may be skipped ("skip", "I do not know"); the others are needed to finish setup
    column: str | None = None                  # the profile column the form saves it to; checked with check_profile
    working_only: bool = False                 # asked only when the person works (work days and hours)
    limits: tuple[int, int] | None = None      # the form's range for a plain number
    max_len: int = 200


CHAT_STEPS: tuple[ChatStep, ...] = (
    ChatStep("name", "text", "What should we call you?", column="display_name"),
    ChatStep("reminderEmail", "email", "Which email should reminders go to? A Gmail address works. You can leave this one blank.", optional=True),
    ChatStep(
        "hasDiabetes", "choice", "Do you have type 2 diabetes? Say yes, or not sure.", column="has_diabetes",
        choices=(("yes", ("yes", "yeah", "yep", "i do")), ("not_sure", ("not sure", "unsure", "dunno", "don't know", "maybe", "do not know"))),
    ),
    ChatStep("birthYear", "year", "What year were you born? Four digits, like 1968.", column="birth_year"),
    ChatStep("gender", "choice", "Are you male or female?", column="gender", choices=(("female", ("woman", "girl")), ("male", ("man", "boy")))),
    ChatStep("heightCm", "number", "What is your height in cm? Say a number, like 168. You can leave this one blank.", optional=True, column="height_cm", limits=(100, 250)),
    ChatStep("weightKg", "number", "And your weight in kg? Say a number, like 72. You can leave this one blank.", optional=True, column="weight_kg", limits=(25, 300)),
    ChatStep("waistCm", "number", "What is your waist in cm? Measure around your middle, level with your belly button. You can leave this one blank.", optional=True),
    ChatStep("diagnosedYear", "year", "What year were you told you have type 2 diabetes? Four digits, like 2016. You can leave this one blank.", optional=True),
    ChatStep(
        "careSetting", "choice", "Where do you usually go for your diabetes? A polyclinic, a GP or family clinic, a hospital specialist clinic, or no regular doctor. You can leave this one blank.",
        optional=True,
        choices=(("polyclinic", ("polyclinic",)), ("gp", ("gp", "family clinic", "family doctor", "general practitioner")), ("hospital", ("hospital", "specialist")), ("none", ("no regular doctor", "no doctor", "none"))),
    ),
    ChatStep(
        "healthierSg", "choice", "Are you enrolled in Healthier SG? Say yes, no, or not sure. You can leave this one blank.", optional=True,
        choices=(("yes", ("yes", "i am enrolled", "i'm enrolled")), ("no", ("no", "not enrolled", "i am not enrolled", "i'm not enrolled")), ("unsure", ("not sure", "unsure"))),
    ),
    ChatStep(
        "hypo3m", "choice", "How many hypos (low glucose) have you had in the last 3 months? None, 1 or 2 times, 3 times or more, or not sure. You can leave this one blank.",
        optional=True,
        choices=(("0", ("none", "zero", "no hypos", "never")), ("1-2", ("1 or 2", "one or two", "once or twice", "1 to 2")), ("3+", ("3 or more", "three or more", "3 times or more", "many")), ("unsure", ("not sure", "unsure"))),
    ),
    ChatStep(
        "severeHypo", "choice", "In the last 12 months, did you have a hypo where you needed someone else to help you? Yes or no. You can leave this one blank.", optional=True,
        choices=(("yes", ("yes", "i needed", "i did need")), ("no", ("no", "did not", "didn't", "never needed"))),
    ),
    ChatStep("gold", "scale", "How well do you notice a hypo coming on? Say a number from 1 (always aware) to 7 (never aware). You can leave this one blank.", optional=True),
    ChatStep(
        "conditions", "multi", "Has a doctor told you that you have any of these? High blood pressure, high cholesterol, kidney disease, heart disease or a past heart attack, stroke or mini-stroke, heart failure, diabetic eye disease, nerve problems in the feet, a past foot ulcer or amputation, sleep apnoea, fatty liver, or anaemia or thalassaemia. Name them, or say none. You can leave this one blank.",
        optional=True,
    ),
    ChatStep("otherConditions", "free", "Any other condition? Type it in, or say none. You can leave this one blank.", optional=True),
    ChatStep("allergies", "allergy", "Are you allergic to any medicine, food or material? Name it, and what happens if you like, such as penicillin (rash). Or say none. You can leave this one blank.", optional=True),
    ChatStep(
        "eyeCheck", "choice", "When did you last have an eye check, the retinal photo? In the last year, more than a year ago, or never or not sure. You can leave this one blank.",
        optional=True,
        choices=(("within_year", ("in the last year", "last year", "within a year", "this year")), ("over_year", ("more than a year", "over a year", "a year ago", "over one year")), ("never_unsure", ("never", "not sure", "unsure"))),
    ),
    ChatStep(
        "footCheck", "choice", "When did you last have a foot check? In the last year, more than a year ago, or never or not sure. You can leave this one blank.",
        optional=True,
        choices=(("within_year", ("in the last year", "last year", "within a year", "this year")), ("over_year", ("more than a year", "over a year", "a year ago", "over one year")), ("never_unsure", ("never", "not sure", "unsure"))),
    ),
    ChatStep("labDate", "date", "What is the date of your most recent blood test? For example 12 March 2026. You can leave this one blank.", optional=True),
    ChatStep("hba1c", "number", "What was your HbA1c? Say the number and the unit, like 7.2% or 55 mmol/mol. You can leave this one blank.", optional=True),
    ChatStep("fastingGlucose", "number", "What was your fasting glucose? Say the number and the unit, like 7.4 mmol/L or 133 mg/dL. You can leave this one blank.", optional=True),
    ChatStep("fastingInsulin", "number", "What was your fasting insulin, in µIU/mL? Say a number, like 11.5. You can leave this one blank.", optional=True),
    ChatStep(
        "cgm", "choice", "Which glucose sensor do you use? Libre, Dexcom, another sensor, or none. You can leave this one blank.", optional=True,
        choices=(("libre", ("libre", "freestyle", "abbott")), ("dexcom", ("dexcom",)), ("other", ("another sensor", "other sensor", "other")), ("none", ("none", "no sensor", "no glucose sensor"))),
    ),
    ChatStep(
        "wearable", "choice", "Which watch do you wear? Apple, Garmin, Samsung, Fitbit, Xiaomi, another watch, or none. You can leave this one blank.", optional=True,
        choices=(
            ("apple", ("apple", "apple watch")), ("garmin", ("garmin",)), ("samsung", ("samsung", "galaxy watch")), ("fitbit", ("fitbit",)),
            ("xiaomi", ("xiaomi", "mi band", "mi watch")), ("other", ("another watch", "other watch", "other")), ("none", ("none", "no watch")),
        ),
    ),
    ChatStep(
        "workType", "choice", "What is your work like? Mostly sitting, standing, physical, a mix, shifts, or not working? You can leave this one blank.",
        optional=True, column="work_type",
        choices=(
            ("desk", ("mostly sitting", "office")), ("standing", ("mostly standing",)), ("physical", ("physical work", "manual", "labour", "labor")),
            ("mixed", ("a mix", "both")), ("shift", ("shifts", "nights", "night shift")), ("not_working", ("retired", "not working", "unemployed", "homemaker")),
        ),
    ),
    ChatStep("workDays", "days", "Which days do you usually work? For example Mon to Fri. You can leave this one blank.", optional=True, working_only=True),
    ChatStep("workStart", "time", "What time does work start? For example 7.30am. You can leave this one blank.", optional=True, working_only=True),
    ChatStep("workEnd", "time", "What time does work end? For example 6pm. You can leave this one blank.", optional=True, working_only=True),
    ChatStep("contactName", "text", "Who should we contact in an emergency? Their name, please.", column="emergency_contact_name"),
    ChatStep("contactRelation", "text", "How are they to you? For example, wife, son or friend.", column="emergency_contact_relation", max_len=100),
    ChatStep("contactPhone", "phone", "What is their mobile number? For example +65 9123 4567.", column="emergency_contact_phone", max_len=50),
    ChatStep("contactEmail", "email", "What is their email? For example name@gmail.com.", column="emergency_contact_email"),
)
STEP_BY_ID = {s.id: s for s in CHAT_STEPS}


def chat_step(step_id: str) -> ChatStep:
    step = STEP_BY_ID.get(step_id)
    if step is None:
        raise OnboardingError(f"'{step_id}' is not a question of the chat setup.")
    return step


# ------------------------------------------------------------------ the plain rules (no model)
def _norm(text: str) -> str:
    """Lower case, one space between words, underscores as spaces, no trailing punctuation: the form the rules match on."""
    return re.sub(r"\s+", " ", text.lower().replace("’", "'").replace("_", " ")).strip(" .!?")


def _has_phrase(norm: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", norm) is not None


def _choice(step: ChatStep, norm: str) -> str | None:
    """The one choice whose words appear in the answer. Several matches, or none, is not guessed."""
    hits = [value for value, words in step.choices if any(_has_phrase(norm, w) for w in (value.replace("_", " "), *words))]
    return hits[0] if len(hits) == 1 else None


def _codes(norm: str) -> list[str]:
    """The condition codes named. "none" stands alone: with another condition in the same answer nothing is read."""
    hits = [code for code, words in CONDITION_WORDS if any(_has_phrase(norm, w) for w in words)]
    if "none" in hits:
        return ["none"] if hits == ["none"] else []
    return hits


def _days(norm: str) -> list[int] | None:
    """Day numbers from words (Mon to Fri, weekdays, every day) or digits 1 (Monday) to 7 (Sunday)."""
    if re.fullmatch(r"[1-7](?:\s*[,/ ]\s*[1-7])*", norm):
        return sorted({int(d) for d in re.findall(r"[1-7]", norm)})
    if re.search(r"every ?day|daily|all week", norm):
        return list(range(1, 8))
    days: set[int] = set()
    if "weekday" in norm:
        days |= set(range(1, 6))
    if "weekend" in norm:
        days |= {6, 7}
    for first, last in _DAY_RANGE.findall(norm):
        start, end = _DAY_NAMES[first], _DAY_NAMES[last]
        days |= set(range(start, end + 1)) if start <= end else set(range(start, 8)) | set(range(1, end + 1))
    days |= {_DAY_NAMES[w] for w in _DAY_WORD.findall(_DAY_RANGE.sub(" ", norm))}
    return sorted(days) if days else None


def _clock(norm: str) -> str | None:
    """A time of day as HH:MM. 7.30am, 7am, 6 pm, 19:00. An hour alone is not a time: the minutes or am or pm are asked for."""
    m = re.fullmatch(r"(\d{1,2})(?:[:.](\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?", norm)
    if m is None:
        return None
    hour, minute, suffix = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if suffix:
        if not 1 <= hour <= 12:
            return None
        if suffix.startswith("p") and hour != 12:
            hour += 12
        if suffix.startswith("a") and hour == 12:
            hour = 0
    elif m.group(2) is None:
        return None
    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def _date(norm: str) -> str | None:
    """A date as YYYY-MM-DD, from 2026-03-12, 12/03/2026 (day first, as in Singapore) or 12 March 2026."""
    parts: tuple[int, int, int] | None = None
    if m := re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", norm):
        parts = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    elif m := re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", norm):
        parts = (int(m.group(3)), int(m.group(2)), int(m.group(1)))
    elif m := re.fullmatch(r"(\d{1,2}) ([a-z]{3,9})\.? (\d{4})", norm):
        month = next((i for i, name in enumerate(_MONTH_NAMES, 1) if name.startswith(m.group(2))), None)
        if month is not None:
            parts = (int(m.group(3)), month, int(m.group(1)))
    if parts is None:
        return None
    try:
        return date(*parts).isoformat()
    except ValueError:
        return None


def _read_number(step: ChatStep, norm: str, known: Mapping[str, Any]) -> dict[str, Any] | None:
    """A plain number with an optional unit. A lab value with no unit is read in the unit the form shows (known), never converted."""
    m = _NUMBER.fullmatch(norm)
    if m is None:
        return None
    value, unit = m.group(1), m.group(2)
    if step.id == "hba1c":
        stated = _HBA1C_UNITS.get(unit) if unit else None
        if unit and stated is None:
            return None
        return {"hba1c": value, "hba1cUnit": stated or known.get("hba1cUnit") or "%"}
    if step.id == "fastingGlucose":
        stated = _GLUCOSE_UNITS.get(unit) if unit else None
        if unit and stated is None:
            return None
        return {"fastingGlucose": value, "glucoseUnit": stated or known.get("glucoseUnit") or "mmol/L"}
    if unit:
        allowed = _INSULIN_UNITS if step.id == "fastingInsulin" else _KG if step.id == "weightKg" else _CM
        if unit not in allowed:
            return None
    return {step.id: value}


def read_fields(step: ChatStep, text: str, known: Mapping[str, Any]) -> dict[str, Any] | None:
    """The answer fields one reply gives, read with the plain rules. None when the rules cannot tell (the model may be asked)."""
    t = " ".join(text.split())
    norm = _norm(t)
    if not t:
        return None
    sid = step.id
    if step.kind == "text":
        if len(t) > 100 or re.search(r"[\d@]", t):
            return None
        m = re.match(r"(?:my name is|i am|i'm|call me|this is|it's)\s+(.+)$", t, re.I)
        value = (m.group(1) if m else t).strip(" .,")
        return {sid: value} if value else None
    if step.kind == "free":
        return {sid: t}
    if step.kind == "year":
        m = re.fullmatch(r"(?:in |since |born in |i was born in |i was told in |year )?((?:19|20)\d{2})", norm)
        return {sid: m.group(1)} if m else None
    if step.kind == "number":
        return _read_number(step, norm, known)
    if step.kind == "scale":
        m = re.fullmatch(r"([1-7])(?: .*)?", norm)
        return {sid: m.group(1)} if m else None
    if step.kind == "email":
        found = _EMAIL_IN_TEXT.findall(t)
        return {sid: found[0]} if len(found) == 1 else None
    if step.kind == "phone":
        m = _PHONE_IN_TEXT.search(t)
        return {sid: m.group(0).strip()} if m else None
    if step.kind == "choice":
        value = _choice(step, norm)
        return {sid: value} if value else None
    if step.kind == "multi":
        codes = _codes(norm)
        return {sid: codes} if codes else None
    if step.kind == "allergy":
        if norm in NONE_WORDS:
            return {"allergies": [], "noAllergies": True}
        if len(t.split()) > 6:                      # a sentence: the model picks out the substance and the reaction
            return None
        m = re.fullmatch(r"(.+?)\s*\((.+)\)", t)
        substance, reaction = (m.group(1), m.group(2)) if m else (t, "")
        substance = substance.strip(" .,")
        if not substance:
            return None
        return {"allergies": [{"substance": substance, "reaction": reaction.strip()}], "noAllergies": False}
    if step.kind == "days":
        days = _days(norm)
        return {sid: days} if days else None
    if step.kind == "time":
        clock = _clock(norm)
        return {sid: clock} if clock else None
    if step.kind == "date":
        iso = _date(norm)
        return {sid: iso} if iso else None
    return None


def _date_value(value: Any) -> date | None:
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _int_value(value: Any) -> int | None:
    return int(value) if isinstance(value, str) and value.isdigit() else None


def _check(
    step: ChatStep, fields: Mapping[str, Any], known: Mapping[str, Any], labels: Mapping[str, frozenset[str]], this_year: int, today: date,
) -> str | None:
    """Why the value read for this step cannot be used, or None. The limits and rules are the form's and the save's."""
    sid = step.id
    value = fields.get(sid)
    if sid == "allergies":
        bad = any(len(a["substance"]) > 200 or len(a["reaction"]) > 200 for a in value)
        return "Keep each allergy to 200 characters or fewer." if bad else None
    if isinstance(value, str) and len(value) > step.max_len:
        return f"Keep it to {step.max_len} characters or fewer."
    if sid == "reminderEmail" and not EMAIL.match(value):
        return "That does not look like an email address."
    if sid == "contactPhone" and (p := phone_problem(value)):
        return p
    if step.limits is not None and not step.limits[0] <= float(value) <= step.limits[1]:
        return f"Enter a number from {step.limits[0]} to {step.limits[1]}."
    if step.column is not None:
        stored = int(value) if sid == "birthYear" else value
        problems = check_profile({step.column: stored}, labels, this_year, today)
        if problems:
            return problems[0]
    if sid in HISTORY_CHECK:
        vals: dict[str, Any] = {HISTORY_CHECK[sid]: _date_value(value) if sid == "labDate" else int(value) if sid == "diagnosedYear" else value}
        if sid == "diagnosedYear":
            vals["birth_year"] = _int_value(known.get("birthYear"))
        if sid in LAB_CHECK:
            vals["lab_date"] = _date_value(known.get("labDate"))
        if sid == "hba1c":
            vals["hba1c_unit"] = fields["hba1cUnit"]
        if sid == "fastingGlucose":
            vals["glucose_unit"] = fields["glucoseUnit"]
        problems = history_problems(vals, today)
        if problems:
            hint = UNIT_HINT.get(sid) if problems[0].startswith(("HbA1c must", "Fasting glucose must")) else None
            return " ".join(p for p in (problems[0], hint) if p)
    return None


def _asked(step: ChatStep, known: Mapping[str, Any]) -> bool:
    """Whether a question is asked for what the person has said so far: the work week only when they work."""
    return not step.working_only or known.get("workType") in WORKING


def _next_id(step_id: str, known: Mapping[str, Any]) -> str | None:
    ids = [s.id for s in CHAT_STEPS]
    return next((s.id for s in CHAT_STEPS[ids.index(step_id) + 1:] if _asked(s, known)), None)


def _result(fields: dict[str, Any], understood: bool, next_step: str | None, reply: str) -> dict[str, Any]:
    return {"fields": fields, "understood": understood, "next_step": next_step, "reply": reply}


def _understood(step: ChatStep, fields: dict[str, Any], known: Mapping[str, Any]) -> dict[str, Any]:
    reply = f"Thanks, {fields['name']}." if step.id == "name" else "Got it."
    return _result(fields, True, _next_id(step.id, {**known, **fields}), reply)


# ------------------------------------------------------------------ the model path (only for sentences the rules cannot read)
class ChatExtraction(BaseModel):
    """What the model may fill from one message, keyed by the store names. Every field is optional: null means not stated."""

    name: str | None = None
    reminderEmail: str | None = None
    hasDiabetes: str | None = None
    birthYear: str | None = None
    gender: str | None = None
    heightCm: str | None = None
    weightKg: str | None = None
    waistCm: str | None = None
    diagnosedYear: str | None = None
    careSetting: str | None = None
    healthierSg: str | None = None
    hypo3m: str | None = None
    severeHypo: str | None = None
    gold: str | None = None
    conditions: str | None = None
    otherConditions: str | None = None
    allergies: str | None = None
    eyeCheck: str | None = None
    footCheck: str | None = None
    labDate: str | None = None
    hba1c: str | None = None
    fastingGlucose: str | None = None
    fastingInsulin: str | None = None
    cgm: str | None = None
    wearable: str | None = None
    workType: str | None = None
    workDays: str | None = None
    workStart: str | None = None
    workEnd: str | None = None
    contactName: str | None = None
    contactRelation: str | None = None
    contactPhone: str | None = None
    contactEmail: str | None = None


CHAT_PROMPT = """You fill in a health app's profile from one message a person typed in answer to a question.
Fill ONLY the fields the person clearly stated, in their own words. Use null for anything not stated, unclear, or a skip ("skip", "I do not know").
Never guess. Never work out one value from another (for example, do not turn an age into a birth year, or a date from "last month").
Never give advice.
Allowed values:
- name, contactName, contactRelation, otherConditions: the words the person used.
- reminderEmail, contactEmail: the email address as written. contactPhone: the phone number as written.
- birthYear, diagnosedYear: four digits. labDate: YYYY-MM-DD.
- gender: female or male only. hasDiabetes: yes or not_sure.
- heightCm, weightKg, waistCm, fastingInsulin: a number, without the unit.
- hba1c: the number with its unit if given, such as 7.2% or 55 mmol/mol. fastingGlucose: the number with its unit if given, such as 7.4 mmol/L or 133 mg/dL.
- careSetting: polyclinic, gp, hospital or none. healthierSg: yes, no or unsure.
- hypo3m: 0, 1-2, 3+ or unsure. severeHypo: yes or no. gold: a number from 1 to 7.
- conditions: the codes, comma separated: hypertension, high_cholesterol, kidney, heart, stroke, heart_failure, eye, nerve, foot_ulcer, sleep_apnoea, fatty_liver, anaemia; or none.
- allergies: the substance, with the reaction in brackets if given, such as penicillin (rash); or none.
- eyeCheck, footCheck: within_year, over_year or never_unsure.
- cgm: libre, dexcom, other or none. wearable: apple, garmin, samsung, fitbit, xiaomi, other or none.
- workType: desk, standing, physical, mixed, shift or not_working.
- workDays: the day numbers 1 (Monday) to 7 (Sunday), comma separated. workStart, workEnd: a 24-hour time such as 07:30.
The question being answered: {ask}
Message: "{message}"
"""


def model_extract(text: str, step: ChatStep) -> dict[str, str] | None:
    """The fields the model reads from one message, keyed by the store names. None when the model cannot answer (no key, cap reached, an error)."""
    try:
        from google.genai import types

        client = gateway._client()
        if not usage.allowed("vertex_generate"):
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
        usage.record("vertex_generate", getattr(um, "prompt_token_count", 0) or 0, getattr(um, "candidates_token_count", 0) or 0)
        parsed = resp.parsed if isinstance(resp.parsed, ChatExtraction) else ChatExtraction.model_validate_json(resp.text or "")
    except Exception as e:  # no key, quota, network or a bad shape: the person is asked again or sent to the form
        logger.warning("chat answer not read by the model: %s", type(e).__name__)
        return None
    return {k: v for k, v in parsed.model_dump().items() if v}


# ------------------------------------------------------------------ the answer to one question
def answer_step(
    step_id: str,
    text: str,
    labels: Mapping[str, frozenset[str]],
    this_year: int,
    extract: Callable[[str, ChatStep], dict[str, str] | None] | None = None,
    known: Mapping[str, Any] | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Read the person's answer to one question. Nothing is written.

    `known` holds the answers already on the form that this answer depends on (birthYear, labDate, hba1cUnit, glucoseUnit,
    workType). `today` is the current date. Every value goes through the same checks as the form and the save. An optional
    question can be skipped; a required one cannot, and the model is not asked about a skip.
    """
    step = chat_step(step_id)
    known = dict(known or {})
    today = today or date(this_year, 12, 31)
    text = " ".join((text or "").split())[:1000]
    norm = _norm(text)
    if not text:
        return _result({}, False, step.id, step.ask)
    if step.optional and (norm in SKIP_WORDS or (step.kind == "free" and norm in NONE_WORDS)):
        return _result({}, True, _next_id(step.id, known), "Skipped.")
    if norm in SKIP_WORDS and step.kind != "choice":
        return _result({}, False, step.id, NEEDED_REPLY)

    fields = read_fields(step, text, known)
    if fields is not None:
        problem = _check(step, fields, known, labels, this_year, today)
        return _understood(step, fields, known) if problem is None else _result({}, False, step.id, problem)
    if norm in SKIP_WORDS:
        return _result({}, False, step.id, NEEDED_REPLY)

    got = (model_extract if extract is None else extract)(text, step)
    if got is None:
        return _result({}, False, step.id, FALLBACK_REPLY)
    fields, problems = {}, {}
    for key, raw in got.items():
        other = STEP_BY_ID.get(key)
        # free text and allergies are taken only from the question asked, so a sentence about one thing never fills another
        if other is None or (other.id != step.id and other.kind in ("free", "allergy")) or not _asked(other, {**known, **fields}):
            continue
        value = read_fields(other, raw, known)
        if value is None:
            continue
        problem = _check(other, value, known, labels, this_year, today)
        if problem is None:
            fields.update(value)
        else:
            problems[key] = problem
    if step.id in fields:
        return _understood(step, fields, known)
    return _result(fields, False, step.id, problems.get(step.id, FALLBACK_REPLY))
