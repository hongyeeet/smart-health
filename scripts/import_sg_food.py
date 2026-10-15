#!/usr/bin/env python3
"""Load the Singapore food composition tables into `foods` (Reference layer), with 768-dimension embeddings.

Usage:  python scripts/import_sg_food.py            (safe to run again: upserts on (source, name); embeds only missing rows)

Input:  data/raw/sgfood/food_nutrition_sgfoodid_combined_202607.csv  (2,689 rows, a superset of the 1,163-row hawker file)
        The file is not committed (data/raw/ is ignored). Values are per serving; per-100 values are kept in `per100`.
Rules:  '-' means not available (null), 'Trace' means 0, never guess a missing value. Source grade comes from "Source of Data".
        Approved by the owner on 2026-10-06 as an exception to the cited-datasets policy; licence still to be confirmed.
"""
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etl_common import connect  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "raw" / "sgfood" / "food_nutrition_sgfoodid_combined_202607.csv"
SOURCE = "sgfoodid_2026_07"
GRADE = {"Lab Analysis": "lab_analysis", "Derived": "derived", "Borrowed": "borrowed", "NIP": "label"}
PER100 = ["Energy (kcal)", "Carbohydrate (g)", "Sugar (g)", "Dietary Fibre (g)", "Sodium (mg)", "Protein (g)", "Total Fat (g)", "Saturated Fat (g)"]


def num(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    if s in ("", "-"):
        return None
    if s.lower() == "trace":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return None


def serving_g(text):
    """'1 plate(s) = 363g' -> 363.0 ; '1 cup(s) = 450ml' -> 450.0 (ml kept as is, drinks are about 1 g per ml)."""
    m = re.search(r"=\s*([\d.]+)\s*(g|ml)", str(text))
    return float(m.group(1)) if m else None


def embed_all(texts):
    from google import genai
    from google.genai import types

    key = os.environ.get("GOOGLE_API_KEY", "")
    for k in ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION", "GOOGLE_APPLICATION_CREDENTIALS"):
        os.environ.pop(k, None)
    client = genai.Client(vertexai=True, api_key=key)
    out = []
    for i in range(0, len(texts), 100):
        r = client.models.embed_content(model="gemini-embedding-001", contents=texts[i:i + 100], config=types.EmbedContentConfig(output_dimensionality=768))
        out += [e.values for e in r.embeddings]
        print(f"  embedded {len(out)}/{len(texts)}", flush=True)
    return out


def main():
    df = pd.read_csv(CSV)
    print(f"read {len(df)} rows from {CSV.name}")
    conn = connect()
    # provenance
    conn.execute(
        """insert into data_sources (name, kind, licence, url, retrieved_on, used_for, notes)
           select %s, 'dataset', %s, %s, current_date, %s, %s
           where not exists (select 1 from data_sources where name = %s)""",
        (
            "Singapore food composition tables (Kaggle: adisongoh)",
            "CC0: Public Domain (as declared on Kaggle by the uploader)",
            "https://www.kaggle.com/datasets/adisongoh/singapore-hawker-food-nutritional-information",
            "Dish and item matching, healthier alternatives, high-salt flags (learning-loop LL4, LL5, LL9)",
            "Owner-approved exception to the cited-datasets policy, 2026-10-06. 2,689 rows, per serving. Raw file kept in data/raw/sgfood (not committed).",
            "Singapore food composition tables (Kaggle: adisongoh)",
        ),
    )
    rows = []
    for _, r in df.iterrows():
        per100 = {k: num(r[f"{k} - Per 100"]) for k in PER100 if f"{k} - Per 100" in df.columns}
        year = num(r["Last Updated"])
        rows.append(
            dict(
                name=str(r["Food Name"]).strip(),
                category=str(r["Category"]).strip(),
                subgroup=None if pd.isna(r["Food Subgroup"]) else str(r["Food Subgroup"]).strip(),
                serving_desc=str(r["Default Serving Size"]).strip(),
                serving_g=serving_g(r["Default Serving Size"]),
                kcal=num(r["Energy (kcal) - Per Serving"]),
                carbs_g=num(r["Carbohydrate (g) - Per Serving"]),
                sugar_g=num(r["Sugar (g) - Per Serving"]),
                fibre_g=num(r["Dietary Fibre (g) - Per Serving"]),
                protein_g=num(r["Protein (g) - Per Serving"]),
                fat_g=num(r["Total Fat (g) - Per Serving"]),
                sat_fat_g=num(r["Saturated Fat (g) - Per Serving"]),
                sodium_mg=num(r["Sodium (mg) - Per Serving"]),
                potassium_mg=num(r["Potassium (mg) - Per Serving"]),
                source_grade=GRADE.get(str(r["Source of Data"]).strip()),
                data_year=int(year) if year else None,
                per100=json.dumps(per100),
                desc=None if pd.isna(r["Description"]) else str(r["Description"]).strip(),
            )
        )
    sql = """
      insert into foods (name, category, subgroup, serving_desc, serving_g, kcal, carbs_g, sugar_g, fibre_g, protein_g, fat_g, sat_fat_g,
                         sodium_mg, potassium_mg, source, source_grade, data_year, per100, gi)
      values (%(name)s, %(category)s, %(subgroup)s, %(serving_desc)s, %(serving_g)s, %(kcal)s, %(carbs_g)s, %(sugar_g)s, %(fibre_g)s, %(protein_g)s,
              %(fat_g)s, %(sat_fat_g)s, %(sodium_mg)s, %(potassium_mg)s, %(source)s, %(source_grade)s, %(data_year)s, %(per100)s::jsonb, 'unknown')
      on conflict (source, name) do update set
        category=excluded.category, subgroup=excluded.subgroup, serving_desc=excluded.serving_desc, serving_g=excluded.serving_g,
        kcal=excluded.kcal, carbs_g=excluded.carbs_g, sugar_g=excluded.sugar_g, fibre_g=excluded.fibre_g, protein_g=excluded.protein_g,
        fat_g=excluded.fat_g, sat_fat_g=excluded.sat_fat_g, sodium_mg=excluded.sodium_mg, potassium_mg=excluded.potassium_mg,
        source_grade=excluded.source_grade, data_year=excluded.data_year, per100=excluded.per100"""
    with conn.cursor() as cur:
        cur.executemany(sql, [dict(r, source=SOURCE) for r in rows])
    conn.commit()
    print(f"upserted {len(rows)} foods")

    todo = conn.execute("select id, name, category, subgroup from foods where source=%s and embedding is null", (SOURCE,)).fetchall()
    by_name = {r["name"]: r for r in rows}
    if todo:
        texts = [f"{n}. {by_name[n]['desc'] or ''} {sg or ''} {cat or ''}".strip() for _, n, cat, sg in todo]
        vecs = embed_all(texts)
        with conn.cursor() as cur:
            cur.executemany("update foods set embedding = %s::vector where id = %s", [("[" + ",".join(f"{x:.6f}" for x in v) + "]", fid) for (fid, *_), v in zip(todo, vecs)])
        conn.commit()
    # mark the hawker subset (the 1,163-row hawker file is contained in the combined file)
    hawker = ROOT / "data" / "raw" / "sgfood" / "food_nutrition_sgfoodid_hawker_202607.csv"
    if hawker.exists():
        names = pd.read_csv(hawker)["Food Name"].astype(str).str.strip().tolist()
        conn.execute("update foods set flags = array(select distinct unnest(coalesce(flags, '{}') || array['hawker'])) where source=%s and name = any(%s)", (SOURCE, names))
        conn.commit()
    n = conn.execute("select count(*), count(embedding), count(sodium_mg) from foods where source=%s", (SOURCE,)).fetchone()
    print(f"done: {n[0]} rows, {n[1]} embedded, {n[2]} with sodium")


if __name__ == "__main__":
    main()
