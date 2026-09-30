# Schema — Smart Health (PostgreSQL 16 + pgvector)

Source of truth for the database. Any change here must ship with an Alembic migration, and any migration must be reflected here (see [rules.md](rules.md)). Feature IDs (F#) refer to [prd.md](prd.md).

## 0. Conventions

| Rule | Detail |
|---|---|
| Primary keys | `id uuid PRIMARY KEY DEFAULT gen_random_uuid()` |
| Ownership | Every patient-data table has `user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE` and an index on `(user_id, <time column>)` |
| Time | All timestamps `timestamptz`, stored UTC; display in `Asia/Singapore`. Column suffix `_at`. Dates use `date`, suffix `_on` |
| Audit columns | `created_at timestamptz NOT NULL DEFAULT now()`, `updated_at timestamptz NOT NULL DEFAULT now()` (trigger-maintained) on mutable tables |
| Soft delete | User-deletable logs have `deleted_at timestamptz NULL`; queries filter `deleted_at IS NULL` |
| Units (canonical) | glucose **mmol/L** `numeric(4,1)`; mass g; sodium mg; energy kcal; duration seconds `integer`; distance m |
| Enums | Postgres `CREATE TYPE … AS ENUM`; values listed below. Add values only via migration |
| Idempotency | Ingested rows carry `source` + `external_id`; `UNIQUE (user_id, source, external_id)` |
| JSONB | Only for semi-structured payloads (extractions, evidence, event payloads). Never for values we filter or aggregate on |
| Naming | snake_case, plural table names, FK column `<singular>_id` |
| Vectors | `vector(EMBED_DIM)`, where EMBED_DIM is set once from config at migration time; HNSW index, cosine |
| Row-level security | Enabled on every table with no policies, so the public API key gets nothing. Only the backend connects, with server-side credentials. Per-user policies are deferred |

## 0b. Layer map

Every table lives in the `public` schema. The layer says what kind of data it holds (see [memory.md](memory.md) sections 1 and 2).

| Layer | Tables and views |
|---|---|
| **Bronze** (raw, as received) | `ingestion_events` plus the stored original objects (meal photos, medication and supplement images, wearable and dataset exports, documents) |
| **Silver** (canonical, user-confirmed) | `users`, `patient_profiles`, `conditions`, `allergies`, `family_history`, `consents`, `prescription_scans`, `patient_medications`, `medication_ingredients`, `dose_events`, `refill_forecasts`, `glucose_readings`, `cgm_sprints`, `health_samples`, `sleep_sessions`, `meals`, `meal_items`, `meal_analyses`, `workouts`, `mood_checkins`, `symptom_logs`, `symptom_checkins`, `lab_results`, `blood_pressure_readings`, `body_measurements`, `appointments`, `doctor_questions`, `patient_preventive_status`, `devices`, `health_goals`, `notifications` |
| **Gold** (derived values and application memory) | `daily_aggregates`, `baselines`, `momentum_snapshots`, `clinical_flags`, `urgent_events`, `meal_responses`, `food_responses`, `sprint_summaries`, `event_windows`, `pattern_candidates`, `interaction_alerts`, `memory_facts`, `memory_episodes`, `nudge_stats`, `briefs`, `brief_shares`, `brief_share_access`; views `timeline_events`, `health_state`, `trends`, `adherence_summary`, `insight_context` |
| **Reference** (seeded, versioned) | `drug_reference`, `drug_aliases`, `drug_side_effects`, `interaction_rules`, `foods`, `preventive_items`, `routing_rules`, `population_priors`, `knowledge_documents`, `knowledge_chunks`, `data_sources` |
| **Operations** (cross-cutting) | `agent_runs`, `agent_steps`, `guardrail_events`, `conversations`, `messages`, `event_log` |

---

## 1. Enums

```sql
CREATE TYPE locale_code        AS ENUM ('en','zh','ms','ta');
CREATE TYPE sex_type           AS ENUM ('female','male','other','undisclosed');
CREATE TYPE med_kind           AS ENUM ('prescription','otc','supplement','tcm');
CREATE TYPE med_status         AS ENUM ('active','paused','stopped');
CREATE TYPE entry_source       AS ENUM ('manual','scan','onboarding_chat','health_connect','healthkit','file_import','cgm','replay','demo_dataset','system');
CREATE TYPE scan_status        AS ENUM ('uploaded','extracting','needs_review','confirmed','rejected','failed');
CREATE TYPE dose_status        AS ENUM ('scheduled','taken','taken_late_logged','unconfirmed','missed','skipped_by_plan');
CREATE TYPE miss_reason        AS ENUM ('forgot','side_effects','ran_out','felt_fine','cost','away_from_home','other');
CREATE TYPE interaction_severity AS ENUM ('minor','moderate','major','unknown');
CREATE TYPE glucose_context    AS ENUM ('fasting','pre_meal','post_meal_2h','bedtime','random','cgm');
CREATE TYPE meal_type          AS ENUM ('breakfast','lunch','dinner','snack','drink');
CREATE TYPE gi_category        AS ENUM ('low','medium','high','unknown');
CREATE TYPE sample_metric      AS ENUM ('steps','heart_rate','resting_heart_rate','hrv_rmssd','sleep_session','spo2','stress_score','active_energy','distance','skin_temp','eda');
CREATE TYPE lab_kind           AS ENUM ('hba1c','fasting_glucose','total_chol','ldl','hdl','triglycerides','creatinine','uacr','egfr_reported');
CREATE TYPE timeline_stream    AS ENUM ('meal','dose','workout','glucose_event','symptom','sleep','checkin','urgent');
CREATE TYPE workout_intensity  AS ENUM ('light','moderate','vigorous');
CREATE TYPE flag_severity      AS ENUM ('watch','review','urgent');
CREATE TYPE flag_status        AS ENUM ('open','acknowledged','in_brief','resolved','dismissed');
CREATE TYPE urgent_tier        AS ENUM ('hypo_selfcare','seek_care_today','urgent_now');
CREATE TYPE fact_category      AS ENUM ('preference','routine','barrier','food_response','goal','context');
CREATE TYPE fact_status        AS ENUM ('proposed','active','superseded','rejected');
CREATE TYPE appointment_kind   AS ENUM ('gp_review','diabetes_review','eye_screening','foot_screening','kidney_test','hba1c_test','vaccination','dental','other');
CREATE TYPE appointment_status AS ENUM ('suggested','planned','completed','cancelled','missed');
CREATE TYPE brief_status       AS ENUM ('generating','ready','failed','superseded');
CREATE TYPE consent_kind       AS ENUM ('data_processing','brief_sharing','calendar_access','caregiver_view','research_use');
CREATE TYPE notification_kind  AS ENUM ('dose_reminder','dose_renudge','miss_reason','checkin','nudge','refill','appointment','urgent','clash','brief_ready');
CREATE TYPE actor_type         AS ENUM ('user','agent','system','clinician_link');
CREATE TYPE guard_verdict      AS ENUM ('pass','blocked_med_advice','blocked_diagnosis','urgent','blocked_injection','blocked_uncited','blocked_other');
CREATE TYPE knowledge_kind     AS ENUM ('drug','lifestyle','hypo_guidance','condition_education','food');
CREATE TYPE evidence_status    AS ENUM ('observed','derived','inferred','reference_matched');   -- nothing is 'validated'
CREATE TYPE relationship_type  AS ENUM ('user_reported','temporal_association','observed_association','repeated_observation');
CREATE TYPE goal_kind          AS ENUM ('weekly_moderate_minutes','weekly_strength_sessions','daily_steps','sleep_hours','fasting_glucose_range','custom');
CREATE TYPE device_kind        AS ENUM ('watch','cgm','glucometer','phone_camera','other');
```

---

## 2. Identity, profile and consent (F1)

### users
| column | type | constraints |
|---|---|---|
| id | uuid | PK |
| email | citext | UNIQUE, NULL (demo users may lack) |
| password_hash | text | NULL (if OAuth) |
| locale | locale_code | NOT NULL DEFAULT 'en' |
| timezone | text | NOT NULL DEFAULT 'Asia/Singapore' |
| onboarding_completed_at | timestamptz | NULL |
| is_demo | boolean | NOT NULL DEFAULT false |
| created_at / updated_at | timestamptz | |

### patient_profiles (1:1 users)
| column | type | constraints |
|---|---|---|
| user_id | uuid | PK, FK users |
| display_name | text | NOT NULL (never sent to LLM) |
| birth_year | smallint | CHECK 1900..current year |
| sex | sex_type | NOT NULL DEFAULT 'undisclosed' |
| height_cm | numeric(5,1) | CHECK 100..250 |
| weight_kg | numeric(5,1) | CHECK 25..300 |
| diabetes_type | text | NOT NULL CHECK = 'type2' |
| diagnosed_year | smallint | NULL |
| last_hba1c_pct | numeric(3,1) | CHECK 4.0..20.0 |
| last_hba1c_on | date | NULL |
| targets | jsonb | e.g. `{"fasting":[4.0,7.0],"post_meal_max":10.0,"hba1c_max":7.0}`, doctor-set or defaults, with `source` |
| smoker | boolean | NULL |
| onboarding_method | text | CHECK IN ('form','chat') |

### conditions
`id, user_id, name text NOT NULL, code text NULL (e.g. SNOMED/ICD if known), since_year smallint NULL, notes text, created_at, updated_at, deleted_at`. Comorbidities (e.g. hypertension, hyperlipidaemia).

### allergies
`id, user_id, substance text NOT NULL, reaction text NULL, severity text NULL, created_at, updated_at, deleted_at`.

### family_history
`id, user_id, relation text NOT NULL, condition text NOT NULL, created_at`.

### consents
| column | type | constraints |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK |
| kind | consent_kind | NOT NULL |
| version | text | NOT NULL (consent text version) |
| granted_at | timestamptz | NOT NULL |
| revoked_at | timestamptz | NULL |
| | | Partial UNIQUE (user_id, kind) WHERE revoked_at IS NULL |

---

## 3. Medications, scans, adherence, clashes (F2–F5)

### drug_reference (seeded)
`id, generic_name text NOT NULL UNIQUE, brand_names text[] NOT NULL DEFAULT '{}', atc_code text NULL, kind med_kind NOT NULL, knowledge_doc_id uuid NULL FK knowledge_documents`. Used to normalise names for clash lookup.

### prescription_scans
| column | type | constraints |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK |
| image_key | text | NOT NULL (object storage key) |
| status | scan_status | NOT NULL DEFAULT 'uploaded' |
| extraction | jsonb | model output: `{items:[{field:{value,confidence}}]}` |
| model_id | text | NULL |
| agent_run_id | uuid | FK agent_runs NULL |
| error | text | NULL |
| created_at / updated_at | timestamptz | |

### patient_medications
| column | type | constraints |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK |
| drug_reference_id | uuid | FK drug_reference NULL (NULL = unrecognised → clash "not checked") |
| display_name | text | NOT NULL (as on label) |
| kind | med_kind | NOT NULL |
| strength | text | NULL (e.g. "500 mg") |
| dose_amount | numeric(6,2) | NULL (units per intake, e.g. 1 tablet) |
| dose_unit | text | NULL |
| times_per_day | smallint | CHECK 1..6 |
| schedule_times | time[] | NOT NULL (local times, length = times_per_day) |
| with_food | boolean | NOT NULL DEFAULT false |
| window_minutes | smallint | NOT NULL DEFAULT 120 CHECK 30..360 |
| instructions | text | NULL (verbatim from label) |
| prescriber | text | NULL |
| prescribed_on | date | NULL |
| start_on | date | NOT NULL |
| end_on | date | NULL CHECK end_on >= start_on |
| quantity_dispensed | integer | NULL |
| status | med_status | NOT NULL DEFAULT 'active' |
| source | entry_source | NOT NULL |
| scan_id | uuid | FK prescription_scans NULL |
| confirmed_by_user_at | timestamptz | NOT NULL (no unconfirmed meds are active) |
| created_at / updated_at | timestamptz | |

### dose_events
One row per scheduled intake, generated by `adherence.py` 7 days ahead.
| column | type | constraints |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK |
| patient_medication_id | uuid | FK patient_medications ON DELETE CASCADE |
| scheduled_at | timestamptz | NOT NULL |
| window_end_at | timestamptz | NOT NULL CHECK > scheduled_at |
| status | dose_status | NOT NULL DEFAULT 'scheduled' |
| confirmed_at | timestamptz | NULL |
| miss_reason | miss_reason | NULL |
| miss_note | text | NULL |
| reason_captured_at | timestamptz | NULL |
| | | UNIQUE (patient_medication_id, scheduled_at) |
| | | CHECK (status IN ('missed') ⇒ miss_reason IS NOT NULL) |
| | | CHECK (status IN ('taken','taken_late_logged') ⇒ confirmed_at IS NOT NULL) |

Status transitions (enforced in service + tested): `scheduled → taken | unconfirmed | skipped_by_plan`; `unconfirmed → taken_late_logged | missed`. No other transitions.

### interaction_rules (seeded reference)
`id, drug_a_id uuid FK drug_reference, drug_b_id uuid FK drug_reference, severity interaction_severity NOT NULL, mechanism text, patient_text_key text NOT NULL (i18n key for plain-language text), source text NOT NULL, source_url text, CHECK drug_a_id < drug_b_id, UNIQUE (drug_a_id, drug_b_id)`.

### interaction_alerts
`id, user_id, med_a_id uuid FK patient_medications, med_b_id uuid FK patient_medications NULL, interaction_rule_id uuid FK NULL, status text CHECK IN ('open','acknowledged','resolved_by_clinician','not_checked'), created_at, acknowledged_at`. `not_checked` rows record items with no reference match (honest uncertainty).

### refill_forecasts
`patient_medication_id uuid PK FK, remaining_units numeric, runs_out_on date, reminder_sent_at timestamptz NULL, computed_at`.

---

## 4. Measurements and logs (F6, F7)

### glucose_readings
| column | type | constraints |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK |
| measured_at | timestamptz | NOT NULL |
| value_mmol | numeric(4,1) | NOT NULL CHECK 1.0..35.0 |
| context | glucose_context | NOT NULL |
| source | entry_source | NOT NULL |
| external_id | text | NULL |
| cgm_sprint_id | uuid | FK cgm_sprints NULL |
| device | text | NULL (e.g. 'dexcom_g6', 'libre_pro', 'glucometer') |
| quality_ok | boolean | NOT NULL DEFAULT true (false = sensor flagged reading as unreliable; excluded from stats) |
| native_interval_min | smallint | NULL (5 for Dexcom, 15 for Libre Pro; used by TIR/response calculations) |
| meal_id | uuid | FK meals NULL (for pre/post-meal) |
| note | text | NULL |
| deleted_at | timestamptz | NULL |
| | | UNIQUE (user_id, source, external_id); INDEX (user_id, measured_at DESC) |

Inputs in mg/dL are converted at the API (÷ 18.0, round to 0.1) and never stored in mg/dL.

### cgm_sprints
`id, user_id, device text, started_at timestamptz NOT NULL, ended_at timestamptz NULL, planned_days smallint DEFAULT 14, purpose text, created_at`. Constraint: at most one open sprint per user (partial unique index WHERE ended_at IS NULL).

### health_samples (wearables)
| column | type | constraints |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK |
| metric | sample_metric | NOT NULL |
| start_at | timestamptz | NOT NULL |
| end_at | timestamptz | NOT NULL CHECK >= start_at |
| value | numeric | NOT NULL (steps count, bpm, ms, %, score, seconds asleep) |
| unit | text | NOT NULL |
| detail | jsonb | NULL (e.g. sleep stages) |
| source | entry_source | NOT NULL |
| device | text | NULL |
| external_id | text | NOT NULL |
| | | UNIQUE (user_id, source, external_id); INDEX (user_id, metric, start_at DESC) |

### foods (seeded reference, local food DB)
`id, name text NOT NULL, category text NULL (staple, drink, alcohol, snack, packaged...), gi_source text NULL, aliases text[] DEFAULT '{}', locale_names jsonb, serving_desc text, serving_g numeric, kcal numeric, carbs_g numeric, sugar_g numeric, fibre_g numeric, protein_g numeric, fat_g numeric, sodium_mg numeric, gi gi_category DEFAULT 'unknown', flags text[] (computed: high_sodium, high_sugar, high_gi), source text NOT NULL`. Trigram index on name + aliases.

### meals
`id, user_id, eaten_at timestamptz NOT NULL, meal_type meal_type NOT NULL, photo_key text NULL, description text NULL, source entry_source, deleted_at, created_at, updated_at`.

### meal_items
`id, meal_id uuid FK meals ON DELETE CASCADE, food_id uuid FK foods NULL, custom_name text NULL, portion_multiplier numeric(4,2) NOT NULL DEFAULT 1.0 CHECK 0.1..5, carbs_g numeric, sugar_g numeric, sodium_mg numeric, kcal numeric, protein_g numeric, fat_g numeric, fibre_g numeric, alcohol_units numeric(3,1) NOT NULL DEFAULT 0, estimated_by text CHECK IN ('dataset','llm_estimate','user','food_db'), estimate_confidence numeric(3,2) NULL CHECK 0..1, evidence_status evidence_status NOT NULL DEFAULT 'inferred', analysis_id uuid FK meal_analyses NULL`. CHECK (food_id IS NOT NULL OR custom_name IS NOT NULL). Nutrients are snapshotted at log time (foods may be edited later). LLM estimates start as `llm_estimate` / `inferred`; when the user confirms or edits them they become `user` / `observed`. Dataset meals (CGMacros, BIG IDEAs) are `dataset` / `observed` and their parent meal is marked `demo_dataset`.

### meal_responses (per meal, CGM sprint only)
`meal_id uuid PK FK meals, baseline_mmol numeric(4,1), peak_rise_mmol numeric(4,1), iauc_mmol_min numeric(7,1), window_complete boolean NOT NULL, is_mixed boolean NOT NULL, dominant_food_id uuid FK foods NULL, computed_at`.

### food_responses (per user × food aggregate)
`user_id, food_id, n smallint NOT NULL, mean_iauc numeric, min_iauc numeric, max_iauc numeric, mean_peak_rise numeric, rank_pct numeric (0–1 vs user's other foods), updated_at`, PK (user_id, food_id). Surface only when n ≥ 2.

### workouts
`id, user_id, started_at timestamptz NOT NULL, duration_s integer NOT NULL CHECK > 0, activity text NOT NULL, intensity workout_intensity NOT NULL, kcal numeric NULL, avg_hr numeric NULL, source entry_source, external_id text NULL, deleted_at`, UNIQUE (user_id, source, external_id).

### mood_checkins
`id, user_id, checked_on date NOT NULL, mood smallint CHECK 1..5, stress smallint CHECK 1..5, sleep_quality smallint CHECK 1..5, energy smallint CHECK 1..5, note text NULL, created_at`, UNIQUE (user_id, checked_on).

### symptom_logs
`id, user_id, occurred_at timestamptz NOT NULL, symptom text NOT NULL, symptom_code text NULL, severity smallint CHECK 1..5, note text, source text CHECK IN ('user','checkin'), checkin_id uuid FK symptom_checkins NULL, deleted_at, created_at`.

### symptom_checkins (F9)
`id, user_id, question_key text NOT NULL (i18n key), triggered_by_flag_id uuid FK clinical_flags NULL, asked_at timestamptz, answered_at timestamptz NULL, answer jsonb NULL, skipped boolean DEFAULT false`.

---

## 5. Derived analytics (F8, F10)

### daily_aggregates
PK (user_id, day date). Columns: `fasting_glucose_mean, postmeal_glucose_mean, glucose_readings_n, tir_pct (CGM days), tbr_pct, tar_pct, steps, workout_min, sleep_min, sleep_midpoint_min, resting_hr, hrv_rmssd, mood, stress, carbs_g, sugar_g, sodium_mg, meals_n, doses_scheduled, doses_taken, adherence_pct, logged_streams smallint`, `computed_at`. All `numeric NULL` (NULL = no data, never 0).

### baselines
`user_id, metric text, computed_on date, median numeric, mad numeric, n_days smallint, status text CHECK IN ('learning','ready')`, PK (user_id, metric, computed_on).

### momentum_snapshots
`user_id, metric text, day date, value numeric, z numeric, ewma numeric, slope numeric, accel numeric`, PK (user_id, metric, day).

### clinical_flags
| column | type | constraints |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK |
| kind | text | NOT NULL (e.g. 'momentum_drift','momentum_accel','hypo_event','high_repeat','adherence_drop','side_effect_report','clash') |
| metric | text | NULL |
| severity | flag_severity | NOT NULL |
| status | flag_status | NOT NULL DEFAULT 'open' |
| evidence | jsonb | NOT NULL (numbers + row ids that caused it) |
| patient_message_key | text | NULL (neutral i18n text) |
| first_seen_on / last_seen_on | date | NOT NULL |
| brief_id | uuid | FK briefs NULL |
| created_at / updated_at | | |

### urgent_events
`id, user_id, tier urgent_tier NOT NULL, trigger jsonb NOT NULL (reading id / symptom id / rule id), shown_at timestamptz NOT NULL, acknowledged_at timestamptz NULL, user_action text NULL`.

---

## 6. Preventive care, appointments, questions (F13, F14)

### preventive_items (seeded reference)
`id, kind appointment_kind UNIQUE, interval_months smallint NOT NULL, label_key text NOT NULL, source text NOT NULL`.

### patient_preventive_status
`user_id, preventive_item_id, last_done_on date NULL, next_due_on date NULL, status text CHECK IN ('ok','due_soon','overdue','unknown'), updated_at`, PK (user_id, preventive_item_id).

### appointments
`id, user_id, kind appointment_kind NOT NULL, status appointment_status NOT NULL, scheduled_for timestamptz NULL, location text NULL, suggested_reason jsonb NULL (flag ids / due item), calendar_event_id text NULL, confirmed_by_user_at timestamptz NULL, brief_id uuid FK briefs NULL, created_at, updated_at`. CHECK (calendar_event_id IS NULL OR confirmed_by_user_at IS NOT NULL).

### doctor_questions
`id, user_id, text text NOT NULL, origin text CHECK IN ('user','refused_chat','checkin','agent_suggested'), status text CHECK IN ('open','asked','archived'), brief_id uuid FK NULL, created_at`.

---

## 7. Doctor brief (F12)

### briefs
| column | type | constraints |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK |
| period_start / period_end | date | NOT NULL, CHECK end >= start |
| status | brief_status | NOT NULL |
| data | jsonb | NOT NULL (BriefData snapshot, all numbers) |
| narrative | jsonb | NULL (sentences with evidence ids) |
| html_key / pdf_key | text | NULL |
| appointment_id | uuid | FK NULL |
| agent_run_id | uuid | FK agent_runs NULL |
| validator_report | jsonb | NULL (rejected sentences, reasons) |
| generated_at | timestamptz | |

Briefs are **immutable** once `ready`; regenerating creates a new row and marks the old one `superseded`.

### brief_shares
`id, brief_id FK briefs ON DELETE CASCADE, token_hash text NOT NULL UNIQUE (sha256), expires_at timestamptz NOT NULL, revoked_at timestamptz NULL, consent_id uuid FK consents NOT NULL, created_at`.

### brief_share_access
`id, brief_share_id FK, accessed_at timestamptz NOT NULL, ip_hash text, user_agent text`.

---

## 8. Agents, memory, knowledge

### conversations / messages
`conversations(id, user_id, started_at, ended_at, locale, summary_episode_id uuid NULL)`
`messages(id, conversation_id FK, role text CHECK IN ('user','assistant','system_template'), content text NOT NULL, agent_run_id uuid NULL, guard_verdict guard_verdict NULL, tts_audio_key text NULL, created_at)`.

### agent_runs
`id, user_id NULL, agent text NOT NULL, trigger text CHECK IN ('chat','scan','nightly','brief','onboarding','checkin'), model_id text, prompt_version text, status text CHECK IN ('running','ok','guard_blocked','error'), input_tokens int, output_tokens int, latency_ms int, error text, started_at, finished_at`.

### agent_steps
`id, agent_run_id FK ON DELETE CASCADE, seq smallint NOT NULL, node text NOT NULL, tool text NULL, input_digest text, output jsonb, latency_ms int, created_at`, UNIQUE (agent_run_id, seq).

### guardrail_events
`id, agent_run_id FK NULL, user_id, stage text CHECK IN ('input','output'), verdict guard_verdict NOT NULL, rule_id text NOT NULL, excerpt text (≤ 300 chars), created_at`.

### memory_facts (user model, F16)
| column | type | constraints |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK |
| key | text | NOT NULL (namespaced, e.g. `routine.walk_time`, `barrier.evening_dose`, `food.chicken_rice.response`) |
| category | fact_category | NOT NULL |
| value | jsonb | NOT NULL |
| statement_key | text | NULL (i18n template) / `statement` text for display |
| confidence | numeric(3,2) | NOT NULL CHECK 0..1 |
| evidence_status | evidence_status | NOT NULL (`inferred` when proposed by reflection; `observed` when the user stated or confirmed it) |
| evidence_refs | jsonb | NOT NULL (array of {table,id}) |
| status | fact_status | NOT NULL |
| version | integer | NOT NULL DEFAULT 1 |
| supersedes_id | uuid | FK memory_facts NULL |
| source | text | CHECK IN ('reflection','user','onboarding') |
| user_confirmed_at | timestamptz | NULL |
| last_evidence_at | timestamptz | NOT NULL |
| created_at / updated_at | | |
| | | Partial UNIQUE (user_id, key) WHERE status = 'active' |

`rejected` facts are kept (so the same key+value isn't re-proposed).

### memory_episodes
`id, user_id, conversation_id FK NULL, occurred_at timestamptz, summary text NOT NULL, topics text[], embedding vector(EMBED_DIM) NOT NULL, created_at`. HNSW index on embedding (cosine), btree (user_id, occurred_at).

### nudge_stats (adaptive nudging)
`user_id, nudge_type text, time_slot smallint (0–23), sent int DEFAULT 0, acted int DEFAULT 0, updated_at`, PK (user_id, nudge_type, time_slot).

### knowledge_documents / knowledge_chunks
`knowledge_documents(id, kind knowledge_kind, title, source_org text NOT NULL, source_url text, licence text NOT NULL, locale locale_code, version text, retrieved_on date, active boolean DEFAULT true)`
`knowledge_chunks(id, document_id FK ON DELETE CASCADE, seq int, content text NOT NULL, locale locale_code, embedding vector(EMBED_DIM) NOT NULL, tokens int)`, UNIQUE (document_id, seq), HNSW on embedding.

---

## 9. Notifications and event log (all steps logged)

### notifications
`id, user_id, kind notification_kind NOT NULL, ref_table text NULL, ref_id uuid NULL, scheduled_for timestamptz NOT NULL, sent_at timestamptz NULL, opened_at timestamptz NULL, acted_at timestamptz NULL, action text NULL, channel text CHECK IN ('push','local','in_app'), payload jsonb`. INDEX (user_id, scheduled_for).

### event_log (append-only audit trail)
| column | type | constraints |
|---|---|---|
| id | bigint | PK GENERATED ALWAYS AS IDENTITY |
| occurred_at | timestamptz | NOT NULL DEFAULT now() |
| user_id | uuid | NULL (system events) |
| actor | actor_type | NOT NULL |
| event | text | NOT NULL (dot-namespaced, catalogue in flow.md §4) |
| entity_table | text | NULL |
| entity_id | uuid | NULL |
| payload | jsonb | NOT NULL DEFAULT '{}' (no free-text health notes, only ids and enums) |
| client_event_id | uuid | NULL, UNIQUE (dedupe client batches) |
| agent_run_id | uuid | NULL |
| prev_hash / hash | text | hash = sha256(prev_hash ‖ row content); tamper-evident chain per user |

App DB role has `INSERT, SELECT` only on `event_log` (no UPDATE/DELETE). INDEX (user_id, occurred_at DESC), (event).

---

## 9b. Data-plan additions (added 2026-09-29)

These tables support the lifestyle timeline (F18), fuller clinical history, and dataset provenance. Sources are cited-only (prd.md A10).

### lab_results
`id, user_id, kind lab_kind NOT NULL, value numeric NOT NULL, unit text NOT NULL (canonical: % for hba1c, mmol/L for glucose and lipids, umol/L creatinine, mg/g uacr, mL/min/1.73m² egfr), taken_on date NOT NULL, source entry_source NOT NULL, external_id text NULL, note text NULL, deleted_at, created_at`. UNIQUE (user_id, source, external_id); INDEX (user_id, kind, taken_on DESC). `patient_profiles.last_hba1c_*` become a cached copy of the newest `hba1c` row (updated in the same transaction). eGFR is computed in code (CKD-EPI 2021) when creatinine, age and sex are known; `egfr_reported` is only for values printed on a lab report.

### blood_pressure_readings
`id, user_id, measured_at timestamptz NOT NULL, systolic smallint CHECK 60..260, diastolic smallint CHECK 30..160 (CHECK diastolic < systolic), pulse smallint NULL CHECK 30..220, context text CHECK IN ('home','clinic'), source entry_source NOT NULL, external_id text NULL, deleted_at`. UNIQUE (user_id, source, external_id).

### body_measurements
`id, user_id, measured_at timestamptz NOT NULL, weight_kg numeric(5,1) NULL CHECK 25..300, waist_cm numeric(5,1) NULL CHECK 40..200, source entry_source NOT NULL, external_id text NULL, deleted_at`. CHECK (weight_kg IS NOT NULL OR waist_cm IS NOT NULL).

### sleep_sessions
`id, user_id, start_at timestamptz NOT NULL, end_at timestamptz NOT NULL CHECK end_at > start_at, asleep_min int NOT NULL, awake_min int NULL, light_min int NULL, deep_min int NULL, rem_min int NULL, efficiency_pct numeric(4,1) NULL, source entry_source NOT NULL, device text NULL, external_id text NOT NULL`. UNIQUE (user_id, source, external_id); INDEX (user_id, start_at DESC). Stage columns are NULL when the device reports only asleep/awake. `daily_aggregates.sleep_min` and `sleep_midpoint_min` are computed from this table.

### medication_ingredients
`id, patient_medication_id uuid FK patient_medications ON DELETE CASCADE, ingredient_name text NOT NULL, drug_reference_id uuid FK drug_reference NULL (NULL = unmatched → "not checked"), amount numeric NULL, unit text NULL, source text CHECK IN ('label_photo','user')`. Supplements and TCM products list several ingredients; the clash checker runs per ingredient. Prescription items normally have one row (or none, using `patient_medications.drug_reference_id`).

### prescription_scans (changes)
ADD `item_type text CHECK IN ('prescription_label','blister_or_box','supplement','tcm','otc','unknown')`, `photo_count smallint NOT NULL DEFAULT 1`, `quality_ok boolean`, `prompt_version text`, `extraction_review jsonb` (which fields the user changed, so accuracy per field and item type can be reported). Patient name, NRIC, address and phone are removed from `extraction` before it is stored.

### drug_aliases
`id, drug_reference_id uuid FK drug_reference ON DELETE CASCADE, alias text NOT NULL, locale locale_code NULL, kind text CHECK IN ('brand','generic','local_name'), source text NOT NULL`. UNIQUE (drug_reference_id, lower(alias)). Trigram index on alias. Aliases are for name matching only. The app never suggests a substitute.

### drug_side_effects
`id, drug_reference_id uuid FK ON DELETE CASCADE, effect_key text NOT NULL (i18n key), source text NOT NULL, frequency_band text NULL CHECK IN ('very_common','common','uncommon','rare')`. `frequency_band` stays NULL unless an authoritative label states it. UNIQUE (drug_reference_id, effect_key).

### population_priors
`metric text NOT NULL, sex sex_type NOT NULL, age_band text NOT NULL ('40-49','50-59','60-69'), has_diabetes boolean NOT NULL, p10, p25, p50, p75, p90 numeric, n integer NOT NULL, source text NOT NULL (e.g. 'NHANES 2017-2018'), PRIMARY KEY (metric, sex, age_band, has_diabetes, source)`. Used only to cold-start baselines (`baselines.status = 'learning'`) and to sanity-check onboarding entries. Never shown to the user as a target.

### sprint_summaries
`cgm_sprint_id uuid PK FK cgm_sprints, tir_pct, tbr_pct, tar_pct numeric(4,1), gmi_pct numeric(3,1), cv_pct numeric(4,1), mean_mmol numeric(4,1), n_valid_readings int NOT NULL, computed_at`. Computed only from `quality_ok = true` readings; requires ≥ 70% of expected readings, otherwise `status = 'insufficient'` (extra column `status text CHECK IN ('ok','insufficient')`).

### routing_rules
`id, complication_key text NOT NULL UNIQUE, specialty_key text NOT NULL, patient_text_key text NOT NULL, source text NOT NULL`. About 8 seeded rows (eye, foot, kidney, blood pressure, lipids, mental health...). Used by healthcare preparation to suggest *who* to ask, never *what the diagnosis is*.

### data_sources
`id, name text NOT NULL, kind text CHECK IN ('dataset','guideline','own'), licence text NOT NULL, url text NULL, retrieved_on date NULL, used_for text NULL, notes text NULL`. Referenced by `foods.source`, `knowledge_documents`, `interaction_rules.source`, `drug_aliases.source`, `population_priors.source` (by name). Seeded from the data plan workbook so attribution is generated, not typed by hand.

### timeline_events (VIEW, not a table)
One time-ordered stream per user across all data. Definition (logical):
```
SELECT user_id, measured_at AS occurred_at, NULL AS end_at, 'glucose_event' AS stream, ...   -- only spikes/lows/urgent, not every CGM point
UNION ALL meals (eaten_at, + carbs)  UNION ALL dose_events (scheduled_at, status)
UNION ALL workouts (started_at, duration)  UNION ALL sleep_sessions (start_at, end_at)
UNION ALL symptom_logs  UNION ALL mood_checkins  UNION ALL urgent_events
```
Columns: `user_id, occurred_at, end_at, stream timeline_stream, ref_table, ref_id, label_key, magnitude numeric NULL`. Raw CGM and heart-rate points are **not** in the view (too many); the day-trace chart draws those from `glucose_readings` and `health_samples` directly and overlays timeline events.

### event_windows
| column | type | constraints |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK |
| anchor_kind | text | NOT NULL CHECK IN ('meal','workout','dose','sleep','alcohol') |
| anchor_table / anchor_id | text / uuid | NOT NULL |
| window_start / window_end | timestamptz | NOT NULL CHECK window_end > window_start |
| outcome_metric | text | NOT NULL (e.g. 'glucose_peak_rise', 'glucose_delta_120m', 'next_fasting_glucose') |
| baseline_value / outcome_value / delta | numeric | NULL when insufficient data |
| n_points | int | NOT NULL (valid readings inside the window) |
| quality_ok | boolean | NOT NULL (false when < 70% of expected points, or CGM gap) |
| computed_at | timestamptz | NOT NULL |
| | | UNIQUE (anchor_table, anchor_id, outcome_metric) |

Rows with `quality_ok = false` are stored (so gaps are visible) but excluded from `pattern_candidates`.

### pattern_candidates
`id, user_id, pattern_key text NOT NULL (e.g. 'late_dinner_next_fasting', 'postmeal_walk_glucose', 'missed_dose_glucose'), anchor_kind text, outcome_metric text, n_pairs int NOT NULL CHECK >= 5, median_delta numeric NOT NULL, iqr_low numeric, iqr_high numeric, first_seen_on date, last_seen_on date, status text CHECK IN ('open','in_brief','dismissed'), relationship_type relationship_type NOT NULL, evidence_status evidence_status NOT NULL DEFAULT 'derived', evidence jsonb NOT NULL (list of event_windows ids), brief_id uuid FK briefs NULL, created_at, updated_at`. `relationship_type` becomes `repeated_observation` once n_pairs >= 5; never anything causal. UNIQUE (user_id, pattern_key) WHERE status = 'open'. Always rendered as *"associated with"*, never *"caused by"*, and labelled unverified in the brief.

---

## 9c. Layer and memory additions (2026-09-30)

### ingestion_events (Bronze)
`id, user_id, source_type text CHECK IN ('meal_photo','meal_text','prescription_image','medication_image','supplement_image','wearable_export','dataset_import','document'), object_key text NULL (private storage path), checksum text NOT NULL, received_at timestamptz NOT NULL, source_recorded_at timestamptz NULL, source_timezone text NULL, content_type text NULL, schema_version text NOT NULL, processing_status text CHECK IN ('received','processed','failed','deleted'), entry_source entry_source NOT NULL, created_at`. UNIQUE (user_id, checksum). Rows and objects are never modified. A user-initiated deletion sets `processing_status = 'deleted'`, removes the object, and is written to `event_log`.

### meal_analyses
`id, user_id, meal_id uuid FK meals, ingestion_event_id uuid FK ingestion_events NULL, model_id text NOT NULL, prompt_version text NOT NULL, raw_output jsonb NOT NULL (items, per-field estimates, per-field confidence), status text CHECK IN ('ok','failed','superseded'), created_at`. A re-run with a newer model or prompt inserts a new row and marks the old one `superseded`; the original object is untouched.

### devices
`id, user_id, kind device_kind NOT NULL, label text NOT NULL, source entry_source NOT NULL, last_synced_at timestamptz NULL, status text CHECK IN ('connected','disconnected'), created_at, updated_at`. The "Connected sources" row in the app. External sources only supply data; this table records that they are connected and when they last synced.

### health_goals
`id, user_id, kind goal_kind NOT NULL, target_value numeric NULL, target_low numeric NULL, target_high numeric NULL, unit text NULL, set_by text CHECK IN ('user','clinician','default'), active boolean NOT NULL DEFAULT true, starts_on date NULL, ends_on date NULL, created_at, updated_at`. Defaults (such as weekly moderate minutes) are placeholders until a clinician sets them.

### Gold views
Plain-named views, recomputed from Silver and other Gold tables. Each row carries the calculation version, evidence window, freshness timestamp, and quality status.

| View | Columns (logical) |
|---|---|
| `health_state` | user_id, as_of, glucose_state, sleep_state, activity_state, nutrition_state, adherence_state, symptom_state, quality_status |
| `trends` | user_id, metric, day, value, baseline_median, baseline_mad, z, ewma, slope, accel (from `momentum_snapshots` and `baselines`) |
| `adherence_summary` | user_id, period, scheduled, taken, unconfirmed, missed, adherence_pct, top_reasons |
| `insight_context` | user_id, as_of, open flags, active facts (top n), latest patterns, latest food responses, data completeness |

---

## 10. Relationships (summary)

```
users 1─1 patient_profiles
users 1─* conditions | allergies | family_history | consents
users 1─* prescription_scans 1─* patient_medications 1─* dose_events
patient_medications *─1 drug_reference ; drug_reference *─* drug_reference via interaction_rules
users 1─* interaction_alerts (→ patient_medications ×2, → interaction_rules)
users 1─* glucose_readings (→ cgm_sprints?, → meals?)
users 1─* meals 1─* meal_items *─1 foods ; meals 1─1 meal_responses ; users×foods → food_responses
users 1─* health_samples | workouts | mood_checkins | symptom_logs | symptom_checkins
users 1─* daily_aggregates | baselines | momentum_snapshots | clinical_flags | urgent_events
clinical_flags 1─* symptom_checkins ; clinical_flags *─1 briefs
users 1─* appointments ─1 briefs ; users 1─* doctor_questions *─1 briefs
briefs 1─* brief_shares 1─* brief_share_access ; brief_shares *─1 consents
users 1─* conversations 1─* messages ; agent_runs 1─* agent_steps ; agent_runs 1─* guardrail_events
users 1─* memory_facts (self-ref supersedes_id) | memory_episodes | nudge_stats | notifications | event_log
knowledge_documents 1─* knowledge_chunks
users 1─* lab_results | blood_pressure_readings | body_measurements | sleep_sessions | event_windows | pattern_candidates
cgm_sprints 1─1 sprint_summaries ; drug_reference 1─* drug_aliases | drug_side_effects
event_windows *─1 (meals | workouts | dose_events | sleep_sessions) via anchor_table/anchor_id ; pattern_candidates *─* event_windows via evidence
timeline_events (view) ← meals, dose_events, workouts, sleep_sessions, symptom_logs, mood_checkins, urgent_events
users 1─* ingestion_events ; meals 1─* meal_analyses ─1 ingestion_events ; meal_items *─1 meal_analyses
users 1─* devices | health_goals
```

## 11. Data consistency rules

1. **One source of truth per fact:** medication doses live only in `patient_medications`; the LLM never writes them.
2. **Nulls mean "no data"**, never zero. Aggregates, brief and charts must show "no data" distinctly from 0.
3. **Canonical units** at write time (mmol/L, mg, g, seconds). Conversion only in the API layer.
4. **Idempotent ingest:** `(user_id, source, external_id)` unique; re-imports upsert.
5. **State machines** (dose_status, scan_status, fact_status, appointment_status) enforced in services and covered by tests. Invalid transitions raise `InvalidTransition`.
6. **Immutability:** `event_log` (append-only), `briefs` once `ready`, `meal_items` nutrient snapshot.
7. **Transactions:** confirming a scan (create meds + dose events + clash check + event log) is one DB transaction; any failure rolls back all of it.
8. **Time:** recurring schedules are stored as local `time[]` + user timezone; generated `dose_events` are UTC instants.
9. **Deletion:** user deletes → soft delete in logs, cascade in derived tables recomputed nightly; account deletion cascades everything except `event_log` rows, which are pseudonymised (user_id nulled, payload stripped).
10. **One clock:** every timestamp is stored in UTC; imported datasets are shifted to the demo window once per person, so glucose, meals, doses, workouts and watch data stay aligned. Event windows are computed in UTC and displayed in SGT.
11. **Native sampling kept:** CGM interval (5 or 15 min) is stored per reading; heart rate is downsampled to 1-min on import; raw 1-min samples are kept 90 days, then rolled into `daily_aggregates`.
12. **Quality gates:** readings with `quality_ok = false` and windows with < 70% expected points never feed `sprint_summaries`, `food_responses`, `event_windows` statistics or `pattern_candidates`.
13. **Association, not cause:** `pattern_candidates` require n_pairs ≥ 5, store the median difference with IQR and the evidence ids, and are only ever worded as "associated with".
14. **Insulin is out of scope:** no table stores insulin doses. Datasets containing insulin fields are imported with those columns discarded.
15. **Provenance:** seeded reference and demo rows carry `source` (and `entry_source = 'demo_dataset'` for dataset-derived logs) so demo data is always distinguishable from user-entered data.
16. **Evidence status:** every AI-estimated or AI-proposed item is `inferred`; deterministic calculations are `derived`; direct records and user-confirmed values are `observed`; an unreviewed reference lookup is `reference_matched`. Nothing is `validated`. Confidence never changes the status.
17. **Bronze is immutable:** originals and `ingestion_events` are never modified. The only exceptions are a user-initiated deletion or retention expiry, both logged. A better analysis is a new record linked to the same original.
18. **LLM estimates are labelled:** LLM-estimated meal nutrients are stored as estimates, shown as "Estimated" until confirmed, and never presented as measured. Deterministic services read the stored values; the LLM is not asked to recompute them.
19. **No parallel tables:** one table per job. Semantic memory is `memory_facts`, associations are `pattern_candidates`, the timeline is `timeline_events`.
20. **Reference data versioning:** `interaction_rules`, `foods`, `knowledge_documents` carry source and licence; changes go through `scripts/seed_*.py`, never ad-hoc SQL.
