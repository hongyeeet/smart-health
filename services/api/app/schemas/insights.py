"""API shape of the Insights tab (screens C1 to C6 and C8). camelCase on the wire, like the other routers.

Every value is computed in `app/services/insights.py` from stored data; the screen only lays it out. Nothing here is a verdict:
a comparison is "associated with", never "caused by", and a number with too little behind it says so.
"""
from __future__ import annotations

from typing import Literal

from app.schemas.medicines import Camel


class Period(Camel):
    start: str
    end: str
    days: int
    label: str
    has_data: bool


class Pattern(Camel):
    """One finding the nightly job found in the person's own history (table pattern_candidates). Associated with, not proven."""
    key: str
    text: str
    n: int
    to: Literal["C2", "C3", "C4", "C5", "C6"]


class Change(Camel):
    id: str
    text: str
    to: Literal["C2", "C3", "C4", "C5", "C6"]


class GridCell(Camel):
    date: str
    weekday: str
    value: float | None
    label: str
    level: int                      # 0 no data, 1 to 4 how much (a shade, not a verdict)


class GridRow(Camel):
    key: Literal["glucose", "meals", "activity", "sleep", "stress", "doses"]
    label: str
    cells: list[GridCell]


class Overview(Camel):
    period: Period
    grid: list[GridRow]
    changes: list[Change]
    patterns: list[Pattern]


# ── Glucose ────────────────────────────────────────────────────────────────
class Band(Camel):
    key: Literal["very_high", "high", "in_range", "low", "very_low"]
    label: str
    pct: float


class GlucoseDay(Camel):
    date: str
    mean: float | None
    tir: float | None
    fasting: float | None


class Baseline(Camel):
    p25: float
    p50: float
    p75: float
    n: int


class Drift(Camel):
    weeks: int
    text: str


class GlucoseMetrics(Camel):
    mean: float | None
    gmi: float | None
    cv: float | None
    coverage: float | None          # percent of the period the sensor was worn
    readings: int


class GlucoseEvents(Camel):
    spikes: int
    lows: int
    sustained_high: int


class GlucoseInsights(Camel):
    period: Period
    has_data: bool
    bands: list[Band]
    days: list[GlucoseDay]
    baseline: Baseline | None
    drift: Drift | None
    metrics: GlucoseMetrics
    events: GlucoseEvents
    low: float
    high: float
    patterns: list[Pattern]


# ── Food ───────────────────────────────────────────────────────────────────
class MealRow(Camel):
    id: str
    when: str
    name: str
    meal_type: str
    kcal: int | None
    carbs_g: float | None
    sugar_g: float | None
    sodium_mg: float | None
    flags: list[Literal["high_salt", "high_sugar"]]
    rise: float | None


class FoodResponse(Camel):
    name: str
    n: int
    median_rise: float
    low: float
    high: float


class FoodTotals(Camel):
    meals: int
    avg_kcal_per_day: int | None
    avg_sodium_per_day: int | None
    high_salt_meals: int
    high_sugar_meals: int


class FoodInsights(Camel):
    period: Period
    totals: FoodTotals
    meals: list[MealRow]
    responses: list[FoodResponse]   # gentlest to spikiest, only foods seen at least twice
    still_learning: list[str]       # foods seen once: not ranked yet
    patterns: list[Pattern]


# ── Activity ───────────────────────────────────────────────────────────────
class WeekBar(Camel):
    label: str
    light: int
    moderate: int
    vigorous: int


class MixItem(Camel):
    type: str
    label: str
    count: int
    minutes: int


class WorkoutRow(Camel):
    id: str
    date: str
    label: str
    type: str
    intensity: int
    minutes: int
    glucose_change_2h: float | None


class StepDay(Camel):
    date: str
    steps: int | None


class ActivityInsights(Camel):
    period: Period
    moderate_min: int
    moderate_goal: int
    strength: int
    strength_goal: int
    weeks: list[WeekBar]
    mix: list[MixItem]
    workouts: list[WorkoutRow]
    steps: list[StepDay]
    steps_avg: int | None
    steps_baseline: int | None
    patterns: list[Pattern]


# ── Sleep and stress ───────────────────────────────────────────────────────
class SleepDay(Camel):
    date: str
    hours: float | None
    mood: float | None
    stress: float | None
    energy: float | None


class SleepInsights(Camel):
    period: Period
    days: list[SleepDay]
    sleep_avg: float | None
    sleep_baseline: float | None
    short_nights: int
    stress_avg: float | None
    mood_avg: float | None
    high_stress_days: int
    logged_days: int
    patterns: list[Pattern]


# ── Medication ─────────────────────────────────────────────────────────────
DoseCell = Literal["taken", "late", "unconfirmed", "missed", "none"]


class MedRow(Camel):
    id: str
    name: str
    regimen: str
    taken: int
    scheduled: int
    adherence_pct: int | None
    cells: list[DoseCell]


class Reason(Camel):
    key: str
    label: str
    count: int


class MedicationInsights(Camel):
    period: Period
    dates: list[str]
    meds: list[MedRow]
    fasting: list[float | None]     # the same dates, so the line can sit over the grid
    taken: int
    scheduled: int
    unconfirmed: int                # doses whose window passed and nobody answered (counted as not taken)
    adherence_pct: int | None
    reasons: list[Reason]
    patterns: list[Pattern]
    shown_days: int


# ── Glucose sensor sprint (C8) ─────────────────────────────────────────────
class SprintFood(Camel):
    name: str
    median_rise: float
    n: int


class SensorRun(Camel):
    period: Period
    status: Literal["complete", "partial", "none"]
    days_worn: int
    of: int
    metrics: GlucoseMetrics
    bands: list[Band]
    gentlest: list[SprintFood]
    spikiest: list[SprintFood]
