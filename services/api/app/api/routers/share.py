"""Sharing the doctor report by link (L2, flow.md step 4). Routes under /brief/shares:

  POST   /brief/shares                         make a link {days, hours}; the token is returned once
  GET    /brief/shares                         this person's links (no tokens)
  GET    /brief/shares/context                open doctor questions and the next appointment, for L1
  DELETE /brief/shares/{id}                   turn a link off (returns the new state)
  GET    /brief/shares/public/{token}/report  the doctor's view. No X-User: the token is the only key

The public route reads the report for the link's owner, never for the caller, and returns the same 404 for a wrong, expired or
turned-off link. The token is never logged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from app.db import logstore
from app.schemas import share as S
from app.schemas.brief import DoctorReport
from app.services import share as svc

router = APIRouter(prefix="/brief/shares", tags=["share"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.post("", response_model=S.ShareCreated, response_model_by_alias=True, status_code=201)
async def create(body: S.ShareIn) -> S.ShareCreated:
    user, now = logstore.current_user(), _now()

    def work() -> dict:
        with logstore.tx() as conn:
            return svc.create_share(conn, user, body.days, body.hours, now)

    made = await run_in_threadpool(work)
    return S.ShareCreated(id=made["id"], token=made["token"], path=f"/s/{made['token']}", days=made["days"], expires_at=made["expires_at"])


@router.get("", response_model=S.ShareList, response_model_by_alias=True)
async def list_mine() -> S.ShareList:
    user, now = logstore.current_user(), _now()

    def work() -> list[dict]:
        with logstore.tx() as conn:
            return svc.list_shares(conn, user, now)

    return S.ShareList(shares=await run_in_threadpool(work))


@router.get("/context", response_model=S.ShareContext, response_model_by_alias=True)
async def context() -> S.ShareContext:
    user, now = logstore.current_user(), _now()

    def work() -> dict:
        with logstore.tx() as conn:
            return svc.context(conn, user, now)

    return S.ShareContext.model_validate(await run_in_threadpool(work))


@router.delete("/{share_id}", response_model=S.ShareRevoked, response_model_by_alias=True)
async def revoke(share_id: UUID) -> S.ShareRevoked:
    user, now = logstore.current_user(), _now()

    def work() -> dict | None:
        with logstore.tx() as conn:
            return svc.revoke_share(conn, user, share_id, now)

    done = await run_in_threadpool(work)
    if done is None:
        raise HTTPException(404, "This link was not found.")
    return S.ShareRevoked(id=done["id"], status=done["status"], revoked_at=done["revoked_at"])


@router.get("/public/{token}/report", response_model=DoctorReport, response_model_by_alias=True)
async def public_report(token: str, request: Request) -> DoctorReport:
    now = _now()
    agent = request.headers.get("user-agent")

    def work() -> dict | None:
        with logstore.tx() as conn:
            return svc.public_report(conn, token, agent, now)

    report = await run_in_threadpool(work)
    if report is None:
        raise HTTPException(404, svc.NOT_AVAILABLE)
    return DoctorReport.model_validate(report)
