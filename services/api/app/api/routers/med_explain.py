"""The medicine page (H6, prd F3, docs/specs/f3-explainer.md) and the name check for the add screens:

  GET  /medications/scope              is a typed or scanned name outside what the app is for (a gentle note, never a block)
  GET  /medications/{id}               the medicine as saved, plus its explanation if one has been made
  POST /medications/{id}/explanation   make the explanation (a web search and a short summary, about 10 to 30 seconds), or return the
                                       saved one. It is made once and kept; it is made again when the medicine's name, strength,
                                       type or label text changes, when the saved one is in the older layout (no four parts), or
                                       with `?refresh=true`.
  POST /medications/{id}/questions     a question for the doctor, saved to the doctor-question list

Nothing here writes or suggests a dose: the dose shown on the page is the person's own label.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from psycopg.rows import tuple_row

from app.agents import med_explain_pipeline
from app.api.routers.medications import datetime_today, list_medications
from app.core.errors import NotFound, ValidationFailed
from app.db import logstore
from app.schemas.medicines import (
    ExplanationOut,
    ExplanationPartsOut,
    MedicationDetailOut,
    MedicineScopeOut,
    QuestionIn,
    QuestionOut,
    WebSourceOut,
)
from app.services import med_explain_store as store
from app.services import medicine_scope, texts, ui_translate, usage
from app.services.web_sources import clean as clean_sources

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/medications", tags=["medicine page"])

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()

CANNOT_LOOK_UP = "We could not look this medicine up right now. Please try again in a moment."
NO_RELIABLE_PAGE = "We could not find a reliable page for this medicine yet. Please ask your pharmacist."
INVALID_ANSWER = "We could not read the information for this medicine just now. Please try again."
CAP_REACHED = "The daily limit for looking things up has been reached. Please try again tomorrow."


def _lock_for(med_id: str) -> threading.Lock:
    """One search at a time per medicine, so two quick opens of the page (or a double tap) cost one search, not two."""
    with _locks_guard:
        return _locks.setdefault(med_id, threading.Lock())


def to_out(saved: dict[str, Any]) -> ExplanationOut:
    parts = saved.get("parts")
    out = ExplanationOut(
        status=saved["status"], purpose=saved["purpose"] or "",
        parts=ExplanationPartsOut(for_diabetes=parts.get("for_diabetes", ""), how_it_works=parts.get("how_it_works", ""),
                                  what_you_may_notice=parts.get("what_you_may_notice", ""),
                                  why_timing_matters=parts.get("why_timing_matters", "")) if parts else None,
        side_effects=list(saved["side_effects"] or []), tell_doctor=saved["tell_doctor"] or "",
        sources=[WebSourceOut(title=s["title"], url=s["url"]) for s in clean_sources(saved["sources"])], generated_at=saved["generated_at"])
    return _in_chosen_language(out)


def _in_chosen_language(out: ExplanationOut) -> ExplanationOut:
    """The model wrote the explanation in English. In another language it is translated (translation only, see services/ui_translate.py)."""
    if texts.request_lang() == "en":
        return out
    p = out.parts
    flat = [out.purpose, out.tell_doctor, *(out.side_effects or [])] + ([p.for_diabetes, p.how_it_works, p.what_you_may_notice, p.why_timing_matters] if p else [])
    got = ui_translate.translate(None, flat)
    out.purpose, out.tell_doctor = got[0], got[1]
    n = len(out.side_effects or [])
    out.side_effects = got[2:2 + n]
    if p:
        p.for_diabetes, p.how_it_works, p.what_you_may_notice, p.why_timing_matters = got[2 + n:6 + n]
    return out


def _input_key(med: dict[str, Any]) -> str:
    return store.input_hash(med["name"], med["strength"], med["kind"], med["description"])


@router.get("/scope", response_model=MedicineScopeOut, response_model_by_alias=True)
async def medicine_scope_check(name: str = Query("", max_length=200), kind: str = Query("prescription", max_length=20)) -> MedicineScopeOut:
    return await run_in_threadpool(_scope, name, kind)


def _scope(name: str, kind: str) -> MedicineScopeOut:
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        return MedicineScopeOut(out_of_scope=medicine_scope.out_of_scope(conn, name, kind))


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
            parts_ok = store.parts_column_present(conn)
            names = [r[0] for r in conn.execute("select display_name from user_profile where user_id = %s", (user,)).fetchall() if r[0]]
        input_key = _input_key(med)
        # Kept unless it is for another version of the medicine, or asked to refresh. An explanation in the older layout (no four parts)
        # is made again, but only when the database can keep the four parts (migration 0033); until then the saved one is returned.
        if saved and saved["input_hash"] == input_key and not refresh and (not store.is_old_shape(saved) or not parts_ok):
            return to_out(saved)
        if not usage.allowed("vertex_generate"):
            raise HTTPException(429, CAP_REACHED)
        outcome = med_explain_pipeline.run(name=med["name"], strength=med["strength"], kind=med["kind"], directions=med["description"],
                                           known_names=names)
        usage.record("vertex_generate", outcome.input_tokens, outcome.output_tokens)
        if outcome.status == "failed":
            logger.warning("explanation not made: %s", outcome.reason)
            # 503: the model could not be reached. 404: the search found no page we can rely on (or the answer had nothing usable in
            # it): a plain answer the screen explains. 502: the model answered, but in a shape that could not be read.
            if outcome.reason == "service_unavailable":
                raise HTTPException(503, CANNOT_LOOK_UP)
            if outcome.reason in ("no_sources", "unusable_answer"):
                raise HTTPException(404, NO_RELIABLE_PAGE)
            raise HTTPException(502, INVALID_ANSWER)
        with logstore.tx() as conn:
            conn.row_factory = tuple_row
            store.save(conn, user, med_id, status=outcome.status, purpose=outcome.purpose, side_effects=outcome.side_effects,
                       tell_doctor=outcome.tell_doctor, sources=[{"title": s.title, "url": s.url} for s in outcome.sources],
                       input_key=input_key, model_id=outcome.model_id, prompt_version=outcome.prompt_version,
                       tokens_in=outcome.input_tokens, tokens_out=outcome.output_tokens, parts=outcome.parts or None)
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
        except ValidationFailed as e:
            raise HTTPException(422, str(e)) from None
    logger.info("doctor question added from the medicine page")
    return QuestionOut(id=qid)
