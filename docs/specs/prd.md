# PRD — Equinox: an AI companion for Type 2 diabetes self-care

> Project name: Equinox.
> Track: AI CAN DO IT Tencent Cloud Hackathon SG 2026 · Healthcare (NTU LKC Medicine) · Challenge 2 "AI Healthier Every Day" · Scenario 2 — Type 2 Diabetes self-care, adults 45–65.
> Submission: 16 Oct 2026 · Demo Day: ~3 Nov 2026 · Must be built with CodeBuddy/WorkBuddy (keep chat-log screenshots as proof).

**Status note (2026-10-15):** the product is built as a mobile-first web app (`apps/web`, React) with a FastAPI backend (`services/api`), 76 tables, Alembic head 0040. The app opens on Mr Tan's example record (read-only for everyone) and anyone can create their own user; there is no real sign-in yet (the app sends an `X-User` key). The status notes inside each feature below show what is built and what is not; where one is older than 2026-10-15, the code and [app-flow-and-features.md](app-flow-and-features.md) win.

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

| Typical diabetes/health app | Equinox |
|---|---|
| Logs data for the patient to look at | **Turns logs into a clinician-grade pre-visit brief**: the doctor is a first-class user |
| Generic reminders ("take your pill") | **Captures *why* a dose was missed** (side effects, cost, ran out, felt fine) and reports the barrier pattern to the doctor |
| Generic diet advice | **Personal food-response learning**: the days a CGM is worn (for example a 14-day sensor before a review) learn which local foods spike *this* patient (e.g. chicken rice vs yong tau foo), and that knowledge keeps working after the sensor is removed |
| Alerts on fixed thresholds | **Momentum engine**: tracks each metric against the patient's *own* fixed baseline, so drift is caught before it becomes a crisis |
| Chatbot that "answers anything" | **Bounded by design**: a deterministic safety gate. The AI explains and organises but never advises on medication; interaction checks are a database lookup, not LLM guesses |
| "AI memory" hidden from the user | **Visible learning ("What Equinox has learned about you")**: every learned fact has evidence, confidence and version history, and the patient can confirm, correct or delete it |
| English only | Explanations in **English, Mandarin, Malay, Tamil**, with text-to-speech |

**One-line pitch:** *"Equinox is the everyday companion for your health, and the notes your doctor always wished they had."*

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
*Data (data model v2, see [data-flow.md](data-flow.md) section 6): writes `bronze_profile` then `user_profile`, and `consents`; creates the first pending `medication_log` rows.*

Collects demographics (birth year, gender, race, height, weight), diagnosis and year, conditions and allergies (two free-text notes; family history is no longer a separate question), the typical work week (days, hours, type of job), an emergency contact (name, phone and relationship, all required), current meds/supplements/TCM with the time, quantity and before / after meal setting of each dose, last HbA1c, targets set by their doctor (if known), preferred language, reminder times, and the watch and CGM model.
- AC: user can finish via **either** a step-by-step form **or** a conversational onboarding agent; both write the same records.
- AC: out-of-scope users (T1D, pregnancy, <18) get a clear message and are not enrolled.
- AC: user must accept consent screens (data use; optional brief sharing) before any data is stored.

### F2 Prescription & medication capture
*Data (data model v2, see [data-flow.md](data-flow.md) section 6): photo to `bronze_medication` and `prescription_scans`; after confirmation `medications`, `medication_schedule`, `medication_log`; then `interaction_alerts`.*

Photo of a prescription label, medication box, supplement or TCM packaging → vision model extracts name, strength, dose, frequency, timing, prescriber, date → **user confirms/edits** → saved.
- AC: every extracted field shows a confidence score; low-confidence fields are highlighted and must be confirmed.
- AC: the scanner only reads what is printed and never guesses. A medicine that is not in our reference list is still read and saved as the label prints it, and shows as "Not checked" for interactions; it is never called "safe". An unreadable or unclear label goes to manual entry (D-064, D-070).
- AC: saving a medication builds its dose schedule (F4) and triggers the clash check (F5).

### F3 Medication explainer
*Data (data model v2, see [data-flow.md](data-flow.md) section 6, [f3-explainer.md](f3-explainer.md)): reads `medications` and `medication_schedule`; writes `medication_explanations` (the saved explanation) and `doctor_questions` (a question from the page).*

Open a medicine from the Meds page: plain-language "what this is for, how you take it (from your own label), common side effects, when to tell your doctor", written by the model from the medicine's name and label text after a web search, with the web pages it used, and a box to save a question for the doctor. The 250k Medicines file is not used: it is a general list (under 5% anti-diabetic) with no supplements or herbal products (D-071). Not an authoritative drug label, and the page says so.
- AC: every explanation cites its web sources; nothing is shown without at least one (reliable medical sites are preferred and are the only ones shown when any were used).
- AC: dose information shown is **only** what's on the user's own confirmed label, never generated. Any generated sentence that gives a dose, a number of tablets or a schedule, tells the person to stop, skip, change or swap a treatment, or calls a medicine "safe" is dropped by code before it is saved.
- AC: a product the model cannot identify is not explained; the page says so and offers the doctor-question box.
- AC: the explanation is made once (the first open takes up to about 30 seconds) and kept; it is made again only when the medicine's name, strength, type or label text changes.
- AC: a question typed on the page is saved to the doctor-question list (`origin` user) for the care plan and the doctor brief (F12).
- Not in F3 for now: text-to-speech and 4 languages (to be discussed with the team first); refusal template for "can I stop/double/skip…" questions in chat.

### F4 Adherence engine
*Calendar reminders (2026-10-09, [f4-calendar.md](f4-calendar.md)): after a medicine is confirmed the backend adds each dose time to Google Calendar through a Workato recipe, so the phone's calendar app gives the reminder. Backend built; the Workato recipe (owned by Joely) is not finished, and reminder e-mails through a second Workato recipe are described in [email-notifications.md](email-notifications.md).*

*Built so far (2026-10-08, [f4-home-doses.md](f4-home-doses.md)): the Home card (due now, next dose, "not confirmed" with "Tell us why"), the Taken button and the missed-dose sheet H7. Since then (2026-10-15, from the code): dose reminders inside the dose window with learned timing are built (`app/agents/dose_timing.py`, see [learning-loop.md](learning-loop.md) section 14), and medicine stock and refill logic exist (`app/services/medication_stock.py`). The adherence timeline was not re-checked in this pass.*

*Data (data model v2, see [data-flow.md](data-flow.md) section 6): writes `medication_log` (taken, missed with reason, skipped), `notifications`, `refill_forecasts`; reads `medication_schedule`, the `adherence_summary` view (prescription medicines only) and `care_summary`.*

The Home page names each dose by what to take ("Metformin, 1 Tab"), not its strength. Dose windows (scheduled time ±2h, configurable per med), with a reminder at T and a re-nudge at T+1h. Unconfirmed at window close → the dose stays `pending` and is shown as unconfirmed. On the next app open, a one-tap reason prompt: *took it, forgot to log / forgot / side effects / ran out / felt fine, skipped / cost / other*.
- AC: "with food" medications can be triggered by logging a meal.
- AC: a reason turns an unconfirmed dose into `taken` (shown as late if more than 60 minutes after the scheduled time) or `missed`, with the reason stored.
- AC: running out is predicted from pill count and dose rate (`refill_forecasts`), with a refill reminder 7 days ahead.
- AC: the adherence timeline and reason breakdown appear in the brief.

### F5 Clash checker (drug–drug, drug–supplement, drug–TCM)
*Data (data model v2, see [data-flow.md](data-flow.md) section 6): writes `interaction_alerts`; reads `medications`, `interaction_rules`.*

*Built (2026-10-08, [f5-clash.md](f5-clash.md)): a clash box on the Meds page. **Changed by Joely on 2026-10-08, pending Hong Yi's confirmation:** a pair is flagged if the interaction reference table (a deterministic lookup, always run) OR an AI model with a web search finds a possible clash; the AI can only add a flag, never remove one the table found. The earlier rule (table only, the LLM only rephrases a confirmed hit) no longer describes the build.*

Lookup against an interaction reference table, plus an AI check of all the person's saved medicines after every add. The wording is fixed and never advises.
- AC: runs in the background whenever a medication, supplement or TCM item is added (typed or scanned), and looks at all saved medicines each time. No box shows when nothing may clash; a check that could not finish says so and is never shown as all clear.
- AC: patient message is always of the form "Possible interaction between X and Y. Please check with your pharmacist or doctor before continuing." It never says "stop X".
- AC: items not found in the reference table are labelled "not checked" (honest about uncertainty), never "safe".
- AC: every hit appears in the brief.

### F6 Health tracking and logging
*Data (data model v2, see [data-flow.md](data-flow.md) section 6): each entry goes to a `bronze_*` table then `cgm_readings`, `food_logs`, `exercise_logs` / `exercise_sets`, `symptom_logs`, `wellbeing_logs`, `blood_pressure_readings` or `lab_results`; watch syncs go to `watch_readings`; reads `timeline_5min`.*

- **Glucose:** a continuous CGM stream, and finger-prick entry (stored with the CGM readings, source manual; whether it was fasting or after a meal is worked out from the time and the last meal, not asked). Unit: mmol/L.
- **Meals:** a photo or a text description is analysed by the LLM, which returns the items and estimated kcal, carbs, protein, fat, fibre, sugar and sodium with a confidence per field. Estimates are tagged "Estimated" until the user confirms or edits them, then behave like any other logged value. Flags for high salt, high sugar or high GI are computed in code from the stored values. Local dish names are fine; Open Food Facts and NHANES values are only a sanity check that can add a "check this" flag. Meals from the demo datasets keep their measured macros.
- **Exercise:** manual entry (type, start and end, intensity 1 to 5, how it felt; strength sessions can add sets) plus wearable import.
- **Wearables:** steps, heart rate, sleep, HRV/stress (where available) via Health Connect (Android) / HealthKit (iOS), or file import plus demo replay.
- **Mood / stress / sleep check-in:** a 30-second evening check-in (mood, stress, energy) and a morning question on sleep quality, all on 1–5 scales.
- **Blood pressure and labs:** blood pressure (systolic and diastolic, a few times a week) and three lab values (HbA1c in %, fasting glucose, fasting insulin). The watch also records heart rate, HRV, SpO2, steps and minutes asleep in 5-minute buckets.
- **Symptoms (on hold, D-054: pending clinical review; D-052):** a picker with severity, built to take about 30 seconds. The sensor glucose and trend at that moment and the time are filled in automatically. The person can say when it happened (just now, earlier today, last night, or a set time), so night symptoms logged at breakfast get the right time. Optional detail: how long it lasted; left, right or both sides for numbness and pain; relation to a meal or exercise; and for dizziness what it felt like (standing up, shaky or sweaty, spinning). Extra symptoms: vomiting, night sweats, breathlessness at rest, sudden vision loss. Red-flag symptoms go straight to the urgent path. The app records and asks; it never labels a cause.
- AC: every log is timestamped, has a source, and is idempotent (re-syncs don't duplicate).
- AC: the user can edit or delete their own logs; edits are versioned in the event log.

### F7 CGM and personal food response
*Data (data model v2, see [data-flow.md](data-flow.md) section 6): computed into `meal_response`; the per-food view groups it by food.*

Whenever a CGM is worn (continuously, or for example a 14-day sensor before a review or after a medication change; the target group doesn't need a permanent CGM) each meal gets a glucose response: the level before, the peak rise, the time to peak, the area above the pre-meal level over 2 hours and the time to recover (`meal_response`). Aggregate per food. Wear periods are just stretches of data; there is no separate sprint record.
- AC: a food's response is only surfaced after ≥2 observations, and shown with n and a range.
- AC: after the sensor is removed, logging a known high-response food shows a gentle, factual note: "Last time you had this, your glucose rose more than after most of your meals."
- AC: a food-response leaderboard ("your gentlest / your spikiest foods") appears in Insights and the brief.

### F8 Momentum engine
*Data (data model v2, see [data-flow.md](data-flow.md) section 6): computed into `baselines`, `daily_summary` (the `*_worse_pct` columns and `declining_metrics`) and `clinical_flags`.*

For each tracked metric (heart rate, HRV, SpO2, glucose, blood pressure): a **fixed personal baseline**, the person's usual range by hour of day (median with the 5th, 25th, 75th and 95th percentiles). It is built once from their first 14 days with enough data (blood pressure: the first 5 readings) and changes only when it is reset on purpose (doctor review, medication change, or the user), so a slow decline cannot become the new normal. Each day, the share of a metric's readings on the worse side of that range (above the 95th percentile for heart rate and glucose, below the 5th for HRV and SpO2) is computed; a day is flagged when more than 20% are on the worse side, and a metric is flagged as declining when 3 of the last 5 days are flagged. Getting better (for example lower glucose) is not flagged. These are starting values, not clinically validated. The 7-day momentum slope and the "accelerating" flag are no longer part of the engine (data-model-v2.md sections 5.2 and 5.3).
- AC: deterministic and explainable. Each flag stores the numbers that caused it.
- AC: flags go to the **brief** as "patterns for clinician review". The patient sees a neutral framing ("your fasting readings have been trending higher this week, worth mentioning to your doctor") plus a targeted symptom check-in (F9).
- AC: fixed clinical safety thresholds bypass the momentum logic (see F10).

### F9 Targeted symptom check-ins
*Data (data model v2, see [data-flow.md](data-flow.md) section 6): the question is a `notifications` row (kind `checkin`); the answer goes `bronze_symptom` then `symptom_logs`.*

When a pattern suggests something the doctor should know about, the agent asks a specific, neutral question ("Any tingling or numbness in your feet this week?", "More thirsty or more trips to the toilet than usual?") and logs the answer.
- AC: check-ins **ask, never diagnose**. No condition names shown to the patient in a diagnostic sense.
- AC: at most 1 check-in per day and 3 per week (anti-nag), adapted to the patient's response rate.
- AC: answers appear in the brief's symptom section, linked to the triggering pattern.

### F10 Urgent escalation (safety tier)
*Data (data model v2, see [data-flow.md](data-flow.md) section 6): writes the event log, a `glucose_events` row and a `clinical_flags` row for a low; reads `cgm_readings` (rules only).*

> **On hold (2026-10-03, D-054):** pending clinical review by Damien (`docs/handover/questions-for-damien.md`). The values and fields below are placeholders. Do not build E1-7, E11-2, E7-4 or E13-4 until it is cleared.

Rule-based, not LLM. Low glucose has two tiers. The values come from the owner's clinical feedback (2026-10-03, D-050) and are placeholders pending clinical validation.
- **Tier 1, low (below 4.0 mmol/L, 3.0 or above):** the person can usually still treat it. A plain screen says to take the fast-acting sugar listed in their doctor's low-sugar plan, shows a 15-minute recheck countdown, then asks how they feel (better, about the same, worse). Same or worse, or still low at the recheck, moves to tier 2.
- **Tier 2, very low (below 3.0 mmol/L):** the person may be unable to function, and around 2.8 may faint or lose consciousness. A full-screen instruction to get help now (call 995 or the clinic), and the emergency contact is alerted.
- **Other triggers:** repeated readings above the configured high threshold; red-flag symptoms (chest pain, confusion, fainting, breathlessness at rest, sudden vision loss or a curtain across the vision); vomiting together with high glucose (get care today).
- AC: tier 1 and tier 2 screens are fixed text written by people, with no LLM and no network call. The hypo steps come from the approved corpus; until a source is approved the screen points to the doctor's own low-sugar plan.
- AC: **emergency contact (D-051).** The patient adds one contact, chooses message, email and/or call, and consents. On tier 2 a message and email go straight away and a call follows if there is no reply in 5 minutes (placeholder). On tier 1 the contact is alerted only if the 15-minute check-in is unanswered and the glucose is still low. The message says only that the reading is very low and asks the contact to check on the person or call 995. No other health data is sent. No alert is sent without consent.
- AC: after a low, one question is asked and recorded: "Did you feel it before your sensor alerted you?" It appears in the brief as a self-report.
- AC: never delayed until the next brief; written to the event log, and a low also becomes a `glucose_events` row and a `clinical_flags` row.
- AC: thresholds, tiers and timings live in config and are marked "clinical validation pending".

### F11 Lifestyle coach
*Data (data model v2, see [data-flow.md](data-flow.md) section 6): writes `notifications` (kind `nudge`); reads `memory_facts`, `pattern_candidates`, `daily_summary`, `meal_response`.*

Short, practical nudges personalised by the user's data and learned preferences (e.g. prefers evening walks). Nudge content must come from an approved corpus: **no guideline corpus (e.g. Health Promotion Board) is in the cited data sources**, so until you approve one, nudges are fixed team-written templates driven by the user's own data (e.g. "you walked after dinner 3 times this week and your evening readings were lower").
- AC: every nudge is a reviewed template or cites its approved source; no free-generated health claims.
- AC: nudge timing and type adapt to what this user actually responds to (see §7).
- AC: high-salt / high-sugar food flags link to a swap suggestion from the corpus.

### F12 Doctor brief (headline feature)
*Data (data model v2, see [data-flow.md](data-flow.md) section 6): writes `briefs`, `brief_shares`, `brief_share_access`; reads the timeline, baselines, summaries, responses, glucose events, labs, flags, patterns, interaction alerts and doctor questions.*

Auto-generated before each appointment (and on demand) for a chosen period. Rendered as an in-app view, printable PDF, and time-limited share link (with consent).

Sections:
1. Profile snapshot (age, diagnosis and duration, comorbidities, allergies, family history, current meds with start dates, last HbA1c, period covered)
2. Top 3 to discuss (ranked, each linked to evidence)
3. Medication and adherence: **prescription timeline chart** (row per medication, day cells taken / late / unconfirmed / missed, glucose overlay), adherence %, miss-reason breakdown, side effects, clash flags
4. Glucose: fasting and post-meal trend, time-in-range, out-of-range counts, whether readings are outside the person's usual range, and heart rate, HRV, SpO2 and blood pressure beside it on the same dates (D-053; wording "associated with", unverified). The four charts (heart rate, SpO2 and glucose as lines with the usual range, blood pressure as a scatter) sit on one time axis with the day's overlay of meals, doses, exercise, symptoms, mood, steps and work hours
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
- AC: the four charts are drawn from the Gold timeline (`timeline_5min`) and the person's fixed baseline (`baselines`); readings on the worse side of the usual range are marked, and simulated points are marked from `source`.

### F13 Preventive care and scheduler
*Data (data model v2, see [data-flow.md](data-flow.md) section 6): writes `appointments` and `patient_preventive_status`; reads `preventive_items`, `care_summary`, `clinical_flags`, `lab_results`.*

Tracks recommended diabetes care items (eye screening, foot screening, kidney function / urine test, HbA1c review, flu vaccination, etc.) with last-done and interval → due/overdue. Momentum flags or due items suggest booking a visit; the user can add it to Google Calendar (or an .ics file).
- AC: the app never books on the user's behalf without explicit confirmation.
- AC: an appointment created in-app automatically schedules a brief 48h before.

### F14 Healthcare preparation (questions for my doctor)
*Data (data model v2, see [data-flow.md](data-flow.md) section 6): writes `doctor_questions`; reads `care_summary` and `briefs`.*

Patient collects questions anytime (typed, voice, or "add to doctor questions" from a refused chat). The agent helps phrase them clearly. Included in the brief.

### F15 Companion chat
*Data (data model v2, see [data-flow.md](data-flow.md) section 6): writes `conversations`, `messages`, `agent_runs`, `agent_steps`; a refused request adds a `doctor_questions` row.*

In-app assistant for "what is this med for", "how was my week", "what does this reading mean in general". Grounded in the user's data and the corpus, passes the safety gate, and uses memory.
- AC: the chat supplements the app; every feature is reachable without chat.

### F16 "What Equinox has learned about you" (transparent memory)
*Data (data model v2, see [data-flow.md](data-flow.md) section 6): reads and writes `memory_facts` (versioned).*

A screen listing learned facts (preferences, routines, barriers, food responses) with evidence, confidence and date. The user can confirm, correct or delete; changes are versioned.
- AC: each fact shows how it is supported: *observed* (you told us or we measured it), *derived* (calculated from your data) or *inferred* (proposed by the app, waiting for you). Nothing is labelled "validated": no part of this project is clinically validated yet.
- AC: proposed facts never drive nudges or briefs until confirmed or until confidence reaches 0.7 with at least the minimum evidence for that feature.

### F17 Multilingual and TTS
*Data (data model v2, see [data-flow.md](data-flow.md) section 6): reads `user_profile.language`.*

EN / 中文 / BM / தமிழ் UI strings and explanations; TTS playback for explanations and reminders.

### F18 Lifestyle timeline and day traces
*Data (data model v2, see [data-flow.md](data-flow.md) section 6): reads `timeline_5min`, `meal_response`, `exercise_response`, `glucose_events`, `baselines`.*

Puts every stream on one clock (meals, doses taken/missed, exercise, glucose, watch heart rate and steps, sleep, symptoms, mood, blood pressure and work hours) so the patient and the doctor can see *what happened around what*. The doctor brief adds **day traces**: a best, a worst and a typical day drawn as one chart, plus event-window findings (meal → glucose, workout → glucose, dose → glucose, sleep → next fasting glucose).
- AC: the Insights tab has a day view drawn from `timeline_5min`: glucose line (continuous CGM, with finger-prick points) with meal, dose (taken / late / missed), exercise and symptom markers (the symptom note shows on tap), mood dots, scheduled work hours, and heart-rate, SpO2, blood-pressure, steps and sleep underneath.
- AC: results are computed deterministically (services, no LLM) from `meal_response`, `exercise_response`, `glucose_events` and the timeline; a finding needs ≥ 5 matched events and quality-checked data, otherwise it is not shown.
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
3. **Personal baselines:** every alert and trend is relative to *this* user's own usual range: a fixed baseline built from their first 14 days that changes only when it is reset on purpose, so a decline is not absorbed into it.
4. **Typed decisions (JEV):** a fast decision layer answers small yes/no and choice questions with a calibrated confidence: which memory a question needs, whether a message asks for medication advice or a diagnosis, what kind of fact a candidate is. Rules always win and low confidence takes the conservative path (memory.md).
5. **Episodic recall:** past conversations are summarised and embedded so the companion remembers context ("last week you mentioned stomach upset after metformin, is that still happening?"), and reported side effects flow into the brief.

## 8. Safety and responsible AI principles

1. **Explain, organise, remind. Never advise on medication.** No dose changes, starts, stops or substitutions.
2. **Deterministic where it matters:** interactions, thresholds, all numbers in the brief, and urgent escalation are rule-based and code-computed.
3. **Honest about uncertainty:** confidence shown on extraction; "not checked" instead of "safe"; a label that cannot be read is typed in by the person, never guessed.
4. **No hidden findings:** the patient can see everything the doctor sees. Patterns are framed as "worth discussing", never as diagnoses.
5. **Urgent never waits:** safety thresholds trigger immediate guidance.
6. **Cited sources only** for health and lifestyle content.
7. **Everything is logged:** every user action, agent run, tool call and guardrail decision goes to an append-only event log.
8. **User control:** consent before storage and sharing; the user can edit or delete learned memory and logs.

## 9. Scope

**In scope:** everything in §6 F1–F17, a mobile-first web app (React, the same app on phone and desktop), backend and agent harness, doctor brief (in-app, PDF, share link), demo data pipeline (watch export + mock CGM replay), red-team test suite.

**Out of scope (this submission):** real clinical integrations (EMR, HealthHub, national programmes), insulin dosing, diagnosis, telemedicine, payments, full PDPA compliance programme (PII hardening deferred; basic consent and encryption in transit are in).

## 10. Assumptions and open decisions

| # | Item | Current assumption | Owner |
|---|---|---|---|
| A1 | Front end | Mobile-first web app in a phone frame / WebView (no store fees). No live Health Connect/HealthKit: device data is replayed from the cited datasets | Team |
| A2 | AI models | Google Cloud Vertex AI for everything except speech (ElevenLabs) and JEV (TypeSafe, on OpenRouter): Gemini 3.8 Flash (`gemini-3.8-flash`) for chat, photos and wording, `gemini-embedding-001` at 768 dimensions, Google Cloud Translation for fixed text, `gemini-2.5-flash-image` for dish pictures. No Claude, no Tencent fallback. Behind one gateway (`app/llm/gateway.py`), with a daily cap per kind of call. Details and cost control in [ai-models.md](ai-models.md) (D-059 replaced the Claude choice of D-047). ElevenLabs speech and Cloud Translation are not yet in the code | Team |
| A3 | Clinical thresholds | Rules, not data: low-glucose tiers (below 4.0 and below 3.0 mmol/L, owner values 2026-10-03, D-050) and configurable highs are team-written config. No cited source contains them, so this is under "Needs your OK". **Validate with a clinical advisor** | Team |
| A4 | Drug corpus and interactions | Drug facts (uses, side effects, classes, aliases) come from the 250k Medicines dataset only. **It has no interactions column** (checked 2026-10-02), so interactions come from the openFDA drug-label `drug_interactions` text, shown as general label information and labelled `reference_matched` (owner decision D-036). No supplement/TCM interaction data exists in the cited sources, so those items show "not checked" | Team |
| A5 | Food nutrients | Meal photos and text are analysed by the LLM for macros (kcal, carbs, protein, fat, fibre, sugar, sodium), stored as estimates with confidence and confirmed by the user. Open Food Facts and NHANES dietary files are sanity-check references only. Dataset meals keep measured macros. Glucose response is always measured | Team |
| A6 | Mock CGM | CGMacros (T2D participants) and BIG IDEAs, both on PhysioNet. Only CGMacros has T2D (14 people); BIG IDEAs participants are HbA1c 5.2-6.4% | Team |
| A7 | Healthier SG integration | Dropped for now | — |
| A8 | Demo data | **Only data from the cited sources** (see A10). The demo patient is Mr Tan (CGMacros participant 046) for 91 days, shown as the app's read-only example record: his real Dexcom glucose, heart rate, 29 meals and two labs cover the last ~10 days; the rest, including SpO2, blood pressure, adherence, mood, exercise and symptoms, is simulated from his own data and disclosed as simulated (`demo-data-plan.md`). Summary: `data/plan/smart_health_data_plan.xlsx` (Use now / Still missing / Domain knowledge). | Team |
| A10 | Data source policy | The app may ingest data only from the datasets in `download_manifest.csv` (48) and the GlucoBench Kaggle link. Owner-approved additions (2026-10-02): NHANES 2011-2012, 2013-2014 and 2015-2016 without the accelerometer files, and the openFDA drug-label API for interactions. Joely approved photos of real medicine packs for scanner testing on 2026-10-06 (D-065; kept in git-ignored `data/raw/label_photos/`, never committed). Anything else (guideline text, drug labels, own watch export or other photos) needs explicit approval first and is listed under "Needs your OK" in the workbook | Team |
| A9 | Insulin | Out of scope: no dose tracking or advice. Datasets with insulin columns are imported with those columns discarded | — |
| A11 | Decision layer (JEV) | JEV typed decisions behind `app/llm/jev.py` using the TypeSafe JEV model; if JEV is off or unreachable the conservative path applies (no model fallback). It is hosted on OpenRouter as `typesafe/jev-1.13` (D-049). Rules always override JEV | Team |
| A12 | Security scope | Demo-grade. Deferred until after the demo: row-level security, consent-scoped retrieval, data-classification tagging, retention workflows. Never deferred: the clinical safety path and keeping names and identifiers out of prompts | Team |
| A13 | Runtime | The web app and API run locally on each developer's machine. The database and file storage are Supabase (Postgres with pgvector), one shared project. Row-level security is on with no policies and only the backend connects. The other outbound calls are the AI APIs and Workato. A deployment to Google Cloud (Firebase Hosting, Cloud Run API and worker) is written up in `docs/handover/deployment-gcp.md`; whether it is live was not verified in this pass | Team |
| A14 | Emergency contact delivery | One emergency contact per patient, alerted by message, email and/or call with the patient's consent (D-051). An urgent alert to the contact's e-mail address goes through the Workato e-mail recipe ([email-notifications.md](email-notifications.md); recipe not finished); message and call delivery are not built. The contact's phone and email are never sent to an AI model. This is not the caregiver view, which stays a stretch goal | Team |
| A15 | SpO2 | No cited dataset is known to hold blood oxygen. The schema has an `spo2` metric. The demo simulates it from cited data and says so; a real watch source needs the owner's OK | Team |
| A16 | Appointment booking | Calendar entry and `.ics` file only. No HealthHub or clinic-system booking (owner, 2026-10-03) | Team |

## 11. Submission deliverables checklist
- [ ] Project title and ≤10-word blurb
- [ ] Project description (scenario / users / value, pain points, architecture, business value)
- [ ] ≥3 CodeBuddy/WorkBuddy chat screenshots (capture throughout, not at the end)
- [ ] 16:9 cover image (380×216)
- [ ] Architecture diagram **with trust boundaries** and design trade-offs
- [ ] Live demo (script in flow.md §5)
- [ ] GitHub repo with complete source
- [ ] Optional: 5–8 min video, live URL (bonus)
