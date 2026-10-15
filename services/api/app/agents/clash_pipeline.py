"""Runs one clash check for one person (prd F5, docs/specs/f5-clash.md): the database rules, then the AI model, then saves the alerts.

Called in the background right after a medicine is saved (typed in or scanned), and by `POST /interactions/check` and the replay script.
One check at a time per person, so two quick adds cost two checks in order, never two at once. The database half always runs and is saved
even when the AI half fails or the daily AI limit is reached; the AI half can only add flags. This is the only place the clash check
touches the model client, so tests can replace `_ai`.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Iterable

from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb

from app.agents import clash_checker as ai
from app.core.settings import get_settings
from app.db import logstore
from app.llm.vertex import VertexClient
from app.services import clash_store as store
from app.services import usage

logger = logging.getLogger(__name__)
_locks: dict[str, threading.Lock] = {}
_guard = threading.Lock()
_running: dict[str, int] = {}
_last_failed: dict[str, bool] = {}
_client: dict[str, Any] = {}


def _lock_for(user_id: str) -> threading.Lock:
    with _guard:
        return _locks.setdefault(user_id, threading.Lock())


def is_checking(user_id: str) -> bool:
    return _running.get(user_id, 0) > 0


def last_check_failed(user_id: str) -> bool:
    """True when the AI half of the latest check could not finish (the database half still ran)."""
    return _last_failed.get(user_id, False)


def _ai(meds: list[ai.Medicine]) -> ai.ClashOutcome:
    try:
        if not _client:
            s = get_settings()
            _client["c"] = VertexClient(s.google_api_key.get_secret_value(), s.google_cloud_project, s.google_cloud_region)
            _client["model"] = s.llm_vision_model
    except Exception as e:   # noqa: BLE001 - a missing key must not stop the database half
        logger.warning("clash check AI not available: %s", type(e).__name__)
        return ai.ClashOutcome(status="failed", reason="service_unavailable")
    return ai.check(_client["c"], model=_client["model"], meds=meds)


def check_user(user_id: str, only_ids: Iterable[str] | None = None) -> dict[str, Any]:
    """Check the person's saved medicines (or just `only_ids`, to replay the order they were added). Never raises."""
    with _lock_for(user_id):
        with _guard:
            _running[user_id] = _running.get(user_id, 0) + 1
        try:
            return _check(user_id, only_ids)
        except Exception:   # noqa: BLE001 - a background check must never take the app down
            logger.exception("clash check failed")
            return {"medicines": 0, "database": 0, "ai": 0, "ai_status": "failed", "reason": "error", "new": 0, "updated": 0}
        finally:
            with _guard:
                _running[user_id] = max(0, _running.get(user_id, 1) - 1)


def _check(user_id: str, only_ids: Iterable[str] | None) -> dict[str, Any]:
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        meds = store.list_medicines(conn, user_id, only_ids)
        db_pairs = store.database_pairs(conn, meds) if len(meds) >= 2 else []
    outcome = ai.ClashOutcome(status="done")
    if len(meds) >= 2:
        if usage.allowed("vertex_generate"):
            outcome = _ai([ai.Medicine(m["id"], m["name"], m["strength"], m["kind"]) for m in meds])
            usage.record("vertex_generate", outcome.input_tokens, outcome.output_tokens)
        else:
            outcome = ai.ClashOutcome(status="failed", reason="daily_limit")
    _last_failed[user_id] = outcome.status == "failed"
    ai_pairs = [(p.a, p.b, p.summary) for p in outcome.pairs]
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        counts = store.save_alerts(conn, user_id, db_pairs, ai_pairs, [{"title": s.title, "url": s.url} for s in outcome.sources], outcome.model_id or None)
        conn.execute("insert into event_log (user_id, actor, event, entity_table, payload) values (%s, 'agent', 'interaction.checked', 'interaction_alerts', %s)",
                     (user_id, Jsonb({"medicines": len(meds), "database": len(db_pairs), "ai": len(ai_pairs), "ai_status": outcome.status,
                                            "reason": outcome.reason, "input_tokens": outcome.input_tokens, "output_tokens": outcome.output_tokens})))
    logger.info("clash check medicines=%d database=%d ai=%d ai_status=%s", len(meds), len(db_pairs), len(ai_pairs), outcome.status)
    return {"medicines": len(meds), "database": len(db_pairs), "ai": len(ai_pairs), "ai_status": outcome.status, "reason": outcome.reason, **counts}
