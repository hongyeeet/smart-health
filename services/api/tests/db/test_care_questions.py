"""Care plan: doctor questions (open, done, removed, order) and visits of old and new kinds, against the shared database.

Each test runs inside a transaction that is rolled back, so the shared database is left untouched. Only a new, throwaway user is written.
Run from services/api:  python -m pytest tests/db/test_care_questions.py -q   (needs DATABASE_URL in .env)
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

from app.core.errors import InvalidTransition, NotFound  # noqa: E402
from app.schemas import care as S  # noqa: E402
from app.services import care as svc  # noqa: E402


@pytest.fixture()
def conn():
    load_env()
    c = psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20, row_factory=dict_row)
    try:
        yield c
    finally:
        c.rollback()
        c.close()


@pytest.fixture()
def user(conn):
    return str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()["id"])


NOW = datetime.now(timezone.utc)


def test_a_question_can_be_marked_done_and_put_back(conn, user):
    q = svc.add_question(conn, user, "Can I walk after dinner?")
    assert q["status"] == "open" and q["can_remove"] is True

    done = svc.set_question_done(conn, user, q["id"], True)
    assert done["status"] == "asked" and done["origin_label"] == "Added by you"

    back = svc.set_question_done(conn, user, q["id"], False)
    assert back["status"] == "open"


def test_marking_done_writes_an_event_with_ids_only(conn, user):
    q = svc.add_question(conn, user, "Is my blood pressure medicine due?")
    svc.set_question_done(conn, user, q["id"], True)
    row = conn.execute(
        "select event, entity_table, entity_id::text as entity_id, payload from event_log "
        "where user_id = %s and event = 'doctor_question.done'",
        (user,),
    ).fetchone()
    assert row["entity_table"] == "doctor_questions" and row["entity_id"] == q["id"]
    assert row["payload"] == {}


def test_open_questions_come_first_then_done_ones(conn, user):
    first = svc.add_question(conn, user, "First question")
    second = svc.add_question(conn, user, "Second question")
    svc.set_question_done(conn, user, second["id"], True)
    plan = svc.load_plan(conn, user, NOW)
    assert [q["text"] for q in plan["questions"]] == ["First question", "Second question"]
    assert [q["status"] for q in plan["questions"]] == ["open", "asked"]
    assert first["id"] != second["id"]


def test_a_removed_question_leaves_the_list_and_cannot_be_marked_again(conn, user):
    q = svc.add_question(conn, user, "Old question")
    svc.archive_question(conn, user, q["id"])
    assert svc.load_plan(conn, user, NOW)["questions"] == []
    with pytest.raises(InvalidTransition):
        svc.set_question_done(conn, user, q["id"], True)
    with pytest.raises(InvalidTransition):
        svc.archive_question(conn, user, q["id"])


def test_a_question_of_someone_else_is_not_found(conn, user):
    other = str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()["id"])
    q = svc.add_question(conn, other, "Not yours")
    with pytest.raises(NotFound):
        svc.set_question_done(conn, user, q["id"], True)


def test_a_done_question_can_be_removed(conn, user):
    q = svc.add_question(conn, user, "Done then removed")
    svc.set_question_done(conn, user, q["id"], True)
    assert svc.archive_question(conn, user, q["id"]) == {"id": q["id"], "status": "archived"}


def test_a_new_visit_is_saved_without_a_place(conn, user):
    when = (datetime.now(svc.TZ) + timedelta(days=10)).replace(microsecond=0)
    out = svc.add_appointment(conn, user, "hba1c_test", when, None, datetime.now(timezone.utc))
    assert out["kind"] == "hba1c_test" and out["kind_label"] == "HbA1c blood test" and out["location"] is None
    S.AppointmentOut.model_validate(out)


def test_an_old_visit_of_a_removed_kind_still_shows_on_the_plan(conn, user):
    when = datetime.now(timezone.utc) + timedelta(days=20)
    conn.execute(
        "insert into appointments (user_id, kind, status, scheduled_for, location, confirmed_by_user_at) "
        "values (%s, 'dental', 'planned', %s, 'Old clinic', now())",
        (user, when),
    )
    plan = svc.load_plan(conn, user, NOW)
    visit = plan["upcoming"][0]
    assert visit["kind"] == "dental" and visit["kind_label"] == "Dental check"
    S.CarePlan.model_validate(plan)


def test_a_suggested_visit_of_an_old_kind_can_be_confirmed_with_that_kind(conn, user):
    when = datetime.now(timezone.utc) + timedelta(days=30)
    row = conn.execute(
        "insert into appointments (user_id, kind, status, scheduled_for) values (%s, 'vaccination', 'suggested', %s) returning id::text as id",
        (user, when),
    ).fetchone()
    out = svc.add_appointment(conn, user, "vaccination", when + timedelta(days=1), row["id"], datetime.now(timezone.utc))
    assert out["status"] == "planned" and out["kind"] == "vaccination"
    with pytest.raises(InvalidTransition):
        svc.add_appointment(conn, user, "other", when, row["id"], datetime.now(timezone.utc))



def test_a_question_taken_from_the_suggestions_says_so_and_a_made_up_key_does_not(conn, user):
    q = svc.add_question(conn, user, "Are my results where they should be for me?", "results")
    assert q["origin"] == "agent_suggested" and q["origin_label"] == "Suggested by Equinox"
    other = svc.add_question(conn, user, "Can I walk after dinner?", "not-a-key")
    assert other["origin"] == "user"
