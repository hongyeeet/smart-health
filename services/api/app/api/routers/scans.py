"""POST /scans, GET /scans/{id}, POST /scans/{id}/confirm (architecture.md 4.1, 7).

The flow:
  1. POST /scans (image) → store image, run extractor agent, return ScanResult
  2. GET /scans/{id} → re-fetch the scan for the review screen
  3. POST /scans/{id}/confirm → user confirms/edits fields → save medication (E3-2)

For now, the scan is stored in memory (a dict) because the full DB model layer is part of E0-2.
When E0-2 lands, replace _scan_store with real prescription_scans table queries.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.agents.extractor import extract_label, extraction_to_scan_result
from app.schemas.scan import ScanConfirmRequest, ScanResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scans", tags=["scans"])

# In-memory store until E0-2 wires the DB session and the prescription_scans model.
_scan_store: dict[str, ScanResult] = {}


@router.post("", response_model=ScanResult)
async def upload_scan(file: UploadFile = File(...)) -> ScanResult:
    """Upload a label photo and run the vision extractor.

    Returns the ScanResult with extracted fields and confidence per field.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image")

    scan_id = str(uuid.uuid4())

    # Run the extractor agent (vision → strict JSON → validate → fail safe)
    extraction = extract_label(image_bytes, file.content_type)

    # Build the ScanResult
    result = extraction_to_scan_result(extraction, scan_id)

    # Store for re-fetch in GET /scans/{id}
    _scan_store[scan_id] = result

    logger.info("scan uploaded scan_id=%s status=%s fields=%d", scan_id, result.status, len(result.fields))
    return result


@router.get("/{scan_id}", response_model=ScanResult)
async def get_scan(scan_id: str) -> ScanResult:
    """Re-fetch a scan by id (for the review screen or polling)."""
    result = _scan_store.get(scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return result


@router.post("/{scan_id}/confirm", response_model=ScanResult)
async def confirm_scan(scan_id: str, body: ScanConfirmRequest) -> ScanResult:
    """User confirms the reviewed/edited fields.

    In E3-2, this endpoint will:
      - match the medicine name to drug_reference
      - parse the directions into dose schedule
      - save patient_medications + dose_events + clash check in one transaction
    For now (E3-1), it just applies the user's edits to the stored scan.
    """
    result = _scan_store.get(scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Apply user edits to the fields
    if body.fields:
        updated_fields = []
        for f in result.fields:
            if f.key in body.fields:
                edited_value = body.fields[f.key]
                updated_fields.append(f.model_copy(update={"value": edited_value}))
            else:
                updated_fields.append(f)
        result = result.model_copy(update={"fields": updated_fields})

    _scan_store[scan_id] = result
    logger.info("scan confirmed scan_id=%s fields_edited=%s", scan_id, list(body.fields.keys()))
    return result
