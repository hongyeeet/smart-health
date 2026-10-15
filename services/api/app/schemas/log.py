"""Pydantic v2 schemas for the logs API (rules.md 4: no raw dicts across layers).

They mirror apps/web/src/data/types.ts. The web app sends and receives camelCase; Python uses snake_case.

There is no glucose log: every user wears a CGM patch, so glucose arrives from the sensor, never by hand.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated, Literal, Union
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

SG = ZoneInfo("Asia/Singapore")
# a device clock can be a few seconds ahead of the server; a reading a minute ahead is still accepted
BP_CLOCK_GRACE = timedelta(minutes=1)


class Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class LogKind(str, Enum):
    meal = "meal"
    workout = "workout"
    symptom = "symptom"
    checkin = "checkin"
    blood_pressure = "blood_pressure"


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
    # null when the person did not rate how hard it felt
    intensity: int | None = Field(None, ge=1, le=5)
    start_at: datetime
    minutes: int = Field(ge=1, le=600)
    # how the person felt afterwards: null when not answered
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
    # each answer is null when the person did not answer that question; at least one must be answered (wellbeing_logs CHECK)
    mood: int | None = Field(None, ge=1, le=5)
    stress: int | None = Field(None, ge=1, le=5)
    sleep: int | None = Field(None, ge=1, le=5)
    energy: int | None = Field(None, ge=1, le=5)

    @model_validator(mode="after")
    def _one_answer(self) -> "CheckinInput":
        if self.mood is None and self.stress is None and self.sleep is None and self.energy is None:
            raise ValueError("Answer at least one question to save.")
        return self


class BloodPressureInput(Camel):
    """One manual reading: the top number (systolic), the bottom number (diastolic), optional pulse, and the time taken."""
    kind: Literal["blood_pressure"] = "blood_pressure"
    systolic: int = Field(ge=60, le=260)
    diastolic: int = Field(ge=30, le=150)
    pulse: int | None = Field(None, ge=30, le=220)
    # left out means "now" (the server fills it in)
    measured_at: datetime | None = None
    note: str | None = Field(None, max_length=300)

    @model_validator(mode="after")
    def _check_pair_and_time(self) -> "BloodPressureInput":
        if self.diastolic >= self.systolic:
            raise ValueError("The bottom number must be lower than the top number.")
        if self.measured_at is not None:
            taken = self.measured_at if self.measured_at.tzinfo else self.measured_at.replace(tzinfo=SG)
            if taken > datetime.now(timezone.utc) + BP_CLOCK_GRACE:
                raise ValueError("The time taken cannot be in the future.")
        return self


LogInput = Annotated[Union[MealInput, WorkoutInput, SymptomInput, CheckinInput, BloodPressureInput], Field(discriminator="kind")]


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


class MealSensor(Camel):
    """How glucose moved after one meal, from the sensor (meal_response). Unknown values are null."""
    pre_mmol: float | None
    peak_mmol: float | None
    minutes_to_peak: int | None
    rise_mmol: float | None


class RecentMeal(Camel):
    """A meal in the recent list, with its macros (null when unknown) and its sensor response (null when there is no sensor data).
    `numbers_from` is "you" when the person typed or changed the numbers, "estimate" when the photo reading gave them."""
    id: str
    numbers_from: Literal["you", "estimate"] = "estimate"
    when: str
    name: str | None
    meal_type: str | None
    kcal: int | None
    carbs_g: float | None
    protein_g: float | None
    fat_g: float | None
    sugar_g: float | None
    fibre_g: float | None
    sodium_mg: float | None
    flags: list[Literal["salt", "sugar"]]
    response: MealSensor | None


class RecentEntry(Camel):
    id: str
    kind: LogKind
    title: str
    detail: str
    when: str
    date: str
    meal: RecentMeal | None = None   # set for a meal only; the other fields are unchanged for every caller


class WorkoutEntry(Camel):
    """A saved workout, as the edit form needs it."""
    id: str
    type: ExerciseKind
    activity: str = ""
    intensity: int | None = None
    start_at: str
    minutes: int
    feeling: int | None = None


class BloodPressureEntry(Camel):
    """A saved reading. `id` is the entry's id for edit and delete."""
    id: str
    measured_at: str
    systolic: int
    diastolic: int
    pulse: int | None = None
    note: str | None = None


class BloodPressureToday(Camel):
    count: int = 0
    # plain words, for example "128 over 82 at 8:10 am"; None when nothing is logged today
    latest: str | None = None
    readings: list[BloodPressureEntry] = Field(default_factory=list)


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
    # blood pressure is not one of the three core items: it is listed on its own, so Home is unchanged
    blood_pressure: BloodPressureToday = Field(default_factory=BloodPressureToday)


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
    date: str | None = None            # only on the Reminders page list: the Singapore day the reminder belongs to, YYYY-MM-DD
    current: bool | None = None        # only on that list: still waiting and inside its time window (not yet done or past)
    pinned: int | None = None          # only on that list: the place (0, 1, 2) of a first "get started" notice, which is shown on top until done
