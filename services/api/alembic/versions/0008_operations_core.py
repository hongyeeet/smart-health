"""Operations core (E1-3 step 1): agent_runs, agent_steps, guardrail_events.

Source: docs/specs/schema.md section 8. Operations tables hold ids, digests and counts, never health values or
free text (data-flow.md section 2). JEV calls are logged here as agent_steps with node = 'jev' (memory.md 12).

Revision ID: 0008
Revises: 0007
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

TABLES = ["agent_runs", "agent_steps", "guardrail_events"]


def run(statements):
    conn = op.get_bind()
    for s in statements:
        conn.exec_driver_sql(s)


def upgrade():
    run([
        """CREATE TABLE agent_runs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid REFERENCES users(id) ON DELETE CASCADE,
            agent text NOT NULL,
            trigger text CHECK (trigger IN ('chat','scan','nightly','brief','onboarding','checkin')),
            model_id text,
            prompt_version text,
            status text CHECK (status IN ('running','ok','guard_blocked','error')),
            input_tokens integer,
            output_tokens integer,
            latency_ms integer,
            error text,
            started_at timestamptz NOT NULL DEFAULT now(),
            finished_at timestamptz
        )""",
        "CREATE INDEX agent_runs_user_started ON agent_runs (user_id, started_at DESC)",
        """CREATE TABLE agent_steps (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_run_id uuid NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
            seq smallint NOT NULL,
            node text NOT NULL,
            tool text,
            input_digest text,
            output jsonb,
            latency_ms integer,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (agent_run_id, seq)
        )""",
        "CREATE INDEX agent_steps_node ON agent_steps (node, tool, created_at DESC)",
        """CREATE TABLE guardrail_events (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_run_id uuid REFERENCES agent_runs(id) ON DELETE SET NULL,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            stage text CHECK (stage IN ('input','output')),
            verdict guard_verdict NOT NULL,
            rule_id text NOT NULL,
            excerpt text CHECK (char_length(excerpt) <= 300),
            created_at timestamptz NOT NULL DEFAULT now()
        )""",
        "CREATE INDEX guardrail_events_user_created ON guardrail_events (user_id, created_at DESC)",
    ])
    run([f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY" for t in TABLES])


def downgrade():
    run([f"DROP TABLE IF EXISTS {t} CASCADE" for t in reversed(TABLES)])
