"""Medicine scan (prd F2): what the medication tables needed to hold a scanned or hand-typed label.

Revision ID: 0024
Revises: 0023

Decided by Joely on 2026-10-07 from her ground-truth sheet of real labels:
  - medications.total_quantity: the total tablets, capsules or units supplied (the label total), to predict when the supply runs out.
    Required for every NEW medicine (the app, the form and the scanner insist on it), but the database allows it to be empty, because one
    demo medicine has a label that could not be read and so has no total. The other existing demo rows were given a 30-day supply
    (doses per day x amount x 30) as a labelled placeholder.
  - medication_schedule.dose_time may be empty: an "as needed" medicine has no clock time, so no daily dose is expected and no reminder
    is due. A label that names a part of the day ("every morning") becomes a suggested clock time in the app (morning 08:00 and so on);
    no separate column is kept for it.
The other label fields (dose unit, drowsiness warning, minutes from food) are not columns: they stay in the verbatim directions in
medications.description and in the scan record.

Written so it can run twice. On 2026-10-07 the same SQL was first applied directly to the shared database (the files for migrations
0021 to 0023 were not in the repository yet, so Alembic could not run); once they were, `alembic upgrade head` ran this file as a no-op
and recorded revision 0024. A short-lived column `medication_schedule.when_to_take` that existed in the shared database for a few hours
was dropped by hand before this file was pushed and never appears here.
"""
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

UP = [
    "ALTER TABLE medications ADD COLUMN IF NOT EXISTS total_quantity integer CHECK (total_quantity IS NULL OR total_quantity >= 0)",
    # Existing rows are simulated demo medicines: a 30-day supply is a placeholder, not a measured value.
    "UPDATE medications m SET total_quantity = GREATEST(1, CEIL(COALESCE(NULLIF((SELECT sum(s.quantity) FROM medication_schedule s "
    "WHERE s.medication_id = m.id AND s.deleted_at IS NULL), 0), m.frequency) * 30))::integer WHERE m.total_quantity IS NULL",
    # The database allows an empty total (new medicines still require one in the app). The medicine whose label could not be read has
    # none: empty means no data, never 0. The column must stop requiring a value before it can be cleared.
    "ALTER TABLE medications ALTER COLUMN total_quantity DROP NOT NULL",
    "UPDATE medications SET total_quantity = NULL WHERE name = 'Herbal tonic (label not readable)' AND source = 'demo_dataset'",
    "COMMENT ON COLUMN medications.total_quantity IS 'Total tablets, capsules or units supplied, as printed on the label or typed by the user. Required for every new medicine by the app; empty only where the label could not be read. Used to predict when the supply runs out. Demo rows hold a 30-day placeholder.'",
    "ALTER TABLE medication_schedule ALTER COLUMN dose_time DROP NOT NULL",
    "COMMENT ON COLUMN medication_schedule.dose_time IS 'Local clock time of the dose. Empty means the medicine is taken only when needed (as needed): no daily dose is expected and no reminder is due.'",
]


def upgrade():
    conn = op.get_bind()
    for s in UP:
        conn.exec_driver_sql(s)


def downgrade():
    conn = op.get_bind()
    conn.exec_driver_sql("DELETE FROM medication_schedule WHERE dose_time IS NULL")
    conn.exec_driver_sql("ALTER TABLE medication_schedule ALTER COLUMN dose_time SET NOT NULL")
    conn.exec_driver_sql("ALTER TABLE medications DROP COLUMN IF EXISTS total_quantity")
