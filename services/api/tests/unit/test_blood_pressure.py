"""Blood pressure: the input rules (limits, top above bottom, no future time) and the recent_bp read function.

Pure checks, no database. The save and read-back checks against the database are in tests/db/test_blood_pressure_store.py.
"""
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from pydantic import TypeAdapter, ValidationError

from app.db import logstore
from app.schemas.log import BloodPressureInput, LogInput
from app.services import blood_pressure
from app.services.blood_pressure import recent_bp

REAL_COLUMNS_READY = blood_pressure.columns_ready


@pytest.fixture(autouse=True)
def bronze_layout(monkeypatch):
    """Most checks here are for the layout before migration 0035. The table-layout checks switch it on themselves."""
    blood_pressure.reset_cache()
    monkeypatch.setattr(blood_pressure, "columns_ready", lambda conn: False)
    yield
    blood_pressure.reset_cache()

SG = ZoneInfo("Asia/Singapore")


def bp(**kw) -> BloodPressureInput:
    data = {"systolic": 120, "diastolic": 80}
    data.update(kw)
    return BloodPressureInput(**data)


def rejected(**kw) -> str:
    """The plain message from the rule that refused the input (the field's own message or the pair check)."""
    with pytest.raises(ValidationError) as err:
        bp(**kw)
    return str(err.value)


# ------------------------------------------------------------------ the two numbers
def test_both_numbers_are_required():
    with pytest.raises(ValidationError):
        BloodPressureInput(diastolic=80)
    with pytest.raises(ValidationError):
        BloodPressureInput(systolic=120)


@pytest.mark.parametrize("systolic, diastolic", [(60, 30), (260, 150), (120, 80), (130, 129)])
def test_numbers_at_the_limits_are_accepted(systolic, diastolic):
    r = bp(systolic=systolic, diastolic=diastolic)
    assert (r.systolic, r.diastolic) == (systolic, diastolic)


@pytest.mark.parametrize("systolic", [59, 261])
def test_top_number_outside_60_to_260_is_refused(systolic):
    with pytest.raises(ValidationError):
        bp(systolic=systolic)


@pytest.mark.parametrize("diastolic", [29, 151])
def test_bottom_number_outside_30_to_150_is_refused(diastolic):
    with pytest.raises(ValidationError):
        bp(systolic=200, diastolic=diastolic)


def test_bottom_number_must_be_lower_than_the_top_number():
    assert "The bottom number must be lower than the top number." in rejected(systolic=120, diastolic=120)
    assert "The bottom number must be lower than the top number." in rejected(systolic=120, diastolic=125)


def test_whole_numbers_only():
    with pytest.raises(ValidationError):
        bp(systolic=120.5)


# ------------------------------------------------------------------ pulse
def test_pulse_is_optional():
    assert bp().pulse is None
    assert bp(pulse=None).pulse is None


@pytest.mark.parametrize("pulse", [30, 70, 220])
def test_pulse_in_range_is_accepted(pulse):
    assert bp(pulse=pulse).pulse == pulse


@pytest.mark.parametrize("pulse", [29, 221])
def test_pulse_outside_30_to_220_is_refused(pulse):
    with pytest.raises(ValidationError):
        bp(pulse=pulse)


# ------------------------------------------------------------------ time taken
def test_time_taken_defaults_to_none_so_the_server_uses_now():
    assert bp().measured_at is None


def test_a_time_in_the_past_is_accepted():
    past = datetime.now(timezone.utc) - timedelta(hours=3)
    assert bp(measured_at=past).measured_at == past


def test_a_time_a_few_seconds_ahead_is_accepted_for_clock_difference():
    almost_now = datetime.now(timezone.utc) + timedelta(seconds=20)
    assert bp(measured_at=almost_now).measured_at == almost_now


def test_a_time_in_the_future_is_refused():
    msg = rejected(measured_at=datetime.now(timezone.utc) + timedelta(minutes=10))
    assert "cannot be in the future" in msg


def test_a_naive_time_is_read_as_singapore_time_for_the_future_check():
    later_in_sg = (datetime.now(SG) + timedelta(hours=2)).replace(tzinfo=None)
    with pytest.raises(ValidationError):
        bp(measured_at=later_in_sg)


def test_the_time_can_be_sent_in_camel_case_as_the_web_app_does():
    r = BloodPressureInput.model_validate({"systolic": 118, "diastolic": 76, "measuredAt": "2020-05-01T08:10:00+08:00"})
    assert r.measured_at == datetime(2020, 5, 1, 8, 10, tzinfo=SG)


# ------------------------------------------------------------------ note
def test_note_is_optional_and_limited():
    assert bp(note="After a walk").note == "After a walk"
    with pytest.raises(ValidationError):
        bp(note="x" * 301)


# ------------------------------------------------------------------ the log endpoint's union
def test_the_log_input_union_routes_by_kind_to_blood_pressure():
    got = TypeAdapter(LogInput).validate_python({"kind": "blood_pressure", "systolic": 130, "diastolic": 85, "pulse": 72})
    assert isinstance(got, BloodPressureInput)
    assert got.pulse == 72


# ------------------------------------------------------------------ recent_bp (fake connection)
class FakeConn:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        return self

    def fetchall(self):
        return self.rows


def test_recent_bp_passes_the_user_and_the_day_window_and_returns_plain_rows():
    uid = uuid.uuid4()
    newest = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    rows = [
        {"id": uuid.uuid4(), "measured_at": newest, "systolic": 130, "diastolic": 84, "pulse": 70, "note": None},
        {"id": uuid.uuid4(), "measured_at": newest - timedelta(days=1), "systolic": 122, "diastolic": 78, "pulse": None, "note": "x"},
    ]
    conn = FakeConn(rows)
    got = recent_bp(conn, uid, 14)
    assert got == rows and all(isinstance(r, dict) for r in got)
    sql, params = conn.calls[0]
    assert params == {"u": uid, "d": 14}
    assert "deleted_at is null" in sql
    assert "order by b.recorded_at desc" in sql


def test_recent_bp_needs_at_least_one_day():
    with pytest.raises(ValueError):
        recent_bp(FakeConn([]), uuid.uuid4(), 0)


# ------------------------------------------------------------------ the HTTP routes (no database: refusals happen before any query)
def test_the_routes_refuse_bad_input_and_unknown_ids_in_plain_terms(monkeypatch):
    from fastapi.testclient import TestClient

    from app.db import logstore
    from app.main import app

    client = TestClient(app)
    # a diastolic at or above the systolic is refused by the schema (422) before the store is called
    bad = client.post("/api/v1/logs", json={"kind": "blood_pressure", "systolic": 120, "diastolic": 130})
    assert bad.status_code == 422
    # a malformed id is "not found" for read and edit (the store refuses it before it queries)
    assert client.get("/api/v1/logs/blood-pressure/not-an-id").status_code == 404
    assert client.put("/api/v1/logs/blood-pressure/not-an-id", json={"systolic": 120, "diastolic": 80}).status_code == 404

    # a save that clashes with a live reading comes back as 409 with the plain sentence the screen shows
    def clash(i):
        raise logstore.DuplicateReading()

    monkeypatch.setattr(logstore, "create_blood_pressure", clash)
    res = client.post("/api/v1/logs", json={"kind": "blood_pressure", "systolic": 120, "diastolic": 80})
    assert res.status_code == 409
    assert res.json()["detail"].startswith("You already have a reading saved at that time.")


# ------------------------------------------------------------------ the two table layouts (no database)
class Result:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row

    def fetchall(self):
        return [self.row] if self.row else []


class Scripted:
    """Answers each statement with the row of the first key found in its SQL, and records every statement."""

    def __init__(self, answers=()):
        self.answers = list(answers)
        self.sql = []

    def execute(self, sql, params=None):
        self.sql.append(sql)
        for key, row in self.answers:
            if key in sql:
                return Result(row)
        return Result(None)

    def statements_with(self, key):
        return [s for s in self.sql if key in s]


class Counting:
    """A column-count answer for the detection query, counting how many times it was asked."""

    def __init__(self, n):
        self.n = n
        self.asked = 0

    def execute(self, sql, params=None):
        self.asked += 1
        return Result({"count": self.n})


@pytest.fixture()
def table_layout(monkeypatch):
    blood_pressure.reset_cache()
    monkeypatch.setattr(blood_pressure, "columns_ready", lambda conn: True)
    yield
    blood_pressure.reset_cache()


@pytest.fixture()
def fake_db(monkeypatch):
    """Stand-in for logstore.tx and the current user, so the store runs against a scripted connection."""
    from contextlib import contextmanager

    user = uuid.uuid4()
    state = {}

    def install(conn):
        @contextmanager
        def fake_tx():
            yield conn

        monkeypatch.setattr(logstore, "tx", fake_tx)
        monkeypatch.setattr(logstore, "current_user", lambda: user)
        return conn

    state["install"] = install
    return state


def test_the_layout_is_the_table_layout_only_when_all_four_columns_exist(monkeypatch):
    blood_pressure.reset_cache()
    monkeypatch.setattr(blood_pressure, "columns_ready", REAL_COLUMNS_READY)
    assert REAL_COLUMNS_READY(Counting(4)) is True
    blood_pressure.reset_cache()
    assert REAL_COLUMNS_READY(Counting(3)) is False  # one column missing: stay on the old layout
    blood_pressure.reset_cache()
    assert REAL_COLUMNS_READY(Counting(0)) is False


def test_a_found_layout_is_remembered_but_a_missing_one_is_checked_again(monkeypatch):
    blood_pressure.reset_cache()
    monkeypatch.setattr(blood_pressure, "columns_ready", REAL_COLUMNS_READY)
    missing = Counting(0)
    assert REAL_COLUMNS_READY(missing) is False
    assert REAL_COLUMNS_READY(missing) is False
    assert missing.asked == 2  # not yet: asked again on every call
    found = Counting(4)
    blood_pressure.reset_cache()
    assert REAL_COLUMNS_READY(found) is True
    assert REAL_COLUMNS_READY(found) is True
    assert found.asked == 1  # found once, then remembered
    blood_pressure.reset_cache()


def test_the_id_column_follows_the_layout(table_layout):
    assert blood_pressure.id_column(None) == "id"


def test_the_id_column_before_the_migration(monkeypatch):
    assert blood_pressure.id_column(None) == "bronze_id"


def test_recent_bp_reads_the_table_columns_after_the_migration(table_layout):
    conn = FakeConn([])
    recent_bp(conn, uuid.uuid4(), 14)
    sql = conn.calls[-1][0]
    assert "b.pulse as pulse" in sql and "b.note as note" in sql and "b.id as id" in sql
    assert "payload" not in sql and "bronze_blood_pressure" not in sql


def test_recent_bp_reads_the_bronze_payload_before_the_migration():
    conn = FakeConn([])
    recent_bp(conn, uuid.uuid4(), 14)
    sql = conn.calls[-1][0]
    assert "payload->>'pulse'" in sql and "b.bronze_id as id" in sql


def test_get_reading_matches_the_layout_column(table_layout):
    conn = Scripted()
    blood_pressure.get_reading(conn, uuid.uuid4(), uuid.uuid4())
    assert "and b.id = %(e)s" in conn.sql[-1]


def test_get_reading_before_the_migration_matches_the_bronze_id():
    conn = Scripted()
    blood_pressure.get_reading(conn, uuid.uuid4(), uuid.uuid4())
    assert "and b.bronze_id = %(e)s" in conn.sql[-1]


def test_recent_select_for_the_recent_list_in_both_layouts(monkeypatch):
    monkeypatch.setattr(blood_pressure, "columns_ready", lambda conn: True)
    assert "b.pulse::numeric, b.note from blood_pressure_readings" in blood_pressure.recent_select(None)
    monkeypatch.setattr(blood_pressure, "columns_ready", lambda conn: False)
    assert "(bz.payload->>'pulse')::numeric, bz.payload->>'note'" in blood_pressure.recent_select(None)


def test_saving_in_the_table_layout_writes_pulse_and_note_and_returns_the_table_id(fake_db, table_layout):
    entry, bronze = uuid.uuid4(), uuid.uuid4()
    conn = fake_db["install"](Scripted([
        ("insert into bronze_blood_pressure", {"id": bronze}),
        ("insert into blood_pressure_readings", {"id": entry}),
    ]))
    when = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    saved = logstore.create_blood_pressure(BloodPressureInput(systolic=128, diastolic=82, pulse=70, measured_at=when, note=" walk "))
    assert saved["id"] == str(entry)
    insert = conn.statements_with("insert into blood_pressure_readings")[0]
    assert "pulse, note" in insert and "returning id" in insert
    assert "on conflict (user_id, recorded_at)" in insert and "id=gen_random_uuid()" in insert


def test_saving_before_the_migration_keeps_the_bronze_layout_and_returns_the_bronze_id(fake_db):
    bronze = uuid.uuid4()
    conn = fake_db["install"](Scripted([
        ("insert into bronze_blood_pressure", {"id": bronze}),
        ("insert into blood_pressure_readings", {"bronze_id": bronze}),
    ]))
    when = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    saved = logstore.create_blood_pressure(BloodPressureInput(systolic=128, diastolic=82, pulse=70, measured_at=when))
    assert saved["id"] == str(bronze)
    insert = conn.statements_with("insert into blood_pressure_readings")[0]
    assert "pulse" not in insert and "note" not in insert and "returning bronze_id" in insert


@pytest.mark.parametrize("table", [True, False])
def test_a_live_reading_at_the_same_time_is_refused_in_both_layouts(fake_db, monkeypatch, table):
    monkeypatch.setattr(blood_pressure, "columns_ready", lambda conn: table)
    fake_db["install"](Scripted([("insert into bronze_blood_pressure", {"id": uuid.uuid4()})]))  # the insert itself gives no row
    with pytest.raises(logstore.DuplicateReading):
        logstore.create_blood_pressure(BloodPressureInput(systolic=128, diastolic=82, measured_at=datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)))


def test_an_edit_in_the_table_layout_updates_the_same_row_by_its_id(fake_db, table_layout):
    entry = uuid.uuid4()
    when = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    conn = fake_db["install"](Scripted([
        ("select recorded_at from blood_pressure_readings where id", {"recorded_at": when}),
        ("insert into bronze_blood_pressure", {"id": uuid.uuid4()}),
    ]))
    kept = logstore.update_blood_pressure(str(entry), BloodPressureInput(systolic=122, diastolic=78, pulse=66, measured_at=when))
    assert kept["id"] == str(entry)
    update = conn.statements_with("update blood_pressure_readings set recorded_at")[0]
    assert "where id=%s and user_id=%s" in update and "updated_at=now()" in update
    assert not conn.statements_with("set deleted_at=now() where bronze_id")  # no soft-delete-and-reinsert
