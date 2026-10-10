"""Sharing the doctor report by link: token hashing, expiry and revoke rules, and the public read, with a fake connection (no database)."""
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.services import share as svc

NOW = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)


class FakeConn:
    """Answers each execute() with the next list of rows, and records every call so tests can see what was written."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((" ".join(sql.split()), tuple(params)))
        rows = self.answers.pop(0) if self.answers else []
        return FakeResult(rows)

    def writes(self):
        return [c for c in self.calls if c[0].startswith(("insert", "update"))]


def row(**kw):
    base = {"id": uuid4(), "user_id": uuid4(), "days": "14", "expires_at": NOW + timedelta(hours=24), "revoked_at": None}
    base.update(kw)
    return base


# ----------------------------------------------------------------------------------------------- tokens
def test_token_is_long_and_different_every_time():
    a, b = svc.new_token(), svc.new_token()
    assert len(a) >= 32 and a != b


def test_hash_is_sha256_hex_of_the_token_and_not_the_token():
    token = "example-token"
    h = svc.hash_token(token)
    assert h == hashlib.sha256(token.encode()).hexdigest()
    assert len(h) == 64 and token not in h
    assert svc.hash_token(token) == h                      # stable, so a lookup by hash finds the row


# ----------------------------------------------------------------------------------------------- expiry and revoke
def test_expiry_is_now_plus_the_chosen_hours():
    assert svc.expires_at(NOW, 72) == NOW + timedelta(hours=72)
    assert set(svc.ALLOWED_HOURS) == {24, 72, 168}


def test_link_is_open_before_expiry_and_closed_at_or_after_it():
    assert svc.is_open(NOW + timedelta(seconds=1), None, NOW)
    assert not svc.is_open(NOW, None, NOW)                 # the expiry instant itself is already closed
    assert not svc.is_open(NOW - timedelta(seconds=1), None, NOW)


def test_revoked_link_is_closed_even_before_expiry():
    assert not svc.is_open(NOW + timedelta(days=7), NOW - timedelta(minutes=1), NOW)


def test_status_words():
    assert svc.status(NOW + timedelta(hours=1), None, NOW) == "active"
    assert svc.status(NOW - timedelta(hours=1), None, NOW) == "expired"
    assert svc.status(NOW + timedelta(hours=1), NOW, NOW) == "revoked"
    assert svc.status(NOW - timedelta(hours=1), NOW - timedelta(hours=2), NOW) == "revoked"


# ----------------------------------------------------------------------------------------------- lookup
def test_lookup_uses_the_hash_and_never_sends_the_raw_token():
    token = svc.new_token()
    conn = FakeConn([row()])
    assert svc.find_share(conn, token) is not None
    (sql, params), = conn.calls
    assert svc.hash_token(token) in params
    assert all(token not in str(p) for p in params)


def test_overlong_or_empty_token_is_refused_without_a_query():
    conn = FakeConn()
    assert svc.find_share(conn, "") is None
    assert svc.find_share(conn, "x" * (svc.MAX_TOKEN_LENGTH + 1)) is None
    assert conn.calls == []


def test_wrong_token_is_not_found():
    assert svc.open_share(FakeConn([]), "no-such-token", NOW) is None


def test_expired_and_revoked_links_are_not_open():
    assert svc.open_share(FakeConn([row(expires_at=NOW - timedelta(minutes=1))]), "t", NOW) is None
    assert svc.open_share(FakeConn([row(revoked_at=NOW - timedelta(minutes=5))]), "t", NOW) is None


def test_open_link_is_returned():
    r = row()
    assert svc.open_share(FakeConn([r]), "t", NOW) == r


# ----------------------------------------------------------------------------------------------- the public read
@pytest.fixture
def fake_report(monkeypatch):
    seen = {}

    def load(conn, user_id, days, now):
        seen.update(user_id=user_id, days=days, now=now)
        return "inputs"

    monkeypatch.setattr(svc.doctor_report, "load", load)
    monkeypatch.setattr(svc.doctor_report, "build", lambda inputs: {"built": inputs})
    return seen


def test_public_read_reports_for_the_owner_and_writes_one_access_row(fake_report):
    owner, share_id = uuid4(), uuid4()
    conn = FakeConn([row(id=share_id, user_id=owner, days="30")])
    out = svc.public_report(conn, "t", "Mozilla/5.0", NOW)
    assert out == {"built": "inputs"}
    assert fake_report == {"user_id": str(owner), "days": 30, "now": NOW}
    writes = conn.writes()
    assert len(writes) == 1 and writes[0][0].startswith("insert into brief_share_access")
    assert writes[0][1][0] == share_id


def test_closed_link_gives_nothing_and_writes_nothing(fake_report):
    for closed in (row(expires_at=NOW - timedelta(hours=1)), row(revoked_at=NOW - timedelta(minutes=1))):
        conn = FakeConn([closed])
        assert svc.public_report(conn, "t", None, NOW) is None
        assert conn.writes() == []
    assert fake_report == {}


def test_unknown_link_gives_nothing(fake_report):
    assert svc.public_report(FakeConn([]), "nope", None, NOW) is None


def test_user_agent_is_cut_to_200_characters(fake_report):
    conn = FakeConn([row()])
    svc.public_report(conn, "t", "a" * 500, NOW)
    assert len(conn.writes()[0][1][2]) == 200


# ----------------------------------------------------------------------------------------------- revoke
def test_revoke_sets_revoked_at_once_and_keeps_the_first_time(monkeypatch):
    share_id = uuid4()
    conn = FakeConn([row(id=share_id)], [])
    out = svc.revoke_share(conn, uuid4(), share_id, NOW)
    assert out["status"] == "revoked" and out["revoked_at"] == NOW
    assert any(c[0].startswith("update brief_shares set revoked_at") for c in conn.calls)

    earlier = NOW - timedelta(hours=3)
    conn2 = FakeConn([row(id=share_id, revoked_at=earlier)])
    out2 = svc.revoke_share(conn2, uuid4(), share_id, NOW)
    assert out2["revoked_at"] == earlier
    assert conn2.writes() == []


def test_revoke_of_someone_elses_or_missing_share_is_none():
    assert svc.revoke_share(FakeConn([]), uuid4(), uuid4(), NOW) is None
