#!/usr/bin/env python3
"""Remove the demo user and everything stored for them (Joely's request, 2026-10-14: the app opens on Mr Tan, and new people start their own user).

Usage (from the repository root):
  python scripts/remove_demo_user.py            dry run: list how many rows would go from each table, change nothing
  python scripts/remove_demo_user.py --yes      do it (one transaction: all of it, or none of it)

The demo user is the one row in `users` with the id `uuid5(NAMESPACE, "user:app-demo")`. For every table with a `user_id` column the person's rows are
deleted (tables that point at other tables are taken in the order the foreign keys allow), then the user row. Mr Tan and every other person are never
touched. The event log is append-only and hash-chained and is NEVER deleted from here: its rows for the demo user stay, holding only the old user id,
kinds and counts, never a name or an answer.
"""
import argparse
import sys
import uuid
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

from app.db import logstore  # noqa: E402

DEMO = uuid.uuid5(logstore.NAMESPACE, "user:app-demo")
KEEP_TABLES = {"event_log"}      # append-only: never deleted from here


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="do it (without it: a dry run)")
    args = ap.parse_args()
    assert DEMO != logstore.MR_TAN_USER
    with logstore.tx() as c:
        row = c.execute("select is_demo from users where id = %s", (DEMO,)).fetchone()
        if row is None:
            print("There is no demo user. Nothing to do.")
            return 0
        tables = [r["table_name"] for r in c.execute(
            "select distinct table_name from information_schema.columns where column_name = 'user_id' and table_schema = 'public' "
            "and table_name in (select table_name from information_schema.tables where table_schema = 'public' and table_type = 'BASE TABLE') order by 1").fetchall()]
        counts = {t: c.execute(f'select count(*) n from "{t}" where user_id = %s', (DEMO,)).fetchone()["n"] for t in tables}
        for t, n in counts.items():
            if n:
                print(f"  {t}: {n} row(s)" + ("  (kept: append-only)" if t in KEEP_TABLES else ""))
        if not args.yes:
            print("Dry run: nothing was changed. Run again with --yes.")
            return 0
        left = {t for t, n in counts.items() if n and t not in KEEP_TABLES}
        while left:                                          # a table another table points at waits until that one is empty
            progress = False
            for t in sorted(left):
                c.execute("savepoint s")
                try:
                    c.execute(f'delete from "{t}" where user_id = %s', (DEMO,))
                except psycopg.errors.ForeignKeyViolation:
                    c.execute("rollback to savepoint s")
                    continue
                c.execute("release savepoint s")
                left.discard(t)
                progress = True
            if not progress:
                raise SystemExit(f"Stopped without changing anything: could not delete from {sorted(left)} (a foreign key still points at them).")
        c.execute("delete from users where id = %s", (DEMO,))
        print("Demo user and their rows deleted. The event log rows are kept.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
