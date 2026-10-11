"""The chat setup (A4): the plain-rule reader, the checks, the skip rules, the model path with the model faked, and the endpoint.

Nothing here reaches the model or the database. The model client is a fake, the usage counter is replaced, and the endpoint runs
against a fake connection that records every statement, so the test can show that a chat answer writes nothing.
The questions follow the form pages, so the table below covers each question: a valid answer, an invalid one and a skip.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import date
from types import SimpleNamespace

import pytest

from app.llm import gateway
from app.services import onboarding as svc
from app.services import usage
from app.services.onboarding import CHAT_STEPS, FALLBACK_REPLY, NEEDED_REPLY, UNIT_HINT, answer_step, chat_step, model_extract, read_fields

LABELS = {
    "gender_type": frozenset({"female", "male", "other", "prefer_not_to_say"}),
    "work_type": frozenset({"desk", "mixed", "standing", "physical", "shift", "not_working"}),
    "locale_code": frozenset({"en", "zh", "ms", "ta"}),
    "yes_no_unsure": frozenset({"yes", "no", "not_sure"}),
}
THIS_YEAR = 2026
TODAY = date(2026, 10, 11)
# the answers already on the form that an answer depends on: a birth year, a blood test date, the units and a desk job
KNOWN = {"birthYear": "1968", "labDate": "2026-03-12", "hba1cUnit": "%", "glucoseUnit": "mmol/L", "workType": "desk"}
REQUIRED = ["name", "hasDiabetes", "birthYear", "gender", "contactName", "contactRelation", "contactPhone", "contactEmail"]


def must_not_run(*_):
    raise AssertionError("the model was called")


def ask(step_id: str, text: str, known: dict | None = None, extract=must_not_run):
    """One answer, with the model off unless the test gives it a fake."""
    return answer_step(step_id, text, LABELS, THIS_YEAR, extract=extract, known=KNOWN if known is None else known, today=TODAY)


def step(step_id: str):
    return chat_step(step_id)


# ------------------------------------------------------------------ the order and the required questions
def test_the_questions_follow_the_form_pages_in_order():
    # Welcome (name, reminder email), eligibility, about you, diabetes history, low glucose, conditions and checks, labs,
    # devices, the work week, the emergency contact. Medicines are not asked here (the screen points to Scan a label).
    assert [s.id for s in CHAT_STEPS] == [
        "name", "reminderEmail", "hasDiabetes", "birthYear", "gender", "heightCm", "weightKg", "waistCm",
        "diagnosedYear", "careSetting", "healthierSg", "hypo3m", "severeHypo", "gold", "conditions", "otherConditions",
        "allergies", "eyeCheck", "footCheck", "labDate", "hba1c", "fastingGlucose", "fastingInsulin", "cgm", "wearable",
        "workType", "workDays", "workStart", "workEnd", "contactName", "contactRelation", "contactPhone", "contactEmail",
    ]
    with pytest.raises(svc.OnboardingError, match="not a question of the chat setup"):
        chat_step("redFlags")
    with pytest.raises(svc.OnboardingError, match="not a question of the chat setup"):
        chat_step("language")
    with pytest.raises(svc.OnboardingError, match="not a question of the chat setup"):
        chat_step("medicines")


def test_the_required_questions_are_exactly_the_ones_the_brief_names():
    # name, birth year, sex, and the four emergency contact fields. hasDiabetes is also needed: the profile cannot be created without it.
    assert [s.id for s in CHAT_STEPS if not s.optional] == REQUIRED


def test_the_work_week_is_asked_only_when_the_person_works():
    assert [s.id for s in CHAT_STEPS if s.working_only] == ["workDays", "workStart", "workEnd"]
    assert ask("workType", "retired")["reply"] == "Got it."
    res = ask("workType", "retired", known={})
    assert res["fields"] == {"workType": "not_working"} and res["next_step"] == "contactName"
    res = ask("workType", "mostly sitting", known={})
    assert res["fields"] == {"workType": "desk"} and res["next_step"] == "workDays"


def test_a_skipped_optional_question_moves_on_to_the_next_question_asked():
    res = ask("hypo3m", "skip", known={"workType": None})
    assert res == {"fields": {}, "understood": True, "next_step": "severeHypo", "reply": "Skipped."}
    res = ask("workType", "skip", known={})
    assert res["next_step"] == "contactName"


# ------------------------------------------------------------------ table: a valid answer for each question
VALID = [
    ("name", "Ahmad", {}, {"name": "Ahmad"}),
    ("name", "My name is Mei Ling.", {}, {"name": "Mei Ling"}),
    ("reminderEmail", "my email is mei@gmail.com", {}, {"reminderEmail": "mei@gmail.com"}),
    ("hasDiabetes", "Yes", {}, {"hasDiabetes": "yes"}),
    ("hasDiabetes", "Not sure", {}, {"hasDiabetes": "not_sure"}),
    ("birthYear", "1968", {}, {"birthYear": "1968"}),
    ("birthYear", "I was born in 1968", {}, {"birthYear": "1968"}),
    ("gender", "male", {}, {"gender": "male"}),
    ("gender", "woman", {}, {"gender": "female"}),
    ("heightCm", "168", {}, {"heightCm": "168"}),
    ("heightCm", "about 170 cm", {}, {"heightCm": "170"}),
    ("weightKg", "72.5 kg", {}, {"weightKg": "72.5"}),
    ("waistCm", "84", {}, {"waistCm": "84"}),
    ("waistCm", "about 84 cm", {}, {"waistCm": "84"}),
    ("diagnosedYear", "2016", {}, {"diagnosedYear": "2016"}),
    ("diagnosedYear", "in 2016", {}, {"diagnosedYear": "2016"}),
    ("careSetting", "polyclinic", {}, {"careSetting": "polyclinic"}),
    ("careSetting", "I see a GP", {}, {"careSetting": "gp"}),
    ("careSetting", "no regular doctor", {}, {"careSetting": "none"}),
    ("healthierSg", "yes", {}, {"healthierSg": "yes"}),
    ("healthierSg", "I am enrolled", {}, {"healthierSg": "yes"}),
    ("healthierSg", "not enrolled", {}, {"healthierSg": "no"}),
    ("healthierSg", "not sure", {}, {"healthierSg": "unsure"}),
    ("hypo3m", "none", {}, {"hypo3m": "0"}),
    ("hypo3m", "1 or 2 times", {}, {"hypo3m": "1-2"}),
    ("hypo3m", "3 or more", {}, {"hypo3m": "3+"}),
    ("hypo3m", "not sure", {}, {"hypo3m": "unsure"}),
    ("severeHypo", "yes", {}, {"severeHypo": "yes"}),
    ("severeHypo", "No", {}, {"severeHypo": "no"}),
    ("severeHypo", "I did not need help", {}, {"severeHypo": "no"}),
    ("gold", "3", {}, {"gold": "3"}),
    ("gold", "7 never aware", {}, {"gold": "7"}),
    ("conditions", "none", {}, {"conditions": ["none"]}),
    ("conditions", "high blood pressure and kidney disease", {}, {"conditions": ["hypertension", "kidney"]}),
    ("conditions", "heart failure", {}, {"conditions": ["heart_failure"]}),
    ("otherConditions", "gout", {}, {"otherConditions": "gout"}),
    ("allergies", "penicillin (rash)", {}, {"allergies": [{"substance": "penicillin", "reaction": "rash"}], "noAllergies": False}),
    ("allergies", "peanuts", {}, {"allergies": [{"substance": "peanuts", "reaction": ""}], "noAllergies": False}),
    ("allergies", "none", {}, {"allergies": [], "noAllergies": True}),
    ("eyeCheck", "in the last year", {}, {"eyeCheck": "within_year"}),
    ("eyeCheck", "more than a year ago", {}, {"eyeCheck": "over_year"}),
    ("eyeCheck", "never", {}, {"eyeCheck": "never_unsure"}),
    ("footCheck", "not sure", {}, {"footCheck": "never_unsure"}),
    ("labDate", "12 March 2026", {}, {"labDate": "2026-03-12"}),
    ("labDate", "12/03/2026", {}, {"labDate": "2026-03-12"}),
    ("labDate", "2026-03-12", {}, {"labDate": "2026-03-12"}),
    ("hba1c", "7.2%", KNOWN, {"hba1c": "7.2", "hba1cUnit": "%"}),
    ("hba1c", "55 mmol/mol", KNOWN, {"hba1c": "55", "hba1cUnit": "mmol/mol"}),
    ("hba1c", "7.2", KNOWN, {"hba1c": "7.2", "hba1cUnit": "%"}),
    ("fastingGlucose", "7.4 mmol/L", KNOWN, {"fastingGlucose": "7.4", "glucoseUnit": "mmol/L"}),
    ("fastingGlucose", "133 mg/dL", KNOWN, {"fastingGlucose": "133", "glucoseUnit": "mg/dL"}),
    ("fastingInsulin", "11.5", KNOWN, {"fastingInsulin": "11.5"}),
    ("cgm", "Libre", {}, {"cgm": "libre"}),
    ("cgm", "none", {}, {"cgm": "none"}),
    ("wearable", "Apple Watch", {}, {"wearable": "apple"}),
    ("wearable", "Garmin", {}, {"wearable": "garmin"}),
    ("workType", "mostly sitting at a desk", {}, {"workType": "desk"}),
    ("workType", "shifts", {}, {"workType": "shift"}),
    ("workDays", "Mon to Fri", KNOWN, {"workDays": [1, 2, 3, 4, 5]}),
    ("workDays", "weekdays", KNOWN, {"workDays": [1, 2, 3, 4, 5]}),
    ("workDays", "Monday, Wednesday and Friday", KNOWN, {"workDays": [1, 3, 5]}),
    ("workStart", "7.30am", KNOWN, {"workStart": "07:30"}),
    ("workEnd", "6pm", KNOWN, {"workEnd": "18:00"}),
    ("workEnd", "19:00", KNOWN, {"workEnd": "19:00"}),
    ("contactName", "Siti", {}, {"contactName": "Siti"}),
    ("contactRelation", "son", {}, {"contactRelation": "son"}),
    ("contactPhone", "+65 9123 4567", {}, {"contactPhone": "+65 9123 4567"}),
    ("contactEmail", "mei@gmail.com", {}, {"contactEmail": "mei@gmail.com"}),
]


@pytest.mark.parametrize(("step_id", "text", "known", "fields"), VALID, ids=[f"{s}:{t}" for s, t, _, _ in VALID])
def test_a_valid_answer_is_understood_and_fills_the_store_field(step_id, text, known, fields):
    res = ask(step_id, text, known)
    assert res["understood"] is True, res
    assert res["fields"] == fields


# ------------------------------------------------------------------ table: an invalid answer for each question
INVALID = [
    ("name", "Mr 123", {}, FALLBACK_REPLY),
    ("reminderEmail", "mei@gmail", {}, FALLBACK_REPLY),
    ("birthYear", "2015", {}, "Smart Health is for adults aged 18 or older."),
    ("birthYear", "55", {}, FALLBACK_REPLY),
    ("gender", "other", {}, FALLBACK_REPLY),
    ("gender", "prefer not to say", {}, FALLBACK_REPLY),
    ("heightCm", "900", {}, "Enter a number from 100 to 250."),
    ("weightKg", "10", {}, "Enter a number from 25 to 300."),
    ("waistCm", "30", {}, "Waist must be between 40 and 200 cm."),
    ("waistCm", "300", {}, "Waist must be between 40 and 200 cm."),
    ("diagnosedYear", "2030", KNOWN, "The year you were told you have diabetes must be four digits, and not in the future."),
    ("diagnosedYear", "1960", KNOWN, "The year you were told you have diabetes cannot be before the year you were born."),
    ("careSetting", "the moon", {}, FALLBACK_REPLY),
    ("healthierSg", "maybe later", {}, FALLBACK_REPLY),
    ("hypo3m", "lots", {}, FALLBACK_REPLY),
    ("severeHypo", "sometimes", {}, FALLBACK_REPLY),
    ("gold", "9", {}, FALLBACK_REPLY),
    ("conditions", "my knee hurts", {}, FALLBACK_REPLY),
    ("otherConditions", "x" * 201, {}, "Keep it to 200 characters or fewer."),
    ("allergies", "x" * 201, {}, "Keep each allergy to 200 characters or fewer."),
    ("eyeCheck", "last week", {}, FALLBACK_REPLY),
    ("footCheck", "sometime", {}, FALLBACK_REPLY),
    ("labDate", "2030-01-01", KNOWN, "The date of the blood test cannot be in the future."),
    ("labDate", "31/02/2026", KNOWN, FALLBACK_REPLY),
    ("hba1c", "7.2", {"hba1cUnit": "%"}, "Enter the date of your blood test."),
    ("hba1c", "55", KNOWN, "HbA1c must be between 4 and 20 %. " + UNIT_HINT["hba1c"]),
    ("hba1c", "7.2", {**KNOWN, "hba1cUnit": "mmol/mol"}, "HbA1c must be between 20 and 195 mmol/mol. " + UNIT_HINT["hba1c"]),
    ("hba1c", "7.2 mg", KNOWN, FALLBACK_REPLY),
    ("fastingGlucose", "133", KNOWN, "Fasting glucose must be between 1 and 35 mmol/L. " + UNIT_HINT["fastingGlucose"]),
    ("fastingInsulin", "0", KNOWN, "Fasting insulin must be between 0.1 and 1000 µIU/mL."),
    ("cgm", "a bicycle", {}, FALLBACK_REPLY),
    ("wearable", "a bracelet", {}, FALLBACK_REPLY),
    ("workType", "sometimes", {}, FALLBACK_REPLY),
    ("workDays", "someday", KNOWN, FALLBACK_REPLY),
    ("workStart", "7", KNOWN, FALLBACK_REPLY),
    ("workEnd", "25:00", KNOWN, FALLBACK_REPLY),
    ("contactRelation", "x" * 101, {}, FALLBACK_REPLY),
    ("contactPhone", "999", {}, "Enter a mobile number with digits, like +65 9123 4567."),
    ("contactEmail", "mei@gmail", {}, FALLBACK_REPLY),
]


@pytest.mark.parametrize(("step_id", "text", "known", "reply"), INVALID, ids=[f"{s}:{t[:20]}" for s, t, _, _ in INVALID])
def test_an_invalid_answer_is_asked_again_with_a_plain_reason_and_stores_nothing(step_id, text, known, reply):
    res = ask(step_id, text, known, extract=lambda *_: None)
    assert res["understood"] is False
    assert res["fields"] == {}
    assert res["next_step"] == step_id
    assert res["reply"] == reply


# ------------------------------------------------------------------ table: skip (optional) and "needed" (required)
OPTIONAL = [s.id for s in CHAT_STEPS if s.optional]


@pytest.mark.parametrize("step_id", OPTIONAL)
@pytest.mark.parametrize("words", ["skip", "I do not know"])
def test_every_optional_question_can_be_skipped(step_id, words):
    res = ask(step_id, words)                       # the model is not asked: must_not_run
    assert res["understood"] is True and res["fields"] == {} and res["reply"] == "Skipped."
    assert res["next_step"] == svc._next_id(step_id, KNOWN)


def test_a_none_answer_skips_the_free_text_question():
    res = ask("otherConditions", "none", {})
    assert res == {"fields": {}, "understood": True, "next_step": "allergies", "reply": "Skipped."}


@pytest.mark.parametrize("step_id", REQUIRED)
@pytest.mark.parametrize("words", ["skip", "I do not know"])
def test_a_required_question_cannot_be_skipped(step_id, words):
    res = ask(step_id, words)                       # the model is not asked for a skip: must_not_run
    assert res["understood"] is False and res["fields"] == {}
    assert res["next_step"] == step_id
    assert res["reply"] == NEEDED_REPLY


def test_an_empty_answer_asks_the_question_again():
    res = ask("birthYear", "   ")
    assert res == {"fields": {}, "understood": False, "next_step": "birthYear", "reply": chat_step("birthYear").ask}


def test_a_required_yes_or_no_question_still_reads_its_own_not_sure_answer():
    res = ask("hasDiabetes", "I don't know")
    assert res["understood"] is True and res["fields"] == {"hasDiabetes": "not_sure"}


# ------------------------------------------------------------------ the lab rules: the date, the unit, the required date
def test_a_lab_value_needs_the_blood_test_date_first():
    res = ask("fastingInsulin", "11.5", {"birthYear": "1968"})
    assert res["understood"] is False and res["reply"] == "Enter the date of your blood test."
    res = ask("fastingInsulin", "11.5", {"labDate": "2026-03-12"})
    assert res["understood"] is True


def test_a_plain_hba1c_with_no_unit_is_read_in_the_unit_the_form_shows():
    # the form shows % by default; a value out of that range is asked again with the unit named
    assert ask("hba1c", "7.2", {**KNOWN, "hba1cUnit": "%"})["fields"] == {"hba1c": "7.2", "hba1cUnit": "%"}
    assert ask("hba1c", "55", {**KNOWN, "hba1cUnit": "mmol/mol"})["fields"] == {"hba1c": "55", "hba1cUnit": "mmol/mol"}


def test_the_model_only_reads_a_sentence_the_rules_cannot_and_its_value_is_checked():
    calls = []

    def fake(text, st):
        calls.append(st.id)
        return {"conditions": "hypertension, heart_failure"}

    res = answer_step("conditions", "my blood pressure runs high and my heart is weak", LABELS, THIS_YEAR, extract=fake, known=KNOWN, today=TODAY)
    assert calls == ["conditions"]
    assert res["understood"] is True and sorted(res["fields"]["conditions"]) == ["heart_failure", "hypertension"]


def test_the_model_value_for_another_question_is_stored_only_when_it_passes_the_checks():
    # one message can answer more than the question asked; a value that fails its check is not stored
    got = {"name": "Ahmad", "birthYear": "2015", "contactPhone": "999"}
    res = answer_step("name", "I'm Ahmad, born 2015", LABELS, THIS_YEAR, extract=lambda *_: got, known={}, today=TODAY)
    assert res["understood"] is True and res["fields"] == {"name": "Ahmad"}


def test_a_sentence_about_an_allergy_goes_to_the_model_and_the_substance_and_reaction_are_read_from_it():
    calls = []

    def fake(text, st):
        calls.append(st.id)
        return {"allergies": "penicillin (rash)"}

    res = answer_step("allergies", "I react badly to penicillin, it gives me a rash", LABELS, THIS_YEAR, extract=fake, known=KNOWN, today=TODAY)
    assert calls == ["allergies"]
    assert res["understood"] is True
    assert res["fields"] == {"allergies": [{"substance": "penicillin", "reaction": "rash"}], "noAllergies": False}


def test_a_long_allergy_sentence_asks_again_when_the_model_is_unavailable():
    res = ask("allergies", "I react badly to penicillin, it gives me a rash", extract=lambda *_: None)
    assert res["understood"] is False and res["fields"] == {} and res["reply"] == FALLBACK_REPLY


def test_free_text_and_allergies_are_taken_only_from_the_question_asked():
    got = {"conditions": "hypertension", "otherConditions": "heart is weak", "allergies": "penicillin (rash)"}
    res = answer_step("conditions", "my blood pressure runs high and my heart is weak", LABELS, THIS_YEAR, extract=lambda *_: got, known=KNOWN, today=TODAY)
    assert res["understood"] is True and res["fields"] == {"conditions": ["hypertension"]}


def test_a_model_problem_for_the_question_asked_is_said_plainly():
    res = answer_step("birthYear", "born in the year 2015 I think", LABELS, THIS_YEAR, extract=lambda *_: {"birthYear": "2015"}, known={}, today=TODAY)
    assert res["understood"] is False and res["reply"] == "Smart Health is for adults aged 18 or older."


def test_when_the_model_is_unavailable_the_person_is_sent_to_the_form():
    res = ask("gender", "I am a bloke", extract=lambda *_: None)
    assert res == {"fields": {}, "understood": False, "next_step": "gender", "reply": FALLBACK_REPLY}
    res = ask("careSetting", "my clinic is near the bus stop", extract=lambda *_: {})
    assert res["understood"] is False and res["reply"] == FALLBACK_REPLY


def test_the_plain_rules_answer_first_and_the_model_is_not_called():
    res = ask("birthYear", "1968")
    assert res["understood"] is True and res["fields"] == {"birthYear": "1968"}


def test_an_unknown_question_is_refused():
    with pytest.raises(svc.OnboardingError, match="not a question of the chat setup"):
        answer_step("notAStep", "x", LABELS, THIS_YEAR)


# ------------------------------------------------------------------ the reader on its own (dates, times, days)
@pytest.mark.parametrize(
    ("step_id", "text", "value"),
    [
        ("labDate", "31 Feb 2026", None),
        ("labDate", "March 2026", None),
        ("workStart", "7pm", "19:00"),
        ("workStart", "12am", "00:00"),
        ("workStart", "13:00 pm", None),
        ("workDays", "every day", [1, 2, 3, 4, 5, 6, 7]),
        ("workDays", "weekends", [6, 7]),
        ("workDays", "Fri to Mon", [1, 5, 6, 7]),
    ],
)
def test_the_plain_readers_for_dates_times_and_days(step_id, text, value):
    got = read_fields(step(step_id), text, KNOWN)
    if value is None:
        assert got is None
    else:
        assert got == {step_id: value}


# ------------------------------------------------------------------ no advice wording
FORBIDDEN = re.compile(r"\b(stop|safe|normal|abnormal|caused by|you should|dose|increase|decrease|treatment|take|change|diagnos\w*)\b", re.I)


def test_no_question_or_reply_gives_advice_or_judges_a_value():
    texts = [s.ask for s in CHAT_STEPS] + [FALLBACK_REPLY, NEEDED_REPLY, *UNIT_HINT.values(), "Skipped.", "Got it.", "Thanks, Ahmad."]
    texts += [reply for *_, reply in INVALID]
    texts += [svc.CHAT_PROMPT.split("\n")[0]]
    for text in texts:
        assert not FORBIDDEN.search(text), text


# ------------------------------------------------------------------ the model path, with the model faked
def test_an_unknown_enum_from_the_model_is_not_guessed():
    res = answer_step("gender", "I am a robot", LABELS, THIS_YEAR, extract=lambda *_: {"gender": "robot"}, known={}, today=TODAY)
    assert res["understood"] is False and res["fields"] == {}
    assert res["next_step"] == "gender" and res["reply"] == FALLBACK_REPLY


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
    res = answer_step("name", "I am Ahmad, born in 1968", LABELS, THIS_YEAR, known={}, today=TODAY)   # a sentence the rules cannot read
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
    assert res.json() == {"fields": {"name": "Ahmad"}, "understood": True, "nextStep": "reminderEmail", "reply": "Thanks, Ahmad."}
    assert client.state["conn"].writes() == []


def test_the_known_answers_from_the_form_are_used_for_a_lab_value(client):
    body = {"text": "7.2%", "step": "hba1c", "known": {"labDate": "", "hba1cUnit": "%"}}
    res = client.post("/api/v1/onboarding/chat", json=body)
    assert res.json()["understood"] is False and res.json()["reply"] == "Enter the date of your blood test."
    body["known"]["labDate"] = "2026-03-12"
    res = client.post("/api/v1/onboarding/chat", json=body)
    assert res.json()["understood"] is True and res.json()["fields"] == {"hba1c": "7.2", "hba1cUnit": "%"}
    assert client.state["conn"].writes() == []


def test_a_list_answer_comes_back_as_a_list(client):
    res = client.post("/api/v1/onboarding/chat", json={"text": "none", "step": "allergies"})
    assert res.json() == {"fields": {"allergies": [], "noAllergies": True}, "understood": True, "nextStep": "eyeCheck", "reply": "Got it."}


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
