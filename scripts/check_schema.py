#!/usr/bin/env python3
"""Compare the tables in the database with the layer map in docs/specs/schema.md (section 0b).

Usage:
  python scripts/check_schema.py                          every layer (after E1-3)
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
DEFAULT = LAYERS  # every layer: E1-3 added Gold and Operations
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


def layer_views():
    """View names are listed after the word 'views' in the Gold row of the layer map."""
    text = (ROOT / "docs" / "specs" / "schema.md").read_text(encoding="utf-8")
    section = text.split("## 0b. Layer map", 1)[1].split("\n---", 1)[0]
    for line in section.splitlines():
        if line.startswith("| **Gold**"):
            return set(re.findall(r"`([a-z_]+)`", line.split("views", 1)[1]))
    return set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", default="default", help="'default' (every layer), 'all', or a comma list")
    a = ap.parse_args()
    layers = DEFAULT if a.layers == "default" else LAYERS if a.layers == "all" else [x.strip() for x in a.layers.split(",")]
    lm = layer_map()
    load_env()
    with psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=15) as c, c.cursor() as cur:
        cur.execute("select c.relname, c.relrowsecurity from pg_class c join pg_namespace n on n.oid = c.relnamespace "
                    "where n.nspname = 'public' and c.relkind = 'r'")
        db = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute("select c.relname, coalesce('security_invoker=on' = any (c.reloptions), false) from pg_class c "
                    "join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'public' and c.relkind = 'v'")
        views = {r[0]: r[1] for r in cur.fetchall()}
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
    if "gold" in layers:
        want = sorted(layer_views())
        miss_v = [v for v in want if v not in views]
        loose = sorted(v for v in views if not views[v])
        print(f"{'OK  ' if not miss_v else 'FAIL'} views {len(want) - len(miss_v)} of {len(want)} exist" + (f"; missing: {', '.join(miss_v)}" if miss_v else ""))
        print(f"{'OK  ' if not loose else 'FAIL'} every view runs with the caller's row-level security (security_invoker)" + (f" (not: {', '.join(loose)})" if loose else ""))
        bad += len(miss_v) + len(loose)
    print(f"\n{len(db_tables)} tables in the database, {len(expected)} expected for layers: {', '.join(layers)}")
    print("MATCH" if not bad else "MISMATCH")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
