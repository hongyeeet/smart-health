"""Log fixes (C3), database side: the new Bronze join in the meal reads runs against the real schema, and the check-in table accepts
a check-in with unanswered questions (null) but not an empty one.

Read only, or inside a transaction that is rolled back, so the shared database is left as it was.
Run from services/api:  python -m pytest tests/db/test_log_c3_db.py -q
"""
from datetime import datetime, timedelta

import psycopg
import pytest
from psycopg.rows import dict_row

from app.db import logstore
from app.services import diet_days as DD


@pytest.fixture()
def conn():
    c = psycopg.connect(logstore._dsn(), connect_timeout=20, row_factory=dict_row)
    try:
        yield c
    finally:
        c.rollback()
        c.close()


def test_the_day_reads_run_with_the_bronze_join_and_return_the_new_fields():
    today = datetime.now(logstore.TZ).date()
    out = DD.progress_days(today - timedelta(days=6), today)
    assert len(out["days"]) == 7
    for d in out["days"]:
        for m in d["meal_list"]:
            assert m["numbers_from"] in ("you", "estimate")


def test_the_recent_list_runs_and_labels_each_meal_by_its_source():
    rows = [e for e in logstore.recent(30) if e["kind"] == "meal"]
    for e in rows:
        assert e["detail"].startswith(("Your numbers", "Estimated", "Logged"))
        assert e["meal"] is None or e["meal"]["numbers_from"] in ("you", "estimate")


def test_the_meal_details_query_runs_for_real_meal_ids(conn):
    ids = [str(r["id"]) for r in conn.execute("select id from food_logs where deleted_at is null limit 3").fetchall()]
    if not ids:
        pytest.skip("no meals in the database yet")
    details = DD.meal_details(ids)
    assert set(details) <= set(ids)
    for d in details.values():
        assert d["numbers_from"] in ("you", "estimate")


def test_a_check_in_with_unanswered_questions_is_stored_as_null_and_an_empty_one_is_refused(conn):
    user = conn.execute("select id from users where id = %s", (logstore.person_id("person-0123456789ab"),)).fetchone()
    if user is None:
        pytest.skip("the demo user is not in this database")
    bronze = conn.execute(
        "insert into bronze_wellbeing (user_id, source, payload, checksum) values (%s, 'manual', '{}'::jsonb, %s) returning id",
        (logstore.person_id("person-0123456789ab"), "c3-test-" + "x" * 8),
    ).fetchone()
    row = conn.execute(
        """insert into wellbeing_logs (user_id, recorded_at, mood, stress_self, sleep_quality, energy, source, bronze_id)
           values (%s, now(), null, 4, null, null, 'manual', %s) returning mood, stress_self""",
        (logstore.person_id("person-0123456789ab"), bronze["id"]),
    ).fetchone()
    assert row["mood"] is None and row["stress_self"] == 4
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        conn.execute(
            """insert into wellbeing_logs (user_id, recorded_at, mood, stress_self, sleep_quality, energy, source, bronze_id)
               values (%s, now(), null, null, null, null, 'manual', %s)""",
            (logstore.person_id("person-0123456789ab"), bronze["id"]),
        )


def test_the_notification_lock_and_lookup_run(conn):
    # the advisory lock taken before every reminder write, and the lunch-slot lookup, both run on this schema
    conn.execute("select pg_advisory_xact_lock(hashtext(%s))", (f"notifications:{logstore.person_id("person-0123456789ab")}",))
    n = conn.execute(
        "select count(*) n from notifications where user_id=%s and payload->>'key' = any(%s)",
        (logstore.person_id("person-0123456789ab"), sorted(logstore.lunch_slot_keys(datetime.now(logstore.TZ).date().isoformat()))),
    ).fetchone()["n"]
    assert n >= 0
