"""Blood pressure readings: the read functions shared by the Log screens and the Insights and doctor brief reads.

Saving, editing and deleting are in app/db/logstore.py beside the other logs. Here are only the reads.

Two layouts are read, and the right one is found once (columns_ready):
  - Migration 0035 applied: the Silver table has its own `id`, `pulse`, `note` and `updated_at`. A reading's id is `b.id`.
  - Before 0035: the table has no id, pulse or note. A reading's id is its Bronze row's id (`bronze_id`), and the pulse and note are
    read from that Bronze payload.
Both give the same rows and the same shape for an existing reading, so every caller is the same either way.
"""
from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import date
from typing import Any

import psycopg

# Before 0035: the id is the Bronze row's id; pulse and note come from the Bronze payload.
_BRONZE_BASE = """
    select b.bronze_id as id, b.recorded_at as measured_at, b.systolic_mmhg as systolic, b.diastolic_mmhg as diastolic,
           (bz.payload->>'pulse')::int as pulse, bz.payload->>'note' as note
      from blood_pressure_readings b
      left join bronze_blood_pressure bz on bz.id = b.bronze_id
     where b.user_id = %(u)s and b.deleted_at is null
"""

# After 0035: the table holds everything.
_TABLE_BASE = """
    select b.id as id, b.recorded_at as measured_at, b.systolic_mmhg as systolic, b.diastolic_mmhg as diastolic,
           b.pulse as pulse, b.note as note
      from blood_pressure_readings b
     where b.user_id = %(u)s and b.deleted_at is null
"""

_ready = False


def _first(row: Any) -> Any:
    """The first value of a row, whether the connection gives tuples or dicts."""
    return next(iter(row.values())) if isinstance(row, Mapping) else row[0]


def columns_ready(conn: psycopg.Connection) -> bool:
    """Whether migration 0035 is applied (the id, pulse, note and updated_at columns exist). Found once and remembered; a 'not yet' is
    checked again on the next call, so the change shows as soon as the migration is applied."""
    global _ready
    if not _ready:
        n = _first(conn.execute(
            "select count(*) from information_schema.columns where table_schema = 'public' and table_name = 'blood_pressure_readings' "
            "and column_name in ('id', 'pulse', 'note', 'updated_at')").fetchone())
        _ready = int(n) == 4
    return _ready


def reset_cache() -> None:
    global _ready
    _ready = False


def id_column(conn: psycopg.Connection) -> str:
    """The column that holds a reading's entry id: `id` after 0035, `bronze_id` before it (the table's own column name)."""
    return "id" if columns_ready(conn) else "bronze_id"


def recent_select(conn: psycopg.Connection) -> str:
    """The blood pressure part of the Log's recent list, as one select with the same columns as the other kinds:
    id, kind, time, systolic (title), diastolic (number), pulse (number), note (text). Uses the user parameter `u`."""
    if columns_ready(conn):
        return ("select b.id, 'blood_pressure', b.recorded_at, b.systolic_mmhg::text, b.diastolic_mmhg::numeric, b.pulse::numeric, b.note "
                "from blood_pressure_readings b where b.user_id = %(u)s and b.deleted_at is null")
    return ("select b.bronze_id, 'blood_pressure', b.recorded_at, b.systolic_mmhg::text, b.diastolic_mmhg::numeric, "
            "(bz.payload->>'pulse')::numeric, bz.payload->>'note' "
            "from blood_pressure_readings b left join bronze_blood_pressure bz on bz.id = b.bronze_id "
            "where b.user_id = %(u)s and b.deleted_at is null")


def _base(conn: psycopg.Connection) -> str:
    return _TABLE_BASE if columns_ready(conn) else _BRONZE_BASE


def recent_bp(conn: psycopg.Connection, user_id: uuid.UUID, days: int) -> list[dict[str, Any]]:
    """Live readings from the last `days` days, newest first.

    Each row: id, measured_at (timezone-aware), systolic, diastolic, pulse (None when not entered), note.
    Rows come from the Silver table only: deleted readings are left out.
    """
    if days < 1:
        raise ValueError("days must be at least 1")
    rows = conn.execute(
        _base(conn) + " and b.recorded_at >= now() - make_interval(days => %(d)s) order by b.recorded_at desc",
        {"u": user_id, "d": int(days)},
    ).fetchall()
    return [dict(r) for r in rows]


def reading_on_day(conn: psycopg.Connection, user_id: uuid.UUID, day: date, tz: str = "Asia/Singapore") -> list[dict[str, Any]]:
    """Live readings whose local date (in `tz`) is `day`, newest first. Used by the Log screen's "today" view."""
    rows = conn.execute(
        _base(conn) + " and (b.recorded_at at time zone %(tz)s)::date = %(d)s order by b.recorded_at desc",
        {"u": user_id, "d": day, "tz": tz},
    ).fetchall()
    return [dict(r) for r in rows]


def get_reading(conn: psycopg.Connection, user_id: uuid.UUID, entry_id: uuid.UUID) -> dict[str, Any] | None:
    """One live reading by its entry id, or None when it does not exist, is deleted, or belongs to someone else."""
    row = conn.execute(_base(conn) + f" and b.{id_column(conn)} = %(e)s", {"u": user_id, "e": entry_id}).fetchone()
    return dict(row) if row else None
