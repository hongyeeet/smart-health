"""API shape of the reviewer screen (K11). camelCase on the wire, like the other routers.

The queue is computed from the person's own logged dishes (or the shared sample set); a rating is the only thing written.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.medicines import Camel

Verdict = Literal["reasonable", "not_reasonable", "unsafe"]


class Usual(Camel):
    name: str
    times_logged: int | None                 # None for the sample set (its numbers are the published serving, not logged)
    kcal: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    sugar_g: float | None
    sodium_mg: float | None


class Suggested(Camel):
    name: str
    serving: str | None
    kcal: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    sugar_g: float | None
    sodium_mg: float | None


class MyRating(Camel):
    verdict: Verdict
    comment: str | None


class QueueItem(Camel):
    suggestion_key: str
    usual: Usual
    suggested: Suggested
    change: str                              # the saving in words, from the compared numbers
    my_rating: MyRating | None


class Queue(Camel):
    source: Literal["mine", "sample"]
    items: list[QueueItem]
    total: int
    rated: int
    message: str | None                      # plain reason when the queue is empty or short
    sample_offered: bool                     # true when "mine" is empty and the sample set is offered


class RatingIn(Camel):
    suggestion_key: str = Field(min_length=8, max_length=64)
    verdict: Verdict
    comment: str | None = Field(None, max_length=300)


class RatingOut(Camel):
    suggestion_key: str
    verdict: Verdict
    comment: str | None
    rated: int


class Counts(Camel):
    reasonable: int
    not_reasonable: int
    unsafe: int


class Score(Camel):
    counts: Counts
    rated: int
    reasonable_share: float | None           # None until anything is rated
    target: float
    min_ratings: int
    unsafe: int
    status: Literal["met", "not_met", "too_few"]
