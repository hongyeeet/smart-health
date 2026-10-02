# Damien: backlog

**Owner:** Damien (GitHub chua-damien) · **Role:** Onboarding, food response, check-ins, nudges, recurring checks and doctor questions. Reviewer for E4 and E13.

You edit only this file. As you work: tick subtasks (`- [ ]` becomes `- [x]`), set **Status** (`backlog`, `in progress`, `in review`, `blocked`, `done`) and write a one-line **Note**. Then run `python scripts/update_tracker.py` to refresh the blocker check below and the central tracker ([SOT.md](SOT.md)). Never edit another person's file (one exception: a Reviewer sets the Status and Note of a task they review) or the generated parts of SOT.md.

If a task has a **Reviewer**, set `in review` when you finish; only the Reviewer (or the owner) moves it to `done`, after writing `Verified by <name> <date>` in the Note. **Needs first** are tasks that must be done before you can start; **Needed later** are tasks you will need partway through.

## Blocker check

<!-- BLOCKERS:START -->
Ready means everything under **Needs first** is done, so you can start. Blocked means you must wait.

**Ready now (3)**

- E8-1 Sprint and meal response: unblocks 7 other tasks.
- E21-1 Submission text and visuals: unblocks 1 other task.
- E14-1 Recurring checks and appointments: unblocks 0 other tasks. Later you will need: E13-2 (Hong Yi, backlog).

**Blocked (7)**

- E2-1 Onboarding flow: waiting for E0-2 (Hong Yi, in progress)
- E2-2 Chat onboarding: waiting for E2-1 (Damien, backlog), E16-1 (Hong Yi, backlog), E0-3 (Hong Yi, in progress)
- E8-2 Food leaderboard: waiting for E8-1 (Damien, backlog)
- E10-1 Check-ins: waiting for E9-1 (Hong Yi, backlog)
- E12-1 Nudge messages and learning: waiting for E9-1 (Hong Yi, backlog)
- E12-2 Nudge cards and food swaps: waiting for E12-1 (Damien, backlog), E0-2 (Hong Yi, in progress)
- E15-1 Doctor questions: waiting for E0-2 (Hong Yi, in progress)

Done: 0 of 10 tasks.
<!-- BLOCKERS:END -->

## Tasks

### E2-1 Onboarding flow · P0

- **Ask:** Build the onboarding flow: a step-by-step form, eligibility and consent checks, an editable summary and the demo shortcut. Use medical domain knowledge to ask the right history questions: past illnesses, conditions, allergies, family history and current medicines.
- **Status:** backlog
- **Needs first:** E0-2, E1-2
- **Needed later:** E1-4
- **Phase:** 1
- **Spec:** prd F1
- **Note:**
- **Success criteria:**
  - [ ] Steps: about you, diagnosis and HbA1c, conditions, allergies, family history, medications entry point, connected sources, reminder times
  - [ ] Finishes in 5 minutes or less on a phone-size screen
  - [ ] Each step saves
  - [ ] Leaving and returning resumes
  - [ ] Writes profile, conditions and allergies
  - [ ] Type 1, pregnancy and under-18 are blocked with a clear message
  - [ ] Consent rows stored
  - [ ] The user cannot continue without data-processing consent
  - [ ] Editable summary screen
  - [ ] 'Start as demo patient' skips onboarding and loads the seeded persona

### E2-2 Chat onboarding · P1

- **Ask:** Offer a chat version of onboarding that collects the same details by conversation and gives the same result as the form. Optional (P1).
- **Status:** backlog
- **Needs first:** E2-1, E16-1, E0-3
- **Needed later:** none
- **Phase:** 2
- **Spec:** prd F1
- **Note:**
- **Success criteria:**
  - [ ] Same fields collected conversationally, with a live 'captured so far' card and edit before saving
  - [ ] A scripted transcript produces the same records as the form

### E8-1 Sprint and meal response · P0

- **Ask:** Build the CGM sprint: start and end a 14-day sprint from replayed data, and for each meal calculate glucose before, peak rise and area under the curve, plus the sprint summary numbers.
- **Status:** backlog
- **Needs first:** E1-2, E1-4
- **Needed later:** none
- **Phase:** 1
- **Spec:** prd F7
- **Note:**
- **Success criteria:**
  - [ ] Start and end a 14-day CGM sprint
  - [ ] Replay of the chosen CGMacros participant fills it
  - [ ] One open sprint per user
  - [ ] For each meal, baseline glucose, peak rise and 2-hour incremental AUC
  - [ ] Matches a pandas reference on 20 meals
  - [ ] Windows with too little data are excluded
  - [ ] Time in range, below range, above range, GMI and CV match a pandas reference

### E8-2 Food leaderboard · P0

- **Ask:** Build the personal food leaderboard (gentlest to spikiest, only with 2 or more observations) and the gentle note on spiky foods. Stretch: compare with the population model.
- **Status:** backlog
- **Needs first:** E8-1
- **Needed later:** E1-5
- **Phase:** 2
- **Spec:** prd F7
- **Note:**
- **Success criteria:**
  - [ ] Responses per food shown only when n is 2 or more, with n and range
  - [ ] Logging a known high-response food shows the factual note
  - [ ] Leaderboard in Insights and the brief
  - [ ] Screen shows the model's expected response next to the actual one, labelled as a population estimate

### E10-1 Check-ins · P0 · NEEDS OK

- **Ask:** Build the check-ins: a question bank (needs a clinician's review) and a planner that asks at most one neutral question a day, the card, and linking answers to the pattern and the brief. Needs your OK.
- **Status:** backlog
- **Needs first:** E9-1
- **Needed later:** none
- **Phase:** 2
- **Spec:** prd F9
- **Note:**
- **Success criteria:**
  - [ ] Question wording is team-written and needs clinician review
  - [ ] Planner picks at most 1 check-in per day and 3 per week, and learns which the user answers
  - [ ] One neutral question card
  - [ ] Answer or skip is stored as a symptom log
  - [ ] Answers show in the brief symptom section, linked to the pattern that triggered them

### E12-1 Nudge messages and learning · P0 · NEEDS OK

- **Ask:** Build nudge messages (reviewed templates filled with the user's own data) and the learning that picks which nudge and time works for each user. Needs your OK.
- **Status:** backlog
- **Needs first:** E9-1
- **Needed later:** none
- **Phase:** 2
- **Spec:** prd F11; architecture 5.4
- **Note:**
- **Success criteria:**
  - [ ] No guideline corpus is in the cited data, so nudges are reviewed team-written templates filled with the user's own data
  - [ ] Each nudge names the data it is based on
  - [ ] Chooses nudge type and time slot by observed act rate with 15% exploration, 3 per day cap, quiet hours
  - [ ] A simulation over the demo persona shifts toward the slots and types the user acts on

### E12-2 Nudge cards and food swaps · P0

- **Ask:** Build the nudge card on Today ('Done' and 'Not for me') and suggestions of gentler foods when a meal is salty or sugary. The food swaps are optional (P1).
- **Status:** backlog
- **Needs first:** E12-1, E0-2
- **Needed later:** E7-2, E8-2
- **Phase:** 2
- **Spec:** prd F11
- **Note:**
- **Success criteria:**
  - [ ] High-salt or high-sugar meals show a card suggesting a food that gave this user a gentler response
  - [ ] Today shows at most one nudge card with 'Done' and 'Not for me' that feed the policy

### E14-1 Recurring checks and appointments · P1 · NEEDS OK

- **Ask:** Build recurring checks: the checklist (eye, foot, kidney, HbA1c, flu) with due status, appointment planning with a calendar file, and an automatic brief before the visit. Optional (P1); needs a clinician's review and your OK.
- **Status:** backlog
- **Needs first:** E1-2
- **Needed later:** E13-2
- **Phase:** 2
- **Spec:** prd F13
- **Note:**
- **Success criteria:**
  - [ ] Screening intervals are team-written config needing clinician review
  - [ ] Screen shows each item as ok, due soon, overdue or unknown
  - [ ] Suggest, plan and confirm an appointment
  - [ ] Nothing is booked without confirmation
  - [ ] Downloads an .ics file that opens in a calendar
  - [ ] (Google Calendar link is a stretch.)
  - [ ] A brief is generated 48 hours before a planned appointment and the user is notified

### E15-1 Doctor questions · P0

- **Ask:** Build the doctor-questions list: add from anywhere, edit, feed into the brief, and have the AI tidy the wording and suggest who to ask (without naming any diagnosis).
- **Status:** backlog
- **Needs first:** E1-2, E0-2
- **Needed later:** E1-4
- **Phase:** 1
- **Spec:** prd F14
- **Note:**
- **Success criteria:**
  - [ ] Add a question from anywhere (chat refusal, clash sheet, side-effect reason)
  - [ ] List editable
  - [ ] Flows into brief section 12
  - [ ] Model tidies wording
  - [ ] Routing table suggests who to ask (eye, foot, kidney, heart) without naming diagnoses

### E21-1 Submission text and visuals · P0

- **Ask:** Write the submission text (title, blurb under 10 words, description), draw the architecture and trust-boundary diagram, and make the 16:9 cover image.
- **Status:** backlog
- **Also:** the whole team
- **Needs first:** none
- **Needed later:** none
- **Phase:** 3
- **Spec:** prd 11
- **Flag:** Your list said the team. Damien is the lead here; everyone contributes. Change the lead if you prefer.
- **Note:**
- **Success criteria:**
  - [ ] Title, blurb under 10 words, description covering scenario, users, value, design and business value
  - [ ] One diagram with the trust boundaries and the key trade-offs
  - [ ] 16:9 image at 380x216
