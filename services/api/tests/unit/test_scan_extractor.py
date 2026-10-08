"""The scan pipeline with a fake model and a fake OCR: no network, no photos, fast. Covers the fail-safe paths."""
import io
import json

from PIL import Image

from app.agents import scan_extractor as x
from app.core.errors import ExternalServiceError
from app.llm.vertex import GenerationResult


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
    assert (out.status, out.review_mode, out.reasons) == ("failed", "manual", ["service_unavailable"])


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
