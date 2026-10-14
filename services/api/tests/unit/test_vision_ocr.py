"""Google Cloud Vision as the scanner's text reader: the lines it returns, errors without leaking anything, and the fall back to the offline reader.
Fake HTTP and a made-up response; nothing leaves the machine."""
import numpy as np
import pytest
import requests

from app.core.errors import ExternalServiceError
from app.integrations.vision_ocr import FallbackOcr, VisionOcr, parse_lines


def word(text, x0, y0, x1, y1, brk="SPACE", conf=0.98):
    syms = [{"text": ch} for ch in text]
    syms[-1]["property"] = {"detectedBreak": {"type": brk}}
    return {"symbols": syms, "confidence": conf, "boundingBox": {"vertices": [{"x": x0, "y": y0}, {"x": x1, "y": y0}, {"x": x1, "y": y1}, {"x": x0, "y": y1}]}}


RESP = {"fullTextAnnotation": {"pages": [{"blocks": [{"paragraphs": [{"words": [
    word("Take", 10, 10, 50, 30), word("2", 55, 10, 65, 30), word("tablets", 70, 10, 140, 30, brk="EOL_SURE_SPACE"),
    word("after", 10, 40, 60, 60), word("food", 65, 40, 110, 60, brk="LINE_BREAK", conf=0.90),
]}, {"words": [word("T0123456Z", 10, 80, 120, 100, brk="LINE_BREAK")]}]}]}]}}


def test_lines_end_where_vision_marks_a_line_wrap_or_the_end_of_a_paragraph():
    lines = parse_lines(RESP)
    assert [ln[1] for ln in lines] == ["Take 2 tablets", "after food", "T0123456Z"]
    box, text, conf = lines[0]
    assert box == [[10.0, 10.0], [140.0, 10.0], [140.0, 30.0], [10.0, 30.0]]          # the box covers that line's words only
    assert lines[1][2] == pytest.approx(0.94)                                          # the mean of its words' confidences
    assert parse_lines({}) == [] and parse_lines({"fullTextAnnotation": {}}) == []


def test_punctuation_that_vision_does_not_separate_stays_attached():
    resp = {"fullTextAnnotation": {"pages": [{"blocks": [{"paragraphs": [{"words": [word("500", 0, 0, 30, 10, brk=""), word("mg", 31, 0, 50, 10, brk=""), word(",", 51, 0, 55, 10, brk="LINE_BREAK")]}]}]}]}}
    assert parse_lines(resp)[0][1] == "500mg,"


class Resp:
    def __init__(self, status, body=None):
        self.status_code, self._b = status, body

    def json(self):
        return self._b


class Session:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def post(self, url, json, timeout):
        self.calls.append((url, json, timeout))
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


IMG = np.zeros((20, 40, 3), dtype=np.uint8)


def reader(*replies, **kw):
    s = Session(*replies)
    return VisionOcr("proj", session=s, sleep=lambda x: None, **kw), s


def test_a_photo_is_sent_once_as_document_text_detection_and_lines_come_back_in_the_scanners_shape():
    v, s = reader(Resp(200, {"responses": [RESP]}))
    out, extra = v(IMG)
    assert extra is None and [t for _, t, _ in out] == ["Take 2 tablets", "after food", "T0123456Z"]
    url, body, timeout = s.calls[0]
    assert url.endswith("/images:annotate") and body["requests"][0]["features"] == [{"type": "DOCUMENT_TEXT_DETECTION"}] and timeout == 20.0
    assert body["requests"][0]["imageContext"]["languageHints"] == ["en"]


def test_a_5xx_or_a_timeout_is_tried_once_more_and_a_4xx_is_refused_at_once():
    v, s = reader(Resp(503), Resp(200, {"responses": [RESP]}))
    assert v(IMG)[0] and len(s.calls) == 2
    v, s = reader(requests.Timeout(), Resp(200, {"responses": [RESP]}))
    assert v(IMG)[0] and len(s.calls) == 2
    v, s = reader(Resp(403, {"error": {"message": "secret detail"}}))
    with pytest.raises(ExternalServiceError) as e:
        v(IMG)
    assert e.value.code == "vision_refused" and "secret" not in str(e.value) and len(s.calls) == 1
    v, s = reader(Resp(500), Resp(500))
    with pytest.raises(ExternalServiceError) as e:
        v(IMG)
    assert e.value.code == "vision_unavailable"


def test_an_error_inside_a_200_answer_is_an_error_not_an_empty_label():
    v, _ = reader(Resp(200, {"responses": [{"error": {"message": "bad image"}}]}))
    with pytest.raises(ExternalServiceError) as e:
        v(IMG)
    assert e.value.code == "vision_error"


# ------------------------------------------------------------------ the fall back to the offline reader
class Clock:
    t = 0.0

    def __call__(self):
        return self.t


def test_when_vision_cannot_be_used_the_offline_reader_answers_and_vision_waits_before_the_next_try():
    clock, made, local_calls = Clock(), [], []

    def vision(bgr):
        raise ExternalServiceError("no", code="vision_unavailable")

    def make_local():
        made.append(1)
        return lambda bgr: (local_calls.append(1) or [["box", "local text", 0.9]], None)

    f = FallbackOcr(vision, make_local, cooldown_s=60, clock=clock)
    assert f(IMG)[0][0][1] == "local text" and f.last_engine == "local"
    assert f(IMG)[0][0][1] == "local text" and made == [1] and len(local_calls) == 2        # the offline reader is loaded once
    calls = []
    f._primary = lambda bgr: (calls.append(1) or ([["b", "vision text", 0.9]], None))
    f(IMG)
    assert calls == []                                                                       # still waiting: Vision is not tried on every photo
    clock.t = 61
    assert f(IMG)[0][0][1] == "vision text" and f.last_engine == "vision" and calls == [1]


def test_a_missing_credential_is_just_another_reason_to_use_the_offline_reader():
    class NoCreds(VisionOcr):
        def _get_session(self):
            raise RuntimeError("no default credentials")

    f = FallbackOcr(NoCreds("p"), lambda: (lambda bgr: ([["b", "local", 0.9]], None)))
    assert f(IMG)[0][0][1] == "local"


def test_the_engine_setting_chooses_the_reader(monkeypatch):
    from app.core import settings as S
    from app.services import scan_privacy as P

    s = S.get_settings()
    monkeypatch.setattr(s, "scan_ocr_engine", "local")
    assert type(P.default_ocr()).__name__ == "RapidOcrAdapter"
    monkeypatch.setattr(s, "scan_ocr_engine", "Vision")
    assert type(P.default_ocr()).__name__ == "FallbackOcr"
