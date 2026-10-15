"""Barrier actions and dose anchoring (docs/specs/learning-loop.md LL2, LL3): the rules with no network, plus one database test that runs
for the demo user inside a transaction that is rolled back. Both sides of every threshold are checked: 3 misses, 70% and 14 days, 7 days
before a refill runs out, and the 2-hour dose window."""
from __future__ import annotations

import sys
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row, tuple_row

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.agents import adherence, barrier_actions as ba, trace  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db import logstore, nutritionstore  # noqa: E402
from app.db.logstore import TZ  # noqa: E402
from app.llm import jev  # noqa: E402

TODAY = date(2026, 10, 10)


def at(d: date, h: int, m: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, h, m, tzinfo=TZ)


# ----------------------------------------------------------------------------- thresholds and windows
def test_a_reason_needs_three_misses_to_be_acted_on():
    assert ba.due_reasons({"forgot": 2}) == []                  # two misses is not a pattern
    assert ba.due_reasons({"forgot": 3}) == ["forgot"]          # three is
    assert ba.due_reasons({"forgot": 4, "ran_out": 3, "cost": 1}) == ["forgot", "ran_out"]   # most common first, cost is not handled


def test_the_window_is_28_days_including_both_ends():
    lo, hi = ba.window_days(TODAY)
    assert hi == TODAY and lo == TODAY - timedelta(days=27)     # 28 days in all
    assert lo > TODAY - timedelta(days=28)                      # the 28th day back is out


def test_the_anchor_needs_fourteen_days_and_seventy_percent():
    assert not ba.anchor_holds(13, 13)                          # 13 days is too few, however good
    assert ba.anchor_holds(14, 10)                              # exactly 71%: 10 of 14 days
    assert not ba.anchor_holds(14, 9)                           # 64%: not enough
    assert ba.anchor_holds(20, 14) and not ba.anchor_holds(20, 13)   # exactly 70% holds, just under does not


def test_a_refill_is_due_from_seven_days_before_the_estimate_runs_out():
    assert ba.refill_due(7) and ba.refill_due(0)                # from 7 days before, through the day it runs out
    assert not ba.refill_due(8) and not ba.refill_due(-1)


def test_a_dose_reminder_is_only_inside_the_doctor_recorded_window():
    # from the dose time to 60 minutes after it, never before and never later
    sched = at(TODAY, 8)
    assert ba.dose_due(at(TODAY, 8), sched) and ba.dose_due(at(TODAY, 9), sched)
    assert not ba.dose_due(at(TODAY, 7, 59), sched) and not ba.dose_due(at(TODAY, 9, 1), sched)


# ----------------------------------------------------------------------------- wording: fixed templates, the person's own counts
def test_forgot_says_most_common_only_when_it_is():
    assert ba.action_text("forgot", 17, True) == ("Forgot is your most common reason (17 times in 4 weeks). "
                                                  "Link your reminder to something you already do, such as breakfast?")
    assert ba.action_text("forgot", 9, False) == ("You forgot 9 doses in the last 4 weeks. "
                                                  "Link your reminder to something you already do, such as breakfast?")


def test_ran_out_and_away_from_home_wording():
    assert ba.action_text("ran_out", 4, True) == "You ran out 4 times. Get a refill reminder 7 days before you run out?"
    assert ba.action_text("away_from_home", 8, True) == "You missed 8 doses when you were away. Keep a note on your phone for those days?"


def test_felt_fine_and_side_effects_are_questions_for_the_doctor_never_medicine_changes():
    q1 = ba.question_text("felt_fine", "Metformin")
    q2 = ba.question_text("side_effects", "Metformin")
    assert q1 == "I sometimes miss Metformin when I feel fine. I would like to discuss this at my next visit."
    assert q2 == "I noticed side effects after taking Metformin. I would like to talk about this at my next visit."
    for q in (q1, q2):
        assert not any(w in q.lower() for w in ("stop", "skip", "double", "change", "reduce"))
    with pytest.raises(ValueError):
        ba.action_text("felt_fine", 3, True)                    # no action for these: they are questions


# ----------------------------------------------------------------------------- anchoring from the person's rows
def _row(mid, sid, day, part, meal=None):
    return {"mid": mid, "sid": sid, "d": day, "part": part, "meal": meal}


def test_anchor_slots_count_days_and_hits_and_ignore_other_parts_of_the_day():
    rows = [_row("m1", "s1", TODAY - timedelta(days=i), "morning", "breakfast" if i < 10 else None) for i in range(14)]
    rows += [_row("m1", "s2", TODAY - timedelta(days=i), "night") for i in range(20)]       # night is not a routine we look for
    a = ba.anchor_slots(rows)
    assert len(a) == 1 and a[0]["part"] == "morning"
    assert a[0]["days"] == 14 and a[0]["hits"] == 10 and a[0]["holds"] is True


def test_a_day_with_a_dose_but_no_meal_counts_as_not_anchored():
    rows = [_row("m1", "s1", TODAY - timedelta(days=i), "evening", "dinner" if i < 9 else None) for i in range(14)]
    a = ba.anchor_slots(rows)[0]
    assert a["days"] == 14 and a["hits"] == 9 and a["holds"] is False


def test_one_routine_per_medicine_and_part_the_strongest_evidence_wins():
    strong = [_row("m1", "s1", TODAY - timedelta(days=i), "morning", "breakfast") for i in range(16)]
    weak = [_row("m1", "s2", TODAY - timedelta(days=i), "morning", None) for i in range(30)]
    a = ba.anchor_slots(strong + weak)
    assert len(a) == 1 and a[0]["holds"] is True and a[0]["days"] == 16


def test_anchor_key_names_the_medicine_and_part():
    assert ba.anchor_key("abc", "morning") == "routine.dose_anchor.abc.morning"


# ----------------------------------------------------------------------------- deleted and confirmed facts are respected
class FakeConn:
    """Answers the two reads of `_propose_fact` and records the writes, so the lifecycle rules run with no database."""

    def __init__(self, rejected=(), current=None):
        self.rejected, self.current, self.writes = list(rejected), current, []

    def execute(self, sql, params=()):
        s = " ".join(sql.split())
        if s.startswith("select value from memory_facts") and "'rejected'" in s:
            rows = [{"value": v} for v in self.rejected]
        elif s.startswith("select id, value, version, user_confirmed_at"):
            rows = [self.current] if self.current else []
        else:
            self.writes.append(s[:30])
            rows = []

        class R:
            def fetchall(_):
                return rows

            def fetchone(_):
                return rows[0] if rows else None

        return R()


def test_a_deleted_action_is_never_proposed_again_even_when_the_count_moves():
    deleted = {"barrier": "forgot", "action": "anchor_to_routine"}
    c = FakeConn(rejected=[deleted])
    assert adherence._propose_fact(c, "u", "barrier.action.forgot", "routine", dict(deleted), "Forgot is your most common reason (20 times).", 0.9, []) == "skipped_rejected"
    assert c.writes == []


def test_a_deleted_anchor_is_never_proposed_again():
    value = {"medication_id": "m1", "part": "morning"}
    c = FakeConn(rejected=[value])
    assert adherence._propose_fact(c, "u", ba.anchor_key("m1", "morning"), "routine", dict(value), "statement", 0.8, []) == "skipped_rejected"


# ----------------------------------------------------------------------------- run(): the dry path, with the database replaced by fixed rows
@contextmanager
def no_db():
    """No connection: every read helper is replaced by the test, so nothing reaches the database."""
    yield None


def _fixed(monkeypatch, *, meds, counts, rows=(), asked=False, guard=(False, {})):
    monkeypatch.setattr(ba, "tx", no_db)
    monkeypatch.setattr(ba, "medicines", lambda c, u: meds)
    monkeypatch.setattr(ba, "latest_day", lambda c, u, now: TODAY)
    monkeypatch.setattr(ba, "reason_counts", lambda c, u, end: counts)
    monkeypatch.setattr(ba, "anchor_rows", lambda c, u: list(rows))
    monkeypatch.setattr(ba, "_question_exists", lambda c, u, text, name, kw: asked)
    monkeypatch.setattr(jev, "guard_blocks", lambda text: guard)


def test_no_medicines_is_an_empty_state_with_no_rows(monkeypatch):
    _fixed(monkeypatch, meds={}, counts={("forgot", "m1"): 5})
    assert ba.run("u", write=False) == {"skipped": "no medicines yet"}


def test_no_miss_reasons_is_an_empty_state_with_no_rows(monkeypatch):
    _fixed(monkeypatch, meds={"m1": "Metformin"}, counts={})
    assert ba.run("u", write=False) == {"skipped": "no miss reasons in the last 28 days"}


def test_the_dry_run_proposes_one_action_per_barrier_and_says_so(monkeypatch):
    _fixed(monkeypatch, meds={"m1": "Metformin"},
           counts={("forgot", "m1"): 4, ("ran_out", "m1"): 3, ("away_from_home", "m1"): 2, ("felt_fine", "m1"): 3})
    r = ba.run("u", write=False)
    by = {p["key"]: p for p in r["proposals"]}
    assert set(by) == {"barrier.action.forgot", "barrier.action.ran_out"}           # away_from_home has only 2
    assert by["barrier.action.forgot"]["statement"].startswith("Forgot is your most common reason (4 times in 4 weeks).")
    assert all(p["result"] == "dry_run" for p in by.values())
    assert r["doctor_questions"] == [{"medication": "Metformin", "reason": "felt_fine",
                                      "statement": "I sometimes miss Metformin when I feel fine. I would like to discuss this at my next visit.", "result": "dry_run"}]


def test_a_question_needs_three_misses_for_that_medicine(monkeypatch):
    _fixed(monkeypatch, meds={"m1": "Metformin", "m2": "Fish oil"}, counts={("side_effects", "m1"): 2, ("side_effects", "m2"): 3})
    r = ba.run("u", write=False)
    assert [q["medication"] for q in r["doctor_questions"]] == ["Fish oil"]       # one miss-cluster per medicine, not per reason


def test_a_question_already_on_the_list_is_not_asked_again_and_the_guard_is_not_run(monkeypatch):
    _fixed(monkeypatch, meds={"m1": "Metformin"}, counts={("felt_fine", "m1"): 3}, asked=True)

    def no_guard(text):
        raise AssertionError("the guard must not run for a question already asked")

    monkeypatch.setattr(jev, "guard_blocks", no_guard)
    r = ba.run("u", write=False)
    assert r["doctor_questions"][0]["result"] == "already_asked"


def test_a_text_the_guard_blocks_is_never_proposed(monkeypatch):
    _fixed(monkeypatch, meds={"m1": "Metformin"}, counts={("forgot", "m1"): 3}, guard=(True, {"med_advice": 0.9}))
    r = ba.run("u", write=False)
    assert r["proposals"][0]["guard"] == "blocked" and r["proposals"][0]["result"] == "blocked"


def test_a_confirmed_routine_is_proposed_only_when_it_holds(monkeypatch):
    rows = [{"mid": "m1", "sid": "s1", "d": TODAY - timedelta(days=i), "part": "morning", "meal": "breakfast" if i < 15 else None} for i in range(16)]
    rows += [{"mid": "m2", "sid": "s2", "d": TODAY - timedelta(days=i), "part": "evening", "meal": None} for i in range(16)]
    _fixed(monkeypatch, meds={"m1": "Metformin", "m2": "Fish oil"}, counts={("forgot", "m1"): 3}, rows=rows)
    r = ba.run("u", write=False)
    keys = [p["key"] for p in r["proposals"]]
    assert ba.anchor_key("m1", "morning") in keys and ba.anchor_key("m2", "evening") not in keys


# ----------------------------------------------------------------------------- nudges: dose reminders are exempt, the rest count
class Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class Dispatch:
    """Answers each query by a word it contains, so the reminder rules run on fixed rows."""

    def __init__(self, routes):
        self.routes = routes

    def execute(self, sql, params=()):
        for word, rows in self.routes.items():
            if word in sql:
                return Rows(rows)
        return Rows([])


def _no_refill_or_question(monkeypatch):
    """The anchor rule on its own: the refill and question reminders are tested separately."""
    monkeypatch.setattr(ba, "_refill_reminders", lambda *a: [])
    monkeypatch.setattr(ba, "_question_reminders", lambda *a: [])


def _tx_with(routes):
    @contextmanager
    def t():
        yield Dispatch(routes)
    return t


def test_the_anchor_reminder_comes_after_the_meal_inside_the_dose_window(monkeypatch):
    routes = {
        "memory_facts": [{"value": {"medication_id": "m1", "part": "morning"}}],
        "food_logs": [{"meal": "breakfast", "end_at": at(TODAY, 8, 20)}],
        "medication_log": [{"scheduled_at": at(TODAY, 8), "name": "Metformin 500 mg", "strength": "500 mg"}],
    }
    monkeypatch.setattr(ba, "tx", _tx_with(routes))
    monkeypatch.setattr(ba, "guarded", lambda u, t, r: True)
    _no_refill_or_question(monkeypatch)
    rows = ba.nudges("u", at(TODAY, 8, 40), set(), 3)
    assert len(rows) == 1
    key, kind, title, body, to, until = rows[0]
    assert key == f"dose-anchor-m1-morning-{TODAY.isoformat()}" and kind == "dose_reminder" and to == "B1"
    assert body == "Breakfast logged. Time for your morning Metformin?"
    assert until == at(TODAY, 9)                        # the window closes 60 minutes after the dose time


def test_no_anchor_reminder_outside_the_window_or_when_already_stored(monkeypatch):
    routes = {
        "memory_facts": [{"value": {"medication_id": "m1", "part": "morning"}}],
        "food_logs": [{"meal": "breakfast", "end_at": at(TODAY, 8, 20)}],
        "medication_log": [{"scheduled_at": at(TODAY, 8), "name": "Metformin 500 mg", "strength": "500 mg"}],
    }
    monkeypatch.setattr(ba, "tx", _tx_with(routes))
    monkeypatch.setattr(ba, "guarded", lambda u, t, r: True)
    _no_refill_or_question(monkeypatch)
    assert ba.nudges("u", at(TODAY, 10, 30), set(), 3) == []                       # the window closed at 10:00
    key = f"dose-anchor-m1-morning-{TODAY.isoformat()}"
    assert ba.nudges("u", at(TODAY, 8, 40), {key}, 3) == []                        # already stored today


def test_a_dinner_does_not_remind_a_morning_dose(monkeypatch):
    routes = {
        "memory_facts": [{"value": {"medication_id": "m1", "part": "morning"}}],
        "food_logs": [{"meal": "dinner", "end_at": at(TODAY, 19, 40)}],
        "medication_log": [{"scheduled_at": at(TODAY, 8), "name": "Metformin", "strength": None}],
    }
    monkeypatch.setattr(ba, "tx", _tx_with(routes))
    monkeypatch.setattr(ba, "guarded", lambda u, t, r: True)
    _no_refill_or_question(monkeypatch)
    assert ba.nudges("u", at(TODAY, 8, 40), set(), 3) == []


def test_dose_reminders_are_exempt_from_the_cap_and_the_rest_are_not(monkeypatch):
    dose = ("dose-anchor-m1-morning-x", "dose_reminder", "t", "b", "B1", at(TODAY, 10))
    refill = ("refill-m1-x", "refill", "t", "b", "H1", at(TODAY, 23, 59))
    question = ("question-added-q1", "nudge", "t", "b", "K3", at(TODAY, 23, 59))
    monkeypatch.setattr(ba, "_anchor_reminders", lambda *a: [dose])
    monkeypatch.setattr(ba, "_refill_reminders", lambda *a: [refill])
    monkeypatch.setattr(ba, "_question_reminders", lambda *a: [question])
    monkeypatch.setattr(ba, "tx", no_db)
    assert ba.nudges("u", at(TODAY, 8), set(), 0) == [dose]                        # the cap is full: the dose still goes
    assert ba.nudges("u", at(TODAY, 8), set(), 1) == [dose, refill]
    assert ba.nudges("u", at(TODAY, 8), set(), 5) == [dose, refill, question]


# ----------------------------------------------------------------------------- the database: demo user, rolled back, and an empty person
@pytest.fixture
def rolled_back(monkeypatch):
    if not settings.database_url:
        pytest.skip("DATABASE_URL is not set")
    conn = psycopg.connect(logstore._dsn(), row_factory=dict_row, connect_timeout=20)

    @contextmanager
    def shared():
        prev = conn.row_factory
        try:
            yield conn
        finally:
            conn.row_factory = prev

    for mod in (ba, nutritionstore, trace):
        monkeypatch.setattr(mod, "tx", shared)
    monkeypatch.setattr(jev, "guard_blocks", lambda text: (False, {}))
    try:
        yield conn
    finally:
        conn.rollback()                                                              # nothing the test wrote is kept
        conn.close()


def test_a_person_with_no_data_gets_the_empty_state(rolled_back):
    uid = rolled_back.execute("insert into users (id, is_demo) values (gen_random_uuid(), true) returning id").fetchone()["id"]
    assert ba.run(uid, write=True) == {"skipped": "no medicines yet"}
    assert ba.nudges(uid, datetime.now(TZ), set(), 3) == []


def test_a_person_gets_proposals_once_and_the_refill_reminder_after_confirming(rolled_back):
    from app.schemas.medicine_scan import ConfirmedMedication, DoseTime
    from app.services.scan_store import confirm_medication

    conn = rolled_back
    demo = str(logstore.person_id("person-0123456789ab"))
    conn.execute("insert into users (id, is_demo) values (%s, false) on conflict (id) do nothing", (demo,))     # rolled back with the rest
    conn.row_factory = tuple_row                                                    # the shared save code reads rows by position
    med = confirm_medication(conn, demo, ConfirmedMedication(name="Rollback Test Metformin", kind="prescription", strength="500 mg",
                                                             doses=[DoseTime(dose_time=time(8, 0), quantity=1)], total_quantity=6))
    conn.row_factory = dict_row
    sched = conn.execute("select id from medication_schedule where medication_id=%s", (med,)).fetchone()["id"]
    today = datetime.now(TZ).date()
    reasons = ["forgot"] * 4 + ["ran_out"] * 3 + ["felt_fine"] * 3 + ["away_from_home"] * 2
    for i, reason in enumerate(reasons):
        when = datetime.combine(today - timedelta(days=i + 1), time(8, 0), tzinfo=TZ)
        conn.execute(
            "insert into medication_log (user_id, medication_id, schedule_id, scheduled_at, status, miss_reason, source) "
            "values (%s, %s, %s, %s, 'missed', %s, 'manual')", (demo, med, sched, when, reason))

    r = ba.run(demo, write=True)
    assert "skipped" not in r
    keys = {p["key"] for p in r["proposals"]}
    for reason, key in ba.ACTION_KEY.items():                                       # one action per barrier with 3 or more misses, no more
        assert (key in keys) == (r["reasons"].get(reason, 0) >= ba.MIN_OCCURRENCES)
    assert r["proposals"] and all(p["result"] in ("proposed", "superseded_and_proposed", "refreshed", "kept_user_version", "skipped_rejected")
                                  for p in r["proposals"])
    q = [x for x in r["doctor_questions"] if x["medication"] == "Rollback Test Metformin"]
    assert len(q) == 1 and q[0]["result"] == "added"

    again = ba.run(demo, write=True)                                                # a second night adds no second question
    q2 = [x for x in again["doctor_questions"] if x["medication"] == "Rollback Test Metformin"]
    assert q2 and q2[0]["result"] == "already_asked"
    n = conn.execute("select count(*) n from doctor_questions where user_id=%s and text=%s",
                     (demo, ba.question_text("felt_fine", "Rollback Test Metformin"))).fetchone()["n"]
    assert n == 1

    conn.execute("update memory_facts set status='active', user_confirmed_at=now() where user_id=%s and key=%s", (demo, ba.ACTION_KEY["ran_out"]))
    rows = ba.nudges(demo, datetime.now(TZ), set(), 9)
    refill = [x for x in rows if x[0].startswith(f"refill-{med}-") and x[1] == "refill"]
    assert len(refill) == 1 and refill[0][2] == "Time to refill Rollback Test Metformin"
    assert any(x[0].startswith("question-added-") for x in rows)                    # the person is told the question was added
    assert not any(x[0].startswith("dose-") for x in rows)                          # no routine is confirmed, so no dose reminder


# ----------------------------------------------------------------------------- Area A fixes (12 Oct)
def test_a_rejected_barrier_is_not_proposed_again_when_its_count_changes():
    rejected = {"barrier": "forgot", "missed_doses": 4}
    c = FakeConn(rejected=[rejected])
    assert adherence._propose_fact(c, "u", "barrier.forgot", "barrier", {"barrier": "forgot", "missed_doses": 5}, "x", 0.5, []) == "skipped_rejected"
    assert c.writes == []


def test_a_barrier_statement_is_neutral_and_names_the_window():
    s = adherence.barrier_statement("forgot", 4)
    assert "because" not in s and "4 times in the last 60 days" in s
    assert adherence.BARRIER_WINDOW_DAYS == 60


def test_an_anchor_is_proposed_without_any_miss_reason(monkeypatch):
    rows = [{"mid": "m1", "sid": "s1", "part": "morning", "d": date(2026, 9, 1) + timedelta(days=i), "meal": "breakfast"} for i in range(15)]
    _fixed(monkeypatch, meds={"m1": "Metformin"}, counts={}, rows=rows)
    r = ba.run("u", write=False)
    assert "skipped" not in r and [p["key"] for p in r["proposals"]] == [ba.anchor_key("m1", "morning")]


def test_the_anchor_reminder_gives_way_to_the_dose_time_reminder_for_the_same_dose(monkeypatch):
    from app.agents import dose_timing
    now = datetime(2026, 10, 12, 8, 20, tzinfo=TZ)
    sched = datetime(2026, 10, 12, 8, 0, tzinfo=TZ)
    mid = "11111111-1111-1111-1111-111111111111"

    class Conn:
        def execute(self, sql, params=()):
            s = " ".join(sql.split())
            rows = ([{"value": {"medication_id": mid, "part": "morning"}}] if "from memory_facts" in s else
                    [{"meal": "breakfast", "end_at": now - timedelta(minutes=10)}] if "from food_logs" in s else
                    [{"scheduled_at": sched, "name": "Metformin", "strength": None}])

            class R:
                def fetchall(_):
                    return rows
            return R()

    monkeypatch.setattr(ba.texts, "person_language", lambda u, conn=None: "en")
    monkeypatch.setattr(ba, "guarded", lambda *a: pytest.fail("a fixed-template dose reminder must not use the live guard"))
    got = ba._anchor_reminders(Conn(), "u", now, now.date(), set())
    assert [r[0] for r in got] == [f"dose-anchor-{mid}-morning-2026-10-12"]
    assert ba._anchor_reminders(Conn(), "u", now, now.date(), {dose_timing.dose_key(mid, sched)}) == []
