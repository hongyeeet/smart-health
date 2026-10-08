"""How a dose is named and described on the Home page: what to take (not how strong it is), and when."""
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app.services import dose_store as d

TZ = ZoneInfo("Asia/Singapore")


@pytest.mark.parametrize("name,strength,expected", [
    ("Metformin 500 mg", "500 mg", "Metformin"), ("Amlodipine 5 mg", None, "Amlodipine"), ("Fish oil", None, "Fish oil"),
    ("CRESTOR", "10 mg", "CRESTOR"), ("Vitamin D3 1000 IU", None, "Vitamin D3"), ("Atorvastatin  20mg", "20 mg", "Atorvastatin"),
    ("Herbal tonic (label not readable)", None, "Herbal tonic (label not readable)"), ("500 mg", "500 mg", "500 mg"),
])
def test_the_strength_is_taken_out_of_the_name(name, strength, expected):
    assert d.short_name(name, strength) == expected


@pytest.mark.parametrize("args,expected", [
    (("Metformin 500 mg", "500 mg", "prescription", None, Decimal("1.0")), "Metformin, 1 Tab"),
    (("Metformin 500 mg", "500 mg", "prescription", None, Decimal("2")), "Metformin, 2 Tabs"),
    (("CRESTOR", "10 mg", "prescription", "Take 1 tab/s every morning For cholesterol lowering", Decimal("1")), "CRESTOR, 1 Tab"),
    (("Fish oil", None, "supplement", "Supplement taken with breakfast.", Decimal("1")), "Fish oil, 1 Capsule"),
    (("Fish oil", None, "supplement", None, Decimal("2")), "Fish oil, 2 Capsules"),
    (("Cough syrup", None, "otc", "Take 5 ml three times a day", Decimal("5")), "Cough syrup, 5 ml"),
    (("Herbal tonic", None, "tcm", None, Decimal("1")), "Herbal tonic, 1 Dose"),
    (("Metformin", None, "prescription", None, Decimal("0.5")), "Metformin, 0.5 Tab"),
    (("Amoxicillin", None, "prescription", "Take 2 capsules daily", Decimal("2")), "Amoxicillin, 2 Capsules"),
])
def test_a_dose_is_named_by_what_to_take(args, expected):
    assert d.dose_title(*args) == expected


def test_phrases_say_which_dose_and_when():
    now = datetime(2026, 10, 8, 21, 30, tzinfo=TZ)
    at = lambda day, h: datetime(2026, 10, day, h, 0, tzinfo=TZ)   # noqa: E731
    assert d.day_phrase(at(8, 8), now) == "This morning's dose"
    assert d.day_phrase(at(7, 20), now) == "Yesterday's evening dose"
    assert d.day_phrase(at(5, 22), now) == "Monday's night dose"
    assert d.when_phrase(at(9, 8), now) == "tomorrow at 8:00 am"
    assert d.when_phrase(at(8, 22), now) == "today at 10:00 pm"
