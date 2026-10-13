"""API shape of GET /home/overview (the new Home page): today's plan, four KPI cards and a 7-day chart.

camelCase on the wire, like the other schemas. Mirrors `HomeOverview` in apps/web/src/data/types.ts. Computed in
`app/services/home_overview.py`. Nothing here says a value is good or bad: a status only compares the person with THEIR OWN usual
range, and a value that is not known is null (never 0).
"""
from __future__ import annotations

from typing import Literal

from app.schemas.medicines import Camel

RangeState = Literal["within", "above", "below", "unknown"]


class KpiStatus(Camel):
    state: RangeState
    usual_low: float | None         # 25th percentile of the person's own daily values over the 60 days before the 7-day window
    usual_high: float | None        # 75th percentile of the same
    usual_median: float | None
    delta: float | None             # the 7-day value minus usual_median, same unit as the value (null when the state is unknown)


class PlanItem(Camel):
    kind: Literal["meal", "dose"]
    title: str                      # "Breakfast" or "Metformin 500 mg": the person's own label
    status: Literal["done", "due", "later", "missed"]
    dose_id: str | None             # a dose: the waiting dose row (what Taken sends); null when there is none (or it is answered)
    meal_type: Literal["breakfast", "lunch", "dinner"] | None


class PlanStep(Camel):
    time: str                       # "08:00", local Singapore time
    label: str                      # "8:00 am"
    state: Literal["done", "now", "later", "missed"]
    items: list[PlanItem]           # meals first, then medicines


class HomePlan(Camel):
    date: str
    done: int
    total: int
    now_index: int | None
    steps: list[PlanStep]


class Nutrient(Camel):
    state: Literal["ok", "high", "unknown"]
    high_meals: int | None          # meals over the limit in the last 7 days (null when no meal has this value)
    meals: int                      # meals logged in those 7 days


class GlucoseKpi(Camel):
    value: float | None
    unit: Literal["mmol/L"] = "mmol/L"
    day: str | None
    in_range_pct: float | None
    spark: list[float | None]
    status: KpiStatus


class StepsKpi(Camel):
    avg: float | None
    spark: list[float | None]
    status: KpiStatus


class CaloriesKpi(Camel):
    avg_kcal: float | None
    sugar: Nutrient
    salt: Nutrient
    spark: list[float | None]
    status: KpiStatus


class HeartKpi(Camel):
    bpm: float | None
    resting_bpm: float | None
    spo2: float | None
    status: KpiStatus
    spo2_status: KpiStatus


class HomeChart(Camel):
    days: list[str]
    glucose: list[float | None]
    steps: list[float | None]
    calories: list[float | None]
    heart_rate: list[float | None]


class HomeOverview(Camel):
    as_of: str | None
    plan: HomePlan
    glucose: GlucoseKpi | None
    steps: StepsKpi | None
    calories: CaloriesKpi | None
    heart: HeartKpi | None
    chart: HomeChart
