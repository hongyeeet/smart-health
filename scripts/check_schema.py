#!/usr/bin/env python3
"""Compare the tables in the database with the layer map in docs/specs/schema.md (section 0b).

Usage:
  python scripts/check_schema.py                          Bronze, Silver and Reference (E1-1, E1-2)
  python scripts/check_schema.py --layers all             every layer (after E1-3 adds Gold and Operations)

Exit code 0 only if the checked layers match the database exactly (no missing table, no extra table)
and row-level security is on for every table. Prints no secrets.
"""
import argparse
import os
import re
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LAYERS = ["bronze", "silver", "reference", "gold", "operations"]
DEFAULT = ["bronze", "silver", "reference"]
TOOL_TABLES = {"alembic_version"}  # the migration tool's own table: not part of the layer map


def layer_map():
    text = (ROOT / "docs" / "specs" / "schema.md").read_text(encoding="utf-8")
    section = text.split("## 0b. Layer map", 1)[1].split("\n---", 1)[0]
    out = {}
    for line in section.splitlines():
        m = re.match(r"\|\s*\*\*(\w+)\*\*[^|]*\|(.+)\|\s*$", line)
        if not m:
            continue
        layer = m.group(1).lower()
        cell = m.group(2)
        # views are listed after a "; views" marker and are not tables
        cell = cell.split("views", 1)[0]
        out[layer] = set(re.findall(r"`([a-z_]+)`", cell))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", default="default", help="'default' (bronze,silver,reference), 'all', or a comma list")
    a = ap.parse_args()
    layers = DEFAULT if a.layers == "default" else LAYERS if a.layers == "all" else [x.strip() for x in a.layers.split(",")]
    lm = layer_map()
    load_env()
    with psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=15) as c, c.cursor() as cur:
        cur.execute("select c.relname, c.relrowsecurity from pg_class c join pg_namespace n on n.oid = c.relnamespace "
                    "where n.nspname = 'public' and c.relkind = 'r'")
        db = {r[0]: r[1] for r in cur.fetchall()}
    db_tables = set(db) - TOOL_TABLES
    expected, bad = set(), 0
    for layer in layers:
        names = lm.get(layer, set())
        expected |= names
        have = names & db_tables
        missing = sorted(names - db_tables)
        print(f"{'OK  ' if not missing else 'FAIL'} {layer:<10} {len(have)} of {len(names)} tables exist" + (f"; missing: {', '.join(missing)}" if missing else ""))
        bad += len(missing)
    extra = sorted(db_tables - expected - set().union(*[lm.get(l, set()) for l in LAYERS if l not in layers]))
    print(f"{'OK  ' if not extra else 'FAIL'} no tables outside the layer map" + (f": {', '.join(extra)}" if extra else ""))
    no_rls = sorted(t for t in db if not db[t])
    print(f"{'OK  ' if not no_rls else 'FAIL'} row-level security is on for every table" + (f" (off: {', '.join(no_rls)})" if no_rls else ""))
    bad += len(extra) + len(no_rls)
    print(f"\n{len(db_tables)} tables in the database, {len(expected)} expected for layers: {', '.join(layers)}")
    print("MATCH" if not bad else "MISMATCH")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
