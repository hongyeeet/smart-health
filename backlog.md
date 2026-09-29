# Smart Health backlog

Plan for the 3-person team to build the demo and submit by **16 Oct 2026**. Stories carry testable success criteria and link back to the specs ([prd.md](prd.md), [architecture.md](architecture.md), [flow.md](flow.md), [schema.md](schema.md), [design.md](design.md), [rules.md](rules.md)). This file is the plan; live status and owners are tracked as GitHub Issues once created.

## How to read this

- **Epics E2-E19 map one-to-one to features F1-F18** (E2 = F1 ... E19 = F18). E0 is the demo mockup and foundation, E1 is data readiness, E20 is optional testing and validation, E21 is the submission package.
- **Size:** S = about half a day, M = about a day, L = about two days of focused work.
- **Priority:** P0 = appears in the demo script, P1 = should have, P2 = stretch.
- **Milestone:** M0 to M3 (below). **Depends** lists story IDs that must be done first.
- **Demo-grade** means the feature works end to end on the seeded demo patient, and the safety-critical parts (urgent alerts, clash lookup, refusal of medication advice, brief validator) are done properly. Production hardening is out of scope.
- **[NEEDS OK]** marks stories that rely on something outside the cited data sources (for example clinical thresholds, guideline wording, photos). Decide before starting them.

## Capacity check

| | Days of work |
|---|---|
| All stories | 113 |
| P0 only | 86.5 |
| P1 | 25.5 |
| P2 | 1 |
| Optional epic E20 (included above) | 4 |

3 people from 29 Sep to 16 Oct is about 17 calendar days each, roughly 35 to 45 productive person-days assuming most weekdays and some weekends. Sizes are estimates for hand-written code; AI-assisted coding may cut them, but the P0 total is the number to watch. If P0 is more than the team can deliver, cut from the bottom of P1 first, then move P0 stories that are not in the demo script to P1.

**Warning: P0 alone is 86.5 days against roughly 40 available person-days (about 2.2x over).** M1 and M2 are the most overloaded (40.5 and 53.5 days planned for about 18 person-days each). Decide before assigning owners. Options, which can be combined:

1. **Rely on AI-assisted coding speed.** Only works if the team is about twice as fast as these sizes assume. Test it in M0 by timing E0-2 and E1-3.
2. **Two depths per feature.** *Live* = real logic and data (urgent alerts, clash lookup, refusal guard, momentum, food response, brief builder and validator). *Seeded* = the screen is real but reads seeded demo data with light logic (preventive care, healthcare prep, multilingual, nudge content, calendar). This keeps every feature in the demo while cutting cost.
3. **Cut to the demo-script essentials.** Move P0 stories that are not needed in flow.md section 5 down to P1.

## Milestones

| Milestone | Dates | Goal | Done when | Days planned |
|---|---|---|---|---|
| M0 | 29 Sep - 2 Oct | Mockup and data ready | The frozen prototype can be clicked through the whole demo script. Datasets downloaded and profiled, schema migrated, hosted app and database live, LLM decision made. | 12.5 |
| M1 | 3 - 8 Oct | Thin vertical slice | Real data in the real database: open as demo patient, Today with doses, log glucose and a meal, medication photo becomes a saved medication, CGM sprint replay fills in, urgent screen and refusal template work. | 40.5 |
| M2 | 9 - 14 Oct | All features and the brief | Full demo script F1-F18 end to end at demo-grade, including day view, learned facts, food responses, brief PDF and share link. | 53.5 |
| M3 | 15 - 16 Oct | Submission | Package complete and rehearsed. Submit on the 16th. | 6.5 |

## Integration checkpoints

A checkpoint is one end-to-end run that must pass before the next phase starts. This is how the parts are made to link.

**CP0 (2 Oct)**
- Prototype walks the whole demo script with no dead ends (E0-5).
- Importers can load one participant into the database (E1-5, E1-3).
- A deployed page reads from the hosted database (E0-6).
- Schema, demo data files and design tokens frozen (shared contracts below).

**CP1 (8 Oct)**
- Open as demo patient, see doses on Today, tap Taken (E0-7, E5-2).
- Log a glucose reading and a meal, see them stored (E7-1, E7-2).
- Replay a CGM sprint and see food responses computed (E8-1, E8-2).
- Photograph a medication, review, confirm, dose schedule appears (E3-*).
- Ask 'can I skip metformin?' and get the refusal template (E16-2). Replay 2.8 mmol/L and the urgent screen opens (E11-3).

**CP2 (14 Oct)**
- Every step of flow.md section 5 works with the real backend.
- Brief generated for the demo patient with prescription timeline, day traces and validator report (E13-*, E19-4).
- Learned facts and the week 1 vs week 8 view work (E17-*).
- Share link opens on a second device (E13-5).

**CP3 (16 Oct)**
- Submission package complete (E21-*).
- Two clean rehearsals (E21-7).

## Shared contracts

Each part is built against these, so work can run in parallel.

| ID | Contract | Where | Rule |
|---|---|---|---|
| C1 | Database schema | schema.md and the migrations (E1-3) | Frozen at CP0. Changes need all 3 owners to agree and schema.md updated in the same change. |
| C2 | Demo data pack | seed_demo.py output and table contents (E1-9) | Same seed gives same data. Frozen at CP0. Everyone builds against it. |
| C3 | API contract | OpenAPI generated from the backend, plus a mock server (E0-6) | The UI can be built against mock responses before the backend exists. |
| C4 | Event names | flow.md section 4 | Add to the catalogue before using a new event. |
| C5 | Design tokens | design.md and the component kit (E0-2) | No hard-coded colours or sizes. |
| C6 | Guardrail templates | Approved refusal and urgent templates (E16-2) | Every patient-facing AI output goes through them. |

## Suggested tracks

Owners are assigned per story in GitHub. These tracks are only a suggested split.

| Track | Focus | Epics |
|---|---|---|
| A | Data and intelligence | E1, E8, E9, E10, E11, E19 (engines) |
| B | App and experience | E0, E2, E5, E7, E12, E14, E15, E18, day view UI |
| C | Backend, AI and brief | E3, E4, E6, E13, E16, E17 |

## Epic map

| Epic | Name | Feature | Track | Stories | Days |
|---|---|---|---|---|---|
| E0 | Demo mockup and foundation | - | B | 10 | 8.5 |
| E1 | Data readiness | - | A | 12 | 18 |
| E2 | Onboarding | F1 | B | 4 | 4 |
| E3 | Prescription and medication capture | F2 | C | 6 | 7 |
| E4 | Medication explainer | F3 | C | 3 | 4 |
| E5 | Adherence engine | F4 | B | 5 | 5 |
| E6 | Clash checker | F5 | C | 4 | 2.5 |
| E7 | Health tracking and logging | F6 | B | 5 | 5.5 |
| E8 | CGM sprint and personal food response | F7 | A | 5 | 4.5 |
| E9 | Momentum engine | F8 | A | 4 | 4.5 |
| E10 | Targeted symptom check-ins | F9 | A | 3 | 2 |
| E11 | Urgent escalation | F10 | A | 3 | 2.5 |
| E12 | Lifestyle coach and adaptive nudges | F11 | B | 4 | 3.5 |
| E13 | Doctor brief | F12 | C | 6 | 9 |
| E14 | Preventive care and scheduler | F13 | B | 3 | 2.5 |
| E15 | Healthcare preparation | F14 | B | 2 | 1 |
| E16 | Companion chat and agent harness | F15 | C | 5 | 7 |
| E17 | Transparent memory and learning | F16 | C | 4 | 5 |
| E18 | Multilingual and TTS | F17 | B | 3 | 2 |
| E19 | Lifestyle timeline and day traces | F18 | A | 4 | 6 |
| E20 | Testing and validation (optional) | - | All | 5 | 4 |
| E21 | Submission package | - | All | 7 | 5 |

## E0 Demo mockup and foundation

Mockup first. Wireframes cover the app only; watch, CGM and camera are just data sources feeding it.

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E0-1 | Scope key pages and end-to-end flow | S | P0 | M0 | - | Working session with all 3. Output: list of at most 15 key pages (purpose, entry/exit, data shown) and one flow diagram. Every feature F1-F18 appears on at least one page. All 3 sign off. | flow.md 1-2 |
| E0-2 | Design tokens and component kit | M | P0 | M0 | - | Tokens from design.md in code. The 12 primitives (Button, Card, DoseCard, ReasonSheet, ReadingInput, ConfidenceChip, SourceTag, TrendCard, MemoryFactRow, UrgentScreen, ChatBubble, Banner) render in light and dark, at 100% and 200% font scale, contrast at least 4.5:1. | design.md 2-5 |
| E0-3 | Clickable prototype: core flow | L | P0 | M0 | E0-1, E0-2 | Phone-frame web prototype with fake data and no backend. Screens: onboarding, scan and review, Today, Log, Meds, Insights with day view, Brief, Memory, Urgent, Chat. Every step of the demo script is clickable start to finish with no dead ends. | flow.md 5 |
| E0-4 | Prototype: data-source simulator panel | M | P1 | M0 | E0-3 | Side panel with buttons that push a watch sync, a CGM reading, a meal and a medication photo into the prototype. App shows the imported state (for example 'Connected: watch, CGM'). Makes clear the outside sources only supply data. | prd F6, F7 |
| E0-5 | Prototype review and freeze | S | P0 | M0 | E0-3 | 30-minute walkthrough by all 3, change list applied, prototype v1 frozen and hosted at a public URL, open questions logged in the repo. | - |
| E0-6 | App skeleton and hosting | M | P0 | M0 | E0-1 | Mobile-first web app deployed to a free host, API deployed, hosted Postgres reachable. One page reads a database row through the API. .env.example complete. Setup takes at most 5 commands. | architecture.md |
| E0-7 | Demo session (replaces sign-in) | S | P1 | M1 | E0-6 | 'Start as demo patient' creates a session. Every API query is scoped by the session's user id. No password screens. | rules.md 8 |
| E0-8 | Event log writer | S | P0 | M1 | E0-6, E1-3 | Client logEvent() and server writer append to event_log. Client events are deduplicated by client_event_id. A test proves the per-user hash chain detects a tampered row. | flow.md 0; schema 9 |
| E0-9 | LLM and AI provider decision and gateway | M | P0 | M0 | E0-6 | Provider decision recorded in the repo. Gateway wraps chat, vision and embeddings with timeout, retry and logging. A smoke test gets a response from each. Keys live in env only. | architecture 2 |
| E0-10 | Build-proof habit | S | P1 | M0 | - | docs/proof/ folder. At least 3 screenshots of CodeBuddy/WorkBuddy work saved by CP1, then one per milestone. | prd 11 |

## E1 Data readiness

Data ready for analysis and model training, stored in the schema, with scaffolding fields for all user data.

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E1-1 | Data download scripts | M | P0 | M0 | - | One script fetches the cited subsets into gitignored data/raw: CGMacros, BIG IDEAs (3-5 participants: Dexcom, HR, EDA, TEMP, Food_Log, Demographics), NHANES files, Fitbit, 250k Medicines, Open Food Facts (SG/MY subset), Doctor Specialty, GlucoBench. Sizes and checksums logged. data/README lists each licence. | data plan |
| E1-2 | Profiling report per dataset | M | P0 | M0 | E1-1 | One short report per dataset (participants, rows, date span, missing values, units, sampling interval). Answers: how many CGMacros T2D participants have complete CGM and meals; whether 250k Medicines really has an interactions column; BIG IDEAs HbA1c range. | data plan |
| E1-3 | Canonical schema and migrations | L | P0 | M0 | - | Migrations create every table in schema.md sections 2-9b. They apply cleanly to an empty database and roll back. Constraints and enums present. Seeding one empty user succeeds. schema.md updated if anything changed. | schema.md |
| E1-4 | User-data scaffolding and data dictionary | M | P0 | M0 | E1-3 | Every field the app collects has a table, column, unit and source flag (manual, imported, simulated). docs/data_dictionary.md lists them. Covers profile, conditions, allergies, medications and ingredients, doses, glucose, meals, workouts, sleep, wearable samples, symptoms, mood, BP, labs, appointments, questions, memory. | schema.md |
| E1-5 | CGMacros importer | L | P0 | M1 | E1-2, E1-3 | Loads the chosen T2D participant(s): CGM to glucose_readings (mmol/L, quality flag, native interval), meals and macros, Fitbit HR/steps to health_samples, bio.csv to profile and lab_results. Dates shifted per person, stored in UTC. Row counts equal the source. 100 random glucose rows verified against the raw file. | data plan; schema |
| E1-6 | BIG IDEAs importer | M | P1 | M1 | E1-3 | Dexcom, HR, EDA, TEMP, food log and demographics loaded for the chosen participants. HR downsampled to 1 minute. Rows marked entry_source demo_dataset. Test compares counts to source. | data plan |
| E1-7 | Fitbit, NHANES and GlucoBench importers | M | P1 | M1 | E1-3 | Fitbit to samples and sleep. NHANES to population_priors (percentiles by age, sex, diabetes) plus a persona-sampling table. GlucoBench to a fixture table with insulin columns discarded. Each has a test. | data plan |
| E1-8 | Reference tables | L | P0 | M1 | E1-2, E1-3 | drug_reference, drug_aliases and drug_side_effects from 250k Medicines (diabetes, BP and lipid drugs first, at least 100 generics). foods from Open Food Facts (SG/MY) and NHANES dietary files with sodium and sugar. routing_rules from Doctor Specialty. data_sources filled. Searching 'metformin' returns its aliases. At least 90% of seeded foods have sodium or are flagged unknown. | schema 9b |
| E1-9 | Demo persona and 60-day simulator | L | P0 | M1 | E1-5, E1-8 | Persona is one CGMacros T2D participant. seed_demo.py builds 60 days: glucometer readings, doses with a weekend/evening miss pattern and one 4-day streak, mood/sleep/stress, BP, workouts, symptoms, and a rising fasting-glucose drift in the last 3 weeks. Every simulated row is flagged and a disclosure list is generated. Same seed gives identical data. | prd A8 |
| E1-10 | Analysis-ready feature tables | L | P1 | M1 | E1-5, E1-6 | meal_features (macros, context, response iAUC and peak rise) and a daily feature table. Train and test split by participant with no leakage. Documented. | - |
| E1-11 | Baseline model: meal to glucose response | L | P1 | M2 | E1-10 | Model card (data, split, metric). Beats predicting the mean on held-out participants. Artefact loadable by the API. Labelled as a population model. | - |
| E1-12 | Storage and replay | M | P0 | M1 | E1-5 | replay.py streams the demo data as if live (1x and accelerated). The import endpoint is idempotent by source plus external_id: running twice creates no duplicates. | architecture 4.3 |

## E2 Onboarding (F1)

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E2-1 | Form onboarding screens | L | P0 | M1 | E0-2, E1-3 | Steps: about you, diagnosis and HbA1c, conditions, allergies, family history, medications entry point, connected sources, reminder times. Finishes in 5 minutes or less on a phone-size screen. Each step saves. Leaving and returning resumes. Writes profile, conditions and allergies. | prd F1 |
| E2-2 | Eligibility and consent | S | P0 | M1 | E2-1 | Type 1, pregnancy and under-18 are blocked with a clear message. Consent rows stored. The user cannot continue without data-processing consent. | prd F1 |
| E2-3 | Chat onboarding | M | P1 | M2 | E16-1, E0-9 | Same fields collected conversationally, with a live 'captured so far' card and edit before saving. A scripted transcript produces the same records as the form. | prd F1 |
| E2-4 | Summary review and demo fast-path | S | P0 | M1 | E2-1, E0-7 | Editable summary screen. 'Start as demo patient' skips onboarding and loads the seeded persona. | flow J1 |

## E3 Prescription and medication capture (F2)

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E3-1 | Scan UI: capture and review | M | P0 | M1 | E0-2 | Camera/upload screen with framing tips. Review screen shows each field with a confidence chip. Fields below 0.85 must be tapped to confirm. Nothing saves until confirmed. | prd F2 |
| E3-2 | Extraction service | L | P0 | M1 | E0-9 | Vision model returns strict JSON with confidence and source text per field. Missing means null. Patient name and NRIC are dropped before storage. Handles prescription label, box, supplement, TCM and OTC. Invalid JSON retried once then fails safe. | prd F2; med capture pipeline |
| E3-3 | Name matching to drug database | M | P0 | M1 | E1-8 | Exact then fuzzy match to drug_aliases. Test set of 30 names passes. No match shows 'I'm not able to identify this medication, please check with your pharmacist' and offers manual entry. The model never chooses the database id. | prd F2 |
| E3-4 | Directions parser | M | P0 | M1 | - | Deterministic parser for at least 30 phrases ('twice daily after meals', 'at night', ...) gives times per day, timing and with-food. Unknown phrases turn into a question to the user. Verbatim text always stored. | prd F2 |
| E3-5 | Confirm and save transaction | M | P0 | M1 | E3-2, E3-3, E3-4, E1-3 | One transaction saves the medication, ingredients, dose schedule, clash check and event log. A forced failure rolls back everything. | schema 3 |
| E3-6 | Extraction test set and accuracy report | M | P1 | M2 | E3-2 | [NEEDS OK] No photo set exists in the cited data, so this needs photos the team takes. 30 or more photos across item types, ground truth per photo, per-field accuracy reported by item type, target at least 90% on name and strength for printed labels, and low confidence flagged for the rest. | data plan |

## E4 Medication explainer (F3)

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E4-1 | Drug knowledge index | M | P0 | M2 | E1-8 | 250k Medicines text chunked and embedded. Retrieval returns the correct drug for 20 test names. | prd F3 |
| E4-2 | Explainer generation with guard | L | P0 | M2 | E4-1, E0-9, E16-2 | Plain-language sections (what it is for, how you take it from your own label, common side effects, when to tell your doctor). Every sentence cites its source. Dose text comes only from the confirmed medication. 'Can I skip it?' triggers the refusal template. | prd F3 |
| E4-3 | Explainer screen, language and audio | M | P0 | M2 | E4-2, E18-1 | Medication detail screen with sources shown, four-language switch and a listen button. | flow J3 |

## E5 Adherence engine (F4)

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E5-1 | Dose schedule generator | M | P0 | M1 | E1-3 | Seven days of dose events generated per medication in the user's timezone. Re-running creates no duplicates. | schema 3 |
| E5-2 | Today screen and dose card | M | P0 | M1 | E0-2, E5-1 | Today lists due doses. Tapping Taken updates status and logs the event. Card shows scheduled, taken and unconfirmed states. | flow J4 |
| E5-3 | Reminder engine | M | P0 | M1 | E5-1, E0-8 | Reminder at the scheduled time, re-nudge after 60 minutes, unconfirmed when the window closes. Jobs are idempotent. Demo mode can trigger each step on demand. In-app notifications (no push needed). | prd F4 |
| E5-4 | Miss-reason flow and state machine | M | P0 | M1 | E5-3 | Next open shows one-tap reasons (forgot, side effects, ran out, felt fine, cost, other). Only valid transitions allowed, invalid ones raise an error, covered by tests. Side effects offers to add a symptom and a doctor question. | prd F4 |
| E5-5 | Meal-triggered prompt and refill forecast | M | P1 | M2 | E5-1, E7-2 | Logging a meal prompts the with-food medication. Refill date predicted from quantity and dose rate, with a reminder 7 days ahead. | prd F4 |

## E6 Clash checker (F5)

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E6-1 | Interaction data check and load | S | P0 | M1 | E1-8 | Report confirms whether 250k Medicines contains interactions, and how many usable pairs. If it does not, raise it as a decision and stop. interaction_rules loaded with source recorded. | prd A4 |
| E6-2 | Clash service | M | P0 | M2 | E6-1, E3-5 | Deterministic lookup per ingredient. A known pair produces a hit. An unmatched pair or any supplement/TCM item gives 'not checked', never 'safe'. Runs whenever a medication is added or changed. | prd F5 |
| E6-3 | Clash screen and question hand-off | S | P0 | M2 | E6-2, E15-1 | Fixed wording: 'Possible interaction between X and Y. Please check with your pharmacist or doctor before continuing.' Never says stop. Offers to add to doctor questions. Hits appear in the brief. | prd F5 |
| E6-4 | Seed a demo clash | S | P0 | M2 | E6-2 | The demo persona has one pair that hits and one supplement that shows 'not checked'. | flow 5 |

## E7 Health tracking and logging (F6)

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E7-1 | Glucose entry with threshold hook | M | P0 | M1 | E1-3, E11-1 | Entry in 3 taps or fewer, with context (fasting, pre, post, bedtime, random), stored in mmol/L. Every reading is checked by the threshold service. | prd F6 |
| E7-2 | Meal logging with nutrient flags | L | P0 | M1 | E1-8 | Search foods, choose portion, optional photo. Shows carbs, sugar, sodium with high-salt and high-sugar flags. Foods not found can be entered by hand. | prd F6 |
| E7-3 | Workout, symptom and mood check-in logs | M | P0 | M1 | E1-3 | Three quick forms, each at most 15 seconds. Evening check-in captures mood, stress, sleep quality and energy on 1 to 5. | prd F6 |
| E7-4 | Connect sources and import | M | P0 | M1 | E1-12 | 'Connect sources' screen shows watch and CGM as connected and feeds data from the replay. Import is idempotent and shows last-synced time. | prd F6 |
| E7-5 | Edit, delete and completeness | S | P1 | M2 | E7-1 | Users can edit or delete their own logs, edits are recorded in the event log. Data completeness percent per stream is calculated for the brief. | prd F6 |

## E8 CGM sprint and personal food response (F7)

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E8-1 | Sprint start, end and replay | M | P0 | M1 | E1-12 | Start and end a 14-day CGM sprint. Replay of the chosen CGMacros participant fills it. One open sprint per user. | prd F7 |
| E8-2 | Meal response calculator | M | P0 | M1 | E8-1 | For each meal, baseline glucose, peak rise and 2-hour incremental AUC. Matches a pandas reference on 20 meals. Windows with too little data are excluded. | architecture 6 |
| E8-3 | Food response leaderboard and note | M | P0 | M2 | E8-2 | Responses per food shown only when n is 2 or more, with n and range. Logging a known high-response food shows the factual note. Leaderboard in Insights and the brief. | prd F7 |
| E8-4 | Sprint summary metrics | S | P1 | M2 | E8-1 | Time in range, below range, above range, GMI and CV match a pandas reference. | schema 9b |
| E8-5 | Compared to typical (population model) | M | P2 | M2 | E1-11 | Screen shows the model's expected response next to the actual one, labelled as a population estimate. | - |

## E9 Momentum engine (F8)

Learns each person's own baseline across all data streams.

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E9-1 | Daily aggregates job | M | P0 | M2 | E1-9 | Nightly rollup of glucose, meals, activity, sleep, mood and adherence per day. Missing data stays empty, never zero. | schema 5 |
| E9-2 | Baseline, momentum and flags | L | P0 | M2 | E9-1 | 28-day median and MAD baseline, 7-day slope and change of slope. Unit tests on synthetic series: a known drift is flagged, plain noise is not, fewer than 10 days shows 'learning'. Each flag stores the numbers behind it. | architecture 6 |
| E9-3 | Insights screen | M | P0 | M2 | E9-2, E0-2 | Trend cards with baseline band and one plain-language line each. Period switch 7, 30, 90 days. | design 6-7 |
| E9-4 | Flag hand-offs | S | P0 | M2 | E9-2 | A flag creates a neutral patient note and an entry for the brief. | prd F8 |

## E10 Targeted symptom check-ins (F9)

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E10-1 | Question bank and planner | M | P0 | M2 | E9-2 | [NEEDS OK] Question wording is team-written and needs clinician review. Planner picks at most 1 check-in per day and 3 per week, and learns which the user answers. | prd F9 |
| E10-2 | Check-in UI and logging | S | P0 | M2 | E10-1 | One neutral question card. Answer or skip is stored as a symptom log. | flow J7 |
| E10-3 | Link to flag and brief | S | P1 | M2 | E10-2 | Answers show in the brief symptom section, linked to the pattern that triggered them. | prd F9 |

## E11 Urgent escalation (F10)

Rule-based, no LLM in the path.

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E11-1 | Threshold service and config | M | P0 | M1 | - | [NEEDS OK] Thresholds are team-written rules. Boundary tests at 2.9, 3.0, 3.8 and 3.9 mmol/L, repeated highs, and the symptom rule all pass. Config file marked 'clinical validation pending'. | prd F10 |
| E11-2 | Urgent screen and recheck | M | P0 | M1 | E11-1, E0-2 | Full-screen instruction by tier with call buttons and hypo self-help steps. No LLM in the path. Works with the network off. Recheck timer prompts a new reading. Events logged. | flow J8 |
| E11-3 | Demo trigger and replay of a low reading | S | P0 | M1 | E11-1, E1-12 | Replaying a 2.8 mmol/L reading opens the urgent screen within 2 seconds. | flow 5 |

## E12 Lifestyle coach and adaptive nudges (F11)

Adapts to what this user responds to.

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E12-1 | Nudge templates and triggers | M | P0 | M2 | E9-2 | [NEEDS OK] No guideline corpus is in the cited data, so nudges are reviewed team-written templates filled with the user's own data. Each nudge names the data it is based on. | prd F11 |
| E12-2 | Adaptive nudge policy | M | P0 | M2 | E12-1 | Chooses nudge type and time slot by observed act rate with 15% exploration, 3 per day cap, quiet hours. A simulation over the demo persona shifts toward the slots and types the user acts on. | architecture 5.4 |
| E12-3 | Salt and sugar flags with own-data swaps | M | P1 | M2 | E7-2, E8-3 | High-salt or high-sugar meals show a card suggesting a food that gave this user a gentler response. | prd F11 |
| E12-4 | Nudge cards UI | S | P0 | M2 | E12-1, E0-2 | Today shows at most one nudge card with 'Done' and 'Not for me' that feed the policy. | flow J9 |

## E13 Doctor brief (F12)

Headline feature.

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E13-1 | Brief data builder | L | P0 | M2 | E1-9, E9-1 | Builds all 14 sections deterministically. JSON validates against a schema. Every number traces to source rows. 90 days builds in under 30 seconds. | prd F12 |
| E13-2 | Brief charts | L | P0 | M2 | E13-1 | Prescription timeline with glucose overlay, glucose trend and time in range, nutrition, activity, sleep, food-response leaderboard. Readable in grayscale. | design 11 |
| E13-3 | Narrative with validator | L | P0 | M2 | E13-1, E0-9 | Model writes 'top 3 to discuss' and section summaries. Every sentence carries an evidence id. Validator rejects untagged sentences, unknown ids and numbers not in the data. Tested with deliberately bad drafts. | architecture 4.6 |
| E13-4 | HTML and PDF render with patient view | M | P0 | M2 | E13-2, E13-3 | Two-page A4 PDF plus in-app view. The patient sees exactly what the doctor sees. Patterns labelled unverified. | design 11 |
| E13-5 | Share link | M | P1 | M2 | E13-4 | Requires sharing consent. Expiring random token stored hashed, revocable, every access logged. Opens read-only on a second device. | schema 7 |
| E13-6 | Brief screens in app | M | P0 | M2 | E13-4 | Generate, view, add own questions, share and revoke from the Me tab. | flow J11 |

## E14 Preventive care and scheduler (F13)

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E14-1 | Preventive items and screen | M | P1 | M2 | E1-3 | [NEEDS OK] Screening intervals are team-written config needing clinician review. Screen shows each item as ok, due soon, overdue or unknown. | prd F13 |
| E14-2 | Appointments and calendar file | M | P1 | M2 | E14-1 | Suggest, plan and confirm an appointment. Nothing is booked without confirmation. Downloads an .ics file that opens in a calendar. (Google Calendar link is a stretch.) | prd F13 |
| E14-3 | Auto-brief before appointment | S | P1 | M2 | E14-2, E13-4 | A brief is generated 48 hours before a planned appointment and the user is notified. | prd F13 |

## E15 Healthcare preparation (F14)

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E15-1 | Doctor questions list | S | P0 | M1 | E1-3 | Add a question from anywhere (chat refusal, clash sheet, side-effect reason). List editable. Flows into brief section 12. | prd F14 |
| E15-2 | Question phrasing and routing | S | P1 | M2 | E15-1, E1-8 | Model tidies wording. Routing table suggests who to ask (eye, foot, kidney, heart) without naming diagnoses. | prd F14 |

## E16 Companion chat and agent harness (F15)

Guardrails live here.

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E16-1 | Agent graph, context builder and router | L | P0 | M1 | E0-9 | Graph with load context, input guard, router, specialist, output guard, persist. Every step written to agent_runs and agent_steps. Context strips name and identifiers. | architecture 5 |
| E16-2 | Guards and refusal templates | L | P0 | M1 | E16-1 | Medication-advice, diagnosis, injection and urgent inputs are caught. Approved templates returned instead of model text. Smoke set of 40 prompts (in 4 languages) passes: no medication advice leaks. | rules 1 |
| E16-3 | Chat UI | M | P0 | M1 | E16-1, E0-2 | Chat screen with bubbles, distinct style for guard templates, and 'add to doctor questions' on refusals. | flow J12 |
| E16-4 | Specialist wiring | M | P1 | M2 | E16-1 | Explainer, adherence, lifestyle, check-in and question helper reachable from chat. Each has an allow-listed toolset only. | architecture 5.2 |
| E16-5 | Episodic memory | M | P1 | M2 | E16-1 | Chat sessions summarised and embedded. The next chat can recall context (for example last week's side effect). | architecture 5.3 |

## E17 Transparent memory and learning (F16)

Makes the learning visible.

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E17-1 | Memory store and lifecycle | M | P0 | M2 | E1-3 | memory_facts with confidence, evidence and versions. Status changes covered by state tests. Rejected facts never re-proposed. | schema 8 |
| E17-2 | Nightly reflection agent | L | P0 | M2 | E17-1, E16-1, E1-9 | On the demo persona it proposes at least 5 correct facts across food, medication, activity and sleep, each with evidence. It never proposes a fact without evidence. | architecture 5.3 |
| E17-3 | 'What Smart Health has learned' screen | M | P0 | M2 | E17-1, E0-2 | Facts grouped by category with 'why I think this'. Confirm, edit and delete work and are logged. | flow J13 |
| E17-4 | Show the adaptation | M | P0 | M2 | E17-2, E12-2, E9-2 | One screen or demo view comparing week 1 with week 8 for the same person: baseline shift, nudge timing, learned facts, food responses drawn from every data stream. | prd 7 |

## E18 Multilingual and TTS (F17)

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E18-1 | Language framework and strings | M | P0 | M2 | E0-2 | English, Chinese, Malay, Tamil for all UI text. Lint fails on hard-coded strings. Language switch changes every screen. | rules 5 |
| E18-2 | Audio playback | S | P1 | M2 | E4-2, E0-9 | Listen button plays speech for explainers and reminders. Falls back to hiding the button if audio fails. | prd F17 |
| E18-3 | Translation review | S | P1 | M2 | E18-1 | Native-speaker teammate or friend reviews the medication explainers and safety templates. Checklist signed off. | prd F17 |

## E19 Lifestyle timeline and day traces (F18)

Multimodal fusion on one clock.

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E19-1 | Timeline view and API | M | P0 | M2 | E1-9 | timeline_events view merges meals, doses, workouts, sleep, symptoms, check-ins and urgent events on one clock. API returns a day in under 500 ms. | schema 9b |
| E19-2 | Day view screen | L | P0 | M2 | E19-1, E0-2 | Glucose line with markers for meals, doses (taken, unconfirmed, missed), workouts and symptoms. Heart rate, steps and sleep bands underneath. Missing data shows as a gap, not a line. | prd F18 |
| E19-3 | Event windows and pattern candidates | L | P0 | M2 | E19-1, E8-2 | Meal, workout, dose and sleep anchors produce outcomes. Unit test: an injected pattern is found with 5 or more pairs and ignored with 4. Wording says 'associated with'. | architecture 4.4b |
| E19-4 | Brief day traces | M | P0 | M2 | E19-3, E13-2 | Brief shows best, worst and typical day chosen by fixed rules, each linking to its logs. | prd F18 |

## E20 Testing and validation (optional)

Optional epic. Safety-critical tests are inside their feature epics and are not optional.

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E20-1 | Red-team suite | M | P1 | M2 | E16-2 | Extended set (medication advice, injection via chat and label text, diagnosis, urgent wording) in 4 languages. 100% pass. Never weakened to pass. | rules 7 |
| E20-2 | Engine unit tests | M | P1 | M2 | E9-2, E8-2, E19-3, E5-4 | Momentum, food response, event windows and adherence have edge-case tests (no data, boundaries, duplicates). | rules 7 |
| E20-3 | Data validation checks | S | P1 | M2 | E1-9 | Automated checks: units, time zones, no zeros for missing, simulated rows flagged, disclosure list matches. | schema 11 |
| E20-4 | End-to-end demo rehearsal | M | P1 | M3 | - | Script runs the full demo path. Timed at 6 minutes or less. Run twice with no fix needed. | flow 5 |
| E20-5 | Phone-size and accessibility pass | S | P1 | M3 | - | All key screens checked at phone size, 200% font, light and dark. | design 10 |

## E21 Submission package

| ID | Story | Size | Pri | Milestone | Depends | Success criteria | Spec |
|---|---|---|---|---|---|---|---|
| E21-1 | Title, blurb and description | S | P0 | M3 | - | Title, blurb under 10 words, description covering scenario, users, value, design and business value. | prd 11 |
| E21-2 | Architecture and trust-boundary diagram | M | P0 | M3 | - | One diagram with the trust boundaries and the key trade-offs. | architecture 1 |
| E21-3 | Build proof | S | P0 | M3 | E0-10 | At least 3 screenshots of CodeBuddy/WorkBuddy work in the submission. | prd 11 |
| E21-4 | Cover image | S | P0 | M3 | E0-5 | 16:9 image at 380x216. | prd 11 |
| E21-5 | Demo video (optional bonus) | M | P1 | M3 | E20-4 | 5 to 8 minutes: overview, core features, build reflection. | prd 11 |
| E21-6 | Public repo, README and live URL | M | P0 | M3 | E0-6 | Repo public, README runs the demo in 5 commands, hosted URL opens the demo patient. | prd 11 |
| E21-7 | Final rehearsal | S | P0 | M3 | E20-4 | Two clean run-throughs by different presenters. | flow 5 |
