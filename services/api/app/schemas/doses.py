"""API shapes for today's doses (Home B1) and the missed-dose answer (sheet H7). camelCase on the wire, like the other routers."""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.medicines import Camel

Reason = Literal["took_it", "forgot", "side_effects", "ran_out", "felt_fine", "cost", "away_from_home", "other"]


class DoseOut(Camel):
    id: str
    title: str                      # "Metformin, 1 Tab": what to take, not how strong it is
    time: str                       # "8:00 pm"
    with_food: bool
    when_label: str                 # "Yesterday's evening dose"


class NextDoseOut(Camel):
    title: str
    when: str                       # "tomorrow at 8:00 am"


class DosesToday(Camel):
    has_medicines: bool
    due: list[DoseOut]
    unconfirmed: list[DoseOut]
    taken_today: int
    next: NextDoseOut | None = None


class ReasonIn(Camel):
    reason: Reason
    note: str | None = Field(default=None, max_length=500)


class DoseResult(Camel):
    status: Literal["taken", "missed", "pending"]
