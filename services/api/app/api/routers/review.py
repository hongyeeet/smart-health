"""The reviewer screen (K11), for the care team and reviewers:

  GET  /review/queue?limit=20&set=mine|sample   the suggestions to rate, from the person's own dishes (or the shared sample set)
  POST /review/ratings                          rate one suggestion: reasonable, not_reasonable or unsafe (+ comment)
  GET  /review/score                            the share judged reasonable against the 85% target, and the unsafe count

Suggestions are computed from stored data (app/services/review.py); only ratings are written.
"""
from __future__ import annotations

from typing import Any, Callable, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.db import logstore
from app.schemas import review as S
from app.services import review as svc

router = APIRouter(prefix="/review", tags=["review"])


async def _run(fn: Callable[..., Any], *args: Any) -> Any:
    user = str(logstore.current_user())

    def work() -> Any:
        with logstore.tx() as conn:
            return fn(conn, user, *args)

    return await run_in_threadpool(work)


@router.get("/queue", response_model=S.Queue, response_model_by_alias=True)
async def queue(limit: int = Query(20, ge=1, le=50), source: Literal["mine", "sample"] = Query("mine", alias="set")):
    # Suggestions are computed outside the transaction: each one may search the shelf and ask the model.
    user = str(logstore.current_user())
    with logstore.tx() as conn:
        ratings = svc.load_ratings(conn, user)
        dishes = svc.logged_dishes(conn, user) if source == "mine" else svc.sample_dishes(conn)
    items = await run_in_threadpool(svc.build_queue, dishes, ratings, limit)
    return S.Queue.model_validate({
        "source": source,
        "items": items,
        "total": len(items),
        "rated": sum(1 for i in items if i["my_rating"]),
        "message": svc.queue_message(source, dishes, items, limit),
        "sample_offered": source == "mine" and not items,
    })


@router.post("/ratings", response_model=S.RatingOut, response_model_by_alias=True)
async def rate(body: S.RatingIn):
    try:
        verdict, comment = svc.check_rating(body.verdict, body.comment)
    except ValueError as e:
        raise HTTPException(422, str(e))

    def write(conn, user: str) -> dict[str, Any]:
        svc.record_rating(conn, user, body.suggestion_key, verdict, comment)
        return {"suggestion_key": body.suggestion_key, "verdict": verdict, "comment": comment, "rated": len(svc.load_ratings(conn, user))}

    return S.RatingOut.model_validate(await _run(write))


@router.get("/score", response_model=S.Score, response_model_by_alias=True)
async def score():
    return S.Score.model_validate(await _run(lambda conn, user: svc.score(svc.load_ratings(conn, user))))
