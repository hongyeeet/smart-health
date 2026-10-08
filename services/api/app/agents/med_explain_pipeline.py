"""Wires the medicine explainer for the API: the model client is created once per process and reused.

This is the only place the explain route touches the model, so the route stays thin and tests can replace `run` with a fake.
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents.med_explainer import ExplainOutcome, explain
from app.core.settings import get_settings
from app.llm.vertex import VertexClient

logger = logging.getLogger(__name__)
_state: dict[str, Any] = {}


def _components() -> dict[str, Any]:
    if not _state:
        s = get_settings()
        _state["client"] = VertexClient(s.google_api_key.get_secret_value(), s.google_cloud_project, s.google_cloud_region)
        _state["model"] = s.llm_vision_model
    return _state


def run(*, name: str, strength: str | None, kind: str, directions: str | None, known_names: list[str]) -> ExplainOutcome:
    """Explain one medicine. Never raises: a missing key or a failed search comes back as a `failed` outcome."""
    try:
        c = _components()
    except Exception as e:   # noqa: BLE001 - a missing key must not take the medicine page down
        logger.warning("explainer not available: %s", type(e).__name__)
        return ExplainOutcome(status="failed", reason="service_unavailable")
    return explain(c["client"], model=c["model"], name=name, strength=strength, kind=kind, directions=directions, known_names=known_names)
