"""K10 day calendar and K2 KPI row, read-only, through the real endpoints against the shared database (Mr Tan and a blank user).

Nothing is written. Run from the repo root:  python -m pytest services/api/tests/db/test_memory_reads.py -q  (needs DATABASE_URL in .env)
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.core.config import settings  # noqa: E402

settings.scheduler_enabled = False


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def test_day_calendar_covers_every_day_and_keeps_empty_days_empty(client):
    end = date(2026, 10, 11)
    start = end.replace(day=1)
    r = client.get("/api/v1/memory/progress/days", params={"from": start.isoformat(), "to": end.isoformat()}, headers={"X-User": "mr-tan"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["days"]) == (end - start).days + 1
    for d in body["days"]:
        if d["meals"] == 0:
            assert d["mealList"] == []
            assert all(v is None for v in d["totals"].values())
        else:
            assert len(d["mealList"]) == d["meals"]


def test_a_blank_user_has_no_meals_on_any_day(client):
    r = client.get("/api/v1/memory/progress/days", params={"from": "2026-10-01", "to": "2026-10-07"}, headers={"X-User": "demo"})
    assert r.status_code == 200
    assert all(d["meals"] == 0 for d in r.json()["days"])


def test_a_range_over_the_limit_is_refused_in_plain_words(client):
    far = date(2026, 10, 11)
    r = client.get("/api/v1/memory/progress/days", params={"from": (far - timedelta(days=100)).isoformat(), "to": far.isoformat()}, headers={"X-User": "demo"})
    assert r.status_code == 422
    assert "92 days" in r.json()["detail"]


@pytest.mark.parametrize("user", ["demo", "mr-tan"])
def test_barrier_summary_has_every_field_and_no_running_out_idea(client, user):
    r = client.get("/api/v1/memory/barriers/summary", headers={"X-User": user})
    assert r.status_code == 200
    s = r.json()
    for key in ("missedThisWeek", "onTimePct", "topReason", "confirmedBarriers", "waitingBarriers", "confirmedDoses", "scheduledThisWeek"):
        assert key in s
    facts = client.get("/api/v1/memory/facts", headers={"X-User": user}).json()
    statements = [f["statement"] for g in facts["groups"] for f in g["facts"]]
    assert not any("running out" in x for x in statements)
