# Data model v2: data dictionary and mapping

Status: **proposal, not migrated yet.** The live database still has the old 67-table schema; `docs/data_dictionary.md` is generated from it and will change when the migration runs. Revised on 2026-10-04 after Joely's review (the changes are listed below). Owner confirmation of the revision is pending.

Goal: replace about 35 Silver tables with 12 plain tables the whole team can hold in their heads, and put the effort into one Gold dataset, the **master timeline**, that tells the story of a user's day.

The document is ordered like the data flows: **Bronze, then Silver, then Gold.**

## Changes in the 2026-10-04 revision

| Area | Change |
|---|---|
| Lab results | Only three tests are kept: **HbA1c (%)**, **fasting glucose (mg/dL or mmol/L)** and **fasting insulin (mcU/mL)**. All other test types are removed. |
| Watch readings | **Added** heart rate variability (`hrv_rmssd_ms`), blood pressure (`systolic_mmhg`, `diastolic_mmhg`) and body temperature (`body_temp_c`). **Kept**: heart rate, SpO2, steps, sleep and the watch's activity score. **Removed**: the watch's stress score (`stress_watch`). |
| Nutrition | `food_logs` gains **fibre** (`fibre_g`) and **sodium** (`sodium_mg`); the Gold tables carry them. |
| User profile | `user_profile` gains **gender** and **ethnicity**. |
| Gold | Every Gold table is written out column by column (the previous version described most of them in prose). |
| Mapping and decisions | Sections 6 to 8 are updated to match: blood pressure is no longer dropped, nutrition keeps fibre and sodium, and lab tests other than the three are dropped. |
| Data gaps | Blood pressure and SpO2 do not exist in any cited dataset. They will be simulated and marked `demo_dataset` (accepted by Joely, 2026-10-04). |

## 0. Conventions (apply to every table)

- All times are UTC (`timestamptz`). The user's timezone is stored once in `user_profile.timezone`; local time is derived in Gold.
- Glucose from the CGM is stored in **mmol/L** `numeric(4,1)`. Conversion to mg/dL happens only in the API. A fasting-glucose **lab** value keeps the unit it was reported in (`mg/dL` or `mmol/L`); Gold converts it to mmol/L.
- Every table has `id uuid` (primary key), `user_id uuid` (-> `users`), `created_at`. Tables a person can edit also have `updated_at` and `deleted_at` (soft delete).
- Every row has a **`source`** using the existing `entry_source` values (`manual`, `watch`, `cgm`, `llm_estimate`, `scan`, `file_import`, `replay`, `system`, `demo_dataset`). `demo_dataset` keeps marking simulated or imported data, so the demo-honesty rule survives.
- `NULL` means "no data", never zero. The one deliberate exception is watch `sleep_minutes` and `steps`: `0` means "the watch was worn and recorded none".
- `1-5` scales: 1 = lowest, 5 = highest. Labels for the frontend: mood (very low ... very good), stress (calm ... very stressed), sleep quality (very poor ... excellent), energy (exhausted ... energised), intensity (very light ... all-out), feeling (awful ... great), symptom severity (barely noticeable ... severe).

## 1. Layers

| Layer | Tables | Notes |
|---|---|---|
| Bronze | `ingestion_events` | One row per raw input as received: a watch batch, a CGM file or push, a meal photo, a prescription scan. Never edited. Keeps the raw payload (or `object_key` to it) plus checksum for idempotency. |
| Silver | 12 tables, section 3 | Typed, cleaned, one row per fact. Rows entered by hand in a form are Bronze and Silver in one step (the form is the raw record). Rows from the watch, CGM, photo or scan keep a link back to their `ingestion_events` row. |
| Gold | timeline plus derived tables, section 4 | Rebuilt from Silver. Never written to by the app. |

---

## 2. BRONZE

### `ingestion_events` (kept as is)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id` | uuid | yes | primary key |
| `user_id` | uuid | yes | -> `users` |
| `source_type` | text | yes | `watch_batch`, `cgm_batch`, `meal_photo`, `meal_text`, `prescription_scan`, `lab_document`, `file_import` |
| `object_key` | text | no | where the raw payload sits in private storage |
| `checksum` | text | yes | unique per user; re-sending a batch is a no-op |
| `received_at` | timestamptz | yes | |
| `source_recorded_at` | timestamptz | no | |
| `source_timezone` | text | no | |
| `content_type` | text | no | |
| `schema_version` | text | yes | |
| `processing_status` | text | yes | `received`, `processed`, `failed`, `deleted`; the only column allowed to change |
| `entry_source` | entry_source | yes | |
| `created_at` | timestamptz | yes | |

---

## 3. SILVER

### 3.1 One-time records

#### `user_profile` (one row per user)

| Column | Type | Required | Notes |
|---|---|---|---|
| `user_id` | uuid | yes | primary key, -> `users` (identity stays in `users`) |
| `language` | text | yes | BCP-47 code, e.g. `en`, `zh-Hans` |
| `has_diabetes` | enum `yes` / `no` / `not_sure` | yes | |
| `birth_year` | smallint | yes | frontend: number input (replaces the age picker); age is computed |
| `gender` | enum `female` / `male` / `other` / `prefer_not_to_say` | no | **new**. Optional. Gold uses `female` and `male` to pick the matching typical-value tables (`population_priors.sex`); the other values simply get no match |
| `ethnicity` | text | no | **new**. Optional free text so any dataset's wording maps without loss (CGMacros uses "African American Black", "Hispanic/Latino", "White"). The frontend offers suggestions, for example Chinese, Malay, Indian, Eurasian, White, Black or African, Hispanic or Latino, Other. Treat as sensitive personal data: recommended not to send to any AI model unless a feature needs it |
| `height_cm` | numeric(4,1) | no | |
| `weight_kg` | numeric(5,1) | no | |
| `weight_updated_at` | timestamptz | no | set whenever `weight_kg` changes |
| `work_week` | enum `desk` / `mixed` / `on_feet` / `physical` / `shift` / `not_working` | no | typical work week |
| `work_hours_per_week` | smallint | no | |
| `emergency_contact_name` | text | no | |
| `emergency_contact_phone` | text | no | |
| `emergency_contact_relation` | text | no | |
| `watch_brand`, `watch_model` | text | no | free text with suggestions in the frontend |
| `cgm_brand`, `cgm_model` | text | no | |
| `timezone` | text | yes | IANA name, default from the browser |
| `glucose_target_low`, `glucose_target_high` | numeric(3,1) | yes | mmol/L, default 3.9 and 10.0; used for time in range |
| `allergies_note`, `conditions_note`, `family_history_note` | text | no | free text; replaces three tables |
| `created_at`, `updated_at` | timestamptz | yes | |

#### `medications` (one row per medicine the user takes)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id`, `user_id` | uuid | yes | |
| `name` | text | yes | as the user says it, e.g. "Metformin" |
| `dose_amount` | numeric | no | e.g. 500 |
| `dose_unit` | text | no | `mg`, `units`, `tablet` |
| `times_per_day` | smallint | yes | |
| `dose_times` | `time[]` (local time) | no | e.g. `{08:00, 20:00}`; the "timing" |
| `timing_note` | text | no | "with food", "before bed" |
| `description` | text | no | what it is for |
| `start_date`, `end_date` | date | no | `end_date` empty = still taking |
| `active` | boolean | yes | |
| `source` | entry_source | yes | `manual` or `scan` |
| `prescription_scan_id` | uuid | no | -> `prescription_scans` (kept, section 5) |
| `drug_reference_id` | uuid | no | -> `drug_reference` (kept) |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | | |

#### `medication_log` (dose log: one row per scheduled or ad-hoc dose)

Replaces `dose_events`. Rows are generated from `medications.dose_times` each day, then updated when the user confirms.

| Column | Type | Required | Notes |
|---|---|---|---|
| `id`, `user_id` | uuid | yes | |
| `medication_id` | uuid | yes | -> `medications` |
| `scheduled_at` | timestamptz | no | empty for an extra, unscheduled dose |
| `taken_at` | timestamptz | no | empty until taken |
| `status` | enum `scheduled` / `taken` / `late` / `missed` / `skipped` | yes | `late` = taken more than 60 min after `scheduled_at`; a job flips untaken rows to `missed` after the window |
| `miss_reason` | enum `forgot` / `side_effects` / `felt_fine` / `ran_out` / `other` | no | |
| `note` | text | no | |
| `source` | entry_source | yes | |
| `created_at`, `updated_at` | timestamptz | yes | |

#### `lab_results` (kept, cut to three tests)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id`, `user_id` | uuid | yes | |
| `measured_at` | timestamptz | yes | date of the sample |
| `test` | enum `hba1c` / `fasting_glucose` / `fasting_insulin` | yes | **changed**: only these three tests |
| `value` | numeric | yes | |
| `unit` | text | yes | **changed**, fixed per test: `hba1c` = `%`; `fasting_glucose` = `mg/dL` or `mmol/L` (as reported); `fasting_insulin` = `mcU/mL` |
| `ref_low`, `ref_high` | numeric | no | |
| `source` | entry_source | yes | |
| `ingestion_event_id` | uuid | no | -> `ingestion_events` |
| `created_at`, `deleted_at` | timestamptz | | |

`fasting_insulin` is a **blood test** (the fasting level), not insulin dosing. Dosing stays out of scope (PRD A9).

#### `consents` (kept as is)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id`, `user_id` | uuid | yes | |
| `kind` | enum | yes | what was agreed to |
| `version` | text | yes | |
| `granted_at` | timestamptz | yes | |
| `revoked_at` | timestamptz | no | |

Minimal record of what the user agreed to. Health data needs this even in a demo.

### 3.2 Passive: watch and CGM

#### `watch_readings` (one row per user per 5-minute bucket, delivered in batches)

The watch syncs in **batches** (a few times a day, or one big upload); one batch is one `ingestion_events` row with `source_type = 'watch_batch'`. Each row covers one 5-minute bucket and holds what happened *in that bucket*, not a running total. That is how "sleep is 0 all day and grows overnight" works: `sleep_minutes` is 0 in daytime buckets and 1-5 in buckets where the user was asleep. Daily totals and running totals are computed in Gold, so batches can arrive late or out of order and nothing needs correcting.

| Column | Type | Required | Notes |
|---|---|---|---|
| `id`, `user_id` | uuid | yes | |
| `recorded_at` | timestamptz | yes | bucket start, aligned to 5 minutes; unique with `user_id` (upsert makes re-sent batches harmless) |
| `heart_rate_bpm` | smallint | no | average over the bucket |
| `hrv_rmssd_ms` | numeric(5,1) | no | **new**. Heart rate variability (RMSSD, milliseconds) over the bucket; watches report it only now and then, so it is empty in most buckets |
| `spo2_pct` | numeric(4,1) | no | blood oxygen, average |
| `systolic_mmhg`, `diastolic_mmhg` | smallint | no | **new**. Blood pressure; a spot reading, so empty in most buckets |
| `body_temp_c` | numeric(4,1) | no | **new**. Body temperature in degrees Celsius; wrist devices measure skin temperature |
| `steps` | integer | no | steps taken inside the bucket |
| `sleep_minutes` | smallint | no | 0-5: minutes asleep inside the bucket |
| `activity_level` | smallint | no | 0-4 from the watch (0 still ... 4 vigorous); the vendor's own score |
| `ingestion_event_id` | uuid | yes | -> `ingestion_events` (the batch) |
| `source` | entry_source | yes | `watch`, `replay` or `demo_dataset` |
| `created_at` | timestamptz | yes | |

The watch's own stress score (`stress_watch`) is not kept. Stress comes from `wellbeing_logs.stress_self`.

#### `cgm_readings` (continuous glucose; one row per reading)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id`, `user_id` | uuid | yes | |
| `recorded_at` | timestamptz | yes | unique with `user_id` |
| `glucose_mmol` | numeric(4,1) | yes | |
| `source` | entry_source | yes | `cgm`; a manual finger-prick is allowed as `manual` so it shows on the same timeline |
| `quality_ok` | boolean | yes | false for sensor warm-up or error readings; Gold ignores those |
| `ingestion_event_id` | uuid | no | |
| `created_at`, `deleted_at` | timestamptz | | |

CGM sensors report every 5 or 15 minutes. Gold does **not** interpolate; gaps stay `NULL` and are flagged.

### 3.3 Active: logged by the user

#### `exercise_logs`

| Column | Type | Required | Notes |
|---|---|---|---|
| `id`, `user_id` | uuid | yes | |
| `start_at`, `end_at` | timestamptz | yes | `end_at` after `start_at` |
| `type` | enum | yes | `strength` / `walking` / `running` / `cycling` / `swimming` / `hiit` / `sports` / `yoga_pilates` / `stretching_mobility` / `dance` / `household_gardening` / `other` |
| `activity` | text | no | the specific thing, e.g. "badminton", "leg day" |
| `energy_system` | enum `aerobic` / `anaerobic` / `mixed` | no | prefilled from `type`, editable (strength and hiit lean anaerobic) |
| `intensity` | smallint (1-5) | yes | |
| `feeling` | smallint (1-5) | no | how it felt afterwards |
| `note` | text | no | |
| `source` | entry_source | yes | |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | | |

#### `exercise_sets` (optional child, only for `type = strength`)

Keeps the E7-5 strength tracker. Existing `workout_sets` columns carry across; only the parent key and names change.

| Column | Type | Required | Notes |
|---|---|---|---|
| `id`, `user_id` | uuid | yes | |
| `exercise_log_id` | uuid | yes | -> `exercise_logs` |
| `set_order` | smallint | yes | |
| `exercise_name` | text | yes | |
| `reps` | smallint | no | |
| `weight_kg` | numeric(5,1) | no | |
| `rpe` | numeric(3,1) | no | |
| `created_at` | timestamptz | yes | |

#### `food_logs` (nutrition)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id`, `user_id` | uuid | yes | |
| `start_at`, `end_at` | timestamptz | yes | when eating began and finished; `end_at` defaults to `start_at` + 15 min |
| `meal_type` | enum `breakfast` / `lunch` / `dinner` / `snack` / `drink` | no | |
| `food` | text | yes | description, e.g. "chicken rice, half portion" |
| `protein_g`, `carbs_g`, `fat_g`, `sugar_g` | numeric(5,1) | no | `sugar_g` is part of `carbs_g` |
| `fibre_g` | numeric(5,1) | no | **new**. Dietary fibre, also part of `carbs_g` |
| `sodium_mg` | numeric(6,0) | no | **new**. Sodium in milligrams (salt is about 2.5 times sodium) |
| `kcal` | numeric(6,0) | no | optional |
| `estimated_by` | enum `user` / `llm_text` / `llm_photo` / `database` | yes | who produced the numbers; macros are LLM estimates, shown as such |
| `photo_ingestion_id` | uuid | no | -> `ingestion_events` (the meal photo and raw LLM output) |
| `source` | entry_source | yes | |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | | |

`meal_items` and `meal_analyses` are folded in: the LLM's raw answer lives in `ingestion_events`, and the totals live here.

#### `symptom_logs`

| Column | Type | Required | Notes |
|---|---|---|---|
| `id`, `user_id` | uuid | yes | |
| `occurred_at` | timestamptz | yes | default now, editable |
| `symptom_type` | enum | yes | `numbness` / `tingling` / `blurred_vision` / `fatigue` / `thirst` / `frequent_urination` / `dizziness` / `headache` / `shaky_sweaty` / `nausea` / `foot_pain` / `slow_healing_wound` / `other` |
| `symptom_name` | text | no | when `other` |
| `severity` | smallint (1-5) | yes | "how strong" |
| `duration_min` | integer | no | |
| `note` | text | no | frontend prompt: "Record which part of your body felt numbness" |
| `source` | entry_source | yes | |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | | |

#### `wellbeing_logs` (mood and sleep quality)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id`, `user_id` | uuid | yes | |
| `recorded_at` | timestamptz | yes | default now, editable |
| `mood` | smallint (1-5) | no | |
| `stress_self` | smallint (1-5) | no | what the user feels |
| `sleep_quality` | smallint (1-5) | no | how the last sleep felt; compare with the watch's measured sleep |
| `energy` | smallint (1-5) | no | |
| `note` | text | no | |
| `source` | entry_source | yes | |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | | |

At least one of the four scores must be present.

---

## 4. GOLD

Gold is rebuilt from Silver and never edited by the app. The master timeline is the foundation; everything else reads from it.

### 4.1 `timeline_5min`: the master temporal dataset

One row per user per 5-minute bucket, from the user's first data to now. Every Silver source is lined up on the same clock, so any question that crosses sources ("what was my heart rate when glucose spiked?") is a single-row or small-window query.

**How it is built.** A regular SQL view `v_timeline_5min` defines it (`generate_series` grid left-joined to each source). Because the "time since last meal / exercise / dose" columns need as-of lookups that are slow to recompute, it is also kept as a table `timeline_5min`. After each ingested batch, the days it touches are deleted and rebuilt from the view. The view is the source of truth; the table is a cache.

Primary key: (`user_id`, `bucket_start`). Every column except the key is empty when there is no data.

| Group | Column | Type | Meaning |
|---|---|---|---|
| Key | `user_id` | uuid | |
| | `bucket_start` | timestamptz | UTC |
| Clock | `local_date` | date | from `user_profile.timezone` |
| | `local_time` | time | |
| | `hour_of_day` | smallint | 0-23 local |
| | `weekday` | smallint | 1 = Monday ... 7 = Sunday |
| | `days_since_start` | integer | since the user's first data |
| Watch | `heart_rate_bpm` | smallint | from `watch_readings` |
| | `hrv_rmssd_ms` | numeric(5,1) | **new** |
| | `spo2_pct` | numeric(4,1) | |
| | `systolic_mmhg`, `diastolic_mmhg` | smallint | **new**, spot readings |
| | `body_temp_c` | numeric(4,1) | **new** |
| | `steps` | integer | |
| | `sleep_minutes` | smallint | |
| | `activity_level` | smallint | the watch's 0-4 score |
| Watch, running | `steps_day_cum` | integer | running total since local midnight |
| | `sleep_min_night_cum` | integer | running total since the sleep period began, so "sleep rises overnight" is visible |
| Watch, derived | `hr_vs_baseline` | numeric(5,1) | `heart_rate_bpm` minus the user's median at this `state` and hour (from `baselines`) |
| | `hrv_vs_baseline` | numeric(5,1) | **new**, same idea for HRV |
| | `temp_vs_baseline` | numeric(3,1) | **new**, same idea for body temperature |
| CGM | `glucose_mmol` | numeric(4,1) | average of the bucket's readings |
| CGM, derived | `glucose_delta_5m`, `glucose_delta_30m` | numeric(4,1) | change since 5 and 30 min ago |
| | `glucose_rate_mmol_per_h` | numeric(4,1) | slope over the last 30 min |
| | `glucose_zone` | enum | `low` (< target low), `in_range`, `high` (> target high), `very_high` (> 13.9) |
| | `has_cgm`, `has_watch` | boolean | data-present flags; gaps stay visible |
| Food, current | `eating_now` | boolean | bucket overlaps a `food_logs` interval |
| | `food_log_id` | uuid | |
| Food, as-of | `last_food_log_id` | uuid | most recent meal at or before this bucket |
| | `min_since_meal_start`, `min_since_meal_end` | integer | |
| | `last_meal_carbs_g`, `last_meal_protein_g`, `last_meal_fat_g`, `last_meal_sugar_g` | numeric(5,1) | copied from that meal for easy filtering |
| | `last_meal_fibre_g` | numeric(5,1) | **new** |
| | `last_meal_sodium_mg` | numeric(6,0) | **new** |
| | `last_meal_type` | enum | |
| | `meal_window` | enum | `pre_meal` (0-30 min before the next meal), `eating`, `post_0_2h`, `post_2_4h`, `fasting` (> 4 h since a meal) |
| Exercise, current | `exercising_now` | boolean | bucket overlaps an `exercise_logs` interval |
| | `exercise_log_id` | uuid | |
| | `exercise_type` | enum | |
| | `exercise_intensity` | smallint | 1-5 |
| Exercise, as-of | `min_since_exercise_end` | integer | |
| | `last_exercise_type` | enum | |
| | `last_exercise_intensity` | smallint | |
| | `exercise_window` | enum | `during`, `post_0_2h`, `post_2_12h` (delayed effect), `none` |
| Medication | `dose_taken_in_bucket` | boolean | from `medication_log` |
| | `min_since_last_dose` | integer | |
| | `last_medication_id` | uuid | |
| | `last_dose_status` | enum | |
| Subjective, as-of | `mood`, `stress_self`, `sleep_quality`, `energy` | smallint | most recent `wellbeing_logs` value |
| | `min_since_wellbeing_log` | integer | so stale values can be ignored |
| Symptoms | `symptom_in_bucket` | boolean | |
| | `symptom_type` | enum | symptom whose `occurred_at` falls in the bucket (the latest if several) |
| | `symptom_severity` | smallint | |
| State label | `state` | enum | one label per bucket, first match wins: `asleep` (sleep_minutes > 0), `exercising`, `post_meal` (0-2 h), `post_exercise` (0-2 h), `active` (activity_level >= 2 or steps >= 100), `resting` (everything else with watch data), `unknown` (no watch data) |
| Honesty | `is_demo` | boolean | true if any contributing row has `source = 'demo_dataset'` |
| | `built_at` | timestamptz | when the cached row was rebuilt |

**Why these columns.** The story questions map to them directly:

| Question | Uses |
|---|---|
| How high and how often do glucose spikes go? | `glucose_zone`, `glucose_delta_30m`, `glucose_rate_mmol_per_h` |
| What caused a spike? | `meal_window`, `last_meal_*`, `min_since_meal_start`, `exercise_window`, `last_dose_status`, `stress_self` |
| How does exercise affect heart rate? | `exercising_now`, `exercise_intensity`, `heart_rate_bpm`, `hr_vs_baseline` |
| How does exercise affect glucose, now and later? | `exercise_window`, `glucose_delta_30m`, `exercise_type` |
| How does rest change the measurements? | `state = 'resting'` vs `asleep` vs `active`: glucose, heart rate, HRV, SpO2, body temperature and blood pressure side by side |
| Does poor sleep change next-day glucose? | `sleep_min_night_cum`, `sleep_quality`, then next-day `glucose_zone` |
| Do missed doses show up in glucose? | `last_dose_status`, `min_since_last_dose` |
| Do symptoms line up with highs or lows? | `symptom_type`, `symptom_severity`, `glucose_zone` |
| Does a salty or fibre-rich meal change the response? | `last_meal_sodium_mg`, `last_meal_fibre_g`, `meal_window`, `glucose_delta_30m` |

### 4.2 Derived Gold tables (built from the timeline)

#### `daily_summary` (user x local day)

Primary key: (`user_id`, `local_date`).

| Group | Column | Type | Meaning |
|---|---|---|---|
| Key | `user_id` | uuid | |
| | `local_date` | date | |
| Glucose | `glucose_mean_mmol`, `glucose_sd_mmol`, `glucose_min_mmol`, `glucose_max_mmol` | numeric(4,1) | |
| | `tir_pct`, `tbr_pct`, `tar_pct` | numeric(4,1) | time in range / below / above (%) |
| | `cgm_coverage_pct` | numeric(4,1) | share of buckets with a reading |
| Watch | `steps_total` | integer | |
| | `sleep_hours` | numeric(3,1) | |
| | `resting_hr_bpm` | smallint | 10th percentile of waking heart rate |
| | `hrv_mean_ms` | numeric(5,1) | **new** |
| | `spo2_mean_pct`, `spo2_min_pct` | numeric(4,1) | |
| | `body_temp_mean_c` | numeric(4,1) | **new** |
| | `bp_systolic_mean`, `bp_diastolic_mean` | numeric(4,0) | **new**, mean of the day's readings |
| | `bp_readings_n` | smallint | **new** |
| Food | `meals_n` | smallint | |
| | `carbs_g`, `protein_g`, `fat_g`, `sugar_g`, `fibre_g` | numeric(6,1) | `fibre_g` is **new** |
| | `sodium_mg` | numeric(6,0) | **new** |
| | `kcal` | numeric(6,0) | |
| Exercise | `exercise_min` | integer | |
| | `exercise_sessions_n` | smallint | |
| Medication | `doses_scheduled`, `doses_taken`, `doses_missed` | smallint | |
| Symptoms and mood | `symptoms_n` | smallint | |
| | `symptom_worst_severity` | smallint | |
| | `mood_avg`, `stress_self_avg`, `energy_avg`, `sleep_quality_avg` | numeric(2,1) | |
| Quality | `data_quality` | jsonb | flags such as missing CGM or watch hours |
| | `built_at` | timestamptz | |

#### `meal_response` (one per `food_logs` row)

Primary key: `food_log_id`.

| Column | Type | Meaning |
|---|---|---|
| `food_log_id` | uuid | -> `food_logs` |
| `user_id` | uuid | |
| `pre_glucose_mmol` | numeric(4,1) | mean of the 30 min before eating |
| `peak_glucose_mmol` | numeric(4,1) | |
| `minutes_to_peak` | integer | |
| `rise_mmol` | numeric(4,1) | peak minus pre |
| `glucose_1h_mmol`, `glucose_2h_mmol` | numeric(4,1) | value at +1 h and +2 h |
| `iauc_2h_mmol_min` | numeric(7,1) | area above baseline over 2 h |
| `minutes_to_baseline` | integer | minutes to return to baseline |
| `steps_next_2h` | integer | to separate food from movement |
| `exercise_min_next_2h` | integer | |
| `last_dose_status` | enum | |
| `spike_flag` | boolean | rise >= 2.5 mmol/L or peak > target high |
| `n_points` | smallint | valid CGM readings in the window |
| `built_at` | timestamptz | |

#### `exercise_response` (one per `exercise_logs` row)

Primary key: `exercise_log_id`.

| Column | Type | Meaning |
|---|---|---|
| `exercise_log_id` | uuid | -> `exercise_logs` |
| `user_id` | uuid | |
| `hr_pre_bpm`, `hr_avg_bpm`, `hr_peak_bpm`, `hr_30min_after_bpm` | smallint | heart rate before, during, peak and 30 min after |
| `hr_zone_minutes` | jsonb | time in heart-rate zones, only if age is known |
| `glucose_pre_mmol`, `glucose_min_during_mmol` | numeric(4,1) | |
| `glucose_change_at_end` | numeric(4,1) | |
| `glucose_1h_mmol`, `glucose_2h_mmol`, `glucose_12h_mmol` | numeric(4,1) | |
| `post_exercise_low_flag` | boolean | glucose fell below target low |
| `glucose_change_vs_same_type_median` | numeric(4,1) | compared with that user's other exercises of the same `type` |
| `built_at` | timestamptz | |

#### `state_profile` (user x local day x `state`)

The "how does resting affect the different measurements" table. Primary key: (`user_id`, `local_date`, `state`).

| Column | Type | Meaning |
|---|---|---|
| `user_id` | uuid | |
| `local_date` | date | |
| `state` | enum | asleep, resting, active, post_meal, post_exercise, exercising |
| `minutes_in_state` | integer | |
| `hr_mean`, `hr_sd` | numeric(5,1) | heart rate |
| `hrv_mean`, `hrv_sd` | numeric(5,1) | **new** |
| `spo2_mean`, `spo2_sd` | numeric(4,1) | |
| `body_temp_mean`, `body_temp_sd` | numeric(4,2) | **new** |
| `glucose_mean`, `glucose_sd` | numeric(4,1) | |
| `built_at` | timestamptz | |

#### `glucose_events` (one per excursion; the rows the doctor brief quotes)

Every spike (rise >= 2.5 mmol/L in 60 min or crossing 10.0), every sustained high (> 10.0 for 60 min) and every low (< 3.9).

| Column | Type | Meaning |
|---|---|---|
| `id`, `user_id` | uuid | |
| `event_type` | enum | `spike`, `sustained_high`, `low` |
| `started_at`, `extreme_at`, `ended_at` | timestamptz | start, peak or nadir, end |
| `duration_min` | integer | |
| `start_glucose_mmol`, `extreme_glucose_mmol` | numeric(4,1) | |
| `rise_mmol` | numeric(4,1) | |
| `ctx_meal_window` | enum | context snapshot of the timeline at the start |
| `ctx_last_meal_carbs_g`, `ctx_last_meal_protein_g`, `ctx_last_meal_fat_g`, `ctx_last_meal_sugar_g` | numeric(5,1) | |
| `ctx_last_meal_fibre_g` | numeric(5,1) | **new** |
| `ctx_exercise_window` | enum | |
| `ctx_last_dose_status` | enum | |
| `ctx_state` | enum | |
| `ctx_heart_rate_bpm` | smallint | |
| `ctx_stress_self` | smallint | |
| `ctx_last_symptom_type` | enum | |
| `built_at` | timestamptz | |

#### `baselines` (user x `state` x hour-of-day band)

Rolling 14-day median and spread; feeds `hr_vs_baseline` and "unusual for you" flags. Primary key: (`user_id`, `state`, `hour_band`).

| Column | Type | Meaning |
|---|---|---|
| `user_id` | uuid | |
| `state` | enum | |
| `hour_band` | smallint | 4-hour band: 0 = 00-04, 1 = 04-08, ... 5 = 20-24 local |
| `hr_median`, `hr_mad` | numeric(5,1) | median and median absolute deviation |
| `hrv_median`, `hrv_mad` | numeric(5,1) | **new** |
| `spo2_median`, `spo2_mad` | numeric(4,1) | |
| `body_temp_median`, `body_temp_mad` | numeric(4,2) | **new** |
| `glucose_median`, `glucose_mad` | numeric(4,1) | |
| `n_days` | smallint | days of data in the window |
| `computed_at` | timestamptz | |

### 4.3 Gold tables kept unchanged

| Table | Grain | What it is |
|---|---|---|
| `pattern_candidates` | one per candidate pattern | A statistical pattern across the tables above, e.g. "post-dinner spikes are 2.1 mmol/L higher on days with a missed evening dose (n = 9)". Holds effect size, sample size, confidence, and the supporting `glucose_events` / `meal_response` ids. Nothing is shown to a doctor without n and the supporting rows. |
| `briefs`, `brief_shares`, `brief_share_access` | per brief | The doctor brief: built from `daily_summary`, `glucose_events`, `meal_response`, `exercise_response`, `state_profile`, `lab_results` and accepted `pattern_candidates`. Every claim links to its source rows. |
| `memory_facts`, `memory_episodes` | per fact / episode | Application memory, unchanged. |

Their columns stay as in the current database.

**Rules for the story.**
- Correlation is not cause: statements say "tends to", with n and the date range, and the brief shows counts.
- Windows overlap: a spike after a meal eaten before a walk is both. `meal_response` records the exercise in the same window so the writer can say so.
- Minimum data: a pattern needs at least 5 events of the kind, and shows as "early signal" below 10.
- Gaps are shown as gaps. Missing CGM or watch buckets lower the coverage figures in `daily_summary`.

---

## 5. Kept unchanged and out of scope for this redesign

I did not review these tables for this document; they stay as they are until a later pass:

- **Reference:** `data_sources`, `drug_aliases`, `drug_reference`, `drug_side_effects`, `foods`, `interaction_rules`, `knowledge_chunks`, `knowledge_documents`, `population_priors`, `preventive_items`, `routing_rules`.
- **Operations:** `agent_runs`, `agent_steps`, `conversations`, `messages`, `event_log`, `guardrail_events`.
- **Silver, tied to features in progress or to the brief:** `prescription_scans` (the scan feature is mid-build), `appointments`, `doctor_questions`, `notifications`, `refill_forecasts`, `patient_preventive_status`.
- **Gold:** `interaction_alerts`.

## 6. Mapping from the old schema

### Silver

| Old table | New home | What happens to the data |
|---|---|---|
| `users` | `users` | stays as identity only |
| `patient_profiles` | `user_profile` | columns mapped by name; the age column becomes `birth_year`; `sex` becomes `gender` (`undisclosed` -> `prefer_not_to_say`); `ethnicity` is new and filled only where the source has it (CGMacros `Self-identify`) |
| `devices` | `user_profile.watch_*` and `cgm_*` | brand and model copied; sync status dropped |
| `body_measurements` | `user_profile.weight_kg` | latest weight kept; history and waist dropped |
| `allergies` | `user_profile.allergies_note` | rows joined into text |
| `conditions` | `user_profile.conditions_note` | rows joined into text |
| `family_history` | `user_profile.family_history_note` | rows joined into text |
| `health_goals` | `user_profile.glucose_target_low` / `high` | only glucose range kept; other goals dropped |
| `patient_medications` | `medications` | |
| `medication_ingredients` | none | dropped; `drug_reference` already covers ingredients |
| `dose_events` | `medication_log` | `status` mapped; `confirmed_at` -> `taken_at`; `window_end_at` used to compute `late` / `missed` |
| `health_samples` | `watch_readings` | rows re-bucketed to 5 minutes; kinds pivoted into columns: heart rate, HRV, SpO2, body temperature (`skin_temp`), steps. Other kinds (EDA, active energy, resting heart rate, distance, stress score) are dropped |
| `blood_pressure_readings` | `watch_readings.systolic_mmhg` / `diastolic_mmhg` | each reading goes into the 5-minute bucket that contains its time; pulse dropped |
| `sleep_sessions` | `watch_readings.sleep_minutes` | session spread across its 5-minute buckets |
| `glucose_readings` | `cgm_readings` | `value_mmol` -> `glucose_mmol`; `measured_at` -> `recorded_at`; `context`, `meal_id`, `note`, `cgm_sprint_id` dropped (the timeline derives context). Glucometer and finger-prick rows keep `source = manual` |
| `cgm_sprints` | none | dropped; CGM is continuous, so no sprint grouping is needed |
| `workouts` | `exercise_logs` | |
| `workout_sets` | `exercise_sets` | |
| `meals` | `food_logs` | |
| `meal_items` | `food_logs` | summed into the meal's macros, **including `fibre_g` and `sodium_mg`**; item list dropped |
| `meal_analyses` | `ingestion_events` + `food_logs.estimated_by` | raw LLM output kept as Bronze |
| `symptom_logs`, `symptom_checkins` | `symptom_logs` | merged into one table |
| `mood_checkins` | `wellbeing_logs` | |
| `lab_results` | `lab_results` | only `hba1c` (%), `fasting_glucose` and, newly, `fasting_insulin` are kept; all other tests (total cholesterol, LDL, HDL, triglycerides, creatinine, UACR, eGFR) are dropped. The old `egfr_reported` kind is dropped too |
| `consents` | `consents` | unchanged |

### Gold

| Old table | New home |
|---|---|
| `daily_aggregates` | `daily_summary` |
| `meal_responses`, `food_responses` | `meal_response` |
| `event_windows` | replaced by `timeline_5min` |
| `baselines` | `baselines` (rebuilt) |
| `pattern_candidates`, `briefs`, `brief_shares`, `brief_share_access`, `memory_facts`, `memory_episodes` | kept |
| `clinical_flags`, `urgent_events` | proposed drop: folded into `glucose_events` and the brief |
| `sprint_summaries` | proposed drop: no sprints |
| `momentum_snapshots`, `nudge_stats` | proposed drop: **not reviewed**; confirm no feature depends on them |

## 7. Open decisions (owner to confirm)

| # | Decision | Default in this document | Status |
|---|---|---|---|
| 1 | Tables left unchanged and not reviewed (section 5): `prescription_scans`, `appointments`, `doctor_questions`, `notifications`, `refill_forecasts`, `patient_preventive_status`. Cut any of them? | Keep. The scan feature is mid-build and the brief appears to depend on some of them. | open |
| 2 | Gold tables proposed for dropping: `clinical_flags`, `urgent_events`, `sprint_summaries`, `momentum_snapshots`, `nudge_stats`. | Drop. `momentum_snapshots` and `nudge_stats` are **not reviewed**; confirm nothing reads them before the drop. | open |
| 3 | Data dropped because it was not in the requested list: weight and waist history, CGM sprints, lab tests other than HbA1c, fasting glucose and fasting insulin, EDA, active energy and the watch stress score. Bring any back? | Dropped. Export first if any real data exists. (Blood pressure is **no longer** dropped: it is kept as watch columns.) | open |
| 4 | Medication log: one table (`medication_log`) replaces both `dose_events` and a separate log. | One table. | decided in the 2026-10-04 review |
| 5 | Watch data is stored per 5-minute bucket (not running totals); sleep is 0 by day and rises overnight. | As described in section 3.2. | decided in the 2026-10-04 review |
| 6 | Lab results keep only HbA1c (stored in %, not mmol/mol), fasting glucose (mg/dL or mmol/L, as reported) and fasting insulin (mcU/mL). | As described in section 3.1. | decided by Joely, 2026-10-04 (owner confirmation pending) |
| 7 | HRV, blood pressure and body temperature are columns of `watch_readings`; the watch activity score is kept; the watch stress score is dropped. | As described in section 3.2. | decided by Joely, 2026-10-04 (owner confirmation pending) |
| 8 | Nutrition includes fibre and sodium. | `food_logs.fibre_g` and `sodium_mg`, carried into Gold. | decided by Joely, 2026-10-04 (owner confirmation pending) |
| 9 | The user profile includes gender and ethnicity. | `user_profile.gender` (enum) and `ethnicity` (free text), both optional; ethnicity treated as sensitive. | decided by Joely, 2026-10-04 (owner confirmation pending) |
| 10 | Blood pressure and SpO2 do not exist in any cited dataset. | Simulate them and mark `demo_dataset`; data gaps accepted. | decided by Joely, 2026-10-04 (owner confirmation pending) |

## 8. Next steps (when approved)

1. Check what the app, API and views currently read from each old table (`apps/web/src/data/**`, `services/api/app/**`, SQL views in `docs/specs/schema.md` section 0b) so nothing is dropped while still in use. This includes the uncommitted scan, hooks and repository changes.
2. Write the migration: create new tables, copy data per section 6, then drop the old ones in a later migration.
3. Write the `timeline_5min` view and its per-day rebuild, then the derived Gold tables.
4. Update the frontend forms (birth year input, gender and ethnicity, more exercise types, fibre and sodium on the food log, the new symptom and medication fields) and the demo-data generator so it emits watch batches (heart rate, HRV, SpO2, blood pressure, body temperature, steps, sleep, activity), CGM readings, the three lab tests and logs that produce visible spikes and exercise effects. Blood pressure and SpO2 have no cited source and are simulated.
5. Regenerate the loaded datasets in the new shape: CGMacros `bio.csv` gives HbA1c (as %), fasting glucose (mg/dL) and fasting insulin (mcU/mL), plus gender and ethnicity; its LDL error code of 800 is no longer a concern because LDL is not kept.
6. Re-run `scripts/make_data_dictionary.py` so `docs/data_dictionary.md` matches the new schema.
