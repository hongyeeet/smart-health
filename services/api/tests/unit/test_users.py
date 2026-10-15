"""Who the app can act as: Mr Tan (the example record everyone sees first, never changed by a request) and the people started with "Start as
new person" (POST /api/v1/users, only when set-up is finished). There is no demo user. The database is a fake that records each statement."""
from __future__ import annotations

import uuid
from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers import users as users_mod
from app.db import logstore

KEY = "person-0123456789ab"


class _Result:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class _RecordingConn:
    def __init__(self, calls: list, row):
        self.calls, self.row = calls, row

    def execute(self, sql, params=()):
        self.calls.append((" ".join(sql.split()), params))
        return _Result(self.row)


@pytest.fixture
def writes(monkeypatch):
    calls: list = []
    row = {"id": "x"}                 # the insert made a row; set to None for "already there"

    @contextmanager
    def fake_tx():
        yield _RecordingConn(calls, row)

    monkeypatch.setattr(logstore, "tx", fake_tx)
    return calls


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(users_mod.router, prefix="/api/v1")
    return TestClient(app)


def test_a_person_key_is_accepted_and_maps_to_a_stable_user_id():
    token = logstore._current.set("mr-tan")
    try:
        assert logstore.set_user(KEY) == KEY
        assert logstore.current_user() == logstore.person_id(KEY)
        assert logstore.current_user() == logstore.person_id(KEY)               # the same key, the same person
    finally:
        logstore._current.reset(token)


def test_a_new_person_is_never_mr_tan():
    assert logstore.person_id(KEY) != logstore.MR_TAN_USER
    assert logstore.person_id(KEY) != logstore.person_id("person-ba9876543210")


def test_no_key_means_mr_tan_and_there_is_no_demo_user():
    token = logstore._current.set(KEY)
    try:
        assert logstore.set_user(None) == "mr-tan" and logstore.current_user() == logstore.MR_TAN_USER
        with pytest.raises(KeyError):
            logstore.set_user("demo")
        assert logstore.current_user_key() == "mr-tan"
    finally:
        logstore._current.reset(token)


@pytest.mark.parametrize("bad", ["salary", "demo", "person-XYZ", "person-0123", "../mr-tan", "person-0123456789ab-extra"])
def test_an_unknown_or_malformed_key_is_still_refused(bad):
    token = logstore._current.set("mr-tan")
    try:
        with pytest.raises(KeyError):
            logstore.set_user(bad)
        assert logstore.current_user_key() == "mr-tan"                         # a refused key never changes who is acting
    finally:
        logstore._current.reset(token)


def test_the_known_users_are_only_mr_tan():
    assert set(logstore.USERS) == {"mr-tan"}
    assert logstore.USERS["mr-tan"]["id"] == logstore.MR_TAN_USER


def test_a_job_can_act_as_a_person_by_user_id_but_a_request_header_cannot():
    uid = logstore.person_id(KEY)
    ik = logstore.internal_key(uid)
    token = logstore._current.set("mr-tan")
    try:
        with pytest.raises(KeyError):
            logstore.set_user(ik)                                              # the header route refuses it
        assert logstore.set_user(ik, internal=True) == ik and logstore.current_user() == uid
        assert logstore.user_id_for_key("mr-tan") == logstore.MR_TAN_USER and logstore.user_id_for_key(KEY) == uid
        with pytest.raises(KeyError):
            logstore.user_id_for_key("uid:not-a-uuid")
    finally:
        logstore._current.reset(token)


def test_post_users_creates_only_the_user_row_for_the_key(client, writes):
    res = client.post("/api/v1/users", json={"key": KEY})
    assert res.status_code == 200
    assert res.json() == {"key": KEY, "created": True}
    assert len(writes) == 1
    sql, params = writes[0]
    assert sql.startswith("insert into users") and "is_demo" in sql and "false" in sql
    assert params == (logstore.person_id(KEY),)
    assert isinstance(params[0], uuid.UUID)
    assert all(not s.startswith(("update", "delete")) for s, _ in writes)     # nothing existing is touched


@pytest.mark.parametrize("bad", ["demo", "mr-tan", "person-xyz", "", "person-0123456789abc"])
def test_post_users_refuses_a_key_that_is_not_a_new_persons(client, writes, bad):
    res = client.post("/api/v1/users", json={"key": bad})
    assert res.status_code == 400
    assert writes == []


# ------------------------------------------------------------------ Mr Tan's example record is never written by a request
def test_a_request_that_would_change_mr_tan_is_refused_but_reading_and_asking_are_not():
    from app.main import app

    c = TestClient(app, raise_server_exceptions=False)
    for method, path in [("post", "/api/v1/logs"), ("delete", "/api/v1/medications/x"), ("put", "/api/v1/me/language"), ("post", "/api/v1/doses/x/taken"),
                         ("post", "/api/v1/notifications/x/dismiss")]:
        for headers in ({"X-User": "mr-tan"}, {}):                              # naming him, or naming nobody, is the same
            r = getattr(c, method)(path, headers=headers, **({"json": {}} if method != "delete" else {}))
            assert r.status_code == 403 and "example record" in r.json()["detail"], (method, path, headers)
    assert c.get("/api/v1/users").status_code == 200


def test_mr_tan_may_still_be_asked_questions_and_have_a_reminder_opened():
    from app.main import app

    c = TestClient(app, raise_server_exceptions=False)
    for path in ("/api/v1/chat/route", "/api/v1/onboarding/chat", "/api/v1/notifications/abc/open"):
        r = c.post(path, headers={"X-User": "mr-tan"}, json={})
        assert r.status_code != 403, path                                       # it may fail for another reason (bad body, no database) but is not refused as a write
