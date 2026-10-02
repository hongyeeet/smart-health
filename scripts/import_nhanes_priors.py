#!/usr/bin/env python3
"""NHANES to population_priors, and the top-100 drug list (E1-4 step 2).

1. population_priors: typical values (10th/25th/50th/75th/90th percentile) for adults aged 40-69, by metric, sex,
   age band and diabetes status (told by a doctor: DIQ010 = 1 yes, 2 no), one set per NHANES cycle.
   Participant percentiles, NOT survey-weighted (documented limit). Groups with fewer than 20 people are skipped.
   Used only to give a new user a starting baseline. Never shown to a person as a target.
2. data/processed/nhanes_top_drugs.csv: the 100 most-taken single-ingredient generic drugs among people with
   diabetes (cycles 2011-2018; the 2021-2023 prescription file publishes no drug names). Insulin is left out
   (out of scope), and so are vitamins and supplements (the demo shows supplements as "not checked").
   Clarithromycin is added as the demo drug (decision D-033, owner-approved).

Safe to run twice.  Usage: python scripts/import_nhanes_priors.py
"""
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etl_common import PROCESSED, RAW, bulk_insert, connect, count, report  # noqa: E402

CYCLES = {"2011-2012": "G", "2013-2014": "H", "2015-2016": "I", "2017-2018": "J", "2021-2023": "L"}
DRUG_CYCLES = ["2011-2012", "2013-2014", "2015-2016", "2017-2018"]
AGE_BANDS = [(40, 49, "40-49"), (50, 59, "50-59"), (60, 69, "60-69")]
MIN_N = 20

# metric name -> (file prefix, candidate columns (first found is used), multiplier to the stored unit)
METRICS = {
    "hba1c_pct": ("GHB", ["LBXGH"], 1.0),
    "fasting_glucose_mmol_l": ("GLU", ["LBXGLU"], 1 / 18.0),
    "total_cholesterol_mmol_l": ("TCHOL", ["LBXTC"], 1 / 38.67),
    "hdl_cholesterol_mmol_l": ("HDL", ["LBDHDD", "LBDHDD"], 1 / 38.67),
    "ldl_cholesterol_mmol_l": ("TRIGLY", ["LBDLDL"], 1 / 38.67),
    "triglycerides_mmol_l": ("TRIGLY", ["LBXTR"], 1 / 88.57),
    "creatinine_umol_l": ("BIOPRO", ["LBXSCR"], 88.4),
    "uacr_mg_g": ("ALB_CR", ["URDACT"], 1.0),
    "bmi_kg_m2": ("BMX", ["BMXBMI"], 1.0),
    "waist_cm": ("BMX", ["BMXWAIST"], 1.0),
}
EXCLUDE_WORDS = ("insulin", "omega", "vitamin", "cholecalciferol", "ergocalciferol", "folic", "calcium", "multivit",
                 "fish oil", "iron", "magnesium", "zinc", "niacin")
DEMO_DRUG = ("clarithromycin", "demo drug (decision D-033, owner-approved)")


def read(cycle, prefix):
    suffix = CYCLES[cycle]
    for name in (f"{prefix}_{suffix}.xpt", f"{prefix}_{suffix}.XPT"):
        p = RAW / "nhanes" / cycle / name
        if p.exists():
            return pd.read_sas(p, format="xport")
    return None


def bp_frame(cycle):
    """Mean systolic and diastolic over the available readings: BPXO (oscillometric) when the cycle has it, else BPX."""
    for prefix, sy, di in (("BPXO", "BPXOSY", "BPXODI"), ("BPX", "BPXSY", "BPXDI")):
        df = read(cycle, prefix)
        if df is not None:
            scols = [c for c in df.columns if c.startswith(sy)]
            dcols = [c for c in df.columns if c.startswith(di)]
            if scols and dcols:
                return pd.DataFrame({"SEQN": df["SEQN"], "systolic_bp_mmhg": df[scols].mean(axis=1), "diastolic_bp_mmhg": df[dcols].mean(axis=1)})
    return None


def priors_for_cycle(cycle):
    demo, diq = read(cycle, "DEMO"), read(cycle, "DIQ")
    base = demo[["SEQN", "RIAGENDR", "RIDAGEYR"]].merge(diq[["SEQN", "DIQ010"]], on="SEQN")
    base = base[base["DIQ010"].isin([1.0, 2.0]) & base["RIAGENDR"].isin([1.0, 2.0])]
    base = base[(base["RIDAGEYR"] >= 40) & (base["RIDAGEYR"] < 70)].copy()
    base["sex"] = base["RIAGENDR"].map({1.0: "male", 2.0: "female"})
    base["has_diabetes"] = base["DIQ010"] == 1.0
    base["age_band"] = pd.cut(base["RIDAGEYR"], [40, 50, 60, 70], right=False, labels=[b[2] for b in AGE_BANDS]).astype(str)
    series = {}
    for metric, (prefix, cols, mult) in METRICS.items():
        df = read(cycle, prefix)
        col = next((c for c in cols if df is not None and c in df.columns), None)
        if col:
            series[metric] = df[["SEQN", col]].rename(columns={col: metric}).assign(**{metric: lambda d, m=metric: d[m] * mult})
    bp = bp_frame(cycle)
    if bp is not None:
        series["systolic_bp_mmhg"], series["diastolic_bp_mmhg"] = bp[["SEQN", "systolic_bp_mmhg"]], bp[["SEQN", "diastolic_bp_mmhg"]]
    rows, coverage = [], []
    for metric, df in series.items():
        m = base.merge(df, on="SEQN").dropna(subset=[metric])
        found = 0
        for (sex, band, dm), g in m.groupby(["sex", "age_band", "has_diabetes"]):
            if len(g) < MIN_N:
                continue
            p = np.percentile(g[metric], [10, 25, 50, 75, 90])
            rows.append((metric, sex, band, bool(dm), *[round(float(x), 2) for x in p], int(len(g)), f"NHANES {cycle}"))
            found += 1
        coverage.append((metric, found))
    return rows, coverage


def top_drugs():
    people = defaultdict(set)
    cycles = defaultdict(set)
    for cycle in DRUG_CYCLES:
        rx, diq = read(cycle, "RXQ_RX"), read(cycle, "DIQ")
        dm = set(diq.loc[diq["DIQ010"] == 1.0, "SEQN"])
        r = rx[rx["SEQN"].isin(dm)]
        for seq, b in zip(r["SEQN"], r["RXDDRUG"]):
            g = (b.decode() if isinstance(b, bytes) else str(b)).strip().lower()
            if not g or g == "nan" or g.startswith("9999") or ";" in g or "(" in g or any(w in g for w in EXCLUDE_WORDS):
                continue
            people[g].add((cycle, int(seq)))
            cycles[g].add(cycle)
    ranked = sorted(people.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:100]
    out = [(i + 1, g, len(v), ",".join(sorted(cycles[g])), "top 100 among people with diabetes (NHANES 2011-2018)") for i, (g, v) in enumerate(ranked)]
    if DEMO_DRUG[0] not in {o[1] for o in out}:
        out.append((len(out) + 1, DEMO_DRUG[0], len(people.get(DEMO_DRUG[0], ())), ",".join(sorted(cycles.get(DEMO_DRUG[0], []))), DEMO_DRUG[1]))
    return out


def main():
    all_rows = []
    for cycle in CYCLES:
        rows, coverage = priors_for_cycle(cycle)
        all_rows += rows
        print(f"  {cycle}: {len(rows)} groups; metrics with data: " + ", ".join(f"{m}({n})" for m, n in coverage if n))
    with connect() as conn:
        n = bulk_insert(conn, "population_priors", ["metric", "sex", "age_band", "has_diabetes", "p10", "p25", "p50", "p75", "p90", "n", "source"], all_rows)
        conn.commit()
        report("population_priors", inserted=n, total=count(conn, "population_priors"))
    drugs = top_drugs()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(drugs, columns=["rank", "generic_name", "diabetic_people", "cycles", "note"]).to_csv(PROCESSED / "nhanes_top_drugs.csv", index=False)
    print(f"drug list: {len(drugs)} drugs written to data/processed/nhanes_top_drugs.csv (top 5: {', '.join(d[1] + ' ' + str(d[2]) for d in drugs[:5])})")


if __name__ == "__main__":
    main()
