"""Confidence for scanned fields, and the decision between "confirm" and "type it yourself" (prd F2, rules.md section 1 rule 7).

The model's own score is a rough signal and is not calibrated, so every field's final confidence is the LOWER of that
score and a set of code checks:
  - the text the model says it read must really appear in the OCR text of the photo (guards against invented values)
  - the value must agree with that text
  - the name is read like every other field: it is NEVER checked against a medicine list (understanding the medicine comes later)
  - strength, times per day, dates and numbers must have a valid shape
Pure functions: no network, no database, no model. All thresholds are team placeholders (clinical validation pending).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Sequence

from rapidfuzz import fuzz

from app.schemas.medicine_scan import (
    FIELD_NAMES,
    REQUIRED_FIELDS,
    RawExtraction,
    RawField,
    RawItem,
    ReviewMode,
    ScoredField,
    ScoredItem,
)

THRESHOLD = 0.85            # below this a filled-in field must be typed by the user (the default, from settings)

# Per-field thresholds. A field listed here uses its own number instead of THRESHOLD. Owner: Joely. The owner may change these
# again. Only the medicine NAME is lower (0.6, plan section 13.4 and Q9): a wrong name is still caught on the review screen,
# where the person reads it. Strength, directions, times and dates stay at the default (D-064: any low field forces typing).
FIELD_THRESHOLDS: dict[str, float] = {
    "name": 0.6,
}
SOURCE_COVERAGE_MIN = 0.7   # at least this share of the quoted words must be found in the OCR text
VALUE_IN_SOURCE_MIN = 70.0
VALUE_IN_SOURCE_CAP = 0.6

STRENGTH_RE = re.compile(r"^\d+(?:[.,]\d+)?\s?(?:mg|mcg|µg|ug|g|ml|iu|units?|%|mmol)(?:\s?/\s?\d*(?:[.,]\d+)?\s?(?:ml|mg|g|l|tab|tablet|dose))?$", re.I)
MEAL = {"before_meal", "after_meal", "with_meal", "na"}
WHEN = {"morning", "noon", "afternoon", "evening", "night", "bedtime", "as_needed"}
# These are checked against the quoted text but are read from words ("twice daily" -> 2), so the value need not appear in it.
DERIVED = {"times_per_day", "meal_relation", "start_date", "when_to_take", "meal_offset_minutes", "drowsiness_warning"}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def _tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def token_coverage(quote: str, ocr_text: str) -> float:
    """Share of the quoted characters that belong to words found anywhere in the OCR text (small misreads allowed).
    The OCR drops spaces ("TAKE2TAB/S4timesaday") and reads sideways labels in a scrambled line order, so the check is
    made on the OCR text with every space and mark removed, and word order does not matter."""
    words = _tokens(quote)
    pool = re.sub(r"[^a-z0-9]", "", ocr_text.lower())
    total = sum(len(w) for w in words)
    if not words or not pool or total == 0:
        return 0.0
    found = sum(len(w) for w in words if w in pool or (len(w) >= 5 and fuzz.partial_ratio(w, pool) >= 85))
    return found / total


def threshold_for(name: str, threshold: float = THRESHOLD) -> float:
    """The confidence a field needs. A field listed in FIELD_THRESHOLDS uses its own number; every other field uses `threshold`."""
    return FIELD_THRESHOLDS.get(name, threshold)


def _cap(conf: float, limit: float, flags: list[str], flag: str) -> float:
    if conf > limit:
        flags.append(flag)
        return limit
    return conf


def _int_in(value: str, lo: int, hi: int) -> bool:
    return bool(re.fullmatch(r"\d{1,6}", value.strip())) and lo <= int(value) <= hi


def _valid_shape(name: str, value: str) -> bool:
    v = value.strip()
    if name == "strength":
        return bool(STRENGTH_RE.match(v))
    if name == "times_per_day":
        return _int_in(v, 1, 6)
    if name == "total_quantity":
        return _int_in(v, 0, 100000)
    if name == "dose_amount":
        return bool(re.fullmatch(r"\d+(?:[.,]\d+)?|\d+/\d+", v))
    if name == "meal_relation":
        return v in MEAL
    if name == "when_to_take":
        return v in WHEN
    if name == "meal_offset_minutes":
        return _int_in(v, 0, 240)
    if name == "drowsiness_warning":
        return v == "true"
    if name == "start_date":
        try:
            date.fromisoformat(v)
        except ValueError:
            return False
        return date.fromisoformat(v) <= date.today()
    return True


def score_field(name: str, raw: RawField, ocr_text: str, threshold: float = THRESHOLD) -> ScoredField:
    value = raw.value.strip() if raw.value and raw.value.strip() else None
    if value is None:
        return ScoredField(value=None, confidence=0.0, model_confidence=raw.confidence, source_text=None, needs_confirmation=False)
    flags: list[str] = []
    conf = raw.confidence
    src = raw.source_text.strip() if raw.source_text and raw.source_text.strip() else None
    if src is None:
        conf = _cap(conf, 0.5, flags, "no_source_text")
    else:
        if ocr_text and token_coverage(src, ocr_text) < SOURCE_COVERAGE_MIN:
            conf = _cap(conf, 0.55, flags, "source_not_in_ocr")
        if name not in DERIVED and fuzz.partial_ratio(_norm(value), _norm(src)) < VALUE_IN_SOURCE_MIN:
            # A value that disagrees with its quote is always flagged: its cap sits below the field's own threshold
            # (the name threshold is 0.6, so the name cap is 0.55, not 0.6).
            conf = _cap(conf, min(VALUE_IN_SOURCE_CAP, threshold_for(name, threshold) - 0.05), flags, "value_not_in_source")
    if not _valid_shape(name, value):
        conf = _cap(conf, 0.4, flags, "invalid_shape")
    return ScoredField(value=value, confidence=round(conf, 3), model_confidence=raw.confidence, source_text=src,
                       flags=flags, needs_confirmation=conf < threshold_for(name, threshold))


def score_item(item: RawItem, ocr_text: str, threshold: float = THRESHOLD) -> ScoredItem:
    """Score every field of one item. This is PURE reading: every field, the name included, is judged the same way (is it really on the
    label, does it agree with the text it was read from, is it the right shape). Nothing is looked up and nothing is matched to a
    medicine list: understanding the medicine comes later and never blocks a scan."""
    fields: dict[str, ScoredField] = {fname: score_field(fname, getattr(item, fname), ocr_text, threshold) for fname in FIELD_NAMES}
    present = [f.confidence for f in fields.values() if f.value is not None]
    return ScoredItem(item_type=item.item_type, fields=fields, ingredients=item.ingredients, min_confidence=min(present) if present else 0.0)


@dataclass(frozen=True)
class Decision:
    status: str                  # needs_review or failed
    review_mode: ReviewMode
    reasons: list[str]


# Shown to the user but never saved to the medicine, so a shaky read of these must not send a good scan to typing.
INFORMATION_ONLY = ("prescriber",)


def decide(raw: RawExtraction, items: Sequence[ScoredItem], threshold: float = THRESHOLD) -> Decision:
    """Any low field or missing required field sends the user to type it themselves. Whether the drug is in our list plays no part:
    the scanner only reads the label. Nothing is saved here."""
    if not raw.readable:
        return Decision("failed", "manual", ["unreadable"])
    if not raw.is_medication_item or not items:
        return Decision("failed", "manual", ["not_a_medicine"])
    reasons: list[str] = []
    for it in items:
        judged = {name: f for name, f in it.fields.items() if name not in INFORMATION_ONLY and f.value is not None}
        low = [name for name, f in judged.items() if f.needs_confirmation]
        if low:
            # Every filled field is low: the label was not read at all, so the screen says so and asks for another photo or typing.
            reasons.append("low_confidence_all" if len(low) == len(judged) else "low_confidence")
        as_needed = it.fields["when_to_take"].value == "as_needed"       # "when necessary" has no times per day: that is not a gap
        if any(it.fields[r].value is None for r in REQUIRED_FIELDS if not (r == "times_per_day" and as_needed)):
            reasons.append("missing_required")
    reasons = sorted(set(reasons))
    return Decision("needs_review", "manual" if reasons else "confirm", reasons)
