"""API shapes for the medicine warehouse (docs/specs/implementation-plan-2026-10-11.md section 4.3). camelCase on the wire, like the other routers.

`status` is ok | low | out | unknown: a fact about the count, never advice (see app/services/medication_stock.py).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.medicines import Camel


class StockIn(BaseModel):
    """Exactly one of: `add` (bought more) or `set` (the exact number). Each is from 0 to 10000."""
    model_config = ConfigDict(populate_by_name=True)

    add: Decimal | None = Field(default=None, ge=0, le=10000)
    set_count: Decimal | None = Field(default=None, ge=0, le=10000, alias="set")

    @model_validator(mode="after")
    def _one_change(self) -> "StockIn":
        if (self.add is None) == (self.set_count is None):
            raise ValueError("send either add or set, not both")
        return self


class StockOut(Camel):
    id: str
    name: str
    strength: str
    stock_count: float | None                      # None: not set yet (never shown as 0)
    stock_unit: str | None
    days_left: int | None                          # whole days at the usual dose; None when unknown
    status: Literal["ok", "low", "out", "unknown"]
    updated_at: datetime | None
    full_count: float | None = None                # the last amount set or bought: the full mark of the bar
    pack_size: int | None = None                   # the pack size when it was entered: quick choices in "I bought more"


class StockListOut(Camel):
    ready: bool                                    # False while migration 0032 is not applied: the screen says it is being set up
    items: list[StockOut] = []
