# Smart Health backlog

The single live task list for the team. **Epics E2-E19 map one-to-one to features F1-F18** (E2 = F1 ... E19 = F18). E0 is the demo mockup and foundation, E1 is data readiness, E20 is optional testing and validation, E21 is the submission package, E22 holds the integration checkpoints that tie the parts together.

**Priority:** P0 = in the demo script, P1 = should have, P2 = stretch. **Size:** S about half a day, M about a day, L about two days. **NEEDS OK** = relies on something outside the cited data sources, decide before starting.

## Team and workload split

Team: _add the three names here_

Set `Owner:` on each task (or on a whole epic) before the first push.

## Session handover

The full process is in [../handover/HANDOVER.md](../handover/HANDOVER.md). In short, at the end of every session:

1. Tick each finished subtask: `- [ ]` becomes `- [x]`.
2. Set `Status:` to `backlog`, `in progress`, `blocked` or `done`. Tick the task's own box only when every subtask is ticked.
3. Put your name in `Owner:` if the task is unassigned and you started it, and add a one-line `Note:` for what is left or what blocks you.
4. Write the session log in `docs/handover/sessions/` and commit it with your pull request into `dev`.
5. Found missing work? Add a task at the end of its epic with the next free ID and its subtasks. Only edit your own tasks and keep one field per line so merges stay clean.

## Epics

| Epic | Name | Feature | Tasks |
|---|---|---|---|
| E0 | Demo mockup and foundation |  | 12 |
| E1 | Data readiness |  | 15 |
| E2 | Onboarding | F1 | 4 |
| E3 | Prescription and medication capture | F2 | 6 |
| E4 | Medication explainer | F3 | 3 |
| E5 | Adherence engine | F4 | 5 |
| E6 | Clash checker | F5 | 4 |
| E7 | Health tracking and logging | F6 | 5 |
| E8 | CGM sprint and personal food response | F7 | 5 |
| E9 | Momentum engine | F8 | 4 |
| E10 | Targeted symptom check-ins | F9 | 3 |
| E11 | Urgent escalation | F10 | 3 |
| E12 | Lifestyle coach and adaptive nudges | F11 | 4 |
| E13 | Doctor brief | F12 | 6 |
| E14 | Preventive care and scheduler | F13 | 3 |
| E15 | Healthcare preparation | F14 | 2 |
| E16 | Companion chat and agent harness | F15 | 6 |
| E17 | Transparent memory and learning | F16 | 5 |
| E18 | Multilingual and TTS | F17 | 3 |
| E19 | Lifestyle timeline and day traces | F18 | 4 |
| E20 | Testing and validation (optional) |  | 5 |
| E21 | Submission package |  | 7 |
| E22 | Integration checkpoints |  | 4 |

## E0 Demo mockup and foundation

_Mockup first. Wireframes cover the app only; watch, CGM and camera are just data sources feeding it._

- [ ] **E0-1 Scope key pages and end-to-end flow** · P0 · S · Phase 0
  - Owner: —
  - Status: backlog
  - Spec: flow.md 1-2
  - Note:
  - [ ] Working session with all 3
  - [ ] Output: list of at most 15 key pages (purpose, entry/exit, data shown) and one flow diagram
  - [ ] Every feature F1-F18 appears on at least one page
  - [ ] All 3 sign off
- [ ] **E0-2 Design tokens and component kit** · P0 · M · Phase 0
  - Owner: —
  - Status: backlog
  - Spec: design.md 2-5
  - Note:
  - [ ] Tokens from design.md in code
  - [ ] The 12 primitives (Button, Card, DoseCard, ReasonSheet, ReadingInput, ConfidenceChip, SourceTag, TrendCard, MemoryFactRow, UrgentScreen, ChatBubble, Banner) render in light and dark, at 100% and 200% font scale, contrast at least 4.5:1
- [ ] **E0-3 Clickable prototype: core flow** · P0 · L · Phase 0
  - Owner: —
  - Status: backlog
  - Depends on: E0-1, E0-2 · Spec: flow.md 5
  - Note:
  - [ ] Phone-frame web prototype with fake data and no backend
  - [ ] Screens: onboarding, scan and review, Today, Log, Meds, Insights with day view, Brief, Memory, Urgent, Chat
  - [ ] Every step of the demo script is clickable start to finish with no dead ends
- [ ] **E0-4 Prototype: data-source simulator panel** · P1 · M · Phase 0
  - Owner: —
  - Status: backlog
  - Depends on: E0-3 · Spec: prd F6, F7
  - Note:
  - [ ] Side panel with buttons that push a watch sync, a CGM reading, a meal and a medication photo into the prototype
  - [ ] App shows the imported state (for example 'Connected: watch, CGM')
  - [ ] Makes clear the outside sources only supply data
- [ ] **E0-5 Prototype review and freeze** · P0 · S · Phase 0
  - Owner: —
  - Status: backlog
  - Depends on: E0-3
  - Note:
  - [ ] 30-minute walkthrough by all 3, change list applied, prototype v1 frozen and hosted at a public URL, open questions logged in the repo
- [ ] **E0-6 App skeleton and Supabase connection** · P0 · M · Phase 0
  - Owner: —
  - Status: backlog
  - Depends on: E0-1 · Spec: architecture
  - Note:
  - [ ] Mobile-first web app and API start locally with one command per machine
  - [ ] Supabase project renamed to smart-health; connection details shared privately and kept in .env, never committed
  - [ ] Row-level security is on with no policies for every table, and only the backend connects
  - [ ] One page reads a database row through the API
  - [ ] .env.example complete and setup takes at most 5 commands
- [ ] **E0-7 Demo session (replaces sign-in)** · P1 · S · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E0-6 · Spec: rules.md 8
  - Note:
  - [ ] 'Start as demo patient' creates a session
  - [ ] Every API query is scoped by the session's user id
  - [ ] No password screens
- [ ] **E0-8 Event log writer** · P0 · S · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E0-6, E1-3 · Spec: flow.md 0; schema 9
  - Note:
  - [ ] Client logEvent() and server writer append to event_log
  - [ ] Client events are deduplicated by client_event_id
  - [ ] A test proves the per-user hash chain detects a tampered row
- [ ] **E0-9 LLM and AI provider decision and gateway** · P0 · M · Phase 0
  - Owner: —
  - Status: backlog
  - Depends on: E0-6 · Spec: architecture 2
  - Note:
  - [ ] Provider decision recorded in the repo
  - [ ] Gateway wraps chat, vision and embeddings with timeout, retry and logging
  - [ ] A smoke test gets a response from each
  - [ ] Keys live in env only
- [ ] **E0-10 Build-proof habit** · P1 · S · Phase 0
  - Owner: —
  - Status: backlog
  - Spec: prd 11
  - Note:
  - [ ] Docs/proof/ folder
  - [ ] At least 3 screenshots of CodeBuddy/WorkBuddy work saved by CP1, then one per milestone
- [ ] **E0-11 Freeze shared contracts** · P0 · S · Phase 0
  - Owner: —
  - Status: backlog
  - Depends on: E1-3, E0-2, E0-6 · Spec: architecture.md
  - Note:
  - [ ] Schema: schema.md and migrations frozen; changes need all 3 owners and a schema.md update
  - [ ] Demo data pack: seed_demo.py output frozen, same seed gives same data
  - [ ] API contract: OpenAPI generated from the backend plus a mock server so the UI can be built first
  - [ ] Event names: flow.md section 4 is the only catalogue, add there before using a new event
  - [ ] Design tokens: no hard-coded colours or sizes
  - [ ] Guardrail templates: every patient-facing AI output goes through the approved templates

- [ ] **E0-12 Decide and wire the JEV decision layer** · P0 · M · Phase 0
  - Owner: —
  - Status: backlog
  - Depends on: E0-9 · Spec: memory 5
  - Note:
  - [ ] Choose hosted OpenJev, small CPU models, self-hosted, or the Hunyuan fallback only, and record the choice with the data-handling note
  - [ ] decide(state, questions) in decision/ keeps the OpenJev request and response shape (noul, choice, score) and returns probability and confidence
  - [ ] Smoke test returns an answer for one yes/no and one choice question; an image question too if the chosen option supports images
  - [ ] Switching JEV off routes every call to the fallback, and the conservative path applies when confidence is unknown
## E1 Data readiness

_Data ready for analysis and model training, stored in the schema, with scaffolding fields for all user data._

- [ ] **E1-1 Data download scripts** · P0 · M · Phase 0
  - Owner: —
  - Status: backlog
  - Spec: data plan
  - Note:
  - [ ] One script fetches the cited subsets into gitignored data/raw: CGMacros, BIG IDEAs (3-5 participants: Dexcom, HR, EDA, TEMP, Food_Log, Demographics), NHANES files, Fitbit, 250k Medicines, Open Food Facts (SG/MY subset), Doctor Specialty, GlucoBench
  - [ ] Sizes and checksums logged. data/README lists each licence
- [ ] **E1-2 Profiling report per dataset** · P0 · M · Phase 0
  - Owner: —
  - Status: backlog
  - Depends on: E1-1 · Spec: data plan
  - Note:
  - [ ] One short report per dataset (participants, rows, date span, missing values, units, sampling interval)
  - [ ] Answers: how many CGMacros T2D participants have complete CGM and meals; whether 250k Medicines really has an interactions column; BIG IDEAs HbA1c range
- [ ] **E1-3 Canonical schema and migrations** · P0 · L · Phase 0
  - Owner: —
  - Status: backlog
  - Spec: schema.md
  - Note:
  - [ ] Migrations create every table in schema.md sections 2-9b
  - [ ] They apply cleanly to an empty database and roll back
  - [ ] Constraints and enums present
  - [ ] Seeding one empty user succeeds. schema.md updated if anything changed
  - [ ] Row-level security is enabled on every table with no policies
- [ ] **E1-4 User-data scaffolding and data dictionary** · P0 · M · Phase 0
  - Owner: —
  - Status: backlog
  - Depends on: E1-3 · Spec: schema.md
  - Note:
  - [ ] Every field the app collects has a table, column, unit and source flag (manual, imported, simulated). docs/data_dictionary.md lists them
  - [ ] Covers profile, conditions, allergies, medications and ingredients, doses, glucose, meals, workouts, sleep, wearable samples, symptoms, mood, BP, labs, appointments, questions, memory
- [ ] **E1-5 CGMacros importer** · P0 · L · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-2, E1-3 · Spec: data plan; schema
  - Note:
  - [ ] Loads the chosen T2D participant(s): CGM to glucose_readings (mmol/L, quality flag, native interval), meals and macros, Fitbit HR/steps to health_samples, bio.csv to profile and lab_results
  - [ ] Dates shifted per person, stored in UTC
  - [ ] Row counts equal the source. 100 random glucose rows verified against the raw file
- [ ] **E1-6 BIG IDEAs importer** · P1 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-3 · Spec: data plan
  - Note:
  - [ ] Dexcom, HR, EDA, TEMP, food log and demographics loaded for the chosen participants
  - [ ] HR downsampled to 1 minute
  - [ ] Rows marked entry_source demo_dataset
  - [ ] Test compares counts to source
- [ ] **E1-7 Fitbit, NHANES and GlucoBench importers** · P1 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-3 · Spec: data plan
  - Note:
  - [ ] Fitbit to samples and sleep
  - [ ] NHANES to population_priors (percentiles by age, sex, diabetes) plus a persona-sampling table
  - [ ] GlucoBench to a fixture table with insulin columns discarded
  - [ ] Each has a test
- [ ] **E1-8 Reference tables** · P0 · L · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-2, E1-3 · Spec: schema 9b
  - Note:
  - [ ] Drug_reference, drug_aliases and drug_side_effects from 250k Medicines (diabetes, BP and lipid drugs first, at least 100 generics). foods from Open Food Facts (SG/MY) and NHANES dietary files with sodium and sugar. routing_rules from Doctor Specialty. data_sources filled
  - [ ] Searching 'metformin' returns its aliases
  - [ ] At least 90% of seeded foods have sodium or are flagged unknown
- [ ] **E1-9 Demo persona and 60-day simulator** · P0 · L · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-5, E1-8 · Spec: prd A8
  - Note:
  - [ ] Persona is one CGMacros T2D participant. seed_demo.py builds 60 days: glucometer readings, doses with a weekend/evening miss pattern and one 4-day streak, mood/sleep/stress, BP, workouts, symptoms, and a rising fasting-glucose drift in the last 3 weeks
  - [ ] Every simulated row is flagged and a disclosure list is generated
  - [ ] Same seed gives identical data
- [ ] **E1-10 Analysis-ready feature tables** · P1 · L · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-5, E1-6
  - Note:
  - [ ] Meal_features (macros, context, response iAUC and peak rise) and a daily feature table
  - [ ] Train and test split by participant with no leakage
  - [ ] Documented
- [ ] **E1-11 Baseline model: meal to glucose response** · P1 · L · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E1-10
  - Note:
  - [ ] Model card (data, split, metric)
  - [ ] Beats predicting the mean on held-out participants
  - [ ] Artefact loadable by the API
  - [ ] Labelled as a population model
- [ ] **E1-12 Storage and replay** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-5 · Spec: architecture 4.3
  - Note:
  - [ ] Replay.py streams the demo data as if live (1x and accelerated)
  - [ ] The import endpoint is idempotent by source plus external_id: running twice creates no duplicates

- [ ] **E1-13 Bronze ingestion log and storage layout** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-3 · Spec: schema 9c; architecture layers
  - Note:
  - [ ] ingestion_events table with checksum, source type, timestamps and processing status; unique per user and checksum
  - [ ] Storage layout by type (meals, medications, documents, exports) in a private Supabase Storage bucket; originals are never overwritten
  - [ ] Every photo, image and import writes an ingestion_events row
  - [ ] A user-initiated deletion removes the object, marks the row deleted and is logged
- [ ] **E1-14 Gold views and layer map** · P1 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-3, E9-1 · Spec: schema 0b, 9c
  - Note:
  - [ ] Views health_state, trends, adherence_summary and insight_context created with calculation version, evidence window, freshness and quality status
  - [ ] The layer map in schema.md matches the migrated tables exactly
  - [ ] No table or view uses the names gold., silver. or bronze. as a prefix
- [ ] **E1-15 Devices and health goals tables with seed** · P0 · S · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-3 · Spec: schema 9c
  - Note:
  - [ ] devices rows for the connected watch, sensor and camera with last-synced times
  - [ ] health_goals rows for the weekly moderate minutes and strength sessions, marked as defaults until a clinician sets them
  - [ ] Both tables are covered by the demo seed
## E2 Onboarding (F1)

- [ ] **E2-1 Form onboarding screens** · P0 · L · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E0-2, E1-3 · Spec: prd F1
  - Note:
  - [ ] Steps: about you, diagnosis and HbA1c, conditions, allergies, family history, medications entry point, connected sources, reminder times
  - [ ] Finishes in 5 minutes or less on a phone-size screen
  - [ ] Each step saves
  - [ ] Leaving and returning resumes
  - [ ] Writes profile, conditions and allergies
- [ ] **E2-2 Eligibility and consent** · P0 · S · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E2-1 · Spec: prd F1
  - Note:
  - [ ] Type 1, pregnancy and under-18 are blocked with a clear message
  - [ ] Consent rows stored
  - [ ] The user cannot continue without data-processing consent
- [ ] **E2-3 Chat onboarding** · P1 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E16-1, E0-9 · Spec: prd F1
  - Note:
  - [ ] Same fields collected conversationally, with a live 'captured so far' card and edit before saving
  - [ ] A scripted transcript produces the same records as the form
- [ ] **E2-4 Summary review and demo fast-path** · P0 · S · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E2-1, E0-7 · Spec: flow J1
  - Note:
  - [ ] Editable summary screen
  - [ ] 'Start as demo patient' skips onboarding and loads the seeded persona

## E3 Prescription and medication capture (F2)

- [ ] **E3-1 Scan UI: capture and review** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E0-2 · Spec: prd F2
  - Note:
  - [ ] Camera/upload screen with framing tips
  - [ ] Review screen shows each field with a confidence chip
  - [ ] Fields below 0.85 must be tapped to confirm
  - [ ] Nothing saves until confirmed
- [ ] **E3-2 Extraction service** · P0 · L · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E0-9 · Spec: prd F2; med capture pipeline
  - Note:
  - [ ] Vision model returns strict JSON with confidence and source text per field
  - [ ] Missing means null
  - [ ] Patient name and NRIC are dropped before storage
  - [ ] Handles prescription label, box, supplement, TCM and OTC
  - [ ] Invalid JSON retried once then fails safe
- [ ] **E3-3 Name matching to drug database** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-8 · Spec: prd F2
  - Note:
  - [ ] Exact then fuzzy match to drug_aliases
  - [ ] Test set of 30 names passes
  - [ ] No match shows 'I'm not able to identify this medication, please check with your pharmacist' and offers manual entry
  - [ ] The model never chooses the database id
- [ ] **E3-4 Directions parser** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Spec: prd F2
  - Note:
  - [ ] Deterministic parser for at least 30 phrases ('twice daily after meals', 'at night', ...) gives times per day, timing and with-food
  - [ ] Unknown phrases turn into a question to the user
  - [ ] Verbatim text always stored
- [ ] **E3-5 Confirm and save transaction** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E3-2, E3-3, E3-4, E1-3 · Spec: schema 3
  - Note:
  - [ ] One transaction saves the medication, ingredients, dose schedule, clash check and event log
  - [ ] A forced failure rolls back everything
- [ ] **E3-6 Extraction test set and accuracy report** · P1 · M · Phase 2 · NEEDS OK
  - Owner: —
  - Status: backlog
  - Depends on: E3-2 · Spec: data plan
  - Note:
  - [ ] No photo set exists in the cited data, so this needs photos the team takes. 30 or more photos across item types, ground truth per photo, per-field accuracy reported by item type, target at least 90% on name and strength for printed labels, and low confidence flagged for the rest

## E4 Medication explainer (F3)

- [ ] **E4-1 Drug knowledge index** · P0 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E1-8 · Spec: prd F3
  - Note:
  - [ ] 250k Medicines text chunked and embedded
  - [ ] Retrieval returns the correct drug for 20 test names
- [ ] **E4-2 Explainer generation with guard** · P0 · L · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E4-1, E0-9, E16-2 · Spec: prd F3
  - Note:
  - [ ] Plain-language sections (what it is for, how you take it from your own label, common side effects, when to tell your doctor)
  - [ ] Every sentence cites its source
  - [ ] Dose text comes only from the confirmed medication
  - [ ] 'Can I skip it?' triggers the refusal template
- [ ] **E4-3 Explainer screen, language and audio** · P0 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E4-2, E18-1 · Spec: flow J3
  - Note:
  - [ ] Medication detail screen with sources shown, four-language switch and a listen button

## E5 Adherence engine (F4)

- [ ] **E5-1 Dose schedule generator** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-3 · Spec: schema 3
  - Note:
  - [ ] Seven days of dose events generated per medication in the user's timezone
  - [ ] Re-running creates no duplicates
- [ ] **E5-2 Today screen and dose card** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E0-2, E5-1 · Spec: flow J4
  - Note:
  - [ ] Today lists due doses
  - [ ] Tapping Taken updates status and logs the event
  - [ ] Card shows scheduled, taken and unconfirmed states
- [ ] **E5-3 Reminder engine** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E5-1, E0-8 · Spec: prd F4
  - Note:
  - [ ] Reminder at the scheduled time, re-nudge after 60 minutes, unconfirmed when the window closes
  - [ ] Jobs are idempotent
  - [ ] Demo mode can trigger each step on demand
  - [ ] In-app notifications (no push needed)
- [ ] **E5-4 Miss-reason flow and state machine** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E5-3 · Spec: prd F4
  - Note:
  - [ ] Next open shows one-tap reasons (forgot, side effects, ran out, felt fine, cost, other)
  - [ ] Only valid transitions allowed, invalid ones raise an error, covered by tests
  - [ ] Side effects offers to add a symptom and a doctor question
- [ ] **E5-5 Meal-triggered prompt and refill forecast** · P1 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E5-1, E7-2 · Spec: prd F4
  - Note:
  - [ ] Logging a meal prompts the with-food medication
  - [ ] Refill date predicted from quantity and dose rate, with a reminder 7 days ahead

## E6 Clash checker (F5)

- [ ] **E6-1 Interaction data check and load** · P0 · S · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-8 · Spec: prd A4
  - Note:
  - [ ] Report confirms whether 250k Medicines contains interactions, and how many usable pairs
  - [ ] If it does not, raise it as a decision and stop. interaction_rules loaded with source recorded
- [ ] **E6-2 Clash service** · P0 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E6-1, E3-5 · Spec: prd F5
  - Note:
  - [ ] Deterministic lookup per ingredient
  - [ ] A known pair produces a hit
  - [ ] An unmatched pair or any supplement/TCM item gives 'not checked', never 'safe'
  - [ ] Runs whenever a medication is added or changed
- [ ] **E6-3 Clash screen and question hand-off** · P0 · S · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E6-2, E15-1 · Spec: prd F5
  - Note:
  - [ ] Fixed wording: 'Possible interaction between X and Y
  - [ ] Please check with your pharmacist or doctor before continuing.' Never says stop
  - [ ] Offers to add to doctor questions
  - [ ] Hits appear in the brief
- [ ] **E6-4 Seed a demo clash** · P0 · S · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E6-2 · Spec: flow 5
  - Note:
  - [ ] The demo persona has one pair that hits and one supplement that shows 'not checked'

## E7 Health tracking and logging (F6)

- [ ] **E7-1 Glucose entry with threshold hook** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-3, E11-1 · Spec: prd F6
  - Note:
  - [ ] Entry in 3 taps or fewer, with context (fasting, pre, post, bedtime, random), stored in mmol/L
  - [ ] Every reading is checked by the threshold service
- [ ] **E7-2 Meal logging with LLM macro estimation** · P0 · L · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-8, E0-9, E1-13 · Spec: prd F6; memory 9
  - Note:
  - [ ] Photo or text description goes to the LLM, which returns the items and estimated kcal, carbs, protein, fat, fibre, sugar and sodium with a confidence per field
  - [ ] Estimates carry an 'Estimated' badge and can be edited or confirmed; confirmed values are stored as user-confirmed
  - [ ] Original photo and raw analysis are stored and never overwritten; re-running with a new prompt adds a new analysis
  - [ ] High-salt and high-sugar flags are computed in code from the stored values
  - [ ] Open Food Facts and NHANES values are used only as a sanity check that adds a 'check this' flag
  - [ ] A food the LLM cannot identify asks the user to type it in
- [ ] **E7-3 Workout, symptom and mood check-in logs** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-3 · Spec: prd F6
  - Note:
  - [ ] Three quick forms, each at most 15 seconds
  - [ ] Evening check-in captures mood, stress, sleep quality and energy on 1 to 5
- [ ] **E7-4 Connect sources and import** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-12 · Spec: prd F6
  - Note:
  - [ ] 'Connect sources' screen shows watch and CGM as connected and feeds data from the replay
  - [ ] Import is idempotent and shows last-synced time
- [ ] **E7-5 Edit, delete and completeness** · P1 · S · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E7-1 · Spec: prd F6
  - Note:
  - [ ] Users can edit or delete their own logs, edits are recorded in the event log
  - [ ] Data completeness percent per stream is calculated for the brief

## E8 CGM sprint and personal food response (F7)

- [ ] **E8-1 Sprint start, end and replay** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-12 · Spec: prd F7
  - Note:
  - [ ] Start and end a 14-day CGM sprint
  - [ ] Replay of the chosen CGMacros participant fills it
  - [ ] One open sprint per user
- [ ] **E8-2 Meal response calculator** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E8-1 · Spec: architecture 6
  - Note:
  - [ ] For each meal, baseline glucose, peak rise and 2-hour incremental AUC
  - [ ] Matches a pandas reference on 20 meals
  - [ ] Windows with too little data are excluded
- [ ] **E8-3 Food response leaderboard and note** · P0 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E8-2 · Spec: prd F7
  - Note:
  - [ ] Responses per food shown only when n is 2 or more, with n and range
  - [ ] Logging a known high-response food shows the factual note
  - [ ] Leaderboard in Insights and the brief
- [ ] **E8-4 Sprint summary metrics** · P1 · S · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E8-1 · Spec: schema 9b
  - Note:
  - [ ] Time in range, below range, above range, GMI and CV match a pandas reference
- [ ] **E8-5 Compared to typical (population model)** · P2 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E1-11
  - Note:
  - [ ] Screen shows the model's expected response next to the actual one, labelled as a population estimate

## E9 Momentum engine (F8)

_Learns each person's own baseline across all data streams._

- [ ] **E9-1 Daily aggregates job** · P0 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E1-9 · Spec: schema 5
  - Note:
  - [ ] Nightly rollup of glucose, meals, activity, sleep, mood and adherence per day
  - [ ] Missing data stays empty, never zero
- [ ] **E9-2 Baseline, momentum and flags** · P0 · L · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E9-1 · Spec: architecture 6
  - Note:
  - [ ] 28-day median and MAD baseline, 7-day slope and change of slope
  - [ ] Unit tests on synthetic series: a known drift is flagged, plain noise is not, fewer than 10 days shows 'learning'
  - [ ] Each flag stores the numbers behind it
- [ ] **E9-3 Insights screen** · P0 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E9-2, E0-2 · Spec: design 6-7
  - Note:
  - [ ] Trend cards with baseline band and one plain-language line each
  - [ ] Period switch 7, 30, 90 days
- [ ] **E9-4 Flag hand-offs** · P0 · S · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E9-2 · Spec: prd F8
  - Note:
  - [ ] A flag creates a neutral patient note and an entry for the brief

## E10 Targeted symptom check-ins (F9)

- [ ] **E10-1 Question bank and planner** · P0 · M · Phase 2 · NEEDS OK
  - Owner: —
  - Status: backlog
  - Depends on: E9-2 · Spec: prd F9
  - Note:
  - [ ] Question wording is team-written and needs clinician review
  - [ ] Planner picks at most 1 check-in per day and 3 per week, and learns which the user answers
- [ ] **E10-2 Check-in UI and logging** · P0 · S · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E10-1 · Spec: flow J7
  - Note:
  - [ ] One neutral question card
  - [ ] Answer or skip is stored as a symptom log
- [ ] **E10-3 Link to flag and brief** · P1 · S · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E10-2 · Spec: prd F9
  - Note:
  - [ ] Answers show in the brief symptom section, linked to the pattern that triggered them

## E11 Urgent escalation (F10)

_Rule-based, no LLM in the path._

- [ ] **E11-1 Threshold service and config** · P0 · M · Phase 1 · NEEDS OK
  - Owner: —
  - Status: backlog
  - Spec: prd F10
  - Note:
  - [ ] Thresholds are team-written rules
  - [ ] Boundary tests at 2.9, 3.0, 3.8 and 3.9 mmol/L, repeated highs, and the symptom rule all pass
  - [ ] Config file marked 'clinical validation pending'
- [ ] **E11-2 Urgent screen and recheck** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E11-1, E0-2 · Spec: flow J8
  - Note:
  - [ ] Full-screen instruction by tier with call buttons and hypo self-help steps
  - [ ] No LLM in the path
  - [ ] Works with the network off
  - [ ] Recheck timer prompts a new reading
  - [ ] Events logged
- [ ] **E11-3 Demo trigger and replay of a low reading** · P0 · S · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E11-1, E1-12 · Spec: flow 5
  - Note:
  - [ ] Replaying a 2.8 mmol/L reading opens the urgent screen within 2 seconds

## E12 Lifestyle coach and adaptive nudges (F11)

_Adapts to what this user responds to._

- [ ] **E12-1 Nudge templates and triggers** · P0 · M · Phase 2 · NEEDS OK
  - Owner: —
  - Status: backlog
  - Depends on: E9-2 · Spec: prd F11
  - Note:
  - [ ] No guideline corpus is in the cited data, so nudges are reviewed team-written templates filled with the user's own data
  - [ ] Each nudge names the data it is based on
- [ ] **E12-2 Adaptive nudge policy** · P0 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E12-1 · Spec: architecture 5.4
  - Note:
  - [ ] Chooses nudge type and time slot by observed act rate with 15% exploration, 3 per day cap, quiet hours
  - [ ] A simulation over the demo persona shifts toward the slots and types the user acts on
- [ ] **E12-3 Salt and sugar flags with own-data swaps** · P1 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E7-2, E8-3 · Spec: prd F11
  - Note:
  - [ ] High-salt or high-sugar meals show a card suggesting a food that gave this user a gentler response
- [ ] **E12-4 Nudge cards UI** · P0 · S · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E12-1, E0-2 · Spec: flow J9
  - Note:
  - [ ] Today shows at most one nudge card with 'Done' and 'Not for me' that feed the policy

## E13 Doctor brief (F12)

_Headline feature._

- [ ] **E13-1 Brief data builder** · P0 · L · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E1-9, E9-1 · Spec: prd F12
  - Note:
  - [ ] Builds all 14 sections deterministically
  - [ ] JSON validates against a schema
  - [ ] Every number traces to source rows. 90 days builds in under 30 seconds
- [ ] **E13-2 Brief charts** · P0 · L · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E13-1 · Spec: design 11
  - Note:
  - [ ] Prescription timeline with glucose overlay, glucose trend and time in range, nutrition, activity, sleep, food-response leaderboard
  - [ ] Readable in grayscale
- [ ] **E13-3 Narrative with validator** · P0 · L · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E13-1, E0-9 · Spec: architecture 4.6
  - Note:
  - [ ] Model writes 'top 3 to discuss' and section summaries
  - [ ] Every sentence carries an evidence id
  - [ ] Validator rejects untagged sentences, unknown ids and numbers not in the data
  - [ ] Tested with deliberately bad drafts
- [ ] **E13-4 HTML and PDF render with patient view** · P0 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E13-2, E13-3 · Spec: design 11
  - Note:
  - [ ] Two-page A4 PDF plus in-app view
  - [ ] The patient sees exactly what the doctor sees
  - [ ] Patterns labelled unverified
- [ ] **E13-5 Share link** · P1 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E13-4 · Spec: schema 7
  - Note:
  - [ ] Requires sharing consent
  - [ ] Expiring random token stored hashed, revocable, every access logged
  - [ ] Opens read-only on a second device
- [ ] **E13-6 Brief screens in app** · P0 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E13-4 · Spec: flow J11
  - Note:
  - [ ] Generate, view, add own questions, share and revoke from the Me tab

## E14 Preventive care and scheduler (F13)

- [ ] **E14-1 Preventive items and screen** · P1 · M · Phase 2 · NEEDS OK
  - Owner: —
  - Status: backlog
  - Depends on: E1-3 · Spec: prd F13
  - Note:
  - [ ] Screening intervals are team-written config needing clinician review
  - [ ] Screen shows each item as ok, due soon, overdue or unknown
- [ ] **E14-2 Appointments and calendar file** · P1 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E14-1 · Spec: prd F13
  - Note:
  - [ ] Suggest, plan and confirm an appointment
  - [ ] Nothing is booked without confirmation
  - [ ] Downloads an .ics file that opens in a calendar
  - [ ] (Google Calendar link is a stretch.)
- [ ] **E14-3 Auto-brief before appointment** · P1 · S · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E14-2, E13-4 · Spec: prd F13
  - Note:
  - [ ] A brief is generated 48 hours before a planned appointment and the user is notified

## E15 Healthcare preparation (F14)

- [ ] **E15-1 Doctor questions list** · P0 · S · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E1-3 · Spec: prd F14
  - Note:
  - [ ] Add a question from anywhere (chat refusal, clash sheet, side-effect reason)
  - [ ] List editable
  - [ ] Flows into brief section 12
- [ ] **E15-2 Question phrasing and routing** · P1 · S · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E15-1, E1-8 · Spec: prd F14
  - Note:
  - [ ] Model tidies wording
  - [ ] Routing table suggests who to ask (eye, foot, kidney, heart) without naming diagnoses

## E16 Companion chat and agent harness (F15)

_Guardrails live here._

- [ ] **E16-1 Agent graph, Memory Service and evidence packet** · P0 · L · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E0-9 · Spec: architecture 5; memory 6-7
  - Note:
  - [ ] Graph with input guard, route, Memory Service, specialist, output guard, persist
  - [ ] Memory Service functions (get_context, get_timeline, get_entities, get_relationships, search_memories, propose_memory, supersede_memory) scope every call to the session user and return source ids, evidence status and confidence
  - [ ] Evidence packet built in the standard shape and the model answers from it only
  - [ ] Every step written to agent_runs and agent_steps; the packet never contains names or identifiers
- [ ] **E16-2 Guards and refusal templates** · P0 · L · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E16-1 · Spec: rules 1
  - Note:
  - [ ] Medication-advice, diagnosis, injection and urgent inputs are caught
  - [ ] Approved templates returned instead of model text
  - [ ] Smoke set of 40 prompts (in 4 languages) passes: no medication advice leaks
- [ ] **E16-3 Chat UI** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E16-1, E0-2 · Spec: flow J12
  - Note:
  - [ ] Chat screen with bubbles, distinct style for guard templates, and 'add to doctor questions' on refusals
- [ ] **E16-4 Specialist wiring** · P1 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E16-1 · Spec: architecture 5.2
  - Note:
  - [ ] Explainer, adherence, lifestyle, check-in and question helper reachable from chat
  - [ ] Each has an allow-listed toolset only
- [ ] **E16-5 Episodic memory** · P1 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E16-1 · Spec: architecture 5.3
  - Note:
  - [ ] Chat sessions summarised and embedded
  - [ ] The next chat can recall context (for example last week's side effect)

- [ ] **E16-6 JEV typed decisions for routing and guards** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: E0-12, E16-1 · Spec: memory 5
  - Note:
  - [ ] Memory route chosen with a choice question (semantic, temporal, entity, relationship)
  - [ ] Guard questions for medication advice, diagnosis and urgent wording use yes/no decisions on top of the rules; a rule that fires always wins
  - [ ] Confidence below the floor or a JEV outage takes the conservative path (refusal template, default route)
  - [ ] The 40-prompt smoke set passes with JEV on and with JEV off
## E17 Transparent memory and learning (F16)

_Makes the learning visible._

- [ ] **E17-1 Memory store and lifecycle** · P0 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E1-3 · Spec: schema 8; memory 8
  - Note:
  - [ ] memory_facts with confidence, evidence_status, evidence references and versions
  - [ ] Status changes (proposed, active, superseded, rejected) covered by state tests
  - [ ] Superseding links supersedes_id and never overwrites; rejected facts are never re-proposed
  - [ ] No fact is labelled validated anywhere in the data or the UI
- [ ] **E17-2 Nightly reflection agent** · P0 · L · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E17-1, E16-1, E1-9 · Spec: architecture 5.3
  - Note:
  - [ ] On the demo persona it proposes at least 5 correct facts across food, medication, activity and sleep, each with evidence
  - [ ] It never proposes a fact without evidence
- [ ] **E17-3 'What Smart Health has learned' screen** · P0 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E17-1, E0-2 · Spec: flow J13
  - Note:
  - [ ] Facts grouped by category with 'why I think this'
  - [ ] Confirm, edit and delete work and are logged
- [ ] **E17-4 Show the adaptation** · P0 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E17-2, E12-2, E9-2 · Spec: prd 7
  - Note:
  - [ ] One screen or demo view comparing week 1 with week 8 for the same person: baseline shift, nudge timing, learned facts, food responses drawn from every data stream

- [ ] **E17-5 Memory candidate typing and supersession** · P1 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E17-1, E0-12 · Spec: memory 8
  - Note:
  - [ ] Candidate fact type chosen with a choice decision; low confidence stores it as context, proposed
  - [ ] Memory Service validates the candidate (user owns sources, sources exist, threshold met, no conflict with an active fact)
  - [ ] A changed routine creates a new version and supersedes the old one
  - [ ] Contradiction check with a yes/no decision keeps both facts and asks the user (stretch)
## E18 Multilingual and TTS (F17)

- [ ] **E18-1 Language framework and strings** · P0 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E0-2 · Spec: rules 5
  - Note:
  - [ ] English, Chinese, Malay, Tamil for all UI text
  - [ ] Lint fails on hard-coded strings
  - [ ] Language switch changes every screen
- [ ] **E18-2 Audio playback** · P1 · S · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E4-2, E0-9 · Spec: prd F17
  - Note:
  - [ ] Listen button plays speech for explainers and reminders
  - [ ] Falls back to hiding the button if audio fails
- [ ] **E18-3 Translation review** · P1 · S · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E18-1 · Spec: prd F17
  - Note:
  - [ ] Native-speaker teammate or friend reviews the medication explainers and safety templates
  - [ ] Checklist signed off

## E19 Lifestyle timeline and day traces (F18)

_Multimodal fusion on one clock._

- [ ] **E19-1 Timeline view and API** · P0 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E1-9 · Spec: schema 9b
  - Note:
  - [ ] Timeline_events view merges meals, doses, workouts, sleep, symptoms, check-ins and urgent events on one clock
  - [ ] API returns a day in under 500 ms
- [ ] **E19-2 Day view screen** · P0 · L · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E19-1, E0-2 · Spec: prd F18
  - Note:
  - [ ] Glucose line with markers for meals, doses (taken, unconfirmed, missed), workouts and symptoms
  - [ ] Heart rate, steps and sleep bands underneath
  - [ ] Missing data shows as a gap, not a line
- [ ] **E19-3 Event windows and pattern candidates** · P0 · L · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E19-1, E8-2 · Spec: architecture 4.4b
  - Note:
  - [ ] Meal, workout, dose and sleep anchors produce outcomes
  - [ ] Unit test: an injected pattern is found with 5 or more pairs and ignored with 4
  - [ ] Wording says 'associated with'
- [ ] **E19-4 Brief day traces** · P0 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E19-3, E13-2 · Spec: prd F18
  - Note:
  - [ ] Brief shows best, worst and typical day chosen by fixed rules, each linking to its logs

## E20 Testing and validation (optional)

_Optional epic. Safety-critical tests are inside their feature epics and are not optional._

- [ ] **E20-1 Red-team suite** · P1 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E16-2 · Spec: rules 7
  - Note:
  - [ ] Extended set (medication advice, injection via chat and label text, diagnosis, urgent wording) in 4 languages. 100% pass
  - [ ] Never weakened to pass
- [ ] **E20-2 Engine unit tests** · P1 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E9-2, E8-2, E19-3, E5-4 · Spec: rules 7
  - Note:
  - [ ] Momentum, food response, event windows and adherence have edge-case tests (no data, boundaries, duplicates)
- [ ] **E20-3 Data validation checks** · P1 · S · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: E1-9 · Spec: schema 11
  - Note:
  - [ ] Automated checks: units, time zones, no zeros for missing, simulated rows flagged, disclosure list matches
- [ ] **E20-4 End-to-end demo rehearsal** · P1 · M · Phase 3
  - Owner: —
  - Status: backlog
  - Spec: flow 5
  - Note:
  - [ ] Script runs the full demo path
  - [ ] Timed at 6 minutes or less
  - [ ] Run twice with no fix needed
- [ ] **E20-5 Phone-size and accessibility pass** · P1 · S · Phase 3
  - Owner: —
  - Status: backlog
  - Spec: design 10
  - Note:
  - [ ] All key screens checked at phone size, 200% font, light and dark

## E21 Submission package

- [ ] **E21-1 Title, blurb and description** · P0 · S · Phase 3
  - Owner: —
  - Status: backlog
  - Spec: prd 11
  - Note:
  - [ ] Title, blurb under 10 words, description covering scenario, users, value, design and business value
- [ ] **E21-2 Architecture and trust-boundary diagram** · P0 · M · Phase 3
  - Owner: —
  - Status: backlog
  - Spec: architecture 1
  - Note:
  - [ ] One diagram with the trust boundaries and the key trade-offs
- [ ] **E21-3 Build proof** · P0 · S · Phase 3
  - Owner: —
  - Status: backlog
  - Depends on: E0-10 · Spec: prd 11
  - Note:
  - [ ] At least 3 screenshots of CodeBuddy/WorkBuddy work in the submission
- [ ] **E21-4 Cover image** · P0 · S · Phase 3
  - Owner: —
  - Status: backlog
  - Depends on: E0-5 · Spec: prd 11
  - Note:
  - [ ] 16:9 image at 380x216
- [ ] **E21-5 Demo video (optional bonus)** · P1 · M · Phase 3
  - Owner: —
  - Status: backlog
  - Depends on: E20-4 · Spec: prd 11
  - Note:
  - [ ] 5 to 8 minutes: overview, core features, build reflection
- [ ] **E21-6 Public repo, README and demo instructions** · P0 · M · Phase 3
  - Owner: —
  - Status: backlog
  - Depends on: E0-6 · Spec: prd 11
  - Note:
  - [ ] Repo made public for the submission, with no secrets or raw datasets in its history
  - [ ] README runs the demo in 5 commands on a fresh machine
  - [ ] A live URL is optional and not planned: the demo runs locally
- [ ] **E21-7 Final rehearsal** · P0 · S · Phase 3
  - Owner: —
  - Status: backlog
  - Depends on: E20-4 · Spec: flow 5
  - Note:
  - [ ] Two clean run-throughs by different presenters

## E22 Integration checkpoints

_End-to-end runs that must pass before the next phase starts. This is how the parts link together._

- [ ] **CP0 Checkpoint 0: mockup and data ready** · P0 · M · Phase 0
  - Owner: —
  - Status: backlog
  - Depends on: E0-5, E1-5, E0-6, E0-11 · Spec: backlog
  - Note:
  - [ ] Prototype walks the whole demo script with no dead ends
  - [ ] Importers load one participant into the database
  - [ ] A deployed page reads from the hosted database
  - [ ] Schema, demo data pack and design tokens are frozen
- [ ] **CP1 Checkpoint 1: thin vertical slice** · P0 · M · Phase 1
  - Owner: —
  - Status: backlog
  - Depends on: CP0, E5-2, E7-2, E8-2, E3-5, E16-2, E11-3 · Spec: backlog
  - Note:
  - [ ] Open as demo patient, see doses on Today and tap Taken
  - [ ] Log a glucose reading and a meal and see them stored
  - [ ] Replay a CGM sprint and see food responses computed
  - [ ] Photograph a medication, review, confirm and see the dose schedule appear
  - [ ] Ask 'can I skip metformin' and get the refusal template
  - [ ] Replay a 2.8 mmol/L reading and the urgent screen opens
- [ ] **CP2 Checkpoint 2: all features and the brief** · P0 · M · Phase 2
  - Owner: —
  - Status: backlog
  - Depends on: CP1, E13-4, E19-4, E17-4, E13-5 · Spec: backlog
  - Note:
  - [ ] Every step of the demo script in flow.md section 5 works with the real backend
  - [ ] Brief generated for the demo patient with prescription timeline, day traces and validator report
  - [ ] Learned facts and the week 1 versus week 8 view work
  - [ ] Share link opens on a second device
- [ ] **CP3 Checkpoint 3: submission ready** · P0 · S · Phase 3
  - Owner: —
  - Status: backlog
  - Depends on: CP2, E21-1, E21-2, E21-3, E21-4, E21-6, E21-7 · Spec: backlog
  - Note:
  - [ ] Submission package complete
  - [ ] Two clean rehearsals by different presenters
