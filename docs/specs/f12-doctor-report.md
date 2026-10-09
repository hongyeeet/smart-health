# F12 Doctor report: how it works and what is open

**Status (2026-10-10): built by Damien's session, not yet run against the shared database.** The numbers are covered by unit tests; the database reads and the screens against the real API are untested (see section 7). This is the first working piece of the doctor brief (prd F12). Hong Yi's tasks E13-1 to E13-3 cover the full brief; this document says what exists now.

## 1. What the person sees

- **Me → Doctor brief** (L1, `/brief`): choose the period (7, 14, 30 or 90 days), read the key findings and the alerts, and tap **Open the printable report**.
- **The printable report** (L3, `/brief/a4?days=14`): a paper-style page outside the app frame, "Diabetes monitoring report", with **Print or save as PDF**. Layout follows Damien's report design (an HTML mock-up of a two-page report, 2026-10-09).

There is one report. The person sees exactly what the doctor sees (rules.md 1.8).

## 2. What is in the report

| Section | Content |
|---|---|
| Header | Patient (the display name), sex and age, diabetes (self-reported), the period, sensor wear, data sources |
| Key findings | Three fixed sentences filled with numbers: time in range and below range with CV; how many symptom entries were logged with low glucose and at what times of day; doses marked taken per medicine and the number of interaction flags |
| Alerts | **Urgent**: any sensor reading below 3.0 mmol/L (count, days, the lowest), and any symptom logged with a reading below 3.0. **Interaction**: each open clash alert (f5-clash.md), worded "Possible interaction", with where it came from. **Review**: a symptom logged twice or more with low glucose; a symptom logged twice or more always with glucose in range (with the heart rate and SpO2 seen); doses marked missed; too little sensor data |
| Glucose (CGM) | Time in the five ranges (%, about how long a day, a reference figure); mean, GMI, standard deviation, CV, sensor active; and glucose by time of day (median, 25th to 75th and 5th to 95th percentile bands) |
| Symptoms and glucose | Per symptom: entries logged, and how many had a low, high or in-range reading, or no reading within 15 minutes |
| Symptom entries | The latest 20 entries: time, symptom and the person's note, the reading, the change over the 30 minutes before, heart rate and SpO2, and the last dose marked taken in the 6 hours before |
| Medications | Per medicine: regimen, doses scheduled, taken, missed, not logged, adherence, and an Interaction tag if it is in an open clash alert; the dates of missed doses |
| Activity, heart rate and wellbeing | Steps a day, heart rate while asleep, SpO2 while asleep, days with self-rated stress of 4 or 5 |
| Patient's questions | The open doctor questions (including those saved from a clash alert) |
| Data notes | The limits of each data source, and "not a diagnosis" |

## 3. Rules the report follows

- **Every number is computed in code** (`services/api/app/services/doctor_report.py`); no model is called and the sentences are fixed templates (rules.md 1.2).
- **It shows what was recorded together, never why.** A symptom sits next to the reading and the last dose before it; the report does not say one led to the other. The words "caused", "because", "normal", "safe", "should" and "validated" do not appear, and a unit test checks this.
- **No medication advice** and no diagnosis (rules.md 1.1, 1.6).
- **No data is shown as "No data" or a dash, never as 0** (rules.md 1.7). A symptom with no reading nearby is counted as "No reading", not as in range. Hours of the day with fewer than 5 readings are left blank on the chart.
- **The reference figures are not targets.** Time in range above 70%, below range under 4% (under 1% below 3.0), above range under 25% (under 5% above 13.9), CV at most 36%, sensor active at least 70%: these are the general consensus figures in Damien's design, kept in one constant (`REFERENCE`) marked "clinical validation pending". The in-range band itself comes from the person's `user_profile.glucose_target_low` and `glucose_target_high`.
- **GMI** is the published formula, 3.31 + 0.02392 x mean glucose in mg/dL, labelled "estimated from mean glucose".
- **Below 70% sensor wear** the glucose figures are still shown, with a line saying they may not be representative and a Review alert.

## 4. What was left out of the design, and why

| In the design | What the report does instead |
|---|---|
| "Hypoglycaemia clusters 2–3 h after gliclazide", "highs follow missed doses", "breathlessness is not explained by glucose", "the faint followed a fluconazole dose" | Says how many entries had low glucose and when, and shows the last dose before each entry. Linking them is for the clinician. A "missed doses followed by highs" pattern also needs at least 5 pairs under the project's pattern rule |
| "Since gliclazide" column | "Last dose taken before" (any medicine, within 6 hours). Choosing which medicine matters is a clinical judgement |
| "can raise gliclazide levels and hypoglycaemia risk. Source: [drug interaction database]" | The clash alert's own stored reason and its real origin (drug-label rules, AI web search), marked not clinically reviewed |
| "Target" columns | "Reference", with the note above |
| Fainting and breathlessness rows | The symptom list has no fainting or breathlessness type (`symptom_kind`); the report shows whatever types were logged, with the person's note |
| Resting heart rate, overnight SpO2 as device figures | Heart rate and SpO2 while asleep, from the watch's 5-minute rows. SpO2 is simulated in the demo data (prd A15) and the report says so |
| Year of diagnosis | `user_profile` has no such column |
| Fixed two pages with page numbers | One flowing page that breaks before the detail part when printed, so long tables are not cut off |
| IBM Plex Sans, embedded | The app's own typeface |

## 5. The period

The period ends on the day of the person's latest sensor reading (today if there is none) and runs back 7, 14, 30 or 90 days in their timezone. This keeps a full report for a loaded demo patient whose data stops earlier.

## 6. Where things are

| What | Where |
|---|---|
| Calculations (pure, no database) and the row reader | `services/api/app/services/doctor_report.py` (`build`, `load`) |
| Route | `GET /api/v1/brief/report?days=14` in `app/api/routers/brief.py`; shape in `app/schemas/brief.py` |
| Screens | `apps/web/src/features/brief/BriefHome.tsx` (L1), `ReportA4.tsx` and `report.css` (L3) |
| Tests | `services/api/tests/unit/test_doctor_report.py` (12): band boundaries, percentages adding up, mean, SD, CV and GMI, no data, too little data, the daily profile, symptom matching, dose counts, alert order and wording, activity, the API shape |

Tables read: `user_profile`, `cgm_readings`, `symptom_logs`, `medications`, `medication_log`, `watch_readings`, `wellbeing_logs`, `interaction_alerts`, `doctor_questions`. Nothing is written.

## 7. Not done, and open

- **Not run against the database.** The session had no connection, so `load()` (nine SELECT statements) has never been executed and the screens were checked with sample data produced by `build()`, not with the live API. Someone with the `.env` should open `/brief` as Mr Tan and add a database test.
- **Clinical review** of the reference figures, the alert rules (what counts as Urgent or Review) and the fixed sentences. Damien designed the layout; the wording here was changed to fit the rules and he has not signed it off.
- The rest of prd F12: the AI narrative with evidence ids, nutrition, exercise and sleep sections, preventive care status, day traces, data completeness per stream, the share link (L2) and a server-made PDF. The older `BriefData` type and `getBrief` in `apps/web` are untouched and still unwired.
- Events (`brief.viewed`, `brief.pdf.downloaded`) are not emitted.
- The report is not saved in `briefs`; it is recomputed each time.
- Strings on the printable page are English only and not yet in the translation files.
