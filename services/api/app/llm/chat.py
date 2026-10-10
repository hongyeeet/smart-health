"""Plain text generation for the chat (screen I1): one call to Gemini on Vertex AI, through the same cached client as gateway.py.

It sends only the de-identified prompt it is given and returns the model's words. It does not judge them: the caller runs the
guard on the reply and takes the conservative path when the guard blocks it or the model cannot be reached.
"""
from __future__ import annotations

import logging
import os

from app.core.config import settings
from app.llm.gateway import LLMUnavailable, _client
from app.services import usage

logger = logging.getLogger(__name__)
MAX_OUTPUT_TOKENS = 2048   # thinking tokens count against this; the prompt keeps the visible reply under 120 words
# ai_usage_daily only accepts vertex_vision, vertex_embed and jev (a database check). Chat is Gemini too, so it is counted under vertex_vision
# until a migration adds a vertex_chat provider.
PROVIDER = "vertex_vision"


def model_name() -> str:
    # LLM_CHAT_MODEL is in .env (docs/specs/ai-models.md); fall back to the vision model name if it is missing
    return os.environ.get("LLM_CHAT_MODEL") or settings.llm_vision_model


def generate(system: str, history: list[tuple[str, str]], user_text: str) -> str:
    """history is [(role, text)] with role user or assistant, oldest first. Raises LLMUnavailable on any failure."""
    from google.genai import types

    if not usage.allowed(PROVIDER):
        raise LLMUnavailable("The daily AI limit has been reached.")
    contents = [types.Content(role="user" if r == "user" else "model", parts=[types.Part.from_text(text=t)]) for r, t in history]
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))
    try:
        resp = _client().models.generate_content(
            model=model_name(),
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.2,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                http_options=types.HttpOptions(timeout=settings.llm_timeout_s * 1000),
            ),
        )
    except LLMUnavailable:
        raise
    except Exception as e:  # network, quota, permission: the caller shows a calm fixed reply
        logger.exception("chat call failed")
        raise LLMUnavailable(str(e)[:200]) from e
    um = getattr(resp, "usage_metadata", None)
    usage.record(PROVIDER, getattr(um, "prompt_token_count", 0) or 0, getattr(um, "candidates_token_count", 0) or 0)
    text = (resp.text or "").strip()
    reason = str(getattr(resp.candidates[0], "finish_reason", "")) if getattr(resp, "candidates", None) else ""
    if "MAX_TOKENS" in reason:  # a cut-off reply is never shown
        raise LLMUnavailable("The model ran out of room before it finished.")
    if not text:
        raise LLMUnavailable("The model returned no text.")
    return text
