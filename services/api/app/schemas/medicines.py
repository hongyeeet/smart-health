"""API shapes for adding a medicine by hand (screen H8) and returning it. camelCase on the wire, like the other routers.

They mirror `NewMedication` and `Medication` in apps/web/src/data. The save itself is `app/services/scan_store.confirm_medication`.
"""
from __future__ import annotations

from datetime import date, datetime
from datetime import time as ClockTime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

Kind = Literal["prescription", "otc", "supplement", "tcm"]
MealRelation = Literal["before_meal", "after_meal", "na"]


class Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class DoseIn(Camel):
    time: ClockTime | None = None                    # "08:00", the person's local clock time. Empty means "only when needed"
    quantity: Decimal = Field(gt=0, le=100)     # units each time (tablets, capsules or measures)
    meal_relation: MealRelation = "na"


class NewMedicationIn(Camel):
    name: str = Field(min_length=1, max_length=200)
    kind: Kind = "prescription"
    strength: str | None = Field(default=None, max_length=100)
    doses: list[DoseIn] = Field(min_length=1, max_length=6)
    total_quantity: int = Field(ge=1, le=100000)     # required: the total supplied
    start_date: date | None = None
    directions: str | None = Field(default=None, max_length=500)
    scan_id: str | None = Field(default=None, max_length=64)   # set when the typed form completes a scan that needed manual entry

    @model_validator(mode="after")
    def _times_or_as_needed(self) -> "NewMedicationIn":
        times = [d.time for d in self.doses]
        if any(t is None for t in times) and len(times) > 1:
            raise ValueError("an as-needed medicine has one entry and no clock times")
        if len(set(times)) != len(times):
            raise ValueError("each time of day can only be listed once")
        return self


class Refill(Camel):
    days_left: int
    units_left: int


class MedicationOut(Camel):
    id: str
    name: str
    strength: str
    kind: Kind
    times: list[str]
    with_food: bool
    as_needed: bool = False                      # taken only when needed: no dose times, no reminders, no supply estimate
    purpose: str = ""
    badge: Literal["interaction", "not_checked"] | None = None
    refill: Refill | None = None
    refill_source: Literal["stock", "estimate"] | None = None    # 'stock': from the count in hand; 'estimate': from the pack date
    side_effects: list[str] = []
    end_date: date | None = None                 # the last day of a course (an antibiotic): after it the medicine has no supply to show


class WebSourceOut(Camel):
    title: str
    url: str


class ExplanationPartsOut(Camel):
    """The four labelled parts (prompt version 2). Each is a short text; a part the pages did not cover is an empty string."""
    for_diabetes: str = ""              # what it is for in the person's diabetes (or in general, when it is not a diabetes medicine)
    how_it_works: str = ""              # one sentence
    what_you_may_notice: str = ""
    why_timing_matters: str = ""


class ExplanationOut(Camel):
    """The plain-language explanation of a medicine and the web pages it came from (docs/specs/f3-explainer.md).

    `parts` is null for an explanation made before the four parts existed: the page then shows the older layout (`purpose`)."""
    status: Literal["ready", "not_identified"]
    purpose: str = ""
    parts: ExplanationPartsOut | None = None
    side_effects: list[str] = []
    tell_doctor: str = ""
    sources: list[WebSourceOut] = []
    generated_at: datetime


class MedicineScopeOut(Camel):
    """Whether a typed or scanned name is outside what the app is for. A gentle note only: it never blocks a save."""
    out_of_scope: bool


class MedicationDetailOut(MedicationOut):
    """One medicine on its own page (H6). `directions` is the label text exactly as saved; `explanation` is empty until it is made."""
    directions: str | None = None
    explanation: ExplanationOut | None = None


class QuestionIn(Camel):
    text: str = Field(min_length=3, max_length=500)


class QuestionOut(Camel):
    id: str
