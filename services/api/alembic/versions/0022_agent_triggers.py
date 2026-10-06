"""Learning loop, step 2: let `agent_runs.trigger` name the scheduler and log events, and drop the unused `food_matches` table.

`food_matches` was created in 0021 for matching logged meals to database dishes. That design was withdrawn (the food database never sets a
logged meal's numbers), the table is empty and nothing reads it. The trigger check is only widened, so existing rows stay valid.

Revision ID: 0022
Revises: 0021
"""
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

OLD = "'chat'::text, 'scan'::text, 'nightly'::text, 'brief'::text, 'onboarding'::text, 'checkin'::text"
NEW = OLD + ", 'tick'::text, 'log'::text, 'memory'::text"


def upgrade():
    c = op.get_bind()
    c.exec_driver_sql("ALTER TABLE agent_runs DROP CONSTRAINT IF EXISTS agent_runs_trigger_check")
    c.exec_driver_sql(f"ALTER TABLE agent_runs ADD CONSTRAINT agent_runs_trigger_check CHECK (trigger = ANY (ARRAY[{NEW}]))")
    c.exec_driver_sql("DROP TABLE IF EXISTS food_matches")


def downgrade():
    c = op.get_bind()
    c.exec_driver_sql("ALTER TABLE agent_runs DROP CONSTRAINT IF EXISTS agent_runs_trigger_check")
    c.exec_driver_sql(f"ALTER TABLE agent_runs ADD CONSTRAINT agent_runs_trigger_check CHECK (trigger = ANY (ARRAY[{OLD}]))")
    c.exec_driver_sql(
        """CREATE TABLE IF NOT EXISTS food_matches (
             id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
             food_log_id uuid REFERENCES food_logs(id) ON DELETE CASCADE, item_name text NOT NULL, food_id uuid REFERENCES foods(id),
             grams numeric, method text NOT NULL, score numeric, jev_confidence numeric, user_confirmed boolean,
             created_at timestamptz NOT NULL DEFAULT now())"""
    )
