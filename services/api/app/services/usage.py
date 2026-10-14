"""AI usage accounting and the daily caps (docs/specs/learning-loop.md 12.5).

Every model call is counted per day and provider in `ai_usage_daily` (calls, tokens and, where the provider reports it, cost).

Each kind of AI call has its own daily cap, so one kind being used up never blocks another:
  vertex_vision    photo and label reads (meal photos)                  AI_CAP_VERTEX_VISION   default 300
  vertex_generate  text the person sees (brief findings, medicine explainer, clash checker, chat, onboarding answers)
                                                                        AI_CAP_VERTEX_GENERATE default 500
  vertex_embed     background embeddings for food search                AI_CAP_VERTEX_EMBED    default 2000
  jev              typed decisions (guards and checks)                  AI_CAP_JEV             default 500
A provider with no cap of its own uses AI_DAILY_CALL_CAP (default 500). AI_DAILY_BUDGET_USD applies to each provider's own cost
(only JEV reports cost today).

When a cap is reached the call is refused and the caller takes its conservative path: the photo is not read (the person is told),
JEV is treated as unavailable (guards block, no substitute is offered), embeddings fall back to text search, and the model-written
text is not shown. A refused call is counted as `blocked` against that provider only. The tokens a run used are also added to the
current agent run, if there is one.
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

# The kinds of AI call, in the order they are reported. Each has its own cap setting.
PROVIDERS = ("vertex_vision", "vertex_generate", "vertex_embed", "vertex_image", "jev")
_CAP_SETTING = {
    "vertex_vision": "ai_cap_vertex_vision",
    "vertex_generate": "ai_cap_vertex_generate",
    "vertex_embed": "ai_cap_vertex_embed",
    "vertex_image": "ai_cap_vertex_image",
    "jev": "ai_cap_jev",
}


def _day():
    return datetime.now(TZ).date()


def cap_for(provider: str) -> int:
    """The daily call cap for one provider: its own setting, or AI_DAILY_CALL_CAP for any provider without one."""
    name = _CAP_SETTING.get(provider)
    return int(getattr(settings, name)) if name else settings.ai_daily_call_cap


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
    """Today's use by provider. The top-level fields are totals across providers; each provider has its own cap and overCap."""
    with tx() as c:
        rows = {r["provider"]: r for r in c.execute("select provider, calls, blocked, input_tokens, output_tokens, cost_usd from ai_usage_daily where day=%s", (_day(),)).fetchall()}
    providers = []
    for p in list(PROVIDERS) + sorted(k for k in rows if k not in PROVIDERS):
        r = rows.get(p) or {"calls": 0, "blocked": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": None}
        calls = int(r["calls"])
        cost = float(r["cost_usd"] or 0)
        providers.append({
            "provider": p, "calls": calls, "blocked": int(r["blocked"]), "cap": cap_for(p), "overCap": over_cap(calls, cost, cap_for(p)),
            "inputTokens": int(r["input_tokens"]), "outputTokens": int(r["output_tokens"]),
            "costUsd": float(r["cost_usd"]) if r["cost_usd"] is not None else None,
        })
    calls = sum(p["calls"] for p in providers)
    cost = sum(float(rows[p]["cost_usd"] or 0) for p in rows)
    return {
        "day": _day().isoformat(), "calls": calls,
        # callCap is the sum of the caps of the known kinds (kept for the existing screen line "X of N calls")
        "callCap": sum(p["cap"] for p in providers if p["provider"] in PROVIDERS), "costUsd": round(cost, 4), "budgetUsd": settings.ai_daily_budget_usd,
        "blocked": sum(p["blocked"] for p in providers), "overCap": any(p["overCap"] for p in providers),
        "caps": {p["provider"]: p["cap"] for p in providers if p["provider"] in PROVIDERS},
        "providers": providers,
        "note": "Each kind of AI call has its own daily cap. Cost is only counted where the provider reports it (JEV). Gemini cost is not priced yet, so the Gemini caps are call caps only.",
    }


def over_cap(calls: int, cost: float, cap: int | None = None) -> bool:
    """True when calls or cost have reached the cap. Without `cap`, the shared AI_DAILY_CALL_CAP is used."""
    limit = settings.ai_daily_call_cap if cap is None else cap
    return calls >= limit or cost >= settings.ai_daily_budget_usd


def _provider_today(provider: str) -> tuple[int, float]:
    with tx() as c:
        r = c.execute("select calls, cost_usd from ai_usage_daily where day=%s and provider=%s", (_day(), provider)).fetchone()
    return (int(r["calls"]), float(r["cost_usd"] or 0)) if r else (0, 0.0)


def allowed(provider: str) -> bool:
    """False once this provider's own calls or cost today reach its cap (the refusal is counted against that provider only)."""
    try:
        calls, cost = _provider_today(provider)
    except Exception:
        return True  # if the counter itself is unreachable, do not stop the app; the call is not counted either
    if over_cap(calls, cost, cap_for(provider)):
        record(provider, blocked=True)
        return False
    return True
