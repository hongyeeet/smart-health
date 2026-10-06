"""Learning loop (docs/specs/learning-loop.md section 6): Singapore food columns on foods, and four new tables.

ADDITIVE ONLY. Nothing is dropped or rewritten.
  foods            + subgroup, sat_fat_g, potassium_mg, source_grade, data_year, per100, embedding (vector 768), unique (source, name)
  food_matches     which food-database row (or items) a logged meal was matched to, how, and how sure
  nudge_policy     per person: how often each slot, template or suggestion was tried and acted on (bandit state)
  adherence_barriers  per person per week: the barrier pattern behind missed doses
  content_proposals   agent-drafted wording or routines waiting for user or team approval

Revision ID: 0021
Revises: 0020
"""
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade():
    c = op.get_bind()
    c.exec_driver_sql(
        """
        ALTER TABLE foods
          ADD COLUMN IF NOT EXISTS subgroup text,
          ADD COLUMN IF NOT EXISTS sat_fat_g numeric CHECK (sat_fat_g >= 0),
          ADD COLUMN IF NOT EXISTS potassium_mg numeric CHECK (potassium_mg >= 0),
          ADD COLUMN IF NOT EXISTS source_grade text CHECK (source_grade IN ('lab_analysis', 'derived', 'borrowed', 'label')),
          ADD COLUMN IF NOT EXISTS data_year smallint,
          ADD COLUMN IF NOT EXISTS per100 jsonb,
          ADD COLUMN IF NOT EXISTS embedding vector(768)
        """
    )
    c.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS foods_source_name_key ON foods (source, name)")
    c.exec_driver_sql("CREATE INDEX IF NOT EXISTS foods_name_trgm ON foods USING gin (name gin_trgm_ops)")
    c.exec_driver_sql("CREATE INDEX IF NOT EXISTS foods_embedding_hnsw ON foods USING hnsw (embedding vector_cosine_ops)")
    c.exec_driver_sql("CREATE INDEX IF NOT EXISTS foods_category_subgroup ON foods (category, subgroup)")

    c.exec_driver_sql(
        """
        CREATE TABLE food_matches (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          food_log_id uuid REFERENCES food_logs(id) ON DELETE CASCADE,
          item_name text NOT NULL,
          food_id uuid REFERENCES foods(id),
          grams numeric CHECK (grams >= 0),
          method text NOT NULL CHECK (method IN ('exact', 'hybrid', 'jev', 'llm')),
          score numeric CHECK (score >= 0 AND score <= 1),
          jev_confidence numeric CHECK (jev_confidence >= 0 AND jev_confidence <= 1),
          user_confirmed boolean,
          created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    c.exec_driver_sql("CREATE INDEX food_matches_log ON food_matches (food_log_id)")
    c.exec_driver_sql("CREATE INDEX food_matches_user ON food_matches (user_id, created_at DESC)")

    c.exec_driver_sql(
        """
        CREATE TABLE nudge_policy (
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          arm_kind text NOT NULL CHECK (arm_kind IN ('slot', 'template', 'suggestion', 'activity')),
          arm_key text NOT NULL,
          tries integer NOT NULL DEFAULT 0 CHECK (tries >= 0),
          acts integer NOT NULL DEFAULT 0 CHECK (acts >= 0 AND acts <= tries),
          last_tried_at timestamptz,
          updated_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (user_id, arm_kind, arm_key)
        )
        """
    )

    c.exec_driver_sql(
        """
        CREATE TABLE adherence_barriers (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          week_start date NOT NULL,
          barrier text NOT NULL CHECK (barrier IN ('forgot', 'ran_out', 'side_effects', 'busy_away', 'cost', 'felt_fine', 'other')),
          n integer NOT NULL CHECK (n > 0),
          share numeric CHECK (share >= 0 AND share <= 1),
          evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
          evidence_status text NOT NULL DEFAULT 'observed',
          built_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (user_id, week_start, barrier)
        )
        """
    )

    c.exec_driver_sql(
        """
        CREATE TABLE content_proposals (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid REFERENCES users(id) ON DELETE CASCADE,
          kind text NOT NULL CHECK (kind IN ('nudge_wording', 'routine_anchor', 'swap_tip', 'barrier_label')),
          body text NOT NULL,
          locale locale_code NOT NULL DEFAULT 'en',
          evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
          guard_verdict guard_verdict NOT NULL,
          status text NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed', 'approved', 'rejected')),
          created_by text NOT NULL,
          reviewer text,
          reviewed_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          CHECK (status <> 'approved' OR guard_verdict = 'pass')
        )
        """
    )
    c.exec_driver_sql("CREATE INDEX content_proposals_status ON content_proposals (status, kind)")

    for t in ("food_matches", "nudge_policy", "adherence_barriers", "content_proposals"):
        c.exec_driver_sql(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")


def downgrade():
    c = op.get_bind()
    for t in ("content_proposals", "adherence_barriers", "nudge_policy", "food_matches"):
        c.exec_driver_sql(f"DROP TABLE IF EXISTS {t}")
    for i in ("foods_category_subgroup", "foods_embedding_hnsw", "foods_name_trgm", "foods_source_name_key"):
        c.exec_driver_sql(f"DROP INDEX IF EXISTS {i}")
    c.exec_driver_sql(
        "ALTER TABLE foods DROP COLUMN IF EXISTS embedding, DROP COLUMN IF EXISTS per100, DROP COLUMN IF EXISTS data_year, "
        "DROP COLUMN IF EXISTS source_grade, DROP COLUMN IF EXISTS potassium_mg, DROP COLUMN IF EXISTS sat_fat_g, DROP COLUMN IF EXISTS subgroup"
    )
