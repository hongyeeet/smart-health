"""Adding a medicine by hand (screen H8): the request shape, the saved rows and the answer the app shows.

Each test runs inside a transaction that is rolled back. Run from services/api:  python -m pytest tests/db/test_medications_api.py -q
Needs DATABASE_URL in the private .env.
"""
import os
import sys
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

from app.api.routers import medications as api  # noqa: E402
from app.schemas.medicines import NewMedicationIn  # noqa: E402


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
def user(conn):
    return str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0])


def body(**over):
    base = {"name": "Metformin", "kind": "prescription", "strength": "500 mg", "totalQuantity": 60,
            "doses": [{"time": "08:00", "quantity": 1, "mealRelation": "after_meal"}, {"time": "20:00", "quantity": 1, "mealRelation": "after_meal"}]}
    base.update(over)
    return NewMedicationIn.model_validate(base)


def test_a_hand_typed_medicine_is_saved_and_returned_as_the_app_shows_it(conn, user):
    out = api.create_medication(conn, user, body())
    assert (out.name, out.strength, out.kind, out.times, out.with_food) == ("Metformin", "500 mg", "prescription", ["8:00 am", "8:00 pm"], True)
    assert out.badge is None and out.refill.days_left == 30 and out.refill.units_left == 60       # 60 tablets at 2 a day
    row = conn.execute("select source, frequency, total_quantity, drug_reference_id is not null from medications where id = %s", (out.id,)).fetchone()
    assert row == ("manual", 2, 60, True)                       # linked to the drug list by a name match in code
    sched = conn.execute("select dose_time::text, quantity, meal_relation::text, null from medication_schedule where medication_id = %s order by dose_time", (out.id,)).fetchall()
    assert [(s[0], s[1], s[2], s[3]) for s in sched] == [("08:00:00", Decimal("1"), "after_meal", None), ("20:00:00", Decimal("1"), "after_meal", None)]


def test_an_unlisted_name_and_every_supplement_show_as_not_checked(conn, user):
    unknown = api.create_medication(conn, user, body(name="Zorblaxine"))
    assert unknown.badge == "not_checked"
    fish = api.create_medication(conn, user, body(name="Fish oil", kind="supplement"))
    assert fish.badge == "not_checked"


def test_blank_optional_fields_become_nothing_not_empty_text(conn, user):
    out = api.create_medication(conn, user, body(strength="  ", directions=" "))
    row = conn.execute("select strength, description from medications where id = %s", (out.id,)).fetchone()
    assert row == (None, None) and out.strength == "Strength not entered"


def test_the_label_directions_are_kept_word_for_word(conn, user):
    out = api.create_medication(conn, user, body(directions="Take 1 tablet twice daily after meals"))
    assert conn.execute("select description from medications where id = %s", (out.id,)).fetchone() == ("Take 1 tablet twice daily after meals",)


def test_the_event_log_gets_the_three_events_and_no_name(conn, user):
    api.create_medication(conn, user, body(name="Private Name Pill"))
    rows = conn.execute("select event, payload::text from event_log where user_id = %s order by id", (user,)).fetchall()
    assert [r[0] for r in rows] == ["medication.created", "dose.schedule.generated"]
    assert all("Private Name Pill" not in r[1] for r in rows)


@pytest.mark.parametrize("bad", [
    {"name": ""}, {"name": "x" * 201}, {"totalQuantity": 0}, {"totalQuantity": None}, {"doses": []},
    {"doses": [{"time": "08:00", "quantity": 0}]}, {"doses": [{"time": "25:00", "quantity": 1}]},
    {"doses": [{"time": "08:00", "quantity": 1, "mealRelation": "whenever"}]}, {"kind": "magic"},
    {"doses": [{"time": "08:00", "quantity": 1}] * 7},
])
def test_bad_requests_are_refused_before_anything_is_saved(bad):
    with pytest.raises(ValidationError):
        body(**bad)


def test_the_total_supplied_is_required():
    raw = {"name": "x", "doses": [{"time": "08:00", "quantity": 1}]}
    with pytest.raises(ValidationError):
        NewMedicationIn.model_validate(raw)


def test_the_route_is_registered():
    from app.main import app
    assert "post" in app.openapi()["paths"]["/api/v1/medications"]


# --- the Meds page list -------------------------------------------------------------------------------------

from datetime import date  # noqa: E402


def test_the_list_shows_what_was_saved_oldest_first_and_nothing_hidden(conn, user):
    a = api.create_medication(conn, user, body(name="Metformin"))
    b = api.create_medication(conn, user, body(name="Fish oil", kind="supplement", doses=[{"time": "09:00", "quantity": 1}]))
    conn.execute("update medications set created_at = created_at + interval '1 minute' where id = %s", (b.id,))   # one transaction = one timestamp
    gone = api.create_medication(conn, user, body(name="Hidden one"))
    conn.execute("update medications set deleted_at = now() where id = %s", (gone.id,))
    conn.execute("update medication_schedule set deleted_at = now() where medication_id = %s", (gone.id,))
    listed = api.list_medications(conn, user, date.today())
    assert [m.name for m in listed] == ["Metformin", "Fish oil"] and [m.id for m in listed] == [a.id, b.id]
    assert listed[0].times == ["8:00 am", "8:00 pm"] and listed[0].with_food is True and listed[0].badge is None
    assert listed[1].badge == "not_checked" and listed[1].with_food is False


def test_one_persons_list_never_shows_another_persons_medicines(conn, user):
    api.create_medication(conn, user, body(name="Mine"))
    other = str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0])
    assert api.list_medications(conn, other, date.today()) == []


def test_the_supply_estimate_counts_down_from_the_start_date():
    r = api.refill_for(60, Decimal(2), date(2026, 10, 1), "manual", date(2026, 10, 11))      # 10 days at 2 a day = 20 used
    assert (r.units_left, r.days_left) == (40, 20)
    assert api.refill_for(60, Decimal(2), date(2026, 10, 1), "manual", date(2026, 12, 1)).days_left == 0     # long gone: zero, not negative
    assert api.refill_for(60, Decimal(2), date(2026, 10, 11), "manual", date(2026, 10, 1)).units_left == 60  # a future start date counts nothing


def test_an_empty_total_gives_no_estimate_and_never_fails():
    assert api.refill_for(None, Decimal(2), date(2026, 1, 1), "manual", date(2026, 10, 1)) is None


def test_the_demo_medicine_with_an_unreadable_label_has_no_total(conn):
    row = conn.execute("select total_quantity from medications where name = 'Herbal tonic (label not readable)' and source = 'demo_dataset'").fetchone()
    assert row == (None,)


def test_demo_placeholders_get_no_supply_estimate_and_zero_doses_never_divide():
    assert api.refill_for(60, Decimal(2), date(2026, 1, 1), "demo_dataset", date(2026, 10, 1)) is None
    assert api.refill_for(60, Decimal(0), date(2026, 1, 1), "manual", date(2026, 10, 1)) is None


def test_the_demo_patients_list_loads_and_shows_no_invented_supply(conn):
    mr_tan = "dc48e209-5731-5b3d-89d9-986242c54368"
    meds = api.list_medications(conn, mr_tan, date.today())
    assert len(meds) >= 6 and all(m.refill is None for m in meds) and all(m.times for m in meds)


def test_an_as_needed_medicine_has_no_times_no_reminder_and_no_supply_estimate(conn, user):
    out = api.create_medication(conn, user, body(name="Cough syrup", doses=[{"quantity": 2}]))
    assert out.as_needed and out.times == [] and out.refill is None
    listed = api.list_medications(conn, user, date.today())
    assert [(m.name, m.as_needed, m.times, m.refill) for m in listed] == [("Cough syrup", True, [], None)]
    assert conn.execute("select dose_time from medication_schedule where medication_id = %s", (out.id,)).fetchall() == [(None,)]


def test_an_as_needed_medicine_cannot_also_have_clock_times():
    with pytest.raises(ValidationError):
        body(doses=[{"quantity": 1}, {"time": "08:00", "quantity": 1}])
    with pytest.raises(ValidationError):
        body(doses=[{"time": "08:00", "quantity": 1}, {"time": "08:00", "quantity": 1}])
