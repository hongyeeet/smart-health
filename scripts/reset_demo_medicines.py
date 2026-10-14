#!/usr/bin/env python3
"""Make the demo user a person who has never logged a medicine (Joely's request, 2026-10-14).

Usage (from the repository root):
  python scripts/reset_demo_medicines.py            dry run: count what would go, change nothing
  python scripts/reset_demo_medicines.py --yes      do it (one transaction)

Only the DEMO user is touched (never Mr Tan). What is done:
  - every live medicine is removed the way the app removes one (the soft delete `deleted_at`, the app rule), with its dose times;
  - the demo user's medicine records that hang on them are deleted outright: the dose log, calendar sync rows, interaction alerts, scan
    history (the label scans), saved explanations, medicine reminders (dose, re-nudge, refill, missed-dose questions) and the learned dose-time arms;
  - the doctor question about CRESTOR is archived.
The event log is append-only and is never changed. Events already on Google Calendar are not removed (delete them by hand).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

from app.db import logstore  # noqa: E402
from app.services.medication_remove import remove_medication  # noqa: E402

DEMO = str(logstore.USERS["demo"]["id"])

DELETES = [
    ("medication_log", "user_id = %s"),
    ("calendar_syncs", "user_id = %s"),
    ("interaction_alerts", "user_id = %s"),
    ("prescription_scans", "user_id = %s"),
    ("medication_explanations", "user_id = %s"),
    ("notifications", "user_id = %s and kind::text in ('dose_reminder', 'dose_renudge', 'refill', 'miss_reason')"),
    ("nudge_policy", "user_id = %s and arm_key like 'dose_time:%%'"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="do it (without it: a dry run)")
    args = ap.parse_args()
    with logstore.tx() as c:
        meds = c.execute("select id, name from medications where user_id = %s and deleted_at is null order by name", (DEMO,)).fetchall()
        print(f"medicines to remove: {[m['name'] for m in meds]}")
        for table, where in DELETES:
            try:
                n = c.execute(f"select count(*) n from {table} where {where}", (DEMO,)).fetchone()["n"]
            except Exception as e:  # noqa: BLE001
                print(f"  {table}: skipped ({str(e)[:50]})")
                c.rollback()
                continue
            print(f"  {table}: {n} row(s)")
            if args.yes and n:
                c.execute(f"delete from {table} where {where}", (DEMO,))
        if args.yes:
            c.row_factory = __import__("psycopg").rows.tuple_row
            for m in meds:
                remove_medication(c, DEMO, str(m["id"]) if isinstance(m, dict) else str(m[0]))
            c.execute("update doctor_questions set status = 'archived' where user_id = %s and text like 'About CRESTOR%%' and status <> 'archived'", (DEMO,))
            print("Done.")
        else:
            print("Dry run: nothing was changed. Run again with --yes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
