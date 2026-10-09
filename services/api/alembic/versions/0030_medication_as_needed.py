"""Every day or only when needed (prd F2 and F4): a yes/no column on each medicine.

Revision ID: 0030
Revises: 0029

Decided by Joely on 2026-10-09. A medicine is either taken every day at set times, or only when it is needed (paracetamol for a fever, an
inhaler). The person says which before confirming a medicine, and the answer is kept as `medications.as_needed` (true: only when needed;
false: every day). It decides everything that depends on a routine: an only-when-needed medicine has no dose times, no reminders on Home,
no calendar events and no refill estimate (the app cannot know how much is used), while an every-day medicine gets all of them.

Until now this was only implied by an empty `medication_schedule.dose_time`. That rule stays (an only-when-needed medicine has one schedule
row with no time), and the column is now the thing to read. Existing rows are filled in from that rule. Written so it can run twice.
"""
from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None

UP = [
    "ALTER TABLE medications ADD COLUMN IF NOT EXISTS as_needed boolean NOT NULL DEFAULT false",
    "UPDATE medications m SET as_needed = true WHERE EXISTS (SELECT 1 FROM medication_schedule s WHERE s.medication_id = m.id "
    "AND s.dose_time IS NULL AND s.deleted_at IS NULL)",
    "COMMENT ON COLUMN medications.as_needed IS 'true: taken only when needed (no dose times, no reminders, no calendar events, no refill estimate); false: taken every day at set times. Chosen by the person before the medicine is saved.'",
]


def upgrade():
    c = op.get_bind()
    for s in UP:
        c.exec_driver_sql(s)


def downgrade():
    op.get_bind().exec_driver_sql("ALTER TABLE medications DROP COLUMN IF EXISTS as_needed")
