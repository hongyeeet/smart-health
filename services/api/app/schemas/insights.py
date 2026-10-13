"""API shape of the Insights tab (screens C1 to C6 and C8). camelCase on the wire, like the other routers.

Every value is computed in `app/services/insights.py` from stored data; the screen only lays it out. Nothing here is a verdict:
a comparison is "associated with", never "caused by", and a number with too little behind it says so.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field

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
    """One measure against the same number of days before. `direction` is "none" when either period has no value."""
    id: str
    to: Literal["C2", "C3", "C4", "C5", "C6"]
    unit: Literal["points", "mmol", "steps", "minutes", "hours", "score"]
    direction: Literal["up", "down", "same", "none"]
    current: float | None
    previous: float | None
    delta: float | None


class GridCell(Camel):
    date: str
    value: float | None
    label: str
    level: int                      # 0 no data, 1 to 4 how much (a shade, not a verdict)


class GridRow(Camel):
    key: Literal["glucose", "meals", "activity", "sleep", "stress", "doses"]
    cells: list[GridCell]


class Overview(Camel):
    period: Period
    changes: list[Change]
    patterns: list[Pattern]


class OverviewDays(Camel):
    """The overview calendar: one cell per day in [start, end]. Days after `today` are never included."""
    start: str
    end: str
    today: str
    rows: list[GridRow]


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
class ActivityBar(Camel):
    """One bar of the minutes-by-effort chart: a day (7 days), a calendar week (30 days) or a calendar month (90 days)."""
    label: str
    first_day: str
    last_day: str     # the last day with data in the bar (the end of the period for the newest, still running, bar)
    partial: bool     # the newest week or month is not over yet
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
    intensity: int | None  # None means not rated; never counted as moderate
    minutes: int
    glucose_change_2h: float | None


class StepDay(Camel):
    date: str
    steps: int | None


class ActivityInsights(Camel):
    period: Period
    bar_unit: str     # 'day', 'week' or 'month'
    bars: list[ActivityBar]
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
    short_nights: int            # nights under 6 hours in the period
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
    counted: bool                   # prescription medicines count towards adherence; the others are listed only, with no numbers
    taken: int | None               # null when not counted
    missed: int | None
    unconfirmed: int | None
    scheduled: int | None
    adherence_pct: int | None       # null until a dose is answered (taken or missed), and for medicines not counted
    cells: list[DoseCell]


class Reason(Camel):
    key: str
    label: str
    count: int


class MedicationInsights(Camel):
    period: Period
    dates: list[str]
    meds: list[MedRow]
    taken: int
    missed: int
    scheduled: int
    unconfirmed: int                # doses whose window passed and nobody answered (counted as not taken)
    adherence_pct: int | None       # null when no prescription dose has been answered yet
    reasons: list[Reason]
    patterns: list[Pattern]
    shown_days: int
    month: str | None = None          # "YYYY-MM" when a month was asked for
    prev_month: str | None = None     # null at the first month with a dose record
    next_month: str | None = None     # null at the month of the latest day with data


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


# ── Overview timeline (GET /insights/timeline) ──────────────────────────────
class TLPeriod(Period):
    bucket_minutes: int
    buckets: int
    latest: str                  # the last day with data: the period can move back from here, never past it
    earliest: str | None         # the first day with data


class TLSeries(Camel):
    """One value per bucket (null where there is no reading), all on the same time axis."""
    glucose: list[float | None]
    glucose_min: list[float | None]
    glucose_max: list[float | None]
    heart: list[float | None]
    heart_min: list[float | None]
    heart_max: list[float | None]
    spo2: list[float | None]
    spo2_min: list[float | None]
    spo2_max: list[float | None]
    steps: list[int | None]


class TLHourly(Camel):
    """Per hour of the day (24 numbers): the person's average and the middle half (25th to 75th percentile)."""
    mean: list[float | None]
    lo: list[float | None]
    hi: list[float | None]


class TLDailyUsual(Camel):
    """One number each: the person's mean daily average, and the middle half of their daily averages (for the one-point-a-day views)."""
    mean: float | None
    lo: float | None
    hi: float | None


class TLDailyUsualSet(Camel):
    glucose: TLDailyUsual
    heart: TLDailyUsual
    spo2: TLDailyUsual


class TLBaseline(Camel):
    days: int
    source: Literal["before", "start", "period"]
    from_: str = Field(alias="from")
    to: str
    available: bool
    bp_available: bool
    bp_systolic: float | None
    bp_diastolic: float | None
    bp_readings: int
    daily: TLDailyUsualSet
    glucose: TLHourly
    heart: TLHourly
    spo2: TLHourly


class TLBp(Camel):
    m: int
    systolic: int
    diastolic: int


class TLMeal(Camel):
    m: int
    type: str
    food: str


class TLSpan(Camel):
    m0: int
    m1: int
    type: str


class TLSymptom(Camel):
    m: int
    type: str


class TLAt(Camel):
    m: int


class TLMood(Camel):
    m: int
    mood: int
    stress: int | None


class TLEvents(Camel):
    meals: list[TLMeal]
    exercise: list[TLSpan]
    symptoms: list[TLSymptom]
    missed: list[TLAt]
    mood: list[TLMood]


class TLWork(Camel):
    days: list[int]
    start: str | None
    end: str | None
    set: bool


class TLValues(Camel):
    avg_glucose: float | None
    gmi: float | None
    cv: int | None
    steps_per_day: int | None
    doses_taken_pct: int | None
    sensor_worn_pct: int | None


class TLMinMax(Camel):
    avg: float | None
    min: float | None
    max: float | None


class TLDay(Camel):
    """One local day: the stats bar and the one-point-a-day charts read this."""
    date: str
    glucose: TLMinMax
    heart: TLMinMax
    spo2: TLMinMax
    systolic: float | None
    diastolic: float | None
    steps: int | None
    kcal: int | None
    sugar_g: float | None
    sodium_mg: float | None
    meals: int
    missed: int
    symptoms: int


class TLMetric(Camel):
    """The period set against the baseline: its average, the average of its most recent days, and the drift per week (a number, never a verdict)."""
    baseline: float | None
    period: float | None
    recent: float | None
    slope_per_week: float | None


class TLCompare(Camel):
    recent_days: int
    glucose: TLMetric
    heart: TLMetric
    spo2: TLMetric
    bp: TLMetric


class Timeline(Camel):
    period: TLPeriod
    series: TLSeries
    baseline: TLBaseline
    bp: list[TLBp]
    events: TLEvents
    work: TLWork
    values: TLValues
    day_rows: list[TLDay]
    compare: TLCompare
