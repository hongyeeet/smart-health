#!/usr/bin/env python3
"""Replay tool: stream the demo patient's last 3 hours of sensor data as if it were live (E1-4 step 10).

import_cgmacros.py holds back the final 3 hours of Mr Tan's Libre glucose and active-energy readings in
data/demo/replay_feed.jsonl. This tool inserts them one minute at a time (committing each minute, so the app sees
them arrive) as entry_source = 'replay'. It only inserts data: urgent-threshold checks and the rest of the logic run
in the app, as for any real reading. Safe to run twice (a second run inserts nothing; use --reset to replay again).

Usage:
  python scripts/replay.py                  real time (1 data minute per real minute)
  python scripts/replay.py --speed 60       fast: 1 data minute per second
  python scripts/replay.py --speed 0        instant
  python scripts/replay.py --limit 20       only the first 20 minutes
  python scripts/replay.py --reset          delete the replayed rows so they can be streamed again
"""
import argparse
import json
import sys
import time
from datetime import datetime
from itertools import groupby
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etl_common import DEMO_DIR, bulk_insert, connect, count, uid  # noqa: E402

FEED = DEMO_DIR / "replay_feed.jsonl"
USER = uid("user", "cgmacros-046")


def reset(conn):
    n1 = conn.execute("delete from glucose_readings where user_id = %s and source = 'replay'", (USER,)).rowcount
    n2 = conn.execute("delete from health_samples where user_id = %s and source = 'replay'", (USER,)).rowcount
    conn.commit()
    print(f"removed {n1} replayed glucose readings and {n2} replayed samples")


def insert_minute(conn, items):
    g, h = [], []
    for it in items:
        r = it["row"]
        ext = r["external_id"]
        if it["table"] == "glucose_readings":
            g.append((uid("glu", "replay", ext), USER, datetime.fromisoformat(r["measured_at"]), r["value_mmol"], "cgm", "replay", ext, uid("sprint", "cgmacros", 46), r["device"], True, r["native_interval_min"]))
        else:
            h.append((uid("hs", "replay", ext), USER, r["metric"], datetime.fromisoformat(r["start_at"]), datetime.fromisoformat(r["end_at"]), r["value"], r["unit"], "replay", r["device"], ext))
    n = bulk_insert(conn, "glucose_readings", ["id", "user_id", "measured_at", "value_mmol", "context", "source", "external_id", "cgm_sprint_id", "device", "quality_ok", "native_interval_min"], g)
    n += bulk_insert(conn, "health_samples", ["id", "user_id", "metric", "start_at", "end_at", "value", "unit", "source", "device", "external_id"], h)
    conn.commit()
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--speed", type=float, default=1.0, help="data minutes per real minute; 0 = instant")
    ap.add_argument("--limit", type=int, default=0, help="stop after this many data minutes")
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()
    with connect() as conn:
        if a.reset:
            reset(conn)
            return
        rows = [json.loads(line) for line in FEED.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not rows:
            raise SystemExit("The replay feed is empty. Run scripts/import_cgmacros.py first.")
        minutes = [(t, list(g)) for t, g in groupby(rows, key=lambda r: r["t"])]
        if a.limit:
            minutes = minutes[:a.limit]
        print(f"replaying {len(minutes)} data minutes ({len(rows)} readings) at speed {a.speed:g}")
        prev, total = None, 0
        for t, items in minutes:
            now = datetime.fromisoformat(t)
            if prev is not None and a.speed > 0:
                time.sleep(max(0.0, (now - prev).total_seconds() / 60.0 * 60.0 / a.speed))
            prev = now
            total += insert_minute(conn, items)
            if total and (total % 60 == 0 or t == minutes[-1][0]):
                print(f"  {t}: {total} readings inserted so far")
        print(f"done: {total} readings inserted ({count(conn, 'glucose_readings', chr(39) + 'replay' + chr(39) + ' = source')} replayed glucose rows now)")


if __name__ == "__main__":
    main()
