"""The urgent low-glucose alert (screen J1):

  GET  /urgent/state         the current alert, or status 'none'
  POST /urgent/simulate      {value}  a DEMO alert (refused at 4.0 or above)
  POST /urgent/acknowledge   "I'm okay now": sets the recheck time
  POST /urgent/escalate      queues the email to the emergency contact (the dispatcher sends it; nothing is sent here)
"""
from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.api.guards import MR_TAN
from app.db import logstore
from app.schemas import urgent as S
from app.services import urgent as svc

router = APIRouter(prefix="/urgent", tags=["urgent"])


async def _run(fn: Callable[..., Any], *args: Any) -> dict[str, Any]:
    user = logstore.current_user()

    def work() -> dict[str, Any]:
        with logstore.tx() as conn:
            return fn(conn, user, *args)

    return await run_in_threadpool(work)


async def _change(fn: Callable[..., Any], *args: Any) -> S.UrgentState:
    """Run a state change in one transaction, then write the audit events once it has committed."""
    user = logstore.current_user()

    def work() -> tuple[dict, list]:
        with logstore.tx() as conn:
            return fn(conn, user, *args)

    try:
        state, events = await run_in_threadpool(work)
    except svc.NoAlert:
        raise HTTPException(409, "There is no low glucose alert right now.")
    await run_in_threadpool(svc.record, user, events)
    return S.UrgentState.model_validate(state)


@router.get("/state", response_model=S.UrgentState, response_model_by_alias=True)
async def state():
    return S.UrgentState.model_validate(await _run(lambda c, u: svc.get_state(c, u, svc.utcnow())))


@router.post("/simulate", response_model=S.UrgentState, response_model_by_alias=True)
async def simulate(body: S.SimulateIn):
    # a demo alert on the loaded patient could queue a real email to his emergency contact: it is for the demo user only
    if str(logstore.current_user()) == str(MR_TAN):
        raise HTTPException(409, "A demo alert can only be made on the demo user, so no message can reach a real contact.")
    if svc.tier_for(body.value) == "none":
        raise HTTPException(422, f"A demo alert needs a value below {svc.LOW_BELOW} mmol/L.")
    return await _change(svc.simulate, body.value, svc.utcnow())


@router.post("/acknowledge", response_model=S.UrgentState, response_model_by_alias=True)
async def acknowledge():
    return await _change(svc.acknowledge, svc.utcnow())


@router.post("/escalate", response_model=S.UrgentState, response_model_by_alias=True)
async def escalate():
    return await _change(svc.escalate, svc.utcnow())
