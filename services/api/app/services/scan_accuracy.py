"""Compare what the scanner read with the answers a person wrote down (ground truth). Pure code, no model, no database.

Used by `scripts/scan_accuracy.py` to measure, per field, how often the scanner is right and whether its confidence tells
right from wrong. Everything is normalised first so "500MG", "500 mg" and "500mg" agree.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Mapping

from rapidfuzz import fuzz

COMPARED = ("item_type", "name", "strength", "dose_amount", "times_per_day", "when_to_take", "meal_relation", "meal_offset_minutes",
            "drowsiness_warning", "total_quantity", "start_date")
FORM_WORDS = re.compile(r"\b(?:tablets?|tabs?|capsules?|caps?|cap/s|tab/s)\b", re.I)


def _blank(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def norm_name(v: Any) -> str | None:
    if _blank(v):
        return None
    s = re.sub(r"\([^)]*\)", " ", str(v))               # drop a bracketed brand name: "(ALVERSIME)"
    s = FORM_WORDS.sub(" ", s)
    s = re.sub(r"\b\d+(?:[.,]\d+)?\s?(?:mg|mcg|g|ml)\b", " ", s, flags=re.I)
    s = re.sub(r"[^a-z+ ]", " ", s.lower())
    s = re.sub(r"\s*\+\s*", "+", s)
    return re.sub(r"\s+", " ", s).strip() or None


def norm_strength(v: Any) -> str | None:
    if _blank(v):
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(mg|mcg|µg|ug|g|ml|iu|%)", str(v), re.I)
    if not m:
        return re.sub(r"\s+", "", str(v).lower())
    num = m.group(1).replace(",", ".")
    num = num.rstrip("0").rstrip(".") if "." in num else num
    return f"{num} {m.group(2).lower().replace('µg', 'mcg').replace('ug', 'mcg')}"


def norm_number(v: Any) -> str | None:
    if _blank(v):
        return None
    m = re.search(r"\d+(?:[.,]\d+)?", str(v))
    if not m:
        return None
    n = m.group(0).replace(",", ".")
    return n.rstrip("0").rstrip(".") if "." in n else n


def norm_meal_relation(v: Any) -> str | None:
    if _blank(v):
        return None
    s = str(v).lower()
    if s in ("before_meal", "after_meal", "with_meal", "na"):
        return s
    if "before" in s:
        return "before_meal"
    if "after" in s:
        return "after_meal"
    if "with" in s:
        return "with_meal" if "without" not in s else "na"
    return None


def meal_offset_from_text(v: Any) -> str | None:
    """'half an hour before food' -> '30'; '1 hour after meals' -> '60'; '15 minutes before' -> '15'."""
    if _blank(v):
        return None
    s = str(v).lower()
    if "half an hour" in s or "half hour" in s:
        return "30"
    m = re.search(r"(\d+)\s*(hour|hr|min)", s)
    if not m:
        return None
    return str(int(m.group(1)) * (60 if m.group(2).startswith(("hour", "hr")) else 1))


def norm_date(v: Any, *, swap_excel: bool = False) -> str | None:
    """Day-month-year text or a date. `swap_excel`: a spreadsheet read '06-12-2025' as 12 June, so day and month are swapped back."""
    if _blank(v):
        return None
    if isinstance(v, datetime):
        v = v.date()
    if isinstance(v, date):
        return (date(v.year, v.day, v.month) if swap_excel and v.day <= 12 else v).isoformat()
    s = str(v).strip()
    m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", s)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    return s if m else None


def norm_bool_flag(v: Any) -> str | None:
    if _blank(v):
        return None
    return "true" if str(v).strip().lower() in ("1", "true", "yes", "y") else None


def norm_when(v: Any) -> str | None:
    return None if _blank(v) else str(v).strip().lower().replace(" ", "_")


def expected_from_sheet(row: Mapping[str, Any]) -> dict[str, str | None]:
    """Turn one row of the ground-truth sheet into the same normalised shape the scanner's fields are compared in."""
    meal_text = row.get("meal_relation")
    return {
        "item_type": None if _blank(row.get("item_type")) else str(row["item_type"]).strip(),
        "name": norm_name(row.get("name")),
        "strength": norm_strength(row.get("strength")),
        "dose_amount": norm_number(row.get("no_of_tabs")),
        "times_per_day": norm_number(row.get("times_per_day")),
        "when_to_take": norm_when(row.get("when_to_take")),
        "meal_relation": norm_meal_relation(meal_text),
        "meal_offset_minutes": meal_offset_from_text(meal_text),
        "drowsiness_warning": norm_bool_flag(row.get("drowsiness")),
        "total_quantity": norm_number(row.get("total_no_of_tabs")),
        "start_date": norm_date(row.get("start_date"), swap_excel=isinstance(row.get("start_date"), (datetime, date))),
    }


def normalise_scanned(field: str, value: str | None, item_type: str | None = None) -> str | None:
    if field == "item_type":
        return item_type
    return {
        "name": norm_name, "strength": norm_strength, "dose_amount": norm_number, "times_per_day": norm_number,
        "when_to_take": norm_when, "meal_relation": norm_meal_relation, "meal_offset_minutes": norm_number,
        "drowsiness_warning": norm_bool_flag, "total_quantity": norm_number, "start_date": norm_date,
    }[field](value)


def same(field: str, expected: str | None, got: str | None) -> bool:
    if field == "meal_relation":                  # "not stated" and "na" mean the same
        expected, got = (None if x == "na" else x for x in (expected, got))
    if expected is None or got is None:
        return expected is None and got is None
    if field == "name":
        return fuzz.token_set_ratio(expected, got) >= 85 or fuzz.partial_ratio(expected, got) >= 90
    return expected == got
