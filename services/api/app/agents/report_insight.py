"""Key findings for the doctor report, worded by an AI (owner decision, 2026-10-11).

The code computes every number (`doctor_report.build`). This module only words them:

  1. the model is given the computed FACT lines of one report and nothing else (no names, no dates, no free text);
  2. it answers with 3 to 5 short labelled lines, as JSON (`gateway.text_json`);
  3. a line is kept only if every number in it appears in the facts, it has a plain label, and it has no advice, dose,
     stop/skip/change, "safe"/"normal"/"abnormal", good/bad or causal wording;
  4. if fewer than MIN_FINDINGS lines pass, or the model is unavailable, refused by the daily limit, or unusable, the
     code-written findings are shown instead (`source` = "rules"). The report never breaks and never waits on a second try.

The result is cached per person, period and facts (a fingerprint), so a page load or a print does not call the model again.
Nothing from the facts or the answer is logged; only the kind of failure is.
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from pydantic import BaseModel, ConfigDict

from app.llm import gateway
from app.llm.gateway import LLMUnavailable

log = logging.getLogger(__name__)
PROMPT_VERSION = "report-insight-1"
MIN_FINDINGS = 3
MAX_FINDINGS = 5
MAX_TEXT = 200                       # characters in one sentence
OK_TTL_S = 24 * 3600                 # a worded result is kept for a day (it is also keyed by the facts)
FAILED_TTL_S = 600                   # a failed try is not repeated for ten minutes
CACHE_MAX = 256

# Written for the model. The owner's rules: no advice, no dose, no stop/skip/change, no "safe"/"normal"/"abnormal", no causes.
SYSTEM_PROMPT = """You write the short labelled lines of a doctor report for an adult in Singapore who has type 2 diabetes. The doctor reads it, and the person reads it too.

You are given a list of FACTS. Each fact is a number or count that the app has already worked out from the person's own recorded data. These are the only numbers you may use. Do not calculate, estimate or add any number that is not in the facts.

Write 3 to 5 lines. Each line:
- has a label of one or two words (for example Glucose, Medicines, Symptoms, Activity, Alerts)
- has one idea in one short plain sentence of at most 25 words
- puts the number first where it can, and copies each number exactly as written in the facts
- says what was recorded, and nothing more

Rules you must keep:
- Give no advice of any kind. Do not tell the person or the doctor to do anything.
- Never use these words: stop, skip, change, double, safe, normal, abnormal, good, bad, better, worse, dose, take, avoid, should, must, need to.
- Never say one thing caused, led to, or was because of another. Symptoms are "logged together with" a glucose reading or a medicine; say that and nothing stronger.
- Do not name a diagnosis, a condition or a medicine that is not in the facts.
- Do not give dates, times of day that are not in the facts, names of people, or personal details.
- Do not call a result in or out of target as a judgement. "Time in range was 62%" is fine.
- Plain English that a patient can follow.

Answer only with a JSON object in this form: {"findings": [{"label": "...", "text": "..."}]}"""

NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
LABEL_RE = re.compile(r"^[A-Za-z][A-Za-z ]{0,23}$")
# Advice, doses, judgements and causes. A line with any of these is dropped (the word list is checked, not the meaning).
BANNED_RE = re.compile(
    r"\b(stop\w*|skip\w*|chang\w*|doubl\w*|halv\w*|reduc\w*|increas\w*|safe\w*|unsafe|normal\w*|abnormal\w*|good|bad|better|worse|"
    r"dose\w*|dosage\w*|tablets?|capsules?|mg|mcg|take|taking|takes|avoid\w*|should|must|need|needs|advis\w*|recommend\w*|consider\w*|"
    r"caus\w*|because|due|leads?|led|results?|resulting|diagnos\w*|cure\w*|risk\w*|try|ask|talk|see|improv\w*|worsen\w*)\b",
    re.I,
)

_CACHE: dict[tuple, tuple[float, list[str], str]] = {}


class Finding(BaseModel):
    model_config = ConfigDict(extra="ignore")
    label: str = ""
    text: str = ""


class FindingsOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    findings: list[Finding] = []


def numbers(text: str) -> list[float]:
    """Every number in a text, as a float. '08:00' gives 8 and 0, the same way for the facts and for the sentence."""
    return [float(x) for x in NUMBER_RE.findall(text)]


def line_problem(label: str, text: str, allowed: set[float]) -> str | None:
    """Why one line must not be shown, or None when it may be. The reason is a short word, never the text."""
    if not LABEL_RE.match(label):
        return "label"
    if BANNED_RE.search(label) or BANNED_RE.search(text):
        return "wording"
    if not 15 <= len(text) <= MAX_TEXT:
        return "length"
    if any(n not in allowed for n in numbers(text)):
        return "number"
    return None


def checked_lines(out: FindingsOut, facts: list[str]) -> tuple[list[str], list[str]]:
    """The lines that may be shown, as 'Label: sentence', and the reasons for the ones dropped."""
    allowed = {n for f in facts for n in numbers(f)}
    kept: list[str] = []
    rejected: list[str] = []
    for item in out.findings:
        label = " ".join(item.label.split())
        text = " ".join(item.text.split())
        problem = line_problem(label, text, allowed)
        if problem:
            rejected.append(problem)
            continue
        if text[-1] not in ".!":
            text += "."
        line = f"{label}: {text}"
        if line not in kept:
            kept.append(line)
    return kept[:MAX_FINDINGS], rejected


def _generate(facts: list[str]) -> FindingsOut:
    """The one call to the model. Tests replace this function; the production path is gateway.text_json."""
    prompt = "FACTS:\n" + "\n".join(f"- {f}" for f in facts)
    return gateway.text_json(SYSTEM_PROMPT, prompt, FindingsOut)


def _facts_hash(facts: list[str]) -> str:
    return hashlib.sha256("\n".join([PROMPT_VERSION, *facts]).encode("utf-8")).hexdigest()


def _store(key: tuple, expires: float, lines: list[str], source: str) -> None:
    while len(_CACHE) >= CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = (expires, lines, source)


def key_findings(facts: list[str], fallback: list[str], *, user_key: str, days: int, start: str, end: str) -> tuple[list[str], str]:
    """The key findings for one report: (lines, source) where source is "ai" or "rules". Never raises."""
    if len(facts) < 2:
        return list(fallback), "rules"
    now = time.monotonic()
    key = (user_key, days, start, end, _facts_hash(facts))
    hit = _CACHE.get(key)
    if hit and hit[0] > now:
        return list(hit[1]), hit[2]
    lines, source, ttl = list(fallback), "rules", FAILED_TTL_S
    try:
        out = _generate(facts)
    except LLMUnavailable as e:
        log.warning("key findings: code-written text used (model: %s)", e.code)
    except Exception as e:  # any other failure must not break the report
        log.warning("key findings: code-written text used (%s)", type(e).__name__)
    else:
        kept, rejected = checked_lines(out, facts)
        if len(kept) >= MIN_FINDINGS:
            lines, source, ttl = kept, "ai", OK_TTL_S
        else:
            log.warning("key findings: code-written text used (%d line(s) passed; dropped for: %s)", len(kept), ", ".join(sorted(set(rejected)) or ["none"]))
    _store(key, now + ttl, lines, source)
    return list(lines), source
