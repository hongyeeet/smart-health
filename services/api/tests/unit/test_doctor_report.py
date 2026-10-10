"""The doctor report's numbers (prd F12), on made-up data with known answers. No database: `build()` is pure."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.schemas.brief import DoctorReport
from app.services import doctor_report as dr

TZ = ZoneInfo("Asia/Singapore")
START, END = date(2026, 10, 1), date(2026, 10, 2)          # a two-day period
NOW = datetime(2026, 10, 3, 9, 0, tzinfo=TZ)


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=TZ)


def cgm(values: list[float], start: datetime | None = None, step: int = 15) -> list[tuple[datetime, float]]:
    t0 = start or at(1, 0)
    return [(t0 + timedelta(minutes=step * k), v) for k, v in enumerate(values)]


def inputs(**kw: object) -> dr.Inputs:
    base: dict[str, object] = {"now": NOW, "tz": TZ, "start": START, "end": END,
                               "profile": {"display_name": "Mr Tan", "birth_year": 1968, "gender": "male", "has_diabetes": "yes",
                                           "glucose_target_low": 3.9, "glucose_target_high": 10.0}}
    base.update(kw)
    return dr.Inputs(**base)  # type: ignore[arg-type]


def test_time_in_ranges_adds_up_and_uses_the_persons_own_range() -> None:
    # 192 readings = two full days at 15 minutes: 96 in range, 48 high, 24 very high, 16 low, 8 very low
    values = [6.0] * 96 + [11.0] * 48 + [15.0] * 24 + [3.5] * 16 + [2.8] * 8
    r = dr.build(inputs(cgm=cgm(values)))
    bands = {b["key"]: b for b in r["glucose"]["bands"]}
    assert [bands[k]["pct"] for k in ("in_range", "high", "very_high", "low", "very_low")] == [50.0, 25.0, 12.5, 8.3, 4.2]
    assert abs(sum(b["pct"] for b in bands.values()) - 100.0) <= 0.2
    assert bands["in_range"]["per_day"] == "12 h 00 min" and bands["very_low"]["per_day"] == "1 h 00 min"
    assert bands["in_range"]["outside"] is True and bands["low"]["outside"] is True          # below 70% in range, 12.5% below range
    assert r["cgm_wear"] == "100% of period" and r["glucose"]["sufficient"] is True


def test_boundary_readings_fall_in_the_right_band() -> None:
    r = dr.build(inputs(cgm=cgm([3.0, 3.8, 3.9, 10.0, 10.1, 13.9, 14.0, 2.9])))
    bands = {b["key"]: b["pct"] for b in r["glucose"]["bands"]}
    assert bands == {"very_high": 12.5, "high": 25.0, "in_range": 25.0, "low": 25.0, "very_low": 12.5}


def test_mean_sd_cv_and_gmi_match_the_formulas() -> None:
    r = dr.build(inputs(cgm=cgm([5.0, 7.0, 9.0] * 64)))
    m = {x["label"]: x["value"] for x in r["glucose"]["metrics"]}
    assert m["Mean glucose"] == "7.0" and m["Standard deviation"] == "1.6" and m["Variability (CV)"] == "23%"
    assert m["GMI (estimated from mean glucose)"] == "6.3%"                                # 3.31 + 0.02392 * 7.0 * 18.016


def test_no_sensor_data_says_so_and_never_shows_zero() -> None:
    r = dr.build(inputs())
    assert r["glucose"]["has_data"] is False and r["glucose"]["bands"] == [] and r["cgm_wear"] == "No sensor data"
    assert r["key_findings"][0] == "No sensor glucose readings in this period."
    assert all(c["value"] == "No data" for c in r["activity"])


def test_too_little_sensor_time_is_flagged() -> None:
    r = dr.build(inputs(cgm=cgm([6.0] * 20)))                                              # 20 of 192 expected readings
    assert r["glucose"]["sufficient"] is False
    assert any(a["title"] == "Little sensor data" for a in r["alerts"])


def test_the_daily_profile_only_draws_hours_with_enough_readings() -> None:
    r = dr.build(inputs(cgm=cgm([5.0, 6.0, 7.0, 8.0, 9.0], start=at(1, 8), step=10) + cgm([6.0], start=at(1, 12))))
    assert [p["hour"] for p in r["glucose"]["profile"]] == [8]
    p = r["glucose"]["profile"][0]
    assert (p["p5"], p["p25"], p["p50"], p["p75"], p["p95"]) == (5.2, 6.0, 7.0, 8.0, 8.8)


def test_a_symptom_is_matched_to_the_nearest_reading_the_change_before_it_the_last_dose_and_the_watch() -> None:
    readings = cgm([6.0], start=at(1, 8, 30)) + cgm([3.4], start=at(1, 9, 0))
    r = dr.build(inputs(
        cgm=readings,
        symptoms=[{"occurred_at": at(1, 9, 5), "symptom_type": "dizziness", "severity": 3, "note": "after a walk"}],
        medicines=[{"id": "m1", "name": "Gliclazide", "strength": "80 mg", "frequency": 1, "as_needed": False}],
        doses=[{"medication_id": "m1", "scheduled_at": at(1, 7), "taken_at": at(1, 7, 10), "status": "taken"}],
        watch=[{"recorded_at": at(1, 9, 5), "heart_rate_bpm": 96, "spo2_pct": 97.2, "steps": 40, "sleep_minutes": 0}],
    ))
    [e] = r["episodes"]
    assert (e["when"], e["symptom"], e["glucose"], e["zone"], e["change_30"]) == ("Thu 1 Oct 09:05", "Dizziness", 3.4, "low", -2.6)
    assert e["last_dose"] == "Gliclazide 80 mg, 1 h 55 min before" and (e["heart_rate"], e["spo2"]) == (96, 97)
    [row] = r["symptoms"]
    assert (row["logged"], row["low"], row["high"], row["in_range"], row["no_reading"]) == (1, 1, 0, 0, 0)
    assert row["note"] == "Low readings at 09:05"


def test_a_symptom_with_no_reading_nearby_is_counted_as_no_reading_not_as_in_range() -> None:
    r = dr.build(inputs(cgm=cgm([6.0], start=at(1, 8)), symptoms=[{"occurred_at": at(1, 20), "symptom_type": "headache", "severity": 2, "note": None}]))
    assert r["episodes"][0]["glucose"] is None and r["episodes"][0]["zone"] is None
    assert r["symptoms"][0]["no_reading"] == 1 and r["symptoms"][0]["in_range"] == 0


def test_doses_count_scheduled_taken_missed_and_not_logged_and_future_doses_are_left_out() -> None:
    meds = [{"id": "m1", "name": "Metformin", "strength": "500 mg", "frequency": 2, "as_needed": False},
            {"id": "m2", "name": "Paracetamol", "strength": None, "frequency": 1, "as_needed": True}]
    doses = [{"medication_id": "m1", "scheduled_at": at(1, 8), "taken_at": at(1, 8, 5), "status": "taken"},
             {"medication_id": "m1", "scheduled_at": at(1, 20), "taken_at": None, "status": "missed"},
             {"medication_id": "m1", "scheduled_at": at(2, 8), "taken_at": at(2, 9), "status": "taken"},
             {"medication_id": "m1", "scheduled_at": at(2, 20), "taken_at": None, "status": "pending"},
             {"medication_id": "m1", "scheduled_at": at(3, 20), "taken_at": None, "status": "pending"},        # after "now": not due yet
             {"medication_id": "m2", "scheduled_at": None, "taken_at": at(2, 14), "status": "taken"}]
    r = dr.build(inputs(medicines=meds, doses=doses))
    met, para = r["medicines"]
    assert (met["name"], met["regimen"], met["scheduled"], met["taken"], met["missed"], met["not_logged"], met["adherence_pct"]) == \
        ("Metformin 500 mg", "Twice a day", 4, 2, 1, 1, 50)
    assert (para["regimen"], para["scheduled"], para["taken"], para["adherence_pct"]) == ("Only when needed", None, 1, None)
    assert "Metformin 500 mg: 1 Oct 20:00" in r["medicines_note"]
    assert any(a["title"] == "Missed doses: Metformin 500 mg" for a in r["alerts"])


def test_alerts_are_ordered_facts_and_an_interaction_is_never_called_safe_or_a_reason_to_stop() -> None:
    r = dr.build(inputs(
        cgm=cgm([6.0] * 10 + [2.8]),
        medicines=[{"id": "a", "name": "Atorvastatin", "strength": "20 mg", "frequency": 1, "as_needed": False},
                   {"id": "b", "name": "Clarithromycin", "strength": "500 mg", "frequency": 2, "as_needed": False}],
        alerts=[{"med_a_id": "a", "med_b_id": "b", "med_a": "Atorvastatin 20 mg", "med_b": "Clarithromycin 500 mg", "summary": "May raise the statin level.", "origin": "both"}],
    ))
    assert [a["priority"] for a in r["alerts"]] == ["urgent", "interaction", "review"]            # the review row is "Little sensor data"
    assert r["alerts"][0]["title"] == "Glucose below 3.0 mmol/L" and "lowest 2.8 mmol/L" in r["alerts"][0]["detail"]
    inter = r["alerts"][1]
    assert inter["title"] == "Atorvastatin 20 mg + Clarithromycin 500 mg" and inter["detail"].startswith("Possible interaction.") and "not clinically reviewed" in inter["detail"]
    assert all(m["interaction"] for m in r["medicines"])
    text = " ".join([*r["key_findings"], *(a["title"] + " " + a["detail"] for a in r["alerts"]), r["medicines_note"] or ""]).lower()
    for word in ("stop ", "safe", "caused", "because", "normal", "validated", "should"):
        assert word not in text


def test_activity_uses_daily_steps_sleeping_heart_rate_and_high_stress_days() -> None:
    watch = [{"recorded_at": at(1, 10), "heart_rate_bpm": 80, "spo2_pct": None, "steps": 3000, "sleep_minutes": 0},
             {"recorded_at": at(1, 18), "heart_rate_bpm": 85, "spo2_pct": None, "steps": 2000, "sleep_minutes": 0},
             {"recorded_at": at(2, 10), "heart_rate_bpm": 82, "spo2_pct": None, "steps": 9000, "sleep_minutes": 0},
             {"recorded_at": at(2, 2), "heart_rate_bpm": 60, "spo2_pct": 95.0, "steps": 0, "sleep_minutes": 5},
             {"recorded_at": at(2, 3), "heart_rate_bpm": 64, "spo2_pct": 93.0, "steps": 0, "sleep_minutes": 5}]
    r = dr.build(inputs(watch=watch, stress=[(at(1, 21), 4), (at(2, 21), 2)]))
    cells = {c["label"]: c for c in r["activity"]}
    assert cells["Steps"]["value"] == "7,000/day" and cells["Steps"]["sub"] == "range 5,000–9,000"
    assert cells["Heart rate while asleep"]["value"] == "62 bpm" and cells["SpO2 while asleep"]["value"] == "94%"
    assert cells["Stress (self-rated)"]["value"] == "High on 1 of 2 logged days" and cells["Stress (self-rated)"]["sub"] == "1 Oct"


def test_the_report_fits_the_api_shape_and_the_header_is_filled_from_the_profile() -> None:
    r = dr.build(inputs(cgm=cgm([6.0] * 192), questions=["Should I take these at different times of day?"]))
    out = DoctorReport.model_validate(r)
    assert out.patient.name == "Mr Tan" and out.patient.sex_age == "Male, 58" and out.patient.diagnosis == "Diabetes (self-reported)"
    assert out.period.label == "1 Oct – 2 Oct 2026 (2 days)" and out.generated_on == "3 Oct 2026"
    assert out.questions == ["Should I take these at different times of day?"] and out.sources == "CGM"


BANNED = ("stop ", "safe", "caused", "because", "normal", "validated", "should")


def test_worth_discussing_is_ordered_capped_and_only_uses_the_rules_in_the_brief() -> None:
    alerts = [{"med_a_id": "a", "med_b_id": "b", "med_a": "Atorvastatin 20 mg", "med_b": "Clarithromycin 500 mg", "summary": "", "origin": "database"}]
    doses = [{"medication_id": "m1", "scheduled_at": at(1, 8), "taken_at": None, "status": "missed", "miss_reason": "forgot"},
             {"medication_id": "m1", "scheduled_at": at(1, 20), "taken_at": None, "status": "missed", "miss_reason": "forgot"},
             {"medication_id": "m1", "scheduled_at": at(2, 8), "taken_at": None, "status": "missed", "miss_reason": "forgot"},
             {"medication_id": "m1", "scheduled_at": at(2, 20), "taken_at": None, "status": "missed", "miss_reason": "felt_fine"}]
    patterns = [{"pattern_key": "short_sleep__fasting_glucose", "n_pairs": 9, "median_delta": 0.5},
                {"pattern_key": "evening_walk__next_morning_fasting", "n_pairs": 5, "median_delta": -0.4},     # exactly 5: counted
                {"pattern_key": "sweet_drink__rise", "n_pairs": 4, "median_delta": 1.0}]                    # 4: left out
    facts = [{"statement": "Skips the evening dose on busy days", "category": "barrier", "confidence": 0.9},
             {"statement": "Prefers tea without sugar", "category": "preference", "confidence": 0.99},       # not a shown category
             {"statement": "Walks after dinner", "category": "routine", "confidence": 0.7},
             {"statement": "Eats rice at lunch", "category": "food_response", "confidence": 0.8}]
    r = dr.build(inputs(alerts=alerts, doses=doses, patterns=patterns, facts=facts))
    items = r["worth_discussing"]
    assert [x["kind"] for x in items] == ["clash", "adherence", "pattern", "pattern", "fact"]          # 6 candidates, capped at 5
    assert items[0]["text"] == "A possible interaction is flagged between Atorvastatin 20 mg and Clarithromycin 500 mg."
    assert items[0]["evidence"] == "Open alert · source: drug-label rules, not clinically reviewed"
    assert items[1] == {"text": "Missed doses marked 'Forgot': 3 in 2 days.", "evidence": "3 of 4 doses marked missed in the period", "kind": "adherence"}
    assert items[2]["text"] == "After nights of under 6 hours of sleep, your fasting glucose was 0.5 mmol/L higher."
    assert items[3]["text"] == "On mornings after an evening walk, your fasting glucose was 0.4 mmol/L lower."
    assert items[4] == {"text": "Skips the evening dose on busy days", "evidence": "Confirmed by you · Barrier", "kind": "fact"}
    text = " ".join(f"{x['text']} {x['evidence']}" for x in items).lower()
    assert not any(w in text for w in BANNED)


def test_no_data_gives_an_empty_worth_list_and_empty_overnight_columns_not_zeros() -> None:
    r = dr.build(inputs())
    assert r["worth_discussing"] == []
    assert [(n["day"], n["fasting"], n["heart_rate"], n["spo2"]) for n in r["overnight"]] == [("1 Oct", None, None, None), ("2 Oct", None, None, None)]


def test_overnight_pairs_each_morning_fasting_glucose_with_the_night_that_ends_on_it() -> None:
    watch = [{"recorded_at": at(1, 0), "heart_rate_bpm": 90, "spo2_pct": 97.0, "steps": 0, "sleep_minutes": 5},       # night of 30 Sep
             {"recorded_at": at(1, 23), "heart_rate_bpm": 58, "spo2_pct": 96.0, "steps": 0, "sleep_minutes": 5},      # night ending 2 Oct
             {"recorded_at": at(2, 2), "heart_rate_bpm": 62, "spo2_pct": 94.0, "steps": 0, "sleep_minutes": 5},       # night ending 2 Oct
             {"recorded_at": at(2, 14), "heart_rate_bpm": 75, "spo2_pct": 98.0, "steps": 0, "sleep_minutes": 0}]      # awake: not a night
    r = dr.build(inputs(cgm=cgm([6.2], start=at(2, 5, 30)) + cgm([6.6], start=at(2, 6)), watch=watch))
    assert r["overnight"] == [{"day": "1 Oct", "fasting": None, "heart_rate": 90, "spo2": 97},
                              {"day": "2 Oct", "fasting": 6.4, "heart_rate": 60, "spo2": 95}]
    out = DoctorReport.model_validate(r)
    dumped = out.model_dump(by_alias=True)
    assert dumped["overnight"][1] == {"day": "2 Oct", "fasting": 6.4, "heartRate": 60, "spo2": 95}
    assert dumped["worthDiscussing"] == []
