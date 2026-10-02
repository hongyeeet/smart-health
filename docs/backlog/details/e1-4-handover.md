# E1-4 handover: the data is loaded, start here

Written by Joely (with Claude) on 2026-10-02 for **Hong Yi** and **Damien**. It stands alone: you do not need the chat history. It says what is in the database now, how the demo patient differs from the mock, what is placeholder or missing, how to re-run or reset anything, and what still waits for E0-3. Companion documents: [e1-3-handover.md](e1-3-handover.md) (the tables), [../../specs/bronze-silver.md](../../specs/bronze-silver.md) (how every column links), [../../data_dictionary.md](../../data_dictionary.md) (every column), `data/demo/DISCLOSURE.md` (everything that is simulated), `data/dataset_profiles.md` (the datasets).

## 1. Status

E1-4 is **done and verified**. The medicine search index was split out into the new task **E1-6** (it needs the embedding model from E0-3, Hong Yi), so it no longer holds E1-4 open. All checks pass: `python scripts/verify_loaded.py` prints **74 of 74 checks passed**, and `python -m pytest services/api/tests/db -q` passes 12 tests.

## 2. What is in the database now (shared Supabase project, 180 MB of the free 500 MB)

| Table | Rows | What it holds |
|---|---|---|
| `users` | 24 | All demo users: 14 CGMacros people (with profiles), 5 BIG IDEAs and 5 Fitbit people (no profile: they are not known to have diabetes, and profiles only allow Type 2) |
| `patient_profiles` | 14 | The 14 CGMacros participants with HbA1c 6.5% or more. One is **"Mr Tan"** (see section 3) |
| `glucose_readings` | 244,466 | CGMacros Libre (218,355) and Dexcom (26,008), BIG IDEAs Dexcom, 42 fingersticks, 61 simulated glucometer readings. All mmol/L |
| `health_samples` | 164,650 | heart rate 122,142; active energy 14,475; skin temperature 9,432; EDA 9,432; HRV 5,783 (derived from beat intervals); steps 3,386 |
| `meals` / `meal_items` | 830 / 1,092 | Dataset meals with measured macros (`estimated_by = dataset`) plus 147 simulated meals for Mr Tan copied from his own real meals |
| `lab_results`, `body_measurements`, `sleep_sessions`, `cgm_sprints` | 92, 52, 169, 19 | Labs from `bio.csv`, weights, Fitbit and simulated sleep, one sensor period per person |
| `ingestion_events` | 83 | Bronze rows for the dataset files (`dataset_import`, no upload: files stay in `data/raw`) |
| Mr Tan only | | `patient_medications` 5, `dose_events` 268, `mood_checkins` 47, `workouts` 32, `blood_pressure_readings` 9, `symptom_logs` 3, `appointments` 6, `patient_preventive_status` 6, `devices` 3, `health_goals` 2, `conditions` 2, `family_history` 1, `consents` 1 |
| Reference | | `drug_reference` 101, `knowledge_documents` 94, `drug_aliases` 362, `drug_side_effects` 391, `interaction_rules` 238, `foods` 53, `routing_rules` 4, `preventive_items` 6, `population_priors` 617, `data_sources` 15 |
| Still empty (by design) | | `allergies`, `doctor_questions`, `prescription_scans`, `meal_analyses`, `notifications`, `refill_forecasts` (filled by real use) and `knowledge_chunks` (task E1-6, waits for E0-3) |

No table was created: Alembic is still at 0007.

## 3. The demo patient "Mr Tan"

- **Who:** CGMacros participant 046: a real, anonymous person in a public dataset. Id: `dc48e209-5731-5b3d-89d9-986242c54368`. Find him in SQL with `select user_id from patient_profiles where display_name = 'Mr Tan'`. His real data: Libre and Dexcom glucose, heart rate and active energy for about 10 days, 29 meals with measured macros, labs, weight. Everything else is simulated (a fixed seed, so it is identical every run) and listed in `data/demo/DISCLOSURE.md`.
- **Window:** the demo end date is stored in `data/demo/demo_config.json` (**2026-10-02**). His last real day is that date; the 50 days before are simulated.
- **Medicines:** Metformin 500 mg twice daily with food (08:00, 20:00), Amlodipine 5 mg (08:00), Atorvastatin 20 mg (22:00), plus a fish-oil supplement and a herbal tonic that have no drug match, so the clash check says "not checked". Interaction demo: **clarithromycin interacts with atorvastatin and with amlodipine** in the openFDA text (both are `interaction_rules`).

### Where the real data differs from the mock (Hong Yi: the mock and `apps/web` text should change, or the numbers should be read from the database)

| Item | Mock says | The database has |
|---|---|---|
| Age | 58 | **51** (real participant; `birth_year` 1975). Owner approved |
| HbA1c "4 months ago" | 4 months | The real HbA1c 7.4% is dated at the start of the sensor period (10 days ago); earlier simulated values 7.1% (about 6 months ago) and 6.9% (about a year ago) |
| Sensor sprint | day 9 of 14 | Started 22 Sep, still open: day 11 on 2 Oct |
| Time in range, last 24 h / week | 78% / 71% | Real 10-day time in range (3.9 to 10.0 mmol/L) is **64%** (mean 9.6) |
| Fasting last 7 mornings | 7.1 7.3 7.2 7.6 7.8 7.5 7.9 | Real morning sensor values 6.3 to 9.1 (about 7.4 on average); the simulated glucometer fasting trend rises from about 6.8 to 7.5 |
| Missed doses | Friday and Sunday evening metformin | Missed 27 Sep (Sunday, "forgot") and 29 Sep (Tuesday, "away from home"); 2 unconfirmed; **24 of 28 taken** as in the mock |
| Sleep, last night / 7-night average | 5 h 50 / 6 h 10 | 5 h 50 / about 6 h 16 |
| Steps today / 7-day average | 5,840 / 6,300 | 5,840 / about 6,230 (baseline about 8,000) |
| Moderate minutes per week | 55 so far; 140, 120, 95, 70 | Same |
| Care plan | eye overdue, foot due in 3 weeks, review in 9 days, flu not recorded | Same (appointments and preventive status are seeded) |
| Mood / stress last evening | 3 / 4 | 3 / 4 |

## 4. What is placeholder, pending review, or missing

| Item | Status |
|---|---|
| `preventive_items` (eye 12, foot 12, kidney 12, HbA1c 6, flu vaccination 12, diabetes review 6 months) and the default targets on Mr Tan's profile (fasting 4.0 to 7.0, after meals up to 10.0, HbA1c up to 7.0) | **Placeholders, clinical review pending.** Hong Yi approved them as placeholders on 2026-10-02; `source = 'Smart Health team placeholder (clinical review pending)'` |
| Clarithromycin in the drug list | Added as the demo drug (owner-approved, D-033) |
| `routing_rules` | **Only 4 rows** (diabetes and hypoglycaemia to endocrinologist; high blood pressure and heart attack to cardiologist). The source file has nothing for eye, foot, kidney or lipids, and the owner agreed to leave those out. **Damien (E15): healthcare preparation has no routing for those complications** |
| `foods` | 53 Singapore/Malaysia packaged products; **only 13 have sodium**, the other 40 are flagged `sodium_unknown`. No local dishes (the AI estimate covers dishes, D-011) |
| `interaction_rules` | 238 pairs from **text matching** in openFDA labels: `severity = unknown`, unreviewed, may over-match (a label that says "not studied with X" still names X). 7 drugs have no label (aspirin, cetirizine, docusate, fluticasone nasal, hydrocodone, hydroxyzine, brimonidine), so they are "not checked". Show the fixed "Possible interaction ... check with your pharmacist" wording only |
| `drug_aliases` / `drug_side_effects` | Only single-ingredient products of the 101 drugs (56 drugs have 250k product names); combination products are skipped; a side effect needs to be listed for at least 30% of a drug's products. Substitute columns were never loaded |
| CGMacros glucose | The file holds one reading per minute that are smooth interpolations of 15-minute (Libre) and 5-minute (Dexcom) sensor readings; stored as given with the real device interval |
| Other 13 CGMacros people, BIG IDEAs, Fitbit | Thinned to fit the free database: Libre glucose only, heart rate every 5th minute, EDA and skin temperature 5-minute means, Fitbit heart rate 5-minute means. Only Mr Tan has everything |
| BIG IDEAs participant 003 food log | No header and only calories and carbs can be mapped; the other four have the full macros. Meal types are derived from the time of day |
| `population_priors` | Participant percentiles, **not survey-weighted** (US adults aged 40 to 69; never shown as targets). Some lipid metrics are missing for some cycles: HDL, LDL and triglycerides for 2011 to 2014, HDL and triglycerides for 2021 to 2023 (the files or columns are not in the download) |

## 5. How to run, check and reset

```bash
python scripts/load_all.py            # every loader in order; a repeat run must insert 0 rows
python scripts/verify_loaded.py       # 74 checks, recomputed from the raw files
python -m pytest services/api/tests/db -q
python scripts/replay.py --speed 60   # stream the last 3 hours of Mr Tan's sensor data as if live (--speed 0 instant)
python scripts/replay.py --reset      # remove the replayed rows so it can be played again
python scripts/ingest_knowledge.py    # re-stage the medicine chunks and test names (no embedding)
```

- Order: `seed_data_sources`, `import_nhanes_priors`, `fetch_openfda` (needs the network; raw answers are kept in `data/raw/openfda/` and logged in `data/download_log.csv`), `seed_reference`, `import_cgmacros`, `import_bigideas`, `import_fitbit_kaggle`, `seed_demo`. The replay tool is separate.
- Every row has a stable id made from its natural key (`etl_common.uid`), so loaders never duplicate. **Do not change an end date and re-run the loaders on a loaded database**: ids of simulated doses contain their dates, so a different end date would add a second set. A shared database has one end date (`data/demo/demo_config.json`).
- Replay rows are `entry_source = 'replay'` and only add data; the app's own threshold logic must react to them as to any reading.

## 6. Not built yet, and what waits on E0-3

1. **Date refresh for demo day (Nov 3).** All demo data ends on 2026-10-02. A small `shift_demo_dates` tool (add N days to every timestamp and date of the demo users, update `demo_config.json` and the replay feed) is **not built**. Without it the demo will look a month old, so decide before the demo. It is a one-task follow-up.
2. **Medicine knowledge index = task E1-6** (needs Hong Yi's E0-3; **E4-1, the medicine explainer, should list E1-6 under Needs first**): `python scripts/ingest_knowledge.py --stage` has produced 667 chunks for 97 drugs (`data/processed/knowledge_chunks_staging.jsonl`) and 20 test names (`data/demo/knowledge_test_names.csv`: 8 generic, 7 brand or product names such as Eliquis and Invokana, 5 misspellings). When the gateway provides `embed(texts) -> list of vectors of size EMBED_DIM` (importable as `app.llm.gateway.embed`), run `--embed`, then `--test`; all 20 must find the right drug. `EMBED_DIM` is still the placeholder 1024.
3. **GlucoBench** is a test fixture only: `services/api/tests/fixtures/glucobench_sample.csv` (1,000 rows, insulin columns removed), never loaded into the database.

## 7. Decisions made in this task (all `Pending` owner confirmation in `project-memory.md`)

- **Approved by Hong Yi on 2026-10-02 (reported by Joely):** (1) the check-up interval placeholders and default targets; (2) clarithromycin as the demo drug; (3) only 4 routing rows; (4) demo patient participant 046, real age 51.
- **Free-plan size guard:** thin everyone except Mr Tan; database 180 MB.
- **Drug list from cited data:** top 100 single-ingredient generic drugs taken by NHANES diabetic participants (cycles 2011 to 2018, because 2021-23 publishes no drug names), insulin and supplements excluded, plus clarithromycin.
- **Simulated rows:** flagged `entry_source = demo_dataset` with an `external_id` starting `sim:`; tables without a source column are all-simulated for the demo user; disclosure in `data/demo/DISCLOSURE.md`.
- **Times:** clock times in the datasets are read as Singapore local time and stored in UTC; each person's last day is shifted to the demo end date.
- **No profile for non-diabetic people; NHANES persona-sampling table skipped; GlucoBench fixture only.**
- **The medicine index was split into the new task E1-6** (Joely, 2026-10-02), so E1-4 is done and E1-6 waits for E0-3.
