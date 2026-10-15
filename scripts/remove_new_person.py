#!/usr/bin/env python3
"""Delete the people made with the removed "Start as new person" button (Joely's request, 2026-10-13), and everything stored for them.

Usage (from the repository root):
  python scripts/remove_new_person.py            dry run: list who would be deleted and how many rows, change nothing
  python scripts/remove_new_person.py --yes      do it (one transaction)

A person here is any row in `users` that is not the demo user, not Mr Tan and not marked is_demo. The demo user and Mr Tan are never
touched. For each person the rows in every table with a user_id column are deleted first (the event log is append-only and is never
deleted from here), then the user row.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

from app.db import logstore  # noqa: E402

KEEP_TABLES = {"event_log"}      # append-only and hash-chained: never deleted from here


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="delete (without it: a dry run)")
    args = ap.parse_args()
    keep = {str(logstore.USERS["demo"]["id"]), str(logstore.MR_TAN_USER)}
    with logstore.tx() as c:
        people = [str(r["id"]) for r in c.execute("select id from users where coalesce(is_demo, false) = false").fetchall() if str(r["id"]) not in keep]
        if not people:
            print("No new persons found. Nothing to do.")
            return 0
        tables = [r["table_name"] for r in c.execute(
            "select distinct table_name from information_schema.columns where column_name = 'user_id' and table_schema = 'public' "
            "and table_name in (select table_name from information_schema.tables where table_schema = 'public' and table_type = 'BASE TABLE') order by 1").fetchall()]
        for uid in people:
            print(f"person {uid}")
            for t in tables:
                if t in KEEP_TABLES:
                    n = c.execute(f"select count(*) n from {t} where user_id = %s", (uid,)).fetchone()["n"]
                    if n:
                        print(f"   {t}: {n} row(s) kept (append-only)")
                    continue
                n = c.execute(f"select count(*) n from {t} where user_id = %s", (uid,)).fetchone()["n"]
                if n:
                    print(f"   {t}: {n} row(s)" + ("  -> delete" if args.yes else ""))
                    if args.yes:
                        c.execute(f"delete from {t} where user_id = %s", (uid,))
            if args.yes:
                c.execute("delete from users where id = %s", (uid,))
                print("   user row deleted")
        if not args.yes:
            print("Dry run: nothing was changed. Run again with --yes to delete these.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
