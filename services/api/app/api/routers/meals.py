"""POST /meals/analyze: a meal photo (and an optional description) to estimated nutrients, via Gemini on Vertex AI.

The photo's checksum, the description and the model's raw answer are stored as received in `bronze_food`; the
`analysisId` returned here is passed back when the meal is saved, so the Silver row points at its Bronze row.
"""
from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.agents.meal import analyse_meal, flags_for
from app.core.config import settings
from app.agents.trace import Run
from app.db import logstore
from app.services import usage
from app.llm.gateway import LLMUnavailable
from app.schemas.log import FoodNote, Macros, MealAnalysis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meals", tags=["meals"])

MAX_BYTES = 8 * 1024 * 1024
ALLOWED = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


@router.post("/analyze", response_model=MealAnalysis, response_model_by_alias=True)
async def analyze(file: UploadFile = File(...), description: str | None = Form(None)) -> MealAnalysis:
    mime = (file.content_type or "").lower()
    if mime not in ALLOWED:
        raise HTTPException(status_code=415, detail="Please use a JPEG, PNG or WebP photo.")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="The photo is empty.")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="The photo is too large. Please use one under 8 MB.")
    # one agent run per photo read, with its tokens and model, so the audit trail shows what the vision model cost
    acc: dict = {}
    token = usage.RUN_TOKENS.set(acc)
    run = await run_in_threadpool(Run, logstore.current_user(), "meal_vision", "log")
    try:
        est = await run_in_threadpool(analyse_meal, data, mime, description)
        await run_in_threadpool(run.finish, "ok", None, True, acc, settings.llm_vision_model)
    except LLMUnavailable as e:
        logger.warning("meal analysis unavailable: %s", e)
        await run_in_threadpool(run.finish, "error", str(e)[:200], True, acc, settings.llm_vision_model)
        raise HTTPException(status_code=503, detail="We could not read the photo just now. Please try again.")
    finally:
        usage.RUN_TOKENS.reset(token)
    if not est.is_food:
        raise HTTPException(status_code=422, detail="That does not look like a meal. Take a photo of your food or drink.")
    # The words the photo model wrote (the meal name and the portion note) are shown to the person, and the description box can influence
    # them, so they pass the same frozen guard as every other text. If either is blocked, plain wording is used instead.
    from app.db.nutritionstore import guarded

    shown = f"{est.meal_name}. {est.portion_note}".strip(". ")
    if shown and not await run_in_threadpool(guarded, logstore.current_user(), shown, "meal_words"):
        est.meal_name, est.portion_note = "Your meal", ""
    # The numbers saved for this meal are the photo model's (or the person's). The food database plays no part in logging a meal;
    # it is only used later, by the memory loop, to suggest lighter dishes for the next meal.
    bronze_id = await run_in_threadpool(
        logstore.save_meal_analysis,
        {"photo_sha256": hashlib.sha256(data).hexdigest(), "photo_bytes": len(data), "mime": mime, "description": (description or "").strip() or None,
         "model": settings.llm_vision_model, "model_answer": est.model_dump(mode="json")},
    )
    return MealAnalysis(
        analysis_id=bronze_id, name=est.meal_name or "Your meal", items=[i.name for i in est.items],
        macros=Macros(kcal=est.kcal, carbs_g=est.carbs_g, protein_g=est.protein_g, fat_g=est.fat_g, fibre_g=est.fibre_g, sugar_g=est.sugar_g, sodium_mg=est.sodium_mg),
        confidence="high" if est.confidence >= 0.85 else "check", flags=flags_for(est.carbs_g, est.sugar_g, est.sodium_mg),
        portion_note=est.portion_note, model_id=settings.llm_vision_model,
    )


@router.get("/response", response_model=FoodNote, response_model_by_alias=True)
async def response(food: str) -> dict:
    return await run_in_threadpool(logstore.food_response, food)
