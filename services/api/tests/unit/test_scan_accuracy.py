"""The ground-truth comparison rules (pure code)."""
from datetime import datetime

import pytest

from app.services import scan_accuracy as a


@pytest.mark.parametrize("raw,expected", [("paracetamol tab", "paracetamol"), ("PARACETAMOL TAB 500MG", "paracetamol"),
                                         ("alverine citrate + simethicone tab", "alverine citrate+simethicone"),
                                         ("ALVERINE CITRATE + SIMETHICONE (ALVERSIME)", "alverine citrate+simethicone"), ("dexcophan", "dexcophan"), (None, None), ("", None)])
def test_names_are_normalised(raw, expected):
    assert a.norm_name(raw) == expected


@pytest.mark.parametrize("raw,expected", [("500MG", "500 mg"), ("500 mg", "500 mg"), ("5mg", "5 mg"), ("0.50 g", "0.5 g"), (None, None)])
def test_strengths_are_normalised(raw, expected):
    assert a.norm_strength(raw) == expected


@pytest.mark.parametrize("raw,rel,offset", [("after food", "after_meal", None), ("half an hour before food", "before_meal", "30"),
                                           ("1 hour after meals", "after_meal", "60"), ("with or without food", "na", None), (None, None, None)])
def test_meal_text_is_split_into_relation_and_minutes(raw, rel, offset):
    assert (a.norm_meal_relation(raw), a.meal_offset_from_text(raw)) == (rel, offset)


def test_a_spreadsheet_that_swapped_day_and_month_is_corrected():
    assert a.norm_date("13-04-2026") == "2026-04-13"
    assert a.norm_date(datetime(2025, 6, 12), swap_excel=True) == "2025-12-06"      # typed 06-12-2025
    assert a.norm_date(datetime(2025, 6, 12)) == "2025-06-12"


def test_one_sheet_row_becomes_comparable_values():
    e = a.expected_from_sheet({"item_type": "prescription_label", "name": "paracetamol tab", "strength": "500MG", "no_of_tabs": 2, "times_per_day": 4,
                               "when_to_take": None, "meal_relation": "after food", "drowsiness": 0, "total_no_of_tabs": "30tabs", "start_date": "13-04-2026"})
    assert e == {"item_type": "prescription_label", "name": "paracetamol", "strength": "500 mg", "dose_amount": "2", "times_per_day": "4",
                 "when_to_take": None, "meal_relation": "after_meal", "meal_offset_minutes": None, "drowsiness_warning": None,
                 "total_quantity": "30", "start_date": "2026-04-13"}


def test_comparison_rules():
    assert a.same("name", "alverine citrate+simethicone", "alverine citrate+simethicone") and not a.same("name", "paracetamol", "cetirizine")
    assert a.same("meal_relation", None, "na") and a.same("strength", None, None) and not a.same("strength", "5 mg", None)
