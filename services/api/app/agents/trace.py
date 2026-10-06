"""Audit trail for the agents (docs/specs/learning-loop.md section 11; rules.md: every agent run, tool call and guard decision is logged).

`Run` writes one `agent_runs` row and one `agent_steps` row per node, each in its own small transaction so a failed node still
leaves its record. `audit` appends to `event_log`, whose hash chain the database maintains; rows are never updated or deleted.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from typing import Any, Callable

from app.db.logstore import tx

logger = logging.getLogger(__name__)


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _small(obj: Any, limit: int = 4000) -> Any:
    """Keep what is stored in a step small and JSON-safe."""
    text = json.dumps(obj, default=str)
    return json.loads(text) if len(text) <= limit else {"truncated": True, "bytes": len(text)}


class Run:
    """One agent run. `lazy` runs keep their steps in memory and are written only if `finish(keep=True)`, so a routine check that
    changed nothing (the once-a-minute reminder tick) does not fill the audit trail."""

    def __init__(self, user_id: uuid.UUID | None, agent: str, trigger: str, lazy: bool = False):
        self.user_id, self.agent, self.trigger, self.seq, self.lazy = user_id, agent, trigger, 0, lazy
        self.t0 = time.perf_counter()
        self.buffer: list[tuple] = []
        if lazy:
            self.id = uuid.uuid4()
            return
        with tx() as c:
            self.id = c.execute(
                "insert into agent_runs (user_id, agent, trigger, status) values (%s,%s,%s,'running') returning id", (user_id, agent, trigger)
            ).fetchone()["id"]

    def step(self, node: str, tool: str | None, inp: Any, fn: Callable[[], Any]) -> Any:
        """Run one node, recording its input digest, a small output and its latency."""
        self.seq += 1
        t = time.perf_counter()
        try:
            out = fn()
        except Exception as e:
            self._write(node, tool, inp, {"error": str(e)[:300]}, t)
            raise
        self._write(node, tool, inp, out, t)
        return out

    _STEP_SQL = "insert into agent_steps (agent_run_id, seq, node, tool, input_digest, output, latency_ms) values (%s,%s,%s,%s,%s,%s::jsonb,%s)"

    def _write(self, node: str, tool: str | None, inp: Any, out: Any, t: float) -> None:
        row = (self.id, self.seq, node, tool, _digest(inp), json.dumps(_small(out)), int((time.perf_counter() - t) * 1000))
        if self.lazy:
            self.buffer.append(row)
            return
        try:
            with tx() as c:
                c.execute(self._STEP_SQL, row)
        except Exception:
            logger.exception("could not write an agent step")

    def finish(self, status: str = "ok", error: str | None = None, keep: bool = True, tokens: dict | None = None, model_id: str | None = None) -> None:
        ms = int((time.perf_counter() - self.t0) * 1000)
        if self.lazy and not keep:
            return
        tin, tout = (tokens or {}).get("input_tokens"), (tokens or {}).get("output_tokens")
        with tx() as c:
            if self.lazy:
                c.execute(
                    "insert into agent_runs (id, user_id, agent, trigger, status, error, latency_ms, input_tokens, output_tokens, model_id, finished_at) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())",
                    (self.id, self.user_id, self.agent, self.trigger, status, error, ms, tin, tout, model_id),
                )
                for row in self.buffer:
                    c.execute(self._STEP_SQL, row)
                return
            c.execute(
                "update agent_runs set status=%s, error=%s, latency_ms=%s, input_tokens=%s, output_tokens=%s, model_id=%s, finished_at=now() where id=%s",
                (status, error, ms, tin, tout, model_id, self.id),
            )


def audit(user_id: uuid.UUID | None, actor: str, event: str, entity_table: str | None = None, entity_id: Any = None,
          payload: dict | None = None, run_id: uuid.UUID | None = None) -> None:
    """Append one row to the hash-chained `event_log`. `actor` is user, agent or system."""
    try:
        with tx() as c:
            c.execute(
                "insert into event_log (user_id, actor, event, entity_table, entity_id, payload, agent_run_id) values (%s,%s::actor_type,%s,%s,%s,%s::jsonb,%s)",
                (user_id, actor, event, entity_table, entity_id, json.dumps(payload or {}, default=str), run_id),
            )
    except Exception:
        logger.exception("could not write the audit event %s", event)
