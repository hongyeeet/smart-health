"""Workout effort from heart rate, and training volume from sets.

Deterministic, no LLM, no database (rules.md 1 and 4): this module only does arithmetic on numbers it is
given. The caller reads heart-rate samples from `health_samples`, the resting heart rate from
`daily_aggregates.resting_hr` (Gold, once it exists) and the sets from the workout, then writes the result
back. The model may later turn the finished numbers into a plain-language sentence; it never computes them.

Every cut-off below is a placeholder pending clinical validation (questions-for-damien.md, G1).
Heart rate is not a reliable effort signal for people on beta-blockers: pass `beta_blocker=True` and no
intensity is reported.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, Optional, Sequence

# clinical validation pending: percent of maximum heart rate. Placeholders, never shown as advice.
BAND_EDGES = (("rest_or_very_light", 0.0), ("light", 57.0), ("moderate", 64.0), ("vigorous", 77.0), ("near_maximal", 96.0))
MIN_COVERAGE = 0.70  # share of the expected samples that must exist, otherwise "insufficient" (schema consistency rule 12)
EXPECTED_INTERVAL_S = 60  # heart rate is downsampled to 1 minute on import (schema consistency rule 11)


def max_heart_rate(age: float) -> float:
    """Tanaka estimate: 208 - 0.7 x age. An estimate, not a measurement."""
    return 208.0 - 0.7 * age


def percent_of_max(bpm: float, age: float) -> float:
    return 100.0 * bpm / max_heart_rate(age)


def band_for_percent(pct: float) -> str:
    name = BAND_EDGES[0][0]
    for label, edge in BAND_EDGES:
        if pct >= edge:
            name = label
    return name


def intensity_for_band(band: str) -> str:
    """Map a band onto the app's three intensities (light, moderate, vigorous)."""
    if band in ("rest_or_very_light", "light"):
        return "light"
    if band == "moderate":
        return "moderate"
    return "vigorous"


@dataclass(frozen=True)
class Sample:
    at: datetime
    bpm: float


@dataclass
class Effort:
    avg_hr: Optional[float]
    max_hr: Optional[float]
    intensity: Optional[str]
    minutes_in_band: dict[str, float] = field(default_factory=dict)
    quality: str = "insufficient"  # 'ok' or 'insufficient'
    note: Optional[str] = None


def _in_window(samples: Iterable[Sample], start: datetime, end: datetime) -> list[Sample]:
    return [s for s in samples if start <= s.at <= end]


def effort_between(
    samples: Sequence[Sample],
    start: datetime,
    end: datetime,
    age: float,
    *,
    beta_blocker: bool = False,
) -> Effort:
    """Average and peak heart rate, minutes in each band, and an intensity label for one window.

    Returns `quality='insufficient'` and no intensity when there are too few samples. Unknown stays unknown.
    """
    if end <= start:
        return Effort(None, None, None, quality="insufficient", note="The window has no length.")
    window = _in_window(samples, start, end)
    expected = max((end - start).total_seconds() / EXPECTED_INTERVAL_S, 1.0)
    if not window:
        return Effort(None, None, None, quality="insufficient", note="No heart rate data for this time.")
    coverage = len(window) / expected
    avg = sum(s.bpm for s in window) / len(window)
    peak = max(s.bpm for s in window)
    minutes: dict[str, float] = {}
    for s in window:
        band = band_for_percent(percent_of_max(s.bpm, age))
        minutes[band] = minutes.get(band, 0.0) + EXPECTED_INTERVAL_S / 60.0
    if coverage < MIN_COVERAGE:
        return Effort(round(avg, 1), peak, None, minutes, "insufficient", "Heart rate was missing for too much of this time to judge effort.")
    if beta_blocker:
        return Effort(round(avg, 1), peak, None, minutes, "insufficient", "Heart rate is not a reliable effort signal on this medicine.")
    dominant_pct = percent_of_max(avg, age)
    return Effort(round(avg, 1), peak, intensity_for_band(band_for_percent(dominant_pct)), minutes, "ok")


@dataclass(frozen=True)
class SetEntry:
    reps: int
    weight_kg: Optional[float]  # None means bodyweight
    performed_at: Optional[datetime] = None


@dataclass
class ExerciseEntry:
    name: str
    sets: list[SetEntry]


def exercise_volume_kg(sets: Sequence[SetEntry]) -> float:
    """Reps x weight, summed. Bodyweight sets count as zero volume (they are listed, not weighed)."""
    return round(sum(s.reps * s.weight_kg for s in sets if s.weight_kg), 1)


def session_volume_kg(exercises: Sequence[ExerciseEntry]) -> float:
    return round(sum(exercise_volume_kg(e.sets) for e in exercises), 1)


def exercise_window(sets: Sequence[SetEntry], lead: timedelta = timedelta(seconds=45), tail: timedelta = timedelta(seconds=45)) -> Optional[tuple[datetime, datetime]]:
    """Time span of an exercise from its logged sets, padded a little either side. None if no set has a time."""
    times = [s.performed_at for s in sets if s.performed_at]
    if not times:
        return None
    return min(times) - lead, max(times) + tail


def exercise_efforts(
    exercises: Sequence[ExerciseEntry],
    samples: Sequence[Sample],
    age: float,
    *,
    beta_blocker: bool = False,
) -> dict[str, Effort]:
    """Average heart rate per exercise, from the time its sets were done."""
    out: dict[str, Effort] = {}
    for e in exercises:
        window = exercise_window(e.sets)
        out[e.name] = (
            effort_between(samples, window[0], window[1], age, beta_blocker=beta_blocker)
            if window
            else Effort(None, None, None, quality="insufficient", note="Set times were not logged.")
        )
    return out
