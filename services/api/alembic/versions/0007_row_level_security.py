"""Turn row-level security on for every table in public, with no policies.

Source: docs/specs/schema.md section 0 and architecture.md (Platform decisions): the public API key
must be able to read and write nothing; only the backend connects with server-side credentials.
Per-user policies are deferred (memory.md section 13).

This also covers alembic_version, the migration tool's own table. Any table added later in another
migration (for example Gold and Operations tables in E1-3) must enable RLS the same way.

Revision ID: 0007
Revises: 0006
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

DO_ENABLE = """DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE 'ALTER TABLE public.' || quote_ident(r.tablename) || ' ENABLE ROW LEVEL SECURITY';
  END LOOP;
END $$"""

DO_DISABLE = """DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE 'ALTER TABLE public.' || quote_ident(r.tablename) || ' DISABLE ROW LEVEL SECURITY';
  END LOOP;
END $$"""


def upgrade():
    op.get_bind().exec_driver_sql(DO_ENABLE)


def downgrade():
    op.get_bind().exec_driver_sql(DO_DISABLE)
