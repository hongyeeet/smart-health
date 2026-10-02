#!/usr/bin/env python3
"""Shared helpers for the E1-4 loaders (import_*.py, seed_*.py, simulate_persona.py, replay.py).

The rules every loader follows:
  * Safe to run twice. Every row gets a stable id made from its natural key (uid()), and rows go in with
    INSERT ... ON CONFLICT DO NOTHING, so a second run inserts nothing.
  * Times: the clock times in the datasets are read as Asia/Singapore local time and stored in UTC.
  * Dates are shifted per person so the last real day lands on the demo end date (shift_days()).
  * Glucose is stored in mmol/L only (mg/dL / 18, one decimal).
  * Rows made from the cited datasets carry entry_source = 'demo_dataset'; simulated rows carry the same value
    and an external_id that starts with 'sim:' (see data/demo/DISCLOSURE.md).
No secrets are printed.
"""
import csv
import json
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
DEMO_DIR = ROOT / "data" / "demo"
CONFIG = DEMO_DIR / "demo_config.json"
SGT = ZoneInfo("Asia/Singapore")
NAMESPACE = uuid.UUID("5c0a3f0e-1b2d-4c6e-9a77-0c0ffee50001")  # fixed: ids derived from it never change
DEMO_SOURCE = "demo_dataset"


def uid(*parts):
    """Stable uuid from a natural key, for example uid('user', 'cgmacros-046')."""
    return uuid.uuid5(NAMESPACE, ":".join(str(p) for p in parts))


def connect():
    load_env()
    return psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=30)


# ---------------------------------------------------------------- time and units
def local_to_utc(naive):
    """A naive clock time from a dataset, read as Singapore local time, as an aware UTC datetime."""
    return naive.replace(tzinfo=SGT).astimezone(timezone.utc)


def mgdl_to_mmol(v):
    """mg/dL to mmol/L, one decimal (schema.md: divide by 18.0)."""
    return round(float(v) / 18.0 + 1e-9, 1)


def demo_end_date(override=None):
    """The date the real CGM days end on. Stored on first use so every run (and every teammate) agrees."""
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    if override:
        d = date.fromisoformat(override)
        CONFIG.write_text(json.dumps({"end_date": d.isoformat()}, indent=2) + "\n", encoding="utf-8")
        return d
    if CONFIG.exists():
        return date.fromisoformat(json.loads(CONFIG.read_text(encoding="utf-8"))["end_date"])
    d = datetime.now(SGT).date()
    CONFIG.write_text(json.dumps({"end_date": d.isoformat()}, indent=2) + "\n", encoding="utf-8")
    return d


def shift_days(last_real_day, end_date):
    """Whole days to add to a person's timestamps so their last real day lands on end_date."""
    return (end_date - last_real_day).days


# ---------------------------------------------------------------- loading
def bulk_insert(conn, table, columns, rows, batch=50000):
    """INSERT rows (tuples in `columns` order) with ON CONFLICT DO NOTHING; returns how many were really inserted.

    Rows are streamed with COPY into a temporary table and merged, which is fast over the network.
    Pass a stable id (uid(...)) in the 'id' column so a second run conflicts and inserts nothing.
    """
    rows = list(rows)
    if not rows:
        return 0
    cols = ", ".join(columns)
    inserted = 0
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        with conn.cursor() as cur:
            cur.execute(f"CREATE TEMP TABLE _stage (LIKE public.{table} INCLUDING DEFAULTS) ON COMMIT DROP")
            with cur.copy(f"COPY _stage ({cols}) FROM STDIN") as cp:
                for r in chunk:
                    cp.write_row(r)
            cur.execute(f"INSERT INTO public.{table} ({cols}) SELECT {cols} FROM _stage ON CONFLICT DO NOTHING")
            inserted += cur.rowcount
            cur.execute("DROP TABLE _stage")
    return inserted


def count(conn, table, where="true", params=()):
    return conn.execute(f"SELECT count(*) FROM public.{table} WHERE {where}", params).fetchone()[0]


# ---------------------------------------------------------------- Bronze for local dataset files
_log_cache = {}


def _download_log():
    if not _log_cache:
        path = ROOT / "data" / "download_log.csv"
        if path.exists():
            with open(path, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    _log_cache[r["file"]] = r
    return _log_cache


def log_dataset_file(conn, user_id, path, source_type="dataset_import"):
    """Write the Bronze ingestion_events row for a dataset file that stays in data/raw (no upload).

    The checksum comes from data/download_log.csv (computed when the file was downloaded); if the file was
    made later (for example a derived file) it is hashed here. Repeat-safe: UNIQUE (user_id, checksum).
    """
    import hashlib
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    entry = _download_log().get(rel)
    if entry:
        checksum, received = entry["sha256"], entry["downloaded_at"]
        received_at = datetime.strptime(received, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    else:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        checksum, received_at = h.hexdigest(), datetime.now(timezone.utc)
    ext = Path(path).suffix.lower()
    ctype = {".csv": "text/csv", ".zip": "application/zip", ".json": "application/json", ".xpt": "application/octet-stream"}.get(ext, "text/plain")
    return bulk_insert(conn, "ingestion_events",
                       ["id", "user_id", "source_type", "object_key", "checksum", "received_at", "content_type", "schema_version", "processing_status", "entry_source"],
                       [(uid("ingest", user_id, checksum), user_id, source_type, None, checksum, received_at, ctype, "v1", "processed", DEMO_SOURCE)])


def ensure_user(conn, key, locale="en"):
    """Create the demo user for a dataset person (stable id from the key) and return its uuid."""
    u = uid("user", key)
    bulk_insert(conn, "users", ["id", "locale", "is_demo"], [(u, locale, True)])
    return u


def report(title, **numbers):
    print(f"{title}: " + ", ".join(f"{k}={v:,}" if isinstance(v, int) else f"{k}={v}" for k, v in numbers.items()))


if __name__ == "__main__":
    load_env()
    with connect() as c:
        size = c.execute("select pg_size_pretty(pg_database_size(current_database()))").fetchone()[0]
        print("database size:", size, "| free plan limit: 500 MB | target for E1-4: under about 300 MB")
