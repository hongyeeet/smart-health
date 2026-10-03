"""Gold: briefs, brief_shares, brief_share_access (E1-3 step 2).

Source: docs/specs/schema.md section 7. A brief is immutable once it is 'ready': a trigger rejects any change to
its content, and the only allowed change is ready -> superseded (a regenerated brief is a new row).

Revision ID: 0009
Revises: 0008
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

TABLES = ["briefs", "brief_shares", "brief_share_access"]


def run(statements):
    conn = op.get_bind()
    for s in statements:
        conn.exec_driver_sql(s)


def upgrade():
    run([
        """CREATE TABLE briefs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            period_start date NOT NULL,
            period_end date NOT NULL,
            status brief_status NOT NULL,
            data jsonb NOT NULL DEFAULT '{}'::jsonb,
            narrative jsonb,
            html_key text,
            pdf_key text,
            appointment_id uuid REFERENCES appointments(id) ON DELETE SET NULL,
            agent_run_id uuid REFERENCES agent_runs(id) ON DELETE SET NULL,
            validator_report jsonb,
            generated_at timestamptz NOT NULL DEFAULT now(),
            CHECK (period_end >= period_start)
        )""",
        "CREATE INDEX briefs_user_generated ON briefs (user_id, generated_at DESC)",
        """CREATE FUNCTION briefs_immutable_when_ready() RETURNS trigger LANGUAGE plpgsql AS $f$
        BEGIN
          IF OLD.status = 'ready' THEN
            IF NEW.status NOT IN ('ready', 'superseded')
               OR NEW.user_id IS DISTINCT FROM OLD.user_id
               OR NEW.period_start IS DISTINCT FROM OLD.period_start
               OR NEW.period_end IS DISTINCT FROM OLD.period_end
               OR NEW.data IS DISTINCT FROM OLD.data
               OR NEW.narrative IS DISTINCT FROM OLD.narrative
               OR NEW.html_key IS DISTINCT FROM OLD.html_key
               OR NEW.pdf_key IS DISTINCT FROM OLD.pdf_key
               OR NEW.validator_report IS DISTINCT FROM OLD.validator_report THEN
              RAISE EXCEPTION 'a brief that is ready cannot be changed; regenerate it as a new brief';
            END IF;
          END IF;
          RETURN NEW;
        END
        $f$""",
        "CREATE TRIGGER trg_briefs_immutable BEFORE UPDATE ON briefs FOR EACH ROW EXECUTE FUNCTION briefs_immutable_when_ready()",
        """CREATE TABLE brief_shares (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            brief_id uuid NOT NULL REFERENCES briefs(id) ON DELETE CASCADE,
            token_hash text NOT NULL UNIQUE,
            expires_at timestamptz NOT NULL,
            revoked_at timestamptz,
            consent_id uuid NOT NULL REFERENCES consents(id),
            created_at timestamptz NOT NULL DEFAULT now()
        )""",
        "CREATE INDEX brief_shares_brief ON brief_shares (brief_id)",
        """CREATE TABLE brief_share_access (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            brief_share_id uuid NOT NULL REFERENCES brief_shares(id) ON DELETE CASCADE,
            accessed_at timestamptz NOT NULL DEFAULT now(),
            ip_hash text,
            user_agent text
        )""",
        "CREATE INDEX brief_share_access_share ON brief_share_access (brief_share_id, accessed_at DESC)",
    ])
    run([f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY" for t in TABLES])


def downgrade():
    run([f"DROP TABLE IF EXISTS {t} CASCADE" for t in reversed(TABLES)])
    run(["DROP FUNCTION IF EXISTS briefs_immutable_when_ready()"])
