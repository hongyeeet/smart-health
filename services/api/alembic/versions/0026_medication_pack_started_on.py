"""Supply estimate (prd F2/F4): the day the current pack was started.

Revision ID: 0026
Revises: 0025

`medications.start_date` is when the person began the medicine (Metformin since 2021). The supply estimate needs the day the pack in hand
was started, which is a different date. The new column is optional: empty means "use start_date" for a medicine the person added
themselves (the label date), and means "no estimate" for a simulated demo medicine whose pack size is only a placeholder.
Mr Tan's medicines get realistic pack sizes and pack start dates in the loader (scripts/load_mr_tan_v2.py), labelled as demo data.

Written so it can run twice.
"""
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade():
    c = op.get_bind()
    c.exec_driver_sql("ALTER TABLE medications ADD COLUMN IF NOT EXISTS pack_started_on date")
    c.exec_driver_sql("COMMENT ON COLUMN medications.pack_started_on IS 'The day the pack in hand was started, for the supply estimate (total_quantity minus doses taken since). Empty: the estimate counts from start_date, and simulated demo medicines show no estimate.'")


def downgrade():
    op.get_bind().exec_driver_sql("ALTER TABLE medications DROP COLUMN IF EXISTS pack_started_on")
