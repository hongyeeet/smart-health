"""Barriers to taking medicines, turned into one small confirmable action, and a dose tied to a routine the person already has (anchoring).

Learning-loop rules (docs/specs/learning-loop.md LL2, LL3). Everything is computed from the signed-in person's own rows; no name, date,
medicine or threshold is written for one person. The loop only proposes: each action or routine is a `proposed` memory fact until the
person confirms it, and a fact the person deleted is never proposed again (adherence._propose_fact). Wording is a fixed template with the
person's own numbers, guarded before it is stored.

What it will not do: suggest changing, skipping or combining a medicine or its dose. "Felt fine" and "side effects" become a question for
the doctor, written once per reason per medicine, in the person's own voice. A routine is "usually taken within 30 minutes of a meal",
never a cause of anything.

Thresholds are placeholders pending clinical review. They are named here, not in config.py.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Any

from psycopg.rows import tuple_row

from app.agents import adherence
from app.agents.trace import audit
from app.db.logstore import TZ, tx
from app.db.nutritionstore import guarded
from app.llm import jev
from app.services import texts
from app.services.dose_store import period_word, short_name

logger = logging.getLogger(__name__)
DOSE_WINDOW = timedelta(minutes=60)               # a reminder is sent from the doctor-recorded dose time to 60 minutes after it, never outside
WINDOW_DAYS = 28                                # miss reasons are counted over this many days, ending on the latest day with an answered dose
MIN_OCCURRENCES = adherence.MIN_OCCURRENCES     # a reason needs this many misses before anything is proposed (3)
REFILL_WARN_DAYS = 7                            # a refill reminder this many days before the supply estimate runs out
ANCHOR_MIN_DAYS = 14                            # a dose slot needs this many answered days before it is a routine
ANCHOR_SHARE_PCT = 70                           # ...and the dose came within ANCHOR_MINUTES after a logged meal on this share of those days
ANCHOR_MINUTES = 30
ANCHOR_PARTS = ("morning", "evening")           # the parts of the day a routine is looked for in
ANCHOR_MEALS = ("breakfast", "lunch", "dinner")
ACTION_KEY = {"forgot": "barrier.action.forgot", "ran_out": "barrier.action.ran_out", "away_from_home": "barrier.action.away_from_home"}
ACTION_NAME = {"forgot": "anchor_to_routine", "ran_out": "refill_reminder", "away_from_home": "phone_note"}
QUESTION_REASONS = ("felt_fine", "side_effects")
QUESTION_KEYWORD = {"felt_fine": "felt fine", "side_effects": "side effect"}
MEAL_LABEL = {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner"}
Row = tuple[str, str, str, str, str, datetime]


# ----------------------------------------------------------------------------- pure rules (no database)
def window_days(end: date) -> tuple[date, date]:
    """The 28 local days that end on `end`, both included."""
    return end - timedelta(days=WINDOW_DAYS - 1), end


def due_reasons(totals: dict[str, int]) -> list[str]:
    """Reasons with enough misses to act on, most common first. Fewer than MIN_OCCURRENCES is not a pattern yet."""
    return [r for r, n in sorted(totals.items(), key=lambda kv: (-kv[1], kv[0])) if n >= MIN_OCCURRENCES]


def action_text(reason: str, n: int, most_common: bool, lang: str = "en") -> str:
    """The proposal for one barrier, as a fixed template with the person's own count. 'Most common' is said only when it is true."""
    if reason == "forgot":
        lead = texts.tr(lang, "action.forgot.most", n=n) if most_common else texts.tr(lang, "action.forgot.some", n=n)
        return lead + texts.tr(lang, "action.forgot.tail")
    if reason == "ran_out":
        return texts.tr(lang, "action.ran_out", n=n, days=REFILL_WARN_DAYS)
    if reason == "away_from_home":
        return texts.tr(lang, "action.away", n=n)
    raise ValueError(f"no action for {reason}")


def anchor_text(part: str, name: str, hits: int, days: int, lang: str = "en") -> str:
    """The proposal to remind a dose right after a meal it usually follows. The guard reads the English text."""
    return texts.tr(lang, "anchor.suggest", part=texts.label(lang, "period", part), name=name, minutes=ANCHOR_MINUTES, hits=hits, days=days)


def meal_label(meal: str, lang: str = "en") -> str:
    return texts.tr(lang, f"meal.label.{meal}") if meal in MEAL_LABEL else texts.tr(lang, "meal.label.other")


def question_text(reason: str, name: str) -> str:
    """A question for the doctor, in the person's voice. It asks; it never tells them to change a medicine."""
    # worded to ask for a conversation, not for a ruling: the frozen output guard treats "do I still need" and "what should I do" as advice or diagnosis
    if reason == "felt_fine":
        return f"I sometimes miss {name} when I feel fine. I would like to discuss this at my next visit."
    return f"I noticed side effects after taking {name}. I would like to talk about this at my next visit."


def anchor_holds(days: int, hits: int) -> bool:
    """A dose slot is a routine when there are enough answered days and the dose came after a meal on at least 70% of them."""
    return days >= ANCHOR_MIN_DAYS and hits * 100 >= ANCHOR_SHARE_PCT * days


def dose_due(now: datetime, scheduled: datetime) -> bool:
    """Inside the doctor-recorded dose window: from the dose time to 60 minutes after it."""
    return scheduled <= now <= scheduled + DOSE_WINDOW


def refill_due(days_left: int) -> bool:
    """A refill reminder is due from 7 days before the estimate runs out, including the day it runs out."""
    return 0 <= days_left <= REFILL_WARN_DAYS


def anchor_key(medication_id: str, part: str) -> str:
    return f"routine.dose_anchor.{medication_id}.{part}"


def anchor_slots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per medicine, dose time and part of day: the answered days, and the days the dose came within 30 minutes after a logged meal."""
    slots: dict[tuple[str, str, str], dict[str, set]] = {}
    for r in rows:
        s = slots.setdefault((r["mid"], r["sid"], r["part"]), {"days": set(), "hits": set()})
        s["days"].add(r["d"])
        if r["meal"] is not None:
            s["hits"].add(r["d"])
    out = []
    for (mid, _sid, part), s in slots.items():
        if part in ANCHOR_PARTS:
            out.append({"medication_id": mid, "part": part, "days": len(s["days"]), "hits": len(s["hits"]),
                        "holds": anchor_holds(len(s["days"]), len(s["hits"]))})
    # one routine per medicine and part: the strongest evidence wins
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for a in out:
        k = (a["medication_id"], a["part"])
        if k not in best or (a["holds"], a["days"]) > (best[k]["holds"], best[k]["days"]):
            best[k] = a
    return list(best.values())


# ----------------------------------------------------------------------------- database reads
def _period_sql(ts: str) -> str:
    """The same parts of the day as dose_store.period_word, in SQL."""
    h = f"extract(hour from {ts} at time zone 'Asia/Singapore')"
    return f"(case when {h} < 12 then 'morning' when {h} < 17 then 'afternoon' when {h} < 21 then 'evening' else 'night' end)"


def medicines(c, user_id) -> dict[str, str]:
    """The person's current medicines: id -> the name without its strength."""
    rows = c.execute("select id::text id, name, strength from medications where user_id=%s and deleted_at is null", (user_id,)).fetchall()
    return {r["id"]: short_name(r["name"], r["strength"]) for r in rows}


def latest_day(c, user_id, now: datetime) -> date:
    """The window ends on the latest day with an answered dose (today if there is none): the same rule as the insights and the doctor report."""
    d = c.execute("select max((scheduled_at at time zone 'Asia/Singapore')::date) d from medication_log where user_id=%s and status in ('taken','missed')",
                  (user_id,)).fetchone()["d"]
    today = now.astimezone(TZ).date()
    return min(d, today) if d else today


def reason_counts(c, user_id, end: date) -> dict[tuple[str, str], int]:
    """(miss reason, medicine id) -> missed doses in the window."""
    lo, hi = window_days(end)
    rows = c.execute(
        """select miss_reason::text r, medication_id::text mid, count(*) n from medication_log
           where user_id=%s and status='missed' and miss_reason is not null
             and (scheduled_at at time zone 'Asia/Singapore')::date between %s and %s group by 1, 2""",
        (user_id, lo, hi),
    ).fetchall()
    return {(r["r"], r["mid"]): int(r["n"]) for r in rows}


def anchor_rows(c, user_id) -> list[dict[str, Any]]:
    """Every answered dose, with the breakfast, lunch or dinner logged within 30 minutes before it was taken, on the same day and part."""
    sched_part = _period_sql("l.scheduled_at")
    meal_part = _period_sql("f.end_at")
    sql = f"""
        select l.schedule_id::text sid, l.medication_id::text mid, (l.scheduled_at at time zone 'Asia/Singapore')::date d,
               {sched_part} part, meal.meal
        from medication_log l
        left join lateral (
            select f.meal_type::text meal from food_logs f
            where f.user_id = l.user_id and f.deleted_at is null and l.status = 'taken' and l.taken_at is distinct from l.scheduled_at
              and f.meal_type::text in ('breakfast', 'lunch', 'dinner')
              and f.end_at <= l.taken_at and l.taken_at - f.end_at <= make_interval(mins => %s)
              and (f.end_at at time zone 'Asia/Singapore')::date = (l.scheduled_at at time zone 'Asia/Singapore')::date
              and {meal_part} = {sched_part}
            order by f.end_at desc limit 1
        ) meal on true
        where l.user_id = %s and l.schedule_id is not null and l.status in ('taken', 'missed')"""
    return c.execute(sql, (ANCHOR_MINUTES, user_id)).fetchall()


def _question_exists(c, user_id, text: str, name: str, keyword: str) -> bool:
    """The same question already on the list (any status), or one the app or the person already wrote about this medicine and reason."""
    return c.execute(
        "select 1 from doctor_questions where user_id=%s and (text=%s or (text ilike %s and text ilike %s)) limit 1",
        (user_id, text, f"%{name}%", f"%{keyword}%"),
    ).fetchone() is not None


def _allowed(user_id, text: str, rule: str, write: bool) -> bool:
    """The output guard. A real run logs its decision; a dry run only asks the guard, so it writes nothing."""
    if write:
        return guarded(user_id, text, rule)
    blocked, _ = jev.guard_blocks(text)
    return not blocked


# ----------------------------------------------------------------------------- nightly step
def run(user_id: Any, write: bool = False) -> dict[str, Any]:
    """Propose one action per barrier the person's own history shows, a question for the doctor where it is about feeling fine or side
    effects, and a routine for each medicine that a dose follows. With write=False nothing is stored (not even the guard's log)."""
    now = datetime.now(TZ)
    with tx() as c:
        meds = medicines(c, user_id)
        if not meds:
            return {"skipped": "no medicines yet"}
        end = latest_day(c, user_id, now)
        counts = reason_counts(c, user_id, end)
        rows = anchor_rows(c, user_id)
    totals: dict[str, int] = {}
    for (reason, _mid), n in counts.items():
        totals[reason] = totals.get(reason, 0) + n
    if not totals:
        return {"skipped": "no miss reasons in the last 28 days"}
    lo, hi = window_days(end)
    most = max(totals.values())
    report: dict[str, Any] = {"window": {"from": lo.isoformat(), "to": hi.isoformat()}, "reasons": totals, "proposals": [], "doctor_questions": [], "routines": []}

    lang = texts.person_language(user_id)
    facts: list[dict[str, Any]] = []
    for reason in due_reasons(totals):
        n = totals[reason]
        if reason in ACTION_KEY:
            # "text" is the English draft the guard reads; "statement" is what the person sees and what is stored
            facts.append({"key": ACTION_KEY[reason], "category": "routine", "value": {"barrier": reason, "action": ACTION_NAME[reason]},
                          "text": action_text(reason, n, n == most), "statement": action_text(reason, n, n == most, lang), "conf": min(0.9, 0.4 + 0.03 * n),
                          "refs": [{"table": "medication_log", "miss_reason": reason, "n": n, "window_days": WINDOW_DAYS}]})
    questions: list[dict[str, Any]] = []
    for reason in QUESTION_REASONS:   # a question is about one medicine, so it needs the threshold for that medicine
        for mid, name in meds.items():
            k = counts.get((reason, mid), 0)
            if k >= MIN_OCCURRENCES:
                questions.append({"reason": reason, "medication_id": mid, "name": name, "keyword": QUESTION_KEYWORD[reason],
                                  "text": question_text(reason, name), "n": k})
    for a in anchor_slots(rows):
        name = meds.get(a["medication_id"])
        report["routines"].append({"medication": name, "part": a["part"], "days": a["days"], "hits": a["hits"], "holds": a["holds"]})
        if a["holds"] and name:
            text = anchor_text(a["part"], name, a["hits"], a["days"])
            facts.append({"key": anchor_key(a["medication_id"], a["part"]), "category": "routine",
                          "value": {"medication_id": a["medication_id"], "part": a["part"]}, "text": text,
                          "statement": anchor_text(a["part"], name, a["hits"], a["days"], lang),
                          "conf": min(0.95, 0.5 + a["days"] / 400),
                          "refs": [{"table": "medication_log", "n": a["days"]}, {"table": "food_logs", "n": a["hits"]}]})

    with tx() as c:
        for q in questions:
            q["asked"] = _question_exists(c, user_id, q["text"], q["name"], q["keyword"])
    for f in facts:
        f["allowed"] = _allowed(user_id, f["text"], f"barrier_action:{f['key']}", write)
        f["result"] = "dry_run" if f["allowed"] else "blocked"
    for q in questions:
        if q["asked"]:
            q["result"] = "already_asked"
            q["allowed"] = False
        else:
            q["allowed"] = _allowed(user_id, q["text"], f"doctor_question:{q['reason']}", write)
            q["result"] = "dry_run" if q["allowed"] else "blocked"

    if write:
        with tx() as c:
            for f in facts:
                if f["allowed"]:
                    f["result"] = adherence._propose_fact(c, user_id, f["key"], f["category"], f["value"], f["statement"], f["conf"], f["refs"])
            for q in questions:
                if q["allowed"]:
                    row = c.execute("insert into doctor_questions (user_id, text, origin, status) values (%s, %s, 'agent_suggested', 'open') returning id",
                                    (user_id, q["text"])).fetchone()
                    q["id"] = str(row["id"])
                    q["result"] = "added"
        for f in facts:
            if f["result"] in ("proposed", "superseded_and_proposed"):
                audit(user_id, "agent", "barrier_action.proposed", "memory_facts", None, {"key": f["key"], "result": f["result"]})
        for q in questions:
            if q["result"] == "added":
                audit(user_id, "agent", "doctor_question.added", "doctor_questions", q["id"], {"reason": q["reason"], "medication_id": q["medication_id"]})

    report["proposals"] = [{"key": f["key"], "statement": f["statement"], "confidence": round(f["conf"], 2), "guard": "pass" if f["allowed"] else "blocked",
                            "result": f["result"]} for f in facts]
    report["doctor_questions"] = [{"medication": q["name"], "reason": q["reason"], "statement": q["text"], "result": q["result"]} for q in questions]
    return report


def nudges(user_id: Any, now: datetime, have_keys: set[str], max_new: int) -> list[Row]:
    """Reminders the notification list should hold now. Dose reminders (keys start with "dose-") are exempt from the cap, the rest count."""
    today = now.astimezone(TZ).date()
    exempt: list[Row] = []
    with tx() as c:
        exempt += _anchor_reminders(c, user_id, now, today, have_keys)
    capped = _refill_reminders(user_id, now, today, have_keys)
    with tx() as c:
        capped += _question_reminders(c, user_id, now, have_keys)
    return exempt + capped[: max(0, max_new)]


def _anchor_reminders(c, user_id, now: datetime, today: date, have_keys: set[str]) -> list[Row]:
    """After the breakfast, lunch or dinner that a confirmed routine follows is logged, the dose is reminded, while it is still in its window."""
    out: list[Row] = []
    lang = texts.person_language(user_id, conn=c)
    facts = c.execute(
        "select value from memory_facts where user_id=%s and status='active' and user_confirmed_at is not null and key like %s",
        (user_id, "routine.dose_anchor.%"),
    ).fetchall()
    for f in facts:
        v = f["value"] or {}
        mid, part = v.get("medication_id"), v.get("part")
        if part not in ANCHOR_PARTS or not mid:
            continue
        key = f"dose-anchor-{mid}-{part}-{today.isoformat()}"
        if key in have_keys:
            continue
        meals = c.execute(
            """select f.meal_type::text meal, f.end_at from food_logs f where f.user_id=%s and f.deleted_at is null
               and (f.end_at at time zone 'Asia/Singapore')::date=%s and f.end_at <= %s and f.meal_type::text in ('breakfast', 'lunch', 'dinner')
               order by f.end_at desc""",
            (user_id, today, now),
        ).fetchall()
        meal = next((m for m in meals if period_word(m["end_at"].astimezone(TZ).hour) == part), None)
        doses = c.execute(
            """select l.scheduled_at, m.name, m.strength from medication_log l join medications m on m.id = l.medication_id
               where l.user_id=%s and l.medication_id=%s and l.status='pending' and (l.scheduled_at at time zone 'Asia/Singapore')::date=%s
               order by l.scheduled_at""",
            (user_id, mid, today),
        ).fetchall()
        dose = next((d for d in doses if period_word(d["scheduled_at"].astimezone(TZ).hour) == part and dose_due(now, d["scheduled_at"])), None)
        if meal is None or dose is None:
            continue
        name = short_name(dose["name"], dose["strength"])
        body_en = texts.tr("en", "dose.anchor.body", meal=meal_label(meal["meal"]), part=part, name=name)
        if guarded(user_id, body_en, "dose_anchor"):
            body = texts.tr(lang, "dose.anchor.body", meal=meal_label(meal["meal"], lang), part=texts.label(lang, "period", part), name=name)
            title = texts.tr(lang, "dose.anchor.title", part=texts.label(lang, "period", part))
            out.append((key, "dose_reminder", title, body, "B1", dose["scheduled_at"] + DOSE_WINDOW))
    return out


def _refill_body(days_left: int, short: str, lang: str) -> str:
    if days_left == 0:
        return texts.tr(lang, "refill.used_up")
    return texts.tr(lang, "refill.days", name=short, days=days_left)


def _refill_reminders(user_id, now: datetime, today: date, have_keys: set[str]) -> list[Row]:
    """A refill reminder 7 days before the supply estimate runs out, once per supply (the key holds the run-out date). Only after the person
    confirmed the refill action. The estimate is the Meds page's own (medications.refill_for), so the two never disagree."""
    from app.api.routers.medications import list_medications

    out: list[Row] = []
    lang = texts.person_language(user_id)
    with tx() as c:
        if not c.execute("select 1 from memory_facts where user_id=%s and key=%s and status='active' and user_confirmed_at is not null",
                         (user_id, ACTION_KEY["ran_out"])).fetchone():
            return out
        c.row_factory = tuple_row
        meds = list_medications(c, str(user_id), today)
    for m in meds:
        if m.as_needed or m.refill is None or not refill_due(m.refill.days_left):
            continue
        runout = today + timedelta(days=m.refill.days_left)
        key = f"refill-{m.id}-{runout.isoformat()}"
        if key in have_keys:
            continue
        short = short_name(m.name, None)
        body_en = _refill_body(m.refill.days_left, short, "en")
        if guarded(user_id, body_en, "refill_reminder"):
            body = _refill_body(m.refill.days_left, short, lang)
            out.append((key, "refill", texts.tr(lang, "refill.title", name=short), body, "H1", datetime.combine(runout, time(23, 59), tzinfo=TZ)))
    return out


def _question_reminders(c, user_id, now: datetime, have_keys: set[str]) -> list[Row]:
    """Tells the person a question was added to their doctor list (once, for the two days after it was added)."""
    out: list[Row] = []
    lang = texts.person_language(user_id, conn=c)
    rows = c.execute(
        """select id::text id, text from doctor_questions where user_id=%s and origin='agent_suggested' and status='open'
           and created_at > %s - interval '2 days' and (text like %s or text like %s)""",
        (user_id, now, "I sometimes miss % when I feel fine.%", "I noticed side effects after taking %"),
    ).fetchall()
    for r in rows:
        key = f"question-added-{r['id']}"
        if key in have_keys:
            continue
        # the question itself stays as the doctor will read it (English); only the wording around it follows the person's language
        body_en = texts.tr("en", "question.added.body", text=r["text"])
        if guarded(user_id, body_en, "doctor_question_added"):
            body = texts.tr(lang, "question.added.body", text=r["text"])
            out.append((key, "nudge", texts.tr(lang, "question.added.title"), body, "K3", now + timedelta(days=2)))
    return out
