"""Blood pressure readings: an id, pulse, note and an updated time on the Silver table.

Revision ID: 0035
Revises: 0034

Until now a reading's pulse and note were kept only in its Bronze payload, and its id was its Bronze row's id, because the table had
no id of its own. Its key was (user_id, recorded_at), so a second reading at the same time was refused. This migration gives the table
the columns it needs. Nothing is dropped and every statement can run twice.

The key stays (user_id, recorded_at), so every existing constraint, the foreign keys, and the exact-duplicate protection are unchanged.
A new unique `id` is what the app uses to read, edit and delete a reading.

Existing readings keep the id they already show: `id` is back-filled from `bronze_id`, which is unique per reading (checked on
2026-10-11: 44 readings, 44 distinct Bronze rows). So the 42 seeded readings for Mr Tan keep the same ids, values and display. Their
pulse and note stay null, because their Bronze payloads have none. Any reading saved by hand before this migration gets its pulse and
note copied from its Bronze payload, so nothing is lost from the reads.

The app code (app/services/blood_pressure.py and app/db/logstore.py) checks for these columns and keeps working on the old layout until
this migration is applied.

Downgrade drops only what this migration adds: the id (and its index), pulse, note and updated_at. The pulse and note of a reading are
still in its Bronze payload, and editing a reading after the downgrade gives it its Bronze id, so the ids of readings edited or saved
after the upgrade change on the downgrade. The readings themselves are kept.
"""
from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None

UP = [
    # 1. the entry id: added without a default first, so the back-fill can fill it from the Bronze row
    "ALTER TABLE blood_pressure_readings ADD COLUMN IF NOT EXISTS id uuid",
    # 2. existing readings keep the id they already show (their Bronze row id)
    "UPDATE blood_pressure_readings SET id = bronze_id WHERE id IS NULL",
    # 3. new readings get a random id; the unique index makes the id a key in its own right
    "ALTER TABLE blood_pressure_readings ALTER COLUMN id SET DEFAULT gen_random_uuid()",
    "ALTER TABLE blood_pressure_readings ALTER COLUMN id SET NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS blood_pressure_readings_id_key ON blood_pressure_readings (id)",
    # 4. pulse and note, with the limits the API already enforces
    "ALTER TABLE blood_pressure_readings ADD COLUMN IF NOT EXISTS pulse smallint CHECK (pulse BETWEEN 30 AND 220)",
    "ALTER TABLE blood_pressure_readings ADD COLUMN IF NOT EXISTS note text CHECK (char_length(note) <= 300)",
    # 5. the time of the last edit (null: never edited since it was saved)
    "ALTER TABLE blood_pressure_readings ADD COLUMN IF NOT EXISTS updated_at timestamptz",
    # 6. copy pulse and note from the Bronze payload for readings that have them (saved by hand before this migration)
    """UPDATE blood_pressure_readings b SET
         pulse = CASE WHEN jsonb_typeof(bz.payload->'pulse') = 'number' AND (bz.payload->>'pulse')::numeric BETWEEN 30 AND 220
                      THEN (bz.payload->>'pulse')::numeric::smallint END,
         note = CASE WHEN jsonb_typeof(bz.payload->'note') = 'string' THEN left(bz.payload->>'note', 300) END
       FROM bronze_blood_pressure bz
       WHERE bz.id = b.bronze_id AND b.pulse IS NULL AND b.note IS NULL""",
    "COMMENT ON COLUMN blood_pressure_readings.id IS 'Layer: Silver. The entry id the app uses to read, edit and delete a reading. "
    "A reading keeps this id when it is edited. Readings from before migration 0035 keep the id of their Bronze row.'",
    "COMMENT ON COLUMN blood_pressure_readings.pulse IS 'Layer: Silver. Pulse in beats a minute, when the person entered it (30 to 220). "
    "Null for a reading without a pulse.'",
    "COMMENT ON COLUMN blood_pressure_readings.note IS 'Layer: Silver. The person''s own note on the reading, up to 300 characters. "
    "Null when there is none.'",
    "COMMENT ON COLUMN blood_pressure_readings.updated_at IS 'Layer: Silver. When the reading was last edited. Null when it has never been edited.'",
]

DOWN = [
    "DROP INDEX IF EXISTS blood_pressure_readings_id_key",
    "ALTER TABLE blood_pressure_readings DROP COLUMN IF EXISTS updated_at",
    "ALTER TABLE blood_pressure_readings DROP COLUMN IF EXISTS note",
    "ALTER TABLE blood_pressure_readings DROP COLUMN IF EXISTS pulse",
    "ALTER TABLE blood_pressure_readings DROP COLUMN IF EXISTS id",
]


def upgrade():
    conn = op.get_bind()
    for s in UP:
        conn.exec_driver_sql(s)


def downgrade():
    conn = op.get_bind()
    for s in DOWN:
        conn.exec_driver_sql(s)
