"""Pydantic v2 schemas for scan request/response (rules.md 4: no raw dicts across layers).

These mirror the TypeScript types in apps/web/src/data/types.ts.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ScanStatus(str, Enum):
    uploaded = "uploaded"
    extracting = "extracting"
    extracted = "extracted"
    failed = "failed"


class ItemType(str, Enum):
    prescription_label = "prescription_label"
    blister_or_box = "blister_or_box"
    supplement = "supplement"
    tcm = "tcm"
    otc = "otc"
    unknown = "unknown"


class ScanConfidenceLevel(str, Enum):
    high = "high"
    check = "check"
    unreadable = "unreadable"


class ScanFieldSchema(BaseModel):
    """One extracted field with its confidence and the source text from the label."""

    key: str
    label: str
    value: str | None = Field(None, description="null means the model could not read this field")
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    source_text: str | None = Field(None, alias="sourceText")
    level: ScanConfidenceLevel = Field(
        ScanConfidenceLevel.unreadable, description="derived from confidence: >= 0.85 high, > 0 check, 0/null unreadable"
    )

    model_config = {"populate_by_name": True}


class ScanScheduleItem(BaseModel):
    time: str
    label: str


class ScanResult(BaseModel):
    """The full scan result returned by GET /scans/{id} and POST /scans."""

    scan_id: str = Field(alias="scanId")
    item_type: ItemType = Field(ItemType.unknown, alias="itemType")
    status: ScanStatus = ScanStatus.uploaded
    drug: str = ""
    fields: list[ScanFieldSchema] = Field(default_factory=list)
    schedule: list[ScanScheduleItem] = Field(default_factory=list)
    description: str | None = None
    interaction: dict | None = None
    model_id: str | None = None
    error: str | None = None
    # Added for the medicine scan (docs/specs/f2-scan.md). "manual" means the person types the form: the scan was unreadable, a field was
    # below the confidence threshold, a required field was missing or the drug is not in the drug list. `notice` says why, in plain words.
    as_needed: bool = Field(False, alias="asNeeded")     # the label says "when necessary": no dose times
    symptom_hint: bool = Field(False, alias="symptomHint")     # the label is for a symptom (fever, pain...): ask whether it is only taken when needed
    review_mode: Literal["confirm", "manual"] = Field("manual", alias="reviewMode")
    reasons: list[str] = Field(default_factory=list)
    notice: str | None = None

    model_config = {"populate_by_name": True, "from_attributes": True}


class ScanConfirmRequest(BaseModel):
    """User's confirmed/edited fields, sent to POST /scans/{id}/confirm."""

    fields: dict[str, str | None] = Field(default_factory=dict, description="field key -> edited value or null")
    times: list[str] | None = Field(None, description="dose clock times chosen on the plan screen, 24-hour HH:MM")
    kind: Literal["prescription", "otc", "supplement", "tcm"] | None = None
    # The person's own answer to "how do you take it?": true = only when needed (no times, no reminders, no refill estimate), false = every day.
    as_needed: bool | None = Field(None, alias="asNeeded")

    model_config = {"populate_by_name": True}
