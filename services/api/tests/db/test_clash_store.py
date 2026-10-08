"""The medicine clash check against the real tables: the drug-pair rules, saving alerts, and the pipeline with a fake AI.

Everything runs inside one transaction that is rolled back, so the shared database is left untouched.
Run from services/api:  python -m pytest tests/db/test_clash_store.py -q       Needs DATABASE_URL in the private .env.
"""
import os
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

import psycopg
import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

from app.agents import clash_checker as ck  # noqa: E402
from app.agents import clash_pipeline as pipe  # noqa: E402
from app.api.routers import interactions as route  # noqa: E402
from app.api.routers import medications as meds  # noqa: E402
from app.core.errors import NotFound  # noqa: E402
from app.db import logstore  # noqa: E402
from app.llm.vertex import WebSource  # noqa: E402
from app.schemas.medicines import NewMedicationIn  # noqa: E402
from app.services import clash_store as store  # noqa: E402
from app.services import usage  # noqa: E402

PAGES = [WebSource("drugs.com", "https://vertexaisearch.cloud.google.com/r/1")]


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
    monkeypatch.setattr(usage, "allowed", lambda provider: True)
    monkeypatch.setattr(usage, "record", lambda *a, **k: None)
    pipe._running.clear()
    pipe._last_failed.clear()
    return uid


def add(conn, user, name, kind="prescription", strength=None, start="2024-01-01"):
    mid = meds.create_medication(conn, user, NewMedicationIn.model_validate(
        {"name": name, "kind": kind, "strength": strength, "totalQuantity": 30, "startDate": start,
         "doses": [{"time": "08:00", "quantity": 1}]}), meds.datetime_today()).id
    return mid


def fake_ai(monkeypatch, outcome):
    calls = []

    def _ai(medicines):
        calls.append([m.name for m in medicines])
        return outcome(medicines) if callable(outcome) else outcome

    monkeypatch.setattr(pipe, "_ai", _ai)
    return calls


def ok(*pairs, sources=PAGES):
    return ck.ClashOutcome(status="done", pairs=[ck.AiPair(a, b, s) for a, b, s in pairs], sources=list(sources), model_id="m", prompt_version="2",
                           input_tokens=10, output_tokens=5)


# ------------------------------------------------------------------ the drug-pair rules
def test_the_rules_find_the_demo_pair_by_name_in_either_order(conn, user):
    atorva = add(conn, user, "Atorvastatin 20 mg")
    clari = add(conn, user, "Clarithromycin 500 mg", start="2026-09-13")
    found = store.database_pairs(conn, store.list_medicines(conn, user))
    assert [(p.a, p.b) for p in found] == [(atorva, clari)] and found[0].source_url.startswith("https://api.fda.gov/")


def test_a_medicine_that_matches_no_rule_or_only_a_brand_name_is_not_flagged_by_the_rules(conn, user):
    add(conn, user, "Metformin 500 mg")
    add(conn, user, "Amlodipine 5 mg")
    add(conn, user, "CRESTOR", strength="10 mg")                # a brand name with no generic in it: the AI half covers it
    add(conn, user, "Fish oil", kind="supplement")
    assert store.database_pairs(conn, store.list_medicines(conn, user)) == []


def test_names_match_whole_words_only(conn, user):
    add(conn, user, "Atorvastatin 20 mg")
    add(conn, user, "Superclarithromycinx")                     # contains the word inside a longer one: not a match
    assert store.database_pairs(conn, store.list_medicines(conn, user)) == []


def test_a_medicine_already_linked_to_a_drug_keeps_its_link(conn, user):
    atorva = add(conn, user, "My cholesterol tablet")
    clari = add(conn, user, "My antibiotic")
    ref = {n: str(i) for i, n in conn.execute("select id, generic_name from drug_reference where generic_name in ('atorvastatin','clarithromycin')")}
    conn.execute("update medications set drug_reference_id = %s where id = %s", (ref["atorvastatin"], atorva))
    conn.execute("update medications set drug_reference_id = %s where id = %s", (ref["clarithromycin"], clari))
    assert len(store.database_pairs(conn, store.list_medicines(conn, user))) == 1


def test_medicines_are_listed_in_the_order_they_were_started(conn, user):
    add(conn, user, "Newer", start="2026-01-01")
    add(conn, user, "Older", start="2020-01-01")
    assert [m["name"] for m in store.list_medicines(conn, user)] == ["Older", "Newer"]


# ------------------------------------------------------------------ saving alerts
def test_one_alert_per_pair_whichever_order_and_the_ai_reason_is_not_overwritten_by_the_database(conn, user):
    atorva = add(conn, user, "Atorvastatin 20 mg", strength="20 mg")
    clari = add(conn, user, "Clarithromycin 500 mg")
    meds_ = store.list_medicines(conn, user)
    dbp = store.database_pairs(conn, meds_)
    assert store.save_alerts(conn, user, dbp, [], [], None) == {"new": 1, "updated": 0}
    assert store.save_alerts(conn, user, [], [(clari, atorva, "Clarithromycin raises the level of Atorvastatin.")], [{"title": "drugs.com", "url": "https://x/1"}], "m") \
        == {"new": 0, "updated": 1}
    again = store.save_alerts(conn, user, dbp, [], [], None)                 # the database finds it again: the AI reason stays
    row = conn.execute("select origin, summary, interaction_rule_id is not null, model_id, sources from interaction_alerts where user_id = %s", (user,)).fetchall()
    assert again == {"new": 0, "updated": 1} and len(row) == 1
    assert row[0][:4] == ("both", "Clarithromycin raises the level of Atorvastatin.", True, "m")
    assert [s["title"] for s in row[0][4]] == ["Drug label information (openFDA)", "drugs.com"]


def test_an_ai_only_flag_is_saved_with_its_pages_and_a_neutral_reason_when_empty(conn, user):
    a, b = add(conn, user, "CRESTOR"), add(conn, user, "Clarithromycin 500 mg")
    store.save_alerts(conn, user, [], [(a, b, "")], [{"title": "nhs.uk", "url": "https://x/2"}], "m")
    row = conn.execute("select origin, summary, interaction_rule_id from interaction_alerts where user_id = %s", (user,)).fetchone()
    assert row == ("ai", "These two medicines may interact.", None)


def test_the_patient_message_is_the_fixed_wording_and_never_says_stop(conn, user):
    atorva, clari = add(conn, user, "Atorvastatin", strength="20 mg"), add(conn, user, "Clarithromycin 500 mg")
    store.save_alerts(conn, user, store.database_pairs(conn, store.list_medicines(conn, user)), [], [], None)
    [a] = store.list_open(conn, user)
    assert a["text"] == "Possible interaction between Atorvastatin 20 mg and Clarithromycin 500 mg. Please check with your pharmacist or doctor before continuing." \
        or a["text"] == "Possible interaction between Clarithromycin 500 mg and Atorvastatin 20 mg. Please check with your pharmacist or doctor before continuing."
    assert "stop" not in a["text"].lower() and "safe" not in a["text"].lower() and atorva and clari


def test_a_medicine_removed_from_the_list_takes_its_alert_with_it(conn, user):
    atorva, clari = add(conn, user, "Atorvastatin 20 mg"), add(conn, user, "Clarithromycin 500 mg")
    store.save_alerts(conn, user, store.database_pairs(conn, store.list_medicines(conn, user)), [], [], None)
    conn.execute("update medications set deleted_at = now() where id = %s", (clari,))
    assert store.list_open(conn, user) == [] and atorva


# ------------------------------------------------------------------ the pipeline
def test_adding_the_second_medicine_checks_both_and_the_box_appears_only_when_something_may_clash(conn, user, monkeypatch):
    calls = fake_ai(monkeypatch, lambda ms: ok())
    add(conn, user, "Metformin 500 mg")
    assert pipe.check_user(user)["medicines"] == 1 and calls == []                      # one medicine: nothing to compare
    add(conn, user, "Amlodipine 5 mg")
    r = pipe.check_user(user)
    assert (r["medicines"], r["database"], r["ai"], r["new"]) == (2, 0, 0, 0) and len(calls) == 1 and store.list_open(conn, user) == []
    add(conn, user, "Clarithromycin 500 mg", start="2026-09-13")
    r = pipe.check_user(user)
    assert (r["medicines"], r["database"], r["new"]) == (3, 1, 1) and len(store.list_open(conn, user)) == 1       # Clarithromycin + Amlodipine


def test_the_ai_can_add_a_flag_the_rules_do_not_have(conn, user, monkeypatch):
    crestor, clari = add(conn, user, "CRESTOR", strength="10 mg"), add(conn, user, "Clarithromycin 500 mg")
    fake_ai(monkeypatch, ok((crestor, clari, "Clarithromycin may raise the level of CRESTOR in the blood.")))
    r = pipe.check_user(user)
    assert (r["database"], r["ai"], r["new"]) == (0, 1, 1)
    [a] = store.list_open(conn, user)
    assert a["origin"] == "ai" and "may raise the level" in a["summary"] and a["sources"][0]["title"] == "drugs.com"


def test_the_ai_failing_never_hides_what_the_rules_found_and_marks_the_check_incomplete(conn, user, monkeypatch):
    add(conn, user, "Atorvastatin 20 mg")
    add(conn, user, "Clarithromycin 500 mg")
    fake_ai(monkeypatch, ck.ClashOutcome(status="failed", reason="service_unavailable"))
    r = pipe.check_user(user)
    assert r["ai_status"] == "failed" and len(store.list_open(conn, user)) == 1 and pipe.last_check_failed(user) is True
    fake_ai(monkeypatch, ok())
    pipe.check_user(user)
    assert pipe.last_check_failed(user) is False and len(store.list_open(conn, user)) == 1      # a quiet AI never removes the rule's flag


def test_the_daily_ai_limit_skips_the_ai_but_still_runs_the_rules(conn, user, monkeypatch):
    add(conn, user, "Atorvastatin 20 mg")
    add(conn, user, "Clarithromycin 500 mg")
    monkeypatch.setattr(usage, "allowed", lambda provider: False)
    calls = fake_ai(monkeypatch, ok())
    r = pipe.check_user(user)
    assert calls == [] and r["ai_status"] == "failed" and r["reason"] == "daily_limit" and len(store.list_open(conn, user)) == 1


def test_replaying_the_order_medicines_were_added_shows_the_box_only_at_the_step_that_causes_it(conn, user, monkeypatch):
    fake_ai(monkeypatch, ok())
    ids = [add(conn, user, n, start=s) for n, s in [("Metformin 500 mg", "2021-04-11"), ("Amlodipine 5 mg", "2022-12-02"),
                                                   ("Atorvastatin 20 mg", "2023-06-20"), ("Clarithromycin 500 mg", "2026-09-13")]]
    steps = []
    for k in range(1, 5):
        pipe.check_user(user, only_ids=ids[:k])
        steps.append(len(store.list_open(conn, user)))
    assert steps == [0, 0, 0, 2]                                 # Clarithromycin clashes with both Amlodipine and Atorvastatin


def test_the_event_log_holds_counts_and_codes_never_names_or_reasons(conn, user, monkeypatch):
    a, b = add(conn, user, "CRESTOR"), add(conn, user, "Clarithromycin 500 mg")
    fake_ai(monkeypatch, ok((a, b, "Clarithromycin may raise the level of CRESTOR.")))
    pipe.check_user(user)
    ev = [str(r[0]) for r in conn.execute("select payload from event_log where user_id = %s and event like 'interaction.%%'", (user,)).fetchall()]
    assert len(ev) == 2 and not any(w in " ".join(ev) for w in ("CRESTOR", "Clarithromycin", "raise"))


def test_a_check_that_crashes_is_reported_not_raised(conn, user, monkeypatch):
    add(conn, user, "Atorvastatin 20 mg")
    add(conn, user, "Clarithromycin 500 mg")

    def boom(medicines):
        raise RuntimeError("model blew up")

    monkeypatch.setattr(pipe, "_ai", boom)
    r = pipe.check_user(user)
    assert r["ai_status"] == "failed" and r["reason"] == "error" and pipe.is_checking(user) is False


# ------------------------------------------------------------------ the routes
def test_the_status_route_lists_open_alerts_and_the_question_and_acknowledge_buttons_work(conn, user, monkeypatch):
    add(conn, user, "Atorvastatin 20 mg")
    add(conn, user, "Clarithromycin 500 mg")
    fake_ai(monkeypatch, ok())
    pipe.check_user(user)
    s = route._status(user)
    assert s.checking is False and len(s.alerts) == 1 and s.alerts[0].origin == "database" and s.alerts[0].sources[0].url.startswith("https://")
    q = route._ask(user, s.alerts[0].id)
    row = conn.execute("select text, origin, status from doctor_questions where id = %s", (q.id,)).fetchone()
    assert row[1:] == ("agent_suggested", "open") and "Atorvastatin 20 mg" in row[0] and "Clarithromycin 500 mg" in row[0] and "together" in row[0]
    assert route._ack(user, s.alerts[0].id).alerts == []                    # the box goes away; the alert is kept as acknowledged
    assert conn.execute("select status from interaction_alerts where user_id = %s", (user,)).fetchone()[0] == "acknowledged"


def test_someone_elses_alert_is_not_found(conn, user, monkeypatch):
    other = str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0])
    add(conn, other, "Atorvastatin 20 mg")
    add(conn, other, "Clarithromycin 500 mg")
    fake_ai(monkeypatch, ok())
    pipe.check_user(other)
    [a] = route._status(other).alerts
    for call in (lambda: route._ask(user, a.id), lambda: route._ack(user, a.id), lambda: route._ack(user, "not-a-uuid")):
        with pytest.raises(HTTPException) as e:
            call()
        assert e.value.status_code == 404
    with pytest.raises(NotFound):
        store.acknowledge(conn, user, a.id)


def test_asking_the_doctor_twice_saves_one_question_and_the_alert_remembers_it(conn, user, monkeypatch):
    add(conn, user, "Atorvastatin 20 mg")
    add(conn, user, "Clarithromycin 500 mg")
    fake_ai(monkeypatch, ok())
    pipe.check_user(user)
    [alert] = route._status(user).alerts
    assert alert.question_added is False
    first, second = route._ask(user, alert.id), route._ask(user, alert.id)
    assert first.id == second.id
    assert conn.execute("select count(*) from doctor_questions where user_id = %s", (user,)).fetchone()[0] == 1
    assert route._status(user).alerts[0].question_added is True
    conn.execute("update doctor_questions set status = 'asked' where id = %s", (first.id,))          # once it has been asked, the button is offered again
    assert route._status(user).alerts[0].question_added is False
