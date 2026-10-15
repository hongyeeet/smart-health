"""The extractor agent: vision model → strict JSON medication fields (E3-1).

This is the core of the scan feature. The vision model (Claude Sonnet 5.5 via Vertex AI, per
ai-models.md) reads the label photo and returns structured fields with confidence per field
and the source text it found. The output is validated with Pydantic; on validation failure,
retry once, then fail safe (rules.md 4 and 6).

Patient name, NRIC, phone and address are never stored — the prompt instructs the model to
ignore them, and a post-processing step strips any that slip through (rules.md 3).

When E0-3 lands, the _call_vision_model() function is replaced with the real Vertex AI call
through llm/gateway.py. The rest of the agent stays the same.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.schemas.scan import (
    ItemType,
    ScanConfidenceLevel,
    ScanFieldSchema,
    ScanResult,
    ScanScheduleItem,
    ScanStatus,
)

logger = logging.getLogger(__name__)

PROMPT_VERSION = "extractor-v1"
MODEL_ID = settings.llm_vision_model or "stub-vision"

# Fields the model must never return (privacy: rules.md 3, ai-models.md 6).
_FORBIDDEN_KEYS = {"patient_name", "name_patient", "nric", "phone", "address", "patient_id"}

# The JSON schema the model must return. Each field has value + confidence + source_text.
EXTRACTION_SCHEMA = {
    "item_type": "prescription_label | blister_or_box | supplement | tcm | otc | unknown",
    "items": [
        {
            "name": {"value": "string or null", "confidence": "0.0-1.0", "source_text": "string or null"},
            "strength": {"value": "string or null", "confidence": "0.0-1.0", "source_text": "string or null"},
            "dose": {"value": "string or null", "confidence": "0.0-1.0", "source_text": "string or null"},
            "frequency": {"value": "string or null", "confidence": "0.0-1.0", "source_text": "string or null"},
            "timing": {"value": "string or null", "confidence": "0.0-1.0", "source_text": "string or null"},
            "duration": {"value": "string or null", "confidence": "0.0-1.0", "source_text": "string or null"},
        }
    ],
    "description": "one-sentence plain-language description of what the medicine is for, or null",
    "schedule": [{"time": "e.g. 8:30 am", "label": "e.g. After breakfast"}],
}

# The system prompt. In production this lives in agents/prompts/extractor.md with a version header.
SYSTEM_PROMPT = """You are a medicine label reader. You read photos of prescription labels, medication boxes,
supplement packaging, TCM products and OTC medicines.

Your job: extract structured fields from the photo. Return STRICT JSON only — no markdown, no explanation.

Rules:
1. NEVER extract or include patient name, NRIC, phone number, address, or any personal identifier.
   If you see these on the label, ignore them completely.
2. For each field, return the value, a confidence score (0.0 to 1.0), and the exact source text you
   found on the label (source_text). If you cannot read a field, return value=null, confidence=0.0,
   source_text=null.
3. NEVER guess. If you are unsure, set confidence below 0.85. If you cannot read it at all, set value=null.
4. Also return a one-sentence plain-language description of what the medicine is for, if you can tell.
   If you cannot tell, return null.
5. If you can parse dose times from the label, return them in the schedule array.

Return JSON in this exact shape:
{{
  "item_type": "prescription_label | blister_or_box | supplement | tcm | otc | unknown",
  "items": [
    {{
      "name": {{"value": "...", "confidence": 0.95, "source_text": "..."}},
      "strength": {{"value": "...", "confidence": 0.9, "source_text": "..."}},
      "dose": {{"value": "...", "confidence": 0.9, "source_text": "..."}},
      "frequency": {{"value": "...", "confidence": 0.7, "source_text": "..."}},
      "timing": {{"value": "...", "confidence": 0.6, "source_text": "..."}},
      "duration": {{"value": "...", "confidence": 0.8, "source_text": "..."}}
    }}
  ],
  "description": "...",
  "schedule": [{{"time": "8:30 am", "label": "After breakfast"}}]
}}
"""


@dataclass
class ExtractionResult:
    """Parsed extraction result, validated."""

    item_type: ItemType
    fields: list[ScanFieldSchema]
    description: str | None
    schedule: list[ScanScheduleItem]
    model_id: str
    prompt_version: str
    raw_output: str
    error: str | None = None


def _confidence_level(score: float) -> ScanConfidenceLevel:
    """Map numeric confidence to the UI level: >= 0.85 high, > 0 check, 0/null unreadable."""
    if score >= 0.85:
        return ScanConfidenceLevel.high
    if score > 0.0:
        return ScanConfidenceLevel.check
    return ScanConfidenceLevel.unreadable


def _strip_forbidden(data: dict[str, Any]) -> dict[str, Any]:
    """Remove patient name, NRIC, phone, address from the extraction (rules.md 3)."""
    if not isinstance(data, dict):
        return data
    cleaned = {}
    for k, v in data.items():
        if k.lower() in _FORBIDDEN_KEYS:
            logger.warning("Stripped forbidden field '%s' from extraction", k)
            continue
        cleaned[k] = v
    return cleaned


def _parse_item(item: dict[str, Any]) -> list[ScanFieldSchema]:
    """Parse one item from the model output into ScanFieldSchema list."""
    field_labels = {
        "name": "Medicine",
        "strength": "Strength",
        "dose": "How much",
        "frequency": "How often",
        "timing": "When",
        "duration": "For how long",
    }
    fields: list[ScanFieldSchema] = []
    for key, label in field_labels.items():
        raw = item.get(key, {})
        if not isinstance(raw, dict):
            raw = {"value": raw, "confidence": 0.0, "source_text": None}
        value = raw.get("value")
        confidence = float(raw.get("confidence", 0.0) or 0.0)
        source_text = raw.get("source_text")
        # null or empty string → null (rules.md 3: never empty string)
        if value is not None and not str(value).strip():
            value = None
        if value is None:
            confidence = 0.0
        fields.append(
            ScanFieldSchema(
                key=key,
                label=label,
                value=value,
                confidence=confidence,
                source_text=source_text,
                level=_confidence_level(confidence),
            )
        )
    return fields


def _parse_schedule(schedule_raw: list[dict] | None) -> list[ScanScheduleItem]:
    """Parse the schedule array."""
    if not schedule_raw:
        return []
    result: list[ScanScheduleItem] = []
    for item in schedule_raw:
        if not isinstance(item, dict):
            continue
        time = item.get("time", "")
        label = item.get("label", "")
        if time:
            result.append(ScanScheduleItem(time=time, label=label or "Dose"))
    return result


def _validate_extraction(raw_json: dict[str, Any]) -> ExtractionResult:
    """Validate the model's JSON output against the expected schema.

    Returns an ExtractionResult. Does not raise — invalid fields become null.
    """
    # Strip forbidden fields first
    cleaned = _strip_forbidden(raw_json)

    # Parse item_type
    item_type_str = cleaned.get("item_type", "unknown")
    try:
        item_type = ItemType(item_type_str)
    except ValueError:
        item_type = ItemType.unknown

    # Parse items (take the first item — multiple items per photo is a later enhancement)
    items = cleaned.get("items", [])
    if not isinstance(items, list) or not items:
        fields: list[ScanFieldSchema] = []
    else:
        first_item = items[0] if isinstance(items[0], dict) else {}
        fields = _parse_item(first_item)

    # Parse description
    description = cleaned.get("description")
    if description is not None and not str(description).strip():
        description = None

    # Parse schedule
    schedule_raw = cleaned.get("schedule", [])
    schedule = _parse_schedule(schedule_raw if isinstance(schedule_raw, list) else None)

    return ExtractionResult(
        item_type=item_type,
        fields=fields,
        description=description,
        schedule=schedule,
        model_id=MODEL_ID,
        prompt_version=PROMPT_VERSION,
        raw_output=json.dumps(cleaned, ensure_ascii=False),
    )


def _call_vision_model(image_bytes: bytes, mime_type: str) -> dict[str, Any]:
    """Call the vision model to read the label.

    STUB for E0-3: returns the demo Clarithromycin result so the full flow works end-to-end.
    When E0-3 lands, this calls llm/gateway.py which talks to Vertex AI.
    """
    if settings.demo_mode or not settings.google_cloud_project:
        return _demo_extraction()

    # Real call would go through llm/gateway.py:
    # from app.llm.gateway import vision_extract
    # return vision_extract(image_bytes, mime_type, SYSTEM_PROMPT, EXTRACTION_SCHEMA)
    return _demo_extraction()


def _demo_extraction() -> dict[str, Any]:
    """The demo extraction result (matches apps/mock scanResult fixture)."""
    return {
        "item_type": "prescription_label",
        "items": [
            {
                "name": {"value": "Clarithromycin 500 mg", "confidence": 0.95, "source_text": "CLARITHROMYCIN 500MG"},
                "strength": {"value": "500 mg", "confidence": 0.92, "source_text": "500MG"},
                "dose": {"value": "1 tablet", "confidence": 0.88, "source_text": "TAKE ONE TABLET"},
                "frequency": {"value": "Twice daily after meals", "confidence": 0.72, "source_text": "BID AFTER MEALS"},
                "timing": {"value": "after meals", "confidence": 0.68, "source_text": "AFTER MEALS"},
                "duration": {"value": "7 days", "confidence": 0.85, "source_text": "FOR 7 DAYS"},
            }
        ],
        "description": "An antibiotic for bacterial infections, taken as a short course.",
        "schedule": [
            {"time": "8:30 am", "label": "After breakfast"},
            {"time": "8:30 pm", "label": "After dinner"},
        ],
    }


def extract_label(image_bytes: bytes, mime_type: str = "image/jpeg") -> ExtractionResult:
    """Run the extractor on a label image.

    Calls the vision model, validates the JSON output, retries once on failure,
    then fails safe (returns a failed result, never raises).

    Args:
        image_bytes: raw image bytes
        mime_type: image MIME type

    Returns:
        ExtractionResult with parsed fields, or error set if extraction failed.
    """
    start = time.time()
    last_error: str | None = None

    for attempt in range(settings.llm_max_retries + 1):
        try:
            raw = _call_vision_model(image_bytes, mime_type)
            result = _validate_extraction(raw)
            latency_ms = int((time.time() - start) * 1000)
            logger.info(
                "extraction attempt=%d ok fields=%d latency_ms=%d model=%s",
                attempt + 1,
                len(result.fields),
                latency_ms,
                result.model_id,
            )
            return result
        except Exception as e:
            last_error = str(e)
            logger.warning("extraction attempt=%d failed: %s", attempt + 1, e)
            if attempt >= settings.llm_max_retries:
                break

    # Fail safe: return a failed result (rules.md 6 and fail-safe matrix)
    latency_ms = int((time.time() - start) * 1000)
    logger.error("extraction failed after %d attempts, latency_ms=%d, error=%s", settings.llm_max_retries + 1, latency_ms, last_error)
    return ExtractionResult(
        item_type=ItemType.unknown,
        fields=[],
        description=None,
        schedule=[],
        model_id=MODEL_ID,
        prompt_version=PROMPT_VERSION,
        raw_output="",
        error=last_error or "Extraction failed after retry",
    )


def extraction_to_scan_result(extraction: ExtractionResult, scan_id: str, interaction: dict | None = None) -> ScanResult:
    """Convert an ExtractionResult into a ScanResult for the API response."""
    drug = ""
    for f in extraction.fields:
        if f.key == "name" and f.value:
            drug = f.value
            break

    status = ScanStatus.failed if extraction.error else ScanStatus.extracted

    return ScanResult(
        scanId=scan_id,
        itemType=extraction.item_type,
        status=status,
        drug=drug,
        fields=extraction.fields,
        schedule=extraction.schedule,
        description=extraction.description,
        interaction=interaction,
        modelId=extraction.model_id,
        error=extraction.error,
    )
