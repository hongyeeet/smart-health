"""Today's doses, "Taken" and "Why was it not confirmed?" against the real tables, with a fixed clock.

Everything runs inside one transaction that is rolled back, so the shared database is left untouched.
Run from services/api:  python -m pytest tests/db/test_dose_store.py -q       Needs DATABASE_URL in the private .env.
"""
import os
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

from app.api.routers import doses as route  # noqa: E402
from app.api.routers import medications as meds  # noqa: E402
from app.core.errors import InvalidTransition, NotFound, ValidationFailed  # noqa: E402
from app.db import logstore  # noqa: E402
from app.schemas.medicines import NewMedicationIn  # noqa: E402
from app.services import dose_store as store  # noqa: E402

TZ = store.TZ
MR_TAN = "dc48e209-5731-5b3d-89d9-986242c54368"


def at(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute, tzinfo=TZ)


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


def add_med(conn, user, name="Metformin 500 mg", times=("08:00", "20:00"), created=None, **over):
    base = {"name": name, "kind": "prescription", "strength": "500 mg", "totalQuantity": 60, "doses": [{"time": t, "quantity": 1, "mealRelation": "after_meal"} for t in times]}
    base.update(over)
    mid = meds.create_medication(conn, user, NewMedicationIn.model_validate(base), meds.datetime_today()).id
    # the schedule counts as having existed since long ago unless a test says otherwise
    conn.execute("update medication_schedule set created_at = %s where medication_id = %s", (created or at(1, 0), mid))
    return mid


def test_rows_are_made_for_today_and_tomorrow_only_where_somebody_could_still_answer(conn, user):
    add_med(conn, user)
    assert store.ensure_rows(conn, user, at(8, 14)) == 3          # 8 am today is long over (window closed at 10 am): not made up
    assert store.ensure_rows(conn, user, at(8, 14)) == 0          # asking again changes nothing
    rows = conn.execute("select scheduled_at, status::text from medication_log where user_id = %s order by scheduled_at", (user,)).fetchall()
    assert [(r[0].astimezone(TZ).day, r[0].astimezone(TZ).hour, r[1]) for r in rows] == [(8, 20, "pending"), (9, 8, "pending"), (9, 20, "pending")]


def test_a_dose_before_the_medicine_was_added_is_never_made_up(conn, user):
    add_med(conn, user, created=at(8, 15))
    store.ensure_rows(conn, user, at(8, 16))
    hours = [r[0].astimezone(TZ).hour for r in conn.execute("select scheduled_at from medication_log where user_id = %s and scheduled_at < %s", (user, at(9, 0))).fetchall()]
    assert hours == [20]                                          # 8 am today was before it existed


def test_an_as_needed_medicine_has_no_doses(conn, user):
    mid = meds.create_medication(conn, user, NewMedicationIn.model_validate(
        {"name": "Cough syrup", "kind": "otc", "totalQuantity": 1, "doses": [{"time": None, "quantity": 5}]}), meds.datetime_today()).id
    assert mid and store.ensure_rows(conn, user, at(8, 14)) == 0
    assert store.today(conn, user, at(8, 14)) == {"has_medicines": False, "due": [], "unconfirmed": [], "taken_today": 0, "next": None}


def test_the_next_dose_is_shown_until_its_window_opens_then_it_is_due(conn, user):
    add_med(conn, user)
    afternoon = store.today(conn, user, at(8, 14))
    assert afternoon["due"] == [] and afternoon["unconfirmed"] == [] and afternoon["next"] == {"title": "Metformin, 1 Tab", "when": "today at 8:00 pm"}
    evening = store.today(conn, user, at(8, 18, 5))               # the window opens at 6 pm
    assert [(x["title"], x["time"], x["with_food"]) for x in evening["due"]] == [("Metformin, 1 Tab", "8:00 pm", True)]
    assert evening["next"]["when"] == "tomorrow at 8:00 am"


def test_taken_marks_the_dose_and_asking_twice_changes_nothing(conn, user):
    add_med(conn, user)
    due = store.today(conn, user, at(8, 20, 10))["due"][0]
    assert store.mark_taken(conn, user, due["id"], at(8, 20, 10)) == "taken"
    first = conn.execute("select status::text, taken_at from medication_log where id = %s", (due["id"],)).fetchone()
    assert store.mark_taken(conn, user, due["id"], at(8, 20, 40)) == "taken"
    assert conn.execute("select taken_at from medication_log where id = %s", (due["id"],)).fetchone()[0] == first[1]
    t = store.today(conn, user, at(8, 20, 45))
    assert t["due"] == [] and t["taken_today"] == 1 and t["next"]["when"] == "tomorrow at 8:00 am"
    ev = conn.execute("select payload from event_log where user_id = %s and event = 'dose.taken'", (user,)).fetchall()
    assert len(ev) == 1 and ev[0][0]["late"] is False


def test_a_dose_taken_over_an_hour_late_is_marked_late_in_the_log(conn, user):
    add_med(conn, user)
    due = store.today(conn, user, at(8, 21, 30))["due"][0]
    store.mark_taken(conn, user, due["id"], at(8, 21, 30))
    assert conn.execute("select payload from event_log where user_id = %s and event = 'dose.taken'", (user,)).fetchone()[0]["late"] is True


def test_taken_is_refused_before_the_window_opens_and_after_an_answer(conn, user):
    add_med(conn, user)
    store.ensure_rows(conn, user, at(8, 14))
    row = conn.execute("select id from medication_log where user_id = %s and scheduled_at = %s", (user, at(8, 20))).fetchone()
    with pytest.raises(InvalidTransition):
        store.mark_taken(conn, user, str(row[0]), at(8, 14))
    store.today(conn, user, at(8, 23))
    store.save_reason(conn, user, str(row[0]), "forgot", None, at(8, 23))
    with pytest.raises(InvalidTransition):
        store.mark_taken(conn, user, str(row[0]), at(8, 23, 5))


def test_a_dose_nobody_answered_is_shown_as_not_confirmed_with_a_plain_label(conn, user):
    add_med(conn, user)
    store.today(conn, user, at(8, 19))                            # the row is made while the window is open
    later = store.today(conn, user, at(8, 22, 30))
    assert later["due"] == [] and [(u["when_label"], u["title"]) for u in later["unconfirmed"]] == [("This evening's dose", "Metformin, 1 Tab")]
    tomorrow = store.today(conn, user, at(9, 9, 0))
    assert [u["when_label"] for u in tomorrow["unconfirmed"]] == ["Yesterday's evening dose"]


def test_nothing_is_flagged_when_every_dose_is_answered_or_too_old(conn, user):
    add_med(conn, user)
    store.today(conn, user, at(8, 19))
    assert store.today(conn, user, at(12, 9))["unconfirmed"] == []         # days later: no longer asked about


def test_a_reason_turns_the_dose_into_missed_and_keeps_the_note_out_of_the_logs(conn, user):
    add_med(conn, user)
    store.today(conn, user, at(8, 19))
    did = store.today(conn, user, at(8, 23))["unconfirmed"][0]["id"]
    assert store.save_reason(conn, user, did, "forgot", "  I was out with friends  ", at(8, 23)) == "missed"
    row = conn.execute("select status::text, miss_reason::text, miss_note, taken_at from medication_log where id = %s", (did,)).fetchone()
    assert row == ("missed", "forgot", "I was out with friends", None)
    ev = conn.execute("select payload from event_log where user_id = %s and event = 'dose.reason.saved'", (user,)).fetchone()[0]
    assert ev["reason"] == "forgot" and ev["has_note"] is True and "friends" not in str(ev)
    assert store.today(conn, user, at(8, 23, 5))["unconfirmed"] == []
    with pytest.raises(InvalidTransition):
        store.save_reason(conn, user, did, "other", None, at(8, 23, 6))      # already answered


def test_took_it_but_forgot_to_log_counts_as_taken(conn, user):
    add_med(conn, user)
    store.today(conn, user, at(8, 19))
    did = store.today(conn, user, at(8, 23))["unconfirmed"][0]["id"]
    assert store.save_reason(conn, user, did, "took_it", None, at(8, 23)) == "taken"
    assert conn.execute("select status::text, taken_at = scheduled_at, miss_reason from medication_log where id = %s", (did,)).fetchone() == ("taken", True, None)


def test_side_effects_also_adds_a_doctor_question(conn, user):
    add_med(conn, user)
    store.today(conn, user, at(8, 19))
    did = store.today(conn, user, at(8, 23))["unconfirmed"][0]["id"]
    store.save_reason(conn, user, did, "side_effects", None, at(8, 23))
    q = conn.execute("select text, origin, status from doctor_questions where user_id = %s", (user,)).fetchall()
    assert q == [("I missed a dose of Metformin because of side effects. Can we talk about them?", "agent_suggested", "open")]


def test_a_reason_is_refused_while_the_dose_can_still_be_taken_or_when_it_is_not_a_reason(conn, user):
    add_med(conn, user)
    due = store.today(conn, user, at(8, 20, 5))["due"][0]
    with pytest.raises(InvalidTransition):
        store.save_reason(conn, user, due["id"], "forgot", None, at(8, 20, 5))
    with pytest.raises(ValidationFailed):
        store.save_reason(conn, user, due["id"], "because", None, at(8, 23))


def test_someone_elses_dose_is_not_found(conn, user):
    other = str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0])
    add_med(conn, other)
    did = store.today(conn, other, at(8, 20, 5))["due"][0]["id"]
    for call in (lambda: store.mark_taken(conn, user, did, at(8, 20, 5)), lambda: store.save_reason(conn, user, did, "forgot", None, at(8, 23)),
                 lambda: store.mark_taken(conn, user, "not-a-uuid", at(8, 20, 5))):
        with pytest.raises(NotFound):
            call()


def test_the_demo_patient_is_not_given_missed_doses_for_days_nobody_could_answer(conn):
    t = store.today(conn, MR_TAN, at(8, 14))                       # his record ends on 1 October
    assert t["unconfirmed"] == [] and t["due"] == [] and t["next"] is not None          # the exact next dose depends on what was tapped in the live data
    assert store.today(conn, MR_TAN, at(8, 14, 1))["has_medicines"] is True


def test_the_routes_turn_refusals_into_plain_http_errors(conn, user, monkeypatch):
    @contextmanager
    def fake_tx():
        yield conn

    monkeypatch.setattr(logstore, "tx", fake_tx)
    monkeypatch.setattr(logstore, "current_user", lambda: uuid.UUID(user))
    monkeypatch.setattr(route, "_now", lambda: at(8, 14))
    add_med(conn, user)
    out = route._today()
    assert out.has_medicines and out.next.when == "today at 8:00 pm" and out.due == []
    did = str(conn.execute("select id from medication_log where user_id = %s and scheduled_at = %s", (user, at(8, 20))).fetchone()[0])
    with pytest.raises(HTTPException) as e:
        route._taken(did)
    assert e.value.status_code == 409 and "not time" in e.value.detail
    with pytest.raises(HTTPException) as e2:
        route._taken(str(uuid.uuid4()))
    assert e2.value.status_code == 404
    monkeypatch.setattr(route, "_now", lambda: at(8, 20, 5) + timedelta(hours=0))
    assert route._taken(did).status == "taken"
