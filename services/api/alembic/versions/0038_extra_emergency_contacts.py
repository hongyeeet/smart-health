"""More than one emergency contact (Me, Data and account).

Revision ID: 0038
Revises: 0037

Decided by Joely on 2026-10-13. A person can add another emergency contact. The FIRST contact stays where it has always been
(`user_profile.emergency_contact_*`), because set-up, the chat and the urgent alert already read it there. Every contact added after
that is one row in this table. The urgent alert emails the first contact and every live row here.

A row is soft-deleted (`deleted_at`), never removed. Written so it can run twice. The downgrade drops the table.
"""
from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None

UP = [
    """CREATE TABLE IF NOT EXISTS extra_emergency_contacts (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name text NOT NULL,
        relation text,
        phone text,
        email text,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        deleted_at timestamptz
    )""",
    "CREATE INDEX IF NOT EXISTS extra_emergency_contacts_user ON extra_emergency_contacts (user_id) WHERE deleted_at IS NULL",
    "ALTER TABLE extra_emergency_contacts ENABLE ROW LEVEL SECURITY",
    "COMMENT ON TABLE extra_emergency_contacts IS 'Layer: App. The emergency contacts a person added after the first one (the first is on user_profile). Each has a name, how they are related and a phone or email. The urgent alert emails every live row. Soft-deleted with deleted_at.'",
]


def upgrade():
    c = op.get_bind()
    for s in UP:
        c.exec_driver_sql(s)


def downgrade():
    op.get_bind().exec_driver_sql("DROP TABLE IF EXISTS extra_emergency_contacts")
