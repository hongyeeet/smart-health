"""AI usage per day and provider (docs/specs/learning-loop.md 12.5): calls, tokens and cost, so a daily cap can be enforced and shown.

One row per day and provider (vertex_vision, vertex_embed, jev). Additive; nothing else changes.

Revision ID: 0023
Revises: 0022
"""
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade():
    c = op.get_bind()
    c.exec_driver_sql(
        """
        CREATE TABLE ai_usage_daily (
          day date NOT NULL,
          provider text NOT NULL CHECK (provider IN ('vertex_vision', 'vertex_embed', 'jev')),
          calls integer NOT NULL DEFAULT 0 CHECK (calls >= 0),
          blocked integer NOT NULL DEFAULT 0 CHECK (blocked >= 0),
          input_tokens bigint NOT NULL DEFAULT 0,
          output_tokens bigint NOT NULL DEFAULT 0,
          cost_usd numeric(10, 5),
          updated_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (day, provider)
        )
        """
    )
    c.exec_driver_sql("ALTER TABLE ai_usage_daily ENABLE ROW LEVEL SECURITY")


def downgrade():
    op.get_bind().exec_driver_sql("DROP TABLE IF EXISTS ai_usage_daily")
