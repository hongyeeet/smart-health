"""Medicine clash checker (prd F5): where an alert came from, why, and one alert per pair.

Revision ID: 0028
Revises: 0027

Decided by Joely on 2026-10-08: every time a medicine is added, an AI model (with a web search) studies all the person's saved medicines
and flags any pair that may clash, AND the known drug-pair rules from the drug labels (`interaction_rules`) are looked up in code. An alert
is raised if either finds one. The AI can add a flag but can never remove one the database found.

  - origin: 'database' (found in `interaction_rules`), 'ai' (found by the model), 'both'
  - summary: one or two plain sentences about why the two may clash (the model's, cleaned by code of any dose or treatment advice)
  - sources: the web pages the model used, or the drug-label link for a database alert
  - one alert per pair of medicines, whichever order they are stored in

Existing rows keep their meaning (origin 'database'). Written so it can run twice.
"""
from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None

UP = [
    "ALTER TABLE interaction_alerts ADD COLUMN IF NOT EXISTS origin text NOT NULL DEFAULT 'database' CHECK (origin IN ('database', 'ai', 'both'))",
    "ALTER TABLE interaction_alerts ADD COLUMN IF NOT EXISTS summary text",
    "ALTER TABLE interaction_alerts ADD COLUMN IF NOT EXISTS sources jsonb NOT NULL DEFAULT '[]'::jsonb",
    "ALTER TABLE interaction_alerts ADD COLUMN IF NOT EXISTS model_id text",
    "CREATE UNIQUE INDEX IF NOT EXISTS interaction_alerts_pair ON interaction_alerts (user_id, LEAST(med_a_id::text, med_b_id::text), GREATEST(med_a_id::text, med_b_id::text)) WHERE med_b_id IS NOT NULL",
    "COMMENT ON COLUMN interaction_alerts.origin IS 'Where the alert came from: database (a drug-pair rule from the drug labels), ai (found by the model with a web search) or both.'",
    "COMMENT ON COLUMN interaction_alerts.summary IS 'Plain-language reason the two medicines may clash. Never dose or treatment advice.'",
]


def upgrade():
    c = op.get_bind()
    for s in UP:
        c.exec_driver_sql(s)


def downgrade():
    c = op.get_bind()
    c.exec_driver_sql("DROP INDEX IF EXISTS interaction_alerts_pair")
    for col in ("model_id", "sources", "summary", "origin"):
        c.exec_driver_sql(f"ALTER TABLE interaction_alerts DROP COLUMN IF EXISTS {col}")
