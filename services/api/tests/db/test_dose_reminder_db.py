"""A dose reminder is really stored, and its learning record really saved, against the real tables (the unit tests use no database and
missed that nudge_policy's CHECK refused the old kind). Everything runs inside one transaction that is rolled back.
Run from services/api:  python -m pytest tests/db/test_dose_reminder_db.py -q       Needs DATABASE_URL in the private .env.
"""
import os
import uuid
import sys
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

from app.agents import dose_timing  # noqa: E402
from app.api.routers import medications as meds  # noqa: E402
from app.db import logstore  # noqa: E402
from app.schemas.medicines import NewMedicationIn  # noqa: E402

KEY = "test-dose-user"         # a throwaway person for this test only: it is added to the known users below and removed again


@pytest.fixture()
def conn():
    load_env()
    c = psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20, row_factory=dict_row)
    token = logstore._shared.set(c)       # every tx() in the code under test uses this rolled-back transaction
    logstore.USERS[KEY] = {"id": uuid.uuid5(logstore.NAMESPACE, f"user:{KEY}"), "label": "Test", "sub": ""}
    try:
        yield c
    finally:
        logstore.USERS.pop(KEY, None)
        logstore._shared.reset(token)
        logstore.set_user("demo")
        c.rollback()
        c.close()


def test_a_dose_reminder_row_and_a_policy_row_are_really_saved(conn):
    now = datetime.now(logstore.TZ)
    if now.hour == 0 and now.minute < 10:
        pytest.skip("too close to midnight for a dose time just before now")
    uid = logstore.USERS[KEY]["id"]
    conn.execute("insert into users (id, is_demo) values (%s, true) on conflict (id) do nothing", (uid,))
    when = (now - timedelta(minutes=5)).strftime("%H:%M")
    body = {"name": "Metformin 500 mg", "kind": "prescription", "strength": "500 mg", "totalQuantity": 60, "doses": [{"time": when, "quantity": 1, "mealRelation": "after_meal"}]}
    mid = meds.create_medication(conn, str(uid), NewMedicationIn.model_validate(body), meds.datetime_today()).id
    conn.execute("update medication_schedule set created_at = now() - interval '2 days' where medication_id = %s", (mid,))
    logstore.set_user(KEY)

    logstore.notifications()

    rows = conn.execute("select payload->>'key' k, payload->>'title' t from notifications where user_id = %s and payload->>'key' like 'dose-%%'", (uid,)).fetchall()
    assert len(rows) == 1 and rows[0]["k"].startswith(f"dose-{mid}-") and rows[0]["t"].startswith("Time for your")
    pol = conn.execute("select arm_kind, arm_key, tries from nudge_policy where user_id = %s", (uid,)).fetchall()
    assert len(pol) == 1 and pol[0]["arm_kind"] == dose_timing.ARM_KIND and pol[0]["arm_key"].startswith(f"dose_time:{mid}:") and pol[0]["tries"] == 1
