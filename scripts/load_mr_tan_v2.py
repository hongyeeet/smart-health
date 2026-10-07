#!/usr/bin/env python3
"""Load Mr Tan's generated dataset into the v2 tables (Bronze first, then Silver), with lineage on every row.

Usage:
  python scripts/load_mr_tan_v2.py            dry run: show what would happen, change nothing
  python scripts/load_mr_tan_v2.py --yes      do it (one transaction)

What it does (docs/specs/demo-data-plan.md, data-model-v2.md):
  1. checks the database is at Alembic 0018 and the CSV backup exists
  2. deletes the other 23 demo users (and everything of theirs) so only Mr Tan remains
  3. removes any earlier v2 rows of Mr Tan (so the script can be run again) and loads Bronze then Silver
Real rows (Dexcom glucose, his 29 meals, the labs of 2026-09-22) get source 'file_import'; every simulated or
derived row gets 'demo_dataset'. Bronze payloads of simulated data are the generated device batches / form entries.
Gold is built afterwards by scripts/build_gold_v2.py.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_mr_tan as G  # noqa: E402
from etl_common import bulk_insert, connect, uid  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TAN = G.TAN
TZ = G.TZ
SIM, REAL = "demo_dataset", "file_import"

BRONZE_TABLES = ["bronze_profile", "bronze_medication", "bronze_lab", "bronze_watch", "bronze_cgm", "bronze_blood_pressure",
                 "bronze_exercise", "bronze_food", "bronze_symptom", "bronze_wellbeing"]
# delete order for a clean reload: Gold, Silver (children first), then Bronze
RESET_ORDER = ["timeline_5min", "glucose_events", "exercise_response", "meal_response", "daily_summary", "care_summary", "baselines",
               "medication_log", "medication_schedule", "exercise_sets", "exercise_logs", "food_logs", "symptom_logs", "wellbeing_logs",
               "blood_pressure_readings", "cgm_readings", "watch_readings", "lab_results", "medications", "user_profile"] + BRONZE_TABLES[::-1]


def py(v):
    """pandas/numpy value -> plain Python (None for NaN/NaT)."""
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    if v is pd.NaT:
        return None
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


class Bronze:
    """Collects Bronze rows per table and hands out their ids."""

    def __init__(self):
        self.rows = {t: [] for t in BRONZE_TABLES}

    def add(self, table, key, source, payload, received_at):
        bid = str(uid("v2", table, key))
        text = json.dumps(payload, sort_keys=True, default=str)
        checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.rows[table].append((bid, TAN, py(received_at), source, text, None, checksum, "processed"))
        return bid


BCOLS = ["id", "user_id", "received_at", "source", "payload", "object_key", "checksum", "processing_status"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="really write to the database")
    ap.add_argument("--backup", default=str(ROOT / "data/processed/db_backup_2026-10-05"))
    a = ap.parse_args()
    np.seterr(over="ignore")

    if not (Path(a.backup) / "manifest.json").exists():
        sys.exit("The CSV backup is missing: run scripts/v2_backup.py first (and keep it).")
    real = G.load_real(a.backup)
    g = G.Gen(real)
    g.run()
    F = G.build_frames(g)
    B = Bronze()

    # ---------------------------------------------------------------- profile
    p = F["user_profile"]
    onboard = pd.Timestamp("2026-07-03 21:00", tz=TZ)
    b_prof = B.add("bronze_profile", "onboarding", SIM, {"form": "onboarding", "fields": {k: iso(v) if not isinstance(v, list) else v for k, v in p.items()}}, onboard)
    S = {}
    S["user_profile"] = [(TAN, p["display_name"], p["language"], p["has_diabetes"], p["birth_year"], p["gender"], p["race"], p["height_cm"], p["weight_kg"],
                          p["work_type"], p["work_days"], p["work_start"], p["work_end"], p["emergency_contact_name"], p["emergency_contact_phone"],
                          p["emergency_contact_relation"], p["watch_model"], p["cgm_model"], p["timezone"], p["glucose_target_low"], p["glucose_target_high"],
                          p["allergies_note"], p["conditions_note"], b_prof)]
    PCOLS = ["user_id", "display_name", "language", "has_diabetes", "birth_year", "gender", "race", "height_cm", "weight_kg", "work_type", "work_days", "work_start",
             "work_end", "emergency_contact_name", "emergency_contact_phone", "emergency_contact_relation", "watch_model", "cgm_model", "timezone",
             "glucose_target_low", "glucose_target_high", "allergies_note", "conditions_note", "bronze_id"]

    # ---------------------------------------------------------------- medications, schedule, log
    med_b = {}
    ms = F["medication_schedule"]
    meds_rows, sched_rows = [], []
    with connect() as conn0:
        ref = dict(conn0.execute("select generic_name, id from drug_reference").fetchall())
    for _, m in F["medications"].iterrows():
        rows = ms[ms.medication_id == m["id"]]
        payload = {"entry": "medication", "name": m["name"], "kind": m["kind"], "strength": m["strength"], "frequency": int(m["frequency"]),
                   "schedule": [{"time": r.dose_time, "quantity": float(r.quantity), "meal_relation": r.meal_relation} for r in rows.itertuples()]}
        rec = pd.Timestamp(m["start_date"] + " 09:00", tz=TZ) if m["key"] == "clarithro" else onboard
        med_b[m["id"]] = B.add("bronze_medication", f"entry:{m['key']}", SIM, payload, rec)
        meds_rows.append((m["id"], TAN, m["name"], m["kind"], m["strength"], int(m["frequency"]), m["description"], m["start_date"], m["end_date"],
                          ref.get(m["drug_ref"]) if m["drug_ref"] else None, SIM, med_b[m["id"]],
                          None if m["key"] == "tonic" else max(1, round(float(rows.quantity.sum()) * 30))))   # a 30-day supply (demo placeholder); none for the unreadable label
    S["medications"] = meds_rows
    for r in ms.itertuples():
        sched_rows.append((r.id, TAN, r.medication_id, r.dose_time, float(r.quantity), r.meal_relation))
    S["medication_schedule"] = sched_rows
    log_rows = []
    for r in F["medication_log"].itertuples():
        if r.status == "taken":
            bid = B.add("bronze_medication", f"dose:{r.id}", SIM, {"action": "taken", "medication": r.med, "scheduled_at": iso(r.scheduled_at), "taken_at": iso(r.taken_at)}, r.taken_at)
        else:
            bid = B.add("bronze_medication", f"dose:{r.id}", SIM, {"action": "missed", "medication": r.med, "scheduled_at": iso(r.scheduled_at), "reason": r.miss_reason},
                        r.scheduled_at + pd.Timedelta(hours=2))
        log_rows.append((r.id, TAN, r.medication_id, r.schedule_id, py(r.scheduled_at), py(r.taken_at), r.status, r.miss_reason, SIM, bid))
    S["medication_log"] = log_rows

    # ---------------------------------------------------------------- labs
    lab_rows = []
    for r in F["lab_results"].itertuples():
        src = REAL if r.real else SIM
        bid = B.add("bronze_lab", f"lab:{r.id}", src, {"entry": "lab", "test": r.test, "value": r.value, "unit": r.unit, "measured_at": iso(r.measured_at),
                                                           "origin": "CGMacros 1.0.0 participant 046, bio.csv" if r.real else "simulated history"}, r.measured_at)
        lab_rows.append((r.id, TAN, py(r.measured_at), r.test, r.value, r.unit, src, bid))
    S["lab_results"] = lab_rows

    # ---------------------------------------------------------------- watch: four syncs a day
    w = F["watch_readings"].copy()
    loc = w.recorded_at
    slot_end_h = np.select([loc.dt.hour < 6, loc.dt.hour < 12, loc.dt.hour < 18], [6, 12, 18], 24)
    w["sync_end"] = loc.dt.normalize() + pd.to_timedelta(slot_end_h, unit="h")
    watch_rows = []
    for sync_end, grp in w.groupby("sync_end"):
        rows_p = [[iso(t), int(h), (None if pd.isna(v) else float(v)), float(s), int(st), int(sl), o] for t, h, v, s, st, sl, o in
                  zip(grp.recorded_at, grp.heart_rate_bpm, grp.hrv_rmssd_ms, grp.spo2_pct, grp.steps, grp.sleep_minutes, grp.hr_origin)]
        payload = {"device": "Fitbit Sense", "interval_min": 5, "from": iso(grp.recorded_at.min()), "to": iso(grp.recorded_at.max()),
                   "columns": ["t", "heart_rate_bpm", "hrv_rmssd_ms", "spo2_pct", "steps", "sleep_minutes", "hr_origin"], "rows": rows_p,
                   "note": "heart_rate_bpm is real (or lightly imputed) where hr_origin is real/imputed; steps and sleep are derived from his real activity in that range; "
                           "everything else is simulated"}
        received = min(sync_end, g.end + pd.Timedelta(minutes=5)) + pd.Timedelta(minutes=2)
        bid = B.add("bronze_watch", f"sync:{sync_end}", SIM, payload, received)
        for r in grp.itertuples():
            watch_rows.append((TAN, py(r.recorded_at), int(r.heart_rate_bpm), py(r.hrv_rmssd_ms), py(r.spo2_pct), int(r.steps), int(r.sleep_minutes), SIM, bid))
    S["watch_readings"] = watch_rows

    # ---------------------------------------------------------------- CGM: one batch per day and origin
    c = F["cgm_readings"].copy()
    c["day"] = c.recorded_at.dt.normalize()
    cgm_rows = []
    for (day, isreal), grp in c.groupby(["day", "real"]):
        payload = {"device": "Dexcom G6", "interval_min": 5, "origin": "real" if isreal else "simulated", "columns": ["t", "mmol_per_l"],
                   "rows": [[iso(t), float(v)] for t, v in zip(grp.recorded_at, grp.glucose_mmol)],
                   "note": ("5-minute means of the Dexcom G6 file of CGMacros participant 046" if isreal else "simulated sensor batch")}
        src = REAL if isreal else SIM
        bid = B.add("bronze_cgm", f"day:{day}:{int(isreal)}", src, payload, grp.recorded_at.max() + pd.Timedelta(minutes=3))
        for r in grp.itertuples():
            cgm_rows.append((TAN, py(r.recorded_at), float(r.glucose_mmol), True, src, bid))
    S["cgm_readings"] = cgm_rows

    # ---------------------------------------------------------------- blood pressure
    bp_rows = []
    for r in F["blood_pressure_readings"].itertuples():
        bid = B.add("bronze_blood_pressure", f"bp:{r.id}", SIM, {"entry": "blood_pressure", "recorded_at": iso(r.recorded_at), "systolic": int(r.systolic_mmhg),
                                                                 "diastolic": int(r.diastolic_mmhg)}, r.recorded_at + pd.Timedelta(minutes=1))
        bp_rows.append((TAN, py(r.recorded_at), int(r.systolic_mmhg), int(r.diastolic_mmhg), SIM, bid))
    S["blood_pressure_readings"] = bp_rows

    # ---------------------------------------------------------------- exercise and sets
    ex_rows, set_rows = [], []
    sets_df = F["exercise_sets"]
    for r in F["exercise_logs"].itertuples():
        sets = sets_df[sets_df.exercise_log_id == r.id] if len(sets_df) else sets_df
        payload = {"entry": "exercise", "type": r.type, "start": iso(r.start), "end": iso(r.end), "intensity": int(r.intensity), "feeling": int(r.feeling) if pd.notna(r.feeling) else None,
                   "note": py(r.note), "origin": "inferred from real heart rate and activity" if r.real else "simulated",
                   "sets": [{"exercise": s.exercise, "order": int(s.exercise_order), "set": int(s.set_no), "reps": int(s.reps), "weight_kg": float(s.weight_kg)} for s in sets.itertuples()]}
        bid = B.add("bronze_exercise", f"ex:{r.id}", SIM, payload, r.end + pd.Timedelta(minutes=5))
        ex_rows.append((r.id, TAN, py(r.start), py(r.end), r.type, int(r.intensity), (int(r.feeling) if pd.notna(r.feeling) else None), py(r.note), SIM, bid))
    S["exercise_logs"] = ex_rows
    for s in sets_df.itertuples():
        set_rows.append((str(uid("v2", "set", s.exercise_log_id, s.exercise_order, s.set_no)), s.exercise_log_id, TAN, s.exercise, int(s.exercise_order), int(s.set_no),
                         int(s.reps), float(s.weight_kg), int(s.rest_s), int(s.rpe), py(s.performed_at)))
    S["exercise_sets"] = set_rows

    # ---------------------------------------------------------------- food
    food_rows = []
    for r in F["food_logs"].itertuples():
        src = REAL if r.real else SIM
        payload = {"entry": "food", "text": r.food, "start": iso(r.start), "end": iso(r.end),
                   "macros": {k: py(getattr(r, k)) for k in ["carbs_g", "protein_g", "fat_g", "fibre_g", "sugar_g", "sodium_mg", "kcal"]},
                   "estimated_by": r.estimated_by, "origin": ("CGMacros participant 046: macros from the dataset, the dish name is an illustrative label" if r.real
                                                              else "simulated entry; macros are team estimates for a typical serving")}
        bid = B.add("bronze_food", f"food:{r.id}", src, payload, r.end + pd.Timedelta(minutes=2))
        food_rows.append((r.id, TAN, py(r.start), py(r.end), r.meal_type, r.food, py(r.protein_g), py(r.carbs_g), py(r.fat_g), py(r.sugar_g), py(r.fibre_g), py(r.sodium_mg),
                          r.estimated_by, src, bid))
    S["food_logs"] = food_rows

    # ---------------------------------------------------------------- symptoms, wellbeing
    sy_rows = []
    for r in F["symptom_logs"].itertuples():
        bid = B.add("bronze_symptom", f"sy:{r.id}", SIM, {"entry": "symptom", "type": r.symptom_type, "severity": int(r.severity), "duration_min": py(r.duration_min), "note": r.note,
                                                           "occurred_at": iso(r.occurred_at)}, r.occurred_at + pd.Timedelta(minutes=10))
        sy_rows.append((r.id, TAN, py(r.occurred_at), r.symptom_type, int(r.severity), (int(r.duration_min) if pd.notna(r.duration_min) else None), r.note, SIM, bid))
    S["symptom_logs"] = sy_rows
    wb_rows = []
    for r in F["wellbeing_logs"].itertuples():
        vals = {k: (None if pd.isna(getattr(r, k)) else int(getattr(r, k))) for k in ["mood", "stress_self", "sleep_quality", "energy"]}
        bid = B.add("bronze_wellbeing", f"wb:{r.id}", SIM, {"entry": "wellbeing", "recorded_at": iso(r.recorded_at), **vals}, r.recorded_at + pd.Timedelta(minutes=1))
        wb_rows.append((r.id, TAN, py(r.recorded_at), vals["mood"], vals["stress_self"], vals["sleep_quality"], vals["energy"], SIM, bid))
    S["wellbeing_logs"] = wb_rows

    # ---------------------------------------------------------------- report
    print("Bronze rows:", {t: len(v) for t, v in B.rows.items()})
    print("Silver rows:", {t: len(v) for t, v in S.items()})
    if not a.yes:
        print("\nDry run: nothing was written. Run again with --yes to load.")
        return

    COLS = {
        "medications": ["id", "user_id", "name", "kind", "strength", "frequency", "description", "start_date", "end_date", "drug_reference_id", "source", "bronze_id", "total_quantity"],
        "medication_schedule": ["id", "user_id", "medication_id", "dose_time", "quantity", "meal_relation"],
        "medication_log": ["id", "user_id", "medication_id", "schedule_id", "scheduled_at", "taken_at", "status", "miss_reason", "source", "bronze_id"],
        "lab_results": ["id", "user_id", "measured_at", "test", "value", "unit", "source", "bronze_id"],
        "watch_readings": ["user_id", "recorded_at", "heart_rate_bpm", "hrv_rmssd_ms", "spo2_pct", "steps", "sleep_minutes", "source", "bronze_id"],
        "cgm_readings": ["user_id", "recorded_at", "glucose_mmol", "quality_ok", "source", "bronze_id"],
        "blood_pressure_readings": ["user_id", "recorded_at", "systolic_mmhg", "diastolic_mmhg", "source", "bronze_id"],
        "exercise_logs": ["id", "user_id", "start_at", "end_at", "type", "intensity", "feeling", "note", "source", "bronze_id"],
        "exercise_sets": ["id", "exercise_log_id", "user_id", "exercise", "exercise_order", "set_no", "reps", "weight_kg", "rest_s", "rpe", "performed_at"],
        "food_logs": ["id", "user_id", "start_at", "end_at", "meal_type", "food", "protein_g", "carbs_g", "fat_g", "sugar_g", "fibre_g", "sodium_mg", "estimated_by", "source", "bronze_id"],
        "symptom_logs": ["id", "user_id", "occurred_at", "symptom_type", "severity", "duration_min", "note", "source", "bronze_id"],
        "wellbeing_logs": ["id", "user_id", "recorded_at", "mood", "stress_self", "sleep_quality", "energy", "source", "bronze_id"],
    }
    ORDER = ["lab_results", "medications", "medication_schedule", "medication_log", "watch_readings", "cgm_readings", "blood_pressure_readings",
             "exercise_logs", "exercise_sets", "food_logs", "symptom_logs", "wellbeing_logs"]
    with connect() as conn:
        with conn.transaction():
            ver = conn.execute("select version_num from alembic_version").fetchone()[0]
            if ver != "0018":
                sys.exit(f"Database is at Alembic {ver}, expected 0018.")
            n_users = conn.execute("select count(*) from users where id <> %s", (TAN,)).fetchone()[0]
            conn.execute("delete from users where id <> %s", (TAN,))
            print(f"deleted {n_users} other demo users (their rows went with them)")
            for t in RESET_ORDER:
                conn.execute(f"delete from {t} where user_id = %s", (TAN,))
            conn.execute("update users set locale = 'en', timezone = %s, onboarding_completed_at = %s, is_demo = true where id = %s", (TZ, py(onboard), TAN))
            # Bronze first
            for t in BRONZE_TABLES:
                bulk_insert(conn, t, BCOLS, [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]) for r in B.rows[t]])
            bulk_insert(conn, "user_profile", PCOLS, S["user_profile"])
            for t in ORDER:
                n = bulk_insert(conn, t, COLS[t], S[t])
                print(f"  {t:26s} {n:>7,d} rows")
    print("done.")


if __name__ == "__main__":
    main()
