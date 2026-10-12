"""Ask Smart Health (screen I1): a chat that answers only from the signed-in person's own data.

What it does, in this order, for every message:
  1. trims and limits the text; 2. a rule check for urgent words (no model is called when it matches); 3. the frozen JEV guard on the
  message (a medicine, diagnosis or urgent question gets a fixed reply, never a model answer); 4. routes the message (JEV choice) and
  builds a context from this person's own rows; 5. asks the model to answer only from that context; 6. runs the guard on the reply.
Every step that fails (model, JEV, daily cap, no data) ends in a calm fixed reply. The reply is never advice on a dose or a medicine, a
diagnosis, or a verdict such as "normal". Names, NRIC numbers, phones and emails are scrubbed before anything leaves this process.

What it will not do: write to the person's health record, remember a chat as a memory fact, or keep more than the last 8 messages
as context. Thresholds here are placeholders pending clinical review.
"""
from __future__ import annotations

import logging
import re
import threading
import uuid
from collections import OrderedDict
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from app.agents.orchestrator import SKILLS
from app.agents.trace import Run
from app.core.config import settings
from app.core.errors import ValidationFailed
from app.db import logstore
from app.db.logstore import TZ, tx
from app.llm import chat as chat_llm
from app.llm import jev
from app.llm.gateway import LLMUnavailable
from app.schemas.chat import MAX_TEXT
from app.agents import chat_assistant as AI
from app.db import nutritionstore
from app.services import blood_pressure, care, clash_store, insights, texts, usage
from app.services import chat_guard as G
from app.services import chat_planner as P

logger = logging.getLogger(__name__)

HISTORY_N = 8             # messages kept as context for the model, never older ones
ROUTE_FLOOR = 0.6         # below this JEV confidence the message goes to the general path (same as the orchestrator)
DIAGNOSIS_REFUSE_P = 0.6  # a message is refused as a diagnosis request only when JEV scores it this high (the reply guard stays at 1 - jev_guard_floor)
URGENT_P = 0.5            # JEV says an urgent symptom is this likely: treat it as urgent
CONTEXT_DAYS = 14
STARTER_CGM_DAYS = 5      # days with glucose in the last 7 that count as "a CGM week"
MAX_STARTERS = 4
MAX_REPLY_WORDS = 130     # the prompt asks for under 120; a longer reply is cut at a sentence end
MAX_PASSAGES = 3
# the extra views the planner picks (see chat_planner.py): every view is capped so the context stays small
MAX_VIEW_LINES = 14       # lines kept per extra view (a weekly history of 90 days is 13 weekly lines plus one heading)
MAX_VIEW_CHARS = 3000     # characters kept across ALL extra views together; later lines are dropped first
LATE_DINNER_HOUR = 21     # a dinner logged at 9 pm or later counts as a late dinner in the responses view
EMBED_DIM = 768           # gemini-embedding-001 at 768 dimensions (decision D-048), the size of knowledge_chunks.embedding
EMBED_MODEL = "gemini-embedding-001"
EMBED_CACHE_SIZE = 128    # questions whose embedding is remembered in this process, so a repeated question costs nothing
MAX_VECTOR_DISTANCE = 0.6 # cosine distance above which a guidance chunk is not close enough to quote (placeholder until there is content to tune it on)

URGENT_TEXT = texts.tr("en", "chat.urgent")       # the English source; other languages come from texts.tr(lang, key)
REFUSED_TEXT = texts.tr("en", "chat.refused")
CAUTION_TEXT = texts.tr("en", "chat.caution")
UNAVAILABLE_TEXT = texts.tr("en", "chat.unavailable")
GUARD_DOWN_TEXT = texts.tr("en", "chat.guard_down")
BLOCKED_REPLY_TEXT = texts.tr("en", "chat.blocked_reply")
EMPTY_TEXT = texts.tr("en", "chat.empty")
HELP_TEXT = texts.tr("en", "chat.help")
_KIND_BY_KEY = {"chat.urgent": "urgent", "chat.refused": "refused", "chat.caution": "refused", "chat.blocked_reply": "refused",
                "chat.unavailable": "unavailable", "chat.guard_down": "unavailable", "chat.empty": "empty", "chat.help": "help"}
KIND_OF = {texts.tr(lang, key): kind for key, kind in _KIND_BY_KEY.items() for lang in texts.LANGS}   # the stored kind of a fixed reply, in any language

# ----------------------------------------------------------------------------- the urgent rule (runs before any model or JEV call)
_URGENT = [re.compile(p, re.I) for p in (
    r"\bchest (pain|pains|tight|tightness|pressure)\b", r"\bpain in (my|the) chest\b", r"\b(can ?not|can't|cannot|unable to) breathe\b",
    r"\b(trouble|difficulty|hard to) breathing\b", r"\bshort of breath\b", r"\bfaint(ed|ing)\b", r"\bpass(ed|ing) out\b", r"\bcollaps(e|ed|ing)\b",
    r"\bunconscious\b", r"\bseizure|\bconvuls", r"\bsuicid", r"\b(kill|hurt|harm) myself\b", r"\bend my life\b", r"\bwant to die\b",
    r"\boverdos", r"\bslurred speech\b", r"\bface (is )?droop", r"\b(very|extremely|dangerously) low (blood )?(sugar|glucose)\b",
    r"\b(sugar|glucose) (is |was )?(very|extremely|dangerously) low\b", r"\bsevere hypo",
    # more English wording (the rules are the safety floor when JEV is off or does not score a phrase)
    r"\b(having|getting|feels? like|feel like|looks? like|think (i|he|she|it)'?s?|think (i am|i'm))\b[^.?!]{0,20}\b(a |an )?heart attack\b", r"\bis (this|it|that) (a |an )?(heart attack|stroke)\b",
    r"\b(having|think[\w' ]{0,12}) (a |an )?stroke\b",
    r"\bchest (hurts?|aches?|aching|discomfort|pains?|is (tight|heavy|hurting|painful|squeezing)|feels? (tight|heavy|squeezed|crushed|funny))\b", r"\b(tightness|pressure|heaviness|discomfort|squeezing|crushing) (in|on|around|across) (my |the )?chest\b",
    r"\bpain (in|around|across|down) (my |the )?(left |right )?(chest|arm|jaw)\b", r"\b(left|both) arms?\b[^.?!]{0,15}\b(numb\w*|tingl\w*|heavy|weak\w*|hurts?|pain\w*)\b",
    r"\b(numb|numbness|tingling)\b[^.?!]{0,20}\b(left arm|jaw|one side)\b",
    r"\b(can ?not|can't|cant|unable to|struggling to|hard to|difficult to|difficulty|trouble) (to )?(breathe|breathing|catch my breath|get (any )?air)\b", r"\bshortness of breath\b|\bbreathless\b|\bgasping\b",
    r"\bspeech is slurred\b|\bslurring (my )?(words|speech)\b", r"\bsudden(ly)?\b[^.?!]{0,25}\b(weak\w*|numb\w*|confus\w*|can'?t see|lost (my )?vision|trouble (seeing|speaking|walking))\b",
    r"\b(one side of|half of) (my )?(face|body)\b", r"\bhaving a fit\b", r"\b(not|isn't|is not) (breathing|waking up)\b|\bunresponsive\b|\bblack(ed)? out\b",
    r"\b(severe|severely|critically) low\b[^.?!]{0,15}\b(sugar|glucose)\b|\b(sugar|glucose)\b[^.?!]{0,15}\b(severely|critically) low\b",
    r"\b(took|taken|swallowed|had) (too many|too much|an extra|a lot of)\b[^.?!]{0,25}\b(tablets?|pills?|insulin|medic\w*|capsules?|doses?)\b",
)]
_CONFUSED = re.compile(r"\b(confused|confusion|disoriented)\b", re.I)
_LOW_WORDS = re.compile(r"\b(low|sugar|glucose|hypo|sweat\w*|shak\w+|dizzy)\b", re.I)
_HELP = re.compile(r"^\W*(what can you (help|do)( me)?( with)?|how (can|do) you help|what do you do|help)\W*$", re.I)


def clean_text(text: str) -> str:
    """Trim, collapse whitespace and limit the length."""
    return re.sub(r"\s+", " ", (text or "").replace("’", "'")).strip()[:MAX_TEXT]


def is_urgent_text(text: str) -> bool:
    t = clean_text(text)
    return (any(p.search(t) for p in _URGENT) or bool(_CONFUSED.search(t) and _LOW_WORDS.search(t)) or G.low_reading_with_symptoms(t)
            or G.low_sugar_with_symptoms(t))


def is_help_request(text: str) -> bool:
    return bool(_HELP.match(clean_text(text)))


# ----------------------------------------------------------------------------- scrubbing
_TITLES = {"mr", "mrs", "mdm", "ms", "miss", "dr", "madam", "sir", "the", "and", "bin", "binte", "s/o", "d/o"}


def name_tokens(*names: str | None) -> list[str]:
    """Words of the person's and their contact's names that must never reach the model (titles and short words are left out)."""
    out: list[str] = []
    for n in names:
        for w in re.split(r"[\s,]+", n or ""):
            w = w.strip(".")
            if len(w) >= 3 and w.lower() not in _TITLES and w.lower() not in (x.lower() for x in out):
                out.append(w)
    return out


def scrub(text: str, names: list[str] | None = None) -> str:
    """NRIC, phone and email are replaced by jev.deidentify; the person's own names become 'the person'."""
    t = "\n".join(jev.deidentify(line) for line in (text or "").split("\n"))
    for w in names or []:
        t = re.sub(rf"(?<![\w]){re.escape(w)}(?![\w])", "the person", t, flags=re.I)
    return t


def verdict_for(res: dict[str, float | None]) -> str:
    """The guardrail_events verdict for a guard result (same mapping as nutritionstore.guarded)."""
    cut = 1 - settings.jev_guard_floor
    if not any(v is None or v >= cut for v in res.values()):
        return "pass"
    if res.get("med_advice") is None or (res.get("med_advice") or 0) >= cut:
        return "blocked_med_advice"
    if (res.get("diagnosis") or 0) >= cut:
        return "blocked_diagnosis"
    if (res.get("urgent") or 0) >= cut:
        return "urgent"
    return "blocked_other"


def classify_message(res: dict[str, float | None], reply: bool = False) -> str:
    """What to do with a guard result: down, urgent, refuse, caution or ok. Conservative at every edge.
    On the person's MESSAGE the diagnosis score has its own, less strict line (DIAGNOSIS_REFUSE_P): JEV scores an ordinary blood pressure
    question about 0.4 for it, and real diagnosis questions are refused by our own word rules before this. On a REPLY (reply=True) every
    score uses the strict line."""
    cut = 1 - settings.jev_guard_floor
    if (res.get("urgent") or 0) >= URGENT_P:
        return "urgent"
    if (res.get("med_advice") or 0) >= cut or (res.get("diagnosis") or 0) >= (cut if reply else max(cut, DIAGNOSIS_REFUSE_P)):
        return "refuse"
    if (res.get("urgent") or 0) >= cut:
        return "caution"
    if any(v is None for v in res.values()):
        return "down"                 # nothing it did answer was a problem, and some answers are missing
    return "ok"


def tidy(reply: str) -> str:
    """Plain text only, and not longer than MAX_REPLY_WORDS (cut at the last full sentence)."""
    t = re.sub(r"[*_`#>]+", "", reply or "")
    t = re.sub(r"[ \t]+", " ", t).strip()
    words = t.split()
    if len(words) <= MAX_REPLY_WORDS:
        return t
    cut = " ".join(words[:MAX_REPLY_WORDS])
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    return (cut[: end + 1] if end > 40 else cut.rstrip(",;:") + ".").strip()


# ----------------------------------------------------------------------------- the context
@dataclass
class Section:
    key: str
    label: str            # shown as a source chip
    to: str               # route id
    lines: list[str]
    detail: str | None = None


@dataclass
class Context:
    sections: list[Section] = field(default_factory=list)
    passages: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    today: date | None = None
    latest: date | None = None

    def empty(self) -> bool:
        return not any(s.lines for s in self.sections) and not self.passages

    def only(self, keys: set[str] | None) -> "Context":
        return self if keys is None else Context([s for s in self.sections if s.key in keys], self.passages, self.names, self.today, self.latest)

    def text(self) -> str:
        head = [f"Today is {self.today:%d %b %Y}." if self.today else "", f"The latest day with data is {self.latest:%d %b %Y}." if self.latest else ""]
        body = [f"{s.label.upper()}\n" + "\n".join(f"- {x}" for x in s.lines) for s in self.sections if s.lines]
        if self.passages:
            body.append("GENERAL INFORMATION (quoted reference text with its source in brackets; general reading, NOT about this person)\n" +"\n".join(f"- {p}" for p in self.passages))
        return scrub("\n\n".join([" ".join(h for h in head if h), *body]), self.names)


# which sections each routed skill sees; None (general path) sees everything
ROUTE_SECTIONS: dict[str, set[str] | None] = {
    "adherence": {"meds", "doses", "facts", "questions"}, "nutrition": {"food", "glucose", "facts"}, "activity": {"activity", "sleep", "glucose", "facts"},
    "preventive": {"questions", "facts", "meds"}, "unrouted": None,
}
# what each kind of question may see (None = everything). A symptom question never sees the food list, a food question never sees symptoms.
INTENT_SECTIONS: dict[str, set[str] | None] = {
    "data_summary": None, "insights": None,
    "diet": {"food", "glucose", "facts", "food_ideas", "activity"}, "food_ideas": {"food", "glucose", "facts", "food_ideas"},
    "symptoms": {"symptoms", "glucose", "doses", "meds", "blood_pressure", "questions", "sleep"},
    "medicine_info": {"meds", "doses", "questions", "medicine_alerts"}, "appointments": {"questions", "appointments", "meds"},
}
KEYWORDS: dict[str, tuple[str, ...]] = {
    "glucose": ("glucose", "sugar", "cgm", "range", "spike", "high", "low", "mmol", "reading"),
    "food": ("meal", "food", "eat", "ate", "carb", "salt", "sodium", "lunch", "dinner", "breakfast", "snack", "dish"),
    "activity": ("walk", "exercise", "workout", "step", "active", "gym", "run", "move"),
    "sleep": ("sleep", "tired", "rest", "bed"),
    "meds": ("medicine", "tablet", "pill", "capsule", "drug", "supplement"),
    "doses": ("dose", "missed", "taken", "tablet", "pill", "on time"),
    "questions": ("doctor", "appointment", "ask"),
    "facts": ("routine", "habit", "learned", "know about me", "noticed"),
    "symptoms": ("symptom", "feel", "dizz", "nausea", "pain", "tired", "thirst", "tingling", "blurred", "headache", "sweat", "shak"),
    "blood_pressure": ("blood pressure", " bp", "pulse"),
    "appointments": ("appointment", "visit", "clinic", "check-up", "checkup"),
    "medicine_alerts": ("interact", "clash", "together", "combine"),
    "food_ideas": ("suggest", "idea", "what to eat", "lighter", "swap", "instead"),
    # the extra views ("flu" alone is not a keyword: it would match inside "influence")
    "labs": ("hba1c", "a1c", "lab ", "lab result", "blood test", "test result", "cholesterol", "ldl", "hdl", "triglycerid", "insulin", "glycated"),
    "profile": ("allerg", "condition", "diagnosed", "my history", "profile", "polyclinic", "healthier sg", "who looks after", "how long have i"),
    "baseline": ("usual", "typical", "normally", "baseline", "compared", "than before", "drift"),
    "preventive": ("eye screen", "eye check", "eye test", "eye exam", "retina", "foot screen", "foot check", "foot exam", "kidney", "flu shot", "flu jab", "influenza", "vaccin", "screening", "preventive", "check-up", "checkup"),
    "responses": ("after ", "spike", "affect", "response", "respond", "pattern", "late dinner", "impact", "what works"),
    "longer_history": ("month", "trend", "since", "improv", "compared", "history", "over time", "weekly", "30 days", "60 days", "90 days", "better", "worse"),
}


def pick_sources(sent: list[Section], question: str, reply: str, med_names: list[str]) -> list[Section]:
    """The screens behind the answer: the sections that were sent, have data, and are mentioned in the question or the reply."""
    both, asked = f"{question} {reply}".lower(), question.lower()
    out = []
    for s in sent:
        hay = asked if s.key in ("questions", "facts") else both   # "ask your doctor" in a reply is not a source
        if not s.lines:
            continue
        words = list(KEYWORDS.get(s.key, ()))
        if s.key == "meds":
            words += [m.lower() for m in med_names]
        if any(w in hay for w in words):
            out.append(s)
    return out[:3]


def _short(d: date) -> str:
    return f"{d.day} {d:%b}"


def _num(x: Any, digits: int = 1) -> str:
    return "none" if x is None else f"{float(x):.{digits}f}"


def build_sections(rows: dict[str, Any], today: date) -> Context:
    """Pure: turns the loaded rows into sections of short lines with the person's own numbers. Missing values are left out, never zero."""
    daily: list[dict[str, Any]] = rows["daily"]
    secs: list[Section] = []
    span = f"last {CONTEXT_DAYS} days to {_short(rows['anchor'])}" if rows.get("anchor") else None

    g = [d for d in daily if d["glucose_mean_mmol"] is not None]
    lines = [f"{_short(d['local_date'])}: mean {_num(d['glucose_mean_mmol'])} mmol/L, in range {_num(d['tir_pct'], 0)}%, below range {_num(d['tbr_pct'], 0)}%, above range {_num(d['tar_pct'], 0)}%" for d in g]
    if g:
        lines.insert(0, f"{len(g)} day{'s' if len(g) != 1 else ''} with glucose readings out of {CONTEXT_DAYS}; average of daily means {_num(sum(float(d['glucose_mean_mmol']) for d in g) / len(g))} mmol/L")
    secs.append(Section("glucose", "Your glucose", "C2", lines, span))

    sched = sum(d["doses_scheduled"] or 0 for d in daily)
    taken = sum(d["doses_taken"] or 0 for d in daily)
    missed = sum(d["doses_missed"] or 0 for d in daily)
    secs.append(Section("doses", "Your doses", "C6", [f"{sched} dose{'s' if sched != 1 else ''} planned, {taken} taken, {missed} marked missed"] if sched else [], span))

    meds = []
    for m in rows["meds"]:
        bits = [m["name"]]
        times = [t for t in (m.get("times") or []) if t]
        if times:
            bits.append("times " + ", ".join(times))
        elif m.get("as_needed"):
            bits.append("only when needed")
        if m.get("purpose"):
            bits.append("what it is for: " + m["purpose"])
        meds.append("; ".join(bits))
    secs.append(Section("meds", "Your medicines", "H1", meds))

    meal_days = [d for d in daily if d["meals_n"]]
    food = []
    if meal_days:
        n_meals = sum(int(d['meals_n']) for d in meal_days)
        food.append(f"{n_meals} meal{'s' if n_meals != 1 else ''} logged on {len(meal_days)} of the last {CONTEXT_DAYS} days")
    for m in rows["meals"]:
        known = [f"carbs {_num(m['carbs_g'], 0)} g"] if m["carbs_g"] is not None else []
        known += [f"sodium {_num(m['sodium_mg'], 0)} mg"] if m["sodium_mg"] is not None else []     # an unknown value is left out, never written as none or 0
        food.append(f"{_short(m['day'])} {m['meal_type'] or 'meal'}: {m['food']}" + (f" ({', '.join(known)})" if known else ""))
    secs.append(Section("food", "Your meals", "C3", food, span))

    act = []
    ex = [d for d in daily if d["exercise_min"]]
    if ex:
        act.append(f"{sum(int(d['exercise_min']) for d in ex)} exercise minutes on {len(ex)} of the last {CONTEXT_DAYS} days")
    st = [int(d["steps_total"]) for d in daily if d["steps_total"] is not None]
    if st:
        act.append(f"average {round(sum(st) / len(st))} steps a day on {len(st)} day{'s' if len(st) != 1 else ''} with step data")
    for w in rows["workouts"]:
        act.append(f"{_short(w['day'])}: {w['type']}, {w['minutes']} minutes")
    secs.append(Section("activity", "Your activity", "C4", act, span))

    sl = [float(d["sleep_hours"]) for d in daily if d["sleep_hours"] is not None]
    secs.append(Section("sleep", "Your sleep", "C5", [f"average {_num(sum(sl) / len(sl))} hours a night on {len(sl)} night{'s' if len(sl) != 1 else ''}"] if sl else [], span))

    secs.append(Section("questions", "Your doctor questions", "K3", [q for q in rows["questions"]]))
    secs.append(Section("facts", "What Smart Health has learned", "K2", [f for f in rows["facts"]]))

    sym: list[str] = []
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for r in rows.get("symptoms", []):
        by_kind.setdefault(str(r["kind"]).replace("_", " "), []).append(r)
    if by_kind:
        sym.append(f"{sum(len(v) for v in by_kind.values())} symptom entries in the last 30 days")
    for kind, items in by_kind.items():
        last = items[0]
        bits = [f"{kind}: {len(items)} time{'s' if len(items) != 1 else ''}, latest {_short(last['day'])}"]
        if last.get("severity") is not None:
            bits.append(f"strength {last['severity']} of 5")
        if last.get("duration_min"):
            bits.append(f"about {last['duration_min']} minutes")
        if "glucose_near" in last:                     # only the latest entries were looked up; an entry not looked up says nothing either way
            bits.append(f"sensor glucose near it {_num(last['glucose_near'])} mmol/L" if last["glucose_near"] is not None else "no sensor reading within 30 minutes of it")
        sym.append(", ".join(bits))
    secs.append(Section("symptoms", "Your symptoms", "D1", sym, "last 30 days"))

    bpl: list[str] = []
    bp = rows.get("bp", [])
    if bp:
        top, bottom = [int(b["systolic"]) for b in bp], [int(b["diastolic"]) for b in bp]
        latest = bp[0]
        bpl.append(f"{len(bp)} blood pressure readings in the last 30 days; the top numbers ran from {min(top)} to {max(top)} and the bottom numbers from {min(bottom)} to {max(bottom)} mmHg")
        bpl.append(f"latest {_short(latest['measured_at'].astimezone(TZ).date())}: {latest['systolic']} over {latest['diastolic']} mmHg" + (f", pulse {latest['pulse']}" if latest.get("pulse") else ""))
    secs.append(Section("blood_pressure", "Your blood pressure", "C5", bpl, "last 30 days"))

    secs.append(Section("medicine_alerts", "Medicine alerts from Smart Health", "H5", list(rows.get("alerts", []))))

    visit = rows.get("visit")
    secs.append(Section("appointments", "Your next visit", "K3",
                        [f"{visit['kind_label']}: {visit['scheduled_label']}"] if visit and visit.get("scheduled_label") else []))

    for sec in secs:                                    # what the person typed, or a label said, is data: instruction-like lines are dropped
        sec.lines = [x for x in (G.sanitize_data_line(l) for l in sec.lines) if x]
    passages_ = [x for x in (G.sanitize_data_line(p_, 400) for p_ in rows.get("passages", [])) if x]
    return Context(secs, passages_, name_tokens(*rows.get("names", [])), today, rows.get("anchor"))


# ----------------------------------------------------------------------------- reading the rows
def _strength_free(name: str) -> str:
    return re.sub(r"\s+\d[\d.,]*\s*(mg|mcg|g|ml|iu|units?)?\b.*$", "", name, flags=re.I).strip() or name


def load_rows(conn, uid: str, today: date, text: str) -> dict[str, Any]:
    anchor = insights.anchor(conn, uid, today)
    lo = anchor - timedelta(days=CONTEXT_DAYS - 1)
    daily = [dict(r) for r in conn.execute(
        """select local_date, glucose_mean_mmol, tir_pct, tbr_pct, tar_pct, steps_total, sleep_hours, meals_n, exercise_min, doses_scheduled, doses_taken, doses_missed
           from daily_summary where user_id=%s and local_date between %s and %s order by local_date""", (uid, lo, anchor))]
    p = conn.execute("select display_name, emergency_contact_name from user_profile where user_id=%s", (uid,)).fetchone()
    meds = [dict(r) for r in conn.execute(
        """select m.id, m.name, m.description, m.as_needed, e.purpose,
                  (select array_agg(to_char(s.dose_time, 'HH24:MI') order by s.dose_time) from medication_schedule s where s.medication_id=m.id and s.deleted_at is null) times
           from medications m left join medication_explanations e on e.medication_id=m.id and e.status='ready'
           where m.user_id=%s and m.deleted_at is null and (m.end_date is null or m.end_date >= %s) order by m.created_at""", (uid, today))]
    meals = [dict(r) for r in conn.execute(
        """select (start_at at time zone 'Asia/Singapore')::date as day, meal_type::text meal_type, food, carbs_g, sodium_mg from food_logs
           where user_id=%s and deleted_at is null order by start_at desc limit 5""", (uid,))]
    workouts = [dict(r) for r in conn.execute(
        """select (start_at at time zone 'Asia/Singapore')::date as day, type::text type, round(extract(epoch from (end_at - start_at)) / 60)::int minutes from exercise_logs
           where user_id=%s and deleted_at is null and end_at is not null order by start_at desc limit 5""", (uid,))]
    questions = [r["text"] for r in conn.execute("select text from doctor_questions where user_id=%s and status='open' order by created_at desc limit 5", (uid,))]
    facts = [r["statement"] or r["key"] for r in conn.execute("select statement, key from memory_facts where user_id=%s and status='active' order by confidence desc limit 12", (uid,))]
    symptoms = [dict(r) for r in conn.execute(
        """select (occurred_at at time zone 'Asia/Singapore')::date as day, occurred_at as at, symptom_type::text kind, severity, duration_min from symptom_logs
           where user_id=%s and deleted_at is null and occurred_at > now() - interval '30 days' order by occurred_at desc limit 20""", (uid,))]
    for sy in symptoms[:6]:                            # the sensor reading nearest each recent symptom (within 30 minutes), or none
        try:
            near = conn.execute(
                """select glucose_mmol from cgm_readings
                   where user_id = %s and quality_ok and recorded_at between %s::timestamptz - interval '30 minutes' and %s::timestamptz + interval '30 minutes'
                   order by abs(extract(epoch from recorded_at - %s::timestamptz)) limit 1""", (uid, sy["at"], sy["at"], sy["at"])).fetchone()
        except Exception:
            logger.exception("sensor reading near a symptom not readable for the chat")
            near = None
        sy["glucose_near"] = float(near["glucose_mmol"]) if near and near["glucose_mmol"] is not None else None
    try:
        bp = blood_pressure.recent_bp(conn, uid, 30)
    except Exception:
        logger.exception("blood pressure not readable for the chat")
        bp = []
    try:
        visit = care.next_appointment(conn, uid, datetime.now(TZ))
    except Exception:
        logger.exception("next visit not readable for the chat")
        visit = None
    try:                                               # the medicine clash alerts the app raised (clash_store reads tuple rows)
        from psycopg.rows import tuple_row
        before = conn.row_factory
        conn.row_factory = tuple_row
        try:
            alerts = [a["text"] for a in clash_store.list_open(conn, uid)][:5]
        finally:
            conn.row_factory = before
    except Exception:
        logger.exception("medicine alerts not readable for the chat")
        alerts = []
    return {"daily": daily, "anchor": anchor if daily else None, "meds": meds, "meals": meals,
            "workouts": workouts, "questions": questions, "facts": facts, "names": [p["display_name"], p["emergency_contact_name"]] if p else [],
            "symptoms": symptoms, "bp": bp, "visit": visit, "alerts": alerts,
            "passages": passages(conn, text, name_tokens(*([p["display_name"], p["emergency_contact_name"]] if p else [])))}


# ----------------------------------------------------------------------------- the extra views the planner picks
LAB_NAMES = {"hba1c": "HbA1c", "fasting_glucose": "Fasting glucose (lab)", "fasting_insulin": "Fasting insulin"}
CARE_SETTING_TEXT = {"polyclinic": "a polyclinic", "gp": "a GP clinic", "hospital": "a hospital", "none": "no regular place of care"}
PREVENTIVE_NAMES = {"eye_screening": "Eye screening", "foot_screening": "Foot screening", "kidney_test": "Kidney test", "hba1c_test": "HbA1c test",
                    "vaccination": "Vaccination (flu and others)"}
VIEW_SECTIONS: dict[str, tuple[str, str, str]] = {      # key -> (label shown as a source chip, screen id, detail)
    "labs": ("Your lab results", "K1", "latest results on record"),
    "profile": ("Your profile", "K1", "from your sign-up answers"),
    "baseline": ("Your usual range", "C2", f"last {CONTEXT_DAYS} days against the {insights.BASELINE_DAYS} days before"),
    "preventive": ("Your preventive checks", "K3", "dates on record"),
    "responses": ("How you responded", "K2", "your own computed responses"),
    "longer_history": ("Your longer history", "C1", "weekly summaries"),
}


def _view_rows(conn, key: str, fn, default):
    """One view's rows. A failed view is logged and left out (its own savepoint keeps the rest of the transaction usable); the chat goes on."""
    try:
        with _savepoint(conn):
            return fn()
    except Exception:
        logger.exception("chat view %s not readable", key)
        return default


def late_dinner_stats(dinners: list[dict[str, Any]], fasting: dict[date, float], late_hour: int = LATE_DINNER_HOUR) -> dict[str, Any] | None:
    """Pure: the average morning (fasting) glucose the day after a dinner logged at late_hour or later, against the day after earlier dinners.
    None unless BOTH groups have at least insights.MIN_PATTERN_PAIRS mornings with a reading (the app's own minimum for a finding)."""
    late, other = [], []
    for d in dinners:
        g = fasting.get(d["day"] + timedelta(days=1))
        if g is None:
            continue
        (late if int(d["hour"]) >= late_hour else other).append(float(g))
    if len(late) < insights.MIN_PATTERN_PAIRS or len(other) < insights.MIN_PATTERN_PAIRS:
        return None
    return {"late_n": len(late), "late_avg": sum(late) / len(late), "other_n": len(other), "other_avg": sum(other) / len(other), "hour": late_hour}


def load_views(conn, uid: str, today: date, views: set[str] | frozenset[str], text: str = "") -> dict[str, Any]:
    """Read-only. The rows for the views the planner picked, over the connection the caller already holds (no new connection). A view that
    cannot be read is left out. Returns {} for no views."""
    out: dict[str, Any] = {}
    if not views:
        return out
    try:
        anchor = insights.anchor(conn, uid, today)
    except Exception:
        logger.exception("chat views: anchor not readable")
        return out
    out["anchor"] = anchor
    if "labs" in views:
        out["labs"] = _view_rows(conn, "labs", lambda: [dict(r) for r in conn.execute(
            """select test::text test, value, unit, measured_at from (
                   select test, value, unit, measured_at, row_number() over (partition by test order by measured_at desc) rn
                   from lab_results where user_id=%s and deleted_at is null) x
               where rn <= 2 order by test, measured_at desc""", (uid,)).fetchall()], [])
    if "profile" in views:
        def prof() -> dict[str, Any]:
            p = conn.execute("select diagnosed_year, care_setting, healthier_sg, allergies_note, conditions_note from user_profile where user_id=%s", (uid,)).fetchone()
            res = dict(p) if p else {}
            res["conditions"] = [r["name"] for r in conn.execute("select name from conditions where user_id=%s and deleted_at is null order by created_at limit 10", (uid,)).fetchall()]
            res["allergies"] = [dict(r) for r in conn.execute("select substance, reaction from allergies where user_id=%s and deleted_at is null order by created_at limit 10", (uid,)).fetchall()]
            return res
        out["profile"] = _view_rows(conn, "profile", prof, {})
    if "baseline" in views:
        def base() -> dict[str, Any]:
            start = anchor - timedelta(days=CONTEXT_DAYS - 1)
            fasting = insights._fasting(conn, uid, start - timedelta(days=insights.BASELINE_DAYS), anchor)          # the Insights definition: 05:00 to 07:00 local
            daily = insights._daily(conn, uid, start - timedelta(days=insights.BASELINE_DAYS), anchor)
            prior = [g for d, g in fasting.items() if d < start]
            weekly: list[float | None] = []
            for k in range(5, -1, -1):                      # six weeks of medians, oldest first, as Insights does for its drift line
                hi_d = anchor - timedelta(days=7 * k)
                w = [g for d, g in fasting.items() if hi_d - timedelta(days=6) <= d <= hi_d]
                weekly.append(insights._median(w) if len(w) >= 3 else None)
            p75 = insights._percentile(prior, 0.75) if len(prior) >= 7 else None
            return {"fasting_prior": prior, "fasting_recent": [g for d, g in fasting.items() if d >= start],
                    "steps_prior": [float(v["steps_total"]) for d, v in daily.items() if d < start and v.get("steps_total") is not None],
                    "steps_recent": [float(v["steps_total"]) for d, v in daily.items() if d >= start and v.get("steps_total") is not None],
                    "drift_weeks": insights.drift_weeks(weekly, p75) if p75 is not None else 0}
        out["baseline"] = _view_rows(conn, "baseline", base, {})
    if "preventive" in views:
        out["preventive"] = _view_rows(conn, "preventive", lambda: [dict(r) for r in conn.execute(
            """select i.kind::text kind, s.last_done_on, s.next_due_on from preventive_items i
               left join patient_preventive_status s on s.preventive_item_id = i.id and s.user_id = %s""", (uid,)).fetchall()], [])
    if "responses" in views:
        def resp() -> dict[str, Any]:
            lo = anchor - timedelta(days=89)
            lo_ts = datetime.combine(lo, datetime.min.time(), TZ)
            meals = [dict(r) for r in conn.execute(
                """select f.meal_type::text meal_type, count(*) n, avg(m.rise_mmol) rise, avg(m.peak_glucose_mmol) peak
                   from meal_response m join food_logs f on f.id = m.food_log_id
                   where m.user_id=%s and f.deleted_at is null and f.start_at >= %s and m.rise_mmol is not null group by 1 order by 1""", (uid, lo_ts)).fetchall()]
            ex = conn.execute(
                """select count(*) n, avg(r.glucose_change_at_end) avg_change, count(*) filter (where r.post_exercise_low_flag) lows, count(r.post_exercise_low_flag) known
                   from exercise_response r join exercise_logs e on e.id = r.exercise_log_id
                   where r.user_id=%s and e.deleted_at is null and e.start_at >= %s and r.glucose_change_at_end is not null""", (uid, lo_ts)).fetchone()
            dinners = [dict(r) for r in conn.execute(
                """select (start_at at time zone 'Asia/Singapore')::date day, extract(hour from start_at at time zone 'Asia/Singapore')::int hour from food_logs
                   where user_id=%s and deleted_at is null and meal_type::text = 'dinner' and start_at >= %s""", (uid, lo_ts)).fetchall()]
            late = late_dinner_stats(dinners, insights._fasting(conn, uid, lo, anchor + timedelta(days=1))) if dinners else None
            pats = insights.patterns_for(insights._patterns(conn, uid))
            return {"meals": meals, "exercise": dict(ex) if ex and ex["n"] else None, "late": late, "patterns": pats}
        out["responses"] = _view_rows(conn, "responses", resp, {})
    if "longer_history" in views:
        days = P.history_days(text)
        lo = anchor - timedelta(days=days - 1)
        out["history"] = _view_rows(conn, "longer_history", lambda: {
            "days": days, "daily": list(insights._daily(conn, uid, lo, anchor).values())}, {})
    return out


def _trim(x: Any, digits: int = 2) -> str:
    """A lab value as written on the report: no trailing zeros (7.20 is 7.2)."""
    t = f"{float(x):.{digits}f}"
    return t.rstrip("0").rstrip(".") if "." in t else t


def _full(d: Any) -> str:
    """A date with its year, for records that can be old (lab results, check dates)."""
    d = d.astimezone(TZ).date() if isinstance(d, datetime) else d
    return f"{d.day} {d:%b %Y}"


def _with_unit(r: dict[str, Any]) -> str:
    return f"{_trim(r['value'])}" + (f" {r['unit']}" if r.get("unit") else "")


def _lab_lines(labs: list[dict[str, Any]]) -> list[str]:
    by: dict[str, list[dict[str, Any]]] = {}
    for r in labs:
        by.setdefault(str(r["test"]), []).append(r)
    out = []
    for test, rows in by.items():
        rows = sorted(rows, key=lambda r: r["measured_at"], reverse=True)
        r0 = rows[0]
        if r0.get("value") is None:
            continue
        line = f"{LAB_NAMES.get(test, test.replace('_', ' '))}: {_with_unit(r0)} on {_full(r0['measured_at'])}"
        if len(rows) > 1 and rows[1].get("value") is not None:
            line += f"; the one before: {_with_unit(rows[1])} on {_full(rows[1]['measured_at'])}"
        out.append(line)
    return out


def _profile_lines(p: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if p.get("diagnosed_year"):
        out.append(f"Told they have type 2 diabetes in {int(p['diagnosed_year'])}")
    if p.get("care_setting") in CARE_SETTING_TEXT:
        out.append(f"Diabetes care is usually at {CARE_SETTING_TEXT[p['care_setting']]}")
    if p.get("healthier_sg") in ("yes", "no"):
        out.append(f"Healthier SG enrolment: {p['healthier_sg']}")
    conds = [str(c).strip() for c in p.get("conditions") or [] if c and str(c).strip()]
    if conds:
        out.append("Other conditions they listed: " + ", ".join(conds))
    elif p.get("conditions_note"):
        out.append("Conditions note: " + str(p["conditions_note"]).strip())
    alls = [f"{a['substance']}" + (f" (reaction: {a['reaction']})" if a.get("reaction") else "") for a in p.get("allergies") or [] if a.get("substance")]
    if alls:
        out.append("Allergies they listed: " + "; ".join(alls))
    elif p.get("allergies_note"):
        out.append("Allergies note: " + str(p["allergies_note"]).strip())
    return out        # nothing recorded means nothing is said: an empty list is not written as "none"


def _baseline_lines(b: dict[str, Any]) -> list[str]:
    out: list[str] = []
    prior, recent = b.get("fasting_prior") or [], b.get("fasting_recent") or []
    if len(prior) >= 7:       # the same minimum as Insights uses for a usual range
        lo, mid, hi = (insights._percentile(prior, q) for q in (0.25, 0.5, 0.75))
        out.append(f"Morning (fasting) glucose over the {insights.BASELINE_DAYS} days before the last {CONTEXT_DAYS}: middle {_num(mid)} mmol/L, usual range {_num(lo)} to {_num(hi)} mmol/L, on {len(prior)} mornings")
        if len(recent) >= 3:
            out.append(f"Morning (fasting) glucose over the last {CONTEXT_DAYS} days: average {_num(sum(recent) / len(recent))} mmol/L, on {len(recent)} mornings")
        if int(b.get("drift_weeks") or 0) >= 2:
            out.append(f"Morning glucose has been above the usual range for about {int(b['drift_weeks'])} weeks")
    sp, sr = b.get("steps_prior") or [], b.get("steps_recent") or []
    if len(sp) >= 7:
        out.append(f"Steps over the {insights.BASELINE_DAYS} days before the last {CONTEXT_DAYS}: average {round(sum(sp) / len(sp))} a day, on {len(sp)} days")
        if len(sr) >= 3:
            out.append(f"Steps over the last {CONTEXT_DAYS} days: average {round(sum(sr) / len(sr))} a day, on {len(sr)} days")
    return out


def _preventive_lines(rows: list[dict[str, Any]], today: date) -> list[str]:
    out = []
    for kind, name in PREVENTIVE_NAMES.items():
        r = next((x for x in rows if x.get("kind") == kind), None)
        if r is None:
            continue
        bits = []
        if r.get("last_done_on"):
            bits.append(f"last done {_full(r['last_done_on'])}")
        if r.get("next_due_on"):
            bits.append(f"next due {_full(r['next_due_on'])}" + (" (that date has passed)" if r["next_due_on"] < today else ""))
        out.append(f"{name}: " + ("; ".join(bits) if bits else "no date on record"))
    return out


def _response_lines(r: dict[str, Any], facts: list[str]) -> list[str]:
    out: list[str] = []
    for m in r.get("meals") or []:
        if m.get("rise") is None or not m.get("n"):
            continue
        bit = f"{m['meal_type'] or 'meal'}: after {int(m['n'])} meal{'s' if int(m['n']) != 1 else ''} with sensor data, glucose rose by {_num(m['rise'])} mmol/L on average"
        if m.get("peak") is not None:
            bit += f", peak {_num(m['peak'])} mmol/L on average"
        out.append(bit + " (last 90 days)")
    ex = r.get("exercise")
    if ex and ex.get("avg_change") is not None:
        ch = float(ex["avg_change"])
        bit = f"{int(ex['n'])} exercise session{'s' if int(ex['n']) != 1 else ''} with sensor data: glucose {'fell' if ch < 0 else 'rose'} by {_num(abs(ch))} mmol/L on average by the end of the session"
        if ex.get("known"):
            bit += f"; {int(ex['lows'] or 0)} of {int(ex['known'])} were followed by a low reading"
        out.append(bit + " (last 90 days)")
    late = r.get("late")
    if late:
        out.append(f"Fasting glucose the morning after a dinner logged at {late['hour'] - 12} pm or later: average {_num(late['late_avg'])} mmol/L on {late['late_n']} mornings; "
                   f"after earlier dinners: average {_num(late['other_avg'])} mmol/L on {late['other_n']} mornings")
    for p in r.get("patterns") or []:
        out.append(f"{p['text']} (from {int(p['n'])} matched days)")
    out += [f"Smart Health has learned: {f}" for f in facts[:5] if f]
    return out


def _history_lines(h: dict[str, Any], anchor: date) -> list[str]:
    days = int(h.get("days") or 0)
    daily = {d["local_date"]: d for d in h.get("daily") or []}
    if not days or not daily:
        return []
    out = [f"Weekly summaries for the last {days} days to {_short(anchor)}"]
    first = anchor - timedelta(days=days - 1)
    for k in range(-(-days // 7) - 1, -1, -1):             # oldest week first
        hi = anchor - timedelta(days=7 * k)
        lo = max(first, hi - timedelta(days=6))
        rows = [d for dt, d in daily.items() if lo <= dt <= hi]
        bits = []
        g = [float(d["glucose_mean_mmol"]) for d in rows if d.get("glucose_mean_mmol") is not None]
        if g:
            bits.append(f"glucose average of daily means {_num(sum(g) / len(g))} mmol/L on {len(g)} day{'s' if len(g) != 1 else ''}")
        sched = sum(d.get("doses_scheduled") or 0 for d in rows)
        if sched:
            bits.append(f"{sum(d.get('doses_taken') or 0 for d in rows)} of {sched} planned doses taken")
        meals = sum(int(d.get("meals_n") or 0) for d in rows)
        if meals:
            bits.append(f"{meals} meal{'s' if meals != 1 else ''} logged")
        ex = sum(int(d.get("exercise_min") or 0) for d in rows)
        if ex:
            bits.append(f"{ex} exercise minutes")
        st = [int(d["steps_total"]) for d in rows if d.get("steps_total") is not None]
        if st:
            bits.append(f"average {round(sum(st) / len(st))} steps a day")
        if bits:
            out.append(f"{_short(lo)} to {_short(hi)}: " + ", ".join(bits))
    return out if len(out) > 1 else []


def cap_view_sections(secs: list[Section], max_lines: int = MAX_VIEW_LINES, max_chars: int = MAX_VIEW_CHARS) -> list[Section]:
    """At most max_lines lines per view and max_chars characters over all the views together; the later lines are the ones dropped."""
    used = 0
    for s in secs:
        keep = []
        for line in s.lines[:max_lines]:
            if used + len(line) > max_chars:
                break
            keep.append(line)
            used += len(line)
        s.lines = keep
    return secs


def build_view_sections(extra: dict[str, Any], today: date, facts: list[str] | None = None) -> list[Section]:
    """Pure: the extra views as sections. Only the views that were loaded are built. Unknown values are left out (never zero), no line gives a
    verdict or advice, every line passes the data-line check and the whole set is capped (MAX_VIEW_LINES per view, MAX_VIEW_CHARS together)."""
    raw: dict[str, list[str]] = {}
    if "labs" in extra:
        raw["labs"] = _lab_lines(extra["labs"] or [])
    if "profile" in extra:
        raw["profile"] = _profile_lines(extra["profile"] or {})
    if "baseline" in extra:
        raw["baseline"] = _baseline_lines(extra["baseline"] or {})
    if "preventive" in extra:
        raw["preventive"] = _preventive_lines(extra["preventive"] or [], today)
    if "responses" in extra:
        raw["responses"] = _response_lines(extra["responses"] or {}, list(facts or []))
    if "history" in extra:
        raw["longer_history"] = _history_lines(extra["history"] or {}, extra.get("anchor") or today)
    secs = []
    for key, lines in raw.items():
        label, to, detail = VIEW_SECTIONS[key]
        secs.append(Section(key, label, to, [x for x in (G.sanitize_data_line(l) for l in lines) if x], detail))
    return cap_view_sections(secs)


def build_context(conn, uid: str, today: date, text: str, views: set[str] | frozenset[str] = frozenset()) -> Context:
    """The whole context for a question over ONE connection: the default 14-day sections, plus only the extra views the planner picked."""
    rows = load_rows(conn, uid, today, text)
    ctx = build_sections(rows, today)
    if views:
        extra = load_views(conn, uid, today, views, text)
        ctx.sections += build_view_sections(extra, today, rows.get("facts", []))
    return ctx


def load_names(uid: str) -> list[str]:
    """The person's and their emergency contact's name words, so they can be scrubbed from text that goes to JEV. Empty if unreadable."""
    try:
        with tx() as c:
            p = c.execute("select display_name, emergency_contact_name from user_profile where user_id=%s", (uid,)).fetchone()
        return name_tokens(p["display_name"], p["emergency_contact_name"]) if p else []
    except Exception:
        logger.exception("could not read the names to scrub")
        return []


# ----------------------------------------------------------------------------- guidance passages (meaning-based search, keyword search as the fallback)
_EMBED_CACHE: "OrderedDict[str, tuple[float, ...]]" = OrderedDict()
_EMBED_LOCK = threading.Lock()


def _embed_remote(text: str) -> tuple[float, ...]:
    """One embedding call (the same client and model as the food search). Raises on any problem; the caller treats that as 'no embedding'."""
    from google.genai import types

    from app.agents import food   # local import: the client is only built when an embedding is really needed

    r = food._embed_client().models.embed_content(model=EMBED_MODEL, contents=[text], config=types.EmbedContentConfig(output_dimensionality=EMBED_DIM))
    return tuple(float(x) for x in r.embeddings[0].values)


def embed_question(text: str) -> tuple[float, ...] | None:
    """The embedding of an (already scrubbed) question, or None. Remembered per question text in a small in-process LRU (a repeated question is
    free; a failure is not remembered). Counted under the `vertex_embed` daily cap like every other embedding; over the cap, or on any error,
    the answer is None and the caller uses the keyword search. Never raises."""
    key = re.sub(r"\s+", " ", text or "").strip().lower()
    if not key:
        return None
    with _EMBED_LOCK:
        if key in _EMBED_CACHE:
            _EMBED_CACHE.move_to_end(key)
            return _EMBED_CACHE[key]
    try:
        if not usage.allowed("vertex_embed"):
            return None
        vec = _embed_remote(key)
        usage.record("vertex_embed", len(key.split()), 0)
        if len(vec) != EMBED_DIM:
            logger.warning("question embedding has %s numbers, expected %s; using the keyword search", len(vec), EMBED_DIM)
            return None
    except Exception as e:
        logger.warning("question embedding failed, using the keyword search: %s", str(e)[:120])
        return None
    with _EMBED_LOCK:
        _EMBED_CACHE[key] = vec
        while len(_EMBED_CACHE) > EMBED_CACHE_SIZE:
            _EMBED_CACHE.popitem(last=False)
    return vec


@contextmanager
def _reuse(conn):
    """Inside this block every tx() (for example the embedding usage counter) reuses the connection already open, instead of opening another
    (each one is a network round trip). Does nothing for a stub connection or when a shared connection is already set."""
    if conn is None or not hasattr(conn, "transaction") or logstore._shared.get() is not None:
        yield
        return
    token = logstore._shared.set(conn)
    try:
        yield
    finally:
        logstore._shared.reset(token)


@contextmanager
def _savepoint(conn):
    """A savepoint when the connection has one (so a failed search does not spoil the rest of the transaction); nothing for a plain stub."""
    with (conn.transaction() if hasattr(conn, "transaction") else nullcontext()):
        yield


def _quoted(title: Any, content: Any) -> str:
    """One passage as quoted reference text with its source label: [Document title] "text"."""
    return f'[{str(title or "guidance").strip()[:50]}] "{" ".join(str(content or "").split())[:330]}"'


def passages(conn, text: str, names: list[str] | None = None) -> list[str]:
    """Short guidance passages for the question, each labelled with its document's title (only active documents, at most MAX_PASSAGES).
    1. Meaning-based: when the question needs general reading (the planner says so), the scrubbed question is embedded and the nearest
       chunks by cosine distance are returned (none further than MAX_VECTOR_DISTANCE).
    2. Otherwise, or when there is no embedding (over the daily cap, no key, any error), the keyword search as before: chunks that share
       a word with the question.
    Never raises: any error is logged and the result is an empty list or the keyword result."""
    try:
        vec = embed_question(scrub(G.scrub_pii(text or ""), names or [])) if P.needs_guidance(text) else None
    except Exception:
        logger.exception("question embedding failed")
        vec = None
    if vec is not None:
        try:
            lit = "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
            with _savepoint(conn):
                rows = conn.execute(
                    """select left(c.content, 400) c, d.title t, (c.embedding <=> %(v)s::vector) dist
                       from knowledge_chunks c join knowledge_documents d on d.id=c.document_id and d.active
                       order by c.embedding <=> %(v)s::vector limit %(n)s""", {"v": lit, "n": MAX_PASSAGES}).fetchall()
            return [_quoted(r["t"], r["c"]) for r in rows if r.get("dist") is None or float(r["dist"]) <= MAX_VECTOR_DISTANCE]
        except Exception:
            logger.exception("meaning-based knowledge search failed; using the keyword search")
    words = [w for w in re.findall(r"[a-z]{5,}", (text or "").lower())][:5]
    if not words:
        return []
    try:
        with _savepoint(conn):
            rows = conn.execute(
                """select left(c.content, 400) c, d.title t from knowledge_chunks c join knowledge_documents d on d.id=c.document_id and d.active
                   where c.content ilike any(%s) limit %s""", ([f"%{w}%" for w in words], MAX_PASSAGES)).fetchall()
    except Exception:
        logger.exception("knowledge search failed")
        return []
    return [_quoted(r["t"], r["c"]) for r in rows]


def starter_facts(conn, uid: str, today: date) -> dict[str, Any]:
    anchor = insights.anchor(conn, uid, today)
    cgm = conn.execute("select count(*) n from daily_summary where user_id=%s and local_date between %s and %s and glucose_mean_mmol is not null",
                       (uid, anchor - timedelta(days=6), anchor)).fetchone()["n"]
    meds = [r["name"] for r in conn.execute("select name from medications where user_id=%s and deleted_at is null and (end_date is null or end_date >= %s) order by created_at", (uid, today))]
    q = conn.execute("select count(*) n from doctor_questions where user_id=%s and status='open'", (uid,)).fetchone()["n"]
    return {"cgm_days": int(cgm), "medicines": meds, "questions": int(q)}


def build_starters(f: dict[str, Any]) -> list[str]:
    """Pure: starter chips from what the person has. With nothing at all there is one honest starter."""
    out: list[str] = []
    if f["cgm_days"] >= STARTER_CGM_DAYS:
        out.append(texts.tr(texts.request_lang(), "chat.starter.glucose"))
    med = next((_strength_free(m) for m in f["medicines"] if "not readable" not in m.lower()), None)
    if med:
        out.append(texts.tr(texts.request_lang(), "chat.starter.med", med=med))
    if f["questions"] > 0:
        out.append(texts.tr(texts.request_lang(), "chat.starter.doctor"))
    if not out:
        out.append(texts.tr(texts.request_lang(), "chat.starter.help"))
    return out[:MAX_STARTERS]


def follow_ups(f: dict[str, Any], asked: str) -> list[str]:
    ask = clean_text(asked).lower()
    return [s for s in build_starters(f) if s.lower() != ask and s != "What can you help me with?"][:3]


# ----------------------------------------------------------------------------- conversation storage
class NotFound(Exception):
    pass


def _conversation(uid: str, conv_id: str | None) -> str:
    with tx() as c:
        if conv_id:
            try:
                cid = uuid.UUID(conv_id)
            except ValueError:
                raise NotFound(conv_id) from None
            if not c.execute("select 1 from conversations where id=%s and user_id=%s", (cid, uid)).fetchone():
                raise NotFound(conv_id)
            return str(cid)
        return str(c.execute("insert into conversations (user_id) values (%s) returning id", (uid,)).fetchone()["id"])


def _history(conv: str) -> list[tuple[str, str]]:
    with tx() as c:
        rows = c.execute("select role, content from messages where conversation_id=%s order by created_at desc limit %s", (conv, HISTORY_N)).fetchall()
    return [("user" if r["role"] == "user" else "assistant", texts.strip_links(r["content"])) for r in reversed(rows)]


def _save(conv: str, role: str, text: str, at: datetime, verdict: str | None = None, run_id: Any = None) -> dict[str, Any]:
    with tx() as c:
        r = c.execute("insert into messages (conversation_id, role, content, created_at, guard_verdict, agent_run_id) values (%s,%s,%s,%s,%s::guard_verdict,%s) returning id",
                      (conv, role, text, at, verdict, run_id)).fetchone()
    return {"id": str(r["id"]), "at": at.isoformat()}


def _log_guard(uid: str, stage: str, verdict: str, excerpt: str, run_id: Any) -> None:
    try:
        with tx() as c:
            c.execute("insert into guardrail_events (agent_run_id, user_id, stage, verdict, rule_id, excerpt) values (%s,%s,%s,%s::guard_verdict,%s,%s)",
                      (run_id, uid, stage, verdict, f"chat_{stage}@{jev.GUARD_VERSION}", excerpt[:200]))
    except Exception:
        logger.exception("could not log the guard decision")


def get_conversation(uid: str, conv_id: str) -> dict[str, Any]:
    try:
        cid = uuid.UUID(conv_id)
    except ValueError:
        raise NotFound(conv_id) from None
    with tx() as c:
        if not c.execute("select 1 from conversations where id=%s and user_id=%s", (cid, uid)).fetchone():
            raise NotFound(conv_id)
        rows = c.execute("select id, role, content, created_at from messages where conversation_id=%s order by created_at limit 200", (cid,)).fetchall()
    return {"id": str(cid), "messages": [_msg(str(r["id"]), r["role"], r["content"], r["created_at"]) for r in rows]}


def _msg(mid: str, role: str, text: str, at: datetime, kind: str | None = None) -> dict[str, Any]:
    if role == "user":
        return {"id": mid, "role": "user", "text": text, "kind": None, "at": at.isoformat()}
    return {"id": mid, "role": "assistant", "text": text, "kind": kind or KIND_OF.get(text, "answer"), "at": at.isoformat()}


def add_doctor_question(uid: str, text: str) -> dict[str, str]:
    """The person's own words, added to their doctor questions. Origin refused_chat marks where it came from."""
    t = clean_text(text)
    if not t:
        raise ValueError("The question is empty.")
    from app.services import care  # local import: care does not import chat, but keep the module graph flat
    try:
        t = care.check_question_text(t)
    except ValidationFailed as e:
        raise ValueError(str(e)) from None
    with tx() as c:
        have = c.execute("select id, text from doctor_questions where user_id=%s and status='open' and lower(text)=lower(%s)", (uid, t)).fetchone()
        if have:
            return {"id": str(have["id"]), "text": have["text"]}
        r = c.execute("insert into doctor_questions (user_id, text, origin, status) values (%s,%s,'refused_chat','open') returning id, text", (uid, t)).fetchone()
    return {"id": str(r["id"]), "text": r["text"]}


# ----------------------------------------------------------------------------- the answer
SYSTEM = AI.ANSWER_SYSTEM            # the answer instructions live in app/agents/chat_assistant.py


def system_for(lang: str) -> str:
    """The answer prompt in the person's language (the checks always run on the English copy of the reply)."""
    return AI.system_for(texts.LANG_NAMES.get(lang, "English"))


def prompt_for(ctx_text: str, text: str) -> str:
    return f"CONTEXT\n{ctx_text}\n\nQUESTION\n{text}"


@dataclass
class Outcome:
    kind: str
    text: str
    sources: list[Section] = field(default_factory=list)
    open_urgent: bool = False
    offer_question: bool = False
    verdict: str | None = None
    actions: list[dict[str, Any]] = field(default_factory=list)


FIXED_KEY = {"injection": "chat.injection", "off_topic": "chat.off_scope", "harmful_action": "chat.harmful",
             "other_person_or_secret": "chat.other_person", "diagnosis_request": "chat.diagnosis", "medicine_change": "chat.med_change"}
_REPLY_VERDICT = {"diagnosis": "blocked_diagnosis", "medicine_advice": "blocked_med_advice", "uncited_numbers": "blocked_uncited"}


def _fixed(uid: str, run: Any, lang: str, intent: str, safe: str) -> Outcome:
    """A message the chat must not answer: a fixed reply, no model call. A diagnosis or medicine question also offers the doctor questions."""
    verdict = G.VERDICT[intent]
    _log_guard(uid, "input", verdict, safe, run.id)
    ask = intent in ("diagnosis_request", "medicine_change")
    text = texts.tr(lang, FIXED_KEY[intent]) + ("\n\n" + texts.tr(lang, "chat.offer_question") if ask else "")
    return Outcome("refused", text, offer_question=ask, verdict=verdict)


def food_ideas_section(uid: str) -> Section:
    """Real ideas from the person's own history and the Singapore food database (the same ones as Lunch ideas), never made up by the model."""
    lines: list[str] = []
    try:
        for o in nutritionstore.lunch_options(uid, limit=3):
            bits = [str(o["name"])]
            if o.get("serving"):
                bits.append(f"serving {o['serving']}")
            if o.get("carbs") is not None:
                bits.append(f"carbs about {_num(o['carbs'], 0)} g")
            if o.get("sodium") is not None:
                bits.append(f"sodium about {_num(o['sodium'], 0)} mg")
            if o.get("why"):
                bits.append(str(o["why"]))
            lines.append("; ".join(bits))
    except Exception:
        logger.exception("food ideas not available for the chat")
    return Section("food_ideas", "Food ideas", "E8", [x for x in (G.sanitize_data_line(l) for l in lines) if x])


def unsupported_numbers(reply_en: str, evidence: str) -> list[str]:
    """Numbers in a reply that are in neither the person's data nor their question. Small whole numbers (counts like 3 meals) are allowed."""
    have = set(re.findall(r"\d+(?:\.\d+)?", evidence))
    out = []
    for n in re.findall(r"\d+(?:\.\d+)?", reply_en):
        if n in have or n == "995" or ("." not in n and int(n) <= 10):
            continue
        out.append(n)
    return out


def fallback_text(ctx: Context, lang: str, question: str = "") -> str | None:
    """When the model cannot answer, or its reply is not allowed: the person's own numbers, plainly, built by code. None if there are none.
    The sections the question is about (by its words) come first."""
    q = (question or "").lower()
    full = [sec for sec in ctx.sections if sec.lines]
    about = [sec for sec in full if any(w in q for w in KEYWORDS.get(sec.key, ()))]
    if full and not about:
        return texts.tr(lang, "chat.empty")           # nothing in the data is about this question: say so, do not list unrelated sections
    lines = [f"{sec.label}: {sec.lines[0]}" for sec in about][:4]
    return (texts.tr(lang, "chat.fallback_intro") + "\n" + "\n".join(f"- {x}" for x in lines)) if lines else None


def compose(lang: str, answer: str, intent: str, symptom: bool, wants_food: bool, noticed: bool, verdict_q: bool = False) -> tuple[str, list[dict[str, Any]], bool]:
    """The answer plus what code always adds: the doctor referral, where to look in the app, and the offer to add a doctor question."""
    tail: list[str] = []
    if G.needs_doctor_referral(intent, symptom):
        tail.append(texts.tr(lang, "chat.med_refer" if intent == "medicine_info" and not symptom else "chat.symptom_refer"))
    if verdict_q:
        tail.append(texts.tr(lang, "chat.verdict_note"))
    posts = G.signposts(intent, wants_food, noticed)
    tail += [texts.tr(lang, k) for k in G.signpost_text_keys(posts)]
    offer = G.offers_doctor_question(intent, symptom) or verdict_q
    if offer:
        tail.append(texts.tr(lang, "chat.offer_question"))
    actions = [{"kind": "open", "label": p.label, "to": p.to, "text": None} for p in posts if p.to]
    return (answer + ("\n\n" + " ".join(tail) if tail else "")), actions, offer


def decide(uid: str, text: str, history: list[tuple[str, str]], run: Any, today: date, lang: str = "en") -> Outcome:
    """One turn, in this order: urgent words -> speed limit -> help -> input rules -> (JEV when it can be reached) -> triage -> the person's
    own data -> the model's answer -> output rules -> doctor referral, signposts and the offer. Every check that fails ends in a calm fixed
    reply or a plain summary of the person's own data, and the JEV guard being unreachable never stops the chat (our own rules always run)."""
    if G.is_self_harm(text):
        run.step("self_harm_rule", "rules", {}, lambda: {"self_harm": True})
        _log_guard(uid, "input", "urgent", scrub(text, load_names(uid)), run.id)
        return Outcome("urgent", texts.tr(lang, "chat.self_harm"), verdict="urgent")
    if is_urgent_text(text):
        run.step("urgent_rule", "rules", {}, lambda: {"urgent": True})
        _log_guard(uid, "input", "urgent", scrub(text, load_names(uid)), run.id)
        return Outcome("urgent", texts.tr(lang, "chat.urgent"), open_urgent=True, verdict="urgent")
    if not G.LIMITER.allow(uid):
        return Outcome("unavailable", texts.tr(lang, "chat.rate"))
    if is_help_request(text):
        return Outcome("help", texts.tr(lang, "chat.help"))

    names = load_names(uid)
    safe = scrub(G.scrub_pii(text), names)

    rule = G.inspect_input(text)
    if rule is not None:
        run.step("input_rules", "rules", {"rule": rule.rule}, lambda: {"intent": rule.intent})
        if rule.intent == "greeting":
            return Outcome("help", texts.tr(lang, "chat.thanks" if G.is_thanks(text) else "chat.greet"))
        if rule.intent == "unclear":
            return Outcome("help", texts.tr(lang, "chat.unclear"))
        return _fixed(uid, run, lang, rule.intent, safe)

    # JEV is an extra layer while it can be reached. When it cannot, the rules above and below still apply.
    act = "down"
    try:
        if jev._key():
            res = run.step("guard_input", "jev.guard", {"version": jev.GUARD_VERSION}, lambda: jev.guard(safe))
            act = classify_message(res)
    except Exception:
        logger.exception("JEV guard failed; continuing on the chat's own rules")
    if act == "urgent":
        return Outcome("urgent", texts.tr(lang, "chat.urgent"), open_urgent=True, verdict="urgent")
    if act in ("refuse", "caution"):
        return Outcome("refused", texts.tr(lang, "chat.refused" if act == "refuse" else "chat.caution"), offer_question=True, verdict=verdict_for(res))

    try:
        tri = run.step("triage", chat_llm.model_name(), {}, lambda: AI.triage(safe))
    except LLMUnavailable:
        tri = AI.Triage(intent=G.rules_intent(text))        # the model could not label it: the words do, and only to a safe intent
    intent = tri.intent
    verdict_q = G.asks_for_verdict(text)           # by the words only: the model's flag was too eager ("how was my glucose this week?")
    if intent == "diagnosis_request" and G.asks_for_verdict(text) and not G.mentions_symptom(text):
        intent = "data_summary"                  # "is my blood pressure normal?" gets the numbers and a pointer to the doctor, not a refusal
    symptom = bool(tri.mentions_symptom or G.mentions_symptom(text))
    if intent == "greeting":
        return Outcome("help", texts.tr(lang, "chat.greet"))
    if intent == "unclear":
        return Outcome("help", texts.tr(lang, "chat.unclear"))
    if intent == "app_help":
        return Outcome("help", texts.tr(lang, "chat.help"))
    if intent in G.FIXED_INTENTS:
        return _fixed(uid, run, lang, intent, safe)
    wants_food = bool(tri.wants_food_ideas or intent == "food_ideas")
    noticed = bool(tri.about_noticed_things or intent == "insights")

    holder: list[Context] = []
    views = P.plan(text)             # the extra views this question needs (rules only, no model call); empty for a plain 14-day question

    def load() -> dict:
        with tx() as c, _reuse(c):       # ONE connection for the 14-day rows, the planned views, the guidance search and the embedding counter
            holder.append(build_context(c, uid, today, text, views))
        if intent in ("food_ideas", "diet") or wants_food:
            holder[0].sections.append(food_ideas_section(uid))
        return {"sections": {s.key: len(s.lines) for s in holder[0].sections}, "passages": len(holder[0].passages), "views": sorted(views)}

    run.step("context", "sql", {"intent": intent, "views": sorted(views)}, load)
    ctx = holder[0]
    keys = INTENT_SECTIONS.get(intent)
    if wants_food and keys is not None:
        keys = set(keys) | {"food_ideas"}
    if views and keys is not None:
        keys = set(keys) | views         # a planned view is sent whatever the intent (the default sections keep their per-intent limits)
    sent = ctx.only(keys)

    def finish(answer: str, kind: str = "answer", verdict: str | None = "pass", sources: list[Section] | None = None) -> Outcome:
        full, actions, offer = compose(lang, answer, intent, symptom, wants_food, noticed, verdict_q)
        return Outcome(kind, full, sources or [], offer_question=offer, verdict=verdict, actions=actions)

    if sent.empty():
        return finish(texts.tr(lang, "chat.empty"), "empty")

    out: list[Any] = []

    def ask() -> dict:
        hist = [(r, scrub(G.scrub_pii(t), ctx.names)) for r, t in history]
        out.append(AI.answer(texts.LANG_NAMES.get(lang, "English"), sent.text(), hist, scrub(G.scrub_pii(text), ctx.names)))
        return {"chars": len(out[0].reply)}

    try:
        run.step("model", chat_llm.model_name(), {}, ask)
    except LLMUnavailable:
        fb = fallback_text(sent, lang, text)
        return finish(fb) if fb else Outcome("unavailable", texts.tr(lang, "chat.unavailable"), verdict="pass")

    en = G.tidy_reply(G.scrub_pii(out[0].reply_en if lang != "en" else out[0].reply))
    local = G.tidy_reply(G.scrub_pii(out[0].reply)) if lang != "en" else en
    problems = G.reply_problems(en)
    if lang != "en":
        problems += [p for p in G.reply_problems(local, neutral_only=True) if p not in problems]
    honest_no_data = not problems and G.is_no_data_reply(en)       # "I do not have that in your data": it claims nothing, so JEV has nothing to add
    if unsupported_numbers(en, sent.text() + " " + text):
        problems.append("uncited_numbers")
    if not problems and not honest_no_data and jev_reachable():
        if classify_message(jev.guard(en), reply=True) in ("refuse", "urgent", "caution"):
            problems.append("jev")
    _log_guard(uid, "output", "pass" if not problems else _REPLY_VERDICT.get(problems[0], "blocked_other"), en, run.id)
    if problems:
        fb = fallback_text(sent, lang, text)
        return finish(fb, verdict=_REPLY_VERDICT.get(problems[0], "blocked_other")) if fb else Outcome(
            "refused", texts.tr(lang, "chat.blocked_reply"), offer_question=True, verdict=_REPLY_VERDICT.get(problems[0], "blocked_other"))
    if honest_no_data:
        return finish(local, "empty")
    return finish(local, sources=pick_sources(sent.sections, text, en, _med_names(sent)))


def jev_reachable() -> bool:
    try:
        return bool(jev._key())
    except Exception:
        return False


def _med_names(ctx: Context) -> list[str]:
    s = next((x for x in ctx.sections if x.key == "meds"), None)
    return [_strength_free(l.split(";")[0]) for l in s.lines] if s else []


def send(user_key: str, uid: str, raw_text: str, conv_id: str | None) -> dict[str, Any]:
    """One chat turn. Never raises for a model, JEV, cap or data problem: those end in a fixed reply."""
    text = clean_text(raw_text)
    if not text:
        raise ValueError("Please type a message.")
    lang = texts.current_lang(uid)
    conv = _conversation(uid, conv_id)
    history = _history(conv)
    today = datetime.now(TZ).date()
    asked_at = datetime.now(TZ)
    run = Run(uid, "chat", "chat")
    acc: dict[str, Any] = {}
    token = usage.RUN_TOKENS.set(acc)
    status, err = "ok", None
    try:
        try:
            o = decide(uid, text, history, run, today, lang)
        except Exception as e:  # nothing here may reach the person as a stack trace
            logger.exception("chat turn failed")
            o, status, err = Outcome("unavailable", texts.tr(lang, "chat.unavailable"), verdict=None), "error", str(e)[:300]
        if status == "ok" and o.kind in ("urgent", "refused"):
            status = "guard_blocked"
        role = "assistant" if o.kind == "answer" else "system_template"
        stored_text = G.scrub_pii(text)                  # an NRIC, phone or email is never stored; the person sees the scrubbed words after a reload
        me = _save(conv, "user", stored_text, asked_at, None, run.id)
        bot = _save(conv, role, o.text, datetime.now(TZ), o.verdict if o.verdict in (
            "pass", "urgent", "blocked_diagnosis", "blocked_med_advice", "blocked_other", "blocked_injection", "blocked_uncited") else None, run.id)
        try:
            with tx() as c:
                f = starter_facts(c, uid, today)
        except Exception:
            logger.exception("could not read follow-up facts")
            f = {"cgm_days": 0, "medicines": [], "questions": 0}
        run.finish(status, err, tokens=acc, model_id=chat_llm.model_name() if acc.get("calls") else None)
    finally:
        usage.RUN_TOKENS.reset(token)
    actions = list(o.actions)
    if o.open_urgent:
        actions.append({"kind": "open", "label": "Open the urgent screen", "to": "J1", "text": None})
    if o.offer_question:
        actions.append({"kind": "doctor_question", "label": "Add to my doctor questions", "to": None, "text": stored_text})
    return {
        "conversation_id": conv,
        "message": _msg(me["id"], "user", stored_text, asked_at),
        "reply": _msg(bot["id"], role, o.text, datetime.fromisoformat(bot["at"]), o.kind),
        "sources": [{"label": s.label, "to": s.to, "detail": s.detail} for s in o.sources],
        "actions": actions,
        "follow_ups": [] if o.kind == "urgent" else follow_ups(f, text),
    }


def starters(uid: str) -> list[str]:
    with tx() as c:
        return build_starters(starter_facts(c, uid, datetime.now(TZ).date()))
