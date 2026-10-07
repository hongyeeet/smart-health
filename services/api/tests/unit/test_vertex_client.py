"""The Vertex gateway: retries, no retry on a refusal, and the key goes in a header and nowhere else. Fake HTTP, no network."""
import pytest
import requests

from app.core.errors import ExternalServiceError
from app.llm.vertex import ImagePart, VertexClient

OK = {"candidates": [{"content": {"parts": [{"text": '{"a": 1}'}]}}], "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 2}}


class Resp:
    def __init__(self, status, body=None):
        self.status_code, self._b = status, body or {}

    def json(self):
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
    return VertexClient("SECRET-KEY", "proj", session=session, sleep=lambda s: None, **kw)


def go(c):
    return c.generate_json(model="gemini-x", system="s", parts=[ImagePart(b"img"), "hi"], response_schema={"type": "OBJECT"})


def test_success_returns_text_and_counts():
    r = go(client(Session(Resp(200, OK))))
    assert r.text == '{"a": 1}' and (r.input_tokens, r.output_tokens) == (5, 2)


def test_the_key_is_in_a_header_not_the_url_and_the_timeout_is_45s():
    s = Session(Resp(200, OK))
    go(client(s))
    url, body, headers, timeout = s.calls[0]
    assert "SECRET-KEY" not in url and headers["x-goog-api-key"] == "SECRET-KEY" and timeout == 45.0
    assert url.startswith("https://aiplatform.googleapis.com/v1/projects/proj/locations/global/publishers/google/models/gemini-x:generateContent")
    assert body["generationConfig"]["responseMimeType"] == "application/json" and body["generationConfig"]["temperature"] == 0.0


def test_429_and_5xx_and_timeouts_are_retried():
    s = Session(Resp(429), requests.Timeout(), Resp(503), Resp(200, OK))
    assert go(client(s)).text and len(s.calls) == 4


def test_it_gives_up_after_the_retries():
    s = Session(*[Resp(500)] * 4)
    with pytest.raises(ExternalServiceError) as e:
        go(client(s))
    assert e.value.code == "llm_unavailable" and len(s.calls) == 4


def test_a_400_is_not_retried():
    s = Session(Resp(400), Resp(200, OK))
    with pytest.raises(ExternalServiceError) as e:
        go(client(s))
    assert e.value.code == "llm_refused" and len(s.calls) == 1


def test_an_empty_or_blocked_answer_is_an_error_without_leaking_the_content():
    with pytest.raises(ExternalServiceError) as e:
        go(client(Session(Resp(200, {"promptFeedback": {"blockReason": "SAFETY"}}))))
    assert e.value.code == "llm_empty" and "SAFETY" in str(e.value)


def test_a_missing_key_is_a_clear_error():
    with pytest.raises(ExternalServiceError) as e:
        VertexClient("", "proj")
    assert e.value.code == "llm_not_configured"


def test_the_image_is_sent_as_base64_inline_data():
    s = Session(Resp(200, OK))
    go(client(s))
    parts = s.calls[0][1]["contents"][0]["parts"]
    assert parts[0]["inlineData"]["mimeType"] == "image/jpeg" and parts[0]["inlineData"]["data"] == "aW1n" and parts[1] == {"text": "hi"}
