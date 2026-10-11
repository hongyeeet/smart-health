#!/usr/bin/env python3
"""Build the v2 Gold layer for Mr Tan from the Silver tables, and seed the care tables the Gold layer reads.

Usage:  python scripts/build_gold_v2.py          (rebuilds everything for the demo patient; safe to run again)

Order: timeline_5min -> baselines -> *_vs_baseline -> daily_summary -> meal_response -> exercise_response -> glucose_events
       -> care tables (doctor_questions, refill_forecasts, interaction_alerts, notifications) -> clinical_flags
       -> care_summary -> pattern_candidates

Rules implemented (docs/specs/data-model-v2.md section 5):
  baseline  usual range by hour of day from the first 14 days with data (blood pressure: the first 5 readings), percentiles
            p05..p95, buckets inside logged exercise left out of the heart-rate and HRV baselines; it applies from the day after
            its window ends and never moves afterwards
  flag      a day is flagged for a metric when more than 20% of its readings are on the WORSE side of the usual range (above p95 for
            heart rate and glucose, below p05 for HRV and SpO2; getting better is not flagged); a metric is declining when
            3 of the last 5 days are flagged (starting values, not clinically validated)
The timeline is built here in Python; the SQL view v_timeline_5min described in the spec is not written yet.
"""
import json
import sys
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etl_common import bulk_insert, connect, uid  # noqa: E402

TAN = "dc48e209-5731-5b3d-89d9-986242c54368"
VERY_HIGH = 13.9
METRICS = {"heart_rate": "heart_rate_bpm", "hrv": "hrv_rmssd_ms", "spo2": "spo2_pct", "glucose": "glucose_mmol"}
VS_COL = {"heart_rate": "hr_vs_baseline", "hrv": "hrv_vs_baseline", "spo2": "spo2_vs_baseline", "glucose": "glucose_vs_baseline"}
WORSE_FLAG_PCT, DECLINE_DAYS, DECLINE_WINDOW = 20.0, 3, 5


def q(conn, sql, params=()):
    cur = conn.execute(sql, params)
    cols = [d.name for d in cur.description]
    df = pd.DataFrame(cur.fetchall(), columns=cols)
    for c in df.columns:                                   # Postgres numeric comes back as Decimal
        s = df[c]
        if s.dtype == object and any(isinstance(v, Decimal) for v in s.dropna().head(5)):
            df[c] = s.map(lambda v: float(v) if isinstance(v, Decimal) else v)
    return df


def py(v):
    if v is None or v is pd.NaT:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return None if np.isnan(v) else float(v)
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, (list, dict)):
        return json.dumps(v, default=str) if isinstance(v, dict) else v
    return v


def ints(df, cols):
    """Integer columns that may contain gaps: None or int (never 120.0), so COPY accepts them."""
    df = df.copy()
    for c in cols:
        df[c] = pd.Series([None if (v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NaT) else int(round(v)) for v in df[c]], index=df.index, dtype=object)
    return df


def rows_of(df, cols):
    return [tuple(py(v) for v in r) for r in df[cols].itertuples(index=False, name=None)]


def bucket(ts, tz):
    return pd.to_datetime(ts, utc=True).dt.tz_convert(tz).dt.floor("5min")


def pct(a, p):
    a = np.asarray(a, dtype=float)
    a = a[~np.isnan(a)]
    return float(np.percentile(a, p)) if len(a) else np.nan


# ============================================================================================= timeline
def build_timeline(ctx):
    prof, tz = ctx["profile"], ctx["tz"]
    wr, cg, bp = ctx["watch"], ctx["cgm"], ctx["bp"]
    wr = wr.assign(b=bucket(wr.recorded_at, tz)).set_index("b")
    cg = cg.assign(b=bucket(cg.recorded_at, tz))
    start = min(wr.index.min(), cg.b.min())
    end = max(wr.index.max(), cg.b.max())
    idx = pd.date_range(start, end, freq="5min")
    N = len(idx)
    T = pd.DataFrame(index=idx)
    T["user_id"] = TAN
    T["local_date"] = idx.date
    T["hour_of_day"] = idx.hour
    for c in ["heart_rate_bpm", "hrv_rmssd_ms", "spo2_pct", "steps", "sleep_minutes"]:
        T[c] = wr[c].reindex(idx)
    steps0 = T.steps.fillna(0)
    T["steps_day_cum"] = steps0.groupby(T.local_date).cumsum()
    T.loc[T.steps.isna(), "steps_day_cum"] = np.nan
    # sleep night: running total since 18:00 local (the "night" a bucket belongs to starts at 18:00)
    night = (idx - pd.Timedelta(hours=18)).date
    T["sleep_min_night_cum"] = T.sleep_minutes.fillna(0).groupby(night).cumsum()
    T.loc[T.sleep_minutes.isna(), "sleep_min_night_cum"] = np.nan
    # blood pressure: only in the bucket of a reading
    T["systolic_mmhg"] = np.nan
    T["diastolic_mmhg"] = np.nan
    b = bp.assign(b=bucket(bp.recorded_at, tz))
    for _, r in b.iterrows():
        if r.b in T.index:
            T.at[r.b, "systolic_mmhg"] = r.systolic_mmhg
            T.at[r.b, "diastolic_mmhg"] = r.diastolic_mmhg
    # glucose
    g = cg.groupby("b").glucose_mmol.mean().astype(float).reindex(idx)
    T["glucose_mmol"] = g.round(1)
    T["glucose_change_1h"] = (T.glucose_mmol - T.glucose_mmol.shift(12)).round(1)
    lo, hi = float(prof.glucose_target_low), float(prof.glucose_target_high)
    z = np.select([T.glucose_mmol < lo, T.glucose_mmol > VERY_HIGH, T.glucose_mmol > hi], ["low", "very_high", "high"], "in_range").astype(object)
    z[T.glucose_mmol.isna().to_numpy()] = None
    T["glucose_zone"] = z

    def span(start_s, end_s):
        s = pd.to_datetime(start_s, utc=True).tz_convert(tz)
        e = pd.to_datetime(end_s, utc=True).tz_convert(tz)
        i0 = int(np.clip(idx.searchsorted(s.floor("5min")), 0, N))
        i1 = int(np.clip(idx.searchsorted(e, side="left"), 0, N))      # first bucket starting at or after the end
        return i0, max(i1, i0 + 1)

    # food (only while eating; later start wins)
    for c in ["meal_id", "meal_type", "food", "carbs_g", "protein_g", "fat_g", "sugar_g", "fibre_g", "sodium_mg"]:
        T[c] = None
    food = ctx["food"].sort_values("start_at")
    cols = {c: T.columns.get_loc(c) for c in ["meal_id", "meal_type", "food", "carbs_g", "protein_g", "fat_g", "sugar_g", "fibre_g", "sodium_mg"]}
    for r in food.itertuples():
        i0, i1 = span(r.start_at, r.end_at)
        for c, j in cols.items():
            T.iloc[i0:i1, j] = r.id if c == "meal_id" else (None if c not in ("meal_type", "food") and pd.isna(getattr(r, c)) else getattr(r, c))
    # exercise
    for c in ["exercise_id", "exercise_type", "exercise_intensity"]:
        T[c] = None
    ex_mask = np.zeros(N, bool)
    for r in ctx["ex"].sort_values("start_at").itertuples():
        i0, i1 = span(r.start_at, r.end_at)
        T.iloc[i0:i1, T.columns.get_loc("exercise_id")] = r.id
        T.iloc[i0:i1, T.columns.get_loc("exercise_type")] = r.type
        if pd.notna(r.intensity):  # an unrated workout keeps exercise_intensity null (not rated), it is still in exercise_id and the mask
            T.iloc[i0:i1, T.columns.get_loc("exercise_intensity")] = int(r.intensity)
        ex_mask[i0:i1] = True
    ctx["ex_mask"] = ex_mask
    # medication: the bucket of the dose (taken time if taken, otherwise the scheduled time)
    ml = ctx["medlog"]
    names = ctx["meds"].set_index("id").name
    rel = ctx["schedule"].set_index("id").meal_relation
    qty = ctx["schedule"].set_index("id").quantity
    T["medication_names"] = None
    T["dose_status"] = None
    T["meal_relation"] = None
    T["doses"] = None
    rank = {"taken": 1, "late": 2, "skipped": 3, "missed": 4}
    per = {}
    for r in ml[ml.status != "pending"].itertuples():
        when = r.taken_at if r.status == "taken" else r.scheduled_at
        outcome = r.status
        if r.status == "taken" and pd.notna(r.scheduled_at) and (r.taken_at - r.scheduled_at) > pd.Timedelta(minutes=60):
            outcome = "late"
        t = pd.to_datetime(when, utc=True).tz_convert(tz).floor("5min")
        if t not in T.index:
            continue
        per.setdefault(t, []).append(dict(medication=names.get(r.medication_id), quantity=float(qty.get(r.schedule_id, 1)) if r.schedule_id else 1.0,
                                          status=outcome, meal_relation=str(rel.get(r.schedule_id, "na")) if r.schedule_id else "na"))
    for t, lst in per.items():
        i = T.index.get_loc(t)
        T.iat[i, T.columns.get_loc("medication_names")] = ", ".join(sorted({d["medication"] for d in lst}))
        T.iat[i, T.columns.get_loc("dose_status")] = max((d["status"] for d in lst), key=lambda s: rank[s])
        rs = {d["meal_relation"] for d in lst}
        T.iat[i, T.columns.get_loc("meal_relation")] = rs.pop() if len(rs) == 1 else "mixed"
        T.iat[i, T.columns.get_loc("doses")] = json.dumps(lst)
    # wellbeing (only the bucket where logged)
    for c in ["mood", "stress_self", "sleep_quality", "energy"]:
        T[c] = np.nan
    for r in ctx["wb"].itertuples():
        t = pd.to_datetime(r.recorded_at, utc=True).tz_convert(tz).floor("5min")
        if t in T.index:
            for c in ["mood", "stress_self", "sleep_quality", "energy"]:
                v = getattr(r, c)
                if pd.notna(v):
                    T.at[t, c] = v
    # symptoms (across their duration; the more severe one wins)
    for c in ["symptom_type", "symptom_note"]:
        T[c] = None
    for c in ["symptom_severity", "symptom_duration_min"]:
        T[c] = np.nan
    for r in ctx["sym"].sort_values("severity").itertuples():
        s = pd.to_datetime(r.occurred_at, utc=True).tz_convert(tz).floor("5min")
        n = int(np.ceil(r.duration_min / 5)) if pd.notna(r.duration_min) else 1
        i0 = idx.searchsorted(s)
        i1 = min(i0 + max(n, 1), N)
        if i0 >= N:
            continue
        T.iloc[i0:i1, T.columns.get_loc("symptom_type")] = r.symptom_type
        T.iloc[i0:i1, T.columns.get_loc("symptom_severity")] = r.severity
        T.iloc[i0:i1, T.columns.get_loc("symptom_duration_min")] = r.duration_min
        T.iloc[i0:i1, T.columns.get_loc("symptom_note")] = r.note
    # scheduled work hours
    T["at_work"] = None
    T["work_type"] = None
    days = list(prof.work_days) if prof.work_days is not None else []
    if days and prof.work_start is not None:
        wd = idx.weekday + 1
        tod = idx.hour * 60 + idx.minute
        s_, e_ = prof.work_start.hour * 60 + prof.work_start.minute, prof.work_end.hour * 60 + prof.work_end.minute
        if e_ > s_:
            on = np.isin(wd, days) & (tod >= s_) & (tod < e_)
        else:
            prev = np.isin(((idx - pd.Timedelta(days=1)).weekday + 1), days)
            on = (np.isin(wd, days) & (tod >= s_)) | (prev & (tod < e_))
        T.loc[on, "at_work"] = True
        T.loc[on, "work_type"] = prof.work_type
    return T


# ============================================================================================= baselines
def build_baselines(T, ctx):
    rows = []
    ex_mask = ctx["ex_mask"]
    dates = pd.Series(T.local_date.to_numpy(), index=T.index)
    for metric, col in METRICS.items():
        v = T[col]
        ok = v.notna().to_numpy()
        if metric in ("heart_rate", "hrv"):
            ok = ok & ~ex_mask
        if not ok.any():
            continue
        first = dates[ok].min()
        a_start, a_end = first, first + pd.Timedelta(days=13).to_pytimedelta()
        win = ok & (dates >= a_start).to_numpy() & (dates <= a_end).to_numpy()
        for h in range(24):
            m = win & (T.hour_of_day.to_numpy() == h)
            x = v.to_numpy()[m]
            if len(x) < 10:
                continue
            nd = int(dates[m].nunique())
            if nd < 5:
                continue
            rows.append(dict(user_id=TAN, anchor_start=a_start, anchor_end=a_end, metric=metric, hour_of_day=h,
                             p05=pct(x, 5), p25=pct(x, 25), p50=pct(x, 50), p75=pct(x, 75), p95=pct(x, 95), n_days=nd, n_points=len(x),
                             reset_reason="first_14_days"))
    bp = ctx["bp"].sort_values("recorded_at").head(5)
    if len(bp) == 5:
        d = pd.to_datetime(bp.recorded_at, utc=True).dt.tz_convert(ctx["tz"]).dt.date
        for metric, col in [("systolic", "systolic_mmhg"), ("diastolic", "diastolic_mmhg")]:
            x = bp[col].to_numpy(float)
            rows.append(dict(user_id=TAN, anchor_start=d.min(), anchor_end=d.max(), metric=metric, hour_of_day=None,
                             p05=pct(x, 5), p25=pct(x, 25), p50=pct(x, 50), p75=pct(x, 75), p95=pct(x, 95), n_days=int(d.nunique()), n_points=5,
                             reset_reason="first_14_days"))
    B = pd.DataFrame(rows)
    for c in ["p05", "p25", "p50", "p75", "p95"]:
        B[c] = B[c].astype(float).round(1)
    B["id"] = [str(uid("v2", "baseline", r.metric, r.hour_of_day, r.anchor_start)) for r in B.itertuples()]
    return B


def apply_vs_baseline(T, B):
    ctx_b = {}
    for metric in METRICS:
        sub = B[B.metric == metric]
        arr50 = np.full(24, np.nan)
        arr05 = np.full(24, np.nan)
        arr95 = np.full(24, np.nan)
        for r in sub.itertuples():
            arr50[int(r.hour_of_day)], arr05[int(r.hour_of_day)], arr95[int(r.hour_of_day)] = r.p50, r.p05, r.p95
        applies = pd.Timestamp(sub.anchor_end.max()).date() if len(sub) else None
        ctx_b[metric] = (arr05, arr50, arr95, applies)
        col = METRICS[metric]
        if applies is None:
            T[VS_COL[metric]] = np.nan
            continue
        after = (T.local_date.to_numpy() > applies)
        val = T[col].to_numpy(float) - arr50[T.hour_of_day.to_numpy()]
        T[VS_COL[metric]] = np.where(after, val, np.nan)
    return ctx_b


# ============================================================================================= daily summary
def build_daily(T, ctx, ctx_b):
    prof = ctx["profile"]
    lo, hi = float(prof.glucose_target_low), float(prof.glucose_target_high)
    D = pd.DataFrame(index=sorted(set(T.local_date)))
    grp = T.groupby("local_date")
    g = T.glucose_mmol
    D["glucose_mean_mmol"] = grp.glucose_mmol.mean()
    D["glucose_sd_mmol"] = grp.glucose_mmol.std()
    D["glucose_min_mmol"] = grp.glucose_mmol.min()
    D["glucose_max_mmol"] = grp.glucose_mmol.max()
    valid = g.notna()
    for name, cond in [("tir_pct", (g >= lo) & (g <= hi)), ("tbr_pct", g < lo), ("tar_pct", g > hi)]:
        D[name] = (cond & valid).groupby(T.local_date).sum() / valid.groupby(T.local_date).sum() * 100
    D["cgm_coverage_pct"] = valid.groupby(T.local_date).sum() / grp.size() * 100
    D["steps_total"] = grp.steps.sum(min_count=1)
    # sleep: the night that ends on this date (18:00 the evening before to 12:00)
    t = T.index
    key = np.where(t.hour >= 18, (t + pd.Timedelta(days=1)).date, np.where(t.hour < 12, t.date, None))
    sl = T.sleep_minutes.groupby(key).sum(min_count=1)
    D["sleep_hours"] = pd.Series({k: v / 60 for k, v in sl.items() if k is not None}).reindex(D.index)
    awake_hr = T.heart_rate_bpm.where(T.sleep_minutes.fillna(0) == 0)
    D["resting_hr_bpm"] = awake_hr.groupby(T.local_date).quantile(0.10)
    D["hrv_mean_ms"] = grp.hrv_rmssd_ms.mean()
    D["spo2_mean_pct"] = grp.spo2_pct.mean()
    D["bp_systolic_mean"] = grp.systolic_mmhg.mean()
    D["bp_diastolic_mean"] = grp.diastolic_mmhg.mean()
    tz = ctx["tz"]
    f = ctx["food"].assign(d=pd.to_datetime(ctx["food"].start_at, utc=True).dt.tz_convert(tz).dt.date)
    fg = f.groupby("d")
    D["meals_n"] = fg.size()
    for c in ["carbs_g", "protein_g", "fat_g", "sugar_g", "fibre_g", "sodium_mg"]:
        D[c] = fg[c].sum(min_count=1)
    e = ctx["ex"].assign(d=pd.to_datetime(ctx["ex"].start_at, utc=True).dt.tz_convert(tz).dt.date,
                         mins=lambda x: (x.end_at - x.start_at).dt.total_seconds() / 60)
    D["exercise_min"] = e.groupby("d").mins.sum()
    D["exercise_sessions_n"] = e.groupby("d").size()
    presc = set(ctx["meds"][ctx["meds"].kind == "prescription"].id)
    m = ctx["medlog"]
    m = m[(m.status != "pending") & m.scheduled_at.notna() & m.medication_id.isin(presc)].assign(d=lambda x: pd.to_datetime(x.scheduled_at, utc=True).dt.tz_convert(tz).dt.date)
    D["doses_scheduled"] = m.groupby("d").size()
    D["doses_taken"] = m[m.status == "taken"].groupby("d").size()
    D["doses_missed"] = m[m.status == "missed"].groupby("d").size()
    s = ctx["sym"].assign(d=pd.to_datetime(ctx["sym"].occurred_at, utc=True).dt.tz_convert(tz).dt.date)
    D["symptoms_n"] = s.groupby("d").size()
    D["symptom_worst_severity"] = s.groupby("d").severity.max()
    w = ctx["wb"].assign(d=pd.to_datetime(ctx["wb"].recorded_at, utc=True).dt.tz_convert(tz).dt.date)
    for src, dst in [("mood", "mood_avg"), ("stress_self", "stress_self_avg"), ("energy", "energy_avg"), ("sleep_quality", "sleep_quality_avg")]:
        D[dst] = w.groupby("d")[src].mean()
    days = list(prof.work_days) if prof.work_days is not None else []
    D["work_day"] = [(pd.Timestamp(d).weekday() + 1) in days for d in D.index]
    # share of readings on the worse side of the usual range (above p95 for heart rate and glucose, below p05 for HRV and SpO2)
    for metric, col in METRICS.items():
        arr05, arr50, arr95, applies = ctx_b[metric]
        name = {"heart_rate": "hr", "hrv": "hrv", "spo2": "spo2", "glucose": "glucose"}[metric] + "_worse_pct"
        if applies is None:
            D[name] = np.nan
            continue
        v = T[col].to_numpy(float)
        h = T.hour_of_day.to_numpy()
        ok = ~np.isnan(v) & ~np.isnan(arr05[h])
        if metric in ("heart_rate", "hrv"):
            ok = ok & ~ctx["ex_mask"]
        worse = ok & ((v > arr95[h]) if metric in ("heart_rate", "glucose") else (v < arr05[h]))
        o = pd.Series(worse.astype(float), index=T.index).groupby(T.local_date).sum()
        n = pd.Series(ok.astype(float), index=T.index).groupby(T.local_date).sum()
        res = (o / n.replace(0, np.nan) * 100)
        res[[d for d in res.index if d <= applies]] = np.nan
        D[name] = res
    flagged = {}
    for metric, nm in [("heart_rate", "hr"), ("hrv", "hrv"), ("spo2", "spo2"), ("glucose", "glucose")]:
        flagged[metric] = (D[nm + "_worse_pct"] > WORSE_FLAG_PCT).astype(int)
    decl = []
    for i in range(len(D)):
        lst = []
        for metric in flagged:
            last = flagged[metric].iloc[max(0, i - DECLINE_WINDOW + 1):i + 1]
            if last.sum() >= DECLINE_DAYS:
                lst.append(metric)
        decl.append(lst)
    D["declining_metrics"] = decl
    D["data_quality"] = [json.dumps({"cgm_coverage_pct": round(float(a), 1) if pd.notna(a) else None,
                                     "watch_buckets": int(b), "hrv_points": int(c)}) for a, b, c in
                         zip(D.cgm_coverage_pct, T.groupby("local_date").heart_rate_bpm.count().reindex(D.index).fillna(0),
                             T.groupby("local_date").hrv_rmssd_ms.count().reindex(D.index).fillna(0))]
    D.index.name = "local_date"
    return D.reset_index()


# ============================================================================================= responses and events
def meal_responses(T, ctx):
    prof = ctx["profile"]
    hi = float(prof.glucose_target_high)
    tz = ctx["tz"]
    g = T.glucose_mmol
    rows = []
    for r in ctx["food"].itertuples():
        t0 = pd.to_datetime(r.start_at, utc=True).tz_convert(tz).floor("5min")
        pre = g[(g.index >= t0 - pd.Timedelta(minutes=30)) & (g.index <= t0)].dropna()
        post = g[(g.index > t0) & (g.index <= t0 + pd.Timedelta(hours=3))].dropna()
        if len(pre) < 3 or len(post) < 20:
            continue
        base = float(pre.mean())
        peak = float(post.max())
        tpk = int((post.idxmax() - t0).total_seconds() / 60)
        def at(mins):
            x = g[(g.index >= t0 + pd.Timedelta(minutes=mins - 5)) & (g.index <= t0 + pd.Timedelta(minutes=mins + 5))].dropna()
            return float(x.mean()) if len(x) else np.nan
        two = g[(g.index > t0) & (g.index <= t0 + pd.Timedelta(hours=2))].dropna()
        iauc = float(((two - base).clip(lower=0) * 5).sum())
        back = g[(g.index > post.idxmax()) & (g.index <= t0 + pd.Timedelta(hours=6)) & (g <= base + 0.3)]
        steps2 = float(T.steps[(T.index >= t0) & (T.index < t0 + pd.Timedelta(hours=2))].sum())
        rows.append(dict(food_log_id=r.id, user_id=TAN, pre_glucose_mmol=round(base, 1), peak_glucose_mmol=round(peak, 1), minutes_to_peak=tpk,
                         rise_mmol=round(max(peak - base, 0.0), 1), glucose_1h_mmol=at(60), glucose_2h_mmol=at(120), iauc_2h_mmol_min=round(iauc, 1),
                         minutes_to_baseline=int((back.index[0] - t0).total_seconds() / 60) if len(back) else None, steps_next_2h=int(steps2),
                         spike_flag=bool((peak - base) >= 2.5 or peak > hi)))
    M = pd.DataFrame(rows)
    for c in ["glucose_1h_mmol", "glucose_2h_mmol"]:
        M[c] = M[c].round(1)
    return M


def exercise_responses(T, ctx):
    lo = float(ctx["profile"].glucose_target_low)
    tz = ctx["tz"]
    g, hr = T.glucose_mmol, T.heart_rate_bpm
    rows = []
    for r in ctx["ex"].itertuples():
        s = pd.to_datetime(r.start_at, utc=True).tz_convert(tz).floor("5min")
        e = pd.to_datetime(r.end_at, utc=True).tz_convert(tz).floor("5min")
        during = (T.index >= s) & (T.index < e + pd.Timedelta(minutes=5))
        hr_pre = hr[(T.index >= s - pd.Timedelta(minutes=30)) & (T.index < s)].mean()
        gpre = g[(T.index >= s - pd.Timedelta(minutes=15)) & (T.index <= s)].mean()
        def at(t):
            x = g[(T.index >= t - pd.Timedelta(minutes=5)) & (T.index <= t + pd.Timedelta(minutes=5))].dropna()
            return float(x.mean()) if len(x) else np.nan
        after = (T.index > e) & (T.index <= e + pd.Timedelta(hours=4))
        gmin_after = g[after].min()
        rows.append(dict(exercise_log_id=r.id, user_id=TAN, hr_pre_bpm=hr_pre, hr_avg_bpm=hr[during].mean(), hr_peak_bpm=hr[during].max(),
                         hr_30min_after_bpm=hr[(T.index >= e + pd.Timedelta(minutes=25)) & (T.index <= e + pd.Timedelta(minutes=35))].mean(),
                         glucose_pre_mmol=gpre, glucose_min_during_mmol=g[during].min(), glucose_change_at_end=at(e) - gpre if pd.notna(gpre) else np.nan,
                         glucose_1h_mmol=at(e + pd.Timedelta(hours=1)), glucose_2h_mmol=at(e + pd.Timedelta(hours=2)), glucose_12h_mmol=at(e + pd.Timedelta(hours=12)),
                         post_exercise_low_flag=bool(pd.notna(gmin_after) and gmin_after < lo)))
    X = pd.DataFrame(rows)
    for c in ["hr_pre_bpm", "hr_avg_bpm", "hr_peak_bpm", "hr_30min_after_bpm"]:
        X[c] = X[c].round(0)
    for c in ["glucose_pre_mmol", "glucose_min_during_mmol", "glucose_change_at_end", "glucose_1h_mmol", "glucose_2h_mmol", "glucose_12h_mmol"]:
        X[c] = X[c].round(1)
    return X


def glucose_events(T, ctx):
    """Excursions of the CGM trace: runs above the target high (a 'spike' under 60 minutes, a 'sustained_high' from 60 minutes) and lows below the target low (10+ minutes)."""
    prof = ctx["profile"]
    lo, hi = float(prof.glucose_target_low), float(prof.glucose_target_high)
    tz = ctx["tz"]
    g = T.glucose_mmol
    idx = T.index
    ev = []

    def runs(mask):
        m = mask.to_numpy()
        out, i, n = [], 0, len(m)
        while i < n:
            if m[i]:
                j = i
                while j + 1 < n and m[j + 1]:
                    j += 1
                out.append((i, j))
                i = j + 1
            else:
                i += 1
        return out

    meals = ctx["food"].assign(t=lambda x: pd.to_datetime(x.start_at, utc=True).dt.tz_convert(tz)).sort_values("t")
    exs = ctx["ex"].assign(s=lambda x: pd.to_datetime(x.start_at, utc=True).dt.tz_convert(tz), e=lambda x: pd.to_datetime(x.end_at, utc=True).dt.tz_convert(tz))
    ml = ctx["medlog"][ctx["medlog"].status != "pending"].copy()
    ml["when"] = pd.to_datetime(ml.scheduled_at.fillna(ml.taken_at), utc=True).dt.tz_convert(tz)
    syms = ctx["sym"].assign(t=lambda x: pd.to_datetime(x.occurred_at, utc=True).dt.tz_convert(tz))
    wb = ctx["wb"].assign(t=lambda x: pd.to_datetime(x.recorded_at, utc=True).dt.tz_convert(tz))

    def context(t0):
        mm = meals[(meals.t <= t0) & (meals.t >= t0 - pd.Timedelta(hours=3))]
        ctx_meal = mm.id.iloc[-1] if len(mm) else None
        ee = exs[((exs.e <= t0) & (exs.e >= t0 - pd.Timedelta(hours=12))) | ((exs.s <= t0) & (exs.e >= t0))]
        ctx_ex = ee.id.iloc[-1] if len(ee) else None
        dd = ml[(ml.when <= t0) & (ml.when >= t0 - pd.Timedelta(hours=12))].sort_values("when")
        st = None
        if len(dd):
            last = dd.iloc[-1]
            st = last.status
            if st == "taken" and pd.notna(last.scheduled_at) and (last.taken_at - last.scheduled_at) > pd.Timedelta(minutes=60):
                st = "late"
        ww = wb[(wb.t <= t0) & (wb.t >= t0 - pd.Timedelta(hours=6)) & wb.stress_self.notna()]
        ss = ww.stress_self.iloc[-1] if len(ww) else None
        sy = syms[(syms.t >= t0 - pd.Timedelta(hours=1)) & (syms.t <= t0 + pd.Timedelta(hours=1))]
        return ctx_meal, ctx_ex, st, ss, (sy.symptom_type.iloc[-1] if len(sy) else None)

    def add(kind, i, j):
        seg = g.iloc[i:j + 1]
        t0, t1 = idx[i], idx[j] + pd.Timedelta(minutes=5)
        ext_i = seg.idxmin() if kind == "low" else seg.idxmax()
        start_g = float(g.iloc[max(i - 6, 0):i + 1].dropna().iloc[0]) if len(g.iloc[max(i - 6, 0):i + 1].dropna()) else float(seg.iloc[0])
        cm, ce, st, ss, sy = context(t0)
        hr0 = T.heart_rate_bpm.iloc[i]
        ev.append(dict(id=str(uid("v2", "gevent", kind, str(t0))), user_id=TAN, event_type=kind, started_at=t0, extreme_at=ext_i, ended_at=t1,
                       duration_min=int((t1 - t0).total_seconds() / 60), start_glucose_mmol=round(start_g, 1), extreme_glucose_mmol=round(float(seg.min() if kind == "low" else seg.max()), 1),
                       rise_mmol=round(float(seg.max() - start_g), 1) if kind != "low" else round(float(seg.min() - start_g), 1),
                       ctx_meal_id=cm, ctx_exercise_id=ce, ctx_dose_status=st, ctx_heart_rate_bpm=None if pd.isna(hr0) else int(hr0),
                       ctx_stress_self=None if ss is None or pd.isna(ss) else int(ss), ctx_symptom_type=sy))

    for i, j in runs(g > hi):
        if (j - i + 1) < 2:
            continue
        mins = (j - i + 1) * 5
        pre_min = float(g.iloc[max(i - 12, 0):i + 1].min())
        rise = float(g.iloc[i:j + 1].max() - pre_min)
        add("sustained_high" if mins >= 60 else "spike", i, j)
    for i, j in runs(g < lo):
        if (j - i + 1) >= 2:
            add("low", i, j)
    return pd.DataFrame(ev)


# ============================================================================================= care tables
def seed_care(conn, ctx, Dsum, events):
    tz = ctx["tz"]
    meds = ctx["meds"].set_index("name")
    mid = {n: meds.loc[n, "id"] for n in meds.index}
    ref = dict(conn.execute("select generic_name, id from drug_reference").fetchall())
    # appointments: give the two future items a believable creation date
    conn.execute("update appointments set created_at = %s where user_id = %s and status = 'planned'", (pd.Timestamp("2026-09-14 10:00", tz=tz).to_pydatetime(), TAN))
    conn.execute("update appointments set created_at = %s where user_id = %s and status = 'suggested'", (pd.Timestamp("2026-09-03 09:00", tz=tz).to_pydatetime(), TAN))
    for t in ["doctor_questions", "notifications", "refill_forecasts", "interaction_alerts"]:
        conn.execute(f"delete from {t} where user_id = %s" if t != "refill_forecasts" else "delete from refill_forecasts where medication_id in (select id from medications where user_id = %s)", (TAN,))
    # doctor questions (questions to ask, never advice)
    qs = [("2026-08-16 08:30", "I felt shaky at the end of a long walk when I had skipped dinner. Should I change when I walk or eat?", "user"),
          ("2026-09-04 21:00", "My sugar went very high on a day I ate out three times. Is there a better way to plan those days?", "agent_suggested"),
          ("2026-09-13 09:00", "I started clarithromycin for a chest infection. Is it fine to take with atorvastatin and amlodipine?", "agent_suggested"),
          ("2026-09-24 20:30", "My morning sugar has been creeping up for two weeks. What could be causing it?", "agent_suggested"),
          ("2026-09-28 22:00", "I get tingling and numbness in my left foot at night. Should my feet be checked?", "checkin"),
          ("2026-10-01 21:30", "My blood pressure readings look higher lately. Is that something to adjust at my review?", "agent_suggested")]
    for i, (t, text, origin) in enumerate(qs):
        conn.execute("insert into doctor_questions (id, user_id, text, origin, status, created_at) values (%s,%s,%s,%s,'open',%s)",
                     (str(uid("v2", "dq", i)), TAN, text, origin, pd.Timestamp(t, tz=tz).to_pydatetime()))
    # refill forecasts for the three prescription medicines (runs out soon after the end of the data)
    end_date = pd.Timestamp(ctx["T_end"]).date()
    for name, left in [("Metformin 500 mg", 18), ("Amlodipine 5 mg", 24), ("Atorvastatin 20 mg", 16)]:
        conn.execute("insert into refill_forecasts (medication_id, remaining_units, runs_out_on, computed_at) values (%s,%s,%s,%s)",
                     (mid[name], left, end_date + pd.Timedelta(days={18: 9, 24: 24, 16: 16}[left]).to_pytimedelta(), pd.Timestamp(ctx["T_end"]).to_pydatetime()))
    # interaction alerts at the moment clarithromycin was added; not-checked alerts for the tonic and the fish oil
    cl = mid["Clarithromycin 500 mg"]
    created = pd.Timestamp("2026-09-13 09:05", tz=tz).to_pydatetime()
    for other, other_name in [("atorvastatin", "Atorvastatin 20 mg"), ("amlodipine", "Amlodipine 5 mg")]:
        rule = conn.execute("select id from interaction_rules where (drug_a_id=%s and drug_b_id=%s) or (drug_a_id=%s and drug_b_id=%s)",
                            (ref["clarithromycin"], ref[other], ref[other], ref["clarithromycin"])).fetchone()
        conn.execute("insert into interaction_alerts (id, user_id, med_a_id, med_b_id, interaction_rule_id, status, created_at, acknowledged_at) values (%s,%s,%s,%s,%s,'open',%s,%s)",
                     (str(uid("v2", "ia", other)), TAN, cl, mid[other_name], rule[0] if rule else None, created, None))   # open, so the Meds page clash box shows (Joely, 2026-10-08)
    for name in ["Herbal tonic (label not readable)", "Fish oil"]:
        conn.execute("insert into interaction_alerts (id, user_id, med_a_id, med_b_id, interaction_rule_id, status, created_at) values (%s,%s,%s,NULL,NULL,'not_checked',%s)",
                     (str(uid("v2", "ia", name)), TAN, mid[name], pd.Timestamp("2026-07-04 08:10", tz=tz).to_pydatetime()))
    # notifications: a reason prompt after each missed dose, weekly walk nudges, refill, symptom follow-up
    notes = []
    ml = ctx["medlog"]
    for r in ml[ml.status == "missed"].itertuples():
        sent = pd.to_datetime(r.scheduled_at, utc=True) + pd.Timedelta(minutes=90)
        notes.append(("miss_reason", "medication_log", r.id, sent, sent, sent + pd.Timedelta(minutes=14), sent + pd.Timedelta(minutes=15), "reason_given", "push",
                      json.dumps({"medication_id": str(r.medication_id), "reason": r.miss_reason})))
    for k in range(6):
        sent = pd.Timestamp("2026-08-02 19:30", tz=tz) + pd.Timedelta(days=7 * k)
        notes.append(("nudge", None, None, sent, sent, sent + pd.Timedelta(minutes=40), None, None, "push", json.dumps({"key": "nudge.evening_walk_effect", "week": k + 1})))
    notes.append(("refill", "refill_forecasts", None, pd.Timestamp("2026-10-01 09:00", tz=tz), pd.Timestamp("2026-10-01 09:00", tz=tz), None, None, None, "push",
                  json.dumps({"medication": "Metformin 500 mg"})))
    notes.append(("checkin", None, None, pd.Timestamp("2026-09-28 20:00", tz=tz), pd.Timestamp("2026-09-28 20:00", tz=tz), pd.Timestamp("2026-09-28 20:10", tz=tz),
                  pd.Timestamp("2026-09-28 20:12", tz=tz), "answered", "push", json.dumps({"question_key": "feet_tingling"})))
    for i, n in enumerate(notes):
        conn.execute("insert into notifications (id, user_id, kind, ref_table, ref_id, scheduled_for, sent_at, opened_at, acted_at, action, channel, payload) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                     (str(uid("v2", "notif", i)), TAN, n[0], n[1], n[2], py(n[3]), py(n[4]), py(n[5]), py(n[6]), n[7], n[8], n[9]))
    return len(qs), len(notes)


def clinical_flags(conn, ctx, Dsum, events):
    conn.execute("delete from clinical_flags where user_id = %s", (TAN,))
    n = 0
    D = Dsum.set_index("local_date")
    for metric in ["heart_rate", "hrv", "spo2", "glucose"]:
        nm = {"heart_rate": "hr", "hrv": "hrv", "spo2": "spo2", "glucose": "glucose"}[metric]
        days = [d for d in D.index if metric in (D.loc[d, "declining_metrics"] or [])]
        if not days:
            continue
        first, last = days[0], days[-1]
        sev = "review" if len(days) >= 7 else "watch"
        recent = D[nm + "_worse_pct"].dropna().tail(5)
        conn.execute("insert into clinical_flags (id, user_id, kind, metric, severity, status, evidence, patient_message_key, first_seen_on, last_seen_on) values (%s,%s,'outside_usual_range',%s,%s,'open',%s,'flag.outside_usual_range',%s,%s)",
                     (str(uid("v2", "flag", metric)), TAN, metric, sev, json.dumps({"worse_side_pct_last_5_days": [round(float(x), 1) for x in recent], "rule": "more than 20% of readings on the worse side of the usual range on 3 of the last 5 days",
                                                                                      "flagged_days": len(days)}), first, last))
        n += 1
    # adherence drop and low glucose
    ad = ctx["adherence_drop"]
    if ad:
        conn.execute("insert into clinical_flags (id, user_id, kind, metric, severity, status, evidence, patient_message_key, first_seen_on, last_seen_on) values (%s,%s,'adherence_drop','adherence','watch','open',%s,'flag.adherence_drop',%s,%s)",
                     (str(uid("v2", "flag", "adherence")), TAN, json.dumps(ad["evidence"]), ad["first"], ad["last"]))
        n += 1
    lows = events[events.event_type == "low"]
    for r in lows.itertuples():
        d = pd.Timestamp(r.started_at).tz_convert(ctx["tz"]).date()
        conn.execute("insert into clinical_flags (id, user_id, kind, metric, severity, status, evidence, patient_message_key, first_seen_on, last_seen_on) values (%s,%s,'low_glucose','glucose','review','acknowledged',%s,'flag.low_glucose',%s,%s)",
                     (str(uid("v2", "flag", "low", str(r.started_at))), TAN, json.dumps({"lowest_mmol": float(r.extreme_glucose_mmol), "duration_min": int(r.duration_min)}), d, d))
        n += 1
    return n


def care_summary(conn, ctx, Dsum):
    tz = ctx["tz"]
    presc = set(ctx["meds"][ctx["meds"].kind == "prescription"].id)
    ml = ctx["medlog"]
    ml = ml[(ml.status != "pending") & ml.scheduled_at.notna() & ml.medication_id.isin(presc)].copy()
    ml["when"] = pd.to_datetime(ml.scheduled_at, utc=True).dt.tz_convert(tz)
    ml["d"] = ml["when"].dt.date
    flags = q(conn, "select severity::text sev, first_seen_on, last_seen_on, status::text st from clinical_flags where user_id = %s", (TAN,))
    appts = q(conn, "select kind::text kind, status::text st, scheduled_for, created_at from appointments where user_id = %s", (TAN,))
    prev = q(conn, "select pi.kind::text kind, s.next_due_on from patient_preventive_status s join preventive_items pi on pi.id = s.preventive_item_id where s.user_id = %s", (TAN,))
    rf = q(conn, "select runs_out_on from refill_forecasts where medication_id in (select id from medications where user_id = %s)", (TAN,))
    qs = q(conn, "select created_at from doctor_questions where user_id = %s and status = 'open'", (TAN,))
    labs = ctx["labs"]
    hb = labs[labs.test == "hba1c"].assign(d=lambda x: pd.to_datetime(x.measured_at, utc=True).dt.tz_convert(tz).dt.date)
    sev_rank = {"watch": 1, "review": 2, "urgent": 3}
    rows = []
    dates = list(Dsum.local_date)
    decl = dict(zip(Dsum.local_date, Dsum.declining_metrics))
    for d in dates:
        end = pd.Timestamp(d)
        win7 = ml[(ml.d > (end - pd.Timedelta(days=7)).date()) & (ml.d <= d)]
        win30 = ml[(ml.d > (end - pd.Timedelta(days=30)).date()) & (ml.d <= d)]
        def adh(w):
            if len(w) < 5:
                return np.nan
            return round(float((w.status == "taken").mean() * 100), 1)
        miss30 = win30[win30.status == "missed"]
        # longest run of consecutive days with a missed dose in the last 30 days
        md = sorted(set(miss30.d))
        best = cur = 0
        prev_d = None
        for x in md:
            cur = cur + 1 if prev_d is not None and (x - prev_d).days == 1 else 1
            best = max(best, cur)
            prev_d = x
        top_reason = miss30.miss_reason.value_counts().index[0] if len(miss30) and miss30.miss_reason.notna().any() else None
        most_time = None
        if len(miss30):
            tt = miss30.scheduled_at.pipe(pd.to_datetime, utc=True).dt.tz_convert(tz).dt.strftime("%H:%M").value_counts()
            most_time = tt.index[0]
        runout = None
        if len(rf):
            ro = min(rf.runs_out_on)
            if (d >= pd.Timestamp("2026-09-20").date()):
                runout = (ro - d).days
        over = [r.kind for r in prev.itertuples() if r.next_due_on is not None and r.next_due_on < d]
        soon = [r.kind for r in prev.itertuples() if r.next_due_on is not None and d <= r.next_due_on <= (end + pd.Timedelta(days=30)).date()]
        last_hb = hb[hb.d <= d].d.max() if len(hb[hb.d <= d]) else None
        oq = int((pd.to_datetime(qs.created_at, utc=True).dt.tz_convert(tz).dt.date <= d).sum()) if len(qs) else 0
        fut = appts[(appts.scheduled_for.notna()) & (appts.st.isin(["planned", "suggested"])) & (pd.to_datetime(appts.created_at, utc=True).dt.tz_convert(tz).dt.date <= d) &
                    (pd.to_datetime(appts.scheduled_for, utc=True).dt.tz_convert(tz).dt.date >= d)].sort_values("scheduled_for")
        nxt = fut.iloc[0] if len(fut) else None
        openf = flags[(flags.first_seen_on <= d) & (flags.last_seen_on >= d)]
        rows.append(dict(user_id=TAN, local_date=d, adherence_7d_pct=adh(win7), adherence_30d_pct=adh(win30), doses_missed_7d=int((win7.status == "missed").sum()),
                         longest_miss_streak_days=best, top_miss_reason_30d=top_reason, most_missed_time=most_time, days_to_runout=runout,
                         preventive_overdue=over, preventive_due_soon=soon, hba1c_days_since=(d - last_hb).days if last_hb else None, open_questions_n=oq,
                         next_appointment_at=nxt.scheduled_for if nxt is not None else None, next_appointment_kind=nxt.kind if nxt is not None else None, brief_status=None,
                         open_flags_n=int(len(openf)), top_flag_severity=(max(openf.sev, key=lambda s: sev_rank[s]) if len(openf) else None), declining_metrics=decl.get(d, [])))
    C = pd.DataFrame(rows)
    return C


# ============================================================================================= patterns
def patterns(conn, ctx, T, Dsum, M):
    conn.execute("delete from pattern_candidates where user_id = %s", (TAN,))
    tz = ctx["tz"]
    food = ctx["food"].assign(t=lambda x: pd.to_datetime(x.start_at, utc=True).dt.tz_convert(tz))
    food["d"] = food.t.dt.date
    food["hour"] = food.t.dt.hour + food.t.dt.minute / 60
    Mf = M.merge(food[["id", "d", "hour", "carbs_g", "fibre_g", "food"]], left_on="food_log_id", right_on="id")
    ml = ctx["medlog"]
    ml = ml.assign(d=pd.to_datetime(ml.scheduled_at, utc=True).dt.tz_convert(tz).dt.date)
    met_eve = ml[(ml.medication_id.isin(ctx["meds"][ctx["meds"].name.str.startswith("Metformin")].id)) & (ml.schedule_id.isin(ctx["schedule"][ctx["schedule"].dose_time.astype(str).str.startswith("20:00")].id))]
    missed_days = set(met_eve[met_eve.status == "missed"].d)
    taken_days = set(met_eve[met_eve.status == "taken"].d)
    out = []

    def emit(key, anchor, outcome, exposed, ref, dates, ids, note):
        exposed, ref = np.asarray(exposed, float), np.asarray(ref, float)
        if len(exposed) < 5 or len(ref) < 5:
            return
        delta = exposed - np.median(ref)
        out.append(dict(pattern_key=key, anchor_kind=anchor, outcome_metric=outcome, n_pairs=len(exposed), median_delta=round(float(np.median(delta)), 2),
                        iqr_low=round(float(np.percentile(delta, 25)), 2), iqr_high=round(float(np.percentile(delta, 75)), 2), first_seen_on=min(dates), last_seen_on=max(dates),
                        evidence=json.dumps({"exposed_n": len(exposed), "reference_n": len(ref), "reference_median": round(float(np.median(ref)), 2),
                                             "note": note, "evidence_ids": [str(i) for i in ids][:30]})))

    # 1 post-dinner rise on days with a missed evening metformin
    dn = Mf[(Mf.hour >= 17.5)]
    a = dn[dn.d.isin(missed_days)]
    b = dn[dn.d.isin(taken_days)]
    emit("missed_evening_dose__post_dinner_rise", "dose", "meal_rise_mmol", a.rise_mmol, b.rise_mmol, list(a.d), list(a.food_log_id),
         "evening meal rise on days the evening metformin was missed, minus the median on days it was taken")
    # 2 next-morning fasting after an evening walk
    g = T.glucose_mmol
    fast = g[(g.index.hour >= 5) & (g.index.hour < 7)].groupby(g[(g.index.hour >= 5) & (g.index.hour < 7)].index.date).mean()
    ex = ctx["ex"].assign(s=lambda x: pd.to_datetime(x.start_at, utc=True).dt.tz_convert(tz))
    walk_days = set(ex[(ex.type == "walking") & (ex.s.dt.hour >= 18)].s.dt.date)
    nxt = lambda s: [d + pd.Timedelta(days=1).to_pytimedelta() for d in s]
    wk = [d for d in nxt(walk_days) if d in fast.index]
    nowk = [d for d in fast.index if (d - pd.Timedelta(days=1).to_pytimedelta()) not in walk_days]
    emit("evening_walk__next_morning_fasting", "exercise", "fasting_glucose_mmol", [fast[d] for d in wk], [fast[d] for d in nowk], wk, [], "fasting glucose (05:00-07:00) the morning after an evening walk")
    # 3 higher-carbohydrate meals
    net = Mf.carbs_g.astype(float) - 0.6 * Mf.fibre_g.fillna(0).astype(float)
    hi_ = Mf[net >= 60]
    lo_ = Mf[net < 40]
    emit("high_carb_meal__rise", "meal", "meal_rise_mmol", hi_.rise_mmol, lo_.rise_mmol, list(hi_.d), list(hi_.food_log_id), "meals with 60 g or more of net carbohydrate versus under 40 g")
    # 4 short sleep and the next morning's fasting glucose
    sl = Dsum.set_index("local_date").sleep_hours
    short = [d for d in sl.index if pd.notna(sl[d]) and sl[d] < 6 and d in fast.index]
    norm = [d for d in sl.index if pd.notna(sl[d]) and sl[d] >= 6.5 and d in fast.index]
    emit("short_sleep__fasting_glucose", "sleep", "fasting_glucose_mmol", [fast[d] for d in short], [fast[d] for d in norm], short, [], "fasting glucose after a night under 6 hours versus 6.5 hours or more")
    # 5 high-stress days and HRV
    wb = ctx["wb"].assign(d=lambda x: pd.to_datetime(x.recorded_at, utc=True).dt.tz_convert(tz).dt.date)
    st = wb[wb.stress_self.notna()].groupby("d").stress_self.mean()
    hrv = Dsum.set_index("local_date").hrv_mean_ms
    hs = [d for d in st.index if st[d] >= 4 and d in hrv.index and pd.notna(hrv[d])]
    ls = [d for d in st.index if st[d] <= 2.5 and d in hrv.index and pd.notna(hrv[d])]
    emit("high_stress_day__hrv", "wellbeing", "hrv_mean_ms", [hrv[d] for d in hs], [hrv[d] for d in ls], hs, [], "daily HRV on days with a self-reported stress of 4 or more versus 2.5 or less")
    # 6 sweet drinks
    sd = Mf[Mf.food.str.contains("sweet|Bubble|tarik", case=False, regex=True)]
    other = Mf[~Mf.food.str.contains("sweet|Bubble|tarik", case=False, regex=True)]
    emit("sweet_drink__rise", "meal", "meal_rise_mmol", sd.rise_mmol, other.rise_mmol, list(sd.d), list(sd.food_log_id), "meals that include a sweet drink versus other meals")
    for i, p in enumerate(out):
        conn.execute("insert into pattern_candidates (id, user_id, pattern_key, anchor_kind, outcome_metric, n_pairs, median_delta, iqr_low, iqr_high, first_seen_on, last_seen_on, status, relationship_type, evidence_status, evidence) "
                     "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'open','repeated_observation','derived',%s)",
                     (str(uid("v2", "pattern", p["pattern_key"])), TAN, p["pattern_key"], p["anchor_kind"], p["outcome_metric"], p["n_pairs"], p["median_delta"], p["iqr_low"], p["iqr_high"],
                      p["first_seen_on"], p["last_seen_on"], p["evidence"]))
    return out


# ============================================================================================= main
def write(conn, table, cols, rows):
    n = bulk_insert(conn, table, cols, rows)
    print(f"  {table:22s} {n:>7,d} rows")


def main():
    np.seterr(all="ignore")
    with connect() as conn:
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
        for c in ["start_at", "end_at"]:
            ctx["ex"][c] = pd.to_datetime(ctx["ex"][c], utc=True)
        print("building the timeline ...")
        T = build_timeline(ctx)
        ctx["T_end"] = T.index.max()
        print(f"  {len(T):,d} buckets from {T.index.min()} to {T.index.max()}")
        B = build_baselines(T, ctx)
        ctx_b = apply_vs_baseline(T, B)
        Dsum = build_daily(T, ctx, ctx_b)
        M = meal_responses(T, ctx)
        X = exercise_responses(T, ctx)
        ev = glucose_events(T, ctx)
        # adherence drop: weeks (prescription medicines only) with adherence under 80%
        presc = set(ctx["meds"][ctx["meds"].kind == "prescription"].id)
        ml = ctx["medlog"]
        ml = ml[(ml.status != "pending") & ml.scheduled_at.notna() & ml.medication_id.isin(presc)].assign(
            d=lambda x: pd.to_datetime(x.scheduled_at, utc=True).dt.tz_convert(ctx["tz"]).dt.date)
        wk = ml.groupby(pd.to_datetime(ml.d).dt.to_period("W")).apply(lambda x: (x.status == "taken").mean() * 100)
        bad = wk[wk < 80]
        ctx["adherence_drop"] = (dict(evidence={"weekly_adherence_pct_below_80": {str(k): round(float(v), 1) for k, v in bad.items()}}, first=bad.index.min().start_time.date(), last=bad.index.max().end_time.date())
                                 if len(bad) else None)
        ctx["weekly_adherence"] = wk
        print("writing Gold ...")
        with conn.transaction():
            for t in ["timeline_5min", "glucose_events", "exercise_response", "meal_response", "daily_summary", "care_summary", "baselines"]:
                conn.execute(f"delete from {t} where user_id = %s", (TAN,))
            tl = T.reset_index(names="bucket_start")
            tl = tl.replace({np.nan: None})
            tcols = ["user_id", "bucket_start", "local_date", "hour_of_day", "heart_rate_bpm", "hrv_rmssd_ms", "spo2_pct", "steps", "sleep_minutes", "steps_day_cum", "sleep_min_night_cum",
                     "hr_vs_baseline", "hrv_vs_baseline", "spo2_vs_baseline", "glucose_vs_baseline", "systolic_mmhg", "diastolic_mmhg", "glucose_mmol", "glucose_change_1h", "glucose_zone",
                     "meal_id", "meal_type", "food", "carbs_g", "protein_g", "fat_g", "sugar_g", "fibre_g", "sodium_mg", "exercise_id", "exercise_type", "exercise_intensity",
                     "medication_names", "dose_status", "meal_relation", "doses", "mood", "stress_self", "sleep_quality", "energy", "symptom_type", "symptom_severity", "symptom_duration_min",
                     "symptom_note", "at_work", "work_type"]
            assert len(tcols) == 46                                              # 44 features + the 2-column key
            tl = ints(tl, ["hour_of_day", "heart_rate_bpm", "steps", "sleep_minutes", "steps_day_cum", "sleep_min_night_cum", "systolic_mmhg", "diastolic_mmhg",
                           "exercise_intensity", "mood", "stress_self", "sleep_quality", "energy", "symptom_severity", "symptom_duration_min"])
            bcols = ["id", "user_id", "anchor_start", "anchor_end", "metric", "hour_of_day", "p05", "p25", "p50", "p75", "p95", "n_days", "n_points", "reset_reason"]
            write(conn, "baselines", bcols, rows_of(ints(B, ["hour_of_day", "n_days", "n_points"]), bcols))
            write(conn, "timeline_5min", tcols, rows_of(tl, tcols))
            dcols = [c for c in Dsum.columns]
            Dsum2 = Dsum.copy()
            Dsum2.insert(0, "user_id", TAN)
            dcols = ["user_id"] + list(Dsum.columns)
            for c in ["meals_n", "exercise_sessions_n", "doses_scheduled", "doses_taken", "doses_missed", "symptoms_n"]:
                Dsum2[c] = Dsum2[c].fillna(0)
            Dsum2 = ints(Dsum2, ["steps_total", "resting_hr_bpm", "meals_n", "exercise_sessions_n", "doses_scheduled", "doses_taken", "doses_missed", "symptoms_n", "symptom_worst_severity"])
            for c in ["exercise_min"]:
                Dsum2[c] = Dsum2[c].fillna(0).round(0).astype(int)
            for c in ["glucose_mean_mmol", "glucose_sd_mmol", "glucose_min_mmol", "glucose_max_mmol"]:
                Dsum2[c] = Dsum2[c].round(1)
            for c in ["tir_pct", "tbr_pct", "tar_pct", "cgm_coverage_pct", "hr_worse_pct", "hrv_worse_pct", "spo2_worse_pct", "glucose_worse_pct", "hrv_mean_ms", "spo2_mean_pct", "sleep_hours"]:
                Dsum2[c] = Dsum2[c].round(1)
            for c in ["mood_avg", "stress_self_avg", "energy_avg", "sleep_quality_avg"]:
                Dsum2[c] = Dsum2[c].round(1)
            for c in ["bp_systolic_mean", "bp_diastolic_mean", "sodium_mg"]:
                Dsum2[c] = Dsum2[c].round(0)
            for c in ["carbs_g", "protein_g", "fat_g", "sugar_g", "fibre_g"]:
                Dsum2[c] = Dsum2[c].round(1)
            write(conn, "daily_summary", dcols, rows_of(Dsum2, dcols))
            mcols = ["food_log_id", "user_id", "pre_glucose_mmol", "peak_glucose_mmol", "minutes_to_peak", "rise_mmol", "glucose_1h_mmol", "glucose_2h_mmol", "iauc_2h_mmol_min",
                     "minutes_to_baseline", "steps_next_2h", "spike_flag"]
            write(conn, "meal_response", mcols, rows_of(ints(M, ["minutes_to_peak", "minutes_to_baseline", "steps_next_2h"]), mcols))
            xcols = ["exercise_log_id", "user_id", "hr_pre_bpm", "hr_avg_bpm", "hr_peak_bpm", "hr_30min_after_bpm", "glucose_pre_mmol", "glucose_min_during_mmol", "glucose_change_at_end",
                     "glucose_1h_mmol", "glucose_2h_mmol", "glucose_12h_mmol", "post_exercise_low_flag"]
            X2 = X.copy()
            X2 = ints(X2, ["hr_pre_bpm", "hr_avg_bpm", "hr_peak_bpm", "hr_30min_after_bpm"])
            write(conn, "exercise_response", xcols, rows_of(X2, xcols))
            ecols = ["id", "user_id", "event_type", "started_at", "extreme_at", "ended_at", "duration_min", "start_glucose_mmol", "extreme_glucose_mmol", "rise_mmol", "ctx_meal_id",
                     "ctx_exercise_id", "ctx_dose_status", "ctx_heart_rate_bpm", "ctx_stress_self", "ctx_symptom_type"]
            write(conn, "glucose_events", ecols, rows_of(ints(ev, ["duration_min", "ctx_heart_rate_bpm", "ctx_stress_self"]), ecols))
            nq, nn = seed_care(conn, ctx, Dsum, ev)
            print(f"  care tables: {nq} doctor questions, {nn} notifications, 3 refill forecasts, 4 interaction alerts")
            nf = clinical_flags(conn, ctx, Dsum, ev)
            print(f"  clinical_flags         {nf:>7,d} rows")
            C = care_summary(conn, ctx, Dsum)
            ccols = ["user_id", "local_date", "adherence_7d_pct", "adherence_30d_pct", "doses_missed_7d", "longest_miss_streak_days", "top_miss_reason_30d", "most_missed_time",
                     "days_to_runout", "preventive_overdue", "preventive_due_soon", "hba1c_days_since", "open_questions_n", "next_appointment_at", "next_appointment_kind", "brief_status",
                     "open_flags_n", "top_flag_severity", "declining_metrics"]
            C = ints(C, ["adherence_dummy"] if False else ["doses_missed_7d", "longest_miss_streak_days", "days_to_runout", "hba1c_days_since", "open_questions_n", "open_flags_n"])
            write(conn, "care_summary", ccols, rows_of(C, ccols))
            pats = patterns(conn, ctx, T, Dsum, M)
            print(f"  pattern_candidates     {len(pats):>7,d} rows:", [p["pattern_key"] + f" (n={p['n_pairs']}, delta={p['median_delta']})" for p in pats])
    print("done.")


if __name__ == "__main__":
    main()
