"""Onboarding history (migration 0032): the checks (pure), the plans (pure), the save rules with a fake connection, and the report reads.

The fake keeps a small in-memory copy of the conditions and body_measurements rows, so a save twice in a row is checked for
duplicates the way the database would hold it. The real SQL is checked in tests/db/test_onboarding_history.py.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.onboarding import ProfileIn
from app.services import onboarding as svc

LABELS = {
    "gender_type": frozenset({"female", "male", "other", "prefer_not_to_say"}),
    "work_type": frozenset({"desk", "mixed", "standing", "physical", "shift", "not_working"}),
    "locale_code": frozenset({"en", "zh", "ms", "ta"}),
    "yes_no_unsure": frozenset({"yes", "no", "not_sure"}),
}
TODAY = date(2026, 10, 11)
USER = uuid4()
PROFILE = {
    "display_name": "Test", "language": "en", "has_diabetes": "yes", "birth_year": 1960, "gender": "male", "race": None,
    "height_cm": None, "weight_kg": None, "work_type": None, "work_days": [], "work_start": None, "work_end": None,
    "emergency_contact_name": None, "emergency_contact_phone": None, "emergency_contact_relation": None, "watch_model": None,
    "cgm_model": None, "allergies_note": None, "conditions_note": None, "updated_at": datetime(2026, 10, 9, tzinfo=timezone.utc),
}
HISTORY_COLUMNS = {"diagnosed_year": None, "care_setting": None, "healthier_sg": None, "hypo_last_3m": None, "hypo_symptoms": None}
BASE = {"birth_year": 1960, "has_diabetes": "yes"}


class Result:
    def __init__(self, value):
        self.value = value

    def fetchone(self):
        if isinstance(self.value, list):
            return self.value[0] if self.value else None
        return self.value

    def fetchall(self):
        if isinstance(self.value, list):
            return self.value
        return [] if self.value is None else [self.value]


class Conn:
    """Answers a query with the first rule whose text it contains (the test's rules come first), and records every statement.

    The conditions and body_measurements rows written during the test are kept, so repeated saves can be checked.
    """

    def __init__(self, rules: dict | None = None):
        defaults = {
            "select diagnosed_year, care_setting, healthier_sg": HISTORY_COLUMNS,
            "insert into bronze_profile": {"id": uuid4()},
            "insert into bronze_lab": {"id": uuid4()},
            "from consents where user_id": None,
            "from user_profile where user_id": PROFILE,
            "pg_enum": [{"typname": k, "enumlabel": v} for k, vals in LABELS.items() for v in sorted(vals)],
        }
        self.rules = {**(rules or {}), **{k: v for k, v in defaults.items() if k not in (rules or {})}}
        self.calls: list[tuple[str, tuple]] = []
        self.conditions: list[dict] = []
        self.body: list[dict] = []

    def execute(self, sql, params=()):
        flat = " ".join(sql.split())
        self.calls.append((flat, tuple(params)))
        if flat.startswith("update conditions set deleted_at"):
            user, source = params[0], params[1]
            want_code = "code is not null" in flat
            for r in self.conditions:
                if r["user"] == user and r["source"] == source and not r["deleted"] and (r["code"] is not None) == want_code:
                    r["deleted"] = True
            return Result(None)
        if flat.startswith("insert into conditions"):
            if len(params) == 4:                         # the free-text other condition is written with a literal null code
                user, name, source, _bronze = params
                code = None
            else:
                user, name, code, source, _bronze = params
            self.conditions.append({"user": user, "name": name, "code": code, "source": source, "deleted": False})
            return Result(None)
        if flat.startswith("select waist_cm from body_measurements"):
            live = [r for r in self.body if not r["deleted"]]
            return Result({"waist_cm": live[-1]["waist_cm"]} if live else None)
        if flat.startswith("insert into body_measurements"):
            user, waist, source = params[0], params[1], params[2]
            self.body.append({"user": user, "waist_cm": waist, "source": source, "deleted": False})
            return Result(None)
        if flat.startswith("update body_measurements set deleted_at"):
            for r in self.body:
                if not r["deleted"] and r["source"] == params[1]:
                    r["deleted"] = True
            return Result(None)
        for key, value in self.rules.items():
            if key in flat:
                return Result(value)
        return Result(None)

    def statements(self, text: str) -> list[tuple[str, tuple]]:
        return [(s, p) for s, p in self.calls if text in s]

    def writes(self) -> list[str]:
        return [s for s, _ in self.calls if s.startswith(("insert", "update", "delete"))]


@pytest.fixture(autouse=True)
def _fresh_caches():
    svc.reset_email_column_cache()
    yield
    svc.reset_email_column_cache()
    svc.reset_history_cache()


@pytest.fixture()
def ready(monkeypatch):
    monkeypatch.setattr(svc, "_history_ready", True)


@pytest.fixture()
def not_ready(monkeypatch):
    monkeypatch.setattr(svc, "_history_ready", False)


def save(conn, **sent):
    return svc.save_profile(conn, USER, {**BASE, **sent}, LABELS, TODAY.year, TODAY)


# ------------------------------------------------------------------ gender: only male or female now
def test_gender_accepts_only_male_or_female_and_clearing_it():
    for ok in ("male", "female", None):
        assert svc.check_profile({"gender": ok}, LABELS, 2026) == []
    for bad in ("other", "prefer_not_to_say", "robot"):
        assert svc.check_profile({"gender": bad}, LABELS, 2026) == [
            f"gender '{bad}' is not a choice Equinox knows. Choose male or female."]


def test_a_refused_gender_writes_nothing(ready):
    conn = Conn()
    with pytest.raises(svc.OnboardingError, match="Choose male or female"):
        save(conn, gender="other", conditions=["hypertension"])
    assert conn.writes() == []


# ------------------------------------------------------------------ pure checks for the history answers
def test_a_full_valid_history_passes_every_check():
    values = {
        "birth_year": 1960, "diagnosed_year": 2015, "care_setting": "gp", "healthier_sg": "yes", "hypo_last3m": "1-2",
        "hypo_awareness": "5", "hypo_needed_help": "no", "waist_cm": Decimal("88.5"), "conditions": ["hypertension", "none"],
        "other_condition": "Gout", "eye_check": "over_year", "foot_check": "never_unsure", "lab_date": date(2026, 9, 1),
        "hba1c": Decimal("7.2"), "hba1c_unit": "%", "fasting_glucose": Decimal("7.4"), "glucose_unit": "mmol/L",
        "fasting_insulin": Decimal("11.5"),
    }
    assert svc.history_problems(values, TODAY) == []


@pytest.mark.parametrize("field,bad", [
    ("care_setting", "clinic"), ("healthier_sg", "maybe"), ("hypo_last3m", "5"), ("hypo_awareness", "9"),
    ("hypo_needed_help", "sometimes"), ("eye_check", "yesterday"), ("foot_check", "sometimes"),
])
def test_a_choice_outside_its_list_is_refused_with_a_plain_message(field, bad):
    problems = svc.history_problems({field: bad}, TODAY)
    assert len(problems) == 1 and f"'{bad}' is not a choice Equinox knows" in problems[0]


def test_diagnosed_year_must_be_past_and_not_before_birth():
    assert svc.history_problems({"diagnosed_year": 2027}, TODAY) != []
    assert svc.history_problems({"diagnosed_year": 1985, "birth_year": 1990}, TODAY) == [
        "The year you were told you have diabetes cannot be before the year you were born."]
    assert svc.history_problems({"diagnosed_year": 2010, "birth_year": 1990}, TODAY) == []


def test_labs_need_a_date_units_and_a_value_in_range():
    assert svc.history_problems({"hba1c": Decimal("7.2"), "hba1c_unit": "%"}, TODAY) == ["Enter the date of your blood test."]
    assert svc.history_problems({"lab_date": date(2026, 9, 1), "hba1c": Decimal("7.2")}, TODAY) == [
        "Choose the unit for HbA1c: % or mmol/mol."]
    assert svc.history_problems({"lab_date": date(2026, 9, 1), "hba1c": Decimal(200), "hba1c_unit": "mmol/mol"}, TODAY) == [
        "HbA1c must be between 20 and 195 mmol/mol."]
    assert svc.history_problems({"lab_date": date(2026, 9, 1), "fasting_glucose": Decimal(7), "glucose_unit": None}, TODAY) == [
        "Choose the unit for fasting glucose: mmol/L or mg/dL."]
    assert svc.history_problems({"lab_date": date(2026, 10, 20), "fasting_insulin": Decimal(5)}, TODAY) == [
        "The date of the blood test cannot be in the future."]


def test_waist_and_condition_codes_are_checked():
    assert svc.history_problems({"waist_cm": Decimal(39)}, TODAY) == ["Waist must be between 40 and 200 cm."]
    assert svc.history_problems({"conditions": ["gout"]}, TODAY) == ["'gout' is not a condition Equinox knows."]
    assert svc.history_problems({"conditions": ["none"]}, TODAY) == []


# ------------------------------------------------------------------ plans
def test_hba1c_in_mmol_per_mol_is_stored_as_a_percentage_like_the_form_shows_it():
    assert svc.hba1c_percent(Decimal(55), "mmol/mol") == Decimal("7.2")
    assert svc.hba1c_percent(Decimal("7.25"), "%") == Decimal("7.25")


def test_waist_keeps_one_decimal_so_the_same_answer_is_recognised_as_unchanged():
    stored = svc.waist_value(Decimal("84.25"))
    assert stored == Decimal("84.3")
    assert svc.waist_changed(None, stored) is True
    assert svc.waist_changed(stored, svc.waist_value("84.25")) is False
    assert svc.waist_changed(Decimal("84.3"), svc.waist_value("85")) is True


def test_condition_rows_are_one_per_code_plus_the_free_text_other():
    rows = svc.condition_rows(["hypertension", "none", "hypertension", "high_cholesterol"], "  Gout  ")
    assert rows == [("High blood pressure", "hypertension"), ("High cholesterol", "high_cholesterol"), ("Gout", None)]
    assert svc.condition_rows(["none"], "") == []


def test_allergy_rows_drop_blank_names_and_store_a_blank_reaction_as_null():
    rows = svc.allergy_rows([{"substance": " Penicillin ", "reaction": " rash "}, {"substance": "  ", "reaction": "x"},
                             {"substance": "Peanut", "reaction": ""}])
    assert rows == [("Penicillin", "rash"), ("Peanut", None)]


def test_lab_rows_carry_the_unit_each_value_is_stored_in():
    rows = svc.lab_rows({"hba1c": Decimal(55), "hba1c_unit": "mmol/mol", "fasting_glucose": Decimal("7.4"),
                         "glucose_unit": "mmol/L", "fasting_insulin": Decimal("11.5")})
    assert [(r["test"], r["unit"]) for r in rows] == [("hba1c", "%"), ("fasting_glucose", "mmol/L"), ("fasting_insulin", "mcU/mL")]
    assert rows[0]["value"] == Decimal("7.2")


def test_a_device_of_none_or_blank_means_no_device():
    assert svc.device_label(None) is None and svc.device_label("none") is None and svc.device_label("") is None
    assert svc.device_label("apple") == "apple"


def test_hypo_patch_holds_only_the_keys_sent():
    assert svc.hypo_patch({"hypo_awareness": "3"}) == {"awareness": "3"}
    assert svc.hypo_patch({"hypo_needed_help": None}) == {"needed_help_12m": None}


# ------------------------------------------------------------------ schema: camelCase in, and the removed fields are not saved
def test_the_request_takes_the_new_fields_in_camel_case():
    sent = ProfileIn.model_validate({
        "waistCm": 88, "diagnosedYear": 2015, "careSetting": "gp", "hypoLast3m": "1-2", "allergies": [{"substance": "Penicillin"}],
        "labDate": "2026-09-01", "hba1c": 7.2, "hba1cUnit": "%",
    }).model_dump(exclude_unset=True)
    assert sent["waist_cm"] == 88 and sent["hypo_last3m"] == "1-2" and sent["allergies"] == [{"substance": "Penicillin"}]
    assert sent["lab_date"] == date(2026, 9, 1)


def test_kidney_and_blood_pressure_sent_by_an_old_screen_are_not_saved():
    assert ProfileIn.model_validate({"egfr": 80, "systolic": 128, "diastolic": 82}).model_dump(exclude_unset=True) == {}


def test_a_waist_outside_the_range_is_refused_by_the_schema():
    with pytest.raises(ValidationError):
        ProfileIn.model_validate({"waistCm": -3})


# ------------------------------------------------------------------ save rules (fake connection)
def test_before_the_migration_history_is_not_written_and_is_named_in_not_saved(not_ready):
    conn = Conn()
    out = save(conn, waist_cm=Decimal(88), conditions=["hypertension"], race="Malay")
    assert sorted(out["not_saved"]) == ["conditions", "waistCm"]
    assert conn.statements("insert into conditions") == [] and conn.statements("insert into body_measurements") == []
    assert conn.statements("insert into bronze_lab") == []
    assert any(s.startswith("update user_profile set") and "race = %s" in s for s, _ in conn.calls)   # the rest of the save still happens


def test_the_same_waist_saved_twice_gives_one_row(ready):
    conn = Conn()
    save(conn, waist_cm=Decimal(88))
    save(conn, waist_cm=Decimal(88))
    assert len(conn.body) == 1


def test_a_changed_waist_adds_a_row_and_the_latest_one_is_the_current_value(ready):
    conn = Conn()
    save(conn, waist_cm=Decimal(88))
    save(conn, waist_cm=Decimal("86.5"))
    assert [r["waist_cm"] for r in conn.body] == [Decimal("88.0"), Decimal("86.5")]
    assert conn.body[-1]["waist_cm"] == Decimal("86.5")


def test_conditions_saved_twice_leave_one_live_row_each(ready):
    conn = Conn()
    save(conn, conditions=["hypertension", "high_cholesterol"], other_condition="Gout")
    save(conn, conditions=["hypertension", "high_cholesterol"], other_condition="Gout")
    live = sorted(r["name"] for r in conn.conditions if not r["deleted"])
    assert live == ["Gout", "High blood pressure", "High cholesterol"]
    assert len(conn.conditions) == 6                     # the earlier copies are soft deleted, not removed


def test_a_new_condition_list_replaces_only_the_coded_rows(ready):
    conn = Conn()
    save(conn, conditions=["hypertension", "heart"], other_condition="Gout")
    save(conn, conditions=["stroke"])
    live = sorted(r["name"] for r in conn.conditions if not r["deleted"])
    assert live == ["Gout", "Stroke or mini-stroke"]


def test_each_replacement_soft_deletes_before_it_inserts(ready):
    conn = Conn()
    save(conn, allergies=[{"substance": "Penicillin"}], conditions=["hypertension"])
    order = [" ".join(s.split(" ")[:3]) for s, _ in conn.calls
             if s.startswith(("update conditions", "insert into conditions", "update allergies", "insert into allergies"))]
    assert order == ["update conditions set", "insert into conditions", "update allergies set", "insert into allergies"]


def test_check_dates_map_to_preventive_status_without_inventing_a_date(ready):
    conn = Conn()
    save(conn, eye_check="within_year", foot_check="never_unsure")
    writes = conn.statements("insert into patient_preventive_status")
    assert [p[1:] for _, p in writes] == [("ok", "eye_screening"), ("unknown", "foot_screening")]
    assert all("last_done_on" not in s for s, _ in writes)


def test_labs_are_written_with_one_bronze_row_and_the_lab_date(ready):
    conn = Conn()
    save(conn, lab_date=date(2026, 9, 1), hba1c=Decimal(55), hba1c_unit="mmol/mol", fasting_glucose=Decimal("7.4"),
         glucose_unit="mmol/L")
    assert len(conn.statements("insert into bronze_lab")) == 1
    inserted = conn.statements("insert into lab_results")
    assert len(inserted) == 2
    hba1c = next(p for _, p in inserted if p[2] == "hba1c")
    assert hba1c[3] == Decimal("7.2") and hba1c[4] == "%"
    assert hba1c[1].date() == date(2026, 9, 1)


def test_a_lab_value_without_its_date_is_refused_before_any_write(ready):
    conn = Conn()
    with pytest.raises(svc.OnboardingError, match="Enter the date of your blood test"):
        save(conn, hba1c=Decimal("7.2"), hba1c_unit="%")
    assert conn.writes() == []


def test_devices_one_row_for_the_chosen_watch_and_none_clears_the_sensor(ready):
    conn = Conn()
    save(conn, watch_model="apple", cgm_model=None)
    inserts = conn.statements("insert into devices")
    assert [(p[1], p[2]) for _, p in inserts] == [("watch", "apple")]
    deletes = conn.statements("update devices set deleted_at")
    assert [p[2] for _, p in deletes] == ["watch", "cgm"]


def test_report_fields_are_empty_before_the_migration(not_ready):
    conn = Conn()
    out = svc.onboarding_report_fields(conn, USER)
    assert out == {"waist": None, "diagnosed_year": None, "care_setting": None, "conditions": [], "allergies": [], "labs": [], "devices": []}
    assert all("from body_measurements" not in s for s, _ in conn.calls)


def test_report_fields_read_only_onboarding_rows_that_are_not_deleted(ready):
    conn = Conn({
        "select diagnosed_year, care_setting from user_profile": {"diagnosed_year": 2015, "care_setting": "gp"},
        "select waist_cm, (measured_at": {"waist_cm": Decimal("88.5"), "measured_on": date(2026, 10, 1)},
        "select name, code from conditions": [{"name": "High blood pressure", "code": "hypertension"}],
        "select substance, reaction from allergies": [{"substance": "Penicillin", "reaction": "rash"}],
        "distinct on (test)": [{"test": "hba1c", "value": Decimal("7.2"), "unit": "%", "taken_on": date(2026, 9, 1)}],
        "select kind, label from devices": [{"kind": "watch", "label": "apple"}],
    })
    out = svc.onboarding_report_fields(conn, USER)
    assert out["waist"] == {"cm": 88.5, "measured_on": "2026-10-01"}
    assert out["diagnosed_year"] == 2015 and out["care_setting"] == "gp"
    assert out["conditions"] == [{"name": "High blood pressure", "code": "hypertension"}]
    assert out["allergies"] == [{"substance": "Penicillin", "reaction": "rash"}]
    assert out["labs"] == [{"test": "hba1c", "value": 7.2, "unit": "%", "taken_on": "2026-09-01"}]
    assert out["devices"] == [{"kind": "watch", "label": "Apple Watch"}]
    assert conn.writes() == []                            # a read only
    for table in ("body_measurements", "conditions", "allergies", "lab_results", "devices"):
        reads = [(s, p) for s, p in conn.calls if f"from {table}" in s]
        assert reads, table
        assert all("source = %s" in s and "deleted_at is null" in s and "onboarding" in p for s, p in reads), table


# ------------------------------------------------------------------ the wire: PUT and GET through the router (camelCase in and out)
def test_put_and_get_speak_camel_case_and_refuse_a_gender_with_a_plain_422(monkeypatch, ready):
    from contextlib import contextmanager

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.routers import onboarding as router_mod
    from app.db import logstore

    conn = Conn()

    @contextmanager
    def fake_tx():
        yield conn

    monkeypatch.setattr(logstore, "tx", fake_tx)
    app = FastAPI()
    app.include_router(router_mod.router, prefix="/api/v1")
    client = TestClient(app)

    res = client.put("/api/v1/onboarding/profile", json={"gender": "other"})
    assert res.status_code == 422 and "Choose male or female" in res.json()["detail"]

    res = client.put("/api/v1/onboarding/profile", json={
        "birthYear": 1960, "hasDiabetes": "yes", "waistCm": 88, "labDate": "2026-09-01", "hba1c": 55, "hba1cUnit": "mmol/mol",
        "egfr": 80, "systolic": 128,
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["notSaved"] == [] and body["historyReady"] is True
    assert float(body["history"]["waistCm"]) == 88.0
    assert "egfr" not in str(body) and "systolic" not in str(body)     # the removed screens' fields are ignored
    assert len(conn.statements("insert into lab_results")) == 1
