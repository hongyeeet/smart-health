# Hong Yi: backlog

**Owner:** Hong Yi (GitHub hongyeeet) · **Role:** Project owner. Verifies UAT and promotes dev to uat and main.

You edit only this file. As you work: tick subtasks (`- [ ]` becomes `- [x]`), set **Status** (`backlog`, `in progress`, `in review`, `blocked`, `done`) and write a one-line **Note**. Then run `python scripts/update_tracker.py` to refresh the blocker check below and the central tracker ([SOT.md](SOT.md)). Never edit another person's file (one exception: a Reviewer sets the Status and Note of a task they review) or the generated parts of SOT.md.

If a task has a **Reviewer**, set `in review` when you finish; only the Reviewer (or the owner) moves it to `done`, after writing `Verified by <name> <date>` in the Note. **Needs first** are tasks that must be done before you can start; **Needed later** are tasks you will need partway through.

## Blocker check

<!-- BLOCKERS:START -->
Ready means everything under **Needs first** is done, so you can start. Blocked means you must wait.

**Ready now (1)**

- E1-3 Gold and operations tables and views: unblocks 23 other tasks.

**In progress or in review**

- E0-1 Hardcoded mockup (in progress)
- E0-2 App skeleton and design kit (in progress)

**Blocked (24)**

- E0-3 AI services: waiting for E0-2 (Hong Yi, in progress)
- E3-1 Scan and read: waiting for E0-2 (Hong Yi, in progress), E0-3 (Hong Yi, in progress)
- E3-2 Match, parse and save: waiting for E3-1 (Hong Yi, backlog)
- E3-3 Accuracy report: waiting for E3-1 (Hong Yi, backlog)
- E4-1 Medicine explainer: waiting for E0-3 (Hong Yi, in progress), E16-2 (Hong Yi, backlog)
- E5-1 Doses and reminders: waiting for E0-2 (Hong Yi, in progress)
- E5-2 Missed doses and refills: waiting for E5-1 (Hong Yi, backlog)
- E9-1 Daily totals, baseline and flags: waiting for E1-3 (Hong Yi, backlog)
- E9-2 Insights screen: waiting for E9-1 (Hong Yi, backlog), E0-2 (Hong Yi, in progress)
- E13-1 Brief data and charts: waiting for E9-1 (Hong Yi, backlog)
- E13-2 Narrative and PDF: waiting for E13-1 (Hong Yi, backlog), E0-3 (Hong Yi, in progress)
- E13-3 Brief screens and sharing: waiting for E13-2 (Hong Yi, backlog)
- E16-1 Chat pipeline and Memory Service: waiting for E0-3 (Hong Yi, in progress), E1-3 (Hong Yi, backlog)
- E16-2 Safety net and JEV decisions: waiting for E16-1 (Hong Yi, backlog), E0-3 (Hong Yi, in progress)
- E16-3 Chat screen, helpers and chat memory: waiting for E16-1 (Hong Yi, backlog), E0-2 (Hong Yi, in progress)
- E17-1 Memory and nightly reflection: waiting for E1-3 (Hong Yi, backlog), E16-1 (Hong Yi, backlog)
- E17-2 What it learned screen: waiting for E17-1 (Hong Yi, backlog), E0-2 (Hong Yi, in progress)
- E17-3 Week 1 versus week 8: waiting for E17-1 (Hong Yi, backlog), E9-1 (Hong Yi, backlog)
- E20-1 Safety and engine tests: waiting for E16-2 (Hong Yi, backlog), E9-1 (Hong Yi, backlog), E8-1 (Damien, backlog)
- E21-3 Public-ready repo and rehearsals: waiting for E0-2 (Hong Yi, in progress)
- CP0 Gate 0: mockup and data ready: waiting for E0-1 (Hong Yi, in progress), E0-2 (Hong Yi, in progress)
- CP1 Gate 1: thin working slice: waiting for CP0 (Hong Yi, backlog), E3-2 (Hong Yi, backlog), E5-1 (Hong Yi, backlog), E7-2 (Joely, backlog), E8-1 (Damien, backlog), E11-1 (Joely, backlog), E16-2 (Hong Yi, backlog)
- CP2 Gate 2: all features and the brief: waiting for CP1 (Hong Yi, backlog), E13-3 (Hong Yi, backlog), E17-3 (Hong Yi, backlog), E19-2 (Joely, backlog)
- CP3 Gate 3: submission ready: waiting for CP2 (Hong Yi, backlog), E21-1 (Damien, backlog), E21-2 (Joely, backlog), E21-3 (Hong Yi, backlog)

Done: 0 of 27 tasks.
<!-- BLOCKERS:END -->

## Tasks

### E0-1 Hardcoded mockup · P0

- **Ask:** Produce the hardcoded mockup of the whole app: visuals only, with fixed fake data, no logic and no backend. It is the agreed picture of what we are building. Use the Claude Design prompt, review it with the team, then freeze it and share the link.
- **Status:** in progress
- **Needs first:** none
- **Needed later:** none
- **Phase:** 0
- **Spec:** flow 5; design
- **Detail:** [docs/mockup/mockup-prompt.md](../mockup/mockup-prompt.md)
- **Note:** Built as the real web app in apps/web (D-028), not a separate mockup. Screens, demo data and click paths done; the Demo panel stays until the owner has vetted it, then it is removed (D-030). Team walkthrough, freeze and share link still to do.
- **Success criteria:**
  - [x] Mockup generated from the prompt covers every feature F1 to F18 on at least one screen, with the demo patient's numbers used consistently
  - [ ] Everything is hardcoded visuals: no logic, no backend, no simulator panel
  - [ ] Team walkthrough done, changes applied, version 1 frozen and shared as a link

### E0-2 App skeleton and design kit · P0

- **Ask:** Get the empty app running: the web app and API start locally with one command and connect to Supabase, a 'Start as demo patient' button, the activity-log writer, and the reusable design blocks for the real screens. Everything else is built on this.
- **Status:** in progress
- **Needs first:** none
- **Needed later:** E1-3
- **Phase:** 0
- **Spec:** architecture; design 2-5
- **Flag:** Missing from your pasted list; kept because most tasks depend on it. Confirm it stays with Hong Yi.
- **Note:** Front end skeleton, design tokens and UI kit done in apps/web. Still to do: the API, Supabase connection, row-level security, demo-patient session, event writer and .env.example.
- **Success criteria:**
  - [ ] Web app and API start locally with one command per machine
  - [ ] Supabase connection works (project renamed to smart-health, details shared privately in .env, never committed) and one page reads a database row through the API
  - [ ] Row-level security is on with no policies, and only the backend connects
  - [ ] 'Start as demo patient' creates a session and every query is scoped to that user; no passwords
  - [ ] Activity-log writer appends events with duplicate protection, and a test proves a tampered entry is detected (needs the event_log table from E1-3)
  - [x] Design tokens and the reusable UI blocks (buttons, cards, dose card, chat bubble and so on) work in light and dark mode and at large text sizes
  - [ ] .env.example is complete and setup takes at most five commands

### E0-3 AI services · P0

- **Ask:** Choose and wire the AI: the provider for chat, photo reading and embeddings, and how the fast yes/no layer (JEV) runs, all behind one gateway so the rest of the app never calls AI directly. The provider and model choices are written in docs/specs/ai-models.md.
- **Status:** in progress
- **Needs first:** E0-2
- **Needed later:** none
- **Phase:** 0
- **Spec:** architecture 2; memory 5
- **Flag:** Missing from your pasted list; kept because chat, scanning, meal logging and the brief depend on it. Confirm it stays with Hong Yi.
- **Note:** Provider and model decision written in docs/specs/ai-models.md (D-047). Still to confirm: the JEV deployment, Vertex model IDs and region, and Malay and Tamil on ElevenLabs. The gateway and smoke test are not built.
- **Success criteria:**
  - [x] Provider decision recorded in the repo (chat, vision, embeddings)
  - [ ] JEV option chosen (the TypeSafe JEV model: hosted or self-hosted) and the data-handling note recorded
  - [ ] One gateway keeps the OpenJev request and response shape and returns probability and confidence; keys live only in settings
  - [ ] Smoke test gets an answer from each kind of call; switching JEV off sends every decision down the conservative path

### E1-3 Gold and operations tables and views · P0

- **Ask:** Gold and operations tables and views: create all derived and memory tables (aggregates, baselines, flags, patterns, memory facts, briefs and so on), the four views, and the agent, guard, chat and event-log tables, so later tasks only read and write rows. It needs the Silver tables first because they link to them.
- **Status:** backlog
- **Needs first:** E1-2
- **Needed later:** none
- **Phase:** 0
- **Spec:** schema 5, 7, 8, 9, 9c
- **Detail:** [details/e1-data-foundation.md](details/e1-data-foundation.md)
- **Note:**
- **Success criteria:**
  - [ ] Migrations create every Gold and operations table in the layer map and apply cleanly on top of the Silver tables
  - [ ] Views health_state, trends, adherence_summary, insight_context and timeline_events exist with calculation version, evidence window, freshness and quality status
  - [ ] event_log is append-only for the app role
  - [ ] The three foreign keys from Silver up to Gold (symptom_checkins to clinical_flags, appointments and doctor_questions to briefs) are added once the Gold tables exist
  - [ ] Row-level security is on with no policies for every table; no table or view uses a gold., silver. or bronze. prefix

### E3-1 Scan and read · P0

- **Ask:** Build the medicine scan: the scan screen with a confidence review, and the service that reads the label photo with the vision AI into structured fields, never guessing and never keeping names or ID numbers.
- **Status:** backlog
- **Needs first:** E0-2, E0-3
- **Needed later:** none
- **Phase:** 1
- **Spec:** prd F2
- **Note:**
- **Success criteria:**
  - [ ] Camera/upload screen with framing tips
  - [ ] Review screen shows each field with a confidence chip
  - [ ] Fields below 0.85 must be tapped to confirm
  - [ ] Nothing saves until confirmed
  - [ ] Vision model returns strict JSON with confidence and source text per field
  - [ ] Missing means null
  - [ ] Patient name and NRIC are dropped before storage
  - [ ] Handles prescription label, box, supplement, TCM and OTC
  - [ ] Invalid JSON retried once then fails safe

### E3-2 Match, parse and save · P0

- **Ask:** Turn the scan into a saved medicine: match the name to the drug list (or say 'not able to identify'), parse the directions in plain code, and save the medicine, ingredients, dose schedule and clash check in one go or not at all.
- **Status:** backlog
- **Needs first:** E3-1, E1-2, E1-4
- **Needed later:** none
- **Phase:** 1
- **Spec:** schema 3
- **Note:**
- **Success criteria:**
  - [ ] Exact then fuzzy match to drug_aliases
  - [ ] Test set of 30 names passes
  - [ ] No match shows 'I'm not able to identify this medication, please check with your pharmacist' and offers manual entry
  - [ ] The model never chooses the database id
  - [ ] Deterministic parser for at least 30 phrases ('twice daily after meals', 'at night', ...) gives times per day, timing and with-food
  - [ ] Unknown phrases turn into a question to the user
  - [ ] Verbatim text always stored
  - [ ] One transaction saves the medication, ingredients, dose schedule, clash check and event log
  - [ ] A forced failure rolls back everything

### E3-3 Accuracy report · P1 · NEEDS OK

- **Ask:** Measure scanner accuracy on 30 or more photos you take yourselves, by item type. Needs your OK (outside the allowed datasets). Optional (P1).
- **Status:** backlog
- **Needs first:** E3-1
- **Needed later:** none
- **Phase:** 2
- **Spec:** data plan
- **Note:**
- **Success criteria:**
  - [ ] No photo set exists in the cited data, so this needs photos the team takes. 30 or more photos across item types, ground truth per photo, per-field accuracy reported by item type, target at least 90% on name and strength for printed labels, and low confidence flagged for the rest

### E4-1 Medicine explainer · P0

- **Ask:** Build the medicine explainer: plain-language explanations with sources, the user's own dose taken only from their confirmed label, a refusal for 'can I skip it', and a screen with four languages and a listen button. Damien reviews it.
- **Status:** backlog
- **Reviewer:** Damien
- **Needs first:** E0-3, E1-4, E16-2
- **Needed later:** E18-1
- **Phase:** 2
- **Spec:** prd F3
- **Note:**
- **Success criteria:**
  - [ ] Plain-language sections (what it is for, how you take it from your own label, common side effects, when to tell your doctor)
  - [ ] Every sentence cites its source
  - [ ] Dose text comes only from the confirmed medication
  - [ ] 'Can I skip it?' triggers the refusal template
  - [ ] Medication detail screen with sources shown, four-language switch and a listen button

### E5-1 Doses and reminders · P0

- **Ask:** Build the dose loop: generate the next 7 days of dose slots, the Today screen with a 'Taken' button, and reminders that mark a dose 'unconfirmed' when its window closes.
- **Status:** backlog
- **Needs first:** E0-2, E1-2
- **Needed later:** none
- **Phase:** 1
- **Spec:** prd F4
- **Note:**
- **Success criteria:**
  - [ ] Seven days of dose events generated per medication in the user's timezone
  - [ ] Re-running creates no duplicates
  - [ ] Today lists due doses
  - [ ] Tapping Taken updates status and logs the event
  - [ ] Card shows scheduled, taken and unconfirmed states
  - [ ] Reminder at the scheduled time, re-nudge after 60 minutes, unconfirmed when the window closes
  - [ ] Jobs are idempotent
  - [ ] Demo mode can trigger each step on demand
  - [ ] In-app notifications (no push needed)

### E5-2 Missed doses and refills · P0

- **Ask:** Handle missed doses: ask why with one tap, enforce the allowed status changes, prompt the with-food medicine at meals and predict refills. The meal prompt and refill are optional (P1).
- **Status:** backlog
- **Needs first:** E5-1
- **Needed later:** E7-2
- **Phase:** 1
- **Spec:** prd F4
- **Note:**
- **Success criteria:**
  - [ ] Next open shows one-tap reasons (forgot, side effects, ran out, felt fine, cost, other)
  - [ ] Only valid transitions allowed, invalid ones raise an error, covered by tests
  - [ ] Side effects offers to add a symptom and a doctor question
  - [ ] Logging a meal prompts the with-food medication
  - [ ] Refill date predicted from quantity and dose rate, with a reminder 7 days ahead

### E9-1 Daily totals, baseline and flags · P0

- **Ask:** Build the 'your own normal' engine: nightly daily totals, a 28-day baseline, the 7-day trend and flags when the person drifts, with the numbers behind each flag and neutral notes for the patient and the brief.
- **Status:** backlog
- **Needs first:** E1-3, E1-4
- **Needed later:** none
- **Phase:** 2
- **Spec:** architecture 6
- **Note:**
- **Success criteria:**
  - [ ] Nightly rollup of glucose, meals, activity, sleep, mood and adherence per day
  - [ ] Missing data stays empty, never zero
  - [ ] 28-day median and MAD baseline, 7-day slope and change of slope
  - [ ] Unit tests on synthetic series: a known drift is flagged, plain noise is not, fewer than 10 days shows 'learning'
  - [ ] Each flag stores the numbers behind it
  - [ ] A flag creates a neutral patient note and an entry for the brief

### E9-2 Insights screen · P0

- **Ask:** Build the Insights screen: trend cards with the personal baseline band and a one-line summary, with a 7, 30 and 90 day switch.
- **Status:** backlog
- **Needs first:** E9-1, E0-2
- **Needed later:** none
- **Phase:** 2
- **Spec:** design 6-7
- **Note:**
- **Success criteria:**
  - [ ] Trend cards with baseline band and one plain-language line each
  - [ ] Period switch 7, 30, 90 days

### E13-1 Brief data and charts · P0

- **Ask:** Build the doctor brief's data and charts: gather all 14 sections from the data with every number traceable, then draw the prescription timeline, glucose, nutrition, activity and sleep charts. Damien reviews it.
- **Status:** backlog
- **Reviewer:** Damien
- **Needs first:** E1-4, E9-1
- **Needed later:** none
- **Phase:** 2
- **Spec:** prd F12; design 11
- **Note:**
- **Success criteria:**
  - [ ] Builds all 14 sections deterministically
  - [ ] JSON validates against a schema
  - [ ] Every number traces to source rows. 90 days builds in under 30 seconds
  - [ ] Prescription timeline with glucose overlay, glucose trend and time in range, nutrition, activity, sleep, food-response leaderboard
  - [ ] Readable in grayscale

### E13-2 Narrative and PDF · P0

- **Ask:** Write the brief narrative and PDF: the AI writes sentences that each need an evidence ID, a validator rejects the rest, and the brief renders as a two-page A4 PDF the patient also sees. Damien reviews it.
- **Status:** backlog
- **Reviewer:** Damien
- **Needs first:** E13-1, E0-3
- **Needed later:** none
- **Phase:** 2
- **Spec:** architecture 4.6
- **Note:**
- **Success criteria:**
  - [ ] Model writes 'top 3 to discuss' and section summaries
  - [ ] Every sentence carries an evidence id
  - [ ] Validator rejects untagged sentences, unknown ids and numbers not in the data
  - [ ] Tested with deliberately bad drafts
  - [ ] Two-page A4 PDF plus in-app view
  - [ ] The patient sees exactly what the doctor sees
  - [ ] Patterns labelled unverified

### E13-3 Brief screens and sharing · P0

- **Ask:** Build the brief screens in the app (generate, view, add questions) and the share link with consent, expiry, revoke and logging (the share link is P1). Damien reviews it.
- **Status:** backlog
- **Reviewer:** Damien
- **Needs first:** E13-2
- **Needed later:** none
- **Phase:** 2
- **Spec:** flow J11
- **Note:**
- **Success criteria:**
  - [ ] Requires sharing consent
  - [ ] Expiring random token stored hashed, revocable, every access logged
  - [ ] Opens read-only on a second device
  - [ ] Generate, view, add own questions, share and revoke from the Me tab

### E16-1 Chat pipeline and Memory Service · P0

- **Ask:** Build the chat pipeline and the Memory Service: the steps every message goes through, and the single door to a user's data that returns where each fact came from. The AI answers only from a prepared evidence packet.
- **Status:** backlog
- **Needs first:** E0-3, E1-2, E1-3
- **Needed later:** none
- **Phase:** 1
- **Spec:** architecture 5; memory 6-7
- **Note:**
- **Success criteria:**
  - [ ] Graph with input guard, route, Memory Service, specialist, output guard, persist
  - [ ] Memory Service functions (get_context, get_timeline, get_entities, get_relationships, search_memories, propose_memory, supersede_memory) scope every call to the session user and return source ids, evidence status and confidence
  - [ ] Evidence packet built in the standard shape and the model answers from it only
  - [ ] Every step written to agent_runs and agent_steps; the packet never contains names or identifiers

### E16-2 Safety net and JEV decisions · P0

- **Ask:** Build chat's safety net: approved fixed replies for medication changes, diagnosis, tricks and urgent wording, tested on 40 prompts in four languages, plus JEV yes/no checks as a second opinion that falls back to caution.
- **Status:** backlog
- **Needs first:** E16-1, E0-3
- **Needed later:** none
- **Phase:** 1
- **Spec:** rules 1; memory 5
- **Note:**
- **Success criteria:**
  - [ ] Medication-advice, diagnosis, injection and urgent inputs are caught
  - [ ] Approved templates returned instead of model text
  - [ ] Smoke set of 40 prompts (in 4 languages) passes: no medication advice leaks
  - [ ] Memory route chosen with a choice question (semantic, temporal, entity, relationship)
  - [ ] Guard questions for medication advice, diagnosis and urgent wording use yes/no decisions on top of the rules; a rule that fires always wins
  - [ ] Confidence below the floor or a JEV outage takes the conservative path (refusal template, default route)
  - [ ] The 40-prompt smoke set passes with JEV on and with JEV off

### E16-3 Chat screen, helpers and chat memory · P0

- **Ask:** Build the chat screen with a distinct look for safety messages, connect the specialist helpers (explainer, adherence, lifestyle, check-in, question helper), and make chat remember past sessions.
- **Status:** backlog
- **Needs first:** E16-1, E0-2
- **Needed later:** none
- **Phase:** 1
- **Spec:** flow J12; architecture 5.2
- **Note:**
- **Success criteria:**
  - [ ] Chat screen with bubbles, distinct style for guard templates, and 'add to doctor questions' on refusals
  - [ ] Explainer, adherence, lifestyle, check-in and question helper reachable from chat
  - [ ] Each has an allow-listed toolset only
  - [ ] Chat sessions summarised and embedded
  - [ ] The next chat can recall context (for example last week's side effect)

### E17-1 Memory and nightly reflection · P0

- **Ask:** Build memory and the nightly reflection: where learned facts are stored with confidence and versions, and the nightly AI job that proposes facts with evidence (at least five correct facts on the demo patient), with safe versioning.
- **Status:** backlog
- **Needs first:** E1-3, E1-4, E16-1
- **Needed later:** none
- **Phase:** 2
- **Spec:** schema 8; memory 8
- **Note:**
- **Success criteria:**
  - [ ] memory_facts with confidence, evidence_status, evidence references and versions
  - [ ] Status changes (proposed, active, superseded, rejected) covered by state tests
  - [ ] Superseding links supersedes_id and never overwrites; rejected facts are never re-proposed
  - [ ] No fact is labelled validated anywhere in the data or the UI
  - [ ] On the demo persona it proposes at least 5 correct facts across food, medication, activity and sleep, each with evidence
  - [ ] It never proposes a fact without evidence
  - [ ] Candidate fact type chosen with a choice decision; low confidence stores it as context, proposed
  - [ ] Memory Service validates the candidate (user owns sources, sources exist, threshold met, no conflict with an active fact)
  - [ ] A changed routine creates a new version and supersedes the old one
  - [ ] Contradiction check with a yes/no decision keeps both facts and asks the user (stretch)

### E17-2 What it learned screen · P0

- **Ask:** Build the 'What Smart Health has learned about you' screen: facts grouped by type with 'why I think this', and buttons to confirm, edit or delete.
- **Status:** backlog
- **Needs first:** E17-1, E0-2
- **Needed later:** none
- **Phase:** 2
- **Spec:** flow J13
- **Note:**
- **Success criteria:**
  - [ ] Facts grouped by category with 'why I think this'
  - [ ] Confirm, edit and delete work and are logged

### E17-3 Week 1 versus week 8 · P0

- **Ask:** Build the week 1 versus week 8 view that shows the same person's baseline, reminder times, learned facts and food responses changing, drawing on every data type: your headline proof that it learns.
- **Status:** backlog
- **Needs first:** E17-1, E9-1
- **Needed later:** E12-1
- **Phase:** 2
- **Spec:** prd 7
- **Note:**
- **Success criteria:**
  - [ ] One screen or demo view comparing week 1 with week 8 for the same person: baseline shift, nudge timing, learned facts, food responses drawn from every data stream

### E20-1 Safety and engine tests · P1

- **Ask:** Write the safety and engine tests: a bigger tricky prompt set in four languages, edge-case tests for the calculation engines, and automatic data checks. Optional but recommended.
- **Status:** backlog
- **Also:** Joely
- **Needs first:** E16-2, E9-1, E8-1
- **Needed later:** E19-2, E5-1
- **Phase:** 2
- **Spec:** rules 7
- **Flag:** Your list said Hong Yi and Joely for E20. Hong Yi leads this one; Joely leads E20-2.
- **Note:**
- **Success criteria:**
  - [ ] Extended set (medication advice, injection via chat and label text, diagnosis, urgent wording) in 4 languages. 100% pass
  - [ ] Never weakened to pass
  - [ ] Momentum, food response, event windows and adherence have edge-case tests (no data, boundaries, duplicates)
  - [ ] Automated checks: units, time zones, no zeros for missing, simulated rows flagged, disclosure list matches

### E21-3 Public-ready repo and rehearsals · P0

- **Ask:** Make the repo ready to go public (no secrets or raw datasets in its history, a README that runs the demo in five commands) and do two clean final rehearsals by different presenters.
- **Status:** backlog
- **Also:** the whole team
- **Needs first:** E0-2
- **Needed later:** E20-2
- **Phase:** 3
- **Spec:** prd 11
- **Flag:** Team task. Hong Yi is the lead here; everyone contributes. Change the lead if you prefer.
- **Note:**
- **Success criteria:**
  - [ ] Repo made public for the submission, with no secrets or raw datasets in its history
  - [ ] README runs the demo in 5 commands on a fresh machine
  - [ ] A live URL is optional and not planned: the demo runs locally
  - [ ] Two clean run-throughs by different presenters

### CP0 Gate 0: mockup and data ready · P0

- **Ask:** First gate: prove the mockup is frozen, the app skeleton runs against Supabase, every table exists and every value is loaded (E1), and the schema, demo data and design tokens are frozen. After this gate nobody creates tables or loads reference data.
- **Status:** backlog
- **Needs first:** E0-1, E0-2, E1-4
- **Needed later:** E1-3
- **Phase:** 0
- **Spec:** backlog
- **Note:**
- **Success criteria:**
  - [ ] Mockup version 1 is frozen and shared
  - [ ] App skeleton runs locally against Supabase and reads from the database
  - [ ] All Silver, Gold, operations and reference tables exist and every seed value and the demo patient are loaded
  - [ ] Schema, demo data pack, API shape, event names, design tokens and safety message templates are frozen; a new table needs the owner's approval

### CP1 Gate 1: thin working slice · P0

- **Ask:** Second gate: prove a thin working slice end to end: open as the demo patient, mark a dose taken, log a glucose reading and a meal, replay a sensor sprint, scan and confirm a medicine, get the refusal message for 'can I skip metformin', and see the urgent screen for a 2.8 reading.
- **Status:** backlog
- **Needs first:** CP0, E3-2, E5-1, E7-2, E8-1, E11-1, E16-2
- **Needed later:** none
- **Phase:** 1
- **Spec:** backlog
- **Note:**
- **Success criteria:**
  - [ ] Open as the demo patient, see doses on Today and tap Taken
  - [ ] Log a glucose reading and a meal and see them stored
  - [ ] Replay a CGM sprint and see food responses computed
  - [ ] Photograph a medication, review, confirm and see the dose schedule appear
  - [ ] Ask 'can I skip metformin' and get the refusal template
  - [ ] Replay a 2.8 mmol/L reading and the urgent screen opens

### CP2 Gate 2: all features and the brief · P0

- **Ask:** Third gate: prove the whole demo script works with the real backend, including the generated brief with timeline, day traces and validator report, the learned-facts and week 1 versus week 8 view, and the share link opening on a second device.
- **Status:** backlog
- **Needs first:** CP1, E13-3, E17-3, E19-2
- **Needed later:** none
- **Phase:** 2
- **Spec:** backlog
- **Note:**
- **Success criteria:**
  - [ ] Every step of the demo script in flow.md section 5 works with the real backend
  - [ ] Brief generated for the demo patient with prescription timeline, day traces and validator report
  - [ ] Learned facts and the week 1 versus week 8 view work
  - [ ] Share link opens on a second device

### CP3 Gate 3: submission ready · P0

- **Ask:** Final gate: the submission package is complete and two clean rehearsals have been done by different presenters.
- **Status:** backlog
- **Needs first:** CP2, E21-1, E21-2, E21-3
- **Needed later:** none
- **Phase:** 3
- **Spec:** backlog
- **Note:**
- **Success criteria:**
  - [ ] Submission package complete
  - [ ] Two clean rehearsals by different presenters
