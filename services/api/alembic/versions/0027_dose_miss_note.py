"""Missed-dose answer (prd F4, screen H7): the optional note that goes with the reason.

Revision ID: 0027
Revises: 0026

"Why was it not confirmed?" has seven reasons (already the enum `miss_reason`) and an optional note ("Anything your doctor should know").
The note is free text the person chose to write for their doctor, so it lives on the dose row (medication_log.miss_note) and is read
into the doctor brief. It is never copied into event_log or the logs (rules.md section 3).

Written so it can run twice.
"""
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade():
    c = op.get_bind()
    c.exec_driver_sql("ALTER TABLE medication_log ADD COLUMN IF NOT EXISTS miss_note text CHECK (miss_note IS NULL OR char_length(miss_note) <= 500)")
    c.exec_driver_sql("COMMENT ON COLUMN medication_log.miss_note IS 'Optional note the person wrote with the reason a dose was not confirmed, for their doctor. Free text: never copied into event_log or logs.'")


def downgrade():
    op.get_bind().exec_driver_sql("ALTER TABLE medication_log DROP COLUMN IF EXISTS miss_note")
