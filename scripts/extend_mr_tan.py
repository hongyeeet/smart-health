#!/usr/bin/env python3
"""Extend Mr Tan's demo record from his last simulated day up to today. Additive: nothing before the gap is changed.

Usage:
  python scripts/extend_mr_tan.py            dry run: builds everything in memory, checks it, writes nothing
  python scripts/extend_mr_tan.py --yes      writes it, in ONE transaction (all or nothing)

How the new days are made (they are simulated, so every new row has source 'demo_dataset'):
  * Each new day copies the same weekday of an earlier simulated week (the template day), so meals, doses, exercise, symptoms and mood keep
    a believable weekly rhythm, and the glucose and heart-rate response to a meal stays realistic.
  * Each day then gets a small, deterministic change (a glucose shift of about +/- 0.3 mmol/L and a scale of about +/- 6 %, a heart-rate shift
    of a couple of beats, steps +/- 12 %, blood pressure a few mmHg), so no two weeks are identical. Same date, same result.
  * New Bronze rows are written for every new Silver row (lineage), and the Gold layer for the new days is built with the SAME functions as
    scripts/build_gold_v2.py, so the numbers on screen are computed, not pasted.
  * Today stops at the current time: nothing is made for the future.
Rows already there (for example a meal a tester logged on 9 or 13 October) are kept; a copied row is skipped if one is within 30 minutes.
Gold rows from the first new day onward are rebuilt; the old ones are first saved to data/processed/extend_backup_<time>/ (git-ignored).

To undo: delete the rows with source 'demo_dataset' dated 2 October 2026 or later for this user in the Silver and Bronze tables, and the Gold rows
from that date (or restore the Gold backup).
"""
import argparse
import hashlib
import json
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_gold_v2 as BG  # noqa: E402
from etl_common import bulk_insert, connect  # noqa: E402

TAN = BG.TAN
SGT = timezone(timedelta(hours=8))
FIRST = date(2026, 10, 2)                       # the first local day with anything missing (the sensors stop at 07:40 on 2 October)
NS = uuid.uuid5(uuid.NAMESPACE_URL, "equinox-demo-extension-2026-10")
SIM = "demo_dataset"
ROOT = Path(__file__).resolve().parents[1]


def nid(*parts):
    return str(uuid.uuid5(NS, "|".join(str(p) for p in parts)))


def ldate(s):
    return pd.to_datetime(s, utc=True).dt.tz_convert(SGT).dt.date


def template_day(d):
    """The same weekday, one, three or five weeks earlier (week 0 of the gap uses 7 days back, week 1 uses 21, week 2 uses 35)."""
    w = (d - FIRST).days // 7
    return d - timedelta(days=7 * (1 + 2 * w))


def day_params(d):
    r = np.random.default_rng(int(d.strftime("%Y%m%d")))
    return dict(a=r.uniform(0.94, 1.06), b=r.normal(0, 0.3), hr=int(round(r.normal(0, 2))), steps=r.uniform(0.88, 1.12),
                sys=int(round(r.normal(0, 3))), dia=int(round(r.normal(0, 2))), hrv=r.uniform(0.95, 1.05))


def checksum(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def clean(v):
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    if v is pd.NaT:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if isinstance(v, (dict, list)) and not isinstance(v, str):
        return json.dumps(v, default=str)
    return v


def tuples(df, cols):
    return [tuple(clean(v) for v in row) for row in df[cols].itertuples(index=False, name=None)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="write it (default is a dry run)")
    args = ap.parse_args()
    np.seterr(all="ignore")
    now = datetime.now(timezone.utc)
    today = now.astimezone(SGT).date()
    days = [FIRST + timedelta(days=i) for i in range((today - FIRST).days + 1)]
    print(f"{'WRITING' if args.yes else 'DRY RUN'}: new days {days[0]} to {days[-1]} ({len(days)} days), now = {now.astimezone(SGT):%Y-%m-%d %H:%M} SGT")

    with connect() as conn:
        q = BG.q
        profile = q(conn, "select * from user_profile where user_id = %s", (TAN,)).iloc[0]
        ctx = dict(profile=profile, tz=profile.timezone)
        ctx["watch"] = q(conn, "select * from watch_readings where user_id = %s order by recorded_at", (TAN,))
        ctx["cgm"] = q(conn, "select * from cgm_readings where user_id = %s order by recorded_at", (TAN,))
        ctx["bp"] = q(conn, "select * from blood_pressure_readings where user_id = %s and deleted_at is null order by recorded_at", (TAN,))
        ctx["ex"] = q(conn, "select * from exercise_logs where user_id = %s and deleted_at is null order by start_at", (TAN,))
        ctx["food"] = q(conn, "select * from food_logs where user_id = %s and deleted_at is null order by start_at", (TAN,))
        ctx["sym"] = q(conn, "select * from symptom_logs where user_id = %s and deleted_at is null order by occurred_at", (TAN,))
        ctx["wb"] = q(conn, "select * from wellbeing_logs where user_id = %s and deleted_at is null order by recorded_at", (TAN,))
        ctx["medlog"] = q(conn, "select * from medication_log where user_id = %s order by scheduled_at", (TAN,))
        ctx["meds"] = q(conn, "select * from medications where user_id = %s", (TAN,))
        ctx["schedule"] = q(conn, "select * from medication_schedule where user_id = %s", (TAN,))
        ctx["labs"] = q(conn, "select * from lab_results where user_id = %s", (TAN,))
        sets = q(conn, "select * from exercise_sets where user_id = %s", (TAN,))
        for k in ("watch", "cgm", "bp", "ex", "food", "sym", "wb", "medlog"):
            for c in ctx[k].columns:
                if str(ctx[k][c].dtype).startswith("datetime64") or c in ("recorded_at", "start_at", "end_at", "occurred_at", "scheduled_at", "taken_at", "created_at", "updated_at", "deleted_at"):
                    ctx[k][c] = pd.to_datetime(ctx[k][c], utc=True)
        sets["performed_at"] = pd.to_datetime(sets["performed_at"], utc=True)
        old = {k: ctx[k].copy() for k in ("watch", "cgm", "bp", "ex", "food", "sym", "wb", "medlog")}
        last_cgm, last_watch = ctx["cgm"].recorded_at.max(), ctx["watch"].recorded_at.max()
        print(f"existing: last glucose {last_cgm.astimezone(SGT):%Y-%m-%d %H:%M}, last watch {last_watch.astimezone(SGT):%Y-%m-%d %H:%M} SGT")

        # ------------------------------------------------------------------------------------------ new Silver and Bronze rows
        bronze = {t: [] for t in ("bronze_cgm", "bronze_watch", "bronze_food", "bronze_exercise", "bronze_symptom", "bronze_wellbeing", "bronze_blood_pressure", "bronze_medication")}
        new = {k: [] for k in ("cgm", "watch", "bp", "food", "ex", "sets", "sym", "wb", "medlog")}

        def near(existing, col, t, minutes=30):
            if existing.empty:
                return False
            return bool((abs(existing[col] - t) <= pd.Timedelta(minutes=minutes)).any())

        # template bronze rows for the entry tables, by silver bronze id
        def template_bronze(table, ids):
            ids = [str(i) for i in ids if i is not None and str(i) != "nan"]
            if not ids:
                return {}
            df = q(conn, f"select * from {table} where id = any(%s::uuid[])", (ids,))
            return {str(r.id): r for r in df.itertuples()}

        def entry_bronze(table, old_row_bronze_id, new_key, new_time, tb, d, t):
            """A Bronze row for one copied entry; returns its id (or None when the template had none)."""
            src = tb.get(str(old_row_bronze_id))
            if src is None:
                return None
            payload = dict(src.payload) if isinstance(src.payload, dict) else {"original": src.payload}
            payload["extension"] = {"copied_from_day": str(t), "for_day": str(d), "note": "simulated, copied from an earlier week of the demo record"}
            bid = nid(table, new_key)
            bronze[table].append(dict(id=bid, user_id=TAN, received_at=new_time, source=SIM, payload=json.dumps(payload, default=str), object_key=None,
                                      checksum=checksum(payload), processing_status=src.processing_status))
            return bid

        tb_food = template_bronze("bronze_food", ctx["food"].bronze_id.tolist())
        tb_ex = template_bronze("bronze_exercise", ctx["ex"].bronze_id.tolist())
        tb_sym = template_bronze("bronze_symptom", ctx["sym"].bronze_id.tolist())
        tb_wb = template_bronze("bronze_wellbeing", ctx["wb"].bronze_id.tolist())
        tb_bp = template_bronze("bronze_blood_pressure", ctx["bp"].bronze_id.tolist())
        tb_med = template_bronze("bronze_medication", ctx["medlog"].bronze_id.tolist())
        # one template Bronze row to copy the status words from for the per-day sensor batches
        proc_cgm = q(conn, "select processing_status from bronze_cgm where user_id = %s limit 1", (TAN,)).iloc[0, 0]
        proc_watch = q(conn, "select processing_status from bronze_watch where user_id = %s limit 1", (TAN,)).iloc[0, 0]

        for k in ("watch", "cgm", "bp", "ex", "food", "sym", "wb", "medlog"):
            ctx[k]["_ld"] = ldate(ctx[k][{"watch": "recorded_at", "cgm": "recorded_at", "bp": "recorded_at", "ex": "start_at", "food": "start_at", "sym": "occurred_at", "wb": "recorded_at", "medlog": "scheduled_at"}[k]])
        sets_by_ex = {str(k): v for k, v in sets.groupby("exercise_log_id")}

        for d in days:
            t = template_day(d)
            p = day_params(d)
            delta = pd.Timedelta(days=(d - t).days)
            # sensor streams ---------------------------------------------------------------------------------------------------------
            c = ctx["cgm"][ctx["cgm"]._ld == t].copy()
            c["recorded_at"] = c.recorded_at + delta
            c = c[(c.recorded_at > last_cgm) & (c.recorded_at <= now)]
            if len(c):
                c["glucose_mmol"] = (c.glucose_mmol.astype(float) * p["a"] + p["b"]).clip(2.4, 25).round(1)
                bid = nid("bronze_cgm", d)
                bronze["bronze_cgm"].append(dict(id=bid, user_id=TAN, received_at=min(c.recorded_at.max(), now), source=SIM,
                                                 payload=json.dumps({"note": "simulated 5-minute glucose, copied from an earlier week of the demo record with small changes",
                                                                     "rows": [[r.recorded_at.astimezone(SGT).isoformat(), float(r.glucose_mmol)] for r in c.itertuples()]}),
                                                 object_key=None, checksum=checksum({"cgm": str(d), "n": len(c)}), processing_status=proc_cgm))
                c["bronze_id"], c["source"], c["user_id"] = bid, SIM, TAN
                new["cgm"].append(c)
            w = ctx["watch"][ctx["watch"]._ld == t].copy()
            w["recorded_at"] = w.recorded_at + delta
            w = w[(w.recorded_at > last_watch) & (w.recorded_at <= now)]
            if len(w):
                w["heart_rate_bpm"] = (w.heart_rate_bpm.astype(float) + p["hr"]).clip(38, 200).round()
                w["hrv_rmssd_ms"] = (w.hrv_rmssd_ms.astype(float) * p["hrv"]).round(1)
                w["steps"] = (w.steps.astype(float) * p["steps"]).round()
                bid = nid("bronze_watch", d)
                bronze["bronze_watch"].append(dict(id=bid, user_id=TAN, received_at=min(w.recorded_at.max(), now), source=SIM,
                                                   payload=json.dumps({"note": "simulated watch readings, copied from an earlier week of the demo record with small changes",
                                                                       "rows": [[r.recorded_at.astimezone(SGT).isoformat(), clean(r.heart_rate_bpm), clean(r.hrv_rmssd_ms), clean(r.spo2_pct), clean(r.steps), clean(r.sleep_minutes)] for r in w.itertuples()]},
                                                                      default=str),
                                                   object_key=None, checksum=checksum({"watch": str(d), "n": len(w)}), processing_status=proc_watch))
                w["bronze_id"], w["source"], w["user_id"] = bid, SIM, TAN
                new["watch"].append(w)
            # entries ----------------------------------------------------------------------------------------------------------------
            def copy_entries(key, table, time_col, tb, id_col="id", span=False):
                sub = ctx[key][ctx[key]._ld == t]
                out = []
                for r in sub.itertuples():
                    row = ctx[key].loc[r.Index].copy()
                    t_new = row[time_col] + delta
                    if t_new > now:
                        continue
                    if near(old[key], time_col, t_new):
                        continue
                    row["id"] = nid(table, row["id"], d)
                    row[time_col] = t_new
                    if span:
                        row["end_at"] = row["end_at"] + delta
                    row["source"] = SIM
                    row["bronze_id"] = entry_bronze(f"bronze_{table_bronze[key]}", ctx[key].loc[r.Index, "bronze_id"], row["id"], t_new, tb, d, t)
                    for cc in ("created_at", "updated_at"):
                        if cc in row.index:
                            row[cc] = t_new
                    if "deleted_at" in row.index:
                        row["deleted_at"] = pd.NaT
                    out.append(row)
                return out

            table_bronze = {"food": "food", "ex": "exercise", "sym": "symptom", "wb": "wellbeing", "bp": "blood_pressure"}
            for key, table, tcol, tb, span in (("food", "food_logs", "start_at", tb_food, True), ("ex", "exercise_logs", "start_at", tb_ex, True),
                                               ("sym", "symptom_logs", "occurred_at", tb_sym, False), ("wb", "wellbeing_logs", "recorded_at", tb_wb, False),
                                               ("bp", "blood_pressure_readings", "recorded_at", tb_bp, False)):
                rows = copy_entries(key, table, tcol, tb, span=span)
                for r in rows:
                    if key == "bp":
                        r["systolic_mmhg"] = int(r["systolic_mmhg"] + p["sys"])
                        r["diastolic_mmhg"] = int(r["diastolic_mmhg"] + p["dia"])
                    if key == "ex":
                        old_id = [x for x in ctx["ex"].id if nid("exercise_logs", x, d) == r["id"]][0]
                        for s in sets_by_ex.get(str(old_id), pd.DataFrame()).itertuples() if str(old_id) in sets_by_ex else []:
                            sr = sets.loc[s.Index].copy()
                            sr["id"] = nid("exercise_sets", sr["id"], d)
                            sr["exercise_log_id"] = r["id"]
                            sr["performed_at"] = sr["performed_at"] + delta
                            sr["created_at"] = r["start_at"]
                            new["sets"].append(sr)
                    new[key].append(pd.DataFrame([r]))
            # doses ------------------------------------------------------------------------------------------------------------------
            sub = ctx["medlog"][ctx["medlog"]._ld == t]
            have = set(zip(old["medlog"].medication_id.astype(str), old["medlog"].scheduled_at))
            for r in sub.itertuples():
                row = ctx["medlog"].loc[r.Index].copy()
                s_new = row["scheduled_at"] + delta
                if s_new > now - pd.Timedelta(hours=1) or (str(row["medication_id"]), s_new) in have:
                    continue
                key_id = nid("medication_log", row["id"], d)
                row["id"], row["scheduled_at"], row["source"] = key_id, s_new, SIM
                if pd.notna(row["taken_at"]):
                    row["taken_at"] = row["taken_at"] + delta
                    if row["taken_at"] > now:
                        continue
                row["bronze_id"] = entry_bronze("bronze_medication", ctx["medlog"].loc[r.Index, "bronze_id"], key_id, s_new, tb_med, d, t)
                row["created_at"] = row["updated_at"] = s_new
                new["medlog"].append(pd.DataFrame([row]))

        def cat(key):
            parts = [x if isinstance(x, pd.DataFrame) else x.to_frame().T for x in new[key]]
            return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

        N = {k: cat(k) for k in new}
        print("new Silver rows:", {k: len(v) for k, v in N.items()})
        print("new Bronze rows:", {k: len(v) for k, v in bronze.items()})

        # ------------------------------------------------------------------------------------------ Gold for old + new, then keep the new
        def merged(k):
            n = N[k].drop(columns=[c for c in ("_ld",) if c in N[k].columns]) if len(N[k]) else N[k]
            base = ctx[k].drop(columns=["_ld"])
            if not len(n):
                return base
            for c in base.columns:
                if c in n.columns and str(base[c].dtype).startswith("datetime64"):
                    n[c] = pd.to_datetime(n[c], utc=True)
            out = pd.concat([base, n[[c for c in base.columns if c in n.columns]]], ignore_index=True)
            return out

        ctx2 = dict(ctx)
        for k in ("watch", "cgm", "bp", "ex", "food", "sym", "wb", "medlog"):
            ctx2[k] = merged(k)
        for k in ("watch", "cgm", "bp", "ex", "food", "sym", "wb"):
            tcol = {"watch": "recorded_at", "cgm": "recorded_at", "bp": "recorded_at", "ex": "start_at", "food": "start_at", "sym": "occurred_at", "wb": "recorded_at"}[k]
            ctx2[k] = ctx2[k].sort_values(tcol).reset_index(drop=True)
        ctx2["medlog"] = ctx2["medlog"].sort_values("scheduled_at").reset_index(drop=True)
        for c in ("start_at", "end_at"):
            ctx2["ex"][c] = pd.to_datetime(ctx2["ex"][c], utc=True)
        for c in ("glucose_mmol",):
            ctx2["cgm"][c] = ctx2["cgm"][c].astype(float)
        for c in ("heart_rate_bpm", "hrv_rmssd_ms", "spo2_pct", "steps", "sleep_minutes"):
            ctx2["watch"][c] = pd.to_numeric(ctx2["watch"][c], errors="coerce")
        for c in ("systolic_mmhg", "diastolic_mmhg"):
            ctx2["bp"][c] = pd.to_numeric(ctx2["bp"][c], errors="coerce")
        print("building Gold for the whole record ...")
        T = BG.build_timeline(ctx2)
        Bq = q(conn, "select * from baselines where user_id = %s", (TAN,))
        ctx_b = BG.apply_vs_baseline(T, Bq)
        Dsum = BG.build_daily(T, ctx2, ctx_b)
        M = BG.meal_responses(T, ctx2)
        X = BG.exercise_responses(T, ctx2)
        ev = BG.glucose_events(T, ctx2)
        C = BG.care_summary(conn, ctx2, Dsum)

        # sanity check: the days that already existed must come out the same as what is stored
        dbd = q(conn, "select * from daily_summary where user_id = %s and local_date between %s and %s order by local_date", (TAN, date(2026, 9, 20), date(2026, 10, 1)))
        mine = Dsum.set_index("local_date")
        for col in ("glucose_mean_mmol", "steps_total", "tir_pct", "doses_taken", "bp_systolic_mean"):
            a = pd.to_numeric(dbd.set_index("local_date")[col], errors="coerce")
            b = pd.to_numeric(mine[col], errors="coerce")
            diff = (a - b.reindex(a.index)).abs().max()
            print(f"  check {col:20s} max difference vs stored, 20 Sep to 1 Oct: {diff:.3f}")

        T_new = T[T.local_date >= FIRST].copy()
        D_new = Dsum[(Dsum.local_date >= FIRST) & (Dsum.local_date < today)]
        new_food_ids = set(ctx2["food"][pd.to_datetime(ctx2["food"].start_at, utc=True).dt.tz_convert(SGT).dt.date >= FIRST].id.astype(str))
        new_ex_ids = set(ctx2["ex"][pd.to_datetime(ctx2["ex"].start_at, utc=True).dt.tz_convert(SGT).dt.date >= FIRST].id.astype(str))
        M_new = M[M.food_log_id.astype(str).isin(new_food_ids)]
        X_new = X[X.exercise_log_id.astype(str).isin(new_ex_ids)] if len(X) else X
        t_first = datetime.combine(FIRST, datetime.min.time(), tzinfo=SGT)
        ev_new = ev[pd.to_datetime(ev.started_at).dt.tz_localize(SGT) >= t_first] if len(ev) and pd.to_datetime(ev.started_at).dt.tz is None else ev[pd.to_datetime(ev.started_at, utc=True) >= t_first]
        C_new = C[[d >= FIRST and d < today for d in C.local_date]]
        print(f"new Gold rows: timeline {len(T_new):,d}, daily_summary {len(D_new)}, meal_response {len(M_new)}, exercise_response {len(X_new)}, glucose_events {len(ev_new)}, care_summary {len(C_new)}")
        print(f"glucose on new days: mean {T_new.glucose_mmol.mean():.1f}, in range {((T_new.glucose_mmol >= 3.9) & (T_new.glucose_mmol <= 10.0)).sum() / T_new.glucose_mmol.notna().sum() * 100:.0f} %")

        if not args.yes:
            print("dry run: nothing written. Run again with --yes to write.")
            return

        # ------------------------------------------------------------------------------------------ write
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        backup = ROOT / "data" / "processed" / f"extend_backup_{stamp}"
        backup.mkdir(parents=True, exist_ok=True)
        with conn.transaction():
            for table, col in (("timeline_5min", "local_date"), ("daily_summary", "local_date"), ("care_summary", "local_date")):
                q(conn, f"select * from {table} where user_id = %s and {col} >= %s", (TAN, FIRST)).to_csv(backup / f"{table}.csv", index=False)
                conn.execute(f"delete from {table} where user_id = %s and {col} >= %s", (TAN, FIRST))
            q(conn, "select * from glucose_events where user_id = %s and started_at >= %s", (TAN, t_first)).to_csv(backup / "glucose_events.csv", index=False)
            conn.execute("delete from glucose_events where user_id = %s and started_at >= %s", (TAN, t_first))
            print(f"old Gold rows from {FIRST} saved to {backup}")
            for tname, rows in bronze.items():
                if rows:
                    df = pd.DataFrame(rows)
                    n = bulk_insert(conn, tname, list(df.columns), tuples(df, list(df.columns)))
                    print(f"  {tname:24s} {n:>7,d}")
            for key, table in (("cgm", "cgm_readings"), ("watch", "watch_readings"), ("bp", "blood_pressure_readings"), ("food", "food_logs"), ("ex", "exercise_logs"),
                               ("sets", "exercise_sets"), ("sym", "symptom_logs"), ("wb", "wellbeing_logs"), ("medlog", "medication_log")):
                df = N[key]
                if not len(df):
                    continue
                meta = conn.execute("select column_name, data_type from information_schema.columns where table_schema='public' and table_name=%s", (table,)).fetchall()
                cols = [c for c, _ in meta if c in df.columns]
                ints_ = [c for c, t_ in meta if t_ in ("smallint", "integer", "bigint") and c in df.columns]
                df = df.copy()
                for c in ints_:
                    df[c] = pd.to_numeric(df[c], errors="coerce").round().astype("Int64").astype(object).where(df[c].notna(), None)
                n = bulk_insert(conn, table, cols, tuples(df, cols))
                print(f"  {table:24s} {n:>7,d}")
            tl = T_new.reset_index(names="bucket_start").replace({np.nan: None})
            tcols = ["user_id", "bucket_start", "local_date", "hour_of_day", "heart_rate_bpm", "hrv_rmssd_ms", "spo2_pct", "steps", "sleep_minutes", "steps_day_cum", "sleep_min_night_cum",
                     "hr_vs_baseline", "hrv_vs_baseline", "spo2_vs_baseline", "glucose_vs_baseline", "systolic_mmhg", "diastolic_mmhg", "glucose_mmol", "glucose_change_1h", "glucose_zone",
                     "meal_id", "meal_type", "food", "carbs_g", "protein_g", "fat_g", "sugar_g", "fibre_g", "sodium_mg", "exercise_id", "exercise_type", "exercise_intensity",
                     "medication_names", "dose_status", "meal_relation", "doses", "mood", "stress_self", "sleep_quality", "energy", "symptom_type", "symptom_severity", "symptom_duration_min",
                     "symptom_note", "at_work", "work_type"]
            tl = BG.ints(tl, ["hour_of_day", "heart_rate_bpm", "steps", "sleep_minutes", "steps_day_cum", "sleep_min_night_cum", "systolic_mmhg", "diastolic_mmhg",
                              "exercise_intensity", "mood", "stress_self", "sleep_quality", "energy", "symptom_severity", "symptom_duration_min"])
            print(f"  {'timeline_5min':24s} {bulk_insert(conn, 'timeline_5min', tcols, BG.rows_of(tl, tcols)):>7,d}")
            D2 = D_new.copy()
            D2.insert(0, "user_id", TAN)
            dcols = ["user_id"] + list(D_new.columns)
            for c in ["meals_n", "exercise_sessions_n", "doses_scheduled", "doses_taken", "doses_missed", "symptoms_n"]:
                D2[c] = D2[c].fillna(0)
            D2 = BG.ints(D2, ["steps_total", "resting_hr_bpm", "meals_n", "exercise_sessions_n", "doses_scheduled", "doses_taken", "doses_missed", "symptoms_n", "symptom_worst_severity"])
            D2["exercise_min"] = D2["exercise_min"].fillna(0).round(0).astype(int)
            for c in ["glucose_mean_mmol", "glucose_sd_mmol", "glucose_min_mmol", "glucose_max_mmol", "tir_pct", "tbr_pct", "tar_pct", "cgm_coverage_pct", "hr_worse_pct", "hrv_worse_pct",
                      "spo2_worse_pct", "glucose_worse_pct", "hrv_mean_ms", "spo2_mean_pct", "sleep_hours", "mood_avg", "stress_self_avg", "energy_avg", "sleep_quality_avg",
                      "carbs_g", "protein_g", "fat_g", "sugar_g", "fibre_g"]:
                D2[c] = D2[c].round(1)
            for c in ["bp_systolic_mean", "bp_diastolic_mean", "sodium_mg"]:
                D2[c] = D2[c].round(0)
            print(f"  {'daily_summary':24s} {bulk_insert(conn, 'daily_summary', dcols, BG.rows_of(D2, dcols)):>7,d}")
            mcols = ["food_log_id", "user_id", "pre_glucose_mmol", "peak_glucose_mmol", "minutes_to_peak", "rise_mmol", "glucose_1h_mmol", "glucose_2h_mmol", "iauc_2h_mmol_min",
                     "minutes_to_baseline", "steps_next_2h", "spike_flag"]
            print(f"  {'meal_response':24s} {bulk_insert(conn, 'meal_response', mcols, BG.rows_of(BG.ints(M_new, ['minutes_to_peak', 'minutes_to_baseline', 'steps_next_2h']), mcols)):>7,d}")
            xcols = ["exercise_log_id", "user_id", "hr_pre_bpm", "hr_avg_bpm", "hr_peak_bpm", "hr_30min_after_bpm", "glucose_pre_mmol", "glucose_min_during_mmol", "glucose_change_at_end",
                     "glucose_1h_mmol", "glucose_2h_mmol", "glucose_12h_mmol", "post_exercise_low_flag"]
            if len(X_new):
                print(f"  {'exercise_response':24s} {bulk_insert(conn, 'exercise_response', xcols, BG.rows_of(BG.ints(X_new, ['hr_pre_bpm', 'hr_avg_bpm', 'hr_peak_bpm', 'hr_30min_after_bpm']), xcols)):>7,d}")
            ecols = ["id", "user_id", "event_type", "started_at", "extreme_at", "ended_at", "duration_min", "start_glucose_mmol", "extreme_glucose_mmol", "rise_mmol", "ctx_meal_id",
                     "ctx_exercise_id", "ctx_dose_status", "ctx_heart_rate_bpm", "ctx_stress_self", "ctx_symptom_type"]
            print(f"  {'glucose_events':24s} {bulk_insert(conn, 'glucose_events', ecols, BG.rows_of(BG.ints(ev_new, ['duration_min', 'ctx_heart_rate_bpm', 'ctx_stress_self']), ecols)):>7,d}")
            ccols = ["user_id", "local_date", "adherence_7d_pct", "adherence_30d_pct", "doses_missed_7d", "longest_miss_streak_days", "top_miss_reason_30d", "most_missed_time",
                     "days_to_runout", "preventive_overdue", "preventive_due_soon", "hba1c_days_since", "open_questions_n", "next_appointment_at", "next_appointment_kind", "brief_status",
                     "open_flags_n", "top_flag_severity", "declining_metrics"]
            C2 = BG.ints(C_new, ["doses_missed_7d", "longest_miss_streak_days", "days_to_runout", "hba1c_days_since", "open_questions_n", "open_flags_n"])
            print(f"  {'care_summary':24s} {bulk_insert(conn, 'care_summary', ccols, BG.rows_of(C2, ccols)):>7,d}")
        print("done: committed.")


if __name__ == "__main__":
    main()
