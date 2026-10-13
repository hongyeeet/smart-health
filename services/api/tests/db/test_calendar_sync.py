"""Calendar reminders for a medicine against the real tables, with a fake Workato client and a fixed clock (2026-10-08 14:00 Singapore).
One event per dose time per day for the next 14 days (option A, 2026-10-13): 08:00 has 13 (today's has passed), 20:00 has 14.

Everything runs inside one transaction that is rolled back, so the shared database is left untouched.
Run from services/api:  python -m pytest tests/db/test_calendar_sync.py -q       Needs DATABASE_URL in the private .env.
"""
import os
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import psycopg
import pytest
from fastapi import BackgroundTasks, HTTPException

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

from app.api.routers import calendar as route  # noqa: E402
from app.api.routers import medications as meds  # noqa: E402
from app.core.errors import ExternalServiceError, NotFound  # noqa: E402
from app.db import logstore  # noqa: E402
from app.integrations.workato import CalendarEvent  # noqa: E402
from app.schemas.medicines import NewMedicationIn  # noqa: E402
from app.services import calendar_sync as sync  # noqa: E402

TZ = sync.TZ
NOW = datetime(2026, 10, 8, 14, 0, tzinfo=TZ)


class FakeClient:
    def __init__(self, *outcomes, configured=True):
        self.outcomes, self.calls, self._configured = list(outcomes), [], configured

    @property
    def configured(self):
        return self._configured

    def create_event(self, payload):
        self.calls.append(payload)
        o = self.outcomes.pop(0) if self.outcomes else None
        if isinstance(o, Exception):
            raise o
        return CalendarEvent(event_id=o or f"ev-{len(self.calls)}")


@pytest.fixture()
def conn():
    load_env()
    c = psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20)
    try:
        yield c
    finally:
        c.rollback()
        c.close()


@pytest.fixture()
def user(conn, monkeypatch):
    uid = str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0])

    @contextmanager
    def fake_tx():
        yield conn

    monkeypatch.setattr(logstore, "tx", fake_tx)
    monkeypatch.setattr(logstore, "current_user", lambda: uuid.UUID(uid))
    return uid


def add(conn, user, name="CRESTOR", times=("08:00",), strength="10 mg", **over):
    body = {"name": name, "kind": "prescription", "strength": strength, "totalQuantity": 30, "startDate": "2026-10-01",
            "doses": [{"time": t, "quantity": 1, "mealRelation": "na"} for t in times]}
    body.update(over)
    return meds.create_medication(conn, user, NewMedicationIn.model_validate(body), meds.datetime_today()).id


# ------------------------------------------------------------------ the plan
def test_one_event_per_dose_time_per_day_named_by_what_to_take(conn, user):
    mid = add(conn, user, "Metformin 500 mg", times=("08:00", "20:00"), strength="500 mg")
    p = sync.plan(conn, user, mid, NOW)
    morning = [e for e in p if e["time"] == "08:00"]
    evening = [e for e in p if e["time"] == "20:00"]
    assert (len(morning), len(evening)) == (13, 14)                                  # today's 08:00 has passed; 14 days in all
    assert morning[0]["summary"] == "Take Metformin, 1 Tab" and morning[0]["date"] == "2026-10-09" and morning[-1]["date"] == "2026-10-21"
    assert evening[0]["date"] == "2026-10-08" and evening[-1]["date"] == "2026-10-21"
    assert morning[0]["start"] == {"dateTime": "2026-10-09T08:00:00+08:00", "timeZone": "Asia/Singapore"}
    assert morning[0]["end"] == {"dateTime": "2026-10-09T08:15:00+08:00", "timeZone": "Asia/Singapore"}
    assert "recurrence" not in morning[0] and morning[0]["source"] == "smart-health"
    assert morning[0]["request_id"].startswith(f"{mid}:") and morning[0]["request_id"].endswith(":2026-10-09") and "strength" not in str(morning[0]).lower()
    assert "500 mg" not in morning[0]["summary"] and "with food" not in morning[0]["description"]
    assert [(e["date"], e["time"]) for e in p] == sorted((e["date"], e["time"]) for e in p)


def test_a_medicine_taken_with_food_says_so_in_the_event_note(conn, user):
    mid = add(conn, user, doses=[{"time": "08:00", "quantity": 2, "mealRelation": "after_meal"}])
    e = sync.plan(conn, user, mid, NOW)[0]
    assert e["summary"] == "Take CRESTOR, 2 Tabs" and ", with food" in e["description"]


def test_a_medicine_that_starts_in_the_future_starts_its_reminders_then(conn, user):
    mid = add(conn, user, startDate="2026-10-20")
    p = sync.plan(conn, user, mid, NOW)
    assert [e["date"] for e in p] == ["2026-10-20", "2026-10-21"]                    # inside the 14 days only


def test_a_course_with_an_end_date_gets_no_events_after_that_day(conn, user):
    mid = add(conn, user, "Clarithromycin 500 mg", times=("09:00",))
    conn.execute("update medications set end_date = '2026-10-12' where id = %s", (mid,))
    assert [e["date"] for e in sync.plan(conn, user, mid, NOW)] == ["2026-10-09", "2026-10-10", "2026-10-11", "2026-10-12"]


def test_a_finished_course_and_an_only_when_needed_medicine_get_no_events(conn, user):
    done = add(conn, user)
    conn.execute("update medications set end_date = '2026-10-05' where id = %s", (done,))
    as_needed = meds.create_medication(conn, user, NewMedicationIn.model_validate(
        {"name": "Cough syrup", "kind": "otc", "totalQuantity": 1, "doses": [{"time": None, "quantity": 5}]}), meds.datetime_today()).id
    assert sync.plan(conn, user, done, NOW) == [] and sync.plan(conn, user, as_needed, NOW) == []


def test_someone_elses_medicine_or_a_bad_id_is_not_found(conn, user):
    other = str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0])
    mid = add(conn, other)
    for bad in (mid, "not-a-uuid"):
        with pytest.raises(NotFound):
            sync.plan(conn, user, bad, NOW)
        with pytest.raises(NotFound):
            sync.owns(conn, user, bad)


# ------------------------------------------------------------------ queue and run
def test_a_new_medicine_is_queued_then_made_one_event_at_a_time_with_progress_saved_each_step(conn, user):
    mid = add(conn, user, times=("08:00", "13:00", "20:00"))                         # 13 + 13 + 14 = 40 events
    sid, go = sync.queue(conn, user, mid, configured=True, now=NOW)
    assert go is True and sync.status(conn, user, mid) == {"status": "queued", "reason": None, "events_done": 0, "events_total": 40, "error_code": None}
    seen = []

    class Watching(FakeClient):
        def create_event(self, payload):
            seen.append(sync.status(conn, user, mid)["events_done"])      # what the loading page would see before each call
            return super().create_event(payload)

    sync.run(sid, Watching(), now_fn=lambda: NOW)
    assert seen == list(range(40))
    assert sync.status(conn, user, mid) == {"status": "done", "reason": None, "events_done": 40, "events_total": 40, "error_code": None}
    events = conn.execute("select events from calendar_syncs where medication_id = %s", (mid,)).fetchone()[0]
    assert [(e["date"], e["time"], e["event_id"]) for e in events][:2] == [("2026-10-08", "20:00", "ev-1"), ("2026-10-09", "08:00", "ev-2")]


def test_a_failed_event_leaves_the_others_made_and_a_retry_only_makes_the_missing_one(conn, user):
    mid = add(conn, user, times=("08:00", "20:00"))                                  # 13 + 14 = 27 events
    sid, _ = sync.queue(conn, user, mid, configured=True, now=NOW)
    first = FakeClient("ev-a", ExternalServiceError("down", code="workato_unavailable"))
    sync.run(sid, first, now_fn=lambda: NOW)
    assert sync.status(conn, user, mid) == {"status": "failed", "reason": None, "events_done": 26, "events_total": 27, "error_code": "workato_unavailable"}
    sid2, go = sync.queue(conn, user, mid, configured=True, now=NOW)
    assert sid2 == sid and go is True and sync.status(conn, user, mid)["events_done"] == 26
    second = FakeClient("ev-b")
    sync.run(sid, second, now_fn=lambda: NOW)
    assert [(c["date"], c["time"]) for c in second.calls] == [("2026-10-09", "08:00")]       # only the one that failed; nothing is made twice
    assert sync.status(conn, user, mid)["status"] == "done" and sync.status(conn, user, mid)["events_done"] == 27


def test_a_plain_ok_with_no_event_id_still_counts_and_the_event_is_named_by_its_request(conn, user):
    mid = add(conn, user)

    class Plain(FakeClient):
        def create_event(self, payload):
            self.calls.append(payload)
            return CalendarEvent(event_id="")

    sid, _ = sync.queue(conn, user, mid, configured=True, now=NOW)
    sync.run(sid, Plain(), now_fn=lambda: NOW)
    events = conn.execute("select events from calendar_syncs where medication_id = %s", (mid,)).fetchone()[0]
    assert sync.status(conn, user, mid)["status"] == "done" and events[0]["event_id"] == f"{mid}:{events[0]['schedule_id']}:2026-10-09"


def test_without_the_calendar_consent_nothing_is_queued_or_called(conn, user):
    mid = add(conn, user)
    _, go = sync.queue(conn, user, mid, configured=True, now=NOW, consent=False)
    s = sync.status(conn, user, mid)
    assert go is False and (s["status"], s["reason"]) == ("skipped", "no_consent")
    assert sync.allowed(conn, user) is False
    conn.execute("insert into consents (user_id, kind, version, granted_at) values (%s, 'calendar_access', 'v1', now())", (user,))
    assert sync.allowed(conn, user) is True
    conn.execute("update consents set revoked_at = now() where user_id = %s and kind = 'calendar_access'", (user,))
    assert sync.allowed(conn, user) is False


def test_the_daily_top_up_only_serves_people_who_agreed(conn, user, monkeypatch):
    mid = add(conn, user)
    monkeypatch.setitem(logstore.USERS, "topup-test", {"id": uuid.UUID(user), "label": "t", "sub": ""})
    from app.core.config import settings as app_settings
    monkeypatch.setattr(app_settings, "scheduler_users", "topup-test")
    try:
        client = FakeClient()
        assert sync.top_up_all(client, now_fn=lambda: NOW)["people"] == 0 and client.calls == []      # no consent yet
        conn.execute("insert into consents (user_id, kind, version, granted_at) values (%s, 'calendar_access', 'v1', now())", (user,))
        out = sync.top_up_all(client, now_fn=lambda: NOW)
        assert out["people"] == 1 and out["medicines"] == 1 and len(client.calls) == 13
        again = FakeClient()
        sync.top_up_all(again, now_fn=lambda: NOW)
        assert again.calls == []                                                                       # a second pass makes nothing twice
        assert sync.top_up_all(FakeClient(configured=False), now_fn=lambda: NOW) == {"people": 0, "medicines": 0, "events": 0, "failed": 0}
    finally:
        pass
    assert mid


def test_everything_already_made_is_done_without_calling_workato_again(conn, user):
    mid = add(conn, user)
    sid, _ = sync.queue(conn, user, mid, configured=True, now=NOW)
    sync.run(sid, FakeClient(), now_fn=lambda: NOW)
    sid2, go = sync.queue(conn, user, mid, configured=True, now=NOW)
    assert (sid2, go) == (sid, False) and sync.status(conn, user, mid)["status"] == "done"


def test_without_workato_set_up_the_sync_is_skipped_and_nothing_is_called(conn, user):
    mid = add(conn, user)
    sid, go = sync.queue(conn, user, mid, configured=False, now=NOW)
    assert go is False and sync.status(conn, user, mid)["status"] == "skipped" and sync.status(conn, user, mid)["reason"] == "not_configured"


def test_an_only_when_needed_medicine_is_skipped(conn, user):
    mid = meds.create_medication(conn, user, NewMedicationIn.model_validate(
        {"name": "Cough syrup", "kind": "otc", "totalQuantity": 1, "doses": [{"time": None, "quantity": 5}]}), meds.datetime_today()).id
    _, go = sync.queue(conn, user, mid, configured=True, now=NOW)
    s = sync.status(conn, user, mid)
    assert go is False and (s["status"], s["reason"], s["events_total"]) == ("skipped", "as_needed", 0)


def test_a_sync_that_is_already_running_is_not_started_a_second_time(conn, user):
    mid = add(conn, user)
    sid, _ = sync.queue(conn, user, mid, configured=True, now=NOW)
    conn.execute("update calendar_syncs set status = 'running', updated_at = now() where id = %s", (sid,))
    assert sync.queue(conn, user, mid, configured=True, now=datetime.now(TZ)) == (sid, False)


def test_a_crash_inside_the_background_job_is_recorded_not_raised(conn, user):
    mid = add(conn, user)
    sid, _ = sync.queue(conn, user, mid, configured=True, now=NOW)

    class Boom(FakeClient):
        def create_event(self, payload):
            raise RuntimeError("boom")

    sync.run(sid, Boom(), now_fn=lambda: NOW)
    assert sync.status(conn, user, mid)["status"] == "failed" and sync.status(conn, user, mid)["error_code"] == "error"


def test_the_event_log_holds_counts_and_codes_never_the_medicine_name(conn, user):
    mid = add(conn, user, "Secretdrug 5 mg")
    sid, _ = sync.queue(conn, user, mid, configured=True, now=NOW)
    sync.run(sid, FakeClient(), now_fn=lambda: NOW)
    ev = [str(r[0]) for r in conn.execute("select payload from event_log where user_id = %s and event = 'calendar.sync.finished'", (user,)).fetchall()]
    assert len(ev) == 1 and "Secretdrug" not in ev[0] and "'events': 13" in ev[0]


# ------------------------------------------------------------------ the routes
def test_the_status_route_speaks_plainly_for_every_state(conn, user):
    mid = add(conn, user)
    assert route._status(user, mid).status == "none" and route._status(user, mid).can_retry is True
    sid, _ = sync.queue(conn, user, mid, configured=True, now=NOW)
    q = route._status(user, mid)
    assert (q.status, q.events_total, q.can_retry) == ("queued", 13, False) and "Google Calendar" in q.message
    sync.run(sid, FakeClient(ExternalServiceError("x", code="workato_refused")), now_fn=lambda: NOW)
    f = route._status(user, mid)
    assert f.status == "failed" and f.can_retry is True and "try again" in f.message
    sync.run(sid, FakeClient(), now_fn=lambda: NOW)
    assert route._status(user, mid).message == "Your reminders are on your calendar."
    sk = add(conn, user, "Other")
    sync.queue(conn, user, sk, configured=False, now=NOW)
    assert "not set up" in route._status(user, sk).message and route._status(user, sk).reason == "not_configured"


def test_the_status_route_refuses_someone_elses_medicine(conn, user):
    other = str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0])
    mid = add(conn, other)
    with pytest.raises(HTTPException) as e:
        route._status(user, mid)
    assert e.value.status_code == 404


def test_queueing_from_the_save_endpoints_never_raises_even_if_everything_is_broken(conn, user, monkeypatch):
    mid = add(conn, user)
    monkeypatch.setattr(sync, "queue", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("database down")))
    route.schedule_sync(BackgroundTasks(), user, mid)              # must simply return: the medicine is already saved


def test_scheduling_queues_the_row_and_hands_the_background_job_to_the_response(conn, user, monkeypatch):
    mid = add(conn, user)
    conn.execute("insert into consents (user_id, kind, version, granted_at) values (%s, 'calendar_access', 'v1', now())", (user,))
    monkeypatch.setenv("WORKATO_WEBHOOK_URL", "https://hooks.example.test/x")
    monkeypatch.setenv("WORKATO_WEBHOOK_TOKEN", "t")
    from app.core import settings as cfg
    cfg.get_settings.cache_clear()
    try:
        bg = BackgroundTasks()
        route.schedule_sync(bg, user, mid)
        assert len(bg.tasks) == 1 and sync.status(conn, user, mid)["status"] == "queued"
    finally:
        cfg.get_settings.cache_clear()
