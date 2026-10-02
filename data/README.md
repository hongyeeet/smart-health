# Data

Everything data-related lives here. Documents live in `docs/`.

| Folder | Holds | Committed? |
|---|---|---|
| `data-map.md` | What data we need, what it is for, where it comes from (with links), what is missing, and what the user enters in the app | Yes |
| `plan/` | `smart_health_data_plan.xlsx`: datasets to use now, what is still missing, and data that strengthens the AI | Yes |
| `raw/` | Downloaded datasets, one subfolder per dataset (`cgmacros/`, `big-ideas/`, `nhanes/`, `fitbit/`, `medicines-250k/`, `open-food-facts/`, `glucobench/`, `doctor-specialty/`) | **No.** Large and licensed |
| `processed/` | Output of the importers (cleaned, converted, time-shifted) | **No** |
| `reference/` | Small seed tables (interactions, foods, preventive items), each with its source recorded | Yes |
| `knowledge/` | The approved corpus used for retrieval, with a `sources.csv` (manifest number and licence per source) | Yes |
| `demo/` | Small synthetic demo data (the simulated 60-day history) | Yes |

## Rules

- **Only the datasets in the hackathon download manifest and the GlucoBench Kaggle dataset are allowed.** Anything else needs the owner's approval first and is listed as "Needs your OK" in the plan workbook.
- **Never commit raw datasets.** Several carry licences (for example CGMacros is CC BY-NC-SA 4.0). The repo holds scripts and small samples only.
- **Simulated data must be marked** as simulated (`entry_source = 'demo_dataset'` or a simulated flag) and disclosed.
- **AI estimates** (such as meal macros) are labelled as estimates and are never mixed in with measured values.
- Every seeded reference row records its source in `data_sources`.

## Getting the data

The plan workbook lists each dataset with its link, the columns we use and its licence. The download script (backlog task E1-1) fetches the allowed subsets into `raw/`.

## What is downloaded (E1-1)

Fetched by `scripts/download_data.py` into the gitignored `raw/`; every file's size, checksum, source and licence is in `download_log.csv`. Profiles of each dataset are in `dataset_profiles.md` (`scripts/profile_data.py` regenerates it). `plan/dataset_links.md` lists the links.

| Manifest # | Dataset | In `raw/` | Licence | Note |
|---|---|---|---|---|
| 1, 2 | NHANES 2017-18 and 2021-23 | `nhanes/<cycle>/` | US public domain (CDC) | |
| (owner OK) | NHANES 2011-12, 2013-14, 2015-16, without the accelerometer minute files | `nhanes/<cycle>/` | US public domain (CDC) | Not in the manifest. Owner approved 2026-10-02 (reported by Joely); the 10 PAXMIN files stay excluded (about 17 GB). `plan/nhanes_files.csv` has the `allowed` flag |
| 5 | CGMacros | `cgmacros/` | **CC BY-NC-SA 4.0** (non-commercial, share-alike, attribution) | Checked against PhysioNet's SHA256SUMS |
| 4 | BIG IDEAs Lab, participants 003, 004, 009, 010, 011 | `big-ideas/` | Open Data Commons Attribution v1.0 | Dexcom, HR, EDA, TEMP, IBI, food log, demographics only. From PhysioNet's S3 mirror (v1.1.2), verified against the v1.1.3 checksums |
| 14 | Fitbit | `fitbit/` | CC0 | |
| 20 | 250k Medicines | `250k-medicines-.../` | CC BY-SA 4.0 | No interactions column. The five `substitute*` columns are dropped at load time |
| 17 | Open Food Facts | `world-food-facts/` | Database Contents License (DbCL 1.0) | |
| 37 | Doctor Specialty | `doctor-specialist-.../` | CC BY-SA 4.0 | Load only `Doctor_Versus_Disease.csv` |
| (policy) | GlucoBench | `glucobench-.../` | Apache 2.0 | Not in the manifest. Fixture only; insulin columns discarded |

**Drug interactions.** 250k Medicines has no interactions column. The owner decided (2026-10-02, reported by Joely) to use the openFDA drug-label `drug_interactions` text (`api.fda.gov/drug/label.json`, a live API, not in the manifest) as general information labelled `reference_matched`. Anything not found is "not checked". Supplements and TCM stay "not checked". This is loaded in E1-4.

## What is loaded into the database (E1-4)

Loaded by the scripts in `scripts/` (order and details: `docs/backlog/details/e1-4-handover.md`; run `python scripts/load_all.py`, a repeat run inserts nothing; `python scripts/verify_loaded.py` proves it against the raw files). The database holds **no raw files**: those stay in git-ignored `raw/`.

| Folder or file | What it is | Committed? |
|---|---|---|
| `demo/demo_config.json` | The demo end date (2026-10-02) shared by every loader and teammate | Yes |
| `demo/DISCLOSURE.md` | Generated list of everything simulated for the demo patient (table, rows, dates, rule, seed) | Yes |
| `demo/replay_feed.jsonl` | The last 3 hours of the demo patient's sensor data, held back for `scripts/replay.py` | Yes |
| `demo/knowledge_test_names.csv` | The 20 test names for the medicine search index (waits for E0-3) | Yes |
| `processed/` (git-ignored) | Working copies: unzipped CGMacros, `nhanes_top_drugs.csv`, staged medicine chunks | No |
| `raw/openfda/` (git-ignored) | The 101 raw openFDA label answers (public domain, CC0 1.0), logged in `download_log.csv` | No |

**Rules that held:** only cited or owner-approved sources; simulated rows are flagged (`entry_source = demo_dataset`, `external_id` starting `sim:`) and disclosed; GlucoBench is a test fixture only (`services/api/tests/fixtures/`, insulin removed); the five `substitute*` columns are never loaded; AI estimates are not stored yet (dataset meals keep their measured macros); nothing is called validated; the check-up intervals and default targets are placeholders pending clinical review.

