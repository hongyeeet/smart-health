"""Medicine clash checker, the AI half (prd F5, docs/specs/f5-clash.md).

The model searches the web (Google Search grounding) and names pairs from the person's medicine list that may clash. Code then decides
what may be kept, so the model can only ever ADD a flag:

  - the model refers to medicines by their number in the list; a number outside the list, or a medicine paired with itself, is dropped
  - a flag needs at least one web page behind it (no sources: the model's flags are discarded and the run is reported as failed)
  - the reason sentences go through the same filter as the medicine explainer: any sentence that gives a dose or tells the person to stop,
    skip, change or swap a medicine, or calls something "safe", is dropped
  - the model can never remove a flag the drug-pair rules found: that merge is done by the caller

Only the names, strengths and types of the person's medicines are sent. No name, ID or other personal detail. Nothing from the prompt or the
answer is logged.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Sequence

from pydantic import BaseModel, ConfigDict, ValidationError

from app.agents.med_explainer import clean_text, pick_sources
from app.core.errors import ExternalServiceError
from app.llm.vertex import VertexClient, WebSource

log = logging.getLogger(__name__)
PROMPT_PATH = Path(__file__).parent / "prompts" / "clash_check.md"
VERIFY_PATH = Path(__file__).parent / "prompts" / "clash_verify.md"
KIND_WORD = {"prescription": "prescription", "otc": "over the counter", "supplement": "supplement", "tcm": "herbal"}


@dataclass(frozen=True)
class Medicine:
    id: str
    name: str
    strength: str | None
    kind: str


@dataclass(frozen=True)
class AiPair:
    a: str                      # medicine id
    b: str
    summary: str


@dataclass
class ClashOutcome:
    status: Literal["done", "failed"]
    pairs: list[AiPair] = field(default_factory=list)
    sources: list[WebSource] = field(default_factory=list)
    reason: str | None = None   # why it failed: service_unavailable, invalid_answer, no_sources
    model_id: str = ""
    prompt_version: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


class RawPair(BaseModel):
    model_config = ConfigDict(extra="ignore")
    a: int
    b: int
    summary: str = ""


class RawConfirmed(BaseModel):
    model_config = ConfigDict(extra="ignore")
    confirmed: list[RawPair] = []


class RawClash(BaseModel):
    model_config = ConfigDict(extra="ignore")
    pairs: list[RawPair] = []


def load_prompt() -> tuple[str, str]:
    text = PROMPT_PATH.read_text(encoding="utf-8")
    first, _, rest = text.partition("\n")
    return rest.strip(), first.removeprefix("version:").strip()


def load_verify() -> str:
    return VERIFY_PATH.read_text(encoding="utf-8").partition("\n")[2].strip()


def build_verify_prompt(meds: Sequence[Medicine], pairs: Sequence[AiPair]) -> str:
    index = {m.id: i for i, m in enumerate(meds, 1)}
    lines = ["The person's medicines:"]
    lines += [f"{i}. {' '.join(m.name.split())} ({KIND_WORD.get(m.kind, m.kind)})" for i, m in enumerate(meds, 1)]
    lines.append("Suspected pairs to verify: " + "; ".join(f"{index[p.a]} and {index[p.b]}" for p in pairs))
    lines.append("Search the web for each pair, then return the JSON object.")
    return "\n".join(lines)


def build_prompt(meds: Sequence[Medicine]) -> str:
    lines = ["The person's medicines:"]
    for i, m in enumerate(meds, 1):
        lines.append(f"{i}. {' '.join(m.name.split())}{', ' + m.strength.strip() if m.strength and m.strength.strip().lower() not in m.name.lower() else ''} ({KIND_WORD.get(m.kind, m.kind)})")
    lines.append("Search the web, then return the JSON object. An empty pairs list means nothing was found.")
    return "\n".join(lines)


def parse_answer(text: str) -> RawClash:
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the answer")
    return RawClash.model_validate(json.loads(t[start:end + 1]))


def _short(m: Medicine) -> str:
    """The name without its strength, for use inside a sentence ('Atorvastatin 20 mg' -> 'Atorvastatin')."""
    n = " ".join(m.name.split())
    if m.strength:
        n = re.sub(re.escape(" ".join(m.strength.split())), "", n, flags=re.I).strip(" ,-")
    return re.sub(r"[\s,\-]*\d+(?:[.,]\d+)?\s?(?:mg|mcg|µg|g|ml|iu|%)\s*$", "", n, flags=re.I).strip(" ,-") or n


def _name_the_numbers(text: str, ia: int, ib: int, meds: Sequence[Medicine]) -> str:
    """The model sometimes writes the list numbers in its sentences ('6 can raise the level of 2'): put the names back."""
    for i in (ia, ib):
        text = re.sub(rf"(?<![\w.]){i}(?![\w.%])", _short(meds[i - 1]), text)
    return text


def valid_pairs(raw: RawClash, meds: Sequence[Medicine]) -> list[AiPair]:
    """Keep real, distinct pairs once each, with a reason cleaned of dose and treatment advice."""
    seen: set[frozenset[int]] = set()
    out: list[AiPair] = []
    for p in raw.pairs:
        if not (1 <= p.a <= len(meds) and 1 <= p.b <= len(meds)) or p.a == p.b or frozenset((p.a, p.b)) in seen:
            continue
        seen.add(frozenset((p.a, p.b)))
        out.append(AiPair(meds[p.a - 1].id, meds[p.b - 1].id, clean_text(_name_the_numbers(p.summary, p.a, p.b, meds))))
    return out


def _verify(client: VertexClient, *, model: str, meds: Sequence[Medicine], pairs: list[AiPair]) -> tuple[bool, list[AiPair], list[WebSource], int, int, int]:
    """The model named pairs without a web page behind them. Ask it, with search on, about exactly those pairs and keep the ones it confirms.

    Returns (the call worked, the confirmed pairs, the pages it used, tokens in, tokens out, milliseconds). A confirmed pair is kept even if the
    search returned no page: it is a precaution that only says "may clash, check with your pharmacist", and the page labels it as an AI
    suggestion with no web page. If the call itself fails, nothing is kept."""
    try:
        res = client.generate_grounded(model=model, system=load_verify(), prompt=build_verify_prompt(meds, pairs), timeout_s=120.0)
        raw = RawConfirmed.model_validate(json.loads(_json_text(res.text)))
    except (ExternalServiceError, ValueError, ValidationError) as e:
        log.warning("clash verification failed: %s", type(e).__name__)
        return False, [], [], 0, 0, 0
    ids = {m.id: i for i, m in enumerate(meds, 1)}
    ok = {frozenset((c.a, c.b)) for c in raw.confirmed}
    kept = [p for p in pairs if frozenset((ids[p.a], ids[p.b])) in ok]
    return True, kept, pick_sources(res.sources), res.input_tokens or 0, res.output_tokens or 0, res.latency_ms


def _json_text(text: str) -> str:
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the answer")
    return t[start:end + 1]


def check(client: VertexClient, *, model: str, meds: Sequence[Medicine]) -> ClashOutcome:
    """Ask the model which pairs may clash. Never raises for a model or search failure: that comes back as `failed`.

    Flags should have a web page behind them. When the model names pairs without one, a second call asks it to search for exactly those pairs
    and only the pairs it confirms are kept (with a page if the search found one). A single unchecked answer from memory is never kept."""
    system, version = load_prompt()
    base = ClashOutcome(status="failed", model_id=model, prompt_version=version)
    if len(meds) < 2:
        return ClashOutcome(status="done", model_id=model, prompt_version=version)
    prompt = build_prompt(meds)
    pairs: list[AiPair] = []
    sources: list[WebSource] = []
    parsed = False
    tokens_in = tokens_out = latency = 0
    for attempt in range(2):          # an unreadable answer is retried once, then it fails safe
        try:
            res = client.generate_grounded(model=model, system=system, prompt=prompt, timeout_s=120.0)
        except ExternalServiceError as e:
            log.warning("clash check model call failed: %s", e.code)
            base.reason = "service_unavailable"
            return base
        tokens_in += res.input_tokens or 0
        tokens_out += res.output_tokens or 0
        latency += res.latency_ms
        try:
            raw = parse_answer(res.text)
        except (ValueError, ValidationError) as e:
            log.warning("clash answer was not valid (attempt %d): %s", attempt + 1, type(e).__name__)
            continue
        pairs, sources, parsed = valid_pairs(raw, meds), pick_sources(res.sources), True
        break
    if not parsed:
        base.input_tokens, base.output_tokens, base.latency_ms = tokens_in, tokens_out, latency
        base.reason = "invalid_answer"
        return base
    if pairs and not sources:
        log.warning("clash answer had flags but no web source: verifying")
        worked, pairs, sources, ti, to, lat = _verify(client, model=model, meds=meds, pairs=pairs)
        tokens_in, tokens_out, latency = tokens_in + ti, tokens_out + to, latency + lat
        if not worked:                # the second look could not be made: flags from memory alone are not kept, and the check is incomplete
            base.input_tokens, base.output_tokens, base.latency_ms = tokens_in, tokens_out, latency
            base.reason = "no_sources"
            return base
    return ClashOutcome(status="done", pairs=pairs, sources=sources, model_id=model, prompt_version=version, input_tokens=tokens_in,
                        output_tokens=tokens_out, latency_ms=latency)
