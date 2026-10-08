"""Medicine explainer (prd F3): one saved explanation per medicine, so the web search is done once and the page then opens instantly.

Revision ID: 0025
Revises: 0024

Decided by Joely on 2026-10-08. The 250k Medicines file is a general medicine list (under 5% anti-diabetic, and it has no supplements or
herbal products), so the explanation is written by the model from the medicine's name and the label text, after a web search. The text is
kept here together with the web pages it came from, and a hash of what it was written from so it is made again if the medicine changes.

  - one row per medicine (medication_id is the key); deleted with the medicine
  - `status` ready: the model found and explained the medicine; not_identified: it could not tell what the product is, so nothing is shown
    as fact and the page says so
  - `sources` are the web pages the answer was based on (title and link); an explanation without a source is never stored (prd F3)
  - nothing here is dose advice: the dose shown on the page always comes from the person's own label

Written so it can run twice.
"""
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None

UP = [
    """CREATE TABLE IF NOT EXISTS medication_explanations (
        medication_id uuid PRIMARY KEY REFERENCES medications(id) ON DELETE CASCADE,
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        status text NOT NULL CHECK (status IN ('ready', 'not_identified')),
        purpose text,
        side_effects jsonb NOT NULL DEFAULT '[]'::jsonb,
        tell_doctor text,
        sources jsonb NOT NULL DEFAULT '[]'::jsonb,
        input_hash text NOT NULL,
        model_id text NOT NULL,
        prompt_version text NOT NULL,
        generated_at timestamptz NOT NULL DEFAULT now(),
        CHECK (status <> 'ready' OR (purpose IS NOT NULL AND jsonb_array_length(sources) > 0))
    )""",
    "CREATE INDEX IF NOT EXISTS medication_explanations_user ON medication_explanations (user_id)",
    "ALTER TABLE medication_explanations ENABLE ROW LEVEL SECURITY",
    "COMMENT ON TABLE medication_explanations IS 'Layer: App. The plain-language explanation of one medicine (what it is for, common side effects, when to tell the doctor), written by the model from the medicine name and label text after a web search, with the web pages it used. Made once and kept; made again when the medicine changes. Never holds dose advice.'",
]


def upgrade():
    conn = op.get_bind()
    for s in UP:
        conn.exec_driver_sql(s)


def downgrade():
    op.get_bind().exec_driver_sql("DROP TABLE IF EXISTS medication_explanations")
