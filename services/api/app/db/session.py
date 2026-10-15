"""Async SQLAlchemy session factory.

Uses the Supabase Session pooler connection string (port 5432). The pgbouncer parameter
is stripped because the psycopg 3 driver rejects it.
"""
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _clean_database_url(url: str) -> str:
    """Strip pgbouncer and use the psycopg (async) driver."""
    if not url:
        return ""
    u = urlparse(url)
    query = "&".join(p for p in u.query.split("&") if p and not p.startswith("pgbouncer="))
    scheme = "postgresql+psycopg" if u.scheme in ("postgres", "postgresql") else u.scheme
    return u._replace(scheme=scheme, query=query).geturl()


_DB_URL = _clean_database_url(settings.database_url)

# Async engine for the FastAPI app
async_engine = create_async_engine(_DB_URL, pool_pre_ping=True, echo=False) if _DB_URL else None

# Sync engine for scripts and tests
_sync_url = _clean_database_url(settings.database_url).replace("+psycopg", "") if _DB_URL else ""
sync_engine = create_engine(_sync_url, pool_pre_ping=True) if _sync_url else None

AsyncSessionFactory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False) if async_engine else None


def get_async_session() -> AsyncSession:
    """FastAPI dependency: yields an async session."""
    if AsyncSessionFactory is None:
        raise RuntimeError("DATABASE_URL is not set. Add it to the repo .env.")
    return AsyncSessionFactory()
