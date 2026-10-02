#!/usr/bin/env python3
"""Write docs/data_dictionary.md from the live database (E1-2).

For every Bronze, Silver and Reference table: purpose, and for every column its type, whether it may be
empty, its unit and its source flag. Re-run after any migration:  python scripts/make_data_dictionary.py
Gold and Operations tables (E1-3) are added by extending LAYERS below.
"""
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_schema import layer_map  # noqa: E402
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LAYERS = ["bronze", "silver", "reference"]

PURPOSE = {
    "ingestion_events": "Log of every raw input kept exactly as received (photo, text, export, document). Never edited.",
    "users": "One row per person (the demo patient, for now). No sign-in screens.",
    "patient_profiles": "Who the patient is: age, sex, body size, diagnosis year, last HbA1c, doctor-set targets.",
    "conditions": "Other conditions the patient has (for example high blood pressure).",
    "allergies": "Allergies and reactions.",
    "family_history": "Conditions in the family.",
    "consents": "What the patient agreed to (data use, sharing a brief, and so on) and when.",
    "prescription_scans": "A photo of a label or box and what the AI read from it, until the user confirms.",
    "patient_medications": "Medicines, supplements and TCM the patient confirmed taking, with the schedule on the label.",
    "medication_ingredients": "Ingredients of a product (one row per ingredient), used by the clash check.",
    "dose_events": "One row per scheduled dose and what happened to it (taken, late, missed and why).",
    "refill_forecasts": "When a medicine is expected to run out.",
    "glucose_readings": "Every glucose value (glucometer or CGM) in mmol/L.",
    "cgm_sprints": "A 14-day sensor period.",
    "health_samples": "Watch and wearable readings: heart rate, steps, HRV, skin temperature and so on.",
    "sleep_sessions": "One row per night's sleep.",
    "meals": "A meal that was logged (photo or text).",
    "meal_items": "The foods in a meal, with nutrients, who estimated them and how sure.",
    "meal_analyses": "The AI's raw answer for a meal photo or text, with model and prompt version. Re-runs add rows.",
    "workouts": "Logged or imported exercise.",
    "mood_checkins": "The daily 30-second mood, stress, sleep and energy check-in.",
    "symptom_logs": "Symptoms the patient reported.",
    "symptom_checkins": "Targeted symptom questions the app asked and the answers.",
    "lab_results": "Lab values (HbA1c, lipids, kidney) with date.",
    "blood_pressure_readings": "Blood pressure readings.",
    "body_measurements": "Weight and waist measurements.",
    "appointments": "Planned or suggested visits and screenings.",
    "doctor_questions": "Questions the patient wants to ask their doctor.",
    "patient_preventive_status": "When each check-up (eye, foot, kidney...) was last done and is next due.",
    "devices": "The connected sources shown in the app (watch, sensor, camera) and when they last synced.",
    "health_goals": "Targets such as weekly exercise minutes; defaults until a clinician sets them.",
    "notifications": "Reminders and nudges that were scheduled, sent and acted on.",
    "drug_reference": "Reference list of generic drugs (from the 250k Medicines file).",
    "drug_aliases": "Brand and local names that map to a drug. For matching only; never suggests a substitute.",
    "drug_side_effects": "Common side effects per drug.",
    "interaction_rules": "Drug pairs that may interact (from the openFDA drug-label text). Unreviewed reference data.",
    "foods": "Food list with nutrients per serving (sanity check for AI estimates).",
    "preventive_items": "Recommended check-ups and how often.",
    "routing_rules": "Which kind of doctor to ask about which complication. Routing only, never diagnosis.",
    "population_priors": "Typical values by age, sex and diabetes status (NHANES). Used only to cold-start baselines.",
    "knowledge_documents": "Approved source documents for retrieval.",
    "knowledge_chunks": "Text pieces of those documents with their embeddings.",
    "data_sources": "Where every dataset came from, with licence (for attribution).",
}
# column name (or suffix) -> unit
UNITS = {
    "value_mmol": "mmol/L", "sodium_mg": "mg", "kcal": "kcal", "duration_s": "seconds", "height_cm": "cm",
    "weight_kg": "kg", "waist_cm": "cm", "systolic": "mmHg", "diastolic": "mmHg", "pulse": "beats/min",
    "avg_hr": "beats/min", "alcohol_units": "alcohol units", "window_minutes": "minutes", "interval_months": "months",
    "portion_multiplier": "x portion", "planned_days": "days", "native_interval_min": "minutes", "tokens": "tokens",
    "photo_count": "photos", "birth_year": "year", "diagnosed_year": "year", "since_year": "year",
    "serving_g": "g", "last_hba1c_pct": "% HbA1c", "efficiency_pct": "%", "estimate_confidence": "0 to 1",
    "times_per_day": "doses/day", "quantity_dispensed": "units", "remaining_units": "units",
}
SPECIAL = {
    ("lab_results", "value"): "unit in the `unit` column (% HbA1c, mmol/L, umol/L creatinine, mg/g UACR, mL/min/1.73m2 eGFR)",
    ("health_samples", "value"): "unit in the `unit` column (count, bpm, ms, %, score, seconds)",
    ("dose_events", "scheduled_at"): "UTC",
}
PLAIN_UUID = {  # columns that will become foreign keys in E1-3 (Gold and Operations tables do not exist yet)
    ("symptom_checkins", "triggered_by_flag_id"): "clinical_flags",
    ("appointments", "brief_id"): "briefs",
    ("doctor_questions", "brief_id"): "briefs",
    ("prescription_scans", "agent_run_id"): "agent_runs",
}
SOURCE_COLS = ("source", "entry_source", "estimated_by")


def unit_of(table, col, typ):
    if (table, col) in SPECIAL:
        return SPECIAL[(table, col)]
    if col in UNITS:
        return UNITS[col]
    if col.endswith("_g"):
        return "g"
    if col.endswith("_pct"):
        return "%"
    if col.endswith("_min"):
        return "minutes"
    if typ.startswith("timestamp"):
        return "UTC"
    if typ == "date":
        return "date"
    if typ.startswith("time"):
        return "local time"
    return ""


def main():
    load_env()
    lm = layer_map()
    layer_of = {t: l for l in LAYERS for t in lm[l]}
    with psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20) as c:
        cols = c.execute("""select cl.relname, a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull,
                                   exists (select 1 from pg_constraint k where k.conrelid = cl.oid and k.contype = 'p' and a.attnum = any (k.conkey))
                            from pg_attribute a join pg_class cl on cl.oid = a.attrelid join pg_namespace n on n.oid = cl.relnamespace
                            where n.nspname = 'public' and cl.relkind = 'r' and a.attnum > 0 and not a.attisdropped
                            order by cl.relname, a.attnum""").fetchall()
        fks = c.execute("""select cl.relname, a.attname, rcl.relname from pg_constraint k
                           join pg_class cl on cl.oid = k.conrelid join pg_class rcl on rcl.oid = k.confrelid
                           join pg_attribute a on a.attrelid = k.conrelid and a.attnum = k.conkey[1]
                           where k.contype = 'f' and cl.relnamespace = 'public'::regnamespace and cardinality(k.conkey) = 1""").fetchall()
    fk = {(t, col): ref for t, col, ref in fks}
    by_table = {}
    for t, col, typ, notnull, pk in cols:
        by_table.setdefault(t, []).append((col, typ, notnull, pk))
    out = ["# Data dictionary", "",
           f"Generated by `scripts/make_data_dictionary.py` from the live database on {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. "
           "Do not edit by hand: change the migration, then re-run the script.", "",
           "Covers the Bronze, Silver and Reference tables (epic E1-1 and E1-2). The Gold and Operations tables, including "
           "application memory (`memory_facts`), are added after E1-3.", "",
           "**How to read it.** *Required* means the column cannot be empty. `NULL` always means \"no data\", never zero. "
           "*Unit* is the canonical unit stored (conversion to other units happens only in the API). "
           "*Source flag* names the column that says where a row came from: `source` / `entry_source` hold "
           "`manual`, `scan`, `file_import`, `cgm`, `replay`, `system`, ... and `demo_dataset` marks data derived from the cited datasets "
           "(simulated or imported); `estimated_by` says who produced a nutrient value. All times are UTC.", ""]
    total = 0
    for layer in LAYERS:
        out += [f"## {layer.capitalize()}", ""]
        for t in sorted(lm[layer]):
            flag = ", ".join(f"`{col}`" for col, *_ in by_table[t] if col in SOURCE_COLS) or "none"
            out += [f"### `{t}`", "", PURPOSE[t], "", f"Source flag: {flag}", "",
                    "| Column | Type | Required | Unit | Notes |", "|---|---|---|---|---|"]
            for col, typ, notnull, pk in by_table[t]:
                notes = []
                if pk:
                    notes.append("primary key")
                if (t, col) in fk:
                    notes.append(f"-> `{fk[(t, col)]}`")
                if (t, col) in PLAIN_UUID:
                    notes.append(f"plain uuid for now; foreign key to `{PLAIN_UUID[(t, col)]}` is added in E1-3")
                out.append(f"| `{col}` | {typ.replace('extensions.', '')} | {'yes' if notnull else 'no'} | {unit_of(t, col, typ)} | {'; '.join(notes)} |")
                total += 1
            out.append("")
    (ROOT / "docs" / "data_dictionary.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote docs/data_dictionary.md: {sum(len(lm[l]) for l in LAYERS)} tables, {total} columns")


if __name__ == "__main__":
    main()
