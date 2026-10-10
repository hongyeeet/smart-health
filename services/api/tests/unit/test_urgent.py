"""Urgent low-glucose alert: tiers, freshness, state resolution, the contact wording and the 0031 SQL (with fakes)."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.db import logstore
from app.services import urgent as U

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)


def reading(value, minutes_ago=2, ok=True):
    return {"at": NOW - timedelta(minutes=minutes_ago), "value": value, "quality_ok": ok}


def alert(value=3.4, tier="low", minutes_ago=6, demo=True, **kw):
    return {"id": "a1", "since": NOW - timedelta(minutes=minutes_ago), "tier": tier, "value": value, "demo": demo,
            "ack_at": None, "recheck_at": None, "escalated_at": None, "email_queued": False, **kw}


def test_tier_edges():
    assert U.tier_for(2.9) == "very_low"
    assert U.tier_for(3.0) == "low"        # not below 3.0
    assert U.tier_for(3.9) == "low"
    assert U.tier_for(4.0) == "none"       # not below 4.0
    assert U.tier_for(None) == "none"


def test_limits_mirror_the_app_config():
    assert (U.LOW_BELOW, U.VERY_LOW_BELOW, U.RECHECK_MINUTES, U.CONTACT_AFTER_MINUTES, U.EMERGENCY_NUMBER) == (4.0, 3.0, 15, 5, "995")


def test_no_reading_means_no_alert():
    assert U.resolve(NOW, None, None)["status"] == "none"


def test_stale_or_poor_quality_reading_does_not_count():
    assert U.resolve(NOW, reading(2.5, minutes_ago=21), None)["status"] == "none"
    assert U.resolve(NOW, reading(2.5, ok=False), None)["status"] == "none"
    assert U.resolve(NOW, reading(2.5, minutes_ago=20), None)["status"] == "active"   # exactly 20 still counts
    assert U.resolve(NOW, reading(2.5, minutes_ago=-30), None)["status"] == "none"    # from the future: a clock fault


def test_fresh_low_reading_is_active_and_contact_is_due_after_five_minutes():
    s = U.resolve(NOW, reading(3.4, minutes_ago=6), None)
    assert (s["status"], s["tier"], s["value"], s["id"]) == ("active", "low", 3.4, None)
    assert s["contact_after"] == s["since"] + timedelta(minutes=5)
    assert U.resolve(NOW, reading(2.8), None)["tier"] == "very_low"
    assert U.resolve(NOW, reading(4.0), None)["status"] == "none"


def test_demo_alert_shows_then_expires_after_twenty_minutes():
    s = U.resolve(NOW, None, alert())
    assert (s["status"], s["demo"], s["id"]) == ("active", True, "a1")
    assert U.resolve(NOW, None, alert(minutes_ago=21))["status"] == "none"


def test_acknowledged_until_recheck_then_over_for_demo():
    a = alert(ack_at=NOW - timedelta(minutes=1), recheck_at=NOW + timedelta(minutes=14))
    s = U.resolve(NOW, None, a)
    assert s["status"] == "acknowledged" and s["recheck_at"] == a["recheck_at"] and s["contact_after"] is None
    late = alert(ack_at=NOW - timedelta(minutes=16), recheck_at=NOW - timedelta(minutes=1), minutes_ago=17)
    assert U.resolve(NOW, None, late)["status"] == "none"


def test_real_alert_ends_when_a_newer_fresh_reading_is_back_in_range():
    a = alert(demo=False, minutes_ago=8)
    assert U.resolve(NOW, reading(5.0, minutes_ago=1), a)["status"] == "none"
    assert U.resolve(NOW, reading(3.5, minutes_ago=1), a)["status"] == "active"


def test_demo_alert_ignores_in_range_readings():
    assert U.resolve(NOW, reading(5.5, minutes_ago=1), alert())["status"] == "active"


def test_real_alert_gets_worse_shows_the_newer_number():
    s = U.resolve(NOW, reading(2.7, minutes_ago=1), alert(demo=False, value=3.5, minutes_ago=8))
    assert (s["tier"], s["value"]) == ("very_low", 2.7)


def test_old_reading_does_not_raise_a_second_alert_after_the_recheck():
    a = alert(demo=False, minutes_ago=18, value=3.4, ack_at=NOW - timedelta(minutes=17), recheck_at=NOW - timedelta(minutes=2))
    s = U.resolve(NOW, {"at": a["since"], "value": 3.4, "quality_ok": True}, a)
    assert s["status"] == "none"
    s = U.resolve(NOW, reading(3.3, minutes_ago=1), a)   # a new low reading after the recheck does alert again
    assert s["status"] == "active" and s["id"] is None


def test_escalated_status():
    assert U.resolve(NOW, None, alert(escalated_at=NOW, email_queued=True))["status"] == "escalated"


def test_contact_message_is_the_fixed_template():
    title, body = U.contact_message("Mr Tan", 3.4, NOW, demo=False)
    assert body == "Mr Tan may have low glucose (3.4 mmol/L at 20:00). Please check on them. If they cannot answer, call 995."
    assert "Mr Tan" in title
    t2, b2 = U.contact_message("Mr Tan", 3.4, NOW, demo=True)
    assert t2.startswith("DEMO.") and b2.startswith("This is a demo test") and b2.endswith("call 995.")
    assert "may have low glucose" in U.contact_message(None, 3.0, NOW, False)[1]


def test_email_check():
    assert U.valid_email("a@b.co") and not U.valid_email("a@b") and not U.valid_email(None) and not U.valid_email("")


class FakeConn:
    def __init__(self, rows=None):
        self.calls, self.rows = [], rows or {}

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        return self

    def fetchone(self):
        return self.rows.get("fetchone")


def test_contact_request_sql_uses_the_delivery_columns():
    c = FakeConn()
    U.insert_contact_request(c, "u1", "a1", "T", "B", {"tier": "low", "value": 3.4, "demo": True, "contactName": "Ann", "contactEmail": "ann@x.com"})
    sql, params = c.calls[0]
    assert "delivery_status" in sql and "delivery_to" in sql and "'pending'" in sql and "'contact'" in sql
    payload = json.loads(params[2])
    assert payload["key"] == "urgent-a1-contact" and payload["to"] == "J1" and payload["tier"] == "low" and payload["demo"] is True
    assert payload["contactEmail"] == "ann@x.com" and payload["title"] == "T" and payload["body"] == "B"
    assert params[1] == U.CONTACT_CHANNEL


def _setup(monkeypatch, contact, cols=True, state=None):
    monkeypatch.setattr(U, "load_reading", lambda c, u: None)
    monkeypatch.setattr(U, "load_alert", lambda c, u: state or alert())
    monkeypatch.setattr(U, "load_contact", lambda c, u: contact)
    monkeypatch.setattr(U, "delivery_columns_exist", lambda c: cols)


def test_escalate_without_a_contact_email_records_but_queues_nothing(monkeypatch):
    _setup(monkeypatch, {"person": "Mr Tan", "name": None, "phone": None, "email": None})
    c = FakeConn()
    state, events = U.escalate(c, "u1", NOW)
    sqls = " ".join(s for s, _ in c.calls)
    assert "insert into notifications" not in sqls and "update notifications set payload" in sqls
    esc = next(e for e in events if e[0] == "urgent.escalated")
    assert esc[2]["emailQueued"] is False and esc[2]["reason"] == "no_contact_email"
    assert not any(e[0] == "urgent.contact_email_requested" for e in events)


def test_escalate_with_email_queues_one_request_and_audits_without_the_address(monkeypatch):
    _setup(monkeypatch, {"person": "Mr Tan", "name": "Ann", "phone": "91234567", "email": "ann@x.com"})
    c = FakeConn()
    _, events = U.escalate(c, "u1", NOW)
    inserts = [p for s, p in c.calls if "insert into notifications" in s]
    assert len(inserts) == 1 and json.loads(inserts[0][2])["contactEmail"] == "ann@x.com"
    assert [e[0] for e in events] == ["urgent.escalated", "urgent.contact_email_requested"]
    assert "ann@x.com" not in json.dumps(events, default=str)


def test_escalate_before_the_columns_exist_does_not_touch_them(monkeypatch):
    _setup(monkeypatch, {"person": "Mr Tan", "name": "Ann", "phone": None, "email": "ann@x.com"}, cols=False)
    c = FakeConn()
    _, events = U.escalate(c, "u1", NOW)
    assert not any("insert into notifications" in s for s, _ in c.calls)
    assert next(e for e in events if e[0] == "urgent.escalated")[2]["reason"] == "email_not_ready"


def test_escalate_twice_queues_only_once(monkeypatch):
    _setup(monkeypatch, {"person": "x", "name": "Ann", "phone": None, "email": "ann@x.com"}, state=alert(escalated_at=NOW, email_queued=True))
    c = FakeConn()
    _, events = U.escalate(c, "u1", NOW)
    assert events == [] and not any("insert into notifications" in s for s, _ in c.calls)


def test_acting_with_no_alert_raises(monkeypatch):
    _setup(monkeypatch, {"person": None, "name": None, "phone": None, "email": None}, state=alert(minutes_ago=40))
    with pytest.raises(U.NoAlert):
        U.acknowledge(FakeConn(), "u1", NOW)


def test_simulate_refuses_in_range_values():
    with pytest.raises(ValueError):
        U.simulate(FakeConn(), "u1", 4.0, NOW)


def test_urgent_keys_are_exempt_from_the_cap_and_quiet_hours():
    assert logstore.is_exempt("urgent-abc") and logstore.is_exempt("urgent-abc-contact")
