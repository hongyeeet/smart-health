"""Wires the scan together for the API: the model client, the offline OCR and the drug list are created once per process and reused.

This is the only place the scan route touches the model gateway, so the route stays thin and tests can replace `run` with a fake.
"""
from __future__ import annotations

import logging
from typing import Any

import psycopg

from app.agents.scan_extractor import extract_scan
from app.core.settings import get_settings
from app.llm.vertex import VertexClient
from app.schemas.medicine_scan import ScanOutcome
from app.services.scan_privacy import MaskResult, default_ocr
from app.services.scan_store import load_drug_index

logger = logging.getLogger(__name__)
_state: dict[str, Any] = {}


def _components(conn: psycopg.Connection) -> dict[str, Any]:
    if not _state:
        s = get_settings()
        _state["client"] = VertexClient(s.google_api_key.get_secret_value(), s.google_cloud_project, s.google_cloud_region)
        _state["ocr"] = default_ocr()          # slow to load: once
        _state["index"] = load_drug_index(conn)
        _state["model"] = s.llm_vision_model
        _state["threshold"] = s.scan_confidence_threshold
    return _state


def run(image: bytes, conn: psycopg.Connection, user_id: str) -> tuple[ScanOutcome, MaskResult | None]:
    """Read one photo. Never raises for a bad photo or a model failure: those come back as a `failed` outcome that offers manual entry."""
    try:
        c = _components(conn)
    except Exception as e:   # noqa: BLE001 - a missing key or model setting must not take the Meds page down
        logger.warning("scan not available: %s", type(e).__name__)
        return ScanOutcome(status="failed", review_mode="manual", reasons=["service_unavailable"]), None
    names = [r[0] for r in conn.execute("select display_name from user_profile where user_id = %s", (user_id,)).fetchall() if r[0]]
    return extract_scan(image, client=c["client"], model=c["model"], index=c["index"], ocr=c["ocr"], known_names=names,
                        threshold=c["threshold"])
