"""API shapes for adding a medicine by hand (screen H8) and returning it. camelCase on the wire, like the other routers.

They mirror `NewMedication` and `Medication` in apps/web/src/data. The save itself is `app/services/scan_store.confirm_medication`.
"""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

Kind = Literal["prescription", "otc", "supplement", "tcm"]
MealRelation = Literal["before_meal", "after_meal", "na"]
WhenToTake = Literal["morning", "noon", "afternoon", "evening", "night", "bedtime", "as_needed"]


class Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class DoseIn(Camel):
    time: time                                  # "08:00", the person's local clock time
    quantity: Decimal = Field(gt=0, le=100)     # units each time (tablets, capsules or measures)
    meal_relation: MealRelation = "na"
    when_to_take: WhenToTake | None = None


class NewMedicationIn(Camel):
    name: str = Field(min_length=1, max_length=200)
    kind: Kind = "prescription"
    strength: str | None = Field(default=None, max_length=100)
    doses: list[DoseIn] = Field(min_length=1, max_length=6)
    total_quantity: int = Field(ge=1, le=100000)     # required: the total supplied
    start_date: date | None = None
    directions: str | None = Field(default=None, max_length=500)
    scan_id: str | None = Field(default=None, max_length=64)   # set when the typed form completes a scan that needed manual entry


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
    purpose: str = ""
    badge: Literal["interaction", "not_checked"] | None = None
    refill: Refill | None = None
    side_effects: list[str] = []
