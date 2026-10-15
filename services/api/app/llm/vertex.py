"""Gateway to Gemini on Vertex AI (docs/specs/ai-models.md, D-059).

All model calls go through here: timeout, retry with backoff for 429 and 5xx, token and latency counts.
Nothing from the request or the answer is logged (rules.md section 3: no health values in logs).
Authentication is the Vertex API key in the `x-goog-api-key` header, never in the URL.
"""
from __future__ import annotations

import base64
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

import requests

from app.core.errors import ExternalServiceError

USER_AGENT = "smart-health-backend/0.1"
RETRY_STATUS = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class ImagePart:
    data: bytes
    mime_type: str = "image/jpeg"


@dataclass(frozen=True)
class GenerationResult:
    text: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int


@dataclass(frozen=True)
class WebSource:
    title: str
    url: str


@dataclass(frozen=True)
class GroundedResult(GenerationResult):
    sources: list[WebSource]


class VertexClient:
    def __init__(
        self,
        api_key: str,
        project: str,
        region: str = "global",
        *,
        timeout_s: float = 45.0,  # rules.md section 6: vision 45 s
        max_retries: int = 3,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise ExternalServiceError("GOOGLE_API_KEY is not set", code="llm_not_configured")
        self._key = api_key
        self._project = project
        self._region = region
        self._timeout = timeout_s
        self._retries = max_retries
        self._session = session or requests.Session()
        self._sleep = sleep

    def _url(self, model: str) -> str:
        host = "aiplatform.googleapis.com" if self._region == "global" else f"{self._region}-aiplatform.googleapis.com"
        return (f"https://{host}/v1/projects/{self._project}/locations/{self._region}"
                f"/publishers/google/models/{model}:generateContent")

    def generate_json(
        self,
        *,
        model: str,
        system: str,
        parts: Sequence[ImagePart | str],
        response_schema: Mapping[str, Any],
        max_output_tokens: int = 4096,
    ) -> GenerationResult:
        """One call that must return JSON matching `response_schema`. The caller validates it (Pydantic) and decides on retries."""
        body_parts: list[dict[str, Any]] = []
        for p in parts:
            if isinstance(p, str):
                body_parts.append({"text": p})
            else:
                body_parts.append({"inlineData": {"mimeType": p.mime_type, "data": base64.b64encode(p.data).decode()}})
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": body_parts}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": response_schema,
                "temperature": 0.0,
                "maxOutputTokens": max_output_tokens,
            },
        }
        started = time.monotonic()
        return self._parse(self._post(model, body), model, started)

    def generate_grounded(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        max_output_tokens: int = 8192,
        timeout_s: float = 90.0,
    ) -> GroundedResult:
        """One call that may search the web (Google Search grounding) before it answers. The answer is plain text (the model cannot
        be forced into JSON while it searches), so the caller must parse and validate it. The web pages used come back as `sources`.
        Only the prompt text leaves the machine: callers must keep personal details out of it."""
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "tools": [{"googleSearch": {}}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": max_output_tokens},
        }
        started = time.monotonic()
        j = self._post(model, body, timeout_s=timeout_s)
        res = self._parse(j, model, started)
        sources = self._sources(j)
        return GroundedResult(text=res.text, model=model, input_tokens=res.input_tokens, output_tokens=res.output_tokens,
                              latency_ms=res.latency_ms, sources=sources)

    def _post(self, model: str, body: Mapping[str, Any], *, timeout_s: float | None = None) -> Mapping[str, Any]:
        """POST with the retry rules of rules.md section 6 (429 and 5xx retried with backoff, other 4xx refused at once)."""
        headers = {"x-goog-api-key": self._key, "Content-Type": "application/json", "User-Agent": USER_AGENT}
        last = "no attempt"
        for attempt in range(self._retries + 1):
            try:
                r = self._session.post(self._url(model), json=body, headers=headers, timeout=timeout_s or self._timeout)
            except requests.RequestException as e:  # timeouts and connection errors are retried too
                last = type(e).__name__
            else:
                if r.status_code == 200:
                    return r.json()  # type: ignore[no-any-return]
                last = f"HTTP {r.status_code}"
                if r.status_code not in RETRY_STATUS:  # no retry on other 4xx
                    raise ExternalServiceError(f"model call refused ({last})", code="llm_refused")
            if attempt < self._retries:
                self._sleep(min(8.0, 0.5 * (2 ** attempt)) + random.uniform(0, 0.25))
        raise ExternalServiceError(f"model call failed ({last})", code="llm_unavailable")

    @staticmethod
    def _sources(j: Mapping[str, Any]) -> list[WebSource]:
        """The web pages the answer was based on, from the grounding metadata. Links are Google's redirect links to the page."""
        try:
            chunks = j["candidates"][0]["groundingMetadata"]["groundingChunks"]
        except (KeyError, IndexError, TypeError):
            return []
        seen: set[str] = set()
        out: list[WebSource] = []
        for ch in chunks:
            web = (ch or {}).get("web") or {}
            uri = web.get("uri")
            if not uri or uri in seen or not str(uri).startswith("https://"):
                continue
            seen.add(uri)
            out.append(WebSource(title=str(web.get("title") or "Web page")[:120], url=str(uri)))
        return out

    @staticmethod
    def _parse(j: Mapping[str, Any], model: str, started: float) -> GenerationResult:
        try:
            cand = j["candidates"][0]
            text = "".join(p.get("text", "") for p in cand["content"]["parts"] if not p.get("thought"))
        except (KeyError, IndexError, TypeError):
            reason = (j.get("promptFeedback") or {}).get("blockReason", "no candidates")
            raise ExternalServiceError(f"model returned no answer ({reason})", code="llm_empty") from None
        usage = j.get("usageMetadata") or {}
        return GenerationResult(
            text=text.strip(), model=model,
            input_tokens=usage.get("promptTokenCount"), output_tokens=usage.get("candidatesTokenCount"),
            latency_ms=int((time.monotonic() - started) * 1000),
        )
