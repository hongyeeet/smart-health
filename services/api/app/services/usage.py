"""AI usage accounting and the daily cap (docs/specs/learning-loop.md 12.5).

Every model call is counted per day and provider in `ai_usage_daily` (calls, tokens and, where the provider reports it, cost). The
daily caps come from the settings. When a cap is reached the call is refused and the caller takes its conservative path: the photo is
not read (the person is told), JEV is treated as unavailable (guards block, no substitute is offered), embeddings fall back to text
search. A refused call is counted as `blocked`. The tokens a run used are also added to the current agent run, if there is one.
"""
from __future__ import annotations

import logging
from contextvars import ContextVar
from datetime import datetime
from typing import Any

from app.core.config import settings
from app.db.logstore import TZ, tx

logger = logging.getLogger(__name__)
RUN_TOKENS: ContextVar[dict[str, Any] | None] = ContextVar("run_tokens", default=None)


def _day():
    return datetime.now(TZ).date()


def record(provider: str, input_tokens: int = 0, output_tokens: int = 0, cost_usd: float | None = None, blocked: bool = False) -> None:
    acc = RUN_TOKENS.get()
    if acc is not None and not blocked:
        acc["input_tokens"] = acc.get("input_tokens", 0) + (input_tokens or 0)
        acc["output_tokens"] = acc.get("output_tokens", 0) + (output_tokens or 0)
        acc["calls"] = acc.get("calls", 0) + 1
    try:
        with tx() as c:
            c.execute(
                """insert into ai_usage_daily (day, provider, calls, blocked, input_tokens, output_tokens, cost_usd) values (%s,%s,%s,%s,%s,%s,%s)
                   on conflict (day, provider) do update set calls = ai_usage_daily.calls + excluded.calls, blocked = ai_usage_daily.blocked + excluded.blocked,
                     input_tokens = ai_usage_daily.input_tokens + excluded.input_tokens, output_tokens = ai_usage_daily.output_tokens + excluded.output_tokens,
                     cost_usd = case when excluded.cost_usd is null then ai_usage_daily.cost_usd else coalesce(ai_usage_daily.cost_usd, 0) + excluded.cost_usd end,
                     updated_at = now()""",
                (_day(), provider, 0 if blocked else 1, 1 if blocked else 0, input_tokens or 0, output_tokens or 0, cost_usd),
            )
    except Exception:
        logger.exception("could not record AI usage")


def today() -> dict[str, Any]:
    with tx() as c:
        rows = c.execute("select provider, calls, blocked, input_tokens, output_tokens, cost_usd from ai_usage_daily where day=%s", (_day(),)).fetchall()
    calls = sum(r["calls"] for r in rows)
    cost = sum(float(r["cost_usd"] or 0) for r in rows)
    return {
        "day": _day().isoformat(), "calls": calls, "callCap": settings.ai_daily_call_cap, "costUsd": round(cost, 4), "budgetUsd": settings.ai_daily_budget_usd,
        "blocked": sum(r["blocked"] for r in rows), "overCap": over_cap(calls, cost),
        "providers": [{"provider": r["provider"], "calls": r["calls"], "inputTokens": int(r["input_tokens"]), "outputTokens": int(r["output_tokens"]),
                       "costUsd": float(r["cost_usd"]) if r["cost_usd"] is not None else None} for r in rows],
        "note": "Cost is only counted where the provider reports it (JEV). Gemini cost is not priced yet, so the budget cap currently rests on the call cap.",
    }


def over_cap(calls: int, cost: float) -> bool:
    return calls >= settings.ai_daily_call_cap or cost >= settings.ai_daily_budget_usd


def allowed(provider: str) -> bool:
    """False once today's calls or cost reach the cap (the refusal is counted)."""
    try:
        t = today()
    except Exception:
        return True  # if the counter itself is unreachable, do not stop the app; the call is not counted either
    if t["overCap"]:
        record(provider, blocked=True)
        return False
    return True
