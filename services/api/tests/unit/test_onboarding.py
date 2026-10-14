"""Onboarding save: the checks (pure), the upsert and consent SQL (fake connection), and the emergency-email column with and without 0031."""
from __future__ import annotations

from datetime import datetime, time, timezone
from uuid import uuid4

import pytest

from app.schemas.onboarding import ProfileIn
from app.services import onboarding as svc

LABELS = {
    "gender_type": frozenset({"female", "male", "other", "prefer_not_to_say"}),
    "work_type": frozenset({"desk", "mixed", "standing", "physical", "shift", "not_working"}),
    "locale_code": frozenset({"en", "zh", "ms", "ta"}),
    "yes_no_unsure": frozenset({"yes", "no", "not_sure"}),
}
THIS_YEAR = 2026


class FakeResult:
    def __init__(self, value):
        self.value = value

    def fetchone(self):
        if isinstance(self.value, list):
            return self.value[0] if self.value else None
        return self.value

    def fetchall(self):
        if isinstance(self.value, list):
            return self.value
        return [] if self.value is None else [self.value]


class FakeConn:
    """Answers each query with the first rule whose text it contains. Records every statement it was given."""

    def __init__(self, rules: dict | None = None):
        self.rules = rules or {}
        self.calls: list[tuple[str, tuple]] = []

    def execute(self, sql, params=()):
        flat = " ".join(sql.split())
        self.calls.append((flat, tuple(params)))
        for key, value in self.rules.items():
            if key in flat:
                return FakeResult(value)
        return FakeResult(None)

    def count(self, text: str) -> int:
        return sum(1 for sql, _ in self.calls if text in sql)

    def upserts(self) -> list[str]:
        """Every statement that writes the profile, insert or update."""
        return [sql for sql, _ in self.calls if sql.startswith(("insert into user_profile", "update user_profile"))]


@pytest.fixture(autouse=True)
def _fresh_column_cache():
    svc.reset_email_column_cache()
    yield
    svc.reset_email_column_cache()


USER = uuid4()
EXISTING_PROFILE = {
    "display_name": "Test", "language": "en", "has_diabetes": "yes", "birth_year": 1975, "gender": "male", "race": None,
    "height_cm": None, "weight_kg": None, "work_type": None, "work_days": [], "work_start": time(9, 0), "work_end": None,
    "emergency_contact_name": None, "emergency_contact_phone": None, "emergency_contact_relation": None, "watch_model": None,
    "cgm_model": None, "allergies_note": None, "conditions_note": None, "updated_at": datetime(2026, 10, 9, tzinfo=timezone.utc),
}


def rules(profile=EXISTING_PROFILE, email_column=True, consent=None, exists=True):
    out = {
        "select 1 from user_profile": {"?column?": 1} if exists else None,
        "from user_profile where user_id": profile,
        "from consents where user_id": consent,
        "insert into bronze_profile": {"id": uuid4()},
        "information_schema.columns": {"column_name": "emergency_contact_email"} if email_column else None,
    }
    return out


# ------------------------------------------------------------------ pure checks
def test_known_choices_pass_and_unknown_ones_get_a_plain_message():
    assert svc.unknown_choice_messages({"gender": "female", "work_type": "shift", "language": "ta", "has_diabetes": "not_sure"}, LABELS) == []
    msgs = svc.unknown_choice_messages({"gender": "robot"}, LABELS)
    assert len(msgs) == 1
    assert "gender 'robot' is not a choice" in msgs[0] and "prefer_not_to_say" in msgs[0]


def test_check_profile_reports_each_problem_once():
    assert svc.check_profile({"birth_year": 1968, "work_days": [1, 2, 3], "work_start": "07:30", "work_end": "17:00"}, LABELS, THIS_YEAR) == []
    assert svc.check_profile({"birth_year": 2015}, LABELS, THIS_YEAR) == ["Equinox is for adults aged 18 or older."]
    assert any("cannot be blank" in p for p in svc.check_profile({"display_name": None}, LABELS, THIS_YEAR))
    assert any("1 (Monday) to 7" in p for p in svc.check_profile({"work_days": [0, 8]}, LABELS, THIS_YEAR))
    assert any("like 07:30" in p for p in svc.check_profile({"work_start": "25:00"}, LABELS, THIS_YEAR))
    assert any("name@example.com" in p for p in svc.check_profile({"emergency_contact_email": "not-an-email"}, LABELS, THIS_YEAR))
    assert svc.check_profile({"emergency_contact_email": ""}, LABELS, THIS_YEAR) == []     # a blank optional email is fine


def test_normalise_sorts_days_and_stores_blank_optional_text_as_null():
    out = svc.normalise({"work_days": [5, 1, 5, 3], "race": "", "display_name": ""})
    assert out == {"work_days": [1, 3, 5], "race": None, "display_name": ""}


# ------------------------------------------------------------------ emergency email column (0031 applied or not)
def test_email_column_present_is_detected_once_and_cached():
    conn = FakeConn(rules(email_column=True))
    assert svc.email_column_present(conn) is True
    assert svc.email_column_present(conn) is True
    assert conn.count("information_schema.columns") == 1


def test_email_column_absent_is_detected_once_and_cached():
    conn = FakeConn(rules(email_column=False))
    assert svc.email_column_present(conn) is False
    assert svc.email_column_present(conn) is False
    assert conn.count("information_schema.columns") == 1


def test_save_writes_the_email_only_when_the_column_exists():
    sent = {"emergency_contact_name": "Mei", "emergency_contact_email": "mei@gmail.com"}
    with_col = FakeConn(rules(email_column=True))
    out = svc.save_profile(with_col, USER, sent, LABELS, THIS_YEAR)
    assert "emergency_contact_email = %s" in with_col.upserts()[0]
    assert out["not_saved"] == []

    svc.reset_email_column_cache()
    without = FakeConn(rules(email_column=False))
    out = svc.save_profile(without, USER, sent, LABELS, THIS_YEAR)
    assert "emergency_contact_email" not in without.upserts()[0]
    assert out["not_saved"] == ["emergencyContactEmail"]
    assert "emergency_contact_name = %s" in without.upserts()[0]   # the rest of the save still happens


def test_load_reports_no_email_when_the_column_is_missing():
    conn = FakeConn(rules(email_column=False))
    out = svc.load(conn, USER)
    assert out["email_column"] is False
    assert out["profile"]["emergency_contact_email"] is None
    assert "emergency_contact_email" not in " ".join(sql for sql, _ in conn.calls if "from user_profile where user_id" in sql)


# ------------------------------------------------------------------ upsert: only the sent fields, never blanks
def test_save_writes_only_the_fields_sent_and_never_blanks_the_rest():
    conn = FakeConn(rules())
    svc.save_profile(conn, USER, {"race": "Malay", "work_days": [5, 1]}, LABELS, THIS_YEAR)
    assert len(conn.upserts()) == 1 and conn.upserts()[0].startswith("update user_profile")   # the profile exists
    sql, params = [(s, p) for s, p in conn.calls if s.startswith("update user_profile")][0]
    assert sql == "update user_profile set race = %s, work_days = %s::smallint[], bronze_id = %s where user_id = %s"
    assert "birth_year" not in sql and "emergency_contact_name" not in sql
    assert params == ("Malay", [1, 5], params[2], USER)


def test_a_partial_save_of_an_existing_profile_is_an_update_not_an_insert():
    conn = FakeConn(rules())
    svc.save_profile(conn, USER, {"race": "Indian"}, LABELS, THIS_YEAR)
    assert not any(s.startswith("insert into user_profile") for s, _ in conn.calls)
    assert conn.count("update user_profile set race = %s") == 1


def test_a_sent_null_clears_an_optional_column_but_not_a_required_one():
    conn = FakeConn(rules())
    svc.save_profile(conn, USER, {"gender": None}, LABELS, THIS_YEAR)
    assert conn.upserts()[0] == "update user_profile set gender = %s, bronze_id = %s where user_id = %s"
    with pytest.raises(svc.OnboardingError, match="birth year cannot be blank"):
        svc.save_profile(FakeConn(rules()), USER, {"birth_year": None}, LABELS, THIS_YEAR)


def test_first_save_needs_birth_year_and_diabetes_answer():
    conn = FakeConn(rules(exists=False))
    with pytest.raises(svc.OnboardingError, match="Enter birth year and has diabetes to finish setup."):
        svc.save_profile(conn, USER, {"race": "Malay"}, LABELS, THIS_YEAR)
    assert conn.upserts() == []                                # nothing written when the check fails


def test_first_save_with_the_required_answers_creates_the_profile_and_a_bronze_row():
    conn = FakeConn(rules(exists=False))
    svc.save_profile(conn, USER, {"birth_year": 1968, "has_diabetes": "yes"}, LABELS, THIS_YEAR)
    assert conn.count("insert into bronze_profile") == 1
    assert conn.count("update bronze_profile set processing_status = 'processed'") == 1
    params = [p for sql_, p in conn.calls if sql_.startswith("insert into user_profile")][0]
    # display_name is NOT NULL: a blank name is stored as empty text, not null
    assert "display_name" in conn.upserts()[0] and params[2] == ""


def test_unknown_enum_is_refused_before_any_write():
    conn = FakeConn(rules())
    with pytest.raises(svc.OnboardingError, match="gender 'robot' is not a choice"):
        svc.save_profile(conn, USER, {"gender": "robot"}, LABELS, THIS_YEAR)
    assert conn.upserts() == [] and conn.count("insert into bronze_profile") == 0


def test_work_times_are_written_as_clock_times():
    conn = FakeConn(rules())
    svc.save_profile(conn, USER, {"work_start": "22:00", "work_end": "06:00"}, LABELS, THIS_YEAR)
    assert "work_start = %s::time, work_end = %s::time" in conn.upserts()[0]


def test_load_returns_times_as_text_and_days_as_a_list():
    out = svc.load(FakeConn(rules()), USER)
    assert out["profile"]["work_start"] == "09:00" and out["profile"]["work_end"] is None
    assert out["profile"]["work_days"] == []
    assert out["data_consent"] is False


# ------------------------------------------------------------------ completion: consent and event
def test_complete_records_consent_and_an_event_when_none_is_active():
    now = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)
    conn = FakeConn(rules(consent=None))
    out = svc.complete(conn, USER, now)
    assert out == {"consent_recorded": True, "completed_at": now}
    assert conn.count("insert into consents") == 1
    assert conn.count("insert into event_log") == 1
    consent_params = [p for sql_, p in conn.calls if sql_.startswith("insert into consents")][0]
    assert consent_params == (USER, "data_processing", "v1", now)


def test_complete_does_not_duplicate_an_active_consent():
    conn = FakeConn(rules(consent={"?column?": 1}))
    out = svc.complete(conn, USER, datetime(2026, 10, 10, tzinfo=timezone.utc))
    assert out["consent_recorded"] is False
    assert conn.count("insert into consents") == 0
    assert conn.count("insert into event_log") == 1


def test_complete_needs_a_saved_profile_first():
    conn = FakeConn(rules(exists=False))
    with pytest.raises(svc.OnboardingError, match="Save your answers before you finish setup."):
        svc.complete(conn, USER, datetime(2026, 10, 10, tzinfo=timezone.utc))
    assert conn.count("insert into consents") == 0 and conn.count("insert into event_log") == 0


# ------------------------------------------------------------------ request shape
def test_request_fields_are_read_only_when_sent_and_accept_camel_case():
    body = ProfileIn.model_validate({"birthYear": 1968, "workDays": [1, 2]})
    assert body.model_dump(exclude_unset=True) == {"birth_year": 1968, "work_days": [1, 2]}


def test_request_rejects_an_out_of_range_height_before_the_database():
    with pytest.raises(Exception):
        ProfileIn.model_validate({"heightCm": 900})


# ------------------------------------------------------------------ the router, with the database replaced by the fake
ENUM_ROWS = [{"typname": k, "enumlabel": v} for k, vs in LABELS.items() for v in sorted(vs)]


@pytest.fixture
def client(monkeypatch):
    from contextlib import contextmanager

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.routers import onboarding as router_mod
    from app.db import logstore

    state = {"rules": rules()}

    @contextmanager
    def fake_tx():
        conn = FakeConn({**state["rules"], "pg_enum": ENUM_ROWS})
        state["conn"] = conn
        yield conn

    monkeypatch.setattr(logstore, "tx", fake_tx)
    app = FastAPI()
    app.include_router(router_mod.router, prefix="/api/v1")
    c = TestClient(app)
    c.state = state                                       # type: ignore[attr-defined]
    return c


def test_get_returns_camel_case_and_no_profile_for_a_new_person(client):
    client.state["rules"] = rules(exists=False, profile=None, consent=None, email_column=False)
    body = client.get("/api/v1/onboarding").json()
    assert {k: body[k] for k in ("profile", "dataConsent", "emailColumn")} == {"profile": None, "dataConsent": False, "emailColumn": False}
    assert body["historyReady"] is False and body["history"]["conditions"] == [] and body["history"]["waistCm"] is None


def test_put_profile_refuses_an_unknown_choice_with_a_plain_422(client):
    res = client.put("/api/v1/onboarding/profile", json={"gender": "robot"})
    assert res.status_code == 422
    assert "gender 'robot' is not a choice Equinox knows" in res.json()["detail"]


def test_put_profile_saves_and_reports_fields_that_could_not_be_stored(client):
    client.state["rules"] = rules(email_column=False)
    res = client.put("/api/v1/onboarding/profile", json={"race": "Malay", "emergencyContactEmail": "a@gmail.com"})
    assert res.status_code == 200
    body = res.json()
    assert body["notSaved"] == ["emergencyContactEmail"]
    assert body["profile"]["displayName"] == "Test" and body["profile"]["workStart"] == "09:00"


def test_put_first_profile_without_required_answers_is_422(client):
    client.state["rules"] = rules(exists=False, profile=None)
    res = client.put("/api/v1/onboarding/profile", json={"race": "Malay"})
    assert res.status_code == 422
    assert "birth year and has diabetes" in res.json()["detail"]


def test_complete_without_a_profile_is_422(client):
    client.state["rules"] = rules(exists=False)
    res = client.post("/api/v1/onboarding/complete")
    assert res.status_code == 422
    assert res.json()["detail"] == "Save your answers before you finish setup."
