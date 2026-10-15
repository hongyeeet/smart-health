"""API shapes for sharing the doctor report by link (L2). camelCase on the wire, like the other routers."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.medicines import Camel


class ShareIn(BaseModel):
    days: Literal[7, 14, 30, 90]
    hours: Literal[24, 72, 168]


class ShareCreated(Camel):
    id: UUID
    token: str                      # shown once; only its hash is stored
    path: str                       # the page on this site, for example /s/<token>
    days: int
    expires_at: datetime


class ShareItem(Camel):
    id: UUID
    days: int
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    status: Literal["active", "expired", "revoked"]
    view_count: int
    last_viewed_at: datetime | None = None


class ShareRevoked(Camel):
    id: UUID
    status: Literal["revoked"]
    revoked_at: datetime


class ShareList(Camel):
    shares: list[ShareItem]


class QuestionItem(Camel):
    id: UUID
    text: str


class AppointmentItem(Camel):
    id: UUID
    kind: str
    scheduled_for: datetime
    location: str | None = None


class ShareContext(Camel):
    questions: list[QuestionItem]
    next_appointment: AppointmentItem | None = None


class LearnedItem(Camel):
    """One thing the app learnt, as the doctor sees it. `confirmed` is false for what the person has not confirmed yet."""
    statement: str
    why: str
    confirmed: bool


class ShareExtras(Camel):
    """What the shared page shows besides the report: the four charts' data, what the app learnt, the next visit. Same as the printed brief."""
    timeline: dict
    learned: list[LearnedItem]
    next_appointment: AppointmentItem | None = None
