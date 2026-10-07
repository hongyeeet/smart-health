# Data model v2: final design

Status: **built and deployed to the shared Supabase project on 2026-10-05** at Hong Yi's request (Alembic 0017 to 0020; the old Bronze, Silver and Gold tables and the other 23 demo users were deleted after a CSV backup). **Not yet committed or pushed, and the team has not approved it yet.** Section 11 lists what was built, where it differs from the design above, and what is still open. `docs/data_dictionary.md` is regenerated from the new database.

Last updated 2026-10-05 (second pass: race, required emergency contact, medication schedule, work-schedule overlay, symptom notes). Written in review with Hong Yi; it includes Joely's scope decisions of 2026-10-04.

## 1. Design in one page

1. **Every data source has its own Bronze table and its own Silver table.** Anything that reaches the app (onboarding form, a medication entry, a meal photo, a watch batch, a CGM push) is first stored as received (Bronze), then turned into typed columns (Silver). One-time inputs count as Bronze too.
2. **One master timeline** (`timeline_5min`, Gold) puts watch, CGM, blood pressure, food, exercise, medication, mood and symptoms on one 5-minute clock. It feeds the four report charts.
3. **A fixed personal baseline** (`baselines`, Gold) is built once from the person's first 14 days (blood pressure: first 5 readings) and only changes when someone resets it on purpose. Because it does not drift, a slow decline shows up as readings leaving the usual range instead of becoming the new normal.
4. **Demo:** 3 months of synthetic data for the demo patient, marked `demo_dataset` (section 8).

```
Bronze (10 tables, as received)  ->  Silver (13 tables, typed)  ->  Gold (timeline, baselines, summaries)
```

## 1b. Table index by layer

| Layer | Tables | Rule |
|---|---|---|
| **Bronze** (10) | `bronze_profile`, `bronze_medication`, `bronze_lab`, `bronze_watch`, `bronze_cgm`, `bronze_blood_pressure`, `bronze_exercise`, `bronze_food`, `bronze_symptom`, `bronze_wellbeing` | raw input as received, never edited |
| **Silver** (13) | `user_profile`, `medications`, `medication_schedule`, `medication_log`, `lab_results`, `watch_readings`, `cgm_readings`, `blood_pressure_readings`, `exercise_logs`, `exercise_sets`, `food_logs`, `symptom_logs`, `wellbeing_logs` | typed facts, each with a `bronze_id` (the children `medication_schedule` and `exercise_sets` use their parent's) |
| **Gold** (15) | `timeline_5min`, `baselines`, `daily_summary`, `care_summary`, `meal_response`, `exercise_response`, `glucose_events`, `clinical_flags`, `pattern_candidates`, `briefs`, `brief_shares`, `brief_share_access`, `memory_facts`, `memory_episodes`, `interaction_alerts` | computed from Silver, never written by the app |
| **App** (8) | `users`, `consents`, `notifications`, `refill_forecasts`, `patient_preventive_status`, `doctor_questions`, `appointments`, `prescription_scans` | application state and records outside the Bronze -> Silver -> Gold pipeline: no Bronze twin, no `bronze_id` |
| **Reference** (11) | `data_sources`, `drug_aliases`, `drug_reference`, `drug_side_effects`, `foods`, `interaction_rules`, `knowledge_chunks`, `knowledge_documents`, `population_priors`, `preventive_items`, `routing_rules` | shared lookups, not per user |
| **Operations** (6) | `agent_runs`, `agent_steps`, `conversations`, `messages`, `event_log`, `guardrail_events` | how the app itself ran |
| **Views** (6) | `timeline_events`, `health_state`, `trends`, `adherence_summary`, `insight_context`, `jev_decisions` | read-only views over the tables above (`security_invoker`) |

`consents` is described in section 4.1 but belongs to the App group. In the database every table gets a Postgres comment that starts with its layer (`Layer: Bronze`, `Layer: Silver`, ...), visible in the Supabase table editor and readable by the dictionary script. Separate schemas per layer would also work, but every query, security rule and API setting would have to change, so they are not proposed.

## 2. Conventions

- All times are UTC (`timestamptz`). The user's timezone is stored once in `user_profile.timezone`; local time is derived in Gold.
- CGM glucose is stored in **mmol/L** `numeric(4,1)`. Conversion to mg/dL happens only in the API. A fasting-glucose **lab** keeps the unit it was reported in (`mg/dL` or `mmol/L`); Gold converts it.
- Every Silver table has `user_id` (-> `users`) and `source`. Tables with an `id` use `uuid`. Editable tables also have `created_at`, `updated_at` and `deleted_at` (soft delete); sensor tables are append-only and have none of these.
- `source` uses the existing `entry_source` values: `manual`, `watch`, `cgm`, `llm_estimate`, `scan`, `file_import`, `replay`, `system`, `demo_dataset`. `demo_dataset` marks simulated or imported data, so the demo-honesty rule survives: a chart marks simulated points by checking `source` on the Silver rows.
- `NULL` means "no data", never zero. The one exception is watch `steps` and `sleep_minutes`, where `0` means "the watch was worn and recorded none".
- Every Silver row has `bronze_id` pointing to the Bronze row it came from. **Editing never changes Bronze**; the Silver row keeps the `bronze_id` of the original submission.
- `1-5` scales: 1 = lowest, 5 = highest. Frontend labels: mood (very low ... very good), stress (calm ... very stressed), sleep quality (very poor ... excellent), energy (exhausted ... energised), intensity (very light ... all-out), feeling (awful ... great), symptom severity (barely noticeable ... severe).

---

## 3. BRONZE (10 tables, all with the same 8 columns)

`bronze_profile`, `bronze_medication`, `bronze_lab`, `bronze_watch`, `bronze_cgm`, `bronze_blood_pressure`, `bronze_exercise`, `bronze_food`, `bronze_symptom`, `bronze_wellbeing`.

They replace the single `ingestion_events` table. Rows are never edited; only `processing_status` may change (the existing guard trigger carries over).

| Column | Type | Required | Comes from | Used for |
|---|---|---|---|---|
| `id` | uuid | yes | system | primary key |
| `user_id` | uuid | yes | logged-in user | owner |
| `received_at` | timestamptz | yes | server clock | audit, late-data detection |
| `source` | entry_source | yes | the ingest code | provenance, demo flag |
| `payload` | jsonb | yes | the input exactly as submitted: form fields, the whole batch, or the raw LLM answer | re-reading and replaying the original |
| `object_key` | text | no | private storage path of a photo, scan or file | opening the original |
| `checksum` | text | yes | hash of the payload; unique per user | re-sending a batch does nothing |
| `processing_status` | text | yes | pipeline: `received`, `processed`, `failed`, `deleted` | tracking; the only mutable column |

What each Bronze table holds:

| Table | One row is | Notes |
|---|---|---|
| `bronze_profile` | one onboarding or profile form submission | one-time input |
| `bronze_medication` | one medication entry (with its dose schedule), dose confirmation, or prescription scan | feeds `medications`, `medication_schedule` and `medication_log` |
| `bronze_lab` | one lab entry or lab document | |
| `bronze_watch` | one watch sync (a whole batch) | one row per sync, many Silver rows |
| `bronze_cgm` | one CGM push or file | |
| `bronze_blood_pressure` | one blood pressure entry or device sync | |
| `bronze_exercise` | one exercise entry (including its sets) | |
| `bronze_food` | one food entry: text, photo, and the raw LLM answer | |
| `bronze_symptom` | one symptom entry | |
| `bronze_wellbeing` | one mood / stress / sleep-quality / energy entry | |

Deleting an original removes the stored object and sets `processing_status = 'deleted'`; the row stays.

---

## 4. SILVER (13 tables)

### 4.1 One-time records

#### `user_profile` (one row per user)

| Column | Type | Required | Comes from | Used for |
|---|---|---|---|---|
| `user_id` | uuid PK | yes | auth user | identity |
| `display_name` | text | yes | onboarding ("Mr Tan" for the demo patient) | greeting and the doctor brief |
| `language` | locale_code (`en`, `zh`, `ms`, `ta`) | yes | onboarding picker | app language |
| `has_diabetes` | enum `yes` / `no` / `not_sure` | yes | onboarding | switches diabetes features; allows non-diabetic people |
| `birth_year` | smallint (1900-2100) | yes | number input | age for norms; stored as a year so it does not go stale |
| `gender` | enum `female` / `male` / `other` / `prefer_not_to_say` | no | onboarding | picks matching population tables (female / male only) |
| `race` | text | no | free text with suggestions | population norms; sensitive, not sent to AI unless a feature needs it |
| `height_cm` | numeric(4,1) | no | onboarding | BMI context |
| `weight_kg` | numeric(5,1) | no | onboarding, editable | BMI context |
| `work_type` | enum `desk` / `mixed` / `standing` / `physical` / `shift` / `not_working` | no in the database, asked in the app form | onboarding | labels the work overlay (e.g. "standing job"); reading activity and sleep patterns |
| `work_days` | smallint[] (1 = Monday ... 7 = Sunday) | no in the database; required in the form unless `work_type` is `not_working` | onboarding (e.g. `{1,2,3,4,5}`) | the days shaded as work in the overlay |
| `work_start`, `work_end` | time (local) | no in the database; required in the form unless `work_type` is `not_working` | onboarding | work hours on those days; an end before the start means a night shift that runs past midnight |
| `emergency_contact_name`, `emergency_contact_phone`, `emergency_contact_relation` | text | no in the database, **required in the app form** | onboarding | safety feature only, never analytics; imported or simulated users may have none, so the database does not force invented values |
| `watch_model`, `cgm_model` | text | no | onboarding (brand and model in one text) | explaining sensor gaps |
| `timezone` | text | yes | browser default, editable | turning UTC into the person's day |
| `glucose_target_low`, `glucose_target_high` | numeric(3,1) | yes | defaults 3.9 and 10.0 mmol/L, doctor-editable | time in range, `glucose_zone` |
| `allergies_note`, `conditions_note` | text | no | free text | context for the doctor brief |
| `bronze_id` | uuid | yes | -> `bronze_profile` | lineage |
| `created_at`, `updated_at` | timestamptz | yes | system | |

#### `medications` (one row per medicine)

| Column | Type | Required | Comes from | Used for |
|---|---|---|---|---|
| `id`, `user_id` | uuid | yes | system | |
| `name` | text | yes | user, or a prescription scan | display, matching to drug reference |
| `kind` | enum `prescription` / `otc` / `supplement` / `tcm` | yes | user or scan, default `prescription` | supplements and TCM are "not checked" for interactions; adherence counts prescription medicines only |
| `strength` | text | no | user or scan (e.g. "500 mg") | the brief, interaction checks |
| `frequency` | smallint | yes | user: doses per day | must equal the number of active rows in `medication_schedule` |
| `description` | text | no | user ("for sugar, with food") | what it is for and timing notes |
| `start_date`, `end_date` | date | no | user | window in which doses are expected; no end date = still taking |
| `total_quantity` | integer (0 or more) | **yes** | scan or user: the total tablets, capsules or units supplied, as printed on the label or typed in | predicting when the supply runs out (refill reminder). The six demo medicines hold a 30-day placeholder (doses per day x 30) |
| `drug_reference_id` | uuid | no | matched by name -> `drug_reference` | side-effect and interaction lookups |
| `source` | entry_source | yes | `manual` or `scan` | provenance |
| `bronze_id` | uuid | yes | -> `bronze_medication` | lineage |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | | system | |

#### `medication_schedule` (one row per dose time of a medicine)

Each row is one time of day the medicine is taken, so a medicine can have different times, quantities and meal settings (e.g. 2 tablets before breakfast, 1 after dinner), and several medicines each have their own rows. Like `exercise_sets`, it has no Bronze row of its own: the schedule is inside the `bronze_medication` payload. When a schedule changes, old rows are soft-deleted (`deleted_at`), never removed, so earlier dose logs keep their meaning.

| Column | Type | Required | Comes from | Used for |
|---|---|---|---|---|
| `id`, `user_id` | uuid | yes | system | |
| `medication_id` | uuid | yes | -> `medications` | which medicine |
| `dose_time` | time (local) | yes | user (e.g. 08:00) | when a dose is expected, reminders |
| `quantity` | numeric(4,1) | yes | user: number per dose in the medicine's own unit (e.g. 1, 2, 0.5 tablets) | the brief, how much per dose |
| `meal_relation` | enum `before_meal` / `after_meal` / `na` | yes | user, default `na` | overlay marker; comparing dose timing with logged meals |
| `when_to_take` | text: `morning` / `noon` / `afternoon` / `evening` / `night` / `bedtime` / `as_needed` | no | scan or user, only when the label names a part of the day ("every morning") | showing the dose in the person's own words; empty when the label only gives a number of times a day |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | | system | |

Rule: the number of active rows for a medicine equals `medications.frequency`.

Added 2026-10-07 for the medicine scan (F2), decided by Joely: `medications.total_quantity` and `medication_schedule.when_to_take` (migration 0024). `total_quantity` is required (Joely, 2026-10-07). The dose unit, the drowsiness warning and the minutes from food are not columns: they stay in the verbatim directions in `medications.description` and in the scan record (`prescription_scans.extraction`).


#### `medication_log` (dose log: one row per scheduled or extra dose)

Rows are generated from `medication_schedule` each day with `status = pending`, then updated when the user confirms.

| Column | Type | Required | Comes from | Used for |
|---|---|---|---|---|
| `id`, `user_id` | uuid | yes | system | |
| `medication_id` | uuid | yes | the schedule | which medicine |
| `schedule_id` | uuid | no | -> `medication_schedule`; empty for an extra, unscheduled dose | quantity and meal relation of this dose |
| `scheduled_at` | timestamptz | no | generated from `medication_schedule`; empty for an extra dose | expected time |
| `taken_at` | timestamptz | no | user taps "taken" | actual time |
| `status` | enum `pending` / `taken` / `missed` / `skipped` | yes | system; a job turns an untaken `pending` row into `missed` after the window | adherence; "late" is not stored, it is computed (taken more than 60 min after `scheduled_at`) |
| `miss_reason` | enum `forgot` / `side_effects` / `ran_out` / `felt_fine` / `cost` / `away_from_home` / `other` | no | user, asked after a miss | the brief; the barrier shown in `care_summary` |
| `source` | entry_source | yes | system | |
| `bronze_id` | uuid | no | -> `bronze_medication`; empty for a generated row until the user acts on it | lineage |
| `created_at`, `updated_at` | timestamptz | yes | system | |

Rules: `taken` needs `taken_at`; at least one of `scheduled_at` and `taken_at` is present.

#### `lab_results` (three tests only)

| Column | Type | Required | Comes from | Used for |
|---|---|---|---|---|
| `id`, `user_id` | uuid | yes | system | |
| `measured_at` | timestamptz | yes | user or document | trend |
| `test` | enum `hba1c` / `fasting_glucose` / `fasting_insulin` | yes | user or document | which test |
| `value` | numeric | yes | user or document | the result |
| `unit` | text | yes | fixed per test: `hba1c` = `%`; `fasting_glucose` = `mg/dL` or `mmol/L` as reported; `fasting_insulin` = `mcU/mL` | Gold converts glucose to mmol/L |
| `source` | entry_source | yes | system | |
| `bronze_id` | uuid | yes | -> `bronze_lab` | lineage |
| `created_at`, `deleted_at` | timestamptz | | system | |

`fasting_insulin` is the blood test, not insulin dosing (dosing is out of scope).

#### `consents` (unchanged)

`id`, `user_id`, `kind`, `version`, `granted_at`, `revoked_at`. An operational record of what the user agreed to; it has no Bronze twin.

### 4.2 Passive recording

#### `watch_readings` (one row per user per 5-minute bucket, delivered in batches)

A sync is one `bronze_watch` row. Each Silver row holds what happened *inside its bucket*, not a running total, so `sleep_minutes` is 0 by day and 1-5 overnight, and late or re-sent batches need no corrections. Primary key (`user_id`, `recorded_at`); re-sending a batch is an upsert.

| Column | Type | Required | Comes from | Used for |
|---|---|---|---|---|
| `user_id` | uuid | yes | | |
| `recorded_at` | timestamptz | yes | watch timestamp rounded to the 5-minute bucket start | the timeline clock |
| `heart_rate_bpm` | smallint | no | watch, average of the bucket | chart 1, exercise response |
| `hrv_rmssd_ms` | numeric(5,1) | no | watch (RMSSD); empty in many buckets | recovery signal, possible future chart |
| `spo2_pct` | numeric(4,1) | no | watch average (simulated in the demo) | chart 2 |
| `steps` | integer | no | watch, steps inside the bucket | overlay, daily total |
| `sleep_minutes` | smallint (0-5) | no | watch sleep tracking | sleep overlay and nightly total |
| `source` | entry_source | yes | `watch`, `replay` or `demo_dataset` | |
| `bronze_id` | uuid | yes | -> `bronze_watch` (the sync) | lineage |

At least one of the measurements is present. There is no activity score, stress score, body temperature or blood pressure here.

#### `cgm_readings` (continuous glucose)

Primary key (`user_id`, `recorded_at`).

| Column | Type | Required | Comes from | Used for |
|---|---|---|---|---|
| `user_id` | uuid | yes | | |
| `recorded_at` | timestamptz | yes | sensor timestamp | the glucose line |
| `glucose_mmol` | numeric(4,1) | yes | sensor, converted to mmol/L | chart 3, everything glucose |
| `quality_ok` | boolean | yes | sensor flags (warm-up, error) | Gold ignores bad readings |
| `source` | entry_source | yes | `cgm`; `manual` for a finger-prick, so it shares the timeline | |
| `bronze_id` | uuid | yes | -> `bronze_cgm` | lineage |

Sensors report every 5 or 15 minutes. Gold does not interpolate; buckets without a reading stay empty and charts connect the points.

#### `blood_pressure_readings` (a few readings a week)

Primary key (`user_id`, `recorded_at`).

| Column | Type | Required | Comes from | Used for |
|---|---|---|---|---|
| `user_id` | uuid | yes | | |
| `recorded_at` | timestamptz | yes | cuff or user entry | chart 4 (scatter) |
| `systolic_mmhg`, `diastolic_mmhg` | smallint | yes | cuff or user entry (simulated in the demo) | chart 4, baseline, brief |
| `source` | entry_source | yes | | |
| `bronze_id` | uuid | yes | -> `bronze_blood_pressure` | lineage |
| `deleted_at` | timestamptz | no | user deletes a wrong entry | |

### 4.3 Active recording

#### `exercise_logs`

| Column | Type | Required | Comes from | Used for |
|---|---|---|---|---|
| `id`, `user_id` | uuid | yes | system | |
| `start_at`, `end_at` | timestamptz | yes | user | the interval the timeline overlaps |
| `type` | enum `strength` / `walking` / `running` / `cycling` / `swimming` / `hiit` / `sports` / `yoga_pilates` / `stretching_mobility` / `dance` / `household_gardening` / `other` | yes | user picks | grouping, comparisons |
| `intensity` | smallint 1-5 | yes | user | dose-response of exercise |
| `feeling` | smallint 1-5 | no | user, afterwards | subjective context |
| `note` | text | no | user ("badminton", "leg day") | display |
| `source` | entry_source | yes | | |
| `bronze_id` | uuid | yes | -> `bronze_exercise` | lineage |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | | | |

#### `exercise_sets` (optional child, strength sessions only)

Keeps the E7-5 strength tracker. It has no Bronze row of its own; the sets are inside the session's `bronze_exercise` payload.

| Column | Type | Required | Notes |
|---|---|---|---|
| `id`, `user_id` | uuid | yes | |
| `exercise_log_id` | uuid | yes | -> `exercise_logs` |
| `exercise` | text | yes | |
| `exercise_order`, `set_no` | smallint | yes | unique with `exercise_log_id` |
| `reps` | smallint | yes | 1 to 200 |
| `weight_kg` | numeric(5,1) | no | empty means bodyweight |
| `rest_s` | smallint | no | |
| `rpe` | smallint | no | 1 to 10 |
| `performed_at` | timestamptz | yes | |
| `created_at` | timestamptz | yes | |

#### `food_logs`

| Column | Type | Required | Comes from | Used for |
|---|---|---|---|---|
| `id`, `user_id` | uuid | yes | system | |
| `start_at`, `end_at` | timestamptz | yes | user; the end defaults to start + 15 min | the meal interval |
| `meal_type` | enum `breakfast` / `lunch` / `dinner` / `snack` / `drink` | no | prefilled from the time of day, editable | overlay label |
| `food` | text | yes | user text, or the LLM's reading of a photo | overlay label, input to the estimate |
| `protein_g`, `carbs_g`, `fat_g`, `sugar_g`, `fibre_g` | numeric(5,1) | no | LLM estimate or user; `sugar_g` and `fibre_g` are parts of `carbs_g` | what drives the glucose response |
| `sodium_mg` | numeric(6,0) | no | same | blood pressure link |
| `estimated_by` | enum `user` / `llm_text` / `llm_photo` / `database` | yes | system | "AI estimate" labels |
| `source` | entry_source | yes | | |
| `bronze_id` | uuid | yes | -> `bronze_food` (photo, text and raw LLM answer) | lineage |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | | | |

#### `symptom_logs`

| Column | Type | Required | Comes from | Used for |
|---|---|---|---|---|
| `id`, `user_id` | uuid | yes | system | |
| `occurred_at` | timestamptz | yes | default now, editable | placed on the timeline |
| `symptom_type` | enum `numbness` / `tingling` / `blurred_vision` / `fatigue` / `thirst` / `frequent_urination` / `dizziness` / `headache` / `shaky_sweaty` / `nausea` / `foot_pain` / `slow_healing_wound` / `other` | yes | user picks | matching symptoms to highs and lows |
| `severity` | smallint 1-5 | yes | user ("how strong") | weighting |
| `duration_min` | integer | no | user | how long the overlay band lasts |
| `note` | text | no | user; frontend prompt: "Record which part of your body felt numbness" | neuropathy tracking; also describes an `other` symptom |
| `source` | entry_source | yes | | |
| `bronze_id` | uuid | yes | -> `bronze_symptom` | lineage |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | | | |

#### `wellbeing_logs` (mood, stress, sleep quality, energy)

| Column | Type | Required | Comes from | Used for |
|---|---|---|---|---|
| `id`, `user_id` | uuid | yes | system | |
| `recorded_at` | timestamptz | yes | default now, editable | placed on the timeline |
| `mood`, `stress_self`, `sleep_quality`, `energy` | smallint 1-5 | no each; at least one required | user sliders | overlay; compare `sleep_quality` with measured sleep |
| `source` | entry_source | yes | | |
| `bronze_id` | uuid | yes | -> `bronze_wellbeing` | lineage |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | | | |

---

## 5. GOLD

Gold is rebuilt from Silver and never written to by the app.

### 5.1 `timeline_5min`: the master temporal dataset

One row per user per 5-minute bucket, from the user's first data to now. The key is (`user_id`, `bucket_start`). **All four report charts read only from this table.**

**How it is built.** A SQL view `v_timeline_5min` defines it (a time grid left-joined to each Silver table). The result is also stored as the table `timeline_5min`, and after each ingested batch the affected days are deleted and rebuilt from the view. The view is the source of truth; the table is a cache.

Every feature below is empty when there is no data for that bucket.

| Group | Feature | Type | Meaning and rule | Built from |
|---|---|---|---|---|
| Key | `user_id` | uuid | | |
| | `bucket_start` | timestamptz | start of the 5-minute bucket, UTC | |
| Clock | `local_date` | date | the person's own day | `bucket_start` + `user_profile.timezone` |
| | `hour_of_day` | smallint | local hour 0-23 | same |
| Watch | `heart_rate_bpm` | smallint | | `watch_readings` |
| | `hrv_rmssd_ms` | numeric(5,1) | | `watch_readings` |
| | `spo2_pct` | numeric(4,1) | | `watch_readings` |
| | `steps` | integer | steps in the bucket | `watch_readings` |
| | `sleep_minutes` | smallint | minutes asleep in the bucket | `watch_readings` |
| | `steps_day_cum` | integer | steps so far today (since local midnight) | running sum of `steps` |
| | `sleep_min_night_cum` | integer | minutes slept since 18:00 local; resets at 18:00, so last night's total stays visible all day | running sum of `sleep_minutes` |
| Vs baseline | `hr_vs_baseline` | numeric(5,1) | `heart_rate_bpm` minus the baseline median for this hour | `baselines` (5.2) |
| | `hrv_vs_baseline` | numeric(5,1) | same for HRV | `baselines` |
| | `spo2_vs_baseline` | numeric(4,1) | same for SpO2 | `baselines` |
| | `glucose_vs_baseline` | numeric(4,1) | same for glucose | `baselines` |
| Blood pressure | `systolic_mmhg`, `diastolic_mmhg` | smallint | present only in the bucket containing a reading (one scatter point) | `blood_pressure_readings` |
| Glucose | `glucose_mmol` | numeric(4,1) | average of the valid readings in the bucket | `cgm_readings` (`quality_ok`) |
| | `glucose_change_1h` | numeric(4,1) | `glucose_mmol` minus the value 60 minutes earlier; empty if either is missing (the one momentum number) | `glucose_mmol` |
| | `glucose_zone` | enum `low` / `in_range` / `high` / `very_high` | below target low / between targets / above target high / above 13.9 | `glucose_mmol`, profile targets |
| Food, only while eating | `meal_id` | uuid | bucket is inside [`start_at`, `end_at`) of a meal; if two overlap, the later start wins | `food_logs` |
| | `meal_type` | enum | | `food_logs` |
| | `food` | text | | `food_logs` |
| | `carbs_g`, `protein_g`, `fat_g`, `sugar_g`, `fibre_g` | numeric(5,1) | that meal's nutrition | `food_logs` |
| | `sodium_mg` | numeric(6,0) | | `food_logs` |
| Exercise, only during the session | `exercise_id` | uuid | bucket is inside the session | `exercise_logs` |
| | `exercise_type` | enum | | `exercise_logs` |
| | `exercise_intensity` | smallint 1-5 | | `exercise_logs` |
| Medication, only at the dose bucket | `medication_names` | text | every medicine with a dose in this bucket, joined (e.g. "Metformin, Gliclazide"); medicines taken at different times land in different buckets | `medications` |
| | `dose_status` | enum `taken` / `late` / `missed` / `skipped` | taken and late sit in the bucket of `taken_at`; missed and skipped in the bucket of `scheduled_at`; `late` = taken more than 60 min after schedule; `pending` rows are not shown; if doses in one bucket differ, the worst wins (missed, then skipped, then late, then taken) | `medication_log` |
| | `meal_relation` | enum `before_meal` / `after_meal` / `na` / `mixed` | from the dose's schedule row (`na` for an extra dose); `mixed` if the doses in the bucket differ | `medication_schedule` via `medication_log.schedule_id` |
| | `doses` | jsonb | the full list for the bucket, `[{medication, quantity, status, meal_relation}]`, so nothing is lost when several medicines share a bucket | `medication_log`, `medication_schedule` |
| Wellbeing, only where logged | `mood`, `stress_self`, `sleep_quality`, `energy` | smallint 1-5 | in the bucket containing `recorded_at` | `wellbeing_logs` |
| Symptoms, across their duration | `symptom_type` | enum | in every bucket from `occurred_at` for `duration_min`; with no duration, one bucket; if two overlap, the more severe wins | `symptom_logs` |
| | `symptom_severity` | smallint 1-5 | | `symptom_logs` |
| | `symptom_duration_min` | integer | | `symptom_logs` |
| | `symptom_note` | text | the log's note (e.g. where the numbness is felt); repeated across the symptom's buckets so the overlay can show it | `symptom_logs` |
| Work schedule (scheduled, not measured) | `at_work` | boolean | true in buckets inside the person's work hours on a work day (local weekday in `work_days`, between `work_start` and `work_end`; a night shift belongs to the day it starts); empty otherwise or when no schedule was entered | `user_profile` |
| | `work_type` | enum | the profile's `work_type` while `at_work`, for the overlay label (e.g. "working: standing job") | `user_profile` |

44 features plus the 2-column key. The state label and demo flag of earlier drafts were removed: "resting versus asleep versus active" is read from `sleep_minutes`, `steps` and the exercise columns, and simulated points are marked from `source` on the Silver rows.

### 5.2 `baselines`: fixed, reset on purpose

A personal reference for "usual for this person". Built from the AGP-style idea used in glucose reports: the median by time of day with percentile bands, so it respects the daily rhythm and is not thrown off by spikes. It **does not move as the person's readings change**, so a decline cannot become the new normal.

Rules:
- **Window.** The first 14 days with enough data (at least 5 days with data for that metric). Imported histories shorter than 14 days (7-13) use what exists; `n_days` shows it.
- **Blood pressure** has no hourly pattern (a few readings a week), so its baseline is a single range from the **first 5 readings**, with no hour split.
- **Exercise is excluded** from heart rate and HRV baselines (buckets inside a logged session).
- **A baseline applies from the day after its window ends.** A new one is built only on a reset (`doctor_review`, `medication_change`, `user_reset`) from the 14 days (5 readings) after the reset date; the old one stays current until the new one completes. Old baselines are kept.
- The **current baseline for a date** is the latest one whose window ended before that date.

Primary key (`user_id`, `anchor_start`, `metric`, `hour_of_day`).

| Column | Type | Required | Meaning |
|---|---|---|---|
| `user_id` | uuid | yes | |
| `anchor_start`, `anchor_end` | date | yes | the days the baseline was built from |
| `metric` | enum `heart_rate` / `hrv` / `spo2` / `glucose` / `systolic` / `diastolic` | yes | |
| `hour_of_day` | smallint 0-23 | no | local hour; empty for blood pressure |
| `p05`, `p25`, `p50`, `p75`, `p95` | numeric(6,1) | yes | percentiles; `p50` is the baseline line, `p25`-`p75` the "typical" band, `p05`-`p95` the "usual range" |
| `n_days` | smallint | yes | days of data behind it |
| `n_points` | integer | yes | readings behind it, so thin evidence is visible |
| `reset_reason` | enum `first_14_days` / `doctor_review` / `medication_change` / `user_reset` | yes | why this baseline exists |

Roughly 100 rows per user per baseline (4 metrics x 24 hours + 2).

### 5.3 `daily_summary` (user x local day)

Primary key (`user_id`, `local_date`).

| Group | Columns | Type |
|---|---|---|
| Key | `user_id`, `local_date` | uuid, date |
| Glucose | `glucose_mean_mmol`, `glucose_sd_mmol`, `glucose_min_mmol`, `glucose_max_mmol` | numeric(4,1) |
| | `tir_pct`, `tbr_pct`, `tar_pct` (time in, below, above range), `cgm_coverage_pct` | numeric(4,1) |
| Watch | `steps_total` | integer |
| | `sleep_hours` | numeric(3,1) |
| | `resting_hr_bpm` (10th percentile of waking heart rate) | smallint |
| | `hrv_mean_ms`, `spo2_mean_pct` | numeric(5,1), numeric(4,1) |
| | `bp_systolic_mean`, `bp_diastolic_mean` | numeric(4,0) |
| Food | `meals_n` | smallint |
| | `carbs_g`, `protein_g`, `fat_g`, `sugar_g`, `fibre_g` | numeric(6,1) |
| | `sodium_mg` | numeric(6,0) |
| Exercise | `exercise_min` (integer), `exercise_sessions_n` (smallint) | |
| Medication | `doses_scheduled`, `doses_taken`, `doses_missed` | smallint |
| Symptoms and mood | `symptoms_n`, `symptom_worst_severity` | smallint |
| | `mood_avg`, `stress_self_avg`, `energy_avg`, `sleep_quality_avg` | numeric(2,1) |
| Context | `work_day` (a scheduled work day, from the profile) | boolean |
| Worse than usual | `hr_worse_pct`, `hrv_worse_pct`, `spo2_worse_pct`, `glucose_worse_pct` | numeric(4,1) |
| | `declining_metrics` | text[] |
| Quality | `data_quality` (jsonb), `built_at` | |

**Decline flag (as built).** `*_worse_pct` is the share of the day's readings on the **worse side** of the usual range for that hour: above `p95` for heart rate and glucose, below `p05` for HRV and SpO2 (about 5% on a normal day). Getting better, such as lower glucose after he starts walking, is not flagged. A day is flagged for a metric when more than **20%** of its readings are on the worse side; `declining_metrics` lists the metrics flagged on at least 3 of the last 5 days. Heart rate and HRV readings inside logged exercise are left out. The 20% and the 3-of-5 are starting values, not clinically validated numbers. The app wording is **"outside your usual range"**, never a diagnosis; the flag is a prompt for a doctor conversation. (The first version of this document flagged both sides at 25%; it flagged his improvement as decline, so it was changed.)

### 5.4 `meal_response` (one row per meal; key `food_log_id`)

| Column | Type | Meaning |
|---|---|---|
| `food_log_id` | uuid | -> `food_logs` |
| `user_id` | uuid | |
| `pre_glucose_mmol` | numeric(4,1) | mean of the 30 min before eating |
| `peak_glucose_mmol`, `minutes_to_peak`, `rise_mmol` | numeric, integer, numeric | highest value in the 3 h after the start, time to it, peak minus pre (never below zero: a meal eaten while glucose is falling has a rise of 0) |
| `glucose_1h_mmol`, `glucose_2h_mmol` | numeric(4,1) | value at +1 h and +2 h |
| `iauc_2h_mmol_min` | numeric(7,1) | area above the pre-meal level over 2 h |
| `minutes_to_baseline` | integer | minutes to return to the pre-meal level |
| `steps_next_2h` | integer | movement in the window, to separate food from walking |
| `spike_flag` | boolean | rise at least 2.5 mmol/L, or peak above target high |
| `built_at` | timestamptz | |

### 5.5 `exercise_response` (one row per session; key `exercise_log_id`)

| Column | Type | Meaning |
|---|---|---|
| `exercise_log_id` | uuid | -> `exercise_logs` |
| `user_id` | uuid | |
| `hr_pre_bpm`, `hr_avg_bpm`, `hr_peak_bpm`, `hr_30min_after_bpm` | smallint | heart rate before, during, at peak, and 30 min after |
| `glucose_pre_mmol`, `glucose_min_during_mmol`, `glucose_change_at_end` | numeric(4,1) | acute glucose effect |
| `glucose_1h_mmol`, `glucose_2h_mmol`, `glucose_12h_mmol` | numeric(4,1) | delayed effect |
| `post_exercise_low_flag` | boolean | glucose fell below target low |
| `built_at` | timestamptz | |

### 5.6 `glucose_events` (one row per excursion; the rows the doctor brief quotes)

An event is a run of CGM buckets above the target high (a `spike` if it lasts under 60 minutes, a `sustained_high` from 60 minutes) or a run of at least 10 minutes below the target low (a `low`). As built, Mr Tan has 280 events, 238 of them sustained highs, because his glucose is high after most meals; the brief should quote the worst few, not all.

| Column | Type | Meaning |
|---|---|---|
| `id`, `user_id` | uuid | |
| `event_type` | enum `spike` / `sustained_high` / `low` | |
| `started_at`, `extreme_at`, `ended_at` | timestamptz | start, peak or lowest point, end |
| `duration_min` | integer | |
| `start_glucose_mmol`, `extreme_glucose_mmol`, `rise_mmol` | numeric(4,1) | |
| `ctx_meal_id` | uuid | most recent meal that started in the 3 h before the event |
| `ctx_exercise_id` | uuid | session that ended in the 12 h before, or was under way |
| `ctx_dose_status` | enum | status of the nearest scheduled dose in the 12 h before |
| `ctx_heart_rate_bpm` | smallint | heart rate at the start |
| `ctx_stress_self` | smallint | latest stress score within 6 h |
| `ctx_symptom_type` | enum | symptom within 1 h of the event |
| `built_at` | timestamptz | |

The context windows (3 h, 12 h, 6 h, 1 h) are starting values.

### 5.7 Kept unchanged

`pattern_candidates`, `briefs`, `brief_shares`, `brief_share_access`, `memory_facts`, `memory_episodes` keep their current columns. `clinical_flags` is also kept: it is where the decline flag (`daily_summary.declining_metrics`) and adherence drops are written, with severity, status and a `brief_id`, so the brief and notifications can read them. `interaction_alerts` is unchanged (not reviewed here).

### 5.8 `care_summary` (user x local day)

Pulls adherence, preventive health and visit preparation into one row per person per day, so analysis, feedback to the user and the doctor brief can read from one place. Primary key (`user_id`, `local_date`); rebuilt daily.

| Group | Column | Type | Meaning | Built from |
|---|---|---|---|---|
| Key | `user_id`, `local_date` | uuid, date | | |
| Adherence | `adherence_7d_pct`, `adherence_30d_pct` | numeric(4,1) | doses taken (taken or late) divided by doses due; skipped counts as not taken; extra doses excluded | `medication_log` |
| | `doses_missed_7d` | smallint | | `medication_log` |
| | `longest_miss_streak_days` | smallint | longest run of days with a missed dose in the last 30 days | `medication_log` |
| | `top_miss_reason_30d` | enum | the most common `miss_reason`: the main barrier | `medication_log` |
| | `most_missed_time` | time | the scheduled dose time missed most often | `medication_log`, `medication_schedule` |
| | `days_to_runout` | smallint | days until the first medicine runs out | `refill_forecasts` |
| Preventive | `preventive_overdue` | text[] | check-ups past due (eye, foot, kidney, flu...) | `patient_preventive_status` |
| | `preventive_due_soon` | text[] | due in the next 30 days | `patient_preventive_status` |
| | `hba1c_days_since` | smallint | days since the last HbA1c | `lab_results` |
| Preparation | `open_questions_n` | smallint | questions not yet asked | `doctor_questions` |
| | `next_appointment_at` | timestamptz | | `appointments` |
| | `next_appointment_kind` | enum | | `appointments` |
| | `brief_status` | text | status of the latest doctor brief | `briefs` |
| Flags | `open_flags_n` | smallint | | `clinical_flags` |
| | `top_flag_severity` | enum | | `clinical_flags` |
| | `declining_metrics` | text[] | copied from `daily_summary` | `daily_summary` |

The 7- and 30-day windows and the skipped-counts-as-not-taken rule are starting choices. `top_miss_reason_30d` and `most_missed_time` only work if the app asks for a reason after a miss.

---

## 6. The four report charts

All four read from `timeline_5min`, with the baseline from `baselines` and the overlay from the same table.

| Chart | Y axis | Type | Baseline on the chart |
|---|---|---|---|
| 1 | `heart_rate_bpm` | continuous line | `p50` line, `p25`-`p75` and `p05`-`p95` bands for that hour; points outside `p05`-`p95` highlighted |
| 2 | `spo2_pct` | continuous line | same |
| 3 | `glucose_mmol` | continuous line, with `glucose_zone` shading | same |
| 4 | `systolic_mmhg`, `diastolic_mmhg` | scatter (non-empty buckets only) | horizontal range from the blood pressure baseline |

X axis is always time. Overlay on all four: steps (per bucket and daily total), sleep, food (spans labelled with `meal_type` and `food`), exercise (spans with type and intensity), medication markers (one per dose, showing status and `meal_relation`; several medicines at once are read from `doses`), mood markers, symptoms as spans with `symptom_note` on hover, and a shaded band for scheduled work hours (e.g. "working: standing job, Mon-Fri"). Simulated points are marked from `source`. HRV is kept in the table and can become a fifth chart later.

## 7. Later step (not designed yet)

Lifestyle recommendations for the user, based on the patterns in the timeline, `glucose_events`, the responses and the baseline flags. They will follow the project rules: wording like "outside your usual range", evidence shown with sample size, no diagnosis and no medication advice. A Gold table for them will be designed when this step starts.

## 8. Demo data plan: 3 months, synthetic

- One demo patient, **Mr Tan** (CGMacros participant 046): 91 days, 26,013 five-minute buckets from 2026-07-04 00:00 to 2026-10-02 07:40 Singapore time. Simulated or derived rows have `source = demo_dataset`; the real Dexcom glucose (2,856 buckets, the last 9.9 days), his 29 real meals and two real labs have `source = file_import`. Full plan and numbers: `docs/specs/demo-data-plan.md` and `docs/specs/mr-tan-profile.md`.
- Watch and CGM arrive as **batches** (four watch syncs a day, one CGM batch per day and origin); logs (food, exercise, symptoms, mood, medication) are generated to match, each with its own Bronze row.
- No baseline reset is included in the demo data. The generator is `scripts/generate_mr_tan.py`, the loader `scripts/load_mr_tan_v2.py`, the Gold builder `scripts/build_gold_v2.py`.

## 9. Migration notes (for deployment after approval)

### Old table to new home

| Old | New | Notes |
|---|---|---|
| `ingestion_events` | the 10 `bronze_*` tables | loaded datasets get one Bronze row per person per dataset (`file_import` or `demo_dataset`, `object_key` -> the original file); no raw payloads are invented |
| `users` | `users` | identity only |
| `patient_profiles`, `devices`, `body_measurements`, `allergies`, `conditions`, `health_goals` | `user_profile` | `sex` -> `gender` (`undisclosed` -> `prefer_not_to_say`); age -> `birth_year`; `race` filled only where the source has it (CGMacros `Self-identify`); work schedule and emergency contact start empty for loaded users; latest weight only; glucose targets only; allergies and conditions joined into text; family history, waist, other goals dropped |
| `patient_medications` | `medications` + `medication_schedule` | dose times become schedule rows; the old table has no quantity or meal relation, so loaded medicines get quantity 1 and `na` as placeholders (they are demo data); `medication_ingredients` dropped (`drug_reference` covers it) |
| `dose_events` | `medication_log` | status mapped; the old rule "a missed dose needs a reason" is relaxed (the system marks doses missed before the user explains) |
| `lab_results` | `lab_results` | only HbA1c, fasting glucose and fasting insulin kept; other tests and `egfr_reported` dropped |
| `health_samples`, `sleep_sessions` | `watch_readings` | re-bucketed to 5 minutes; heart rate, HRV, SpO2, steps and sleep kept; skin temperature, EDA, active energy, resting heart rate, distance and stress score dropped |
| `blood_pressure_readings` | `blood_pressure_readings` | pulse and context dropped |
| `glucose_readings` | `cgm_readings` | `context`, `meal_id`, `note`, `cgm_sprint_id` dropped; finger-pricks keep `source = manual` |
| `cgm_sprints` | none | CGM is continuous |
| `workouts`, `workout_sets` | `exercise_logs`, `exercise_sets` | |
| `meals`, `meal_items`, `meal_analyses` | `food_logs` | item list dropped; totals summed (including fibre and sodium); raw LLM output kept as Bronze |
| `symptom_logs`, `symptom_checkins` | `symptom_logs` | merged |
| `mood_checkins` | `wellbeing_logs` | |
| `consents` | `consents` | unchanged |
| `daily_aggregates` | `daily_summary` | |
| `meal_responses`, `food_responses` | `meal_response` | |
| `event_windows` | `timeline_5min` | |
| `baselines` (old) | `baselines` (new, fixed) | |

### Not part of this redesign (unchanged, not reviewed)

- **Reference:** `data_sources`, `drug_aliases`, `drug_reference`, `drug_side_effects`, `foods`, `interaction_rules`, `knowledge_chunks`, `knowledge_documents`, `population_priors`, `preventive_items`, `routing_rules`.
- **Operations:** `agent_runs`, `agent_steps`, `conversations`, `messages`, `event_log`, `guardrail_events`.
- **App tables** (section 1b): `notifications` (reminder state), `refill_forecasts` (computed; its `patient_medication_id` must be repointed to `medications.id`), `patient_preventive_status` (`last_done_on` is recorded, `next_due_on` is computed), `doctor_questions`, `appointments`, `prescription_scans` (feeds `medications`; the scan file itself is stored in `bronze_medication`). They back adherence support, preventive health and visit preparation, and `care_summary` reads from them.
- **Gold:** `interaction_alerts`.

### Proposed drops (confirm first)

`urgent_events`, `sprint_summaries`, `momentum_snapshots`, `nudge_stats`, and the old `state_profile` idea. (`clinical_flags` is kept.) `momentum_snapshots` and `nudge_stats` were not reviewed: confirm nothing reads them before dropping.

## 10. Decisions and open items

### Decided

| Decision | Decided by |
|---|---|
| Per-source Bronze and Silver tables; one-time inputs are Bronze too | Hong Yi, 2026-10-05 |
| Lean Silver columns (section 4) | Hong Yi, 2026-10-05 |
| Watch in 5-minute buckets, delivered in batches; sleep 0 by day | Hong Yi, 2026-10-04 |
| Blood pressure is its own table; body temperature and the watch activity and stress scores are not kept | Hong Yi, 2026-10-05 |
| HRV kept; lab tests limited to HbA1c, fasting glucose, fasting insulin; fibre and sodium added; gender and race added (race renamed from ethnicity on 2026-10-05); BP and SpO2 simulated | Joely, 2026-10-04 (included in this design) |
| Timeline features and current-only rule for food, exercise, medication, wellbeing and symptoms | Hong Yi, 2026-10-05 |
| Fixed baseline, reset on purpose; blood pressure baseline = first 5 readings | Hong Yi, 2026-10-05 |
| App wording "outside your usual range"; recommendations are a later step | Hong Yi, 2026-10-05 |
| Demo is 3 months of synthetic data | Hong Yi, 2026-10-05 |
| Emergency contact name, phone and relationship are required in the app form; the database columns stay nullable so imported and simulated users can exist without invented contacts | Hong Yi, 2026-10-05 |
| Medications: `times_per_day` renamed `frequency`; dose times, quantity per dose and meal relation (before / after / n.a.) are stored per dose time in the child table `medication_schedule`; strength is optional text and quantity is required | Hong Yi, 2026-10-05 |
| Work schedule (days, hours, type) is stored in the profile (same hours on the chosen days) and shown as a "scheduled work hours" overlay in `timeline_5min` and `daily_summary` | Hong Yi, 2026-10-05 |
| Symptom notes (e.g. where numbness is felt) are carried into the timeline | Hong Yi, 2026-10-05 |
| New Gold table `care_summary` (adherence, preventive health, visit preparation, flags); `clinical_flags` kept; five care tables grouped as App tables outside the Bronze -> Silver -> Gold pipeline | Hong Yi, 2026-10-05 |

### Open

1. **Team approval** of this design. The database has already been changed (section 11).
2. **Migrations are local only:** the shared database is at Alembic 0020, but 0017 to 0020 are not pushed yet. Anyone who runs `alembic` before they are pushed will get "can't locate revision 0020".
3. **Unreviewed tables** (section 9) and the proposed Gold drops. `momentum_snapshots`, `nudge_stats` and the others were dropped with the old Gold tables in 0018.
4. **Tune the starting values:** the 20% / 3-of-5 decline rule, the context windows in `glucose_events`, the 18:00 start of the sleep night, and the 60-minute "late" cutoff.
5. **Free-plan space:** after the reset the database is about 30 MB of 500 MB.
6. **Work-schedule history:** the work overlay applies the profile's current schedule to all past days. If a job change must not rewrite history, a dated schedule table is needed.

### Next steps (after approval)

1. Get team approval and push the migrations, scripts, tests and docs (nothing is committed yet).
2. Write the SQL view `v_timeline_5min` and its per-day rebuild (today the timeline is built by `scripts/build_gold_v2.py`).
3. Repoint the API and frontend to the new tables (they did not query the old ones directly), and the legacy loaders (section 11).
4. Update the frontend forms (birth year, gender and race, required emergency contact with relationship, work schedule, medication schedule with quantity and before / after meal per dose time, exercise types, fibre and sodium, symptom duration and note, blood pressure entry).
5. Fetch CGMacros `bio.csv` (race, fasting insulin) if wanted; until then `race` is empty and no fasting insulin exists.
6. Re-run `python scripts/make_data_dictionary.py` after any further migration.

## 11. As built (2026-10-05)

**Deployed to the shared Supabase project** with Alembic: 0017 (two new `entry_source` values, `watch` and `llm_estimate`), 0018 (the rebuild), 0019 (worse-side columns and prescription-only adherence view), 0020 (`trends.worse_pct`). The database now has 63 tables (+ `alembic_version`) and 6 views, every table has a `Layer: ...` comment and row-level security, and it is about 30 MB.

**Deleted:** the 34 old Bronze, Silver and Gold tables, the five old views, nine old enum types, and the other 23 demo users with everything of theirs. Reference, Operations and App tables were kept. The CSV export of all 68 old tables is in `data/processed/db_backup_2026-10-05/` (git-ignored; keep it, it is the only copy of the old loaded data because `data/raw/` is not on this machine). Migration 0018 cannot be reversed.

**Loaded for Mr Tan:** 1 profile, 6 medicines with 8 schedule rows and 554 dose-log rows, 5 labs, 26,013 watch buckets, 25,813 CGM readings (sensor-change gaps kept), 42 blood-pressure readings, 43 exercise sessions with 27 sets, 300 meals, 16 symptoms, 147 mood and sleep-quality logs, and 1,568 Bronze rows behind them.
**Built in Gold:** 26,013 timeline rows, 86 baseline rows, 91 daily and care summaries, 297 meal responses, 43 exercise responses, 280 glucose events, 8 clinical flags and 6 pattern candidates; care tables seeded (6 doctor questions, 96 notifications, 3 refill forecasts, 4 interaction alerts).

**Where the build differs from the design above** (all small, all in the code and the data dictionary):
- `user_profile.display_name` (required) and `medications.kind` were missing from the design and were added; `language` uses the existing `locale_code` enum; `miss_reason` and `meal_type` use the existing enums.
- `exercise_sets` keeps the columns of the old strength-tracker table.
- The decline rule looks at the worse side only, at 20% (section 5.3); adherence counts prescription medicines only; the `meal_response` rise is never below zero.
- Every `watch_readings` row has `source = demo_dataset` because every row has simulated or derived fields; where the heart rate is real, the Bronze payload says so (`hr_origin`). `cgm_readings` rows from the real Dexcom file are `file_import`.
- The timeline is built in Python (`scripts/build_gold_v2.py`); the SQL view `v_timeline_5min` is not written.
- Dish names for the 29 real meals are illustrative labels matched to the dataset's macros; the macros are the dataset's. Macros of simulated meals are team estimates.
- Sleep, steps and exercise sessions in the real window are derived from his real active energy and heart rate; HRV uses only the spread of a BIG IDEAs participant; race is empty and there is no fasting insulin (both need `bio.csv`).

**Legacy scripts that no longer match the database** (they write the old tables; not deleted, not run): `scripts/bronze.py`, `etl_common.py` helpers for Bronze, `import_cgmacros.py`, `import_bigideas.py`, `import_fitbit_kaggle.py`, `seed_demo.py`, `simulate_persona.py`, `replay.py`, `verify_loaded.py`, `load_all.py`. Replaced by `generate_mr_tan.py`, `load_mr_tan_v2.py`, `build_gold_v2.py`, `profile_mr_tan.py`, `v2_backup.py`, `plot_mr_tan.py` and `plot_report_charts.py`.

**Checks:** `python -m pytest services/api/tests/db -q` (68 tests, all pass) and `python scripts/check_schema.py` (63 of 63 tables, 6 of 6 views, row-level security on).
