"""API shape of the heart rate, SpO2 and blood pressure blocks shown on Insights C4 (Activity) and C5 (Sleep and stress).

Computed in `app/services/insights_heart.py`. Nothing here says a value is normal, high or low; a missing day is null, never zero.
"""
from __future__ import annotations

from app.schemas.insights import Period
from app.schemas.medicines import Camel


class HeartDay(Camel):
    date: str
    avg: float | None           # the day's average of the watch heart-rate readings
    resting: float | None       # daily_summary resting heart rate for the day
    asleep: float | None        # average while asleep, filed under the morning the night ends on


class HeartRate(Camel):
    avg: float | None           # average of every reading in the period
    high: int | None            # highest single reading in the period
    low: int | None             # lowest single reading in the period
    resting_avg: float | None   # average of the daily resting values that exist
    asleep_avg: float | None    # average while asleep


class Spo2(Camel):
    avg: float | None           # average of every SpO2 reading in the period
    low: float | None           # lowest single SpO2 reading in the period
    asleep_avg: float | None    # average while asleep
    asleep_low: float | None    # lowest while asleep


class HeartInsights(Camel):
    period: Period              # ends on the person's last day of watch data (today when there is none)
    watch_end: str | None       # that last watch day, ISO; None when there is no watch data at all
    end_note: bool              # True when the period ends before today or before the other tabs' end: say so on screen
    has_data: bool
    days_with_data: int
    heart_rate: HeartRate
    spo2: Spo2
    days: list[HeartDay]


class BloodPressureReading(Camel):
    date: str                   # local date
    time: str                   # local time, "08:30"
    systolic: int               # top number
    diastolic: int              # bottom number
    pulse: int | None


class BloodPressureInsights(Camel):
    count: int                  # every reading in the period, not only the rows shown
    latest: str | None          # local date of the newest reading, ISO; None when there is none
    readings: list[BloodPressureReading]
