#!/usr/bin/env python3
"""Seed data_sources: where every dataset and reference list came from, with licence (E1-4 step 1).

Referred to BY NAME from foods.source, interaction_rules.source, drug_aliases.source and population_priors.source,
so the names below are the exact strings the other loaders use. Safe to run twice.
Usage: python scripts/seed_data_sources.py
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etl_common import bulk_insert, connect, count, report, uid  # noqa: E402

# (name, kind, licence, url, retrieved_on, used_for, notes)
SOURCES = [
    ("NHANES 2011-2012", "dataset", "US public domain (CDC data user agreement)", "https://wwwn.cdc.gov/nchs/nhanes/", date(2026, 10, 2), "Typical values by age, sex and diabetes status; drug list", "Owner-approved addition (D-037); accelerometer files not used"),
    ("NHANES 2013-2014", "dataset", "US public domain (CDC data user agreement)", "https://wwwn.cdc.gov/nchs/nhanes/", date(2026, 10, 2), "Typical values by age, sex and diabetes status; drug list", "Owner-approved addition (D-037)"),
    ("NHANES 2015-2016", "dataset", "US public domain (CDC data user agreement)", "https://wwwn.cdc.gov/nchs/nhanes/", date(2026, 10, 2), "Typical values by age, sex and diabetes status; drug list", "Owner-approved addition (D-037)"),
    ("NHANES 2017-2018", "dataset", "US public domain (CDC data user agreement)", "https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2017", date(2026, 10, 1), "Typical values by age, sex and diabetes status; drug list", "Manifest #1"),
    ("NHANES 2021-2023", "dataset", "US public domain (CDC data user agreement)", "https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2021", date(2026, 10, 1), "Typical values by age, sex and diabetes status; drug list", "Manifest #2"),
    ("CGMacros", "dataset", "CC BY-NC-SA 4.0", "https://physionet.org/content/cgmacros/", date(2026, 10, 1), "Demo patient and 13 other people: glucose, meals, heart rate, labs", "Manifest #5. Non-commercial, share-alike, attribution required"),
    ("BIG IDEAs Lab", "dataset", "Open Data Commons Attribution License v1.0", "https://physionet.org/content/big-ideas-glycemic-wearable/", date(2026, 10, 2), "Extra glucose, heart rate, stress signals (5 of 16 people)", "Manifest #4. None of these people has diabetes"),
    ("Fitbit (Kaggle)", "dataset", "CC0 1.0 Public Domain", "https://www.kaggle.com/datasets/arashnic/fitbit", date(2026, 10, 1), "Second watch format: heart rate, steps, sleep, weight", "Manifest #14. 2016 data"),
    ("250k Medicines", "dataset", "CC BY-SA 4.0", "https://www.kaggle.com/datasets/shudhanshusingh/250k-medicines-usage-side-effects-and-substitutes", date(2026, 10, 1), "Drug names (aliases) and side effects", "Manifest #20. Source is 'various'; not authoritative; substitute columns never loaded; has no interactions"),
    ("openFDA drug labels", "dataset", "CC0 1.0 Universal (public domain)", "https://api.fda.gov/drug/label.json", date(2026, 10, 2), "Drug generic and brand names; drug-to-drug interaction text", "Owner-approved addition (D-036). Label text is general information, not medical advice; unreviewed reference data"),
    ("Open Food Facts", "dataset", "Database Contents License (DbCL 1.0)", "https://www.kaggle.com/datasets/openfoodfacts/world-food-facts", date(2026, 10, 1), "Foods with nutrients (Singapore and Malaysia products)", "Manifest #17. Packaged foods only; most lack sodium"),
    ("Doctor Specialty", "dataset", "CC BY-SA 4.0", "https://www.kaggle.com/datasets/ebrahimelgazar/doctor-specialist-recommendation-system", date(2026, 10, 1), "Which kind of doctor for which condition (routing only)", "Manifest #37. Weak provenance; only Doctor_Versus_Disease.csv, disease-to-specialty pairs"),
    ("GlucoBench", "dataset", "Apache 2.0 (source not cited)", "https://www.kaggle.com/datasets/omenkj/glucobench-glucose-monitoring-and-lifestyle-data", date(2026, 10, 1), "Test fixture only; not loaded into the database", "Not in the manifest (allowed by the data policy). May be synthetic; never evidence"),
    ("Smart Health team placeholder (clinical review pending)", "own", "Team-written, not from any dataset", None, date(2026, 10, 2), "Check-up intervals and default targets", "Owner approved 2026-10-02 as placeholders; a clinician must review before real use"),
    ("Smart Health simulator (demo)", "own", "Team-written, not from any dataset", None, date(2026, 10, 2), "Simulated 60-day history for the demo patient", "Built from cited data only and disclosed in data/demo/DISCLOSURE.md"),
]


def main():
    with connect() as conn:
        rows = [(uid("data_source", s[0]), s[0], s[1], s[2], s[3], s[4], s[5], s[6]) for s in SOURCES]
        n = bulk_insert(conn, "data_sources", ["id", "name", "kind", "licence", "url", "retrieved_on", "used_for", "notes"], rows)
        conn.commit()
        report("data_sources", inserted=n, total=count(conn, "data_sources"))


if __name__ == "__main__":
    main()
