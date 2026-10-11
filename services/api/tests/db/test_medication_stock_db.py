"""The medicine warehouse against the real tables: the start value, the decrement and restore on Taken, the add and set, the list, and
the refill figure that now reads the stock. Each test runs in a transaction that is rolled back, so the shared database is untouched.

The tests skip with a message while migration 0032 is not applied to the database (the stock columns do not exist yet). Run from
services/api:  python -m pytest tests/db/test_medication_stock.py -q      (needs DATABASE_URL in the private .env)
"""
import os
import sys
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

from app.api.routers import medications as meds  # noqa: E402
from app.core.errors import InvalidTransition, NotFound, ValidationFailed  # noqa: E402
from app.schemas.medicines import NewMedicationIn  # noqa: E402
from app.services import dose_store as store  # noqa: E402
from app.services import medication_stock as ms  # noqa: E402
from app.services.medication_remove import remove_medication  # noqa: E402

TZ = store.TZ
DAY = date(2026, 10, 11)
NOT_APPLIED = ("migration 0032 is not applied to this database yet (the medications stock columns are missing), so this test is skipped. "
               "It runs once 0032 is applied.")


def at(hour, minute=0):
    return datetime(2026, 10, 11, hour, minute, tzinfo=TZ)


@pytest.fixture()
def conn():
    load_env()
    c = psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20)
    ms.reset_stock_cache()
    try:
        yield c
    finally:
        c.rollback()
        c.close()
        ms.reset_stock_cache()


@pytest.fixture()
def user(conn):
    if not ms.stock_ready(conn):
        pytest.skip(NOT_APPLIED)
    return str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0])


def add_med(conn, user, name="Metformin", quantity=1, times=("08:00",), total=60, **over):
    """A medicine saved the way the app saves it. Its schedule counts as having existed since yesterday, so today's doses are made."""
    base = {"name": name, "kind": "prescription", "strength": "500 mg", "totalQuantity": total,
            "doses": [{"time": t, "quantity": quantity, "mealRelation": "after_meal"} for t in times]}
    base.update(over)
    mid = meds.create_medication(conn, user, NewMedicationIn.model_validate(base), DAY).id
    conn.execute("update medication_schedule set created_at = %s where medication_id = %s", (at(0), mid))
    return mid


def dose_id(conn, mid, hour=8):
    return str(conn.execute("select id from medication_log where medication_id = %s and scheduled_at = %s", (mid, at(hour))).fetchone()[0])


def take(conn, user, mid, hour=8):
    """Make today's doses, then mark the one at `hour` Taken, the way the Home card does (inside its window)."""
    store.ensure_rows(conn, user, at(hour, 5))
    return store.mark_taken(conn, user, dose_id(conn, mid, hour), at(hour, 5))


def count(conn, mid):
    return conn.execute("select stock_count from medications where id = %s", (mid,)).fetchone()[0]


def stock_events(conn, user):
    return conn.execute("select event, payload from event_log where user_id = %s and event in "
                        "('medication.stock.set', 'medication.stock.added', 'medication.stock.dose') order by id", (user,)).fetchall()


def test_a_medicine_saved_with_its_pack_size_starts_at_that_count(conn, user):
    mid = add_med(conn, user, total=60)
    assert count(conn, mid) == Decimal(60)
    assert conn.execute("select stock_unit from medications where id = %s", (mid,)).fetchone()[0] == "tablets"
    assert stock_events(conn, user) == [("medication.stock.set", {"count": 60})]


def test_a_taken_dose_takes_its_amount_off_once_and_is_logged_with_a_count_only(conn, user):
    mid = add_med(conn, user, quantity=2, times=("08:00",), total=60)
    assert take(conn, user, mid) == "taken"
    assert count(conn, mid) == Decimal(58)
    assert take(conn, user, mid) == "taken"                       # saying it again changes nothing
    assert count(conn, mid) == Decimal(58)
    events = stock_events(conn, user)
    assert events[-1] == ("medication.stock.dose", {"delta": -2})
    assert all(set(p) <= {"delta", "count"} for _, p in events)   # ids and counts only: no name, no note


def test_the_count_never_goes_below_zero_and_taking_the_dose_back_restores_exactly_what_it_took(conn, user):
    mid = add_med(conn, user, quantity=2, times=("08:00",), total=60)
    ms.set_count(conn, user, mid, Decimal("1"), at(9))
    take(conn, user, mid)
    assert count(conn, mid) == Decimal(0)
    assert stock_events(conn, user)[-1] == ("medication.stock.dose", {"delta": -1})
    ms.dose_untaken(conn, user, mid, dose_id(conn, mid), at(9))
    assert count(conn, mid) == Decimal(1)
    ms.dose_untaken(conn, user, mid, dose_id(conn, mid), at(9))  # a second take-back adds nothing more
    assert count(conn, mid) == Decimal(1)


def test_a_medicine_whose_count_is_not_set_stays_not_set_when_a_dose_is_taken(conn, user):
    mid = add_med(conn, user, total=60)
    conn.execute("update medications set stock_count = null where id = %s", (mid,))
    take(conn, user, mid)
    assert count(conn, mid) is None                                # never turned into 0 or a number
    assert [e for e, _ in stock_events(conn, user) if e == "medication.stock.dose"] == []


def test_a_taken_dose_of_an_as_needed_medicine_changes_no_count(conn, user):
    mid = add_med(conn, user, times=(None,), total=10, name="Paracetamol")
    assert conn.execute("select as_needed from medications where id = %s", (mid,)).fetchone()[0] is True
    assert count(conn, mid) is None                                 # not tracked at all when saved
    conn.execute("update medications set stock_count = 5 where id = %s", (mid,))
    ms.dose_taken(conn, user, mid, uuid.uuid4(), Decimal(1), at(8))  # even with a count in place, an as-needed dose changes nothing
    assert count(conn, mid) == Decimal(5)


def test_i_bought_more_adds_and_change_the_number_sets_both_are_logged(conn, user):
    mid = add_med(conn, user, total=20)
    ms.add_count(conn, user, mid, Decimal(30), at(10))
    assert count(conn, mid) == Decimal(50)
    ms.set_count(conn, user, mid, Decimal(12), at(11))
    assert count(conn, mid) == Decimal(12)
    events = stock_events(conn, user)
    assert events[-2:] == [("medication.stock.added", {"delta": 30}), ("medication.stock.set", {"count": 12})]


def test_adding_needs_a_count_to_add_to_and_the_number_is_0_to_10000(conn, user):
    mid = add_med(conn, user, total=20)
    conn.execute("update medications set stock_count = null where id = %s", (mid,))
    with pytest.raises(InvalidTransition):
        ms.add_count(conn, user, mid, Decimal(5), at(10))
    with pytest.raises(ValidationFailed):
        ms.set_count(conn, user, mid, Decimal(10001), at(10))
    ms.set_count(conn, user, mid, Decimal(9000), at(10))
    with pytest.raises(ValidationFailed):
        ms.add_count(conn, user, mid, Decimal(2000), at(10))       # 9000 + 2000 would be 11000: over the largest allowed count


def test_another_persons_medicine_and_a_removed_one_are_not_found(conn, user):
    mid = add_med(conn, user, total=20)
    other = str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0])
    with pytest.raises(NotFound):
        ms.set_count(conn, other, mid, Decimal(5), at(10))
    remove_medication(conn, user, mid)
    with pytest.raises(NotFound):
        ms.set_count(conn, user, mid, Decimal(5), at(10))
    assert ms.stock_list(conn, user) == []


def test_the_list_gives_days_left_status_and_the_full_mark_of_the_bar(conn, user):
    mid = add_med(conn, user, quantity=2, times=("08:00", "20:00"), total=60)     # four a day
    rows = {str(r["id"]): r for r in ms.stock_list(conn, user)}
    r = rows[mid]
    assert (r["stock_count"], r["days_left"], r["status"], r["full_count"], r["pack_size"]) == (Decimal(60), 15, "ok", Decimal(60), 60)
    ms.set_count(conn, user, mid, Decimal(24), at(10))                             # six days at four a day
    r = {str(x["id"]): x for x in ms.stock_list(conn, user)}[mid]
    assert (r["days_left"], r["status"], r["full_count"]) == (6, "low", Decimal(24))


def test_the_refill_figure_reads_the_stock_when_it_is_set_and_the_estimate_otherwise(conn, user):
    mid = add_med(conn, user, quantity=2, times=("08:00", "20:00"), total=60)
    listed = {m.id: m for m in meds.list_medications(conn, user, DAY)}
    assert listed[mid].refill_source == "stock" and listed[mid].refill.units_left == 60 and listed[mid].refill.days_left == 15
    conn.execute("update medications set stock_count = null where id = %s", (mid,))
    listed = {m.id: m for m in meds.list_medications(conn, user, DAY)}
    assert listed[mid].refill_source == "estimate"                                  # the old pack-date estimate, labelled as such


def test_with_the_columns_treated_as_missing_the_medicines_still_list_and_doses_still_mark(conn, user, monkeypatch):
    """The degraded path on the real SQL: the list falls back to the estimate, and a dose is still marked Taken and touches no count."""
    mid = add_med(conn, user, quantity=1, times=("08:00",), total=30)
    monkeypatch.setattr(ms, "stock_ready", lambda c: False)
    listed = {m.id: m for m in meds.list_medications(conn, user, DAY)}
    assert listed[mid].refill_source == "estimate"
    assert take(conn, user, mid) == "taken"
    assert count(conn, mid) == Decimal(30)
