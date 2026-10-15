"""Urgent low-glucose alert: response and request shapes (camelCase on the wire)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.medicines import Camel


class Channels(Camel):
    phone: bool
    email: bool


class UrgentState(Camel):
    id: str | None = None
    status: Literal["none", "active", "acknowledged", "escalated"]
    tier: Literal["none", "low", "very_low"]
    value: float | None = None
    since: datetime | None = None
    age_minutes: int | None = None
    recheck_at: datetime | None = None
    contact_after: datetime | None = None
    demo: bool = False
    has_contact: bool
    contact_name: str | None = None
    contact_phone: str | None = None
    channels: Channels
    email_queued: bool = False
    escalated: bool = False
    escalation_note: Literal["no_contact_email", "email_not_ready"] | None = None   # why no one was told, when an escalation could not be sent
    emergency_number: str
    recheck_minutes: int
    contact_after_minutes: int


class SimulateIn(Camel):
    value: float = Field(gt=0, le=33.3)
