"""Read a medicine photo into scored fields (prd F2). Orchestration only: the masking, scoring and the decision live in
`app/services/` (pure code); the model call lives in `app/llm/`. Nothing here saves anything: saving happens only after
the user confirms (`app/services/scan_store.py`).

Order: validate and strip the photo, blank out identity (local OCR), ask the model for strict JSON, validate it (one
retry), scrub identity from the answer, score every field, decide "confirm" or "type it yourself".
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from app.core.errors import ExternalServiceError, ValidationFailed
from app.llm.vertex import GenerationResult, ImagePart, VertexClient
from app.schemas.medicine_scan import (
    FIELD_NAMES,
    RawExtraction,
    RawField,
    RawItem,
    ScanOutcome,
)
from app.services import scan_confidence as conf
from app.services import scan_privacy as privacy

log = logging.getLogger(__name__)
PROMPT_FILE = Path(__file__).parent / "prompts" / "scan_label.md"


# The model "thinks" before it answers and that counts against the limit: a dense label used 3,500 of the old 4,096 and the
# JSON was cut off. A truncated answer is useless, so leave room.
MAX_OUTPUT_TOKENS = 12288


def load_prompt() -> tuple[str, str]:
    """Return (version, text). The prompt lives in a file with a `version:` header (rules.md section 4)."""
    head, _, body = PROMPT_FILE.read_text(encoding="utf-8").partition("\n")
    return head.split(":", 1)[1].strip(), body.strip()


def _field_schema() -> dict[str, Any]:
    return {"type": "OBJECT", "properties": {
        "value": {"type": "STRING", "nullable": True}, "confidence": {"type": "NUMBER"}, "source_text": {"type": "STRING", "nullable": True}},
        "required": ["value", "confidence", "source_text"]}


def response_schema() -> dict[str, Any]:
    item_props: dict[str, Any] = {f: _field_schema() for f in FIELD_NAMES}
    item_props["item_type"] = {"type": "STRING", "enum": ["prescription_label", "blister_or_box", "supplement", "tcm", "otc", "unknown"]}
    item_props["ingredients"] = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
        "name": {"type": "STRING", "nullable": True}, "amount": {"type": "STRING", "nullable": True}}}}
    return {"type": "OBJECT", "properties": {
        "readable": {"type": "BOOLEAN"}, "is_medication_item": {"type": "BOOLEAN"}, "issue": {"type": "STRING", "nullable": True},
        "items": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": item_props, "required": ["item_type", *FIELD_NAMES]}}},
        "required": ["readable", "is_medication_item", "items"]}


def parse_answer(text: str) -> RawExtraction:
    return RawExtraction.model_validate(json.loads(text))


def scrub(raw: RawExtraction, known_names: Iterable[str]) -> tuple[RawExtraction, int]:
    """Drop any value that carries identity (NRIC, name label, phone, address, the user's own name). Returns (clean, removed count)."""
    removed = 0
    names = list(known_names)
    items: list[RawItem] = []
    for it in raw.items:
        data: dict[str, Any] = {"item_type": it.item_type, "ingredients": it.ingredients}
        for f in FIELD_NAMES:
            rf: RawField = getattr(it, f)
            clean, hit = privacy.scrub_value(rf.value, names)
            src, hit2 = privacy.scrub_value(rf.source_text, names)
            if hit or hit2:
                removed += 1
                data[f] = RawField(value=None, confidence=0.0, source_text=None)
            else:
                data[f] = RawField(value=clean, confidence=rf.confidence, source_text=src)
        items.append(RawItem(**data))
    return RawExtraction(is_medication_item=raw.is_medication_item, readable=raw.readable, issue=raw.issue, items=items), removed


def extract_scan(
    image_bytes: bytes,
    *,
    client: VertexClient,
    model: str,
    ocr: Any = None,
    known_names: Iterable[str] = (),
    threshold: float = conf.THRESHOLD,
) -> tuple[ScanOutcome, privacy.MaskResult | None]:
    """Run the whole read. Returns the outcome and the masked photo (the only copy that may be stored). Never raises for a
    bad photo or a model failure: those become a `failed` outcome that offers manual entry (rules.md fail-safe matrix)."""
    version, system = load_prompt()
    names = list(known_names)
    try:
        masked = privacy.mask_photo(image_bytes, ocr=ocr, known_names=names)
    except ValidationFailed as e:
        return ScanOutcome(status="failed", review_mode="manual", reasons=[e.code], prompt_version=version), None

    summary = dict(masked.masked)
    raw: RawExtraction | None = None
    result: GenerationResult | None = None
    in_tokens = out_tokens = latency = 0
    for attempt in range(2):          # invalid JSON is retried once, then it fails safe
        try:
            result = client.generate_json(model=model, system=system, parts=[ImagePart(masked.image, masked.mime_type),
                                          "Read this item and return the JSON."], response_schema=response_schema(),
                                          max_output_tokens=MAX_OUTPUT_TOKENS)
        except ExternalServiceError as e:
            log.warning("scan model call failed: %s", e.code)
            return ScanOutcome(status="failed", review_mode="manual", reasons=["service_unavailable"], prompt_version=version,
                               model_id=model, mask_summary=summary), masked
        in_tokens += result.input_tokens or 0
        out_tokens += result.output_tokens or 0
        latency += result.latency_ms
        try:
            raw = parse_answer(result.text)
            break
        except (json.JSONDecodeError, ValidationError, TypeError) as e:
            # Log what kind of failure and where, never the content (rules.md section 3).
            where = [".".join(str(x) for x in err["loc"]) for err in e.errors()][:5] if isinstance(e, ValidationError) else ""
            log.warning("scan answer was not valid (attempt %d): %s %s", attempt + 1, type(e).__name__, where)
    if raw is None:
        return ScanOutcome(status="failed", review_mode="manual", reasons=["invalid_json"], prompt_version=version, model_id=model,
                           input_tokens=in_tokens, output_tokens=out_tokens, latency_ms=latency, mask_summary=summary), masked

    raw, removed = scrub(raw, names)
    if removed:
        summary["removed_from_answer"] = removed
    items = [conf.score_item(it, masked.ocr_text, threshold) for it in raw.items]
    d = conf.decide(raw, items, threshold)
    return ScanOutcome(status=d.status, review_mode=d.review_mode, reasons=d.reasons, items=items if d.status == "needs_review" else [],  # type: ignore[arg-type]
                       prompt_version=version, model_id=model, input_tokens=in_tokens, output_tokens=out_tokens, latency_ms=latency,
                       mask_summary=summary), masked
