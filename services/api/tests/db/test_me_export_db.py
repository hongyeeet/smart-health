"""The data download (GET /me/export) against the shared database: Mr Tan and a brand-new empty person.

Read-only: the connection is set to read-only, and export_for only reads. The new person is a random id that has no row anywhere,
so every section for that person must come back as an empty list, never an error.
Run from services/api:  python -m pytest tests/db/test_me_export_db.py -q   (needs DATABASE_URL in .env)
"""
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

from app.services import me_settings as svc  # noqa: E402

MR_TAN = uuid.UUID("dc48e209-5731-5b3d-89d9-986242c54368")
NEW_PERSON = uuid.uuid4()
NOW = datetime.now(timezone.utc)
NEW_KEYS = ("blood_pressure", "body_measurements", "conditions", "allergies", "devices", "lab_results", "medicine_stock",
            "doctor_questions", "appointments")
ONBOARDING_PROFILE_KEYS = ("diagnosed_year", "care_setting", "healthier_sg", "hypo_last_3m", "hypo_symptoms")


@pytest.fixture()
def conn():
    load_env()
    c = psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20, row_factory=dict_row)
    c.read_only = True            # nothing in this file may write
    try:
        yield c
    finally:
        c.rollback()
        c.close()


def test_mr_tan_export_has_every_new_key_and_the_live_blood_pressure_count(conn):
    data = svc.export_for(conn, MR_TAN, NOW)
    for key in NEW_KEYS:
        assert isinstance(data[key], list), key
        assert data["counts"][key] == len(data[key]), key
    for key in ONBOARDING_PROFILE_KEYS:
        assert key in data["profile"], key
    live = conn.execute("select count(*) as n from blood_pressure_readings where user_id = %s and deleted_at is null", (MR_TAN,)).fetchone()["n"]
    assert len(data["blood_pressure"]) == live
    assert all(set(r) == {"measured_at", "systolic", "diastolic", "pulse", "note"} for r in data["blood_pressure"])


def test_a_brand_new_empty_person_gets_empty_lists_and_no_error(conn):
    data = svc.export_for(conn, NEW_PERSON, NOW)
    assert data["profile"] is None
    for key in NEW_KEYS:
        assert data[key] == [], key
        assert data["counts"][key] == 0, key
    assert data["consents"] == []
