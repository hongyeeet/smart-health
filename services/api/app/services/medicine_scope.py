"""Is a medicine name one the app is for? (docs/specs/implementation-plan-2026-10-11.md section 4.2)

Equinox is for diabetes medicines and the medicines or supplements a person takes every day. The add screens say so, and a name
that is not on our drug list (`drug_reference` generic names and `drug_aliases`) gets a gentle note. The note never blocks a save and
never says the medicine is wrong or unsafe. Supplements and herbal products are not checked against the list (they are never on it).

The matching follows the clash checker (`clash_store.match_drugs`): a whole-word match of a term of at least five letters.
Pure matching lives here; `list_terms` is the only database read.
"""
from __future__ import annotations

import re
from typing import Iterable

import psycopg

MIN_TERM_LENGTH = 5
NOT_CHECKED_KINDS = ("supplement", "tcm")       # supplements and herbal products are described as not checked, never as out of scope


def _words(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", text.lower()).strip() + " "


def is_listed(name: str, terms: Iterable[str]) -> bool:
    """True when one of the list's terms appears in the name as whole words (`Metformin 500 mg` lists `metformin`)."""
    hay = _words(name)
    for term in terms:
        t = _words(term).strip()
        if len(t) >= MIN_TERM_LENGTH and f" {t} " in hay:
            return True
    return False


def list_terms(conn: psycopg.Connection) -> list[str]:
    """Every generic name and alias on the drug list. Global data: not tied to any user."""
    names = [r[0] for r in conn.execute("select generic_name from drug_reference").fetchall() if r[0]]
    names += [r[0] for r in conn.execute("select alias from drug_aliases").fetchall() if r[0]]
    return names


def out_of_scope(conn: psycopg.Connection, name: str, kind: str) -> bool:
    """A prescription or an over-the-counter medicine whose name is not on the drug list. An empty name is never out of scope."""
    if not name.strip() or kind in NOT_CHECKED_KINDS:
        return False
    return not is_listed(name, list_terms(conn))
