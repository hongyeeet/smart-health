"""Who the app can act as: the demo user, Mr Tan, and a person started with "Start as new person" (POST /api/v1/users, only when set-up is finished).
The database is a fake that records each statement."""
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
    token = logstore._current.set("demo")
    try:
        assert logstore.set_user(KEY) == KEY
        assert logstore.current_user() == logstore.person_id(KEY)
        assert logstore.current_user() == logstore.person_id(KEY)               # the same key, the same person
    finally:
        logstore._current.reset(token)


def test_a_new_person_is_never_mr_tan_or_the_demo_user():
    assert logstore.person_id(KEY) not in {logstore.MR_TAN_USER, logstore.APP_USER}
    assert logstore.person_id(KEY) != logstore.person_id("person-ba9876543210")


@pytest.mark.parametrize("bad", ["salary", "person-XYZ", "person-0123", "../mr-tan", "person-0123456789ab-extra"])
def test_an_unknown_or_malformed_key_is_still_refused(bad):
    token = logstore._current.set("demo")
    try:
        with pytest.raises(KeyError):
            logstore.set_user(bad)
        assert logstore.current_user_key() == "demo"                           # a refused key never changes who is acting
    finally:
        logstore._current.reset(token)


def test_the_known_users_are_unchanged():
    assert set(logstore.USERS) == {"demo", "mr-tan"}
    assert logstore.USERS["mr-tan"]["id"] == logstore.MR_TAN_USER


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
