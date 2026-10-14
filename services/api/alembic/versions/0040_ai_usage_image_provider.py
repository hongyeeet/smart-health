"""AI usage: a separate provider for dish pictures (vertex_image), so it has its own daily cap (services/usage.py).

Revision ID: 0040
Revises: 0039

The Meal suggestions page makes one picture per dish (docs/specs/menu.md). Those calls count under vertex_image (cap AI_CAP_VERTEX_IMAGE).
Additive: existing rows are unchanged. The downgrade folds any vertex_image counts into vertex_vision before the old check comes back.
"""
from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade():
    c = op.get_bind()
    c.exec_driver_sql("ALTER TABLE ai_usage_daily DROP CONSTRAINT IF EXISTS ai_usage_daily_provider_check")
    c.exec_driver_sql(
        "ALTER TABLE ai_usage_daily ADD CONSTRAINT ai_usage_daily_provider_check "
        "CHECK (provider IN ('vertex_vision', 'vertex_generate', 'vertex_embed', 'vertex_image', 'jev'))"
    )


def downgrade():
    c = op.get_bind()
    c.exec_driver_sql(
        """
        INSERT INTO ai_usage_daily (day, provider, calls, blocked, input_tokens, output_tokens, cost_usd)
        SELECT day, 'vertex_vision', calls, blocked, input_tokens, output_tokens, cost_usd FROM ai_usage_daily WHERE provider = 'vertex_image'
        ON CONFLICT (day, provider) DO UPDATE SET
          calls = ai_usage_daily.calls + excluded.calls,
          blocked = ai_usage_daily.blocked + excluded.blocked,
          input_tokens = ai_usage_daily.input_tokens + excluded.input_tokens,
          output_tokens = ai_usage_daily.output_tokens + excluded.output_tokens
        """
    )
    c.exec_driver_sql("DELETE FROM ai_usage_daily WHERE provider = 'vertex_image'")
    c.exec_driver_sql("ALTER TABLE ai_usage_daily DROP CONSTRAINT IF EXISTS ai_usage_daily_provider_check")
    c.exec_driver_sql(
        "ALTER TABLE ai_usage_daily ADD CONSTRAINT ai_usage_daily_provider_check "
        "CHECK (provider IN ('vertex_vision', 'vertex_generate', 'vertex_embed', 'jev'))"
    )
