"""Alembic environment. Migrations are plain SQL (docs/specs/schema.md is the source of truth).

The database URL is read from DATABASE_URL in the repo's private .env (never committed).
Use the Supabase Session pooler string (port 5432) for migrations.
"""
import os
from pathlib import Path
from urllib.parse import urlparse

from alembic import context
from sqlalchemy import create_engine, pool

ROOT = Path(__file__).resolve().parents[3]


def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def database_url():
    load_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set. Add it to the private .env (see .env.example).")
    u = urlparse(url)
    # Python's driver rejects Supabase's ?pgbouncer=true; use the psycopg 3 driver.
    query = "&".join(p for p in u.query.split("&") if p and not p.startswith("pgbouncer="))
    scheme = "postgresql+psycopg" if u.scheme in ("postgres", "postgresql") else u.scheme
    return u._replace(scheme=scheme, query=query).geturl()


def run_migrations_online():
    engine = create_engine(database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise SystemExit("Offline mode is not supported: run against the database.")
run_migrations_online()
