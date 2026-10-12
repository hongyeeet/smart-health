"""The Me care screens: GET /care/plan (K3), questions (K3), appointments (K7) and connected sources (K4).

Every read and write runs in one transaction for the current user (logstore). A soft remove or a cancel changes a status; no row is
deleted. The server never calls a calendar service here.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.core.errors import DomainError, InvalidTransition, NotFound, ValidationFailed
from app.db import logstore
from app.schemas import care as S
from app.services import care as svc

router = APIRouter(prefix="/care", tags=["care"])


async def _run(fn: Callable[..., Any], *args: Any) -> Any:
    user = str(logstore.current_user())

    def work() -> Any:
        with logstore.tx() as conn:
            return fn(conn, user, *args)

    return await run_in_threadpool(work)


def _now() -> datetime:
    return datetime.now(svc.TZ)


def _domain(e: DomainError) -> HTTPException:
    if isinstance(e, NotFound):
        return HTTPException(404, str(e))
    if isinstance(e, InvalidTransition):
        return HTTPException(409, str(e))
    if isinstance(e, ValidationFailed):
        return HTTPException(422, str(e))
    return HTTPException(400, str(e))


@router.get("/plan", response_model=S.CarePlan, response_model_by_alias=True)
async def plan() -> S.CarePlan:
    return S.CarePlan.model_validate(await _run(lambda c, u: svc.load_plan(c, u, _now())))


@router.post("/questions", response_model=S.QuestionOut, response_model_by_alias=True)
async def add_question(body: S.NewQuestion) -> S.QuestionOut:
    try:
        return S.QuestionOut.model_validate(await _run(svc.add_question, body.text))
    except DomainError as e:
        raise _domain(e) from None


@router.post("/questions/{question_id}/done", response_model=S.QuestionOut, response_model_by_alias=True)
async def mark_question_done(question_id: UUID, body: S.QuestionDone) -> S.QuestionOut:
    try:
        return S.QuestionOut.model_validate(await _run(svc.set_question_done, str(question_id), body.done))
    except DomainError as e:
        raise _domain(e) from None


@router.delete("/questions/{question_id}", response_model=S.QuestionRemoved, response_model_by_alias=True)
async def remove_question(question_id: UUID) -> S.QuestionRemoved:
    try:
        return S.QuestionRemoved.model_validate(await _run(svc.archive_question, str(question_id)))
    except DomainError as e:
        raise _domain(e) from None


@router.get("/appointments", response_model=list[S.AppointmentOut], response_model_by_alias=True)
async def appointments() -> list[S.AppointmentOut]:
    return [S.AppointmentOut.model_validate(a) for a in await _run(lambda c, u: svc.list_appointments(c, u, _now()))]


@router.post("/appointments", response_model=S.AppointmentOut, response_model_by_alias=True)
async def plan_appointment(body: S.NewAppointment) -> S.AppointmentOut:
    suggested = str(body.suggested_id) if body.suggested_id else None
    try:
        out = await _run(svc.add_appointment, body.kind, body.scheduled_for, suggested, _now())
    except DomainError as e:
        raise _domain(e) from None
    return S.AppointmentOut.model_validate(out)


@router.post("/appointments/{appointment_id}/cancel", response_model=S.AppointmentOut, response_model_by_alias=True)
async def cancel_appointment(appointment_id: UUID) -> S.AppointmentOut:
    try:
        return S.AppointmentOut.model_validate(await _run(svc.cancel_appointment, str(appointment_id)))
    except DomainError as e:
        raise _domain(e) from None


@router.get("/sources", response_model=S.Sources, response_model_by_alias=True)
async def sources() -> S.Sources:
    return S.Sources.model_validate(await _run(lambda c, u: svc.load_sources(c, u, _now())))
