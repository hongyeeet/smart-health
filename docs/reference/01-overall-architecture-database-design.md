> **Superseded.** This is a starting template. The maintained versions are `memory.md`, `schema.md` and `architecture.md` in `docs/specs/`. In `memory.md`, JEV is the OpenJev typed decision layer (not a memory governor), nothing is "validated", and table names are standardised. Kept for reference only.

# Equinox: Overall Architecture & Database Design

## 1. Purpose

This document defines the overall data architecture, database design, security boundaries, provenance model, and deterministic health-processing components for Equinox, an AI companion for Type 2 diabetes self-care.

The app helps patients understand and organize their daily health data while producing an evidence-backed brief for clinicians. It does not diagnose, prescribe, or independently change medication instructions.

### Design goals

- Preserve original source data.
- Create a canonical representation of health data.
- Build structured, auditable application memory.
- Keep deterministic calculations and safety rules independent of LLM reasoning.
- Minimize exposure of personal and health data.
- Support dashboards, lifestyle timelines, food-response analysis, adherence tracking, and doctor briefs.
- Allow users to correct or delete their own records.
- Preserve provenance from every generated insight back to its source observations.

## 2. Architecture at a glance

```text
DATA SOURCES
Wearables / CGM / glucometer / user input / meals / documents / prescriptions
                              |
                              v
BRONZE — raw source layer
Immutable objects + ingestion metadata
                              |
                              v
SILVER — canonical health data
Cleaned / normalized / validated / deduplicated / versioned
                              |
             +----------------+----------------+
             |                |                |
             v                v                v
       SEMANTIC          TEMPORAL          ENTITY
        MEMORY            MEMORY           MEMORY
             \                |                /
              +--------------+---------------+
                             v
                 RELATIONSHIP MEMORY
           Associations, links, and evidence
                             |
                             v
GOLD — application memory plane
State / trends / anomalies / adherence / food response / brief context
                             |
                             v
       Dashboard, deterministic services, Memory Service, JEV

Cross-cutting security plane:
Identity • Consent • RLS • Encryption • Audit • Provenance • Retention
```

**Central principle:** Bronze and Silver are data layers. Gold is the application memory layer. JEV governs access to Gold through a controlled Memory Service and is covered separately in `02-jev-memory-governance.md`.

## 3. Bronze: immutable source layer

### Purpose

Bronze preserves exactly what was received from a source. It is not modified by AI and does not contain derived interpretations.

### Relevant sources

| Source | Examples |
| --- | --- |
| Wearables | Heart rate, HRV, steps, sleep, stress, activity |
| Glucose sources | CGM streams; fasting, pre-meal, post-meal, and random glucometer readings |
| User input | Meals, exercise, symptoms, mood, goals, onboarding information |
| Images and documents | Food photos, prescriptions, medicine packaging, supplement/TCM packaging, health documents |
| Health records | Diagnoses, allergies, doctor-set targets, lab results, preventive-care records |

### Object storage layout

```text
bronze/{user_id}/
├── food/
├── prescriptions/
├── medications/
├── documents/
└── wearable_exports/
```

Store the object key and metadata in `bronze.ingestion_events`, including:

- `event_id`
- `user_id`
- `source_type`
- `source_id`
- `object_key`
- `checksum`
- `received_at`
- `source_recorded_at`
- `source_timezone`
- `content_type`
- `schema_version`
- `data_classification`
- `contains_pii`
- `contains_health_data`
- `consent_scope`
- `processing_status`

### Bronze rules

- Immutable during normal processing.
- No AI modification.
- No derived values.
- No silent overwriting.
- Full provenance.
- Corrections create a new processing result linked to the original source.

If an image is processed incorrectly, do not replace the Bronze image. Rerun extraction using a new model or prompt version.

## 4. Silver: canonical health data

Silver is the canonical health-data layer. It standardizes the mess created by different devices, input methods, file formats, and AI extraction outputs.

```text
Apple Health / Fitbit / manual entry / CGM / image extraction
                              |
                              v
                         SILVER
                              |
                              v
                 Standardized health representation
```

### Silver domains

```text
silver/
├── glucose
├── heart_rate
├── sleep
├── activity
├── exercise
├── nutrition
├── food_consumption
├── medications
├── medication_doses
├── supplements
├── symptoms
├── mood
├── body_measurements
├── labs
└── health_goals
```

### Silver responsibilities

- Unit normalization.
- Timestamp normalization.
- Timezone handling.
- Deduplication and idempotent ingestion.
- Source reconciliation.
- Validation and quality checks.
- Categorization.
- Schema normalization.
- Confidence and provenance tracking.
- Versioning.
- Soft deletion for user-deletable logs.

Example:

```text
Bronze input: "2 eggs + toast"
        |
        v
Silver representation:
- food item: egg
- quantity: 2
- food item: toast
- quantity: 1
- meal type: breakfast
- timestamp: normalized UTC
- source: user photo
- extraction version: vision_model_v1
- confidence: per field
- confirmation status: confirmed or pending
```

Silver can contain deterministic transformations and extraction candidates. It must not silently convert a low-confidence AI interpretation into a confirmed medical fact.

## 5. Gold: application memory plane

Gold is the structured application-memory layer. It is built from Silver and retains explicit evidence links, confidence, freshness, and derivation metadata.

### 5.1 Semantic memory

**Question answered:** What does this information mean in the context of this user?

Examples:

- User prefers evening walks.
- User usually eats breakfast around 8 a.m.
- User responds well to short reminders.
- User's doctor-set HbA1c target is recorded as a particular value.
- User often misses an evening dose because they are away from home.

Candidate tables:

- `gold.health_facts`
- `gold.user_preferences`
- `gold.health_context`
- `gold.ai_memories`
- `memory_facts`

### 5.2 Temporal memory

**Question answered:** What happened, when did it happen, and what happened around it?

Example:

```text
08:00  Breakfast
08:15  Medication
08:30  Glucose 5.6 mmol/L
09:15  Walking
10:00  Heart rate 84 bpm
10:30  Glucose 6.1 mmol/L
11:00  Glucose 6.8 mmol/L
```

Candidate tables and views:

- `gold.health_timeline`
- `gold.health_events`
- `gold.daily_snapshots`
- `timeline_events` view
- `event_windows`

This powers adherence timelines, health tracking, CGM sprints, momentum analysis, symptom triggers, urgent events, and doctor briefs.

### 5.3 Entity memory

**Question answered:** What things exist in the user's health ecosystem?

Core entities:

- User.
- Medication.
- Supplement.
- TCM product.
- Food.
- Meal.
- Exercise.
- Device.
- CGM.
- Symptom.
- Diagnosis.
- Health goal.
- Doctor.
- Appointment.

Candidate tables:

- `gold.entities`
- `gold.entity_relationships`
- `patient_medications`
- `foods`
- `appointments`
- `health_goals`

Example relationships:

```text
User
├── takes       → Medication A
├── uses        → CGM
├── has         → Health Goal
├── eats        → Food A
└── performs    → Walking
```

### 5.4 Relationship memory

Use **Relationship Memory** rather than casually calling it causal memory. This prevents the system from turning an observed pattern into a causal medical claim.

Suggested relationship types:

- `observed_association`
- `temporal_association`
- `user_reported`
- `repeated_observation`
- `clinically_validated`
- `causal_evidence`

Example:

```text
Meal A
  |
  +-- temporal association --> Glucose spike

After repeated observations:

Food A
  |
  +-- repeated personal response --> Higher-than-usual glucose response
```

The distinction must remain clear:

```text
Observation  ≠  Association  ≠  Inference  ≠  Validated causal evidence
```

The app should phrase personal patterns as “associated with” or “your readings were higher after...” rather than “caused by.”

## 6. Application memory views

Gold should include materialized or precomputed views designed for fast, controlled consumption:

```text
gold.health_state
gold.trends
gold.anomalies
gold.adherence_summary
gold.food_response
gold.insight_context
gold.doctor_brief_context
```

These views are derived representations, not independent sources of truth. Each should include:

- Calculation or model version.
- Evidence window.
- Freshness timestamp.
- Source references.
- Data-quality status.
- Recalculation or invalidation behavior.

Examples:

- `health_state`: glucose, sleep, activity, nutrition, adherence, and symptom states.
- `food_response`: per-user response aggregates for foods with at least two eligible observations.
- `doctor_brief_context`: deterministic numbers and evidence references ready for brief generation.

## 7. PostgreSQL database design

The database uses PostgreSQL 16 with pgvector. Every patient-data table is scoped by `user_id`; all timestamps are stored in UTC and displayed in the user's timezone, currently defaulting to `Asia/Singapore`.

### 7.1 Core conventions

| Rule | Design |
| --- | --- |
| Primary keys | UUID with `gen_random_uuid()` |
| Ownership | Patient-data tables include `user_id` and an index on `(user_id, time_column)` |
| Time | `timestamptz`, stored UTC; displayed in `Asia/Singapore` |
| Units | Glucose mmol/L, mass g, sodium mg, energy kcal, duration seconds, distance metres |
| JSONB | Only for semi-structured payloads, evidence, and extraction results |
| Idempotency | `source + external_id` unique per user |
| Soft delete | `deleted_at` on user-deletable logs |
| Vectors | Fixed `vector(EMBED_DIM)` with HNSW cosine index |
| Naming | snake_case and plural table names |

### 7.2 Identity, profile, and consent

Core tables:

- `users`
- `patient_profiles`
- `conditions`
- `allergies`
- `family_history`
- `consents`

Separate the identity store from health data. Health tables should primarily use an internal pseudonymous `user_id`, not a name, email, phone number, NRIC, or address.

### 7.3 Medications and adherence

Core tables:

- `drug_reference`
- `drug_aliases`
- `drug_side_effects`
- `prescription_scans`
- `patient_medications`
- `medication_ingredients`
- `dose_events`
- `refill_forecasts`
- `interaction_rules`
- `interaction_alerts`

Important rules:

- No medication becomes active until the user confirms or edits extracted fields.
- Every extracted field has a confidence score.
- Unrecognized items are marked “not checked” and can be entered manually.
- Dose schedules are generated from confirmed medication records.
- Interaction checks are deterministic reference lookups, not LLM guesses.
- The app never says to stop, double, substitute, or independently change a medication.

### 7.4 Measurements and logs

Core tables:

- `glucose_readings`
- `cgm_sprints`
- `sprint_summaries`
- `health_samples`
- `foods`
- `meals`
- `meal_items`
- `meal_responses`
- `food_responses`
- `workouts`
- `mood_checkins`
- `symptom_logs`
- `symptom_checkins`
- `lab_results`
- `blood_pressure_readings`
- `body_measurements`
- `sleep_sessions`

Canonical glucose is mmol/L. Re-synchronization must not duplicate records. Quality flags must exclude unreliable readings from analytics.

### 7.5 Derived analytics and safety

Core tables:

- `daily_aggregates`
- `baselines`
- `momentum_snapshots`
- `clinical_flags`
- `urgent_events`
- `event_windows`
- `pattern_candidates`

The Momentum Engine uses deterministic calculations such as:

- Rolling 28-day median and MAD for a personal baseline.
- Seven-day EWMA slope.
- Change in momentum between the current and previous period.
- Persistent drift or acceleration thresholds.

Momentum patterns go to the brief as “patterns for clinician review.” They do not diagnose the patient.

Event-window findings require quality-checked data and at least five matched pairs before being shown as a repeated pattern. Food-response output has its own minimum of at least two eligible observations and must show `n` and a range.

### 7.6 Preventive care, appointments, and questions

Core tables:

- `preventive_items`
- `patient_preventive_status`
- `appointments`
- `doctor_questions`

The app may suggest appointments or add an event to a calendar only after explicit user confirmation.

### 7.7 Doctor brief

Core tables:

- `briefs`
- `brief_shares`
- `brief_share_access`

Brief sections include:

1. Profile snapshot.
2. Top three items to discuss.
3. Medication and adherence timeline.
4. Glucose trends and CGM sprint data.
5. Nutrition and personal food-response patterns.
6. Exercise.
7. Sleep.
8. Mood and stress.
9. Symptoms.
10. Unverified patterns for clinician review.
11. Preventive-care status.
12. Patient questions.
13. Data completeness.
14. Best, worst, and typical day traces.

All numerical values are computed deterministically. The LLM may write narrative summaries only when every sentence can be linked to an evidence ID. Ready briefs are immutable; regeneration creates a new version.

## 8. Security, privacy, and data classification

### 8.1 Classification

| Classification | Examples | Handling |
| --- | --- | --- |
| Public | App configuration | Standard integrity controls |
| Internal | System metadata | Authenticated service access |
| Personal | Preferences, device information | User-scoped access |
| Sensitive health | Glucose, medications, symptoms | Strict user-scoped access and audit |
| Highly sensitive | Diagnoses, prescriptions, medical documents | Strongest access controls |

Tag records at ingestion:

```json
{
  "data_classification": "health_sensitive",
  "contains_pii": false,
  "contains_health_data": true
}
```

A prescription may contain both PII and highly sensitive health information:

```json
{
  "data_classification": "highly_sensitive",
  "contains_pii": true,
  "contains_health_data": true
}
```

### 8.2 Security controls

- Encrypt data in transit and at rest.
- Keep object storage private.
- Use short-lived signed URLs for authorized document access.
- Enforce Supabase Row Level Security.
- Keep service-role credentials on trusted servers only.
- Use managed secrets and least-privilege service accounts.
- Audit access, policy decisions, and agent runs.
- Enforce retention, deletion, backup, and correction workflows.
- Keep unnecessary PII out of embeddings, prompts, logs, and memory representations.
- Never embed raw medical documents without redaction and a clear need.

### 8.3 RLS and authorized reads

```text
Authenticated user
        |
        v
Authorization and consent check
        |
        v
user_id-scoped Memory Service request
        |
        v
Supabase RLS and database policies
        |
        v
Minimal authorized response
```

The system must never allow unrestricted queries such as `SELECT * FROM memories` without a user scope.

## 9. Deterministic clinical safety boundary

```text
Validated health data
        |
        +--> Medication interaction reference + rules
        |       -> confirmed hit / not checked
        |
        +--> Urgent threshold and symptom rule engine
                -> approved escalation path

JEV and LLM may organize or explain results.
They cannot override the safety outputs.
```

### Medication safety

F5 uses normalized medication and supplement entities against a reviewed interaction reference. Confirmed hits use an approved message such as:

> Possible interaction between X and Y. Please check with your pharmacist or doctor before continuing.

Items not found in the reference table are “not checked,” never “safe.”

### Urgent escalation

F10 is rule-based and immediate. Examples include configured low-glucose thresholds, repeated high readings, chest pain, confusion, or fainting. The alert must not wait for a doctor brief. Thresholds and response language require clinical-advisor validation before production use.

## 10. Feature-to-architecture mapping

| Feature | Bronze | Silver | Gold | JEV/application role | Deterministic control |
| --- | --- | --- | --- | --- | --- |
| F1 Onboarding | Form/chat | Profile | Semantic + Entity | Retrieve authorized context | Eligibility and consent |
| F2 Medication | Image/document | Medication record | Entity + Temporal | Propose context/update | Extraction confidence and confirmation |
| F3 Explainer | Reference input | Normalized drug | Semantic | Retrieve cited context | Prescription dose restriction |
| F4 Adherence | Dose logs | Dose events | Temporal | Assemble context | Schedule engine |
| F5 Clash | Interaction reference | Normalized items | Relationship | Present result | Interaction lookup |
| F6 Tracking | Raw streams | Canonical metrics | Temporal | Retrieve timeline | Validation and aggregation |
| F7 CGM | CGM + meals | Aligned data | Relationship | Retrieve food-response evidence | Windowing and sample thresholds |
| F8 Momentum | Measurements | Canonical metrics | Trends | Surface relevant trends | Baseline and slope calculations |
| F9 Symptoms | Check-ins | Symptom records | Temporal + Semantic | Select question | Anti-nag and safety limits |
| F10 Escalation | Readings/symptoms | Validated data | Urgent event | No override | Rule engine |
| F11 Coach | Logs/preferences | Canonical behavior | Semantic preferences | Personalize context | Approved content corpus |
| F12 Brief | All inputs | All canonical data | All memory dimensions | Assemble evidence | Templates, validation, provenance |
| F16 Transparent memory | User interaction | Confirmed edits | User model facts | Retrieve and govern facts | User confirmation and deletion |
| F18 Timeline | All streams | Time-aligned records | Event windows and traces | Select relevant context | Quality gates and association wording |

## 11. End-to-end example: food to CGM insight

1. The user uploads a food photo.
2. Bronze stores the original image and ingestion metadata.
3. A vision model identifies candidate foods.
4. Silver stores meal items, estimated nutrients, extraction confidence, and confirmation state.
5. CGM readings are normalized into Silver.
6. A deterministic service aligns the meal with an explicitly defined glucose window.
7. Temporal Gold stores the event sequence.
8. Relationship Gold stores a labeled association with supporting observations.
9. If there are fewer than two eligible observations, no personalized food-response statement is shown.
10. If there are at least two, the system can show the observation count and range.
11. JEV retrieves the relevant evidence through the Memory Service.
12. The LLM produces cautious, factual wording such as:

> Last time you had this, your glucose rose more than after most of your meals.

The system must not state that the food caused the glucose response.

## 12. Data consistency rules

1. One source of truth per fact.
2. Null means no data; it never means zero.
3. Store canonical units at write time.
4. Make ingestion idempotent with `(user_id, source, external_id)` uniqueness.
5. Enforce state machines for scans, doses, memories, appointments, and briefs.
6. Keep the event log append-only.
7. Make ready briefs immutable.
8. Use transactions for medication confirmation, dose generation, clash checks, and audit logging.
9. Store recurring schedules in local time and generated events as UTC instants.
10. Recompute dependent derived tables after correction or deletion.
11. Exclude low-quality readings and incomplete windows from analytics.
12. Use “associated with,” never “caused by,” for unvalidated personal patterns.
13. Keep insulin out of scope for this project.
14. Label demo-dataset records so they cannot be confused with real user-entered records.
15. Version reference data, interaction rules, food records, knowledge documents, and processing models.

## 13. Implementation boundary

This document covers the database and overall architecture. The JEV orchestration, retrieval, memory lifecycle, and governance design are defined in:

> `02-jev-memory-governance.md`
