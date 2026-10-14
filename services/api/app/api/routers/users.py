"""Create a new person (the switcher's "Start as new person"): POST /api/v1/users.

The app has no sign-in yet, so a person is the key the app sends as X-User. The key is made on the device when set-up opens; nothing
exists in the database for it while the person is answering the questions. When set-up is finished the app calls this route once, and
it makes the user row (nothing else: the answers are saved by the set-up requests that follow). A person who leaves set-up before the
end is never created. Mr Tan and the demo user already exist and are never created or reset here.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.db import logstore

router = APIRouter(prefix="/users", tags=["users"])


class NewPersonIn(BaseModel):
    key: str


class NewPerson(BaseModel):
    key: str
    created: bool


def _create(user: object) -> bool:
    with logstore.tx() as conn:
        done = conn.execute("insert into users (id, is_demo) values (%s, false) on conflict (id) do nothing returning id", (user,)).fetchone()
    return done is not None


@router.post("", response_model=NewPerson)
async def new_person(body: NewPersonIn) -> NewPerson:
    key = body.key.strip().lower()
    if not logstore.PERSON_KEY.fullmatch(key):
        raise HTTPException(400, "that is not a key for a new person")
    return NewPerson(key=key, created=await run_in_threadpool(_create, logstore.person_id(key)))
