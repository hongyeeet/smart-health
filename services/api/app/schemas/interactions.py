"""API shapes for the medicine clash box (Meds page, prd F5). camelCase on the wire, like the other routers."""
from __future__ import annotations

from typing import Literal

from app.schemas.medicines import Camel, WebSourceOut


class ClashAlertOut(Camel):
    id: str
    med_a: str                       # "Atorvastatin 20 mg"
    med_b: str
    text: str                        # always "Possible interaction between X and Y. Please check with your pharmacist or doctor before continuing."
    summary: str                     # why they may clash, in plain words (never dose or treatment advice)
    origin: Literal["database", "ai", "both"]
    sources: list[WebSourceOut] = []
    question_added: bool = False     # the doctor question for this pair is already saved


class ClashStatus(Camel):
    checking: bool                   # a check is running right now, so more alerts may appear in a few seconds
    check_incomplete: bool           # the AI half of the latest check could not finish; the database half still ran
    alerts: list[ClashAlertOut]
