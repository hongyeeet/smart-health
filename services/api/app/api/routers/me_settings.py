"""The Me settings screens (K5, K6, K8, K9):

  GET/PUT /me/language           K5: the language saved to the person's profile
  GET     /me/consents           K6: each consent now, and its history
  PUT     /me/consents/{kind}    K6: {granted: boolean}; a grant or a revoke, both kept in the history
  GET     /me/export             K8: the person's own data as a JSON file download
  POST    /me/delete-request     K8: records a deletion request; nothing is deleted here ({confirm: "DELETE"})
  GET/PUT /me/contact            K9: the one emergency contact

Logic and validation live in app/services/me_settings.py.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

from app.api.guards import not_the_demo_patient
from app.db import logstore
from app.schemas import me_settings as S
from app.services import me_settings as svc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/me", tags=["me_settings"])


async def _run(fn: Callable[..., Any], *args: Any) -> Any:
    user = logstore.current_user()

    def work() -> Any:
        with logstore.tx() as conn:
            return fn(conn, user, *args)

    try:
        return await run_in_threadpool(work)
    except svc.ProfileMissing:
        raise HTTPException(409, "Finish setting up your profile first. Then you can save this.")
    except svc.EmailNotSupported:
        raise HTTPException(409, "Email for your emergency contact is not set up yet. Save the name and phone number for now.")
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/language", response_model=S.LanguageOut, response_model_by_alias=True)
async def get_language():
    return S.LanguageOut(language=await _run(svc.get_language))


@router.put("/language", response_model=S.LanguageOut, response_model_by_alias=True)
async def set_language(body: S.LanguageIn):
    not_the_demo_patient(logstore.current_user())
    return S.LanguageOut(language=await _run(svc.set_language, body.language))


@router.get("/consents", response_model=S.ConsentsOut, response_model_by_alias=True)
async def consents():
    return S.ConsentsOut.model_validate(await _run(svc.list_consents))


@router.put("/consents/{kind}", response_model=S.ConsentsOut, response_model_by_alias=True)
async def set_consent(kind: S.ConsentKind, body: S.ConsentIn):
    return S.ConsentsOut.model_validate(await _run(svc.set_consent, kind, body.granted))


@router.get("/export")
async def export():
    now = datetime.now(timezone.utc)
    data = await _run(svc.export_for, now)
    stamp = now.astimezone(logstore.TZ).date().isoformat()
    return Response(
        content=json.dumps(data, ensure_ascii=False, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="smart-health-export-{stamp}.json"', "Cache-Control": "no-store"},
    )


@router.post("/delete-request", response_model=S.DeleteRequestOut, response_model_by_alias=True)
async def delete_request(body: S.DeleteRequestIn):
    return S.DeleteRequestOut.model_validate(await _run(svc.request_deletion, body.confirm))


@router.get("/contact", response_model=S.ContactOut, response_model_by_alias=True)
async def get_contact():
    return S.ContactOut.model_validate(await _run(svc.get_contact))


@router.put("/contact", response_model=S.ContactOut, response_model_by_alias=True)
async def save_contact(body: S.ContactIn):
    not_the_demo_patient(logstore.current_user())
    return S.ContactOut.model_validate(await _run(svc.save_contact, body.name, body.relation, body.phone, body.email))
