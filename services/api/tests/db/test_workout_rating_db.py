"""Optional workout rating, database side: the column check that the API reads, and migration 0036 with its downgrade guard.

Every test runs inside a transaction that is rolled back, so the shared database is left as it was (still revision 0035 until the
owner applies 0036). Run from services/api:  python -m pytest tests/db/test_workout_rating_db.py -q
"""
import importlib.util
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row
from sqlalchemy import create_engine, pool, text

from app.db import logstore

MIGRATION = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "0036_workout_intensity_optional.py"


@pytest.fixture()
def conn(monkeypatch):
    # the yes-cache is module state: start from "not known" and let monkeypatch restore the original afterwards
    monkeypatch.setattr(logstore, "_rating_optional_known", False)
    c = psycopg.connect(logstore._dsn(), connect_timeout=20, row_factory=dict_row)
    try:
        yield c
    finally:
        c.rollback()
        c.close()


def set_nullable(c, nullable: bool):
    if not nullable:
        # real unrated workouts may exist now (the column is optional); inside this rolled-back transaction give them a value so the old
        # NOT NULL layout can be simulated. Nothing is committed.
        c.execute("update exercise_logs set intensity = 3 where intensity is null")
    c.execute("alter table exercise_logs alter column intensity " + ("drop not null" if nullable else "set not null"))


def test_rating_optional_is_false_while_the_column_is_not_null(conn):
    set_nullable(conn, False)
    assert logstore.rating_optional(conn) is False
    assert logstore._rating_optional_known is False  # a no is never cached


def test_rating_optional_is_true_once_the_column_allows_null_and_the_yes_is_kept(conn):
    set_nullable(conn, True)
    assert logstore.rating_optional(conn) is True
    assert logstore._rating_optional_known is True
    set_nullable(conn, False)  # a cached yes is not read again, so the flag stays on for the life of the process
    assert logstore.rating_optional(conn) is True


def test_migration_0036_upgrade_keeps_the_range_check_and_downgrade_refuses_a_null_rating():
    spec = importlib.util.spec_from_file_location("m0036", MIGRATION)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    engine = create_engine("postgresql+psycopg://" + logstore._dsn().split("://", 1)[1], poolclass=pool.NullPool)
    try:
        with engine.connect() as c0:
            before = c0.execute(text("select is_nullable from information_schema.columns where table_name='exercise_logs' and column_name='intensity'")).scalar()
        with engine.connect() as c:
            tx = c.begin()
            try:
                with Operations.context(MigrationContext.configure(connection=c)):
                    m.upgrade()
                    m.upgrade()  # running twice is harmless
                    assert c.execute(text("select is_nullable from information_schema.columns where table_name='exercise_logs' and column_name='intensity'")).scalar() == "YES"
                    assert c.execute(text("select count(*) from pg_constraint where conrelid='exercise_logs'::regclass and conname='exercise_logs_intensity_check'")).scalar() == 1
                    uid = c.execute(text("insert into users (is_demo) values (true) returning id")).scalar()
                    bid = c.execute(text("insert into bronze_exercise (user_id, source, payload, checksum) values (:u, 'manual', '{}'::jsonb, :k) returning id"),
                                    {"u": uid, "k": str(uuid.uuid4())}).scalar()
                    c.execute(text("insert into exercise_logs (user_id, start_at, end_at, type, intensity, source, bronze_id) "
                                   "values (:u, '2026-10-01T10:00:00Z', '2026-10-01T10:30:00Z', 'walking', null, 'manual', :b)"), {"u": uid, "b": bid})
                    with pytest.raises(RuntimeError, match="no rating"):
                        m.downgrade()  # one unrated workout is present: refused, nothing changed
                    assert c.execute(text("select is_nullable from information_schema.columns where table_name='exercise_logs' and column_name='intensity'")).scalar() == "YES"
            finally:
                tx.rollback()
        with engine.connect() as c:  # the rollback leaves the database as it was
            assert c.execute(text("select is_nullable from information_schema.columns where table_name='exercise_logs' and column_name='intensity'")).scalar() == before
    finally:
        engine.dispose()
