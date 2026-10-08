"""The medicine page routes (H6) end to end against the real tables, with the model and web search replaced by a fake.

Everything runs inside one transaction that is rolled back. Run from services/api:  python -m pytest tests/db/test_med_explain_route.py -q
Needs DATABASE_URL in the private .env.
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

from app.agents import med_explain_pipeline  # noqa: E402
from app.agents.med_explainer import ExplainOutcome  # noqa: E402
from app.api.routers import med_explain as route  # noqa: E402
from app.api.routers import medications as meds  # noqa: E402
from app.db import logstore  # noqa: E402
from app.llm.vertex import WebSource  # noqa: E402
from app.schemas.medicines import NewMedicationIn, QuestionIn  # noqa: E402
from app.services import usage  # noqa: E402


@pytest.fixture()
def db(monkeypatch):
    load_env()
    conn = psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20)
    user = str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0])

    @contextmanager
    def fake_tx():
        yield conn

    monkeypatch.setattr(logstore, "tx", fake_tx)
    monkeypatch.setattr(logstore, "current_user", lambda: uuid.UUID(user))
    monkeypatch.setattr(usage, "allowed", lambda provider: True)
    monkeypatch.setattr(usage, "record", lambda *a, **k: None)
    try:
        yield conn, user
    finally:
        conn.rollback()
        conn.close()


def new_med(conn, user, **over):
    base = {"name": "CRESTOR", "kind": "prescription", "strength": "10 mg", "totalQuantity": 168, "directions": "Take 1 tab every morning",
            "doses": [{"time": "08:00", "quantity": 1, "mealRelation": "na"}]}
    base.update(over)
    return meds.create_medication(conn, user, NewMedicationIn.model_validate(base), meds.datetime_today()).id


def ready(**over):
    base = dict(status="ready", purpose="Lowers bad cholesterol.", side_effects=["Headache", "Nausea"], tell_doctor="Call if you have muscle pain.",
                sources=[WebSource("drugs.com", "https://vertexaisearch.cloud.google.com/r/1")], model_id="m", prompt_version="1",
                input_tokens=10, output_tokens=5)
    base.update(over)
    return ExplainOutcome(**base)


def fake_run(monkeypatch, *outcomes):
    calls = []
    queue = list(outcomes)

    def run(**kw):
        calls.append(kw)
        return queue.pop(0)

    monkeypatch.setattr(med_explain_pipeline, "run", run)
    return calls


def test_a_new_medicine_has_no_explanation_and_shows_its_own_label_text(db):
    conn, user = db
    mid = new_med(conn, user)
    d = route._detail(mid)
    assert (d.name, d.strength, d.directions, d.explanation) == ("CRESTOR", "10 mg", "Take 1 tab every morning", None)
    assert d.times == ["8:00 am"] and d.refill is not None


def test_the_explanation_is_made_once_saved_and_then_returned_without_another_search(db, monkeypatch):
    conn, user = db
    mid = new_med(conn, user)
    calls = fake_run(monkeypatch, ready())
    first = route._explain(mid, False)
    assert first.status == "ready" and first.purpose == "Lowers bad cholesterol." and first.side_effects == ["Headache", "Nausea"]
    assert [(s.title, s.url.startswith("https://")) for s in first.sources] == [("drugs.com", True)]
    again = route._explain(mid, False)                       # served from the saved copy
    assert again.generated_at == first.generated_at and len(calls) == 1
    assert route._detail(mid).explanation.purpose == "Lowers bad cholesterol."
    assert calls[0]["name"] == "CRESTOR" and calls[0]["directions"] == "Take 1 tab every morning"
    ev = conn.execute("select actor, payload from event_log where user_id = %s and event = 'medication.explained'", (user,)).fetchall()
    assert len(ev) == 1 and ev[0][0] == "agent" and "CRESTOR" not in str(ev[0][1]) and "cholesterol" not in str(ev[0][1])


def test_refresh_searches_again_and_replaces_the_saved_text(db, monkeypatch):
    conn, user = db
    mid = new_med(conn, user)
    calls = fake_run(monkeypatch, ready(), ready(purpose="A new wording."))
    route._explain(mid, False)
    assert route._explain(mid, True).purpose == "A new wording." and len(calls) == 2


def test_an_explanation_for_an_old_version_of_the_medicine_is_not_shown_for_the_new_one(db, monkeypatch):
    conn, user = db
    mid = new_med(conn, user)
    fake_run(monkeypatch, ready())
    route._explain(mid, False)
    conn.execute("update medications set strength = '20 mg' where id = %s", (mid,))
    assert route._detail(mid).explanation is None            # the page asks for a new one
    calls = fake_run(monkeypatch, ready(purpose="For 20 mg."))
    assert route._explain(mid, False).purpose == "For 20 mg." and len(calls) == 1


def test_a_failed_search_saves_nothing_and_says_so_in_plain_words(db, monkeypatch):
    conn, user = db
    mid = new_med(conn, user)
    fake_run(monkeypatch, ExplainOutcome(status="failed", reason="service_unavailable"), ExplainOutcome(status="failed", reason="no_sources"))
    with pytest.raises(HTTPException) as e:
        route._explain(mid, False)
    assert e.value.status_code == 503 and "try again" in e.value.detail
    with pytest.raises(HTTPException) as e2:
        route._explain(mid, False)
    assert e2.value.status_code == 502 and "pharmacist" in e2.value.detail
    assert conn.execute("select count(*) from medication_explanations where medication_id = %s", (mid,)).fetchone()[0] == 0


def test_a_product_that_could_not_be_identified_is_kept_so_the_search_is_not_repeated(db, monkeypatch):
    conn, user = db
    mid = new_med(conn, user, name="Herbal tonic", kind="tcm", strength=None)
    calls = fake_run(monkeypatch, ExplainOutcome(status="not_identified", sources=[], model_id="m", prompt_version="1"))
    out = route._explain(mid, False)
    assert out.status == "not_identified" and out.purpose == "" and out.side_effects == []
    route._explain(mid, False)
    assert len(calls) == 1


def test_the_daily_limit_stops_the_search_and_says_so(db, monkeypatch):
    conn, user = db
    mid = new_med(conn, user)
    monkeypatch.setattr(usage, "allowed", lambda provider: False)
    calls = fake_run(monkeypatch)
    with pytest.raises(HTTPException) as e:
        route._explain(mid, False)
    assert e.value.status_code == 429 and calls == []


def test_someone_elses_medicine_is_not_found(db, monkeypatch):
    conn, user = db
    other = str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0])
    mid = new_med(conn, other)
    fake_run(monkeypatch, ready())
    for call in (lambda: route._detail(mid), lambda: route._explain(mid, False), lambda: route._ask(mid, QuestionIn(text="Is this ok?"))):
        with pytest.raises(HTTPException) as e:
            call()
        assert e.value.status_code == 404
    with pytest.raises(HTTPException) as e:
        route._detail("not-a-uuid")
    assert e.value.status_code == 404


def test_a_question_goes_to_the_doctor_question_list(db):
    conn, user = db
    mid = new_med(conn, user)
    q = route._ask(mid, QuestionIn(text="  Will CRESTOR affect my diabetes?  "))
    row = conn.execute("select text, origin, status, user_id::text from doctor_questions where id = %s", (q.id,)).fetchone()
    assert row == ("Will CRESTOR affect my diabetes?", "user", "open", user)
    assert conn.execute("select count(*) from event_log where user_id = %s and event = 'doctor_question.added'", (user,)).fetchone()[0] == 1
    with pytest.raises(ValueError):
        QuestionIn(text="no")                                 # too short to be a question
