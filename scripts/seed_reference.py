#!/usr/bin/env python3
"""Seed the Reference tables (E1-4 steps 3 to 5). Safe to run twice.

  drug_reference, knowledge_documents  the 101 drugs (data/processed/nhanes_top_drugs.csv) and their openFDA label
  drug_aliases                         product names from 250k Medicines whose name holds exactly one of the drugs and
                                       is not a combination ("+"), plus openFDA brand names and the generic name
  drug_side_effects                    effects listed for at least 30% of a drug's single-ingredient 250k rows
  interaction_rules                    a pair when one drug's openFDA label text (drug_interactions) names the other.
                                       severity = unknown; reference data, unreviewed; never "validated"
  foods                                Open Food Facts products sold in Singapore or Malaysia (sodium missing is flagged)
  routing_rules                        Doctor Specialty: the 4 conditions relevant to Type 2 care (disease to specialty)
  preventive_items                     6 placeholder check-up intervals (owner-approved; clinical review pending)

The five substitute* columns of 250k Medicines are never read.  Usage: python scripts/seed_reference.py
"""
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etl_common import PROCESSED, RAW, bulk_insert, connect, count, report, uid  # noqa: E402

RETRIEVED = date(2026, 10, 2)
PLACEHOLDER = "Equinox team placeholder (clinical review pending)"
SIDE_EFFECT_SHARE = 0.30
NAME_COL_PREFIX_SIDE = "sideEffect"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def safe(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def clean(v):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else v


# ------------------------------------------------------------------ drugs
def load_drug_list():
    return list(csv.DictReader(open(PROCESSED / "nhanes_top_drugs.csv", encoding="utf-8")))


def load_labels(drugs):
    out = {}
    for d in drugs:
        p = RAW / "openfda" / f"{safe(d['generic_name'])}.json"
        out[d["generic_name"]] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"_status": "not_fetched"}
    return out


def seed_drugs(conn, drugs, labels):
    docs, refs = [], []
    for d in drugs:
        g, lab = d["generic_name"], labels[d["generic_name"]]
        doc_id = None
        if lab.get("_status") == "found":
            doc_id = uid("knowledge_document", g)
            docs.append((doc_id, "drug", f"{g.title()} drug label (openFDA)", "U.S. Food and Drug Administration (openFDA)", lab["_url"],
                         "CC0 1.0 Universal (public domain)", "en", (lab.get("effective_time") or ""), RETRIEVED, True))
        brands = sorted({b.strip() for b in lab.get("openfda", {}).get("brand_name", []) if b.strip()}) if lab.get("_status") == "found" else []
        refs.append((uid("drug", g), g, brands, "prescription", doc_id))
    n_doc = bulk_insert(conn, "knowledge_documents", ["id", "kind", "title", "source_org", "source_url", "licence", "locale", "version", "retrieved_on", "active"], docs)
    n_ref = bulk_insert(conn, "drug_reference", ["id", "generic_name", "brand_names", "kind", "knowledge_doc_id"], refs)
    report("drug_reference", inserted=n_ref, total=count(conn, "drug_reference"))
    report("knowledge_documents", inserted=n_doc, total=count(conn, "knowledge_documents"))


def seed_aliases_and_side_effects(conn, drugs, labels):
    generics = [d["generic_name"] for d in drugs]
    pattern = re.compile(r"\b(" + "|".join(re.escape(g) for g in sorted(generics, key=len, reverse=True)) + r")\b")
    cols = ["name"] + [f"{NAME_COL_PREFIX_SIDE}{i}" for i in range(42)]   # substitute* columns are deliberately not read
    df = pd.read_csv(RAW / "250k-medicines-usage-side-effects-and-substitutes" / "medicine_dataset.csv", usecols=cols, low_memory=False)
    names = df["name"].fillna("").str.lower().str.strip()
    single = defaultdict(list)     # generic -> row indexes of single-ingredient products
    for idx, nm in enumerate(names):
        if "+" in nm:
            continue
        hit = set(pattern.findall(nm))
        if len(hit) == 1:
            single[hit.pop()].append(idx)
    alias_rows, effect_rows = [], []
    side_cols = [f"{NAME_COL_PREFIX_SIDE}{i}" for i in range(42)]
    for d in drugs:
        g = d["generic_name"]
        ref = uid("drug", g)
        found = labels[g].get("_status") == "found"
        gsrc = "openFDA drug labels" if found else "NHANES " + d["cycles"].split(",")[-1]
        alias_rows.append((uid("alias", g, g), ref, g, None, "generic", gsrc))
        for b in labels[g].get("openfda", {}).get("brand_name", []) if found else []:
            if b.strip():
                alias_rows.append((uid("alias", g, b.lower()), ref, b.strip(), None, "brand", "openFDA drug labels"))
        rows = single.get(g, [])
        for idx in rows:
            alias_rows.append((uid("alias", g, names[idx]), ref, names[idx], None, "brand", "250k Medicines"))
        if rows:
            counts = Counter()
            for idx in rows:
                for v in set(df.loc[idx, side_cols].dropna().astype(str).str.strip().str.lower()):
                    if v:
                        counts[v] += 1
            need = max(1, math.ceil(SIDE_EFFECT_SHARE * len(rows)))
            for eff, c in counts.items():
                if c >= need:
                    effect_rows.append((uid("effect", g, slug(eff)), ref, slug(eff), "250k Medicines"))
    # duplicates inside the batch (same drug and alias in different case) are dropped by the unique index
    seen, uniq = set(), []
    for r in alias_rows:
        key = (r[1], r[2].lower())
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    n_a = bulk_insert(conn, "drug_aliases", ["id", "drug_reference_id", "alias", "locale", "kind", "source"], uniq)
    n_e = bulk_insert(conn, "drug_side_effects", ["id", "drug_reference_id", "effect_key", "source"], effect_rows)
    drugs_with_alias = len({r[1] for r in uniq if r[5] == "250k Medicines"})
    report("drug_aliases", inserted=n_a, total=count(conn, "drug_aliases"), drugs_with_250k_names=drugs_with_alias)
    report("drug_side_effects", inserted=n_e, total=count(conn, "drug_side_effects"))


def seed_interactions(conn, drugs, labels):
    generics = [d["generic_name"] for d in drugs]
    text = {g: " ".join(labels[g].get("drug_interactions", [])).lower() for g in generics if labels[g].get("_status") == "found"}
    rows, pairs = [], {}
    for a, ta in text.items():
        for b in generics:
            if a == b or not re.search(r"\b" + re.escape(b) + r"\b", ta):
                continue
            ida, idb = uid("drug", a), uid("drug", b)
            first, second = (ida, idb) if str(ida) < str(idb) else (idb, ida)
            if (first, second) not in pairs:
                pairs[(first, second)] = labels[a]["_url"]
    for (x, y), url in pairs.items():
        rows.append((uid("interaction", x, y), x, y, "unknown", "clash.possible_interaction", "openFDA drug labels", url))
    n = bulk_insert(conn, "interaction_rules", ["id", "drug_a_id", "drug_b_id", "severity", "patient_text_key", "source", "source_url"], rows)
    report("interaction_rules", inserted=n, total=count(conn, "interaction_rules"))
    return {(a, b) for (a, b) in pairs}


# ------------------------------------------------------------------ foods, routing, check-ups
def seed_foods(conn):
    cols = ["code", "product_name", "countries_en", "categories_en", "energy_100g", "carbohydrates_100g", "sugars_100g",
            "fiber_100g", "proteins_100g", "fat_100g", "salt_100g", "sodium_100g"]
    df = pd.read_csv(RAW / "world-food-facts" / "en.openfoodfacts.org.products.tsv", sep="\t", usecols=cols, low_memory=False, dtype={"code": str})
    c = df["countries_en"].fillna("")
    df = df[c.str.contains("Singapore|Malaysia", case=False) & df["product_name"].notna()].drop_duplicates("code")
    rows = []
    for r in df.itertuples():
        name = str(r.product_name).strip()
        if not name:
            continue
        sodium_g = clean(r.sodium_100g)
        if sodium_g is None and clean(r.salt_100g) is not None:
            sodium_g = float(r.salt_100g) / 2.5            # salt = 2.5 x sodium
        sodium_mg = None if sodium_g is None else round(float(sodium_g) * 1000, 1)
        kcal = None if clean(r.energy_100g) is None else round(float(r.energy_100g) / 4.184, 1)   # Open Food Facts stores kJ
        flags = ["sodium_unknown"] if sodium_mg is None else []
        rows.append((uid("food", r.code), name, "packaged", [], "per 100 g", 100, kcal, clean(r.carbohydrates_100g), clean(r.sugars_100g),
                     clean(r.fiber_100g), clean(r.proteins_100g), clean(r.fat_100g), sodium_mg, "unknown", flags, "Open Food Facts"))
    n = bulk_insert(conn, "foods", ["id", "name", "category", "aliases", "serving_desc", "serving_g", "kcal", "carbs_g", "sugar_g", "fibre_g",
                                    "protein_g", "fat_g", "sodium_mg", "gi", "flags", "source"], rows)
    with_sodium = count(conn, "foods", "sodium_mg is not null")
    report("foods", inserted=n, total=count(conn, "foods"), with_sodium=with_sodium, flagged_sodium_unknown=count(conn, "foods", "'sodium_unknown' = any(flags)"))


def seed_routing(conn):
    dv = pd.read_csv(RAW / "doctor-specialist-recommendation-system" / "Doctor_Versus_Disease.csv", header=None, encoding="latin-1")
    wanted = {"diabetes": "diabetes", "hypoglycemia": "hypoglycaemia", "hypertension": "high_blood_pressure", "heart attack": "heart_attack"}
    rows = []
    for disease, spec in zip(dv[0].astype(str), dv[1].astype(str)):
        key = wanted.get(disease.strip().lower())
        if key:
            sk = slug(spec)
            rows.append((uid("routing", key), key, sk, f"routing.{sk}", "Doctor Specialty"))
    n = bulk_insert(conn, "routing_rules", ["id", "complication_key", "specialty_key", "patient_text_key", "source"], rows)
    report("routing_rules", inserted=n, total=count(conn, "routing_rules"))


def seed_preventive(conn):
    items = [("eye_screening", 12), ("foot_screening", 12), ("kidney_test", 12), ("hba1c_test", 6), ("vaccination", 12), ("diabetes_review", 6)]
    rows = [(uid("preventive", k), k, m, f"preventive.{k}", PLACEHOLDER) for k, m in items]
    n = bulk_insert(conn, "preventive_items", ["id", "kind", "interval_months", "label_key", "source"], rows)
    report("preventive_items", inserted=n, total=count(conn, "preventive_items"))


def main():
    drugs = load_drug_list()
    labels = load_labels(drugs)
    with connect() as conn:
        seed_drugs(conn, drugs, labels)
        seed_aliases_and_side_effects(conn, drugs, labels)
        pairs = seed_interactions(conn, drugs, labels)
        seed_foods(conn)
        seed_routing(conn)
        seed_preventive(conn)
        conn.commit()
        for a, b in (("atorvastatin", "clarithromycin"), ("amlodipine", "atorvastatin"), ("amlodipine", "metformin"), ("atorvastatin", "metformin")):
            x, y = sorted([uid("drug", a), uid("drug", b)], key=str)
            print(f"  demo pair {a} + {b}: {'HIT' if (x, y) in pairs else 'no pair found in the label text'}")


if __name__ == "__main__":
    main()
