# E1 Data foundation: detail

This file holds the detail behind the E1 tasks so the backlogs can stay short. **E1 is the only epic that creates tables or loads reference and demo data.** Every later task reads and writes rows in tables that already exist. If a later task seems to need a new table, stop and ask the owner: it means E1 or the schema missed something, and the fix goes into E1.

Owners: Joely does E1-1, E1-2, E1-4 and E1-5. Hong Yi does E1-3. Layer map: [schema.md](../../specs/schema.md) section 0b.

## Who creates which tables

| Task | Layer | Tables | Owner |
|---|---|---|---|
| E1-1 | Raw and Bronze | `ingestion_events`, the private storage bucket layout (meals, medications, documents, exports) and `data/raw` | Joely |
| E1-2 | Silver and Reference | Every canonical user-data table and every lookup table in schema.md sections 2 to 9b and the Silver tables in 9c (`devices`, `health_goals`, `meal_analyses` and so on) | Joely |
| E1-3 | Gold and Operations | Aggregates, baselines, flags, patterns, memory facts, memory evidence, briefs and brief sections; `agent_runs`, `agent_steps`, `guardrail_events`, `conversations`, `messages`, `event_log`; the views `health_state`, `trends`, `adherence_summary`, `insight_context`, `timeline_events` | Hong Yi |

Order: E1-1 and E1-2 first and in parallel, then E1-3 (it links to the Silver tables), then E1-4 (loads the values).

## E1-1 Raw and Bronze

1. One script, `scripts/download_data.py`, fetches only the allowed subsets into gitignored `data/raw`: CGMacros, BIG IDEAs (3 to 5 participants: Dexcom, HR, EDA, TEMP, Food_Log, Demographics), NHANES files, Fitbit, 250k Medicines, Open Food Facts (SG/MY subset), Doctor Specialty and GlucoBench. Anything else needs the owner's OK ([data/README.md](../../../data/README.md)).
2. Log sizes and checksums. `data/README.md` lists each licence (CGMacros is CC BY-NC-SA 4.0).
3. A short profile per dataset: participants, rows, date span, missing values, units, sampling interval. It must answer: how many CGMacros diabetic participants have complete CGM and meals; whether 250k Medicines really has an interactions column; the BIG IDEAs HbA1c range.
4. Create `ingestion_events` (checksum, source type, timestamps, processing status, unique per user and checksum) and the private Supabase Storage layout. Originals are never overwritten. A user-requested deletion removes the object, marks the row deleted and is logged.

## E1-2 Silver and reference tables

1. Turn schema.md into migrations that apply to an empty Supabase database and roll back.
2. Constraints, enums and unique keys as specified. Row-level security on for every table, no policies.
3. Data dictionary (`docs/data_dictionary.md`): for every user-data field, the table, column, unit and source flag (manual, imported, simulated). It covers profile, conditions, allergies, medications and ingredients, doses, glucose, meals, workouts, sleep, wearable samples, symptoms, mood, blood pressure, labs, appointments, questions and memory.
4. schema.md and the layer map match the migrated tables exactly. If you must change schema.md, say so in the session log.

## E1-3 Gold and operations tables and views

1. Migrations for every table in the Gold and Operations rows of the layer map.
2. The five views carry calculation version, evidence window, freshness and quality status.
3. `event_log` is append-only for the app role.
4. No table or view uses `gold.`, `silver.` or `bronze.` as a prefix. The layer is a label in the layer map, not part of the name.

## E1-4 Ingestion: what is loaded, per source

Everything below is loaded once here. Imports are safe to run twice (unique on source plus external id).

| Source | What goes where | Rules |
|---|---|---|
| CGMacros (chosen diabetic participants) | CGM to `glucose_readings` (mmol/L, quality flag, native interval); meals and macros to meals tables; Fitbit heart rate and steps to `health_samples`; `bio.csv` to profile and `lab_results` | Dates shifted per person, stored in UTC. Row counts equal the source. 100 random glucose rows checked against the raw file |
| BIG IDEAs (3 to 5 participants) | Dexcom, HR, EDA, TEMP, food log and demographics | Heart rate downsampled to 1 minute. Rows marked `entry_source = demo_dataset` |
| Fitbit | Samples and sleep | A second watch format |
| NHANES | `population_priors` (percentiles by age, sex and diabetes) plus a persona-sampling table; dietary files feed foods with sodium and sugar | |
| GlucoBench | A fixture table | Insulin columns are discarded |
| 250k Medicines | `drug_reference`, `drug_aliases`, `drug_side_effects` (diabetes, blood pressure and lipid drugs first, at least 100 generics); interaction data loaded to `interaction_rules` with its source | Check first whether an interactions column exists and how many usable pairs. **If it does not, stop and raise it as a decision.** Searching "metformin" returns its aliases |
| Open Food Facts (SG/MY) | `foods` with sodium and sugar | At least 90% of seeded foods have sodium or are flagged unknown |
| Doctor Specialty | `routing_rules` | |
| Reference items | Preventive-care items and `data_sources` filled | Clinical thresholds and screening intervals need the owner's OK |

**Demo patient.** One real CGMacros diabetic participant's profile plus `seed_demo.py` (same seed, identical data) that builds 60 days: glucometer readings, doses with a weekend and evening miss pattern and one 4-day streak, mood, sleep and stress, blood pressure, workouts, symptoms, and a rising fasting-glucose drift in the last 3 weeks. Every simulated row is flagged and a disclosure list is generated ([prd.md](../../specs/prd.md) A8).

**Setup data.** `devices` rows for the connected watch, sensor and camera with last-synced times. `health_goals` rows for weekly moderate minutes and strength sessions, marked as defaults until a clinician sets them. The demo seed covers both. `replay.py` streams the demo data as if live, at normal and fast speed.

**Medicine knowledge index.** The 250k Medicines text is chunked and embedded (needs the AI gateway from E0-3). Twenty test names must retrieve the right drug.

## E1-5 Analysis data and baseline model (P1)

1. `meal_features` (macros, context, response iAUC and peak rise) and a daily feature table, documented.
2. Train and test split by participant with no leakage.
3. A simple baseline model with a model card (data, split, metric). It must beat predicting the mean on held-out participants. The artefact loads in the API and is labelled as a population model.
