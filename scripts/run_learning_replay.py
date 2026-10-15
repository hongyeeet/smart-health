#!/usr/bin/env python3
"""Run the adherence learning agent over a person's history and print what it would learn (docs/specs/learning-loop.md section 7).

Usage:
  python scripts/run_learning_replay.py                 # Mr Tan, dry run: nothing is written
  python scripts/run_learning_replay.py --write         # store the proposals (memory_facts as 'proposed', adherence_barriers, content_proposals)

Honest scope: this shows what the agent would PROPOSE from real logged history, and the adherence the person already had by week.
It cannot show that nudges improved adherence, because no nudges were sent in the history. That needs the live loop and time.
"""
import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

MR_TAN = uuid.UUID("dc48e209-5731-5b3d-89d9-986242c54368")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="store the proposals (default: dry run)")
    args = ap.parse_args()
    from app.agents import adherence

    r = adherence.run(MR_TAN, write=args.write)
    print("On-time dose rate by week (taken within 60 minutes), from medication_log:")
    for w in r["on_time"]:
        print(f"  {w['week_start']}  {w['doses']:3d} doses  {w['on_time_pct']:3d}%")
    print("\nBarrier totals (from the reasons given for missed doses):")
    tot = {}
    for b in r["barriers"]:
        tot[b["barrier"]] = tot.get(b["barrier"], 0) + b["n"]
    for k, v in sorted(tot.items(), key=lambda kv: -kv[1]):
        print(f"  {k:14s} {v}")
    print("\nWeekend-evening pattern:", r["weekend_evening"])
    print("Morning anchor evidence:", r["morning_anchor"])
    print("\nProposals (all stay 'proposed' until confirmed):")
    for p in r["proposals"]:
        print(f"  [{p['guard']}] {p['key']}  conf {p['confidence']}  -> {p['result']}\n      {p['statement']}")
    from app.db import nutritionstore

    print("\nFood habits (from the person's own logged meals; the food database is only a shelf of lighter dishes):")
    for h in nutritionstore.food_habits(MR_TAN):
        print("  *", nutritionstore.habit_text(h))
    for p in nutritionstore.reflect_habits(MR_TAN, write=args.write):
        print(f"  [{p['guard']}] {p['key']} -> {p['result']}\n      {p['statement']}")
    if r.get("draft"):
        print("\nDrafted for review:", r["draft"])
    if not args.write:
        print("\n(dry run: nothing written. Use --write to store the proposals.)")


if __name__ == "__main__":
    main()
