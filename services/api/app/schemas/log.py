"""Pydantic v2 schemas for the logs API (rules.md 4: no raw dicts across layers).

They mirror apps/web/src/data/types.ts. The web app sends and receives camelCase; Python uses snake_case.

There is no glucose log: every user wears a CGM patch, so glucose arrives from the sensor, never by hand.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class LogKind(str, Enum):
    meal = "meal"
    workout = "workout"
    symptom = "symptom"
    checkin = "checkin"


ExerciseKind = Literal[
    "strength", "walking", "running", "cycling", "swimming", "hiit", "sports",
    "yoga_pilates", "stretching_mobility", "dance", "household_gardening", "other",
]


# ── LogInput: discriminated union by `kind` ─────────────────────────────────

class MealInput(Camel):
    kind: Literal["meal"] = "meal"
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    start_at: datetime
    end_at: datetime
    portion: float = 1.0
    kcal: float | None = Field(None, ge=0)
    carbs_g: float | None = Field(None, ge=0)
    protein_g: float | None = Field(None, ge=0)
    fat_g: float | None = Field(None, ge=0)
    sugar_g: float | None = Field(None, ge=0)
    fibre_g: float | None = Field(None, ge=0)
    sodium_mg: float | None = Field(None, ge=0)
    # the Bronze row written when the photo was analysed (raw photo checksum and the model's raw answer)
    analysis_id: str | None = None
    # true when the person changed the numbers by hand
    edited: bool = False
    # which numbers were saved: the photo model's estimate, or the person's own edits
    values_from: Literal["ai", "user"] = "ai"


class WorkoutInput(Camel):
    kind: Literal["workout"] = "workout"
    type: ExerciseKind
    activity: str = Field(default="", max_length=120)
    intensity: int = Field(ge=1, le=5)
    start_at: datetime
    minutes: int = Field(ge=1, le=600)
    feeling: int | None = Field(None, ge=1, le=5)


class SymptomInput(Camel):
    kind: Literal["symptom"] = "symptom"
    label: str
    severity: int = Field(ge=1, le=5)
    occurred_at: datetime
    # how long the person felt it, in minutes; null when "still going" or unknown
    duration_min: int | None = Field(None, ge=1, le=1440)
    side: str | None = None
    relation: str | None = None
    feel: str | None = None
    note: str | None = None


class CheckinInput(Camel):
    kind: Literal["checkin"] = "checkin"
    mood: int = Field(ge=1, le=5)
    stress: int = Field(ge=1, le=5)
    sleep: int = Field(ge=1, le=5)
    energy: int = Field(ge=1, le=5)


LogInput = Annotated[Union[MealInput, WorkoutInput, SymptomInput, CheckinInput], Field(discriminator="kind")]


# ── Results ──────────────────────────────────────────────────────────────────

class LogFlag(Camel):
    text: str
    level: Literal["info", "in_range", "high"] = "info"


class LogSwap(Camel):
    text: str
    source: str


class LogResult(Camel):
    id: str
    kind: LogKind
    title: str
    landed_in: str
    detail: str
    lines: list[str] = Field(default_factory=list)
    related: str
    day: str
    flag: LogFlag | None = None
    swap: LogSwap | None = None
    urgent: bool = False
    urgent_tier: int | None = None


class RecentEntry(Camel):
    id: str
    kind: LogKind
    title: str
    detail: str
    when: str
    date: str


# ── Meal analysis ────────────────────────────────────────────────────────────

class Macros(Camel):
    kcal: float | None = None
    carbs_g: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    fibre_g: float | None = None
    sugar_g: float | None = None
    sodium_mg: float | None = None


class MealAnalysis(Camel):
    analysis_id: str
    name: str
    items: list[str]
    macros: Macros
    confidence: Literal["high", "check"]
    flags: list[Literal["high_salt", "high_sugar"]]
    portion_note: str
    model_id: str


class FoodNote(Camel):
    kind: Literal["higher", "lower", "similar", "learning"]
    text: str
    n: int
    range: tuple[float, float] | None = None


# ── Progress, context and notifications ──────────────────────────────────────

class ProgressItem(Camel):
    key: Literal["meals", "checkin", "workout", "symptom"]
    label: str
    hint: str
    done: bool
    # done, due (inside its time window right now and not logged yet) or later
    status: Literal["done", "due", "later"]
    count: int
    target: int | None
    to: str
    # when this log is worth doing ("7 to 10:30 am") and, only while it is due, a short sentence to ask for it
    window: str | None = None
    prompt: str | None = None


class LogProgress(Camel):
    date: str
    items: list[ProgressItem]
    done: int
    total: int
    streak_days: int
    week_activity_min: int
    week_activity_goal: int
    week_strength_sessions: int
    week_strength_goal: int
    next_up: ProgressItem | None


class GlucoseContext(Camel):
    v: float
    trend: Literal["rising", "steady", "falling"]
    at: str


class LogContext(Camel):
    glucose: GlucoseContext | None


# every value of the database enum `notification_kind`: other parts of the app (refills, doses, clashes) write reminders too
NotificationKind = Literal["dose_reminder", "dose_renudge", "miss_reason", "checkin", "nudge", "refill", "appointment", "urgent", "clash", "brief_ready"]


class Notification(Camel):
    id: str
    kind: NotificationKind
    title: str
    body: str
    when: str
    to: str | None = None
    unread: bool
