#!/usr/bin/env python3
"""Give the demo user the same medicines and tablet counts as Mr Tan (Joely's request, 2026-10-13).

Usage (from the repository root):
  python scripts/seed_demo_from_mr_tan.py            dry run: show what would be added, change nothing
  python scripts/seed_demo_from_mr_tan.py --yes      do it (one transaction)

What it does: for each live medicine Mr Tan has, the demo user gets the same one (name, kind, strength, dose times, directions, pack size,
start date) when the demo user has no medicine of that name yet, saved the way the app saves a typed-in medicine. Then the tablet count
is set to Mr Tan's current number, and a finished course keeps its end date and has no count. The demo user's own medicines (CRESTOR,
168 tablets) are left as they are. Mr Tan is only READ here. Re-running adds nothing, because a name that is already there is skipped.
The demo user's logs (meals, sleep, glucose, doses) are not touched.
"""
import argparse
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

from psycopg.rows import tuple_row  # noqa: E402

from app.db import logstore  # noqa: E402
from app.schemas.medicine_scan import ConfirmedMedication, DoseTime  # noqa: E402
from app.services import medication_stock as stock  # noqa: E402
from app.services.scan_store import confirm_medication  # noqa: E402

DEMO_USER = "bfd254d6-3498-5f9a-8cbd-343b58513bf6"
FALLBACK_PACK = 20      # the Herbal tonic has no pack size on file (as in seed_mr_tan_stock.py)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="write the medicines (without it: a dry run)")
    args = ap.parse_args()
    now = datetime.now(logstore.TZ)
    with logstore.tx() as c:
        if not stock.stock_ready(c):
            print("Migration 0032 is not applied: nothing to do.")
            return 1
        if str(c.execute("select id from users where id = %s", (DEMO_USER,)).fetchone()["id"]) != DEMO_USER:
            print("The demo user was not found.")
            return 1
        have = {r["name"].strip().lower() for r in c.execute("select name from medications where user_id = %s and deleted_at is null", (DEMO_USER,)).fetchall()}
        meds = c.execute(
            "select id, name, kind::text kind, strength, description, start_date, end_date, total_quantity, as_needed, stock_count, stock_unit "
            "from medications where user_id = %s and deleted_at is null order by created_at, name", (str(logstore.MR_TAN_USER),)).fetchall()
        doses_of = {m["id"]: c.execute(
            "select dose_time, quantity, meal_relation::text rel from medication_schedule where medication_id = %s and deleted_at is null order by dose_time",
            (m["id"],)).fetchall() for m in meds}
        c.row_factory = tuple_row           # the app's save routine reads rows by position
        for m in meds:
            if m["name"].strip().lower() in have:
                print(f"keep     {m['name']}: the demo user already has it")
                continue
            doses = doses_of[m["id"]]
            pack = m["total_quantity"] or FALLBACK_PACK
            count, unit = m["stock_count"], m["stock_unit"]
            print(f"add      {m['name']}: {len(doses)} dose time(s), pack {pack}, now {count if count is not None else 'no count'} {unit or ''}".rstrip())
            if not args.yes:
                continue
            entry = ConfirmedMedication(
                name=m["name"], kind=m["kind"], strength=m["strength"], directions=m["description"], total_quantity=pack, start_date=m["start_date"],
                doses=[DoseTime(dose_time=d["dose_time"], quantity=d["quantity"], meal_relation=d["rel"]) for d in doses] or [DoseTime(dose_time=None, quantity=Decimal(1), meal_relation="na")])
            new_id = confirm_medication(c, DEMO_USER, entry)
            if m["end_date"] is not None:
                c.execute("update medications set end_date = %s where id = %s", (m["end_date"], new_id))
            if count is None:         # a finished course: no count, as for Mr Tan
                c.execute("update medications set stock_count = null, stock_unit = null, stock_updated_at = null where id = %s", (new_id,))
            else:
                c.execute("update medications set stock_count = %s, stock_unit = %s, stock_updated_at = %s where id = %s", (Decimal(count), unit, now, new_id))
        if not args.yes:
            print("Dry run: nothing was changed. Run again with --yes to write these.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
