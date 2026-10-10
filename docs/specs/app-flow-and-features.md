# Smart Health: what is built, every screen, and the flow (v2)

**Written 2026-10-10 from the code on branch `dev`** (last commit `6ec7122`, database migrations up to `0031`). This file **replaces [flow.md](flow.md) as the description of the app that exists today**. `flow.md` still holds the original plan (journeys J1 to J15, the event catalogue and the demo script) and is kept for the planned-but-unbuilt parts. Where the two disagree, this file is right about what is built.

**What this file is for.** It lists everything that works today, screen by screen, so the app's flow and look can be redesigned and regenerated from it. Section 12 is the design brief. Everything else is facts about the current build: what each screen shows, what each button does, which server call it uses, and what is not built. It describes the **behaviour and content to keep**; it does not describe the current look, which is the thing being replaced.

**How it was written.** By reading the code (route registry, screens, services, agents, migrations, scripts). The screens were not user-tested for this file. Section 12.1 (what is wrong with the current design) is therefore based on structure, not on test sessions.

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

**Smart Health** is a companion web app for **adults with type 2 diabetes in Singapore**. It helps a person take their medicines, log meals, symptoms, mood, sleep and workouts, see how their glucose responds, and prepare for the doctor. It is a **hackathon build** (shared Supabase Postgres, Vertex AI Gemini, a Workato sandbox).

| Idea | Meaning |
|---|---|
| Who it is for | A person aged about 40 to 75 who is not technical. Large text, plain words, one thing per screen. Also a doctor, who gets a printable or shared report |
| Two demo people | `demo` (a blank new user who goes through onboarding) and `mr-tan` (Mr Tan, a loaded patient: CGMacros participant 046, about 90 days of history, six medicines, 563 dose rows). The switcher in the header (`UserSwitch`) sends the `X-User` header. There is no sign-in yet |
| What the AI does | Reads things (a medicine label, a meal photo), writes plain-language explanations, and suggests possible medicine clashes. It never decides a number |
| What code does | Every number, flag, threshold, streak and chart is computed in code from the stored data |
| What it will not do | Give medical advice, tell anyone to stop, skip or change a medicine, call anything "safe" or "normal" |

### 1.1 Features that are built (by name)

| Area | Feature | Where |
|---|---|---|
| Onboarding | Welcome and consent, eligibility check, a 10-step "About you" form, summary, reminder email | A1, A2, A3, A6 |
| Home | Greeting, bell, urgent banner, next dose card, logging ring, week bars, things to confirm, food flag, lunch idea, what to log today | B1 |
| Notifications | Medicine clash alerts and reminders, with filters | B2 |
| Insights | Overview, Glucose, Food, Activity, Sleep and stress, Medication, Glucose sensor sprint, "Why am I seeing this?" | C1 to C8 |
| Day | One day on one clock, with tappable markers | D1, D2 |
| Logging | Log hub, meal by photo, symptom, mood and sleep check-in, "Saved" screen, edit or delete an entry, lunch ideas | E1, E2, E4, E5, E6, E7, E8 |
| Workouts | Quick workout log, live strength tracker | F1, F2 |
| Medicines | List, scan a label, review the scan, dose plan, add by hand, medicine detail with AI explanation, clash box, clash details, "why was it missed", remove a medicine | H1 to H8 |
| Urgent | Low-glucose alert (two tiers), call buttons, "I'm okay", email the emergency contact, demo trigger | J1 |
| Me | Hub, what Smart Health has learned, how it is going, care plan, connected sources, language and display, privacy and consent, appointment, data and account, emergency contact | K1 to K10 |
| Doctor brief | Brief home, share by link, printable A4 report, doctor's read-only page | L1, L2, L3, `/s/:token` |
| Background | Reminders every minute, reminder emails, nightly learning, calendar events for doses (backend ready, recipe paused) | scheduler |

Not built: the chat (I1) and chat onboarding (A4). See section 11.

---

## 2. Rules that every screen must obey

These come from [rules.md](rules.md), [design.md](design.md) and decisions D-0xx in [project-memory](../handover/project-memory.md). They must survive any redesign.

1. **The model writes words; code produces facts.** No AI output is a number on a chart, a threshold, a streak or a flag.
2. **Never advice.** No "stop", "skip", "change", "take more", "safe", "normal", "abnormal", "caused by". Use "associated with", "higher than your usual", "may", "please check with your pharmacist or doctor".
3. **"Not checked" is never "safe".** A medicine or product the system could not look at shows a "Not checked" badge. A check that could not finish says so ("This is not the same as all clear").
4. **Unknown stays unknown.** A missing value is a dash or a hatched gap, never zero, and a chart line is never joined across a gap.
5. **Estimates are labelled.** Anything read from a photo or worked out from a model is shown as an estimate until the person confirms it.
6. **The person decides.** The system only proposes; "What Smart Health has learned" lets the person confirm, reword or delete each idea. A deleted idea is never proposed again.
7. **Scan fields:** when any scanned field has low confidence the person must go to manual entry (D-064). A scan is pure extraction (D-070): the AI does not add what the label does not say.
8. **Privacy.** Patient name, NRIC, phone and address on a label are masked on the device before anything is stored. The event log holds ids, counts and enums only, never names or free text. A shared doctor link shows name, sex, age and diagnosis, nothing else.
9. **Soft delete.** Removed medicines get `deleted_at`; they disappear from every screen and keep their history. The event log is append-only.
10. **Plain language, units always shown** (mmol/L, mg, min), sentences short, one main action per screen.
11. **Safety copy is fixed.** The low-glucose alert and the clash sentence use fixed wording (sections J1 and H1/H5). Do not rephrase them with AI.
12. **Placeholders are labelled.** Any threshold not reviewed by a clinician says so on screen ("These limits are placeholders and have not had clinical review").
13. **Accessibility.** Text scale 100% or 200%, light and dark, touch targets 48 px or more, status never by colour alone (icon plus word), `ink3` text only at 16 px or larger.

---

## 3. App structure and navigation

### 3.1 The frame (Shell)

| Part | Behaviour |
|---|---|
| Mobile (below 768 px) | Content column, **bottom tab bar** with five tabs: **Home** (`/`), **Insights** (`/insights`), **Log** (`/log`, centre button with a plus), **Meds** (`/meds`), **Me** (`/me`) |
| Tablet and laptop (768 px and up) | Same content in a column of about 480 px (wider for charts), **side rail** instead of the bottom bar |
| Device frame | An optional 390 x 844 phone frame for demos (setting in the demo panel) |
| Ask button | A floating "Ask" button that leads to the chat (I1). **The chat is not built**, so the button is a dead end today |
| Screen wrapper | `Screen` (page padding, optional tab bar space, `tone="urgent"` for J1), `Header` (title, back arrow, `backTo` route id, optional sub-title and trailing item), `Footer` (sticky action area), `Split` (two columns on wide screens), `Reveal` (fold-away) |
| Sheets | Bottom sheets (`Sheet`) opened with `go(id, { sheet: {...} })`. Registered sheets: **E7** entry, **C7** why, **D2** marker, **L2** share, **H7** missed dose |
| Outside the frame | `/brief/a4` (printable report) and `/s/:token` (doctor's shared report) have no tab bar |
| User switch | `UserSwitch` in the header of Home, Meds and Me; switches between `demo` and `mr-tan` |
| Navigation helper | `useGo()` takes a route id (`go('K3')`), so screens never hard-code paths. The registry `app/routeIds.ts` is the single list of screens |

### 3.2 Persisted client state (`smart-health-ui`)

`theme` (light, dark, system), `textScale` (1 or 2), `locale` (en, zh, ms, ta; only English text exists), `userKey` (`demo` or `mr-tan`). Onboarding answers live in `localStorage` key `smart-health-onboarding`. A live workout session is also held on the device.

### 3.3 Reachability map (what links to what today)

```
Launch
 ├─ A1 Welcome ─ A2 Eligibility ─ A3 About you (10 steps) ─ A6 Summary ─ B1 Home
 └─ Tabs
    ├─ B1 Home ── B2 Notifications and alerts ── H5 Possible interaction
    │          ├─ E8 Lunch ideas  · F1 Log a walk · D1 Day · C2/C4 Insights · H7 Missed sheet
    │          └─ J1 Low-glucose alert (banner, demo link)
    ├─ C1 Insights ── C2 Glucose ─ C8 Sprint · C3 Food · C4 Activity · C5 Sleep · C6 Medication · C7 Why? sheet · D1 Day
    ├─ E1 Log ── E2 Meal · E4 Symptom (red flag → J1) · E5 Check-in · F1 Workout (→ F2 live) · E7 entry sheet → E6 Saved
    ├─ H1 Meds ── H2 Scan → H3 Review → H4 Plan · H8 By hand · H6 Detail · H5 Clash detail
    └─ K1 Me ── K2 Learned · K10 Progress · L1 Brief (→ L2 share, L3 A4) · B2 Reminders · A1 Set up again
Reached only from other screens (NOT from the Me page, see 12.1):
    K3 Care plan   ← L1 Brief ("Open my care plan")      → K7 Appointment
    K9 Contact     ← J1 Urgent ("Add an emergency contact")
    K4 Sources, K5 Language, K6 Privacy, K8 Data and account  ← nothing links to them
```

**Important flow defect:** `Me.tsx` has only five rows (K2, K10, L1, B2, A1). Care plan, Connected sources, Language and display, Privacy and consent, Data and account and Emergency contact are built but **no row on the Me page leads to them**. Only the URL, the brief, or the urgent screen reach three of them; K4, K5, K6 and K8 are orphaned.

---

## 4. Screens, area by area

Format for each screen: **route · reached from · what the person sees · what the buttons do · states · data**. "Hook" names are in `apps/web/src/data/hooks.ts`.

### 4A. Onboarding (A1 to A6)

Folder `features/onboarding/`. Answers stay on the device (D-076) and the profile is saved to the database from A3 and A6.

**A1 Welcome** · `/welcome` · from app start, Me ("Set up again")
- Preferred name, language, and **three consents**: use my health data (**required**), share a doctor brief (optional), use my data for research (optional). Nothing is kept on the device until the data consent is on. A "Start as demo patient" shortcut goes straight to Home.
- Next goes to A2.

**A2 Is this app right for you?** · `/welcome/eligibility`
- Questions that stop out-of-scope people with a clear, kind message: type 1 diabetes, pregnancy, under 18. Otherwise Continue to A3.

**A3 About you** · `/welcome/about?step=1..10` (one route, ten steps, progress shown, Back and Next each step)

| Step | Content |
|---|---|
| 1 Body | Age, sex, height, weight (with unit choice), body measurements |
| 2 Diabetes history | Year or age diagnosed, how it is managed |
| 3 Medicines | Add by **Scan a label** (H2), **Add by hand** (H8), or skip; shows medicines already saved |
| 4 Low glucose | Has the person had low readings, symptoms they notice |
| 5 Other conditions, allergies, checks | Conditions, allergies (including medicine allergies), preventive checks and last dates |
| 6 Lab results and blood pressure | HbA1c, cholesterol, kidney and blood pressure if known |
| 7 Devices and routine | Glucose sensor, watch, usual wake, meal and bed times (A5 `/welcome/connect` redirects here) |
| 8 Lifestyle | Activity, smoking, alcohol, diet pattern |
| 9 Safety check and emergency contact | Name, relationship, phone, email of someone to tell if glucose is very low |
| 10 Reminders email | An email address for reminders and a switch to allow reminder emails (A3 step 10, migration 0031) |
- "Chat instead" (A4) is shown in the registry but **A4 is not built**.
- Check my answers goes to A6.

**A6 Your profile summary** · `/welcome/summary`
- Editable read-back of every answer in sections with "Edit" for each (back to the right A3 step). Plain arithmetic only (age, BMI, unit conversions). Gaps worth raising with a doctor. **No stage, risk score or target** is shown.
- Finish saves the profile (`PUT /onboarding/profile`), records consent and completion (`POST /onboarding/complete`) and goes to Home.

### 4B. Home and notifications (B1, B2)

**B1 Home** · `/` · `features/home/Home.tsx`
Top to bottom (each block hides when it has nothing to say):
1. **Header**: greeting, **bell** with a count (unread reminders plus open clash alerts, opens B2), UserSwitch.
2. **Urgent banner**: if a low-glucose alert is active, a red strip that opens J1.
3. **Meal banner**: a meal reminder with "Log a meal" (E2).
4. **Dose card** (`DoseCard`): the next dose or the doses due now, with **Taken** (marks the dose, `POST /doses/{id}/taken`) and **Tell us why** (opens the missed-dose sheet H7). Shows the medicine name, strength and time, and in the afternoon the earlier unanswered doses. As-needed medicines never appear here.
5. **Hero ring**: how much of today's logging is done (meals, check-in, workout, doses) with a button for the next thing to log.
6. **This week** bars (steps, active minutes or similar), opens C4 or C1.
7. **To confirm card**: ideas Smart Health has suggested that the person has not yet confirmed (opens K2).
8. **Food flag card**: a gentle note when a food habit was noticed (salt, fried food), with a lighter-dishes idea.
9. **Lunch card**: a lunch idea (opens E8).
10. **What to log today**: a list of the four log types with ticks for what is done.
11. **Demo link**: "Simulate a low reading" (visible in demo mode only) which creates a marked DEMO alert on the demo user only.

**B2 Notifications and alerts** · `/notifications`
- Filter chips **All / Medicines / Reminders**; "Mark all reminders as read".
- **Clash alert cards** (open alerts from F5): tag "Medication review", time raised, the two medicines with a "Possible interaction" marker, the fixed sentence, the note that this does not mean the medicines are unsafe, and the buttons **Review interaction** (H5), **Contact clinic** (says there is no clinic number yet), **Ask a question** (typed question saved to doctor questions), **Dismiss for now and add to my doctor questions** (hides on this device, with Restore).
- **Reminders list**: each opens its screen (a meal reminder opens E2, a check-in E5, a lunch reminder E8, a refill H6). `POST /notifications/{id}/open` marks it opened.
- Empty state when there is nothing.

### 4C. Insights (C1 to C8)

Folder `features/insights/`. A **tab strip** at the top of every insights screen switches between Overview, Glucose, Food, Activity, Sleep, Medication. A **period control** (7, 30, 90 days) sits under it. The period ends on the latest day that has data. No AI is called; findings are worded "associated with" and labelled unverified.

| Screen | Path | What it shows |
|---|---|---|
| **C1 Overview** | `/insights` | **Your week**: a grid, one square per day for glucose in range, meals logged, active minutes, sleep, stress, doses taken (darker means more; a dash means no data). Tapping a day opens D1. **What changed**: comparison with the days before. **What your history shows**: findings from the nightly job, each needing at least 5 matching events |
| **C2 Glucose** | `/insights/glucose` | Time-in-range bar (five bands), average, estimated A1c (GMI), ups and downs (CV), sensor worn %. Morning (fasting) glucose by day with the person's usual range. Average glucose by day. Link to the sprint (C8) |
| **C3 Food** | `/insights/food` | Calories and salt (sodium) per day, recent meals with salt/sugar flags, and **how foods moved your glucose** (rise in the 2 hours after each food, gentlest first, "biggest rises", "still learning" for foods seen once). A food needs 2 or more logs with the sensor on to be ranked |
| **C4 Activity** | `/insights/activity` | This week against goals (150 moderate/vigorous minutes, 2 strength sessions), last 4 weeks of minutes by intensity, the mix, recent workouts with the glucose change after each, steps by day against the person's usual. "Log a workout" (F1) |
| **C5 Sleep and stress** | `/insights/sleep` | Hours slept by night against the person's usual, average sleep, nights under 6 hours (from a watch; says so when there is none). Mood and stress check-ins |
| **C6 Medication** | `/insights/medication` | Day-by-day grid for each medicine (taken, late, not confirmed, missed), adherence (prescription medicines only; an unanswered dose counts as not taken), why doses were missed, morning glucose over the same days. "Open my medicines" (H1) |
| **C7 Why am I seeing this?** | sheet | Per-chart explanation: what it shows, where the data comes from, what it cannot tell you. Topics: week, glucose, food, activity, sleep, medication, findings, sprint |
| **C8 Glucose sensor sprint** | `/insights/sprint` | The latest 14 days of sensor data: days worn, average, GMI, CV, gentlest and biggest-rise foods. A timed sprint with start and end arrives with the sensor connection (K4) |

States on every tab: loading skeleton, error card ("We could not load this just now"), and an empty state that says what is needed.

### 4D. Day (D1, D2)

**D1 Your day** · `/day/:date` · from C1, C3, C4, E6, E7, B1
- Header "Your day" with the date; arrows to move between days that have data; "See your latest day" if the date has none.
- **One clock**: glucose line with the person's range shaded; lanes for meals, medicines, workouts and symptoms (markers); then heart rate, steps, sleep and mood/stress dots. Missing data is a hatched gap and the line is broken, never joined.
- "Everything logged" list below the chart. Empty text: "Nothing logged for this day."

**D2 Marker detail** · sheet · tap any marker
- What the data shows around that event (for a meal: glucose before, peak and after; for a dose: taken time; for a workout: glucose change; for a symptom: nearest reading and last dose). One sentence worded from the numbers on screen, "associated with", plus "Things that happen close together are not proof that one caused the other."

### 4E. Logging (E1 to E8)

Folder `features/log/`.

**E1 Log hub** · `/log` (centre tab)
- Four big tiles: **Meal** (E2), **Symptom** (E4), **Mood and sleep check-in** (E5), **Workout** (F1). Under them **Recent entries** (tap opens the E7 sheet to edit or delete). There is no manual glucose entry screen (id E3 is unused; glucose comes from the sensor).

**E2 Log a meal** · `/log/meal`
1. Take or upload a **photo** (optional description: what it is, how much was eaten).
2. The photo goes to Gemini on Vertex; the screen shows "Looking at your meal…" then an **estimate** (dish name, calories, carbohydrate, protein, fat, sodium, sugar) labelled as an estimate. A value the model cannot judge is blank, not zero.
3. The person adjusts the **portion** (stepper) or edits any number, then picks one of: **Start eating** (a timer runs so the glucose response can be measured) or **I already finished**.
4. Save goes to E6. `POST /meals/analyze`, `POST /logs`, `GET /meals/{id}/response`.
- Salt/sugar flags are computed in code from the numbers.

**E4 Log a symptom** · `/log/symptom`
- Grid of **14 symptoms**; **5 are red flags** (these show a clear message and a button to J1 instead of saving first). Then **how long**, **when it started**, optional detail text. The sensor reading at that time is filled in automatically.
- Save goes to E6.

**E5 Mood and sleep check-in** · `/log/checkin`
- Title "Mood and sleep", "Thirty seconds. Tap a number for each." Four 1-to-5 ratings: **Mood**, **Stress**, **Sleep quality**, **Energy**, each with end labels (for example Very low to Very good, Calm to Very stressed). Save goes to E6.

**E6 Saved** · `/log/done`
- Confirmation with the related next step: "See your day" (D1), "The related insight" (C2), "Get help now" (J1, only after a red-flag symptom), "Done" (B1).

**E7 Edit or delete an entry** · sheet from E1 recent entries
- Shows the entry; edit the fields or **Delete** (soft delete, `DELETE /logs/{id}`); "See it in your day" (D1).

**E8 Lunch ideas** · `/log/ideas` · from B1 and a lunch reminder
- Up to **3 options** from the person's own history or the Singapore food database, each with the reason and a source label (swap, your own, general). Buttons **I'll have this** (opens E2) and **Not for me** (`POST /nutrition/suggestions/{id}/dismiss`).

### 4F. Workouts (F1, F2)

**F1 Log a workout** · `/log/workout`
- **12 kinds** of activity (the list is in `LogHub`/workout code). **Quick log** (kind, duration, how hard it felt, note) or **Start a live session** for strength (F2). After saving: E6. A symptom shortcut (E4) is offered if the person felt unwell.

**F2 Workout tracker** · `/log/workout/live`
- A timer; add exercises from a **library** or type one; for each exercise log **sets** with reps and weight (steppers, or bodyweight); a **90-second rest timer** starts after each set; **Finish** asks how it felt (energised, fine, tired, unwell) and a note; the summary shows time, sets, weight lifted and, when the server has the watch data, heart-rate effort per exercise and overall (light, moderate, vigorous; no label for people on beta-blockers or with too little heart-rate data). The live session survives a refresh and a failed upload stays on the device as "Waiting to upload". `POST /workouts`.

### 4G. Medicines (H1 to H8)

Folder `features/meds/` and `features/scan/`.

**H1 Medications** · `/meds` (tab)
- Header with UserSwitch and an **Add** area: **Scan a label** (H2), **Upload a photo**, **Type it in** (H8).
- **Refill alert** (blue box): "may run out in about N days" for regular medicines only, counted from the pack start or label date, with "may have run out" wording when the date is old. As-needed medicines never get one.
- **Clash box** (`ClashBox`, section 4G.1): shown only when two saved medicines may clash.
- **Medicine cards**: name and strength, kind chip (prescription, supplement, herbal), how it is taken, next time, a **"Not checked"** badge for supplements and herbal products, a link "What it is for and side effects" (H6), and a **Remove** button at the top right that asks for an inline confirmation and then soft-deletes (`DELETE /medications/{id}`; the medicine disappears and its clash alerts and calendar events are cleared). Works for both demo users.

**H2 Scan a label** · `/meds/scan`
- Camera frame with guidance (flat, well lit, label in the frame); capture or choose a photo. The photo is **masked on the device** (name, NRIC, phone, address) before upload, then `POST /scans`.

**H3 Check what we read** · `/meds/scan/review`
- Each field the scan read (name, strength, form, directions, quantity, dates) with its confidence; low-confidence fields are marked and **force manual entry** (D-064). The person edits and confirms, or retakes the photo.

**H4 Your dose plan** · `/meds/scan/plan`
- **Kind chips** (prescription, supplement, herbal). **"How do you take it?"** two choices: **every day** or **only when needed**; for as-needed the screen explains there will be no refill reminder and a hint is shown for labels that name a symptom (for example "for fever"). **Dose times** list with add and remove (a time per dose). **Add to my medicines** saves (`POST /scans/{id}/confirm`) and starts a background clash check.

**H8 Add a medicine by hand** · `/meds/add`
- Same fields and the same every-day / only-when-needed choice as H4, typed in. `POST /medications`. Used also from onboarding A3 step 3.

**H6 Medicine detail** · `/meds/:id`
- **What it is for** (AI-written, plain language, from web search, with sources and a "Not medical advice" note), **How you take it** (from the person's own plan), **Side effects**, **Tell your doctor if…**, **Refill** (regular medicines only), **Sources** list (links), and a **box to add a question for the doctor**. The text is cached (`medication_explanations`) and any sentence with a dose or "stop/skip/change/safe" is removed in code (D-071). Generate/regenerate via `POST /medications/{id}/explanation`; questions via `POST /medications/{id}/questions`.

**H7 Why was it missed?** · sheet from the dose card
- Answer to "Why was it not confirmed?": **I took it, forgot to log**, **I forgot**, side effects, ran out, felt fine, cost, away from home, other; optional note; Save or Skip. A shortcut leads to E4 when the reason is a symptom. (Code: `features/sheets/MissSheet.tsx`.)

#### 4G.1 Clash box and clash details (F5)
- **Box (H1):** title "Medicines may clash. Check with your doctor." For each pair: the fixed sentence *"Possible interaction between X and Y. Please check with your pharmacist or doctor before continuing."*, one or two plain sentences on why, where it came from (drug-label link and/or the web pages the AI used), and "Not medical advice". Buttons **Review interaction** (H5), **Add to my doctor questions** (turns into a green "Added" state), **I have checked with my doctor** (acknowledges; the alert is kept as acknowledged). While a check runs: "Checking your medicines for clashes…". If the AI half failed and nothing else is flagged: "We could not finish checking for clashes. This is not the same as all clear." with **Check again**.
- **H5 Possible interaction** (`/meds/interaction/:id`): the pair and the fixed sentence; where the flag came from (drug-label rules, AI web search, or both) with the tag "Not reviewed by a clinician"; **Why this was flagged**; a suggested next step (ask the pharmacist or doctor to review the whole list); contact, add-question and typed-question actions; sources behind a fold.

### 4H. Urgent (J1)

**J1 Low glucose alert** · `/urgent` · from the Home banner, the red-flag symptom, the demo link
- The fixed layout. No model is involved; a reading counts only when it is a quality-ok reading no older than 20 minutes.
- **No alert state**: "No low glucose right now." and Back to Home.
- **Active alert** (red screen): status pill **Low** (below 4.0 mmol/L) or **Very low** (below 3.0), a **DEMO, not a real reading** pill for demo alerts, a big number, the sentence "Your glucose looks low: 3.6 mmol/L, 4 minutes ago", and "If you feel unwell or confused, call 995 now. Follow the plan your doctor gave you."
- Buttons: **Call 995** (large and first when very low), **I'm okay now** (acknowledge; then "Checking again in 14:59", re-check after 15 minutes), **Call my contact**, **Tell my contact now**, **Add an emergency contact** (K9) when none.
- **Countdown to the contact**: "If you do not answer in 5:00, we will email {name}." After 5 minutes unanswered the app tells the contact once (email through Workato; the server refuses a second one). If there is no contact email the screen says nobody was emailed.
- Error state keeps a plain "Call 995" button visible.
- A demo alert can be made on the `demo` user only, so a real contact is never emailed.
- Status: the screen is built; the escalation policy is **on hold pending Damien's decision (D-054)** (section 11).

### 4I. Me (K1 to K10)

Folder `features/me/`.

**K1 Me** · `/me` (tab) · list of cards with an icon, title, one-line description and arrow:
1. What Smart Health has learned (K2) with a count badge of ideas to confirm
2. How it is going (K10)
3. Doctor brief (L1)
4. Reminders (B2)
5. Set up again (A1)
*(Care plan, Sources, Language, Privacy, Data and account and Emergency contact are not listed; see 3.3.)*

**K2 What Smart Health has learned** · `/me/learned`
- Ideas grouped by kind; each card shows what was noticed, **why** (evidence), and three actions: **Confirm**, **Say it your way** (edit the wording), **Delete** (never proposed again). "This week" digest of what it did, "Suggestions it is learning from", and an audit list of every run. Statement: "It only suggests. It never changes your medicines, your numbers or its own safety rules."

**K3 Care plan** · `/me/care`
- **Next visit** card (planned appointment or "No visit is planned yet") with Plan an appointment (K7).
- **Checks and screenings**: eye, foot, kidney, HbA1c test, flu vaccine, diabetes review, each with a status pill (up to date, due soon, overdue, no date) based only on the dates on record.
- **Questions for your doctor**: add a question (text box), list with remove (inline confirm). Questions also arrive from medicines and clash alerts.
- **Generate my doctor brief** (L1).

**K4 Connected sources** · `/me/sources`
- Read only list of where data comes from (glucose sensor, watch, logs) with last data time and a "not connected" state. Sensor sprint link. No connect/disconnect flows.

**K5 Language and display** · `/me/language`
- Language (only English is ready, saved to the profile), **text size** (100% / 200%, with a live preview), **colour theme** (light, dark, system).

**K6 Privacy and consent** · `/me/privacy`
- One toggle per consent: using health data (required), sharing the doctor brief, adding to calendar, caregiver view, research use. Turning off "using health data" asks for confirmation. A history of when each was turned on and off. **Email reminders card** (`EmailCard`): the notification email address and the on/off switch.

**K7 Plan an appointment** · `/me/appointment`
- List of upcoming visits (with Cancel; cancel keeps the row), form for kind, date, time, place; or confirm a visit Smart Health suggested. No calendar is called from here.

**K8 Data and account** · `/me/data`
- **Download my data** (`GET /me/export`, a file). **Delete my account and data**: type DELETE to confirm; the request is recorded and processed within 30 days; nothing is deleted by the screen.

**K9 Emergency contact** · `/me/contact`
- Name, relationship, mobile number, email (with inline validation). Explains that if glucose is very low and the person does not answer, this contact is emailed. Warns when email is not set up. Save contact.

**K10 How it is going** · `/me/progress`
- Week by week: meals logged, average calories and salt per logged meal, doses taken on time. After 4 weeks with 5 or more meals each, compares the first two weeks with the latest two. Does not claim the app caused any change.

### 4J. Doctor brief (L1 to L3)

Folder `features/brief/`. Everything is computed by the server (`doctor_report.py`); there is no separate doctor version.

**L1 Doctor brief** · `/brief`
- Period control (7, 14, 30, 90 days). **Key findings** list and sources line ("Sensor worn: 87%"). **Questions you want to ask** (the open doctor questions). **Your next appointment**. **Alerts in the report** (tags Urgent, Interaction, Review). Buttons: **Open the A4 page** (L3) and **Share with my doctor** (L2).

**L2 Share with my doctor** · sheet
- Choose **period** and **how long the link works**; shows what the doctor will see ("Your name, sex and age, and your diagnosis. Nothing else"); **Create link** shows a new link once (random token, only its hash is stored) with Copy; **Links you have made** with **Turn off**. `POST/GET/DELETE /brief/shares`.

**L3 Doctor brief, A4 page** · `/brief/a4?days=14` · outside the frame
- The printable **"Diabetes monitoring report"**: alerts, glucose (CGM) summary and time in range, glucose by time of day (median and percentile bands), symptoms and glucose, medicines with adherence and last dose before symptoms, activity/heart rate/wellbeing, patient's questions. Print or save as PDF.

**Shared report** · `/s/:token` · outside the frame, no sign-in
- The same report, read only, with a line saying who it is from. A wrong, expired or turned-off link shows one plain page ("This link has expired or was turned off").

### 4K. Screen index (X1)
`/screens` lists every screen from the route registry (used in demos).

---

## 5. The main journeys, step by step

**J-A First use.** A1 consent → A2 eligibility → A3 ten steps (can scan or type medicines, set an emergency contact and a reminder email) → A6 review → Home. The medicine added in step 3 starts a clash check and gets reminders.

**J-B Add a medicine by scan.** H1 Add → H2 photo (masked on device) → H3 check what was read (low confidence forces manual entry) → H4 choose kind, every day or only when needed, dose times → Add. Server: save, link to the drug list, start the clash check in the background, create calendar events when calendar sync is on. H1 now shows the card; ClashBox appears by itself when a clash is found (the page polls every 5 seconds).

**J-C Take a dose.** B1 DoseCard → Taken (or Tell us why → H7). Doses unanswered are counted as not taken. C6 and the brief use these.

**J-D Log a meal.** E1 → E2 photo → estimate → portion → Start eating / I already finished → E6 → later the glucose response appears in C3 and D1/D2.

**J-E Symptom and red flag.** E4 → choose symptom → red flag goes to J1; otherwise duration, when, detail → E6.

**J-F Low glucose.** Sensor reading below 4.0 → `notifications` row → B1 banner → J1 → I'm okay (re-check in 15 minutes) or no answer for 5 minutes → one email to the emergency contact → call 995 when very low.

**J-G Prepare for the doctor.** K3 Care plan (questions, next visit) → L1 brief → L3 print, or L2 link to the doctor → doctor opens `/s/:token`.

**J-H Understand a medicine.** H1 card → H6 explanation → add a question → appears in K3 and in the brief.

**J-I Daily background.** Every minute: reminders due (meal, check-in, workout, lunch, salt prompt) and reminder emails. Nightly 02:00: learning pass proposes facts for K2.

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

Glucose band colours follow the AGP convention (very low, low, in range, high, very high). Adherence cells: taken, late, not confirmed, missed.

### 6.3 Type
Atkinson Hyperlegible for reading; **Newsreader** serif for titles and the numbers you glance at. Scale: display, xl, h1, h2, body, sub, micro, each `calc(Npx * var(--ts))` so the 200% setting scales everything.

### 6.4 Shape and spacing
Radii: card 18, chip 999, field 12, sheet 26. 16 px page gutter, 8 px grid. Target size 48 px. Motion: fast and small, only where it explains something; reduced motion respected.

### 6.5 Components (`src/ui`)
Card (tones plain, soft, hero), Button (primary, secondary, ghost, danger; sizes), Chip, Field (text, multiline, tel, with label, hint, error), Stepper, Toggle, Alert (info, warn, danger with optional title/icon), StatusPill, Segmented, TabStrip, NumberPad, ChoiceCards, Rating, Sheet, Skeleton, EmptyState, TextLink, SectionTitle, Screen/Header/Footer/Split/Reveal, Toast.

### 6.6 Charts (`src/charts`, hand-built SVG, no chart library)
TrendChart, DayChart (the one-clock day), TirBar (time in range), Ring, IntensityBars, FoodBars, WeekGridView, AdherenceTimeline, MoodStress. Rules: gaps are visible, ranges are shaded, every chart has a text alternative and a "Why am I seeing this?" link.

### 6.7 Responsiveness
Phone first (390 px); at 768 px the bottom bar becomes a side rail; the content column stays near 480 px with wider charts. Print stylesheet `brief/report.css` for the A4 report.

---

## 7. Backend: endpoints

FastAPI, `services/api/app/api/routers`, camelCase JSON, the `X-User` header selects `demo` or `mr-tan`. All routes are under `/api/v1` except `/health`.

| Router (prefix) | Endpoints |
|---|---|
| onboarding | `GET /onboarding`, `PUT /onboarding/profile`, `POST /onboarding/complete` |
| scans | `POST /scans`, `GET /scans/{id}`, `POST /scans/{id}/confirm` |
| medications | `GET /medications`, `POST /medications`, `DELETE /medications/{id}`, `GET /medications/{id}` |
| med_explain | `POST /medications/{id}/explanation`, `POST /medications/{id}/questions` |
| doses | `GET /doses/today`, `POST /doses/{id}/taken`, `POST /doses/{id}/reason` |
| interactions | `GET /interactions`, `POST /interactions/check`, `POST /interactions/{id}/question`, `POST /interactions/{id}/acknowledge` |
| calendar | `GET /medications/{id}/calendar`, `POST /medications/{id}/calendar/retry` |
| logs | `POST /logs`, `GET /logs/recent`, `/logs/today`, `/logs/context`, `DELETE /logs/{id}` |
| meals | `POST /meals/analyze`, `GET /meals/{id}/response` |
| workouts | `POST /workouts`, `GET /workouts/week` |
| nutrition | `GET /nutrition/flags`, `GET /nutrition/lunch`, `POST /nutrition/suggestions/{id}/dismiss`, `/accept` |
| notifications | `GET /notifications`, `POST /notifications/{id}/open` |
| notify | `GET/PUT /notify/email`, `POST /notify/test`, `GET /notify/unsubscribe` |
| insights | `GET /insights/overview`, `/glucose`, `/food`, `/activity`, `/sleep`, `/medication`, `/sprint` |
| day | `GET /day/dates`, `GET /day/{day}` |
| memory | `GET /memory/facts`, `/digest`, `/audit`, `/usage`, `/progress`, `POST /memory/facts/{id}/action` |
| care | `GET /care/plan`, `POST/DELETE /care/questions`, `GET/POST /care/appointments` (+cancel), `GET /care/sources` |
| me | `GET/PUT /me/language`, `GET/PUT /me/consents`, `GET /me/export`, `POST /me/delete-request`, `GET/PUT /me/contact` |
| brief | `GET /brief/report?days=` |
| share | `POST/GET/DELETE /brief/shares`, public `GET /s/{token}` report |
| urgent | `GET /urgent/state`, `POST /urgent/simulate`, `/acknowledge`, `/escalate` |
| misc | `GET /health`, `GET /api/v1/users` |

---

## 8. Backend: services, AI agents, scheduler, integrations

### 8.1 Services (`app/services`, plain code, no AI)
`insights` (all trend maths), `day` (the one-clock day and marker sentences), `doctor_report` (every number on the report, pure `build()`), `share` (token hashing, expiry, access log), `urgent` (state machine for the low-glucose alert, placeholder tiers), `care` (preventive due dates, appointments, sources), `me_settings` (consents, export, contact validation), `onboarding`, `notify_email` (the dispatcher rules: kinds, caps, quiet hours, retries, never twice), `scheduler`, `dose_store`, `clash_store` (drug-pair rules plus saving alerts), `med_explain_store`, `medication_remove`, `calendar_sync`, `scan_store/scan_api/scan_privacy/scan_confidence/scan_accuracy`, `workout_effort` (heart-rate effort from watch data), `usage` (daily AI limit).

### 8.2 AI agents (`app/agents`, Gemini on Vertex AI)
| Agent | Job | Guard |
|---|---|---|
| `scan_extractor`, `extractor`, `scan_pipeline` | Read a medicine label into fields with confidence; RapidOCR masks personal text | D-064, D-070: extraction only |
| `meal` | Meal photo to estimated nutrients | Estimates; flags computed in code |
| `med_explainer`, `med_explain_pipeline` | Plain explanation of a medicine with web search | Sentences with doses/advice dropped in code |
| `clash_checker`, `clash_pipeline` | Possible medicine clashes, web-searched, plus a verify pass | Can only add flags; must have a page; fixed patient wording |
| `food` | Food habit and lighter dishes for the next meal | Never overwrites logged numbers |
| `adherence` | Barriers and morning anchors from the person's own data | Proposes only |
| `orchestrator` | LangGraph router: events tick, nightly, habit_scan, dose_review, salt_check, preventive_due, message | Logs every run to `agent_runs` / `agent_steps` |

Prompts live in `agent/prompts` (`scan_label`, `med_explain`, `clash_check` v3, `clash_verify`). Models: `gemini-3.8-flash` (generate_json, generate_grounded with Google Search). A daily AI limit (`ai_usage_daily`) never blocks the rules half of a check.

### 8.3 Scheduler
Every minute: reminders due, lunch ideas, high-salt prompt, and the **email dispatcher**. Nightly 02:00: the reflection that proposes facts. Runs for people named in `scheduler_users` (default Mr Tan and the demo user).

### 8.4 Integrations (`app/integrations`)
`workato.py` (calendar events webhook), `workato_email.py` (reminder emails), `storage.py` (photo storage). Workato sandbox (`app.trial.workato.com`); secrets stay in `.env`, never in chat or the repo.

---

## 9. Database

Supabase Postgres, Alembic migrations **0001 to 0031**. Layers: Bronze (as received), Silver (cleaned), Gold (derived), plus operations. Highlights by area:

| Area | Tables |
|---|---|
| People and consent | `users`, `user_profile`, `patient_profiles`, `consents`, `devices`, `health_goals`, `conditions`, `allergies`, `family_history`, `body_measurements`, `lab_results`, `blood_pressure_readings` |
| Medicines | `medications` (with `as_needed` 0030, `pack_started_on` 0026, `deleted_at`), `medication_schedule`, `medication_log` (with `miss_note` 0027), `dose_events`, `medication_explanations`, `drug_reference`, `drug_aliases`, `drug_side_effects`, `interaction_rules`, `interaction_alerts` (extra columns 0028), `calendar_syncs` (0029), `prescription_scans`, `refill_forecasts` |
| Sensors and logs | `glucose_readings`, `cgm_readings`, `cgm_sprints`, `watch_readings`, `health_samples`, `sleep_sessions`, `food_logs`, `meal_analyses`, `meal_items`, `meal_response`, `exercise_logs`, `exercise_sets`, `exercise_response`, `symptom_logs`, `wellbeing_logs`, `mood_checkins` |
| Derived | `timeline_5min`, `daily_aggregates`, `daily_summary`, `baselines`, `pattern_candidates`, `momentum_snapshots`, `sprint_summaries` |
| Care and doctor | `appointments`, `doctor_questions`, `preventive_items`, `patient_preventive_status`, `briefs`, `brief_shares`, `brief_share_access`, `care_summary` |
| Food and nutrition | `foods`, `food_matches`, `nudge_policy`, `nudge_stats` |
| Memory and agents | `memory_facts`, `memory_episodes`, `agent_runs`, `agent_steps`, `guardrail_events`, `content_proposals`, `knowledge_documents`, `knowledge_chunks`, `conversations`, `messages` |
| Notifications and urgent | `notifications` (delivery columns from 0031), `urgent_events` |
| Operations | `event_log` (append-only), `ingestion_events`, `data_sources`, `population_priors`, `routing_rules`, `ai_usage_daily`, `clinical_flags` |

Row-level security is on. Reference data (drugs, foods, priors) is loaded once by scripts and nothing later loads reference data.

---

## 10. Settings, thresholds and numbers in code

`apps/web/src/config/app.ts` and server constants:
- Glucose ranges (mmol/L): very low below 3.0, low 3.0 to 3.9, in range 4.0 to 10.0 (profile can set a personal range), high above 10.0, very high above 13.9.
- Urgent tiers (**placeholders, not clinically reviewed**): low below 4.0, very low below 3.0, re-check after 15 minutes, tell the contact after 5 minutes unanswered, reading must be under 20 minutes old.
- Weekly goals: 150 moderate/vigorous minutes, 2 strength sessions.
- Emergency number 995. Locales en, zh, ms, ta (English text only).
- Email: at most 3 reminder emails a day, none 22:00 to 07:00 Singapore time, retry up to 3 times, a reminder is not sent late (6 hours; urgent 2 hours).
- Supply (refill) estimate: counted from the pack start or the label date; none for as-needed medicines.
- A food is ranked only after 2 or more logs with the sensor on; a finding needs 5 or more matching events.
- Share links: token shown once, only its hash stored, expiry chosen by the person.

---

## 11. What is not built, on hold, or undecided

| Item | State |
|---|---|
| **I1 Chat** ("Ask Smart Health") and the floating Ask button | Not built; the button is a dead end |
| **A4 Set up by chat** | Not built (the form is the only route) |
| **Manual glucose entry** | No screen (id E3 unused); glucose is sensor data only |
| **K4 connect/disconnect** for sensors and watches | Read only; no connect flow, no real sensor sprint start/end |
| **Other languages** | Locale switch exists, only English text |
| **Me page links** | Care plan, Sources, Language, Privacy, Data and Emergency contact are not linked from Me (3.3) |
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
| **Sign-in and accounts** | None; the user switch is a demo tool |
| **Events** for newer actions | Not all in the `flow.md` event catalogue |

---

## 12. Design brief for regenerating the flow and the screens

### 12.1 What is wrong today (from reading the code; confirm against a live look)

1. **Hidden screens.** Six built screens (K3, K4, K5, K6, K8, K9) have no entry from the Me page. The settings area is effectively missing from the app.
2. **Me is a link list**, not a profile or a place to see "my health plan". Items of very different weight (a data-download page and the learning loop) sit at the same level.
3. **A dead Ask button** on every screen invites a tap that leads nowhere.
4. **Home is a long stack** of up to eleven blocks with no clear order of importance. The most important thing (the next dose, or an alert) competes with food flags and lunch ideas.
5. **Five equal tabs plus a centre plus** put reminders, alerts and clashes in a bell that is only on Home, so they are hard to find from other tabs.
6. **Medicines page** mixes adding, refill warnings, clash warnings and the list in one scroll; "add" has three entry points (scan, upload, type).
7. **Insights has seven views** reached by a tab strip; charts repeat the same "Why am I seeing this?" pattern; the period control and tabs compete at the top of the screen.
8. **Onboarding A3 has ten steps** on one route; heavy for a first visit; the same questions can be answered later.
9. **Settings and safety screens use the same cards** as content screens, so a consent toggle, a clash alert and a care-plan item look equally important.
10. **Text-heavy.** Many screens rely on paragraphs of grey explanation text rather than a clear single action.

### 12.2 Goals for the new flow
1. A person can answer "What do I do now?" on Home within three seconds (next dose or alert first).
2. Everything built is reachable in two taps from a tab. No orphan screens.
3. Safety surfaces (urgent, clash, red flag) look different from content and are never hidden below other cards.
4. Fewer, clearer choices per screen; long forms are split and can be finished later.
5. One notifications entry point reachable from every tab.
6. The doctor path (care plan, brief, share) is a visible journey, not buried in Me.
7. Keep every rule in section 2, every fixed sentence, and every state (loading, empty, error, partial data).

### 12.3 Suggested information architecture (a proposal for the redesign)

| Tab | Contains |
|---|---|
| **Today** (Home) | 1) alert or urgent strip, 2) next dose card, 3) what to log (one next action), 4) one insight or idea at a time. Everything else moves behind "See more" |
| **Log** | The four log types, recent entries, workout; unchanged content |
| **Medicines** | List, add (one "Add medicine" button with scan, photo, type), clash box and refill inside the list, detail pages |
| **Insights** | Overview, Glucose, Food, Activity, Sleep, Medication, Day |
| **Me** | A profile header, then grouped sections: *My care* (care plan, appointments, doctor brief, questions), *My data* (what Smart Health has learned, how it is going, connected sources), *Settings* (language and display, privacy and consent, emergency contact, reminders, data and account), *Help* (set up again) |
| Global | A notification bell in the header of every tab (alerts first, then reminders); the Ask button appears only when chat exists |

### 12.4 Per-screen guidance (keep / change)
- **Keep verbatim:** J1 sentences and call buttons, the clash sentence, "Not checked" badges, the report layout, consent wording, the red-flag symptom behaviour, the scan review rules.
- **Change:** order and grouping on Home, Me and Insights; use one primary button per screen; use large icons and short labels; place the safety note in a consistent spot; make filters (period, tabs) sticky and smaller; show progress on multi-step forms with Save and Continue later.
- **New states to design:** first-time Home for a new user (nothing logged), "demo mode" marker, offline/failed-upload state, long text at 200% size, dark mode for every screen.

### 12.5 Data each new screen needs (all exists already)
Use the endpoints in section 7 as they are. No backend change is required to regenerate the UI; if a new grouped Home feed is wanted it can be assembled from `GET /doses/today`, `GET /urgent/state`, `GET /logs/today`, `GET /nutrition/flags`, `GET /nutrition/lunch`, `GET /notifications`, `GET /interactions`.

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

## 13. Where things live in the repository

| What | Where |
|---|---|
| Web app | `apps/web` (React 19, TypeScript, Vite, Tailwind v4, zustand, react-query) |
| Route registry and shell | `apps/web/src/app` (`routeIds.ts`, `screens.tsx`, `Shell.tsx`, `sheetRegistry.tsx`, `navigation.ts`) |
| Screens | `apps/web/src/features/{onboarding,home,insights,day,log,workouts,meds,scan,alerts,urgent,me,brief}` |
| Data layer | `apps/web/src/data` (`hooks.ts`, `repositories/http.ts`) |
| UI kit and charts | `apps/web/src/ui`, `apps/web/src/charts`, `apps/web/src/theme` |
| API | `services/api/app` (`api/routers`, `services`, `agents`, `integrations`, `schemas`, `db`) |
| Migrations | `services/api/alembic/versions` (0001 to 0031) |
| Tests | `services/api/tests`, web tests next to the code |
| Scripts | `scripts/` (loaders, replay, clash replay, `verify_docs.py`, `workato_recipe.ps1`) |
| Specs | `docs/specs` ([prd](prd.md), [rules](rules.md), [design](design.md), [flow](flow.md), [insights](insights.md), [f2-scan](f2-scan.md), [f3-explainer](f3-explainer.md), [f4-home-doses](f4-home-doses.md), [f4-calendar](f4-calendar.md), [f5-clash](f5-clash.md), [f12-doctor-report](f12-doctor-report.md), [workout-tracker](workout-tracker.md), [email-notifications](email-notifications.md), [learning-loop](learning-loop.md), [memory](memory.md)) |
| Decisions and handover | `docs/handover/project-memory.md`, `docs/handover/sessions/` |
