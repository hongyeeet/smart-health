"""Medicine scan (prd F2): two label fields the medication tables had no place for.

Revision ID: 0024
Revises: 0023

Decided by Joely on 2026-10-07 from her ground-truth sheet of real labels:
  - medication_schedule.when_to_take: the part of the day the label names for this dose time ("every morning").
  - medications.total_quantity: the total tablets, capsules or units supplied (the label total), to predict when the supply runs out.
    REQUIRED (Joely, 2026-10-07). The six existing demo rows were given a 30-day supply (doses per day x 30) as a labelled placeholder.
The other label fields (dose unit, drowsiness warning, minutes from food) are not columns: they stay in the verbatim directions in
medications.description and in the scan record.

Written so it can run twice: on 2026-10-07 the same SQL was first applied directly to the shared database (the files for migrations
0021 to 0023 were not in the repository yet, so Alembic could not run). Once they were pushed, `alembic upgrade head` ran this file as a
no-op and recorded revision 0024.
"""
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

WHEN = "('morning', 'noon', 'afternoon', 'evening', 'night', 'bedtime', 'as_needed')"

UP = [
    f"ALTER TABLE medication_schedule ADD COLUMN IF NOT EXISTS when_to_take text CHECK (when_to_take IS NULL OR when_to_take IN {WHEN})",
    "ALTER TABLE medications ADD COLUMN IF NOT EXISTS total_quantity integer CHECK (total_quantity IS NULL OR total_quantity >= 0)",
    "COMMENT ON COLUMN medication_schedule.when_to_take IS 'Part of the day the label names for this dose time (morning, noon, afternoon, evening, night, bedtime, as_needed). NULL when the label only says how many times a day.'",
    # Existing rows are simulated demo medicines: a 30-day supply is a placeholder, not a measured value.
    "UPDATE medications m SET total_quantity = GREATEST(1, CEIL(COALESCE(NULLIF((SELECT sum(s.quantity) FROM medication_schedule s "
    "WHERE s.medication_id = m.id AND s.deleted_at IS NULL), 0), m.frequency) * 30))::integer WHERE m.total_quantity IS NULL",
    "ALTER TABLE medications ALTER COLUMN total_quantity SET NOT NULL",
    "COMMENT ON COLUMN medications.total_quantity IS 'Required. Total tablets, capsules or units supplied, as printed on the label or typed by the user. Used to predict when the supply runs out. Demo rows hold a 30-day placeholder.'",
]


def upgrade():
    conn = op.get_bind()
    for s in UP:
        conn.exec_driver_sql(s)


def downgrade():
    conn = op.get_bind()
    conn.exec_driver_sql("ALTER TABLE medications DROP COLUMN IF EXISTS total_quantity")
    conn.exec_driver_sql("ALTER TABLE medication_schedule DROP COLUMN IF EXISTS when_to_take")
