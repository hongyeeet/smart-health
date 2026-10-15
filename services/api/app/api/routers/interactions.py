"""The medicine clash box on the Meds page (prd F5, docs/specs/f5-clash.md):

  GET  /interactions                  the open alerts, and whether a check is running now
  POST /interactions/check            run a check now (the app also runs one in the background after every medicine is added)
  POST /interactions/{id}/question    save "Is it OK to take X and Y together?" to the doctor-question list; with a body
                                      {"text": "..."} it saves the person's own question about the alert instead
  POST /interactions/{id}/acknowledge "I have checked with my doctor": the alert stops showing

An alert never says to stop a medicine and never says anything is safe. A medicine the check could not look at shows no alert, which is
not the same as safe: supplements and herbal products still carry their "Not checked" badge.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.concurrency import run_in_threadpool
from psycopg.rows import tuple_row

from app.agents import clash_pipeline
from app.core.errors import NotFound
from app.db import logstore
from app.schemas.interactions import ClashAlertOut, ClashStatus
from app.schemas.medicines import QuestionIn, QuestionOut, WebSourceOut
from app.services import clash_store as store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.get("", response_model=ClashStatus, response_model_by_alias=True)
async def get_interactions() -> ClashStatus:
    return await run_in_threadpool(_status, str(logstore.current_user()))


def _status(user: str) -> ClashStatus:
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        rows = store.list_open(conn, user)
    alerts = [ClashAlertOut(id=r["id"], med_a=r["med_a"], med_b=r["med_b"], text=r["text"], summary=r["summary"], origin=r["origin"], question_added=r["question_added"], raised_at=r["raised_at"],
                            sources=[WebSourceOut(title=s["title"], url=s["url"]) for s in r["sources"]]) for r in rows]
    return ClashStatus(checking=clash_pipeline.is_checking(user), check_incomplete=clash_pipeline.last_check_failed(user), alerts=alerts)


@router.post("/check", response_model=ClashStatus, response_model_by_alias=True)
async def run_check(background: BackgroundTasks) -> ClashStatus:
    user = str(logstore.current_user())
    background.add_task(clash_pipeline.check_user, user)
    status = await run_in_threadpool(_status, user)
    return status.model_copy(update={"checking": True})


@router.post("/{alert_id}/question", response_model=QuestionOut, response_model_by_alias=True)
async def ask_about(alert_id: str, body: QuestionIn | None = None) -> QuestionOut:
    return await run_in_threadpool(_ask, str(logstore.current_user()), alert_id, body.text if body else None)


def _ask(user: str, alert_id: str, text: str | None = None) -> QuestionOut:
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        try:
            return QuestionOut(id=store.add_question(conn, user, alert_id, text))
        except NotFound as e:
            raise HTTPException(404, str(e)) from None


@router.post("/{alert_id}/acknowledge", response_model=ClashStatus, response_model_by_alias=True)
async def acknowledge(alert_id: str) -> ClashStatus:
    return await run_in_threadpool(_ack, str(logstore.current_user()), alert_id)


def _ack(user: str, alert_id: str) -> ClashStatus:
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        try:
            store.acknowledge(conn, user, alert_id)
        except NotFound as e:
            raise HTTPException(404, str(e)) from None
    return _status(user)
