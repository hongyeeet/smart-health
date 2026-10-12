# Smart Health: what is built, every screen, and the flow (v2)

**Written 2026-10-10. Updated 2026-10-11 from the code on branch `dev`, twice: in the morning, and again in the evening after the fix wave, the QA wave and two design critic passes (second docs pass).** The work of 2026-10-11 and 2026-10-12 (onboarding, medicine stock, blood pressure, the doctor brief, Insights, Home, care plan, logs, workouts, the design changes, the rebuilt chat) is **committed and pushed on `dev`**. Where this file says "built", it means present in the code on disk. Database migrations are in the repository up to `0037`. **Migrations `0032` to `0036` were applied on 2026-10-11 and `0037` (layer comments only) on 2026-10-12, each by the owner's approval** (`alembic current` is `0037`). The code still checks each new column at run time. This file **replaces [flow.md](flow.md) as the description of the app that exists today**. `flow.md` still holds the original plan (journeys J1 to J15, the event catalogue and the demo script) and is kept for the planned-but-unbuilt parts. Where the two disagree, this file is right about what is built.

**What this file is for.** It lists everything that works today, screen by screen, so the app's flow and look can be redesigned and regenerated from it. Section 12 is the design brief. Everything else is facts about the current build: what each screen shows, what each button does, which server call it uses, and what is not built. It describes the **behaviour and content to keep**; it does not describe the current look, which is the thing being replaced.

**How it was written.** By reading the code (route registry, screens, services, agents, routers, migrations). The evening pass of 2026-10-11 checked each changed fact against the code on disk. Test results given for that pass: the API unit suite **1,687 passed**, the web typecheck **0 errors**, and the database tests pass **except `test_only_the_demo_patient_remains`**, which expects 1 user while the shared database has 2 (a failure that was already there). The screens were not user-tested in a browser at 390 px, 768 px, 200% text or dark mode, so layout statements in section 6.7 are what the code says, not what was seen. Section 12.1 (what is wrong with the current design) is therefore based on structure and code, not on test sessions. Open items after the fix and QA waves are in section 11.1 and in [implementation plan, section 14.4](implementation-plan-2026-10-11.md).

## Contents

1. The product in one page
2. Rules that every screen must obey
3. App structure and navigation
4. Screens, area by area (A onboarding, B home, C insights, D day, E log, F workout, H medicines, J urgent, K me, L brief)
5. The main journeys, step by step
6. Design system as built
7. Backend: endpoints
8. Backend: services, AI agents, scheduler, integrations
9. Database
10. Settings, thresholds and numbers in code
11. What is not built, on hold, or undecided
12. Design brief for regenerating the flow and the screens
13. Where things live in the repository

---

## 1. The product in one page

**Smart Health** is a companion web app for **adults with type 2 diabetes in Singapore**. It helps a person take their medicines, log meals, blood pressure, symptoms, mood, sleep and workouts, see how their glucose responds, and prepare for the doctor. It is a **hackathon build** (shared Supabase Postgres, Vertex AI Gemini, a Workato sandbox).

| Idea | Meaning |
|---|---|
| Who it is for | A person aged about 40 to 75 who is not technical. Large text, plain words, one thing per screen. Also a doctor, who gets a printable or shared report |
| Two demo people | `demo` (a blank new user who goes through onboarding) and `mr-tan` (Mr Tan, a loaded patient: CGMacros participant 046, about 90 days of history, six medicines, 563 dose rows). The switcher in the header (`UserSwitch`) sends the `X-User` header. A new person can be started on the device ("Start as new person"). There is no sign-in yet |
| What the AI does | Reads things (a medicine label, a meal photo), writes plain-language explanations and key findings for the doctor report, suggests possible medicine clashes, and answers questions in the chat. It never decides a number |
| What code does | Every number, flag, threshold, streak, chart and report figure is computed in code from the stored data |
| What it will not do | Give medical advice, tell anyone to stop, skip or change a medicine, call anything "safe" or "normal" |

### 1.1 Features that are built (by name)

| Area | Feature | Where |
|---|---|---|
| Onboarding | Eleven pages: welcome with the reminder email and consents, eligibility, about you, diabetes history, medicines (scan only), low glucose, other conditions and check-ups, lab results, devices, work week, emergency contact. Each page saves to the record. Set up by chat (A4). "Start as new person" | A1 to A6 |
| Home | Alert strip, one banner (an unfinished meal, or a food habit), dose card (or "Start here" for a new person), today's logging ring, one "for you" card. Everything else sits behind "See more" | B1 |
| Notifications | Medicine clash alerts and reminders, with filters | B2 |
| Insights | Overview (month calendar, what changed, findings), Glucose, Food (macros, recent entries, calendar), Activity (heart rate and SpO2 block), Sleep and stress (heart rate and SpO2 block, blood pressure), Medication, glucose sensor sprint, "Why am I seeing this?" | C1 to C8 |
| Day | One day on one clock, with tappable markers | D1, D2 |
| Logging | Log hub with five tiles (meal, symptom, blood pressure, mood and sleep, workout), meal by photo (redesigned), blood pressure, symptom, check-in, "Saved" screen, edit or delete an entry, lunch ideas | E1 to E8 |
| Workouts | Quick workout log (how hard it felt is optional; an unrated workout is saved and is not counted toward active minutes), live strength tracker with heart-rate effort from the server, labelled "Estimated from your heart rate" | F1, F2 |
| Medicines | List with "My stock" and a refill estimate, scan a label (name threshold 0.6), check what we read (the name needs a tick below the standard bar), dose plan (every day), add by hand, medicine detail with the four-part explanation, clash box, clash details, "why was it missed", remove a medicine | H1 to H8 |
| Urgent | Low-glucose alert (two tiers), call buttons, "I'm okay", email the emergency contact, demo trigger | J1 |
| Me | Hub with every screen listed, what Smart Health has learned (with a row of numbers), diet tracking (baseline and calendar), care plan, questions for your doctor, log an appointment, review suggestions, connected sources, language and display, privacy and consent, appointment, data and account, emergency contact | K1 to K12 |
| Doctor brief | Brief home, share by link, printable A4 report with AI-worded key findings (with a fallback), read-only page for the doctor | L1, L2, L3, `/s/:token` |
| Chat | "Ask Smart Health": a personal assistant that reads the person's own data (glucose, meals, food ideas, activity, sleep, blood pressure, medicines, symptoms they logged, doctor questions, what the app noticed) with its own guardrails: no diagnosis, no medicine advice, no verdicts, always a doctor referral for symptoms and an offer to add a doctor question, fixed pointers to Insights, Lunch ideas and Review suggestions. See [chat-guardrails.md](chat-guardrails.md). The Ask button is in the side rail on every screen from 768 px (not on the chat itself), and a floating pill above the tab bar on Home and the Insights overview on a phone | I1 |
| Background | Reminders every minute, reminder emails, nightly learning, calendar events for doses (backend built; the recipe is paused, see section 11) | scheduler |

Not built: manual glucose entry (there is no screen) and connect or disconnect for sensors and watches. See section 11.

---

## 2. Rules that every screen must obey

These come from [rules.md](rules.md), [design.md](design.md) and decisions D-0xx in [project-memory](../handover/project-memory.md). They must survive any redesign.

1. **The model writes words; code produces facts.** No AI output is a number on a chart, a threshold, a streak or a flag. One exception, decided by Joely on 2026-10-11 (D-081): the **key findings of the doctor brief** are worded by the model from numbers that code has already computed. Every number in the wording is checked against those facts, and the code-written findings are shown when the wording does not pass. This departs from rules.md 1.2 and 1.8 and waits for Hong Yi to confirm (section 11).
2. **Never advice.** No "stop", "skip", "change", "take more", "safe", "normal", "abnormal", "caused by". Use "associated with", "higher than your usual", "may", "please check with your pharmacist or doctor".
3. **"Not checked" is never "safe".** A medicine or product the system could not look at shows a "Not checked" badge. A check that could not finish says so ("This is not the same as all clear").
4. **Unknown stays unknown.** A missing value is a dash, "No data yet" or a hatched gap, never zero, and a chart line is never joined across a gap.
5. **Estimates are labelled.** Anything read from a photo or worked out from a model is shown as an estimate until the person confirms it.
6. **The person decides.** The system only proposes; "What Smart Health has learned" lets the person confirm, reword or delete each idea. A deleted idea is never proposed again.
7. **Scan fields:** when a scanned field has low confidence the person must go to manual entry (D-064). The medicine name is the one exception: it has a lower bar (0.6), and a name below the standard bar must be ticked on the review screen (D-083). A scan is pure extraction (D-070): the AI does not add what the label does not say.
8. **Privacy.** Patient name, NRIC, phone and address on a label are masked on the device before anything is stored. The event log holds ids, counts and enums only, never names or free text. A shared doctor link shows name, sex, age and diagnosis, nothing else.
9. **Soft delete.** Removed medicines get `deleted_at`; they disappear from every screen and keep their history. The event log is append-only.
10. **Plain language, units always shown** (mmol/L, mg, min, mmHg), sentences short, one main action per screen.
11. **Safety copy is fixed.** The low-glucose alert and the clash sentence use fixed wording (sections J1 and H1/H5). Do not rephrase them with AI.
12. **Placeholders are labelled.** Any threshold not reviewed by a clinician says so on screen ("These limits are placeholders and have not had clinical review").
13. **Accessibility.** Text scale 100% or 200%, light and dark, touch targets 48 px or more, status never by colour alone (icon plus word), `ink3` text only at 16 px or larger.
14. **Blood pressure and stock never get judgement words.** A reading is never called high, low or normal. A stock count says how many are left and the days at the current dose, never "good" or "bad".

---

## 3. App structure and navigation

### 3.1 The frame (Shell)

| Part | Behaviour |
|---|---|
| Mobile (below 768 px) | Content column (at most 480 px wide), **bottom tab bar** with five tabs: **Home** (`/`), **Insights** (`/insights`), **Log** (`/log`, centre button with a plus), **Meds** (`/meds`), **Me** (`/me`) |
| Tablet and laptop (768 px and up) | **Side rail** instead of the bottom bar (96 px wide from 768 px, 240 px with labels from 1024 px). The page is no longer a 480 px column: each screen centres its content within a width cap (section 6.7) |
| Device frame | An optional 390 x 844 phone frame for demos (setting in the demo panel; the frame is used only on a window at least 1000 px wide and 700 px high) |
| Ask button | Opens the chat (I1). From 768 px it sits at the foot of the side rail on **every screen that has the rail** (all except setup and the urgent screen, and the chat itself). On a phone it is a small pill that floats above the tab bar and steps aside while the page is scrolled down, shown on **Home (`/`) and the Insights overview (`/insights`)** only, so it does not cover forms. The page keeps room for it at its end (`--ask-space`) |
| Screen wrapper | `Screen` (page padding, optional tab bar space, `tone="urgent"` for J1, `narrow` for forms: 640 px), `Header` (title, back arrow, `backTo` route id, optional sub-title and trailing item), `Footer` (sticky action area), `Split` (two columns from 1024 px), `Reveal` (fold-away), `TileGrid` (a list of tiles: one column on a phone, two on a tablet, three on a laptop, equal heights) |
| Sheets | Bottom sheets (`Sheet`) opened with `go(id, { sheet: {...} })`; from 768 px they are centred and 560 px wide. Registered sheets: **E7** entry, **C7** why, **D2** marker, **L2** share, **H7** missed dose |
| Outside the frame | `/brief/a4` (printable report) and `/s/:token` (doctor's shared report) have no tab bar |
| User switch | `UserSwitch` in the header of Home, Meds and Me. Switches between `demo`, `mr-tan` and any new person. "Start as new person" creates a new person (`POST /users`), clears that person's device copy and opens onboarding at page 1 |
| Navigation helper | `useGo()` takes a route id (`go('K3')`), so screens never hard-code paths. The registry `app/routeIds.ts` is the single list of screens |

### 3.2 Persisted client state (`smart-health-ui`)

`theme` (light, dark, system), `textScale` (1 or 2), `locale` (en, zh, ms, ta; the locale files exist per language and area, and the screens are English text), `userKey` (`demo`, `mr-tan` or a new person's key). A live workout session is also held on the device. Translations exist for the Insights, Log and Me areas in Chinese, Malay and Tamil (`i18n/locales/<lang>/<area>.json`); the other screens show English text.

Onboarding answers are kept on the device under **`smart-health-onboarding:<user>`**: one copy per person, so one person's answers never show for another. The copy is kept only while the data-use consent is on. The database is the source of truth: the form reads `GET /onboarding` first and uses the device copy only for a field the server has nothing for. The old unkeyed copy is removed when the app loads. Mr Tan's onboarding is read only.

Other device copies, **one per person** so one person's choice never shows for another: a meal in progress (`smart-health-meal-in-progress:<user>`, see E2) and the Home banner's "Not now" choices for the day (`smart-health-home-banners:<user>`). The "See more" choice on Home is kept per device (`smart-health-home-more`). A reminder email typed before the profile exists is kept by the screen and saved once the profile exists (see A3).

### 3.3 Reachability map (what links to what today)

```
Launch
 ├─ A1 Welcome ─ A2 Eligibility ─ A3 About you (pages 3 to 11) ─ A6 Summary ─ B1 Home
 │      └─ A4 Set up by chat (the same questions, in a chat) ─ A3 form or A6
 └─ Tabs
    ├─ B1 Home ── B2 Notifications and alerts ── H5 Possible interaction
    │          ├─ E8 Lunch ideas · F1 Log a workout · D1 Day · C2/C4 Insights · H7 Missed sheet
    │          └─ J1 Low-glucose alert (banner, demo link)
    ├─ C1 Insights ── C2 Glucose · C3 Food · C4 Activity · C5 Sleep and stress · C6 Medication
    │               ├─ C8 Sprint (also from K4) · C7 Why? sheet · D1 Day
    │               └─ I1 Ask Smart Health (Ask button)
    ├─ E1 Log ── E2 Meal · E3 Blood pressure · E4 Symptom (red flag → J1) · E5 Check-in
    │          ├─ F1 Workout (→ F2 live) · E7 entry sheet → E6 Saved
    ├─ H1 Meds ── H2 Scan → H3 Review → H4 Plan · H8 By hand · H6 Detail · H5 Clash detail · My stock sheet
    └─ K1 Me ── K2 Learned · K10 Diet tracking · K3 Care plan (→ K7 Log an appointment)
               ├─ K12 Questions for your doctor · L1 Brief (→ L2 share, L3 A4)
               ├─ B2 Reminders · K4 Sources · K5 Language · K6 Privacy · K8 Data · K9 Emergency contact
               └─ K11 Review suggestions · A1 Set up again
```

Resolved on 2026-10-11: **K1 (Me) lists every screen** (13 rows, in `features/me/Me.tsx`), so no built screen is orphaned. Only K7 is reached from another screen (K3), and K12 is on the Me list as well as from K3 and L1. The Me page is still a flat list; see section 12.1.

---

## 4. Screens, area by area

Format for each screen: **route · reached from · what the person sees · what the buttons do · states · data**. "Hook" names are in `apps/web/src/data/hooks.ts`. The route list and short notes for every screen are in `apps/web/src/app/routeIds.ts`.

### 4A. Onboarding (A1 to A6)

Folder `features/onboarding/`. The answers are saved to the record **one page at a time**: Continue saves the page (`PUT /onboarding/profile`) and then moves on. A save that fails keeps the person on the page with the reason in plain words. The next press is "Continue anyway", which moves on with the answers kept on this device. The step counter reads "Step N of 11" (eleven pages; the owner confirmed on 2026-10-11 to keep eleven, see section 11).

**Reminder email before a profile exists.** The profile row is created by the first save, and the server refuses the email before then (`PUT /notify/email` returns 409). So an email typed earlier is kept by the screen and saved with **page 3** (the first About you page), with **Finish**, or in the chat with its first save, whichever comes first.

**Who sees setup.** A person started with "Start as new person" (their key begins `person-`) is sent to onboarding at `/` until setup is finished, that is until the data-use consent is on **and** the profile exists (`features/onboarding/startGate.ts`). The demo user and Mr Tan are never sent there.

**A1 Welcome** · `/welcome` · from app start, Me ("Set up again")
- Preferred name, the **reminder email** (optional, with a reminder on or off), and **three consents**: use my health data (**required**), share a doctor brief (optional), use my data for research (optional).
- The language choice has been removed from this page.
- A "Start as demo patient" shortcut goes straight to Home.
- Next goes to A2.

**A2 Is this app right for you?** · `/welcome/eligibility`
- Questions that stop out-of-scope people with a clear, kind message: type 1 diabetes, pregnancy, under 18. Otherwise Continue to A3.

**A3 About you** · `/welcome/about?step=3` to `?step=11` (one route; the step in the address is the page number)

| Page | Content |
|---|---|
| 3 About you | Year of birth (required to continue; adults only, 18 or over), **sex: male or female only**, ethnic group (a choice or typed in), height, weight, **waist (optional, saved to `body_measurements`)** |
| 4 Diabetes history | Year you were told you have type 2 diabetes (4 digits, not before birth, not in the future), where you usually go for care (polyclinic, GP or family clinic, hospital specialist clinic, none), Healthier SG (yes, no, not sure) |
| 5 Medicines | **Scan a label only** (H2), or add by hand (H8). Shows "Medicines saved so far". The tick lists of diabetes medicines and other medicines have been removed |
| 6 Low glucose | Hypos in the last 3 months (0, 1 to 2, 3 or more, not sure), a hypo that needed someone else's help in the last 12 months (yes or no), how well a hypo is noticed coming (1 always to 7 never). A small "i" explains what a hypo is |
| 7 Other conditions and checks | Conditions the doctor has named (multi-choice, with "none"), any other condition in words, **allergies** (substance and reaction, or none), last eye check and last foot check (within a year, over a year ago, never or not sure) |
| 8 Lab results | Date of the most recent blood test (not in the future), HbA1c (% or mmol/mol), fasting glucose (mmol/L or mg/dL), fasting insulin (µIU/mL). Kidney (eGFR) and blood pressure are no longer asked here |
| 9 Your watch and sensor | Choose the glucose sensor and the watch. A **Connect** button saves the choice ("Chosen: ... It is not paired yet") and "Not now" leaves it for later. Nothing is paired on this page. The choice is kept on the profile and as `devices` rows with no status |
| 10 Your work week | Type of work (mostly sitting, standing, physical, a mix, shifts, not working). If the person works: which days, start time and end time |
| 11 Emergency contact | **Name, relationship, mobile number and email, all four required**, with checks on the phone and email shape |

- "Check my answers" on page 11 goes to A6.

**A4 Set up by chat** · `/welcome/chat` · from A3 ("Chat instead")
- The same questions as the form, asked one at a time in a chat (`CHAT_QUESTIONS`, 33 questions in `features/onboarding/chat/steps.ts`). The work-week questions are asked only when the person works. Medicines are not asked: the screen points to Scan a label.
- Sex is male or female only. Name, whether the person has type 2 diabetes, birth year, sex and the four emergency-contact fields are required; the rest can be skipped with "skip" or "I do not know".
- Each answer is read by `POST /onboarding/chat`, which saves nothing. The model is used to read one answer; when it cannot, the person is asked again or sent to the form. The answers are saved by the normal page save.

**A5 Connect your data** · `/welcome/connect` redirects to A3 page 9.

**A6 Your profile summary** · `/welcome/summary`
- Editable read-back of every answer in sections with "Edit" for each (back to the right A3 page). Plain arithmetic only (age, BMI, unit conversions). Gaps worth raising with a doctor. **No stage, risk score, category or target** is shown.
- Finish records the data-use consent and completion (`POST /onboarding/complete`) and goes to Home.

### 4B. Home and notifications (B1, B2)

**B1 Home** · `/` · `features/home/Home.tsx`

Five blocks at most, top to bottom. Each block hides when it has nothing to say.

1. **Alert strip**: the active low-glucose alert, then open medicine clash alerts (opens J1 or B2).
2. **One banner**: an unfinished meal (Log a meal), or else the **food banner** (a meal due and not logged, or a food habit that is high in salt or sugar; `GET /home/banner`).
3. **Dose card** (`DoseCard`): the next dose or the doses due now, with **Taken** (`POST /doses/{id}/taken`) and **Tell us why** (the missed-dose sheet H7). As-needed medicines never appear here. For a new person with nothing logged, no medicines and no recent entries, this block is **"Start here"** instead of the dose card.
4. **Today's ring** (`TodayCard`): how much of today's logging is done, with the single next thing to log.
5. **One "for you" card**: to-confirm ideas (opens K2), then a lunch idea (opens E8), then a food habit worth a look. Only the first with content shows.

**See more** sits under the cards. It is collapsed by default and the choice is remembered on the device. When open it shows this week's bars and the full "what to log today" list (`ProgressDetails`) and any other "for you" cards. Layout: one column below 1024 px; from 1024 px the cards sit in two columns and "See more" spans the full width below them (section 6.7).

The banner's "Not now" is remembered for the day **per person** on this device, so one person's choice never hides the banner for another.

Header: greeting and date, **bell** (opens B2; the count is unread reminders plus open medicine alerts), UserSwitch. A demo-only "Simulate a low reading" link appears for the `demo` person only.

Not on Home: a low-stock note (the stock count shows on H1 only; see section 11).

**B2 Notifications and alerts** · `/notifications`
- **Clash alert cards** first (open alerts): tag "Medication review", time raised, the two medicines with a "Possible interaction" marker, the fixed sentence, the note that this does not mean the medicines are unsafe, and the buttons **Review interaction** (H5), **Contact clinic** (says there is no clinic number yet), **Ask a question** (typed question saved to the doctor questions, K12) and **Dismiss for now and add to my doctor questions** (hides on this device, with Restore).
- **Reminders list**: each opens its screen (a meal reminder opens E2, a check-in E5, a lunch reminder E8, a refill H1). Filter chips **All / Medicines / Reminders**, "Mark all reminders as read", "Not for me" on a reminder. `POST /notifications/{id}/open` and `/dismiss`.
- Empty state when there is nothing.

### 4C. Insights (C1 to C8)

Folder `features/insights/`. A **tab strip** at the top of every insights screen switches between Overview, Glucose, Food, Activity, Sleep, Medication. A **period control** sits under it. The period ends on the latest day that has data. No AI is called on these screens; findings are worded "associated with" and labelled unverified.

| Screen | Path | What it shows |
|---|---|---|
| **C1 Overview** | `/insights` | **Your month**: a calendar with one square per day for the measure picked (glucose in range, meals logged, active minutes, sleep, stress, doses taken). It opens on the month of the latest day with data, moves by arrows and never goes past the current month. Darker means more; a dash means no data. Meals and active minutes are read from each day's logs, so a day with nothing logged is a dash and never a 0; the other measures come from the daily summary. Tapping a day opens D1. The tab has one "Why am I seeing this?" link at its top. **What changed**: names the measure and both periods ("Glucose in range: x this week, y in the last N days"), and says when nothing moved much. **What your history shows**: findings from the nightly job, each needing at least 5 matching events |
| **C2 Glucose** | `/insights/glucose` | Time-in-range bar (five bands), average, estimated A1c (GMI), ups and downs (CV), sensor worn %. Morning (fasting) glucose by day with the person's usual range. Average glucose by day. Link to the sprint (C8). **One** "Why am I seeing this?" link at the top; the per-chart copies have been removed |
| **C3 Food** | `/insights/food` | **Day by day**: calories, carbohydrate, protein, fat and salt per day (one measure each, a gap when a day has no value; no goal lines). **What your history shows** (findings). **How foods moved your glucose** (rise in the 2 hours after each food, gentlest first; a food needs 2 or more logs with the sensor on). **Recent entries**: meals first with the full detail (dish, time, the macros, salt and sugar notes, the glucose response after the meal); other kinds as short rows. Tapping an entry opens the edit and delete sheet (E7). A **calendar** of the macros for each day sits at the bottom; tap a day for its meals |
| **C4 Activity** | `/insights/activity` | One card with four visuals (steps by day with "this period vs your usual" as one box, what you did, heart rate with hover for the average and resting value of a day, blood oxygen); then the minutes-by-effort bars (7 days: a bar a day, 30 days: the last 4 calendar weeks, 90 days: the last 3 calendar months; light yellow with dots, moderate green, vigorous orange with stripes; the number above a bar is its total, point at or tap a bar for the three parts) beside "What your history shows"; then recent workouts (first 3, a green "See more" link for the rest). The goal rings and the "Log a workout" button were removed on 2026-10-12 (the weekly goals were fixed placeholders nobody could change; Home's "This week" card still uses them). Only rated workouts count toward the minutes; an unrated one is listed as "not rated". Note: "Light, moderate and vigorous are as you rated the effort, not from your heart rate." |
| **C5 Sleep and stress** | `/insights/sleep` | One card in two rows of two on a laptop (one column on a phone and tablet, same order): **Sleep** (two tiles, Average hours and Nights under 6 hours, above the nightly line chart, which grows to match the row), **Watch readings** (blood oxygen above heart rate: average, resting, highest and lowest, a hover chart of both lines), **Mood and stress** (ONE chart with two lines on a 1 to 5 axis, one hover readout for both, an average line, and "Stress was 4 or 5 on N of M days"), **Blood pressure** (one range bar per logged reading, bottom number to top number, placed by date and time; tap or hover for the numbers; no bands, nothing judged; no "Log blood pressure" button here). Below the card, "What your history shows" (the findings, two side by side on a laptop). "Your usual" was removed on 2026-10-12. |
| **C6 Medication** | `/insights/medication` | Day-by-day grid for each medicine: **taken (solid green)**, taken late, not confirmed, missed, and **"No dose due"** (the legend shows all five). On a phone (below 640 px) the grid shows the latest 14 days; from 640 px every day in the period. Adherence counts **prescription medicines only**; a non-prescription row shows "Not counted in adherence". A dose whose time has passed and that nobody answered counts as not taken. With nothing answered there is no percentage (a dash). Why doses were missed, and "Open my medicines" (H1). **The glucose chart has been removed from this tab** |
| **C7 Why am I seeing this?** | sheet | Per-chart explanation: what it shows, where the data comes from, what it cannot tell you. Topics: week, glucose, food, activity, sleep, medication, findings, sprint |
| **C8 Glucose sensor sprint** | `/insights/sprint` | The latest 14 days of sensor data: days worn, average, GMI, CV, gentlest and biggest-rise foods. A timed sprint with start and end arrives with the sensor connection (K4) |

**Heart rate and SpO2 block** (`HeartBlock`, used by C4 and C5): the day's average and resting heart rate, and SpO2, from the watch (`/insights/heart`). It is **one block in two places**, not a separate tab (decision Q6). Its period ends on the day of the person's **last watch reading**, not on the period the other tabs use, and the screen says so when the two differ. A day without watch data is a gap. SpO2 from a wrist watch is less accurate than a fingertip meter, and the screen says so.

States on every tab: loading skeleton, error card ("We could not load this just now"), and an empty state that says what is needed.

### 4D. Day (D1, D2)

Changed on 2026-10-11: a blood pressure lane (on days with readings) and the wording on the markers.

**D1 Your day** · `/day/:date` · from C1, C3, C4, E6, E7, B1
- Header "Your day" with the date; arrows to move between days that have data; "See your latest day" if the date has none.
- **One clock**: glucose line with the person's range shaded; lanes for meals, medicines, workouts, symptoms (markers) and **blood pressure** (the lane appears only on a day with readings); then heart rate, steps, sleep and mood/stress dots. Missing data is a hatched gap and the line is broken, never joined. Mood and stress markers read "mood n of 5" and "stress n of 5". (A symptom in the recent entries reads "Severity n of 5"; the server builds that text in `logstore.recent`.)
- "Everything logged" list below the chart. Empty text: "Nothing logged for this day."

**D2 Marker detail** · sheet · tap any marker
- What the data shows around that event (for a meal: glucose before, peak and after; for a dose: taken time; for a workout: glucose change; for a symptom: nearest reading and last dose). One sentence worded from the numbers on screen, "associated with", plus "Things that happen close together are not proof that one caused the other."

### 4E. Logging (E1 to E8)

Folder `features/log/`.

**E1 Log hub** · `/log` (centre tab)
- Five tiles in two columns on a phone and tablet (the fifth, Mood and sleep, spans the full width there) and in one row of five on a laptop (one column at 200% text). Each has today's state (done, due now, or not yet): **Meal** (E2), **Workout** (F1), **Symptom** (E4), **Blood pressure** (E3), **Mood and sleep** (E5). The recent entries are no longer on this page; they are on Insights, Food (C3). There is no manual glucose entry screen (id E3 is now blood pressure; glucose comes from the sensor only).

**E2 Log a meal** · `/log/meal` (redesigned; `features/log/meal/`)
1. Take or upload a **photo** (optional description: what it is, how much was eaten). The photo comes first.
2. The photo goes to Gemini on Vertex; the screen shows "Looking at your meal…" then an **estimate card** (dish name, calories, carbohydrate, protein, fat, sodium, sugar) labelled as an estimate. A value the model cannot judge is blank, not zero.
3. The person adjusts the **portion** (stepper) or edits any number, then picks one of: **Start eating** (a timer runs so the glucose response can be measured) or **I already finished**.
4. Save goes to E6.
- **When the photo cannot be read, the screen offers typing the meal in** (the manual form). Failures come back with a code and a plain sentence: `bad_photo` (not a JPEG, PNG or WebP, empty or over 8 MB), `not_food` ("That does not look like a meal"), `model_unavailable`, `daily_limit` (the daily photo-read limit has been reached), `timeout`, `bad_response`, `save_failed`.
- Salt and sugar flags are computed in code from the numbers.
- **Numbers the person types or changes are kept as typed** and labelled "Your number"; numbers from the photo are labelled "Estimate". A value that was not judged is blank, never 0. **Open (QA):** the calories shown before save can differ from the value that is saved.
- **A meal in progress is kept per person on this device** (`smart-health-meal-in-progress:<user>`), so one person's unfinished meal never shows for another.
- Endpoints: `POST /meals/analyze`, `POST /logs` (kind `meal`), `GET /meals/response`.

**E3 Log blood pressure** · `/log/bp`
- **Manual entry only** (decision Q10). Top number (systolic, 60 to 260), bottom number (diastolic, 30 to 150, and lower than the top), optional pulse (30 to 220), the time taken (now by default; not in the future) and an optional note (up to 300 characters).
- Never says whether a reading is normal, high or low.
- Saved with `POST /logs` (kind `blood_pressure`), then E6. Edit and delete from the entry sheet E7 (`GET` and `PUT /logs/blood-pressure/{id}`).

**E4 Log a symptom** · `/log/symptom`
- Grid of **14 symptoms**; **5 are red flags** (these show a clear message and a button to J1 instead of saving first). Then **how long**, **when it started**, optional detail text. The sensor reading at that time is filled in automatically.
- Save goes to E6.

**E5 Mood and sleep check-in** · `/log/checkin`
- Title "Mood and sleep", "Thirty seconds. Tap a number for each." Four 1-to-5 ratings: **Mood**, **Stress**, **Sleep quality**, **Energy**, each with end labels. **No rating is pre-selected**: each one is tapped. Save goes to E6.

**E6 Saved** · `/log/done`
- Confirmation with the related next step: "See your day" (D1), "The related insight" (C2), "Get help now" (J1, only after a red-flag symptom), "Done" (B1).

**E7 Edit or delete an entry** · sheet from C3 Food (recent entries)
- Shows the entry; edit the fields or **Delete** (soft delete, `DELETE /logs/{id}`); a blood pressure reading has its own edit form. "See it in your day" (D1).

**E8 Lunch ideas** · `/log/ideas` · from B1 and a lunch reminder
- Up to **3 options** from the person's own history or the Singapore food database, each with the reason and a source label. Buttons **I'll have this** (opens E2) and **Not for me** (`POST /nutrition/suggestions/dismiss`).
- **One lunch reminder a day.** The "Log your lunch" reminder and the lunch ideas both write to the one lunch slot of the day; whichever is stored first takes it, so the person gets one lunch reminder, not two.

### 4F. Workouts (F1, F2)

**F1 Log a workout** · `/log/workout` (`features/workout/LogWorkout.tsx`)
- **12 kinds** of activity. **Quick log**: kind, duration, note, and two optional answers: **how hard it felt** (1 to 5, "Optional. Pick a number from 1 to 5 if you want to note it") and **how you felt afterwards** (optional). A workout can be saved without a rating. A null rating is never counted as moderate or vigorous, and an unrated workout is not counted toward active minutes. The minutes field starts empty (no default value).
- Or **Start a live session** for strength (F2). After saving: E6. A symptom shortcut (E4) is offered if the person felt unwell.

**F2 Workout tracker** · `/log/workout/live` (`features/workout/WorkoutTracker.tsx`)
- A timer; add exercises from a **library** or type one; for each exercise log **sets** with reps and weight (steppers, or bodyweight); a **90-second rest timer** starts after each set; **Finish** asks how it felt (energised, fine, tired, unwell) and a note.
- The summary shows time, sets, weight lifted and, when the server has the watch data, heart-rate effort per exercise and overall (light, moderate, vigorous), labelled **"Estimated from your heart rate: ..."**. Reps and weight start empty (no default). A session with no effort rating says it is not counted toward active minutes.
- **When no effort label is given** (`workout_effort.py`): the heart-rate data covers less than 70% of the expected samples ("Heart rate was missing for too much of this time to judge effort"), or a medicine on the person's list is a beta-blocker by generic name (wired on `POST /workouts`; the list is a placeholder, see section 11). The beta-blocker note says that heart rate is not a reliable sign of effort there, and no intensity label is shown. Missing heart rate is shown as missing, never as zero.
- **Expected samples** are counted at the person's own sampling interval: the median gap between their heart-rate samples, kept between 60 and 600 seconds (the one-minute figure is used only with fewer than three samples). Watch heart rate is stored in 5-minute buckets, so the old one-minute count would have asked for five times too many samples.
- The live session survives a refresh, and a failed upload stays on the device as "Waiting to upload". `POST /workouts` saves; `GET /workouts/week` gives this week's progress.
- **Not built:** the one-sentence model summary of a session. The workouts code makes no model call.

### 4G. Medicines (H1 to H8)

Folder `features/meds/` and `features/scan/`.

**H1 Medications** · `/meds` (tab)
- Header with UserSwitch and an **Add** area: **Scan a label** (H2), **Upload a photo**, **Type it in** (H8).
- **My stock** (`StockCard`, `StockSheet`): each **regular** medicine with how many are left, the days left at the current dose, a bar (full to empty against the last amount set or bought), and a status with an icon and a word: **Running low** (7 days or fewer), **Out**, **Not set yet** (no pack size was recorded, so the count is never shown as 0), or **Days not known**. Buttons **I bought more** (adds a number) and **Change the number** (sets the exact number). Medicines taken only when needed are not counted.
- **Refill line** (blue box, "may run out in about N days") for regular medicines only: from the stock when a count is set; otherwise from the old estimate counted from the pack start or label date. Never for as-needed medicines.
- **Clash box** (`ClashBox`, section 4G.1): shown only when two saved medicines may clash. The page asks again every 3 seconds **only while a check is running** and stops asking when it finishes.
- **The refill line wording is shared** with the other medicine screens (H6, the stock cards and the onboarding list), so one medicine reads the same everywhere.
- **Medicine cards**: name and strength, kind chip (prescription, supplement, herbal), how it is taken, next time, a **"Not checked"** badge for supplements and herbal products, a link "What it is for and side effects" (H6), and a **Remove** button that asks for an inline confirmation and then soft-deletes (`DELETE /medications/{id}`).

**H2 Scan a label** · `/meds/scan`
- Camera frame with guidance ("Use good light and keep the label flat"); capture or choose a photo. The photo is **masked on the device** (name, NRIC, phone, address) before upload, then `POST /scans`. A photo that cannot be read shows an alert titled **"Photo not read"** (on the frame and on the review screen) with the plain reason. A paused photo-read day ("Reading photos is paused for today") is one of these reasons.

**H3 Check what we read** · `/meds/scan/review`
- Shown for one clearly read medicine. Each field the scan read (name, strength, form, directions, quantity, dates) with its confidence.
- **The medicine name** is read with a lower bar (**0.6**). A name **below 0.85** needs a tick: "This is the right name", next to the name printed on the label. Other fields below 0.85 are not ticked here; any other low-confidence or missing required field sends the person to the typed form (H8), which says why (D-064).
- The person can correct any field with the pencil, then **Confirm** goes to H4. Retake the photo is offered.
- Other results (not one clear medicine, unreadable, several medicines) go straight to the typed form with a plain reason (section 8.1, scan reason codes).

**H4 Your dose plan** · `/meds/scan/plan`
- **Kind chips** (prescription, supplement, herbal). **Dose times** list with add and remove (a time per dose; the label gives no clock times, so these are suggestions). **Add to my medicines** saves (`POST /scans/{id}/confirm`) and starts a background clash check.
- **There is no "only when needed" choice.** Every new medicine is saved as a **daily** medicine. When the label says "when necessary", the screen says: "Smart Health saves it as a daily medicine, so choose the times it should appear" (decision D-084).

**H8 Add a medicine by hand** · `/meds/add`
- Same fields as H3 and H4, typed in. **No every-day or only-when-needed switch.** `POST /medications`. Used also from onboarding A3 page 5.
- A gentle **scope note** (`GET /medications/scope`): "Smart Health is for diabetes medicines and the medicines or supplements you take every day." The note never blocks a save. Supplements and herbal products are not checked against the list.

**H6 Medicine detail** · `/meds/:id`
- **What it is for** in four short labelled parts: **What it is for in your diabetes**, **How it works**, **What you may notice**, **Why timing matters** (prompt version 2). Where a part is not found in the pages read, it says "Not found in the pages we read."
- **Failures are plain.** When the search finds **no reliable page**, the answer is "We could not find a reliable page for this medicine yet. Please ask your pharmacist." (HTTP 404). When the daily limit for text is reached, it says so (429). When the model cannot be reached, "We could not look this up" (503). When an update of an existing explanation fails, the alert reads **"We could not update this information"** when an explanation was already there (otherwise "We could not look this up"), and the "Update this information" button tries again. Sources are shown once per site (by site name); openFDA is shown as a name only, with no link, because it is a data query and not a page.
- A saved explanation in the **older layout** (no four parts) says so ("This was written in an older layout. Update it to see the four short parts.") and is made again the next time the page asks for it, when the database has the new column (section 9).
- **How you take it (from your own label)**, **Side effects**, **Tell your doctor if…**, **Refill** (regular medicines only), **Additional information** (the web pages used, with links), a small grey line "Not an authoritative drug label", and "This is not medical advice". A box to add a question for the doctor (saved to K12).
- Any sentence with a dose or "stop, skip, change, safe" is removed in code (D-071). Generate or refresh via `POST /medications/{id}/explanation` (`?refresh=true` forces it); questions via `POST /medications/{id}/questions`.

**H7 Why was it missed?** · sheet from the dose card
- Answer to "Why was it not confirmed?": **I took it, forgot to log**, **I forgot**, side effects, ran out, felt fine, cost, away from home, other; optional note; Save or Skip. **"I took it, forgot to log" marks the dose taken and takes one dose off the stock.** A shortcut leads to E4 when the reason is a symptom. (Code: `features/sheets/MissSheet.tsx`.)

#### 4G.1 Clash box and clash details (F5)
- **Box (H1):** title "Medicines may clash. Check with your doctor." For each pair: the fixed sentence *"Possible interaction between X and Y. Please check with your pharmacist or doctor before continuing."*, one or two plain sentences on why, where it came from (drug-label link and/or the web pages the AI used), and "Not medical advice". Buttons **Review interaction** (H5), **Add to my doctor questions** (turns into a green "Added" state; the question appears on K12), **I have checked with my doctor** (acknowledges; the alert is kept as acknowledged). While a check runs: "Checking your medicines for clashes…". If the AI half failed and nothing else is flagged: "We could not finish checking for clashes. This is not the same as all clear." with **Check again**.
- **H5 Possible interaction** (`/meds/interaction/:id`): the pair and the fixed sentence; where the flag came from (drug-label rules, AI web search, or both) with the tag "Not reviewed by a clinician"; **Why this was flagged**; a suggested next step (ask the pharmacist or doctor to review the whole list); contact, add-question and typed-question actions; sources behind a fold.

### 4H. Urgent (J1)

Unchanged today.

**J1 Low glucose alert** · `/urgent` · from the Home banner, the red-flag symptom, the demo link
- The fixed layout. No model is involved; a reading counts only when it is a quality-ok reading no older than 20 minutes.
- **No alert state**: "No low glucose right now." and Back to Home.
- **Active alert** (red screen): status pill **Low** (below 4.0 mmol/L) or **Very low** (below 3.0), a **DEMO, not a real reading** pill for demo alerts, a big number, the sentence "Your glucose looks low: 3.6 mmol/L, 4 minutes ago", and "If you feel unwell or confused, call 995 now. Follow the plan your doctor gave you."
- Buttons: **Call 995** (large and first when very low), **I'm okay now** (acknowledge; then "Checking again in 14:59", re-check after 15 minutes), **Call my contact**, **Tell my contact now**, **Add an emergency contact** (K9) when none.
- **Countdown to the contact**: "If you do not answer in 5:00, we will email {name}." After 5 minutes unanswered the app tells the contact once (email through Workato; the server refuses a second one). If there is no contact email the screen says nobody was emailed.
- Error state keeps a plain "Call 995" button visible.
- A demo alert can be made on the `demo` user only, so a real contact is never emailed.
- Status: the screen is built; the escalation policy is **on hold pending Damien's decision (D-054)** (section 11).

### 4I. Me (K1 to K12)

Folder `features/me/`.

**K1 Me** · `/me` (tab) · a list of cards with an icon, title, one-line description and arrow, in this order:
1. What Smart Health has learned (K2), with a count of ideas to confirm
2. Diet tracking (K10)
3. Care plan (K3)
4. Questions for your doctor (K12), with a count of open questions
5. Doctor brief (L1)
6. Reminders (B2)
7. Connected sources (K4)
8. Emergency contact (K9)
9. Language and display (K5)
10. Privacy and consent (K6)
11. Data and account (K8)
12. Review suggestions (K11): "For reviewers: rate the suggestions Smart Health made."
13. Set up again (A1)

**K2 What Smart Health has learned** · `/me/learned` (`features/me/Learned.tsx`)
- **AI use today**: one line per kind of AI call (photo and label reads, text written for you, search lookups, safety checks, other AI use), with the paused note "Paused until tomorrow" when a kind has reached its daily limit (section 10).
- **What gets in the way**: a row of numbers (`BarrierKpis`, from `GET /memory/barriers/summary`): doses missed this week (out of the doses scheduled), doses taken on time (over the last 30 days, of the confirmed doses), the most common reason for a missed dose, and confirmed ideas waiting for the person. No data shows a dash and "No data yet".
- **This week** (digest of what it did) and **Suggestions it is learning from**.
- Ideas grouped by kind; each card shows what was noticed, **why** (evidence), and actions: **That is right**, **Change it** (or **Say it your way**, a text box that saves the wording), **Delete** (never proposed again).
- The **audit list ("See what it did") has been removed** from this screen; the audit data is kept in the database.
- Statement: "It only suggests. It never changes your medicines, your numbers or its own safety rules."

**K3 Care plan** · `/me/care`
- **Next visit** card (a planned visit or "No visit is planned yet") with **Log an appointment** (K7). **One rule for the next visit** (`care.is_next_visit`), also used for "Your next appointment" in the doctor brief: a visit the person confirmed (status planned, so not cancelled, missed or completed) whose time is now or later. A visit whose time has passed and is still marked planned is not next: it is listed under **Earlier visits** with the status **"Past"**, never as planned.
- **Checks and screenings**: eye, foot, kidney, HbA1c test, flu vaccine, diabetes review, each with a status pill (up to date, due soon, overdue, no date) based only on the dates on record.
- **Questions for your doctor**: a link to K12. The question list no longer sits on this page.
- **Generate my doctor brief** (L1).

**K7 Log an appointment** · `/me/appointment`
- Form for **kind**, **date** and **time** (Singapore time). The kinds: GP review, diabetes review, eye screening, foot screening, kidney test, **blood test** (the old "HbA1c" label), other. **There is no Place field.** Vaccination and dental are no longer offered; an old visit of those kinds still shows with its old label, and a suggested visit keeps its kind so the person sees what they confirm.
- Upcoming visits are listed with Cancel (cancel keeps the row). Or confirm a visit Smart Health suggested. No calendar is called from here.

**K12 Questions for your doctor** · `/me/questions` (`features/me/Questions.tsx`)
- Add a question (text box). The list shows **open questions first**. Each question can be marked done or not done, or removed. Each one shows where it came from: added by you, suggested by Smart Health, from your chat, or from your check-in.
- Open questions go into the doctor brief (L1 and L3).
- Endpoints: `POST /care/questions`, `POST /care/questions/{id}/done`, `DELETE /care/questions/{id}`.

**K4 Connected sources** · `/me/sources`
- Read only list of where data comes from (glucose sensor, watch, logs) with last data time and a "not connected" state. Sensor sprint link. No connect or disconnect flows.

**K5 Language and display** · `/me/language`
- Language (saved to the profile), **text size** (100% / 200%, with a live preview), **colour theme** (light, dark, system). The language list offers English, Chinese, Malay and Tamil; see section 3.2 for which screens are translated.

**K6 Privacy and consent** · `/me/privacy`
- One toggle per consent: using health data (required), sharing the doctor brief, adding to calendar, caregiver view, research use. Turning off "using health data" asks for confirmation. A history of when each was turned on and off. **Email reminders card** (`EmailCard`): the notification email address and the on/off switch.

**K8 Data and account** · `/me/data`
- **Download my data** (`GET /me/export`, a file). The export now includes the 2026-10-11 data: the onboarding answers on the profile (diagnosis year, care setting, Healthier SG, low-glucose history), body measurements (weight and waist), conditions, allergies, devices, lab results, blood pressure readings, medicine stock counts, doctor questions and appointments. **Delete my account and data**: type DELETE to confirm; the request is recorded and processed within 30 days; nothing is deleted by the screen.

**K9 Emergency contact** · `/me/contact`
- Name, relationship, mobile number, email (with inline validation). Explains that if glucose is very low and the person does not answer, this contact is emailed. Warns when email is not set up. Save contact.

**K10 Diet tracking** · `/me/progress` (formerly "How it is going")
- **Your starting point**: one card with the **baseline**, the first two full weeks the person logged (calories and salt per logged meal, and the share of doses taken on time). It is not a score.
- **A calendar** of the month: each day shows the meals logged, and tapping a day opens its meals and the day's totals (calories, carbohydrate, protein, fat). A macro total is shown only when every meal that day has that value; an unknown value is a dash, never a lower number.
- "Each week" has been removed. The page says it does not prove the app caused any change.

**K11 Review suggestions** · `/me/review`
- For the care team and reviewers: rate each suggestion the app made (reasonable, not reasonable, unsafe). The score endpoints are `GET /review/queue`, `POST /review/ratings`, `GET /review/score`.

### 4J. Doctor brief (L1 to L3)

Folder `features/brief/`. Everything is computed by the server (`doctor_report.py`); the key findings may be worded by a model, and the rest is code. There is no separate doctor version.

**L1 Doctor brief** · `/brief`
- Period control (7, 14, 30, 90 days). **Key findings** (the model's wording when it passes the checks, otherwise the code-written findings). **Worth discussing**. **Questions you want to ask** (the open doctor questions). **Your next appointment** (the same rule as K3, see 4I). **Alerts in the report** (tags Urgent, Interaction, Review). Buttons: **Open the printable report** (L3) and **Share with my doctor** (L2).

**L2 Share with my doctor** · sheet
- Choose **period** and **how long the link works**; shows what the doctor will see ("Your name, sex and age, and your diagnosis. Nothing else"); **Create link** shows a new link once (random token, only its hash is stored) with Copy; **Links you have made** with **Turn off**. `POST/GET/DELETE /brief/shares`.
- **Consent:** the sheet says that creating a link turns on "Share my doctor brief" in Privacy (the server grants that consent when a link is made and none is active). **Turning off the last link does not turn the consent off**; the sheet says sharing stays on in Privacy until it is switched off there.

**L3 Doctor brief, A4 page** · `/brief/a4?days=14` · outside the frame
- The printable **"Diabetes monitoring report"**. **Print or save as PDF**. A **"Back to the app"** button goes back to the Doctor brief it came from (browser back). If the page was opened directly (a new tab or a reload), it opens the Doctor brief (L1) in place of the page.
- Sections, in this order (`REPORT_SECTIONS` in `ReportView.tsx`; the order is held in one constant):
  1. **Health summary**: the onboarding answers only. A row appears only when there is an answer: waist and its date, year diagnosed, who looks after the diabetes, other conditions, allergies, the latest lab results with their dates, devices (shown by the names the person saw in onboarding, not by their codes).
  2. **Key findings**, with the **"AI insight" note** when the model wrote them ("These sentences were written by an AI from the numbers in this report. The numbers come from your data. Not medical advice. Your doctor decides what they mean.").
  3. **Alerts** (Urgent, Interaction, Review).
  4. **Worth discussing** (Hong Yi's section: medicines, missed doses, patterns, the person's notes).
  5. **Glucose (CGM)**: time in the five ranges, mean, GMI, variability, sensor wear, and glucose by time of day.
  6. **Baseline: the first 14 days of sensor data**, beside the chosen period, with the difference worded "higher than" or "lower than", never good or bad. Shows a plain note when there is not enough data.
  7. **Symptoms and glucose**.
  8. **Symptoms and your latest values**: each symptom beside the latest HbA1c, blood pressure, weight and waist on record, worded "logged together with". It does not show a cause.
  9. **Symptom entries** (the latest 20).
  10. **Medications**: regimen, scheduled, taken, missed, not logged, adherence and an Interaction tag. **The dates of missed doses are no longer shown**; the counts and the reasons are. Adherence is a **dash, never 0%**, when no dose has been answered.
  11. **Activity, heart rate and wellbeing**.
  12. **Blood pressure readings**: the readings as logged, the count and the ranges. Never called high, low or normal.
  13. **Patient's questions**.
- **Removed**: the overnight glucose section and its calculation.
- **Data notes** say that wrist SpO2 is simulated in the demo data when the person's sensor or watch rows come from the demo dataset (the report's `simulated` flag).
- **Left open for Joely (decision D-091)**: the four small tables at the top and the position of the glucose section. The report keeps the current arrangement.

**Shared report** · `/s/:token` · outside the frame, no sign-in
- The same report layout (`ReportView`), read only, with a line saying who it is from. A wrong, expired or turned-off link shows one plain page ("This link has expired or was turned off"). The API route is `GET /brief/shares/public/{token}/report`.

### 4K. Screen index (X1)
`/screens` lists every screen from the route registry (used in demos).

---

## 5. The main journeys, step by step

**J-A First use.** A1 consent (and the reminder email) → A2 eligibility → A3 pages 3 to 11 (each page is saved when Continue is pressed; page 5 scans the medicines; page 10 is the work week; page 11 needs all four contact details) → A6 review → Home. The medicine scanned on page 5 starts a clash check and gets reminders. A person can instead use A4, the chat, and finish on the same record.

**J-A2 A new person.** UserSwitch → "Start as new person" → a new key is made in the database (no profile, no consent, no data) → onboarding opens at page 1 with nothing filled in. Until setup is finished (consent on and profile saved), the app opens onboarding at `/` for this person. A reminder email typed before the profile exists is saved with page 3 or Finish.

**J-B Add a medicine by scan.** H1 Add → H2 photo (masked on device) → H3 check what was read (the name needs a tick below 0.85; a low-confidence field goes to the typed form) → H4 kind and dose times → Add. Server: save, link to the drug list, start the clash check in the background, create calendar events when calendar sync is on. The medicine is saved as a **daily** medicine. Its stock starts from the pack size (the total supplied). H1 shows the card; ClashBox appears by itself when a clash is found (the page checks every 3 seconds only while the check is running).

**J-C Take a dose.** B1 DoseCard → Taken (or Tell us why → H7). The dose comes off the medicine's stock in the same step (H1 shows the new count). Doses unanswered are counted as not taken. C6 and the brief use these.

**J-D Log a meal.** E1 → E2 photo → estimate → portion → Start eating / I already finished → E6 → later the glucose response and the macros appear in C3 and D1/D2. If the photo cannot be read, the screen offers typing the meal.

**J-D2 Log blood pressure.** E1 → E3 (top, bottom, optional pulse and note) → Save → E6 → the reading shows in C5 (Sleep and stress), in Day, and in the brief's blood pressure section. Edit or delete from C3 or E7.

**J-E Symptom and red flag.** E4 → choose symptom → red flag goes to J1; otherwise duration, when, detail → E6.

**J-F Low glucose.** Sensor reading below 4.0 → `notifications` row → B1 banner → J1 → I'm okay (re-check in 15 minutes) or no answer for 5 minutes → one email to the emergency contact → call 995 when very low.

**J-G Prepare for the doctor.** K3 Care plan (next visit) → K12 questions (add, mark done) → L1 brief (key findings, questions, alerts) → L3 print, or L2 link to the doctor → doctor opens `/s/:token`. L3 "Back to the app" returns to L1.

**J-H Understand a medicine.** H1 card → H6 explanation (four parts, additional information) → add a question → appears in K12 and in the brief.

**J-I Daily background.** Every minute: reminders due (meal, check-in, workout, lunch, salt prompt) and reminder emails. Nightly 02:00: learning pass proposes facts for K2.

**J-J Chat.** B1 or C1 Ask → I1 chat, grounded in the person's own data → the message goes through the chat's own rules, a Gemini triage and a grounded Gemini answer, and the reply through the output rules before it is shown (chat-guardrails.md). A symptom, diagnosis or medicine question ends with a doctor referral and a button to add it to the doctor questions (K12).

---

## 6. Design system as built

Source: `apps/web/design.md`, [design.md](design.md), `src/theme/palettes.ts`, `src/index.css`, `src/ui`, `src/charts`.

### 6.1 Direction
Calm and precise, like a good clinic or a private bank, not a wellness app. No gradients, no emoji, no glow. Flat cards with a hairline border; one soft shadow (`shadow-lift`) for the hero card and sheets.

### 6.2 Tokens
| Token | Light | Dark | Use |
|---|---|---|---|
| canvas | `#F6F4EE` | `#0D1411` | App background |
| card | `#FFFEFB` | `#141D19` | Cards, sheets |
| well | `#EFECE3` | `#1B2621` | Inset areas, input rest |
| line | `#E1DDD0` | `#2A3731` | Hairlines |
| ink / ink2 / ink3 | `#16201B` / `#46524B` / `#5F6B64` | `#ECEFE8` / `#B3BEB7` / `#8D9993` | Text (ink3 only at 16 px or larger) |
| brand (pine) | `#1D4A3C` | `#86C9AA` | Primary action, active state |
| brass | `#7A5C22` | `#D8B46C` | Estimates, proposed facts, safety messages (sparingly) |
| ok / warn / danger / info | `#2B6B47` `#935812` `#A12B2B` `#2E5A85` | lighter tints | Status, always with an icon and a word |

Glucose band colours follow the AGP convention (very low, low, in range, high, very high). Adherence cells: **taken (solid green), taken late, not confirmed, missed, no dose due** (each with a pattern as well as a colour).

### 6.3 Type
Atkinson Hyperlegible for reading; **Newsreader** serif for titles and the numbers you glance at. Scale: display, xl, h1, h2, body, sub, micro, each `calc(Npx * var(--ts))` so the 200% setting scales everything.

### 6.4 Shape and spacing
Radii: card 18, chip 999, field 12, sheet 26. 16 px page gutter, 8 px grid. Target size 48 px. Motion: fast and small, only where it explains something; reduced motion respected.

Tokens added on 2026-10-11 (`src/index.css`): `--tab-space` (the phone tab bar's height plus the safe area, which a screen reserves at its end), `--ask-space` (3.75 rem for the phone Ask pill, 0 from 768 px, set by `.has-ask` on Home and Insights), `--text-tab` (14 px, grows by 15% at 200%) for the tab labels and `--text-btn` (18 px, grows by 50% at 200%) for buttons, with `--text-btn-sm` (16 px) for small buttons. The secondary button is an outline (brand border, card fill, brand text).

### 6.5 Components (`src/ui`)
Card (tones plain, soft, hero), Button (primary, secondary, ghost, danger; sizes), Chip, Field (text, multiline, tel, with label, hint, error), Stepper, Toggle, Alert (info, warn, danger with optional title/icon), StatusPill, Segmented, TabStrip, NumberPad, ChoiceCards, Rating, Sheet, Skeleton, EmptyState, TextLink, SectionTitle, Screen/Header/Footer/Split/Reveal, Toast.

### 6.6 Charts (`src/charts`, hand-built SVG, no chart library)
TrendChart, DayChart (the one-clock day), TirBar (time in range), Ring, IntensityBars, FoodBars, WeekGridView, DoseGrid (medicine days), AdherenceTimeline, MoodStress, HeartChart (heart rate, resting value), macro bars (calories, carbohydrate, protein, fat, salt). Rules: gaps are visible, ranges are shaded, every chart has a text alternative and a "Why am I seeing this?" link where the screen has one.

### 6.7 Responsiveness
Phone first (390 px). The breakpoints are Tailwind's: 768 px (`md`), 1024 px (`lg`). The rules as built on 2026-10-11 (from the code of `Shell.tsx`, `ui/layout.tsx`, `ui/Sheet.tsx`, `ui/primitives.tsx` and the screens; not checked in a browser):

| Width | Navigation | Content width | Notes |
|---|---|---|---|
| Below 768 px (phone) | Bottom tab bar (five tabs) | Column of at most 480 px | Ask: a small pill above the tab bar, hides while the page scrolls down. Tabs keep `--tab-space` free at the end of the page, plus `--ask-space` (3.75 rem) on Home and Insights |
| 768 px to 1023 px (tablet) | Side rail, 96 px wide, icons only | 720 px cap (`Screen`) | Ask button in the rail. Sheets centred, 560 px. `Split` stays one column. Home cards one column. Log tiles two columns (fifth tile full width) |
| 1024 px and up (laptop) | Side rail, 240 px wide with labels | 1040 px cap | `Split` in two columns. Home cards in two columns, "See more" full width below. Log tiles in one row of five. Medicine cards in three columns, `TileGrid` up to three columns |
| Any width, forms (`Screen narrow`) | As above | 640 px cap from 768 px | Setup pages and single-task pages |
| Any width, 200% text (`data-ts="2"`) | As above | As above | Two-column grids drop to one column (`[[data-ts='2']_&]`); the Log hub fifth tile takes a normal tile size; text sizes scale (section 6.4) |

Other rules: the bottom bar and the Ask pill are hidden from 768 px (`md:hidden`). Setup (`/welcome`) and the urgent screen (`/urgent`) have no side rail. The phone frame (390 x 844) is only used on a window at least 1000 px wide and 700 px high (a demo setting). Print stylesheet `brief/report.css` for the A4 report.

---

## 7. Backend: endpoints

FastAPI, `services/api/app/api/routers`, camelCase JSON, the `X-User` header selects the person (`demo`, `mr-tan` or a new person). All routes are under `/api/v1` except `/health`. The list below comes from the routers and `app/main.py`.

| Router (prefix) | Endpoints |
|---|---|
| onboarding (`/onboarding`) | `GET /onboarding`, `PUT /onboarding/profile` (one page; only the keys sent are written), `POST /onboarding/complete`, `POST /onboarding/chat` (reads one chat answer; saves nothing) |
| users (`/users`) and misc | `GET /api/v1/users` (the switcher list), `POST /api/v1/users` (start as new person; nothing else is written) |
| scans (`/scans`) | `POST /scans` (photo), `GET /scans/{id}`, `POST /scans/{id}/confirm` |
| medications (`/medications`) | `GET /medications`, `POST /medications`, `DELETE /medications/{id}`, `GET /medications/stock` (the stock list), `POST /medications/{id}/stock` (`{"add": n}` bought more, or `{"set": n}` the exact count), `GET /medications/scope` (is the name one the app is for), `GET /medications/{id}` (the medicine page), `POST /medications/{id}/explanation` (`?refresh=true`; 404 when no reliable page, 429 at the daily text limit, 503 when the model cannot be reached, 502 when the answer cannot be read), `POST /medications/{id}/questions` |
| calendar (`/medications`) | `GET /medications/{id}/calendar`, `POST /medications/{id}/calendar/retry` |
| doses (`/doses`) | `GET /doses/today`, `POST /doses/{id}/taken`, `POST /doses/{id}/reason` |
| interactions (`/interactions`) | `GET /interactions` (alerts, each with `raisedAt`), `POST /interactions/check`, `POST /interactions/{id}/question` (optional `text`: the person's own question), `POST /interactions/{id}/acknowledge` |
| logs (`/logs`) | `POST /logs` (one entry; `kind` is `meal`, `workout`, `symptom`, `checkin` or `blood_pressure`), `GET /logs/recent`, `GET /logs/today`, `GET /logs/context`, `GET /logs/blood-pressure/{id}`, `PUT /logs/blood-pressure/{id}`, `DELETE /logs/{id}` |
| meals (`/meals`) | `POST /meals/analyze` (photo to estimate), `GET /meals/response` |
| workouts (`/workouts`) | `POST /workouts` (save a live session, with its heart-rate effort), `GET /workouts/week` |
| notifications (`/notifications`) | `GET /notifications`, `POST /notifications/{id}/open`, `POST /notifications/{id}/dismiss` |
| notify (`/notify`) | `GET/PUT /notify/email` (PUT answers 409 when the person has no profile yet; the screen keeps the email and saves it later), `POST /notify/test`, `GET /notify/unsubscribe` |
| nutrition (`/nutrition`) | `GET /nutrition/flags`, `GET /nutrition/lunch`, `POST /nutrition/suggestions/dismiss`, `POST /nutrition/suggestions/accept` |
| home (`/home`) | `GET /home/banner` (one food banner: an unfinished meal, or a food habit high in salt or sugar) |
| insights (`/insights`) | `GET /insights/overview?days=`, `GET /insights/overview/days?from=&to=` (the month calendar), `/glucose`, `/food`, `/activity`, `/sleep`, `/medication` (all `?days=`), `GET /insights/sprint`, `GET /insights/heart?days=` (heart rate and SpO2, anchored on the last watch reading); `/activity` returns `barUnit` (day, week or month) and `bars` for the chosen period, `GET /insights/blood-pressure?days=` |
| day (`/day`) | `GET /day/dates`, `GET /day/{day}` |
| memory (`/memory`) | `GET /memory/facts`, `GET /memory/digest`, `GET /memory/audit`, `GET /memory/usage` (AI use today by kind), `GET /memory/progress` (the baseline), `GET /memory/progress/days?from=&to=` (the diet calendar), `GET /memory/barriers/summary` (the K2 numbers), `POST /memory/facts/{id}/action` |
| care (`/care`) | `GET /care/plan`, `POST /care/questions`, `POST /care/questions/{id}/done`, `DELETE /care/questions/{id}`, `GET /care/appointments`, `POST /care/appointments`, `POST /care/appointments/{id}/cancel`, `GET /care/sources` |
| me (`/me`) | `GET/PUT /me/language`, `GET /me/consents`, `PUT /me/consents/{kind}`, `GET /me/export`, `POST /me/delete-request`, `GET/PUT /me/contact` |
| brief (`/brief`) | `GET /brief/report?days=` (the doctor report, with AI-worded key findings where they pass). Shares: `POST /brief/shares`, `GET /brief/shares`, `GET /brief/shares/context`, `DELETE /brief/shares/{id}`, public `GET /brief/shares/public/{token}/report` (the `/s/{token}` page) |
| chat (`/chat`) | `POST /chat/messages`, `GET /chat/conversations/{id}`, `GET /chat/starters`, `POST /chat/questions` |
| review (`/review`) | `GET /review/queue`, `POST /review/ratings`, `GET /review/score` |
| urgent (`/urgent`) | `GET /urgent/state`, `POST /urgent/simulate`, `POST /urgent/acknowledge`, `POST /urgent/escalate` |
| health | `GET /health` (outside `/api/v1`) |

The web client also has a call to `GET /patient`. There is no route for it and no screen that uses it (not verified beyond a search of the web app).

---

## 8. Backend: services, AI agents, scheduler, integrations

### 8.1 Services (`app/services`)

Plain code, no AI, unless a row says otherwise.

| Service | Job |
|---|---|
| `insights`, `insights_heart` | All trend maths (the Insights tabs), and the heart rate, SpO2 and blood pressure reads for them |
| `day` | The one-clock day and the marker sentences |
| `doctor_report` | Every number on the report (`build()`, pure), the Health summary, the 14-day baseline, the symptom and latest-values table, the alerts. Hands the computed facts to `report_insight` |
| `blood_pressure` | The reads for blood pressure readings (before and after migration 0035) |
| `medication_stock` | The stock count: starts from the pack size, goes down by one dose each time a dose is taken (also "I took it, forgot to log"), goes back up when a taken dose is taken back, and never goes below 0 |
| `medicine_scope` | Whether a medicine name is one the app is for (a whole-word match against the drug list; supplements and herbal products are described as not checked) |
| `diet_days` | The diet calendar's day totals (a macro total is unknown if any meal that day is unknown) |
| `barrier_kpis` | The K2 numbers (doses missed, taken on time, most common reason, ideas waiting) |
| `care` | Preventive due dates, appointments (kinds), questions, sources. One rule for the next visit (`is_next_visit`), used by K3 and by the brief; earlier planned visits are listed as Past |
| `onboarding` | The answers, saved by page with the history tables (waist, conditions, allergies, labs, devices, checks); the chat reader and its questions |
| `me_settings`, `share`, `urgent`, `notify_email`, `scheduler`, `dose_store`, `clash_store`, `med_explain_store`, `medication_remove`, `calendar_sync` | As before (consents and export, share links, the low-glucose state machine, the email dispatcher, the scheduler, doses, clash alerts, explanations, removals, calendar events) |
| `scan_store`, `scan_api`, `scan_privacy`, `scan_confidence`, `scan_accuracy` | The medicine scan (section 8.4 and f2-scan.md) |
| `workout_effort` | Heart-rate effort; the coverage rule (70% of the expected samples, counted at the person's own sampling interval, 60 to 600 seconds); the beta-blocker rule (placeholder list); the training volume |
| `web_sources` | The one shape for web sources shown with a medicine explanation or a clash alert: one entry per site, named by the site, a link only where there is a page (openFDA is a name only) |
| `usage` | The daily AI limit, kept **per kind of call** (section 10) |
| `chat`, `chat_guard` | The chat's decision flow and its pure guard rules (urgent and self-harm words, speed limit, input rules, output rules, signposts); the model calls are in `app/agents/chat_assistant.py`. JEV is optional |

**Scan reason codes** (`scan_api.REASON_TEXT`; the screen shows the plain sentence): `file_empty`, `file_too_large` (over 10 MB), `file_type_not_allowed`, `ocr_empty` (no text found), `unreadable`, `not_a_medicine`, `daily_limit` ("Reading photos is paused for today"), `model_unavailable`, `ocr_unavailable`, `storage_unavailable`, `invalid_json`, `several_items`, `low_confidence_all`, `missing_required`, `low_confidence`. An older code `service_unavailable` is read as `model_unavailable`.

### 8.2 AI agents (`app/agents`, Gemini on Vertex AI)

| Agent | Job | Guard | Daily limit |
|---|---|---|---|
| `scan_extractor`, `extractor`, `scan_pipeline` | Read a medicine label into fields with confidence; RapidOCR masks personal text | D-064, D-070: extraction only; the name threshold is 0.6 | `vertex_vision` (its reads share the photo cap; when it is used up the scan stops with `daily_limit`) |
| `meal` | Meal photo to estimated nutrients | Estimates; flags computed in code; failures return a code (section 4E) | `vertex_vision` |
| `med_explainer`, `med_explain_pipeline` | Plain four-part explanation of a medicine with web search | Sentences with doses or advice dropped in code; reliable sources preferred | `vertex_generate` |
| `clash_checker`, `clash_pipeline` | Possible medicine clashes, web-searched, plus a verify pass | Can only add flags; must have a page; fixed patient wording | `vertex_generate` |
| `report_insight` (new, 2026-10-11) | Key findings of the doctor brief: 3 to 5 short labelled lines, worded from the code's facts | Every number must appear in the facts; banned words (advice, dose, stop, safe, normal, cause, good or bad); the code-written findings are shown when fewer than 3 lines pass or the model is unavailable; cached for a day per facts; no names or dates are sent | `vertex_generate` |
| `food` | Food habit and lighter dishes for the next meal | Never overwrites logged numbers | `vertex_embed` for search |
| `adherence` | Barriers and morning anchors from the person's own data | Proposes only | none |
| `orchestrator` | LangGraph router: events tick, nightly, habit_scan, dose_review, salt_check, preventive_due, message | Logs every run to `agent_runs` / `agent_steps` | none |

The chat (I1, `app/llm/chat.py`) and the onboarding chat reader (`app/services/onboarding.py`, `model_extract`) also call the model, under `vertex_generate`. The chat is grounded in the person's own rows and runs the safety guard on each message and reply. The onboarding reader reads one answer at a time and saves nothing.

Prompts live in `agent/prompts` and `app/agents/prompts`: `scan_label` (version 3), `med_explain` (**version 2**, four parts), `clash_check` (version 3), `clash_verify`. Models: `gemini-3.8-flash` (`LLM_VISION_MODEL`, also used for text), `gemini-2.5-pro` as the challenger. The model setting did not change on 2026-10-11.

**Limits.** Each kind of call has its own daily cap, so one kind being used up never blocks another (section 10). When a kind is capped, its caller takes the conservative path: the photo is not read and the person is told; the rules half of a clash check still runs; the explanation and the key findings fall back.

### 8.3 Scheduler
Every minute: reminders due, lunch ideas, high-salt prompt, and the **email dispatcher**. Nightly 02:00: the reflection that proposes facts. Runs for people named in `scheduler_users` (default Mr Tan and the demo user).

### 8.4 Integrations (`app/integrations`)
`workato.py` (calendar events webhook), `workato_email.py` (reminder emails), `storage.py` (photo storage). Workato sandbox (`app.trial.workato.com`); secrets stay in `.env`, never in chat or the repo.

---

## 9. Database

Supabase Postgres, Alembic migrations **0001 to 0037** in `services/api/alembic/versions`. **Migrations 0032 to 0036 were applied on 2026-10-11 and 0037 on 2026-10-12, by the owner's approval** (`alembic current` is `0037`). Layers: Bronze (as received), Silver (cleaned), Gold (derived), plus operations. Highlights by area:

**Migrations added on 2026-10-11** (all written to add, never to drop; each can run twice; all applied as above):

| Migration | What it adds |
|---|---|
| `0032_onboarding_and_stock` | Enum value `onboarding` for `entry_source`. `user_profile`: `diagnosed_year`, `care_setting`, `healthier_sg`, `hypo_last_3m`, `hypo_symptoms` (jsonb). `medications`: `stock_count`, `stock_unit`, `stock_updated_at`. **New tables** `body_measurements` (weight and waist), `conditions`, `allergies`, `devices` (the plan assumed these existed; the migration says migration 0018 had dropped them). Row-level security on for all four |
| `0033_medication_explanation_parts` | `medication_explanations.parts` (jsonb: the four labelled parts) |
| `0034_ai_usage_generate_provider` | `ai_usage_daily.provider` now also allows `vertex_generate` (text the person sees) |
| `0035_blood_pressure_columns` | `blood_pressure_readings`: `id` (unique, back-filled from the Bronze row id so existing readings keep their id; Mr Tan's 42 seeded readings keep their ids), `pulse` (30 to 220), `note` (up to 300 characters), `updated_at`. Pulse and note copied from the Bronze payload where present |
| `0036_workout_intensity_optional` | `exercise_logs.intensity` may be null (a workout can be saved without a rating; null means not rated and is never counted as moderate or vigorous). The 1 to 5 check stays. The downgrade refuses to run while any workout is unrated |
| `0037_layer_comments_missing` | Comment-only: a `Layer: App` comment on `nudge_policy`, `adherence_barriers`, `content_proposals` and `ai_usage_daily` (the schema test needs every table to name its layer). No data or structure change |

Decision 1 (Joely, 2026-10-11): **medicine stock is kept on `medications` itself, with no stock events table.** Every change is written to `event_log` as ids and counts only (`medication.stock.set`, `.added`, `.dose`). The migration file does not create a `medication_stock_events` table.

| Area | Tables |
|---|---|
| People and consent | `users`, `user_profile` (with the 2026-10-11 columns), `patient_profiles`, `consents`, `devices` (0032), `health_goals`, `conditions` (0032), `allergies` (0032), `family_history`, `body_measurements` (0032), `lab_results`, `blood_pressure_readings` (0035 columns) |
| Medicines | `medications` (with `as_needed`, `pack_started_on`, `deleted_at`, and `stock_count`, `stock_unit`, `stock_updated_at` from 0032), `medication_schedule`, `medication_log` (with `miss_reason`), `dose_events`, `medication_explanations` (with `parts`, 0033), `drug_reference`, `drug_aliases`, `drug_side_effects`, `interaction_rules`, `interaction_alerts` (extra columns 0028), `calendar_syncs` (0029), `prescription_scans`, `refill_forecasts` |
| Sensors and logs | `glucose_readings`, `cgm_readings`, `cgm_sprints`, `watch_readings`, `health_samples`, `sleep_sessions`, `food_logs`, `meal_analyses`, `meal_items`, `meal_response`, `exercise_logs` (`intensity` nullable, 0036), `exercise_sets`, `exercise_response`, `symptom_logs`, `wellbeing_logs`, `mood_checkins` |
| Derived | `timeline_5min`, `daily_aggregates`, `daily_summary`, `baselines`, `pattern_candidates`, `momentum_snapshots`, `sprint_summaries` |
| Care and doctor | `appointments` (kinds: GP review, diabetes review, eye, foot, kidney, blood test, other, plus the old vaccination and dental rows), `doctor_questions`, `preventive_items`, `patient_preventive_status`, `briefs`, `brief_shares`, `brief_share_access`, `care_summary` |
| Food and nutrition | `foods`, `food_matches`, `nudge_policy`, `nudge_stats` |
| Memory and agents | `memory_facts`, `memory_episodes`, `agent_runs`, `agent_steps`, `guardrail_events`, `content_proposals`, `knowledge_documents`, `knowledge_chunks`, `conversations`, `messages` |
| Notifications and urgent | `notifications` (delivery columns from 0031), `urgent_events` |
| Operations | `event_log` (append-only), `ingestion_events`, `data_sources`, `population_priors`, `routing_rules`, `ai_usage_daily` (four kinds, 0034), `clinical_flags`, `bronze_profile`, `bronze_lab`, `bronze_blood_pressure` (Bronze inputs) |

Row-level security is on. Reference data (drugs, foods, priors) is loaded once by scripts and nothing later loads reference data.

---

## 10. Settings, thresholds and numbers in code

`apps/web/src/config/app.ts` and server constants:
- Glucose ranges (mmol/L): very low below 3.0, low 3.0 to 3.9, in range 4.0 to 10.0 (profile can set a personal range), high above 10.0, very high above 13.9.
- Urgent tiers (**placeholders, not clinically reviewed**): low below 4.0, very low below 3.0, re-check after 15 minutes, tell the contact after 5 minutes unanswered, reading must be under 20 minutes old.
- Weekly goals: 150 moderate/vigorous minutes, 2 strength sessions.
- Emergency number 995. Locales en, zh, ms, ta.
- Email: at most 3 reminder emails a day, none 22:00 to 07:00 Singapore time, retry up to 3 times, a reminder is not sent late (6 hours; urgent 2 hours).
- **Refill and stock**: the refill estimate uses the stock when a count is set, otherwise the pack date; none for as-needed medicines. "Running low" means 7 days or fewer (`LOW_STOCK_DAYS`).
- **Blood pressure entry**: top 60 to 260, bottom 30 to 150 and lower than the top, pulse 30 to 220, note up to 300 characters, time not in the future.
- **Medicine scan confidence** (`scan_confidence.py`): the standard bar is **0.85** for every field (`SCAN_CONFIDENCE_THRESHOLD`). The **medicine name** has its own bar of **0.6** (`FIELD_THRESHOLDS`). Strength, directions, times and dates stay at 0.85. A value that does not agree with its quote is capped below the bar; at least 70% of the quoted words must be found in the OCR text. A file is refused over 10 MB. Output limit for the model: 12,288 tokens.
- **AI daily limits, per kind** (`services/usage.py`, settings `AI_CAP_*`): photo and label reads (`vertex_vision`) **300**; text the person sees (`vertex_generate`: brief findings, medicine explainer, clash checker, chat, onboarding answers) **500**; background embeddings (`vertex_embed`) **2,000**; JEV typed decisions **500**. Any provider without its own cap uses `AI_DAILY_CALL_CAP` (500). `AI_DAILY_BUDGET_USD` (5) applies to each provider's cost, and only JEV reports cost. When a kind is capped, its calls are refused and counted as blocked against that kind only. The label scanner's reads count under the photo cap (`vertex_vision`); onboarding chat reads and the brief's key findings count under text (`vertex_generate`).
- **Doctor brief**: the baseline is the **first 14 days of sensor data on record**. Reference figures, marked "clinical validation pending" and not targets: time in range above 70%, below range under 4%, above range under 25%, CV at most 36%, sensor worn at least 70%. Key findings: 3 to 5 AI lines, or the code-written findings.
- **Heart-rate effort (placeholders)**: maximum heart rate estimated as 208 minus 0.7 times age; band edges at 57, 64, 77 and 96 percent of that maximum; heart-rate data must cover at least 70% of the expected samples, where the expected count uses the person's own sampling interval (the median gap, kept between 60 and 600 seconds; 60 seconds when there are fewer than three samples). Beta-blocker generic names (placeholder list): atenolol, bisoprolol, metoprolol, propranolol, carvedilol, nebivolol, labetalol, sotalol.
- Weekly and monthly calendars: Overview shows the month; it never goes past the current month.
- Food: a food is ranked only after 2 or more logs with the sensor on; a finding needs 5 or more matching events.
- Share links: token shown once, only its hash stored, expiry chosen by the person.

---

## 11. What is not built, on hold, or undecided

| Item | State |
|---|---|
| **Migrations 0032 to 0037 on the shared database** | **Applied by the owner's approval** (0032 to 0036 on 2026-10-11, 0037 on 2026-10-12; `alembic current` is `0037`). Committed and pushed |
| **Database tests for 2026-10-11 work** | The fix wave ran them: all pass except `test_only_the_demo_patient_remains`, which expects 1 user while the shared database has 2 (already failing before this pass). A full database-suite run took over three hours once because of database contention and is being re-checked |
| **Doctor brief key findings by AI (D-081)** | Built with checks and a fallback. **Departs from rules.md 1.2 and 1.8; Hong Yi to confirm** |
| **Stock on Home** (low-stock note at 7 days or fewer) | Not built (the stock is on the Meds page only) |
| **Onboarding counter in steps 1 to 7** (Joely's decision 2) | Not done: the counter reads "Step N of 11", one step per page |
| **Medicine stock, every dose** | Built for "taken" and "I took it, forgot to log". Unlike the plan, the old refill estimate stays as the fallback when no count is set |
| **Mr Tan's "ran out" statement in K2** | The rule in `agents/adherence.py` still writes "Some missed doses were because of running out ... (n times)". Only the `barrier.ran_out` fact is hidden from the screen (`HIDDEN_FACT_KEYS`). Checking Mr Tan's database for these facts was **not done**. Hong Yi's rule (see section 4I) |
| **Workouts: one-sentence model summary** | Not built (the workouts code makes no model call). Effort cut-offs remain placeholders (questions-for-damien G1) |
| **Meal photo reliability** | The code change and the error codes are built. Whether the model now reads real photos reliably is **not verified** (no live test on 2026-10-11) |
| **Four top tables of the doctor brief and the glucose position** | Left open for Joely (D-091) |
| **Heart rate as a separate tab** | Not built; a block in Activity and Sleep (decision Q6) |
| **I1 Chat** | Built (commit `5e08a1b`). The Ask button shows on Home and the Insights overview only |
| **A4 Set up by chat** | Built (commit `5f5552c`). It asks the same questions as the form, in chat |
| **Manual glucose entry** | No screen; glucose is sensor data only |
| **K4 connect/disconnect** for sensors and watches | Read only; no connect flow, no real sensor sprint start/end. The onboarding device choice is saved, not paired |
| **Other languages** | Chinese, Malay and Tamil exist for the Insights, Log and Me areas only (per-area files). Every other screen is English text. Translations are not reviewed |
| **Workato calendar events for doses** | Backend and recipe script exist; recipe paused ("skip the Workato thing first"); repeating-reminder choice (one event per day topped up, or a hand-built action) not decided; three "[TEST]" events on the demo calendar need deleting by Joely |
| **F10 urgent escalation policy** | Screen built by teammates; the policy is on hold pending Damien (D-054) |
| **Clash check by AI (D-073)** | Departs from the team rule "interactions are never decided by an AI"; Hong Yi has not confirmed |
| **Clash box on Home**, un-acknowledge, re-check on edit | Not built |
| **Clash wording** | Needs pharmacist review, as does the medicine explainer |
| **Server-side "dismiss for now"** | Per device only |
| **Consent-gated features** | Caregiver view and research use are toggles with no feature behind them |
| **Delete account** | Recorded only; nothing deleted |
| **Sodium for most foods** | Missing in the food list; flagged `sodium_unknown` |
| **Routing rules** for eye, foot, kidney, lipids | Only 4 rows |
| **Demo patient age** | Real data says 51; mocks say 58 |
| **Sign-in and accounts** | None; the user switch is a demo tool, and "Start as new person" creates a key with no sign-in |
| **Events** for newer actions | Not all in the `flow.md` event catalogue (for example the stock and blood pressure events, and the clash-alert actions) |
| **`GET /patient` in the web client** | No route and no caller; left as it is |
| **Data export (`GET /me/export`) and the new tables** | **Covered since the fix wave** (`services/api/app/services/me_settings.py`): onboarding answers, body measurements, conditions, allergies, devices, lab results, blood pressure readings, medicine stock counts, doctor questions and appointments. Not checked by opening a downloaded file |
| **Mr Tan's onboarding** | Read only: the onboarding routes refuse his record with 409 (`not_the_demo_patient`). The screens do not send his writes |
| **Learning-loop barrier rule** (Hong Yi's) | `agents/adherence.py` still writes "Some missed doses were because of ... (n times)" and counts missed doses with a reason over all time (`barrier_weeks` has no date window). Only the `barrier.ran_out` fact is hidden on K2. Not changed; Hong Yi to decide |

---

### 11.1 Open after the fix wave and the QA wave (2026-10-11 evening)

The full list, with what was fixed and what was checked, is in [implementation plan, section 14.4](implementation-plan-2026-10-11.md). These are still open:

- The daily summary (Gold `daily_summary`) writes 0 for meals and exercise on a day with nothing logged; it should be empty (NULL). The Overview calendar already shows a dash there because it reads the logs.
- Adherence counts a past-window dose nobody answered as not taken, so it sits in the denominator. Whether pending doses should count is the owner's decision.
- Learning-loop barrier rule (above): Hong Yi's.
- The Ask chat can answer "I cannot check this question right now" (the fallback sentence in `services/api/app/services/texts.py`, a teammate's feature). When it appears was not traced.
- Mr Tan's file-imported lab results are not in the doctor report's Health summary (not verified in this pass).
- Mr Tan has test-looking doctor questions ("hello"). This is data, not code, and was not re-read in this pass.
- The demo user's data was changed during QA (name "QA Demo", onboarding answers). The contact and emails were cleared on 2026-10-11. Data, not code.
- Calories shown before a meal is saved can differ from the saved value.
- A few soft-deleted demo workouts and some scan rows remain in the database (data).
- The A4 print preview was not exercised; the design critics did not view the scan screens, the live workout tracker or the meal error screens live.
- The new strings have English text only in the translation files; Chinese, Malay and Tamil do not have them yet.
- K11 review copy: listed by QA; the details were not given in this pass, so not verified.
- Home has no low-stock note (section 11 above). The onboarding counter still reads "Step N of 11".

## 12. Design brief for regenerating the flow and the screens

### 12.1 What is wrong today (from reading the code; confirm against a live look)

Status on 2026-10-11 is given in brackets.

1. **Hidden screens.** Six built screens (K3, K4, K5, K6, K8, K9) had no entry from the Me page. (**Fixed:** Me lists every screen; K12 and K11 are on it too.)
2. **Me is a link list**, not a profile or a place to see "my health plan". Items of very different weight (a data-download page and the learning loop) sit at the same level. (**Open:** still a flat list of 13 rows, no grouping.)
3. **A dead Ask button** on every screen invites a tap that leads nowhere. (**Fixed in part:** the chat is built, and the button now opens it. It shows on Home and the Insights overview only.)
4. **Home is a long stack** of up to eleven blocks with no clear order of importance. (**Fixed:** five blocks at most, in the order alert, banner, dose, today, one "for you" card; the rest sits behind "See more".)
5. **Five equal tabs plus a centre plus** put reminders, alerts and clashes in a bell that is only on Home, so they are hard to find from other tabs. (**Open:** the bell is still on Home only.)
6. **Medicines page mixes** adding, refill warnings, clash warnings and the list in one scroll; "add" has three entry points (scan, upload, type). (**Partly:** the stock section is added and the add-by-hand form is simpler; the three entry points remain.)
7. **Insights has seven views** reached by a tab strip; charts repeat the same "Why am I seeing this?" pattern; the period control and tabs compete at the top of the screen. (**Partly:** each tab has one "Why am I seeing this?" link at its top, and the Medication tab has lost its glucose chart. The tab strip remains.)
8. **Onboarding A3 has ten steps** on one route; heavy for a first visit; the same questions can be answered later. (**Partly:** eleven pages, each saved as it is finished; the chat set-up is an alternative. The length is unchanged.)
9. **Settings and safety screens use the same cards** as content screens, so a consent toggle, a clash alert and a care-plan item look equally important. (**Open.**)
10. **Text-heavy.** Many screens rely on paragraphs of grey explanation text rather than a clear single action. (**Partly:** the Sleep page copy was cut back, and the Insights tabs use less text. Not checked screen by screen.)

### 12.2 Goals for the new flow
1. A person can answer "What do I do now?" on Home within three seconds (next dose or alert first). (**Largely met:** the first two blocks are the alert and the banner; the dose card is third.)
2. Everything built is reachable in two taps from a tab. No orphan screens. (**Met:** see the reachability map.)
3. Safety surfaces (urgent, clash, red flag) look different from content and are never hidden below other cards.
4. Fewer, clearer choices per screen; long forms are split and can be finished later. (**Met for onboarding:** each page saves on its own.)
5. One notifications entry point reachable from every tab. (**Open.**)
6. The doctor path (care plan, brief, share) is a visible journey, not buried in Me. (**Partly:** the brief is on the Me list and on Home only through the care plan.)
7. Keep every rule in section 2, every fixed sentence, and every state (loading, empty, error, partial data).

### 12.3 Suggested information architecture (a proposal for the redesign)
Unchanged from 2026-10-10. It is still a proposal.

| Tab | Contains |
|---|---|
| **Today** (Home) | 1) alert or urgent strip, 2) next dose card, 3) what to log (one next action), 4) one insight or idea at a time. Everything else moves behind "See more" |
| **Log** | The five log types, workout; unchanged content. Recent entries are on Insights, Food |
| **Medicines** | My stock, list, add (one "Add medicine" button with scan, photo, type), clash box and refill inside the list, detail pages |
| **Insights** | Overview, Glucose, Food, Activity, Sleep, Medication, Day |
| **Me** | A profile header, then grouped sections: *My care* (care plan, appointments, questions, doctor brief), *My data* (what Smart Health has learned, diet tracking, connected sources), *Settings* (language and display, privacy and consent, emergency contact, reminders, data and account), *Help* (set up again, review suggestions for reviewers) |
| Global | A notification bell in the header of every tab (alerts first, then reminders); the Ask button appears only when chat exists (it does now, on Home and Insights) |

### 12.4 Per-screen guidance (keep / change)
- **Keep verbatim:** J1 sentences and call buttons, the clash sentence, "Not checked" badges, the report layout, consent wording, the red-flag symptom behaviour, the scan review rules (including the name tick), the AI insight note on the report.
- **Change:** order and grouping on Me and Insights; use one primary button per screen; use large icons and short labels; place the safety note in a consistent spot; make filters (period, tabs) sticky and smaller; show progress on multi-step forms with Save and Continue later.
- **New states to design:** first-time Home for a new user (nothing logged, the "Start here" block), "demo mode" marker, offline or failed-upload state, long text at 200% size, dark mode for every screen, "Not set yet" for a stock count with no pack size, the older-layout medicine explanation.

### 12.5 Data each new screen needs (all exists already)
Use the endpoints in section 7 as they are. No backend change is required to regenerate the UI; if a new grouped Home feed is wanted it can be assembled from `GET /doses/today`, `GET /urgent/state`, `GET /logs/today`, `GET /home/banner`, `GET /nutrition/lunch`, `GET /notifications`, `GET /interactions`, `GET /medications/stock`.

### 12.6 Acceptance checklist for any regenerated UI
- [ ] Every screen in section 4 exists or is deliberately merged, and every route id still works (or the registry is updated)
- [ ] No orphan screens (check with the screen index X1)
- [ ] Section 2 rules hold on every screen (search for "safe", "stop", "normal" in the text)
- [ ] Fixed sentences are unchanged
- [ ] Loading, empty, error and partial-data states exist
- [ ] 200% text, dark mode, 390 px and 768 px layouts checked
- [ ] Status never by colour alone
- [ ] `python scripts/verify_docs.py` passes after the docs are updated

---

### 12.8 Layout decisions from the two design critic passes (2026-10-11 evening)

These are built, and the per-width table is in section 6.7. Any redesign keeps them unless the owner says otherwise:

- The Ask button lives in the side rail from 768 px and is a small pill above the tab bar on a phone. It is on Home and the Insights overview only.
- Content is capped at 720 px (tablet), 1040 px (laptop) and 640 px for forms (`narrow`). Sheets are centred and 560 px wide from 768 px.
- Lists of tiles use `TileGrid` (equal heights; one, two or three columns). The Log hub's fifth tile (Mood and sleep) spans the full width on a phone and tablet.
- The secondary button is an outline (brand border), not a fill.
- Not checked in a browser: whether these read well at 390 px, 768 px, 1024 px, 200% text and in dark mode.

## 13. Where things live in the repository

| What | Where |
|---|---|
| Web app | `apps/web` (React 19, TypeScript, Vite, Tailwind v4, zustand, react-query) |
| Route registry and shell | `apps/web/src/app` (`routeIds.ts` with a note for every screen, `screens.tsx`, `Shell.tsx`, `sheetRegistry.tsx`, `navigation.ts`) |
| Screens | `apps/web/src/features/{onboarding,home,insights,day,log,workout,meds,scan,alerts,urgent,me,brief,chat,review,sheets}` |
| Data layer | `apps/web/src/data` (`hooks.ts`, `repositories/http.ts`) |
| UI kit and charts | `apps/web/src/ui`, `apps/web/src/charts`, `apps/web/src/theme` |
| API | `services/api/app` (`api/routers`, `services`, `agents`, `llm`, `integrations`, `schemas`, `db`) |
| Migrations | `services/api/alembic/versions` (0001 to 0036) |
| Tests | `services/api/tests` (unit, db, live), web tests next to the code (the web app has none) |
| Scripts | `scripts/` (loaders, replay, clash replay, `verify_docs.py`, `workato_recipe.ps1`) |
| Specs | `docs/specs` ([prd](prd.md), [rules](rules.md), [design](design.md), [flow](flow.md), [insights](insights.md), [f2-scan](f2-scan.md), [f3-explainer](f3-explainer.md), [f4-home-doses](f4-home-doses.md), [f4-calendar](f4-calendar.md), [f5-clash](f5-clash.md), [f12-doctor-report](f12-doctor-report.md), [workout-tracker](workout-tracker.md), [email-notifications](email-notifications.md), [learning-loop](learning-loop.md), [memory](memory.md), [implementation plan of 2026-10-11](implementation-plan-2026-10-11.md)) |
| Decisions and handover | `docs/handover/project-memory.md`, `docs/handover/sessions/` |
