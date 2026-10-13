"""API shape of the Me care screens (K3 Care plan, K7 Plan an appointment, K4 Connected sources). camelCase on the wire.

The server builds every label and status word (app/services/care.py); the screens only lay them out. Nothing here is advice: a check
says when something was done and when it is due, from stored dates only.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.medicines import Camel

# The visit kinds a person can log now. "vaccination" and "dental" were removed from the form (they stay in the database, see below).
AppointmentKind = Literal["gp_review", "diabetes_review", "eye_screening", "foot_screening", "kidney_test", "hba1c_test", "other"]
# Every kind the database can hold. Old visits with a removed kind are still read and shown.
StoredAppointmentKind = Literal[
    "gp_review", "diabetes_review", "eye_screening", "foot_screening", "kidney_test", "hba1c_test", "vaccination", "dental", "other",
]
AppointmentStatus = Literal["suggested", "planned", "completed", "cancelled", "missed", "past"]   # "past": a planned visit whose time has passed (K3 Earlier visits)
PreventiveStatus = Literal["ok", "due_soon", "overdue", "unknown"]
QuestionOrigin = Literal["user", "refused_chat", "checkin", "agent_suggested"]
QuestionStatus = Literal["open", "asked"]
SourceKey = Literal["cgm", "watch", "camera"]
SourceStatus = Literal["connected", "connected_no_data", "not_connected", "on_device"]
Freshness = Literal["up_to_date", "old", "none"]


class AppointmentOut(Camel):
    id: str
    kind: StoredAppointmentKind
    kind_label: str
    status: AppointmentStatus
    scheduled_for: datetime | None
    scheduled_label: str | None          # "Sat 11 Oct, 10:00 am", Singapore time
    location: str | None                 # kept for visits saved before the Place field was removed; not shown on the cards
    suggested_reason: str | None         # plain sentence, from the rule that suggested it
    confirmed_at: datetime | None


class PreventiveOut(Camel):
    kind: str
    label: str
    status: PreventiveStatus
    last_done_on: date | None
    next_due_on: date | None
    detail: str


class QuestionOut(Camel):
    id: str
    text: str
    origin: QuestionOrigin | None
    origin_label: str
    status: QuestionStatus
    created_at: datetime
    can_remove: bool


class CarePlan(Camel):
    next_appointment: AppointmentOut | None
    upcoming: list[AppointmentOut]
    earlier: list[AppointmentOut] = []    # planned visits whose time has passed, newest first; status "past"
    preventive: list[PreventiveOut]
    questions: list[QuestionOut]


class NewQuestion(Camel):
    text: str = Field(min_length=1, max_length=300)
    suggested_key: str | None = Field(default=None, max_length=40)   # one of care.SUGGESTED_QUESTIONS: the question came from the suggestions list

    @field_validator("text")
    @classmethod
    def _clean(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Write the question in a few words.")
        return v


class NewAppointment(Camel):
    kind: StoredAppointmentKind          # the service refuses a removed kind unless it confirms a suggested visit of that kind
    scheduled_for: datetime              # a naive time is Singapore time, as the form sends it
    suggested_id: UUID | None = None     # confirming a visit Smart Health suggested, rather than adding a new one


class SourceOut(Camel):
    key: SourceKey
    label: str
    model: str | None
    status: SourceStatus
    status_label: str                    # "Connected, last data 2 Oct 07:40" or "Not connected"
    last_data_at: datetime | None
    freshness: Freshness
    note: str


class Sources(Camel):
    sources: list[SourceOut]


class QuestionDone(Camel):
    done: bool                           # true marks it done (asked at the visit); false puts it back on the open list


class QuestionRemoved(Camel):
    id: str
    status: Literal["archived"]
