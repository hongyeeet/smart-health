"""API shapes for onboarding (screens A3 and A6). camelCase on the wire, like the other routers.

Every field of `ProfileIn` is optional. The service writes only the fields the request sent, so a request that leaves a field out
never blanks the stored value. Enum values (gender, work type, language, has-diabetes) are checked against the database enums in
app/services/onboarding.py, so an unknown value is refused with a plain message rather than a schema error.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class AllergyIn(Camel):
    substance: str = Field(max_length=200)
    reaction: str | None = Field(default=None, max_length=200)


class AllergyOut(Camel):
    substance: str
    reaction: str | None = None


class ProfileIn(Camel):
    """A key left out of the body is not written. A key sent as null (or an empty list) clears that answer.

    The history fields (diabetes history, low glucose, conditions, allergies, check dates, labs, waist) need migration 0032. Until
    it is applied they are not written and are named in `notSaved`; the rest of the save still happens.
    """

    display_name: str | None = Field(default=None, max_length=200)
    language: str | None = Field(default=None, max_length=10)
    has_diabetes: str | None = Field(default=None, max_length=20)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    gender: str | None = Field(default=None, max_length=40)
    race: str | None = Field(default=None, max_length=100)
    height_cm: Decimal | None = Field(default=None, ge=100, le=250)
    weight_kg: Decimal | None = Field(default=None, ge=25, le=300)
    work_type: str | None = Field(default=None, max_length=40)
    work_days: list[int] | None = Field(default=None, max_length=7)      # 1 = Monday ... 7 = Sunday
    work_start: str | None = Field(default=None, max_length=5)            # "HH:MM", the person's local clock time
    work_end: str | None = Field(default=None, max_length=5)
    emergency_contact_name: str | None = Field(default=None, max_length=200)
    emergency_contact_phone: str | None = Field(default=None, max_length=50)
    emergency_contact_relation: str | None = Field(default=None, max_length=100)
    emergency_contact_email: str | None = Field(default=None, max_length=200)   # saved only once migration 0031 is applied
    watch_model: str | None = Field(default=None, max_length=100)
    cgm_model: str | None = Field(default=None, max_length=100)
    allergies_note: str | None = Field(default=None, max_length=2000)
    conditions_note: str | None = Field(default=None, max_length=2000)
    waist_cm: Decimal | None = Field(default=None, ge=40, le=200)          # saved as a new body measurement only when it changed
    # diabetes history
    diagnosed_year: int | None = Field(default=None, ge=1900, le=2100)     # the year the person was told they have type 2 diabetes
    care_setting: str | None = Field(default=None, max_length=40)          # polyclinic, gp, hospital, none
    healthier_sg: str | None = Field(default=None, max_length=20)          # yes, no, unsure
    # low glucose history
    hypo_last3m: str | None = Field(default=None, alias="hypoLast3m", max_length=10)   # 0, 1-2, 3+, unsure
    hypo_awareness: str | None = Field(default=None, max_length=2)         # "1" (always notices a hypo coming) to "5" (never)
    hypo_needed_help: str | None = Field(default=None, max_length=10)      # yes, no: needed someone's help in the last 12 months
    # other conditions and allergies: a sent list replaces the rows written from onboarding
    conditions: list[str] | None = Field(default=None, max_length=20)      # the form's condition codes; "none" is ignored
    other_condition: str | None = Field(default=None, max_length=200)      # the free-text "any other condition"
    allergies: list[AllergyIn] | None = Field(default=None, max_length=20)
    # last diabetes checks (last year, over a year ago, never or not sure)
    eye_check: str | None = Field(default=None, max_length=20)
    foot_check: str | None = Field(default=None, max_length=20)
    # blood test: one date for the sent values; a test key that is left out is not written
    lab_date: date | None = None
    hba1c: Decimal | None = Field(default=None, alias="hba1c", ge=0, le=200)
    hba1c_unit: str | None = Field(default=None, alias="hba1cUnit", max_length=10)   # "%" or "mmol/mol"
    fasting_glucose: Decimal | None = Field(default=None, ge=0, le=1000)
    glucose_unit: str | None = Field(default=None, max_length=10)          # "mmol/L" or "mg/dL"
    fasting_insulin: Decimal | None = Field(default=None, ge=0, le=2000)   # µIU/mL


class ProfileOut(Camel):
    display_name: str
    language: str
    has_diabetes: str
    birth_year: int
    gender: str | None = None
    race: str | None = None
    height_cm: Decimal | None = None
    weight_kg: Decimal | None = None
    work_type: str | None = None
    work_days: list[int] = []
    work_start: str | None = None
    work_end: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    emergency_contact_relation: str | None = None
    emergency_contact_email: str | None = None      # always null while the column is missing
    watch_model: str | None = None
    cgm_model: str | None = None
    allergies_note: str | None = None
    conditions_note: str | None = None
    updated_at: datetime


class HistoryOut(Camel):
    """The onboarding answers that are not profile columns. Only rows written from onboarding are read. Labs: HbA1c is always in %."""

    waist_cm: Decimal | None = None
    diagnosed_year: int | None = None
    care_setting: str | None = None
    healthier_sg: str | None = None
    hypo_last3m: str | None = Field(default=None, alias="hypoLast3m")
    hypo_awareness: str | None = None
    hypo_needed_help: str | None = None
    conditions: list[str] = []
    other_condition: str | None = None
    allergies: list[AllergyOut] = []
    eye_check: str | None = None
    foot_check: str | None = None
    lab_date: date | None = None
    hba1c: Decimal | None = Field(default=None, alias="hba1c")
    hba1c_unit: str | None = Field(default=None, alias="hba1cUnit")
    fasting_glucose: Decimal | None = None
    glucose_unit: str | None = None
    fasting_insulin: Decimal | None = None


class OnboardingOut(Camel):
    profile: ProfileOut | None
    data_consent: bool                              # the data-processing consent is active
    email_column: bool                              # emergency_contact_email exists in the database
    history_ready: bool = False                     # migration 0032 is applied: the history fields are read and written
    history: HistoryOut = Field(default_factory=HistoryOut)


class SaveOut(OnboardingOut):
    not_saved: list[str] = []                       # request fields that were not stored, with the reason in the name


class CompleteOut(Camel):
    consent_recorded: bool                          # False when an active consent already existed
    completed_at: datetime


class ChatRequest(Camel):
    """One chat answer. `known` holds the answers on the form that this answer depends on (birthYear, labDate, hba1cUnit,
    glucoseUnit, workType). Nothing here is saved."""

    text: str = Field(default="", max_length=1000)  # the person's own words for one question
    step: str = Field(max_length=40)                # the question being answered, e.g. "birthYear" (see CHAT_STEPS in the service)
    known: dict[str, str | None] = Field(default_factory=dict, max_length=10)


class ChatResult(Camel):
    """The chat's reading of one answer. `fields` can hold lists (conditions, allergies, work days), so it is not the profile schema's str map."""

    fields: dict[str, Any] = {}                     # answers found in the text, keyed as the form and the answers store name them
    understood: bool                                # the answer to the step asked was read and passed the checks
    next_step: str | None = None                    # the step to ask next; the same step again when it was not understood
    reply: str                                      # a short friendly line, or the clarifying question
