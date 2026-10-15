"""API shapes for the K10 Diet tracking calendar (GET /memory/progress/days). camelCase on the wire; None means unknown, shown as a dash."""
from __future__ import annotations

from typing import Literal

from app.schemas.medicines import Camel


class DietTotals(Camel):
    kcal: int | None = None
    carbs_g: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    sugar_g: float | None = None
    fibre_g: float | None = None
    sodium_mg: float | None = None


class DietMeal(Camel):
    id: str
    when: str
    name: str | None = None
    meal_type: str | None = None
    kcal: int | None = None
    # "you" when the person typed or changed the numbers (shown as "Your numbers"), "estimate" when the photo reading gave them
    numbers_from: Literal["you", "estimate"] = "estimate"
    carbs_g: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    sugar_g: float | None = None
    fibre_g: float | None = None
    sodium_mg: float | None = None


class DietDay(Camel):
    date: str
    meals: int
    totals: DietTotals
    meal_list: list[DietMeal]


class DietDays(Camel):
    start: str
    end: str
    today: str
    days: list[DietDay]
