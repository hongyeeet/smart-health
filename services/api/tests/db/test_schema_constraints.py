"""Constraint tests for the Bronze and Silver tables (E1-1, E1-2).

Each test runs inside a transaction that is rolled back, so the shared database is left untouched.
Run from the repo root:  python -m pytest services/api/tests/db -q
Needs DATABASE_URL in the private .env.
"""
import os
import sys
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg import errors

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402


@pytest.fixture()
def conn():
    load_env()
    c = psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20)
    try:
        yield c
    finally:
        c.rollback()
        c.close()


def new_user(conn):
    return conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0]


def new_med(conn, user_id, **over):
    cols = dict(user_id=user_id, display_name="Test med", kind="prescription", schedule_times="{08:00}",
                times_per_day=1, start_on="2026-01-01", source="manual", confirmed_by_user_at="2026-01-01T00:00:00Z")
    cols.update(over)
    names = ", ".join(cols)
    marks = ", ".join(["%s"] * len(cols))
    return conn.execute(f"insert into patient_medications ({names}) values ({marks}) returning id", list(cols.values())).fetchone()[0]


def rejected(conn, error, sql, params=()):
    """True if the statement raises `error` (rolled back to a savepoint so the test can continue)."""
    try:
        with conn.transaction():
            conn.execute(sql, params)
    except error:
        return True
    return False


def test_glucose_out_of_range_is_rejected(conn):
    u = new_user(conn)
    sql = "insert into glucose_readings (user_id, measured_at, value_mmol, context, source) values (%s, now(), %s, 'random', 'manual')"
    assert rejected(conn, errors.CheckViolation, sql, (u, 0.9))
    assert rejected(conn, errors.CheckViolation, sql, (u, 35.1))
    conn.execute(sql, (u, 5.6))  # a normal reading is accepted


def test_repeat_import_is_blocked_by_source_and_external_id(conn):
    u = new_user(conn)
    sql = "insert into glucose_readings (user_id, measured_at, value_mmol, context, source, external_id) values (%s, now(), 6.0, 'cgm', 'cgm', %s)"
    conn.execute(sql, (u, "abc-1"))
    assert rejected(conn, errors.UniqueViolation, sql, (u, "abc-1"))
    conn.execute(sql, (u, "abc-2"))  # a different external id is fine


def test_missed_dose_needs_a_reason(conn):
    u = new_user(conn)
    med = new_med(conn, u)
    sql = ("insert into dose_events (user_id, patient_medication_id, scheduled_at, window_end_at, status, miss_reason) "
           "values (%s, %s, %s, %s, %s, %s)")
    t0, t1 = "2026-02-01T08:00:00Z", "2026-02-01T10:00:00Z"
    assert rejected(conn, errors.CheckViolation, sql, (u, med, t0, t1, "missed", None))
    conn.execute(sql, (u, med, t0, t1, "missed", "forgot"))
    # a taken dose needs a confirmation time
    sql2 = ("insert into dose_events (user_id, patient_medication_id, scheduled_at, window_end_at, status) "
            "values (%s, %s, '2026-02-02T08:00:00Z', '2026-02-02T10:00:00Z', 'taken')")
    assert rejected(conn, errors.CheckViolation, sql2, (u, med))


def test_medication_end_date_cannot_precede_start(conn):
    u = new_user(conn)
    assert rejected(conn, errors.CheckViolation,
                    "insert into patient_medications (user_id, display_name, kind, schedule_times, times_per_day, start_on, end_on, source, confirmed_by_user_at) "
                    "values (%s, 'x', 'otc', '{08:00}', 1, '2026-03-01', '2026-02-01', 'manual', now())", (u,))
    new_med(conn, u)  # a valid one is accepted


def test_duplicate_bronze_checksum_is_rejected(conn):
    u = new_user(conn)
    sql = ("insert into ingestion_events (user_id, source_type, checksum, received_at, schema_version, entry_source) "
           "values (%s, 'meal_photo', %s, now(), 'v1', 'manual')")
    conn.execute(sql, (u, "sha256-aaa"))
    assert rejected(conn, errors.UniqueViolation, sql, (u, "sha256-aaa"))


def test_bronze_rows_are_immutable_except_status(conn):
    u = new_user(conn)
    ev = conn.execute("insert into ingestion_events (user_id, source_type, checksum, object_key, received_at, schema_version, entry_source) "
                      "values (%s, 'meal_photo', 'sha256-bbb', 'u/meals/bbb.jpg', now(), 'v1', 'manual') returning id", (u,)).fetchone()[0]
    assert rejected(conn, errors.RaiseException, "update ingestion_events set checksum = 'changed' where id = %s", (ev,))
    assert rejected(conn, errors.RaiseException, "update ingestion_events set object_key = 'other/path.jpg' where id = %s", (ev,))
    conn.execute("update ingestion_events set processing_status = 'processed' where id = %s", (ev,))
    conn.execute("update ingestion_events set processing_status = 'deleted', object_key = null where id = %s", (ev,))
    assert rejected(conn, errors.RaiseException, "update ingestion_events set processing_status = 'received' where id = %s", (ev,))


def test_only_one_open_cgm_sprint_per_user(conn):
    u = new_user(conn)
    sql = "insert into cgm_sprints (user_id, started_at) values (%s, now())"
    conn.execute(sql, (u,))
    assert rejected(conn, errors.UniqueViolation, sql, (u,))


def test_blood_pressure_diastolic_must_be_below_systolic(conn):
    u = new_user(conn)
    sql = "insert into blood_pressure_readings (user_id, measured_at, systolic, diastolic, source) values (%s, now(), %s, %s, 'manual')"
    assert rejected(conn, errors.CheckViolation, sql, (u, 100, 110))
    conn.execute(sql, (u, 130, 80))


def test_updated_at_is_maintained_by_trigger(conn):
    u = new_user(conn)
    # even if a caller tries to write an old value, the trigger resets updated_at to now()
    conn.execute("update users set updated_at = '2000-01-01', locale = 'zh' where id = %s", (u,))
    year = conn.execute("select extract(year from updated_at) from users where id = %s", (u,)).fetchone()[0]
    assert year > 2000


def test_row_level_security_is_on_for_every_table(conn):
    rows = conn.execute("select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace "
                        "where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity").fetchall()
    assert rows == [], f"RLS is off for: {[r[0] for r in rows]}"
    policies = conn.execute("select count(*) from pg_policies where schemaname = 'public'").fetchone()[0]
    assert policies == 0, "policies are deferred (memory.md section 13): there must be none"
