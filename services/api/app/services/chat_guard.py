"""The chat's own guardrails (screen I1). Pure rules: no network, no database, no model, so every rule can be tested.

Where it sits in a turn (app/services/chat.py `decide`):
  1. input rules   -> `inspect_input`: prompt injection, requests to change or share things, other people's data or secrets, obvious
                      off-topic requests, requests to diagnose, requests to change a medicine. A match gets a FIXED reply and no model call.
  2. triage        -> a Gemini call labels the message (intent and flags). If it cannot run, `rules_intent` labels it from the words.
  3. the answer    -> Gemini, from this person's own rows only.
  4. output rules  -> `reply_problems`: a reply with a diagnosis, medicine advice, a verdict ("normal", "bad"), a cause ("because of"),
                      a link or a leaked instruction is NEVER shown; the caller shows a plain summary of the person's own data instead.
  5. composition   -> `signposts` and the doctor referral lines are added by code, not by the model, so they cannot be left out.

What this file will not do: decide anything medical. It never says what a number or a symptom means. Every list below is a placeholder
for review by the clinical owner (rules.md 1.15) and is meant to be extended, never relaxed.
"""
from __future__ import annotations

import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass

# ----------------------------------------------------------------------------- intents
# What a message is about. The triage call returns one of these; `rules_intent` can return the ones the words make obvious.
INTENTS = (
    "data_summary", "insights", "diet", "food_ideas", "symptoms", "medicine_info", "appointments", "app_help", "greeting",
    "diagnosis_request", "medicine_change", "off_topic", "injection", "harmful_action", "other_person_or_secret", "unclear",
)
# these never reach the model for an answer: a fixed reply is shown
FIXED_INTENTS = {"diagnosis_request", "medicine_change", "off_topic", "injection", "harmful_action", "other_person_or_secret", "greeting"}
ANSWER_INTENTS = set(INTENTS) - FIXED_INTENTS - {"unclear"}

# the guardrail_events verdicts (enum guard_verdict) each blocked intent is logged as
VERDICT = {"diagnosis_request": "blocked_diagnosis", "medicine_change": "blocked_med_advice", "injection": "blocked_injection",
           "off_topic": "blocked_other", "harmful_action": "blocked_other", "other_person_or_secret": "blocked_other"}

# ----------------------------------------------------------------------------- input rules
def _rx(*patterns: str) -> list[re.Pattern[str]]:
    return [re.compile(p, re.I) for p in patterns]


# someone trying to change the assistant's instructions, reveal them, or make it play another role
INJECTION = _rx(
    r"\b(ignore|disregard|forget|override|bypass|skip)\b.{0,30}\b(all |any |the |your |previous |prior |above |earlier |system |these )*(instructions?|rules?|prompts?|guidelines?|restrictions?|guardrails?|filters?|safety)\b",
    r"\byou are (now|no longer)\b", r"\bfrom now on,? you\b", r"\bact as\b", r"\bpretend (to be|you are|you're)\b", r"\broleplay\b", r"\brole[- ]play\b",
    r"\b(jailbreak|developer mode|dan mode|do anything now|sudo mode|god mode)\b", r"\bwithout (any )?(restrictions?|rules|filters|limits|guardrails)\b",
    r"\b(reveal|show|print|repeat|tell me|display|output|leak|translate)\b.{0,30}\b(your|system|hidden|initial|above|previous)\b.{0,15}\b(prompt|instructions?|rules|context|message|text)\b",
    r"\b(reveal|show|print|repeat|display|output|leak)\b.{0,20}\bthe (system|hidden|initial|original) (prompt|instructions?)\b",
    r"\b(leak|reveal)\b.{0,10}\b(the|your)\b.{0,6}\b(prompt|instructions?|context)\b", r"\bthe (context|prompt|instructions?) you (were|have been) (given|told|using)\b",
    r"\b(repeat|print|output|show|display)\b.{0,15}\b(the |this |your )?(text|message|prompt|conversation)\b.{0,15}\b(above|before|so far|earlier|up to here)\b",
    r"\bwhat (is|are|were) your (system )?(prompt|instructions|rules)\b", r"\bsystem prompt\b", r"\b(begin|end) (of )?(system|prompt|instructions)\b",
    r"<\s*/?\s*(system|assistant|user|context|instructions?)\s*>", r"\[\s*/?(system|inst)\s*\]", r"<\|", r"\bbase64\b", r"\bdecode (this|the following)\b",
    r"\bnew (instructions?|rules?)\s*:", r"\bas an ai (model )?(without|with no)\b", r"\bhypothetically,? (if )?you (had|were|could)\b",
)
# asking the chat to DO something (it can only read and explain): change, delete, send, share, book, buy, turn off, call
HARMFUL_ACTION = _rx(
    r"\b(delete|erase|wipe|remove|clear|reset|destroy)\b.{0,25}\b(my |all |the |every )?(data|account|records?|history|logs?|readings?|medicines?|medications?|messages?|chat|emergency contact|reminders?|appointments?|visits?|photos?|meals?)\b",
    r"\b(send|email|e-mail|text|sms|whatsapp|message|forward|post|upload|share)\b.{0,30}\b(to|with|on)\b.{0,30}\b(doctor|nurse|family|wife|husband|son|daughter|friend|someone|anyone|everyone|him|her|them|my contact|clinic|hospital|insurer|employer|facebook|twitter|instagram|public)\b",
    r"\b(change|edit|update|set|modify|cancel|reschedule|book|make)\b.{0,25}\b(my |the )?(appointment|visit|check-?up|clinic|emergency contact|email|phone number|password|reminders?|consent|dose|prescription|medicine|medication)\b",
    r"\b(turn|switch) (off|on)\b.{0,25}\b(alerts?|reminders?|alarms?|notifications?|consent|sharing|emails?)\b",
    r"\b(disable|enable|stop)\b.{0,15}\b(alerts?|reminders?|alarms?|notifications?)\b",
    r"\b(order|buy|purchase|pay|transfer|refill)\b.{0,25}\b(medicine|medication|prescription|pills?|tablets?|insulin|money|for me)\b",
    r"\b(call|phone|ring|dial)\b.{0,15}\b(someone|my (doctor|wife|husband|son|daughter|family)|an ambulance|995)\b",
    r"\b(log|record|add|enter|save)\b.{0,12}\b(this|that|it|my)\b.{0,20}\b(for me|in my (records?|logs?|chart))\b",
    r"(?:^|\b(?:please|can you|could you|would you|will you|just|and|then)\s+)(text|email|e-mail|send|forward|share|message|whatsapp)\b.{0,15}\b(my )?(doctor|nurse|son|daughter|wife|husband|family|friend|clinic)\b",
)
# asking about other people, or for secrets, credentials or identity numbers
OTHER_PERSON_OR_SECRET = _rx(
    r"\b(other|another|different) (patients?|persons?|people|users?|accounts?|profiles?)\b", r"\b(everyone|all (the )?(users?|patients?|people))\b.{0,20}\b(data|records?|readings?|names?|list)\b",
    r"\b(mr\.? tan|demo (user|patient|account))\b", r"\b(someone else|somebody else|my (neighbou?r|colleague|boss|ex))('s)?\b.{0,20}\b(data|records?|readings?|health|medicines?)\b",
    r"\b(password|passcode|pin number|api[- ]?key|secret|token|credentials?|webhook|database|sql|admin|root)\b", r"\b(nric|fin number|passport number|credit card|card number|cvv|bank account|singpass)\b",
    r"\b(show|give|tell|list|read) me (the |your )?(database|server|logs?|source code|code|config|environment|env)\b",
)
# obviously outside the app, whatever else the message says (checked only when the message has no health or app word in it)
OFF_TOPIC = _rx(
    r"\b(write|create|generate|make|compose|draft)\b.{0,20}\b(a |an |me )?(code|script|program|poem|essay|story|song|joke|email|letter|speech|cv|resume|report|article|blog|lyrics)\b",
    r"\b(python|javascript|typescript|java|c\+\+|html|css|sql|regex|react|linux|bash|powershell)\b", r"\b(homework|exam|assignment|quiz|trivia|riddle)\b",
    r"\b(election|president|prime minister|politic\w*|government|minister|war|religion|god|bible|quran|abortion|immigration|vote)\b",
    r"\b(stocks?|shares?|bitcoin|crypto\w*|invest\w*|forex|loan|mortgage|insurance quote|lottery|toto|4d)\b", r"\b(weather|forecast|football|soccer|nba|score|match result|movie|netflix|celebrity|horoscope|zodiac)\b",
    r"\b(translate|translation)\b", r"\b(who (is|was)|what is the capital|how tall is|when was .* born)\b", r"\b(hack|exploit|malware|phishing|ddos|crack|pirate)\b",
)
# the person asks what is wrong or what they have
DIAGNOSIS_REQUEST = _rx(
    r"\bdo i have\b(?!\s+(any |a |an |to |enough |my |the |another |more |some )*(appointments?|visits?|to\b|until\b|before\b|meals?|medic\w*|tablets?|pills?|questions?|readings?|data|logs?|results?|checks?|reminders?|time|steps?|goals?|messages?|alerts?|allerg\w*|doctors?))", r"\bam i (sick|ill|dying|diabetic|having|getting|developing|suffering)\b", r"\bwhat('s| is| are) (wrong|the matter) with me\b", r"\bdiagnos(e|is|ing)\b",
    r"\bwhat (disease|illness|condition|sickness|infection|problem) (do i|is it|could it be|might it be)\b", r"\b(is|could|might|can) (it|this|that) be (a |an |the )?(cancer|tumou?r|stroke|heart attack|infection|neuropathy|retinopathy|nephropathy|kidney|liver|thyroid|anaemia|anemia|dementia|covid|flu|dengue)\b",
    r"\bwhat (is|are) (causing|making)\b.{0,30}\b(me|my)\b", r"\bwhy (do|am|have|did) i (feel|have|keep|get|got)\b", r"\bis (this|it|that) (serious|dangerous|a sign|something (bad|serious))\b",
    r"\b(is|could|might|may) (this|it|that|my [a-z]+( [a-z]+)?) (be |a sign of |signs of )?(a |an |the |some )?(diabet\w*|neuropathy|retinopathy|nephropathy|kidney (disease|failure|damage|problem)|heart (disease|failure|problem)|liver (disease|damage)|cancer|tumou?r|anaemia|anemia|dementia|depression|thyroid)\b",
    r"\b(is|are) (there )?(something|anything) wrong with (me|my [a-z]+)\b", r"\bhave i (got|developed)\b", r"\bwhat do i have\b",
    r"\b(complications?|damage)\b.{0,25}\b(do i|have i|am i|will i)\b", r"\bwill i (die|go blind|lose|need amputation)\b", r"\bhow (long|much) (do i|time do i) have\b(?!\s+(to|until|before|left until|till)\b)",
)
# the person asks whether to start, stop, skip or change a medicine or its amount
MEDICINE_CHANGE = _rx(
    r"\b(should|can|could|may|must) i\b.{0,25}\b(stop|skip|miss|start|take|double|halve|increase|decrease|reduce|raise|lower|change|switch|swap|combine|mix|crush|split|quit|cut)\b.{0,40}\b(medic\w*|tablets?|pills?|capsules?|doses?|insulin|metformin|statin|drugs?|supplements?|herbs?|\d+ ?mg)\b",
    r"\bis it (ok|okay|fine|safe|alright|all right)\b.{0,25}\b(to )?(stop|skip|miss|take|double|halve|combine|mix)\b", r"\bhow (many|much)\b.{0,20}\b(tablets?|pills?|mg|doses?|units?)\b.{0,20}\b(should|can|do) i\b",
    r"\bwhat (dose|dosage|amount)\b.{0,20}\b(should|can|do) i\b", r"\b(instead of|replace|substitute)\b.{0,20}\b(my )?(medic\w*|tablets?|pills?|metformin|insulin)\b", r"\bcan i (stop|quit)\b",
    r"\bforgot (to take|my)\b.{0,25}\b(should i|can i|what (do|should) i do)\b", r"\bdouble (up|the dose)\b",
    r"\b(skip|stop|double|halve|quit)\b.{0,20}\b(my|the|your)\b.{0,15}\b(medic\w*|tablets?|pills?|metformin|insulin|doses?|statins?)\b", r"\b(dose|dosage)\b.{0,15}\b(i|you) should\b",
    r"\bdo i need to\b.{0,25}\b(stop|skip|miss|start|take|double|halve|increase|decrease|reduce|raise|lower|change|switch|swap|combine|mix)\b.{0,40}\b(medic\w*|tablets?|pills?|capsules?|doses?|insulin|metformin|statin|drugs?|supplements?|herbs?|\d+ ?mg)\b",
)
SYMPTOM_WORDS = _rx(
    r"\b(symptoms?|pain|ache|aching|hurts?|sore|dizz\w*|nausea|nauseous|vomit\w*|tired|fatigue\w*|weak\w*|numb(ness)?|tingling|blurr\w*|thirst\w*|headache|cramps?|rash|itch\w*|swollen|swelling|sweat\w*|shak\w+|faint\w*|cough\w*|fever|breath\w*|palpitations?|hungry|appetite|constipat\w*|diarrh\w*|infection|wound|sore on|cold|flu)\b",
    r"\bfeel(ing)? (unwell|sick|ill|off|weak|dizzy|faint|funny|strange|bad|awful|tired|shaky)\b",
)
# words that show a message is about the person's health data or this app (an off-topic cue is ignored when one of these is present)
DOMAIN_WORDS = _rx(
    r"\b(glucose|sugar|cgm|sensor|hba1c|a1c|gmi|mmol|time in range|spike|reading|readings|meal|meals|food|foods|eat|ate|eating|diet|calor\w*|carbs?|carbohydrate|protein|fat|salt|sodium|breakfast|lunch|dinner|snack|dish)\b",
    r"\b(walk|exercise|workout|steps?|active|activity|gym|run|running|sleep|slept|rest|heart rate|spo2|oxygen|blood pressure|bp|pulse|weight|waist)\b",
    r"\b(medic\w*|tablets?|pills?|capsules?|dose|doses|drug|supplement|metformin|statin|insulin|prescription|refill|stock|side effects?|pharmacist)\b",
    r"\b(doctor|appointment|visit|clinic|brief|report|question|questions|check-?ups?|screening)\b", r"\b(insights?|overview|trend|trends|week|today|yesterday|month|average|my data|my health|logged|log|history|noticed|learned|summary|summarise|summarize)\b",
    r"\b(smart health|this app|the app|dashboard|tab|screen|feature|reminder|notification|alert)\b", r"\bmy\b",
)

_GREETING = re.compile(r"^\W*(hi|hello|hey|good (morning|afternoon|evening)|thanks|thank you|thx|ok|okay|bye|goodbye|cheers)\W*$", re.I)
_THANKS = re.compile(r"^\W*(thanks|thank you|thx|ok|okay|bye|goodbye|cheers)\W*$", re.I)
# asking whether a number or a result is normal, good, bad, high, healthy or safe: the person gets their numbers, never the verdict
_VERDICT_Q = re.compile(r"\b(is|are|was|were)\b.{0,30}\b(normal|abnormal|good|bad|healthy|unhealthy|too high|too low|high enough|low enough|dangerous|safe|unsafe|worrying|concerning|alarming)\b|\b(should|do) i (be )?(worried|concerned|worry|panic)\b|\bis (that|this|it) (a )?(problem|concern|worry)\b", re.I)
# thoughts of ending their life or hurting themselves: a fixed, caring reply with the emergency and support numbers, never a model answer
_SELF_HARM = re.compile(r"\b(suicid\w*|kill(ing)? myself|(end|ending|take|taking) (my|his|her) (own )?life|end it all|want(ed)? to die|wish i (was|were) dead|no (reason|point) (to|in) (live|living|going on)|(hurt|harm|cut)(ting)? myself|self[- ]?harm|don.?t want to (live|be here|go on|be alive)|do not want to (live|be here|go on|be alive)|can.?t (go on|take it anymore)|better off dead|(take|took) my own life|thinking (of|about) ending (it|my life))\b", re.I)
_URL = re.compile(r"(https?://|www\.)\S+|\b[\w.-]+\.(com|org|net|io|sg|gov|edu|co)\b/?\S*", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?<!\d)(\+?\d[\d \-()]{7,}\d|(?:\+?65[ -]?)?[3689]\d{3}[ -]?\d{4})(?!\d)")
_NRIC = re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.I)


@dataclass(frozen=True)
class Finding:
    intent: str           # one of INTENTS
    rule: str             # a short name for the log (never the person's words)


def _first(patterns: list[re.Pattern[str]], text: str) -> bool:
    return any(p.search(text) for p in patterns)


_LOW_NUM = re.compile(r"\b(sugar|glucose|reading|cgm|sensor|hypo)\b[^0-9]{0,25}(\d{1,2}(?:\.\d)?)\b", re.I)
_MMOL = re.compile(r"(?<![\d.])(\d{1,2}(?:\.\d)?)\s*mmol", re.I)
_HYPO_SYMPTOMS = re.compile(r"\b(sweat\w*|shak\w+|trembl\w+|dizz\w*|confus\w*|faint\w*|palpitat\w*|blurr\w+|weak|clammy|light-?headed)\b", re.I)


def low_reading_with_symptoms(text: str) -> bool:
    """A glucose reading below 4.0 mmol/L in the message together with the signs of a low (sweating, shaking, dizziness, confusion): urgent.
    The 4.0 line is the app's own low tier (appConfig.hypoTiers, placeholder pending clinical review)."""
    t = text or ""
    values = [float(m.group(2)) for m in _LOW_NUM.finditer(t)] + [float(m.group(1)) for m in _MMOL.finditer(t)]
    return any(0.5 <= v < 4.0 for v in values) and bool(_HYPO_SYMPTOMS.search(t))


_LOW_SUGAR = re.compile(r"\blow (blood )?(sugar|glucose)\b|\b(sugar|glucose)\b[\w ]{0,20}\b(low|dropp\w+|crash\w+)\b|\bhypo(glyc\w+)?\b|\bsugar crash", re.I)
_LOW_SYMPTOMS = re.compile(r"\b(faint\w*|confus\w*|disorient\w*|shak\w+|trembl\w+|sweat\w*|dizz\w*|clammy|light-?headed|blurr\w+|weak\w*|drowsy|unresponsive|passed out|blacked out)\b", re.I)


def low_sugar_with_symptoms(text: str) -> bool:
    """Words for a low sugar together with a sign of a low (faint, confused, shaky, sweating, dizzy): urgent. A low mentioned alone is not."""
    t = text or ""
    return bool(_LOW_SUGAR.search(t) and _LOW_SYMPTOMS.search(t))


# the model's honest answer when the person's data has nothing on the question: a short sentence, no numbers
_NO_DATA = re.compile(
    r"^\W*(sorry[,. ]+)?(i|smart health|there)\s+(do not|don't|did not|didn't|cannot|can't|could not|couldn't|have no|has no|is no|is not any|am not able to)\b[^.?!]{0,80}\b(in|from|on|about|for) (your|the) (data|records?|logs?|readings?|entries|information|app)\b"
    r"|^\W*(sorry[,. ]+)?(i|smart health)\s+(do not|don't|have no|has no)\b[^.?!]{0,60}\b(data|information|records?)\b[^.?!]{0,30}\b(on|about|for) (that|this|it)\b", re.I)


def is_no_data_reply(reply: str) -> bool:
    """True for a short honest "I do not have that in your data" reply (up to 45 words, no digits). Such a reply claims nothing."""
    t = re.sub(r"\s+", " ", reply or "").strip()
    return bool(t) and len(t.split()) <= 45 and not re.search(r"\d", t) and bool(_NO_DATA.match(t))


def is_thanks(text: str) -> bool:
    return bool(_THANKS.match(re.sub(r"\s+", " ", text or "").strip()))


def asks_for_verdict(text: str) -> bool:
    return bool(_VERDICT_Q.search(text or ""))


def is_self_harm(text: str) -> bool:
    return bool(_SELF_HARM.search(re.sub(r"\s+", " ", text or "")))


def has_domain_word(text: str) -> bool:
    return _first(DOMAIN_WORDS, text)


def mentions_symptom(text: str) -> bool:
    return _first(SYMPTOM_WORDS, text)


def inspect_input(text: str) -> Finding | None:
    """The rule check on what the person typed. None means "no rule fired": the triage call and the answer follow.

    Order matters: an injection or a request for secrets is stopped first; then actions; then the two medical limits (diagnosis, medicine
    change); off-topic last, and only when the message has no health or app word in it.
    """
    t = re.sub(r"\s+", " ", text or "").strip()
    if not t:
        return Finding("unclear", "empty")
    if _first(INJECTION, t):
        return Finding("injection", "injection_pattern")
    if _first(OTHER_PERSON_OR_SECRET, t):
        return Finding("other_person_or_secret", "other_person_or_secret")
    if _first(HARMFUL_ACTION, t):
        return Finding("harmful_action", "action_request")
    if _first(MEDICINE_CHANGE, t):
        return Finding("medicine_change", "medicine_change")
    if _first(DIAGNOSIS_REQUEST, t):
        return Finding("diagnosis_request", "diagnosis_request")
    if _GREETING.match(t):
        return Finding("greeting", "greeting")
    if _first(OFF_TOPIC, t) and not has_domain_word(t.replace("my", "")):
        return Finding("off_topic", "off_topic_words")
    return None


def rules_intent(text: str) -> str:
    """The intent from the words alone: used when the triage call cannot run. It only ever picks a safe answer intent or "unclear"."""
    t = (text or "").lower()
    if mentions_symptom(t):
        return "symptoms"
    if re.search(r"\b(what is|what's|what are|why|when|how)\b.{0,40}\b(for|take|taking)\b.{0,30}\b(medic\w*|tablets?|pills?|metformin|statin|amlodipine|supplement)\b|\b(medic\w*|tablets?|pills?|supplements?)\b|\bwhat(\'s| is| are)\b.{1,40}\bfor\b\W*$", t):
        return "medicine_info"
    if re.search(r"\b(suggest\w*|ideas?|recommend\w*|what (can|should) i (eat|have)|something to eat|lighter|healthier)\b", t) and re.search(r"\b(food|eat|meal|lunch|dinner|breakfast|snack|dish|have)\b", t):
        return "food_ideas"
    if re.search(r"\b(meal|food|eat|ate|diet|carbs?|calor\w*|salt|sodium|lunch|dinner|breakfast|snack)\b", t):
        return "diet"
    if re.search(r"\b(noticed|learned|know about me|insights?|overview|trends?|pattern|changed)\b", t):
        return "insights"
    if re.search(r"\b(appointment|visit|doctor|clinic|check-?up|screening|question)\b", t):
        return "appointments"
    if has_domain_word(t):
        return "data_summary"
    return "unclear"


# ----------------------------------------------------------------------------- the person's own data is scrubbed and made inert
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f​-‏‪-‮⁦-⁩]")


def scrub_pii(text: str) -> str:
    """Emails, phone numbers and ID numbers are removed from text that leaves this process or is shown back."""
    out = _EMAIL.sub("[email]", text or "")
    out = _NRIC.sub("[id]", out)
    return _PHONE.sub("[number]", out)


def sanitize_data_line(line: str, limit: int = 220) -> str | None:
    """One line of the person's own data going into the model's context. Text the person (or a medicine label) typed is DATA: a line that
    reads like an instruction to the model is dropped, control characters are removed, and the length is limited."""
    s = _CONTROL.sub("", str(line or "")).replace("\n", " ").replace("\r", " ").strip()
    if not s:
        return None
    if _first(INJECTION, s):
        return None
    return scrub_pii(s)[:limit]


# ----------------------------------------------------------------------------- output rules
_QUOTED_QUESTION = re.compile(r"\b(asking|asks|asked|wondering|wonder|whether|if)\b[^.?!]{0,25}\b(it is|it's|you can|i can|is it|can i|can you)\b[^.?!]{0,12}\b(ok|okay|fine|safe|alright)\b", re.I)
# "I cannot say whether a number is normal" refuses a verdict, it does not give one (the clause stops at a comma, full stop or semicolon)
_REFUSED_VERDICT = re.compile(r"\b(cannot|can't|can not|do not|don't|not able to|unable to|am not able to)\s+(say|tell|judge|decide|confirm|know|give)\b(?:(?!\s+(?:and|but|however|though|although|yet)\b)[^.?!,;]){0,60}?\b(normal|abnormal|good|bad|healthy|unhealthy|safe|unsafe|dangerous|worrying)\b(?:(?!\s+(?:and|but|however|though|although|yet)\b)[^.?!,;])*", re.I)
# "I cannot advise on stopping a medicine" refuses advice, it does not give it (same clause rule)
_REFUSALS = re.compile(r"\b(cannot|can't|can not|do not|don't|not able to|unable to|am not able to)\s+(advise|recommend|suggest|decide|give advice)\b(?:(?!\s+(?:and|but|however|though|although|yet)\b)[^.?!,;])*", re.I)
_GOOD_PHRASE = re.compile(r"\b(a |an )?good (question|idea|point|time|place|habit to ask)\b", re.I)
_ALLOWED_DIAGNOSE = re.compile(r"\b(cannot|can't|can not|do not|don't|not able to|unable to|am not able to)\s+(diagnose|diagnosis)\b", re.I)

REPLY_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("diagnosis", re.compile(
        r"\byou (probably|likely|may|might|could|seem to|appear to) (have|be suffering|be experiencing|be (diabetic|anaemic|anemic|dehydrated|hypoglyc\w+|hyperglyc\w+|insulin resistant))\b"
        r"|\byou are (suffering|diabetic|anaemic|anemic|dehydrated|hypoglyc\w+|hyperglyc\w+|insulin resistant|in danger|dying|at risk of)\b"
        r"|\b(this|that|it) (is|means|suggests|indicates|signals|could be|might be|may be|sounds like|looks like|points to) (a |an |the )?(sign|symptom|signs|symptoms|infection|neuropathy|retinopathy|nephropathy|hypoglyc\w+|hyperglyc\w+|diabet\w+|condition|disease|problem with)\b"
        r"|\byou (have|had|got|developed) (a |an |the )?(neuropathy|retinopathy|nephropathy|diabetes|hypoglyc\w+|hyperglyc\w+|infection|kidney disease|heart disease|hypertension|high blood pressure|high cholesterol|anaemia|anemia|cancer|stroke|depression|condition|disease)\b(?!\s+(readings?|numbers?|values?|results?|entries|logs?))"
        r"|\b(diagnos(is|ed|e|ing)|prognosis|disorder|syndrome)\b", re.I)),
    ("medicine_advice", re.compile(
        r"\b(you should|you can|you could|you need to|you must|you ought to|try to|consider|i recommend|i suggest|i advise|it is (ok|okay|fine|safe|alright) to|go ahead and|better (to|if you)|make sure (you|to)|don't|do not)\b"
        r".{0,45}\b(take|taking|stop|stopping|skip|skipping|start|starting|increase|decrease|reduce|raise|lower|double|halve|change|switch|adjust|miss|crush|split|combine|mix)\b"
        r".{0,40}\b(medic\w*|tablets?|pills?|capsules?|doses?|insulin|metformin|statins?|drugs?|supplements?|herbs?|\d+ ?mg)\b"
        r"|\b(stop|skip|start|increase|decrease|reduce|double|halve|crush|split)\b.{0,12}\b(your|the|a|an)\b.{0,20}\b(medic\w*|tablets?|pills?|capsules?|doses?|insulin|metformin|statins?|drugs?|supplements?)\b", re.I)),
    ("medicine_advice", re.compile(      # an order to take, double, halve, change, stop or skip; it must start a sentence (or follow please/then/now), so "You take Metformin 500 mg at 08:00" stays allowed
        r"(?:^|[.!?:;,\n]\s*|\b(?:please|then|and|just|now|also|tonight|today)\s+)(take|double|halve|increase|reduce|decrease|stop|skip|miss|cut|raise|lower|swap|switch|crush|split)\b"
        r"[^.?!\n]{0,40}?\b(tablets?|pills?|capsules?|doses?|dosage|medic\w*|insulin|units? of|\d+(\.\d+)? ?(mg|mcg|ml|units?))\b", re.I)),
    ("verdict", re.compile(
        r"\b(is|are|was|were|looks?|seems?|sounds?|appears?|remains?)\s+(a |an |the )?(very |quite |a bit |fairly |pretty |still |perfectly |totally |completely )?(normal|abnormal|healthy|unhealthy|dangerous|safe|unsafe|worrying|concerning|alarming|good|bad|fine|great|excellent|terrible|poor|too high|too low)\b"
        r"|\b(normal|abnormal|healthy|dangerous|safe) (range|level|levels|values?)\b|\bwithin (the )?normal\b|\b(nothing to worry|no need to worry|don't worry|do not worry|not a concern)\b", re.I)),
    ("cause", re.compile(r"\b(because of|caused by|is caused|are caused|due to|leads? to|led to|results? in|resulted in|is why|that is why|the reason (is|for)|triggered by|brought on by)\b", re.I)),
    ("promise", re.compile(r"\b(guarantee\w*|definitely will|cure[sd]?|will fix|will improve|will reverse|proven to|clinically proven)\b", re.I)),
    ("link", _URL),
    ("contact", re.compile(_EMAIL.pattern + "|" + _NRIC.pattern, re.I)),
    ("leak", re.compile(r"\b(system prompt|my instructions|my rules|as an ai language model|i was told to|the context (says|above|below))\b|(?-i:\bCONTEXT\b|\bQUESTION\b|<context>|<message>)", re.I)),
    ("markup", re.compile(r"```|<\s*/?\w+[^>]*>|\[[^\]]+\]\(https?://")),
]


NEUTRAL_RULES = {"link", "contact", "leak", "markup"}      # the rules that do not depend on the language of the reply


def reply_problems(reply: str, neutral_only: bool = False) -> list[str]:
    """Why a model reply must not be shown. Empty means it passed. The word rules run on the ENGLISH text of the reply; for a reply in
    another language only the neutral rules (links, contact details, leaked instructions, markup) run on it directly."""
    text = _GOOD_PHRASE.sub("", _REFUSALS.sub("", _REFUSED_VERDICT.sub("", _QUOTED_QUESTION.sub("", _ALLOWED_DIAGNOSE.sub("", reply or "")))))
    return [name for name, rx in REPLY_RULES if (not neutral_only or name in NEUTRAL_RULES) and rx.search(text)]


def tidy_reply(reply: str, max_words: int = 130) -> str:
    """Plain text: no markdown, no emoji, cut at a sentence end when it is too long."""
    s = re.sub(r"[*_`#>]+", "", reply or "")
    s = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]", "", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    words = s.split()
    if len(words) <= max_words:
        return s
    cut = " ".join(words[:max_words])
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    return (cut[:end + 1] if end > 40 else cut.rstrip(",;:") + ".").strip()


# ----------------------------------------------------------------------------- the part of a reply that code always adds
@dataclass(frozen=True)
class Signpost:
    text_key: str                 # a key in texts.CATALOG
    to: str | None = None         # a route id of the app, opened by a button
    label: str | None = None      # the button label (English; the app translates the screen's own words)


def signposts(intent: str, wants_food: bool, noticed: bool) -> list[Signpost]:
    """Where in the app to look next, chosen by code from the triage labels. The model never decides a link."""
    out: list[Signpost] = []
    if wants_food or intent == "food_ideas":
        out.append(Signpost("chat.sign_food", "K11", "Open Review suggestions"))
        out.append(Signpost("chat.sign_food", "E8", "Open Lunch ideas"))
    if noticed or intent == "insights":
        out.append(Signpost("chat.sign_insights", "C1", "Open Insights, Overview"))
    if intent == "medicine_info":
        out.append(Signpost("chat.sign_meds", "H1", "Open my medicines"))
    if intent == "appointments":
        out.append(Signpost("chat.sign_care", "K3", "Open my care plan"))
    return out


def signpost_text_keys(posts: list[Signpost]) -> list[str]:
    """One sentence per kind of signpost, in order, whatever the number of buttons."""
    keys: list[str] = []
    for p in posts:
        if p.text_key not in keys:
            keys.append(p.text_key)
    return keys


def needs_doctor_referral(intent: str, symptom_flag: bool) -> bool:
    """A symptom, a medicine question or a request for advice always ends with a pointer to the doctor."""
    return symptom_flag or intent in ("symptoms", "medicine_info", "diagnosis_request", "medicine_change")


def offers_doctor_question(intent: str, symptom_flag: bool) -> bool:
    """Whether to ask "Would you like to add this to your doctor questions?" (a button; nothing is added until the person taps it)."""
    return symptom_flag or intent in ("symptoms", "diagnosis_request", "medicine_change", "medicine_info")


# ----------------------------------------------------------------------------- how fast a person can send
class RateLimiter:
    """At most `limit` messages in `window_s` seconds for one person, kept in memory (one process). It stops a script or a stuck key from
    spending the day's AI budget; it is not a security boundary on its own."""

    def __init__(self, limit: int = 12, window_s: int = 120) -> None:
        self.limit, self.window_s = limit, window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        t = time.monotonic() if now is None else now
        with self._lock:
            q = self._hits[key]
            while q and t - q[0] > self.window_s:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(t)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


LIMITER = RateLimiter()
