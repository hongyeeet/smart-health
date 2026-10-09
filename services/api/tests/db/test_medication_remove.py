"""Removing a medicine (Meds page): deleted_at is filled in, the app stops showing it everywhere, and its history is kept.

Everything runs inside one transaction that is rolled back, so the shared database is left untouched.
Run from services/api:  python -m pytest tests/db/test_medication_remove.py -q       Needs DATABASE_URL in the private .env.
"""
import os
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import psycopg
import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

from app.api.routers import med_explain  # noqa: E402
from app.api.routers import medications as api  # noqa: E402
from app.core.errors import NotFound  # noqa: E402
from app.db import logstore  # noqa: E402
from app.schemas.medicines import NewMedicationIn  # noqa: E402
from app.services import calendar_sync, clash_store, dose_store  # noqa: E402
from app.services.medication_remove import remove_medication  # noqa: E402

NOW = datetime(2026, 10, 8, 19, 0, tzinfo=dose_store.TZ)


@pytest.fixture()
def conn():
    load_env()
    c = psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20)
    try:
        yield c
    finally:
        c.rollback()
        c.close()


@pytest.fixture()
def user(conn, monkeypatch):
    uid = str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0])

    @contextmanager
    def fake_tx():
        yield conn

    monkeypatch.setattr(logstore, "tx", fake_tx)
    monkeypatch.setattr(logstore, "current_user", lambda: uuid.UUID(uid))
    return uid


def add(conn, user, name, times=("08:00", "20:00")):
    return api.create_medication(conn, user, NewMedicationIn.model_validate(
        {"name": name, "kind": "prescription", "totalQuantity": 30, "startDate": "2026-10-01", "doses": [{"time": t, "quantity": 1} for t in times]}),
        api.datetime_today()).id


def count(conn, sql, *p):
    return conn.execute(sql, p).fetchone()[0]


def test_removing_fills_in_deleted_at_and_the_app_stops_showing_it_everywhere(conn, user):
    keep, gone, clari = add(conn, user, "Metformin 500 mg"), add(conn, user, "Atorvastatin 20 mg"), add(conn, user, "Clarithromycin 500 mg")
    dose_store.today(conn, user, NOW)
    clash_store.save_alerts(conn, user, clash_store.database_pairs(conn, clash_store.list_medicines(conn, user)), [], [], None)
    assert len(api.list_medications(conn, user, api.datetime_today())) == 3 and len(clash_store.list_open(conn, user)) == 1
    counts = remove_medication(conn, user, gone)
    assert counts == {"dose_times": 2}
    assert count(conn, "select count(*) from medications where id = %s and deleted_at is not null", gone) == 1          # the row stays, marked removed
    assert {m.id for m in api.list_medications(conn, user, api.datetime_today())} == {keep, clari}                       # the Meds list skips it
    assert all(gone not in str(x) for x in dose_store.today(conn, user, NOW)["due"] + dose_store.today(conn, user, NOW)["unconfirmed"])
    assert {m["id"] for m in clash_store.list_medicines(conn, user)} == {keep, clari}                                    # the clash check skips it
    assert clash_store.list_open(conn, user) == []                                                                     # and so does the box
    with pytest.raises(NotFound):
        calendar_sync.plan(conn, user, gone, NOW)
    with pytest.raises(HTTPException) as e:
        med_explain._detail(gone)
    assert e.value.status_code == 404
    assert count(conn, "select count(*) from medication_schedule where medication_id = %s and deleted_at is not null", gone) == 2


def test_the_dose_history_the_original_entry_and_the_other_medicines_are_kept(conn, user):
    keep, gone = add(conn, user, "Metformin 500 mg"), add(conn, user, "Secretdrug 5 mg")
    dose_store.today(conn, user, NOW)
    before = count(conn, "select count(*) from medication_log where medication_id = %s", gone)
    bronze = conn.execute("select bronze_id from medications where id = %s", (gone,)).fetchone()[0]
    assert before > 0
    remove_medication(conn, user, gone)
    assert count(conn, "select count(*) from medication_log where medication_id = %s", gone) == before                   # adherence history is not lost
    assert count(conn, "select count(*) from bronze_medication where id = %s", bronze) == 1
    assert count(conn, "select count(*) from medications where id = %s and deleted_at is null", keep) == 1
    assert count(conn, "select count(*) from medication_schedule where medication_id = %s and deleted_at is null", keep) == 2
    ev = conn.execute("select payload from event_log where user_id = %s and event = 'medication.removed'", (user,)).fetchall()
    assert len(ev) == 1 and "Secretdrug" not in str(ev[0][0]) and ev[0][0]["dose_times"] == 2


def test_the_route_removes_it_and_a_second_try_is_not_found(conn, user):
    mid = add(conn, user, "Metformin 500 mg")
    assert api._remove(mid) == {"removed": True}
    assert api._list() == []
    with pytest.raises(HTTPException) as e:
        api._remove(mid)
    assert e.value.status_code == 404


def test_the_same_medicine_can_be_added_again_after_it_was_removed(conn, user):
    first = add(conn, user, "Metformin 500 mg")
    remove_medication(conn, user, first)
    second = add(conn, user, "Metformin 500 mg")
    assert [m.id for m in api.list_medications(conn, user, api.datetime_today())] == [second] and second != first


def test_someone_elses_medicine_cannot_be_removed(conn, user):
    other = str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0])
    theirs = add(conn, other, "Metformin 500 mg")
    with pytest.raises(NotFound):
        remove_medication(conn, user, theirs)
    with pytest.raises(HTTPException) as e:
        api._remove(theirs)
    assert e.value.status_code == 404
    assert count(conn, "select count(*) from medications where id = %s and deleted_at is null", theirs) == 1


def test_a_bad_id_is_not_found(conn, user):
    with pytest.raises(HTTPException) as e:
        api._remove("not-a-uuid")
    assert e.value.status_code == 404
