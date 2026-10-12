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
    row = conn.execute("select source, frequency, total_quantity, drug_reference_id is null from medications where id = %s", (out.id,)).fetchone()
    assert row == ("manual", 2, 60, True)                       # linked to the drug list by a name match in code
    sched = conn.execute("select dose_time::text, quantity, meal_relation::text, null from medication_schedule where medication_id = %s order by dose_time", (out.id,)).fetchall()
    assert [(s[0], s[1], s[2], s[3]) for s in sched] == [("08:00:00", Decimal("1"), "after_meal", None), ("20:00:00", Decimal("1"), "after_meal", None)]


def test_only_supplements_and_herbal_products_say_not_checked(conn, user):
    unknown = api.create_medication(conn, user, body(name="Zorblaxine"))
    assert unknown.badge is None                       # nothing is matched to a medicine list yet, so no claim either way
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
    # a known pack size also writes a stock event (counts only); it is not part of what this test is about
    assert [r[0] for r in rows if not r[0].startswith("medication.stock.")] == ["medication.created", "dose.schedule.generated"]
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


def test_the_demo_patients_list_shows_supply_from_the_counts_in_hand(conn):
    """Mr Tan's medicines were given tablet counts on 2026-10-12 (scripts/seed_mr_tan_stock.py), so the "may run out" figure now comes from
    the real count ('stock'), not the pack-date estimate: Metformin has 4 tablets at 2 a day, about 2 days. A finished course has no supply."""
    mr_tan = "dc48e209-5731-5b3d-89d9-986242c54368"
    meds = {m.name: m for m in api.list_medications(conn, mr_tan, date(2026, 10, 8))}
    assert len(meds) >= 6 and all(m.times for m in meds.values())
    assert [(meds[n].refill.days_left, meds[n].refill.units_left, meds[n].refill_source) for n in ("Metformin 500 mg", "Amlodipine 5 mg", "Atorvastatin 20 mg", "Fish oil")] \
        == [(2, 4, "stock"), (23, 23, "stock"), (17, 17, "stock"), (41, 41, "stock")]
    assert meds["Clarithromycin 500 mg"].refill is None and str(meds["Clarithromycin 500 mg"].end_date) == "2026-09-19"      # a finished course: no supply, and its end date is sent


def test_a_pack_start_date_counts_from_that_day_not_from_when_the_medicine_began():
    r = api.refill_for(60, Decimal(2), date(2021, 4, 11), "demo_dataset", date(2026, 10, 8), pack_start=date(2026, 9, 14))
    assert (r.days_left, r.units_left) == (6, 12)
    assert api.refill_for(60, Decimal(2), date(2021, 4, 11), "demo_dataset", date(2026, 10, 8)) is None      # placeholder total, no pack start
    assert api.refill_for(60, Decimal(2), date(2021, 4, 11), "manual", date(2026, 10, 8), pack_start=date(2026, 10, 6)).units_left == 56



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


def test_an_old_label_date_does_not_make_a_new_pack_look_finished():
    # Paracetamol: label dated 13 Apr, 30 tablets, 8 a day. Counted from the label the pack was finished in April; the person added it on 8 Oct.
    old = api.refill_for(30, Decimal(8), date(2026, 4, 13), "scan", date(2026, 10, 9), None, date(2026, 10, 8))
    assert (old.days_left, old.units_left) == (2, 22)                       # counted from the day it was added: 30 - 8 = 22 left
    assert api.refill_for(30, Decimal(8), date(2026, 4, 13), "scan", date(2026, 10, 9)).units_left == 0           # no added date known: the plain count


def test_a_recent_label_date_is_still_the_start_of_the_count():
    r = api.refill_for(60, Decimal(2), date(2026, 10, 1), "scan", date(2026, 10, 9), None, date(2026, 10, 8))
    assert (r.days_left, r.units_left) == (22, 44)                          # 8 days at 2 a day (16 tablets) counted from the label, not from the day it was added


def test_a_pack_that_is_used_up_even_counting_from_the_day_it_was_added_still_says_zero():
    r = api.refill_for(30, Decimal(8), date(2026, 4, 13), "scan", date(2026, 10, 20), None, date(2026, 10, 8))
    assert (r.days_left, r.units_left) == (0, 0)


def test_a_pack_start_date_is_never_overridden_by_the_added_date():
    r = api.refill_for(60, Decimal(2), date(2021, 4, 11), "demo_dataset", date(2026, 10, 8), date(2026, 9, 14), date(2026, 10, 1))
    assert (r.days_left, r.units_left) == (6, 12)


def test_the_as_needed_column_is_saved_and_decides_reminders_and_refill(conn, user):
    daily = api.create_medication(conn, user, body(name="Metformin"))
    needed = api.create_medication(conn, user, body(name="Paracetamol", doses=[{"time": None, "quantity": 2, "mealRelation": "na"}]))
    rows = dict(conn.execute("select name, as_needed from medications where user_id = %s", (user,)).fetchall())
    assert rows == {"Metformin": False, "Paracetamol": True}
    assert daily.as_needed is False and daily.refill is not None
    assert needed.as_needed is True and needed.times == [] and needed.refill is None          # no refill estimate for a medicine taken when needed
    listed = {m.name: m for m in api.list_medications(conn, user, date(2026, 10, 9))}
    assert listed["Paracetamol"].as_needed and listed["Paracetamol"].refill is None and listed["Metformin"].refill is not None


def test_the_column_alone_makes_a_medicine_only_when_needed_even_if_it_still_has_clock_times(conn, user):
    mid = api.create_medication(conn, user, body(name="Cetirizine")).id
    assert api.list_medications(conn, user, date(2026, 10, 9))[0].refill is not None
    conn.execute("update medications set as_needed = true where id = %s", (mid,))
    m = api.list_medications(conn, user, date(2026, 10, 9))[0]
    assert m.as_needed and m.refill is None


def test_a_scan_confirmed_as_only_when_needed_keeps_one_entry_with_no_time(conn, user):
    from app.services import scan_api
    ex = {"review_mode": "confirm", "reasons": [], "items": [{"item_type": "prescription_label", "fields": {
        "name": {"value": "PARACETAMOL"}, "dose_amount": {"value": "2"}, "times_per_day": {"value": "4"},
        "directions": {"value": "TAKE 2 TAB/S 4 times a day FOR FEVER/PAIN"}, "total_quantity": {"value": "30"}}}]}
    entry = scan_api.build_confirmed(ex, {}, ["08:00", "12:00"], None, date(2026, 10, 9), True)
    from app.services.scan_store import confirm_medication
    mid = confirm_medication(conn, user, entry)
    assert conn.execute("select as_needed, frequency from medications where id = %s", (mid,)).fetchone() == (True, 1)
    assert conn.execute("select dose_time from medication_schedule where medication_id = %s", (mid,)).fetchall() == [(None,)]
