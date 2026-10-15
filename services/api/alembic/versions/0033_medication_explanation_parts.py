"""Medicine explanation: the four labelled parts (prompt version 2, docs/specs/f3-explainer.md section 3).

Revision ID: 0033
Revises: 0032

The medicine page now shows four short parts (what it is for in the person's diabetes, how it works, what they may notice, why timing
matters). They are kept in one new jsonb column next to the old ones. The old columns are not changed: `purpose` still holds the first
part as plain text (the chat reads it), and an explanation made before this migration has `parts` NULL, so it still shows the old layout
until it is made again (POST /medications/{id}/explanation does that when it sees the old shape).

Nothing is dropped. The statement can run twice.
"""
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None

UP = [
    "ALTER TABLE medication_explanations ADD COLUMN IF NOT EXISTS parts jsonb",
    "COMMENT ON COLUMN medication_explanations.parts IS 'Layer: App. The four labelled parts of the explanation (for_diabetes, how_it_works, "
    "what_you_may_notice, why_timing_matters), prompt version 2. NULL for an explanation made before the four parts existed.'",
]


def upgrade():
    conn = op.get_bind()
    for s in UP:
        conn.exec_driver_sql(s)


def downgrade():
    op.get_bind().exec_driver_sql("ALTER TABLE medication_explanations DROP COLUMN IF EXISTS parts")
