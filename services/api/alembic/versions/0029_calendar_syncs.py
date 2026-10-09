"""Calendar reminders for medicines (prd F4, docs/specs/f4-calendar.md): where each medicine's calendar events stand.

Revision ID: 0029
Revises: 0028

Decided by Joely on 2026-10-09. After a medicine is confirmed, the backend asks a Workato recipe to put each dose time on Google Calendar as a
repeating event with a reminder at the dose time, so the phone's calendar app gives the notification. This table keeps one row per medicine:

  - status: queued (waiting), running (events are being made, one dose time at a time), done, failed (some or all events could not be made;
    it can be retried), skipped (nothing to do: an only-when-needed medicine, or Workato is not set up)
  - events: the calendar events made so far, as a list of {schedule_id, time, event_id}, so a retry only makes the missing ones and the events
    can be removed later
  - events_total and events_done: the progress the loading page shows
  - reason: why it was skipped; error_code: the code of the last failure (never a message with private detail)

One row per medicine (medication_id is unique) and it goes with the medicine. Written so it can run twice.
"""
from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None

UP = [
    """CREATE TABLE IF NOT EXISTS calendar_syncs (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        medication_id uuid NOT NULL UNIQUE REFERENCES medications(id) ON DELETE CASCADE,
        status text NOT NULL CHECK (status IN ('queued', 'running', 'done', 'failed', 'skipped')),
        reason text,
        events jsonb NOT NULL DEFAULT '[]'::jsonb,
        events_total integer NOT NULL DEFAULT 0 CHECK (events_total >= 0),
        events_done integer NOT NULL DEFAULT 0 CHECK (events_done >= 0),
        error_code text,
        attempts integer NOT NULL DEFAULT 0,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        finished_at timestamptz
    )""",
    "CREATE INDEX IF NOT EXISTS calendar_syncs_user ON calendar_syncs (user_id)",
    "ALTER TABLE calendar_syncs ENABLE ROW LEVEL SECURITY",
    "COMMENT ON TABLE calendar_syncs IS 'Layer: App. Where each medicine''s Google Calendar reminders stand: one row per medicine, with progress, the calendar events made so far and the last error code. Filled by the backend through a Workato recipe.'",
]


def upgrade():
    c = op.get_bind()
    for s in UP:
        c.exec_driver_sql(s)


def downgrade():
    op.get_bind().exec_driver_sql("DROP TABLE IF EXISTS calendar_syncs")
