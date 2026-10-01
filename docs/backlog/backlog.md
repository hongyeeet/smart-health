# Smart Health backlog

The single live task list for the team. **Epics E2-E19 map one-to-one to features F1-F18** (E2 = F1 ... E19 = F18). E0 is the demo mockup and foundation, E1 is data readiness, E20 is optional testing and validation, E21 is the submission package, E22 holds the integration checkpoints that tie the parts together.

**Priority:** P0 = in the demo script, P1 = should have, P2 = stretch. **Ask** = the task in plain words. **Status:** `backlog`, `in progress`, `in review`, `blocked`, `done`. **Reviewer:** if a task names a Reviewer, it goes to `in review` when finished, and only the Reviewer (or the owner) moves it to `done` after checking it against its success criteria and writing `Verified by <name> <date>` in the Note. **NEEDS OK** = relies on something outside the cited data sources, decide before starting.

## Team and workload split

| Person | GitHub | Owns | Also |
|---|---|---|---|
| Hong Yi (owner) | hongyeeet | E0, E3, E4, E5, E9, E13, E16, E17, E22 | E20 with Joely, E21 with the team |
| Joely | joelyhee | E1, E6, E7, E11, E18, E19 | E20 with Hong Yi, E21 with the team |
| Damien | chua-damien | E2, E8, E10, E12, E14, E15 | Reviewer for E4 and E13, E21 with the team |

Owners are set on every task. Only the owner of a task, or the person who picked it up and told the team, changes it. The owner of the project alone verifies UAT and promotes `dev` to `uat` and `main`.

## Session handover

The full process is in [../handover/HANDOVER.md](../handover/HANDOVER.md). In short, at the end of every session:

1. Tick each finished subtask: `- [ ]` becomes `- [x]`.
2. Set `Status:` to `backlog`, `in progress`, `in review`, `blocked` or `done`. If the task has a `Reviewer:`, set `in review` instead of `done`. Tick the task's own box only when every subtask is ticked and the task is `done`.
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

**In plain terms:** The mockup you can click through, plus the empty-but-running app, the AI gateway and the agreed ground rules everyone builds against.

_Mockup first. Wireframes cover the app only; watch, CGM and camera are just data sources feeding it._

- [ ] **E0-1 Scope key pages and end-to-end flow** · P0 · Phase 0
  - Ask: Sit down together and decide which screens the mockup needs (at most 15) and how a person moves between them. Produce a short page list and one flow diagram. Done when every feature F1 to F18 appears on at least one screen and all three of you agree.
  - Owner: Hong Yi
  - Status: backlog
  - Spec: flow.md 1-2
  - Note:
  - [ ] Working session with all 3
  - [ ] Output: list of at most 15 key pages (purpose, entry/exit, data shown) and one flow diagram
  - [ ] Every feature F1-F18 appears on at least one page
  - [ ] All 3 sign off
- [ ] **E0-2 Design tokens and component kit** · P0 · Phase 0
  - Ask: Turn the colours, fonts and spacing in design.md into reusable building blocks in code (buttons, cards, dose card, chat bubble and so on) so every screen looks the same. Done when each block works in light and dark mode and at large text sizes.
  - Owner: Hong Yi
  - Status: backlog
  - Spec: design.md 2-5
  - Note:
  - [ ] Tokens from design.md in code
  - [ ] The 12 primitives (Button, Card, DoseCard, ReasonSheet, ReadingInput, ConfidenceChip, SourceTag, TrendCard, MemoryFactRow, UrgentScreen, ChatBubble, Banner) render in light and dark, at 100% and 200% font scale, contrast at least 4.5:1
- [ ] **E0-3 Clickable prototype: core flow** · P0 · Phase 0
  - Ask: Build the clickable mockup of the whole app with fake data and no backend, so you can click through the entire demo script. Done when there are no dead ends from start to finish.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E0-1, E0-2 · Spec: flow.md 5
  - Note:
  - [ ] Phone-frame web prototype with fake data and no backend
  - [ ] Screens: onboarding, scan and review, Today, Log, Meds, Insights with day view, Brief, Memory, Urgent, Chat
  - [ ] Every step of the demo script is clickable start to finish with no dead ends
- [ ] **E0-4 Prototype: data-source simulator panel** · P1 · Phase 0
  - Ask: Add a small side panel to the mockup that pretends to be the watch, glucose sensor and camera pushing data in. It shows that outside sources only supply data and the app does the work.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E0-3 · Spec: prd F6, F7
  - Note:
  - [ ] Side panel with buttons that push a watch sync, a CGM reading, a meal and a medication photo into the prototype
  - [ ] App shows the imported state (for example 'Connected: watch, CGM')
  - [ ] Makes clear the outside sources only supply data
- [ ] **E0-5 Prototype review and freeze** · P0 · Phase 0
  - Ask: Walk through the mockup together, fix what is wrong, then freeze version 1 at a link the team can open. This is the 'we agree this is what we are building' moment.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E0-3
  - Note:
  - [ ] 30-minute walkthrough by all 3, change list applied, prototype v1 frozen and hosted at a public URL, open questions logged in the repo
- [ ] **E0-6 App skeleton and Supabase connection** · P0 · Phase 0
  - Ask: Set up the empty app so it actually runs: the web app and API start with one command, they connect to the Supabase database, and one page can show a row from it. Done when a teammate can set it up in five commands.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E0-1 · Spec: architecture
  - Note:
  - [ ] Mobile-first web app and API start locally with one command per machine
  - [ ] Supabase project renamed to smart-health; connection details shared privately and kept in .env, never committed
  - [ ] Row-level security is on with no policies for every table, and only the backend connects
  - [ ] One page reads a database row through the API
  - [ ] .env.example complete and setup takes at most 5 commands
- [ ] **E0-7 Demo session (replaces sign-in)** · P1 · Phase 1
  - Ask: Replace log-in screens with one 'Start as demo patient' button so the app always knows which patient it is showing. No passwords.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E0-6 · Spec: rules.md 8
  - Note:
  - [ ] 'Start as demo patient' creates a session
  - [ ] Every API query is scoped by the session's user id
  - [ ] No password screens
- [ ] **E0-8 Event log writer** · P0 · Phase 1
  - Ask: Build the activity log: every important thing a user does is written to a tamper-evident record. Done when a test proves that editing an old entry is detected.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E0-6, E1-3 · Spec: flow.md 0; schema 9
  - Note:
  - [ ] Client logEvent() and server writer append to event_log
  - [ ] Client events are deduplicated by client_event_id
  - [ ] A test proves the per-user hash chain detects a tampered row
- [ ] **E0-9 LLM and AI provider decision and gateway** · P0 · Phase 0
  - Ask: Pick which AI provider you will use for chat, reading photos and embeddings, and wrap it in one gateway so the rest of the app never calls it directly. Done when each kind of call returns an answer and the key lives only in settings.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E0-6 · Spec: architecture 2
  - Note:
  - [ ] Provider decision recorded in the repo
  - [ ] Gateway wraps chat, vision and embeddings with timeout, retry and logging
  - [ ] A smoke test gets a response from each
  - [ ] Keys live in env only
- [ ] **E0-10 Build-proof habit** · P1 · Phase 0
  - Ask: Keep proof that you built this with CodeBuddy or WorkBuddy: save screenshots of the work in docs/proof as you go. The hackathon requires at least three.
  - Owner: Hong Yi
  - Status: backlog
  - Spec: prd 11
  - Note:
  - [ ] Docs/proof/ folder
  - [ ] At least 3 screenshots of CodeBuddy/WorkBuddy work saved by CP1, then one per milestone
- [ ] **E0-11 Freeze shared contracts** · P0 · Phase 0
  - Ask: Agree and freeze the things everyone builds against so you can work in parallel: the database schema, the demo data, the API shape, the event names, the design tokens and the safety message templates.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E1-3, E0-2, E0-6 · Spec: architecture.md
  - Note:
  - [ ] Schema: schema.md and migrations frozen; changes need all 3 owners and a schema.md update
  - [ ] Demo data pack: seed_demo.py output frozen, same seed gives same data
  - [ ] API contract: OpenAPI generated from the backend plus a mock server so the UI can be built first
  - [ ] Event names: flow.md section 4 is the only catalogue, add there before using a new event
  - [ ] Design tokens: no hard-coded colours or sizes
  - [ ] Guardrail templates: every patient-facing AI output goes through the approved templates

- [ ] **E0-12 Decide and wire the JEV decision layer** · P0 · Phase 0
  - Ask: Decide how the fast yes/no decision layer (JEV) runs: a hosted service, small models on a laptop, or just the Hunyuan fallback. Wire it so the app asks it small questions and falls back safely if it is unsure or down.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E0-9 · Spec: memory 5
  - Note:
  - [ ] Choose hosted OpenJev, small CPU models, self-hosted, or the Hunyuan fallback only, and record the choice with the data-handling note
  - [ ] decide(state, questions) in decision/ keeps the OpenJev request and response shape (noul, choice, score) and returns probability and confidence
  - [ ] Smoke test returns an answer for one yes/no and one choice question; an image question too if the chosen option supports images
  - [ ] Switching JEV off routes every call to the fallback, and the conservative path applies when confidence is unknown
## E1 Data readiness

**In plain terms:** Get the data ready: download it, understand it, load it into the database, and build the demo patient with a simulated history.

_Data ready for analysis and model training, stored in the schema, with scaffolding fields for all user data._

- [ ] **E1-1 Data download scripts** · P0 · Phase 0
  - Ask: Write one script that downloads only the allowed dataset subsets into data/raw, with sizes and checksums logged and each licence noted. Nothing downloaded is committed to git.
  - Owner: Joely
  - Status: backlog
  - Spec: data plan
  - Note:
  - [ ] One script fetches the cited subsets into gitignored data/raw: CGMacros, BIG IDEAs (3-5 participants: Dexcom, HR, EDA, TEMP, Food_Log, Demographics), NHANES files, Fitbit, 250k Medicines, Open Food Facts (SG/MY subset), Doctor Specialty, GlucoBench
  - [ ] Sizes and checksums logged. data/README lists each licence
- [ ] **E1-2 Profiling report per dataset** · P0 · Phase 0
  - Ask: For each dataset write a short report: how many people, rows, dates, gaps and units. It answers practical questions, such as how many diabetic CGMacros participants have complete glucose and meal data, and whether the medicine dataset really has an interactions column.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-1 · Spec: data plan
  - Note:
  - [ ] One short report per dataset (participants, rows, date span, missing values, units, sampling interval)
  - [ ] Answers: how many CGMacros T2D participants have complete CGM and meals; whether 250k Medicines really has an interactions column; BIG IDEAs HbA1c range
- [ ] **E1-3 Canonical schema and migrations** · P0 · Phase 0
  - Ask: Turn the schema document into real database tables, with migrations you can apply to an empty database and undo. Done when it applies cleanly, the constraints are in, and row-level security is on.
  - Owner: Joely
  - Status: backlog
  - Spec: schema.md
  - Note:
  - [ ] Migrations create every table in schema.md sections 2-9b
  - [ ] They apply cleanly to an empty database and roll back
  - [ ] Constraints and enums present
  - [ ] Seeding one empty user succeeds. schema.md updated if anything changed
  - [ ] Row-level security is enabled on every table with no policies
- [ ] **E1-4 User-data scaffolding and data dictionary** · P0 · Phase 0
  - Ask: List every piece of user data the app collects and make sure each has a table, a column, a unit and a 'where did this come from' flag. Write it up as a data dictionary.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-3 · Spec: schema.md
  - Note:
  - [ ] Every field the app collects has a table, column, unit and source flag (manual, imported, simulated). docs/data_dictionary.md lists them
  - [ ] Covers profile, conditions, allergies, medications and ingredients, doses, glucose, meals, workouts, sleep, wearable samples, symptoms, mood, BP, labs, appointments, questions, memory
- [ ] **E1-5 CGMacros importer** · P0 · Phase 1
  - Ask: Write the importer for CGMacros: glucose, meals and macros, watch data, labs and profile go into our tables in our units, with dates shifted and stored in UTC. Done when row counts match the source and a spot check of 100 glucose values agrees.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-2, E1-3 · Spec: data plan; schema
  - Note:
  - [ ] Loads the chosen T2D participant(s): CGM to glucose_readings (mmol/L, quality flag, native interval), meals and macros, Fitbit HR/steps to health_samples, bio.csv to profile and lab_results
  - [ ] Dates shifted per person, stored in UTC
  - [ ] Row counts equal the source. 100 random glucose rows verified against the raw file
- [ ] **E1-6 BIG IDEAs importer** · P1 · Phase 1
  - Ask: Do the same for BIG IDEAs (a handful of participants): glucose, heart rate, skin signals and the food log, with heart rate reduced to one value per minute.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-3 · Spec: data plan
  - Note:
  - [ ] Dexcom, HR, EDA, TEMP, food log and demographics loaded for the chosen participants
  - [ ] HR downsampled to 1 minute
  - [ ] Rows marked entry_source demo_dataset
  - [ ] Test compares counts to source
- [ ] **E1-7 Fitbit, NHANES and GlucoBench importers** · P1 · Phase 1
  - Ask: Write importers for the smaller datasets: Fitbit (a second watch format), NHANES (typical ranges by age and sex) and GlucoBench (a test file). Insulin columns are thrown away.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-3 · Spec: data plan
  - Note:
  - [ ] Fitbit to samples and sleep
  - [ ] NHANES to population_priors (percentiles by age, sex, diabetes) plus a persona-sampling table
  - [ ] GlucoBench to a fixture table with insulin columns discarded
  - [ ] Each has a test
- [ ] **E1-8 Reference tables** · P0 · Phase 1
  - Ask: Load the reference tables the app looks things up in: medicines with their aliases and side effects, foods with salt and sugar, who-to-see routing, and a record of where each came from. Searching 'metformin' should find its aliases.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-2, E1-3 · Spec: schema 9b
  - Note:
  - [ ] Drug_reference, drug_aliases and drug_side_effects from 250k Medicines (diabetes, BP and lipid drugs first, at least 100 generics). foods from Open Food Facts (SG/MY) and NHANES dietary files with sodium and sugar. routing_rules from Doctor Specialty. data_sources filled
  - [ ] Searching 'metformin' returns its aliases
  - [ ] At least 90% of seeded foods have sodium or are flagged unknown
- [ ] **E1-9 Demo persona and 60-day simulator** · P0 · Phase 1
  - Ask: Build the demo patient: one real diabetic participant's profile plus a repeatable simulator that fills 60 days of doses (with misses and a missed streak), mood, blood pressure, workouts and symptoms, with a rising morning-glucose trend in the last three weeks. Everything simulated is flagged.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-5, E1-8 · Spec: prd A8
  - Note:
  - [ ] Persona is one CGMacros T2D participant. seed_demo.py builds 60 days: glucometer readings, doses with a weekend/evening miss pattern and one 4-day streak, mood/sleep/stress, BP, workouts, symptoms, and a rising fasting-glucose drift in the last 3 weeks
  - [ ] Every simulated row is flagged and a disclosure list is generated
  - [ ] Same seed gives identical data
- [ ] **E1-10 Analysis-ready feature tables** · P1 · Phase 1
  - Ask: Prepare tidy tables for analysis and model training: each meal with its macros, context and measured glucose response, split by participant so training and testing do not leak into each other.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-5, E1-6
  - Note:
  - [ ] Meal_features (macros, context, response iAUC and peak rise) and a daily feature table
  - [ ] Train and test split by participant with no leakage
  - [ ] Documented
- [ ] **E1-11 Baseline model: meal to glucose response** · P1 · Phase 2
  - Ask: Train a simple first model that predicts how much a meal raises glucose, and write a short model card. It must beat just guessing the average on people it has not seen.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-10
  - Note:
  - [ ] Model card (data, split, metric)
  - [ ] Beats predicting the mean on held-out participants
  - [ ] Artefact loadable by the API
  - [ ] Labelled as a population model
- [ ] **E1-12 Storage and replay** · P0 · Phase 1
  - Ask: Make a replay tool that feeds the demo data into the app as if it were live (normal or fast speed), and make imports safe to run twice without creating duplicates.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-5 · Spec: architecture 4.3
  - Note:
  - [ ] Replay.py streams the demo data as if live (1x and accelerated)
  - [ ] The import endpoint is idempotent by source plus external_id: running twice creates no duplicates

- [ ] **E1-13 Bronze ingestion log and storage layout** · P0 · Phase 1
  - Ask: Create the raw-data log: every photo, image and import gets a row (with a checksum and time) and the original file is stored and never overwritten. Deleting is allowed only at the user's request and is logged.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-3 · Spec: schema 9c; architecture layers
  - Note:
  - [ ] ingestion_events table with checksum, source type, timestamps and processing status; unique per user and checksum
  - [ ] Storage layout by type (meals, medications, documents, exports) in a private Supabase Storage bucket; originals are never overwritten
  - [ ] Every photo, image and import writes an ingestion_events row
  - [ ] A user-initiated deletion removes the object, marks the row deleted and is logged
- [ ] **E1-14 Gold views and layer map** · P1 · Phase 1
  - Ask: Create four read-only summary views (health state, trends, adherence, insight context) that other features read from, and make sure the layer map in schema.md matches the real tables.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-3, E9-1 · Spec: schema 0b, 9c
  - Note:
  - [ ] Views health_state, trends, adherence_summary and insight_context created with calculation version, evidence window, freshness and quality status
  - [ ] The layer map in schema.md matches the migrated tables exactly
  - [ ] No table or view uses the names gold., silver. or bronze. as a prefix
- [ ] **E1-15 Devices and health goals tables with seed** · P0 · Phase 1
  - Ask: Add and seed two small tables: connected devices (watch, sensor, camera, with last sync) and health goals (weekly activity targets, marked as defaults until a doctor sets them).
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-3 · Spec: schema 9c
  - Note:
  - [ ] devices rows for the connected watch, sensor and camera with last-synced times
  - [ ] health_goals rows for the weekly moderate minutes and strength sessions, marked as defaults until a clinician sets them
  - [ ] Both tables are covered by the demo seed
## E2 Onboarding (F1)

**In plain terms:** How a new user enters their details, by form or by chat.

- [ ] **E2-1 Form onboarding screens** · P0 · Phase 1
  - Ask: Build the step-by-step form a new user fills in: about you, diagnosis, conditions, allergies, family history, medicines, connected sources and reminder times. It saves each step and resumes where the user left off.
  - Owner: Damien
  - Status: backlog
  - Depends on: E0-2, E1-3 · Spec: prd F1
  - Note:
  - [ ] Steps: about you, diagnosis and HbA1c, conditions, allergies, family history, medications entry point, connected sources, reminder times
  - [ ] Finishes in 5 minutes or less on a phone-size screen
  - [ ] Each step saves
  - [ ] Leaving and returning resumes
  - [ ] Writes profile, conditions and allergies
- [ ] **E2-2 Eligibility and consent** · P0 · Phase 1
  - Ask: Add the checks at the start: block people the app is not for (type 1, pregnant, under 18) with a kind message, and require consent before any data is stored.
  - Owner: Damien
  - Status: backlog
  - Depends on: E2-1 · Spec: prd F1
  - Note:
  - [ ] Type 1, pregnancy and under-18 are blocked with a clear message
  - [ ] Consent rows stored
  - [ ] The user cannot continue without data-processing consent
- [ ] **E2-3 Chat onboarding** · P1 · Phase 2
  - Ask: Offer a chat version of onboarding that collects the same details by conversation and shows what it has captured so far. It must give the same result as the form.
  - Owner: Damien
  - Status: backlog
  - Depends on: E16-1, E0-9 · Spec: prd F1
  - Note:
  - [ ] Same fields collected conversationally, with a live 'captured so far' card and edit before saving
  - [ ] A scripted transcript produces the same records as the form
- [ ] **E2-4 Summary review and demo fast-path** · P0 · Phase 1
  - Ask: Show a final summary the user can edit, and add the 'Start as demo patient' shortcut that skips onboarding for the demo.
  - Owner: Damien
  - Status: backlog
  - Depends on: E2-1, E0-7 · Spec: flow J1
  - Note:
  - [ ] Editable summary screen
  - [ ] 'Start as demo patient' skips onboarding and loads the seeded persona

## E3 Prescription and medication capture (F2)

**In plain terms:** Photograph a medicine, let the app read it, and have the user confirm what it found.

- [ ] **E3-1 Scan UI: capture and review** · P0 · Phase 1
  - Ask: Build the scan screen: take or upload a photo of a medicine label, then a review screen showing each extracted field with a confidence tag. Anything uncertain must be tapped to confirm, and nothing saves until it is confirmed.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E0-2 · Spec: prd F2
  - Note:
  - [ ] Camera/upload screen with framing tips
  - [ ] Review screen shows each field with a confidence chip
  - [ ] Fields below 0.85 must be tapped to confirm
  - [ ] Nothing saves until confirmed
- [ ] **E3-2 Extraction service** · P0 · Phase 1
  - Ask: Build the service that reads a label photo with the vision AI and returns structured fields (name, strength, directions and so on) with a confidence for each. Missing means blank, never guessed. Names and ID numbers are removed.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E0-9 · Spec: prd F2; med capture pipeline
  - Note:
  - [ ] Vision model returns strict JSON with confidence and source text per field
  - [ ] Missing means null
  - [ ] Patient name and NRIC are dropped before storage
  - [ ] Handles prescription label, box, supplement, TCM and OTC
  - [ ] Invalid JSON retried once then fails safe
- [ ] **E3-3 Name matching to drug database** · P0 · Phase 1
  - Ask: Match the name on the label to our medicine list (exact first, then close matches). If nothing matches, say 'I'm not able to identify this medication, please check with your pharmacist' and offer manual entry. The AI never picks the medicine record itself.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E1-8 · Spec: prd F2
  - Note:
  - [ ] Exact then fuzzy match to drug_aliases
  - [ ] Test set of 30 names passes
  - [ ] No match shows 'I'm not able to identify this medication, please check with your pharmacist' and offers manual entry
  - [ ] The model never chooses the database id
- [ ] **E3-4 Directions parser** · P0 · Phase 1
  - Ask: Write a plain-code parser that turns directions like 'twice daily after meals' into times per day and with-food. Anything it does not recognise becomes a question to the user.
  - Owner: Hong Yi
  - Status: backlog
  - Spec: prd F2
  - Note:
  - [ ] Deterministic parser for at least 30 phrases ('twice daily after meals', 'at night', ...) gives times per day, timing and with-food
  - [ ] Unknown phrases turn into a question to the user
  - [ ] Verbatim text always stored
- [ ] **E3-5 Confirm and save transaction** · P0 · Phase 1
  - Ask: Make 'Confirm' do everything in one go: save the medicine and its ingredients, create the dose schedule and run the clash check. If any part fails, nothing is saved.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E3-2, E3-3, E3-4, E1-3 · Spec: schema 3
  - Note:
  - [ ] One transaction saves the medication, ingredients, dose schedule, clash check and event log
  - [ ] A forced failure rolls back everything
- [ ] **E3-6 Extraction test set and accuracy report** · P1 · Phase 2 · NEEDS OK
  - Ask: Measure how accurate the scanner is on 30 or more photos you take yourselves, and report accuracy by type of item. These photos are outside the allowed datasets, so this needs the owner's OK.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E3-2 · Spec: data plan
  - Note:
  - [ ] No photo set exists in the cited data, so this needs photos the team takes. 30 or more photos across item types, ground truth per photo, per-field accuracy reported by item type, target at least 90% on name and strength for printed labels, and low confidence flagged for the rest

## E4 Medication explainer (F3)

**In plain terms:** Explain each medicine in plain language, with sources, in four languages.

- [ ] **E4-1 Drug knowledge index** · P0 · Phase 2
  - Ask: Prepare the medicine knowledge so the app can look facts up: split the medicine dataset into chunks and index them. Twenty test medicine names must retrieve the right drug.
  - Owner: Hong Yi
  - Reviewer: Damien
  - Status: backlog
  - Depends on: E1-8 · Spec: prd F3
  - Note:
  - [ ] 250k Medicines text chunked and embedded
  - [ ] Retrieval returns the correct drug for 20 test names
- [ ] **E4-2 Explainer generation with guard** · P0 · Phase 2
  - Ask: Generate the plain-language explanation of a medicine (what it is for, how you take it from your own label, common side effects, when to tell your doctor), each statement with its source. The user's dose comes only from their confirmed label, and 'can I skip it?' triggers the refusal message.
  - Owner: Hong Yi
  - Reviewer: Damien
  - Status: backlog
  - Depends on: E4-1, E0-9, E16-2 · Spec: prd F3
  - Note:
  - [ ] Plain-language sections (what it is for, how you take it from your own label, common side effects, when to tell your doctor)
  - [ ] Every sentence cites its source
  - [ ] Dose text comes only from the confirmed medication
  - [ ] 'Can I skip it?' triggers the refusal template
- [ ] **E4-3 Explainer screen, language and audio** · P0 · Phase 2
  - Ask: Build the medicine detail screen: it shows the explanation and sources, switches between four languages and has a listen button.
  - Owner: Hong Yi
  - Reviewer: Damien
  - Status: backlog
  - Depends on: E4-2, E18-1 · Spec: flow J3
  - Note:
  - [ ] Medication detail screen with sources shown, four-language switch and a listen button

## E5 Adherence engine (F4)

**In plain terms:** Dose reminders, and recording whether each dose was taken and, if not, why.

- [ ] **E5-1 Dose schedule generator** · P0 · Phase 1
  - Ask: Generate the next seven days of dose slots for each medicine in the user's time zone, without creating duplicates if it runs again.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E1-3 · Spec: schema 3
  - Note:
  - [ ] Seven days of dose events generated per medication in the user's timezone
  - [ ] Re-running creates no duplicates
- [ ] **E5-2 Today screen and dose card** · P0 · Phase 1
  - Ask: Build the Today screen: doses due now with a big 'Taken' button, showing the scheduled, taken and unconfirmed states.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E0-2, E5-1 · Spec: flow J4
  - Note:
  - [ ] Today lists due doses
  - [ ] Tapping Taken updates status and logs the event
  - [ ] Card shows scheduled, taken and unconfirmed states
- [ ] **E5-3 Reminder engine** · P0 · Phase 1
  - Ask: Build the reminder engine: remind at the dose time, nudge again an hour later, and mark the dose 'unconfirmed' when the window closes. In demo mode you can trigger each step on demand.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E5-1, E0-8 · Spec: prd F4
  - Note:
  - [ ] Reminder at the scheduled time, re-nudge after 60 minutes, unconfirmed when the window closes
  - [ ] Jobs are idempotent
  - [ ] Demo mode can trigger each step on demand
  - [ ] In-app notifications (no push needed)
- [ ] **E5-4 Miss-reason flow and state machine** · P0 · Phase 1
  - Ask: When a dose is unconfirmed, ask the user why with one tap (forgot, side effects, ran out and so on). Enforce the allowed status changes in code and test them.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E5-3 · Spec: prd F4
  - Note:
  - [ ] Next open shows one-tap reasons (forgot, side effects, ran out, felt fine, cost, other)
  - [ ] Only valid transitions allowed, invalid ones raise an error, covered by tests
  - [ ] Side effects offers to add a symptom and a doctor question
- [ ] **E5-5 Meal-triggered prompt and refill forecast** · P1 · Phase 2
  - Ask: Prompt the with-food medicine when a meal is logged, and predict when pills will run out so the app can remind the user a week ahead.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E5-1, E7-2 · Spec: prd F4
  - Note:
  - [ ] Logging a meal prompts the with-food medication
  - [ ] Refill date predicted from quantity and dose rate, with a reminder 7 days ahead

## E6 Clash checker (F5)

**In plain terms:** Warn about possible medicine clashes without ever claiming something is safe.

- [ ] **E6-1 Interaction data check and load** · P0 · Phase 1
  - Ask: Check whether the medicine dataset really contains interaction data and how many usable pairs it has. If it does not, stop and raise it as a decision. Load whatever exists with its source.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-8 · Spec: prd A4
  - Note:
  - [ ] Report confirms whether 250k Medicines contains interactions, and how many usable pairs
  - [ ] If it does not, raise it as a decision and stop. interaction_rules loaded with source recorded
- [ ] **E6-2 Clash service** · P0 · Phase 2
  - Ask: Build the checker: look up each new medicine (and each ingredient) against the interaction table. A known pair gives a hit; anything unmatched, and every supplement or TCM item, says 'not checked', never 'safe'.
  - Owner: Joely
  - Status: backlog
  - Depends on: E6-1, E3-5 · Spec: prd F5
  - Note:
  - [ ] Deterministic lookup per ingredient
  - [ ] A known pair produces a hit
  - [ ] An unmatched pair or any supplement/TCM item gives 'not checked', never 'safe'
  - [ ] Runs whenever a medication is added or changed
- [ ] **E6-3 Clash screen and question hand-off** · P0 · Phase 2
  - Ask: Build the interaction message with fixed wording: 'Possible interaction between X and Y. Please check with your pharmacist or doctor before continuing.' Offer to add it to the doctor questions. It never says to stop a medicine.
  - Owner: Joely
  - Status: backlog
  - Depends on: E6-2, E15-1 · Spec: prd F5
  - Note:
  - [ ] Fixed wording: 'Possible interaction between X and Y
  - [ ] Please check with your pharmacist or doctor before continuing.' Never says stop
  - [ ] Offers to add to doctor questions
  - [ ] Hits appear in the brief
- [ ] **E6-4 Seed a demo clash** · P0 · Phase 2
  - Ask: Make sure the demo patient has one real interaction hit and one supplement showing 'not checked', so the demo can show both cases.
  - Owner: Joely
  - Status: backlog
  - Depends on: E6-2 · Spec: flow 5
  - Note:
  - [ ] The demo persona has one pair that hits and one supplement that shows 'not checked'

## E7 Health tracking and logging (F6)

**In plain terms:** All the ways a user logs data: glucose, meals, workouts, symptoms and mood, plus connected sources.

- [ ] **E7-1 Glucose entry with threshold hook** · P0 · Phase 1
  - Ask: Build quick glucose entry (three taps or fewer) with its context (fasting, after a meal and so on), stored in mmol/L, and check every reading against the urgent thresholds.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-3, E11-1 · Spec: prd F6
  - Note:
  - [ ] Entry in 3 taps or fewer, with context (fasting, pre, post, bedtime, random), stored in mmol/L
  - [ ] Every reading is checked by the threshold service
- [ ] **E7-2 Meal logging with LLM macro estimation** · P0 · Phase 1
  - Ask: Build meal logging: the user sends a photo or types a description, the AI estimates the items and macros with a confidence, they show as 'Estimated', and the user can confirm or edit. Keep the original photo and the AI's raw answer.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-8, E0-9, E1-13 · Spec: prd F6; memory 9
  - Note:
  - [ ] Photo or text description goes to the LLM, which returns the items and estimated kcal, carbs, protein, fat, fibre, sugar and sodium with a confidence per field
  - [ ] Estimates carry an 'Estimated' badge and can be edited or confirmed; confirmed values are stored as user-confirmed
  - [ ] Original photo and raw analysis are stored and never overwritten; re-running with a new prompt adds a new analysis
  - [ ] High-salt and high-sugar flags are computed in code from the stored values
  - [ ] Open Food Facts and NHANES values are used only as a sanity check that adds a 'check this' flag
  - [ ] A food the LLM cannot identify asks the user to type it in
- [ ] **E7-3 Workout, symptom and mood check-in logs** · P0 · Phase 1
  - Ask: Build the other quick logs: workouts (type, intensity, duration), symptoms with severity, and the 30-second evening mood, stress and sleep check-in.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-3 · Spec: prd F6
  - Note:
  - [ ] Three quick forms, each at most 15 seconds
  - [ ] Evening check-in captures mood, stress, sleep quality and energy on 1 to 5
- [ ] **E7-4 Connect sources and import** · P0 · Phase 1
  - Ask: Build the 'Connect sources' screen showing the watch and sensor as connected, make imports safe to repeat, and show the last-synced time.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-12 · Spec: prd F6
  - Note:
  - [ ] 'Connect sources' screen shows watch and CGM as connected and feeds data from the replay
  - [ ] Import is idempotent and shows last-synced time
- [ ] **E7-5 Edit, delete and completeness** · P1 · Phase 2
  - Ask: Let users edit or delete their own logs (recorded in the activity log) and calculate how complete each data stream is, for use in the brief.
  - Owner: Joely
  - Status: backlog
  - Depends on: E7-1 · Spec: prd F6
  - Note:
  - [ ] Users can edit or delete their own logs, edits are recorded in the event log
  - [ ] Data completeness percent per stream is calculated for the brief

## E8 CGM sprint and personal food response (F7)

**In plain terms:** Use the glucose sensor to learn how each person responds to different foods.

- [ ] **E8-1 Sprint start, end and replay** · P0 · Phase 1
  - Ask: Let a user start and end a 14-day sensor 'sprint', filled from the replayed data. Only one sprint can be open at a time.
  - Owner: Damien
  - Status: backlog
  - Depends on: E1-12 · Spec: prd F7
  - Note:
  - [ ] Start and end a 14-day CGM sprint
  - [ ] Replay of the chosen CGMacros participant fills it
  - [ ] One open sprint per user
- [ ] **E8-2 Meal response calculator** · P0 · Phase 1
  - Ask: For each meal, calculate the glucose before it, the peak rise and the two-hour area under the curve. Check it against a reference calculation on 20 meals. Windows with too little data are skipped.
  - Owner: Damien
  - Status: backlog
  - Depends on: E8-1 · Spec: architecture 6
  - Note:
  - [ ] For each meal, baseline glucose, peak rise and 2-hour incremental AUC
  - [ ] Matches a pandas reference on 20 meals
  - [ ] Windows with too little data are excluded
- [ ] **E8-3 Food response leaderboard and note** · P0 · Phase 2
  - Ask: Build the personal food-response leaderboard (gentlest to spikiest foods), shown only when a food has at least two observations, with the count and range. Add a gentle note when the user logs a spiky food.
  - Owner: Damien
  - Status: backlog
  - Depends on: E8-2 · Spec: prd F7
  - Note:
  - [ ] Responses per food shown only when n is 2 or more, with n and range
  - [ ] Logging a known high-response food shows the factual note
  - [ ] Leaderboard in Insights and the brief
- [ ] **E8-4 Sprint summary metrics** · P1 · Phase 2
  - Ask: Calculate the sprint summary numbers (time in range, below, above, average, variability) and check them against a reference.
  - Owner: Damien
  - Status: backlog
  - Depends on: E8-1 · Spec: schema 9b
  - Note:
  - [ ] Time in range, below range, above range, GMI and CV match a pandas reference
- [ ] **E8-5 Compared to typical (population model)** · P2 · Phase 2
  - Ask: Stretch: show what the population model expected next to what actually happened, labelled as a population estimate.
  - Owner: Damien
  - Status: backlog
  - Depends on: E1-11
  - Note:
  - [ ] Screen shows the model's expected response next to the actual one, labelled as a population estimate

## E9 Momentum engine (F8)

**In plain terms:** Learn each person's own normal and flag when they drift away from it.

_Learns each person's own baseline across all data streams._

- [ ] **E9-1 Daily aggregates job** · P0 · Phase 2
  - Ask: Every night, roll each day's glucose, meals, activity, sleep, mood and adherence into daily totals. Missing data stays empty and is never turned into zero.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E1-9 · Spec: schema 5
  - Note:
  - [ ] Nightly rollup of glucose, meals, activity, sleep, mood and adherence per day
  - [ ] Missing data stays empty, never zero
- [ ] **E9-2 Baseline, momentum and flags** · P0 · Phase 2
  - Ask: Build the 'your own normal' engine: a 28-day baseline, the 7-day trend and whether it is speeding up. Tests: a real drift is flagged, plain noise is not, and fewer than 10 days says 'still learning'. Each flag stores the numbers behind it.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E9-1 · Spec: architecture 6
  - Note:
  - [ ] 28-day median and MAD baseline, 7-day slope and change of slope
  - [ ] Unit tests on synthetic series: a known drift is flagged, plain noise is not, fewer than 10 days shows 'learning'
  - [ ] Each flag stores the numbers behind it
- [ ] **E9-3 Insights screen** · P0 · Phase 2
  - Ask: Build the Insights screen: trend cards with the personal baseline band and a one-line plain-language summary, with a 7, 30 and 90 day switch.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E9-2, E0-2 · Spec: design 6-7
  - Note:
  - [ ] Trend cards with baseline band and one plain-language line each
  - [ ] Period switch 7, 30, 90 days
- [ ] **E9-4 Flag hand-offs** · P0 · Phase 2
  - Ask: When a flag fires, create a neutral note for the patient and an entry for the doctor brief.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E9-2 · Spec: prd F8
  - Note:
  - [ ] A flag creates a neutral patient note and an entry for the brief

## E10 Targeted symptom check-ins (F9)

**In plain terms:** Ask short, neutral health questions when a pattern suggests the doctor should know.

- [ ] **E10-1 Question bank and planner** · P0 · Phase 2 · NEEDS OK
  - Ask: Write the bank of short, neutral questions (for example about thirst or tingling feet) and a planner that picks at most one per day and three per week. The wording needs a clinician's review, so it needs the owner's OK.
  - Owner: Damien
  - Status: backlog
  - Depends on: E9-2 · Spec: prd F9
  - Note:
  - [ ] Question wording is team-written and needs clinician review
  - [ ] Planner picks at most 1 check-in per day and 3 per week, and learns which the user answers
- [ ] **E10-2 Check-in UI and logging** · P0 · Phase 2
  - Ask: Build the check-in card: it shows one question, and the answer or a skip is saved as a symptom entry.
  - Owner: Damien
  - Status: backlog
  - Depends on: E10-1 · Spec: flow J7
  - Note:
  - [ ] One neutral question card
  - [ ] Answer or skip is stored as a symptom log
- [ ] **E10-3 Link to flag and brief** · P1 · Phase 2
  - Ask: Link each answer back to the pattern that triggered it and show it in the brief's symptom section.
  - Owner: Damien
  - Status: backlog
  - Depends on: E10-2 · Spec: prd F9
  - Note:
  - [ ] Answers show in the brief symptom section, linked to the pattern that triggered them

## E11 Urgent escalation (F10)

**In plain terms:** Immediate, rule-based alerts for dangerous readings. No AI is involved.

_Rule-based, no LLM in the path._

- [ ] **E11-1 Threshold service and config** · P0 · Phase 1 · NEEDS OK
  - Ask: Write the urgent-alert rules as configuration (very low glucose, repeated highs, symptom rules) with tests at the boundaries (2.9, 3.0, 3.8 and 3.9 mmol/L). They are marked 'clinical validation pending' and need the owner's OK.
  - Owner: Joely
  - Status: backlog
  - Spec: prd F10
  - Note:
  - [ ] Thresholds are team-written rules
  - [ ] Boundary tests at 2.9, 3.0, 3.8 and 3.9 mmol/L, repeated highs, and the symptom rule all pass
  - [ ] Config file marked 'clinical validation pending'
- [ ] **E11-2 Urgent screen and recheck** · P0 · Phase 1
  - Ask: Build the full-screen urgent page: a clear instruction by level, call buttons, steps from the doctor's plan and a recheck timer. No AI is involved and it works offline.
  - Owner: Joely
  - Status: backlog
  - Depends on: E11-1, E0-2 · Spec: flow J8
  - Note:
  - [ ] Full-screen instruction by tier with call buttons and hypo self-help steps
  - [ ] No LLM in the path
  - [ ] Works with the network off
  - [ ] Recheck timer prompts a new reading
  - [ ] Events logged
- [ ] **E11-3 Demo trigger and replay of a low reading** · P0 · Phase 1
  - Ask: Make a demo trigger: replaying a 2.8 mmol/L reading opens the urgent screen within two seconds.
  - Owner: Joely
  - Status: backlog
  - Depends on: E11-1, E1-12 · Spec: flow 5
  - Note:
  - [ ] Replaying a 2.8 mmol/L reading opens the urgent screen within 2 seconds

## E12 Lifestyle coach and adaptive nudges (F11)

**In plain terms:** Nudges that adapt to what each person actually responds to.

_Adapts to what this user responds to._

- [ ] **E12-1 Nudge templates and triggers** · P0 · Phase 2 · NEEDS OK
  - Ask: Write the nudge messages as reviewed templates filled with the user's own data (for example 'you walked after dinner 3 times, and your evening readings were lower'). It needs the owner's OK because no guideline source is cited.
  - Owner: Damien
  - Status: backlog
  - Depends on: E9-2 · Spec: prd F11
  - Note:
  - [ ] No guideline corpus is in the cited data, so nudges are reviewed team-written templates filled with the user's own data
  - [ ] Each nudge names the data it is based on
- [ ] **E12-2 Adaptive nudge policy** · P0 · Phase 2
  - Ask: Build the learning part: pick which nudge and which time works for each user from what they act on, with some exploration, a daily cap and quiet hours. A simulation should show it shifting toward what the user acts on.
  - Owner: Damien
  - Status: backlog
  - Depends on: E12-1 · Spec: architecture 5.4
  - Note:
  - [ ] Chooses nudge type and time slot by observed act rate with 15% exploration, 3 per day cap, quiet hours
  - [ ] A simulation over the demo persona shifts toward the slots and types the user acts on
- [ ] **E12-3 Salt and sugar flags with own-data swaps** · P1 · Phase 2
  - Ask: When a meal is salty or sugary, suggest a food that gave this user a gentler response before.
  - Owner: Damien
  - Status: backlog
  - Depends on: E7-2, E8-3 · Spec: prd F11
  - Note:
  - [ ] High-salt or high-sugar meals show a card suggesting a food that gave this user a gentler response
- [ ] **E12-4 Nudge cards UI** · P0 · Phase 2
  - Ask: Build the nudge card on Today with 'Done' and 'Not for me' buttons, which feed the learning.
  - Owner: Damien
  - Status: backlog
  - Depends on: E12-1, E0-2 · Spec: flow J9
  - Note:
  - [ ] Today shows at most one nudge card with 'Done' and 'Not for me' that feed the policy

## E13 Doctor brief (F12)

**In plain terms:** The doctor brief: the key output that summarises the weeks between visits.

_Headline feature._

- [ ] **E13-1 Brief data builder** · P0 · Phase 2
  - Ask: Build the engine that gathers all 14 sections of the doctor brief from the data, with every number traceable to its source rows, in under 30 seconds for 90 days of data.
  - Owner: Hong Yi
  - Reviewer: Damien
  - Status: backlog
  - Depends on: E1-9, E9-1 · Spec: prd F12
  - Note:
  - [ ] Builds all 14 sections deterministically
  - [ ] JSON validates against a schema
  - [ ] Every number traces to source rows. 90 days builds in under 30 seconds
- [ ] **E13-2 Brief charts** · P0 · Phase 2
  - Ask: Draw the brief's charts: the prescription timeline with a glucose overlay, glucose trend, nutrition, activity, sleep and the food leaderboard, all readable in grayscale.
  - Owner: Hong Yi
  - Reviewer: Damien
  - Status: backlog
  - Depends on: E13-1 · Spec: design 11
  - Note:
  - [ ] Prescription timeline with glucose overlay, glucose trend and time in range, nutrition, activity, sleep, food-response leaderboard
  - [ ] Readable in grayscale
- [ ] **E13-3 Narrative with validator** · P0 · Phase 2
  - Ask: Have the AI write the top 3 and the section summaries, but every sentence must carry an evidence ID. A validator rejects sentences without one, unknown IDs, or numbers not in the data. Test it with deliberately bad drafts.
  - Owner: Hong Yi
  - Reviewer: Damien
  - Status: backlog
  - Depends on: E13-1, E0-9 · Spec: architecture 4.6
  - Note:
  - [ ] Model writes 'top 3 to discuss' and section summaries
  - [ ] Every sentence carries an evidence id
  - [ ] Validator rejects untagged sentences, unknown ids and numbers not in the data
  - [ ] Tested with deliberately bad drafts
- [ ] **E13-4 HTML and PDF render with patient view** · P0 · Phase 2
  - Ask: Render the brief as a two-page A4 PDF and an in-app view. The patient sees exactly what the doctor sees, and patterns are labelled unverified.
  - Owner: Hong Yi
  - Reviewer: Damien
  - Status: backlog
  - Depends on: E13-2, E13-3 · Spec: design 11
  - Note:
  - [ ] Two-page A4 PDF plus in-app view
  - [ ] The patient sees exactly what the doctor sees
  - [ ] Patterns labelled unverified
- [ ] **E13-5 Share link** · P1 · Phase 2
  - Ask: Let the patient share the brief by link: it needs consent, it expires, it can be revoked, and every open is logged.
  - Owner: Hong Yi
  - Reviewer: Damien
  - Status: backlog
  - Depends on: E13-4 · Spec: schema 7
  - Note:
  - [ ] Requires sharing consent
  - [ ] Expiring random token stored hashed, revocable, every access logged
  - [ ] Opens read-only on a second device
- [ ] **E13-6 Brief screens in app** · P0 · Phase 2
  - Ask: Build the screens in the app to generate, view, add questions to, share and revoke the brief.
  - Owner: Hong Yi
  - Reviewer: Damien
  - Status: backlog
  - Depends on: E13-4 · Spec: flow J11
  - Note:
  - [ ] Generate, view, add own questions, share and revoke from the Me tab

## E14 Preventive care and scheduler (F13)

**In plain terms:** Reminders for recurring health checks and appointment planning.

- [ ] **E14-1 Preventive items and screen** · P1 · Phase 2 · NEEDS OK
  - Ask: Create the checklist of recurring checks (eye, foot, kidney, HbA1c, flu) with last-done and due status. The intervals are team-written configuration that needs a clinician's review and the owner's OK.
  - Owner: Damien
  - Status: backlog
  - Depends on: E1-3 · Spec: prd F13
  - Note:
  - [ ] Screening intervals are team-written config needing clinician review
  - [ ] Screen shows each item as ok, due soon, overdue or unknown
- [ ] **E14-2 Appointments and calendar file** · P1 · Phase 2
  - Ask: Let users suggest, plan and confirm an appointment and download a calendar file. Nothing is booked without confirmation. Google Calendar is a stretch.
  - Owner: Damien
  - Status: backlog
  - Depends on: E14-1 · Spec: prd F13
  - Note:
  - [ ] Suggest, plan and confirm an appointment
  - [ ] Nothing is booked without confirmation
  - [ ] Downloads an .ics file that opens in a calendar
  - [ ] (Google Calendar link is a stretch.)
- [ ] **E14-3 Auto-brief before appointment** · P1 · Phase 2
  - Ask: Automatically generate the doctor brief two days before a planned appointment and notify the user.
  - Owner: Damien
  - Status: backlog
  - Depends on: E14-2, E13-4 · Spec: prd F13
  - Note:
  - [ ] A brief is generated 48 hours before a planned appointment and the user is notified

## E15 Healthcare preparation (F14)

**In plain terms:** A running list of questions to ask the doctor.

- [ ] **E15-1 Doctor questions list** · P0 · Phase 1
  - Ask: Let users add a question for their doctor from anywhere (a chat refusal, an interaction message, a side-effect reason), edit the list, and feed it into the brief.
  - Owner: Damien
  - Status: backlog
  - Depends on: E1-3 · Spec: prd F14
  - Note:
  - [ ] Add a question from anywhere (chat refusal, clash sheet, side-effect reason)
  - [ ] List editable
  - [ ] Flows into brief section 12
- [ ] **E15-2 Question phrasing and routing** · P1 · Phase 2
  - Ask: Have the AI tidy the wording of a question and suggest who to ask (eye, foot, kidney, heart) without naming any diagnosis.
  - Owner: Damien
  - Status: backlog
  - Depends on: E15-1, E1-8 · Spec: prd F14
  - Note:
  - [ ] Model tidies wording
  - [ ] Routing table suggests who to ask (eye, foot, kidney, heart) without naming diagnoses

## E16 Companion chat and agent harness (F15)

**In plain terms:** The chat companion, the brain behind it, and the safety net around it.

_Guardrails live here._

- [ ] **E16-1 Agent graph, Memory Service and evidence packet** · P0 · Phase 1
  - Ask: Build the wiring of the chat: a pipeline of steps (check the message, route it, fetch the right memory, let a specialist answer, check the answer, save it). Also build the Memory Service, the only door to the user's data, which always works for the current user and returns where each fact came from. The AI answers only from a prepared 'evidence packet', never from guesswork, and the packet never contains names or identifiers.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E0-9 · Spec: architecture 5; memory 6-7
  - Note:
  - [ ] Graph with input guard, route, Memory Service, specialist, output guard, persist
  - [ ] Memory Service functions (get_context, get_timeline, get_entities, get_relationships, search_memories, propose_memory, supersede_memory) scope every call to the session user and return source ids, evidence status and confidence
  - [ ] Evidence packet built in the standard shape and the model answers from it only
  - [ ] Every step written to agent_runs and agent_steps; the packet never contains names or identifiers
- [ ] **E16-2 Guards and refusal templates** · P0 · Phase 1
  - Ask: Build the safety net around chat: detect messages asking to change medication, asking for a diagnosis, trying to trick the AI, or describing something urgent, and answer with approved fixed messages instead of AI text. Test with 40 prompts in four languages: none may leak medication advice.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E16-1 · Spec: rules 1
  - Note:
  - [ ] Medication-advice, diagnosis, injection and urgent inputs are caught
  - [ ] Approved templates returned instead of model text
  - [ ] Smoke set of 40 prompts (in 4 languages) passes: no medication advice leaks
- [ ] **E16-3 Chat UI** · P0 · Phase 1
  - Ask: Build the chat screen: message bubbles, a distinct look for the fixed safety messages, and an 'add to doctor questions' button on refusals.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E16-1, E0-2 · Spec: flow J12
  - Note:
  - [ ] Chat screen with bubbles, distinct style for guard templates, and 'add to doctor questions' on refusals
- [ ] **E16-4 Specialist wiring** · P1 · Phase 2
  - Ask: Connect the specialist helpers (medicine explainer, adherence, lifestyle, check-in, question helper) so chat can use them, each limited to its own allowed tools.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E16-1 · Spec: architecture 5.2
  - Note:
  - [ ] Explainer, adherence, lifestyle, check-in and question helper reachable from chat
  - [ ] Each has an allow-listed toolset only
- [ ] **E16-5 Episodic memory** · P1 · Phase 2
  - Ask: Make the chat remember: summarise each session and store it so next time it can recall context, such as 'last week you mentioned stomach upset'.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E16-1 · Spec: architecture 5.3
  - Note:
  - [ ] Chat sessions summarised and embedded
  - [ ] The next chat can recall context (for example last week's side effect)

- [ ] **E16-6 JEV typed decisions for routing and guards** · P0 · Phase 1
  - Ask: Use the fast yes/no decision layer (JEV) to choose the memory route and to double-check messages for medication advice, diagnosis or urgency. Rules always win; if JEV is unsure or down, take the cautious path. The 40-prompt test must pass with JEV on and off.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E0-12, E16-1 · Spec: memory 5
  - Note:
  - [ ] Memory route chosen with a choice question (semantic, temporal, entity, relationship)
  - [ ] Guard questions for medication advice, diagnosis and urgent wording use yes/no decisions on top of the rules; a rule that fires always wins
  - [ ] Confidence below the floor or a JEV outage takes the conservative path (refusal template, default route)
  - [ ] The 40-prompt smoke set passes with JEV on and with JEV off
## E17 Transparent memory and learning (F16)

**In plain terms:** Make what the app has learned visible and controllable by the user.

_Makes the learning visible._

- [ ] **E17-1 Memory store and lifecycle** · P0 · Phase 2
  - Ask: Build the place where learned facts are stored (for example 'walks after dinner') with a confidence, how well supported each is, and its version history. Facts move through proposed, active, superseded or rejected. A rejected fact is never suggested again, and nothing is ever called 'validated'.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E1-3 · Spec: schema 8; memory 8
  - Note:
  - [ ] memory_facts with confidence, evidence_status, evidence references and versions
  - [ ] Status changes (proposed, active, superseded, rejected) covered by state tests
  - [ ] Superseding links supersedes_id and never overwrites; rejected facts are never re-proposed
  - [ ] No fact is labelled validated anywhere in the data or the UI
- [ ] **E17-2 Nightly reflection agent** · P0 · Phase 2
  - Ask: Build the nightly 'reflection' job: an AI reviews the day and proposes facts about the person, always with evidence. On the demo patient it should propose at least five correct facts across food, medication, activity and sleep, and never one without evidence.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E17-1, E16-1, E1-9 · Spec: architecture 5.3
  - Note:
  - [ ] On the demo persona it proposes at least 5 correct facts across food, medication, activity and sleep, each with evidence
  - [ ] It never proposes a fact without evidence
- [ ] **E17-3 'What Smart Health has learned' screen** · P0 · Phase 2
  - Ask: Build the screen 'What Smart Health has learned about you': facts grouped by type with 'why I think this', and buttons to confirm, edit or delete them (all logged).
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E17-1, E0-2 · Spec: flow J13
  - Note:
  - [ ] Facts grouped by category with 'why I think this'
  - [ ] Confirm, edit and delete work and are logged
- [ ] **E17-4 Show the adaptation** · P0 · Phase 2
  - Ask: Build the 'week 1 versus week 8' view for the same person: how their baseline moved, when reminders now land, which facts were learned and which foods behave differently, drawing on every data type. This is your headline proof that the app learns.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E17-2, E12-2, E9-2 · Spec: prd 7
  - Note:
  - [ ] One screen or demo view comparing week 1 with week 8 for the same person: baseline shift, nudge timing, learned facts, food responses drawn from every data stream

- [ ] **E17-5 Memory candidate typing and supersession** · P1 · Phase 2
  - Ask: Make learning safer: classify each proposed fact, check it against the existing ones, and when a routine changes create a new version instead of overwriting. Low-confidence facts wait for the user.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E17-1, E0-12 · Spec: memory 8
  - Note:
  - [ ] Candidate fact type chosen with a choice decision; low confidence stores it as context, proposed
  - [ ] Memory Service validates the candidate (user owns sources, sources exist, threshold met, no conflict with an active fact)
  - [ ] A changed routine creates a new version and supersedes the old one
  - [ ] Contradiction check with a yes/no decision keeps both facts and asks the user (stretch)
## E18 Multilingual and TTS (F17)

**In plain terms:** Four languages and spoken audio.

- [ ] **E18-1 Language framework and strings** · P0 · Phase 2
  - Ask: Make the whole app available in English, Chinese, Malay and Tamil: all text comes from translation files, a check fails on any hard-coded text, and switching language changes every screen.
  - Owner: Joely
  - Status: backlog
  - Depends on: E0-2 · Spec: rules 5
  - Note:
  - [ ] English, Chinese, Malay, Tamil for all UI text
  - [ ] Lint fails on hard-coded strings
  - [ ] Language switch changes every screen
- [ ] **E18-2 Audio playback** · P1 · Phase 2
  - Ask: Add a 'Listen' button that reads explanations and reminders aloud, and hide it gracefully if the audio fails.
  - Owner: Joely
  - Status: backlog
  - Depends on: E4-2, E0-9 · Spec: prd F17
  - Note:
  - [ ] Listen button plays speech for explainers and reminders
  - [ ] Falls back to hiding the button if audio fails
- [ ] **E18-3 Translation review** · P1 · Phase 2
  - Ask: Get a native speaker to review the translated medicine explanations and safety messages and tick off a checklist, because a wrong translation here could mislead a patient.
  - Owner: Joely
  - Status: backlog
  - Depends on: E18-1 · Spec: prd F17
  - Note:
  - [ ] Native-speaker teammate or friend reviews the medication explainers and safety templates
  - [ ] Checklist signed off

## E19 Lifestyle timeline and day traces (F18)

**In plain terms:** Every kind of data on one timeline, and a finder for patterns.

_Multimodal fusion on one clock._

- [ ] **E19-1 Timeline view and API** · P0 · Phase 2
  - Ask: Build one combined timeline of meals, doses, workouts, sleep, symptoms, check-ins and urgent events on a single clock, with an API that returns a day in under half a second.
  - Owner: Joely
  - Status: backlog
  - Depends on: E1-9 · Spec: schema 9b
  - Note:
  - [ ] Timeline_events view merges meals, doses, workouts, sleep, symptoms, check-ins and urgent events on one clock
  - [ ] API returns a day in under 500 ms
- [ ] **E19-2 Day view screen** · P0 · Phase 2
  - Ask: Build the Day view: a glucose line with markers for meals, doses (taken, unconfirmed, missed), workouts and symptoms, with heart rate, steps and sleep underneath. Missing data shows as a gap, never a made-up line.
  - Owner: Joely
  - Status: backlog
  - Depends on: E19-1, E0-2 · Spec: prd F18
  - Note:
  - [ ] Glucose line with markers for meals, doses (taken, unconfirmed, missed), workouts and symptoms
  - [ ] Heart rate, steps and sleep bands underneath
  - [ ] Missing data shows as a gap, not a line
- [ ] **E19-3 Event windows and pattern candidates** · P0 · Phase 2
  - Ask: Build the pattern finder: take each meal, workout, dose or sleep and measure what happened to glucose afterwards. A pattern needs at least five matched pairs (tested: found with 5, ignored with 4) and is always worded 'associated with'.
  - Owner: Joely
  - Status: backlog
  - Depends on: E19-1, E8-2 · Spec: architecture 4.4b
  - Note:
  - [ ] Meal, workout, dose and sleep anchors produce outcomes
  - [ ] Unit test: an injected pattern is found with 5 or more pairs and ignored with 4
  - [ ] Wording says 'associated with'
- [ ] **E19-4 Brief day traces** · P0 · Phase 2
  - Ask: Add the best, worst and typical day to the doctor brief, chosen by fixed rules, each linking to its logs.
  - Owner: Joely
  - Status: backlog
  - Depends on: E19-3, E13-2 · Spec: prd F18
  - Note:
  - [ ] Brief shows best, worst and typical day chosen by fixed rules, each linking to its logs

## E20 Testing and validation (optional)

**In plain terms:** Extra tests and checks. Optional, but they catch problems before the demo.

_Optional epic. Safety-critical tests are inside their feature epics and are not optional._

- [ ] **E20-1 Red-team suite** · P1 · Phase 2
  - Ask: Build a bigger set of tricky test prompts (medication advice, tricks hidden in chat or label text, diagnosis requests, urgent wording) in four languages. All must pass, and the tests are never weakened to make them pass.
  - Owner: Hong Yi, Joely
  - Status: backlog
  - Depends on: E16-2 · Spec: rules 7
  - Note:
  - [ ] Extended set (medication advice, injection via chat and label text, diagnosis, urgent wording) in 4 languages. 100% pass
  - [ ] Never weakened to pass
- [ ] **E20-2 Engine unit tests** · P1 · Phase 2
  - Ask: Write tests for the calculation engines (baseline and momentum, food response, event windows, adherence) that cover edge cases like no data, exact boundaries and duplicates.
  - Owner: Hong Yi, Joely
  - Status: backlog
  - Depends on: E9-2, E8-2, E19-3, E5-4 · Spec: rules 7
  - Note:
  - [ ] Momentum, food response, event windows and adherence have edge-case tests (no data, boundaries, duplicates)
- [ ] **E20-3 Data validation checks** · P1 · Phase 2
  - Ask: Write automatic data checks: correct units and time zones, empty is never zero, simulated rows are flagged, and the disclosure list matches.
  - Owner: Hong Yi, Joely
  - Status: backlog
  - Depends on: E1-9 · Spec: schema 11
  - Note:
  - [ ] Automated checks: units, time zones, no zeros for missing, simulated rows flagged, disclosure list matches
- [ ] **E20-4 End-to-end demo rehearsal** · P1 · Phase 3
  - Ask: Run the full demo from start to finish, time it (6 minutes or less), and do it twice with nothing needing a fix.
  - Owner: Hong Yi, Joely
  - Status: backlog
  - Spec: flow 5
  - Note:
  - [ ] Script runs the full demo path
  - [ ] Timed at 6 minutes or less
  - [ ] Run twice with no fix needed
- [ ] **E20-5 Phone-size and accessibility pass** · P1 · Phase 3
  - Ask: Check every key screen on a phone-size screen at large text, in light and dark mode.
  - Owner: Hong Yi, Joely
  - Status: backlog
  - Spec: design 10
  - Note:
  - [ ] All key screens checked at phone size, 200% font, light and dark

## E21 Submission package

**In plain terms:** Everything the hackathon submission needs.

- [ ] **E21-1 Title, blurb and description** · P0 · Phase 3
  - Ask: Write the submission text: the project title, a blurb under 10 words, and a description covering the scenario, users, value, design and business value.
  - Owner: Team
  - Status: backlog
  - Spec: prd 11
  - Note:
  - [ ] Title, blurb under 10 words, description covering scenario, users, value, design and business value
- [ ] **E21-2 Architecture and trust-boundary diagram** · P0 · Phase 3
  - Ask: Draw one architecture diagram showing the trust boundaries (where data and AI calls cross) and the key trade-offs.
  - Owner: Team
  - Status: backlog
  - Spec: architecture 1
  - Note:
  - [ ] One diagram with the trust boundaries and the key trade-offs
- [ ] **E21-3 Build proof** · P0 · Phase 3
  - Ask: Collect at least three screenshots of your CodeBuddy or WorkBuddy work as proof the project was built with it.
  - Owner: Team
  - Status: backlog
  - Depends on: E0-10 · Spec: prd 11
  - Note:
  - [ ] At least 3 screenshots of CodeBuddy/WorkBuddy work in the submission
- [ ] **E21-4 Cover image** · P0 · Phase 3
  - Ask: Create the 16:9 cover image (380 by 216 pixels).
  - Owner: Team
  - Status: backlog
  - Depends on: E0-5 · Spec: prd 11
  - Note:
  - [ ] 16:9 image at 380x216
- [ ] **E21-5 Demo video (optional bonus)** · P1 · Phase 3
  - Ask: Optional bonus: record a 5 to 8 minute video covering the overview, the core features and how you built it.
  - Owner: Team
  - Status: backlog
  - Depends on: E20-4 · Spec: prd 11
  - Note:
  - [ ] 5 to 8 minutes: overview, core features, build reflection
- [ ] **E21-6 Public repo, README and demo instructions** · P0 · Phase 3
  - Ask: Make the repo ready to go public: no secrets or raw datasets in its history, and a README that gets someone running the demo in five commands on a fresh machine. A live URL is not planned.
  - Owner: Team
  - Status: backlog
  - Depends on: E0-6 · Spec: prd 11
  - Note:
  - [ ] Repo made public for the submission, with no secrets or raw datasets in its history
  - [ ] README runs the demo in 5 commands on a fresh machine
  - [ ] A live URL is optional and not planned: the demo runs locally
- [ ] **E21-7 Final rehearsal** · P0 · Phase 3
  - Ask: Do two clean run-throughs of the demo, presented by two different people.
  - Owner: Team
  - Status: backlog
  - Depends on: E20-4 · Spec: flow 5
  - Note:
  - [ ] Two clean run-throughs by different presenters

## E22 Integration checkpoints

**In plain terms:** Four gates that prove the separate parts work together.

_End-to-end runs that must pass before the next phase starts. This is how the parts link together._

- [ ] **CP0 Checkpoint 0: mockup and data ready** · P0 · Phase 0
  - Ask: First gate: prove the mockup walks the whole demo script, the importers load a participant into the database, the app can read from it, and the schema, demo data and design tokens are frozen.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: E0-5, E1-5, E0-6, E0-11 · Spec: backlog
  - Note:
  - [ ] Prototype walks the whole demo script with no dead ends
  - [ ] Importers load one participant into the database
  - [ ] A deployed page reads from the hosted database
  - [ ] Schema, demo data pack and design tokens are frozen
- [ ] **CP1 Checkpoint 1: thin vertical slice** · P0 · Phase 1
  - Ask: Second gate: prove a thin working slice end to end: open as the demo patient, mark a dose taken, log a glucose reading and a meal, replay a sensor sprint, scan and confirm a medicine, get the refusal message for 'can I skip metformin', and see the urgent screen for a 2.8 reading.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: CP0, E5-2, E7-2, E8-2, E3-5, E16-2, E11-3 · Spec: backlog
  - Note:
  - [ ] Open as demo patient, see doses on Today and tap Taken
  - [ ] Log a glucose reading and a meal and see them stored
  - [ ] Replay a CGM sprint and see food responses computed
  - [ ] Photograph a medication, review, confirm and see the dose schedule appear
  - [ ] Ask 'can I skip metformin' and get the refusal template
  - [ ] Replay a 2.8 mmol/L reading and the urgent screen opens
- [ ] **CP2 Checkpoint 2: all features and the brief** · P0 · Phase 2
  - Ask: Third gate: prove the whole demo script works with the real backend, including the generated brief with timeline, day traces and validator report, the learned-facts and week 1 versus week 8 view, and the share link opening on a second device.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: CP1, E13-4, E19-4, E17-4, E13-5 · Spec: backlog
  - Note:
  - [ ] Every step of the demo script in flow.md section 5 works with the real backend
  - [ ] Brief generated for the demo patient with prescription timeline, day traces and validator report
  - [ ] Learned facts and the week 1 versus week 8 view work
  - [ ] Share link opens on a second device
- [ ] **CP3 Checkpoint 3: submission ready** · P0 · Phase 3
  - Ask: Final gate: the submission package is complete and two clean rehearsals have been done by different presenters.
  - Owner: Hong Yi
  - Status: backlog
  - Depends on: CP2, E21-1, E21-2, E21-3, E21-4, E21-6, E21-7 · Spec: backlog
  - Note:
  - [ ] Submission package complete
  - [ ] Two clean rehearsals by different presenters
