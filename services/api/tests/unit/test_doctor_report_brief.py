"""The doctor brief changes (owner decisions 2026-10-11): onboarding summary, blood pressure, the 14-day baseline, the symptom block
and the removed sections. Made-up data with known answers; no database (`build()` is pure)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.schemas.brief import DoctorReport
from app.services import doctor_report as dr

TZ = ZoneInfo("Asia/Singapore")
START, END = date(2026, 10, 1), date(2026, 10, 2)
NOW = datetime(2026, 10, 3, 9, 0, tzinfo=TZ)
PROFILE = {"display_name": "Mr Tan", "birth_year": 1968, "gender": "male", "has_diabetes": "yes",
           "glucose_target_low": 3.9, "glucose_target_high": 10.0, "weight_kg": 70}
ONBOARDING = {
    "waist": {"cm": 92.0, "measured_on": "2026-09-01"},
    "diagnosed_year": 2018,
    "care_setting": "gp",
    "conditions": [{"name": "High blood pressure", "code": "htn"}],
    "allergies": [{"substance": "Penicillin", "reaction": "rash"}],
    "labs": [{"test": "hba1c", "value": 7.2, "unit": "%", "taken_on": "2026-09-01"},
             {"test": "fasting_glucose", "value": 6.1, "unit": "mmol/L", "taken_on": "2026-08-20"}],
    "devices": [{"kind": "cgm", "label": "FreeStyle Libre 2"}],
}


def at(day: int, hour: int, minute: int = 0, month: int = 10) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=TZ)


def cgm(values: list[float], start: datetime | None = None, step: int = 15) -> list[tuple[datetime, float]]:
    t0 = start or at(1, 0)
    return [(t0 + timedelta(minutes=step * k), v) for k, v in enumerate(values)]


def inputs(**kw: object) -> dr.Inputs:
    base: dict[str, object] = {"now": NOW, "tz": TZ, "start": START, "end": END, "profile": dict(PROFILE)}
    base.update(kw)
    return dr.Inputs(**base)  # type: ignore[arg-type]


# ----------------------------------------------------------------------------------------------- patient summary
def test_the_summary_shows_only_the_onboarding_answers_that_exist() -> None:
    r = dr.build(inputs(onboarding=ONBOARDING))
    rows = {x["label"]: x["value"] for x in r["summary"]}
    assert rows == {
        "Waist": "92 cm, measured 1 Sep 2026",
        "Year diagnosed": "2018 (8 years ago)",
        "Who looks after the diabetes": "Family doctor (GP)",
        "Other conditions": "High blood pressure",
        "Allergies": "Penicillin (rash)",
        "HbA1c": "7.2%, taken 1 Sep 2026",
        "Fasting glucose": "6.1 mmol/L, taken 20 Aug 2026",
        "Devices": "FreeStyle Libre 2",
    }
    assert DoctorReport.model_validate(r).summary[0].label == "Waist"


def test_before_the_migration_the_summary_is_empty_and_no_row_shows_a_dash_or_zero() -> None:
    r = dr.build(inputs(onboarding={"waist": None, "diagnosed_year": None, "care_setting": None, "conditions": [], "allergies": [], "labs": [], "devices": []}))
    assert r["summary"] == []
    partial = dr.build(inputs(onboarding={"diagnosed_year": 2026, "conditions": [], "labs": [], "devices": [], "allergies": [], "waist": None, "care_setting": "none"}))
    assert [x["label"] for x in partial["summary"]] == ["Year diagnosed", "Who looks after the diabetes"]
    assert partial["summary"][0]["value"] == "2026 (this year)"


# ----------------------------------------------------------------------------------------------- blood pressure
def test_blood_pressure_counts_and_ranges_use_only_the_period_and_are_never_labelled() -> None:
    bp = [{"measured_at": at(1, 8, 10), "systolic": 128, "diastolic": 82, "pulse": 72},
          {"measured_at": at(2, 20), "systolic": 136, "diastolic": 88, "pulse": None},
          {"measured_at": at(20, 8, month=9), "systolic": 150, "diastolic": 95, "pulse": 80}]     # before the period: left out
    r = dr.build(inputs(bp=bp))
    b = r["blood_pressure"]
    assert b["count"] == 2 and b["systolic_range"] == "128–136" and b["diastolic_range"] == "82–88" and b["pulse_range"] == "72"
    assert [(x["when"], x["systolic"], x["diastolic"], x["pulse"]) for x in b["readings"]] == [("2 Oct 20:00", 136, 88, None), ("1 Oct 08:10", 128, 82, 72)]
    text = " ".join(x["when"] for x in b["readings"]).lower()
    assert not any(w in text for w in ("high", "low", "normal"))
    out = DoctorReport.model_validate(r).model_dump(by_alias=True)
    assert out["bloodPressure"]["systolicRange"] == "128–136" and out["bloodPressure"]["readingsTotal"] == 2


def test_no_blood_pressure_gives_a_zero_count_with_no_ranges_and_no_readings() -> None:
    b = dr.build(inputs())["blood_pressure"]
    assert b == {"count": 0, "systolic_range": None, "diastolic_range": None, "pulse_range": None, "readings": [], "readings_total": 0}


def test_blood_pressure_is_never_part_of_the_facts_the_model_may_word() -> None:
    bp = [{"measured_at": at(1, 8), "systolic": 128, "diastolic": 82, "pulse": 72}]
    r = dr.build(inputs(bp=bp, cgm=cgm([6.0] * 192)))
    assert r["_facts"] and not any("blood" in f.lower() or "mmHg" in f for f in r["_facts"])


# ----------------------------------------------------------------------------------------------- baseline
def baseline_cgm(value: float, days: int = 14, first: date = date(2026, 9, 1)) -> list[tuple[datetime, float]]:
    t0 = datetime(first.year, first.month, first.day, 0, 0, tzinfo=TZ)
    return cgm([value] * (96 * days), start=t0)


def test_fewer_than_fourteen_days_of_sensor_data_says_so_and_has_no_card() -> None:
    r = dr.build(inputs(cgm=cgm([6.0] * 192), sensor_first=date(2026, 9, 1), sensor_last=date(2026, 9, 10), baseline_cgm=baseline_cgm(6.0, 10)))
    assert r["baseline"]["available"] is False and r["baseline"]["rows"] == []
    assert r["baseline"]["note"] == "Fewer than 14 days of sensor data are on record (10 so far), so the baseline is not shown."
    out = DoctorReport.model_validate(r)
    assert out.baseline.available is False and out.baseline.note.startswith("Fewer than 14 days")


def test_no_sensor_data_at_all_has_no_baseline() -> None:
    r = dr.build(inputs())
    assert r["baseline"]["available"] is False and "No sensor data" in r["baseline"]["note"]


def test_a_full_baseline_compares_the_period_with_the_first_fourteen_days_in_plain_words() -> None:
    # baseline: 7.0 mmol/L all the time (100% in range, wear 100%). Period: half 6.0 and half 11.0 (50% in range, mean 8.5)
    r = dr.build(inputs(cgm=cgm([6.0] * 96 + [11.0] * 96), sensor_first=date(2026, 9, 1), sensor_last=date(2026, 10, 2), baseline_cgm=baseline_cgm(7.0)))
    b = r["baseline"]
    assert b["available"] is True and b["note"] is None
    assert b["baseline_label"] == "1 Sep – 14 Sep 2026 (first 14 days of sensor data)"
    rows = {x["metric"]: x for x in b["rows"]}
    assert rows["Average glucose (mmol/L)"] == {"metric": "Average glucose (mmol/L)", "baseline": "7.0", "period": "8.5", "comparison": "higher than"}
    assert rows["Time in range (%)"]["baseline"] == "100" and rows["Time in range (%)"]["period"] == "50" and rows["Time in range (%)"]["comparison"] == "lower than"
    assert rows["Sensor worn (%)"]["comparison"] == "about the same as"
    assert {x["comparison"] for x in b["rows"]} <= {"higher than", "lower than", "about the same as"}


def test_the_baseline_says_when_it_overlaps_the_period_and_when_the_sensor_was_too_little() -> None:
    sparse = cgm([7.0] * 40, start=datetime(2026, 9, 1, 0, 0, tzinfo=TZ))          # a few readings in the baseline days
    r = dr.build(inputs(cgm=cgm([6.0] * 192), sensor_first=date(2026, 9, 1), sensor_last=date(2026, 10, 2), baseline_cgm=sparse))
    assert r["baseline"]["available"] is True
    assert "may not be representative" in r["baseline"]["note"]
    assert "share" not in r["baseline"]["note"]           # the baseline ends 14 Sep: no shared day with 1 to 2 Oct
    overlap = dr.build(inputs(cgm=cgm([6.0] * 192), sensor_first=date(2026, 9, 25), sensor_last=date(2026, 10, 8),
                              baseline_cgm=cgm([7.0] * 96 * 14, start=datetime(2026, 9, 25, tzinfo=TZ))))
    assert "share 2 days" in overlap["baseline"]["note"]


# ----------------------------------------------------------------------------------------------- symptoms and latest values
def test_the_symptom_block_puts_the_latest_values_beside_each_symptom_in_fixed_words() -> None:
    symptoms = [{"occurred_at": at(1, 9), "symptom_type": "fatigue", "severity": 2, "note": None},
                {"occurred_at": at(2, 21), "symptom_type": "fatigue", "severity": 1, "note": None}]
    bp = [{"measured_at": at(2, 8), "systolic": 130, "diastolic": 84, "pulse": None}]
    r = dr.build(inputs(cgm=cgm([6.0] * 192), symptoms=symptoms, onboarding=ONBOARDING, bp=bp))
    latest = r["symptom_latest"]
    assert [x["label"] for x in latest["latest"]] == ["HbA1c", "Blood pressure", "Weight", "Waist"]
    assert latest["latest"][1] == {"label": "Blood pressure", "value": "130/84 mmHg", "on": "2 Oct 2026"}
    row = latest["rows"][0]
    assert row["symptom"] == "Fatigue" and row["logged"] == 2
    assert row["text"] == ("Fatigue was logged 2 times. Logged together with: HbA1c 7.2% (1 Sep 2026); Blood pressure 130/84 mmHg (2 Oct 2026); "
                           "Weight 70 kg; Waist 92 cm (1 Sep 2026).")
    text = (row["text"] + latest["note"]).lower()
    assert "cause" in text and not any(w in text for w in ("caused", "because", "due to", "led to", "normal", "safe"))
    out = DoctorReport.model_validate(r).model_dump(by_alias=True)
    assert out["symptomLatest"]["rows"][0]["logged"] == 2


def test_with_no_values_on_record_the_symptom_block_says_so_in_words() -> None:
    symptoms = [{"occurred_at": at(1, 9), "symptom_type": "thirst", "severity": None, "note": None}]
    r = dr.build(inputs(cgm=cgm([6.0] * 192), symptoms=symptoms, onboarding={}, profile={**PROFILE, "weight_kg": None}))
    assert r["symptom_latest"]["latest"] == []
    assert r["symptom_latest"]["rows"][0]["text"] == "Thirst was logged 1 time. Logged together with: no HbA1c, blood pressure, weight or waist on record yet."


def test_no_symptoms_in_the_period_gives_no_rows_but_still_lists_the_latest_values() -> None:
    r = dr.build(inputs(onboarding=ONBOARDING))
    assert r["symptom_latest"]["rows"] == [] and [x["label"] for x in r["symptom_latest"]["latest"]] == ["HbA1c", "Weight", "Waist"]
