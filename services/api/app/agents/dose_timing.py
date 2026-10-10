"""Dose-time learning: a dose reminder is sent only inside the doctor's dose window (dose time to 60 minutes after it), at the offset
(0, 15, 30 or 45 minutes after the dose time) that works best for this person.

  - A reminder is made only for a scheduled dose that is still untaken, inside its window, for a medicine with a dose time. As-needed
    and deleted medicines have no slot, so they never get one. The first reminder waits for the chosen offset; one re-reminder comes
    30 minutes after it if the dose is still untaken and the window is still open.
  - The offset is picked by the existing epsilon-greedy policy (nudge_policy, kind dose_time, 15% exploring). A reminder whose dose
    is taken inside the window is a success for its offset (policy_act). An untaken dose is a miss: the reminder was tried and not
    acted on, so the rate falls. A person's own median delay (taken time minus set time, over their last 30 taken doses) is the prior,
    once there are 7 usable delays; before that the offset starts at 0 and the menu is explored evenly.
  - Nightly, a medicine with at least 14 usable delays gets ONE proposed memory fact (routine) with its usual delay. Only the person's
    confirm makes it active; a changed value supersedes the old proposal, a confirmed or deleted one is never overridden.

Every text is a fixed template (the medicine's name and the label's own directions or meal wording), checked by the output guard
before it is stored. Nothing here changes a dose, a dose time or a medicine, and no reminder is ever made outside its window.
"""
from __future__ import annotations

import hashlib
import logging
import random
import re
import statistics
from datetime import date, datetime, time, timedelta
from typing import Any, Callable, Iterable
from zoneinfo import ZoneInfo

from app.agents.trace import audit
from app.db import nutritionstore
from app.db.logstore import tx
from app.llm import jev
from app.services import texts
from app.services.dose_store import period_word, short_name
from app.services.insights import LATE_AFTER_MIN

logger = logging.getLogger(__name__)
TZ = ZoneInfo("Asia/Singapore")

# placeholders pending clinical review: none of these is advice, and none is specific to one person
MENU = (0, 15, 30, 45)              # minutes after the dose time: the only offsets ever tried
WINDOW_MIN = LATE_AFTER_MIN         # the dose window runs from the dose time to this many minutes after it
RENUDGE_AFTER_MIN = 30
PRIOR_MIN_DOSES = 7                 # usable delays before the person's own median is used as the prior
FACT_MIN_DOSES = 14                 # usable delays before a memory fact about the usual delay is proposed
PRIOR_HISTORY = 30                  # the most recent taken doses per medicine that the prior uses
PRIOR_CUSHION_MIN = 10              # the preferred offset sits this many minutes before the median delay
HISTORY_DAYS = 180
NOTE_LOOKBACK = timedelta(days=60)  # reminder rows kept for learning (acted, dismissed, renudged)
ARM_KIND = "dose_time"
ROUTE = "B1"
RENUDGE_SUFFIX = "-renudge"
DISMISSED = ("dismissed", "dismissed_learned")   # action on a reminder row: the person said "not for me" / already recorded

PERIOD = {"morning": "morning", "afternoon": "afternoon", "evening": "evening", "night": "bedtime"}
MEAL_PHRASE = {"before_meal": "Take it before a meal.", "after_meal": "Take it after a meal."}
_KEY = re.compile(r"^dose-([0-9a-f-]{36})-(\d{4}-\d{2}-\d{2})-(\d{2}:\d{2})(-renudge)?$")


# ───────────────────────────────────────────────────────────────── keys and windows (pure)
def arm_key(medication_id: str, offset: int) -> str:
    return f"{medication_id}:{offset}"


def arm_offset(arm: str) -> int:
    return int(arm.rsplit(":", 1)[1])


def local_at(day: date, t: time) -> datetime:
    return datetime.combine(day, t, tzinfo=TZ)


def dose_key(medication_id: str, at: datetime, renudge: bool = False) -> str:
    local = at.astimezone(TZ)
    return f"dose-{medication_id}-{local:%Y-%m-%d}-{local:%H:%M}" + (RENUDGE_SUFFIX if renudge else "")


def parse_key(key: str) -> tuple[str, datetime, bool] | None:
    """(medication id, dose time, is re-reminder) from a reminder key, or None for any other key."""
    m = _KEY.match(key or "")
    if not m:
        return None
    return m[1], datetime.combine(date.fromisoformat(m[2]), time.fromisoformat(m[3]), tzinfo=TZ), bool(m[4])


def window_end(at: datetime) -> datetime:
    return at + timedelta(minutes=WINDOW_MIN)


def in_window(at: datetime, now: datetime) -> bool:
    return at <= now <= window_end(at)


def is_open(status: str | None) -> bool:
    """A dose nobody has answered: no log row yet, or still pending. Taken or missed doses are never reminded."""
    return status in (None, "pending")


def make_slots(schedules: Iterable[dict], days: Iterable[date]) -> list[dict]:
    """Dose slots for the given days. A schedule with no dose time (as needed) gives none; a slot before the medicine existed,
    or after its end date, is not made."""
    out = []
    days = list(days)
    for s in schedules:
        if s.get("dose_time") is None:
            continue
        for day in days:
            at = local_at(day, s["dose_time"])
            if at < s["created_at"]:
                continue
            if s.get("end_date") and day > s["end_date"]:
                continue
            out.append({**s, "at": at, "day": day})
    return out


# ───────────────────────────────────────────────────────────────── the person's own history (pure)
def usable_delays(pairs: Iterable[tuple[datetime, datetime | None]]) -> list[float]:
    """Minutes from the set time to the time taken, for the most recent taken doses (pairs newest first). A dose logged as "I took
    it" has no time of its own (taken = set time), and a dose taken before its set time is not a delay: neither is counted."""
    out: list[float] = []
    for sched, taken in pairs:
        if taken is None or taken <= sched:
            continue
        out.append((taken - sched).total_seconds() / 60)
        if len(out) == PRIOR_HISTORY:
            break
    return out


def has_fact_history(delays: list[float]) -> bool:
    return len(delays) >= FACT_MIN_DOSES


def usual_rounded(median_min: float) -> int:
    """The usual delay in whole 5-minute steps, never below 5 so the text never says 0 minutes."""
    return max(5, int(round(median_min / 5.0)) * 5)


def preferred_offset(median_min: float) -> int:
    target = median_min - PRIOR_CUSHION_MIN
    return min(MENU, key=lambda o: (abs(o - target), o))


def choose_offset(medication_id: str, delays: list[float], excluded: set[str], tries: dict[str, int],
                  rank: Callable[[list[str]], list[str]]) -> int | None:
    """The offset to use for this medicine's next reminder, or None when every offset was dismissed.

    Under PRIOR_MIN_DOSES usable delays there is no prior: the least-tried offset goes first (ties go to the earlier one, so the
    first reminder is at 0). From PRIOR_MIN_DOSES on, the offset nearest the median minus the cushion is the preferred one, and
    `rank` (the epsilon-greedy policy) decides among the menu with that preference as the tie-break."""
    cands = [o for o in MENU if arm_key(medication_id, o) not in excluded]
    if not cands:
        return None
    if len(delays) < PRIOR_MIN_DOSES:
        return min(cands, key=lambda o: (tries.get(arm_key(medication_id, o), 0), o))
    pref = preferred_offset(statistics.median(delays))
    ordered = [arm_key(medication_id, o) for o in sorted(cands, key=lambda o: (abs(o - pref), o))]
    return arm_offset(rank(ordered)[0])


def is_success(reminded_at: datetime, taken_at: datetime | None, at: datetime) -> bool:
    """A reminder worked when the dose was taken after the reminder was sent and inside the window."""
    return taken_at is not None and reminded_at <= taken_at <= window_end(at)


def offset_of(at: datetime, reminded_at: datetime) -> int | None:
    """The offset a reminder was sent at, from when it was made. None when it was made outside the window: it cannot be attributed."""
    diff = (reminded_at - at).total_seconds() / 60
    if diff < 0 or diff >= WINDOW_MIN:
        return None
    return max(o for o in MENU if o <= diff)


def renudge_due(reminded_at: datetime, at: datetime, now: datetime) -> bool:
    return now >= reminded_at + timedelta(minutes=RENUDGE_AFTER_MIN) and in_window(at, now)


# ───────────────────────────────────────────────────────────────── fixed wording (pure)
def reminder_title(name: str, lang: str = "en") -> str:
    return texts.tr(lang, "dose.title", name=name)


def renudge_title(name: str, lang: str = "en") -> str:
    return texts.tr(lang, "dose.renudge_title", name=name)


def reminder_body(directions: str | None, meal: str | None, lang: str = "en") -> str:
    """The label's own directions when recorded (never translated: it is the label's text), else the meal wording when recorded, else nothing extra."""
    text = " ".join((directions or "").split())[:200]
    return text or (texts.tr(lang, f"dose.meal.{meal}") if meal in MEAL_PHRASE else "")


def period_for(times: set[time]) -> str:
    """'evening' for a medicine taken at one time of day; '' when it has several times (no single period to name)."""
    if len(times) != 1:
        return ""
    return PERIOD[period_word(next(iter(times)).hour)]


def fact_text(name: str, period: str, usual_min: int, offset: int, lang: str = "en") -> str:
    if period:
        return texts.tr(lang, "dose.fact.period", period=texts.label(lang, "period", period), name=name, usual=usual_min, offset=offset)
    return texts.tr(lang, "dose.fact.plain", name=name, usual=usual_min, offset=offset)


def _draft(slot: dict, key: str, renudge: bool, arm: str | None) -> dict[str, Any]:
    name = short_name(slot["name"], slot.get("strength"))
    # title and body are the English text (the guard reads them); name, directions and meal let _vet give the person's language
    return {"key": key, "kind": "dose_renudge" if renudge else "dose_reminder",
            "title": (renudge_title if renudge else reminder_title)(name), "body": reminder_body(slot.get("directions"), slot.get("meal")),
            "until": window_end(slot["at"]), "arm": arm, "medication_id": slot["mid"],
            "name": name, "renudge": renudge, "directions": slot.get("directions"), "meal": slot.get("meal")}


def _vet(d: dict[str, Any], check: Callable[[str, str], bool], lang: str = "en") -> tuple | None:
    """A reminder row, or None when its title is blocked. A blocked body is dropped and the reminder still goes out without it.
    The guard checks the English text; the row carries the text in `lang`."""
    if not check(d["title"], "dose_reminder_title"):
        return None
    body_ok = not d["body"] or check(d["body"], "dose_reminder_body")
    title = (renudge_title if d["renudge"] else reminder_title)(d["name"], lang)
    body = reminder_body(d["directions"], d["meal"], lang) if body_ok else ""
    return (d["key"], d["kind"], title, body, ROUTE, d["until"])


# ───────────────────────────────────────────────────────────────── the decision (pure, no database, no clock but `now`)
def _dismissed(notes: dict[str, dict]) -> tuple[set[str], list[dict]]:
    """Offsets the person dismissed (excluded from now on), and the dismissals not yet written to the policy."""
    excluded: set[str] = set()
    rejects: list[dict] = []
    for key, n in notes.items():
        parsed = parse_key(key)
        if not parsed or parsed[2] or n.get("action") not in DISMISSED:
            continue
        off = offset_of(parsed[1], n["scheduled_for"])
        if off is None:
            continue
        arm = arm_key(parsed[0], off)
        excluded.add(arm)
        if n["action"] == "dismissed":
            rejects.append({"key": key, "arm": arm})
    return excluded, rejects


def plan(slots: list[dict], logs: dict[tuple, tuple], notes: dict[str, dict], tries: dict[str, int], delays: dict[str, list[float]],
         have_keys: set[str], now: datetime, rank: Callable[[str, list[str]], list[str]], max_new: int = 99) -> dict[str, list]:
    """What to create and record now. logs: {(schedule id, dose time): (status, taken_at)}; notes: {reminder key: {id, scheduled_for,
    acted_at, action}}; tries: {arm: count}; delays: {medication id: usable delays}. Returns rows (drafts), tried (arms),
    acts (reminders whose dose was taken in the window) and rejects (dismissals to record). Writes nothing."""
    excluded, rejects = _dismissed(notes)
    tries = dict(tries)
    rows: list[dict] = []
    tried: list[str] = []
    acts: list[dict] = []
    for slot in sorted(slots, key=lambda s: s["at"]):
        mid, sid, at = slot["mid"], slot["sid"], slot["at"]
        key = dose_key(mid, at)
        status, taken_at = logs.get((sid, at), (None, None))
        note = notes.get(key)
        if note is not None:
            if note.get("acted_at") is None and status == "taken" and is_success(note["scheduled_for"], taken_at, at):
                off = offset_of(at, note["scheduled_for"])
                if off is not None:
                    acts.append({"key": key, "arm": arm_key(mid, off)})
                continue
            if note.get("acted_at") is not None:
                continue
        if not in_window(at, now) or not is_open(status) or len(rows) >= max_new:
            continue
        if note is None:
            if key in have_keys:
                continue
            off = choose_offset(mid, delays.get(mid, []), excluded, tries, lambda keys: rank(key, keys))
            if off is None or now < at + timedelta(minutes=off):
                continue
            arm = arm_key(mid, off)
            rows.append(_draft(slot, key, False, arm))
            tried.append(arm)
            tries[arm] = tries.get(arm, 0) + 1
        else:
            rkey = dose_key(mid, at, renudge=True)
            if rkey in have_keys or rkey in notes or not renudge_due(note["scheduled_for"], at, now):
                continue
            rows.append(_draft(slot, rkey, True, None))
    return {"rows": rows, "tried": tried, "acts": acts, "rejects": rejects}


# ───────────────────────────────────────────────────────────────── the database (reads here, writes only in nudges/run)
def _seed(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:12], 16)


def _ranker(user_id) -> Callable[[str, list[str]], list[str]]:
    """The policy's own ranking (15% exploring), seeded per slot so one dose's choice does not change from one tick to the next."""
    def rank(seed: str, keys: list[str]) -> list[str]:
        return nutritionstore.rank_arms(user_id, ARM_KIND, keys, random.Random(_seed(seed)))
    return rank


def _gather(c, user_id, now: datetime) -> dict[str, Any]:
    """Read-only: the medicines, the dose slots for yesterday and today, the log, the reminder rows, the policy and the history."""
    today = now.astimezone(TZ).date()
    days = [today - timedelta(days=1), today]
    sched = c.execute(
        "select s.id sid, s.medication_id mid, s.dose_time, s.created_at, s.meal_relation::text meal, m.name, m.strength, m.description directions, m.end_date "
        "from medication_schedule s join medications m on m.id = s.medication_id "
        "where s.user_id = %s and s.deleted_at is null and m.deleted_at is null and s.dose_time is not null "
        "and m.as_needed is not true and (m.end_date is null or m.end_date >= %s)", (user_id, days[0])).fetchall()
    logs = c.execute(
        "select schedule_id sid, scheduled_at sched_at, status::text st, taken_at from medication_log "
        "where user_id = %s and schedule_id is not null and scheduled_at >= %s and scheduled_at < %s",
        (user_id, local_at(days[0], time(0)), local_at(today + timedelta(days=1), time(0)))).fetchall()
    notes = c.execute(
        "select id, payload->>'key' k, scheduled_for, acted_at, action from notifications "
        "where user_id = %s and payload->>'key' like 'dose-%%' and scheduled_for > %s", (user_id, now - NOTE_LOOKBACK)).fetchall()
    tries = c.execute("select arm_key k, tries from nudge_policy where user_id = %s and arm_kind = %s", (user_id, ARM_KIND)).fetchall()
    hist = c.execute(
        "select medication_id mid, scheduled_at, taken_at from medication_log where user_id = %s and schedule_id is not null "
        "and status = 'taken' and taken_at is not null and taken_at > scheduled_at and scheduled_at > %s order by scheduled_at desc",
        (user_id, now - timedelta(days=HISTORY_DAYS))).fetchall()
    schedules = [{**r, "sid": str(r["sid"]), "mid": str(r["mid"])} for r in sched]
    pairs: dict[str, list[tuple]] = {}
    for r in hist:
        pairs.setdefault(str(r["mid"]), []).append((r["scheduled_at"], r["taken_at"]))
    meds: dict[str, dict] = {}
    for s in schedules:
        m = meds.setdefault(s["mid"], {"name": s["name"], "strength": s["strength"], "times": set()})
        m["times"].add(s["dose_time"])
    return {
        "meds": meds,
        "slots": make_slots(schedules, days),
        "logs": {(str(r["sid"]), r["sched_at"]): (r["st"], r["taken_at"]) for r in logs},
        "notes": {r["k"]: {"id": r["id"], "scheduled_for": r["scheduled_for"], "acted_at": r["acted_at"], "action": r["action"]} for r in notes if r["k"]},
        "tries": {r["k"]: r["tries"] for r in tries},
        "delays": {mid: usable_delays(p) for mid, p in pairs.items()},
    }


def _check_guard(user_id) -> Callable[[str, str], bool]:
    return lambda text, rule: nutritionstore.guarded(user_id, text, rule)


def _check_dry(text: str, rule: str) -> bool:
    """The same guard questions, without writing the guard log (for a read-only preview)."""
    return not jev.guard_blocks(text)[0]


def nudges(user_id, now: datetime, have_keys: set[str], max_new: int) -> list[tuple[str, str, str, str, str, datetime]]:
    """Dose reminder rows that are not stored yet: (key, kind, title, body, route, valid until). Also records the offset tried for each
    new reminder, the outcome of reminders whose dose was taken in the window, and dismissals (once each)."""
    if max_new <= 0:
        return []
    with tx() as c:
        g = _gather(c, user_id, now)
    res = plan(g["slots"], g["logs"], g["notes"], g["tries"], g["delays"], have_keys, now, _ranker(user_id), max_new)
    lang = texts.person_language(user_id)
    out = []
    for d in res["rows"]:
        row = _vet(d, _check_guard(user_id), lang)
        if row is None:
            continue
        out.append(row)
        if d["arm"]:
            nutritionstore.policy_try(user_id, ARM_KIND, d["arm"])
            audit(user_id, "agent", "dose.reminder_offered", None, None, {"key": d["key"], "offset": arm_offset(d["arm"])})
    for a in res["acts"]:
        with tx() as c:
            got = c.execute(
                "update notifications set acted_at = now(), action = 'taken' where user_id = %s and acted_at is null "
                "and payload->>'key' in (%s, %s) returning payload->>'key' k",
                (user_id, a["key"], a["key"] + RENUDGE_SUFFIX)).fetchall()
        if any(r["k"] == a["key"] for r in got):
            nutritionstore.policy_act(user_id, ARM_KIND, a["arm"])
            audit(user_id, "user", "dose.taken_after_reminder", None, None, {"key": a["key"], "offset": arm_offset(a["arm"])})
    for r in res["rejects"]:
        with tx() as c:
            got = c.execute(
                "update notifications set action = 'dismissed_learned' where user_id = %s and action = 'dismissed' and payload->>'key' = %s returning id",
                (user_id, r["key"])).fetchall()
        if got:
            nutritionstore.policy_reject(user_id, ARM_KIND, r["arm"])
    return out


def preview(user_id, now: datetime, have_keys: set[str], max_new: int = 99) -> dict[str, Any]:
    """Read only: what nudges() would return and record, with no writes and no guard log. Same code path as nudges()."""
    with tx() as c:
        g = _gather(c, user_id, now)
    res = plan(g["slots"], g["logs"], g["notes"], g["tries"], g["delays"], have_keys, now, _ranker(user_id), max_new)
    lang = texts.person_language(user_id)
    rows = [r for r in (_vet(d, _check_dry, lang) for d in res["rows"]) if r is not None]
    return {"rows": rows, "tried": res["tried"], "acts": res["acts"], "rejects": res["rejects"]}


def run(user_id, write: bool = False) -> dict[str, Any]:
    """The nightly step. For each medicine: the offset the next reminder would use, and (from 14 usable delays) ONE proposed memory
    fact with the usual delay. With write=False nothing is written and the guard log is not touched."""
    from app.agents.adherence import _propose_fact

    now = datetime.now(TZ)
    with tx() as c:
        g = _gather(c, user_id, now)
    if not g["meds"]:
        return {"skipped": "no scheduled medicines"}
    rank = _ranker(user_id)
    excluded, _ = _dismissed(g["notes"])
    today = now.astimezone(TZ).date().isoformat()
    out: dict[str, Any] = {"medicines": len(g["meds"]), "history": {}, "usual_delay_min": {}, "offsets": {}, "facts": []}
    lang = texts.person_language(user_id)
    for mid, meta in g["meds"].items():
        delays = g["delays"].get(mid, [])
        out["history"][mid] = len(delays)
        off = choose_offset(mid, delays, excluded, g["tries"], lambda keys: rank(f"offset:{mid}:{today}", keys))
        out["offsets"][mid] = off
        if off is None or not has_fact_history(delays):
            continue
        usual = usual_rounded(statistics.median(delays))
        out["usual_delay_min"][mid] = usual
        name, period = short_name(meta["name"], meta["strength"]), period_for(meta["times"])
        text_en = fact_text(name, period, usual, off)
        text = fact_text(name, period, usual, off, lang)     # the statement the person sees; the guard reads text_en
        ok = nutritionstore.guarded(user_id, text_en, f"dose_timing_fact:{mid}") if write else _check_dry(text_en, "dose_timing_fact")
        key = f"routine.dose_timing.{mid}"
        entry = {"key": key, "guard": "pass" if ok else "blocked", "result": "dry_run"}
        if ok and write:
            conf = min(0.9, 0.4 + len(delays) / 100)
            with tx() as c:
                entry["result"] = _propose_fact(c, user_id, key, "routine", {"medication_id": mid, "usual_delay_min": usual}, text, conf,
                                                [{"table": "medication_log", "medication_id": mid, "n": len(delays)}])
            if entry["result"] in ("proposed", "superseded_and_proposed"):
                audit(user_id, "agent", "memory.fact_proposed", "memory_facts", None, {"key": key, "result": entry["result"]})
        out["facts"].append(entry)
    return out
