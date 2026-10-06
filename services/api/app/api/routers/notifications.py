"""GET /notifications, POST /notifications/{id}/open: log reminders that keep the person on track."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from app.db import logstore
from app.schemas.log import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[Notification], response_model_by_alias=True)
async def list_notifications() -> list[dict]:
    return await run_in_threadpool(logstore.notifications)


@router.post("/{notification_id}/open", status_code=204)
async def open_notification(notification_id: str) -> None:
    await run_in_threadpool(logstore.open_notification, notification_id)
