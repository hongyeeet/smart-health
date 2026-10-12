"""Ask Smart Health: the retrieval planner. For one question it decides which EXTRA views of the person's own data are loaded.

Rule based on purpose: a keyword and phrase map, deterministic, no model call, no extra delay and no cost. The default 14-day sections
(glucose, doses, medicines, meals, activity, sleep, symptoms, blood pressure, questions, learned facts, alerts, next visit) are always
built as before; the planner only adds views. A question the map does not recognise adds nothing, so the worst a missed phrase does is
leave the chat where it is today.

Views (the same words are the Section keys in chat.py):
  labs            latest lab results (HbA1c, fasting glucose, fasting insulin) with date and unit
  profile         conditions, allergies, the year diabetes was diagnosed, where the diabetes is looked after
  baseline        the person's usual morning glucose and steps (60 days before) next to the last 14 days
  preventive      eye, foot, kidney, vaccination and HbA1c check dates
  responses       the person's own computed responses after meals and exercise, and the patterns Smart Health found
  longer_history  weekly summaries over 30, 60 or 90 days

`needs_guidance(text)` is the second decision: a plain question about the person's own numbers does not need general guidance passages,
so the meaning-based search (which costs one embedding call) is skipped for it.
"""
from __future__ import annotations

import re

VIEWS = ("labs", "profile", "baseline", "preventive", "responses", "longer_history")


def _rx(*patterns: str) -> re.Pattern[str]:
    return re.compile("|".join(patterns), re.I)


_RULES: dict[str, re.Pattern[str]] = {
    "labs": _rx(
        r"\bhba1c\b", r"\ba1c\b", r"\bhb ?a1c\b", r"\bglycated\b", r"\bglycosylated\b", r"\blab(s|oratory)?\b(?! ?(day|work))", r"\bblood tests?\b", r"\btest results?\b",
        r"\bcholesterol\b", r"\bldl\b", r"\bhdl\b", r"\btriglycerides?\b", r"\binsulin (level|resistance|result|test)s?\b", r"\bfasting insulin\b",
        r"\bfasting (glucose|sugar) (test|result|level) (at|from|in) (the )?(lab|clinic)\b", r"\blast (blood )?test\b",
    ),
    "profile": _rx(
        r"\ballerg\w*", r"\bconditions?\b", r"\bmedical history\b", r"\bmy history\b", r"\bmy profile\b", r"\bwhen was i diagnosed\b", r"\bdiagnosed (in|when|since)\b",
        r"\bhow long (have|has) i (had|been)\b", r"\bsince when\b.*\bdiabet", r"\b(year|age) (i was |was )?diagnosed\b", r"\bwho (looks?|is looking|takes?) (after|care)\b",
        r"\bwhere do i (get|go for|see)\b", r"\bpolyclinic\b", r"\bhealthier sg\b", r"\bmy (gp|clinic)\b", r"\bwhat do you know about me\b", r"\babout me\b.*\bdiabet",
    ),
    "baseline": _rx(
        r"\busual\b", r"\busually\b", r"\btypical(ly)?\b", r"\bnormally\b", r"\bbaseline\b", r"\bcompared (to|with)\b", r"\bcompare\b", r"\bthan (usual|before|normal|i usually)\b",
        r"\bdifferent (from|than)\b", r"\bdrift\w*", r"\bmy (own )?(average|range)\b.*\b(morning|fasting|steps)\b", r"\bback to (my )?(usual|normal)\b", r"\bout of the ordinary\b",
    ),
    "preventive": _rx(
        r"\beye (screen\w*|check\w*|test|exam\w*)\b", r"\bretina\w*\b", r"\bfoot (screen\w*|check\w*|exam\w*|test)\b", r"\bkidney (test|check\w*|screen\w*)\b",
        r"\bflu (shot|jab|vaccin\w*)\b", r"\binfluenza\b", r"\bvaccin\w*", r"\bscreening\b", r"\bpreventive\b", r"\bcheck-?ups?\b.*\b(due|overdue|last|when)\b",
        r"\b(due|overdue)\b.*\b(check|screening|test)\b", r"\bwhen (is|was) my (last|next) (eye|foot|kidney|hba1c|a1c)\b", r"\bannual (check|review|test)s?\b",
    ),
    "responses": _rx(
        r"\bafter (a |my |the |i |we )?(meals?|eat\w*|ate|breakfast|lunch|dinner|snacks?|walk\w*|workouts?|exercis\w*|runs?|running|gym)\b", r"\b(spike|spikes|spiked|spiking)\b",
        r"\b(affect|affects|affected|impact|influence)\b", r"(?<!side )\beffects?\b", r"\bresponse\w*\b", r"\bresponds?\b", r"\bpatterns?\b", r"\bwhat (works|helps)\b.*\bme\b",
        r"\blate (dinner|meal|night)\b", r"\bdoes (eating|dinner|exercise|walking|sleep)\b", r"\bhow (does|did) my (body|glucose|sugar)\b.*\b(react|respond)\b",
        r"\bwhich (meals?|foods?|dish\w*)\b.*\b(spike|raise|rise)\b", r"\bmy morning (glucose|sugar|reading)s?\b.*\b(dinner|walk|sleep|evening|night)\b",
        r"\b(dinner|evening|night)\b.*\bmy morning (glucose|sugar|reading|fasting)\b",
    ),
    "longer_history": _rx(
        r"\blast (month|2 months|two months|3 months|three months|quarter|few months|couple of months)\b", r"\bpast (month|2 months|two months|3 months|three months|few months|quarter)\b",
        r"\b(over|in) the (last|past) (month|few months|\d+ (months|weeks))\b", r"\b(last|past) (30|60|90) days\b", r"\b(30|60|90)[- ]day\b", r"\b(1|2|3|one|two|three) months?\b",
        r"\bsince\b", r"\btrends?\b", r"\btrending\b", r"\bimprov\w*", r"\bgetting (better|worse)\b", r"\bcompared\b", r"\bover time\b", r"\bweek by week\b", r"\bweekly\b",
        r"\bhistory\b(?! of)", r"\bmonthly\b", r"\bthis year\b", r"\blong[- ]term\b",
    ),
}

# a question about general knowledge or "what should / how do I" wants guidance reading; a plain question about my own numbers does not
_GUIDANCE = _rx(
    r"\bwhat (is|are|does|do) (?!my\b|me\b|i\b|the (latest|last)\b)", r"\bwhy\b", r"\bhow (do|can|should|to|does|much should)\b", r"\btips?\b", r"\badvice\b", r"\bexplain\b", r"\bmeans?\b", r"\bmeaning\b",
    r"\brecommend\w*", r"\bsuggest\w*", r"\bhealthy\b", r"\bgood for\b", r"\bcauses?\b", r"\bprevent\w*", r"\breduc\w*", r"\bimprove\b", r"\bavoid\b", r"\bsafe\b", r"\bsafely\b",
    r"\bgeneral(ly)?\b", r"\bguideline\w*", r"\bsymptoms? of\b", r"\bside effects?\b", r"\bcomplications?\b", r"\bshould\b", r"\bcan i\b", r"\bis it ok\w*\b", r"\blearn\b",
)
_PERSONAL = _rx(r"\b(my|me|i|i'm|i've|mine)\b")
_DATA_WORDS = _rx(
    r"\b(glucose|sugar|readings?|cgm|steps?|sleep|slept|meals?|ate|eaten|doses?|tablets?|pills?|medicines?|blood pressure|bp|pulse|weight|exercise|workouts?|walks?|walked|hba1c|a1c|labs?|results?|"
    r"allerg\w*|conditions?|diagnosed|diabetes|eye|foot|kidney|flu|screening|due|overdue|cholesterol|insulin|appointments?|visit|symptoms?|questions?|average|total|how many|how much|how often|trend|usual|range|latest|last|yesterday|today|week|month)\b",
)

_GENERIC_Q = _rx(r"^(what (is|are|does)|why (does|do|is|are)|how (does|do|is|are)) ")

_LONG = {
    30: _rx(r"\b(last|past) month\b", r"\b(1|one) month\b", r"\b30[- ]day", r"\b(last|past) 30 days\b", r"\bmonthly\b"),
    60: _rx(r"\b(2|two) months?\b", r"\b60[- ]day", r"\b(last|past) 60 days\b"),
}


def plan(text: str) -> set[str]:
    """The extra views to load for this question (a subset of VIEWS). Pure and deterministic. Empty for greetings, medicine questions and
    any plain question about the last two weeks."""
    t = re.sub(r"\s+", " ", (text or "").replace("’", "'")).strip()
    if not t:
        return set()
    picked = {view for view, rx in _RULES.items() if rx.search(t)}
    if _GENERIC_Q.search(t) and not _PERSONAL.search(t):
        picked = set()          # "what is a normal HbA1c": general reading, nothing from the person's own records
    return picked


def history_days(text: str) -> int:
    """How far back the longer_history view reaches: 30 for 'last month', 60 for 'two months', otherwise 90 (the most it ever reads)."""
    t = text or ""
    if _LONG[60].search(t):
        return 60
    if _LONG[30].search(t) and not re.search(r"\b(3|three|few|several) months?\b|\b90\b|\bquarter\b|\bsince\b|\byear\b", t, re.I):
        return 30
    return 90


def needs_guidance(text: str) -> bool:
    """False for a plain question about the person's own data (no embedding call is made for it); True when general reading could help:
    the question asks what something is, why, how to, for tips, or does not mention the person's own data at all."""
    t = re.sub(r"\s+", " ", text or "").strip()
    if not t:
        return False
    if _GUIDANCE.search(t):
        return True
    return not (_PERSONAL.search(t) and _DATA_WORDS.search(t))
