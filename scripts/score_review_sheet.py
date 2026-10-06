#!/usr/bin/env python3
"""Read the reviewer's ratings from docs/review/swap_review_sheet.csv and report the result against the 85% target.

A suggestion counts as good if it was rated "reasonable". "unsafe" is reported separately: any unsafe suggestion is a defect to fix before
a demo, whatever the overall share.
"""
import csv
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "docs" / "review" / "swap_review_sheet.csv"
TARGET = 0.85


def main():
    rows = list(csv.DictReader(PATH.open(encoding="utf-8-sig")))
    key = next(k for k in rows[0] if k.startswith("RATING"))
    rated = [r for r in rows if r[key].strip()]
    if not rated:
        print(f"{len(rows)} suggestions, none rated yet. Ask a reviewer to fill the RATING column in {PATH}")
        return
    count = lambda v: sum(1 for r in rated if r[key].strip().lower() == v)  # noqa: E731
    ok, no, bad = count("reasonable"), count("not reasonable"), count("unsafe")
    share = ok / len(rated)
    print(f"{len(rated)} of {len(rows)} rated. Reasonable {ok} ({share:.0%}), not reasonable {no}, unsafe {bad}.")
    print(f"Target {TARGET:.0%}: {'MET' if share >= TARGET and bad == 0 else 'NOT MET'}" + ("" if bad == 0 else f" ({bad} unsafe: fix these first)"))
    for r in rated:
        if r[key].strip().lower() in ("not reasonable", "unsafe"):
            print(f"  {r['id']} {r['usual_dish']}  ->  {r['suggested_dish']}   [{r[key]}] {r['reviewer_comment']}")


if __name__ == "__main__":
    main()
