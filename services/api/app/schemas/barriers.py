"""API shape for the "What gets in the way" KPI row on K2 (GET /memory/barriers/summary). camelCase on the wire; None means no data yet."""
from __future__ import annotations

from app.schemas.medicines import Camel


class TopReason(Camel):
    key: str
    label: str
    count: int
    missed: int


class BarrierSummary(Camel):
    window_days: int
    week_start: str
    scheduled_this_week: int
    missed_this_week: int | None = None
    confirmed_doses: int
    on_time_pct: int | None = None
    top_reason: TopReason | None = None
    confirmed_barriers: int
    waiting_barriers: int
