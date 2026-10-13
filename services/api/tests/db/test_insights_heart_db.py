"""Insights heart rate, SpO2 and blood pressure against the shared database. Read-only: nothing is written.

A brand-new person has no watch data and no blood pressure, so the empty state is tested on a fresh id, not on demo, whose data
may change. Mr Tan's 90 days are checked for plausible shapes only (the numbers themselves are not pinned).
Run from services/api:  python -m pytest tests/db/test_insights_heart.py -q   (needs DATABASE_URL in .env)
"""
import os
import uuid
import sys
from datetime import date
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

from app.db import logstore  # noqa: E402
from app.services import insights as I  # noqa: E402
from app.services import insights_heart as H  # noqa: E402


@pytest.fixture()
def conn():
    load_env()
    c = psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20, row_factory=dict_row)
    try:
        yield c
    finally:
        c.rollback()
        c.close()


def test_a_new_person_has_no_watch_data_and_no_blood_pressure(conn):
    user = str(uuid.uuid4())       # a person with no data at all
    out = H.heart(conn, user, 30, date(2026, 10, 11))
    assert out["has_data"] is False
    assert out["heart_rate"]["avg"] is None and out["spo2"]["low"] is None
    assert len(out["days"]) == 30 and all(d["avg"] is None for d in out["days"])
    assert out["watch_end"] is None and out["end_note"] is False
    assert out["period"]["end"] == "2026-10-11"                 # no watch data: the period ends today
    assert H.blood_pressure(conn, user, 90, date(2026, 10, 11)) == {"count": 0, "latest": None, "readings": []}


def test_mr_tan_ninety_days_have_plausible_shapes(conn):
    user = str(logstore.MR_TAN_USER)
    out = H.heart(conn, user, 90, date(2026, 10, 11))
    assert out["has_data"] is True
    assert 1 <= out["days_with_data"] <= 90
    # the block ends on the last day of watch data, not on the other tabs' end, and says so
    assert out["watch_end"] is not None and out["watch_end"] < "2026-10-11"
    assert out["period"]["end"] == out["watch_end"] and out["end_note"] is True
    hr = out["heart_rate"]
    assert hr["low"] is not None and hr["high"] is not None and hr["low"] <= hr["avg"] <= hr["high"]
    assert 20 <= hr["low"] and hr["high"] <= 250
    sp = out["spo2"]
    assert 50 <= sp["low"] <= sp["avg"] <= 100
    assert len(out["days"]) == 90
    assert all(d["avg"] is None or d["avg"] > 0 for d in out["days"]), "a day without data must be null, never zero"
    bp = H.blood_pressure(conn, user, 3650, date(2026, 10, 11))
    assert bp["count"] >= len(bp["readings"]) >= 1 and bp["latest"] is not None
    assert all(40 <= r["systolic"] <= 260 and 30 <= r["diastolic"] <= 150 for r in bp["readings"])
    assert I.TZ is not None
