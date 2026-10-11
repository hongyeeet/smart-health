"""Saving and reading the medicine explanation (prd F3, docs/specs/f3-explainer.md), and the doctor questions asked from that page.

The explanation is made once per medicine and kept in `medication_explanations`. `input_hash` is a fingerprint of what it was written
from (name, strength, type, label directions): when the medicine changes the saved text is out of date and is made again.
The model call itself is in `app/agents/med_explainer.py`; this module only touches the database and never imports the agents.
Event payloads hold ids, counts and enums only, never names or health values (rules.md section 3).
"""
from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

import psycopg
from psycopg.types.json import Jsonb

from app.core.errors import NotFound


def input_hash(name: str, strength: str | None, kind: str, directions: str | None) -> str:
    key = "|".join(" ".join((p or "").lower().split()) for p in (name, strength, kind, directions))
    return hashlib.sha256(key.encode()).hexdigest()


def get_medicine(conn: psycopg.Connection, user_id: str, med_id: str) -> dict[str, Any]:
    """The person's own medicine (a medicine that belongs to someone else is 'not found')."""
    try:
        row = conn.execute(
            "select name, strength, kind::text, description, total_quantity, start_date, source::text from medications "
            "where id = %s and user_id = %s and deleted_at is null", (med_id, user_id)).fetchone()
    except psycopg.errors.InvalidTextRepresentation:     # not a uuid
        conn.rollback()
        raise NotFound("Medicine not found") from None
    if row is None:
        raise NotFound("Medicine not found")
    keys = ("name", "strength", "kind", "description", "total_quantity", "start_date", "source")
    return dict(zip(keys, row, strict=True))


PARTS_COLUMN_SQL = ("select exists (select 1 from information_schema.columns where table_schema = 'public' "
                    "and table_name = 'medication_explanations' and column_name = 'parts')")
_parts_present = False          # migration 0033 found once, then remembered. A 'not yet' is checked again on the next call.


def parts_column_present(conn: psycopg.Connection) -> bool:
    """Whether migration 0033 (the `parts` column) is applied. Until it is, the four parts are neither read nor written: every explanation
    is then the older layout, and the medicine page still works (the database may be at an older revision)."""
    global _parts_present
    if not _parts_present:
        row = conn.execute(PARTS_COLUMN_SQL).fetchone()
        _parts_present = bool(row and row[0])
    return _parts_present


def reset_parts_cache() -> None:
    global _parts_present
    _parts_present = False


def load(conn: psycopg.Connection, user_id: str, med_id: str) -> dict[str, Any] | None:
    cols = "status, purpose, side_effects, tell_doctor, sources, input_hash, generated_at"
    if parts_column_present(conn):
        cols += ", parts"
    row = conn.execute(f"select {cols} from medication_explanations where medication_id = %s and user_id = %s", (med_id, user_id)).fetchone()
    if row is None:
        return None
    keys = tuple(c.strip() for c in cols.split(","))
    out = dict(zip(keys, row, strict=True))
    out.setdefault("parts", None)                    # no column yet: every explanation is the older layout
    return out


def is_old_shape(saved: Mapping[str, Any] | None) -> bool:
    """A ready explanation made before the four parts existed. It still shows, but POST /explanation makes it again (when the column exists)."""
    return saved is not None and saved["status"] == "ready" and not saved.get("parts")


_SAVE_SQL = """insert into medication_explanations (medication_id, user_id, status, purpose, side_effects, tell_doctor, sources, input_hash,
                                                model_id, prompt_version, generated_at{parts_col})
           values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(){parts_val})
           on conflict (medication_id) do update set status = excluded.status, purpose = excluded.purpose, side_effects = excluded.side_effects,
             tell_doctor = excluded.tell_doctor, sources = excluded.sources, input_hash = excluded.input_hash, model_id = excluded.model_id,
             prompt_version = excluded.prompt_version, generated_at = now(){parts_set}"""


def save(conn: psycopg.Connection, user_id: str, med_id: str, *, status: str, purpose: str, side_effects: Sequence[str], tell_doctor: str,
         sources: Sequence[Mapping[str, str]], input_key: str, model_id: str, prompt_version: str, tokens_in: int = 0,
         tokens_out: int = 0, parts: Mapping[str, str] | None = None) -> None:
    """Keep (or replace) the explanation of one medicine. One transaction with the event log entry. The parts are kept only when the
    column exists; without it the explanation is saved in the older layout."""
    values: tuple[Any, ...] = (med_id, user_id, status, purpose or None, Jsonb(list(side_effects)), tell_doctor or None,
                               Jsonb([dict(s) for s in sources]), input_key, model_id, prompt_version)
    if parts_column_present(conn):
        sql = _SAVE_SQL.format(parts_col=", parts", parts_val=", %s", parts_set=", parts = excluded.parts")
        conn.execute(sql, values + (Jsonb(dict(parts)) if parts else None,))
    else:
        conn.execute(_SAVE_SQL.format(parts_col="", parts_val="", parts_set=""), values)
    conn.execute(
        "insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'agent', 'medication.explained', "
        "'medication_explanations', %s, %s)",
        (user_id, med_id, Jsonb({"status": status, "sources": len(sources), "side_effects": len(side_effects), "model": model_id,
                                 "prompt_version": prompt_version, "input_tokens": tokens_in, "output_tokens": tokens_out})))


def add_question(conn: psycopg.Connection, user_id: str, med_id: str, text: str) -> str:
    """A question the person wants to ask their doctor about this medicine. It goes to the doctor-question list (care plan and brief)."""
    get_medicine(conn, user_id, med_id)                        # must be their own medicine
    row = conn.execute("insert into doctor_questions (user_id, text, origin, status) values (%s, %s, 'user', 'open') returning id",
                       (user_id, text.strip())).fetchone()
    if row is None:
        raise RuntimeError("the database returned no row for an insert")
    conn.execute("insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'user', 'doctor_question.added', "
                 "'doctor_questions', %s, %s)", (user_id, row[0], Jsonb({"from": "medicine_page", "medication_id": med_id})))
    return str(row[0])
