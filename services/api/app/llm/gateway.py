"""One door to the model (docs/specs/ai-models.md): Gemini on Vertex AI.

Auth: a service-account file (GOOGLE_APPLICATION_CREDENTIALS) with project and region when one is configured,
otherwise the Vertex AI express-mode key (GOOGLE_API_KEY). The model name comes from configuration, so it can be
swapped without touching callers.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import TypeVar

from pydantic import BaseModel

from app.core.config import settings
from app.services import usage

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LLMUnavailable(RuntimeError):
    """No credentials, the model could not be reached, or its answer could not be used.

    `code` is a stable name the screens can act on: model_unavailable, daily_limit, timeout or bad_response.
    """

    def __init__(self, message: str, code: str = "model_unavailable") -> None:
        super().__init__(message)
        self.code = code


def _error_code(e: Exception) -> str:
    """Map a failed model call to a stable code: a time-out, or any other failure of the model or the network."""
    text = str(e).lower()
    if isinstance(e, TimeoutError) or "timeout" in type(e).__name__.lower() or "timed out" in text or "deadline" in text:
        return "timeout"
    return "model_unavailable"


@lru_cache(maxsize=1)
def _client():
    from google import genai

    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if creds and os.path.exists(creds) and settings.google_cloud_project:
        return genai.Client(vertexai=True, project=settings.google_cloud_project, location=settings.google_cloud_region)
    if settings.google_api_key:
        # Express mode cannot be combined with a project or location, so keep them out of the environment.
        for k in ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION", "GOOGLE_APPLICATION_CREDENTIALS"):
            os.environ.pop(k, None)
        return genai.Client(vertexai=True, api_key=settings.google_api_key)
    raise LLMUnavailable("No Vertex AI credentials: set GOOGLE_API_KEY or GOOGLE_APPLICATION_CREDENTIALS in .env")


def vision_json(image: bytes, mime_type: str, prompt: str, schema: type[T], model: str | None = None) -> T:
    """Send one image and an instruction; get back a validated object of `schema`. Every failure raises LLMUnavailable with a code."""
    model = model or settings.llm_vision_model
    if not usage.allowed("vertex_vision"):
        raise LLMUnavailable("The daily AI limit has been reached.", code="daily_limit")
    try:
        # the import is inside the try: a missing google-genai package must end as LLMUnavailable, not as a crash
        from google.genai import types

        resp = _client().models.generate_content(
            model=model,
            contents=[types.Part.from_bytes(data=image, mime_type=mime_type), prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.2,
                http_options=types.HttpOptions(timeout=settings.llm_timeout_s * 1000),
            ),
        )
    except LLMUnavailable:
        raise
    except Exception as e:  # network, quota, permission, timeout: the caller shows a plain message and offers manual entry
        logger.error("vision call failed model=%s type=%s", model, type(e).__name__)
        raise LLMUnavailable(str(e)[:200], code=_error_code(e)) from e
    um = getattr(resp, "usage_metadata", None)
    usage.record("vertex_vision", getattr(um, "prompt_token_count", 0) or 0, getattr(um, "candidates_token_count", 0) or 0)
    if resp.parsed is not None and isinstance(resp.parsed, schema):
        return resp.parsed
    try:
        return schema.model_validate_json(resp.text or "")
    except Exception as e:
        raise LLMUnavailable("The model answered in an unexpected format.", code="bad_response") from e


def text_json(system: str, prompt: str, schema: type[T], model: str | None = None) -> T:
    """Text only (no image) in, a validated object of `schema` out, as JSON. Used by the doctor report's key findings.

    Every failure raises LLMUnavailable with a code, so the caller can fall back to the code-written text.
    """
    from app.llm import chat

    model = model or chat.model_name()
    if not usage.allowed("vertex_generate"):
        raise LLMUnavailable("The daily AI limit has been reached.", code="daily_limit")
    try:
        from google.genai import types

        resp = _client().models.generate_content(
            model=model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.2,
                # thinking tokens count against the output limit: a small thinking budget keeps the JSON from being cut off
                thinking_config=types.ThinkingConfig(thinking_budget=512),
                max_output_tokens=4096,
                http_options=types.HttpOptions(timeout=settings.llm_timeout_s * 1000),
            ),
        )
    except LLMUnavailable:
        raise
    except Exception as e:
        logger.error("text call failed model=%s type=%s", model, type(e).__name__)
        raise LLMUnavailable(str(e)[:200], code=_error_code(e)) from e
    um = getattr(resp, "usage_metadata", None)
    usage.record("vertex_generate", getattr(um, "prompt_token_count", 0) or 0, getattr(um, "candidates_token_count", 0) or 0)
    reason =str(getattr(resp.candidates[0], "finish_reason", "")) if getattr(resp, "candidates", None) else ""
    if "MAX_TOKENS" in reason:
        raise LLMUnavailable("The model ran out of room before it finished.", code="bad_response")   # a cut-off answer is never used
    if resp.parsed is not None and isinstance(resp.parsed, schema):
        return resp.parsed
    try:
        return schema.model_validate_json(resp.text or "")
    except Exception as e:
        raise LLMUnavailable("The model answered in an unexpected format.", code="bad_response") from e
