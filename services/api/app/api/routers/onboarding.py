"""The onboarding screens (A3 and A6) saved to the database:

  GET  /onboarding          what is already saved for the current person, so the form can be pre-filled
  PUT  /onboarding/profile  save the answers sent (only the fields in the body are written)
  POST /onboarding/complete record the data-processing consent if none is active, and the completion event
  POST /onboarding/chat     read one answer from the chat setup (A4); nothing is saved here

Checks and SQL live in app/services/onboarding.py.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.api.guards import not_the_demo_patient
from app.db import logstore
from app.schemas import onboarding as S
from app.services import onboarding as svc

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


async def _run(fn: Callable[..., dict[str, Any]], *args: Any) -> dict[str, Any]:
    user = logstore.current_user()

    def work() -> dict[str, Any]:
        with logstore.tx() as conn:
            return fn(conn, user, *args)

    try:
        return await run_in_threadpool(work)
    except svc.OnboardingError as e:
        raise HTTPException(422, str(e)) from e


def _read(conn: Any, user: Any) -> dict[str, Any]:
    return svc.load(conn, user)


def _save(conn: Any, user: Any, sent: dict[str, Any]) -> dict[str, Any]:
    labels = svc.enum_labels(conn)
    return svc.save_profile(conn, user, sent, labels, datetime.now(logstore.TZ).year)


def _complete(conn: Any, user: Any) -> dict[str, Any]:
    return svc.complete(conn, user, datetime.now(logstore.TZ))


@router.get("", response_model=S.OnboardingOut, response_model_by_alias=True)
async def get_onboarding():
    return S.OnboardingOut.model_validate(await _run(_read))


@router.put("/profile", response_model=S.SaveOut, response_model_by_alias=True)
async def save_profile(body: S.ProfileIn):
    not_the_demo_patient(logstore.current_user())
    sent = body.model_dump(exclude_unset=True)
    return S.SaveOut.model_validate(await _run(_save, sent))


@router.post("/complete", response_model=S.CompleteOut, response_model_by_alias=True)
async def complete():
    not_the_demo_patient(logstore.current_user())
    return S.CompleteOut.model_validate(await _run(_complete))


def _labels(conn: Any, user: Any) -> dict[str, Any]:
    return svc.enum_labels(conn)


@router.post("/chat", response_model=S.ChatOut, response_model_by_alias=True)
async def chat(body: S.ChatIn):
    """Read one answer from the chat setup (A4). Writes nothing: the screen saves through PUT /onboarding/profile."""
    not_the_demo_patient(logstore.current_user())
    labels = await _run(_labels)
    year = datetime.now(logstore.TZ).year
    try:
        # Outside the transaction: a model call can take a while and should not hold a database connection.
        result = await run_in_threadpool(svc.answer_step, body.step, body.text, labels, year)
    except svc.OnboardingError as e:
        raise HTTPException(422, str(e)) from e
    return S.ChatOut.model_validate(result)
