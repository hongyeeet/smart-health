"""POST /meals/analyze: a meal photo (and an optional description) to estimated nutrients, via Gemini on Vertex AI.

The photo's checksum, the description and the model's raw answer are stored as received in `bronze_food`; the
`analysisId` returned here is passed back when the meal is saved, so the Silver row points at its Bronze row.

Every failure returns JSON: `detail` is a plain sentence for the person, `code` is a stable name for the screen
(bad_photo, not_food, model_unavailable, daily_limit, timeout, bad_response, save_failed). The screen then offers manual entry.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

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
# The whole read gives up after this many seconds (the model call itself has llm_timeout_s), so the screen is never left waiting.
ANALYSIS_LIMIT_S = settings.llm_timeout_s + 5

MESSAGES = {
    "bad_photo": "Please use a JPEG, PNG or WebP photo under 8 MB.",
    "not_food": "That does not look like a meal. Take a photo of your food or drink, or type the meal in.",
    "model_unavailable": "We could not read the photo just now. Please try again, or type the meal in.",
    "daily_limit": "The daily limit for reading photos has been reached. Please type the meal in for now, or try again tomorrow.",
    "timeout": "Reading the photo took too long. Please try again, or type the meal in.",
    "bad_response": "We could not make sense of the reading for this photo. Please try again, or type the meal in.",
    "save_failed": "We could not save the reading just now. Please try again.",
}
STATUS = {"bad_photo": 400, "not_food": 422, "save_failed": 503}  # every other code is 503 (service unavailable)


def _error(code: str, detail: str | None = None, status: int | None = None) -> JSONResponse:
    return JSONResponse(status_code=status or STATUS.get(code, 503), content={"detail": detail or MESSAGES[code], "code": code})


@router.post("/analyze", response_model=MealAnalysis, response_model_by_alias=True)
async def analyze(file: UploadFile = File(...), description: str | None = Form(None)) -> MealAnalysis | JSONResponse:
    mime = (file.content_type or "").lower()
    if mime not in ALLOWED:
        return _error("bad_photo", "Please use a JPEG, PNG or WebP photo.", 415)
    data = await file.read()
    if not data:
        return _error("bad_photo", "The photo is empty.")
    if len(data) > MAX_BYTES:
        return _error("bad_photo", "The photo is too large. Please use one under 8 MB.", 413)
    # one agent run per photo read, with its tokens and model, so the audit trail shows what the vision model cost
    acc: dict = {}
    token = usage.RUN_TOKENS.set(acc)
    try:
        try:
            run = await run_in_threadpool(Run, logstore.current_user(), "meal_vision", "log")
        except Exception:
            logger.error("meal analysis could not open its run record")
            return _error("model_unavailable")
        try:
            est = await asyncio.wait_for(run_in_threadpool(analyse_meal, data, mime, description), timeout=ANALYSIS_LIMIT_S)
        except asyncio.TimeoutError:
            logger.error("meal analysis passed the %s s limit", ANALYSIS_LIMIT_S)
            await run_in_threadpool(run.finish, "error", "timeout", True, acc, settings.llm_vision_model)
            return _error("timeout")
        except LLMUnavailable as e:
            logger.warning("meal analysis unavailable: %s", e.code)
            await run_in_threadpool(run.finish, "error", e.code, True, acc, settings.llm_vision_model)
            return _error(e.code)
        except Exception as e:  # anything unexpected still ends as a plain message, and the run record is closed
            logger.error("meal analysis failed: %s", type(e).__name__)
            await run_in_threadpool(run.finish, "error", "model_unavailable", True, acc, settings.llm_vision_model)
            return _error("model_unavailable")
        await run_in_threadpool(run.finish, "ok", None, True, acc, settings.llm_vision_model)
    finally:
        usage.RUN_TOKENS.reset(token)
    if not est.is_food:
        return _error("not_food")
    try:
        return await _save_analysis(est, data, mime, description)
    except Exception:
        logger.error("meal analysis could not be saved")
        return _error("save_failed")


async def _save_analysis(est, data: bytes, mime: str, description: str | None) -> MealAnalysis:
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
