"""Data model v2, step 1: two new entry_source values ('watch', 'llm_estimate').

Source: docs/specs/data-model-v2.md section 2. A new enum value cannot be used in the transaction that adds it,
so this is its own migration; 0018 (the v2 rebuild) uses the values in constraints.

Revision ID: 0017
Revises: 0016
"""
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.exec_driver_sql("ALTER TYPE entry_source ADD VALUE IF NOT EXISTS 'watch'")
    conn.exec_driver_sql("ALTER TYPE entry_source ADD VALUE IF NOT EXISTS 'llm_estimate'")


def downgrade():
    # PostgreSQL cannot remove an enum value; leaving the two values in place is harmless.
    pass
