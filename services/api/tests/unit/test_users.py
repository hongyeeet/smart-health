"""Starting a new person: the key rules in logstore and POST /api/v1/users. The database is a fake that records each statement."""
from __future__ import annotations

import uuid
from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers import users as users_mod
from app.db import logstore


class _RecordingConn:
    def __init__(self, calls: list):
        self.calls = calls

    def execute(self, sql, params=()):
        self.calls.append((" ".join(sql.split()), params))


@pytest.fixture
def writes(monkeypatch):
    calls: list = []

    @contextmanager
    def fake_tx():
        yield _RecordingConn(calls)

    monkeypatch.setattr(logstore, "tx", fake_tx)
    return calls


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(users_mod.router, prefix="/api/v1")
    return TestClient(app)


def test_a_person_key_is_accepted_and_maps_to_a_stable_user_id():
    key = logstore.new_person_key()
    assert logstore.PERSON_KEY.fullmatch(key)
    token = logstore._current.set("demo")
    try:
        assert logstore.set_user(key) == key
        assert logstore.current_user() == logstore.person_id(key)
        assert logstore.current_user() == logstore.person_id(key)               # the same key, the same person
    finally:
        logstore._current.reset(token)


def test_a_new_person_is_never_mr_tan_or_the_demo_user():
    key = logstore.new_person_key()
    assert logstore.person_id(key) not in {logstore.MR_TAN_USER, logstore.APP_USER}
    assert logstore.new_person_key() != key


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


def test_post_users_creates_only_the_user_row_for_the_new_key(client, writes):
    res = client.post("/api/v1/users")
    assert res.status_code == 200
    body = res.json()
    assert logstore.PERSON_KEY.fullmatch(body["key"]) and body["label"] == "New person"
    assert len(writes) == 1
    sql, params = writes[0]
    assert sql.startswith("insert into users") and "is_demo" in sql and "false" in sql
    assert params == (logstore.person_id(body["key"]),)
    assert isinstance(params[0], uuid.UUID)
    assert all(not s.startswith(("update", "delete")) for s, _ in writes)     # nothing existing is touched
