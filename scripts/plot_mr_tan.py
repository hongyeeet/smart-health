#!/usr/bin/env python3
"""Draw showcase days of the generated Mr Tan dataset (glucose, heart rate, SpO2, steps with meals / exercise / doses / symptoms).
Usage: python scripts/plot_mr_tan.py [--days 12 34 43 62 75 88]  -> data/processed/demo_v2/plots/day_NN.png (git-ignored)"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import generate_mr_tan as G

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, nargs="*", default=[12, 34, 43, 62, 75, 88])
    ap.add_argument("--backup", default=str(ROOT / "data/processed/db_backup_2026-10-05"))
    a = ap.parse_args()
    g = G.Gen(G.load_real(a.backup)); g.run()
    out = ROOT / "data/processed/demo_v2/plots"; out.mkdir(parents=True, exist_ok=True)
    idx = g.idx
    s = pd.DataFrame({"g": g.glucose_final, "hr": g.hr_final, "spo2": g.spo2_final, "steps": g.steps_final, "asleep": g.asleep}, index=idx)
    for dn in a.days:
        d0 = g.dates[dn - 1]; d1 = d0 + pd.Timedelta(days=1)
        x = s[d0:d1]
        fig, ax = plt.subplots(3, 1, figsize=(13, 8.5), sharex=True, gridspec_kw={"height_ratios": [3, 2, 1.3]})
        ax[0].plot(x.index, x.g, color="#1b6ca8", lw=1.6)
        ax[0].axhspan(3.9, 10, color="#2e9d5b", alpha=0.08)
        ax[0].set_ylabel("glucose mmol/L"); ax[0].set_ylim(2.5, 22)
        ax[1].plot(x.index, x.hr, color="#c0392b", lw=1.2); ax[1].set_ylabel("heart rate"); ax1b = ax[1].twinx()
        ax1b.plot(x.index, x.spo2, color="#7d3c98", lw=0.8, alpha=0.7); ax1b.set_ylim(88, 100); ax1b.set_ylabel("SpO2 %", color="#7d3c98")
        ax[2].bar(x.index, x.steps, width=0.0035, color="#888"); ax[2].set_ylabel("steps / 5 min")
        for _, m in g.meals[(g.meals.start >= d0) & (g.meals.start < d1)].iterrows():
            for a_ in ax: a_.axvspan(m.start, m.end, color="#e67e22", alpha=0.25)
            ax[0].annotate(str(m.food)[:34], (m.start, 21), fontsize=7, rotation=90, va="top", color="#a04000")
        for _, e in g.ex[(g.ex.start >= d0) & (g.ex.start < d1)].iterrows():
            for a_ in ax: a_.axvspan(e.start, e.end, color="#16a085", alpha=0.22)
            ax[0].annotate(f"{e.type} I{e.intensity}", (e.start, 2.7), fontsize=7, color="#0e6655")
        for _, l in g.med_log[(g.med_log.scheduled_at >= d0) & (g.med_log.scheduled_at < d1)].iterrows():
            ax[0].axvline(l.scheduled_at, color="#c0392b" if l.status == "missed" else "#555", lw=0.6, ls=":")
        for _, y in g.symptoms[(g.symptoms.occurred_at >= d0) & (g.symptoms.occurred_at < d1)].iterrows():
            ax[1].annotate(y.symptom_type, (y.occurred_at, x.hr.max()), fontsize=7, color="#6c3483", rotation=90)
        asl = x.asleep > 0
        for a_ in ax: a_.fill_between(x.index, a_.get_ylim()[0], a_.get_ylim()[1], where=asl.values, color="#34495e", alpha=0.07)
        ax[0].set_title(f"Day {dn} ({d0.date()}, {d0.day_name()}), phase {G.phase_of(dn)}; real window starts day {g.real_day0}")
        fig.tight_layout(); fig.savefig(out / f"day_{dn:02d}.png", dpi=80); plt.close(fig)
    print("wrote", out)

main()
