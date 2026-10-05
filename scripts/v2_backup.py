#!/usr/bin/env python3
"""Export every table of the public schema to gzip CSV files before the v2 reset (migration 0017).

Usage:  python scripts/v2_backup.py [--out data/processed/db_backup_2026-10-05]

Writes one <table>.csv.gz per table plus manifest.json (row counts and the Alembic revision).
The folder is under data/processed/, which is git-ignored: never commit it (it holds demo-patient data).
Needs DATABASE_URL in the private .env. Read-only: it only runs SELECT / COPY ... TO STDOUT.
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import psycopg  # noqa: E402

from etl_common import connect  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/processed/db_backup_2026-10-05")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"tables": {}}
    with connect() as conn, conn.cursor() as cur:
        cur.execute("select version_num from alembic_version")
        manifest["alembic_revision"] = cur.fetchone()[0]
        cur.execute("select tablename from pg_tables where schemaname = 'public' order by 1")
        tables = [r[0] for r in cur.fetchall()]
        for t in tables:
            path = out / f"{t}.csv.gz"
            n = 0
            with gzip.open(path, "wb") as f, cur.copy(f'COPY (SELECT * FROM public."{t}") TO STDOUT WITH (FORMAT csv, HEADER true)') as cp:
                for chunk in cp:
                    f.write(bytes(chunk))
            cur.execute(f'select count(*) from public."{t}"')
            n = cur.fetchone()[0]
            manifest["tables"][t] = n
            print(f"{t:32s} {n:>9,d} rows")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nwrote {len(tables)} tables to {out}")


if __name__ == "__main__":
    main()
