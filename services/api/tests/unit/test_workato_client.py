"""The Workato gateway: retries, no retry on a refusal, plain errors, and no secret or medicine name in an error. Fake HTTP, no network."""
import pytest
import requests

from app.core.errors import ExternalServiceError
from app.integrations.workato import WorkatoClient

PAYLOAD = {"title": "Take CRESTOR, 1 Tab", "time": "08:00"}
URL, TOKEN = "https://hooks.example.test/secret-path-123", "SUPER-SECRET-TOKEN"


class Resp:
    def __init__(self, status, body=None, bad_json=False):
        self.status_code, self._b, self._bad = status, body, bad_json

    def json(self):
        if self._bad:
            raise ValueError("not json")
        return self._b


class Session:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def post(self, url, json, headers, timeout):
        self.calls.append((url, json, headers, timeout))
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def client(session, **kw):
    return WorkatoClient(URL, TOKEN, "API-TOKEN", session=session, sleep=lambda s: None, **kw)


OK = Resp(200, {"status": "ok", "event_id": " ev123 ", "link": "https://calendar.google.com/x"})


def test_a_good_answer_returns_the_event_id_and_sends_the_token_in_the_named_header():
    s = Session(OK)
    ev = client(s).create_event(PAYLOAD)
    assert (ev.event_id, ev.link) == ("ev123", "https://calendar.google.com/x")
    url, body, headers, timeout = s.calls[0]
    assert url == URL and body == PAYLOAD and headers["API-TOKEN"] == TOKEN and timeout == 30.0


def test_a_plain_ok_with_no_event_id_is_enough():
    """A plain Workato webhook can only answer {"status": "ok"}: the app then names the event itself (option A, 2026-10-13)."""
    ev = client(Session(Resp(200, {"status": "ok"}))).create_event(PAYLOAD)
    assert ev.event_id == "" and ev.link is None


def test_a_link_that_is_not_https_is_dropped():
    assert client(Session(Resp(200, {"status": "ok", "event_id": "e", "link": "http://x"}))).create_event(PAYLOAD).link is None


def test_a_server_error_is_retried_then_succeeds_and_gives_up_after_the_retries():
    s = Session(Resp(503), requests.Timeout(), OK)
    assert client(s).create_event(PAYLOAD).event_id == "ev123" and len(s.calls) == 3
    s2 = Session(Resp(500), Resp(502), Resp(504))
    with pytest.raises(ExternalServiceError) as e:
        client(s2).create_event(PAYLOAD)
    assert e.value.code == "workato_unavailable" and len(s2.calls) == 3


def test_a_refusal_is_not_retried():
    s = Session(Resp(401))
    with pytest.raises(ExternalServiceError) as e:
        client(s).create_event(PAYLOAD)
    assert e.value.code == "workato_refused" and len(s.calls) == 1


@pytest.mark.parametrize("answer,code", [(Resp(200, bad_json=True), "workato_bad_answer"), (Resp(200, {"status": "error"}), "workato_failed"),
                                         (Resp(200, ["x"]), "workato_failed"), (Resp(200, {"status": "OK?"}), "workato_failed")])
def test_an_answer_that_is_not_a_clear_ok_is_an_error_not_a_guess(answer, code):
    with pytest.raises(ExternalServiceError) as e:
        client(Session(answer)).create_event(PAYLOAD)
    assert e.value.code == code


def test_without_an_address_or_token_nothing_is_sent():
    s = Session()
    for c in (WorkatoClient("", TOKEN, session=s), WorkatoClient(URL, "", session=s)):
        assert c.configured is False
        with pytest.raises(ExternalServiceError) as e:
            c.create_event(PAYLOAD)
        assert e.value.code == "workato_not_configured"
    assert s.calls == []


def test_an_error_never_contains_the_address_the_token_or_the_medicine_name():
    for replies in ([Resp(403)], [requests.ConnectionError("https://hooks.example.test/secret-path-123 refused")] * 3, [Resp(200, {"status": "no"})]):
        with pytest.raises(ExternalServiceError) as e:
            client(Session(*replies)).create_event(PAYLOAD)
        text = str(e.value)
        assert URL not in text and TOKEN not in text and "CRESTOR" not in text and "secret-path" not in text
