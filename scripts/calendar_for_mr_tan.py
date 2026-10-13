#!/usr/bin/env python3
"""Put Mr Tan's medicine reminders on the shared Google Calendar (Joely's request, 2026-10-13: the demo shows Mr Tan's use case only).

Usage (from the repository root):
  python scripts/calendar_for_mr_tan.py            dry run: say what would happen, change nothing
  python scripts/calendar_for_mr_tan.py --yes      do it

What it does, in order:
  1. turns the calendar consent OFF for the demo user (so only Mr Tan's reminders are made from now on);
  2. turns the calendar consent ON for Mr Tan (the app cannot do this for him: his record is read only from the screens);
  3. makes the events for the next 14 days that are not there yet, for every person who has the consent (that is Mr Tan only), through the
     Workato recipe (needs WORKATO_WEBHOOK_URL and WORKATO_WEBHOOK_TOKEN in .env).
Events already on the calendar are never made twice, and none is deleted (delete the old ones by hand in Google Calendar).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

from app.db import logstore  # noqa: E402
from app.integrations.workato import WorkatoClient  # noqa: E402
from app.services import calendar_sync, me_settings  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="do it (without it: a dry run)")
    args = ap.parse_args()
    client = WorkatoClient.from_settings()
    print(f"Workato set up: {client.configured}")
    print("1. calendar consent OFF for the demo user")
    print("2. calendar consent ON for Mr Tan")
    print("3. make the next 14 days of events for Mr Tan's medicines")
    if not args.yes:
        print("Dry run: nothing was changed. Run again with --yes.")
        return 0
    if not client.configured:
        print("Workato is not set up in .env: stopping.")
        return 1
    with logstore.tx() as c:
        me_settings.set_consent(c, logstore.USERS["demo"]["id"], "calendar_access", False)
        me_settings.set_consent(c, logstore.MR_TAN_USER, "calendar_access", True)
    out = calendar_sync.top_up_all(client)
    print("top-up:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
