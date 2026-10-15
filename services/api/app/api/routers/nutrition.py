"""GET /nutrition/flags, GET /nutrition/lunch, GET /nutrition/menu, GET /nutrition/food-image/{key}, POST /nutrition/suggestions/accept.

Food habits and lunch ideas for the person the request acts as (X-User). Numbers come from the person's own logged meals and the
Singapore food database (only as a shelf of lighter dishes), in code; see app/db/nutritionstore.py. Lunch texts and flag texts are templates, not model writing.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.db import logstore, nutritionstore
from app.services import food_images, menu

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/flags")
async def flags() -> list[dict]:
    """Food habits the memory loop noticed, each with lighter dishes to try next time, compared with the person's own logged numbers."""
    uid = logstore.current_user()

    def run():
        with logstore.one_connection():          # many small queries: one connection, not one each
            out = nutritionstore.food_habits(uid)
            for f in out:
                f["text"] = nutritionstore.habit_text(f)
            return out

    return await run_in_threadpool(run)


@router.get("/lunch")
async def lunch() -> dict:
    uid = logstore.current_user()

    def run():
        with logstore.one_connection():          # many small queries: one connection, not one each
            start, end = nutritionstore.lunch_window(uid)
            return {"windowStart": f"{start // 60:02d}:{start % 60:02d}", "windowEnd": f"{end // 60 % 24:02d}:{end % 60:02d}", "options": nutritionstore.lunch_options(uid)}

    return await run_in_threadpool(run)


@router.get("/meal-ideas")
async def meal_ideas(meal: Literal["lunch", "dinner"]) -> dict:
    """Ideas for the next lunch or dinner, same shape as /nutrition/lunch plus the meal. Read only: nothing is written."""
    uid = logstore.current_user()

    def run():
        with logstore.one_connection():
            start, end = nutritionstore.meal_window(uid, meal)
            return {"meal": meal, "windowStart": f"{start // 60:02d}:{start % 60:02d}", "windowEnd": f"{end // 60 % 24:02d}:{end % 60:02d}", "options": nutritionstore.meal_options(uid, meal)}

    return await run_in_threadpool(run)


class Accept(BaseModel):
    key: str
    kind: str = "suggestion"


@router.post("/suggestions/dismiss", status_code=204)
async def dismiss(body: Accept) -> None:
    """"Not for me": the suggestion is not shown again."""
    uid = logstore.current_user()
    await run_in_threadpool(nutritionstore.policy_reject, uid, body.kind if body.kind in ("suggestion", "activity") else "suggestion", body.key)


@router.post("/suggestions/accept", status_code=204)
async def accept(body: Accept) -> None:
    """The person chose this suggestion: the learning policy counts it as acted on, so it is shown more."""
    uid = logstore.current_user()
    await run_in_threadpool(nutritionstore.policy_act, uid, body.kind if body.kind in ("suggestion", "activity") else "suggestion", body.key)


@router.get("/menu")
async def menu_for(meal: Literal["breakfast", "lunch", "dinner", "snack", "all"], background: BackgroundTasks) -> dict:
    """The Meal suggestions menu for one meal (docs/specs/menu.md). Builds the dishes, stores what is shown, and asks the background
    worker to make any missing picture. It never waits for a picture and never makes one for a dish that already has one."""
    uid = logstore.current_user()

    def run():
        with logstore.one_connection():
            return menu.build_all(uid) if meal == "all" else menu.build(uid, meal)

    out = await run_in_threadpool(run)
    if out["picturesWaiting"]:
        background.add_task(food_images.generate_pending, 3)
    return out


@router.get("/food-image/{key}")
async def food_image(key: str) -> Response:
    """One dish picture, for every person. Immutable: a ready picture never changes, so the browser may keep it for a year."""
    if food_images.dish_key(key) != key:
        raise HTTPException(status_code=404, detail="Picture not found")
    data = await run_in_threadpool(food_images.read_picture, key)
    if data is None:
        raise HTTPException(status_code=404, detail="Picture not found")
    return Response(content=data, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=31536000, immutable"})


class Pick(BaseModel):
    meal: Literal["breakfast", "lunch", "dinner", "snack"]
    key: str


@router.post("/menu/pick", status_code=204)
async def menu_pick(body: Pick) -> None:
    """The person added a dish to their picks: it is stamped on the stored suggestion and counted as acted on."""
    uid = logstore.current_user()
    await run_in_threadpool(menu.mark_picked, uid, body.meal, body.key)
