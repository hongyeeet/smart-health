"""Meal photo to estimated nutrients (E7-2). The photo and the optional description go to Gemini on Vertex AI.

Rules (rules.md): everything returned is an estimate until the user confirms it; a value the model cannot judge is
null, never 0; the flags are computed here in code from the numbers, not by the model.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.llm.gateway import vision_json

PROMPT = """You are the food-reading step of a diabetes self-management app for adults in Singapore.
Look at the photo of a meal. The person may add a description (what it is, how much they ate, what was left out); use it
to correct what you see, for example "half portion", "no gravy", "teh kosong".

Return JSON for the food ACTUALLY EATEN, as one total for the whole meal:
- is_food: false if the photo shows no food or drink at all (then leave the rest empty).
- meal_name: a short plain name, for example "Chicken rice".
- items: each separate food or drink you can identify, with an estimated weight in grams.
- kcal, carbs_g, protein_g, fat_g, sugar_g (part of carbs), fibre_g (part of carbs), sodium_mg: estimates for the whole meal.
  Use local Singapore portion sizes and recipes. If you truly cannot judge a number, use null. Never write 0 for unknown.
- confidence: 0 to 1 for how sure you are about the portion size and the dish.
- portion_note: one short sentence on what portion you assumed.
Do not give medical advice."""


class MealItem(BaseModel):
    name: str
    grams: float | None = Field(None, ge=0)


class MealEstimate(BaseModel):
    is_food: bool
    meal_name: str = ""
    items: list[MealItem] = Field(default_factory=list)
    kcal: float | None = Field(None, ge=0)
    carbs_g: float | None = Field(None, ge=0)
    protein_g: float | None = Field(None, ge=0)
    fat_g: float | None = Field(None, ge=0)
    sugar_g: float | None = Field(None, ge=0)
    fibre_g: float | None = Field(None, ge=0)
    sodium_mg: float | None = Field(None, ge=0)
    confidence: float = Field(0.0, ge=0, le=1)
    portion_note: str = ""

    @field_validator("meal_name", "portion_note")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


def analyse_meal(image: bytes, mime_type: str, description: str | None, model: str | None = None) -> MealEstimate:
    """Raises LLMUnavailable (with a code) when the photo cannot be read. `model` is for tests and trials; the default is the setting."""
    prompt = PROMPT
    if description and description.strip():
        prompt += f"\n\nThe person's description: {description.strip()[:500]}"
    est = vision_json(image, mime_type, prompt, MealEstimate, model=model)
    # Keep the database constraints true even if the model rounds oddly: sugar and fibre are parts of carbs.
    if est.carbs_g is not None:
        if est.sugar_g is not None:
            est.sugar_g = min(est.sugar_g, est.carbs_g)
        if est.fibre_g is not None:
            est.fibre_g = min(est.fibre_g, est.carbs_g)
    return est


def flags_for(carbs_g: float | None, sugar_g: float | None, sodium_mg: float | None) -> list[str]:
    out: list[str] = []
    if sodium_mg is not None and sodium_mg >= settings.meal_high_sodium_mg:
        out.append("high_salt")
    if sugar_g is not None and sugar_g >= settings.meal_high_sugar_g:
        out.append("high_sugar")
    return out
