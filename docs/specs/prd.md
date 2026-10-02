# PRD — Smart Health: an AI companion for Type 2 diabetes self-care

> Project name: Smart Health.
> Track: AI CAN DO IT Tencent Cloud Hackathon SG 2026 · Healthcare (NTU LKC Medicine) · Challenge 2 "AI Healthier Every Day" · Scenario 2 — Type 2 Diabetes self-care, adults 45–65.
> Submission: 16 Oct 2026 · Demo Day: ~3 Nov 2026 · Must be built with CodeBuddy/WorkBuddy (keep chat-log screenshots as proof).

Companion docs: [architecture.md](architecture.md) · [flow.md](flow.md) · [schema.md](schema.md) · [design.md](design.md) · [rules.md](rules.md)

---

## 1. Problem

A person with Type 2 diabetes spends about 10 minutes a quarter with their doctor and the other ~364 days on their own. In between, they have to:

- understand several medications (and the supplements and TCM they add on),
- take them on time, every day,
- make sense of glucose readings with no context,
- eat, move, sleep and manage stress in ways that affect glucose,
- keep track of eye, foot and kidney screenings and follow-ups.

The data exists, spread across a watch, a glucometer, a pill box and memory, but no one joins it up. The patient can't interpret it safely, and the doctor never sees it. Consults start from a single HbA1c number and "how have you been?".

## 2. Vision

**The app helps the patient every day, and turns those days into a clear, evidence-backed brief for the doctor, without giving medical advice.**

## 3. Target users

| Persona | Description | Primary need |
|---|---|---|
| **Patient (primary)**, "Uncle Tan", 58 | Diagnosed T2D 4 yrs, on metformin (± one other oral agent). Also has high blood pressure. Smartphone user, not tech-savvy. English/Mandarin. Eats at hawker centres. Wears a budget smartwatch (e.g. Xiaomi). | Know what to take and why, know if he's "doing ok", fewer surprises at the doctor |
| **Patient**, "Mdm Siti", 49 | Newly diagnosed (<1 yr), motivated but overwhelmed. Malay/English. | Understand the condition and meds, build habits |
| **Clinician (secondary)**, GP / polyclinic doctor | ~10-min consults, no visibility between visits. | A one-page, trustworthy summary of what happened since the last visit and what to ask about |
| **Caregiver (stretch)** | Spouse or adult child helping manage. | Read-only view, with the patient's consent |

**Out of target:** Type 1 diabetes, insulin-pump users, gestational diabetes, under-18s. The app says so at onboarding and points those users to their care team.

## 4. What makes this different

| Typical diabetes/health app | Smart Health |
|---|---|
| Logs data for the patient to look at | **Turns logs into a clinician-grade pre-visit brief**: the doctor is a first-class user |
| Generic reminders ("take your pill") | **Captures *why* a dose was missed** (side effects, cost, ran out, felt fine) and reports the barrier pattern to the doctor |
| Generic diet advice | **Personal food-response learning**: 14-day CGM "sprints" learn which local foods spike *this* patient (e.g. chicken rice vs yong tau foo), and that knowledge keeps working after the sensor is removed |
| Alerts on fixed thresholds | **Momentum engine**: tracks each metric against the patient's *own* baseline, including direction and acceleration, so drift is caught before it becomes a crisis |
| Chatbot that "answers anything" | **Bounded by design**: a deterministic safety gate. The AI explains and organises but never advises on medication; interaction checks are a database lookup, not LLM guesses |
| "AI memory" hidden from the user | **Visible learning ("What Smart Health has learned about you")**: every learned fact has evidence, confidence and version history, and the patient can confirm, correct or delete it |
| English only | Explanations in **English, Mandarin, Malay, Tamil**, with text-to-speech |

**One-line pitch:** *"Smart Health is the everyday companion for your health, and the notes your doctor always wished they had."*

## 5. Goals & success metrics

### Hackathon goals
1. All features in §6 working end-to-end in a live demo, on realistic data (a teammate's real watch export + mock CGM replay).
2. Scores well across all 10 judging dimensions. Hardest: Responsible AI & Ethics, AI Interaction, Human-Centered Design, Technical Execution.

### Product metrics (pilot hypotheses, not claims)
| Metric | Definition | Target hypothesis |
|---|---|---|
| Confirmed adherence | Doses confirmed taken ÷ scheduled | +10–15 pts vs baseline month |
| Logging continuity | Days with ≥1 log ÷ days enrolled | ≥ 70% at week 8 |
| Miss-reason capture | Unconfirmed doses with a reason ÷ unconfirmed doses | ≥ 60% |
| Brief usefulness | Clinician rating "changed what I asked/did" | ≥ 3.5 / 5 |
| Preventive completion | Due screenings completed within 60 days of due date | +20% |
| Safety | Medication-advice leakage in red-team suite | **0** |

## 6. Features (all in scope for submission)

Each feature lists its **acceptance criteria (AC)**. IDs are used in flow.md and schema.md.

### F1 Onboarding (form or chat)
Collects demographics, diagnosis and year, comorbidities, allergies, family history, current meds/supplements/TCM, last HbA1c, targets set by their doctor (if known), preferred language, reminder times, devices.
- AC: user can finish via **either** a step-by-step form **or** a conversational onboarding agent; both write the same records.
- AC: out-of-scope users (T1D, pregnancy, <18) get a clear message and are not enrolled.
- AC: user must accept consent screens (data use; optional brief sharing) before any data is stored.

### F2 Prescription & medication capture
Photo of a prescription label, medication box, supplement or TCM packaging → vision model extracts name, strength, dose, frequency, timing, prescriber, date → **user confirms/edits** → saved.
- AC: every extracted field shows a confidence score; low-confidence fields are highlighted and must be confirmed.
- AC: unrecognised items get "I'm not able to identify this medication, please check with your pharmacist" plus a manual-entry option. The app never guesses.
- AC: saving a medication builds its dose schedule (F4) and triggers the clash check (F5).

### F3 Medication explainer
Plain-language "what this is for, how to take it, common side effects, what to tell your doctor", retrieved from the 250k Medicines dataset (uses, side effects, classes; RAG), with citations to that dataset and a note that it is not an authoritative label. Available in 4 languages with TTS playback.
- AC: every explanation cites its source(s).
- AC: dose information shown is **only** what's on the user's own confirmed prescription, never generated.
- AC: questions like "can I stop/double/skip…" get a refusal template and an offer to add the question to the doctor brief (F12).

### F4 Adherence engine
Dose windows (scheduled time ±2h, configurable per med), with a reminder at T and a re-nudge at T+1h. Unconfirmed at window close → status `unconfirmed`. On the next app open, a one-tap reason prompt: *took it, forgot to log / forgot / side effects / ran out / felt fine, skipped / cost / other*.
- AC: "with food" medications can be triggered by logging a meal.
- AC: a reason turns `unconfirmed` into `taken_late_logged` or `missed`, with the reason stored.
- AC: running out is predicted from pill count and dose rate, with a refill reminder 7 days ahead.
- AC: the adherence timeline and reason breakdown appear in the brief.

### F5 Clash checker (drug–drug, drug–supplement, drug–TCM)
Deterministic lookup against an interaction reference table. The LLM only rephrases a confirmed hit into plain language.
- AC: runs whenever a medication, supplement or TCM item is added or changed.
- AC: patient message is always of the form "Possible interaction between X and Y. Please check with your pharmacist or doctor before continuing." It never says "stop X".
- AC: items not found in the reference table are labelled "not checked" (honest about uncertainty), never "safe".
- AC: every hit appears in the brief.

### F6 Health tracking and logging
- **Glucose:** glucometer entry (fasting / pre-meal / post-meal / random), and CGM stream during sprints. Unit: mmol/L.
- **Meals:** a photo or a text description is analysed by the LLM, which returns the items and estimated kcal, carbs, protein, fat, fibre, sugar and sodium with a confidence per field. Estimates are tagged "Estimated" until the user confirms or edits them, then behave like any other logged value. Flags for high salt, high sugar or high GI are computed in code from the stored values. Local dish names are fine; Open Food Facts and NHANES values are only a sanity check that can add a "check this" flag. Meals from the demo datasets keep their measured macros.
- **Workouts:** manual entry (type, duration, intensity) plus wearable import.
- **Wearables:** steps, heart rate, sleep, HRV/stress (where available) via Health Connect (Android) / HealthKit (iOS), or file import plus demo replay.
- **Mood / stress / sleep check-in:** a 30-second evening check-in (1–5 scales and an optional note).
- **Symptoms:** free text or picker, with severity.
- AC: every log is timestamped, has a source, and is idempotent (re-syncs don't duplicate).
- AC: the user can edit or delete their own logs; edits are versioned in the event log.

### F7 CGM sprint and personal food response
A 14-day CGM "sprint" mode (the target group doesn't need a permanent CGM; sprints before a review or after a medication change make it useful and affordable). For each meal during a sprint, compute the 2-hour glucose response (incremental AUC and peak rise). Aggregate per food.
- AC: a food's response is only surfaced after ≥2 observations, and shown with n and a range.
- AC: after the sprint, logging a known high-response food shows a gentle, factual note: "Last time you had this, your glucose rose more than after most of your meals."
- AC: a food-response leaderboard ("your gentlest / your spikiest foods") appears in Insights and the brief.

### F8 Momentum engine
For each tracked metric: personal baseline (rolling 28-day median and MAD), momentum (7-day EWMA slope, normalised), and change-of-momentum (slope now vs previous 7 days). Flags when drift is persistent (≥3 days beyond threshold) or accelerating.
- AC: deterministic and explainable. Each flag stores the numbers that caused it.
- AC: flags go to the **brief** as "patterns for clinician review". The patient sees a neutral framing ("your fasting readings have been trending higher this week, worth mentioning to your doctor") plus a targeted symptom check-in (F9).
- AC: fixed clinical safety thresholds bypass the momentum logic (see F10).

### F9 Targeted symptom check-ins
When a pattern suggests something the doctor should know about, the agent asks a specific, neutral question ("Any tingling or numbness in your feet this week?", "More thirsty or more trips to the toilet than usual?") and logs the answer.
- AC: check-ins **ask, never diagnose**. No condition names shown to the patient in a diagnostic sense.
- AC: at most 1 check-in per day and 3 per week (anti-nag), adapted to the patient's response rate.
- AC: answers appear in the brief's symptom section, linked to the triggering pattern.

### F10 Urgent escalation (safety tier)
Rule-based, not LLM: e.g. glucose < 3.0 mmol/L, glucose < 3.9 mmol/L with symptoms, repeated readings above the configured high threshold, or red-flag symptoms (chest pain, confusion, fainting).
- AC: shows a full-screen, plain-language instruction to seek care now (995 / A&E / call doctor, depending on tier), plus hypo self-help steps from the approved corpus.
- AC: never delayed until the next brief; logged as an urgent event.
- AC: thresholds live in config and are marked "to be validated by clinical advisor".

### F11 Lifestyle coach
Short, practical nudges personalised by the user's data and learned preferences (e.g. prefers evening walks). Nudge content must come from an approved corpus: **no guideline corpus (e.g. Health Promotion Board) is in the cited data sources**, so until you approve one, nudges are fixed team-written templates driven by the user's own data (e.g. "you walked after dinner 3 times this week and your evening readings were lower").
- AC: every nudge is a reviewed template or cites its approved source; no free-generated health claims.
- AC: nudge timing and type adapt to what this user actually responds to (see §7).
- AC: high-salt / high-sugar food flags link to a swap suggestion from the corpus.

### F12 Doctor brief (headline feature)
Auto-generated before each appointment (and on demand) for a chosen period. Rendered as an in-app view, printable PDF, and time-limited share link (with consent).

Sections:
1. Profile snapshot (age, diagnosis and duration, comorbidities, allergies, family history, current meds with start dates, last HbA1c, period covered)
2. Top 3 to discuss (ranked, each linked to evidence)
3. Medication and adherence: **prescription timeline chart** (row per medication, day cells taken / late / unconfirmed / missed, glucose overlay), adherence %, miss-reason breakdown, side effects, clash flags
4. Glucose: fasting and post-meal trend, time-in-range (CGM sprints), out-of-range counts, momentum vs baseline
5. Nutrition: carbs / sugar / sodium vs guideline, high-salt / high-GI frequency, meal timing, personal food-response leaderboard
6. Exercise: minutes/week vs 150-min guideline, steps, trend
7. Sleep: duration and regularity
8. Stress and mood: check-in scores, HRV where available
9. Symptom log (including check-in answers)
10. Patterns for clinician review: AI-identified, labelled *unverified*, each with supporting data
11. Preventive care status: eye / foot / kidney screening, vaccinations, due/overdue
12. Patient's own questions
13. Data completeness (% of days logged per stream), so the doctor knows how much to trust each section
14. Day traces: three representative days (best / worst / typical) on one timeline, with event-window findings and lab history (HbA1c, lipids, kidney) alongside

- AC: every number in the brief is computed deterministically; the LLM only writes narrative summaries and suggested questions, and each sentence must reference an evidence ID (validator rejects any that don't).
- AC: the patient can view their own brief (no hidden findings) and add their own questions.
- AC: generation completes in < 30 s for 90 days of data.

### F13 Preventive care and scheduler
Tracks recommended diabetes care items (eye screening, foot screening, kidney function / urine test, HbA1c review, flu vaccination, etc.) with last-done and interval → due/overdue. Momentum flags or due items suggest booking a visit; the user can add it to Google Calendar (or an .ics file).
- AC: the app never books on the user's behalf without explicit confirmation.
- AC: an appointment created in-app automatically schedules a brief 48h before.

### F14 Healthcare preparation (questions for my doctor)
Patient collects questions anytime (typed, voice, or "add to doctor questions" from a refused chat). The agent helps phrase them clearly. Included in the brief.

### F15 Companion chat
In-app assistant for "what is this med for", "how was my week", "what does this reading mean in general". Grounded in the user's data and the corpus, passes the safety gate, and uses memory.
- AC: the chat supplements the app; every feature is reachable without chat.

### F16 "What Smart Health has learned about you" (transparent memory)
A screen listing learned facts (preferences, routines, barriers, food responses) with evidence, confidence and date. The user can confirm, correct or delete; changes are versioned.
- AC: each fact shows how it is supported: *observed* (you told us or we measured it), *derived* (calculated from your data) or *inferred* (proposed by the app, waiting for you). Nothing is labelled "validated": no part of this project is clinically validated yet.
- AC: proposed facts never drive nudges or briefs until confirmed or until confidence reaches 0.7 with at least the minimum evidence for that feature.

### F17 Multilingual and TTS
EN / 中文 / BM / தமிழ் UI strings and explanations; TTS playback for explanations and reminders.

### F18 Lifestyle timeline and day traces
Puts every stream on one clock (meals, doses taken/missed, workouts, glucose, watch heart rate and steps, sleep, symptoms) so the patient and the doctor can see *what happened around what*. The doctor brief adds **day traces**: a best, a worst and a typical day drawn as one chart, plus event-window findings (meal → glucose, workout → glucose, dose → glucose, sleep → next fasting glucose).
- AC: the Insights tab has a day view: glucose line (CGM sprint or glucometer points) with meal, dose (taken / unconfirmed / missed), workout and symptom markers, and heart-rate/steps and sleep bands underneath.
- AC: event-window results are computed deterministically (services, no LLM) from `event_windows`; a finding needs ≥ 5 matched pairs and quality-checked data, otherwise it is not shown.
- AC: findings are worded "associated with", never "caused by", labelled unverified in the brief, and shown to the patient too (no hidden findings).
- AC: the three representative days in the brief are chosen by fixed rules (lowest time-in-range, highest, closest to median) and each links to its underlying logs.
- AC: gaps are visible. A day with missing CGM, watch or meal data shows "no data" for that stream instead of an interpolated line.
- Event-window catalogue: architecture.md §4.4b. Data plan: `data/plan/smart_health_data_plan.xlsx`.

### Stretch (only after F1–F18 pass)
- S1 Caregiver read-only view (consent-gated)
- S2 Live Health Connect sync on stage (vs replay)
- S3 Voice logging ("I just had chicken rice")

## 7. "Grows with the user": the agentic harness and memory

The system improves for each user through four concrete mechanisms (details in architecture.md §5):

1. **User model memory:** a nightly reflection agent reviews the day's data and chat, and proposes evidence-backed facts ("usually walks after dinner", "misses evening dose on weekends", "chicken rice → high response, n=3"). Facts carry confidence, evidence links and versions, and are visible and editable in F16.
2. **Adaptive nudging:** tracks which nudge types and times this user acts on and shifts toward them (epsilon-greedy over time slots and nudge types).
3. **Personal baselines:** every alert and trend is relative to *this* user's recent normal, recomputed daily.
4. **Typed decisions (JEV):** a fast decision layer answers small yes/no and choice questions with a calibrated confidence: which memory a question needs, whether a message asks for medication advice or a diagnosis, what kind of fact a candidate is. Rules always win and low confidence takes the conservative path (memory.md).
5. **Episodic recall:** past conversations are summarised and embedded so the companion remembers context ("last week you mentioned stomach upset after metformin, is that still happening?"), and reported side effects flow into the brief.

## 8. Safety and responsible AI principles

1. **Explain, organise, remind. Never advise on medication.** No dose changes, starts, stops or substitutions.
2. **Deterministic where it matters:** interactions, thresholds, all numbers in the brief, and urgent escalation are rule-based and code-computed.
3. **Honest about uncertainty:** confidence shown on extraction; "not checked" instead of "safe"; "I'm not able to identify that medication, please check with your pharmacist."
4. **No hidden findings:** the patient can see everything the doctor sees. Patterns are framed as "worth discussing", never as diagnoses.
5. **Urgent never waits:** safety thresholds trigger immediate guidance.
6. **Cited sources only** for health and lifestyle content.
7. **Everything is logged:** every user action, agent run, tool call and guardrail decision goes to an append-only event log.
8. **User control:** consent before storage and sharing; the user can edit or delete learned memory and logs.

## 9. Scope

**In scope:** everything in §6 F1–F17, Android-first mobile app (iOS if time permits via the same codebase), backend and agent harness, doctor brief (in-app, PDF, share link), demo data pipeline (watch export + mock CGM replay), red-team test suite.

**Out of scope (this submission):** real clinical integrations (EMR, HealthHub, national programmes), insulin dosing, diagnosis, telemedicine, payments, full PDPA compliance programme (PII hardening deferred; basic consent and encryption in transit are in).

## 10. Assumptions and open decisions

| # | Item | Current assumption | Owner |
|---|---|---|---|
| A1 | Front end | Mobile-first web app in a phone frame / WebView (no store fees). No live Health Connect/HealthKit: device data is replayed from the cited datasets | Team |
| A2 | AI models | Google Cloud Vertex AI for everything except speech (ElevenLabs) and JEV (TypeSafe): Claude Sonnet 5.5 for text and photos, Gemini Embedding at 768 dimensions, Cloud Translation for fixed text. No Tencent fallback. Behind a provider gateway. Details and cost control in [ai-models.md](ai-models.md) (owner decision D-047) | Team |
| A3 | Clinical thresholds | Rules, not data: hypo levels (3.9 / 3.0 mmol/L) and configurable highs are team-written config. No cited source contains them, so this is under "Needs your OK". **Validate with a clinical advisor** | Team |
| A4 | Drug corpus and interactions | Drug facts (uses, side effects, classes, aliases) come from the 250k Medicines dataset only. **It has no interactions column** (checked 2026-10-02), so interactions come from the openFDA drug-label `drug_interactions` text, shown as general label information and labelled `reference_matched` (owner decision D-036). No supplement/TCM interaction data exists in the cited sources, so those items show "not checked" | Team |
| A5 | Food nutrients | Meal photos and text are analysed by the LLM for macros (kcal, carbs, protein, fat, fibre, sugar, sodium), stored as estimates with confidence and confirmed by the user. Open Food Facts and NHANES dietary files are sanity-check references only. Dataset meals keep measured macros. Glucose response is always measured | Team |
| A6 | Mock CGM | CGMacros (T2D participants) and BIG IDEAs, both on PhysioNet. Only CGMacros has T2D (14 people); BIG IDEAs participants are HbA1c 5.2-6.4% | Team |
| A7 | Healthier SG integration | Dropped for now | — |
| A8 | Demo data | **Only data from the cited sources** (see A10). Real data covers the CGM/meal/watch streams and the patient profile; the 60-day history, adherence, mood, BP and workouts are simulated from cited data and disclosed as simulated. Summary: `data/plan/smart_health_data_plan.xlsx` (Use now / Still missing / Domain knowledge). | Team |
| A10 | Data source policy | The app may ingest data only from the datasets in `download_manifest.csv` (48) and the GlucoBench Kaggle link. Owner-approved additions (2026-10-02): NHANES 2011-2012, 2013-2014 and 2015-2016 without the accelerometer files, and the openFDA drug-label API for interactions. Anything else (guideline text, drug labels, own watch export or label photos) needs explicit approval first and is listed under "Needs your OK" in the workbook | Team |
| A9 | Insulin | Out of scope: no dose tracking or advice. Datasets with insulin columns are imported with those columns discarded | — |
| A11 | Decision layer (JEV) | JEV typed decisions behind `decision/` using the TypeSafe JEV model; if JEV is off or unreachable the conservative path applies (no model fallback). It is hosted on OpenRouter as `typesafe/jev-1.13` (D-049). Rules always override JEV | Team |
| A12 | Security scope | Demo-grade. Deferred until after the demo: row-level security, consent-scoped retrieval, data-classification tagging, retention workflows. Never deferred: the clinical safety path and keeping names and identifiers out of prompts | Team |
| A13 | Runtime | The web app and API run locally on each developer's machine. The database and file storage are Supabase (Postgres with pgvector), one shared project. Row-level security is on with no policies and only the backend connects. The other outbound calls are the AI APIs. There is no hosting for the app, so a live URL (an optional submission bonus) is not planned | Team |

## 11. Submission deliverables checklist
- [ ] Project title and ≤10-word blurb
- [ ] Project description (scenario / users / value, pain points, architecture, business value)
- [ ] ≥3 CodeBuddy/WorkBuddy chat screenshots (capture throughout, not at the end)
- [ ] 16:9 cover image (380×216)
- [ ] Architecture diagram **with trust boundaries** and design trade-offs
- [ ] Live demo (script in flow.md §5)
- [ ] GitHub repo with complete source
- [ ] Optional: 5–8 min video, live URL (bonus)
