"""JEV decision gateway (docs/specs/memory.md section 5): small typed answers with a calibrated confidence.

JEV only classifies and ranks. It is never asked to relax a guard, and its answer never overrides a rule. Every function
returns None when JEV is unreachable or answers in an unexpected shape, and callers must then take the conservative path.
The state sent here must already be free of names, NRIC numbers, phone numbers, emails and addresses; `deidentify` is a
last-line scrub, not a licence to send identifiers.
"""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.core.config import settings
from app.services import usage

logger = logging.getLogger(__name__)

_NRIC = re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.I)
_PHONE = re.compile(r"(?<!\d)(?:\+?65[\s-]?)?[689]\d{3}[\s-]?\d{4}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def deidentify(text: str) -> str:
    return _EMAIL.sub("[email]", _PHONE.sub("[phone]", _NRIC.sub("[id]", text)))[:2000]


@dataclass
class Choice:
    choice: str
    probabilities: dict[str, float]
    confidence: float


def _key() -> str:
    return os.environ.get("OPEN_ROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY") or ""


def _post(state: str, questions: dict) -> dict | None:
    key = _key()
    if not key:
        logger.warning("JEV key missing: taking the conservative path")
        return None
    if not usage.allowed("jev"):
        logger.warning("daily AI cap reached: JEV is treated as unavailable")
        return None
    body = json.dumps({"model": settings.jev_model, "state": deidentify(state), "questions": questions}).encode()
    req = urllib.request.Request(settings.jev_base_url, data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=settings.jev_timeout_s) as r:
            resp = json.loads(r.read())
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        logger.warning("JEV unavailable: %s", e)
        return None
    u = resp.get("usage") or {}
    usage.record("jev", u.get("input_tokens", 0), u.get("output_tokens", 0), u.get("cost"))
    return resp.get("answers")


def noul(state: str, instructions: str) -> float | None:
    """Probability of yes, or None when JEV cannot answer."""
    a = _post(state, {"q": {"type": "noul", "instructions": instructions}})
    try:
        return float(a["q"]["noul"]) if a else None
    except (KeyError, TypeError, ValueError):
        return None


def choice(state: str, instructions: str, criteria: dict[str, str]) -> Choice | None:
    a = _post(state, {"q": {"type": "choice", "instructions": instructions, "criteria": criteria}})
    try:
        r = a["q"] if a else None
        return Choice(r["choice"], {k: float(v) for k, v in r["probabilities"].items()}, float(r["confidence"])) if r else None
    except (KeyError, TypeError, ValueError):
        return None


def score(state: str, instructions: str, levels: list[str]) -> float | None:
    """Expected level as a number from 0 to len(levels) - 1, or None."""
    a = _post(state, {"q": {"type": "score", "instructions": instructions, "criteria": levels}})
    try:
        return float(a["q"]["score"]) if a else None
    except (KeyError, TypeError, ValueError):
        return None


def choice_batch(state: str, questions: dict[str, tuple[str, dict[str, str]]]) -> dict[str, Choice]:
    """Several `choice` questions in one request: {id: (instructions, criteria)}. Missing or unreadable answers are left out."""
    a = _post(state, {k: {"type": "choice", "instructions": ins, "criteria": crit} for k, (ins, crit) in questions.items()})
    out: dict[str, Choice] = {}
    for k in questions:
        try:
            r = a[k]
            out[k] = Choice(r["choice"], {x: float(v) for x, v in r["probabilities"].items()}, float(r["confidence"]))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def noul_batch(state: str, questions: dict[str, str]) -> dict[str, float]:
    """Several yes/no questions in one request: {id: instructions}. Returns the probability of yes for each answered one."""
    a = _post(state, {k: {"type": "noul", "instructions": ins} for k, ins in questions.items()})
    out: dict[str, float] = {}
    for k in questions:
        try:
            out[k] = float(a[k]["noul"])
        except (KeyError, TypeError, ValueError):
            continue
    return out


# ----------------------------------------------------------------------------- the frozen guard questions
# Versioned code, not data: no learning path may write here (learning-loop.md section 5).
GUARD_VERSION = "2026-10-06.1"
GUARD_QUESTIONS = {
    "med_advice": "Does the text tell or ask someone to stop, skip, double, delay or change a medicine or its dose?",
    "diagnosis": "Does the text say or ask what medical condition a person has, or tell them they have or do not have a condition?",
    "urgent": "Does the text describe an urgent symptom such as chest pain, fainting, confusion or very low glucose?",
}


def guard(text: str) -> dict[str, float | None]:
    """Run the three frozen guard questions on a piece of text in ONE request. None means JEV could not answer that question."""
    got = noul_batch(text, GUARD_QUESTIONS)
    return {k: got.get(k) for k in GUARD_QUESTIONS}


def guard_blocks(text: str) -> tuple[bool, dict[str, float | None]]:
    """True when the text must not be shown: any question is yes at or above the floor, or JEV could not answer (conservative path)."""
    res = guard(text)
    floor = settings.jev_guard_floor
    blocked = any(v is None or v >= (1 - floor) for v in res.values())
    return blocked, res
