"""API shape of the doctor report (prd F12). camelCase on the wire, like the other routers. Every value is computed in
`app/services/doctor_report.py`; the key findings may be worded by an AI (`app/agents/report_insight.py`), which `keyFindingsSource`
says. The screen only lays it out."""
from __future__ import annotations

from typing import Literal

from app.schemas.medicines import Camel


class Period(Camel):
    start: str
    end: str
    days: int
    label: str


class Patient(Camel):
    name: str
    sex_age: str
    diagnosis: str


class SummaryRow(Camel):
    label: str
    value: str                     # only rows with an answer are sent


class ReportAlert(Camel):
    priority: Literal["urgent", "interaction", "review"]
    title: str
    detail: str


class GlucoseBand(Camel):
    key: Literal["very_high", "high", "in_range", "low", "very_low"]
    label: str
    pct: float
    per_day: str
    reference: str
    outside: bool                  # outside the printed reference value (clinical validation pending)


class Metric(Camel):
    label: str
    value: str
    reference: str
    outside: bool


class ProfilePoint(Camel):
    hour: int
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float


class Glucose(Camel):
    has_data: bool
    sufficient: bool               # false when the sensor was active for too little of the period
    bands: list[GlucoseBand] = []
    metrics: list[Metric] = []
    profile: list[ProfilePoint] = []
    low: float | None = None
    high: float | None = None
    very_low: float | None = None
    very_high: float | None = None


class BaselineRow(Camel):
    metric: str
    baseline: str
    period: str
    comparison: str                # "higher than", "lower than", "about the same as" or "—"


class Baseline(Camel):
    available: bool                # false: the note says why (fewer than 14 days, or no sensor data)
    note: str | None = None
    period_label: str | None = None
    baseline_label: str | None = None
    rows: list[BaselineRow] = []


class SymptomRow(Camel):
    symptom: str
    logged: int
    low: int
    high: int
    in_range: int
    no_reading: int
    note: str


class LatestValue(Camel):
    label: str
    value: str
    on: str                        # the day it was recorded, or empty when there is no date


class SymptomLine(Camel):
    symptom: str
    logged: int
    text: str                      # the fixed template sentence


class SymptomLatest(Camel):
    latest: list[LatestValue] = []
    rows: list[SymptomLine] = []
    note: str


class Episode(Camel):
    when: str
    symptom: str
    severity: int | None = None
    glucose: float | None = None
    zone: Literal["very_low", "low", "in_range", "high"] | None = None
    change_30: float | None = None
    last_dose: str | None = None
    heart_rate: int | None = None
    spo2: int | None = None
    note: str | None = None


class MedicineRow(Camel):
    name: str
    regimen: str
    scheduled: int | None = None
    taken: int | None = None
    missed: int | None = None
    not_logged: int | None = None
    adherence_pct: int | None = None
    interaction: bool = False


class ActivityCell(Camel):
    label: str
    value: str
    sub: str


class BpReading(Camel):
    when: str                      # day and time, local
    systolic: int
    diastolic: int
    pulse: int | None = None


class BloodPressure(Camel):
    count: int                     # readings in the period; 0 means none were logged
    systolic_range: str | None = None
    diastolic_range: str | None = None
    pulse_range: str | None = None
    readings: list[BpReading] = []
    readings_total: int = 0


class WorthItem(Camel):
    text: str                      # one plain observation, never advice
    evidence: str                  # what it is based on
    kind: Literal["clash", "adherence", "pattern", "fact"]


class DoctorReport(Camel):
    generated_on: str
    simulated: bool = False         # true only for the demo dataset; the report then says its data is simulated
    period: Period
    patient: Patient
    summary: list[SummaryRow] = []
    cgm_wear: str
    sources: str
    key_findings: list[str]
    key_findings_source: Literal["ai", "rules"] = "rules"
    alerts: list[ReportAlert]
    glucose: Glucose
    baseline: Baseline
    symptoms: list[SymptomRow]
    symptom_latest: SymptomLatest
    episodes: list[Episode]
    episodes_total: int
    medicines: list[MedicineRow]
    medicines_note: str | None = None
    activity: list[ActivityCell]
    blood_pressure: BloodPressure
    worth_discussing: list[WorthItem] = []
    questions: list[str]
