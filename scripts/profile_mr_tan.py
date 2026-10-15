#!/usr/bin/env python3
"""Profile the demo patient "Mr Tan" (CGMacros participant 046) from the database, before the v2 reset.

Usage:  python scripts/profile_mr_tan.py [--from-backup data/processed/db_backup_2026-10-05]

Reads his rows (live database by default, or the gzip CSV backup) and writes
  data/processed/mr_tan_profile.json   numbers the demo-data generator is fitted on (git-ignored)
and prints a summary. It only reads. "Real" means taken from the CGMacros files (the meal description is
'CGMacros dataset meal', glucose/heart-rate rows from the sensors); everything else in his history was
simulated in E1-4 and is NOT used as a model for the new data.
"""
import argparse
import gzip
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parents[1]
TZ = "Asia/Singapore"
TAN = "dc48e209-5731-5b3d-89d9-986242c54368"
LOW, HIGH, VERY_HIGH = 3.9, 10.0, 13.9


def load(table, backup):
    if backup:
        with gzip.open(Path(backup) / f"{table}.csv.gz", "rt", encoding="utf-8") as f:
            df = pd.read_csv(f)
        if "user_id" in df.columns:
            df = df[df["user_id"] == TAN]
        return df
    from etl_common import connect
    with connect() as conn:
        return pd.read_sql(f"select * from {table} where user_id = %(u)s" if table not in ("meals",) else "select * from meals where user_id = %(u)s",
                           conn, params={"u": TAN})


def five_min(series_df, tcol, vcol):
    s = series_df.copy()
    s[tcol] = pd.to_datetime(s[tcol], utc=True)
    s["b"] = s[tcol].dt.floor("5min")
    return s.groupby("b")[vcol].mean()


def tir(values):
    v = np.asarray(values, dtype=float)
    return {
        "n": int(len(v)), "mean": round(float(v.mean()), 2), "sd": round(float(v.std()), 2),
        "cv_pct": round(float(100 * v.std() / v.mean()), 1),
        "min": round(float(v.min()), 1), "max": round(float(v.max()), 1),
        "tir_pct": round(float(100 * ((v >= LOW) & (v <= HIGH)).mean()), 1),
        "below_pct": round(float(100 * (v < LOW).mean()), 1),
        "above_pct": round(float(100 * (v > HIGH).mean()), 1),
        "very_high_pct": round(float(100 * (v > VERY_HIGH).mean()), 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-backup")
    ap.add_argument("--out", default=str(ROOT / "data/processed/mr_tan_profile.json"))
    a = ap.parse_args()
    bk = a.from_backup

    gl = load("glucose_readings", bk)
    hs = load("health_samples", bk)
    meals = load("meals", bk)
    items = pd.read_csv(gzip.open(Path(bk) / "meal_items.csv.gz", "rt", encoding="utf-8")) if bk else None
    if items is None:
        from etl_common import connect
        with connect() as conn:
            items = pd.read_sql("select mi.* from meal_items mi join meals m on m.id = mi.meal_id where m.user_id = %(u)s", conn, params={"u": TAN})

    out = {"user_id": TAN, "timezone": TZ}

    # ---------------------------------------------------------------- glucose (Dexcom G6, native 5 minutes)
    cgm = gl[(gl["context"] == "cgm") & (gl["device"] == "dexcom_g6") & (gl["quality_ok"].astype(str).str.lower().isin(["true", "1"]))]
    g5 = five_min(cgm, "measured_at", "value_mmol")
    g5.index = g5.index.tz_convert(TZ)
    out["window"] = {"first": str(g5.index.min()), "last": str(g5.index.max()), "buckets_5min": int(len(g5)),
                     "days": round(len(g5) / 288, 2)}
    out["glucose_dexcom"] = tir(g5.values)
    libre = gl[(gl["context"] == "cgm") & (gl["device"] == "libre_pro")]
    out["glucose_libre_for_comparison"] = tir(libre["value_mmol"].values)

    hour = g5.groupby(g5.index.hour)
    out["glucose_by_local_hour"] = {int(h): {"median": round(float(g.median()), 2), "p25": round(float(g.quantile(.25)), 2),
                                             "p75": round(float(g.quantile(.75)), 2)} for h, g in hour}
    daily = g5.groupby(g5.index.date).agg(["mean", "min", "max", "count"])
    out["glucose_daily"] = {str(d): {"mean": round(float(r["mean"]), 2), "min": round(float(r["min"]), 1),
                                     "max": round(float(r["max"]), 1), "n": int(r["count"])} for d, r in daily.iterrows()}

    # ---------------------------------------------------------------- real meals and the glucose response to each
    meals = meals[~meals["description"].fillna("").str.startswith("Simulated")].copy()
    meals["eaten_at"] = pd.to_datetime(meals["eaten_at"], utc=True).dt.tz_convert(TZ)
    agg = items.groupby("meal_id")[["carbs_g", "protein_g", "fat_g", "fibre_g", "kcal", "sugar_g", "sodium_mg"]].sum(min_count=1)
    meals = meals.merge(agg, left_on="id", right_index=True, how="left").sort_values("eaten_at")
    rows = []
    for _, m in meals.iterrows():
        t0 = m["eaten_at"].floor("5min")
        pre = g5[(g5.index >= t0 - pd.Timedelta(minutes=30)) & (g5.index <= t0)]
        post = g5[(g5.index > t0) & (g5.index <= t0 + pd.Timedelta(hours=3))]
        if len(pre) < 3 or len(post) < 20:
            resp = None
        else:
            base = float(pre.mean())
            peak = float(post.max())
            tpeak = (post.idxmax() - t0).total_seconds() / 60
            two_h = post[(post.index > t0 + pd.Timedelta(minutes=110)) & (post.index <= t0 + pd.Timedelta(minutes=130))]
            above = (post - base).clip(lower=0)
            iauc = float(above.sum() * 5)  # mmol/L x minutes
            back = post[(post.index > post.idxmax()) & (post <= base + 0.3)]
            resp = {"pre": round(base, 2), "peak": round(peak, 2), "rise": round(peak - base, 2), "min_to_peak": round(tpeak),
                    "glucose_2h": round(float(two_h.mean()), 2) if len(two_h) else None, "iauc_3h": round(iauc, 1),
                    "min_to_baseline": round((back.index[0] - t0).total_seconds() / 60) if len(back) else None}
        rows.append({"id": m["id"], "eaten_at": str(m["eaten_at"]), "type": m["meal_type"],
                     "hour": int(m["eaten_at"].hour), "carbs_g": m["carbs_g"], "protein_g": m["protein_g"], "fat_g": m["fat_g"],
                     "fibre_g": m["fibre_g"], "kcal": m["kcal"], "response": resp})
    out["real_meals"] = rows
    ok = [r for r in rows if r["response"] and r["carbs_g"] is not None and not pd.isna(r["carbs_g"])]
    if len(ok) >= 5:
        x = np.array([r["carbs_g"] - (0 if pd.isna(r["fibre_g"]) else r["fibre_g"]) for r in ok], dtype=float)
        y = np.array([r["response"]["rise"] for r in ok], dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        r = float(np.corrcoef(x, y)[0, 1])
        out["meal_response_fit"] = {"n": len(ok), "rise_per_net_carb_g": round(float(slope), 4), "intercept": round(float(intercept), 2),
                                    "pearson_r": round(r, 2), "mean_rise": round(float(y.mean()), 2),
                                    "mean_min_to_peak": round(float(np.mean([q["response"]["min_to_peak"] for q in ok])))}

    # ---------------------------------------------------------------- heart rate and active energy (Fitbit Sense, in CGMacros)
    hr = hs[hs["metric"] == "heart_rate"]
    h5 = five_min(hr, "start_at", "value")
    h5.index = h5.index.tz_convert(TZ)
    out["heart_rate"] = {"buckets_5min": int(len(h5)), "mean": round(float(h5.mean()), 1), "sd": round(float(h5.std()), 1),
                         "p10": round(float(h5.quantile(.10)), 1), "p90": round(float(h5.quantile(.90)), 1),
                         "min": round(float(h5.min()), 1), "max": round(float(h5.max()), 1),
                         "by_local_hour": {int(h): {"median": round(float(g.median()), 1), "p25": round(float(g.quantile(.25)), 1),
                                                    "p75": round(float(g.quantile(.75)), 1)} for h, g in h5.groupby(h5.index.hour)}}
    ae = hs[hs["metric"] == "active_energy"]
    out["active_energy_kcal_per_min"] = {"mean": round(float(ae["value"].mean()), 2), "p90": round(float(ae["value"].quantile(.9)), 2)}

    # ---------------------------------------------------------------- joint HR-glucose check on the real days
    both = pd.concat([g5.rename("g"), h5.rename("h")], axis=1).dropna()
    out["real_overlap_buckets"] = int(len(both))
    out["corr_glucose_hr_5min"] = round(float(both["g"].corr(both["h"])), 2)

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    g = out["glucose_dexcom"]
    print("window", out["window"])
    print("glucose (Dexcom):", g)
    print("glucose (Libre):", out["glucose_libre_for_comparison"])
    print("meal fit:", out.get("meal_response_fit"))
    print("heart rate:", {k: v for k, v in out["heart_rate"].items() if k != "by_local_hour"})
    print("wrote", a.out)


if __name__ == "__main__":
    main()
