"""Start a new person (the switcher's "Start as new person"): POST /api/v1/users.

The app has no sign-in yet, so a person is the key the app sends as X-User. This route makes a new key and its user row. Nothing
else is written: no profile, no consent, no data. The person starts empty at step 1 of onboarding. Mr Tan and the demo user
already exist and are never created or reset here.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.db import logstore

router = APIRouter(prefix="/users", tags=["users"])


class NewPerson(BaseModel):
    key: str
    label: str


def _create(user: object) -> None:
    with logstore.tx() as conn:
        conn.execute("insert into users (id, is_demo) values (%s, false) on conflict (id) do nothing", (user,))


@router.post("", response_model=NewPerson)
async def new_person() -> NewPerson:
    key = logstore.new_person_key()
    await run_in_threadpool(_create, logstore.person_id(key))
    return NewPerson(key=key, label="New person")
