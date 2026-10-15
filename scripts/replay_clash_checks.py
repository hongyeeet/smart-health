"""Replay the medicine clash check as if a person's medicines were added one by one, in the order they were started (prd F5).

For each step it runs the real check (the drug-pair rules plus the AI model with a web search) on the medicines "added so far", saves
what it finds, and prints the result. Nothing is deleted: the medicines and their dose history are untouched. With --reset the person's
existing clash alerts are removed first, so the replay shows exactly what the checker raises on its own.

  python scripts/replay_clash_checks.py --user mr-tan --reset

Every step after the first sends the medicine names (no personal details) to the model with a web search.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))
sys.path.insert(0, str(ROOT / "scripts"))

from download_data import load_env  # noqa: E402

load_env()

from psycopg.rows import tuple_row  # noqa: E402

from app.agents import clash_pipeline  # noqa: E402
from app.db import logstore  # noqa: E402
from app.services import clash_store as store  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user", default="mr-tan", choices=sorted(logstore.USERS))
    ap.add_argument("--reset", action="store_true", help="remove the person's existing clash alerts first")
    a = ap.parse_args()
    user = str(logstore.USERS[a.user]["id"])
    with logstore.tx() as conn:
        conn.row_factory = tuple_row
        meds = store.list_medicines(conn, user)
        if a.reset:
            n = conn.execute("delete from interaction_alerts where user_id = %s", (user,)).rowcount
            print(f"removed {n} existing alerts")
    print(f"{len(meds)} medicines, in the order they were started:")
    for i, m in enumerate(meds, 1):
        print(f"  {i}. {m['name']} ({m['kind']})")
    for k in range(1, len(meds) + 1):
        added = meds[k - 1]
        res = clash_pipeline.check_user(user, only_ids=[m["id"] for m in meds[:k]])
        with logstore.tx() as conn:
            conn.row_factory = tuple_row
            open_now = store.list_open(conn, user)
        print(f"\nadded {k}: {added['name']}  ->  checked {res['medicines']} medicines; database pairs {res['database']}, AI pairs {res['ai']} (AI {res['ai_status']}"
              f"{', ' + res['reason'] if res.get('reason') else ''}); new alerts {res['new']}")
        for al in open_now:
            print(f"    [{al['origin']}] {al['med_a']} + {al['med_b']}: {al['summary']}")
        if not open_now:
            print("    no alert box")


if __name__ == "__main__":
    main()
