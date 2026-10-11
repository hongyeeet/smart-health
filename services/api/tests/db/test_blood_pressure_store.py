"""Blood pressure: save, read back, edit, delete, duplicates, and the recent_bp read, against the shared database.

Every test runs twice, once for each table layout the code supports:
  - before_0035: the table as it is before migration 0035 (no id, pulse or note columns; the Bronze layout).
  - after_0035: the migration's own statements (services/api/alembic/versions/0035_blood_pressure_columns.py) run inside the test's
    transaction. PostgreSQL DDL is transactional, so they are rolled back with it.
Each test runs inside a transaction that is rolled back, so the shared database is left untouched. The store's `tx()` is replaced
by a savepoint on that same connection, so a refused save is rolled back exactly as it is in the app.
Run from services/api:  python -m pytest tests/db/test_blood_pressure_store.py -q   (needs DATABASE_URL in .env)
"""
import importlib.util
import os
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

from app.db import logstore  # noqa: E402
from app.schemas.log import BloodPressureInput  # noqa: E402
from app.services import blood_pressure  # noqa: E402
from app.services.blood_pressure import recent_bp  # noqa: E402

MIGRATION = ROOT / "services" / "api" / "alembic" / "versions" / "0035_blood_pressure_columns.py"
MR_TAN = uuid.UUID("dc48e209-5731-5b3d-89d9-986242c54368")


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_0035", MIGRATION)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MIG = _load_migration()
REAL_COLUMNS_READY = blood_pressure.columns_ready


def apply(conn, statements) -> None:
    """Run migration statements on the test's own transaction. A lock wait is cut short so a busy table cannot hang the tests."""
    conn.execute("set local lock_timeout = '10s'")
    for s in statements:
        conn.execute(s)


@pytest.fixture()
def conn():
    load_env()
    c = psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20, row_factory=dict_row)
    try:
        yield c
    finally:
        c.rollback()
        c.close()


@pytest.fixture(params=["before_0035", "after_0035"])
def schema(request, conn, monkeypatch):
    """The table layout the code sees: before migration 0035, or after it (the migration run inside this test's transaction)."""
    blood_pressure.reset_cache()
    if request.param == "before_0035" and REAL_COLUMNS_READY(conn):
        # the real database already has migration 0035, so the old layout cannot be exercised here any more (the unit tests cover it)
        blood_pressure.reset_cache()
        pytest.skip("migration 0035 is applied to this database")
    blood_pressure.reset_cache()
    if request.param == "after_0035":
        apply(conn, MIG.UP)
        monkeypatch.setattr(blood_pressure, "columns_ready", REAL_COLUMNS_READY)
    else:
        monkeypatch.setattr(blood_pressure, "columns_ready", lambda c: False)
    yield request.param
    blood_pressure.reset_cache()


def only(mode: str, schema: str) -> None:
    if schema != mode:
        pytest.skip(f"this check is for the {mode} layout")


@pytest.fixture()
def uid(conn, schema, monkeypatch):
    user = str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()["id"])

    @contextmanager
    def fake_tx():
        # a savepoint: committed on success, rolled back on any error, all inside the test's own transaction
        with conn.transaction():
            yield conn

    monkeypatch.setattr(logstore, "tx", fake_tx)
    monkeypatch.setattr(logstore, "current_user", lambda: uuid.UUID(user))
    return user


def reading(systolic=128, diastolic=82, pulse=None, measured_at=None, note=None) -> BloodPressureInput:
    return BloodPressureInput(systolic=systolic, diastolic=diastolic, pulse=pulse, measured_at=measured_at, note=note)


def ago(**kw) -> datetime:
    return datetime.now(timezone.utc) - timedelta(**kw)


def live_entry(entry_id: str, recent: list[dict]) -> dict | None:
    return next((e for e in recent if e["id"] == entry_id), None)


# ------------------------------------------------------------------ save and read back
def test_a_saved_reading_reads_back_in_recent_get_and_today(uid):
    when = ago(minutes=5)
    saved = logstore.create_blood_pressure(reading(128, 82, pulse=70, measured_at=when, note="  after a walk  "))

    entry = live_entry(saved["id"], logstore.recent())
    assert entry is not None
    assert entry["kind"] == "blood_pressure"
    assert entry["title"] == "128 over 82 mmHg"
    assert entry["detail"] == "Pulse 70 a minute"

    got = logstore.get_blood_pressure(saved["id"])
    assert (got["systolic"], got["diastolic"], got["pulse"], got["note"]) == (128, 82, 70, "after a walk")
    assert datetime.fromisoformat(got["measured_at"]) == when

    today = logstore.progress()["blood_pressure"]
    assert today["count"] == 1
    assert today["latest"].startswith("128 over 82 at ")
    assert [r["id"] for r in today["readings"]] == [saved["id"]]


def test_a_reading_without_pulse_or_note_reads_back_with_no_pulse(uid):
    saved = logstore.create_blood_pressure(reading(118, 76, measured_at=ago(minutes=2)))
    assert logstore.recent()[0]["detail"] == "No pulse entered"
    got = logstore.get_blood_pressure(saved["id"])
    assert got["pulse"] is None and got["note"] is None


def test_no_time_given_means_now(uid):
    saved = logstore.create_blood_pressure(reading())
    got = logstore.get_blood_pressure(saved["id"])
    assert abs(datetime.fromisoformat(got["measured_at"]) - datetime.now(timezone.utc)) < timedelta(minutes=1)


def test_bronze_keeps_the_entry_as_received_and_the_row_is_processed(conn, uid):
    saved = logstore.create_blood_pressure(reading(130, 85, pulse=72, measured_at=ago(minutes=3)))
    row = conn.execute("select payload, processing_status from bronze_blood_pressure where id=%s", (_bronze_of(conn, saved["id"]),)).fetchone()
    assert row["processing_status"] == "processed"
    assert row["payload"]["systolic"] == 130 and row["payload"]["pulse"] == 72 and "measuredAt" in row["payload"]


def _bronze_of(conn, entry_id: str) -> uuid.UUID:
    """The Bronze row behind an entry, whichever layout the table has (the entry id is that column)."""
    col = blood_pressure.id_column(conn)
    return conn.execute(f"select bronze_id from blood_pressure_readings where {col} = %s", (uuid.UUID(entry_id),)).fetchone()["bronze_id"]


def test_the_event_log_holds_the_kind_and_the_id_only(conn, uid):
    saved = logstore.create_blood_pressure(reading(140, 90, pulse=80, measured_at=ago(minutes=4), note="private note"))
    row = conn.execute(
        "select event, entity_id, payload from event_log where user_id=%s and event='log.blood_pressure.saved'", (uuid.UUID(uid),)
    ).fetchone()
    assert row is not None
    assert str(row["entity_id"]) == saved["id"]
    assert row["payload"] == {"kind": "blood_pressure"}


# ------------------------------------------------------------------ two times and duplicates
def test_readings_at_different_times_in_the_same_minute_do_not_conflict(uid):
    first = ago(minutes=6).replace(second=0, microsecond=0)
    a = logstore.create_blood_pressure(reading(128, 82, measured_at=first))
    b = logstore.create_blood_pressure(reading(131, 84, measured_at=first + timedelta(seconds=30)))
    assert a["id"] != b["id"]
    assert len(logstore.recent()) == 2


def test_a_second_live_reading_at_the_same_time_is_refused_and_leaves_nothing_behind(conn, uid):
    when = ago(minutes=10)
    logstore.create_blood_pressure(reading(128, 82, measured_at=when))
    with pytest.raises(logstore.DuplicateReading):
        logstore.create_blood_pressure(reading(131, 84, pulse=66, measured_at=when))
    assert len(logstore.recent()) == 1
    assert conn.execute("select count(*) n from bronze_blood_pressure where user_id=%s", (uuid.UUID(uid),)).fetchone()["n"] == 1


# ------------------------------------------------------------------ delete
def test_delete_is_soft_and_the_same_time_can_be_logged_again(conn, uid):
    when = ago(minutes=20)
    first = logstore.create_blood_pressure(reading(128, 82, measured_at=when))
    assert logstore.delete_entry(first["id"]) is True
    assert logstore.recent() == []
    assert logstore.get_blood_pressure(first["id"]) is None
    assert logstore.progress()["blood_pressure"]["count"] == 0
    # the row is kept, marked deleted
    assert conn.execute("select count(*) n from blood_pressure_readings where user_id=%s and deleted_at is not null", (uuid.UUID(uid),)).fetchone()["n"] == 1
    # deleting again finds nothing
    assert logstore.delete_entry(first["id"]) is False
    # "delete it and log it again" at the same time works, as a new entry
    again = logstore.create_blood_pressure(reading(126, 80, pulse=68, measured_at=when))
    assert again["id"] != first["id"]
    assert logstore.get_blood_pressure(again["id"])["systolic"] == 126
    assert logstore.get_blood_pressure(first["id"]) is None


def test_delete_with_a_malformed_id_is_refused_as_a_value_error(uid):
    # the router turns this into a 404
    with pytest.raises(ValueError):
        logstore.delete_entry("not-an-id")


# ------------------------------------------------------------------ edit
def test_before_0035_an_edit_saves_a_new_entry_in_place_of_the_old(uid, schema):
    only("before_0035", schema)
    old = logstore.create_blood_pressure(reading(128, 82, pulse=70, measured_at=ago(minutes=30)))
    new = logstore.update_blood_pressure(old["id"], reading(122, 78, measured_at=ago(minutes=25), note="sitting"))
    assert new is not None and new["id"] != old["id"]
    assert logstore.get_blood_pressure(old["id"]) is None
    got = logstore.get_blood_pressure(new["id"])
    assert (got["systolic"], got["diastolic"], got["pulse"], got["note"]) == (122, 78, None, "sitting")
    assert [e["id"] for e in logstore.recent()] == [new["id"]]


def test_after_0035_an_edit_keeps_the_id_and_updates_the_row_in_place(conn, uid, schema):
    only("after_0035", schema)
    old = logstore.create_blood_pressure(reading(128, 82, pulse=70, measured_at=ago(minutes=30)))
    new = logstore.update_blood_pressure(old["id"], reading(122, 78, measured_at=ago(minutes=25), note="sitting"))
    assert new["id"] == old["id"]
    got = logstore.get_blood_pressure(old["id"])
    assert (got["systolic"], got["diastolic"], got["pulse"], got["note"]) == (122, 78, None, "sitting")
    assert [e["id"] for e in logstore.recent()] == [old["id"]]
    # one row, edited in place, with the time of the edit
    rows = conn.execute("select count(*) n, max(updated_at) upd from blood_pressure_readings where user_id=%s", (uuid.UUID(uid),)).fetchone()
    assert rows["n"] == 1 and rows["upd"] is not None


def test_edit_to_the_same_time_keeps_one_live_reading(uid):
    when = ago(minutes=40)
    old = logstore.create_blood_pressure(reading(128, 82, measured_at=when))
    new = logstore.update_blood_pressure(old["id"], reading(129, 83, measured_at=when))
    assert logstore.get_blood_pressure(new["id"])["systolic"] == 129
    assert len(logstore.recent()) == 1


def test_edit_onto_another_live_reading_is_refused_and_the_original_stays(uid):
    t1, t2 = ago(hours=2), ago(hours=1)
    a = logstore.create_blood_pressure(reading(128, 82, measured_at=t1))
    logstore.create_blood_pressure(reading(135, 88, measured_at=t2))
    with pytest.raises(logstore.DuplicateReading):
        logstore.update_blood_pressure(a["id"], reading(120, 75, measured_at=t2))
    still = logstore.get_blood_pressure(a["id"])
    assert still is not None and still["systolic"] == 128
    assert len(logstore.recent()) == 2


def test_edit_onto_the_time_of_a_deleted_reading_works_and_the_entry_is_the_only_one_live(uid, schema):
    """A time that only a deleted reading holds is free for an edit. After 0035 the entry keeps its id."""
    t1, t2 = ago(hours=3), ago(hours=1)
    gone = logstore.create_blood_pressure(reading(128, 82, measured_at=t1))
    assert logstore.delete_entry(gone["id"]) is True
    entry = logstore.create_blood_pressure(reading(135, 88, measured_at=t2))

    new = logstore.update_blood_pressure(entry["id"], reading(140, 92, pulse=75, measured_at=t1, note="moved"))
    assert new is not None
    if schema == "after_0035":
        assert new["id"] == entry["id"]
    live = logstore.recent()
    assert [e["id"] for e in live] == [new["id"]]
    got = logstore.get_blood_pressure(new["id"])
    assert (got["systolic"], got["diastolic"], got["pulse"], got["note"]) == (140, 92, 75, "moved")
    assert datetime.fromisoformat(got["measured_at"]) == t1
    assert logstore.get_blood_pressure(gone["id"]) is None


def test_edit_of_a_missing_or_malformed_entry_finds_nothing(uid):
    assert logstore.update_blood_pressure(str(uuid.uuid4()), reading()) is None
    with pytest.raises(ValueError):
        logstore.update_blood_pressure("not-an-id", reading())


# ------------------------------------------------------------------ recent_bp
def test_recent_bp_is_newest_first_and_respects_the_day_window(conn, uid):
    logstore.create_blood_pressure(reading(120, 76, measured_at=ago(days=40)))
    logstore.create_blood_pressure(reading(128, 82, pulse=70, measured_at=ago(days=3)))
    logstore.create_blood_pressure(reading(131, 85, measured_at=ago(hours=1)))
    user = uuid.UUID(uid)

    two_weeks = recent_bp(conn, user, 14)
    assert [r["systolic"] for r in two_weeks] == [131, 128]
    assert two_weeks[1]["pulse"] == 70 and two_weeks[0]["pulse"] is None
    assert all(isinstance(r["measured_at"], datetime) and r["measured_at"].tzinfo is not None for r in two_weeks)

    everything = recent_bp(conn, user, 60)
    assert [r["systolic"] for r in everything] == [131, 128, 120]


def test_recent_bp_leaves_out_deleted_readings(conn, uid):
    keep = logstore.create_blood_pressure(reading(128, 82, measured_at=ago(hours=2)))
    gone = logstore.create_blood_pressure(reading(140, 90, measured_at=ago(hours=1)))
    logstore.delete_entry(gone["id"])
    rows = recent_bp(conn, uuid.UUID(uid), 14)
    assert [str(r["id"]) for r in rows] == [keep["id"]]


def test_recent_bp_for_a_new_user_is_empty(conn, uid):
    assert recent_bp(conn, uuid.UUID(uid), 14) == []


# ------------------------------------------------------------------ after 0035: the table itself
def test_after_0035_pulse_and_note_are_stored_in_the_table(conn, uid, schema):
    only("after_0035", schema)
    saved = logstore.create_blood_pressure(reading(128, 82, pulse=70, measured_at=ago(minutes=9), note="after a walk"))
    row = conn.execute("select id, pulse, note, updated_at from blood_pressure_readings where id=%s", (uuid.UUID(saved["id"]),)).fetchone()
    assert row is not None
    assert (row["pulse"], row["note"], row["updated_at"]) == (70, "after a walk", None)


def test_after_0035_the_table_refuses_a_pulse_or_note_outside_the_limits(conn, uid, schema):
    only("after_0035", schema)
    saved = logstore.create_blood_pressure(reading(128, 82, measured_at=ago(minutes=8)))
    for sql, args in [
        ("update blood_pressure_readings set pulse=29 where id=%s", (uuid.UUID(saved["id"]),)),
        ("update blood_pressure_readings set pulse=221 where id=%s", (uuid.UUID(saved["id"]),)),
        ("update blood_pressure_readings set note=%s where id=%s", ("x" * 301, uuid.UUID(saved["id"]))),
    ]:
        with pytest.raises(psycopg.errors.CheckViolation):
            with conn.transaction():
                conn.execute(sql, args)


def test_after_0035_the_migration_adds_the_columns_and_runs_twice(conn, schema):
    only("after_0035", schema)
    apply(conn, MIG.UP)  # the fixture already ran it once
    cols = {r["column_name"]: r for r in conn.execute(
        "select column_name, data_type, is_nullable, column_default from information_schema.columns "
        "where table_schema='public' and table_name='blood_pressure_readings'").fetchall()}
    assert cols["id"]["data_type"] == "uuid" and cols["id"]["is_nullable"] == "NO" and "gen_random_uuid" in cols["id"]["column_default"]
    assert cols["pulse"]["data_type"] == "smallint"
    assert cols["note"]["data_type"] == "text"
    assert cols["updated_at"]["data_type"] == "timestamp with time zone"
    idx = conn.execute("select indexname from pg_indexes where tablename='blood_pressure_readings' and indexname='blood_pressure_readings_id_key'").fetchall()
    assert len(idx) == 1
    pk = conn.execute("select pg_get_constraintdef(oid) d from pg_constraint where conrelid='blood_pressure_readings'::regclass and contype='p'").fetchone()
    assert pk["d"] == "PRIMARY KEY (user_id, recorded_at)"


def test_after_0035_the_downgrade_removes_only_the_new_columns_and_keeps_the_readings(conn, uid, schema):
    only("after_0035", schema)
    saved = logstore.create_blood_pressure(reading(128, 82, pulse=70, measured_at=ago(minutes=7), note="kept in bronze"))
    before = conn.execute("select count(*) n from blood_pressure_readings").fetchone()["n"]
    bronze = _bronze_of(conn, saved["id"])
    apply(conn, MIG.DOWN)
    blood_pressure.reset_cache()
    cols = {r["column_name"] for r in conn.execute(
        "select column_name from information_schema.columns where table_schema='public' and table_name='blood_pressure_readings'").fetchall()}
    assert cols == {"user_id", "recorded_at", "systolic_mmhg", "diastolic_mmhg", "source", "bronze_id", "deleted_at"}
    assert conn.execute("select count(*) n from blood_pressure_readings").fetchone()["n"] == before
    # the reading still reads back, with its pulse and note from the Bronze payload
    got = logstore.get_blood_pressure(str(bronze))
    assert got is not None and (got["pulse"], got["note"]) == (70, "kept in bronze")


# ------------------------------------------------------------------ Mr Tan's seeded readings
def test_mr_tans_seeded_readings_read_the_same_before_and_after_0035(conn, monkeypatch):
    load_env()

    @contextmanager
    def fake_tx():
        with conn.transaction():
            yield conn

    monkeypatch.setattr(logstore, "tx", fake_tx)
    monkeypatch.setattr(logstore, "current_user", lambda: MR_TAN)
    monkeypatch.setattr(blood_pressure, "columns_ready", lambda c: False)
    before_recent = [e for e in logstore.recent(limit=100000) if e["kind"] == "blood_pressure"]
    before_bp = recent_bp(conn, MR_TAN, 3650)

    apply(conn, MIG.UP)
    blood_pressure.reset_cache()
    monkeypatch.setattr(blood_pressure, "columns_ready", REAL_COLUMNS_READY)
    after_recent = [e for e in logstore.recent(limit=100000) if e["kind"] == "blood_pressure"]
    after_bp = recent_bp(conn, MR_TAN, 3650)
    try:
        assert len(before_bp) == 42
        assert after_recent == before_recent
        assert after_bp == before_bp
        assert all(r["pulse"] is None and r["note"] is None for r in after_bp)
        assert all(e["detail"] == "No pulse entered" for e in after_recent)
        # the id each seeded reading shows is still its Bronze row's id
        mismatched = conn.execute(
            "select count(*) n from blood_pressure_readings where user_id=%s and id <> bronze_id", (MR_TAN,)).fetchone()["n"]
        assert mismatched == 0
        assert logstore.get_blood_pressure(str(after_bp[0]["id"])) == {
            "id": str(after_bp[0]["id"]), "measured_at": after_bp[0]["measured_at"].isoformat(), "systolic": after_bp[0]["systolic"],
            "diastolic": after_bp[0]["diastolic"], "pulse": None, "note": None,
        }
    finally:
        blood_pressure.reset_cache()


def test_a_reading_saved_before_the_migration_gets_its_pulse_and_note_from_bronze(conn, uid, schema, monkeypatch):
    """Readings saved by hand before 0035 keep their pulse and note: the migration copies them from the Bronze payload."""
    only("before_0035", schema)
    saved = logstore.create_blood_pressure(reading(128, 82, pulse=70, measured_at=ago(minutes=12), note="  after a walk "))
    apply(conn, MIG.UP)
    blood_pressure.reset_cache()
    monkeypatch.setattr(blood_pressure, "columns_ready", REAL_COLUMNS_READY)
    assert blood_pressure.columns_ready(conn) is True
    got = logstore.get_blood_pressure(saved["id"])
    assert got is not None and (got["systolic"], got["pulse"], got["note"]) == (128, 70, "after a walk")
    assert conn.execute("select count(*) n from blood_pressure_readings where id=%s and bronze_id=%s",
                        (uuid.UUID(saved["id"]), uuid.UUID(saved["id"]))).fetchone()["n"] == 1
