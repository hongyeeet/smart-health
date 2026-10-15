#!/usr/bin/env python3
"""Give Mr Tan's medicines a tablet count, so "All medications" on the Meds tab shows real numbers (Joely's request, 2026-10-12).

Usage (from the repository root):
  python scripts/seed_mr_tan_stock.py            dry run: show what would be set, change nothing
  python scripts/seed_mr_tan_stock.py --yes      do it (one transaction)

Why: Mr Tan's 90 days of doses were loaded straight into the dose log, so they never went through the stock code and every medicine
says "Not set yet". The counts below are sample values chosen to match his history (Metformin at 4 tablets keeps the "about 2 days left"
refill notice true). Each medicine gets the "start" event for its pack size (so the bar's full mark is the pack) and then the current
number. It only touches a medicine that has no count yet, so running it again changes nothing. Clarithromycin is a 7-day course that
ended on 19 September, so it gets no count. The Herbal tonic has no pack size on file: 20 capsules is a made-up start.

Writes to a shared record: Mr Tan is read-only for everything else, so this runs only when asked for.
"""
import argparse
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

from app.db import logstore  # noqa: E402
from app.services import medication_stock as stock  # noqa: E402

# name -> (tablets or capsules left now, the unit word, the pack size to start from when the medicine has none on file)
COUNTS = {
    "Amlodipine 5 mg": (23, "tablets", None),
    "Atorvastatin 20 mg": (17, "tablets", None),
    "Metformin 500 mg": (4, "tablets", None),
    "Fish oil": (41, "capsules", None),
    "Herbal tonic (label not readable)": (20, "capsules", 20),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="write the counts (without it: a dry run)")
    args = ap.parse_args()
    now = datetime.now(logstore.TZ)
    with logstore.tx() as c:
        if not stock.stock_ready(c):
            print("Migration 0032 is not applied: nothing to do.")
            return 1
        rows = c.execute(
            "select id, name, total_quantity, stock_count from medications where user_id = %s and deleted_at is null order by name",
            (str(logstore.MR_TAN_USER),)).fetchall()
        for r in rows:
            mid, name, pack, current = r["id"], r["name"], r["total_quantity"], r["stock_count"]
            if name not in COUNTS:
                print(f"skip     {name}: no count (not a regular medicine in stock, or its course ended)")
                continue
            if current is not None:
                print(f"keep     {name}: already {current}")
                continue
            count, unit, fallback_pack = COUNTS[name]
            start = pack or fallback_pack or count
            print(f"set      {name}: pack {start} -> {count} {unit}")
            if args.yes:
                stock.set_start_count(c, str(logstore.MR_TAN_USER), mid, int(start), unit, now)
                c.execute("update medications set stock_count = %s, stock_updated_at = %s where id = %s", (Decimal(count), now, mid))
        if not args.yes:
            print("Dry run: nothing was changed. Run again with --yes to write these.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
