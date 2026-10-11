"""Onboarding history (migration 0032): each new field is saved and read back, against the real tables.

Each test runs inside a transaction that is rolled back, so the shared database is left untouched. The connection uses dict rows,
as the app does (app/db/logstore.py). The tests skip with a message while migration 0032 is not applied to the database (the
columns and tables do not exist yet).
Run from services/api:  python -m pytest tests/db/test_onboarding_history.py -q      (needs DATABASE_URL in the private .env)
"""
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url
from download_data import load_env

from app.schemas.onboarding import ProfileIn
from app.services import onboarding as svc

TODAY = date(2026, 10, 11)
NOT_APPLIED = ("migration 0032 is not applied to this database yet (the onboarding history columns and tables are missing), "
               "so this test is skipped. It runs once 0032 is applied.")


@pytest.fixture()
def conn():
    load_env()
    c = psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20, row_factory=dict_row)
    svc.reset_history_cache()
    try:
        yield c
    finally:
        c.rollback()
        c.close()
        svc.reset_history_cache()


@pytest.fixture()
def user(conn):
    if not svc.history_ready(conn):
        pytest.skip(NOT_APPLIED)
    return conn.execute("insert into users (is_demo) values (true) returning id").fetchone()["id"]


def count(conn, sql, params=()):
    return conn.execute(f"select count(*) as n from ({sql}) q", params).fetchone()["n"]


def save(conn, user, **body):
    """Save the answers the way PUT /onboarding/profile does: the camelCase body, then only the fields it contains."""
    sent = ProfileIn.model_validate({"birthYear": 1960, "hasDiabetes": "yes", **body}).model_dump(exclude_unset=True)
    return svc.save_profile(conn, user, sent, svc.enum_labels(conn), TODAY.year, TODAY)


def test_gender_other_is_refused_and_nothing_is_written(conn, user):
    with pytest.raises(svc.OnboardingError, match="Choose male or female"):
        save(conn, user, gender="other")
    assert count(conn, "select 1 from user_profile where user_id = %s", (user,)) == 0


def test_waist_is_saved_once_per_change_and_read_back(conn, user):
    save(conn, user, waistCm=84.5)
    save(conn, user, waistCm=84.5)                       # the same value again: no new row
    assert count(conn, "select 1 from body_measurements where user_id = %s and source = 'onboarding'", (user,)) == 1
    assert svc.load(conn, user)["history"]["waist_cm"] == Decimal("84.5")
    save(conn, user, waistCm=86)
    assert count(conn, "select 1 from body_measurements where user_id = %s", (user,)) == 2
    assert svc.load(conn, user)["history"]["waist_cm"] == Decimal("86.0")


def test_diabetes_and_low_glucose_history_are_saved_and_read_back(conn, user):
    save(conn, user, diagnosedYear=2015, careSetting="gp", healthierSg="unsure", hypoLast3m="1-2", hypoAwareness="5",
         hypoNeededHelp="no")
    history = svc.load(conn, user)["history"]
    assert (history["diagnosed_year"], history["care_setting"], history["healthier_sg"]) == (2015, "gp", "unsure")
    assert (history["hypo_last3m"], history["hypo_awareness"], history["hypo_needed_help"]) == ("1-2", "5", "no")
    save(conn, user, hypoNeededHelp="yes")                # a key left out is kept
    assert svc.load(conn, user)["history"]["hypo_awareness"] == "5"
    assert svc.load(conn, user)["history"]["hypo_needed_help"] == "yes"


def test_conditions_are_one_row_each_and_saving_again_does_not_duplicate_them(conn, user):
    body = {"conditions": ["hypertension", "high_cholesterol", "none"], "otherCondition": "Gout"}
    save(conn, user, **body)
    save(conn, user, **body)
    assert count(conn, "select 1 from conditions where user_id = %s and deleted_at is null", (user,)) == 3
    history = svc.load(conn, user)["history"]
    assert sorted(history["conditions"]) == ["high_cholesterol", "hypertension"]
    assert history["other_condition"] == "Gout"


def test_allergies_are_one_row_each_and_a_new_list_replaces_the_onboarding_ones(conn, user):
    save(conn, user, allergies=[{"substance": "Penicillin", "reaction": "rash"}, {"substance": "Peanut"}])
    assert count(conn, "select 1 from allergies where user_id = %s and deleted_at is null", (user,)) == 2
    save(conn, user, allergies=[{"substance": "Shellfish"}])
    assert svc.load(conn, user)["history"]["allergies"] == [{"substance": "Shellfish", "reaction": None}]


def test_last_check_dates_are_saved_to_preventive_status_as_answers(conn, user):
    save(conn, user, eyeCheck="within_year", footCheck="never_unsure")
    history = svc.load(conn, user)["history"]
    assert (history["eye_check"], history["foot_check"]) == ("within_year", "never_unsure")
    rows = conn.execute(
        "select i.kind, s.status, s.last_done_on from patient_preventive_status s "
        "join preventive_items i on i.id = s.preventive_item_id where s.user_id = %s order by i.kind", (user,),
    ).fetchall()
    assert [(r["kind"], r["status"], r["last_done_on"]) for r in rows] == [
        ("eye_screening", "ok", None), ("foot_screening", "unknown", None)]       # no date is made up


def test_labs_are_saved_with_the_lab_date_and_hba1c_in_percent(conn, user):
    body = {"labDate": "2026-09-01", "hba1c": 55, "hba1cUnit": "mmol/mol", "fastingGlucose": 7.4, "glucoseUnit": "mmol/L",
            "fastingInsulin": 11.5}
    save(conn, user, **body)
    save(conn, user, **body)                              # the same labs again: still one row each
    rows = conn.execute(
        "select test, value, unit from lab_results where user_id = %s and deleted_at is null order by test::text", (user,)
    ).fetchall()
    assert [(r["test"], r["unit"]) for r in rows] == [("fasting_glucose", "mmol/L"), ("fasting_insulin", "mcU/mL"), ("hba1c", "%")]
    assert Decimal(str(next(r["value"] for r in rows if r["test"] == "hba1c"))) == Decimal("7.2")
    labs = svc.load(conn, user)["history"]
    assert labs["lab_date"] == date(2026, 9, 1) and labs["hba1c_unit"] == "%"


def test_devices_one_row_for_the_chosen_watch_and_none_removes_it(conn, user):
    save(conn, user, watchModel="apple", cgmModel="libre")
    save(conn, user, watchModel="apple", cgmModel="libre")
    rows = conn.execute("select kind, label from devices where user_id = %s and deleted_at is null order by kind", (user,)).fetchall()
    assert [(r["kind"], r["label"]) for r in rows] == [("cgm", "libre"), ("watch", "apple")]
    save(conn, user, cgmModel="none")
    rows = conn.execute("select kind, label from devices where user_id = %s and deleted_at is null", (user,)).fetchall()
    assert [(r["kind"], r["label"]) for r in rows] == [("watch", "apple")]


def test_fields_that_are_not_sent_are_not_written(conn, user):
    save(conn, user, hba1c=7.2, hba1cUnit="%", labDate="2026-09-01", conditions=["heart"])
    save(conn, user, conditions=["stroke"])               # the labs were not sent this time: they stay
    history = svc.load(conn, user)["history"]
    assert history["hba1c"] == Decimal("7.2")
    assert history["conditions"] == ["stroke"]


def test_report_fields_show_only_onboarding_rows_that_are_not_deleted(conn, user):
    save(conn, user, conditions=["hypertension"], waistCm=88, diagnosedYear=2015, careSetting="gp", watchModel="apple")
    bronze = conn.execute(
        "insert into bronze_profile (user_id, source, payload, checksum) values (%s, 'manual', '{}'::jsonb, %s) returning id",
        (user, "manual-check"),
    ).fetchone()["id"]
    conn.execute("insert into conditions (user_id, name, code, source, bronze_id) values (%s, 'Gout', null, 'manual', %s)", (user, bronze))
    report = svc.onboarding_report_fields(conn, user)
    assert report["waist"]["cm"] == 88.0 and report["diagnosed_year"] == 2015 and report["care_setting"] == "gp"
    assert report["conditions"] == [{"name": "High blood pressure", "code": "hypertension"}]   # the manual 'Gout' row is not read
    assert report["devices"] == [{"kind": "watch", "label": "Apple Watch"}]
    assert set(report) == {"waist", "diagnosed_year", "care_setting", "conditions", "allergies", "labs", "devices"}
