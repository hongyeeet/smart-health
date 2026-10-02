#!/usr/bin/env python3
"""Verify what E1-4 loaded, independently of the loaders (E1-4 step 12). Prints a report; exit code 1 if any check fails.

Checks: row counts against the raw files (recomputed here), 100 random glucose rows against the raw CSVs, reference
data minimums and rules, simulated rows all flagged, no new tables (Alembic still 0007), row-level security on, the
GlucoBench fixture is not in the database, and the database size.
Usage: python scripts/verify_loaded.py            (also imported by services/api/tests/db/test_loaded_data.py)
"""
import json
import random
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etl_common import DEMO_DIR, PROCESSED, RAW, count, connect, demo_end_date, local_to_utc, mgdl_to_mmol, shift_days, uid  # noqa: E402

SRC = PROCESSED / "cgmacros" / "CGMacros"
DIABETIC = [3, 5, 12, 14, 28, 30, 35, 36, 38, 39, 42, 46, 47, 49]
BIG = ["003", "004", "009", "010", "011"]
FITBIT = [2026352035, 2347167796, 4558609924, 5577150313, 6962181067]
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    return ok


def feed_rows():
    p = DEMO_DIR / "replay_feed.jsonl"
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def cgmacros_expected(subj):
    d = pd.read_csv(SRC / f"CGMacros-{subj:03d}" / f"CGMacros-{subj:03d}.csv", parse_dates=["Timestamp"])
    libre = int(d["Libre GL"].notna().sum())
    dexcom = int(d["Dexcom GL"].notna().sum()) if subj == 46 else 0
    hr = int(((d["HR"].notna()) & (True if subj == 46 else (d["Timestamp"].dt.minute % 5 == 0))).sum())
    meals = int(d["Meal Type"].notna().sum())
    return {"glucose": libre + dexcom, "hr": hr, "meals": meals, "last_day": d["Timestamp"].max().date()}


def run(conn):
    end = demo_end_date()
    feed = feed_rows()
    # ---- CGMacros counts
    for subj in DIABETIC:
        exp = cgmacros_expected(subj)
        u = uid("user", f"cgmacros-{subj:03d}")
        held_g = sum(1 for r in feed if r["table"] == "glucose_readings") if subj == 46 else 0
        got_g = count(conn, "glucose_readings", "user_id = %s and external_id like 'cgmacros:%%:libre:%%' or user_id = %s and external_id like 'cgmacros:%%:dexcom:%%'", (u, u))
        check(f"CGMacros {subj:03d} glucose rows = source", got_g + held_g == exp["glucose"], f"db {got_g:,} + replay feed {held_g} vs source {exp['glucose']:,}")
        got_hr = count(conn, "health_samples", "user_id = %s and metric = 'heart_rate'", (u,))
        check(f"CGMacros {subj:03d} heart-rate rows = source rule", got_hr == exp["hr"], f"db {got_hr:,} vs {exp['hr']:,}")
        got_m = count(conn, "meals", "user_id = %s and description like 'CGMacros dataset meal%%'", (u,))
        check(f"CGMacros {subj:03d} meals = source", got_m == exp["meals"], f"db {got_m} vs {exp['meals']}")
    # ---- BIG IDEAs and Fitbit counts
    for pid in BIG:
        dx = pd.read_csv(RAW / "big-ideas" / pid / f"Dexcom_{pid}.csv", low_memory=False)
        n = int(pd.to_numeric(dx.loc[dx["Event Type"] == "EGV", "Glucose Value (mg/dL)"], errors="coerce").notna().sum())
        got = count(conn, "glucose_readings", "user_id = %s", (uid("user", f"bigideas-{pid}"),))
        check(f"BIG IDEAs {pid} glucose rows = source", got == n, f"db {got:,} vs {n:,}")
    sleep = pd.read_csv(next((RAW / "fitbit" / "mturkfitbit_export_4.12.16-5.12.16").glob("Fitabase*")) / "minuteSleep_merged.csv")
    for pid in FITBIT:
        n = int(sleep.loc[sleep["Id"] == pid, "logId"].nunique())
        got = count(conn, "sleep_sessions", "user_id = %s", (uid("user", f"fitbit-{pid}"),))
        check(f"Fitbit {pid} sleep sessions = source", got == n, f"db {got} vs {n}")
    # ---- 100 random glucose rows against the raw files
    rows = conn.execute("""select external_id, measured_at, value_mmol::float from glucose_readings
                           where external_id like 'cgmacros:%%:libre:%%' or external_id like 'cgmacros:%%:dexcom:%%' or external_id like 'bigideas:%%:dexcom:%%'
                           order by random() limit 100""").fetchall()
    cache, bad = {}, []
    for ext, at, val in rows:
        kind, pid, dev, ts = ext.split(":", 3)
        if kind == "cgmacros":
            f = SRC / f"CGMacros-{int(pid):03d}" / f"CGMacros-{int(pid):03d}.csv"
            if f not in cache:
                cache[f] = pd.read_csv(f, parse_dates=["Timestamp"]).set_index("Timestamp")
            d = cache[f]
            raw = d.loc[pd.Timestamp(ts), "Libre GL" if dev == "libre" else "Dexcom GL"]
            last = d.index.max().date()
        else:
            f = RAW / "big-ideas" / pid / f"Dexcom_{pid}.csv"
            if f not in cache:
                x = pd.read_csv(f, low_memory=False)
                x = x[x["Event Type"] == "EGV"]
                x.index = pd.to_datetime(x["Timestamp (YYYY-MM-DDThh:mm:ss)"])
                cache[f] = x
            d = cache[f]
            raw = float(d.loc[pd.Timestamp(ts), "Glucose Value (mg/dL)"])
            last = d.index.max().date()
        delta = timedelta(days=shift_days(last, end))
        expect_at = local_to_utc((pd.Timestamp(ts) + delta).to_pydatetime())
        if abs(val - mgdl_to_mmol(raw)) > 1e-9 or at != expect_at:
            bad.append(ext)
    check("100 random glucose rows match the raw files (value and shifted UTC time)", len(rows) == 100 and not bad, f"{len(rows)} checked, {len(bad)} differ")
    # ---- reference data
    n = lambda t, w="true": count(conn, t, w)  # noqa: E731
    check("drug_reference has 101 drugs incl. clarithromycin", n("drug_reference") == 101 and n("drug_reference", "generic_name = 'clarithromycin'") == 1, str(n("drug_reference")))
    check("drug_aliases and drug_side_effects loaded", n("drug_aliases") > 300 and n("drug_side_effects") > 300, f"{n('drug_aliases')} aliases, {n('drug_side_effects')} side effects")
    check("no alias or side effect is sourced from a substitute column", n("drug_aliases", "source not in ('250k Medicines','openFDA drug labels') and source not like 'NHANES%%'") == 0)
    check("interaction_rules loaded from openFDA, all severity unknown and a<b", n("interaction_rules") > 100 and n("interaction_rules", "severity <> 'unknown' or source <> 'openFDA drug labels' or drug_a_id >= drug_b_id") == 0, f"{n('interaction_rules')} pairs")
    a, b = sorted([uid("drug", "atorvastatin"), uid("drug", "clarithromycin")], key=str)
    check("demo pair atorvastatin + clarithromycin is an interaction rule", count(conn, "interaction_rules", "drug_a_id = %s and drug_b_id = %s", (a, b)) == 1)
    check("searching 'metformin' returns aliases", count(conn, "drug_aliases a join drug_reference d on d.id = a.drug_reference_id", "d.generic_name = 'metformin'") >= 5)
    total, ok = n("foods"), n("foods", "sodium_mg is not null or 'sodium_unknown' = any(flags)")
    check("foods: at least 90% have sodium or are flagged unknown", total > 0 and ok / total >= 0.9, f"{ok}/{total}")
    check("routing_rules has the 4 relevant rows", n("routing_rules") == 4, str(n("routing_rules")))
    check("preventive_items has 6 placeholders, labelled", n("preventive_items") == 6 and n("preventive_items", "source like '%%clinical review pending%%'") == 6)
    check("data_sources loaded", n("data_sources") >= 15, str(n("data_sources")))
    check("population_priors loaded and percentiles are ordered", n("population_priors") > 500 and n("population_priors", "not (p10 <= p25 and p25 <= p50 and p50 <= p75 and p75 <= p90)") == 0, f"{n('population_priors')} rows")
    # ---- demo patient and flags
    U = uid("user", "cgmacros-046")
    check("demo patient: Mr Tan, male, HbA1c 7.4, open sensor sprint", conn.execute("select count(*) from patient_profiles p join cgm_sprints s on s.user_id = p.user_id where p.user_id = %s and p.display_name = 'Mr Tan' and p.sex = 'male' and p.last_hba1c_pct = 7.4 and s.ended_at is null", (U,)).fetchone()[0] == 1)
    check("demo patient has 5 medicines, 2 not recognised", count(conn, "patient_medications", "user_id = %s", (U,)) == 5 and count(conn, "patient_medications", "user_id = %s and drug_reference_id is null", (U,)) == 2)
    unflagged = conn.execute("""select (select count(*) from glucose_readings where user_id = %(u)s and external_id is not null and external_id not like 'cgmacros:%%' and external_id not like 'sim:%%')
                                + (select count(*) from health_samples where user_id = %(u)s and external_id not like 'cgmacros:%%' and external_id not like 'sim:%%')
                                + (select count(*) from sleep_sessions where user_id = %(u)s and external_id not like 'sim:%%')
                                + (select count(*) from workouts where user_id = %(u)s and external_id not like 'sim:%%')
                                + (select count(*) from blood_pressure_readings where user_id = %(u)s and external_id not like 'sim:%%')""", {"u": U}).fetchone()[0]
    check("every demo-patient row with a source is either dataset (cgmacros:) or simulated (sim:)", unflagged == 0, f"{unflagged} unflagged")
    check("all loaded users are demo users", n("users", "is_demo = false") == 0)
    check("DISCLOSURE.md exists", (DEMO_DIR / "DISCLOSURE.md").exists())
    check("replay feed exists", len(feed) > 0, f"{len(feed)} readings")
    # ---- structure and size
    check("no new table: Alembic is still at 0007", conn.execute("select version_num from alembic_version").fetchone()[0] == "0007")
    check("row-level security is on for every table", conn.execute("select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity").fetchone()[0] == 0)
    check("GlucoBench is not loaded (fixture only)", n("glucose_readings", "external_id like 'glucobench%%'") == 0 and (Path(__file__).resolve().parent.parent / "services/api/tests/fixtures/glucobench_sample.csv").exists())
    mb = conn.execute("select pg_database_size(current_database()) / 1048576").fetchone()[0]
    check("database size under 300 MB (free plan limit 500 MB)", mb < 300, f"{mb} MB")


def main():
    with connect() as conn:
        run(conn)
        tables = [r[0] for r in conn.execute("select tablename from pg_tables where schemaname = 'public' and tablename <> 'alembic_version' order by 1").fetchall()]
        counts = {t: count(conn, t) for t in tables}
    failed = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    print("\nrows per table (non-empty):", ", ".join(f"{t} {n:,}" for t, n in counts.items() if n))
    print("empty tables:", ", ".join(t for t, n in counts.items() if not n) or "none")
    print(f"\n{len(results) - len(failed)} of {len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
