"""Reminder emails (docs/specs/email-notifications.md):

  GET  /notify/email         the person's address and whether reminder emails are on
  PUT  /notify/email         set or clear it (onboarding and Me, Privacy call this)
  POST /notify/test          send one test email to the saved address, so a person can see it works
  GET  /notify/unsubscribe   the link in every email: turns reminder emails off (public; the signed token is the key)

The sending itself is the dispatcher in app/services/notify_email.py, run by the scheduler every minute.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse
from pydantic import Field

from app.core.errors import DomainError
from app.db import logstore
from app.integrations.workato_email import WorkatoEmail
from app.schemas.medicines import Camel
from app.services import notify_email as svc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notify", tags=["notify"])


class EmailSetting(Camel):
    email: str | None = Field(None, max_length=254)
    opt_in: bool = True


class EmailState(EmailSetting):
    available: bool = True                  # false until the database has the email columns (migration 0031)
    sending: bool = False                   # true when the Workato email recipe is set up


def _get(user: str) -> EmailState:
    with logstore.tx() as c:
        if not svc.columns_ready():
            return EmailState(email=None, opt_in=True, available=False, sending=False)
        r = c.execute("select notification_email, email_opt_in from user_profile where user_id = %s", (user,)).fetchone()
    return EmailState(email=r["notification_email"] if r else None, opt_in=bool(r["email_opt_in"]) if r else True, sending=WorkatoEmail.from_settings().configured)


def _put(user: str, body: EmailSetting) -> EmailState:
    email = (body.email or "").strip() or None
    if email is not None and not svc.is_valid_email(email):
        raise HTTPException(422, "That does not look like an email address. Check it and try again.")
    if not svc.columns_ready():
        raise HTTPException(503, "Email reminders are not ready yet. Please try again later.")
    with logstore.tx() as c:
        c.execute("update user_profile set notification_email = %s, email_opt_in = %s, updated_at = now() where user_id = %s", (email, body.opt_in, user))
        c.execute("insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'user', 'notify.email_changed', 'user_profile', %s, %s::jsonb)",
                  (user, user, '{"set": %s, "opt_in": %s}' % ("true" if email else "false", "true" if body.opt_in else "false")))
    return _get(user)


@router.get("/email", response_model=EmailState, response_model_by_alias=True)
async def get_email() -> EmailState:
    return await run_in_threadpool(_get, str(logstore.current_user()))


@router.put("/email", response_model=EmailState, response_model_by_alias=True)
async def put_email(body: EmailSetting) -> EmailState:
    return await run_in_threadpool(_put, str(logstore.current_user()), body)


class TestResult(Camel):
    sent: bool
    message: str


def _test(user: str) -> TestResult:
    state = _get(user)
    if not state.email:
        return TestResult(sent=False, message="Add your email address first.")
    sender = WorkatoEmail.from_settings()
    if not sender.configured:
        return TestResult(sent=False, message="Sending emails is not set up on this server yet.")
    row = svc.Row("test", user, "nudge", datetime.now(logstore.TZ), None,
                  {"key": "test", "title": "Your reminders are working", "body": "This is a test email from Smart Health. If you can read it, reminders will reach you here.", "to": "B1"},
                  0, "person", None, state.email, True, None, None)
    try:
        sender.send(svc.build_message(row))
    except DomainError as e:
        logger.warning("test email failed: %s", e.code)
        return TestResult(sent=False, message="We could not send the test email just now. Please try again later.")
    return TestResult(sent=True, message="Test email sent. It can take a minute to arrive.")


@router.post("/test", response_model=TestResult, response_model_by_alias=True)
async def test_email() -> TestResult:
    return await run_in_threadpool(_test, str(logstore.current_user()))


def _unsub(token: str) -> bool:
    user = svc.verify_unsubscribe(token)
    if not user or not svc.columns_ready():
        return False
    with logstore.tx() as c:
        c.execute("update user_profile set email_opt_in = false, updated_at = now() where user_id = %s", (user,))
        c.execute("insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'user', 'notify.unsubscribed', 'user_profile', %s, '{}'::jsonb)", (user, user))
    return True


@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(t: str = Query("", max_length=200)) -> Any:
    ok = await run_in_threadpool(_unsub, t)
    body = ("<h1>You are unsubscribed</h1><p>We will not send you reminder emails. You can turn them back on in the app, under Me, then Privacy.</p>" if ok
            else "<h1>This link did not work</h1><p>It may be out of date. You can turn reminder emails off in the app, under Me, then Privacy.</p>")
    return HTMLResponse(f"<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'><title>Smart Health</title>"
                        f"<body style='font-family:Arial,sans-serif;max-width:480px;margin:48px auto;padding:0 16px;color:#16201B'>{body}</body>", status_code=200 if ok else 400)
