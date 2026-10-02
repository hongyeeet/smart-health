#!/usr/bin/env python3
"""Profile every downloaded dataset and write data/dataset_profiles.md (E1-1).

Reads only data/raw (and unzips CGMacros into gitignored data/processed). Never edits a raw file.
Run after scripts/download_data.py:  python scripts/profile_data.py
"""
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "dataset_profiles.md"
lines = []


def w(s=""):
    lines.append(s)


def line_count(path):
    with open(path, "rb") as f:
        return sum(1 for _ in f) - 1


def pct(x):
    return f"{100 * x:.0f}%"


# ---------------------------------------------------------------- NHANES
def nhanes():
    w("## NHANES (manifest #1, #2; also 2011-2016 with the owner's OK)\n")
    w("CDC survey of US adults. Files are SAS XPORT; join every file on `SEQN`. Cycles downloaded: "
      "2011-12, 2013-14, 2015-16, 2017-18, 2021-23. The 10 minute-level accelerometer files (PAXMIN) are not downloaded.\n")
    w("| Cycle | Files | People in DEMO | Rows in glycohaemoglobin (HbA1c) file | Told by a doctor they have diabetes (DIQ010 = 1) |")
    w("|---|---|---|---|---|")
    for cyc in ["2011-2012", "2013-2014", "2015-2016", "2017-2018", "2021-2023"]:
        d = RAW / "nhanes" / cyc
        files = sorted(d.glob("*.xpt"))

        def rd(prefix):
            f = [x for x in files if x.stem.startswith(prefix)]
            return pd.read_sas(f[0], format="xport") if f else None
        demo, ghb, diq = rd("DEMO"), rd("GHB"), rd("DIQ")
        dm = int((diq["DIQ010"] == 1).sum()) if diq is not None and "DIQ010" in diq else "n/a"
        w(f"| {cyc} | {len(files)} | {len(demo):,} | {len(ghb):,} | {dm} |")
    w("\nWatch out: US population, one visit per person (no history). Values are used for starting percentiles "
      "(`population_priors`), never shown as targets. Codebooks are linked in `data/plan/nhanes_files.csv`.\n")


# ---------------------------------------------------------------- CGMacros
def cgmacros():
    out = ROOT / "data" / "processed" / "cgmacros"
    if not (out / "CGMacros").exists():
        zipfile.ZipFile(RAW / "cgmacros" / "CGMacros_dateshifted365.zip").extractall(out)
    base = out / "CGMacros"
    bio = pd.read_csv(base / "bio.csv")
    bio.columns = [c.strip() for c in bio.columns]
    a1c = bio["A1c PDL (Lab)"]
    rows = []
    for s in bio["subject"]:
        d = pd.read_csv(base / f"CGMacros-{int(s):03d}" / f"CGMacros-{int(s):03d}.csv", parse_dates=["Timestamp"])
        rows.append(dict(subject=int(s), a1c=a1c[bio.subject == s].iloc[0],
                         days=(d.Timestamp.max() - d.Timestamp.min()).total_seconds() / 86400,
                         cgm=max(d["Libre GL"].notna().mean(), d["Dexcom GL"].notna().mean()),
                         hr=d["HR"].notna().mean(), meals=int(d["Meal Type"].notna().sum()),
                         photos=int(d["Image path"].notna().sum())))
    r = pd.DataFrame(rows)
    t = r[r.a1c >= 6.5]
    w("## CGMacros (manifest #5)\n")
    w("One CSV per person, one row per minute: Libre glucose, Dexcom glucose (mg/dL, to be converted to mmol/L), "
      "Fitbit heart rate and activity, and meals with macros and a photo path. `bio.csv` has age, sex, BMI, HbA1c, "
      "fasting labs and three fingersticks. Licence CC BY-NC-SA 4.0 (non-commercial, share-alike, attribution).\n")
    w(f"- **{len(r)} participants**, {r.days.min():.1f} to {r.days.max():.1f} days each; HbA1c {a1c.min()} to {a1c.max()}.")
    w(f"- HbA1c under 5.7: {(a1c < 5.7).sum()}, 5.7 to 6.4: {((a1c >= 5.7) & (a1c < 6.5)).sum()}, **6.5 or more: {(a1c >= 6.5).sum()}**. "
      "The 6.5 line is our assumption, not a label in the dataset.")
    ok = t[(t.cgm >= 0.7) & (t.meals >= 10) & (t.days >= 5)]
    w(f"- **{len(ok)} of the {len(t)} with HbA1c 6.5 or more have complete data** (glucose in at least 70% of minutes, "
      f"at least 10 meals, at least 5 days). Subjects: {', '.join(str(x) for x in ok.subject)}.")
    w(f"- Among those: {t.meals.min()} to {t.meals.max()} meals, heart rate present {pct(t.hr.min())} to {pct(t.hr.max())} of minutes, "
      f"{t.photos.min()} to {t.photos.max()} meal photos.")
    w("\nWatch out: dates are shifted; a person has 7 to 19 days, so there is no long history; US foods only, "
      "no sodium column.\n")


# ---------------------------------------------------------------- BIG IDEAs
def bigideas():
    base = RAW / "big-ideas"
    demo = pd.read_csv(base / "Demographics.csv", encoding="utf-8-sig")
    w("## BIG IDEAs Lab (manifest #4)\n")
    w("Free-living adults wearing a Dexcom G6 CGM and an Empatica E4 research wristband. Only 5 of 16 people are downloaded, "
      "and only the Dexcom, heart rate, EDA, skin temperature, beat-to-beat interval (IBI) and food-log files (the "
      "accelerometer and blood-volume files are about 2.3 GB per person and are not needed).\n")
    w(f"- **HbA1c range of all 16 people: {demo.HbA1c.min()} to {demo.HbA1c.max()}. Nobody has diabetes.** (the data plan said 5.2 to 6.4; this version of the file says 5.3 to 6.4)")
    w("- Downloaded: " + ", ".join(sorted(p.name for p in base.iterdir() if p.is_dir())) + ".\n")
    w("| Person | HbA1c | Glucose rows (5-min) | First day | Last day | Heart-rate rows | IBI rows | EDA rows | Skin-temp rows | Food-log rows |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for p in sorted(x for x in base.iterdir() if x.is_dir()):
        n = p.name
        dx = pd.read_csv(p / f"Dexcom_{n}.csv", low_memory=False)
        g = dx[dx["Event Type"] == "EGV"]
        ts = pd.to_datetime(g["Timestamp (YYYY-MM-DDThh:mm:ss)"])
        a = demo.loc[demo.ID == int(n), "HbA1c"].iloc[0]
        first = open(p / f"Food_Log_{n}.csv", encoding="utf-8").readline()
        food = line_count(p / f"Food_Log_{n}.csv") + (0 if first.startswith("date") else 1)  # only participant 003 has no header row
        w(f"| {n} | {a} | {len(g):,} | {ts.min().date()} | {ts.max().date()} | {line_count(p / f'HR_{n}.csv'):,} | "
          f"{line_count(p / f'IBI_{n}.csv'):,} | {line_count(p / f'EDA_{n}.csv'):,} | {line_count(p / f'TEMP_{n}.csv'):,} | {food} |")
    w("\nWatch out: heart rate is about one reading per second (to be downsampled to 1 minute); `Food_Log` of participant 003 has no header row and 11 columns (the others have a header and 14); "
      "the Dexcom file starts with device metadata rows; EDA and temperature are 4 readings per second. "
      "Data came from the S3 mirror at version 1.1.2 and was verified against the 1.1.3 checksums.\n")


# ---------------------------------------------------------------- Fitbit
def fitbit():
    w("## Fitbit (Kaggle, manifest #14)\n")
    w("Two Fitabase exports from a 2016 survey study (CC0).\n")
    w("| Export | Files | People (daily activity) | Date span | People with heart rate | People with sleep | People with weight |")
    w("|---|---|---|---|---|---|---|")
    for exp in sorted((RAW / "fitbit").iterdir()):
        sub = next(exp.iterdir())

        def ids(name):
            f = sub / name
            return pd.read_csv(f, usecols=["Id"])["Id"].nunique() if f.exists() else 0
        da = pd.read_csv(sub / "dailyActivity_merged.csv")
        dates = pd.to_datetime(da.ActivityDate)
        w(f"| {exp.name} | {len(list(sub.glob('*.csv')))} | {da.Id.nunique()} | {dates.min().date()} to {dates.max().date()} | "
          f"{ids('heartrate_seconds_merged.csv')} | {ids('minuteSleep_merged.csv')} | {ids('weightLogInfo_merged.csv')} |")
    w("\nWatch out: 2016 data and a different device format from the demo patient's; sleep and weight are missing for many people. The data plan says 30 users; the files show 33 to 35 people per export, because some appear in only one table.\n")


# ---------------------------------------------------------------- 250k Medicines
def medicines():
    d = pd.read_csv(RAW / "250k-medicines-usage-side-effects-and-substitutes" / "medicine_dataset.csv", low_memory=False)
    side = [c for c in d.columns if c.startswith("sideEffect")]
    use = [c for c in d.columns if c.startswith("use")]
    sub = [c for c in d.columns if c.startswith("substitute")]
    w("## 250k Medicines (Kaggle, manifest #20)\n")
    w(f"- {len(d):,} rows x {len(d.columns)} columns: id, name, {len(sub)} substitute, {len(side)} sideEffect, {len(use)} use columns, "
      "and Chemical Class, Habit Forming, Therapeutic Class, Action Class.")
    w("- **There is no interactions column and no active-ingredient column.** The clash checker cannot use this file. "
      "Decision (owner, via Joely): use the openFDA drug-label `drug_interactions` text instead.")
    w(f"- Rows with at least one use listed: {pct(d[use].notna().any(axis=1).mean())}; with at least one side effect: {pct(d[side].notna().any(axis=1).mean())}.")
    m = d[d["name"].str.contains("metformin", case=False, na=False)]
    w(f"- Rows whose name contains 'metformin': {len(m)}. Names are brand names with strength and form (for example 'augmentin 625 duo tablet'); "
      "mapping to generic names has to come from elsewhere (openFDA or RxNorm).")
    w("- **Decision: the five `substitute*` columns are dropped when loading** (a substitute could look like medication advice). The raw file keeps them.\n")
    w("Watch out: source is given only as 'various sources', brand names may not match Singapore, not authoritative, no dosing.\n")


# ---------------------------------------------------------------- Open Food Facts
def off():
    cols = ["product_name", "countries_en", "energy_100g", "carbohydrates_100g", "sugars_100g", "fiber_100g", "salt_100g", "sodium_100g"]
    d = pd.read_csv(RAW / "world-food-facts" / "en.openfoodfacts.org.products.tsv", sep="\t", usecols=cols, low_memory=False)
    c = d["countries_en"].fillna("")
    sg, my = c.str.contains("Singapore", case=False), c.str.contains("Malaysia", case=False)
    sub = d[sg | my]
    w("## Open Food Facts (Kaggle, manifest #17)\n")
    w(f"- {len(d):,} products (163 columns; profiled: name, country, energy, carbs, sugars, fibre, salt, sodium).")
    w(f"- **Singapore: {int(sg.sum()):,} products; Malaysia: {int(my.sum()):,}; either: {len(sub):,}.**")
    has_na = sub["sodium_100g"].notna() | sub["salt_100g"].notna()
    w(f"- In the Singapore/Malaysia subset: sodium or salt present for {int(has_na.sum()):,} ({pct(has_na.mean()) if len(sub) else 'n/a'}), "
      f"sugars present for {pct(sub['sugars_100g'].notna().mean()) if len(sub) else 'n/a'}, name present for {pct(sub['product_name'].notna().mean()) if len(sub) else 'n/a'}.")
    w("- Target from the backlog (E1-4): at least 90% of seeded foods have sodium or are flagged unknown.\n")
    w("Watch out: packaged products only (not hawker dishes) and values per 100 g. **The Singapore/Malaysia subset is far too thin to be the whole `foods` table**: most rows lack sodium, so unknown values must be flagged unknown (the LLM estimates cover local dishes, D-011).\n")


# ---------------------------------------------------------------- Doctor specialty
def doctor():
    base = RAW / "doctor-specialist-recommendation-system"
    w("## Doctor Specialty (Kaggle, manifest #37)\n")
    w("Files: " + ", ".join(sorted(p.name for p in base.iterdir())) + ".\n")
    dv = pd.read_csv(base / "Doctor_Versus_Disease.csv", header=None, encoding="latin-1")
    w(f"- `Doctor_Versus_Disease.csv`: **{len(dv)} rows, no header, 2 columns (disease, specialty).** This is the only file we load, and only the disease-to-specialty pairs.")
    w("- Never load or index the symptom tables (`Symptom_Weights.csv`, `Original_Dataset.csv`): symptom-to-disease is diagnosis.")
    w("\nWatch out: weak provenance; use only for conditions the patient already has (routing, not diagnosis).\n")


# ---------------------------------------------------------------- GlucoBench
def glucobench():
    d = pd.read_csv(RAW / "glucobench-glucose-monitoring-and-lifestyle-data" / "GlucoBench_benchmark_dataset.csv", low_memory=False)
    ts = pd.to_datetime(d["timestamp"], errors="coerce")
    w("## GlucoBench (Kaggle, not in the manifest; allowed by the data policy)\n")
    w(f"- {len(d):,} rows x {len(d.columns)} columns; {d.user_id.nunique()} users; {ts.min()} to {ts.max()}.")
    w("- Columns present: " + ", ".join(d.columns[:20]) + ", ...")
    keep = ["glucose", "carbs", "heart_rate", "sleep_stage", "stress_level", "alcohol", "exercise_steps", "skin_temp", "gsr"]
    w("- Share of rows with a value: " + ", ".join(f"{k} {pct(d[k].notna().mean())}" for k in keep if k in d) + ".")
    w("- Every column above is filled in every row, which real sensor data rarely is: another sign it may be synthetic.")
    w("- **Fixture only.** No source is cited and the file is 2.76 MB, so it may be synthetic: never presented as evidence. Insulin columns are discarded on load.\n")


def main():
    w("# Dataset profiles\n")
    w(f"Generated by `scripts/profile_data.py` on {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC from the files in `data/raw`. "
      "Re-run the script to refresh. This is a description of the data, not a validation of it.\n")
    for fn in (nhanes, cgmacros, bigideas, fitbit, medicines, off, doctor, glucobench):
        print("profiling", fn.__name__, flush=True)
        fn()
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
