#!/usr/bin/env python3
"""Draw the four report charts for Mr Tan from the Gold timeline (a prototype of the report visuals).

Usage:  python scripts/plot_report_charts.py --from 2026-09-26 --to 2026-10-02 [--out data/processed/demo_v2/plots/report_ID.png]

x axis is always time. Heart rate, SpO2 and glucose are continuous lines drawn with the person's fixed usual range (p50 line,
p25-p75 band, p05-p95 band; readings on the worse side of p05-p95 are marked). Blood pressure is a scatter. Every chart carries the
same overlay from the same table: meals (orange), exercise (green), scheduled work hours (grey), symptoms (purple), mood (dots),
doses (x = missed) and steps (bars).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from etl_common import connect

ROOT = Path(__file__).resolve().parents[1]
TAN = "dc48e209-5731-5b3d-89d9-986242c54368"


def q(conn, sql, params=()):
    cur = conn.execute(sql, params)
    df = pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])
    for c in df.columns:
        if df[c].dtype == object and len(df) and not isinstance(df[c].iloc[0], (str, list, dict, type(None))):
            try:
                df[c] = pd.to_numeric(df[c])
            except (TypeError, ValueError):
                pass
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="d0", default="2026-09-26")
    ap.add_argument("--to", dest="d1", default="2026-10-02")
    ap.add_argument("--out")
    a = ap.parse_args()
    tz = "Asia/Singapore"
    with connect() as conn:
        T = q(conn, "select * from timeline_5min where user_id = %s and local_date between %s and %s order by bucket_start", (TAN, a.d0, a.d1))
        B = q(conn, "select metric::text m, hour_of_day h, p05, p25, p50, p75, p95, anchor_end from baselines where user_id = %s", (TAN,))
        ml = q(conn, "select scheduled_at, status::text st from medication_log where user_id = %s and status = 'missed' and scheduled_at between %s and %s::date + 1", (TAN, a.d0, a.d1))
    T["t"] = pd.to_datetime(T.bucket_start, utc=True).dt.tz_convert(tz)
    T = T.set_index("t")
    fig, ax = plt.subplots(5, 1, figsize=(15, 13), sharex=True, gridspec_kw={"height_ratios": [3, 2.4, 3, 2.2, 1.2]})
    specs = [("heart_rate", "heart_rate_bpm", "Heart rate (bpm)", "#c0392b", "up"), ("spo2", "spo2_pct", "SpO2 (%)", "#7d3c98", "down"),
             ("glucose", "glucose_mmol", "Glucose (mmol/L)", "#1b6ca8", "up")]
    for i, (metric, col, label, color, bad) in enumerate(specs):
        x = T[col].astype(float)
        b = B[B.m == metric].set_index("h")
        h = T.hour_of_day.astype(int)
        for lo, hi, al in [("p05", "p95", 0.10), ("p25", "p75", 0.18)]:
            ax[i].fill_between(T.index, h.map(b[lo].astype(float)), h.map(b[hi].astype(float)), color=color, alpha=al, step="post", lw=0)
        ax[i].step(T.index, h.map(b["p50"].astype(float)), color=color, lw=0.8, alpha=0.6, where="post", ls="--")
        ax[i].plot(T.index, x, color=color, lw=1.3)
        p95, p05 = h.map(b["p95"].astype(float)), h.map(b["p05"].astype(float))
        worse = (x > p95) if bad == "up" else (x < p05)
        ax[i].scatter(T.index[worse.fillna(False)], x[worse.fillna(False)], s=5, color="black", zorder=3)
        ax[i].set_ylabel(label)
    if metric == "glucose":
        ax[2].axhspan(3.9, 10, color="#2e9d5b", alpha=0.05)
    # blood pressure scatter
    bp = T[T.systolic_mmhg.notna()]
    ax[3].scatter(bp.index, bp.systolic_mmhg.astype(float), color="#d35400", s=36, label="systolic", zorder=3)
    ax[3].scatter(bp.index, bp.diastolic_mmhg.astype(float), color="#2980b9", s=36, label="diastolic", zorder=3)
    for m, c in [("systolic", "#d35400"), ("diastolic", "#2980b9")]:
        r = B[B.m == m]
        if len(r):
            ax[3].axhspan(float(r.p05.iloc[0]), float(r.p95.iloc[0]), color=c, alpha=0.10)
    ax[3].set_ylabel("Blood pressure (mmHg)")
    ax[3].legend(loc="upper left", fontsize=8)
    # overlay on every chart: meals, exercise, work, symptoms
    def spans(mask, color, alpha):
        m = mask.to_numpy()
        i = 0
        while i < len(m):
            if m[i]:
                j = i
                while j + 1 < len(m) and m[j + 1]:
                    j += 1
                for a_ in ax[:4]:
                    a_.axvspan(T.index[i], T.index[j] + pd.Timedelta(minutes=5), color=color, alpha=alpha, lw=0)
                i = j + 1
            else:
                i += 1
    spans(T.at_work.notna(), "#7f8c8d", 0.07)
    spans(T.meal_id.notna(), "#e67e22", 0.30)
    spans(T.exercise_id.notna(), "#16a085", 0.30)
    spans(T.symptom_type.notna(), "#8e44ad", 0.18)
    for t, r in T[T.meal_id.notna() & (T.meal_id != T.meal_id.shift())].iterrows():
        ax[2].annotate(str(r.food)[:26], (t, ax[2].get_ylim()[1]), fontsize=6.5, rotation=90, va="top", ha="right", color="#a04000")
    for t, r in T[T.symptom_type.notna() & (T.symptom_type != T.symptom_type.shift())].iterrows():
        ax[0].annotate(r.symptom_type + (": " + str(r.symptom_note)[:40] if r.symptom_note else ""), (t, ax[0].get_ylim()[1]), fontsize=6.5, rotation=90, va="top", ha="right", color="#6c3483")
    for t in pd.to_datetime(ml.scheduled_at, utc=True).dt.tz_convert(tz):
        ax[2].scatter([t], [0.04], marker="x", color="red", s=40, zorder=4, transform=ax[2].get_xaxis_transform())
    mood = T[T.mood.notna()]
    ax[4].scatter(mood.index, mood.mood.astype(float), color="#27ae60", s=30, label="mood (1-5)")
    st = T[T.stress_self.notna()]
    ax[4].scatter(st.index, st.stress_self.astype(float), color="#c0392b", s=30, marker="s", label="stress (1-5)")
    ax4b = ax[4].twinx()
    ax4b.bar(T.index, T.steps.fillna(0).astype(float), width=0.0033, color="#7f8c8d", alpha=0.6)
    ax4b.set_ylabel("steps / 5 min", fontsize=8)
    ax[4].legend(loc="upper left", fontsize=7, ncol=2)
    ax[4].set_ylim(0.5, 5.5)
    ax[0].set_title(f"Mr Tan, {a.d0} to {a.d1}  |  dashed = usual median, bands = p25-p75 and p05-p95, black dots = worse than the usual range  |  "
                    "orange meals, green exercise, grey work hours, purple symptoms, red x = missed dose", fontsize=9)
    fig.tight_layout()
    out = Path(a.out) if a.out else ROOT / "data" / "processed" / "demo_v2" / "plots" / f"report_{a.d0}_{a.d1}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=75)
    print("wrote", out)


if __name__ == "__main__":
    main()
