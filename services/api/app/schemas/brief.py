"""API shape of the doctor report (prd F12). camelCase on the wire, like the other routers. Every value is computed in
`app/services/doctor_report.py`; the screen only lays it out."""
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


class SymptomRow(Camel):
    symptom: str
    logged: int
    low: int
    high: int
    in_range: int
    no_reading: int
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


class DoctorReport(Camel):
    generated_on: str
    period: Period
    patient: Patient
    cgm_wear: str
    sources: str
    key_findings: list[str]
    alerts: list[ReportAlert]
    glucose: Glucose
    symptoms: list[SymptomRow]
    episodes: list[Episode]
    episodes_total: int
    medicines: list[MedicineRow]
    medicines_note: str | None = None
    activity: list[ActivityCell]
    questions: list[str]
