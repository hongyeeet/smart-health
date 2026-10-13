"""GET/POST /notifications: clean errors, no writes for Mr Tan, a short cache. No database."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers import notifications as route
from app.db import logstore


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(route.router)
    route.invalidate()
    calls = []
    monkeypatch.setattr(logstore, "notifications", lambda create=True, history=False: calls.append(("history", create) if history else create) or [])
    monkeypatch.setattr(logstore, "open_notification", lambda nid: calls.append(("open", nid)))
    monkeypatch.setattr(logstore, "dismiss_notification", lambda nid: calls.append(("dismiss", nid)))
    yield TestClient(app), calls
    logstore.set_user("demo")
    route.invalidate()


def test_a_bad_id_is_a_plain_404_not_a_500(client):
    c, calls = client
    for verb in ("open", "dismiss"):
        r = c.post(f"/notifications/not-a-uuid/{verb}")
        assert r.status_code == 404 and r.json()["detail"] == "That reminder was not found."
    assert calls == []


def test_a_good_id_still_works(client):
    c, calls = client
    assert c.post("/notifications/6f1c2d3e-4a5b-5c6d-8e7f-9a0b1c2d3e4f/open").status_code == 204
    assert calls == [("open", "6f1c2d3e-4a5b-5c6d-8e7f-9a0b1c2d3e4f")]


def test_a_get_writes_nothing_for_mr_tan_and_may_for_the_demo_user(client):
    c, calls = client
    logstore.set_user("mr-tan")
    c.get("/notifications")
    logstore.set_user("demo")
    c.get("/notifications")
    assert calls == [False, True]


def test_the_list_is_cached_for_a_short_time_and_a_tap_clears_it(client):
    c, calls = client
    c.get("/notifications")
    c.get("/notifications")
    assert calls == [True]
    c.post("/notifications/6f1c2d3e-4a5b-5c6d-8e7f-9a0b1c2d3e4f/dismiss")
    c.get("/notifications")
    assert calls.count(True) == 2


def test_the_reminders_page_list_is_its_own_read_and_writes_nothing_for_mr_tan(client):
    c, calls = client
    logstore.set_user("mr-tan")
    c.get("/notifications/history")
    logstore.set_user("demo")
    c.get("/notifications/history")
    c.get("/notifications")
    assert calls == [("history", False), ("history", True), True]          # the Home list and the page list are cached apart


def test_opening_a_reminder_clears_both_cached_lists(client):
    c, calls = client
    c.get("/notifications")
    c.get("/notifications/history")
    c.post("/notifications/6f1c2d3e-4a5b-5c6d-8e7f-9a0b1c2d3e4f/open")
    c.get("/notifications")
    c.get("/notifications/history")
    assert calls.count(True) == 2 and calls.count(("history", True)) == 2
