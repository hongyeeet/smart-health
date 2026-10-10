"""Reminder emails: who gets one, when, what it says, and that nothing is sent twice (docs/specs/email-notifications.md)."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import requests

from app.core.errors import ExternalServiceError
from app.integrations.workato_email import WorkatoEmail
from app.services import notify_email as N

TZ = ZoneInfo("Asia/Singapore")
NOON = datetime(2026, 10, 10, 12, 0, tzinfo=TZ)


def row(**kw):
    base = dict(id="n1", user_id="u1", kind="nudge", scheduled_for=NOON - timedelta(minutes=5), acted_at=None,
                payload={"key": "meal-2-2026-10-10", "title": "Log your lunch", "body": "Take a photo and tell us when you finish eating.", "to": "E2",
                         "until": (NOON + timedelta(hours=2)).isoformat()},
                attempts=0, delivery_to="person", name="Mr Tan", email="tan@gmail.com", opt_in=True, contact_name="Mei", contact_email="mei@gmail.com")
    base.update(kw)
    return N.Row(**base)


def test_a_normal_reminder_is_sent():
    assert N.decide(row(), NOON, 0) == ("send", "")


@pytest.mark.parametrize("kind", ["miss_reason", "dose_reminder", "dose_renudge", "clash", "brief_ready"])
def test_only_some_kinds_are_emails(kind):
    assert N.decide(row(kind=kind), NOON, 0)[0] == "skip"


def test_no_address_or_emails_turned_off_means_skip_with_a_reason():
    assert N.decide(row(email=None), NOON, 0) == ("skip", "no address to send to")
    assert N.decide(row(opt_in=False), NOON, 0) == ("skip", "emails turned off")
    assert N.decide(row(email="not an email"), NOON, 0)[0] == "skip"


def test_expired_done_or_stale_reminders_are_not_sent_late():
    assert N.decide(row(), NOON + timedelta(hours=3), 0) == ("skip", "expired")
    assert N.decide(row(acted_at=NOON), NOON, 0) == ("skip", "already done in the app")
    no_expiry = row(payload={"key": "refill-1", "title": "Time to refill", "body": "x"}, kind="refill", scheduled_for=NOON - timedelta(hours=7))
    assert N.decide(no_expiry, NOON, 0) == ("skip", "too old to send")


def test_daily_limit_and_quiet_hours_apply_to_reminders():
    assert N.decide(row(), NOON, 3) == ("skip", "daily email limit reached")
    night = datetime(2026, 10, 10, 23, 0, tzinfo=TZ)
    r = row(payload={"key": "x", "title": "t", "body": "b", "until": (night + timedelta(hours=2)).isoformat()}, scheduled_for=night)
    assert N.decide(r, night, 0) == ("wait", "quiet hours")


def test_an_urgent_alert_goes_to_the_contact_and_ignores_limit_and_quiet_hours():
    night = datetime(2026, 10, 10, 23, 30, tzinfo=TZ)
    r = row(kind="urgent", delivery_to="contact", scheduled_for=night, payload={"key": "urgent-1", "title": "Possible low glucose", "body": "Please check.", "to": "J1"})
    assert N.decide(r, night, 99) == ("send", "")
    assert N.recipient(r) == "mei@gmail.com"
    assert N.decide(row(kind="urgent", delivery_to="contact", contact_email=None, payload={"key": "urgent-1"}), NOON, 0)[0] == "skip"
    # an urgent row is stale after 2 hours, not 6
    old = row(kind="urgent", delivery_to="contact", scheduled_for=NOON - timedelta(hours=3), payload={"key": "urgent-1"})
    assert N.decide(old, NOON, 0) == ("skip", "too old to send")


def test_a_contact_email_row_is_sent_even_though_it_is_marked_acted():
    # the urgent service makes the contact row already-acted so it does not show in the person's own list
    r = row(kind="urgent", delivery_to="contact", acted_at=NOON, payload={"key": "urgent-7-contact", "title": "Possible low glucose", "body": "Please check.", "to": "J1"})
    assert N.decide(r, NOON, 0) == ("send", "")
    assert N.decide(row(acted_at=NOON), NOON, 0) == ("skip", "already done in the app")   # the person's own reminder still is skipped


def test_the_message_is_friendly_has_a_button_and_escapes_html():
    m = N.build_message(row(name="Mr <b>Tan</b>", payload={"key": "meal-2-2026-10-10", "title": "Log your lunch", "body": "A <script> in the text", "to": "E2"}))
    assert m["to"] == "tan@gmail.com" and m["idempotencyKey"] == "n1"
    assert m["subject"] == "Log your lunch? One photo is all it takes"
    assert "/log/meal" in m["html"] and "Log my meal" in m["html"]
    assert "<script>" not in m["html"] and "&lt;script&gt;" in m["html"] and "<b>Tan</b>" not in m["html"]
    assert "Log my meal:" in m["text"] and "Hi Mr <b>Tan</b>," in m["text"]
    assert "turn them off any time in Me" in m["text"]


def test_subjects_by_kind_of_reminder():
    base = {"title": "T", "body": "B", "to": "B1"}
    assert N._subject(row(payload={**base, "key": "checkin-2026-10-10"})) == "How did you sleep? It takes thirty seconds"
    assert N._subject(row(payload={**base, "key": "workout-2026-10-10"})) == "A short walk counts today"
    assert N._subject(row(payload={**base, "key": "lunch-2026-10-10"})) == "Lunch ideas picked for you"
    assert N._subject(row(kind="urgent", delivery_to="contact", payload={**base, "key": "urgent-1"})) == "Please check on Mei: possible low glucose"


def test_the_contact_email_has_no_unsubscribe_and_says_why_they_got_it():
    m = N.build_message(row(kind="urgent", delivery_to="contact", payload={"key": "urgent-1", "title": "Possible low glucose", "body": "Please check on Mr Tan.", "to": "J1"}))
    assert m["to"] == "mei@gmail.com" and "emergency contact" in m["text"] and "Unsubscribe" not in m["text"]


def test_unsubscribe_links_are_signed_and_tamper_proof(monkeypatch):
    monkeypatch.setattr(N.settings, "notify_secret", "s3cret")
    monkeypatch.setattr(N.settings, "api_public_url", "https://api.example.com/")
    link = N.unsubscribe_link("u1")
    assert link and link.startswith("https://api.example.com/api/v1/notify/unsubscribe?t=u1.")
    token = link.split("t=")[1]
    assert N.verify_unsubscribe(token) == "u1"
    assert N.verify_unsubscribe("u2." + token.split(".", 1)[1]) is None       # another person's id with this signature
    assert N.verify_unsubscribe("u1.0000") is None and N.verify_unsubscribe("nodot") is None
    monkeypatch.setattr(N.settings, "notify_secret", "")
    assert N.unsubscribe_link("u1") is None and N.verify_unsubscribe(token) is None   # no secret: no links, nothing verifies
    assert "Unsubscribe" not in N.build_message(row())["text"]


@pytest.mark.parametrize("value,ok", [("a@b.co", True), ("first.last+tag@gmail.com", True), ("a@b", False), ("a b@c.com", False), ("", False), (None, False), ("a@b.com, c@d.com", False), ("x" * 250 + "@a.com", False)])
def test_email_validation(value, ok):
    assert N.is_valid_email(value) is ok


# ── the Workato client: retries on the right errors, refuses the rest, never leaks ──
class FakeSession:
    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append((url, json, headers))
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a

        class R:
            status_code = a[0]

            def json(self_inner):
                if a[1] is ValueError:
                    raise ValueError("bad")
                return a[1]
        return R()


def client(session):
    return WorkatoEmail("https://hooks.example/abc", "TOKEN123", session=session, sleep=lambda s: None, max_retries=2)


def test_the_client_sends_with_the_token_in_the_header():
    s = FakeSession((200, {"status": "ok"}))
    client(s).send({"to": "a@b.co"})
    url, payload, headers = s.calls[0]
    assert headers["API-TOKEN"] == "TOKEN123" and payload == {"to": "a@b.co"}


def test_the_client_retries_server_errors_and_connection_errors_then_gives_up():
    s = FakeSession(requests.ConnectionError("boom: secret-host"), (503, {}), (500, {}))
    with pytest.raises(ExternalServiceError) as e:
        client(s).send({"to": "a@b.co"})
    assert e.value.code == "workato_unavailable" and len(s.calls) == 3
    assert "TOKEN123" not in str(e.value) and "secret-host" not in str(e.value) and "a@b.co" not in str(e.value)


def test_the_client_does_not_retry_a_refusal_or_a_wrong_answer():
    s = FakeSession((401, {}))
    with pytest.raises(ExternalServiceError) as e:
        client(s).send({})
    assert e.value.code == "workato_refused" and len(s.calls) == 1
    for answer in ((200, {"status": "error"}), (200, ValueError)):
        with pytest.raises(ExternalServiceError):
            client(FakeSession((200, answer[1]) if answer[1] is ValueError else answer)).send({})


def test_an_unconfigured_client_says_so_and_sends_nothing():
    c = WorkatoEmail("", "")
    assert not c.configured
    with pytest.raises(ExternalServiceError) as e:
        c.send({})
    assert e.value.code == "workato_not_configured"


# ── the dispatcher end to end, with a fake database and a fake sender ──
class FakeConn:
    """Holds one pending notification and records what the dispatcher writes back."""
    def __init__(self, r):
        self.r, self.writes, self.sent_today = r, [], 0

    def execute(self, sql, params=()):
        s = " ".join(sql.split())
        self.last = s
        if s.startswith("update notifications"):
            self.writes.append((s, params))
            if "delivery_status = 'sent'" in s:
                self.r = None
            return self
        return self

    def fetchone(self):
        if "count(*) n from notifications" in self.last:
            return {"n": self.sent_today}
        return self.r

    def fetchall(self):
        return [{"id": "n1"}] if self.r else []


class Ctx:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, *a):
        return False


class FakeSender:
    configured = True

    def __init__(self, fail=None):
        self.messages, self.fail = [], fail

    def send(self, message):
        if self.fail:
            raise ExternalServiceError("down", code=self.fail)
        self.messages.append(message)


def db_row(**kw):
    base = {"id": "n1", "user_id": "u1", "kind": "nudge", "scheduled_for": NOON - timedelta(minutes=5), "acted_at": None, "delivery_attempts": 0, "delivery_to": "person",
            "payload": {"key": "meal-2-2026-10-10", "title": "Log your lunch", "body": "b", "to": "E2", "until": (NOON + timedelta(hours=2)).isoformat()},
            "display_name": "Mr Tan", "notification_email": "tan@gmail.com", "email_opt_in": True, "emergency_contact_name": None, "emergency_contact_email": None}
    base.update(kw)
    return base


@pytest.fixture
def run(monkeypatch):
    monkeypatch.setattr(N, "columns_ready", lambda conn=None: True)

    def go(r, sender, sent_today=0):
        conn = FakeConn(r)
        conn.sent_today = sent_today
        monkeypatch.setattr(N, "tx", lambda: Ctx(conn))
        out = N.dispatch(sender, now_fn=lambda: NOON)
        return out, conn
    return go


def test_a_pending_row_is_sent_once_and_marked(run):
    sender = FakeSender()
    out, conn = run(db_row(), sender)
    assert out["sent"] == 1 and len(sender.messages) == 1
    assert "delivery_status = 'sent'" in conn.writes[0][0] and conn.r is None
    out2 = N.dispatch(sender, now_fn=lambda: NOON)                      # the row is no longer pending: nothing to send
    assert out2["sent"] == 0 and len(sender.messages) == 1


def test_a_skipped_row_records_why_and_sends_nothing(run):
    sender = FakeSender()
    out, conn = run(db_row(email_opt_in=False), sender)
    assert out["skipped"] == 1 and not sender.messages
    assert conn.writes[0][1][0] == "emails turned off"


def test_a_failed_send_is_retried_then_given_up_on(run):
    out, conn = run(db_row(), FakeSender(fail="workato_unavailable"))
    assert out["retry"] == 1 and conn.writes[0][1][:3] == (1, "pending", "workato_unavailable")
    out, conn = run(db_row(delivery_attempts=2), FakeSender(fail="workato_unavailable"))
    assert out["failed"] == 1 and conn.writes[0][1][1] == "failed"
    out, conn = run(db_row(), FakeSender(fail="workato_refused"))          # a refusal is final at once
    assert out["failed"] == 1


def test_an_unconfigured_sender_leaves_everything_pending(run):
    sender = FakeSender()
    sender.configured = False
    out, conn = run(db_row(), sender)
    assert sum(out.values()) == 0 and not conn.writes


def test_the_daily_limit_counts_what_was_already_sent_today(run):
    out, conn = run(db_row(), FakeSender(), sent_today=3)
    assert out["skipped"] == 1 and conn.writes[0][1][0] == "daily email limit reached"
