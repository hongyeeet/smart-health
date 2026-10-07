"""Confidence for scanned fields, and the decision between "confirm" and "type it yourself" (prd F2, rules.md section 1 rule 7).

The model's own score is a rough signal and is not calibrated, so every field's final confidence is the LOWER of that
score and a set of code checks:
  - the text the model says it read must really appear in the OCR text of the photo (guards against invented values)
  - the value must agree with that text
  - the drug name must match the drug list (`drug_aliases`); the model never chooses a database id
  - strength, times per day, dates and numbers must have a valid shape
Pure functions: no network, no database, no model. All thresholds are team placeholders (clinical validation pending).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Sequence

from rapidfuzz import fuzz, process

from app.schemas.medicine_scan import (
    FIELD_NAMES,
    REQUIRED_FIELDS,
    DrugMatch,
    RawExtraction,
    RawField,
    RawItem,
    ReviewMode,
    ScoredField,
    ScoredItem,
)

THRESHOLD = 0.85            # below this a filled-in field must be typed by the user
MATCH_OK = 92.0             # fuzzy score (0-100) at which a name counts as the same drug
MATCH_WEAK = 80.0           # between this and MATCH_OK: probably a misread, not trusted
SOURCE_COVERAGE_MIN = 0.7   # at least this share of the quoted words must be found in the OCR text
VALUE_IN_SOURCE_MIN = 70.0

STRENGTH_RE = re.compile(r"^\d+(?:[.,]\d+)?\s?(?:mg|mcg|µg|ug|g|ml|iu|units?|%|mmol)(?:\s?/\s?\d*(?:[.,]\d+)?\s?(?:ml|mg|g|l|tab|tablet|dose))?$", re.I)
FORM_WORDS = re.compile(r"\b(?:tablets?|tabs?|capsules?|caps?|film[- ]coated|extended[- ]release|sustained[- ]release|xr|sr|er|oral|syrup|suspension|"
                        r"injection|cream|gel|drops?|sachets?)\b", re.I)
STRENGTH_IN_NAME = re.compile(r"\b\d+(?:[.,]\d+)?\s?(?:mg|mcg|µg|ug|g|ml|iu|%)\b", re.I)
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


def clean_drug_text(name: str) -> str:
    n = STRENGTH_IN_NAME.sub(" ", name)
    n = FORM_WORDS.sub(" ", n)
    return _norm(re.sub(r"[^\w\s/+-]", " ", n))


class DrugIndex:
    """Names and aliases from the drug list, for matching a label's drug name. Built once from the database."""

    def __init__(self, rows: Iterable[tuple[str, str, str]]) -> None:
        """rows: (drug_reference_id, generic_name, text) where text is the generic name itself or one of its aliases."""
        self._ids: list[tuple[str, str]] = []
        self._texts: list[str] = []
        for ref_id, generic, text in rows:
            t = clean_drug_text(text)
            if t:
                self._ids.append((str(ref_id), generic))
                self._texts.append(t)

    def __len__(self) -> int:
        return len(self._texts)

    def words(self) -> set[str]:
        """Every word in the drug names: used so a drug name is never mistaken for a patient's name."""
        return {w for t in self._texts for w in re.findall(r"[a-z]+", t)}

    def match(self, name: str | None) -> DrugMatch | None:
        if not name or not self._texts:
            return None
        q = clean_drug_text(name)
        if not q:
            return None
        found = process.extractOne(q, self._texts, scorer=fuzz.WRatio, score_cutoff=MATCH_WEAK)
        if not found:
            return None
        text, score, idx = found
        if q == text:
            score = 100.0
        ref_id, generic = self._ids[idx]
        return DrugMatch(drug_reference_id=ref_id, generic_name=generic, matched_text=text, score=float(score))


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


def score_field(name: str, raw: RawField, ocr_text: str, threshold: float = THRESHOLD, *, name_cap: float | None = None) -> ScoredField:
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
            conf = _cap(conf, 0.6, flags, "value_not_in_source")
    if not _valid_shape(name, value):
        conf = _cap(conf, 0.4, flags, "invalid_shape")
    if name_cap is not None:
        conf = _cap(conf, name_cap, flags, "name_not_in_drug_list")
    return ScoredField(value=value, confidence=round(conf, 3), model_confidence=raw.confidence, source_text=src,
                       flags=flags, needs_confirmation=conf < threshold)


def score_item(item: RawItem, ocr_text: str, index: DrugIndex | None, threshold: float = THRESHOLD) -> ScoredItem:
    """Score every field of one item. Unlisted supplement and TCM names are normal (they are 'not checked'), not a fault."""
    match = index.match(item.name.value) if index else None
    listed = match is not None and match.score >= MATCH_OK
    must_be_listed = item.item_type in ("prescription_label", "blister_or_box", "otc", "unknown")
    name_cap: float | None = None
    if item.name.value and must_be_listed and index is not None and len(index):
        if match is None:
            name_cap = 0.4        # not in the drug list at all: "I'm not able to identify this medication"
        elif match.score < MATCH_OK:
            name_cap = 0.8        # close to a known drug but not the same: probably misread
    fields: dict[str, ScoredField] = {}
    for fname in FIELD_NAMES:
        fields[fname] = score_field(fname, getattr(item, fname), ocr_text, threshold, name_cap=name_cap if fname == "name" else None)
    present = [f.confidence for f in fields.values() if f.value is not None]
    recognised = listed or (item.item_type in ("supplement", "tcm") and fields["name"].value is not None)
    return ScoredItem(item_type=item.item_type, fields=fields, ingredients=item.ingredients,
                      drug_match=match if listed else None, recognised=recognised,
                      min_confidence=min(present) if present else 0.0)


@dataclass(frozen=True)
class Decision:
    status: str                  # needs_review or failed
    review_mode: ReviewMode
    reasons: list[str]


def decide(raw: RawExtraction, items: Sequence[ScoredItem], threshold: float = THRESHOLD) -> Decision:
    """Any low field, missing required field or unrecognised drug sends the user to type it themselves. Nothing is saved here."""
    if not raw.readable:
        return Decision("failed", "manual", ["unreadable"])
    if not raw.is_medication_item or not items:
        return Decision("failed", "manual", ["not_a_medicine"])
    reasons: list[str] = []
    for it in items:
        if any(f.needs_confirmation for f in it.fields.values()):
            reasons.append("low_confidence")
        if any(it.fields[r].value is None for r in REQUIRED_FIELDS):
            reasons.append("missing_required")
        if not it.recognised:
            reasons.append("unrecognised")
    reasons = sorted(set(reasons))
    return Decision("needs_review", "manual" if reasons else "confirm", reasons)
