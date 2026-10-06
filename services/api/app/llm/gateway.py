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
    """No credentials, or the model could not be reached."""


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
    """Send one image and an instruction; get back a validated object of `schema`."""
    from google.genai import types

    model = model or settings.llm_vision_model
    if not usage.allowed("vertex_vision"):
        raise LLMUnavailable("The daily AI limit has been reached.")
    try:
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
    except Exception as e:  # network, quota, permission: the caller shows "could not read, try again"
        logger.exception("vision call failed model=%s", model)
        raise LLMUnavailable(str(e)[:200]) from e
    um = getattr(resp, "usage_metadata", None)
    usage.record("vertex_vision", getattr(um, "prompt_token_count", 0) or 0, getattr(um, "candidates_token_count", 0) or 0)
    if resp.parsed is not None and isinstance(resp.parsed, schema):
        return resp.parsed
    try:
        return schema.model_validate_json(resp.text or "")
    except Exception as e:
        raise LLMUnavailable(f"The model answered in an unexpected format: {e}") from e
