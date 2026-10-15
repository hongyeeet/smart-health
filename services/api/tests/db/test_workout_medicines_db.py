"""Beta-blocker rule, database side: the medicines read for it are the person's own and not deleted.

Each test runs inside a transaction that is rolled back, so the shared database is left untouched.
Run from services/api:  python -m pytest tests/db/test_workout_medicines_db.py -q       Needs DATABASE_URL in the private .env.
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

from app.db import logstore  # noqa: E402
from app.services.workout_effort import takes_beta_blocker  # noqa: E402


@pytest.fixture()
def conn():
    load_env()
    c = psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20, row_factory=dict_row)
    try:
        yield c
    finally:
        c.rollback()
        c.close()


def new_user(conn):
    return conn.execute("insert into users (is_demo) values (true) returning id").fetchone()["id"]


def add_medicine(conn, user_id, name, deleted=False):
    b = conn.execute("insert into bronze_medication (user_id, source, payload, checksum) values (%s, 'manual', '{}'::jsonb, %s) returning id",
                     (user_id, str(uuid.uuid4()))).fetchone()["id"]
    gone = datetime.now(timezone.utc) if deleted else None
    conn.execute("insert into medications (user_id, name, kind, frequency, source, bronze_id, total_quantity, deleted_at) "
                 "values (%s, %s, 'prescription', 1, 'manual', %s, 30, %s)", (user_id, name, b, gone))


def test_a_live_beta_blocker_is_found(conn):
    u = new_user(conn)
    add_medicine(conn, u, "Metoprolol 50 mg")
    add_medicine(conn, u, "Amlodipine 5 mg")
    assert takes_beta_blocker(logstore.medicine_names(conn, u)) is True


def test_no_beta_blocker_when_the_person_takes_none(conn):
    u = new_user(conn)
    add_medicine(conn, u, "Amlodipine 5 mg")
    add_medicine(conn, u, "Fish oil")
    assert takes_beta_blocker(logstore.medicine_names(conn, u)) is False


def test_a_deleted_beta_blocker_is_ignored(conn):
    u = new_user(conn)
    add_medicine(conn, u, "Atenolol 25 mg", deleted=True)
    add_medicine(conn, u, "Amlodipine 5 mg")
    assert "Atenolol 25 mg" not in logstore.medicine_names(conn, u)
    assert takes_beta_blocker(logstore.medicine_names(conn, u)) is False


def test_another_persons_beta_blocker_is_not_read(conn):
    mine, other = new_user(conn), new_user(conn)
    add_medicine(conn, other, "Propranolol 40 mg")
    assert takes_beta_blocker(logstore.medicine_names(conn, mine)) is False
