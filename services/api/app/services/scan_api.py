"""Turn a stored scan into what the app shows, and what the user confirms back into a medicine to save (prd F2, screens H3 and H4).

Pure code: no model, no database, no network. The scan itself is read and scored by `scan_extractor` and stored by `scan_store`;
this file only reshapes it. Nothing here guesses: a value is either on the label, typed by the user, or missing.
"""
from __future__ import annotations

import re
from datetime import date, time
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Any, Mapping

from app.core.errors import ValidationFailed
from app.schemas.medicine_scan import REQUIRED_FIELDS, ConfirmedMedication, DoseTime

THRESHOLD = 0.85
LABELS = {
    "name": "Medicine name", "strength": "Strength", "dose_amount": "Amount each time", "dose_unit": "Unit", "times_per_day": "Times a day",
    "when_to_take": "When to take it", "meal_relation": "Before or after food", "meal_offset_minutes": "Minutes from food",
    "drowsiness_warning": "Drowsiness warning", "directions": "Directions on the label", "prescriber": "Prescribed by",
    "start_date": "Date on the label", "total_quantity": "Total supplied",
}
ORDER = tuple(LABELS)
# Clock times suggested for N doses a day. They are suggestions the person changes: a label says "twice a day", never "8 am and 8 pm".
DEFAULT_TIMES = {1: ["08:00"], 2: ["08:00", "20:00"], 3: ["08:00", "13:00", "20:00"], 4: ["08:00", "12:00", "16:00", "20:00"],
                 5: ["07:00", "11:00", "15:00", "19:00", "22:00"], 6: ["07:00", "10:00", "13:00", "16:00", "19:00", "22:00"]}
WHEN_TIME = {"morning": "08:00", "noon": "12:00", "afternoon": "15:00", "evening": "18:00", "night": "21:00", "bedtime": "22:00"}
KIND_FOR_ITEM = {"prescription_label": "prescription", "otc": "otc", "supplement": "supplement", "tcm": "tcm"}
MEAL_TEXT = {"before_meal": "before meals", "after_meal": "after meals", "with_meal": "with food", "na": "with or without food"}
# Why a scan sends the person to type the form, in the words the app shows (rules.md: plain, one next step, never a guess).
REASON_TEXT = {
    "unrecognised": "I'm not able to identify this medication. Please check with your pharmacist, and type it in below.",
    "low_confidence": "Some of the label was hard to read, so please type it in yourself.",
    "missing_required": "We could not find the name, how often or the total on the label, so please type it in.",
    "several_items": "There is more than one medicine in this photo. Please add them one at a time.",
    "unreadable": "The photo is too blurred, dark or cut off to read. Retake it, or type the medicine in.",
    "ocr_empty": "We could not find any text in the photo. Retake it with the label in good light, or type the medicine in.",
    "not_a_medicine": "This does not look like a medicine label. Retake the photo, or type the medicine in.",
    "invalid_json": "We could not read this label just now. Please type the medicine in.",
    "service_unavailable": "The label reader is not available right now. Your medicines still work: please type it in.",
    "file_type_not_allowed": "That file type is not supported. Use a JPEG or PNG photo, or type the medicine in.",
    "file_too_large": "That photo is too large (over 10 MB). Retake it, or type the medicine in.",
    "file_empty": "That photo was empty. Retake it, or type the medicine in.",
}


def reason_text(reasons: list[str]) -> str:
    for r in ("unreadable", "ocr_empty", "not_a_medicine", "service_unavailable", "invalid_json", "file_type_not_allowed", "file_too_large",
              "file_empty", "several_items", "unrecognised", "missing_required", "low_confidence"):
        if r in reasons:
            return REASON_TEXT[r]
    return REASON_TEXT["low_confidence"]


def clock12(hhmm: str) -> str:
    h, m = (int(x) for x in hhmm.split(":"))
    return time(h, m).strftime("%I:%M %p").lstrip("0").lower()


def default_times(per_day: int | None, when_to_take: str | None) -> list[str]:
    """Suggested clock times: the part of the day the label names for one dose, otherwise an even spread."""
    if when_to_take == "as_needed":
        return []                                   # taken only when needed: no clock time
    if per_day == 1 and when_to_take in WHEN_TIME:
        return [WHEN_TIME[when_to_take]]
    return list(DEFAULT_TIMES.get(per_day or 0, []))


def is_as_needed(extraction: Mapping[str, Any] | None) -> bool:
    item = first_item(extraction)
    return bool(item) and ((item or {}).get("fields", {}).get("when_to_take") or {}).get("value") == "as_needed"


def first_item(extraction: Mapping[str, Any] | None) -> dict[str, Any] | None:
    items = (extraction or {}).get("items") or []
    return items[0] if len(items) == 1 else None


def review_mode(extraction: Mapping[str, Any] | None) -> tuple[str, list[str]]:
    """'confirm' only when exactly one medicine was read cleanly. Everything else is 'manual', with a reason."""
    ex = extraction or {}
    reasons = list(ex.get("reasons") or [])
    if len(ex.get("items") or []) > 1:
        return "manual", sorted({*reasons, "several_items"})
    return ("confirm" if ex.get("review_mode") == "confirm" and first_item(ex) else "manual"), reasons


def api_fields(extraction: Mapping[str, Any] | None, threshold: float = THRESHOLD) -> list[dict[str, Any]]:
    """The fields of the one medicine, in reading order, as the review screen lists them. Missing ones are not invented."""
    item = first_item(extraction)
    if not item:
        return []
    out = []
    as_needed = is_as_needed(extraction)
    for key in ORDER:
        f = (item.get("fields") or {}).get(key)
        if not f or f.get("value") is None:
            if key in REQUIRED_FIELDS and not (key == "times_per_day" and as_needed):
                out.append({"key": key, "label": LABELS[key], "value": None, "confidence": 0.0, "sourceText": None, "level": "unreadable"})
            continue
        conf = float(f.get("confidence") or 0)
        out.append({"key": key, "label": LABELS[key], "value": f["value"], "confidence": conf, "sourceText": f.get("source_text"),
                    "level": "high" if conf >= threshold else "check"})
    return out


def api_schedule(extraction: Mapping[str, Any] | None) -> list[dict[str, str]]:
    """Suggested dose times for the plan screen (H4)."""
    item = first_item(extraction)
    if not item or is_as_needed(extraction):
        return []
    f = item.get("fields") or {}
    per_day = _int((f.get("times_per_day") or {}).get("value"))
    when = (f.get("when_to_take") or {}).get("value")
    meal = MEAL_TEXT.get((f.get("meal_relation") or {}).get("value") or "")
    times = default_times(per_day, when)
    return [{"time": t, "label": f"Dose {i + 1}" + (f", {meal}" if meal else "")} for i, t in enumerate(times)]


def _int(v: Any) -> int | None:
    return int(v) if isinstance(v, str) and re.fullmatch(r"\d{1,6}", v.strip()) else None


def _amount(v: str | None) -> Decimal:
    """'1' -> 1, '0.5' -> 0.5, '1/2' -> 0.5. Anything else is one unit: the plan screen shows it, so the person can see and change it."""
    try:
        if v and "/" in v:
            return Decimal(str(float(Fraction(v.strip()))))
        return Decimal(v.strip().replace(",", ".")) if v else Decimal(1)
    except (InvalidOperation, ValueError, ZeroDivisionError):
        return Decimal(1)


def build_confirmed(extraction: Mapping[str, Any] | None, edits: Mapping[str, str | None], times: list[str] | None, kind: str | None,
                    today: date) -> ConfirmedMedication:
    """The medicine the person confirmed: the label values with their edits on top, and the times they chose. Raises ValidationFailed
    with a plain message if something required is missing: the caller returns it to the screen and nothing is saved."""
    item = first_item(extraction)
    if item is None:
        raise ValidationFailed("This scan has no single medicine to save. Please type it in.", code="scan_not_confirmable")
    fields = item.get("fields") or {}

    def val(key: str) -> str | None:
        if key in edits:
            v = edits[key]
            return v.strip() if isinstance(v, str) and v.strip() else None
        v = (fields.get(key) or {}).get("value")
        return v.strip() if isinstance(v, str) and v.strip() else None

    name = val("name")
    if not name:
        raise ValidationFailed("Type the medicine name to continue.", code="missing_name")
    total = _int(val("total_quantity"))
    if not total or total < 1:
        raise ValidationFailed("Type the total you were given, for example 30.", code="missing_total")
    chosen = [t for t in (times or []) if re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", t or "")]
    if times and len(chosen) != len(times):
        raise ValidationFailed("One of the dose times is not a valid time.", code="bad_time")
    as_needed = not chosen and val("when_to_take") == "as_needed"      # a label that says "when necessary" has no clock time
    if not chosen and not as_needed:
        chosen = default_times(_int(val("times_per_day")), val("when_to_take"))
    if not chosen and not as_needed:
        raise ValidationFailed("Choose at least one dose time.", code="missing_time")
    if len(set(chosen)) != len(chosen):
        raise ValidationFailed("Each time of day can only be listed once.", code="duplicate_time")
    meal = val("meal_relation")
    meal = meal if meal in ("before_meal", "after_meal") else "na"
    start: date | None = None
    if val("start_date"):
        try:
            start = date.fromisoformat(val("start_date") or "")
        except ValueError:
            start = None
        if start and start > today:
            start = None
    qty = _amount(val("dose_amount"))
    return ConfirmedMedication(
        name=name, kind=kind or KIND_FOR_ITEM.get(item.get("item_type") or "", "prescription"),  # type: ignore[arg-type]
        strength=val("strength"),
        doses=[DoseTime(dose_time=None, quantity=qty if qty > 0 else Decimal(1), meal_relation=meal)] if as_needed  # type: ignore[arg-type]
        else [DoseTime(dose_time=time(int(t[:2]), int(t[3:])), quantity=qty if qty > 0 else Decimal(1), meal_relation=meal)  # type: ignore[arg-type]
              for t in sorted(chosen)],
        directions=val("directions"), prescriber=val("prescriber"), total_quantity=total, start_date=start,
    )
