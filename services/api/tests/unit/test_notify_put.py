"""PUT /notify/email before the profile exists (the Welcome page, before the first save): refused with 409, never reported as saved.

The database is a fake: it answers the three queries the route makes and records the writes.
"""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers import notify as router_mod
from app.db import logstore
from app.services import notify_email as svc

USER = str(uuid4())


class Result:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConn:
    def __init__(self, profile: dict | None, log: dict):
        self.profile = profile          # the user_profile row, or None when the person has no profile yet
        self.log = log                  # every write made through any transaction in the test

    def execute(self, sql, params=()):
        flat = " ".join(sql.split())
        if flat.startswith("select 1 from user_profile"):
            return Result(None if self.profile is None else {"?column?": 1})
        if flat.startswith("select notification_email"):
            return Result(self.profile)
        if flat.startswith("update user_profile"):
            self.log["updates"].append(tuple(params))
            if self.profile is not None:
                self.profile["notification_email"], self.profile["email_opt_in"] = params[0], params[1]
            return Result(None)
        if flat.startswith("insert into event_log"):
            self.log["events"].append(flat)
            return Result(None)
        raise AssertionError(f"unexpected statement: {flat}")


@pytest.fixture
def db(monkeypatch):
    state = {"profile": None, "log": {"updates": [], "events": []}}

    @contextmanager
    def fake_tx():
        conn = FakeConn(state["profile"], state["log"])
        yield conn
        if conn.profile is not None:            # the fake commits on a clean exit, like the real transaction
            state["profile"] = conn.profile

    monkeypatch.setattr(logstore, "tx", fake_tx)
    monkeypatch.setattr(logstore, "current_user", lambda: USER)
    monkeypatch.setattr(svc, "columns_ready", lambda conn=None: True)
    monkeypatch.setattr(router_mod.WorkatoEmail, "from_settings", staticmethod(lambda: SimpleNamespace(configured=False)))
    return state


@pytest.fixture
def client(db):
    app = FastAPI()
    app.include_router(router_mod.router, prefix="/api/v1")
    return TestClient(app)


def test_put_for_a_person_with_no_profile_is_refused_and_nothing_is_written(client, db):
    res = client.put("/api/v1/notify/email", json={"email": "name@gmail.com", "optIn": True})
    assert res.status_code == 409
    assert "not created" in res.json()["detail"]
    assert db["log"]["updates"] == [] and db["log"]["events"] == []


def test_the_email_is_not_reported_as_stored_for_a_person_with_no_profile(client, db):
    assert client.get("/api/v1/notify/email").json()["email"] is None
    client.put("/api/v1/notify/email", json={"email": "name@gmail.com", "optIn": True})
    assert client.get("/api/v1/notify/email").json()["email"] is None


def test_put_once_the_profile_exists_stores_the_email_and_logs_it(client, db):
    db["profile"] = {"notification_email": None, "email_opt_in": True}
    res = client.put("/api/v1/notify/email", json={"email": "  name@gmail.com ", "optIn": True})
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == "name@gmail.com" and body["optIn"] is True
    assert db["log"]["updates"] == [("name@gmail.com", True, USER)]
    assert len(db["log"]["events"]) == 1 and "notify.email_changed" in db["log"]["events"][0]


def test_a_blank_box_clears_the_email_once_the_profile_exists(client, db):
    db["profile"] = {"notification_email": "old@gmail.com", "email_opt_in": True}
    res = client.put("/api/v1/notify/email", json={"email": "  ", "optIn": False})
    assert res.status_code == 200
    assert res.json()["email"] is None and res.json()["optIn"] is False


def test_a_bad_address_is_refused_before_the_database_is_asked(client, db):
    res = client.put("/api/v1/notify/email", json={"email": "not an email", "optIn": True})
    assert res.status_code == 422
    assert db["log"]["updates"] == []
