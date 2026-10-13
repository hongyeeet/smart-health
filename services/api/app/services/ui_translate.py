"""Translate model-written English that is shown on a screen (the medicine explanation) into the language the person chose.

Fixed wording lives in `texts.py` and `texts_ui.json` and is reviewed. This module is only for text that has no fixed form, such as the
short explanation of a medicine that the model wrote in English. It never adds, removes or softens anything: the model is told to translate
only, and an answer is used only when it has the same number of parts and keeps every number. Any failure (no key, a daily limit, a
time-out, a bad answer) returns the English unchanged, so the screen always works.

A translation is kept in memory for the life of the server (keyed by the exact English), so a medicine page costs one model call per
language, not one per visit. Nothing about the person goes in: only the English explanation text. Machine translations wait for review
(docs/review/translations.md).
"""
from __future__ import annotations

import logging
import re
from typing import Sequence

from pydantic import BaseModel

from app.llm import gateway
from app.services import texts

logger = logging.getLogger(__name__)
_CACHE: dict[tuple[str, str], str] = {}
_NUMBERS = re.compile(r"\d+(?:[.,]\d+)?")

_SYSTEM = """You translate short health information texts for a diabetes companion app used by older adults in Singapore.
Target language: {language}.
Rules:
- Translate faithfully. Do not add, remove, soften or strengthen anything. Do not add advice, a diagnosis or reassurance that is not in the English.
- Keep every number, unit, medicine name, web address and the emergency number 995 exactly as written.
- Keep the plain, calm tone and short sentences. Use the polite everyday register.
- Warnings and "contact your doctor or pharmacist" wording must keep exactly the same meaning.
Return JSON: {{"items": [one translation per input, in the same order]}}."""


class _Out(BaseModel):
    items: list[str]


def _ok(english: str, translated: str) -> bool:
    return bool(translated.strip()) and sorted(_NUMBERS.findall(english)) == sorted(_NUMBERS.findall(translated))


def translate(lang: str | None, strings: Sequence[str]) -> list[str]:
    """`strings` in `lang` (the request's language when `lang` is None). English or any problem: the strings as they are."""
    lg = lang or texts.request_lang()
    out = list(strings)
    if lg not in texts.LANGS or lg == "en":
        return out
    todo = [i for i, s in enumerate(strings) if s and s.strip() and (lg, s) not in _CACHE]
    if todo:
        try:
            prompt = "Translate each text. Return one translation per text, in order.\n\n" + "\n".join(f"{n + 1}. {strings[i]}" for n, i in enumerate(todo))
            res = gateway.text_json(_SYSTEM.format(language=texts.LANG_NAMES[lg]), prompt, _Out)
            if len(res.items) == len(todo):
                for i, tr in zip(todo, res.items):
                    if _ok(strings[i], tr):
                        _CACHE[(lg, strings[i])] = tr.strip()
        except Exception:  # noqa: BLE001 - a failed translation is English, never an error on the screen
            logger.warning("could not translate text to %s; showing English", lg)
    return [_CACHE.get((lg, s), s) if s else s for s in strings]
