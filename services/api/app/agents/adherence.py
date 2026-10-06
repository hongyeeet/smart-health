"""Adherence agent, code side (docs/specs/learning-loop.md LL2, LL3): barriers and morning anchoring from the person's own data.

Rules first, in code. The model writes none of the numbers and decides nothing here; JEV is used only by the output guard on the
sentences, through `nutritionstore.guarded`. Nothing is activated: every fact and draft is `proposed` until the person (or the team,
for shared wording) confirms it, and a rejected fact is never proposed again. Barriers lead to a doctor question or a changed
reminder, never to advice about a medicine.
"""
from __future__ import annotations

import json
import logging
import statistics
from datetime import date, timedelta
from typing import Any

from app.db.logstore import tx
from app.db.nutritionstore import guarded

logger = logging.getLogger(__name__)

# miss_reason (what the person said) -> barrier kind (adherence_barriers.barrier)
REASON_TO_BARRIER = {"forgot": "forgot", "ran_out": "ran_out", "side_effects": "side_effects", "away_from_home": "busy_away",
                     "cost": "cost", "felt_fine": "felt_fine", "other": "other"}
BARRIER_LABEL = {"forgot": "forgetting", "ran_out": "running out", "side_effects": "side effects", "busy_away": "being away from home",
                 "cost": "cost", "felt_fine": "feeling fine", "other": "other reasons"}
MIN_OCCURRENCES = 3   # a barrier needs this many misses before it is proposed (learning-loop LL3)
MIN_ANCHOR_DAYS = 20  # days of evidence before a morning anchor is proposed
ANCHOR_SPREAD_MIN = 25  # the middle half of the offsets must fit inside this many minutes


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def barrier_weeks(user_id) -> list[dict[str, Any]]:
    """Per week and barrier: how many missed doses, and the share of that week's misses. From medication_log and miss_reason."""
    with tx() as c:
        rows = c.execute(
            """select (scheduled_at at time zone 'Asia/Singapore')::date d, miss_reason::text r, count(*) n
               from medication_log where user_id=%s and status='missed' and miss_reason is not null group by 1,2""",
            (user_id,),
        ).fetchall()
    by_week: dict[date, dict[str, int]] = {}
    for r in rows:
        b = REASON_TO_BARRIER.get(r["r"], "other")
        by_week.setdefault(_week_start(r["d"]), {}).setdefault(b, 0)
        by_week[_week_start(r["d"])][b] += r["n"]
    out = []
    for wk, bs in sorted(by_week.items()):
        total = sum(bs.values())
        for b, n in bs.items():
            out.append({"week_start": wk, "barrier": b, "n": n, "share": round(n / total, 2)})
    return out


def weekend_evening_cluster(user_id) -> dict[str, Any] | None:
    """Do missed doses cluster on weekend evenings? A pattern of time, found by rules, not a reason the person gave."""
    with tx() as c:
        r = c.execute(
            """select count(*) filter (where status='missed') misses,
                      count(*) filter (where status='missed' and extract(isodow from scheduled_at at time zone 'Asia/Singapore') in (6,7)
                                       and extract(hour from scheduled_at at time zone 'Asia/Singapore') >= 18) wk_eve,
                      count(*) filter (where extract(isodow from scheduled_at at time zone 'Asia/Singapore') in (6,7)
                                       and extract(hour from scheduled_at at time zone 'Asia/Singapore') >= 18) wk_eve_doses,
                      count(*) doses
               from medication_log where user_id=%s""",
            (user_id,),
        ).fetchone()
    if not r["misses"] or r["wk_eve"] < MIN_OCCURRENCES or not r["wk_eve_doses"]:
        return None
    rate_wk = r["wk_eve"] / r["wk_eve_doses"]
    other = (r["misses"] - r["wk_eve"]) / max(1, r["doses"] - r["wk_eve_doses"])
    if rate_wk < 2 * other:  # only a pattern if clearly worse than the rest of the week
        return None
    return {"missed": int(r["wk_eve"]), "doses": int(r["wk_eve_doses"]), "miss_rate_pct": round(100 * rate_wk), "other_miss_rate_pct": round(100 * other)}


def morning_anchor(user_id) -> dict[str, Any] | None:
    """How long after finishing breakfast the person takes their after-meal morning dose. Needs a stable pattern before it is offered."""
    with tx() as c:
        rows = c.execute(
            """select extract(epoch from (l.taken_at - f.end_at)) / 60 off,
                      extract(hour from f.end_at at time zone 'Asia/Singapore') * 60 + extract(minute from f.end_at at time zone 'Asia/Singapore') endm
               from medication_log l
               join medication_schedule s on s.id = l.schedule_id
               join lateral (select end_at from food_logs f where f.user_id = l.user_id and f.deleted_at is null and f.meal_type = 'breakfast'
                              and (f.start_at at time zone 'Asia/Singapore')::date = (l.scheduled_at at time zone 'Asia/Singapore')::date
                              order by end_at limit 1) f on true
               where l.user_id = %s and l.status = 'taken' and s.meal_relation = 'after_meal'
                 and extract(hour from l.scheduled_at at time zone 'Asia/Singapore') < 11""",
            (user_id,),
        ).fetchall()
    return anchor_stats([float(r["off"]) for r in rows], [int(r["endm"]) for r in rows])


def anchor_stats(offsets: list[float], breakfast_end_minutes: list[int]) -> dict[str, Any] | None:
    """Pure rule: a stable gap between finishing breakfast and taking the dose, over enough days. None means no anchor."""
    offs = sorted(offsets)
    if len(offs) < MIN_ANCHOR_DAYS:
        return None
    q = statistics.quantiles(offs, n=4)
    if q[2] - q[0] > ANCHOR_SPREAD_MIN:
        return None
    ends = breakfast_end_minutes
    m = int(statistics.median(ends))
    return {"n": len(offs), "median_offset_min": round(statistics.median(offs)), "q1": round(q[0]), "q3": round(q[2]), "breakfast_end": f"{m // 60:02d}:{m % 60:02d}"}


def on_time_by_week(user_id) -> list[dict[str, Any]]:
    with tx() as c:
        rows = c.execute(
            """select date_trunc('week', scheduled_at at time zone 'Asia/Singapore')::date wk, count(*) n,
                      round(100.0 * avg((status = 'taken' and taken_at - scheduled_at <= interval '60 minutes')::int)) ontime
               from medication_log where user_id=%s group by 1 order by 1""",
            (user_id,),
        ).fetchall()
    return [{"week_start": r["wk"], "doses": int(r["n"]), "on_time_pct": int(r["ontime"])} for r in rows]


# ----------------------------------------------------------------------------- proposing (never activating)
def _base(v: dict | None) -> dict:
    """A fact's value without the flags a person's edit adds, so an edited or deleted fact is still recognised as the same idea."""
    return {k: x for k, x in (v or {}).items() if k != "edited_by_user"}


def _propose_fact(c, user_id, key: str, category: str, value: dict, statement: str, confidence: float, refs: list) -> str:
    """Insert a proposed fact, with these rules (docs/specs/memory.md section 8):
      - a fact the person deleted is never proposed again with the same idea;
      - a fact the person confirmed or edited is never superseded by the agent;
      - otherwise a changed value supersedes the current proposal as a new version, and an unchanged one only refreshes its evidence."""
    vjson = json.dumps(value, sort_keys=True)
    if any(_base(r["value"]) == value for r in c.execute("select value from memory_facts where user_id=%s and key=%s and status='rejected'", (user_id, key)).fetchall()):
        return "skipped_rejected"
    cur = c.execute(
        "select id, value, version, user_confirmed_at from memory_facts where user_id=%s and key=%s and status in ('proposed','active') order by version desc limit 1",
        (user_id, key),
    ).fetchone()
    if cur and cur["user_confirmed_at"] is not None:
        c.execute("update memory_facts set last_evidence_at=now(), updated_at=now() where id=%s", (cur["id"],))
        return "kept_user_version"
    if cur and json.dumps(cur["value"], sort_keys=True) == vjson:
        c.execute("update memory_facts set last_evidence_at=now(), confidence=%s, updated_at=now() where id=%s", (confidence, cur["id"]))
        return "refreshed"
    ver, sup = 1, None
    if cur:
        c.execute("update memory_facts set status='superseded', updated_at=now() where id=%s", (cur["id"],))
        sup, ver = cur["id"], cur["version"] + 1
    c.execute(
        """insert into memory_facts (user_id, key, category, value, statement_key, statement, confidence, evidence_status, evidence_refs, status, version, supersedes_id, source, last_evidence_at)
           values (%s,%s,%s::fact_category,%s::jsonb,%s,%s,%s,'derived'::evidence_status,%s::jsonb,'proposed'::fact_status,%s,%s,'reflection',now())""",
        (user_id, key, category, vjson, key, statement, confidence, json.dumps(refs), ver, sup),
    )
    return "superseded_and_proposed" if sup else "proposed"


def run(user_id, write: bool = False) -> dict[str, Any]:
    """Compute barriers and the morning anchor; with write=True store them as proposals. Returns a report either way."""
    report: dict[str, Any] = {"on_time": on_time_by_week(user_id), "barriers": barrier_weeks(user_id), "proposals": []}
    totals: dict[str, int] = {}
    for b in report["barriers"]:
        totals[b["barrier"]] = totals.get(b["barrier"], 0) + b["n"]
    facts: list[tuple[str, str, dict, str, float, list]] = []
    for barrier, n in sorted(totals.items(), key=lambda kv: -kv[1]):
        if n >= MIN_OCCURRENCES and barrier != "other":
            facts.append((f"barrier.{barrier}", "barrier", {"barrier": barrier, "missed_doses": n}, f"Some missed doses were because of {BARRIER_LABEL[barrier]} ({n} times).", min(0.9, 0.4 + 0.03 * n), [{"table": "medication_log", "miss_reason": barrier, "n": n}]))
    wk = weekend_evening_cluster(user_id)
    report["weekend_evening"] = wk
    if wk:
        facts.append(("barrier.weekend_evening", "barrier", wk, f"Evening doses on weekends are missed more often ({wk['miss_rate_pct']}% against {wk['other_miss_rate_pct']}% the rest of the time).", 0.7, [{"table": "medication_log", "n": wk["doses"]}]))
    anchor = morning_anchor(user_id)
    report["morning_anchor"] = anchor
    if anchor:
        facts.append(("routine.morning_anchor", "routine", {"anchor": "breakfast_finished", **anchor}, f"The morning dose is usually taken about {anchor['median_offset_min']} minutes after breakfast (breakfast ends about {anchor['breakfast_end']}).", min(0.95, 0.5 + anchor["n"] / 400), [{"table": "medication_log", "n": anchor["n"]}, {"table": "food_logs", "meal_type": "breakfast"}]))
    for key, cat, value, text, conf, refs in facts:
        ok = guarded(user_id, text, f"adherence_fact:{key}")
        entry = {"key": key, "statement": text, "confidence": round(conf, 2), "guard": "pass" if ok else "blocked", "result": "dry_run"}
        if ok and write:
            with tx() as c:
                entry["result"] = _propose_fact(c, user_id, key, cat, value, text, conf, refs)
        report["proposals"].append(entry)
    if write:
        with tx() as c:
            for b in report["barriers"]:
                c.execute(
                    """insert into adherence_barriers (user_id, week_start, barrier, n, share) values (%s,%s,%s,%s,%s)
                       on conflict (user_id, week_start, barrier) do update set n=excluded.n, share=excluded.share, built_at=now()""",
                    (user_id, b["week_start"], b["barrier"], b["n"], b["share"]),
                )
            if anchor and any(p["key"] == "routine.morning_anchor" and p["guard"] == "pass" for p in report["proposals"]):
                body = "Remind me to take my morning tablet when I tap that I have finished breakfast."
                if guarded(user_id, body, "routine_anchor_draft"):
                    exists = c.execute("select 1 from content_proposals where user_id=%s and kind='routine_anchor' and status in ('proposed','approved')", (user_id,)).fetchone()
                    if not exists:
                        c.execute(
                            "insert into content_proposals (user_id, kind, body, evidence_refs, guard_verdict, created_by) values (%s,'routine_anchor',%s,%s::jsonb,'pass','adherence_agent')",
                            (user_id, body, json.dumps([{"table": "medication_log", "n": anchor["n"]}])),
                        )
                        report["draft"] = body
    return report
