"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""
from alembic import op

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = None
depends_on = None


def run(statements):
    """Run SQL statements one by one (no bind-parameter parsing)."""
    conn = op.get_bind()
    for s in statements:
        conn.exec_driver_sql(s)


def upgrade():
    run([])


def downgrade():
    run([])
