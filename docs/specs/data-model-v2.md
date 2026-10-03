# Data model v2: data dictionary and mapping

Status: **proposal, not migrated yet.** The live database still has the old 67-table schema; `docs/data_dictionary.md` is generated from it and will change when the migration runs.

Goal: replace about 35 Silver tables with 10 plain tables the whole team can hold in their heads, and put the effort into one Gold dataset, the **master timeline**, that tells the story of a user's day.

## 0. Conventions (apply to every table)

- All times are UTC (`timestamptz`). The user's timezone is stored once in `user_profile.timezone`; local time is derived in Gold.
- Glucose is stored in **mmol/L** `numeric(4,1)`. Conversion to mg/dL happens only in the API.
- Every table has `id uuid` (primary key), `user_id uuid` (-> `users`), `created_at`. Tables a person can edit also have `updated_at` and `deleted_at` (soft delete).
- Every row has a **`source`** using the existing `entry_source` values (`manual`, `watch`, `cgm`, `llm_estimate`, `scan`, `file_import`, `replay`, `system`, `demo_dataset`). `demo_dataset` keeps marking simulated or imported data, so the demo-honesty rule survives.
- `NULL` means "no data", never zero. The one deliberate exception is watch `sleep_minutes` and `steps`: `0` means "the watch was worn and recorded none".
- `1-5` scales: 1 = lowest, 5 = highest. Labels for the frontend: mood (very low ... very good), stress (calm ... very stressed), sleep quality (very poor ... excellent), energy (exhausted ... energised), intensity (very light ... all-out), feeling (awful ... great), symptom severity (barely noticeable ... severe).

## 1. Layers

| Layer | Tables | Notes |
|---|---|---|
| Bronze | `ingestion_events` | One row per raw input as received: a watch batch, a CGM file or push, a meal photo, a prescription scan. Never edited. Keeps the raw payload (or `object_key` to it) plus checksum for idempotency. |
| Silver | 10 tables below | Typed, cleaned, one row per fact. Rows entered by hand in a form are Bronze and Silver in one step (the form is the raw record). Rows from the watch, CGM, photo or scan keep a link back to their `ingestion_events` row. |
| Gold | timeline plus derived tables, section 4 | Rebuilt from Silver. Never written to by the app. |

## 2. One-time records

### `user_profile` (one row per user)

| Column | Type | Required | Notes |
|---|---|---|---|
| `user_id` | uuid | yes | primary key, -> `users` (identity stays in `users`) |
| `language` | text | yes | BCP-47 code, e.g. `en`, `zh-Hans` |
| `has_diabetes` | enum `yes` / `no` / `not_sure` | yes | |
| `birth_year` | smallint | yes | frontend: number input (replaces the age picker); age is computed |
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

### `medications` (one row per medicine the user takes)

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

### `medication_log` (dose log: one row per scheduled or ad-hoc dose)

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

### `lab_results` (kept, slimmed)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id`, `user_id` | uuid | yes | |
| `measured_at` | timestamptz | yes | date of the sample |
| `test` | enum `hba1c` / `fasting_glucose` / `ogtt` / `total_cholesterol` / `ldl` / `hdl` / `triglycerides` / `egfr` / `creatinine` / `uacr` / `other` | yes | |
| `test_name` | text | no | when `test = other` |
| `value` | numeric | yes | |
| `unit` | text | yes | HbA1c stored as `%` or `mmol/mol`, as reported |
| `ref_low`, `ref_high` | numeric | no | |
| `source` | entry_source | yes | |
| `ingestion_event_id` | uuid | no | -> `ingestion_events` |
| `created_at`, `deleted_at` | timestamptz | | |

### `consents` (kept as is)

Minimal record of what the user agreed to (`kind`, `version`, `granted_at`, `revoked_at`). Health data needs this even in a demo.

## 3. Recorded data

### 3a. Passive: watch and CGM

#### `watch_readings` (one row per user per 5-minute bucket, delivered in batches)

The watch syncs in **batches** (a few times a day, or one big upload); one batch is one `ingestion_events` row with `source_type = 'watch_batch'`. Each row covers one 5-minute bucket and holds what happened *in that bucket*, not a running total. That is how "sleep is 0 all day and grows overnight" works: `sleep_minutes` is 0 in daytime buckets and 1-5 in buckets where the user was asleep. Daily totals and running totals are computed in Gold, so batches can arrive late or out of order and nothing needs correcting.

| Column | Type | Required | Notes |
|---|---|---|---|
| `id`, `user_id` | uuid | yes | |
| `recorded_at` | timestamptz | yes | bucket start, aligned to 5 minutes; unique with `user_id` (upsert makes re-sent batches harmless) |
| `heart_rate_bpm` | smallint | no | average over the bucket |
| `spo2_pct` | numeric(4,1) | no | blood oxygen, average |
| `steps` | integer | no | steps taken inside the bucket |
| `sleep_minutes` | smallint | no | 0-5: minutes asleep inside the bucket |
| `activity_level` | smallint | no | 0-4 from the watch (0 still ... 4 vigorous); the vendor's own score |
| `stress_watch` | smallint | no | 0-100 from the watch (device-estimated; not the same as `wellbeing_logs.stress_self`) |
| `ingestion_event_id` | uuid | yes | -> `ingestion_events` (the batch) |
| `source` | entry_source | yes | `watch`, `replay` or `demo_dataset` |
| `created_at` | timestamptz | yes | |

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

### 3b. Active: logged by the user

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

#### `food_logs`

| Column | Type | Required | Notes |
|---|---|---|---|
| `id`, `user_id` | uuid | yes | |
| `start_at`, `end_at` | timestamptz | yes | when eating began and finished; `end_at` defaults to `start_at` + 15 min |
| `meal_type` | enum `breakfast` / `lunch` / `dinner` / `snack` / `drink` | no | |
| `food` | text | yes | description, e.g. "chicken rice, half portion" |
| `protein_g`, `carbs_g`, `fat_g`, `sugar_g` | numeric(5,1) | no | `sugar_g` is part of `carbs_g` |
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
| `stress_self` | smallint (1-5) | no | what the user feels; compare with `watch_readings.stress_watch` |
| `sleep_quality` | smallint (1-5) | no | how the last sleep felt; compare with the watch's measured sleep |
| `energy` | smallint (1-5) | no | |
| `note` | text | no | |
| `source` | entry_source | yes | |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | | |

At least one of the four scores must be present.

### Bronze: `ingestion_events` (kept as is)

`id`, `user_id`, `source_type` (`watch_batch`, `cgm_batch`, `meal_photo`, `meal_text`, `prescription_scan`, `lab_document`, `file_import`), `object_key`, `checksum`, `received_at`, `source_recorded_at`, `source_timezone`, `content_type`, `schema_version`, `processing_status`, `entry_source`, `created_at`. The checksum makes re-sending a batch a no-op.

## 4. Gold

Gold is rebuilt from Silver and never edited by the app. The master timeline is the foundation; everything else reads from it.

### 4.1 `timeline_5min`: the master temporal dataset

One row per user per 5-minute bucket, from the user's first data to now. Every Silver source is lined up on the same clock, so any question that crosses sources ("what was my heart rate when glucose spiked?") is a single-row or small-window query.

**How it is built.** A regular SQL view `v_timeline_5min` defines it (`generate_series` grid left-joined to each source). Because the "time since last meal / exercise / dose" columns need as-of lookups that are slow to recompute, it is also kept as a table `timeline_5min`. After each ingested batch, the days it touches are deleted and rebuilt from the view. The view is the source of truth; the table is a cache.

| Group | Column | Meaning |
|---|---|---|
| Key | `user_id`, `bucket_start` | primary key; UTC |
| Clock | `local_date`, `local_time`, `hour_of_day`, `weekday`, `days_since_start` | from `user_profile.timezone` |
| Watch | `heart_rate_bpm`, `spo2_pct`, `steps`, `sleep_minutes`, `activity_level`, `stress_watch` | from `watch_readings` |
| Watch, running | `steps_day_cum`, `sleep_min_night_cum` | running totals since local midnight and since the sleep period began, so "sleep rises overnight" is visible on the timeline |
| Watch, derived | `hr_vs_baseline` | `heart_rate_bpm` minus the user's median at this `state` and hour (from `baselines`) |
| CGM | `glucose_mmol` | average of the bucket's readings, `NULL` if none |
| CGM, derived | `glucose_delta_5m`, `glucose_delta_30m` | change since 5 and 30 min ago |
| | `glucose_rate_mmol_per_h` | slope over the last 30 min |
| | `glucose_zone` | `low` (< target low), `in_range`, `high` (> target high), `very_high` (> 13.9) |
| | `has_cgm`, `has_watch` | data-present flags; gaps stay visible |
| Food, current | `eating_now`, `food_log_id` | bucket overlaps a `food_logs` interval |
| Food, as-of | `last_food_log_id`, `min_since_meal_start`, `min_since_meal_end` | most recent meal at or before this bucket |
| | `last_meal_carbs_g`, `last_meal_protein_g`, `last_meal_fat_g`, `last_meal_sugar_g`, `last_meal_type` | copied from that meal for easy filtering |
| | `meal_window` | `pre_meal` (0-30 min before the next meal), `eating`, `post_0_2h`, `post_2_4h`, `fasting` (> 4 h since a meal) |
| Exercise, current | `exercising_now`, `exercise_log_id`, `exercise_type`, `exercise_intensity` | bucket overlaps an `exercise_logs` interval |
| Exercise, as-of | `min_since_exercise_end`, `last_exercise_type`, `last_exercise_intensity` | |
| | `exercise_window` | `during`, `post_0_2h`, `post_2_12h` (delayed effect), `none` |
| Medication | `dose_taken_in_bucket`, `min_since_last_dose`, `last_medication_id`, `last_dose_status` | from `medication_log` |
| Subjective, as-of | `mood`, `stress_self`, `sleep_quality`, `energy` | most recent `wellbeing_logs` value, plus `min_since_wellbeing_log` so stale values can be ignored |
| Symptoms | `symptom_in_bucket`, `symptom_type`, `symptom_severity` | symptom whose `occurred_at` falls in the bucket (the latest if several) |
| State label | `state` | one label per bucket, first match wins: `asleep` (sleep_minutes > 0), `exercising`, `post_meal` (0-2 h), `post_exercise` (0-2 h), `active` (activity_level >= 2 or steps >= 100), `resting` (everything else with watch data), `unknown` (no watch data) |
| Honesty | `is_demo` | true if any contributing row has `source = 'demo_dataset'` |

**Why these columns.** The story questions map to them directly:

| Question | Uses |
|---|---|
| How high and how often do glucose spikes go? | `glucose_zone`, `glucose_delta_30m`, `glucose_rate_mmol_per_h` |
| What caused a spike? | `meal_window`, `last_meal_*`, `min_since_meal_start`, `exercise_window`, `last_dose_status`, `stress_self` |
| How does exercise affect heart rate? | `exercising_now`, `exercise_intensity`, `heart_rate_bpm`, `hr_vs_baseline` |
| How does exercise affect glucose, now and later? | `exercise_window`, `glucose_delta_30m`, `exercise_type` |
| How does rest change the measurements? | `state = 'resting'` vs `asleep` vs `active`: glucose, heart rate, SpO2 and `stress_watch` side by side |
| Does poor sleep change next-day glucose? | `sleep_min_night_cum`, `sleep_quality`, then next-day `glucose_zone` |
| Do missed doses show up in glucose? | `last_dose_status`, `min_since_last_dose` |
| Do symptoms line up with highs or lows? | `symptom_type`, `symptom_severity`, `glucose_zone` |

### 4.2 Derived Gold tables (built from the timeline)

| Table | Grain | What it answers |
|---|---|---|
| `daily_summary` | user x local day | Glucose mean, SD, min, max, time in range / low / high (%), CGM coverage (%); steps, sleep hours, resting HR (10th percentile of waking HR), mean SpO2 and minimum SpO2; meal count, total carbs, protein, fat, sugar; exercise minutes; doses taken / missed; symptom count and worst severity; average mood, stress, energy, sleep quality; `data_quality` flags. |
| `meal_response` | one per `food_logs` row | Glucose just before eating (mean of the 30 min before), peak, minutes to peak, rise (peak minus pre), value at +1 h and +2 h, area above baseline over 2 h, minutes to return to baseline; steps and exercise in the 2 h after (to separate food from movement); `last_dose_status`; `spike_flag` (rise >= 2.5 mmol/L or peak > target high). |
| `exercise_response` | one per `exercise_logs` row | Heart rate: pre, average, peak, and at +30 min after; time in HR zones if age is known. Glucose: pre, minimum during, change at end, +1 h, +2 h, +12 h, `post_exercise_low_flag` (< target low). Compares against that user's other exercises of the same `type`. |
| `state_profile` | user x local day x `state` | Average and spread of heart rate, SpO2, glucose and `stress_watch` for each state (asleep, resting, active, post_meal, post_exercise, exercising), plus minutes in the state. This is the "how does resting affect the different measurements" table. |
| `glucose_events` | one per excursion | Every spike (rise >= 2.5 mmol/L in 60 min or crossing 10.0), every sustained high (> 10.0 for 60 min) and every low (< 3.9). For each: start, peak or nadir, duration, and a context snapshot of the timeline at the start (`meal_window`, last meal macros, `exercise_window`, `last_dose_status`, `state`, HR, stress, last symptom). The rows the doctor brief quotes. |
| `baselines` | user x `state` x hour-of-day band | Rolling 14-day median and spread of heart rate, SpO2, glucose; feeds `hr_vs_baseline` and "unusual for you" flags. |
| `pattern_candidates` (kept) | one per candidate pattern | A statistical pattern across the tables above, e.g. "post-dinner spikes are 2.1 mmol/L higher on days with a missed evening dose (n = 9)". Holds effect size, sample size, confidence, and the supporting `glucose_events` / `meal_response` ids. Nothing is shown to a doctor without n and the supporting rows. |
| `briefs`, `brief_shares`, `brief_share_access` (kept) | per brief | The doctor brief: built from `daily_summary`, `glucose_events`, `meal_response`, `exercise_response`, `state_profile`, `lab_results` and accepted `pattern_candidates`. Every claim links to its source rows. |
| `memory_facts`, `memory_episodes` (kept) | per fact / episode | Application memory, unchanged. |

**Rules for the story.**
- Correlation is not cause: statements say "tends to", with n and the date range, and the brief shows counts.
- Windows overlap: a spike after a meal eaten before a walk is both. `meal_response` records the exercise in the same window so the writer can say so.
- Minimum data: a pattern needs at least 5 events of the kind, and shows as "early signal" below 10.
- Gaps are shown as gaps. Missing CGM or watch buckets lower the coverage figures in `daily_summary`.

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
| `patient_profiles` | `user_profile` | columns mapped by name; the age column becomes `birth_year` |
| `devices` | `user_profile.watch_*` and `cgm_*` | brand and model copied; sync status dropped |
| `body_measurements` | `user_profile.weight_kg` | latest weight kept; history and waist dropped |
| `allergies` | `user_profile.allergies_note` | rows joined into text |
| `conditions` | `user_profile.conditions_note` | rows joined into text |
| `family_history` | `user_profile.family_history_note` | rows joined into text |
| `health_goals` | `user_profile.glucose_target_low` / `high` | only glucose range kept; other goals dropped |
| `patient_medications` | `medications` | |
| `medication_ingredients` | none | dropped; `drug_reference` already covers ingredients |
| `dose_events` | `medication_log` | `status` mapped; `confirmed_at` -> `taken_at`; `window_end_at` -> used to compute `late` / `missed` |
| `health_samples` | `watch_readings` | rows re-bucketed to 5 minutes; kinds pivoted into columns |
| `sleep_sessions` | `watch_readings.sleep_minutes` | session spread across its 5-minute buckets |
| `glucose_readings` | `cgm_readings` | `value_mmol` -> `glucose_mmol`; `measured_at` -> `recorded_at`; `context`, `meal_id`, `note`, `cgm_sprint_id` dropped (the timeline derives context) |
| `cgm_sprints` | none | dropped; CGM is continuous, so no sprint grouping is needed |
| `workouts` | `exercise_logs` | |
| `workout_sets` | `exercise_sets` | |
| `meals` | `food_logs` | |
| `meal_items` | `food_logs` | summed into the meal's macros; item list dropped |
| `meal_analyses` | `ingestion_events` + `food_logs.estimated_by` | raw LLM output kept as Bronze |
| `symptom_logs`, `symptom_checkins` | `symptom_logs` | merged into one table |
| `mood_checkins` | `wellbeing_logs` | |
| `lab_results` | `lab_results` | `test` normalised to the enum |
| `blood_pressure_readings` | none | dropped (outside this scope); export first if any real data exists |
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
| 3 | Data dropped because it was not in the requested list: blood pressure readings, weight and waist history, CGM sprints. Bring any back? | Dropped. Export first if any real data exists. | open |
| 4 | Medication log: one table (`medication_log`) replaces both `dose_events` and a separate log. | One table. | decided in the 2026-10-04 review |
| 5 | Watch data is stored per 5-minute bucket (not running totals); sleep is 0 by day and rises overnight. | As described in section 3a. | decided in the 2026-10-04 review |

## 8. Next steps (when approved)

1. Check what the app, API and views currently read from each old table (`apps/web/src/data/**`, `services/api/app/**`, SQL views in `docs/specs/schema.md` section 0b) so nothing is dropped while still in use. This includes the uncommitted scan, hooks and repository changes.
2. Write the migration: create new tables, copy data per section 6, then drop the old ones in a later migration.
3. Write the `timeline_5min` view and its per-day rebuild, then the derived Gold tables.
4. Update the frontend forms (birth year input, more exercise types, the new symptom and medication fields) and the demo-data generator so it emits watch batches, CGM readings and logs that produce visible spikes and exercise effects.
5. Re-run `scripts/make_data_dictionary.py` so `docs/data_dictionary.md` matches the new schema.
