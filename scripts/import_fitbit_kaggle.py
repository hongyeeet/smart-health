#!/usr/bin/env python3
"""Import Fitbit (Kaggle, manifest #14), 5 people from the second export, into the Silver tables (E1-4 step 8).

A second watch format to prove imports work on any device. Safe to run twice. These people get a users row but no
patient profile (not known to have diabetes). Clock times are read as Singapore local time; each person's last day
is shifted to the demo end date. Mapping:
  heartrate_seconds  -> health_samples heart_rate, 5-minute mean (thinned to protect the free database size)
  hourlySteps        -> health_samples steps, one row per hour
  minuteSleep        -> sleep_sessions, one per logId: start/end from the minute rows, asleep_min = minutes with
                        value 1, awake_min = minutes with value 2 (restless) or 3 (awake), efficiency = asleep / in bed
  weightLogInfo      -> body_measurements weight_kg
Usage: python scripts/import_fitbit_kaggle.py
"""
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etl_common import DEMO_SOURCE, RAW, bulk_insert, connect, count, demo_end_date, ensure_user, local_to_utc, log_dataset_file, report, shift_days, uid  # noqa: E402

FOLDER = next((RAW / "fitbit" / "mturkfitbit_export_4.12.16-5.12.16").glob("Fitabase*"))
PEOPLE = [2026352035, 2347167796, 4558609924, 5577150313, 6962181067]
FMT = "%m/%d/%Y %I:%M:%S %p"
DEVICE = "fitbit"


def table(name, **kw):
    return pd.read_csv(FOLDER / name, **kw)


def main():
    end_date = demo_end_date()
    hr = table("heartrate_seconds_merged.csv")
    hr["ts"] = pd.to_datetime(hr["Time"], format=FMT)
    steps = table("hourlySteps_merged.csv")
    steps["ts"] = pd.to_datetime(steps["ActivityHour"], format=FMT)
    sleep = table("minuteSleep_merged.csv")
    sleep["ts"] = pd.to_datetime(sleep["date"], format=FMT)
    weight = table("weightLogInfo_merged.csv")
    weight["ts"] = pd.to_datetime(weight["Date"], format=FMT)
    print(f"demo end date {end_date}; Fitbit people {', '.join(str(p) for p in PEOPLE)}")
    totals = {}
    with connect() as conn:
        for pid in PEOPLE:
            user = ensure_user(conn, f"fitbit-{pid}")
            h = hr[hr["Id"] == pid]
            delta = timedelta(days=shift_days(h["ts"].max().date(), end_date))
            samples = []

            def add(metric, ts, v, unit, minutes):
                at = local_to_utc((ts + delta).to_pydatetime())
                ext = f"fitbit:{pid}:{metric}:{ts:%Y-%m-%dT%H:%M}"
                samples.append((uid("hs", ext), user, metric, at, at + timedelta(minutes=minutes), round(float(v), 1), unit, DEMO_SOURCE, DEVICE, ext))

            for ts, v in h.set_index("ts")["Value"].resample("5min").mean().dropna().items():
                add("heart_rate", ts, v, "bpm", 5)
            for ts, v in zip(steps.loc[steps["Id"] == pid, "ts"], steps.loc[steps["Id"] == pid, "StepTotal"]):
                add("steps", ts, v, "steps", 60)
            sessions = []
            for log, g in sleep[sleep["Id"] == pid].groupby("logId"):
                start, end = g["ts"].min(), g["ts"].max() + timedelta(minutes=1)
                in_bed = max(1, int((end - start).total_seconds() // 60))
                asleep, awake = int((g["value"] == 1).sum()), int(g["value"].isin([2, 3]).sum())
                ext = f"fitbit:{pid}:sleep:{log}"
                sessions.append((uid("sleep", ext), user, local_to_utc((start + delta).to_pydatetime()), local_to_utc((end + delta).to_pydatetime()), asleep, awake,
                                 round(100.0 * asleep / in_bed, 1), DEMO_SOURCE, DEVICE, ext))
            body = []
            for ts, kg, log in zip(weight.loc[weight["Id"] == pid, "ts"], weight.loc[weight["Id"] == pid, "WeightKg"], weight.loc[weight["Id"] == pid, "LogId"]):
                body.append((uid("body", "fitbit", pid, log), user, local_to_utc((ts + delta).to_pydatetime()), round(float(kg), 1), DEMO_SOURCE, f"fitbit:{pid}:weight:{log}"))
            ins = {"ingestion": sum(log_dataset_file(conn, user, FOLDER / f) for f in ("heartrate_seconds_merged.csv", "hourlySteps_merged.csv", "minuteSleep_merged.csv", "weightLogInfo_merged.csv")),
                   "samples": bulk_insert(conn, "health_samples", ["id", "user_id", "metric", "start_at", "end_at", "value", "unit", "source", "device", "external_id"], samples),
                   "sleep": bulk_insert(conn, "sleep_sessions", ["id", "user_id", "start_at", "end_at", "asleep_min", "awake_min", "efficiency_pct", "source", "device", "external_id"], sessions),
                   "weight": bulk_insert(conn, "body_measurements", ["id", "user_id", "measured_at", "weight_kg", "source", "external_id"], body)}
            conn.commit()
            for k, v in ins.items():
                totals[k] = totals.get(k, 0) + v
            print(f"  {pid}: inserted " + ", ".join(f"{k}={v:,}" for k, v in ins.items()) + f" | shift_days={delta.days}")
        report("Fitbit total inserted", **totals)
        report("table totals", users=count(conn, "users"), health_samples=count(conn, "health_samples"), sleep_sessions=count(conn, "sleep_sessions"), body_measurements=count(conn, "body_measurements"))
        print("database size:", conn.execute("select pg_size_pretty(pg_database_size(current_database()))").fetchone()[0])


if __name__ == "__main__":
    main()
