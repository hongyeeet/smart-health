"""API shape of the Day view (screens D1 and D2). camelCase on the wire, like the other routers.

Every value is read from stored data by `app/services/day.py`; the screen only draws it. Times are given as minutes after local
midnight (Asia/Singapore) so the chart can place them without a time zone library, plus a clock string for the words on screen.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.medicines import Camel

MarkerKind = Literal["meal", "dose", "workout", "symptom", "pressure"]
DoseState = Literal["taken", "late", "not_confirmed", "missed"]


class DayDates(Camel):
    latest_date: str                  # the day the app opens on (the same rule as Insights: the latest day with data)
    dates: list[str]                  # days that have any data, newest first


class Point(Camel):
    """One 5-minute slot. A null value is a gap: the sensor or watch gave nothing, and the chart must not join across it."""
    minute: int
    glucose_mmol: float | None
    heart_rate_bpm: int | None
    steps: int | None


class SleepBand(Camel):
    start_minute: int
    end_minute: int


class MarkerRow(Camel):
    label: str
    value: str


class Marker(Camel):
    id: str
    kind: MarkerKind
    minute: int
    end_minute: int | None = None     # workouts only, when the end was logged
    clock: str                        # "08:00", the person's local time
    title: str
    subtitle: str | None = None
    status: DoseState | None = None   # doses only: the worst state in the group
    flags: list[Literal["salt", "sugar"]] = Field(default_factory=list)
    rows: list[MarkerRow] = Field(default_factory=list)
    outcome: str                      # one plain sentence computed from the data


class MoodDot(Camel):
    id: str
    minute: int
    clock: str
    mood: int | None
    stress_self: int | None
    energy: int | None


class DayView(Camel):
    day: str = Field(alias="date")
    label: str
    has_data: bool
    prev_date: str | None
    next_date: str | None
    target_low: float
    target_high: float
    sleep_hours: float | None         # the night's total from the daily summary, shown as words
    series: list[Point]
    sleep: list[SleepBand]
    markers: list[Marker]
    mood: list[MoodDot]
