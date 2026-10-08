"""The medicine page (H6, prd F3, docs/specs/f3-explainer.md):

  GET  /medications/{id}               the medicine as saved, plus its explanation if one has been made
  POST /medications/{id}/explanation   make the explanation (a web search and a short summary, about 10 to 30 seconds), or return the
                                       saved one. It is made once and kept; it is made again only when the medicine's name, strength,
                                       type or label text changes (or `?refresh=true`).
  POST /medications/{id}/questions     a question for the doctor, saved to the doctor-question list

Nothing here writes or suggests a dose: the dose shown on the page is the person's own label.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from psycopg.rows import tuple_row

from app.agents import med_explain_pipeline
from app.api.routers.medications import datetime_today, list_medications
from app.core.errors import NotFound
from app.db import logstore
from app.schemas.medicines import (
    ExplanationOut,
    MedicationDetailOut,
    QuestionIn,
    QuestionOut,
    WebSourceOut,
)
from app.services import med_explain_store as store
from app.services import usage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/medications", tags=["medicine page"])

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()

CANNOT_LOOK_UP = "We could not look this medicine up right now. Please try again in a moment."
NO_RELIABLE_INFO = "We could not find reliable information about this medicine. Please ask your pharmacist."
CAP_REACHED = "The daily limit for looking things up has been reached. Please try again tomorrow."


def _lock_for(med_id: str) -> threading.Lock:
    """One search at a time per medicine, so two quick opens of the page (or a double tap) cost one search, not two."""
    with _locks_guard:
        return _locks.setdefault(med_id, threading.Lock())


def to_out(saved: dict[str, Any]) -> ExplanationOut:
    return ExplanationOut(
        status=saved["status"], purpose=saved["purpose"] or "", side_effects=list(saved["side_effects"] or []),
        tell_doctor=saved["tell_doctor"] or "", sources=[WebSourceOut(title=s["title"], url=s["url"]) for s in saved["sources"] or []],
        generated_at=saved["generated_at"])


def _input_key(med: dict[str, Any]) -> str:
    return store.input_hash(med["name"], med["strength"], med["kind"], med["description"])


@router.get("/{med_id}", response_model=MedicationDetailOut, response_model_by_alias=True)
async def get_medicine(med_id: str) -> MedicationDetailOut:
    return await run_in_threadpool(_detail, med_id)


def _detail(med_id: str) -> MedicationDetailOut:
    user = str(logstore.current_user())
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        try:
            med = store.get_medicine(conn, user, med_id)
        except NotFound as e:
            raise HTTPException(404, str(e)) from None
        listed = next((m for m in list_medications(conn, user, datetime_today()) if m.id == med_id), None)
        saved = store.load(conn, user, med_id)
    if listed is None:
        raise HTTPException(404, "Medicine not found")
    # An explanation written for an older version of the medicine is not shown as if it were about this one.
    current = saved if saved and saved["input_hash"] == _input_key(med) else None
    return MedicationDetailOut(**listed.model_dump(), directions=med["description"], explanation=to_out(current) if current else None)


@router.post("/{med_id}/explanation", response_model=ExplanationOut, response_model_by_alias=True)
async def make_explanation(med_id: str, refresh: bool = False) -> ExplanationOut:
    return await run_in_threadpool(_explain, med_id, refresh)


def _explain(med_id: str, refresh: bool) -> ExplanationOut:
    user = str(logstore.current_user())
    with _lock_for(med_id):
        with logstore.tx() as conn:
            conn.row_factory = tuple_row
            try:
                med = store.get_medicine(conn, user, med_id)
            except NotFound as e:
                raise HTTPException(404, str(e)) from None
            saved = store.load(conn, user, med_id)
            names = [r[0] for r in conn.execute("select display_name from user_profile where user_id = %s", (user,)).fetchall() if r[0]]
        input_key = _input_key(med)
        if saved and saved["input_hash"] == input_key and not refresh:
            return to_out(saved)
        if not usage.allowed("vertex_vision"):
            raise HTTPException(429, CAP_REACHED)
        outcome = med_explain_pipeline.run(name=med["name"], strength=med["strength"], kind=med["kind"], directions=med["description"],
                                           known_names=names)
        usage.record("vertex_vision", outcome.input_tokens, outcome.output_tokens)
        if outcome.status == "failed":
            logger.warning("explanation not made: %s", outcome.reason)
            raise HTTPException(503 if outcome.reason == "service_unavailable" else 502,
                                CANNOT_LOOK_UP if outcome.reason == "service_unavailable" else NO_RELIABLE_INFO)
        with logstore.tx() as conn:
            conn.row_factory = tuple_row
            store.save(conn, user, med_id, status=outcome.status, purpose=outcome.purpose, side_effects=outcome.side_effects,
                       tell_doctor=outcome.tell_doctor, sources=[{"title": s.title, "url": s.url} for s in outcome.sources],
                       input_key=input_key, model_id=outcome.model_id, prompt_version=outcome.prompt_version,
                       tokens_in=outcome.input_tokens, tokens_out=outcome.output_tokens)
            saved = store.load(conn, user, med_id)
    logger.info("explanation made status=%s sources=%d side_effects=%d", outcome.status, len(outcome.sources), len(outcome.side_effects))
    if saved is None:
        raise HTTPException(500, CANNOT_LOOK_UP)
    return to_out(saved)


@router.post("/{med_id}/questions", response_model=QuestionOut, response_model_by_alias=True)
async def ask_doctor(med_id: str, body: QuestionIn) -> QuestionOut:
    return await run_in_threadpool(_ask, med_id, body)


def _ask(med_id: str, body: QuestionIn) -> QuestionOut:
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        try:
            qid = store.add_question(conn, str(logstore.current_user()), med_id, body.text)
        except NotFound as e:
            raise HTTPException(404, str(e)) from None
    logger.info("doctor question added from the medicine page")
    return QuestionOut(id=qid)
