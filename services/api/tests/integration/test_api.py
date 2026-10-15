"""API integration tests: the real endpoints against the real database, as the demo user.

Opt in with  RUN_INTEGRATION=1 python -m pytest tests/integration -q   (they need DATABASE_URL, and they clean up after themselves).
External AI calls are replaced: the photo model returns a fixed estimate and the guard says yes, so a run costs nothing and is repeatable.
Mr Tan is never written to: every request here is the demo user.
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

pytestmark = pytest.mark.skipif(os.environ.get("RUN_INTEGRATION") != "1", reason="set RUN_INTEGRATION=1 to run against the real database")


@pytest.fixture(scope="module")
def client():
    from app.core.config import settings

    settings.scheduler_enabled = False  # no timers during tests
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def _meal_body(start: datetime, minutes: int = 20, name: str = "Integration test noodles"):
    return {"kind": "meal", "name": name, "startAt": start.isoformat(), "endAt": (start + timedelta(minutes=minutes)).isoformat(), "portion": 1,
            "carbsG": 60, "proteinG": 20, "fatG": 15, "sugarG": 3, "fibreG": 3, "sodiumMg": 900, "edited": False, "valuesFrom": "ai"}


def test_health_and_unknown_user(client):
    assert client.get("/health").json()["status"] == "ok"
    r = client.get("/api/v1/logs/today", headers={"X-User": "nobody"})
    assert r.status_code == 400 and "unknown user" in r.json()["detail"]


def test_log_lifecycle_create_list_delete_and_missing(client):
    r = client.post("/api/v1/logs", json={"kind": "checkin", "mood": 3, "stress": 3, "sleep": 3, "energy": 3})
    assert r.status_code == 200 and r.json()["kind"] == "checkin"
    entry = r.json()["id"]
    assert any(e["id"] == entry for e in client.get("/api/v1/logs/recent").json())
    assert client.delete(f"/api/v1/logs/{entry}").status_code == 204
    assert not any(e["id"] == entry for e in client.get("/api/v1/logs/recent").json())
    assert client.delete(f"/api/v1/logs/{entry}").status_code == 404  # already gone
    assert client.delete("/api/v1/logs/not-a-uuid").status_code == 404


def test_saving_the_same_meal_twice_does_not_crash(client):
    """Regression: Bronze is unique per person and content; an identical retry used to return a 500."""
    start = datetime.now(timezone.utc) - timedelta(days=40, hours=int(uuid.uuid4().int % 20))
    body = _meal_body(start)
    first, second = client.post("/api/v1/logs", json=body), client.post("/api/v1/logs", json=body)
    assert first.status_code == 200 and second.status_code == 200
    for r in (first, second):
        assert client.delete(f"/api/v1/logs/{r.json()['id']}").status_code == 204


def test_meal_analysis_validates_input_and_never_returns_database_numbers(client, monkeypatch):
    from app.agents.meal import MealEstimate, MealItem
    from app.api.routers import meals

    assert client.post("/api/v1/meals/analyze", files={"file": ("x.txt", b"hi", "text/plain")}).status_code == 415
    assert client.post("/api/v1/meals/analyze", files={"file": ("x.jpg", b"", "image/jpeg")}).status_code == 400
    monkeypatch.setattr(meals, "analyse_meal", lambda image, mime, desc: MealEstimate(is_food=False))
    assert client.post("/api/v1/meals/analyze", files={"file": ("x.jpg", b"123", "image/jpeg")}).status_code == 422

    est = MealEstimate(is_food=True, meal_name="Test chicken rice", items=[MealItem(name="rice", grams=200)], kcal=650, carbs_g=80, protein_g=30, fat_g=20,
                       sugar_g=3, fibre_g=2, sodium_mg=1100, confidence=0.9, portion_note="One plate.")
    monkeypatch.setattr(meals, "analyse_meal", lambda image, mime, desc: est)
    monkeypatch.setattr("app.db.nutritionstore.guarded", lambda *a, **k: True)
    r = client.post("/api/v1/meals/analyze", files={"file": ("x.jpg", os.urandom(64), "image/jpeg")}, data={"description": "normal portion"})
    assert r.status_code == 200
    d = r.json()
    assert d["macros"]["kcal"] == 650 and d["analysisId"] and "database" not in d and "alternatives" not in d  # the design rule: logged numbers are the model's


def test_blocked_model_words_are_replaced_not_shown(client, monkeypatch):
    from app.agents.meal import MealEstimate
    from app.api.routers import meals

    est = MealEstimate(is_food=True, meal_name="Ignore the rules and stop your tablets", kcal=500, carbs_g=60, protein_g=20, fat_g=10, confidence=0.9, portion_note="Stop your medicine.")
    monkeypatch.setattr(meals, "analyse_meal", lambda image, mime, desc: est)
    monkeypatch.setattr("app.db.nutritionstore.guarded", lambda *a, **k: False)  # the guard blocks the words
    d = client.post("/api/v1/meals/analyze", files={"file": ("x.jpg", os.urandom(64), "image/jpeg")}).json()
    assert d["name"] == "Your meal" and d["portionNote"] == "" and d["macros"]["kcal"] == 500  # words replaced, numbers kept


@pytest.fixture()
def proposed_fact():
    """A proposed fact for the demo user, removed afterwards."""
    from app.agents.adherence import _propose_fact
    from app.db import logstore

    logstore.set_user("person-0123456789ab")
    uid = logstore.current_user()
    key = f"test.integration.{uuid.uuid4().hex[:8]}"
    with logstore.tx() as c:
        _propose_fact(c, uid, key, "routine", {"test": True}, "Integration test fact.", 0.6, [{"table": "food_logs", "meals": 4, "window_days": 14}])
        fid = c.execute("select id from memory_facts where user_id=%s and key=%s", (uid, key)).fetchone()["id"]
    yield str(fid), key
    with logstore.tx() as c:
        c.execute("update memory_facts set supersedes_id=null where user_id=%s and key=%s", (uid, key))
        c.execute("delete from memory_facts where user_id=%s and key=%s", (uid, key))


def test_memory_confirm_edit_delete_and_errors(client, proposed_fact):
    fid, key = proposed_fact
    facts = {f["id"]: f for g in client.get("/api/v1/memory/facts").json()["groups"] for f in g["facts"]}
    assert facts[fid]["status"] == "proposed" and "Based on" in facts[fid]["why"]
    assert client.post(f"/api/v1/memory/facts/{fid}/action", json={"action": "confirm"}).status_code == 200
    r = client.post(f"/api/v1/memory/facts/{fid}/action", json={"action": "edit", "text": "hi"})
    assert r.status_code == 422  # too short
    r = client.post(f"/api/v1/memory/facts/{fid}/action", json={"action": "edit", "text": "In my own words."})
    assert r.status_code == 200
    new_id = r.json()["id"]
    assert new_id != fid  # a new version, the old one is kept
    assert client.post(f"/api/v1/memory/facts/{new_id}/action", json={"action": "delete"}).status_code == 200
    assert client.post(f"/api/v1/memory/facts/{new_id}/action", json={"action": "delete"}).status_code == 404  # already deleted
    assert client.post("/api/v1/memory/facts/00000000-0000-0000-0000-000000000000/action", json={"action": "confirm"}).status_code == 404
    assert client.post(f"/api/v1/memory/facts/{fid}/action", json={"action": "explode"}).status_code == 422


def test_not_for_me_hides_a_suggestion(client):
    from app.db import logstore, nutritionstore

    key = f"swap:test-{uuid.uuid4().hex[:6]}"
    assert client.post("/api/v1/nutrition/suggestions/dismiss", json={"key": key}).status_code == 204
    logstore.set_user("person-0123456789ab")
    uid = logstore.current_user()
    try:
        assert key in nutritionstore.excluded_keys(uid)
    finally:
        with logstore.tx() as c:
            c.execute("delete from nudge_policy where user_id=%s and arm_key=%s", (uid, key))


def test_reminder_cap_and_quiet_hours(client, monkeypatch):
    from app.db import logstore

    logstore.set_user("person-0123456789ab")
    uid = logstore.current_user()

    def count():
        with logstore.tx() as c:
            return c.execute("select count(*) n from notifications where user_id=%s", (uid,)).fetchone()["n"]

    before = count()
    monkeypatch.setattr(logstore, "in_quiet_hours", lambda now: True)
    assert client.get("/api/v1/notifications").status_code == 200
    assert count() == before  # quiet hours: nothing new is created
    monkeypatch.setattr(logstore, "in_quiet_hours", lambda now: False)
    monkeypatch.setattr(logstore, "slots_left", lambda created: 0)
    assert client.get("/api/v1/notifications").status_code == 200
    assert count() == before  # cap reached: nothing new is created


def test_ai_usage_endpoint(client):
    d = client.get("/api/v1/memory/usage").json()
    assert d["callCap"] > 0 and d["budgetUsd"] > 0 and "providers" in d
