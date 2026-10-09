"""Removing a medicine from the Meds page (prd F2, docs/specs/f2-scan.md section 9).

The medicine is removed by filling in its `deleted_at` time (Joely, 2026-10-09), the same soft delete the rest of the app already uses. The row
and its history stay in the database; the app simply stops showing it: the Meds list, today's doses, the clash check, the medicine page and
the calendar plan all skip a medicine that has a `deleted_at`. Its dose times are marked removed too. Its dose log (what was taken or missed
before) is kept, so adherence history is never lost, and so are the Bronze entry and the event log. Calendar events already made on Google
Calendar are not removed by this (there is no Workato recipe for that yet). The event log entry holds the kind, the source and counts only,
never the medicine's name.
"""
from __future__ import annotations

import psycopg
from psycopg.types.json import Jsonb

from app.core.errors import NotFound


def remove_medication(conn: psycopg.Connection, user_id: str, med_id: str) -> dict[str, int]:
    """Mark one of the person's own medicines as removed. Returns how many dose times were marked removed with it."""
    try:
        row = conn.execute("select kind::text, source::text from medications where id = %s and user_id = %s and deleted_at is null for update",
                           (med_id, user_id)).fetchone()
    except psycopg.errors.InvalidTextRepresentation:
        conn.rollback()
        raise NotFound("Medicine not found") from None
    if row is None:
        raise NotFound("Medicine not found")
    conn.execute("update medications set deleted_at = now() where id = %s and user_id = %s", (med_id, user_id))
    times = conn.execute("update medication_schedule set deleted_at = now() where medication_id = %s and deleted_at is null", (med_id,)).rowcount
    counts = {"dose_times": times}
    conn.execute("insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'user', 'medication.removed', 'medications', %s, %s)",
                 (user_id, med_id, Jsonb({"kind": row[0], "source": row[1], **counts})))
    return counts
