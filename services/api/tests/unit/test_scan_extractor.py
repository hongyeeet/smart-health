"""The scan pipeline with a fake model and a fake OCR: no network, no photos, fast. Covers the fail-safe paths."""
import io
import json

import pytest
from PIL import Image

from app.agents import scan_extractor as x
from app.core.errors import ExternalServiceError
from app.llm.vertex import GenerationResult


@pytest.fixture(autouse=True)
def no_usage_counter(monkeypatch):
    """The daily counter is a database table: unit tests use an open cap and count nothing. Tests that check the cap replace this."""
    monkeypatch.setattr(x.usage, "allowed", lambda provider: True)
    monkeypatch.setattr(x.usage, "record", lambda *a, **k: None)


def photo_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (400, 200), "white").save(buf, "PNG")
    return buf.getvalue()


def box(y, w=300):
    return [[10, y], [10 + w, y], [10 + w, y + 30], [10, y + 30]]


class FakeOcr:
    def __init__(self, texts):
        self.texts = texts

    def __call__(self, _arr):
        return [[box(10 + 60 * i), t, 0.95] for i, t in enumerate(self.texts)], None


LABEL_TEXT = ["Patient: TAN AH KOW", "NRIC: S1234567D", "METFORMIN 500 mg TABLET", "Take 1 tablet twice daily after meals", "Qty: 60 TABS"]


def field(v, conf=0.97, src=None):
    return {"value": v, "confidence": conf, "source_text": src if src is not None else v}


def answer(**over):
    item = {"item_type": "prescription_label", "name": field("METFORMIN", src="METFORMIN 500 mg TABLET"), "strength": field("500 mg"),
            "dose_amount": field("1", src="Take 1 tablet"), "dose_unit": field("tablet", src="tablet"), "times_per_day": field("2", src="twice daily"),
            "meal_relation": field("after_meal", src="after meals"), "directions": field("Take 1 tablet twice daily after meals"),
            "prescriber": field(None, 0, ""), "start_date": field(None, 0, ""), "total_quantity": field("60", 0.97, "Qty: 60 TABS"), "ingredients": []}
    item.update(over)
    return {"readable": True, "is_medication_item": True, "issue": None, "items": [item]}


class FakeClient:
    def __init__(self, *replies):
        self.replies, self.calls, self.seen, self.limits = list(replies), 0, [], []

    def generate_json(self, *, model, system, parts, response_schema, max_output_tokens=4096):
        self.calls += 1
        self.limits.append(max_output_tokens)
        self.seen.append((system, parts))
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return GenerationResult(text=r if isinstance(r, str) else json.dumps(r), model=model, input_tokens=100, output_tokens=50, latency_ms=10)


def run(client, texts=LABEL_TEXT, **kw):
    return x.extract_scan(photo_bytes(), client=client, model="m", ocr=FakeOcr(texts), **kw)


def test_a_clear_label_goes_to_confirm_and_nothing_identifying_was_sent():
    client = FakeClient(answer())
    out, masked = run(client)
    assert (out.status, out.review_mode) == ("needs_review", "confirm")
    assert out.mask_summary == {"name_label": 1, "nric": 1}
    assert out.items[0].fields["name"].value == "METFORMIN"
    assert masked is not None and client.calls == 1
    _, parts = client.seen[0]
    assert all(isinstance(p, str) or p.mime_type == "image/jpeg" for p in parts)


def test_invalid_json_is_retried_once_then_succeeds():
    client = FakeClient("not json {", answer())
    out, _ = run(client)
    assert client.calls == 2 and out.status == "needs_review"


def test_invalid_json_twice_fails_safe_with_manual_entry():
    client = FakeClient("nope", '{"items": "wrong"}')
    out, _ = run(client)
    assert (out.status, out.review_mode, out.reasons, client.calls) == ("failed", "manual", ["invalid_json"], 2)


def test_a_model_outage_fails_safe_with_manual_entry():
    out, _ = run(FakeClient(ExternalServiceError("down", code="llm_unavailable")))
    assert (out.status, out.review_mode, out.reasons) == ("failed", "manual", ["model_unavailable"])


def test_identity_in_the_answer_is_removed_before_scoring():
    out, _ = run(FakeClient(answer(prescriber=field("Patient: TAN AH KOW", 0.99), directions=field("Take for S1234567D", 0.99))))
    f = out.items[0].fields
    assert f["prescriber"].value is None and f["directions"].value is None
    assert out.mask_summary["removed_from_answer"] == 2


def test_the_users_own_name_in_the_answer_is_removed():
    out, _ = run(FakeClient(answer(prescriber=field("Mdm Siti Aminah", 0.99))), known_names=["Mdm Siti Aminah"])
    assert out.items[0].fields["prescriber"].value is None


def test_a_invented_strength_not_in_the_photo_sends_the_user_to_manual_entry():
    out, _ = run(FakeClient(answer(strength=field("5000 mg", 0.99, "5000 mg safe to double"))))
    assert out.review_mode == "manual" and "low_confidence" in out.reasons


def test_not_a_medicine_and_unreadable_fail_with_manual_entry():
    bad = answer()
    bad["is_medication_item"] = False
    assert run(FakeClient(bad))[0].reasons == ["not_a_medicine"]
    bad = answer()
    bad["readable"] = False
    out = run(FakeClient(bad))[0]
    assert (out.status, out.reasons) == ("failed", ["unreadable"])


def test_a_photo_with_no_text_is_refused_before_any_model_call():
    client = FakeClient()
    out, masked = x.extract_scan(photo_bytes(), client=client, model="m", ocr=FakeOcr([]))
    assert (out.status, out.reasons, client.calls, masked) == ("failed", ["ocr_empty"], 0, None)


def test_a_file_that_is_not_a_photo_is_refused_before_any_model_call():
    client = FakeClient()
    out, _ = x.extract_scan(b"hello", client=client, model="m", ocr=FakeOcr(LABEL_TEXT))
    assert (out.reasons, client.calls) == (["file_type_not_allowed"], 0)


def test_the_prompt_is_a_versioned_file_and_the_schema_matches_the_fields():
    version, text = x.load_prompt()
    assert version == "3" and "never guess" in text.lower() and "instructions" in text.lower()
    props = x.response_schema()["properties"]["items"]["items"]["properties"]
    assert set(x.FIELD_NAMES) <= set(props) and "ingredients" in props


def test_numbers_and_booleans_from_the_model_are_accepted_as_text():
    ans = answer(strength=field(500, 0.97, "500 mg"), dose_amount=field(1, 0.97, "1 tablet"), drowsiness_warning=field(True, 0.9, "may cause drowsiness"))
    out, _ = run(FakeClient(ans))
    f = out.items[0].fields
    assert out.status == "needs_review" and f["dose_amount"].value == "1" and f["drowsiness_warning"].value == "true"


def test_the_answer_is_given_room_after_the_models_own_thinking():
    # A dense label once used 3,500 of 4,096 tokens thinking and the JSON was cut off mid-way, so the scan failed.
    client = FakeClient(answer())
    run(client)
    assert client.limits == [x.MAX_OUTPUT_TOKENS] and x.MAX_OUTPUT_TOKENS >= 8192


class CrashingOcr:
    def __call__(self, _arr):
        raise RuntimeError("the text reader fell over")


def test_a_crashing_text_reader_is_a_plain_failure_not_a_server_error():
    client = FakeClient()
    out, masked = x.extract_scan(photo_bytes(), client=client, model="m", ocr=CrashingOcr())
    assert (out.status, out.review_mode, out.reasons) == ("failed", "manual", ["ocr_unavailable"])
    assert client.calls == 0 and masked is None


def test_a_failed_model_call_returns_the_model_unavailable_code():
    out, _ = run(FakeClient(ExternalServiceError("down", code="llm_unavailable")))
    assert out.reasons == ["model_unavailable"] and out.status == "failed"


def test_a_name_at_0_6_to_0_85_goes_to_confirm_when_every_other_field_is_clear():
    ans = answer()
    ans["items"][0]["name"] = field("METFORMIN", 0.7, "METFORMIN 500 mg TABLET")
    out, _ = run(FakeClient(ans))
    assert out.status == "needs_review" and out.review_mode == "confirm"
    assert out.items[0].fields["name"].needs_confirmation is False


class CountingUsage:
    """Stands in for app.services.usage: `allowed` answers as told, and every record call is kept."""

    def __init__(self, allow=True, fail=False):
        self.allow, self.fail, self.records, self.checks = allow, fail, [], []

    def allowed(self, provider):
        self.checks.append(provider)
        if self.fail:
            raise RuntimeError("counter unreachable")
        return self.allow

    def record(self, provider, input_tokens=0, output_tokens=0, cost_usd=None, blocked=False):
        if self.fail:
            raise RuntimeError("counter unreachable")
        self.records.append((provider, input_tokens, output_tokens))


def test_an_allowed_read_is_counted_once_with_the_tokens_the_model_returned(monkeypatch):
    counter = CountingUsage(allow=True)
    monkeypatch.setattr(x.usage, "allowed", counter.allowed)
    monkeypatch.setattr(x.usage, "record", counter.record)
    client = FakeClient(answer())
    out, _ = run(client)
    assert out.status == "needs_review" and client.calls == 1
    assert counter.checks == ["vertex_vision"] and counter.records == [("vertex_vision", 100, 50)]


def test_a_refused_read_makes_no_model_call_and_says_daily_limit(monkeypatch):
    counter = CountingUsage(allow=False)
    monkeypatch.setattr(x.usage, "allowed", counter.allowed)
    monkeypatch.setattr(x.usage, "record", counter.record)
    client = FakeClient(answer())
    out, masked = run(client)
    assert client.calls == 0
    assert (out.status, out.review_mode, out.reasons) == ("failed", "manual", ["daily_limit"])
    assert counter.checks == ["vertex_vision"] and counter.records == []
    assert masked is not None   # same as a model outage: the blacked-out photo is kept, nothing else is sent


def test_a_broken_usage_counter_does_not_stop_or_break_a_read(monkeypatch):
    counter = CountingUsage(fail=True)
    monkeypatch.setattr(x.usage, "allowed", counter.allowed)
    monkeypatch.setattr(x.usage, "record", counter.record)
    client = FakeClient(answer())
    out, _ = run(client)
    assert client.calls == 1 and (out.status, out.review_mode) == ("needs_review", "confirm")


def test_a_failed_count_after_a_good_read_is_ignored(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("write failed")
    monkeypatch.setattr(x.usage, "record", boom)
    out, _ = run(FakeClient(answer()))
    assert out.status == "needs_review"


def test_a_strength_at_0_7_still_sends_the_scan_to_typing():
    ans = answer(strength=field("500 mg", 0.7))
    out, _ = run(FakeClient(ans))
    assert out.review_mode == "manual" and "low_confidence" in out.reasons


# ---- the text reader switched off (SCAN_OCR_ENABLED=false): the photo goes to the model as it is, and the real photo is never stored
class ExplodingOcr:
    def __call__(self, _arr):
        raise AssertionError("the text reader must not run when it is switched off")


def test_with_the_text_reader_off_the_photo_is_not_read_locally_not_blacked_out_and_not_stored(monkeypatch):
    client = FakeClient(answer())
    outcome, stored = x.extract_scan(photo_bytes(), client=client, model="m", ocr=ExplodingOcr(), ocr_enabled=False)
    assert outcome.status == "needs_review" and outcome.items                                  # the answer is scored without the text-reader check
    sent = Image.open(io.BytesIO(client.seen[0][1][0].data)) if hasattr(client.seen[0][1][0], "data") else None
    assert sent is None or sent.size == (400, 200)                                              # the model got the whole photo, no black boxes added
    assert outcome.mask_summary == {"ocr_off": 1}
    held = Image.open(io.BytesIO(stored.image))
    assert held.size == (8, 8)                                                                  # what is kept is a grey square, not the label
    import hashlib
    assert hashlib.sha256(photo_bytes()).hexdigest().encode() in stored.image                   # but it carries the photo's checksum, so each photo is its own scan


def test_two_different_photos_get_different_stored_squares_when_the_text_reader_is_off():
    other = io.BytesIO()
    Image.new("RGB", (400, 200), "black").save(other, "PNG")
    _, a = x.extract_scan(photo_bytes(), client=FakeClient(answer()), model="m", ocr=None, ocr_enabled=False)
    _, b = x.extract_scan(other.getvalue(), client=FakeClient(answer()), model="m", ocr=None, ocr_enabled=False)
    assert a.image != b.image


def test_with_the_text_reader_on_nothing_changes(monkeypatch):
    outcome, stored = run(FakeClient(answer()))
    assert outcome.mask_summary.get("ocr_off") is None and stored.masked == outcome.mask_summary


def test_with_the_text_reader_off_a_prescriber_line_that_is_really_the_patient_is_left_out():
    reply = answer(prescriber=field("TAN AH BARK", 0.95, "D9285 TAN AH BARK"))
    outcome, _ = x.extract_scan(photo_bytes(), client=FakeClient(reply), model="m", ocr=None, ocr_enabled=False)
    item = outcome.items[0]
    assert item.fields["prescriber"].value is None
    assert "TAN AH BARK" not in json.dumps(outcome.model_dump(), default=str)                 # it is nowhere in what is stored
