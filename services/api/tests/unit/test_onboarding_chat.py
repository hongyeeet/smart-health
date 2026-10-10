"""The chat setup (A4): the plain-rule reader, the checks, the model path with the model faked, and the endpoint.

Nothing here reaches the model or the database. The model client is a fake, the usage counter is replaced, and the
endpoint runs against a fake connection that records every statement, so the test can show that a chat answer writes nothing.
"""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from app.llm import gateway
from app.services import onboarding as svc
from app.services import usage
from app.services.onboarding import FALLBACK_REPLY, answer_step, canonical, chat_step, model_extract

LABELS = {
    "gender_type": frozenset({"female", "male", "other", "prefer_not_to_say"}),
    "work_type": frozenset({"desk", "mixed", "standing", "physical", "shift", "not_working"}),
    "locale_code": frozenset({"en", "zh", "ms", "ta"}),
    "yes_no_unsure": frozenset({"yes", "no", "not_sure"}),
}
THIS_YEAR = 2026


def step(step_id: str):
    return chat_step(step_id)


# ------------------------------------------------------------------ the plain-rule reader (no model)
def test_name_is_read_from_a_short_answer_and_a_leading_phrase():
    assert canonical(step("name"), "Ahmad") == "Ahmad"
    assert canonical(step("name"), "My name is Mei Ling.") == "Mei Ling"
    assert canonical(step("name"), "I'm 55 years old") is None            # digits: the rules do not guess a name from a sentence


def test_birth_year_needs_a_four_digit_year_and_nothing_else():
    assert canonical(step("birthYear"), "1968") == "1968"
    assert canonical(step("birthYear"), "I was born in 1968") == "1968"
    assert canonical(step("birthYear"), "55") is None                       # an age is not turned into a year


def test_numbers_accept_a_plain_number_with_or_without_the_unit():
    assert canonical(step("heightCm"), "168") == "168"
    assert canonical(step("heightCm"), "about 170 cm") == "170"
    assert canonical(step("weightKg"), "72.5 kg") == "72.5"
    assert canonical(step("weightKg"), "a bit heavy") is None


def test_yes_and_not_sure_are_read_only_when_they_are_clear():
    assert canonical(step("hasDiabetes"), "Yes") == "yes"
    assert canonical(step("hasDiabetes"), "I do") == "yes"
    assert canonical(step("hasDiabetes"), "Not sure") == "not_sure"
    assert canonical(step("hasDiabetes"), "yes, not sure") is None          # two answers at once: not guessed
    assert canonical(step("hasDiabetes"), "I have no idea") is None         # "i have" alone is not a yes
    assert canonical(step("hasDiabetes"), "no") is None                     # a no is not a choice on this question


def test_work_choices_are_read_from_the_words_the_person_uses():
    assert canonical(step("workType"), "mostly sitting at a desk") == "desk"
    assert canonical(step("workType"), "I am retired") == "not_working"
    assert canonical(step("workType"), "sometimes") is None


def test_email_and_phone_are_found_in_the_text_when_there_is_exactly_one():
    assert canonical(step("reminderEmail"), "my email is mei@gmail.com") == "mei@gmail.com"
    assert canonical(step("reminderEmail"), "a@gmail.com or b@gmail.com") is None
    assert canonical(step("contactPhone"), "+65 9123 4567") == "+65 9123 4567"
    assert canonical(step("contactPhone"), "call 999") is None              # too few digits to be a phone number


# ------------------------------------------------------------------ the checks: the same rules as the form and the save
def test_an_adult_check_and_the_form_ranges_refuse_bad_values_with_a_plain_reason():
    res = answer_step("birthYear", "2015", LABELS, THIS_YEAR, extract=lambda *_: None)
    assert res["understood"] is False and res["fields"] == {}
    assert res["reply"] == "Smart Health is for adults aged 18 or older."
    res = answer_step("heightCm", "900", LABELS, THIS_YEAR, extract=lambda *_: None)
    assert res["understood"] is False and res["reply"] == "Enter a number from 100 to 250."


def test_a_good_answer_is_understood_and_points_at_the_next_question():
    res = answer_step("name", "Ahmad", LABELS, THIS_YEAR, extract=lambda *_: None)
    assert res == {"fields": {"name": "Ahmad"}, "understood": True, "next_step": "birthYear", "reply": "Thanks, Ahmad."}
    last = answer_step("reminderEmail", "mei@gmail.com", LABELS, THIS_YEAR, extract=lambda *_: None)
    assert last["understood"] is True and last["next_step"] is None


def test_a_value_the_database_does_not_list_is_refused_by_the_profile_check():
    labels = {**LABELS, "yes_no_unsure": frozenset({"yes"})}               # the database has no "not_sure" choice here
    res = answer_step("hasDiabetes", "not sure", labels, THIS_YEAR, extract=lambda *_: None)
    assert res["understood"] is False and res["fields"] == {}
    assert "is not a choice Smart Health knows" in res["reply"]


def test_an_unknown_question_is_refused():
    with pytest.raises(svc.OnboardingError, match="not a question of the chat setup"):
        answer_step("notAStep", "x", LABELS, THIS_YEAR)


def test_the_plain_rules_answer_first_and_the_model_is_not_called():
    def must_not_run(*_):
        raise AssertionError("the model was called for a plain answer")

    res = answer_step("birthYear", "1968", LABELS, THIS_YEAR, extract=must_not_run)
    assert res["understood"] is True and res["fields"] == {"birthYear": "1968"}


# ------------------------------------------------------------------ the model path, with the model faked
def test_an_unknown_enum_from_the_model_is_not_guessed():
    res = answer_step("gender", "I am a robot", LABELS, THIS_YEAR, extract=lambda *_: {"gender": "robot"})
    assert res["understood"] is False and res["fields"] == {}
    assert res["next_step"] == "gender" and res["reply"] == chat_step("gender").ask


def test_a_sentence_the_model_reads_is_checked_like_any_other_answer():
    res = answer_step("gender", "I am a bloke", LABELS, THIS_YEAR, extract=lambda *_: {"gender": "male"})
    assert res["understood"] is True and res["fields"] == {"gender": "male"}


def test_one_message_can_answer_more_than_the_question_asked_and_each_part_is_checked():
    got = {"name": "Ahmad", "birthYear": "2015"}                           # the year breaks the adult check
    res = answer_step("name", "I'm Ahmad, born 2015", LABELS, THIS_YEAR, extract=lambda *_: got)
    assert res["understood"] is True and res["fields"] == {"name": "Ahmad"}


def test_when_the_model_is_unavailable_the_person_is_sent_to_the_form():
    res = answer_step("gender", "I am a bloke", LABELS, THIS_YEAR, extract=lambda *_: None)
    assert res == {"fields": {}, "understood": False, "next_step": "gender", "reply": FALLBACK_REPLY}


class _FakeModels:
    def __init__(self, text: str):
        self.text = text
        self.contents: list[str] = []

    def generate_content(self, **kwargs):
        self.contents.append(kwargs["contents"])
        return SimpleNamespace(parsed=None, text=self.text, usage_metadata=None)


class _FakeClient:
    def __init__(self, text: str):
        self.models = _FakeModels(text)


def test_nric_is_scrubbed_from_what_is_sent_to_the_model(monkeypatch):
    client = _FakeClient('{"name": "Ahmad"}')
    monkeypatch.setattr(gateway, "_client", lambda: client)
    monkeypatch.setattr(usage, "allowed", lambda provider: True)
    monkeypatch.setattr(usage, "record", lambda *a, **k: None)
    got = model_extract("I am Ahmad, my NRIC is S1234567D", step("name"))
    assert got == {"name": "Ahmad"}
    sent = client.models.contents[0]
    assert "S1234567D" not in sent and "[id]" in sent


def test_the_model_is_not_called_once_the_daily_ai_cap_is_reached(monkeypatch):
    client = _FakeClient('{"name": "Ahmad"}')
    monkeypatch.setattr(gateway, "_client", lambda: client)
    monkeypatch.setattr(usage, "allowed", lambda provider: False)
    assert model_extract("I am Ahmad", step("name")) is None
    assert client.models.contents == []
    res = answer_step("name", "I am Ahmad, born in 1968", LABELS, THIS_YEAR)     # a sentence the rules cannot read: cap reached, so the form is offered
    assert res["understood"] is False and res["reply"] == FALLBACK_REPLY


def test_no_model_credentials_is_the_same_as_no_model(monkeypatch):
    def no_key():
        raise gateway.LLMUnavailable("No Vertex AI credentials")

    monkeypatch.setattr(gateway, "_client", no_key)
    assert model_extract("I am Ahmad", step("name")) is None


# ------------------------------------------------------------------ the endpoint: a fake connection that records writes
ENUM_ROWS = [{"typname": k, "enumlabel": v} for k, vs in LABELS.items() for v in sorted(vs)]


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class _RecordingConn:
    def __init__(self):
        self.calls: list[str] = []

    def execute(self, sql, params=()):
        flat = " ".join(sql.split())
        self.calls.append(flat)
        return _Result(ENUM_ROWS if "pg_enum" in flat else [])

    def writes(self) -> list[str]:
        return [s for s in self.calls if s.split(" ", 1)[0] in {"insert", "update", "delete"}]


@pytest.fixture
def client(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.routers import onboarding as router_mod
    from app.db import logstore

    state: dict = {}

    @contextmanager
    def fake_tx():
        state["conn"] = _RecordingConn()
        yield state["conn"]

    monkeypatch.setattr(logstore, "tx", fake_tx)
    monkeypatch.setattr(svc, "model_extract", lambda text, st: None)     # no model in these tests: the rules or the fallback answer
    app = FastAPI()
    app.include_router(router_mod.router, prefix="/api/v1")
    c = TestClient(app)
    c.state = state                                                         # type: ignore[attr-defined]
    return c


def _as(key: str):
    from app.db import logstore

    return logstore._current.set(key)


def test_mr_tan_is_refused_the_same_way_as_the_other_onboarding_writes(client):
    from app.db import logstore

    token = _as("mr-tan")
    try:
        res = client.post("/api/v1/onboarding/chat", json={"text": "Ahmad", "step": "name"})
    finally:
        logstore._current.reset(token)
    assert res.status_code == 409
    assert "Mr Tan is demo data" in res.json()["detail"]


def test_the_demo_user_gets_an_answer_and_nothing_is_written(client):
    res = client.post("/api/v1/onboarding/chat", json={"text": "Ahmad", "step": "name"})
    assert res.status_code == 200
    assert res.json() == {"fields": {"name": "Ahmad"}, "understood": True, "nextStep": "birthYear", "reply": "Thanks, Ahmad."}
    assert client.state["conn"].writes() == []


def test_the_demo_user_with_a_refused_answer_gets_the_question_again_and_nothing_is_written(client):
    res = client.post("/api/v1/onboarding/chat", json={"text": "2015", "step": "birthYear"})
    body = res.json()
    assert res.status_code == 200
    assert body["understood"] is False and body["nextStep"] == "birthYear" and body["fields"] == {}
    assert client.state["conn"].writes() == []


def test_an_unknown_step_is_a_plain_422(client):
    res = client.post("/api/v1/onboarding/chat", json={"text": "Ahmad", "step": "salary"})
    assert res.status_code == 422
    assert "not a question of the chat setup" in res.json()["detail"]
