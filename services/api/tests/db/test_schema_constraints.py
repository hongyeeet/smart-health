"""Constraint tests for the data model v2 Bronze and Silver tables (docs/specs/data-model-v2.md).

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

BRONZE = ["bronze_profile", "bronze_medication", "bronze_lab", "bronze_watch", "bronze_cgm", "bronze_blood_pressure",
          "bronze_exercise", "bronze_food", "bronze_symptom", "bronze_wellbeing"]


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


def bronze(conn, table, user_id, checksum=None):
    return conn.execute(f"insert into {table} (user_id, source, payload, checksum) values (%s, 'manual', '{{}}'::jsonb, %s) returning id",
                        (user_id, checksum or str(uuid.uuid4()))).fetchone()[0]


def rejected(conn, error, sql, params=()):
    """True if the statement raises `error` (rolled back to a savepoint so the test can continue)."""
    try:
        with conn.transaction():
            conn.execute(sql, params)
    except error:
        return True
    return False


def new_medication(conn, u, **over):
    b = bronze(conn, "bronze_medication", u)
    cols = dict(user_id=u, name="Test med", kind="prescription", frequency=1, source="manual", bronze_id=b, total_quantity=30)
    cols.update(over)
    return conn.execute(f"insert into medications ({', '.join(cols)}) values ({', '.join(['%s'] * len(cols))}) returning id", list(cols.values())).fetchone()[0]


# ---------------------------------------------------------------- structure
def test_row_level_security_is_on_for_every_table(conn):
    rows = conn.execute("select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace "
                        "where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity").fetchall()
    assert rows == [], f"RLS is off for: {[r[0] for r in rows]}"
    assert conn.execute("select count(*) from pg_policies where schemaname = 'public'").fetchone()[0] == 0, "policies are deferred: there must be none"


def test_every_table_says_which_layer_it_belongs_to(conn):
    rows = conn.execute("select c.relname, obj_description(c.oid) from pg_class c where c.relnamespace = 'public'::regnamespace and c.relkind = 'r' "
                        "and c.relname <> 'alembic_version'").fetchall()
    bad = [r[0] for r in rows if not (r[1] or "").startswith("Layer: ")]
    assert bad == [], f"no layer comment on: {bad}"
    assert sum(1 for r in rows if r[1].startswith("Layer: Bronze")) == 10


# ---------------------------------------------------------------- Bronze
def test_duplicate_bronze_checksum_is_rejected_per_user(conn):
    u = new_user(conn)
    sql = "insert into bronze_food (user_id, source, payload, checksum) values (%s, 'manual', '{}'::jsonb, %s)"
    conn.execute(sql, (u, "sha256-aaa"))
    assert rejected(conn, errors.UniqueViolation, sql, (u, "sha256-aaa"))
    conn.execute(sql, (new_user(conn), "sha256-aaa"))  # another user may have the same checksum


@pytest.mark.parametrize("table", BRONZE)
def test_bronze_rows_are_immutable_except_status(conn, table):
    u = new_user(conn)
    b = bronze(conn, table, u, "sha256-bbb")
    assert rejected(conn, errors.RaiseException, f"update {table} set checksum = 'changed' where id = %s", (b,))
    assert rejected(conn, errors.RaiseException, f"update {table} set payload = '{{\"x\": 1}}'::jsonb where id = %s", (b,))
    conn.execute(f"update {table} set processing_status = 'processed' where id = %s", (b,))
    conn.execute(f"update {table} set object_key = 'u/file.jpg' where id = %s", (b,))
    assert rejected(conn, errors.RaiseException, f"update {table} set object_key = 'u/other.jpg' where id = %s", (b,))
    conn.execute(f"update {table} set processing_status = 'deleted' where id = %s", (b,))
    assert rejected(conn, errors.RaiseException, f"update {table} set processing_status = 'received' where id = %s", (b,))


# ---------------------------------------------------------------- Silver: passive recording
def test_watch_readings_checks(conn):
    u = new_user(conn)
    b = bronze(conn, "bronze_watch", u)
    sql = ("insert into watch_readings (user_id, recorded_at, heart_rate_bpm, sleep_minutes, source, bronze_id) values (%s, %s, %s, %s, 'watch', %s)")
    conn.execute(sql, (u, "2026-10-01T08:00:00Z", 80, 0, b))
    assert rejected(conn, errors.CheckViolation, sql, (u, "2026-10-01T08:03:00Z", 80, 0, b))       # not on the 5-minute grid
    assert rejected(conn, errors.CheckViolation, sql, (u, "2026-10-01T08:05:00Z", 80, 6, b))       # at most 5 minutes asleep per bucket
    assert rejected(conn, errors.CheckViolation, sql, (u, "2026-10-01T08:10:00Z", 300, 0, b))      # impossible heart rate
    assert rejected(conn, errors.UniqueViolation, sql, (u, "2026-10-01T08:00:00Z", 81, 0, b))      # one row per bucket
    assert rejected(conn, errors.CheckViolation, "insert into watch_readings (user_id, recorded_at, source, bronze_id) values (%s, '2026-10-01T08:15:00Z', 'watch', %s)", (u, b))


def test_cgm_readings_range_and_uniqueness(conn):
    u = new_user(conn)
    b = bronze(conn, "bronze_cgm", u)
    sql = "insert into cgm_readings (user_id, recorded_at, glucose_mmol, source, bronze_id) values (%s, '2026-10-01T08:00:00Z', %s, 'cgm', %s)"
    assert rejected(conn, errors.CheckViolation, sql, (u, 0.9, b))
    assert rejected(conn, errors.CheckViolation, sql, (u, 35.0, b))
    conn.execute(sql, (u, 6.4, b))
    assert rejected(conn, errors.UniqueViolation, sql, (u, 6.5, b))


def test_blood_pressure_diastolic_must_be_below_systolic(conn):
    u = new_user(conn)
    b = bronze(conn, "bronze_blood_pressure", u)
    sql = "insert into blood_pressure_readings (user_id, recorded_at, systolic_mmhg, diastolic_mmhg, source, bronze_id) values (%s, now(), %s, %s, 'manual', %s)"
    assert rejected(conn, errors.CheckViolation, sql, (u, 100, 110, b))
    conn.execute(sql, (u, 130, 80, b))


# ---------------------------------------------------------------- Silver: medication
def test_medication_dates_frequency_and_schedule(conn):
    u = new_user(conn)
    b = bronze(conn, "bronze_medication", u)
    sql = "insert into medications (user_id, name, frequency, start_date, end_date, source, bronze_id, total_quantity) values (%s, 'x', %s, %s, %s, 'manual', %s, 30)"
    assert rejected(conn, errors.CheckViolation, sql, (u, 1, "2026-03-01", "2026-02-01", b))
    assert rejected(conn, errors.CheckViolation, sql, (u, 0, "2026-01-01", None, b))
    med = new_medication(conn, u)
    s = "insert into medication_schedule (user_id, medication_id, dose_time, quantity, meal_relation) values (%s, %s, '08:00', %s, %s)"
    assert rejected(conn, errors.CheckViolation, s, (u, med, 0, "na"))
    assert rejected(conn, errors.InvalidTextRepresentation, s, (u, med, 1, "during_meal"))
    conn.execute(s, (u, med, 2, "before_meal"))
    assert rejected(conn, errors.UniqueViolation, s, (u, med, 1, "after_meal"))        # one active row per medicine and time


def test_medication_log_rules(conn):
    u = new_user(conn)
    med = new_medication(conn, u)
    sql = "insert into medication_log (user_id, medication_id, scheduled_at, taken_at, status, source) values (%s, %s, %s, %s, %s, 'manual')"
    assert rejected(conn, errors.CheckViolation, sql, (u, med, "2026-02-02T08:00:00Z", None, "taken"))     # taken needs a time
    assert rejected(conn, errors.CheckViolation, sql, (u, med, None, None, "pending"))                      # needs a scheduled or a taken time
    conn.execute(sql, (u, med, "2026-02-01T08:00:00Z", None, "missed"))                                    # a missed dose may have no reason yet
    conn.execute(sql, (u, med, "2026-02-03T08:00:00Z", "2026-02-03T08:10:00Z", "taken"))


def test_lab_unit_must_match_the_test(conn):
    u = new_user(conn)
    b = bronze(conn, "bronze_lab", u)
    sql = "insert into lab_results (user_id, measured_at, test, value, unit, source, bronze_id) values (%s, now(), %s, %s, %s, 'manual', %s)"
    assert rejected(conn, errors.CheckViolation, sql, (u, "hba1c", 7.2, "mmol/mol", b))
    assert rejected(conn, errors.InvalidTextRepresentation, sql, (u, "ldl", 3.0, "mmol/L", b))
    conn.execute(sql, (u, "hba1c", 7.2, "%", b))
    conn.execute(sql, (u, "fasting_glucose", 7.1, "mg/dL", b))


# ---------------------------------------------------------------- Silver: active recording
def test_food_log_checks(conn):
    u = new_user(conn)
    b = bronze(conn, "bronze_food", u)
    sql = ("insert into food_logs (user_id, start_at, end_at, food, carbs_g, sugar_g, estimated_by, source, bronze_id) "
           "values (%s, '2026-10-01T05:00:00Z', %s, 'rice', %s, %s, 'user', 'manual', %s)")
    assert rejected(conn, errors.CheckViolation, sql, (u, "2026-10-01T04:00:00Z", 60, 5, b))        # ends before it starts
    assert rejected(conn, errors.CheckViolation, sql, (u, "2026-10-01T05:20:00Z", 20, 30, b))       # sugar is part of the carbohydrate
    conn.execute(sql, (u, "2026-10-01T05:20:00Z", 60, 10, b))


def test_exercise_log_checks_and_sets(conn):
    u = new_user(conn)
    b = bronze(conn, "bronze_exercise", u)
    sql = "insert into exercise_logs (user_id, start_at, end_at, type, intensity, source, bronze_id) values (%s, '2026-10-01T10:00:00Z', %s, 'walking', %s, 'manual', %s) returning id"
    assert rejected(conn, errors.CheckViolation, sql, (u, "2026-10-01T09:00:00Z", 3, b))
    assert rejected(conn, errors.CheckViolation, sql, (u, "2026-10-01T10:30:00Z", 6, b))
    ex = conn.execute(sql, (u, "2026-10-01T10:30:00Z", 3, b)).fetchone()[0]
    s = "insert into exercise_sets (exercise_log_id, user_id, exercise, exercise_order, set_no, reps, weight_kg, performed_at) values (%s, %s, 'Squat', 1, %s, %s, %s, now())"
    conn.execute(s, (ex, u, 1, 10, 40.0))
    conn.execute(s, (ex, u, 2, 12, None))                                                          # bodyweight: no weight
    assert rejected(conn, errors.UniqueViolation, s, (ex, u, 1, 10, 40.0))
    assert rejected(conn, errors.CheckViolation, s, (ex, u, 3, 0, 40.0))
    conn.execute("delete from exercise_logs where id = %s", (ex,))
    assert conn.execute("select count(*) from exercise_sets where user_id = %s", (u,)).fetchone()[0] == 0


def test_symptom_and_wellbeing_scales(conn):
    u = new_user(conn)
    bs, bw = bronze(conn, "bronze_symptom", u), bronze(conn, "bronze_wellbeing", u)
    s = "insert into symptom_logs (user_id, occurred_at, symptom_type, severity, source, bronze_id) values (%s, now(), 'numbness', %s, 'manual', %s)"
    assert rejected(conn, errors.CheckViolation, s, (u, 6, bs))
    conn.execute(s, (u, 3, bs))
    w = "insert into wellbeing_logs (user_id, recorded_at, mood, source, bronze_id) values (%s, now(), %s, 'manual', %s)"
    assert rejected(conn, errors.CheckViolation, w, (u, 0, bw))
    assert rejected(conn, errors.CheckViolation, "insert into wellbeing_logs (user_id, recorded_at, source, bronze_id) values (%s, now(), 'manual', %s)", (u, bw))   # at least one score
    conn.execute(w, (u, 4, bw))


# ---------------------------------------------------------------- Silver: profile
def test_user_profile_checks(conn):
    u = new_user(conn)
    b = bronze(conn, "bronze_profile", u)
    sql = ("insert into user_profile (user_id, display_name, has_diabetes, birth_year, work_days, glucose_target_low, glucose_target_high, bronze_id) "
           "values (%s, 'Test', 'yes', %s, %s, %s, %s, %s)")
    assert rejected(conn, errors.CheckViolation, sql, (u, 1800, [1, 2], 3.9, 10.0, b))
    assert rejected(conn, errors.CheckViolation, sql, (u, 1975, [1, 8], 3.9, 10.0, b))        # weekdays are 1 to 7
    assert rejected(conn, errors.CheckViolation, sql, (u, 1975, [1, 2], 10.0, 3.9, b))        # low must be below high
    conn.execute(sql, (u, 1975, [1, 2, 3, 4, 5], 3.9, 10.0, b))
    # the emergency contact is required in the app form, not in the database (imported users may have none)
    assert conn.execute("select emergency_contact_name from user_profile where user_id = %s", (u,)).fetchone()[0] is None


# ---------------------------------------------------------------- Gold
def test_baseline_percentiles_are_ordered_and_blood_pressure_has_no_hour(conn):
    u = new_user(conn)
    sql = ("insert into baselines (user_id, anchor_start, anchor_end, metric, hour_of_day, p05, p25, p50, p75, p95, n_days, n_points, reset_reason) "
           "values (%s, '2026-07-04', '2026-07-17', %s, %s, %s, %s, %s, %s, %s, 14, 100, 'first_14_days')")
    assert rejected(conn, errors.CheckViolation, sql, (u, "glucose", 7, 9, 8, 7, 6, 5))                 # not ordered
    assert rejected(conn, errors.CheckViolation, sql, (u, "systolic", 7, 110, 120, 130, 140, 150))     # blood pressure has no hour
    assert rejected(conn, errors.CheckViolation, sql, (u, "glucose", None, 5, 6, 7, 8, 9))             # other metrics need an hour
    conn.execute(sql, (u, "glucose", 7, 5, 6, 7, 8, 9))
    conn.execute(sql, (u, "systolic", None, 110, 120, 130, 140, 150))
    assert rejected(conn, errors.UniqueViolation, sql, (u, "systolic", None, 111, 121, 131, 141, 151))  # one baseline per metric, hour and window


def test_daily_summary_keeps_no_data_as_null(conn):
    u = new_user(conn)
    conn.execute("insert into daily_summary (user_id, local_date) values (%s, '2026-10-01')", (u,))
    assert conn.execute("select steps_total is null and glucose_mean_mmol is null and declining_metrics is null from daily_summary where user_id = %s", (u,)).fetchone()[0]


def test_updated_at_is_maintained_by_trigger(conn):
    u = new_user(conn)
    conn.execute("update users set updated_at = '2000-01-01', locale = 'zh' where id = %s", (u,))
    assert conn.execute("select extract(year from updated_at) from users where id = %s", (u,)).fetchone()[0] > 2000
