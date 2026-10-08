"""Shapes for the medicine scan (prd F2). `RawExtraction` is what the vision model must return; `ScanOutcome` is what the scan service hands on."""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ItemType = Literal["prescription_label", "blister_or_box", "supplement", "tcm", "otc", "unknown"]
MealRelation = Literal["before_meal", "after_meal", "with_meal", "na"]

# The fields read from a label, in the order shown to the user.
FIELD_NAMES = ("name", "strength", "dose_amount", "dose_unit", "times_per_day", "when_to_take", "meal_relation", "meal_offset_minutes",
               "drowsiness_warning", "directions", "prescriber", "start_date", "total_quantity")
# A scan missing any of these cannot become a medicine (medications.name, .frequency and .total_quantity are NOT NULL).
REQUIRED_FIELDS = ("name", "times_per_day", "total_quantity")


class RawField(BaseModel):
    model_config = ConfigDict(extra="ignore")
    value: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_text: str | None = None

    @field_validator("value", "source_text", mode="before")
    @classmethod
    def _as_text(cls, v: Any) -> Any:
        """The model sometimes returns 500 or true instead of "500" or "true". Accept that, keep everything else strict."""
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        return v

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp(cls, v: Any) -> float:
        try:
            return min(1.0, max(0.0, float(v)))
        except (TypeError, ValueError):
            return 0.0


class RawIngredient(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str | None = None
    amount: str | None = None


class RawItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    item_type: ItemType = "unknown"
    name: RawField = RawField()
    strength: RawField = RawField()
    dose_amount: RawField = RawField()
    dose_unit: RawField = RawField()
    times_per_day: RawField = RawField()
    when_to_take: RawField = RawField()
    meal_relation: RawField = RawField()
    meal_offset_minutes: RawField = RawField()
    drowsiness_warning: RawField = RawField()
    directions: RawField = RawField()
    prescriber: RawField = RawField()
    start_date: RawField = RawField()
    total_quantity: RawField = RawField()
    ingredients: list[RawIngredient] = []

    @field_validator("item_type", mode="before")
    @classmethod
    def _known_type(cls, v: Any) -> str:
        return v if v in ("prescription_label", "blister_or_box", "supplement", "tcm", "otc") else "unknown"


class RawExtraction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    is_medication_item: bool = False
    readable: bool = False
    issue: str | None = None
    items: list[RawItem] = []


# --- after scoring --------------------------------------------------------------------------------------------

class ScoredField(BaseModel):
    value: str | None
    confidence: float          # final: the lower of the model's score and every code check
    model_confidence: float
    source_text: str | None
    flags: list[str] = []      # why the confidence was lowered, for example source_not_in_ocr
    needs_confirmation: bool   # value present and confidence below the threshold: the user must type it


class ScoredItem(BaseModel):
    item_type: ItemType
    fields: dict[str, ScoredField]
    ingredients: list[RawIngredient] = []
    min_confidence: float


ReviewMode = Literal["confirm", "manual"]


class ScanOutcome(BaseModel):
    status: Literal["needs_review", "failed"]
    review_mode: ReviewMode          # "confirm": every value is clear, the user still confirms. "manual": the user types the form.
    reasons: list[str]               # stable codes: low_confidence, missing_required, unreadable, not_a_medicine, invalid_json, service_unavailable, ocr_empty
    items: list[ScoredItem] = []
    prompt_version: str | None = None
    model_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    mask_summary: dict[str, int] = {}   # counts only, never the masked text


# --- what the user confirms -----------------------------------------------------------------------------------

class DoseTime(BaseModel):
    """One dose. An empty `dose_time` means the medicine is taken only when needed: no clock time, no daily dose expected."""
    dose_time: time | None = None
    quantity: Decimal = Field(gt=0)
    meal_relation: Literal["before_meal", "after_meal", "na"] = "na"


class ConfirmedMedication(BaseModel):
    """The values the user confirmed or typed. This, not the model's answer, is what gets saved."""
    name: str = Field(min_length=1, max_length=200)
    kind: Literal["prescription", "otc", "supplement", "tcm"] = "prescription"
    strength: str | None = Field(default=None, max_length=100)
    doses: list[DoseTime] = Field(min_length=1, max_length=6)
    directions: str | None = Field(default=None, max_length=500)   # verbatim, as on the label
    prescriber: str | None = Field(default=None, max_length=200)
    total_quantity: int = Field(ge=1)    # required: the total supplied, to predict when it runs out
    start_date: date | None = None

    @model_validator(mode="after")
    def _times_or_as_needed(self) -> "ConfirmedMedication":
        times = [d.dose_time for d in self.doses]
        if any(t is None for t in times) and len(times) > 1:
            raise ValueError("an as-needed medicine has one entry and no clock times")
        if len(set(times)) != len(times):
            raise ValueError("each time of day can only be listed once")
        return self

    @property
    def as_needed(self) -> bool:
        return self.doses[0].dose_time is None
