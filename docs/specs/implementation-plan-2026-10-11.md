# Implementation plan: onboarding, medicines, doctor brief, care plan, logs, insights, home

**Drafted 2026-10-11 for Joely.** Nothing here was built when it was drafted; section 14 gives the status at the end of 2026-10-11. It is based on a read of the code on `dev` after the pull of 2026-10-10 (merge `3449891`), not on a live look at the app. Where the request was open to two readings, the plan says which one it assumes, and section 12 lists the questions that change the work.

## 0. The short version

The list has about 60 items. They fall into **eight pieces of work**. They should be built in this order, because each one needs the one before it:

| # | Piece | Why this order | Size |
|---|---|---|---|
| 1 | Database foundations (one new migration) | Onboarding, blood pressure, medicine stock and the brief all need new columns or tables | Medium |
| 2 | Onboarding rewrite, linked to the database | Needs piece 1. Also fixes "new user sees old answers" | Large |
| 3 | Blood pressure logging, and the Log / Food move | Blood pressure feeds Insights and the brief | Medium |
| 4 | Medicines: scanner, scope, stock ("medicine warehouse"), wording | Stock needs piece 1 | Large |
| 5 | Doctor brief changes | Needs the onboarding data from 2 and blood pressure from 3 | Large |
| 6 | Care plan, questions page, "How it is going", "What Equinox has learned" | Small, independent | Medium |
| 7 | Insights changes (all six tabs) | Needs heart rate, SpO2 and blood pressure from 3 | Large |
| 8 | Home page and the food banner | Last, because it shows things made by the other pieces | Small |

**Three things I would do first, before any building:**
1. **Reproduce "log a meal AI is broken"** and **"the scanner is not working"**. Both could be a bad setting or an AI-service problem, not a code bug, and the fix is different each time.
2. **Answer the open questions in section 12** (about 8). Three of them change what gets built.
3. **Tell Hong Yi and Damien** which of their screens are being changed (section 11).

---

## 1. Database foundations (migration 0032)

The migration number after `0031`. Check `alembic heads` first and pull, because a teammate may have used 0032. All changes add; nothing is dropped.

| Need | What exists | Change |
|---|---|---|
| Waist | `body_measurements` table exists | Use it: a waist row per save. No new column |
| Diabetes history (year diagnosed, who looks after it, Healthier SG) | Not saved | Add columns to `user_profile`: `diagnosed_year`, `care_setting`, `healthier_sg` |
| Low glucose history (hypos in the last 3 months, symptoms) | Not saved | Add `hypo_last_3m`, `hypo_symptoms` to `user_profile` |
| Conditions, allergies | Saved only as one text note (`conditions_note`, `allergies_note`) | Use the existing `conditions` and `allergies` tables, one row each; keep the note as a copy for the brief |
| Last check dates (eye, foot, kidney, flu, ...) | `patient_preventive_status` exists | Write to it from onboarding |
| Lab results (HbA1c, fasting glucose, insulin, cholesterol) | `lab_results` exists, onboarding does not write it | Write to it, with the lab date |
| Blood pressure | `blood_pressure_readings` exists, no screen writes it | Written from the new Log screen (piece 3), no migration |
| Devices (watch, sensor) | `devices` exists; profile has `watch_model`, `cgm_model` | Write a `devices` row when the connect screen is finished |
| Work week | `work_type`, `work_days`, `work_start`, `work_end` already saved | None |
| Emergency contact, all four fields | Saved | None |
| Reminder email | `notification_email` (0031) | None; only the screen moves |
| Medicine stock | Not saved | Add to `medications`: `stock_count` (numeric), `stock_unit`, `stock_updated_at`; add table `medication_stock_events` (id, user, medication, change, reason: `purchase`, `dose_taken`, `manual_set`, at) so every change can be explained |
| Heart rate and SpO2 insights | `watch_readings` and `health_samples` exist | None; read them |

**Rules to keep:** event log holds ids and counts only; soft delete stays; the migration is written so it can run on the shared database without losing data, and the tests in `services/api/tests/db` get a case for each new column.

---

## 2. Onboarding rewrite (screens A1, A3, A6, and the chat A4)

### 2.1 How I read your numbered list

Your numbers follow the "Step N of 12" counter on screen (Welcome = 1, Eligibility = 2, About you step 1 = 3, and so on). The new flow:

| New | Was | What changes |
|---|---|---|
| **1 Welcome** | 1 Welcome, and 12 Email | Remove the **language** choice. Add the **email address** here (moved from step 12), with validation. Keep name and consents |
| **2 Eligibility** | 2 | Unchanged |
| **3 About you** | 3 | **Sex: Male or Female only.** Add **waist** (cm), saved to the database. Birth year, height, weight stay |
| **4 Diabetes history** | 4 | All answers saved to the new columns |
| **5 Medicines** | 5 | **Only "Scan a label".** Remove the "diabetes medicines" and "other regular medicines" tick lists and the fixed "already in your list" text. Shows the medicines scanned so far |
| **6 Low glucose** | 6 | Saved. The long hypo description becomes a **small "i" tooltip** |
| **7 Other conditions and checks** | 7 | Saved to `conditions`, `allergies`, `patient_preventive_status` |
| **8 Lab results** | 8 | Remove **kidney (eGFR)** and **blood pressure**. I check every remaining field has a column and is saved |
| **9 Devices** | 9 | A **connecting screen**: choose a watch or sensor, shows a "Connecting" state and a result (connected, not now). Remove "do you feel regularly" and "good times for reminders" |
| **10 Your work week** | 9's work-day block | The work day questions move here (see question Q1). The old lifestyle page 10 is removed |
| **11 Emergency contact** | 11 | Only the emergency contact. Remove the red-flag symptom tick list. **All four fields required** (name, relationship, phone, email) with validation |
| ~~12 Email~~ | 12 | Gone; moved to step 1 |
| **Summary** | A6 | Updated for the new steps; editing a section opens the right step |

The chat set-up (A4, built by Hong Yi) asks the same questions in a chat. It needs the same list changes (no language, sex M/F, scan only, no kidney/BP). That is his code, so **tell him before changing it**.

### 2.2 Making it "linked" (checking old data and new users)

The problem you described: answers stay in the browser (`smart-health-onboarding`), so a new user can see the last person's answers, and the database is not the source of truth. Plan:
1. **Key the saved answers by user** (`smart-health-onboarding:<user>`) and clear them when the user changes or a new user starts.
2. **The database is the source of truth.** On opening onboarding, the app calls `GET /onboarding`, fills the form from it, and falls back to the device copy only when the server has nothing.
3. **Save at the end of every step**, not only at the end, so closing the app loses nothing. `PUT /onboarding/profile` grows to take the new fields (waist, diabetes history, hypo answers, conditions, allergies, checks, labs, devices).
4. **A "new user" path**: `UserSwitch` gets a "Start as new person" action that creates a clean user, clears the device copy, and starts at step 1.
5. **Tests:** switching users shows no old answers; a field typed in step N is in the database before step N+1 opens.

### 2.3 Files

`features/onboarding/{Welcome,AboutYou,Summary,useOnboarding,api,options,parts}`, `features/onboarding/chat`, `services/api/app/{schemas,services,api/routers}/onboarding.py`, new migration, tests in `services/api/tests`.

---

## 3. Blood pressure logging, and moving Log into Food

### 3.1 Blood pressure (new)
- **New Log tile "Blood pressure"** and screen: top number (systolic), bottom number (diastolic), optional pulse, date and time (defaults to now). Checks: both numbers or neither, bottom lower than top, ranges 60 to 260 and 30 to 150. No "normal" wording.
- Saved to `blood_pressure_readings` (`POST /logs` with a new kind, or a small `POST /logs/blood-pressure`), then the usual "Saved" screen.
- Shown in: Sleep and stress (9.5), the doctor brief, and Day. Edit and delete from the entry sheet.

### 3.2 Move "Recent entries" from Log to Insights, Food (item 8)
- **Log hub** keeps only the log tiles (meal, symptom, blood pressure, check-in, workout).
- **Insights, Food** gets the recent entries list with **full detail**: calories, carbohydrate, protein, fat, sodium, sugar, fibre, the portion, and the glucose result after the meal (rise, peak, hours). Tapping an entry opens the edit sheet.
- **Meal logging screen redesigned** (a new look for E2): photo first, the estimate as a clear macro card, portion stepper, then Start eating / I already finished. The workout "See your day" part is redone the same way (item 8 last line): a day summary card with duration, heart rate, glucose change, and a button to the Day view.
- **Fix "log a meal AI is broken".** Steps: (1) reproduce with a real photo and read the API log; (2) check the model name and the daily AI limit (`ai_usage_daily`); (3) check that `POST /meals/analyze` returns an error the screen can show; (4) fix and add a test with a stubbed model. The screen must always offer manual entry when the AI fails.

---

## 4. Medicines tab (H1 to H8)

### 4.1 Scanner not working
1. Run `scripts/scan_accuracy.py` and `scan_label.py` on a few real labels to see **which step fails** (photo quality, OCR, the model, or the 0.85 confidence rule in `scan_confidence.py`).
2. **On "lower the threshold":** this is allowed, but it is a safety rule (D-064: any low field forces manual entry). I would not just lower the number. Instead: improve the photo step (guidance text, auto-contrast, retry), and only lower the threshold for fields where a wrong value is low risk (the medicine name matched against the drug list), keeping strictness for **strength and directions**. Needs your OK, and the numbers must come from the accuracy script, not from guessing.
3. Add a clearer failure screen: "We could not read this. Take another photo or type it in."

### 4.2 Scope: diabetes medicines and daily medicines or supplements
- The add screens (scan and by hand) and onboarding step 5 are for **diabetes medicines and other daily medicines or supplements**. A medicine that is clearly outside (for example a one-off antibiotic) is not blocked but gets a note: "Equinox is for diabetes and daily medicines."
- The "only when needed" choice I added on 2026-10-06 conflicts with this. See Q3 before removing it.

### 4.3 Medicine warehouse (stock tracker)
- **What the person sees:** a "My stock" section on the Meds tab (or its own page): each medicine with **how many are left**, **days left at the current dose**, and a progress bar. Buttons: **I bought more** (enter the number or the pack size; it adds), **Change the number** (set it by hand).
- **How the number moves:** starts from the pack size at scan or entry; **goes down by one dose each time a dose is marked Taken** (so it is never guessed from the calendar); changes by hand are recorded with a reason.
- **Replaces the old refill estimate** for regular medicines (the "may run out in about N days" box now uses real stock). Never shown for as-needed medicines.
- **Data:** `medications.stock_count`, `medication_stock_events` (section 1). Endpoints: `GET /medications/stock`, `POST /medications/{id}/stock` (`{"add": 30}` or `{"set": 12}`).
- Home gets a low-stock note only when 7 days or fewer remain.

### 4.4 Wording and the explanation
- "Where this comes from" → **"Additional information"**.
- "Not an authoritative drug label" → **small grey fine print**, like terms and conditions.
- **"What it is for", made more intentional.** Rework the explainer prompt (`med_explain.md`) into four short, fixed parts: *What it is for in your diabetes*, *How it works, in one sentence*, *What you may notice*, *Why timing matters*. The same guards apply (no doses, no stop/skip/change, no "safe"; sources shown). Needs the cached explanations to be regenerated, and a review of the wording.

---

## 5. Doctor brief (L1 to L3, `doctor_report.py`)

| Item | Plan |
|---|---|
| Include the new onboarding data | Add **waist**, diabetes history, last labs, conditions and allergies, and blood pressure to the patient summary at the top of the report |
| **Key findings** easier to read, and "is it done by the AI?" | **It is not.** `_findings()` in `doctor_report.py` writes fixed sentences from the numbers (rule: no AI in the report). So "more readable" means rewriting those templates: shorter, one idea each, a label (Glucose, Medicines, Symptoms), and the number first. If you want an AI summary, that departs from rule 1.2 and needs Hong Yi |
| "Put the consolidated 4 tables and replace with the glucose, shift glucose downwards" | **Q4.** My reading: the four small summary tables at the top are merged into **one compact summary block**, and the glucose section moves **lower** on the page |
| Remove "Overnight, beside glucose" | Remove the section and `_overnight()` from the report, keep the heart rate and SpO2 under Activity and wellbeing |
| **Baseline reading from the 14-day one** | Add a **baseline** card: the first 14 days of sensor data as the reference (average, time in range, GMI), with the current period beside it and the difference worded "higher than" or "lower than", never good or bad |
| A high-level insight on **symptoms against current health values** | A single fixed-template sentence block, "Symptoms and your latest values", linking the symptoms logged to latest HbA1c, blood pressure and weight. Worded "associated with". No AI |
| Remove "doses missed" **date** | Remove the date column of missed doses; keep the count and reasons |
| **PDF → back to the app is glitchy** | L3 is outside the app frame, so "back" has no history after printing. Fix: a visible **"Back to the app"** button that goes to `/brief`, `useBack('L1')` instead of browser history, and a test for open from L1, print, return |
| Report tests | `doctor_report` unit tests updated; `test_doctor_report` fixtures for the new baseline and blood pressure |

Hong Yi built the latest brief changes ("Worth discussing", overnight heart rate and SpO2). Removing "overnight" reverses part of that work, so **ask him first**.

---

## 6. Care plan, questions, progress, "learned"

### 6.1 Care plan (K3, K7)
- Remove the **Questions for your doctor** block from K3 (it moves to its own page, 6.2).
- "Plan another appointment" → **"Log an appointment"**.
- **Add a visit** form: the kind list loses **vaccination** and **dental**; **"HbA1c" becomes "Blood test"**; remove the **Place** field. Check the server accepts the smaller set (`appointments` kinds) and old rows still display.

### 6.2 New page: Questions for your doctor
- A route (new id, for example **K12**, `/me/questions`) with: add a question, the list (newest first), each marked done or removed, the source (typed, from a medicine, from a clash alert). Linked from **Me** and from the brief.
- Uses the existing `doctor_questions` endpoints; the care plan and brief link to it.

### 6.3 How it is going (K10)
- Rename to **Diet tracking**.
- Show the **baseline score on its own** (a single card).
- **Remove "Each week".**
- Add a **calendar view**: each day coloured by the macros logged (calories, carbohydrate, protein, fat), tap a day to see the totals. Uses data from `GET /insights/food` or a new `GET /memory/progress/days`.

### 6.4 What Equinox has learned (K2)
- **"What gets in the way" becomes a dashboard KPI**: a small row of numbers (barrier counts, doses missed this week) instead of the text list.
- Remove the **"some missed doses were because of running out"** text. Also **check Mr Tan's database**: query `medication_log` and `dose_events` for `ran_out` reasons and for the adherence barrier facts in `memory_facts`; if the statement comes from a bad fact (made by the nightly learning run), delete it and fix the rule that proposed it (`agents/adherence.py`).
- Remove **"See what it did"** (the audit list) from the screen. Keep the audit data in the database.

Several of these (K2 and the adherence agent) are Hong Yi's learning loop. **Ask before editing.**

---

## 7. Insights (C1 to C6)

| Tab | Changes |
|---|---|
| **New: heart rate** | A heart rate view (resting, average, highest, by day; from `watch_readings`). Either a new tab or a block inside Activity and Sleep. See Q6 |
| **9.1 Overview** | The calendar shows **previous days** as well (a month, scrollable); rewrite the "what changed" wording so it names the range and says what moved ("Glucose in range: 62% this week, 55% last week"), and say so when nothing changed |
| **9.2 Glucose** | Keep **one** "Why am I seeing this?" (the one at the top of the screen); remove the per-chart copies |
| **9.3 Food** | Add the recent entries with macros (3.2), **KPI charts** (calories, carbohydrate, protein, fat, salt per day) and the **calendar at the bottom** |
| **9.4 Activity** | Add **heart rate and SpO2**. **Check how intensity is derived**: today it is `workout_effort.py` (age-based maximum heart rate and fixed cut-offs, placeholders) for strength sessions, and the quick log uses what the person said felt hard. I will write down exactly which rule gives which label and flag where it is a guess |
| **9.5 Sleep and stress** | Add **heart rate, SpO2 and blood pressure** (if logged). **Clean up the view**: remove the explanatory paragraphs, one chart per card, short labels. This is the "too much AI-looking text" fix |
| **9.6 Medication** | A **taken dose is solid green**; remove the legend entry for completely dark squares ("no legend for completely dark squares" is read as: give those squares a legend, see Q7); **remove the glucose chart** from this tab |

New data endpoints: `GET /insights/heart` (heart rate, SpO2) and blood pressure added to `GET /insights/sleep`.

---

## 8. Home page

- **Food banner**: a banner that shows when a meal is not logged by its usual time or when a high-salt food is flagged (reuses `MealBanner`, `FoodFlagCard`); dismissible; opens the meal screen.
- **"Fix the UI"** is not specific enough to build. I propose: show the next dose and alerts first, move lunch and food flags lower, cap the page to **five blocks**, and keep the rest under "See more". Tell me what looks wrong first (see Q8).

---

## 9. Order of work and rough effort

Effort is a guess for one person, in half-days.

| Step | Work | Half-days |
|---|---|---|
| 0 | Reproduce the meal and scanner failures; pull; check teammates are not editing the same files | 1 |
| 1 | Migration 0032, schemas, tests | 2 |
| 2 | Onboarding rewrite, summary, chat list update, per-user storage | 6 |
| 3 | Blood pressure logging, Log / Food move, meal screen redesign, meal AI fix | 6 |
| 4 | Scanner fixes, stock tracker, wording and explainer rework | 7 |
| 5 | Doctor brief changes and the PDF back button | 5 |
| 6 | Care plan, questions page, diet tracking, learned changes | 5 |
| 7 | Insights changes and heart rate | 6 |
| 8 | Home page | 2 |
| 9 | Update `app-flow-and-features.md`, session log, project memory, `verify_docs.py` | 2 |
| | **Total** | **about 42 half-days** |

Each step ends with: tests run, the app opened and checked in the browser, `verify_docs.py` passing, and **you** say "commit and push" before anything is pushed (after a `git fetch` for incoming changes).

---

## 10. Checks for the whole job

- Everything the model writes still passes the guards (no dose, no stop/skip/change, no "safe").
- Unknown stays unknown (a dash, never zero) in every new chart.
- Blood pressure and stock show no "normal", "safe", "good" or "bad".
- New fields appear in the data export (`GET /me/export`) and in the delete request.
- 390 px, 768 px, 200% text, and dark mode checked for every changed screen.
- No secrets in the repo or chat.

## 11. Who else this touches

| Area | Owner | What changes for them |
|---|---|---|
| Chat set-up (A4), chat, review (K11), learning loop, the brief's "Worth discussing" and overnight section | Hong Yi | The A4 question list, K2 and the adherence agent, and the brief sections are edited. Ask before touching; tell him what changes |
| Alerts, onboarding and report designs | Damien | Onboarding and report layouts depart from his Stitch designs (steps removed, sections moved). Show him the new flow |
| Doctor-question and care plan data | Shared | A new questions page and a smaller appointment form change what the brief shows |
| Urgent alert (F10) | On hold | Emergency contact fields becoming required means an old user with a blank contact must be asked to add one |

The scope list in memory says you own F2, F3, F4, F5, F10. **Most of this list is outside those features** (onboarding, brief, insights, home, care plan). You are the decision maker, so I will do it, but these edits are likely to hit files your teammates are changing. Pull before every step, and do the changes in small commits so conflicts stay small.

---

## 12. Questions that change the work

| # | Question | My assumption if you do not answer |
|---|---|---|
| Q1 | Step 9 says "shift work day to the next step", then step 10 says "remove page 10". Do you want **a short "Your work week" page** replacing the old lifestyle page, with the other lifestyle questions dropped? | Yes, as in the table in 2.1 |
| Q2 | Step 2 says "gender: only male or female". Gender is in "About you" (step 3). Is that the field? Do we **drop the "Other" and "Prefer not to say"** options? | Yes, drop them |
| Q3 | Medicines scope is "diabetes and daily medicines or supplements". Should the **"only when needed"** choice (for example paracetamol) **be removed**? | Keep it for now, hidden from the scan and onboarding path |
| Q4 | Doctor brief: "put the consolidated 4 tables and replace with the glucose, shift glucose downwards". Is it: merge the four top tables into one summary block, and move glucose lower? | Yes |
| Q5 | Doctor brief key findings: keep them **code-written** (no AI), only rewritten to be clearer? | Yes, no AI |
| Q6 | Heart rate: a **new Insights tab**, or a block inside Activity and Sleep? | A block inside Activity and Sleep, plus a small card on Overview |
| Q7 | Medication tab: "no legend for completely dark squares". Do you want a **legend added** for them, or those squares **removed**? | A legend added ("No dose due") |
| Q8 | "Home: fix the UI". What looks wrong: too many cards, the order, the colours, or something else? | Order and number of cards (section 8) |
| Q9 | Scanner: are you happy to **lower the confidence threshold only for the medicine name**, and keep strength and directions strict (a safety rule)? | Yes |
| Q10 | Is the blood-pressure reading **manual only**, or should it also come from a connected cuff? | Manual only |

Anything not answered goes ahead on the assumption in the right column, and I record it as a decision in the project memory.

---

## 13. Decisions from Joely (2026-10-11), these override the sections above

1. **Database.** Onboarding answers go into the user tables (`user_profile` and the existing tables), and only the onboarding answers are shown in the doctor report. Medicine stock is added **to the `medications` table itself** (no separate stock-events table): `stock_count`, `stock_unit`, `stock_updated_at`. Changes are still recorded in `event_log` as ids and counts only.
2. **Onboarding.** Steps are renamed **1 to 7** (the counter on screen counts only the steps people see). "Start as new person" is wanted.
3. **Logs.** Blood pressure is a log type and uses the existing `blood_pressure_readings` table. The meal page must read photos reliably; the model may be **upgraded** to find out why it is broken. Rendering must be **dynamic to the device type** (phone, tablet, laptop).
4. **Medicines.** The confidence threshold for the **medicine name** becomes **0.6** (strength and directions stay strict). The "only when needed" choice is **removed** (Q3). Everything else in 4.x stands.
5. **Doctor brief.** **Key findings are written by AI**, with an **"AI insight" note** on the report (this departs from rules.md 1.2 and 1.8; the numbers still come from code and are checked against the computed facts). The rest of section 5 is added. **The four top tables and the position of glucose are left open** (Q4: not changed now, so Joely can decide later).
6. **Care plan and Me, Insights, Home.** As written. Heart rate is a block in both Activity and Sleep (Q6). A legend is added to the Medication squares (Q7). Home: order and number of cards (Q8). Blood pressure is manual only (Q10). Q1, Q2, Q5, Q9 as assumed.
7. **Team.** Joely says all members are aware of the changes to their areas.
## 14. Status 2026-10-11 end of day

**What "built" and "verified" mean here.** *Built* = the code is on disk in the working tree (not committed; the owner commits and pushes). *Verified* = a check run on 2026-10-11: the API unit tests (1,628 passed, `python -m pytest tests/unit -q`) and the web typecheck (`npm run typecheck`, clean). *Not run* = the database tests, the live model, the browser at 390 and 768 px, 200% text, and dark mode. Nothing here has been committed or pushed.

**Migrations.** 0032 to 0036 are in `services/api/alembic/versions`. **Applied on 2026-10-11 by the owner's approval** (`alembic current` is `0036`; the docs pass did not run Alembic). Each new column is still checked at run time.

### 14.1 Piece by piece

| Item (plan section) | Built | Verified | Open |
|---|---|---|---|
| **1. Database foundations** (0032 to 0036, section 1) | Migration 0032 (onboarding answers, stock columns, body measurements, conditions, allergies, devices); 0033 (explanation parts); 0034 (`vertex_generate`); 0035 (blood pressure id, pulse, note, updated time); 0036 (workout rating optional). No `medication_stock_events` table (decision 13.1) | Unit tests for the history, stock and blood pressure code pass | Apply the migrations to the shared database. Run the database tests (`tests/db/test_onboarding_history_db.py`, `test_medication_stock_db.py`, `test_blood_pressure_store.py`, `test_insights_heart_db.py`, `test_care_questions.py`, `test_workout_medicines_db.py`, `test_memory_reads.py`, `test_med_explain_route.py`). Add a database test for each new column, as the plan asked |
| **2. Onboarding** (section 2) | Eleven pages (Welcome with email, Eligibility, About you with waist and sex male or female, Diabetes history, Medicines scan only, Low glucose, Other conditions and checks, Lab results without kidney and blood pressure, Devices with a Connect step, Work week, Emergency contact with all four fields required). Answers saved page by page. Device copy keyed by person. Server read first. "Start as new person" (`POST /users`). Mr Tan read only. Chat set-up (A4) asks 33 questions; sex is male or female only | Unit tests (`test_onboarding.py`, `test_onboarding_chat.py`, `test_onboarding_history.py`, `test_users.py`) pass. Typecheck clean | The counter still reads "Step N of 11" (decision 13.2 asked for 1 to 7). The switch-user test (no old answers shown) and the field-saved-before-next-page test are not run. Browser check not done. The plan's step 9 asked to remove the "good times for reminders" and "feel regularly" questions: not verified against the code |
| **3. Blood pressure and Log / Food** (section 3) | Blood pressure is a log type (E3), manual only (Q10), with the checks in the app-flow spec; edit and delete from the entry sheet; Sleep card on Insights; doctor brief section. Log hub without recent entries; Food tab with recent entries and full detail; meal screen redesigned (`features/log/meal/`); model error codes shown on the meal screen | Unit tests (`test_blood_pressure.py`, `test_meal_analysis.py`) pass | Blood pressure is **not** on the Day view (the plan asked for it; `features/day` is unchanged). Meal photo reliability is not verified (no live run; the model setting is unchanged). Layouts for phone, tablet and laptop (decision 13.3, dynamic rendering) are not checked |
| **4. Medicines** (section 4) | Name threshold 0.6; strength and directions stay at 0.85 (D-083). Review tick for a name below 0.85. "Only when needed" removed from the new-medicine screens (D-084). Scope note on the add screens (`GET /medications/scope`). My stock: count from the pack size, down on every taken dose (including "I took it, forgot to log"), "I bought more", "Change the number", Running low at 7 days. Refill uses the stock when a count is set. "Additional information", fine print, and the four-part explainer (prompt version 2) with the older-layout rule | Unit tests for scan confidence, scan API, medicine scope, medication stock and the explainer pass | The scan was not run again on the five real labels after the threshold change. Photo-step improvements (retry, auto-contrast) not verified. **A Home low-stock note (7 days or fewer) is not built.** Clinical review of the four-part wording. Database stock tests not run |
| **5. Doctor brief** (section 5) | AI-worded key findings with the "AI insight" note and a code fallback (D-081; departs from rules.md 1.2 and 1.8). Health summary from the onboarding answers. 14-day baseline card. Blood pressure section. Symptoms and latest values. Overnight section and missed-dose dates removed. Back to the app button | Unit tests (`test_doctor_report.py`, `test_doctor_report_brief.py`, `test_report_insight.py`) pass | The four top tables and the glucose position are **left open** (decision 13.5, D-091). The report has not been run against the shared database in this pass (`load()`). Hong Yi to confirm the AI key findings and the removal of his overnight section. The back button after printing is not checked in a browser |
| **6. Care plan, questions, progress, learned** (section 6) | K3: questions block moved to K12 (a new page); "Log an appointment" (K7); kinds without vaccination and dental; "Blood test" for HbA1c; no Place field. K10: renamed Diet tracking, one baseline card, month calendar of macros, "Each week" removed. K2: a row of numbers (barrier KPIs), audit list removed | Unit tests (`test_care.py`, `test_memory_progress.py`, `test_diet_days.py`, `test_barrier_kpis.py`) pass | The "some missed doses were because of running out" statement is still written by `agents/adherence.py` (the rule is not changed). Only the `barrier.ran_out` fact is hidden on the screen. Mr Tan's database was **not** checked for the ran-out facts (plan 6.4). This is Hong Yi's learning loop: ask before editing |
| **7. Insights** (section 7) | Overview: month calendar, with earlier months; the what-changed wording names the measure and both periods. Glucose: one Why link. Food: macros per day, recent entries with detail, calendar at the bottom. Activity and Sleep: heart rate and SpO2 block (`/insights/heart`) and blood pressure card (`/insights/blood-pressure`). Medication: taken is solid green, "No dose due" in the legend, glucose chart removed. Effort rules written down (workout-tracker.md section 4, insights.md) | Unit tests (`test_insights.py`, `test_insights_heart.py`) pass | Heart rate is a block, not a tab (decision 13.6, Q6). The Sleep page copy cut-back was not checked line by line. Browser check not done |
| **8. Home** (section 8) | Five blocks at most, the rest behind See more; food banner (`GET /home/banner`); "Start here" for a new person; alert strip first | Unit tests (`test_home_banner.py`) pass. Typecheck clean | **Low-stock note on Home: not built.** Decision 13.6 (Q8, order and number of cards) is built as proposed |
| **9. Documentation** (section 9 of the plan) | `app-flow-and-features.md`, `flow.md` banner (kept), `f2-scan.md`, `f3-explainer.md`, `f12-doctor-report.md`, `insights.md`, `learning-loop.md`, `workout-tracker.md`, `f5-clash.md`, this section, project memory, the session log | `python scripts/verify_docs.py` (the session log has the result) | The database and browser checks above |

### 14.2 Cross-cutting checks (section 10 of the plan)

| Check | State |
|---|---|
| Model text passes the guards (no dose, stop, skip, change, safe) | Guards unchanged. The key findings have their own checks (D-081). Not re-tested live |
| Unknown stays unknown (dash, never zero) in new charts | Written into the code and docstrings of the new services. Not checked on screen |
| Blood pressure and stock use no "normal", "safe", "good" or "bad" | Written into the code. Wording checked by reading only |
| New fields appear in the data export and the delete request | **Not done.** The export does not yet cover the onboarding history, blood pressure or the stock count (app-flow section 11). The delete request is unchanged |
| 390 px, 768 px, 200% text and dark mode | **Not checked** |
| No secrets in the repository or chat | The docs were written from the code. No `.env` value was printed or written. The docs check looks for keys in the tracked files |

### 14.3 Decisions and open questions

Decisions Joely made on 2026-10-11 are in section 13 above. In the project memory they are recorded as D-081 to D-093, all **Pending** until Joely confirms them (the assistant does not mark them confirmed). Section 13 item 7 (team aware of the changes) is Joely's own statement and is not verified.

Open questions for Joely: the four top tables and the glucose position (D-091); whether the counter should show 1 to 7 (decision 13.2); the Home low-stock note; the Day view marker for blood pressure; the export of the new tables.

Open questions for Hong Yi: the AI key findings in the doctor brief (D-081); the learning-loop rule that writes "because of" and counts all time with no window (`agents/adherence.py`), and the Mr Tan check; the chat set-up gender list (male or female only); the clash summary wording (on the alerts page and the details page); refill reminders that now follow the stock.

Open questions for Damien: the onboarding and report layouts depart from his designs (the steps, the sections moved, the overnight removal, the AI wording). His review of the alerts page and the report is still needed.

### 14.4 Fix wave and QA wave (evening of 2026-10-11)

After the morning status (14.1 to 14.3), the work was checked again in three steps: **builders** (Haiku agents) changed the code; a **checker and orchestrator** (Sonnet) reviewed each change against section 13 and the agent rules; **five QA agents** (Haiku) exercised the flows as the three kinds of user (a blank new user, Mr Tan, a user with no consent, no medicines or no email); and **two design critics** (Sonnet) reviewed the layouts at phone, tablet and laptop widths. Docs were then brought up to the code by a separate docs pass (this section and the files it names).

**Results of the checks** (quoted from the run; not re-run by the docs pass):
- API unit suite: **1,687 passed**.
- Web typecheck: **0 errors**. Production build: OK.
- Database tests: all pass **except `test_only_the_demo_patient_remains`**, which expects 1 user while the shared database has 2. This failure was already there before this pass.
- A full database-suite run once took **over three hours** because of database contention. It is being re-checked; no result is claimed here.

**Migrations 0034, 0035 and 0036** are applied on 2026-10-11 by the owner's approval (section 14.1).

**Fixed in the fix and QA waves** (each confirmed in the code on disk):

| Area | What was fixed |
|---|---|
| AI limits | Per-kind caps (vision 300, text 500, embeddings 2,000, JEV 500). The label scanner's reads count under the photo cap, and a refused read returns `daily_limit`. Onboarding chat reads and brief findings count under text |
| Workouts | Rating and feeling optional (null is not rated, never moderate). Heart-rate coverage uses the real sampling interval (`sampling_interval_s`). Beta-blocker rule wired on `POST /workouts` (placeholder list). "Estimated from your heart rate" label. Unrated workouts are not counted toward active minutes, and the Saved summary says so |
| Onboarding | Still 11 pages and "Step N of 11" (owner: keep 11). A reminder email typed before a profile exists is held and saved with page 3 or Finish (`PUT /notify/email` answers 409 until the profile exists). A new person (`person-` key) is sent to onboarding at `/` until setup is finished (`startGate.ts`). Chat set-up has 33 questions with "You can leave this one blank" |
| Care plan | One next-visit rule (planned, not cancelled, now or later), shared with the brief. Past visits listed as "Past" under Earlier visits. Share sheet line about the Privacy consent. Adherence is a dash when nothing was answered. Device names mapped. The report's `simulated` flag |
| Medicines | Sources de-duplicated by site and honest labels (`web_sources.py`). Refill wording shared (`medicineText.ts`). Clash polling only while a check runs (3 seconds). "Photo not read" alert title. "We could not update this information" alert. 404 with a plain sentence when there is no reliable page |
| Insights and Day | Medication counts prescription medicines only; others read "Not counted in adherence". Overview calendar reads each day's logs (a dash when nothing is logged). One "Why" link per tab. Phone dose grid shows 14 days. Day view has a blood pressure lane. "Severity n of 5" wording |
| Logs | Check-in has no pre-selected values. Meal in progress and the Home banner's dismissal are per person on the device. Typed calories are kept and labelled "Your number" or "Your numbers". Workout minutes, reps and weight start empty. One lunch reminder slot a day across both writers |
| Data export | Includes blood pressure, medicine stock, onboarding answers, conditions, allergies, devices, labs, doctor questions and appointments (`me_settings.py`) |
| Design | The Ask button moves into the side rail from 768 px and is a small pill above the tab bar on a phone (Home and Insights overview only). Content caps 1040 px (laptop), 720 px (tablet) and 640 px for forms (`Screen narrow`). `TileGrid` for tile lists. Centred 560 px sheets from 768 px. The Log hub's fifth tile spans the width on a phone and tablet. The secondary button is an outline |

**STILL OPEN** (not fixed in this pass):
1. `daily_summary` writes 0 for meals and exercise on a day with nothing logged. It should be empty (NULL). The Overview calendar already reads the logs, so it shows a dash.
2. Adherence counts a past-window dose nobody answered in the denominator. Whether pending doses should count is an **owner decision**.
3. Mr Tan's learning-loop rule "because of ... (n times)" counts over all time (`barrier_weeks` has no window). **Hong Yi's** rule; not changed.
4. The Ask chat can answer "I cannot check this question right now" (the fallback in `services/api/app/services/texts.py`). It is a **teammate's feature**.
5. Mr Tan's file-import labs are not in the Health summary of the doctor report.
6. Mr Tan has test-looking doctor questions ("hello"). Data, not code.
7. The demo user's data was changed by QA (name "QA Demo", onboarding answers). The contact and emails were cleared on 2026-10-11. Data, not code.
8. Calories shown before a meal is saved can differ from the value saved.
9. Three soft-deleted unrated demo workouts and some scan rows remain in the database. Data, not code.
10. K11 review copy: listed by QA; details not verified in this pass.
11. The A4 print preview was not exercised in a browser.
12. The design critics did not view the scan screens, the live workout tracker or the meal error screens live.
13. New strings have English text only; Chinese, Malay and Tamil translations do not exist for them yet.

**Not verified in this pass:** every screen in a browser (390, 768 and 1024 px, 200% text, dark mode); the live model; the four-part explainer against the live model; Alembic (not run by the docs pass); the layout rules in `app-flow-and-features.md` section 6.7 are what the code says, not what was seen.

**Decisions** for this pass are recorded as D-094 to D-103 in `project-memory.md`, all Pending until the owner confirms them.

