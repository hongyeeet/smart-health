"""Ask Equinox (screen I1):

  POST /chat/route               {text} -> what kind of request it is (for the waiting message); its JEV and triage results are reused by the answer
  POST /chat/messages            {text, conversationId?} -> the reply, sources, actions and follow-up questions
  GET  /chat/conversations/{id}  the messages of one of this person's conversations
  GET  /chat/starters            starter chips computed from this person's own data
  POST /chat/questions           {text} adds the person's own words to their doctor questions (after a refused question)

The answer logic and its guards are in app/services/chat.py. A model, JEV or cap problem never becomes an error here: it is a fixed reply.
"""
from __future__ import annotations

import psycopg
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.db import logstore
from app.schemas import chat as S
from app.services import chat as svc

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/messages", response_model=S.SendOut, response_model_by_alias=True)
async def send(body: S.SendIn) -> S.SendOut:
    key, uid = logstore.current_user_key(), str(logstore.current_user())
    try:
        out = await run_in_threadpool(svc.send, key, uid, body.text, body.conversation_id)
    except svc.NotFound:
        raise HTTPException(404, "That conversation was not found.") from None
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    return S.SendOut.model_validate(out)


@router.post("/route", response_model=S.RouteOut, response_model_by_alias=True)
async def route(body: S.RouteIn) -> S.RouteOut:
    """What kind of request is this? Runs the first steps of a turn so the screen can show a fitting waiting message; the answer reuses the results."""
    return S.RouteOut.model_validate(await run_in_threadpool(svc.route_preview, str(logstore.current_user()), body.text))


@router.get("/conversations/{conversation_id}", response_model=S.Conversation, response_model_by_alias=True)
async def conversation(conversation_id: str) -> S.Conversation:
    uid = str(logstore.current_user())
    try:
        return S.Conversation.model_validate(await run_in_threadpool(svc.get_conversation, uid, conversation_id))
    except svc.NotFound:
        raise HTTPException(404, "That conversation was not found.") from None


@router.get("/starters", response_model=S.Starters, response_model_by_alias=True)
async def starters() -> S.Starters:
    return S.Starters(starters=await run_in_threadpool(svc.starters, str(logstore.current_user())))


@router.post("/questions", response_model=S.QuestionOut, response_model_by_alias=True)
async def add_question(body: S.QuestionIn) -> S.QuestionOut:
    try:
        return S.QuestionOut.model_validate(await run_in_threadpool(svc.add_doctor_question, str(logstore.current_user()), body.text))
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(404, "That person was not found.") from None
