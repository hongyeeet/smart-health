#!/usr/bin/env python3
"""Generate Mr Tan's demo dataset for data model v2: about 90 days at a 5-minute clock, ending at his last real sensor reading.

Usage:  python scripts/generate_mr_tan.py [--backup data/processed/db_backup_2026-10-05] [--plots]

Output: data/processed/demo_v2/*.csv.gz (git-ignored) plus summary.json. Deterministic (fixed seed).

What is real and what is not (docs/specs/demo-data-plan.md, mr-tan-profile.md):
  real      Dexcom G6 glucose, heart rate, meals with macros, HbA1c and fasting glucose of 2026-09-22
            (CGMacros participant 046), the last ~10 days of the window
  derived   sleep, steps and exercise sessions in that real window are inferred from his real active-energy and heart rate;
            HRV uses the spread of a BIG IDEAs participant
  simulated everything else, built as a layered cause-and-effect model (docs/specs/demo-data-plan.md section 5) so that
            meals, exercise, sleep, stress, missed doses and symptoms visibly move glucose, heart rate and mood
Every simulated or derived row is later loaded with source = 'demo_dataset'; rows that are purely real use 'file_import'.
"""
import argparse
import gzip
import json
import sys
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etl_common import uid  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TZ = "Asia/Singapore"
TAN = "dc48e209-5731-5b3d-89d9-986242c54368"
SEED = 20261005
START = pd.Timestamp("2026-07-04 00:00", tz=TZ)        # a Saturday
PHASES = [("A", 1, 14), ("B", 15, 56), ("C", 57, 70), ("D", 71, 91)]
LOW, HIGH = 3.9, 10.0
REAL_STEPS_PER_DAY = 6300
MEAL_SCALE = {"A": 1.75, "B": 1.75, "C": 1.4, "D": 1.25}
FASTING_BASE = 7.35

# ------------------------------------------------------------------------------------------ dishes (team estimates, per serving)
# name: (meal_type, carbs, protein, fat, fibre, sugar, sodium_mg, kcal)
DISHES = {
    # breakfasts
    "Kaya toast set (2 slices), soft-boiled eggs, sweet kopi": ("breakfast", 58, 14, 17, 3, 26, 850, 440),
    "Kaya toast set, soft-boiled eggs, kopi-o kosong": ("breakfast", 40, 14, 17, 3, 12, 800, 380),
    "Oats with milk and banana": ("breakfast", 52, 14, 8, 7, 20, 120, 330),
    "Nasi lemak with egg and ikan bilis": ("breakfast", 88, 20, 38, 4, 6, 1100, 780),
    "Roti prata (2) with curry": ("breakfast", 66, 12, 28, 3, 5, 900, 600),
    "Wholemeal toast, egg, kopi-o kosong": ("breakfast", 32, 16, 12, 5, 4, 520, 300),
    "Fish porridge": ("breakfast", 40, 20, 6, 1, 1, 900, 270),
    # lunches and dinners
    "Chicken rice (regular)": ("lunch", 72, 27, 22, 2, 4, 1250, 600),
    "Chicken rice, less rice, extra cucumber": ("lunch", 52, 27, 20, 3, 3, 1200, 500),
    "Yong tau foo soup with brown rice": ("lunch", 46, 24, 10, 9, 5, 1450, 380),
    "Char kway teow": ("lunch", 96, 18, 40, 4, 8, 1700, 800),
    "Laksa": ("lunch", 70, 22, 38, 4, 6, 2100, 700),
    "Economy rice: brown rice, fish, two vegetables": ("lunch", 62, 28, 14, 8, 5, 1100, 480),
    "Economy rice: white rice, curry chicken, one vegetable": ("lunch", 85, 25, 28, 4, 6, 1400, 700),
    "Fish soup with brown rice": ("lunch", 44, 30, 8, 6, 3, 1100, 360),
    "Wanton mee (dry)": ("lunch", 70, 20, 18, 3, 8, 1500, 540),
    "Mee rebus": ("lunch", 82, 16, 20, 5, 14, 1500, 570),
    "Bak chor mee": ("lunch", 68, 22, 20, 3, 8, 1600, 550),
    "Hokkien mee": ("lunch", 80, 22, 24, 3, 5, 1600, 650),
    "Nasi padang: rice, rendang, vegetables": ("lunch", 90, 28, 34, 5, 6, 1500, 780),
    "Thunder tea rice": ("lunch", 55, 24, 14, 11, 4, 900, 430),
    "Dim sum (5 pieces) with Chinese tea": ("lunch", 48, 20, 22, 2, 3, 1300, 470),
    "Steamed fish, stir-fried vegetables, half bowl of rice (home)": ("dinner", 45, 34, 12, 7, 4, 800, 410),
    "Brown rice, steamed chicken, choy sum (home)": ("dinner", 50, 32, 10, 8, 3, 750, 420),
    # snacks and drinks
    "Teh tarik (sweet)": ("drink", 28, 4, 5, 0, 24, 60, 175),
    "Sweet kopi with condensed milk": ("drink", 22, 3, 4, 0, 20, 50, 140),
    "Kopi-o kosong": ("drink", 1, 0.3, 0, 0, 0, 5, 5),
    "Bubble tea (regular sugar)": ("drink", 62, 3, 6, 0, 50, 90, 300),
    "Papaya slices": ("snack", 15, 1, 0, 3, 10, 10, 60),
    "Kueh (2 pieces)": ("snack", 34, 2, 5, 1, 16, 80, 190),
    "Unsweetened soya milk": ("drink", 6, 8, 4, 1, 2, 80, 90),
    "Handful of nuts": ("snack", 6, 6, 16, 3, 1, 5, 190),
    "Glucose sweets and two biscuits (low treatment)": ("snack", 20, 1, 3, 0, 12, 40, 110),
}
BREAKFAST = [k for k, v in DISHES.items() if v[0] == "breakfast"]
MAINS = [k for k, v in DISHES.items() if v[0] in ("lunch", "dinner")]
SWEET_DRINKS = ["Teh tarik (sweet)", "Sweet kopi with condensed milk", "Bubble tea (regular sugar)"]
LIGHT_DRINKS = ["Kopi-o kosong", "Unsweetened soya milk"]
SNACKS = ["Papaya slices", "Kueh (2 pieces)", "Handful of nuts"]

# weights per phase for choosing breakfast and mains (name -> weight), unspecified dishes get 0
WEIGHTS = {
    "A": {
        "b": {"Kaya toast set (2 slices), soft-boiled eggs, sweet kopi": 4, "Nasi lemak with egg and ikan bilis": 2, "Roti prata (2) with curry": 2,
              "Oats with milk and banana": 1, "Wholemeal toast, egg, kopi-o kosong": 1, "Fish porridge": 1},
        "m": {"Chicken rice (regular)": 4, "Economy rice: white rice, curry chicken, one vegetable": 2, "Economy rice: brown rice, fish, two vegetables": 2,
              "Yong tau foo soup with brown rice": 1, "Wanton mee (dry)": 1, "Char kway teow": 1, "Fish soup with brown rice": 1, "Laksa": 1,
              "Steamed fish, stir-fried vegetables, half bowl of rice (home)": 3, "Hokkien mee": 1},
    },
    "B": {
        "b": {"Wholemeal toast, egg, kopi-o kosong": 3, "Oats with milk and banana": 3, "Kaya toast set, soft-boiled eggs, kopi-o kosong": 2,
              "Fish porridge": 1, "Kaya toast set (2 slices), soft-boiled eggs, sweet kopi": 1},
        "m": {"Yong tau foo soup with brown rice": 3, "Economy rice: brown rice, fish, two vegetables": 3, "Chicken rice, less rice, extra cucumber": 2,
              "Fish soup with brown rice": 2, "Brown rice, steamed chicken, choy sum (home)": 3, "Steamed fish, stir-fried vegetables, half bowl of rice (home)": 3,
              "Thunder tea rice": 2, "Chicken rice (regular)": 1},
    },
    "C": {
        "b": {"Kaya toast set (2 slices), soft-boiled eggs, sweet kopi": 4, "Nasi lemak with egg and ikan bilis": 3, "Roti prata (2) with curry": 3,
              "Mee rebus": 1},
        "m": {"Char kway teow": 3, "Laksa": 3, "Nasi padang: rice, rendang, vegetables": 3, "Chicken rice (regular)": 2, "Hokkien mee": 2,
              "Bak chor mee": 2, "Economy rice: white rice, curry chicken, one vegetable": 2, "Dim sum (5 pieces) with Chinese tea": 1},
    },
    "D": {
        "b": {"Kaya toast set (2 slices), soft-boiled eggs, sweet kopi": 3, "Nasi lemak with egg and ikan bilis": 2, "Roti prata (2) with curry": 2,
              "Wholemeal toast, egg, kopi-o kosong": 1, "Oats with milk and banana": 1},
        "m": {"Chicken rice (regular)": 3, "Economy rice: white rice, curry chicken, one vegetable": 2, "Char kway teow": 2, "Laksa": 1,
              "Yong tau foo soup with brown rice": 1, "Bak chor mee": 2, "Wanton mee (dry)": 2, "Economy rice: brown rice, fish, two vegetables": 1,
              "Steamed fish, stir-fried vegetables, half bowl of rice (home)": 2},
    },
}
PHASE_FOODS = {"A": dict(sweet_drink_p=0.35, snack_p=0.3, dinner_hour=19.3), "B": dict(sweet_drink_p=0.12, snack_p=0.25, dinner_hour=19.1),
               "C": dict(sweet_drink_p=0.65, snack_p=0.4, dinner_hour=20.6), "D": dict(sweet_drink_p=0.45, snack_p=0.3, dinner_hour=19.6)}

# illustrative names for the 29 real meals, matched to their macros (the macros are the dataset's, the names are labels)
REAL_MEAL_NAMES = {
    "breakfast": [(60, "Kaya toast set, soft-boiled eggs, sweet kopi"), (40, "Roti prata (2) with curry"), (0, "Wholemeal toast, egg and kopi")],
    "lunch": [(85, "Nasi padang: rice, rendang, vegetables"), (65, "Chicken rice (regular)"), (45, "Economy rice: brown rice, fish, vegetables"), (0, "Fish soup with a little rice")],
    "dinner": [(75, "Char kway teow"), (55, "Economy rice, white rice, curry chicken"), (35, "Steamed fish with vegetables and rice"), (0, "Light dinner: soup and vegetables")],
}


def smooth(x, lo, hi):
    t = np.clip((np.asarray(x, dtype=float) - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def bump(x, mu, sd):
    return np.exp(-0.5 * ((x - mu) / sd) ** 2)


def phase_of(day):
    for p, a, b in PHASES:
        if a <= day <= b:
            return p
    return "D"


def five(df, t, v, how="mean"):
    d = df.copy()
    d["b"] = pd.to_datetime(d[t], utc=True).dt.tz_convert(TZ).dt.floor("5min")
    return getattr(d.groupby("b")[v], how)()


# ====================================================================================== real inputs
def load_real(bk):
    def rd(name):
        return pd.read_csv(gzip.open(Path(bk) / f"{name}.csv.gz", "rt", encoding="utf-8"), low_memory=False)

    gl = rd("glucose_readings")
    gl = gl[(gl.user_id == TAN) & (gl.context == "cgm") & (gl.device == "dexcom_g6") & (gl.quality_ok.astype(str).str.lower().isin(["t", "true"]))]
    g5 = five(gl, "measured_at", "value_mmol").round(1)
    hs = rd("health_samples")
    hrv_ref = hs[hs.metric == "hrv_rmssd"]
    hrv_user = hrv_ref.groupby("user_id").value.median().sort_values().index[0]       # the lowest-median BIG IDEAs participant
    ref = hrv_ref[hrv_ref.user_id == hrv_user].value
    hrv_logsd = float(np.log(ref[ref > 5]).std())
    hs = hs[hs.user_id == TAN]
    hr5 = five(hs[hs.metric == "heart_rate"], "start_at", "value")
    ae5 = five(hs[hs.metric == "active_energy"], "start_at", "value")
    meals = rd("meals")
    meals = meals[(meals.user_id == TAN) & (~meals.description.fillna("").str.startswith("Simulated"))].copy()
    items = rd("meal_items")
    agg = items.groupby("meal_id")[["carbs_g", "protein_g", "fat_g", "fibre_g", "kcal", "sugar_g", "sodium_mg"]].sum(min_count=1)
    meals = meals.merge(agg, left_on="id", right_index=True, how="left").sort_values("eaten_at")
    meals["start"] = pd.to_datetime(meals.eaten_at, utc=True).dt.tz_convert(TZ)
    labs = rd("lab_results")
    labs = labs[labs.user_id == TAN]
    prof = rd("patient_profiles")
    prof = prof[prof.user_id == TAN].iloc[0]
    return dict(g5=g5, hr5=hr5, ae5=ae5, meals=meals, labs=labs, prof=prof, hrv_logsd=hrv_logsd)


# ====================================================================================== the generator
class Gen:
    def __init__(self, real):
        self.real = real
        self.end = real["g5"].index.max()
        self.real_start = real["g5"].index.min()
        self.idx = pd.date_range(START, self.end, freq="5min")
        self.N = len(self.idx)
        self.hour = (self.idx.hour + self.idx.minute / 60).to_numpy()
        self.dates = pd.date_range(START.normalize(), self.end.normalize(), freq="D")
        self.D = len(self.dates)
        self.day_no = ((self.idx.normalize() - START.normalize()).days + 1).to_numpy()
        self.wd = self.idx.weekday.to_numpy()
        self.t_min = (self.idx - START).total_seconds().to_numpy() / 60.0
        self.rng = np.random.default_rng(SEED)
        # first day number of the real window
        self.real_day0 = int(((self.real_start.normalize() - START.normalize()).days) + 1)

    def rs(self, k):
        return np.random.default_rng(SEED + k)

    # ---------------------------------------------------------------- daily hidden state
    def daily_state(self):
        D = self.D
        r = self.rs(1)
        days = np.arange(1, D + 1)
        wdays = np.array([d.weekday() for d in self.dates])
        weekend = wdays >= 5
        ph = np.array([phase_of(d) for d in days])
        self.days, self.wdays, self.weekend, self.ph = days, wdays, weekend, ph
        # walks after dinner
        pw = np.where(ph == "B", np.where(weekend, 0.55, 0.72), np.where(ph == "A", 0.05, np.where(ph == "C", 0.04, 0.07)))
        pw = np.where((ph == "B") & (days < 22), 0.30, pw)
        walk = r.random(D) < pw
        # the real window uses detected evening bouts (set later in apply_real_window); remember sim flags
        self.walk = walk.copy()
        # sleep (hours, night ending that morning)
        mu = {"A": 6.8, "B": 7.1, "C": 5.8, "D": 6.3}
        sleep = np.array([mu[p] for p in ph]) + np.where(weekend, 0.5, 0.0) + r.normal(0, 0.55, D)
        self.sleep_h = np.clip(sleep, 4.3, 9.0)
        # stress 0..1
        smu = {"A": 0.35, "B": 0.30, "C": 0.62, "D": 0.50}
        st = np.array([smu[p] for p in ph]) + np.where(weekend, -0.08, 0.10) + r.normal(0, 0.11, D) + 0.06 * np.clip(6.5 - self.sleep_h, 0, 3)
        self.stress = np.clip(st, 0.05, 0.98)
        # illness (antibiotic course days 72-78)
        ill = np.zeros(D)
        for d, v in {70: 0.25, 71: 0.5, 72: 0.9, 73: 1.0, 74: 1.0, 75: 0.9, 76: 0.7, 77: 0.5, 78: 0.35, 79: 0.2, 80: 0.1}.items():
            if d <= D:
                ill[d - 1] = v
        self.ill = ill
        # misses decided in meds(); placeholders so glucose can read them
        self.miss_eve = np.zeros(D, bool)
        self.miss_morn = np.zeros(D, bool)

    # ---------------------------------------------------------------- meals
    def make_meals(self):
        r = self.rs(2)
        rows = []
        for i, d in enumerate(self.dates):
            day = i + 1
            if d >= self.real_start.normalize() and day >= self.real_day0:
                continue                                            # real window: dataset meals are added later
            p = self.ph[i]
            w = WEIGHTS[p]
            fp = PHASE_FOODS[p]
            we = self.weekend[i]

            def pick(kind, hour, minute_noise=15, force=None):
                if force is not None:
                    name = force
                else:
                    ws = w["b"] if kind == "b" else w["m"]
                    names, wt = list(ws.keys()), np.array(list(ws.values()), float)
                    name = r.choice(names, p=wt / wt.sum())
                start = d + pd.Timedelta(hours=float(hour)) + pd.Timedelta(minutes=float(r.normal(0, minute_noise)))
                mt, c, pr, f, fi, su, na, kc = DISHES[name]
                portion = float(np.clip(r.normal(1.0, 0.12), 0.7, 1.35))
                rows.append(dict(start=start, end=start + pd.Timedelta(minutes=float(r.integers(15, 30))), food=name, carbs_g=round(c * portion, 1),
                                 protein_g=round(pr * portion, 1), fat_g=round(f * portion, 1), fibre_g=round(fi * portion, 1),
                                 sugar_g=round(su * portion, 1), sodium_mg=round(na * portion, -1), kcal=round(kc * portion), real=False))
                return start

            bh = 9.4 if we else 7.55
            pick("b", bh)
            if r.random() < fp["sweet_drink_p"] * (0.8 if p in ("A", "C") else 0.7):
                pick("m", float(r.choice([10.4, 15.4])), force=r.choice(SWEET_DRINKS), minute_noise=15)
            pick("m", 13.1 if we else 12.45, 25)
            if r.random() < fp["snack_p"] * 0.7:
                s = r.choice(SNACKS + LIGHT_DRINKS)
                pick("m", 16.2, 30, force=s)
            pick("m", fp["dinner_hour"] + (0.3 if we else 0.0), 25)
        # scripted showcase days
        self.meals = pd.DataFrame(rows)

    def script_overrides(self):
        """Hand-written events that make the showcase days work. Called after make_meals and before glucose."""
        m = self.meals
        # day 43 (Saturday 2026-08-15): long walk, dinner skipped, low glucose, treated with sweets
        d43 = self.dates[42]
        drop = m[(m.start >= d43 + pd.Timedelta(hours=17)) & (m.start < d43 + pd.Timedelta(hours=23))].index
        self.meals = m.drop(drop).reset_index(drop=True)
        sw = DISHES["Glucose sweets and two biscuits (low treatment)"]
        self.meals.loc[len(self.meals)] = dict(start=d43 + pd.Timedelta(hours=19.95), end=d43 + pd.Timedelta(hours=20.1), food="Glucose sweets and two biscuits (low treatment)",
                                               carbs_g=sw[1], protein_g=sw[2], fat_g=sw[3], fibre_g=sw[4], sugar_g=sw[5], sodium_mg=sw[6], kcal=sw[7], real=False)
        # day 62 (Thursday 2026-09-03): the worst day - sweet drink with breakfast, char kway teow, late laksa and bubble tea
        d62 = self.dates[61]
        drop = self.meals[(self.meals.start >= d62) & (self.meals.start < d62 + pd.Timedelta(days=1))].index
        self.meals = self.meals.drop(drop).reset_index(drop=True)
        for name, h in [("Kaya toast set (2 slices), soft-boiled eggs, sweet kopi", 7.6), ("Teh tarik (sweet)", 7.7), ("Char kway teow", 12.6),
                        ("Bubble tea (regular sugar)", 16.0), ("Laksa", 21.3), ("Bubble tea (regular sugar)", 21.9)]:
            mt, c, pr, f, fi, su, na, kc = DISHES[name]
            s = d62 + pd.Timedelta(hours=h)
            self.meals.loc[len(self.meals)] = dict(start=s, end=s + pd.Timedelta(minutes=20), food=name, carbs_g=c, protein_g=pr, fat_g=f, fibre_g=fi, sugar_g=su,
                                                   sodium_mg=na, kcal=kc, real=False)
        self.stress[61] = 0.88
        self.script_miss = {(61, 'metformin', '20:00'), (61, 'atorvastatin', '22:00')}
        self.sleep_h[61] = 5.0
        self.sleep_h[62] = 5.3
        self.walk[61] = False
        self.miss_eve[61] = True
        self.walk[42] = False                                     # day 43 is handled as a scripted long walk

    def add_real_meals(self):
        rm = self.real["meals"]
        rows = []
        for _, m in rm.iterrows():
            mt = m["meal_type"]
            c = float(m["carbs_g"]) if pd.notna(m["carbs_g"]) else 0.0
            name = None
            for lim, nm in REAL_MEAL_NAMES.get(mt, [(0, "Meal")]):
                if c >= lim:
                    name = nm
                    break
            rows.append(dict(start=m["start"], end=m["start"] + pd.Timedelta(minutes=20), food=name,
                             carbs_g=m["carbs_g"], protein_g=m["protein_g"], fat_g=m["fat_g"], fibre_g=m["fibre_g"], sugar_g=m["sugar_g"],
                             sodium_mg=m["sodium_mg"], kcal=m["kcal"], real=True, meal_type_real=mt))
        self.meals = pd.concat([self.meals, pd.DataFrame(rows)], ignore_index=True).sort_values("start").reset_index(drop=True)
        # meal type for simulated meals follows the time of day
        def mtype(row):
            if row.get("meal_type_real") is not None and isinstance(row.get("meal_type_real"), str):
                return row["meal_type_real"]
            nm = row["food"]
            base = DISHES.get(nm)
            h = row["start"].hour + row["start"].minute / 60
            if base and base[0] in ("drink", "snack"):
                return base[0]
            if h < 10.5:
                return "breakfast"
            if h < 15:
                return "lunch"
            if h < 17:
                return "snack"
            return "dinner"
        self.meals["meal_type"] = self.meals.apply(mtype, axis=1)
        self.meals["estimated_by"] = np.where(self.meals.real, "database", "user")

    # ---------------------------------------------------------------- real-window derivations (sleep, steps, exercise, walks)
    def derive_real_window(self):
        real = self.real
        idx = self.idx
        ae = real["ae5"].reindex(idx)
        hr = real["hr5"].reindex(idx)
        in_real = (idx >= real["ae5"].index.min()) & (idx <= real["ae5"].index.max())
        self.in_real = in_real
        # HR: real where present; short gaps interpolated; the rest imputed from active energy
        ok = hr.notna() & in_real
        slope, intercept = np.polyfit(ae[ok].to_numpy(), hr[ok].to_numpy(), 1)
        res_sd = float(np.std(hr[ok].to_numpy() - (intercept + slope * ae[ok].to_numpy())))
        hr_i = hr.interpolate(limit=6, limit_area="inside")
        imputed = in_real & hr_i.isna() & ae.notna()
        rr = self.rs(3)
        hr_fill = (intercept + slope * ae + rr.normal(0, res_sd * 0.8, self.N)).clip(lower=45, upper=170)
        hr_i = hr_i.where(~imputed, hr_fill)
        self.hr_real = hr_i.where(in_real)                     # real (or lightly imputed) heart rate inside the real window
        self.hr_imputed = (imputed | (hr.isna() & hr_i.notna() & in_real)).to_numpy()
        self.ae = ae
        # sleep: runs of resting active energy (<= 1.25) in the late evening to morning, at least 60 minutes
        hr_low = (hr_i.fillna(0) < 80).to_numpy() | (ae <= 1.15).to_numpy()
        rest = (ae <= 1.25).to_numpy() & in_real & hr_low
        night = ((self.hour >= 21.5) | (self.hour <= 9.5))
        cand = rest & night
        c = pd.Series(cand.astype(int))
        closed = c.rolling(5, center=True, min_periods=1).max().rolling(5, center=True, min_periods=1).min().to_numpy().astype(bool)
        asleep = np.zeros(self.N)
        i = 0
        while i < self.N:
            if closed[i]:
                j = i
                while j + 1 < self.N and closed[j + 1]:
                    j += 1
                if (j - i + 1) * 5 >= 60:
                    asleep[i:j + 1] = 5.0
                i = j + 1
            else:
                i += 1
        self.asleep_real = asleep
        # steps from active energy
        extra = np.clip((np.nan_to_num(ae.to_numpy(), nan=1.1) - 1.40) / 3.2, 0, 1.4) ** 1.7
        raw = extra * 5 * 100 * rr.uniform(0.9, 1.1, self.N)
        days_real = max(in_real.sum() / 288.0, 1.0)
        self.steps_real = np.round(raw * (REAL_STEPS_PER_DAY * days_real) / max(raw[in_real].sum(), 1.0))
        # exercise bouts: active energy >= 5.0 and heart rate >= 98 for 20 minutes or more, outside weekday work hours
        wd = self.wd
        work = (wd < 5) & (self.hour >= 8.5) & (self.hour < 17.5)
        hot = ((ae.to_numpy() >= 4.9) & (hr_i.fillna(0).to_numpy() >= 96)) & in_real & ~work
        bouts = []
        i = 0
        while i < self.N:
            if hot[i]:
                j = i
                while j + 1 < self.N and (hot[j + 1] or (j + 2 < self.N and hot[j + 2])):
                    j += 1
                nxt = j + 1
                if (j - i + 1) * 5 >= 20:
                    if (j - i + 1) > 12:                          # longer than an hour: keep the 60 minutes with the highest activity
                        a = ae.to_numpy()
                        best = max(range(i, j - 10), key=lambda s: np.nansum(a[s:s + 12]))
                        i, j = best, best + 11
                    bouts.append((i, j))
                i = nxt
            else:
                i += 1
        self.real_bouts = bouts

    def exercise_sessions(self):
        r = self.rs(4)
        rows = []
        sets = []
        # simulated days
        for i, d in enumerate(self.dates):
            day = i + 1
            if day >= self.real_day0:
                continue
            p = self.ph[i]
            we = self.weekend[i]
            if self.walk[i]:
                # a walk 35-60 minutes after the dinner ends
                dn = self.meals[(self.meals.start >= d + pd.Timedelta(hours=16.5)) & (self.meals.start < d + pd.Timedelta(hours=23)) &
                                (~self.meals.food.isin(SWEET_DRINKS))]
                base = (dn.end.max() if len(dn) else d + pd.Timedelta(hours=20))
                s = base + pd.Timedelta(minutes=float(r.integers(12, 32)))
                dur = int(r.integers(25, 42))
                inten = int(r.choice([2, 3, 3, 4]))
                rows.append(dict(start=s, end=s + pd.Timedelta(minutes=dur), type="walking", intensity=inten, feeling=int(np.clip(r.normal(4.0, 0.7), 2, 5)),
                                 note=r.choice(["Walk around the estate after dinner", "Evening walk with my wife", "Walked to the park connector and back", None]), real=False))
            if we and (r.random() < {"A": 0.35, "B": 0.6, "C": 0.12, "D": 0.2}[p]):
                s = d + pd.Timedelta(hours=float(r.choice([7.0, 7.5, 16.5])))
                typ, inten, dur = r.choice([("cycling", 3, 60), ("walking", 3, 55), ("cycling", 4, 75)])
                rows.append(dict(start=s, end=s + pd.Timedelta(minutes=int(dur)), type=typ, intensity=int(inten), feeling=int(np.clip(r.normal(4.2, 0.6), 2, 5)),
                                 note=r.choice(["Cycled along East Coast Park", "Long walk at MacRitchie", None]), real=False))
            if p == "B" and self.wdays[i] == 2 and day >= 22 and r.random() < 0.8:
                s = d + pd.Timedelta(hours=19.0)
                rows.append(dict(start=s, end=s + pd.Timedelta(minutes=45), type="strength", intensity=3, feeling=4, note="Gym after work: machines", real=False, sets=True))
        # scripted long walk on day 43 (Saturday)
        d43 = self.dates[42]
        rows.append(dict(start=d43 + pd.Timedelta(hours=17.5), end=d43 + pd.Timedelta(hours=19.15), type="walking", intensity=4, feeling=3,
                         note="Long brisk walk, skipped dinner, felt shaky near the end", real=False))
        # real window: detected bouts
        for (i, j) in self.real_bouts:
            s, e = self.idx[i], self.idx[j] + pd.Timedelta(minutes=5)
            peak = float(self.hr_real.iloc[i:j + 1].max()) if self.hr_real is not None else 110
            inten = 2 if peak < 108 else 3 if peak < 118 else 4
            typ = "walking"
            rows.append(dict(start=s, end=e, type=typ, intensity=inten, feeling=int(np.clip(r.normal(3.6, 0.7), 2, 5)),
                             note="Detected from his real heart rate and activity", real=True))
        ex = pd.DataFrame(rows).sort_values("start").reset_index(drop=True)
        ex["id"] = [str(uid("v2", "exercise", str(s))) for s in ex.start]
        # sets for strength sessions
        for _, e in ex[ex.get("sets", pd.Series(False, index=ex.index)).fillna(False).astype(bool)].iterrows():
            order = 0
            for name, base_w, reps in [("Leg press", 60, 12), ("Seated row", 35, 12), ("Chest press", 30, 10)]:
                order += 1
                for sn in range(1, 4):
                    sets.append(dict(exercise_log_id=e["id"], exercise=name, exercise_order=order, set_no=sn, reps=int(reps - (sn - 1)),
                                     weight_kg=float(base_w + 2.5 * (self.dates.get_loc(e.start.normalize()) // 14)), rest_s=75, rpe=int(6 + sn),
                                     performed_at=e.start + pd.Timedelta(minutes=int(8 * order + 2 * sn))))
        self.ex = ex
        self.ex_sets = pd.DataFrame(sets)
        # evening-walk flags for the real window (for the walk effect) come from bouts that start after 17:00
        for (i, j) in self.real_bouts:
            if self.idx[i].hour >= 17:
                self.walk[int(self.day_no[i]) - 1] = True

    # ---------------------------------------------------------------- real-window scripted days
    def real_window_states(self):
        d0 = self.real_day0 - 1
        # stress and misses in the real window, scripted to explain the real glucose (09-26 to 09-28 were very high)
        script = {  # date: (stress, miss_evening)
            "2026-09-22": (0.45, False), "2026-09-23": (0.50, False), "2026-09-24": (0.50, False), "2026-09-25": (0.62, True),
            "2026-09-26": (0.76, True), "2026-09-27": (0.80, True), "2026-09-28": (0.84, False), "2026-09-29": (0.66, True),
            "2026-09-30": (0.58, False), "2026-10-01": (0.55, False), "2026-10-02": (0.50, False)}
        for k, (s, m) in script.items():
            i = (pd.Timestamp(k, tz=TZ) - START.normalize()).days
            if 0 <= i < self.D:
                self.stress[i] = s
                if m:
                    self.script_miss.add((i, "metformin", "20:00"))
        # sleep hours in the real window from the derived asleep mask (night ending that morning)
        for i in range(self.D):
            if i + 1 >= self.real_day0 + 1:
                d = self.dates[i]
                lo, hi = d - pd.Timedelta(hours=3), d + pd.Timedelta(hours=11)
                mask = (self.idx >= lo) & (self.idx < hi)
                h = self.asleep_real[mask].sum() / 60.0
                if h > 2.5:
                    self.sleep_h[i] = round(float(h), 2)

    # ---------------------------------------------------------------- medications
    def medications(self):
        r = self.rs(5)
        meds = [
            dict(key="metformin", name="Metformin 500 mg", kind="prescription", strength="500 mg", frequency=2, description="Helps the body use insulin better and lowers sugar. Take with food.",
                 start=pd.Timestamp("2021-04-11"), end=None, ref="metformin", times=[("08:00", 1, "after_meal"), ("20:00", 1, "after_meal")]),
            dict(key="amlodipine", name="Amlodipine 5 mg", kind="prescription", strength="5 mg", frequency=1, description="For high blood pressure.",
                 start=pd.Timestamp("2022-12-02"), end=None, ref="amlodipine", times=[("08:00", 1, "na")]),
            dict(key="atorvastatin", name="Atorvastatin 20 mg", kind="prescription", strength="20 mg", frequency=1, description="For cholesterol, taken at night.",
                 start=pd.Timestamp("2023-06-20"), end=None, ref="atorvastatin", times=[("22:00", 1, "na")]),
            dict(key="fishoil", name="Fish oil", kind="supplement", strength=None, frequency=1, description="Supplement taken with breakfast.",
                 start=pd.Timestamp("2025-08-28"), end=None, ref=None, times=[("08:00", 1, "after_meal")]),
            dict(key="tonic", name="Herbal tonic (label not readable)", kind="tcm", strength=None, frequency=1, description="A tonic from a Chinese medical hall; the label could not be read.",
                 start=pd.Timestamp("2026-03-16"), end=None, ref=None, times=[("21:00", 1, "na")]),
            dict(key="clarithro", name="Clarithromycin 500 mg", kind="prescription", strength="500 mg", frequency=2, description="An antibiotic for a chest infection, 7 days.",
                 start=self.dates[71], end=self.dates[77], ref="clarithromycin", times=[("08:00", 1, "after_meal"), ("20:00", 1, "after_meal")]),
        ]
        self.meds = meds
        rows = []
        D = self.D
        for m in meds:
            for t, q, rel in m["times"]:
                hh, mm = int(t[:2]), int(t[3:])
                for i, d in enumerate(self.dates):
                    if m["start"] is not None and d < m["start"].tz_localize(TZ) if m["start"].tzinfo is None else d < m["start"]:
                        continue
                    if m["end"] is not None and d > (m["end"].tz_localize(TZ) if m["end"].tzinfo is None else m["end"]):
                        continue
                    sched = d + pd.Timedelta(hours=hh, minutes=mm)
                    if sched > self.end:
                        continue
                    p = self.ph[i]
                    work = not self.weekend[i]
                    evening = hh >= 19
                    if m["key"] in ("fishoil", "tonic"):
                        pm = 0.28 if m["key"] == "tonic" else 0.22
                    elif m["key"] == "clarithro":
                        pm = 0.0
                    else:
                        base = {"A": (0.04, 0.08), "B": (0.03, 0.06), "C": (0.12, 0.34), "D": (0.08, 0.20)}[p]
                        pm = base[1] if evening else base[0]
                        if evening and work:
                            pm *= 1.25
                        pm *= (1 + 0.9 * (self.stress[i] - 0.5))
                    miss = r.random() < pm
                    reason = None
                    status = "taken"
                    if i + 1 >= self.real_day0:                       # real window: only the scripted misses
                        if m["key"] == "metformin":
                            miss = (i, "metformin", t) in self.script_miss
                        elif m["key"] == "amlodipine":
                            miss = False
                        elif m["key"] == "atorvastatin":
                            miss = (i, "metformin", "20:00") in self.script_miss and r.random() < 0.5
                    if (i, m["key"], t) in self.script_miss:
                        miss = True
                    if m["key"] == "clarithro":
                        miss = (i == 76 and evening)                 # one missed evening dose on day 77
                    # scripted: metformin ran out on days 60-61
                    if m["key"] == "metformin" and i + 1 in (60, 61):
                        miss, reason = True, "ran_out"
                    if m["key"] == "metformin" and i + 1 in (34, 47) and not evening:
                        miss, reason = True, "side_effects"
                    if miss:
                        status = "missed"
                        if reason is None:
                            if i + 1 == 62 and evening:
                                reason = "away_from_home"
                            elif evening and (work or p == "C") and r.random() < 0.38:
                                reason = "away_from_home"
                            else:
                                reason = str(r.choice(["forgot", "forgot", "forgot", "felt_fine", "other"]))
                        if i + 1 >= self.real_day0 and evening and m["key"] == "metformin":
                            reason = {"2026-09-25": "forgot", "2026-09-26": "away_from_home", "2026-09-27": "forgot", "2026-09-29": "away_from_home"}.get(str(d.date()), reason)
                        taken = None
                        if m["key"] == "metformin" and evening:
                            self.miss_eve[i] = True
                        if m["key"] == "metformin" and not evening:
                            self.miss_morn[i] = True
                    else:
                        delay = float(np.clip(r.lognormal(np.log(10), 0.9), 0, 240))
                        taken = sched + pd.Timedelta(minutes=delay)
                    rows.append(dict(med=m["key"], time=t, scheduled_at=sched, taken_at=taken, status=status, miss_reason=reason, quantity=q, meal_relation=rel,
                                     day_index=i))
        self.med_log = pd.DataFrame(rows).sort_values(["scheduled_at", "med"]).reset_index(drop=True)
        # flags used by the glucose model
        self.miss_eve = np.zeros(D, bool)
        self.miss_morn = np.zeros(D, bool)
        ml = self.med_log[(self.med_log.med == "metformin") & (self.med_log.status == "missed")]
        for _, x in ml.iterrows():
            if x.time == "20:00":
                self.miss_eve[x.day_index] = True
            else:
                self.miss_morn[x.day_index] = True

    # ---------------------------------------------------------------- sleep mask for simulated nights
    def sleep_mask(self):
        r = self.rs(6)
        asleep = np.zeros(self.N)
        for i, d in enumerate(self.dates):
            if i + 1 > self.D:
                break
            if d >= self.real_start.normalize() and i + 1 >= self.real_day0 + 1:
                continue                                              # derived from real data
            prev_we = (d - pd.Timedelta(days=1)).weekday() in (4, 5)   # Fri/Sat night
            bed = d - pd.Timedelta(hours=1.0) + pd.Timedelta(minutes=float(r.normal(0, 40) + (55 if prev_we else 0) + 40 * (self.stress[max(i - 1, 0)] - 0.5)))
            onset = bed + pd.Timedelta(minutes=float(r.integers(8, 25)))
            n_awake = int(r.integers(2, 4))
            awake_buckets = int(sum(r.integers(1, 5) for _ in range(n_awake)))
            need = int(round(self.sleep_h[i] * 12))
            total = need + awake_buckets
            a0 = int(np.searchsorted(self.idx.asi8, onset.tz_convert("UTC").value if hasattr(onset, "tz_convert") else onset.value))
            a1 = min(a0 + total, self.N)
            seg = np.zeros(total)
            seg[:] = 5.0
            pos = np.sort(r.integers(10, max(total - 10, 11), n_awake))
            for p0 in pos:
                seg[p0:p0 + int(r.integers(1, 5))] = 0.0
            lo = max(a0, 0)
            asleep[lo:a1] = np.maximum(asleep[lo:a1], seg[lo - a0:a1 - a0]) if a1 > lo else asleep[lo:a1]
        # first night starts before the grid: sleep until about 06:30 on day 1
        asleep[:int(6.4 * 12)] = np.where(self.rs(7).random(int(6.4 * 12)) < 0.95, 5.0, 0.0)
        self.asleep_sim = asleep
        self.asleep = np.where(self.in_real, self.asleep_real, asleep)
        # a short sleep-hours column by night (ending morning)
        self.sleep_h_actual = np.zeros(self.D)
        for i, d in enumerate(self.dates):
            lo, hi = d - pd.Timedelta(hours=3), d + pd.Timedelta(hours=11)
            mask = (self.idx >= lo) & (self.idx < hi)
            self.sleep_h_actual[i] = self.asleep[mask].sum() / 60.0

    # ---------------------------------------------------------------- glucose
    def glucose(self):
        r = self.rs(8)
        N = self.N
        di = (self.day_no - 1).astype(int)
        # walking effect (exponentially weighted over about two weeks)
        ew = np.zeros(self.D)
        prev = 0.0
        for i in range(self.D):
            ew[i] = prev
            prev = 0.93 * prev + 0.07 * float(self.walk[i])
        wk = np.clip(ew / 0.62, 0, 1.1)
        self.walk_effect = wk
        days = self.days
        disruption = 0.4 * smooth(days, 55, 62) * (1 - smooth(days, 70, 76))
        drift = 1.05 * smooth(days, 64, 91)
        sl_prev = np.where(self.sleep_h_actual > 2, self.sleep_h_actual, self.sleep_h)
        F = (FASTING_BASE - 0.9 * wk + disruption + drift + 0.30 * np.clip(7.0 - sl_prev, 0, 3) + 0.45 * np.concatenate([[0], self.miss_eve[:-1].astype(float)])
             + 0.8 * self.ill + r.normal(0, 0.22, self.D))
        F = F + 0.2 * np.concatenate([[0], self.ex_strength_prev()[:-1]]) * -1
        self.F = F
        # anchors at 05:30 of each day, linear in time
        anchor_t = np.array([(d + pd.Timedelta(hours=5.5) - START).total_seconds() / 60 for d in self.dates])
        base = np.interp(self.t_min, anchor_t, F)
        base = base + 0.55 * bump(self.hour, 5.6, 1.4) - 0.25
        # daytime stress and missed morning dose
        daylight = smooth(self.hour, 6.5, 9) * (1 - smooth(self.hour, 22.5, 24.5))
        stress_t = self.stress[di]
        base = base + 1.1 * (stress_t - 0.5) * daylight
        mm = self.miss_morn[di] & (self.hour >= 8) & (self.hour < 20)
        base = base + 0.45 * mm
        me = np.roll(self.miss_eve[di], 0) & (self.hour >= 20)
        base = base + 0.45 * me
        base = base + 0.9 * self.ill[di] * daylight
        # meal excess
        m = self.meals
        excess = np.zeros(N)
        scale = MEAL_SCALE
        for _, row in m.iterrows():
            t0 = (row.start - START).total_seconds() / 60
            c = float(row.carbs_g) if pd.notna(row.carbs_g) else 0.0
            fi = float(row.fibre_g) if pd.notna(row.fibre_g) else 0.0
            pr = float(row.protein_g) if pd.notna(row.protein_g) else 0.0
            fa = float(row.fat_g) if pd.notna(row.fat_g) else 0.0
            net = max(c - 0.6 * fi, 0.0)
            h = row.start.hour + row.start.minute / 60
            tod = 1.2 if h < 10.5 else (0.8 if h < 15 else 1.0)
            ph = phase_of(int((row.start.normalize() - START.normalize()).days) + 1)
            R = scale[ph] * (0.6 + 0.07 * net) * tod * (1 - 0.004 * min(pr + fa, 80))
            tp = float(np.clip(52 + 0.30 * fa + 0.20 * pr + 0.9 * fi, 45, 115))
            x = (self.t_min - t0) / tp
            xx = np.maximum(x, 1e-9)
            f = np.where(x > 0, (xx ** 1.7) * np.exp(1.7 * (1 - xx)), 0.0)
            excess += R * f
        # exercise envelope
        env = np.zeros(N)
        dip = np.zeros(N)
        for _, e in self.ex.iterrows():
            s = (e.start - START).total_seconds() / 60
            en = (e.end - START).total_seconds() / 60
            I = float(e.intensity)
            kind = e.type
            amp = 0.30 * (I / 3.0) if kind != "strength" else 0.12
            ramp = np.clip((self.t_min - s) / max(en - s, 1), 0, 1)
            decay = np.where(self.t_min > en, np.exp(-(self.t_min - en) / 110.0), 1.0)
            ee = np.where(self.t_min >= s, ramp * decay, 0.0)
            env = np.maximum(env, amp * ee)
            dip += (0.22 * I if kind != "strength" else 0.08 * I) * ee
        g = base + excess * (1 - np.clip(env, 0, 0.5)) - dip
        # scripted low on day 43
        d43 = self.dates[42]
        t_low = (d43 + pd.Timedelta(hours=19.75) - START).total_seconds() / 60
        sd_low = np.where(self.t_min < t_low, 35.0, 45.0)
        g = g - 2.9 * np.exp(-0.5 * ((self.t_min - t_low) / sd_low) ** 2)
        # noise (AR(1))
        eps = r.normal(0, 0.11, N)
        ar = np.zeros(N)
        for k in range(1, N):
            ar[k] = 0.93 * ar[k - 1] + eps[k]
        g = g + ar
        g = 3.3 + np.logaddexp(0, 4.0 * (g - 3.3)) / 4.0               # soft floor near 3.3 so lows look natural
        g = np.clip(g, 3.0, 21.5)
        self.g_sim = g
        # real window
        g5 = self.real["g5"].reindex(self.idx)
        out = g.copy()
        real_mask = g5.notna().to_numpy()
        first = int(np.argmax(real_mask))
        ramp_n = 36                                                   # blend the 3 hours before the real data
        delta = float(g5.iloc[first] - g[first])
        w = np.zeros(N)
        w[first - ramp_n:first] = np.linspace(0, 1, ramp_n)
        out = out + delta * w
        out[real_mask] = g5[real_mask].to_numpy()
        self.glucose_final = np.round(out, 1)
        self.glucose_real = real_mask

    def ex_strength_prev(self):
        v = np.zeros(self.D)
        for _, e in self.ex.iterrows():
            if e.type == "strength":
                v[int((e.start.normalize() - START.normalize()).days)] = 1
        return v

    # ---------------------------------------------------------------- heart rate, HRV, SpO2, steps
    def vitals(self):
        r = self.rs(9)
        N = self.N
        di = (self.day_no - 1).astype(int)
        asleep = self.asleep > 0
        awake = ~asleep
        stress_t = self.stress[di]
        days = self.days[di]
        offs = (-2.0 * smooth(days, 22, 40) * (1 - smooth(days, 56, 64)) + 4.0 * smooth(days, 72, 91) + 5.5 * self.ill[di] + 6.0 * (stress_t - 0.5))
        # circadian
        awake_base = 86 + 9 * bump(self.hour, 19.5, 2.5) + 3 * bump(self.hour, 10.0, 2.0)
        # sleep curve: heart rate eases down through the night
        night_h = np.where(self.hour >= 18, self.hour - 24, self.hour)
        sleep_base = 79 - 1.3 * np.clip(night_h + 2, 0, 7)
        hr = np.where(asleep, sleep_base, awake_base) + offs
        # exercise
        pulse = np.zeros(N)
        for _, e in self.ex.iterrows():
            s = (e.start - START).total_seconds() / 60
            en = (e.end - START).total_seconds() / 60
            I = float(e.intensity)
            amp = 12 + 11 * I if e.type != "strength" else 9 + 8 * I
            up = np.clip((self.t_min - s) / 6.0, 0, 1)
            down = np.where(self.t_min > en, np.exp(-(self.t_min - en) / 9.0), 1.0)
            pulse = np.maximum(pulse, np.where(self.t_min >= s, amp * up * down, 0))
        hr = hr + pulse
        slow = np.cumsum(r.normal(0, 0.35, N)); slow = slow - pd.Series(slow).rolling(288 * 3, min_periods=1, center=True).mean().to_numpy()
        hr = hr + np.clip(slow, -6, 6) * awake
        self._hr_pre_steps = hr.copy()
        # small post-meal rise
        m = self.meals
        pm = np.zeros(N)
        for _, row in m.iterrows():
            t0 = (row.start - START).total_seconds() / 60
            x = (self.t_min - t0) / 40.0
            pm += 2.5 * np.where(x > 0, x * np.exp(1 - x), 0)
        hr = hr + pm
        eps = r.normal(0, 1.6, N)
        ar = np.zeros(N)
        for k in range(1, N):
            ar[k] = 0.8 * ar[k - 1] + eps[k]
        hr = hr + ar
        hr_sim = np.round(np.clip(hr, 48, 175))
        # real window: real heart rate (imputed gaps are marked)
        hr_final = hr_sim.copy()
        has_real = self.hr_real.notna().to_numpy()
        hr_final[has_real] = np.round(self.hr_real[has_real].to_numpy())
        self.hr_final = hr_final
        self.hr_origin = np.where(has_real & ~self.hr_imputed, "real", np.where(has_real, "imputed", "simulated"))

        # HRV (RMSSD, ms): sparse - most asleep buckets, a few awake-and-resting ones
        sl_prev = np.where(self.sleep_h_actual > 2, self.sleep_h_actual, self.sleep_h)[di]
        base_h = 37 + 4.5 * smooth(days, 22, 45) * (1 - smooth(days, 56, 62)) - 6.5 * smooth(days, 66, 91) - 9.0 * self.ill[di] - 7.5 * (stress_t - 0.5) - 2.0 * np.clip(7 - sl_prev, 0, 3)
        base_h = np.clip(base_h, 14, 70) * np.where(asleep, 1.25, 0.85)
        logsd = min(self.real["hrv_logsd"], 0.5)
        hrv = base_h * np.exp(r.normal(-0.5 * logsd ** 2, logsd * 0.65, N))
        p_have = np.where(asleep, 0.65, 0.025)
        have = r.random(N) < p_have
        self.hrv_final = np.where(have, np.round(np.clip(hrv, 6, 140), 1), np.nan)

        # SpO2
        sp = np.where(asleep, 95.7, 96.9) - 0.7 * self.ill[di] - 0.35 * smooth(days, 70, 91) + r.normal(0, np.where(asleep, 0.55, 0.4), N)
        # sleep dips
        dips = np.zeros(N)
        for i, d in enumerate(self.dates):
            lo, hi = d - pd.Timedelta(hours=3), d + pd.Timedelta(hours=10)
            ix = np.where((self.idx >= lo) & (self.idx < hi) & asleep)[0]
            if len(ix) > 20:
                for _ in range(int(r.integers(2, 6))):
                    s0 = int(r.choice(ix))
                    dips[s0:s0 + int(r.integers(1, 4))] += r.uniform(1.8, 3.6)
        sp = np.clip(sp - dips, 88.0, 99.5)
        self.spo2_final = np.round(sp, 1)

        # steps
        steps = np.zeros(N)
        work_h = (self.wd < 5) & (self.hour >= 8.5) & (self.hour < 17.5)
        commute = (self.wd < 5) & (((self.hour >= 7.95) & (self.hour < 8.5)) | ((self.hour >= 17.5) & (self.hour < 18.0)))
        lam = np.where(awake, 7.0, 0.0)
        lam = np.where(work_h & awake, 24.0, lam)
        lam = np.where(commute & awake, 260.0, lam)
        wend = (self.wd >= 5) & awake & (self.hour >= 9) & (self.hour < 21)
        lam = np.where(wend, 22.0, lam)
        lam = lam * np.exp(r.normal(0, 0.45, N))
        # daily targets
        targets = np.array([{"A": 7600, "B": 8700, "C": 6100, "D": 6300}[phase_of(i + 1)] for i in range(self.D)], float)
        targets = targets * np.where(self.weekend, 0.9, 1.0) * np.exp(r.normal(0, 0.14, self.D)) * (1 - 0.35 * self.ill)
        # exercise steps
        ex_steps = np.zeros(N)
        for _, e in self.ex.iterrows():
            ii = np.where((self.idx >= e.start) & (self.idx < e.end))[0]
            per = {"walking": 100, "running": 150, "cycling": 14, "strength": 14}.get(e.type, 40) * (0.85 + 0.08 * e.intensity) * 5
            ex_steps[ii] += per
        lam_sum = np.zeros(self.D)
        np.add.at(lam_sum, di, lam)
        ex_sum = np.zeros(self.D)
        np.add.at(ex_sum, di, ex_steps)
        k = np.clip((targets - ex_sum) / np.maximum(lam_sum, 1), 0.3, 3.0)
        lam = lam * k[di]
        steps = r.poisson(lam) + np.round(ex_steps * r.uniform(0.9, 1.1, N))
        steps = np.where(asleep, 0, steps)
        # real window: from active energy
        steps_final = steps.copy()
        steps_final[self.in_real] = self.steps_real[self.in_real]
        steps_final = np.where(asleep, 0, steps_final)
        self.steps_final = steps_final.astype(int)
        # simulated heart rate also rises a little with steps (outside logged exercise); the real window keeps the real heart rate
        sim_hr = self.hr_final.copy()
        walk_bump = np.clip(self.steps_final / 5.0 - 20, 0, 140) * 0.10 * (self.steps_final > 0)
        ex_mask = np.zeros(N, bool)
        for _, e in self.ex.iterrows():
            ex_mask |= (self.idx >= e.start) & (self.idx < e.end + pd.Timedelta(minutes=20))
        sim_hr = sim_hr + np.where(~ex_mask & awake, walk_bump, 0)
        has_real = self.hr_real.notna().to_numpy()
        sim_hr[has_real] = self.hr_final[has_real]
        self.hr_final = np.round(sim_hr)

    # ---------------------------------------------------------------- blood pressure
    def blood_pressure(self):
        r = self.rs(10)
        rows = []
        d = 0.0
        t = self.dates[0] + pd.Timedelta(hours=7.6)
        sod_by_day = self.meals.groupby(self.meals.start.dt.normalize()).sodium_mg.sum()
        while t < self.end:
            i = int((t.normalize() - START.normalize()).days)
            days = i + 1
            ph = phase_of(days)
            base_s = 135.0 - 3.0 * smooth(days, 22, 45) * (1 - smooth(days, 56, 62)) + 3.0 * smooth(days, 56, 64) * (1 - smooth(days, 70, 76)) + 11.0 * smooth(days, 68, 91)
            sod = float(sod_by_day.get(t.normalize(), 3500.0))
            sys = base_s + 2.2 * (sod - 3600) / 1000.0 + 6.5 * (self.stress[i] - 0.5) + 4.5 * float(self.miss_morn_any(i)) + 4.0 * self.ill[i] + r.normal(0, 3.5)
            dia = 84 + 0.5 * (sys - 135) + r.normal(0, 2.2)
            rows.append(dict(recorded_at=t, systolic_mmhg=int(round(sys)), diastolic_mmhg=int(round(min(dia, sys - 25)))))
            gap = float(np.clip(r.gamma(4.0, 0.65), 1.2, 5.5))
            t = (t.normalize() + pd.Timedelta(days=gap)).floor("D") + pd.Timedelta(hours=float(r.choice([7.5, 7.6, 21.2], p=[.4, .3, .3])), minutes=float(r.integers(0, 20)))
        self.bp = pd.DataFrame(rows)

    def miss_morn_any(self, i):
        x = self.med_log[(self.med_log.day_index == i) & (self.med_log.med == "amlodipine") & (self.med_log.status == "missed")]
        return len(x) > 0

    # ---------------------------------------------------------------- wellbeing, symptoms
    def logs(self):
        r = self.rs(11)
        rows = []
        gday = pd.Series(self.glucose_final, index=self.idx)
        gmean = gday.groupby(gday.index.normalize()).mean()
        gmax = gday.groupby(gday.index.normalize()).max()
        exday = self.ex.groupby(self.ex.start.dt.normalize()).apply(lambda x: float(((x.end - x.start).dt.total_seconds() / 60).sum()))
        for i, d in enumerate(self.dates):
            sleep = self.sleep_h_actual[i] if self.sleep_h_actual[i] > 2 else self.sleep_h[i]
            ex_min = float(exday.get(d, 0.0))
            gm = float(gmean.get(d, 8.5))
            # evening log
            t = d + pd.Timedelta(hours=21.5) + pd.Timedelta(minutes=float(r.normal(0, 25)))
            if t <= self.end:
                stress_self = int(np.clip(round(1 + 4 * self.stress[i] + r.normal(0, 0.45)), 1, 5))
                mood = int(np.clip(round(3.4 + 0.30 * (sleep - 6.5) - 1.5 * (self.stress[i] - 0.5) + 0.012 * ex_min - 0.12 * max(gm - 9.5, 0) + r.normal(0, 0.45) - 0.7 * self.ill[i]), 1, 5))
                energy = int(np.clip(round(3.2 + 0.32 * (sleep - 6.5) - 0.15 * max(gm - 9.5, 0) + 0.008 * ex_min + r.normal(0, 0.5) - 1.0 * self.ill[i]), 1, 5))
                rows.append(dict(recorded_at=t, mood=mood, stress_self=stress_self, sleep_quality=None, energy=energy, kind="evening"))
            # morning log (about 70% of days)
            t = d + pd.Timedelta(hours=7.05) + pd.Timedelta(minutes=float(r.normal(0, 18)))
            if t <= self.end and r.random() < 0.72:
                sq = int(np.clip(round(3.0 + 0.55 * (sleep - 6.5) + r.normal(0, 0.55)), 1, 5))
                rows.append(dict(recorded_at=t, mood=None, stress_self=None, sleep_quality=sq, energy=None, kind="morning"))
        self.wellbeing = pd.DataFrame(rows)

        # symptoms
        sy = []

        def add(t, typ, sev, dur, note):
            if t <= self.end:
                sy.append(dict(occurred_at=t, symptom_type=typ, severity=int(sev), duration_min=dur, note=note))
        for i, d in enumerate(self.dates):
            gm = float(gmean.get(d, 8.5))
            gx = float(gmax.get(d, 10.0))
            if r.random() < np.clip((gm - 9.6) / 7.0, 0, 0.5):
                add(d + pd.Timedelta(hours=float(r.choice([14.5, 16.0, 19.5]))), "fatigue", 2 if gm < 12 else 3, int(r.integers(60, 240)), "Tired and sluggish in the afternoon")
            if gx > 17.5 and r.random() < 0.4:
                add(d + pd.Timedelta(hours=float(r.choice([15.0, 21.0]))), "thirst", 2 if gx < 19 else 3, int(r.integers(60, 180)), "Very thirsty, drank a lot of water")
            if gx > 19.5 and r.random() < 0.4:
                add(d + pd.Timedelta(hours=22.5), "frequent_urination", 2, 180, "Up to pass urine several times tonight")
            if self.ph[i] in ("C", "D") and self.stress[i] > 0.75 and r.random() < 0.18:
                add(d + pd.Timedelta(hours=float(r.choice([10.0, 16.0]))), "headache", 2, int(r.integers(45, 150)), "Headache after a stressful stretch at work")
        # scripted
        add(self.dates[42] + pd.Timedelta(hours=19.75), "shaky_sweaty", 3, 25, "Shaky and sweaty at the end of the long walk; ate glucose sweets and biscuits, felt better in 20 minutes")
        add(self.dates[42] + pd.Timedelta(hours=20.4), "dizziness", 2, 20, "Slightly dizzy after the low")
        add(self.dates[77] + pd.Timedelta(hours=21.2), "tingling", 2, 45, "Tingling in the toes of the left foot, started after sitting for a while")
        add(self.dates[83] + pd.Timedelta(hours=23.0), "numbness", 3, 90, "Left foot numb from the toes to the ball of the foot, mostly at night. Right foot normal")
        add(self.dates[88] + pd.Timedelta(hours=21.0), "tingling", 3, 60, "Pins and needles in both feet, worse on the left")
        add(self.dates[85] + pd.Timedelta(hours=6.0), "blurred_vision", 2, 120, "Blurry when reading the phone this morning")
        sym = pd.DataFrame(sy).sort_values("occurred_at").reset_index(drop=True)
        self.symptoms = sym

    # ---------------------------------------------------------------- finalise
    def run(self):
        self.derive_real_window()
        self.daily_state()
        self.make_meals()
        self.script_overrides()
        self.add_real_meals()
        self.exercise_sessions()
        self.real_window_states()
        self.medications()
        self.sleep_mask()
        self.glucose()
        self.vitals()
        self.blood_pressure()
        self.logs()


# ====================================================================================== table-ready frames
def build_frames(g):
    """Return the Silver-shaped frames (plus provenance columns used to build Bronze) for loading."""
    r = np.random.default_rng(SEED + 99)
    idx = g.idx
    N = g.N
    F = {}
    real = g.real
    prof = real["prof"]
    F["user_profile"] = dict(
        user_id=TAN, display_name="Mr Tan", language="en", has_diabetes="yes", birth_year=int(prof["birth_year"]), gender="male", race=None,
        height_cm=float(prof["height_cm"]), weight_kg=float(prof["weight_kg"]), work_type="standing", work_days=[1, 2, 3, 4, 5], work_start="08:30", work_end="17:30",
        emergency_contact_name="Mdm Lim Mei Ling", emergency_contact_phone="+65 5550 0142", emergency_contact_relation="spouse",
        watch_model="Fitbit Sense", cgm_model="Dexcom G6", timezone=TZ, glucose_target_low=3.9, glucose_target_high=10.0,
        allergies_note="None known", conditions_note="Type 2 diabetes (diagnosed 2020); high blood pressure; high cholesterol")

    # medications and schedule
    meds, sched = [], []
    for m in g.meds:
        mid = str(uid("v2", "medication", m["key"]))
        meds.append(dict(id=mid, key=m["key"], name=m["name"], kind=m["kind"], strength=m["strength"], frequency=m["frequency"], description=m["description"],
                         start_date=str(m["start"].date()), end_date=(str(m["end"].date()) if m["end"] is not None else None), drug_ref=m["ref"]))
        for t, q, rel in m["times"]:
            sched.append(dict(id=str(uid("v2", "schedule", m["key"], t)), medication_id=mid, med=m["key"], dose_time=t, quantity=q, meal_relation=rel))
    F["medications"] = pd.DataFrame(meds)
    F["medication_schedule"] = pd.DataFrame(sched)
    sid = {(s["med"], s["dose_time"]): s["id"] for s in sched}
    mid = {m["key"]: m["id"] for m in meds}
    ml = g.med_log.copy()
    ml["id"] = [str(uid("v2", "dose", k, str(s))) for k, s in zip(ml.med, ml.scheduled_at)]
    ml["medication_id"] = ml.med.map(mid)
    ml["schedule_id"] = [sid[(a, b)] for a, b in zip(ml.med, ml.time)]
    F["medication_log"] = ml

    # labs (HbA1c and fasting glucose are real on 2026-09-22; the earlier ones are simulated history)
    lab = [("hba1c", "2025-09-25", 6.9, "%", False), ("hba1c", "2026-03-26", 7.1, "%", False), ("fasting_glucose", "2026-03-26", 7.6, "mmol/L", False),
           ("hba1c", "2026-09-22", 7.4, "%", True), ("fasting_glucose", "2026-09-22", 8.56, "mmol/L", True)]
    F["lab_results"] = pd.DataFrame([dict(id=str(uid("v2", "lab", t, d)), measured_at=pd.Timestamp(d + " 09:00", tz=TZ), test=t, value=v, unit=u, real=rl) for t, d, v, u, rl in lab])

    # watch
    asleep_min = np.where(g.asleep > 0, 5, 0).astype(int)
    w = pd.DataFrame(dict(recorded_at=idx, heart_rate_bpm=g.hr_final.astype(int), hrv_rmssd_ms=g.hrv_final, spo2_pct=g.spo2_final, steps=g.steps_final,
                          sleep_minutes=asleep_min, hr_origin=g.hr_origin))
    F["watch_readings"] = w

    # CGM: real Dexcom where it exists; sensor-change gaps (2 hours of warm-up every 10 days) and a few short dropouts in the simulated part
    c = pd.DataFrame(dict(recorded_at=idx, glucose_mmol=g.glucose_final, real=g.glucose_real))
    drop = np.zeros(N, bool)
    for dn in range(11, 80, 10):
        t0 = g.dates[dn - 1] + pd.Timedelta(hours=9.75)
        drop |= (idx >= t0) & (idx < t0 + pd.Timedelta(hours=2))
    for k in range(4):
        t0 = g.dates[int(r.integers(3, 70))] + pd.Timedelta(hours=float(r.uniform(1, 22)))
        drop |= (idx >= t0) & (idx < t0 + pd.Timedelta(minutes=int(r.integers(25, 50))))
    drop &= ~g.glucose_real
    F["cgm_readings"] = c[~drop].reset_index(drop=True)

    F["blood_pressure_readings"] = g.bp.assign(id=[str(uid("v2", "bp", str(t))) for t in g.bp.recorded_at])

    ex = g.ex.copy()
    F["exercise_logs"] = ex
    F["exercise_sets"] = g.ex_sets.copy()

    meals = g.meals.copy()
    meals["id"] = [str(uid("v2", "food", str(s), f)) for s, f in zip(meals.start, meals.food)]
    F["food_logs"] = meals

    sy = g.symptoms.copy()
    sy["id"] = [str(uid("v2", "symptom", str(t), s)) for t, s in zip(sy.occurred_at, sy.symptom_type)]
    F["symptom_logs"] = sy
    wb = g.wellbeing.copy()
    wb["id"] = [str(uid("v2", "wellbeing", str(t), k)) for t, k in zip(wb.recorded_at, wb.kind)]
    F["wellbeing_logs"] = wb
    return F


def summarise(g):
    idx = g.idx
    s = pd.DataFrame({"g": g.glucose_final, "hr": g.hr_final, "spo2": g.spo2_final, "steps": g.steps_final, "asleep": g.asleep}, index=idx)
    s["phase"] = [phase_of(int(d)) if int(d) < g.real_day0 or phase_of(int(d)) != "D" else "D_real" for d in g.day_no]
    s.loc[(s.phase == "D"), "phase"] = "D_sim"
    out = {}
    for p in ["A", "B", "C", "D_sim", "D_real"]:
        x = s[s.phase == p]
        fast = x[(x.index.hour >= 5) & (x.index.hour < 7)].g.mean()
        out[p] = dict(days=int(x.index.normalize().nunique()), glucose_mean=round(float(x.g.mean()), 2), tir=round(float(((x.g >= LOW) & (x.g <= HIGH)).mean() * 100), 1),
                      below=round(float((x.g < LOW).mean() * 100), 2), fasting_05_07=round(float(fast), 2), hr_mean=round(float(x.hr.mean()), 1),
                      hr_night=round(float(x[x.asleep > 0].hr.mean()), 1), steps_per_day=int(x.steps.sum() / max(x.index.normalize().nunique(), 1)),
                      sleep_h=round(float(x.asleep.sum() / 60 / max(x.index.normalize().nunique(), 1)), 2))
    return out


def main():
    np.seterr(over="ignore")
    ap = argparse.ArgumentParser()
    ap.add_argument("--backup", default=str(ROOT / "data/processed/db_backup_2026-10-05"))
    ap.add_argument("--out", default=str(ROOT / "data/processed/demo_v2"))
    ap.add_argument("--plots", action="store_true")
    a = ap.parse_args()
    real = load_real(a.backup)
    g = Gen(real)
    g.run()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    import pickle
    with open(out / "gen.pkl", "wb") as f:
        pickle.dump(g, f)
    summ = summarise(g)
    (out / "summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    print(json.dumps(summ, indent=1))
    print("buckets", g.N, "days", g.D, "meals", len(g.meals), "exercise", len(g.ex), "doses", len(g.med_log), "bp", len(g.bp), "symptoms", len(g.symptoms), "wellbeing", len(g.wellbeing))


if __name__ == "__main__":
    main()
