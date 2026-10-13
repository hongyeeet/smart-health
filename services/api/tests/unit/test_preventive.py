"""Preventive nudges: the wording, the counts, the one-a-week rule and the gaps around it, with no database and no network.

Covers: the 30-day due-soon window (both sides), the one-per-week key, the 30-day gap per check (both sides), a planned visit of the
same kind suppressing its nudge, a dismissed check being left out, the empty cases, and the guard before a nudge is returned.
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.agents import preventive as P  # noqa: E402
from app.db.logstore import TZ  # noqa: E402

NOW = datetime(2026, 10, 10, 10, 0, tzinfo=TZ)
TODAY = date(2026, 10, 10)
EYE, FOOT, KIDNEY = "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", "33333333-3333-4333-8333-333333333333"
THIS_WEEK = "2026-W41"


def item(item_id, kind, due):
    return {"item_id": item_id, "kind": kind, "next_due_on": due}


# ------------------------------------------------------------------------------------------------ wording
def test_overdue_statement_names_the_check_and_the_date():
    assert P.overdue_statement("eye_screening", date(2025, 9, 2)) == "Your eye screening was due on 2 Sep 2025. Plan one?"


def test_nudge_text_is_the_fixed_template():
    assert P.nudge_text("eye_screening") == "Your eye screening is due. You can add a visit in Track appointments."


def test_acronyms_keep_their_capitals_in_sentences():
    assert P.nudge_text("hba1c_test") == "Your HbA1c blood test is due. You can add a visit in Track appointments."
    assert P.nudge_text("gp_review") == "Your GP review is due. You can add a visit in Track appointments."


@pytest.mark.parametrize("kind", list(P.KIND_LABELS))
def test_wording_never_gives_advice_or_a_cause(kind):
    for text in (P.nudge_text(kind), P.overdue_statement(kind, date(2025, 9, 2))):
        low = text.lower()
        for banned in ("because", "caused", "should", "must", "need to", "associated"):
            assert banned not in low, (kind, text)


# ------------------------------------------------------------------------------------------------ counts and the week
def test_summarise_counts_overdue_and_due_within_30_days_on_both_sides():
    rows = [
        {"next_due_on": TODAY - timedelta(days=1)},   # overdue
        {"next_due_on": TODAY},                       # due today: due soon, not overdue
        {"next_due_on": TODAY + timedelta(days=30)},  # edge of the window: due soon
        {"next_due_on": TODAY + timedelta(days=31)},  # outside the window: neither
        {"next_due_on": None},                        # no date: neither
    ]
    assert P.summarise(rows, TODAY) == {"overdue": 1, "due_soon": 2}


def test_summarise_with_no_checks_is_zero():
    assert P.summarise([], TODAY) == {"overdue": 0, "due_soon": 0}


def test_iso_week_changes_on_monday_not_sunday():
    assert P.iso_week(date(2026, 10, 10)) == "2026-W41"
    assert P.iso_week(date(2026, 10, 11)) == "2026-W41"
    assert P.iso_week(date(2026, 10, 12)) == "2026-W42"


# ------------------------------------------------------------------------------------------------ choosing the one nudge
def test_the_most_overdue_check_is_chosen_and_its_key_is_per_item_and_week():
    rows = [item(FOOT, "foot_screening", date(2025, 11, 1)), item(EYE, "eye_screening", date(2025, 9, 2))]
    n = P.pick_nudge(rows, NOW, set(), {}, set(), set())
    assert n["key"] == f"preventive-{EYE}-{THIS_WEEK}"
    assert n["body"] == "Your eye screening is due. You can add a visit in Track appointments."
    assert n["route"] == "K3" and n["kind"] == "nudge"
    assert n["valid_until"] == NOW + timedelta(days=3)


def test_due_soon_alone_is_not_nudged():
    rows = [item(FOOT, "foot_screening", TODAY + timedelta(days=13))]
    assert P.pick_nudge(rows, NOW, set(), {}, set(), set()) is None


def test_no_checks_means_no_nudge():
    assert P.pick_nudge([], NOW, set(), {}, set(), set()) is None


def test_a_dismissed_check_is_left_out_and_the_next_overdue_one_is_used():
    rows = [item(EYE, "eye_screening", date(2025, 9, 2)), item(KIDNEY, "kidney_test", date(2025, 10, 1))]
    n = P.pick_nudge(rows, NOW, set(), {}, set(), {EYE})
    assert n["key"] == f"preventive-{KIDNEY}-{THIS_WEEK}"


def test_dismissing_the_only_overdue_check_gives_no_nudge():
    rows = [item(EYE, "eye_screening", date(2025, 9, 2))]
    assert P.pick_nudge(rows, NOW, set(), {}, set(), {EYE}) is None


def test_a_planned_visit_of_the_same_kind_suppresses_that_nudge():
    rows = [item(EYE, "eye_screening", date(2025, 9, 2))]
    assert P.pick_nudge(rows, NOW, set(), {}, {"eye_screening"}, set()) is None


def test_a_planned_visit_of_another_kind_does_not_suppress_it():
    rows = [item(EYE, "eye_screening", date(2025, 9, 2))]
    assert P.pick_nudge(rows, NOW, set(), {}, {"diabetes_review"}, set()) is not None


def test_one_nudge_per_week_across_all_checks():
    rows = [item(EYE, "eye_screening", date(2025, 9, 2))]
    other_this_week = {f"preventive-{KIDNEY}-{THIS_WEEK}"}
    assert P.pick_nudge(rows, NOW, other_this_week, {}, set(), set()) is None


def test_a_nudge_from_last_week_does_not_block_this_week():
    rows = [item(EYE, "eye_screening", date(2025, 9, 2))]
    last_week = {f"preventive-{KIDNEY}-2026-W40"}
    assert P.pick_nudge(rows, NOW, last_week, {}, set(), set()) is not None


def test_the_same_key_already_stored_is_not_repeated():
    rows = [item(EYE, "eye_screening", date(2025, 9, 2))]
    assert P.pick_nudge(rows, NOW, {f"preventive-{EYE}-{THIS_WEEK}"}, {}, set(), set()) is None


@pytest.mark.parametrize("days_ago, allowed", [(29, False), (30, True)])
def test_an_item_is_nudged_at_most_once_per_30_days(days_ago, allowed):
    rows = [item(EYE, "eye_screening", date(2025, 9, 2))]
    recent = {EYE: NOW - timedelta(days=days_ago)}
    assert (P.pick_nudge(rows, NOW, set(), recent, set(), set()) is not None) is allowed


def test_a_recent_nudge_for_one_check_lets_the_next_overdue_check_through():
    rows = [item(EYE, "eye_screening", date(2025, 9, 2)), item(KIDNEY, "kidney_test", date(2025, 10, 1))]
    recent = {EYE: NOW - timedelta(days=2)}
    n = P.pick_nudge(rows, NOW, set(), recent, set(), set())
    assert n["key"] == f"preventive-{KIDNEY}-{THIS_WEEK}"


# ------------------------------------------------------------------------------------------------ the reading of the rows
def test_item_id_is_read_back_from_the_key():
    assert P._item_of(f"preventive-{EYE}-{THIS_WEEK}") == EYE


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class FakeConn:
    """Answers each query by a word in its SQL, so the row logic can be tested without a database."""

    def __init__(self, answers):
        self.answers = answers

    def execute(self, sql, params=None):
        for word, rows in self.answers.items():
            if word in sql:
                return FakeCursor(rows)
        raise AssertionError(f"no fake for: {sql[:60]}")


def fake_tx(answers):
    @contextmanager
    def _tx():
        yield FakeConn(answers)
    return _tx


def test_load_reads_planned_kinds_and_recent_nudges(monkeypatch):
    answers = {
        "preventive_items": [{"id": EYE, "kind": "eye_screening", "next_due_on": date(2025, 9, 2)}],
        "appointments": [{"kind": "diabetes_review"}],
        "notifications": [{"k": f"preventive-{EYE}-2026-W39", "s": NOW - timedelta(days=5)}],
    }
    monkeypatch.setattr(P, "tx", fake_tx(answers))
    data = P._load("someone", NOW)
    assert data["rows"] == [{"item_id": EYE, "kind": "eye_screening", "next_due_on": date(2025, 9, 2)}]
    assert data["planned"] == {"diabetes_review"}
    assert data["recent"] == {EYE: NOW - timedelta(days=5)}


# ------------------------------------------------------------------------------------------------ nudges(): the guard and the empty cases
def test_nudges_returns_the_row_shape_the_hooks_expect(monkeypatch):
    monkeypatch.setattr(P, "_load", lambda u, n: {"rows": [item(EYE, "eye_screening", date(2025, 9, 2))], "planned": set(), "recent": {}})
    monkeypatch.setattr(P.nutritionstore, "excluded_keys", lambda u, k: set())
    monkeypatch.setattr(P, "guarded", lambda u, text, rule: True)
    out = P.nudges("someone", NOW, set(), 1)
    assert out == [(f"preventive-{EYE}-{THIS_WEEK}", "nudge", "A check is due", "Your eye screening is due. You can add a visit in Track appointments.", "K3", NOW + timedelta(days=3))]


def test_nudges_is_silent_when_the_guard_blocks_the_text(monkeypatch):
    monkeypatch.setattr(P, "_load", lambda u, n: {"rows": [item(EYE, "eye_screening", date(2025, 9, 2))], "planned": set(), "recent": {}})
    monkeypatch.setattr(P.nutritionstore, "excluded_keys", lambda u, k: set())
    monkeypatch.setattr(P, "guarded", lambda u, text, rule: False)
    assert P.nudges("someone", NOW, set(), 1) == []


def test_nudges_respects_max_new(monkeypatch):
    monkeypatch.setattr(P, "_load", lambda u, n: pytest.fail("no query when no room is left"))
    assert P.nudges("someone", NOW, set(), 0) == []


def test_a_dismissed_check_is_read_from_the_template_arm(monkeypatch):
    monkeypatch.setattr(P, "_load", lambda u, n: {"rows": [item(EYE, "eye_screening", date(2025, 9, 2))], "planned": set(), "recent": {}})
    seen = {}

    def fake_excluded(user_id, kind):
        seen["kind"] = kind
        return {f"preventive:{EYE}", "suggestion:other"}

    monkeypatch.setattr(P.nutritionstore, "excluded_keys", fake_excluded)
    monkeypatch.setattr(P, "guarded", lambda *a: pytest.fail("a dismissed check is not even worded"))
    assert P.nudges("someone", NOW, set(), 1) == []
    assert seen["kind"] == "template"


def test_nudges_with_no_checks_is_empty(monkeypatch):
    monkeypatch.setattr(P, "_load", lambda u, n: {"rows": [], "planned": set(), "recent": {}})
    monkeypatch.setattr(P.nutritionstore, "excluded_keys", lambda u, k: set())
    assert P.nudges("someone", NOW, set(), 1) == []


# ------------------------------------------------------------------------------------------------ run(): dry run and proposals
def _run_with(monkeypatch, rows):
    monkeypatch.setattr(P, "_load", lambda u, n: {"rows": rows, "planned": set(), "recent": {}})


def test_dry_run_reports_counts_and_writes_nothing(monkeypatch):
    _run_with(monkeypatch, [item(EYE, "eye_screening", date(2025, 9, 2)), item(FOOT, "foot_screening", TODAY + timedelta(days=13))])
    monkeypatch.setattr(P, "guarded", lambda *a: pytest.fail("a dry run asks the guard, which writes a log row"))
    monkeypatch.setattr(P, "tx", lambda: pytest.fail("a dry run opens no write"))
    rep = P.run("someone", write=False)
    assert rep["overdue"] == 1 and rep["due_soon"] == 1 and rep["checks"] == 2
    assert [p["result"] for p in rep["proposals"]] == ["dry_run"]
    assert rep["proposals"][0]["statement"] == "Your eye screening was due on 2 Sep 2025. Plan one?"


def test_write_proposes_one_fact_per_overdue_check(monkeypatch):
    _run_with(monkeypatch, [item(EYE, "eye_screening", date(2025, 9, 2)), item(KIDNEY, "kidney_test", date(2025, 10, 1)), item(FOOT, "foot_screening", TODAY + timedelta(days=13))])
    monkeypatch.setattr(P, "guarded", lambda u, text, rule: True)
    calls = []

    def fake_propose(c, user_id, key, category, value, text, conf, refs):
        calls.append((key, category, value))
        return "proposed"

    monkeypatch.setattr(P, "_propose_fact", fake_propose)
    monkeypatch.setattr(P, "audit", lambda *a, **k: None)

    @contextmanager
    def _tx():
        yield None

    monkeypatch.setattr(P, "tx", _tx)
    rep = P.run("someone", write=True)
    assert [c[0] for c in calls] == ["preventive.eye_screening", "preventive.kidney_test"]
    assert all(c[1] == "routine" for c in calls)
    assert calls[0][2] == {"check": "eye_screening", "due_on": "2025-09-02"}
    assert [p["result"] for p in rep["proposals"]] == ["proposed", "proposed"]


def test_a_blocked_statement_is_not_proposed(monkeypatch):
    _run_with(monkeypatch, [item(EYE, "eye_screening", date(2025, 9, 2))])
    monkeypatch.setattr(P, "guarded", lambda u, text, rule: False)
    monkeypatch.setattr(P, "_propose_fact", lambda *a: pytest.fail("blocked text must not be stored"))

    @contextmanager
    def _tx():
        yield None

    monkeypatch.setattr(P, "tx", _tx)
    rep = P.run("someone", write=True)
    assert rep["proposals"][0]["guard"] == "blocked"


def test_no_checks_gives_an_empty_report(monkeypatch):
    _run_with(monkeypatch, [])
    assert P.run("someone", write=False) == {"overdue": 0, "due_soon": 0, "checks": 0, "proposals": []}
