# Joely: backlog

**Owner:** Joely (GitHub joelyhee) · **Role:** Data foundation, logging, clash checker, urgent alerts, languages and timeline.

You edit only this file. As you work: tick subtasks (`- [ ]` becomes `- [x]`), set **Status** (`backlog`, `in progress`, `in review`, `blocked`, `done`) and write a one-line **Note**. Then run `python scripts/update_tracker.py` to refresh the blocker check below and the central tracker ([SOT.md](SOT.md)). Never edit another person's file (one exception: a Reviewer sets the Status and Note of a task they review) or the generated parts of SOT.md.

If a task has a **Reviewer**, set `in review` when you finish; only the Reviewer (or the owner) moves it to `done`, after writing `Verified by <name> <date>` in the Note. **Needs first** are tasks that must be done before you can start; **Needed later** are tasks you will need partway through.

## Blocker check

<!-- BLOCKERS:START -->
Ready means everything under **Needs first** is done, so you can start. Blocked means you must wait.

**Ready now (4)**

- E1-2 Silver and reference tables: unblocks 39 other tasks.
- E1-1 Raw and Bronze: unblocks 28 other tasks.
- E11-1 Urgent alerts: unblocks 4 other tasks. Later you will need: E0-2 (Hong Yi, backlog), E1-4 (Joely, backlog).
- E21-2 Build proof and video: unblocks 1 other task. Later you will need: E20-2 (Joely, backlog).

**Blocked (10)**

- E1-4 Ingestion: waiting for E1-1 (Joely, backlog), E1-2 (Joely, backlog)
- E1-5 Analysis data and baseline model: waiting for E1-4 (Joely, backlog)
- E6-1 Clash checker: waiting for E3-2 (Hong Yi, backlog), E1-4 (Joely, backlog)
- E7-1 Quick logs: waiting for E0-2 (Hong Yi, backlog), E1-2 (Joely, backlog)
- E7-2 Meal logging with AI macros: waiting for E0-3 (Hong Yi, backlog), E1-1 (Joely, backlog), E1-2 (Joely, backlog), E1-4 (Joely, backlog)
- E7-3 Connected sources and log upkeep: waiting for E7-1 (Joely, backlog), E1-4 (Joely, backlog)
- E18-1 Languages, audio and translation review: waiting for E0-2 (Hong Yi, backlog)
- E19-1 Timeline and Day view: waiting for E1-3 (Hong Yi, backlog), E1-4 (Joely, backlog), E0-2 (Hong Yi, backlog)
- E19-2 Pattern finder and brief day traces: waiting for E19-1 (Joely, backlog), E8-1 (Damien, backlog)
- E20-2 Demo and device checks: waiting for CP1 (Hong Yi, backlog)

Done: 0 of 14 tasks.
<!-- BLOCKERS:END -->

## Tasks

### E1-1 Raw and Bronze · P0

- **Ask:** Raw and Bronze: write the download script for only the allowed datasets into data/raw, profile each one (who, how many, gaps, units), and create the Bronze raw-data log and storage layout so every original file is kept untouched.
- **Status:** backlog
- **Needs first:** none
- **Needed later:** none
- **Phase:** 0
- **Spec:** schema 9c; data plan
- **Detail:** [details/e1-data-foundation.md](details/e1-data-foundation.md)
- **Note:**
- **Success criteria:**
  - [ ] One script downloads only the allowed subsets into gitignored data/raw, logs sizes and checksums, and notes each licence
  - [ ] A short profile per dataset: people, rows, date span, gaps, units, sampling interval; it answers how many CGMacros diabetic participants have complete glucose and meals, and whether 250k Medicines really has an interactions column
  - [ ] ingestion_events table and the storage layout exist (private Supabase Storage bucket); originals are never overwritten
  - [ ] Every photo, image and import writes an ingestion_events row; deletion only on the user's request and logged

### E1-2 Silver and reference tables · P0

- **Ask:** Silver and reference tables: create every canonical and lookup table from schema.md with constraints and row-level security on, as migrations that apply to an empty Supabase database. Write the data dictionary. After E1, nobody creates a table.
- **Status:** backlog
- **Needs first:** none
- **Needed later:** none
- **Phase:** 0
- **Spec:** schema 2-9c
- **Detail:** [details/e1-data-foundation.md](details/e1-data-foundation.md)
- **Note:**
- **Success criteria:**
  - [ ] Migrations create every Silver and reference table in the layer map and apply cleanly to an empty database and roll back
  - [ ] Constraints, enums and unique keys are in; row-level security is on with no policies for every table
  - [ ] Every user-data field has a table, column, unit and source flag, written up in a data dictionary
  - [ ] `symptom_checkins.triggered_by_flag_id`, `appointments.brief_id` and `doctor_questions.brief_id` are plain nullable uuid columns with no foreign key (Hong Yi adds those in E1-3)
  - [ ] schema.md and the layer map match the migrated tables exactly

### E1-4 Ingestion · P0

- **Ask:** Ingestion: load every value the app will ever need, once: all allowed datasets, the medicine, interaction, food, check-up and routing reference data, the demo patient with a simulated 60-day history, devices and goals, the replay tool and the medicine knowledge index. After this, later tasks add no data.
- **Status:** backlog
- **Needs first:** E1-1, E1-2
- **Needed later:** E0-3
- **Phase:** 1
- **Spec:** data plan; schema 9b
- **Detail:** [details/e1-data-foundation.md](details/e1-data-foundation.md)
- **Note:**
- **Success criteria:**
  - [ ] Datasets: CGMacros, BIG IDEAs subset, Fitbit, NHANES and GlucoBench are imported into the Silver tables with units converted, dates shifted, UTC time and row counts matching the source (per-source detail in the details file)
  - [ ] Reference data: medicines with aliases and side effects, interaction data (checked first for an interactions column), foods with salt and sugar, preventive items, routing rules, population priors and data sources
  - [ ] Demo patient: one real diabetic participant's profile plus a repeatable simulator filling 60 days of doses, mood, blood pressure, workouts, symptoms and a rising morning-glucose trend; every simulated row is flagged
  - [ ] Setup data: devices and health goals seeded; the replay tool streams the demo data as if live and imports are safe to run twice
  - [ ] Medicine knowledge index: the medicine data is chunked and embedded (needs E0-3) and 20 test names retrieve the right drug
  - [ ] After this task no later task creates a table or loads reference data

### E1-5 Analysis data and baseline model · P1

- **Ask:** Prepare tidy analysis tables and train a simple baseline model of how much a meal raises glucose. Optional (P1).
- **Status:** backlog
- **Needs first:** E1-4
- **Needed later:** none
- **Phase:** 1
- **Spec:** data plan
- **Flag:** Owner was 'to decide' in your list. Provisionally Joely (data work); change if you prefer.
- **Note:**
- **Success criteria:**
  - [ ] Meal feature tables (macros, context and measured glucose response) split by participant with no leakage
  - [ ] Baseline model beats predicting the average on people it has not seen, with a short model card

### E6-1 Clash checker · P0

- **Ask:** Build the clash checker: look up each new medicine against the interaction data, say 'not checked' for anything unknown (never 'safe'), show the fixed warning wording, and seed one demo hit and one 'not checked' case.
- **Status:** backlog
- **Needs first:** E3-2, E1-4
- **Needed later:** E15-1
- **Phase:** 2
- **Spec:** prd F5
- **Note:**
- **Success criteria:**
  - [ ] Deterministic lookup per ingredient
  - [ ] A known pair produces a hit
  - [ ] An unmatched pair or any supplement/TCM item gives 'not checked', never 'safe'
  - [ ] Runs whenever a medication is added or changed
  - [ ] Fixed wording: 'Possible interaction between X and Y
  - [ ] Please check with your pharmacist or doctor before continuing.' Never says stop
  - [ ] Offers to add to doctor questions
  - [ ] Hits appear in the brief
  - [ ] The demo persona has one pair that hits and one supplement that shows 'not checked'

### E7-1 Quick logs · P0

- **Ask:** Build the quick logs: glucose entry (checked against the urgent thresholds), workouts, symptoms and the daily mood, stress and sleep check-in.
- **Status:** backlog
- **Needs first:** E0-2, E1-2
- **Needed later:** E11-1
- **Phase:** 1
- **Spec:** prd F6
- **Note:**
- **Success criteria:**
  - [ ] Entry in 3 taps or fewer, with context (fasting, pre, post, bedtime, random), stored in mmol/L
  - [ ] Every reading is checked by the threshold service
  - [ ] Three quick forms, each at most 15 seconds
  - [ ] Evening check-in captures mood, stress, sleep quality and energy on 1 to 5

### E7-2 Meal logging with AI macros · P0

- **Ask:** Build meal logging: a photo or text goes to the AI, which estimates the items and macros with a confidence; they show as 'Estimated' until the user confirms or edits. Keep the original and the AI's raw answer.
- **Status:** backlog
- **Needs first:** E0-3, E1-1, E1-2, E1-4
- **Needed later:** none
- **Phase:** 1
- **Spec:** prd F6; memory 9
- **Note:**
- **Success criteria:**
  - [ ] Photo or text description goes to the LLM, which returns the items and estimated kcal, carbs, protein, fat, fibre, sugar and sodium with a confidence per field
  - [ ] Estimates carry an 'Estimated' badge and can be edited or confirmed; confirmed values are stored as user-confirmed
  - [ ] Original photo and raw analysis are stored and never overwritten; re-running with a new prompt adds a new analysis
  - [ ] High-salt and high-sugar flags are computed in code from the stored values
  - [ ] Open Food Facts and NHANES values are used only as a sanity check that adds a 'check this' flag
  - [ ] A food the LLM cannot identify asks the user to type it in

### E7-3 Connected sources and log upkeep · P0

- **Ask:** Build the Connect sources screen, make imports safe to repeat, let users edit or delete their own logs and calculate how complete each data stream is.
- **Status:** backlog
- **Needs first:** E7-1, E1-4
- **Needed later:** none
- **Phase:** 1
- **Spec:** prd F6
- **Note:**
- **Success criteria:**
  - [ ] 'Connect sources' screen shows watch and CGM as connected and feeds data from the replay
  - [ ] Import is idempotent and shows last-synced time
  - [ ] Users can edit or delete their own logs, edits are recorded in the event log
  - [ ] Data completeness percent per stream is calculated for the brief

### E11-1 Urgent alerts · P0 · NEEDS OK

- **Ask:** Build urgent alerts: rules for dangerous readings tested at the boundaries, the full-screen urgent page with no AI that works offline, and a demo trigger. Thresholds need a clinician's review and your OK.
- **Status:** backlog
- **Needs first:** none
- **Needed later:** E0-2, E1-4
- **Phase:** 1
- **Spec:** prd F10
- **Note:**
- **Success criteria:**
  - [ ] Thresholds are team-written rules
  - [ ] Boundary tests at 2.9, 3.0, 3.8 and 3.9 mmol/L, repeated highs, and the symptom rule all pass
  - [ ] Config file marked 'clinical validation pending'
  - [ ] Full-screen instruction by tier with call buttons and hypo self-help steps
  - [ ] No LLM in the path
  - [ ] Works with the network off
  - [ ] Recheck timer prompts a new reading
  - [ ] Events logged
  - [ ] Replaying a 2.8 mmol/L reading opens the urgent screen within 2 seconds

### E18-1 Languages, audio and translation review · P0

- **Ask:** Make the app available in English, Chinese, Malay and Tamil, add the Listen button, and get a native speaker to check the medicine and safety wording.
- **Status:** backlog
- **Needs first:** E0-2
- **Needed later:** E0-3
- **Phase:** 2
- **Spec:** prd F17
- **Note:**
- **Success criteria:**
  - [ ] English, Chinese, Malay, Tamil for all UI text
  - [ ] Lint fails on hard-coded strings
  - [ ] Language switch changes every screen
  - [ ] Listen button plays speech for explainers and reminders
  - [ ] Falls back to hiding the button if audio fails
  - [ ] Native-speaker teammate or friend reviews the medication explainers and safety templates
  - [ ] Checklist signed off

### E19-1 Timeline and Day view · P0

- **Ask:** Build the combined timeline on one clock and the Day view: glucose with meals, doses, workouts and symptoms, heart rate, steps and sleep underneath, with gaps shown as gaps.
- **Status:** backlog
- **Needs first:** E1-3, E1-4, E0-2
- **Needed later:** none
- **Phase:** 2
- **Spec:** prd F18; schema 9b
- **Note:**
- **Success criteria:**
  - [ ] Timeline_events view merges meals, doses, workouts, sleep, symptoms, check-ins and urgent events on one clock
  - [ ] API returns a day in under 500 ms
  - [ ] Glucose line with markers for meals, doses (taken, unconfirmed, missed), workouts and symptoms
  - [ ] Heart rate, steps and sleep bands underneath
  - [ ] Missing data shows as a gap, not a line

### E19-2 Pattern finder and brief day traces · P0

- **Ask:** Build the pattern finder (at least five matched pairs, worded 'associated with') and add the best, worst and typical day to the doctor brief.
- **Status:** backlog
- **Needs first:** E19-1, E8-1
- **Needed later:** E13-1
- **Phase:** 2
- **Spec:** architecture 4.4b
- **Note:**
- **Success criteria:**
  - [ ] Meal, workout, dose and sleep anchors produce outcomes
  - [ ] Unit test: an injected pattern is found with 5 or more pairs and ignored with 4
  - [ ] Wording says 'associated with'
  - [ ] Brief shows best, worst and typical day chosen by fixed rules, each linking to its logs

### E20-2 Demo and device checks · P1

- **Ask:** Check the whole thing before the demo: a timed full run (6 minutes or less, twice), and a phone-size, large-text, light and dark check of every key screen. Optional but recommended.
- **Status:** backlog
- **Also:** Hong Yi
- **Needs first:** CP1
- **Needed later:** none
- **Phase:** 3
- **Spec:** flow 5; design 10
- **Note:**
- **Success criteria:**
  - [ ] Script runs the full demo path
  - [ ] Timed at 6 minutes or less
  - [ ] Run twice with no fix needed
  - [ ] All key screens checked at phone size, 200% font, light and dark

### E21-2 Build proof and video · P0

- **Ask:** Collect at least three build-proof screenshots (CodeBuddy or WorkBuddy) and record the optional 5 to 8 minute demo video.
- **Status:** backlog
- **Also:** the whole team
- **Needs first:** none
- **Needed later:** E20-2
- **Phase:** 3
- **Spec:** prd 11
- **Flag:** Team task. Joely is the lead here; everyone contributes. Change the lead if you prefer.
- **Note:**
- **Success criteria:**
  - [ ] At least 3 screenshots of CodeBuddy/WorkBuddy work in the submission
  - [ ] 5 to 8 minutes: overview, core features, build reflection
