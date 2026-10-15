"""API shapes for the Me settings screens (K5 language, K6 consents, K8 export and deletion request, K9 emergency contact).

camelCase on the wire, like the other routers. The rules (what a valid phone or email is) live in app/services/me_settings.py.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.medicines import Camel

Language = Literal["en", "zh", "ms", "ta"]
ConsentKind = Literal["data_processing", "brief_sharing", "calendar_access", "caregiver_view", "research_use"]


class LanguageIn(Camel):
    language: Language


class LanguageOut(Camel):
    language: Language


class ConsentIn(Camel):
    granted: bool


class ConsentOut(Camel):
    kind: ConsentKind
    granted: bool
    version: str | None = None
    granted_at: datetime | None = None         # when the current grant started; None when not granted


class ConsentHistoryOut(Camel):
    kind: ConsentKind
    version: str
    granted_at: datetime
    revoked_at: datetime | None = None         # None: still granted


class ConsentsOut(Camel):
    consents: list[ConsentOut]
    history: list[ConsentHistoryOut]


class DeleteRequestIn(Camel):
    confirm: str = Field(max_length=20)        # must be exactly "DELETE"; checked in the service


class DeleteRequestOut(Camel):
    status: Literal["received"]
    requested_at: datetime
    process_by: datetime                       # promised within 30 days of the request


class ContactIn(Camel):
    name: str | None = Field(default=None, max_length=100)
    relation: str | None = Field(default=None, max_length=60)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=254)


class ContactOut(Camel):
    name: str | None = None
    relation: str | None = None
    phone: str | None = None
    email: str | None = None
    email_supported: bool                      # False until migration 0031 adds the column; the screen says so


class ContactItem(Camel):
    id: str                                    # "primary" for the first contact, a uuid for the others
    name: str | None = None
    relation: str | None = None
    phone: str | None = None
    email: str | None = None


class ContactsOut(Camel):
    contacts: list[ContactItem]
    email_supported: bool
