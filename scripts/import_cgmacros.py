#!/usr/bin/env python3
"""Import CGMacros (manifest #5) into the Silver tables (E1-4 step 6). Safe to run twice.

The 14 participants with HbA1c >= 6.5% (our assumption for "diabetic", not a dataset label) become demo users.
Participant 046 is the demo patient ("Mr Tan"): everything is loaded, except the last 3 hours of sensor and watch data,
which are held back in data/demo/replay_feed.jsonl for the replay tool. The other 13 are thinned to protect the free
database size (Libre glucose only; heart rate every 5th minute); see docs/backlog/details/e1-4-handover.md.

Mapping: Libre/Dexcom (mg/dL) -> glucose_readings (mmol/L); HR -> health_samples heart_rate; Calories (Activity) ->
active_energy (demo patient only); meals -> meals + meal_items (estimated_by dataset, evidence observed);
bio.csv -> patient_profiles, lab_results, body_measurements; three fingersticks -> glucose_readings (context random).
Clock times are read as Singapore local time; each person's last day is shifted to the demo end date.

Usage: python scripts/import_cgmacros.py [--end-date YYYY-MM-DD]
"""
import argparse
import json
import sys
import zipfile
from datetime import timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etl_common import DEMO_DIR, DEMO_SOURCE, PROCESSED, RAW, bulk_insert, connect, count, demo_end_date, ensure_user, local_to_utc, log_dataset_file, mgdl_to_mmol, report, shift_days, uid  # noqa: E402

DEMO_SUBJECT = 46
HOLDBACK = timedelta(hours=3)
SRC = PROCESSED / "cgmacros" / "CGMacros"
FEED = DEMO_DIR / "replay_feed.jsonl"
MEAL_TYPES = {"breakfast": "breakfast", "lunch": "lunch", "dinner": "dinner", "snack": "snack", "snacks": "snack"}


def ensure_extracted():
    if not (SRC / "bio.csv").exists():
        zipfile.ZipFile(RAW / "cgmacros" / "CGMacros_dateshifted365.zip").extractall(PROCESSED / "cgmacros")


def glucose_value_ok(mmol):
    return 1.0 <= mmol <= 35.0


def import_person(conn, subj, bio_row, end_date):
    key = f"cgmacros-{subj:03d}"
    demo = subj == DEMO_SUBJECT
    user = ensure_user(conn, key)
    f = SRC / f"CGMacros-{subj:03d}" / f"CGMacros-{subj:03d}.csv"
    d = pd.read_csv(f, parse_dates=["Timestamp"])
    delta = timedelta(days=shift_days(d["Timestamp"].max().date(), end_date))
    d["local"] = d["Timestamp"] + delta
    first_local, last_local = d["local"].min(), d["local"].max()
    cutoff = last_local - HOLDBACK if demo else None
    sprint = uid("sprint", "cgmacros", subj)
    feed, held = [], 0

    def emit(table, held_row, normal_rows, ts_local, row):
        """Route a row to the replay feed (demo patient, last 3 hours) or the normal load."""
        nonlocal held
        if cutoff is not None and ts_local > cutoff:
            feed.append({"t": local_to_utc(ts_local.to_pydatetime()).isoformat(), "table": table, "row": held_row})
            held += 1
        else:
            normal_rows.append(row)

    glucose, samples = [], []
    skipped = {"libre": 0, "dexcom": 0}
    devices = [("libre", "Libre GL", "libre_pro", 15)] + ([("dexcom", "Dexcom GL", "dexcom_g6", 5)] if demo else [])
    for name, col, device, interval in devices:
        for ts_src, ts_local, v in zip(d["Timestamp"], d["local"], d[col]):
            if pd.isna(v):
                continue
            mmol = mgdl_to_mmol(v)
            if not glucose_value_ok(mmol):
                skipped[name] += 1
                continue
            ext = f"cgmacros:{subj:03d}:{name}:{ts_src:%Y-%m-%dT%H:%M}"
            at = local_to_utc(ts_local.to_pydatetime())
            emit("glucose_readings", {"measured_at": at.isoformat(), "value_mmol": mmol, "device": device, "native_interval_min": interval, "external_id": ext, "cgm_sprint_id": str(sprint)},
                 glucose, ts_local, (uid("glu", ext), user, at, mmol, "cgm", DEMO_SOURCE, ext, sprint, device, True, interval))
    # heart rate (demo: every minute; others: every 5th minute) and activity energy (demo only)
    for ts_src, ts_local, hr, kcal in zip(d["Timestamp"], d["local"], d["HR"], d["Calories (Activity)"]):
        if not pd.isna(hr) and (demo or ts_src.minute % 5 == 0):
            ext = f"cgmacros:{subj:03d}:hr:{ts_src:%Y-%m-%dT%H:%M}"
            at = local_to_utc(ts_local.to_pydatetime())
            emit("health_samples", {"metric": "heart_rate", "start_at": at.isoformat(), "end_at": (at + timedelta(minutes=1)).isoformat(), "value": float(hr), "unit": "bpm", "device": "fitbit_sense", "external_id": ext},
                 samples, ts_local, (uid("hs", ext), user, "heart_rate", at, at + timedelta(minutes=1), float(hr), "bpm", DEMO_SOURCE, "fitbit_sense", ext))
        if demo and not pd.isna(kcal):
            ext = f"cgmacros:{subj:03d}:kcal:{ts_src:%Y-%m-%dT%H:%M}"
            at = local_to_utc(ts_local.to_pydatetime())
            emit("health_samples", {"metric": "active_energy", "start_at": at.isoformat(), "end_at": (at + timedelta(minutes=1)).isoformat(), "value": float(kcal), "unit": "kcal", "device": "fitbit_sense", "external_id": ext},
                 samples, ts_local, (uid("hs", ext), user, "active_energy", at, at + timedelta(minutes=1), float(kcal), "kcal", DEMO_SOURCE, "fitbit_sense", ext))
    # meals
    meals, items = [], []
    for ts_src, ts_local, mt, kcal, carbs, prot, fat, fib, amt in zip(d["Timestamp"], d["local"], d["Meal Type"], d["Calories"], d["Carbs"], d["Protein"], d["Fat"], d["Fiber"], d.get("Amount Consumed", pd.Series(float("nan"), index=d.index))):  # participant 028 has no such column
        if pd.isna(mt):
            continue
        mtype = MEAL_TYPES.get(str(mt).strip().lower(), "snack")
        at = local_to_utc(ts_local.to_pydatetime())
        mid = uid("meal", "cgmacros", subj, f"{ts_src:%Y-%m-%dT%H:%M}")
        desc = f"CGMacros dataset meal ({mt}); amount consumed {int(amt)}%" if not pd.isna(amt) else f"CGMacros dataset meal ({mt})"
        meals.append((mid, user, at, mtype, desc, DEMO_SOURCE))
        n = lambda x: None if pd.isna(x) else float(x)  # noqa: E731
        items.append((uid("mealitem", mid), mid, f"{str(mt).strip().lower()} (dataset meal)", 1.0, n(carbs), n(kcal), n(prot), n(fat), n(fib), "dataset", "observed"))
    # sprint, profile, labs, fingersticks, body
    sprint_row = (sprint, user, "libre_pro + dexcom_g6" if demo else "libre_pro", local_to_utc(first_local.to_pydatetime()), None if demo else local_to_utc(last_local.to_pydatetime()), 14, "CGMacros dataset sensor period")
    age, sex = int(bio_row["Age"]), {"M": "male", "F": "female"}.get(str(bio_row["Gender"]).strip(), "undisclosed")
    profile = (user, "Mr Tan" if demo else f"CGMacros participant {subj:03d}", end_date.year - age, sex, round(float(bio_row["Height"]) * 2.54, 1),
               round(float(bio_row["Body weight"]) * 0.45359237, 1), "type2", float(bio_row["A1c PDL (Lab)"]), first_local.date())
    labs = []
    for kind, val, unit in (("hba1c", bio_row["A1c PDL (Lab)"], "%"), ("fasting_glucose", bio_row["Fasting GLU - PDL (Lab)"] / 18.0, "mmol/L"),
                            ("triglycerides", bio_row["Triglycerides"] / 88.57, "mmol/L"), ("total_chol", bio_row["Cholesterol"] / 38.67, "mmol/L"),
                            ("hdl", bio_row["HDL"] / 38.67, "mmol/L"), ("ldl", bio_row["LDL (Cal)"] / 38.67, "mmol/L")):
        if not pd.isna(val):
            ext = f"cgmacros:{subj:03d}:lab:{kind}"
            labs.append((uid("lab", ext), user, kind, round(float(val), 2), unit, first_local.date(), DEMO_SOURCE, ext))
    fingers = []
    for i, (gcol, tcol) in enumerate((("#1 Contour Fingerstick GLU", "Time (t)"), ("#2 Contour Fingerstick GLU", "Time (t).1"), ("#3 Contour Fingerstick GLU", "Time (t).2")), 1):
        g, t = bio_row.get(gcol), bio_row.get(tcol)
        if g is not None and not pd.isna(g) and isinstance(t, str) and ":" in t:
            h, m = (int(x) for x in t.strip().split(":")[:2])
            at = local_to_utc(pd.Timestamp(first_local.date()).to_pydatetime().replace(hour=h, minute=m))
            mmol = mgdl_to_mmol(g)
            ext = f"cgmacros:{subj:03d}:finger:{i}"
            if glucose_value_ok(mmol):
                fingers.append((uid("glu", ext), user, at, mmol, "random", DEMO_SOURCE, ext, None, "contour_fingerstick", True, None))
    body = [(uid("body", subj), user, local_to_utc(first_local.to_pydatetime()), profile[5], DEMO_SOURCE, f"cgmacros:{subj:03d}:body")]

    ins = {}
    ins["users+file"] = log_dataset_file(conn, user, f) + log_dataset_file(conn, user, SRC / "bio.csv")
    ins["profile"] = bulk_insert(conn, "patient_profiles", ["user_id", "display_name", "birth_year", "sex", "height_cm", "weight_kg", "diabetes_type", "last_hba1c_pct", "last_hba1c_on"], [profile])
    ins["sprint"] = bulk_insert(conn, "cgm_sprints", ["id", "user_id", "device", "started_at", "ended_at", "planned_days", "purpose"], [sprint_row])
    gcols = ["id", "user_id", "measured_at", "value_mmol", "context", "source", "external_id", "cgm_sprint_id", "device", "quality_ok", "native_interval_min"]
    ins["glucose"] = bulk_insert(conn, "glucose_readings", gcols, glucose + fingers)
    ins["samples"] = bulk_insert(conn, "health_samples", ["id", "user_id", "metric", "start_at", "end_at", "value", "unit", "source", "device", "external_id"], samples)
    ins["meals"] = bulk_insert(conn, "meals", ["id", "user_id", "eaten_at", "meal_type", "description", "source"], meals)
    ins["meal_items"] = bulk_insert(conn, "meal_items", ["id", "meal_id", "custom_name", "portion_multiplier", "carbs_g", "kcal", "protein_g", "fat_g", "fibre_g", "estimated_by", "evidence_status"], items)
    ins["labs"] = bulk_insert(conn, "lab_results", ["id", "user_id", "kind", "value", "unit", "taken_on", "source", "external_id"], labs)
    ins["body"] = bulk_insert(conn, "body_measurements", ["id", "user_id", "measured_at", "weight_kg", "source", "external_id"], body)
    return ins, feed, {"held_back": held, "skipped_out_of_range": skipped, "shift_days": delta.days}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--end-date", help="the date the real CGM days end on (stored for everyone on first use)")
    a = ap.parse_args()
    ensure_extracted()
    end_date = demo_end_date(a.end_date)
    bio = pd.read_csv(SRC / "bio.csv")
    bio.columns = [c.strip() for c in bio.columns]
    people = bio[bio["A1c PDL (Lab)"] >= 6.5].sort_values("subject")
    print(f"demo end date {end_date}; {len(people)} diabetic participants (HbA1c >= 6.5)")
    feed_all, totals = [], {}
    with connect() as conn:
        for _, row in people.iterrows():
            subj = int(row["subject"])
            ins, feed, info = import_person(conn, subj, row.to_dict(), end_date)
            conn.commit()
            feed_all += feed
            for k, v in ins.items():
                totals[k] = totals.get(k, 0) + v
            print(f"  {subj:03d}{' (demo patient)' if subj == DEMO_SUBJECT else ''}: inserted " + ", ".join(f"{k}={v:,}" for k, v in ins.items()) + f" | held back {info['held_back']} | skipped {info['skipped_out_of_range']}")
        feed_all.sort(key=lambda r: r["t"])
        DEMO_DIR.mkdir(parents=True, exist_ok=True)
        FEED.write_text("\n".join(json.dumps(r) for r in feed_all) + ("\n" if feed_all else ""), encoding="utf-8")
        report("CGMacros total inserted", **totals)
        report("table totals", users=count(conn, "users"), glucose_readings=count(conn, "glucose_readings"), health_samples=count(conn, "health_samples"), meals=count(conn, "meals"))
        print("database size:", conn.execute("select pg_size_pretty(pg_database_size(current_database()))").fetchone()[0], "| replay feed rows:", len(feed_all))


if __name__ == "__main__":
    main()
