"""Preventive nudges: checks and screenings that are due, from preventive_items and patient_preventive_status (LL7).

What it does: reports how many checks are overdue or due within 30 days (for the trace); proposes one memory fact per overdue check,
as `proposed` only; and offers at most one nudge a week, for the most overdue check, with a fixed template.
What it will not do: say what a person should have done, choose a clinic, book anything, or change a due date. Dates are only the
stored next date (care.preventive_status). The 30-day, 3-day and 30-day-gap numbers are placeholders pending clinical review.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from app.agents.adherence import _propose_fact
from app.agents.trace import audit
from app.db import nutritionstore
from app.db.logstore import TZ, tx
from app.db.nutritionstore import guarded
from app.services import texts
from app.services.care import KIND_LABELS, preventive_status, today_sg

logger = logging.getLogger(__name__)
FACT_CONFIDENCE = 0.8     # a due date on record is a plain reading of the stored data
FACT_CATEGORY = "routine"  # memory category (fact_category enum has no "activity")
NUDGE_VALID_DAYS = 3
NUDGE_GAP_DAYS = 30       # at most one nudge per check in this many days
NUDGE_ROUTE = "K3"        # the care plan
NUDGE_KEY = "preventive-{item}-{week}"


def iso_week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _name(kind: str, lang: str = "en") -> str:
    """The check's name inside a sentence: lower case, except the acronyms. Other languages use their own wording as it is."""
    if lang != "en" and texts.has(f"check.{kind}"):
        return texts.tr(lang, f"check.{kind}")
    label = KIND_LABELS.get(kind, "Check")
    return label if label[:2] in ("Hb", "GP") else label[0].lower() + label[1:]


def _day(d: date) -> str:
    return f"{d.day} {d:%b} {d.year}"


def overdue_statement(kind: str, due: date, lang: str = "en") -> str:
    return texts.tr(lang, "preventive.overdue", name=_name(kind, lang), day=_day(due))


def nudge_text(kind: str, lang: str = "en") -> str:
    return texts.tr(lang, "preventive.due", name=_name(kind, lang))


def summarise(rows: list[dict[str, Any]], today: date) -> dict[str, int]:
    """Pure rule: how many checks are overdue, and how many fall due within 30 days. A check with no date is counted in neither."""
    st = [preventive_status(r["next_due_on"], today) for r in rows]
    return {"overdue": st.count("overdue"), "due_soon": st.count("due_soon")}


def pick_nudge(rows: list[dict[str, Any]], now: datetime, have_keys: set[str], recent: dict[str, datetime],
               planned_kinds: set[str], excluded: set[str]) -> dict[str, Any] | None:
    """Pure rule: the one nudge for this week, or None. Rows carry item_id, kind, next_due_on.

    None when another preventive nudge already exists this ISO week, when no check is overdue, when the most overdue candidates are
    dismissed, were nudged within the gap, or already have a planned visit of the same kind. Otherwise the most overdue check wins."""
    today = today_sg(now)
    week = iso_week(today)
    if any(k.startswith("preventive-") and k.endswith(f"-{week}") for k in have_keys):
        return None
    cands = []
    for r in rows:
        if preventive_status(r["next_due_on"], today) != "overdue":
            continue
        if r["item_id"] in excluded or r["kind"] in planned_kinds:
            continue
        last = recent.get(r["item_id"])
        if last is not None and now - last < timedelta(days=NUDGE_GAP_DAYS):
            continue
        cands.append(r)
    if not cands:
        return None
    best = min(cands, key=lambda r: r["next_due_on"])
    key = NUDGE_KEY.format(item=best["item_id"], week=week)
    if key in have_keys:
        return None
    return {"key": key, "kind": "nudge", "title": "A check is due", "body": nudge_text(best["kind"]), "check": best["kind"], "route": NUDGE_ROUTE,
            "valid_until": now + timedelta(days=NUDGE_VALID_DAYS)}


def _item_of(key: str) -> str:
    """preventive-<item uuid>-<ISO week>: the item id is the 36 characters after the prefix."""
    return key[len("preventive-"):len("preventive-") + 36]


def _load(user_id, now: datetime) -> dict[str, Any]:
    with tx() as c:
        rows = c.execute(
            """select i.id, i.kind, s.next_due_on from preventive_items i
               left join patient_preventive_status s on s.preventive_item_id = i.id and s.user_id = %s""",
            (user_id,),
        ).fetchall()
        planned = c.execute(
            """select kind from appointments where user_id=%s and status='planned' and (scheduled_for is null or scheduled_for >= %s)""",
            (user_id, now),
        ).fetchall()
        sent = c.execute(
            "select payload->>'key' k, scheduled_for s from notifications where user_id=%s and payload->>'key' like %s and scheduled_for > %s",
            (user_id, "preventive-%", now - timedelta(days=NUDGE_GAP_DAYS)),
        ).fetchall()
    return {
        "rows": [{"item_id": str(r["id"]), "kind": r["kind"], "next_due_on": r["next_due_on"]} for r in rows],
        "planned": {r["kind"] for r in planned},
        "recent": {_item_of(r["k"]): r["s"] for r in sent if r["k"]},
    }


def run(user_id, write: bool = False) -> dict[str, Any]:
    """Count what is due and, with write=True, propose one fact per overdue check. Returns the report either way."""
    now = datetime.now(TZ)
    today = today_sg(now)
    rows = _load(user_id, now)["rows"]
    report: dict[str, Any] = {**summarise(rows, today), "checks": len(rows), "proposals": []}
    lang = texts.person_language(user_id)
    for r in sorted((r for r in rows if preventive_status(r["next_due_on"], today) == "overdue"), key=lambda r: r["next_due_on"]):
        kind, due = r["kind"], r["next_due_on"]
        text_en = overdue_statement(kind, due)
        text = overdue_statement(kind, due, lang)
        key = f"preventive.{kind}"
        entry: dict[str, Any] = {"key": key, "statement": text, "confidence": FACT_CONFIDENCE, "guard": "not_checked", "result": "dry_run"}
        if write:
            # a dry run makes no writes at all, so the guard (which logs its decision) is only asked when a fact is proposed
            entry["guard"] = "pass" if guarded(user_id, text_en, f"preventive_fact:{kind}") else "blocked"
            if entry["guard"] == "pass":
                with tx() as c:
                    entry["result"] = _propose_fact(
                        c, user_id, key, FACT_CATEGORY, {"check": kind, "due_on": due.isoformat()}, text, FACT_CONFIDENCE,
                        [{"table": "patient_preventive_status", "check": kind, "next_due_on": due.isoformat()}],
                    )
                if entry["result"] in ("proposed", "superseded_and_proposed"):
                    audit(user_id, "agent", "memory.fact_proposed", "memory_facts", None, {"key": key, "result": entry["result"]})
        report["proposals"].append(entry)
    return report


def nudges(user_id, now: datetime, have_keys: set[str], max_new: int) -> list[tuple[str, str, str, str, str, datetime]]:
    """At most one preventive nudge a week for the most overdue check. Texts are a fixed template and pass the guard first."""
    if max_new < 1:
        return []
    data = _load(user_id, now)
    # a dismissed check is a "template" arm (nudge_policy allows slot, template, suggestion, activity), keyed preventive:<item>
    excluded = {k.split(":", 1)[1] for k in nutritionstore.excluded_keys(user_id, "template") if k.startswith("preventive:")}
    n = pick_nudge(data["rows"], now, have_keys, data["recent"], data["planned"], excluded)
    if n is None or not guarded(user_id, n["body"], "preventive_nudge"):   # the guard reads the English text
        return []
    lang = texts.person_language(user_id)
    return [(n["key"], n["kind"], texts.tr(lang, "nudge.check_due.title"), nudge_text(n["check"], lang), n["route"], n["valid_until"])]
