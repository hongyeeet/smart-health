"""AI usage: a separate provider for text the person sees (vertex_generate), so it has its own daily cap (services/usage.py).

Until now ai_usage_daily only accepted vertex_vision, vertex_embed and jev. Text generation (brief findings, medicine explainer,
clash checker, chat, onboarding answers) now counts under vertex_generate. Additive: existing rows are unchanged.

Revision ID: 0034
Revises: 0033
"""
from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade():
    c = op.get_bind()
    c.exec_driver_sql("ALTER TABLE ai_usage_daily DROP CONSTRAINT IF EXISTS ai_usage_daily_provider_check")
    c.exec_driver_sql(
        "ALTER TABLE ai_usage_daily ADD CONSTRAINT ai_usage_daily_provider_check "
        "CHECK (provider IN ('vertex_vision', 'vertex_generate', 'vertex_embed', 'jev'))"
    )


def downgrade():
    c = op.get_bind()
    # Keep the counts: fold any vertex_generate counts into vertex_vision before the old check comes back. Nothing is deleted.
    c.exec_driver_sql(
        """
        INSERT INTO ai_usage_daily (day, provider, calls, blocked, input_tokens, output_tokens, cost_usd)
        SELECT day, 'vertex_vision', calls, blocked, input_tokens, output_tokens, cost_usd FROM ai_usage_daily WHERE provider = 'vertex_generate'
        ON CONFLICT (day, provider) DO UPDATE SET
          calls = ai_usage_daily.calls + excluded.calls,
          blocked = ai_usage_daily.blocked + excluded.blocked,
          input_tokens = ai_usage_daily.input_tokens + excluded.input_tokens,
          output_tokens = ai_usage_daily.output_tokens + excluded.output_tokens
        """
    )
    c.exec_driver_sql("DELETE FROM ai_usage_daily WHERE provider = 'vertex_generate'")
    c.exec_driver_sql("ALTER TABLE ai_usage_daily DROP CONSTRAINT IF EXISTS ai_usage_daily_provider_check")
    c.exec_driver_sql(
        "ALTER TABLE ai_usage_daily ADD CONSTRAINT ai_usage_daily_provider_check "
        "CHECK (provider IN ('vertex_vision', 'vertex_embed', 'jev'))"
    )
