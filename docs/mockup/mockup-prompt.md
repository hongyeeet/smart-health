# Prompt for Claude Design: Smart Health interactive mockup

Copy everything below the line into Claude Design.

---

Design a high-fidelity, clickable mobile app prototype called **Smart Health**. It is an AI health companion for working adults aged 40 to 65+ who live with Type 2 diabetes. The prototype exists so a 3-person hackathon team can see how the whole product works end to end. Build it as linked screens with working navigation, not disconnected pictures. Also design one A4 "doctor brief" document view.

## 1. What the product is

Smart Health learns one person from their own data and turns it into two things: daily support for the patient, and a clear summary for their doctor. It combines many data types on one clock: food, glucose readings and sensor data, watch data (heart rate, steps, sleep, stress), workouts, medications, symptoms and mood. It then shows how these fit together, so the person and the doctor can see how the person has been living their life.

It **explains, organises and reminds**. It never gives medication advice, never diagnoses, and never says "normal" or "abnormal". Trends are phrased as "higher than your usual" and "worth mentioning to your doctor".

Most of the app is **dashboards and insights**. Logging exists to feed them. Data sources (smart watch, glucose sensor, phone camera) are outside the app: do NOT design their screens. They only supply data, shown as a small "Connected sources" row and status chips.

## 2. Users and context

Working adults, 40 to 65+, mostly desk-based, some with long or late hours, not tech-savvy, many wearing reading glasses. They open the app in short moments between tasks and in the evening. Design for glanceability, large text, few taps, and a calm tone. Never nag, never blame ("not confirmed", not "you failed").

## 3. Design system (follow strictly)

- **Colour tokens (light):** background #F7F8F6, surface #FFFFFF, text #1C2426, secondary text #4B5563, border #E3E7E6, primary teal #0F766E (pressed #115E59, soft #E6F4F1), warm accent #C2410C used sparingly.
- **Dark mode:** design every screen in dark too (background #0F1416, surface #172024, primary #2DD4BF).
- **Status colours always paired with an icon and a text label, never colour alone:** success #15803D, warning #B45309, danger #B91C1C, info #1D4ED8 (each with a soft tint background).
- **Glucose ranges in charts (fills, with patterns for grayscale):** very low (dark red), low (red), in range (green), high (yellow), very high (orange).
- **Typeface:** Atkinson Hyperlegible for everything (fallback system sans). Body text 18px minimum, secondary 16px minimum, screen titles 28px bold, big readings 40px bold, tabular numbers. Sentence case. No all caps.
- **Shape and spacing:** 4-point spacing scale, 20px screen padding, cards with a hairline border and 16px radius, no heavy shadows. Touch targets at least 48px. One primary action per screen (full-width, 56px).
- **Icons:** simple outline icons with text labels. No emoji.
- **Tone:** short, plain sentences at about a grade 6 to 8 reading level. Units always shown (mmol/L, mg, min, steps, hours).
- **Frames:** phone 390 x 844 for the app. A4 portrait for the brief. Show a small "Demo data" tag in the corner of the prototype.

## 4. Demo patient and data (use these numbers consistently on every screen)

**Mr Tan, 58**, project manager, desk-based, deadline week. Type 2 diabetes for 6 years. Last HbA1c 7.4%, 4 months ago. Eye screening overdue, foot check due in 3 weeks, next diabetes review in 9 days.

- **Medications:** Metformin 500 mg, twice daily with food (8:00 am, 8:00 pm). Amlodipine 5 mg once daily (8:00 am, for blood pressure). Atorvastatin 20 mg at night (10:00 pm). Supplement: fish oil. One herbal tonic shows the state "not checked".
- **Glucose:** he is on day 9 of a 14-day glucose-sensor "sprint" (a short period of continuous monitoring). Last 24 hours in range (3.9 to 10.0 mmol/L): 78%. This week: 71%. Fasting readings, last 7 mornings: 7.1, 7.3, 7.2, 7.6, 7.8, 7.5, 7.9 mmol/L. His personal 28-day baseline is 6.6 to 7.2, so the trend is "higher than your usual" for about 3 weeks.
- **Food today:** 8:10 am toast with egg and coffee (peak glucose rise +1.2). 1:05 pm rice with chicken and vegetables (rise +3.4). His spikiest meals are white-rice lunches with little fibre (about +3.4). His gentlest are vegetable-and-egg breakfasts (about +1.2). Local dish names are fine (for example chicken rice, kaya toast, laksa); their nutrients are AI-estimated and tagged "Estimated" until the user confirms, while the glucose rise is from the sensor.
- **Activity:** steps today 5,840 so far. 7-day average 6,300, 28-day baseline about 8,000. This week so far: Monday brisk walk 30 min (moderate), Wednesday brisk walk 25 min (moderate). Moderate minutes 55 of a 150 goal. Strength sessions 0 of 2. Last 4 weeks of moderate minutes: 140, 120, 95, 70 (declining).
- **Sleep and stress:** last night 5 h 50 min. 7-day average 6 h 10 min, baseline 6 h 50 min. Evening check-in: mood 3 of 5, stress 4 of 5.
- **Adherence:** 24 of 28 doses taken this week (86%). Missed: Friday evening metformin (reason "forgot") and Sunday evening metformin (reason "away from home"). Two other doses unconfirmed.
- **Things the app has learned:** walks after dinner about 3 evenings a week (high confidence, 14 observations); misses the evening dose on days he works past 8 pm; sleeps less Sunday to Wednesday; white-rice lunches raise his glucose most; acts on reminders at 7:30 pm more than at 6:00 pm.
- **Patterns for the doctor (labelled "unverified, associated with, not a cause"):** on mornings after an evening walk (7 nights) fasting glucose was 0.6 mmol/L lower; on nights with under 6 hours of sleep (6 nights) it was 0.5 mmol/L higher.
- **His own doctor questions:** "Is my morning sugar rising because of my sleep?" and "Should I be checking my feet more often?"

## 5. Navigation

Bottom bar with 5 items: **Home, Insights, Log (centre, prominent), Medications, Me**. A floating "Ask" button on Home and Insights opens the Chat screen. Screens open as full pages or bottom sheets as described. Every back arrow and every link named below must work.

## 6. Screens (build all, link as described)

### A. Onboarding (3 screens)
1. **Welcome:** what Smart Health does and does not do (one line each), language choice (English / 中文 / Bahasa Melayu / தமிழ்), consent to use data (required), consent to share a doctor brief (optional). Next.
2. **About you:** age, diagnosis year, typical work week (desk / shifts / on my feet), medicines (buttons: "Scan a label" or "Add by hand"), reminder times. Next.
3. **Connect your data:** three rows with status: Smart watch (connected), Glucose sensor (connected), Phone camera (allowed). Text: "These only send data to Smart Health." Finish goes to Home.

### B. Home (dashboard, the most important screen)
Greeting and date, then in this order:
1. **Alert strip** (only when relevant): "Your morning readings have been higher than your usual for 3 weeks. Worth mentioning to your doctor." Tap goes to Insights, Glucose.
2. **Today at a glance** (4 compact tiles): Glucose (78% in range, latest 7.8), Activity (5,840 steps, 55 of 150 min this week), Sleep (5 h 50 min), Mood and stress (3 and 4). Each tile taps into its Insights tab.
3. **Doses due now:** Metformin 500 mg, 8:00 pm, "with food". Big "Taken" button. Below it: "Yesterday's evening dose is not confirmed" with a "Tell us why" link that opens the Miss-reason sheet.
4. **Exercise prompt card:** "Your usual after-dinner walk is coming up. On days you walked after dinner, your evening readings were lower." Buttons: "Log a walk", "Not today", "Remind me later". "Log a walk" opens the Log workout screen.
5. **What changed this week** (3 plain lines, each taps to the matching insight): fasting glucose drifting up; fewer evening walks (4 last week, 1 this week); shorter sleep on work nights.
6. **Next up:** diabetes review in 9 days, with "Prepare for the visit" that opens the Care plan.
7. A "Connected sources" row of small chips (watch, sensor, camera) with last-synced times. A small "Simulate a low reading" link (prototype only) opens the Urgent screen.

### C. Insights (dashboard with tabs)
A segmented tab bar under the title: **Overview, Glucose, Food, Activity, Sleep and stress, Medication.** Period switch: 7 / 30 / 90 days. Every chart has a one-line plain summary above it and a "Why am I seeing this?" link.

- **Overview: "Your week" grid.** Rows: glucose in range, meals logged, activity minutes, sleep hours, stress, doses taken. Columns: the last 7 days. Each cell is coloured, patterned and numbered. Tap a day to open the Day view. Below: the three "What changed" cards, and a "See your day" link.
- **Glucose:** fasting glucose line with the shaded personal baseline band and the sensor days highlighted; time-in-range bar; a card "Higher than your usual for about 3 weeks".
- **Food:** meal list with salt and sugar flags; "Your meal responses" leaderboard from gentlest to spikiest with the number of times observed (n) and the range. Foods with fewer than 2 observations are marked "still learning".
- **Activity (a key dashboard, see section 7).**
- **Sleep and stress:** sleep duration and bedtime regularity against the baseline band; mood and stress check-in trend; a card "Nights with under 6 hours of sleep: fasting glucose was 0.5 mmol/L higher (associated with, not proven)".
- **Medication:** the prescription timeline chart (one row per medicine, one column per day, cells: taken, late, unconfirmed, missed, with the fasting glucose line overlaid); adherence 86%; reasons breakdown (forgot, away from home).

### D. Day view (the multimodal fusion screen)
Opened from Overview (tap a day), from Home tiles, and from Log confirmations. One day on a single vertical or horizontal timeline: the glucose line with range shading, with markers for meals (with carb amounts and salt or sugar flags), doses (taken, unconfirmed, missed), workouts (type and intensity), symptoms; below, aligned heart rate and steps, and sleep bands. Missing data shows as a gap, never an interpolated line. Tap any marker for a bottom sheet with the details and the outcome (for example, "2 hours after this meal your glucose rose 3.4, more than your usual for lunch"). Date arrows to move between days.

### E. Log hub and logging screens
The centre Log button opens a hub with big tiles: **Workout, Meal, Glucose, Symptom, Mood and sleep check-in.** A "Recent entries" list below. Each logging screen is fast (at most 3 to 4 taps for the simple ones) and ends with a confirmation showing where the entry landed, with links to the Day view and the related Insights tab.

- **Log meal:** photo or a typed description; the AI returns the items and estimated calories, carbs, protein, fat, fibre, sugar and salt, each tagged "Estimated" with tap to edit or confirm; portion stepper; a flag like "High salt". Save then confirmation.
- **Log glucose:** big number pad, context chips (fasting, before meal, 2 h after meal, bedtime, random), shows the range colour and text after saving.
- **Symptom:** picker with severity 1 to 5, optional note.
- **Mood and sleep check-in:** mood, stress, sleep quality, energy, each 1 to 5, 30 seconds.

### F. Log workout (important, design carefully)
Purpose: capture how the person really moves so the doctor sees how they live.
1. **"From your watch" suggestion card at the top:** "Brisk walk, 32 min, average heart rate 108, 7:35 pm. Add it?" Buttons: Confirm, Edit, Not a workout.
2. **Type (4 big choices, each with a one-line plain description):** *Aerobic* (steady effort that raises breathing: walking, cycling, swimming), *Strength* (short hard effort against resistance, anaerobic: weights, bands, bodyweight), *Mixed* (circuit or interval training), *Flexibility and balance* (yoga, tai chi, stretching).
3. **Activity chips that change with the type,** plus "Other". Aerobic: brisk walk, jog, cycling, swimming, dancing, hiking, badminton. Strength: weights, resistance bands, bodyweight, circuit. Mixed: HIIT, sports. Flexibility: yoga, tai chi, stretching.
4. **Intensity (3 large cards with a talk test):** Light ("I can talk or sing easily"), Moderate ("I can talk but not sing"), Vigorous ("I can only say a few words"). Optional "how hard did it feel" slider from 1 to 10. If the watch heart rate is available, show "Your watch suggests moderate" as a hint the person can accept or change.
5. **Duration stepper and start time.**
6. **Auto-filled context chips:** "Last meal 1 h 50 min ago", "Glucose before: 7.8 (from your sensor)", and "We'll remind you to log a reading 30 minutes after, so your doctor can see how exercise affects you."
7. **How did you feel:** energised, fine, tired, unwell. "Unwell" offers a link to log a symptom.
8. **Save.** Confirmation shows: "Added to your day. This week: 85 of 150 minutes of moderate activity, 0 of 2 strength sessions." Links: "See your activity" (Insights, Activity) and "See your day" (Day view).

### G. Insights, Activity (a key dashboard)
- **Weekly goal rings:** moderate or vigorous minutes (55 of 150) and strength sessions (0 of 2). A small "Edit goal" link with a note "Set with your doctor".
- **Last 4 weeks:** stacked bars by intensity (light, moderate, vigorous) showing the decline (140, 120, 95, 70).
- **Mix:** aerobic versus strength versus flexibility, shown as simple bars with counts.
- **Workout list:** type icon, activity, intensity chip, duration, and the measured glucose change over the next 2 hours where a sensor was worn (for example "-1.4 mmol/L in 2 h").
- **Timing card:** when in the day he exercises versus when he eats (small strip). Insight line: "You walk after dinner on about 3 evenings a week."
- **Exercise and glucose:** "On mornings after an evening walk (7 nights), fasting glucose was 0.6 mmol/L lower. Associated with, not proven. Worth mentioning to your doctor."
- **Steps trend** with the personal baseline band (about 8,000) and this week's average (6,300).
- **Prompt card:** "Plan this week's next session", with buttons "Log a workout" and "Remind me on Thursday at 7:30 pm".

### H. Medications
- **List:** each medicine with strength, times, today's status, and a small badge: "Possible interaction" or "Not checked". A prominent "Scan a label" button.
- **Scan a label (3 steps):** camera framing screen with tips; **review screen** with each extracted field and a confidence chip (for example "Metformin 500 mg" high confidence; "Twice daily after meals" tagged "check this"; anything unreadable says "I can't read this, please type it"); then confirm, which shows the dose schedule preview.
- **Interaction sheet** (bottom sheet): fixed wording "Possible interaction between X and Y. Please check with your pharmacist or doctor before continuing." Buttons "Add to my doctor questions" and "OK". Never says stop. The herbal tonic shows "Not checked: we don't have interaction data for this item."
- **Medicine detail:** what it is for, how you take it (from your own label), common side effects, when to tell your doctor, and a source note ("Source: your label and drug information dataset, not medical advice"). A "Listen" button and a language toggle (English / 中文) that shows the page translated.
- **Miss-reason sheet** (opened from Home): one-tap reasons (forgot, side effects, ran out, felt fine, cost, away from home, other), an optional note, and "Skip". "Side effects" offers to add a symptom and a doctor question.

### I. Chat ("Ask Smart Health")
A simple chat with suggestion chips ("How was my week?", "What is metformin for?"). Include the key demo exchange: the user types "My sugar is fine today, can I skip my metformin?" The reply appears in a visibly different style (shield icon) as a fixed safety message: "I can't advise on changing your medication, but your doctor or pharmacist can. Want me to add this to your questions for your visit?" with buttons "Add to my doctor questions" and "Not now". "Add" leads to the Care plan's questions list.

### J. Urgent screen (opened from Home's "Simulate a low reading")
Full screen with a soft red background, clear icon and text: "Your glucose reading is very low: 2.8 mmol/L. Get help now." Large buttons: "Call 995", "Call my clinic", "I'm okay now". A line "Steps from your doctor's low-sugar plan will show here" (placeholder). A "Recheck in 15 minutes" timer. Make clear that this screen involves no AI.

### K. Me
A grouped list: **What Smart Health has learned about you**, **Doctor brief**, **Care plan**, **Connected sources**, **Language**, **Privacy and consent**.

- **What Smart Health has learned** (a key screen): a list of learned facts grouped by category (routines, preferences, barriers, food responses, activity), each with a confidence indicator (dots), "why I think this" (the evidence, for example "14 evenings"), and Confirm / Edit / Delete controls. Above it, a **"Week 1 vs Week 8"** comparison card: fasting baseline (6.6 then, 7.9 now, flagged), evening reminder time (6:00 pm then, 7:30 pm now), walk reminders acted on (1 of 5 then, 3 of 5 now), facts learned (2 then, 9 now), and a strip showing the data types used (food, glucose, watch, workouts, sleep, medication). A line: "Still learning: how stress affects your evenings."
- **Care plan:** next appointment card; preventive checklist (eye screening overdue, foot check due in 3 weeks, HbA1c 4 months ago, flu vaccination not recorded) each with a status chip; "My questions for the doctor" list (the two patient questions plus one added from Chat); primary button "Generate my doctor brief".
- **Connected sources:** rows for watch, sensor, camera with last synced time and "Simulate a sync" (prototype only). Text: "These only send data to Smart Health."

### L. Doctor brief (A4 view plus in-app view)
The in-app page shows a preview with "Share with my doctor" and "Download". The A4 page is dense, structured and printable in grayscale, with the footer "Generated by Smart Health from patient-reported and device data. Not a diagnosis. Numbers are computed, not written by AI." Sections in this order:
1. Header: initials and birth year, period covered (last 4 weeks), data completeness bar.
2. **Top 3 to discuss:** rising fasting glucose; reduced activity and sleep; missed evening doses.
3. **Medication and adherence:** the prescription timeline chart with glucose overlay, adherence 86%, reasons, interaction flags including the "not checked" tonic.
4. **Glucose:** fasting trend against baseline, time in range, sensor sprint summary.
5. **Nutrition:** meal responses (gentlest to spikiest), salt and sugar flags.
6. **Exercise:** minutes by intensity per week, aerobic versus strength split, activity types, timing versus meals, glucose change after workouts.
7. **Sleep and stress:** duration, regularity, mood and stress trend.
8. **Day traces:** three days (best, worst, typical) each as a mini timeline.
9. **Patterns for clinician review** (heading: "unverified, generated from patient-logged data"): the two associations from section 4.
10. **Symptoms** logged.
11. **Preventive care status.**
12. **Patient's own questions.**
13. **Data completeness** by stream.
A **Share sheet:** requires consent, link expires in 72 hours, "Revoke access", and a note "Your doctor sees exactly what you see."

## 7. Key click paths (make these work end to end)

1. **Morning:** Home, tap Taken, tap "Tell us why" on yesterday's dose, Miss-reason sheet, back to Home.
2. **Meal:** Log, Meal, salt flag shown, Save, Confirmation, Day view (new marker visible).
3. **Workout:** Home exercise prompt (or Log, Workout), accept the watch suggestion, Save, Confirmation, "See your activity" (Insights, Activity), then "See your day" (Day view).
4. **Explore a day:** Insights, Overview, tap a day in "Your week", Day view, tap a marker, detail sheet.
5. **New medicine:** Medications, Scan a label, Review, Confirm, Interaction sheet, "Add to my doctor questions", Care plan.
6. **Safety moment:** Ask button, type the metformin question, safety reply, "Add to my doctor questions", Care plan.
7. **Learning:** Me, "What Smart Health has learned", Week 1 vs Week 8, tap a fact's evidence to open the related insight.
8. **Doctor visit:** Home "Prepare for the visit" or Me, Care plan, Generate my doctor brief, Brief preview, Share sheet.
9. **Urgent:** Home, "Simulate a low reading", Urgent screen, "I'm okay now" returns to Home.

## 8. Rules

- Use only the demo data above. No lorem ipsum. Nutrients of logged meals are AI estimates shown with an "Estimated" tag.
- Do not invent health advice. No dose suggestions, no diagnoses, no "normal" or "abnormal".
- Show uncertainty honestly (the "not checked" state, "still learning", "check this").
- Every insight that compares two things says "associated with" and is labelled unverified.
- Design light and dark, 200% text size without broken layouts, and hint at accessibility (contrast, labels).
- Do not design smart watch, glucose sensor or camera app screens.
- Do not include onboarding beyond the 3 screens, login or sign-up screens, payments, or a caregiver view.
- Deliver: the linked prototype, a one-page screen index listing every screen and where it links, and the A4 brief.
