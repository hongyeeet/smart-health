"""Reshaping a stored scan for the screens, and turning what the person confirmed into a medicine to save. Pure code."""
from datetime import date, time
from decimal import Decimal

import pytest

from app.core.errors import ValidationFailed
from app.services import scan_api as s

TODAY = date(2026, 10, 7)


def field(value, conf=0.97):
    return {"value": value, "confidence": conf, "model_confidence": conf, "source_text": value, "flags": [], "needs_confirmation": conf < 0.85}


def extraction(mode="confirm", reasons=(), fields=None, item_type="prescription_label", items=1):
    base = {"name": field("PARACETAMOL"), "strength": field("500 mg"), "dose_amount": field("2"), "times_per_day": field("4"),
            "meal_relation": field("after_meal"), "directions": field("TAKE 2 TAB/S 4 times a day FOR FEVER/PAIN TAKE AFTER FOOD"),
            "start_date": field("2026-04-13"), "total_quantity": field("30")}
    base.update(fields or {})
    item = {"item_type": item_type, "recognised": True, "min_confidence": 0.97, "drug_match": None, "ingredients": [], "fields": base}
    return {"review_mode": mode, "reasons": list(reasons), "mask_summary": {}, "items": [item] * items}


# --- what the screen is told -------------------------------------------------------------------------------

def test_one_clean_medicine_is_confirm_and_lists_its_fields_in_reading_order():
    mode, reasons = s.review_mode(extraction())
    assert (mode, reasons) == ("confirm", [])
    keys = [f["key"] for f in s.api_fields(extraction())]
    assert keys == ["name", "strength", "dose_amount", "times_per_day", "meal_relation", "directions", "start_date", "total_quantity"]
    assert all(f["level"] == "high" for f in s.api_fields(extraction()))


def test_a_manual_scan_stays_manual_and_says_why_in_plain_words():
    ex = extraction("manual", ["unrecognised", "low_confidence"])
    assert s.review_mode(ex) == ("manual", ["unrecognised", "low_confidence"])
    assert "not able to identify" in s.reason_text(["unrecognised", "low_confidence"])
    assert "blurred" in s.reason_text(["unreadable"])


def test_more_than_one_medicine_on_a_photo_is_manual():
    mode, reasons = s.review_mode(extraction(items=2))
    assert mode == "manual" and "several_items" in reasons


def test_a_failed_scan_has_no_fields_and_is_manual():
    ex = {"review_mode": "manual", "reasons": ["ocr_empty"], "items": []}
    assert s.review_mode(ex) == ("manual", ["ocr_empty"]) and s.api_fields(ex) == [] and s.api_schedule(ex) == []


def test_a_missing_required_field_shows_as_unreadable_not_invented():
    f = {x["key"]: x for x in s.api_fields(extraction("manual", ["missing_required"], fields={"total_quantity": {"value": None, "confidence": 0}}))}
    assert f["total_quantity"]["value"] is None and f["total_quantity"]["level"] == "unreadable"
    assert "prescriber" not in f                                    # an optional field the label lacks is simply absent


def test_every_reason_the_scanner_can_give_has_words_for_the_screen():
    for r in ("unrecognised", "low_confidence", "missing_required", "several_items", "unreadable", "ocr_empty", "not_a_medicine", "invalid_json",
              "service_unavailable", "file_type_not_allowed", "file_too_large", "file_empty"):
        assert s.reason_text([r])


# --- suggested dose times -----------------------------------------------------------------------------------

@pytest.mark.parametrize("per_day,when,expected", [(1, None, ["08:00"]), (1, "night", ["21:00"]), (1, "as_needed", ["08:00"]), (2, None, ["08:00", "20:00"]),
                                                  (3, "morning", ["08:00", "13:00", "20:00"]), (4, None, ["08:00", "12:00", "16:00", "20:00"]),
                                                  (6, None, ["07:00", "10:00", "13:00", "16:00", "19:00", "22:00"]), (None, None, []), (7, None, [])])
def test_suggested_times(per_day, when, expected):
    assert s.default_times(per_day, when) == expected


def test_the_plan_screen_gets_one_suggestion_per_dose_with_the_meal_wording():
    plan = s.api_schedule(extraction(fields={"times_per_day": field("2"), "meal_relation": field("before_meal")}))
    assert plan == [{"time": "08:00", "label": "Dose 1, before meals"}, {"time": "20:00", "label": "Dose 2, before meals"}]


# --- what is saved -----------------------------------------------------------------------------------------

def test_the_label_values_become_the_medicine_to_save():
    m = s.build_confirmed(extraction(), {}, ["08:00", "12:00", "16:00", "20:00"], None, TODAY)
    assert (m.name, m.kind, m.strength, m.total_quantity, m.start_date) == ("PARACETAMOL", "prescription", "500 mg", 30, date(2026, 4, 13))
    assert [d.dose_time for d in m.doses] == [time(8), time(12), time(16), time(20)]
    assert all(d.quantity == Decimal("2") and d.meal_relation == "after_meal" for d in m.doses)
    assert "AFTER FOOD" in m.directions


def test_the_persons_edits_win_over_the_label():
    m = s.build_confirmed(extraction(), {"name": " Panadol ", "total_quantity": "20", "strength": ""}, ["08:00"], "otc", TODAY)
    assert (m.name, m.total_quantity, m.strength, m.kind) == ("Panadol", 20, None, "otc")


def test_without_chosen_times_the_suggestions_are_used():
    m = s.build_confirmed(extraction(fields={"times_per_day": field("2")}), {}, None, None, TODAY)
    assert [d.dose_time for d in m.doses] == [time(8), time(20)]


def test_one_dose_a_day_keeps_the_part_of_the_day_from_the_label():
    m = s.build_confirmed(extraction(fields={"times_per_day": field("1"), "when_to_take": field("morning")}), {}, ["08:00"], None, TODAY)
    assert m.doses[0].when_to_take == "morning"
    m2 = s.build_confirmed(extraction(fields={"times_per_day": field("2"), "when_to_take": field("morning")}), {}, ["08:00", "20:00"], None, TODAY)
    assert all(d.when_to_take is None for d in m2.doses)


@pytest.mark.parametrize("meal,expected", [("with_meal", "na"), ("na", "na"), ("whenever", "na"), ("before_meal", "before_meal")])
def test_only_before_or_after_food_is_kept_as_a_meal_relation(meal, expected):
    m = s.build_confirmed(extraction(fields={"meal_relation": field(meal)}), {}, ["08:00"], None, TODAY)
    assert m.doses[0].meal_relation == expected


@pytest.mark.parametrize("raw,expected", [("1", "1"), ("0.5", "0.5"), ("1/2", "0.5"), ("2,5", "2.5"), ("lots", "1"), ("0", "1"), (None, "1")])
def test_the_amount_each_time(raw, expected):
    f = {"dose_amount": field(raw)} if raw is not None else {"dose_amount": {"value": None, "confidence": 0}}
    m = s.build_confirmed(extraction(fields=f), {}, ["08:00"], None, TODAY)
    assert m.doses[0].quantity == Decimal(expected)


def test_a_future_or_bad_start_date_is_dropped_not_saved():
    assert s.build_confirmed(extraction(fields={"start_date": field("2027-01-01")}), {}, ["08:00"], None, TODAY).start_date is None
    assert s.build_confirmed(extraction(fields={"start_date": field("13/04/2026")}), {}, ["08:00"], None, TODAY).start_date is None


@pytest.mark.parametrize("edits,times,code", [
    ({"name": "  "}, ["08:00"], "missing_name"),
    ({"total_quantity": "0"}, ["08:00"], "missing_total"),
    ({"total_quantity": "many"}, ["08:00"], "missing_total"),
    ({}, ["08:00", "25:00"], "bad_time"),
    ({}, ["08:00", "08:00"], "duplicate_time"),
])
def test_missing_or_bad_values_stop_the_save_with_a_plain_message(edits, times, code):
    with pytest.raises(ValidationFailed) as e:
        s.build_confirmed(extraction(), edits, times, None, TODAY)
    assert e.value.code == code


def test_no_times_chosen_and_none_suggestible_stops_the_save():
    ex = extraction(fields={"times_per_day": {"value": None, "confidence": 0}})
    with pytest.raises(ValidationFailed) as e:
        s.build_confirmed(ex, {}, None, None, TODAY)
    assert e.value.code == "missing_time"


def test_a_scan_with_no_single_medicine_cannot_be_saved():
    with pytest.raises(ValidationFailed) as e:
        s.build_confirmed(extraction(items=2), {}, ["08:00"], None, TODAY)
    assert e.value.code == "scan_not_confirmable"


@pytest.mark.parametrize("item_type,kind", [("prescription_label", "prescription"), ("otc", "otc"), ("supplement", "supplement"), ("tcm", "tcm"),
                                           ("blister_or_box", "prescription"), ("unknown", "prescription")])
def test_the_kind_follows_the_item_type_unless_the_person_chooses(item_type, kind):
    assert s.build_confirmed(extraction(item_type=item_type), {}, ["08:00"], None, TODAY).kind == kind
