"""Confidence scoring and the confirm-or-type-it decision (prd F2). Pure code: no model, no database."""
from datetime import date, timedelta

import pytest

from app.schemas.medicine_scan import RawExtraction, RawField, RawItem
from app.services import scan_confidence as c

OCR = "SINGAPORE GENERAL HOSPITAL PHARMACY METFORMIN 500 mg TABLET Take 1 tablet twice daily after meals Qty: 60 Date: 02/10/2026 Dr Lim Wei Ming"
INDEX = c.DrugIndex([("id-met", "metformin", "metformin"), ("id-met", "metformin", "Glucophage"), ("id-ato", "atorvastatin", "atorvastatin"),
                     ("id-ato", "atorvastatin", "Lipitor"), ("id-ami", "amlodipine", "amlodipine")])


def f(value, conf=0.99, src="auto"):
    return RawField(value=value, confidence=conf, source_text=value if src == "auto" else src)


def item(**over):
    base = dict(item_type="prescription_label", name=f("METFORMIN", src="METFORMIN 500 mg TABLET"), strength=f("500 mg", src="500 mg"),
                times_per_day=f("2", src="twice daily"), meal_relation=f("after_meal", src="after meals"),
                total_quantity=f("60", src="Qty: 60"))
    base.update(over)
    return RawItem(**base)


def raw(*items, readable=True, med=True):
    return RawExtraction(readable=readable, is_medication_item=med, items=list(items))


# --- drug matching ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,expected", [("METFORMIN", "metformin"), ("Metformin 500mg tablet", "metformin"), ("Glucophage XR", "metformin"),
                                          ("lipitor 20 mg", "atorvastatin"), ("Metformn", "metformin"), ("Atorvastain", "atorvastatin")])
def test_names_match_the_drug_list(name, expected):
    m = INDEX.match(name)
    assert m and m.generic_name == expected


def test_exact_name_scores_100_and_an_unknown_name_has_no_match():
    assert INDEX.match("metformin").score == 100
    assert INDEX.match("Zorblaxine") is None
    assert INDEX.match("") is None and INDEX.match(None) is None


# --- field scoring ------------------------------------------------------------------------------------------

def test_a_clear_field_keeps_the_models_confidence():
    s = c.score_field("strength", f("500 mg", 0.97, "500 mg"), OCR)
    assert s.confidence == 0.97 and not s.needs_confirmation and s.flags == []


def test_a_missing_value_is_null_with_zero_confidence_and_is_not_flagged_for_typing():
    s = c.score_field("prescriber", RawField(value=None, confidence=0.9), OCR)
    assert s.value is None and s.confidence == 0 and not s.needs_confirmation


def test_a_quote_that_is_not_in_the_photo_text_is_distrusted():
    s = c.score_field("strength", f("5000 mg", 0.99, "take 5000 milligrams now"), OCR)
    assert "source_not_in_ocr" in s.flags and s.confidence <= 0.55 and s.needs_confirmation


def test_no_quote_at_all_caps_the_confidence():
    s = c.score_field("strength", RawField(value="500 mg", confidence=0.99, source_text=None), OCR)
    assert s.confidence == 0.5 and s.needs_confirmation


def test_a_value_that_disagrees_with_its_quote_is_distrusted():
    s = c.score_field("name", f("ATORVASTATIN", 0.99, "METFORMIN 500 mg TABLET"), OCR)
    assert "value_not_in_source" in s.flags and s.needs_confirmation


@pytest.mark.parametrize("name,value,ok", [
    ("strength", "500 mg", True), ("strength", "5 mg/5 ml", True), ("strength", "lots", False), ("strength", "500", False),
    ("times_per_day", "2", True), ("times_per_day", "0", False), ("times_per_day", "7", False), ("times_per_day", "twice", False),
    ("total_quantity", "60", True), ("total_quantity", "sixty", False), ("dose_amount", "0.5", True), ("dose_amount", "1/2", True),
    ("meal_relation", "after_meal", True), ("meal_relation", "whenever", False),
    ("start_date", "2026-10-02", True), ("start_date", "02/10/2026", False), ("start_date", (date.today() + timedelta(days=3)).isoformat(), False),
])
def test_shapes_are_checked(name, value, ok):
    s = c.score_field(name, RawField(value=value, confidence=0.99, source_text="twice daily after meals 500 mg 60 02/10/2026"), OCR + " 60 0 7 1/2")
    assert ("invalid_shape" not in s.flags) is ok


# --- items and the decision ------------------------------------------------------------------------------------

def test_a_clear_listed_prescription_goes_to_confirm():
    r = raw(item())
    d = c.decide(r, [c.score_item(i, OCR, INDEX) for i in r.items])
    assert (d.status, d.review_mode, d.reasons) == ("needs_review", "confirm", [])


def test_one_low_field_sends_the_user_to_manual_entry():
    r = raw(item(strength=f("500 mg", 0.6, "500 mg")))
    d = c.decide(r, [c.score_item(i, OCR, INDEX) for i in r.items])
    assert (d.review_mode, d.reasons) == ("manual", ["low_confidence"])


def test_a_drug_not_in_the_list_is_unrecognised_and_goes_to_manual_entry():
    it = item(name=f("ZORBLAXINE", src="ZORBLAXINE"))
    s = c.score_item(it, OCR + " ZORBLAXINE", INDEX)
    assert not s.recognised and s.fields["name"].confidence <= 0.4
    d = c.decide(raw(it), [s])
    assert d.review_mode == "manual" and "unrecognised" in d.reasons


def test_a_misread_name_close_to_a_real_drug_is_not_trusted():
    s = c.score_item(item(name=f("Metfromin", src="Metfromin")), OCR + " Metfromin", INDEX)
    assert s.fields["name"].confidence <= 0.8 or s.drug_match is not None


def test_a_missing_required_field_goes_to_manual_entry():
    r = raw(item(times_per_day=RawField()))
    d = c.decide(r, [c.score_item(i, OCR, INDEX) for i in r.items])
    assert d.review_mode == "manual" and "missing_required" in d.reasons


def test_a_missing_total_supplied_goes_to_manual_entry():
    r = raw(item(total_quantity=RawField()))
    d = c.decide(r, [c.score_item(i, OCR, INDEX) for i in r.items])
    assert d.review_mode == "manual" and "missing_required" in d.reasons


def test_a_missing_optional_field_does_not_force_manual_entry():
    r = raw(item())          # no prescriber, no date
    assert c.decide(r, [c.score_item(i, OCR, INDEX) for i in r.items]).review_mode == "confirm"


def test_an_unlisted_supplement_is_normal_not_a_fault():
    it = RawItem(item_type="supplement", name=f("OMEGA-3 FISH OIL", src="OMEGA-3 FISH OIL"), times_per_day=f("1", src="1 capsule daily"))
    s = c.score_item(it, "OMEGA-3 FISH OIL Take 1 capsule daily", INDEX)
    assert s.recognised and s.drug_match is None and not s.fields["name"].needs_confirmation


def test_unreadable_or_not_a_medicine_fails_and_offers_manual_entry():
    assert c.decide(raw(readable=False), []).reasons == ["unreadable"]
    d = c.decide(raw(med=False), [])
    assert (d.status, d.review_mode, d.reasons) == ("failed", "manual", ["not_a_medicine"])
    assert c.decide(raw(), []).status == "failed"


def test_a_stricter_threshold_flags_more_fields():
    r = raw(item(strength=f("500 mg", 0.9, "500 mg")))
    assert c.decide(r, [c.score_item(i, OCR, INDEX, 0.85) for i in r.items]).review_mode == "confirm"
    assert c.decide(r, [c.score_item(i, OCR, INDEX, 0.95) for i in r.items]).review_mode == "manual"


def test_an_as_needed_label_needs_no_times_a_day():
    r = raw(item(times_per_day=RawField(), when_to_take=f("as_needed", src="when necessary")))
    d = c.decide(r, [c.score_item(i, OCR + " when necessary", INDEX) for i in r.items])
    assert d.review_mode == "confirm" and d.reasons == []
    r2 = raw(item(times_per_day=RawField()))                              # no times and not as needed: still a gap
    assert "missing_required" in c.decide(r2, [c.score_item(i, OCR, INDEX) for i in r2.items]).reasons
