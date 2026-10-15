"""Gold memory and chat (E1-3 step 4): conversations, memory_facts, memory_episodes, nudge_stats, messages.

Source: docs/specs/schema.md section 8 and memory.md. `conversations.summary_episode_id` is created WITHOUT its
foreign key (memory_episodes points back at conversations); migration 0014 adds the constraint.
memory_episodes.embedding uses EMBED_DIM, default 768 (decision D-048: gemini-embedding-001 at 768 dimensions).
Nothing is ever labelled "validated": evidence_status has no such value (memory.md 4).

Revision ID: 0011
Revises: 0010
"""
import os

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

TABLES = ["conversations", "memory_facts", "memory_episodes", "nudge_stats", "messages"]
UPDATED_AT = ["memory_facts", "nudge_stats"]


def run(statements):
    conn = op.get_bind()
    for s in statements:
        conn.exec_driver_sql(s)


def upgrade():
    dim = int(os.environ.get("EMBED_DIM", "768"))
    run([
        """CREATE TABLE conversations (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            started_at timestamptz NOT NULL DEFAULT now(),
            ended_at timestamptz,
            locale locale_code,
            summary_episode_id uuid
        )""",
        "CREATE INDEX conversations_user_started ON conversations (user_id, started_at DESC)",
        """CREATE TABLE memory_facts (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            key text NOT NULL,
            category fact_category NOT NULL,
            value jsonb NOT NULL,
            statement_key text,
            statement text,
            confidence numeric(3,2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
            evidence_status evidence_status NOT NULL,
            evidence_refs jsonb NOT NULL,
            status fact_status NOT NULL,
            version integer NOT NULL DEFAULT 1,
            supersedes_id uuid REFERENCES memory_facts(id),
            source text CHECK (source IN ('reflection','user','onboarding')),
            user_confirmed_at timestamptz,
            last_evidence_at timestamptz NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )""",
        "CREATE UNIQUE INDEX memory_facts_active_key_uq ON memory_facts (user_id, key) WHERE status = 'active'",
        "CREATE INDEX memory_facts_user_status ON memory_facts (user_id, status, category)",
        f"""CREATE TABLE memory_episodes (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            conversation_id uuid REFERENCES conversations(id) ON DELETE SET NULL,
            occurred_at timestamptz,
            summary text NOT NULL,
            topics text[],
            embedding extensions.vector({dim}) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )""",
        "CREATE INDEX memory_episodes_embedding_hnsw ON memory_episodes USING hnsw (embedding extensions.vector_cosine_ops)",
        "CREATE INDEX memory_episodes_user_occurred ON memory_episodes (user_id, occurred_at)",
        """CREATE TABLE nudge_stats (
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            nudge_type text NOT NULL,
            time_slot smallint NOT NULL CHECK (time_slot BETWEEN 0 AND 23),
            sent integer NOT NULL DEFAULT 0,
            acted integer NOT NULL DEFAULT 0,
            updated_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, nudge_type, time_slot)
        )""",
        """CREATE TABLE messages (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role text CHECK (role IN ('user','assistant','system_template')),
            content text NOT NULL,
            agent_run_id uuid REFERENCES agent_runs(id) ON DELETE SET NULL,
            guard_verdict guard_verdict,
            tts_audio_key text,
            created_at timestamptz NOT NULL DEFAULT now()
        )""",
        "CREATE INDEX messages_conversation_created ON messages (conversation_id, created_at)",
    ])
    run([f"CREATE TRIGGER trg_updated_at BEFORE UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION set_updated_at()" for t in UPDATED_AT])
    run([f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY" for t in TABLES])


def downgrade():
    run([f"DROP TABLE IF EXISTS {t} CASCADE" for t in reversed(TABLES)])
