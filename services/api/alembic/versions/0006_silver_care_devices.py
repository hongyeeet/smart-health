"""Silver, part 3: appointments, doctor questions, preventive status, devices, goals, notifications (6 tables).

Source: docs/specs/schema.md sections 6, 9, 9c.

NOTE: appointments.brief_id and doctor_questions.brief_id point at briefs (Gold, E1-3). They are plain
nullable uuid columns here; Hong Yi adds the foreign keys at the end of E1-3.

Revision ID: 0006
Revises: 0005
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

TABLES = ["appointments", "doctor_questions", "patient_preventive_status", "devices", "health_goals", "notifications"]
UPDATED_AT = ["appointments", "patient_preventive_status", "devices", "health_goals"]


def run(statements):
    conn = op.get_bind()
    for s in statements:
        conn.exec_driver_sql(s)


def upgrade():
    run([
        """CREATE TABLE appointments (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            kind appointment_kind NOT NULL,
            status appointment_status NOT NULL,
            scheduled_for timestamptz,
            location text,
            suggested_reason jsonb,
            calendar_event_id text,
            confirmed_by_user_at timestamptz,
            brief_id uuid,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CHECK (calendar_event_id IS NULL OR confirmed_by_user_at IS NOT NULL)
        )""",
        "CREATE INDEX appointments_user_scheduled ON appointments (user_id, scheduled_for)",
        """CREATE TABLE doctor_questions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            text text NOT NULL,
            origin text CHECK (origin IN ('user','refused_chat','checkin','agent_suggested')),
            status text CHECK (status IN ('open','asked','archived')),
            brief_id uuid,
            created_at timestamptz NOT NULL DEFAULT now()
        )""",
        "CREATE INDEX doctor_questions_user ON doctor_questions (user_id, created_at DESC)",
        """CREATE TABLE patient_preventive_status (
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            preventive_item_id uuid NOT NULL REFERENCES preventive_items(id),
            last_done_on date,
            next_due_on date,
            status text CHECK (status IN ('ok','due_soon','overdue','unknown')),
            updated_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, preventive_item_id)
        )""",
        """CREATE TABLE devices (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            kind device_kind NOT NULL,
            label text NOT NULL,
            source entry_source NOT NULL,
            last_synced_at timestamptz,
            status text CHECK (status IN ('connected','disconnected')),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )""",
        "CREATE INDEX devices_user ON devices (user_id)",
        """CREATE TABLE health_goals (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            kind goal_kind NOT NULL,
            target_value numeric,
            target_low numeric,
            target_high numeric,
            unit text,
            set_by text CHECK (set_by IN ('user','clinician','default')),
            active boolean NOT NULL DEFAULT true,
            starts_on date,
            ends_on date,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )""",
        "CREATE INDEX health_goals_user ON health_goals (user_id, active)",
        """CREATE TABLE notifications (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            kind notification_kind NOT NULL,
            ref_table text,
            ref_id uuid,
            scheduled_for timestamptz NOT NULL,
            sent_at timestamptz,
            opened_at timestamptz,
            acted_at timestamptz,
            action text,
            channel text CHECK (channel IN ('push','local','in_app')),
            payload jsonb
        )""",
        "CREATE INDEX notifications_user_scheduled ON notifications (user_id, scheduled_for)",
    ])
    run([f"CREATE TRIGGER trg_updated_at BEFORE UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION set_updated_at()" for t in UPDATED_AT])


def downgrade():
    run([f"DROP TABLE IF EXISTS {t} CASCADE" for t in reversed(TABLES)])
