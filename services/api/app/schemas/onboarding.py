"""API shapes for onboarding (screens A3 and A6). camelCase on the wire, like the other routers.

Every field of `ProfileIn` is optional. The service writes only the fields the request sent, so a request that leaves a field out
never blanks the stored value. Enum values (gender, work type, language, has-diabetes) are checked against the database enums in
app/services/onboarding.py, so an unknown value is refused with a plain message rather than a schema error.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class ProfileIn(Camel):
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


class OnboardingOut(Camel):
    profile: ProfileOut | None
    data_consent: bool                              # the data-processing consent is active
    email_column: bool                              # emergency_contact_email exists in the database


class SaveOut(OnboardingOut):
    not_saved: list[str] = []                       # request fields that were not stored, with the reason in the name


class CompleteOut(Camel):
    consent_recorded: bool                          # False when an active consent already existed
    completed_at: datetime
