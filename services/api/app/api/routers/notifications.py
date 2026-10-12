"""GET /notifications, POST /notifications/{id}/open and /dismiss: log reminders that keep the person on track."""
from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.db import logstore
from app.schemas.log import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])

CACHE_SECONDS = 20.0
_cache: dict[str, tuple[float, list[dict]]] = {}     # person key -> (when it was read, the list)


def invalidate(user_key: str | None = None) -> None:
    if user_key is None:
        _cache.clear()
    else:
        _cache.pop(user_key, None)


def _read_only() -> bool:
    """A page view never writes reminder rows for Mr Tan (his history is loaded data); his list shows what is stored."""
    return logstore.current_user() == logstore.MR_TAN_USER


def _list() -> list[dict]:
    key = logstore.current_user_key()
    hit = _cache.get(key)
    now = time.monotonic()
    if hit and now - hit[0] < CACHE_SECONDS:
        return hit[1]
    out = logstore.notifications(create=not _read_only())
    _cache[key] = (now, out)
    return out


def _id_or_404(notification_id: str):
    nid = logstore.notification_uuid(notification_id)
    if nid is None:
        raise HTTPException(status_code=404, detail="That reminder was not found.")
    return nid


@router.get("", response_model=list[Notification], response_model_by_alias=True)
async def list_notifications() -> list[dict]:
    return await run_in_threadpool(_list)


@router.post("/{notification_id}/open", status_code=204)
async def open_notification(notification_id: str) -> None:
    _id_or_404(notification_id)
    invalidate(logstore.current_user_key())
    await run_in_threadpool(logstore.open_notification, notification_id)


@router.post("/{notification_id}/dismiss", status_code=204)
async def dismiss_notification(notification_id: str) -> None:
    """"Not for me". Removes the reminder and tells the learning loop, so it stops offering that time or idea."""
    _id_or_404(notification_id)
    invalidate(logstore.current_user_key())
    await run_in_threadpool(logstore.dismiss_notification, notification_id)
