#!/usr/bin/env python3
"""Import BIG IDEAs Lab (manifest #4), 5 participants, into the Silver tables (E1-4 step 7). Safe to run twice.

None of these people has diabetes (HbA1c 5.3 to 6.4), so they get a users row and data but NO patient_profiles row
(the profile table only allows Type 2). Mapping (clock times read as Singapore local time; each person's last day is
shifted to the demo end date):
  Dexcom.csv (EGV, mg/dL)   -> glucose_readings (mmol/L, device dexcom_g6, native interval 5) + one closed cgm_sprint
  HR.csv (about 1 per second) -> health_samples heart_rate, 1-minute mean
  EDA.csv, TEMP.csv (4 Hz)  -> health_samples eda / skin_temp, 5-minute mean (thinned to protect the free database size)
  IBI.csv (beat intervals)  -> health_samples hrv_rmssd, RMSSD over 5-minute windows with at least 30 beats (derived)
  Food_Log.csv              -> meals + meal_items (estimated_by dataset). Rows with the same start time are one meal.
                               Participant 003's file has no header and only 4 numbers per row: only calories and carbs
                               are loaded for it. Meal type is derived from the time of day.
  Demographics.csv          -> lab_results hba1c
Usage: python scripts/import_bigideas.py
"""
import json
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etl_common import DEMO_SOURCE, RAW, bulk_insert, connect, count, demo_end_date, ensure_user, local_to_utc, log_dataset_file, mgdl_to_mmol, report, shift_days, uid  # noqa: E402

BASE = RAW / "big-ideas"
PEOPLE = ["003", "004", "009", "010", "011"]
DEVICE = "empatica_e4"


def meal_type(ts):
    h = ts.hour + ts.minute / 60
    return "breakfast" if 5 <= h < 10.5 else "lunch" if 10.5 <= h < 15 else "dinner" if 17 <= h < 21 else "snack"


def read_series(path, col):
    df = pd.read_csv(path, usecols=["datetime", " " + col] if False else None)
    df.columns = [c.strip() for c in df.columns]
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df[["datetime", col]].dropna()


def read_food(path):
    raw = pd.read_csv(path, header=None, dtype=str, keep_default_na=False)
    if raw.iloc[0, 0] == "date":                       # has a header row, 14 columns
        raw.columns = raw.iloc[0]
        raw = raw.iloc[1:].reset_index(drop=True)
        full = True
    else:                                              # participant 003: no header, 11 columns
        raw.columns = ["date", "time", "time_begin", "logged_food", "amount", "unit", "searched_food", "calorie", "total_carb", "n3", "n4"]
        full = False
    num = lambda c: pd.to_numeric(raw[c], errors="coerce") if c in raw else pd.Series(np.nan, index=raw.index)  # noqa: E731
    out = pd.DataFrame({"begin": pd.to_datetime(raw["time_begin"]), "name": raw["logged_food"].str.strip(), "kcal": num("calorie"), "carbs": num("total_carb"),
                        "fibre": num("dietary_fiber") if full else np.nan, "sugar": num("sugar") if full else np.nan,
                        "protein": num("protein") if full else np.nan, "fat": num("total_fat") if full else np.nan})
    return out[out["name"] != ""]


def import_person(conn, pid, demo_hba1c, end_date):
    key = f"bigideas-{pid}"
    user = ensure_user(conn, key)
    folder = BASE / pid
    ins = {}
    dx = pd.read_csv(folder / f"Dexcom_{pid}.csv", low_memory=False)
    dx = dx[dx["Event Type"] == "EGV"].copy()
    dx["ts"] = pd.to_datetime(dx["Timestamp (YYYY-MM-DDThh:mm:ss)"])
    dx["mg"] = pd.to_numeric(dx["Glucose Value (mg/dL)"], errors="coerce")
    non_numeric = int(dx["mg"].isna().sum())
    dx = dx.dropna(subset=["mg"])
    delta = timedelta(days=shift_days(dx["ts"].max().date(), end_date))
    first, last = dx["ts"].min() + delta, dx["ts"].max() + delta
    sprint = uid("sprint", "bigideas", pid)
    glucose, skipped = [], 0
    for ts, mg in zip(dx["ts"], dx["mg"]):
        mmol = mgdl_to_mmol(mg)
        if not 1.0 <= mmol <= 35.0:
            skipped += 1
            continue
        ext = f"bigideas:{pid}:dexcom:{ts:%Y-%m-%dT%H:%M:%S}"
        at = local_to_utc((ts + delta).to_pydatetime())
        glucose.append((uid("glu", ext), user, at, mmol, "cgm", DEMO_SOURCE, ext, sprint, "dexcom_g6", True, 5))

    samples = []

    def add(metric, ts_series, unit, step_min):
        for ts, v in ts_series.items():
            at = local_to_utc((ts + delta).to_pydatetime())
            ext = f"bigideas:{pid}:{metric}:{ts:%Y-%m-%dT%H:%M}"
            samples.append((uid("hs", ext), user, metric, at, at + timedelta(minutes=step_min), round(float(v), 2), unit, DEMO_SOURCE, DEVICE, ext))

    hr = read_series(folder / f"HR_{pid}.csv", "hr")
    add("heart_rate", hr.set_index("datetime")["hr"].resample("1min").mean().dropna(), "bpm", 1)
    for metric, col, unit in (("eda", "eda", "uS"), ("skin_temp", "temp", "degC")):
        s = read_series(folder / f"{col.upper()}_{pid}.csv", col)
        add(metric, s.set_index("datetime")[col].resample("5min").mean().dropna(), unit, 5)
    ibi = read_series(folder / f"IBI_{pid}.csv", "ibi")
    ibi["ms"] = ibi["ibi"] * 1000.0
    hrv = []
    for win, g in ibi.groupby(ibi["datetime"].dt.floor("5min")):
        if len(g) >= 30:
            d = np.diff(g["ms"].to_numpy())
            at = local_to_utc((win + delta).to_pydatetime())
            ext = f"bigideas:{pid}:hrv_rmssd:{win:%Y-%m-%dT%H:%M}"
            hrv.append((uid("hs", ext), user, "hrv_rmssd", at, at + timedelta(minutes=5), round(float(np.sqrt(np.mean(d ** 2))), 1), "ms", DEMO_SOURCE, DEVICE, ext,
                        json.dumps({"derived_from": "IBI", "window_min": 5, "beats": int(len(g)), "calculation": "RMSSD"})))
    food = read_food(folder / f"Food_Log_{pid}.csv")
    meals, items = [], []
    for begin, g in food.groupby("begin"):
        at = local_to_utc((begin + delta).to_pydatetime())
        mid = uid("meal", "bigideas", pid, f"{begin:%Y-%m-%dT%H:%M}")
        meals.append((mid, user, at, meal_type(begin), "BIG IDEAs dataset food log (meal type derived from time of day)", DEMO_SOURCE))
        for i, r in enumerate(g.itertuples()):
            n = lambda x: None if pd.isna(x) else float(x)  # noqa: E731
            items.append((uid("mealitem", mid, i, r.name), mid, r.name, 1.0, n(r.carbs), n(r.sugar), n(r.kcal), n(r.protein), n(r.fat), n(r.fibre), "dataset", "observed"))
    lab = [(uid("lab", "bigideas", pid, "hba1c"), user, "hba1c", float(demo_hba1c), "%", first.date(), DEMO_SOURCE, f"bigideas:{pid}:lab:hba1c")]
    sprint_row = [(sprint, user, "dexcom_g6", local_to_utc(first.to_pydatetime()), local_to_utc(last.to_pydatetime()), 14, "BIG IDEAs dataset sensor period")]

    files = sum(log_dataset_file(conn, user, folder / f"{k}_{pid}.csv") for k in ("Dexcom", "HR", "EDA", "TEMP", "IBI", "Food_Log")) + log_dataset_file(conn, user, BASE / "Demographics.csv")
    ins["ingestion"] = files
    ins["sprint"] = bulk_insert(conn, "cgm_sprints", ["id", "user_id", "device", "started_at", "ended_at", "planned_days", "purpose"], sprint_row)
    ins["glucose"] = bulk_insert(conn, "glucose_readings", ["id", "user_id", "measured_at", "value_mmol", "context", "source", "external_id", "cgm_sprint_id", "device", "quality_ok", "native_interval_min"], glucose)
    base_cols = ["id", "user_id", "metric", "start_at", "end_at", "value", "unit", "source", "device", "external_id"]
    ins["samples"] = bulk_insert(conn, "health_samples", base_cols, samples)
    ins["hrv"] = bulk_insert(conn, "health_samples", base_cols + ["detail"], hrv)
    ins["meals"] = bulk_insert(conn, "meals", ["id", "user_id", "eaten_at", "meal_type", "description", "source"], meals)
    ins["meal_items"] = bulk_insert(conn, "meal_items", ["id", "meal_id", "custom_name", "portion_multiplier", "carbs_g", "sugar_g", "kcal", "protein_g", "fat_g", "fibre_g", "estimated_by", "evidence_status"], items)
    ins["labs"] = bulk_insert(conn, "lab_results", ["id", "user_id", "kind", "value", "unit", "taken_on", "source", "external_id"], lab)
    return ins, {"non_numeric_glucose": non_numeric, "out_of_range": skipped, "shift_days": delta.days}


def main():
    end_date = demo_end_date()
    demo = pd.read_csv(BASE / "Demographics.csv", encoding="utf-8-sig")
    print(f"demo end date {end_date}; BIG IDEAs participants {', '.join(PEOPLE)}")
    totals = {}
    with connect() as conn:
        for pid in PEOPLE:
            ins, info = import_person(conn, pid, demo.loc[demo["ID"] == int(pid), "HbA1c"].iloc[0], end_date)
            conn.commit()
            for k, v in ins.items():
                totals[k] = totals.get(k, 0) + v
            print(f"  {pid}: inserted " + ", ".join(f"{k}={v:,}" for k, v in ins.items()) + f" | {info}")
        report("BIG IDEAs total inserted", **totals)
        report("table totals", users=count(conn, "users"), glucose_readings=count(conn, "glucose_readings"), health_samples=count(conn, "health_samples"), meals=count(conn, "meals"))
        print("database size:", conn.execute("select pg_size_pretty(pg_database_size(current_database()))").fetchone()[0])


if __name__ == "__main__":
    main()
