# F12 Doctor report: how it works and what is open

**Status (2026-10-10): built by Damien's session.** **Updated 2026-10-15:** the printable report now carries four charts (glucose, blood pressure, SpO2, heart rate) with eight topic filters, and the shared link page shows the same report, charts and extras as the printable one (section 1). **Updated 2026-10-11:** the key findings are worded by an AI model from code-computed facts, with checks and a code-written fallback (decision D-081, a departure from rules.md 1.2 and 1.8 that waits for Hong Yi). The report also has a Health summary from the onboarding answers, a 14-day baseline, blood pressure readings, and "Symptoms and your latest values". The overnight section and the dates of missed doses are removed. **Fix wave (evening of 2026-10-11):** adherence is a dash, never 0%, when nothing was answered; devices are shown by name, not by code; the Data notes say SpO2 is simulated when the report's `simulated` flag is on; the share sheet's consent line is accurate (section 4). Migrations 0032 and 0035 are applied on the shared database (2026-10-11, the owner's approval). The numbers are covered by unit tests, and the fix wave ran the database tests; the report's `load()` against the real API and the screens were **not verified** in a browser. This is the doctor brief (prd F12). Hong Yi's tasks E13-1 to E13-3 cover the full brief; this document says what exists now.

## 1. What the person sees

- **Me → Doctor brief** (L1, `/brief`): choose the period (7, 14, 30 or 90 days), read the key findings, the worth-discussing items, the questions and the alerts, and tap **Open the printable report**.
- **The printable report** (L3, `/brief/a4?days=14`): a paper-style page outside the app frame, "Diabetes monitoring report", with **Print or save as PDF**. **"Back to the app"** goes back to the Doctor brief it came from (browser back), or opens the Doctor brief (L1) when the page was opened directly. It is the fix for the earlier problem after printing. Layout follows Damien's report design (an HTML mock-up of a two-page report, 2026-10-09), with the changes in section 4.

There is one report. The person sees exactly what the doctor sees (rules.md 1.8). The report is also shown on the read-only page `/s/:token` (`SharedReport.tsx`, `ReportView`).

**Charts and topic filters.** Above the sections, the printable page (and the shared page) adds, from the Insights timeline for the same period: a Health overview table (six health numbers compared with the person's own baseline), four charts (glucose, heart rate, SpO2 and blood pressure, `PrintCharts.tsx`) each with a one-line reason, and below the sections the patterns the app learnt (Confirmed or Not confirmed) and the next appointment. A filter bar (`FilterBar`) lets the person or the doctor choose what is drawn: Glucose, Heart rate, SpO2, Blood pressure, Meals, Exercise, Symptoms and Missed doses (the last four are log rows on the same time axis). All are on by default. These extras are built in code (`features/brief/extras.ts`, `analysis.ts`); no model writes them.

**Sharing (L2).** The link opens `/s/:token`, which reads `GET /api/v1/brief/shares/public/{token}/report` (the same report) and `GET /api/v1/brief/shares/public/{token}/extras` (the chart data, what the app learnt and the next visit, for the link's own period). Creating a link turns on "Share my doctor brief" in Privacy (the server grants that consent when a link is made and none is active), and the sheet says so. Turning off a link does not turn that consent off; the sheet says sharing stays on in Privacy until it is switched off there (`services/api/app/services/share.py`).

## 2. What is in the report

Sections appear in the order of `REPORT_SECTIONS` in `apps/web/src/features/brief/ReportView.tsx`. The order is held in that one constant.

| Section | Content |
|---|---|
| Header | Patient (the display name), sex and age, diabetes (self-reported), the period, sensor wear, data sources |
| **Health summary** (new) | The onboarding answers only, from `onboarding_report_fields` (migration 0032): waist and its date, year diagnosed, who looks after the diabetes, other conditions, allergies, the latest lab results with their dates, devices (shown by name; codes are mapped in `onboarding.device_display_name`). A row appears only when there is an answer: never a dash, never zero |
| **Key findings** | Three to five short labelled lines (for example Glucose, Medicines, Symptoms, Alerts). **Worded by the AI model** when the wording passes the checks in section 3, with the **"AI insight" note** under them. Otherwise the code-written findings, with no note. The code-written findings: time in range and below range with CV; how many symptom entries were logged with low glucose and at what times of day; doses marked taken per medicine and the number of interaction flags |
| Alerts | **Urgent**: any sensor reading below 3.0 mmol/L (count, days, the lowest), and any symptom logged with a reading below 3.0. **Interaction**: each open clash alert (f5-clash.md), worded "Possible interaction", with where it came from. **Review**: a symptom logged twice or more with low glucose; a symptom logged twice or more always with glucose in range (with the heart rate and SpO2 seen); doses marked missed; too little sensor data |
| Worth discussing | Up to a fixed number of items from the person's own data, most important first: a possible interaction (open clash alert, with its origin), the most common reason for missed doses (count), patterns (associated with, unverified), and confirmed ideas from the learning loop (K2) |
| Glucose (CGM) | Time in the five ranges (%, about how long a day, a reference figure); mean, GMI, standard deviation, CV, sensor active; and glucose by time of day (median, 25th to 75th and 5th to 95th percentile bands) |
| **Baseline: the first 14 days of sensor data** (new) | The first 14 days of sensor data on record, beside the chosen period: average, time in range, GMI, and the difference worded "higher than" or "lower than", never good or bad. A plain note when there is no sensor data or fewer than 14 days; a warning when the sensor was worn for little of the baseline |
| Symptoms and glucose | Per symptom: entries logged, and how many had a low, high or in-range reading, or no reading within 15 minutes |
| **Symptoms and your latest values** (new) | Each symptom in the period beside the latest HbA1c, blood pressure, weight and waist on record (the latest may be outside the period). Worded "logged together with". It does not show a cause |
| Symptom entries | The latest 20 entries: time, symptom and the person's note, the reading, the change over the 30 minutes before, heart rate and SpO2, and the last dose marked taken in the 6 hours before |
| Medications | Per medicine: regimen, doses scheduled, taken, missed, not logged, adherence (a dash, never 0%, when no dose was answered), and an Interaction tag if it is in an open clash alert. Adherence counts prescription medicines only. **The dates of missed doses are no longer shown**; the counts and the reasons are |
| Activity, heart rate and wellbeing | Steps a day, heart rate while asleep, SpO2 while asleep, days with self-rated stress of 4 or 5 |
| **Blood pressure readings** (new) | The readings as logged (top, bottom, pulse, time), the count and the ranges. Never called high, low or normal |
| Patient's questions | The open doctor questions (including those saved from a clash alert and from K12) |
| Data notes | The limits of each data source, and "not a diagnosis". Wrist SpO2 is also marked "simulated in the demo data" when the person's sensor or watch rows come from the demo dataset (`simulated` flag, `doctor_report.py`) |

**Removed:** the **overnight glucose** section and its calculation (`_overnight`), which Hong Yi's earlier work had added. Heart rate and SpO2 while asleep stay under Activity, heart rate and wellbeing.

## 3. Rules the report follows

- **Every number is computed in code** (`services/api/app/services/doctor_report.py`). The AI model may word the key findings, and only those (decision D-081, section 3.1). No other sentence is written by a model.
- **It shows what was recorded together, never why.** A symptom sits next to the reading and the last dose before it; the report does not say one led to the other. The words "caused", "because", "normal", "safe", "should" and "validated" do not appear in the code-written text, and a unit test checks this.
- **No medication advice** and no diagnosis (rules.md 1.1, 1.6).
- **No data is shown as "No data" or a dash, never as 0** (rules.md 1.7). A symptom with no reading nearby is counted as "No reading", not as in range. Hours of the day with fewer than 5 readings are left blank on the chart.
- **The reference figures are not targets.** Time in range above 70%, below range under 4% (under 1% below 3.0), above range under 25% (under 5% above 13.9), CV at most 36%, sensor active at least 70%: these are the general consensus figures in Damien's design, kept in one constant (`REFERENCE`) marked "clinical validation pending". The in-range band itself comes from the person's `user_profile.glucose_target_low` and `glucose_target_high`.
- **GMI** is the published formula, 3.31 + 0.02392 x mean glucose in mg/dL, labelled "estimated from mean glucose".
- **Below 70% sensor wear** the glucose figures are still shown, with a line saying they may not be representative and a Review alert.
- **The baseline is fixed.** It is the first 14 days of sensor data on record and is only reset on purpose (data model v2, D-060).

### 3.1 The AI key findings (decision D-081, 2026-10-11)

This departs from rules.md 1.2 (no AI in the brief) and 1.8. Joely decided it on 2026-10-11 (implementation plan section 13, item 5). Hong Yi is to confirm it. The module is `services/api/app/agents/report_insight.py`.

| Safeguard | What it does |
|---|---|
| Facts only | The model is given the computed fact lines of one report and nothing else: no names of people, no dates, no free text. Medicines appear by name only, never with a strength |
| Numbers must match | Every number in a line must appear in the facts. A line with a number that is not in the facts is dropped |
| Shape | 3 to 5 lines, each with a plain label of one or two words and one short sentence. The prompt asks for at most 25 words; the code keeps a line of 15 to 200 characters |
| Banned words | A line with advice, a dose or a unit (mg, mcg, tablets), a judgement (good, bad, normal, safe, better, worse) or a cause (caused, because, due, leads to, results) is dropped |
| Fallback | If fewer than 3 lines pass, or the model is unavailable, refused by its daily limit (`vertex_generate`), or its answer cannot be read, the code-written findings are shown and the note is not shown |
| No retry loop | The report never waits on a second try. A failed try is not repeated for 10 minutes |
| Cache | A worded result is kept for a day per person, period and facts (a fingerprint), so a page load or a print does not call the model again |
| Logs | Nothing from the facts or the answer is logged; only the kind of failure is |

The AI wording is checked by the same code as the rest of the report; it can change words only, never the numbers.

## 4. What was left out of the design, and why

| In the design | What the report does instead |
|---|---|
| "Hypoglycaemia clusters 2–3 h after gliclazide", "highs follow missed doses", "breathlessness is not explained by glucose", "the faint followed a fluconazole dose" | Says how many entries had low glucose and when, and shows the last dose before each entry. Linking them is for the clinician. A "missed doses followed by highs" pattern also needs at least 5 pairs under the project's pattern rule |
| "Since gliclazide" column | "Last dose taken before" (any medicine, within 6 hours). Choosing which medicine matters is a clinical judgement |
| "can raise gliclazide levels and hypoglycaemia risk. Source: [drug interaction database]" | The clash alert's own stored reason and its real origin (drug-label rules, AI web search), marked not clinically reviewed |
| "Target" columns | "Reference", with the note above |
| Fainting and breathlessness rows | The symptom list has no fainting or breathlessness type (`symptom_kind`); the report shows whatever types were logged, with the person's note |
| Resting heart rate, overnight SpO2 as device figures | Heart rate and SpO2 while asleep, from the watch's 5-minute rows. SpO2 is simulated in the demo data (prd A15) and the report says so |
| Year of diagnosis | **Now in the Health summary** (`user_profile.diagnosed_year`, from onboarding page 4) |
| Overnight section beside glucose (Hong Yi's earlier addition) | **Removed on 2026-10-11** (implementation plan, section 5) |
| Dates of missed doses | **Removed on 2026-10-11**; counts and reasons remain |
| Fixed two pages with page numbers | One flowing page that breaks before the detail part when printed, so long tables are not cut off |
| IBM Plex Sans, embedded | The app's own typeface |

**Left open (decision D-091).** The four small summary tables at the top of the report and the position of the glucose section were **not changed**. Joely will decide later (Q4 of the implementation plan).

## 5. The period

The period ends on the day of the person's latest sensor reading (today if there is none) and runs back 7, 14, 30 or 90 days in their timezone. This keeps a full report for a person whose data stops earlier, such as Mr Tan's example record.

## 6. Where things are

| What | Where |
|---|---|
| Calculations (pure, no database) and the row reader | `services/api/app/services/doctor_report.py` (`build`, `load`, `read`, `assemble`) |
| The AI wording and its checks | `services/api/app/agents/report_insight.py` (prompt version `report-insight-1`) |
| Onboarding answers in the report | `services/api/app/services/onboarding.py` (`onboarding_report_fields`) |
| Route | `GET /api/v1/brief/report?days=14` in `app/api/routers/brief.py`; shape in `app/schemas/brief.py`. The read-only page uses `GET /api/v1/brief/shares/public/{token}/report` and `.../extras` (`app/api/routers/share.py`, `app/services/share.py`) |
| Screens | `apps/web/src/features/brief/BriefHome.tsx` (L1), `ReportA4.tsx` (L3, with "Back to the app" and print) and `ReportView.tsx` (the sections), `PrintCharts.tsx` (the four charts and the filter bar), `extras.ts` and `analysis.ts` (health overview and reasons), `ShareSheet.tsx` (L2), `SharedReport.tsx` (`/s/:token`), `report.css` |
| Tests | `services/api/tests/unit/test_doctor_report.py` (band boundaries, percentages adding up, mean, SD, CV and GMI, no data, too little data, the daily profile, symptom matching, dose counts, alert order and wording, activity, the API shape); `tests/unit/test_doctor_report_brief.py` and `tests/unit/test_report_insight.py` (added 2026-10-11); `tests/unit/test_share.py` for the share link |

Tables read: `user_profile`, `cgm_readings`, `symptom_logs`, `medications`, `medication_log`, `watch_readings`, `wellbeing_logs`, `interaction_alerts`, `doctor_questions`, `blood_pressure_readings`, `body_measurements`, `conditions`, `allergies`, `lab_results`, `devices`. Nothing is written.

## 7. Not done, and open

- **`load()` against the shared database is not verified in the records of this file.** Someone with the `.env` should open `/brief` as Mr Tan and add a database test. Migrations 0032 and 0035 are applied (2026-10-11), so the onboarding and blood pressure sections can appear.
- **Doctor brief sections not yet verified against Mr Tan's data:** his file-imported lab results do not reach the Health summary (QA finding, not traced in this pass).
- **Clinical review** of the reference figures, the alert rules (what counts as Urgent or Review), the fixed sentences and the AI wording. Damien designed the layout; he has not signed off the wording.
- **Hong Yi to confirm** the AI key findings (D-081), since they depart from rules.md 1.2 and 1.8 and the "Worth discussing" and overnight sections are his.
- **Left open:** the four top tables and the glucose position (D-091).
- The rest of prd F12: nutrition, exercise and sleep sections, preventive care status, day traces, data completeness per stream, and a server-made PDF (the share link, L2, is built). The older `BriefData` type and `getBrief` in `apps/web` are untouched and still unwired.
- Events (`brief.viewed`, `brief.pdf.downloaded`) are not emitted.
- The report is not saved in `briefs`; it is recomputed each time (the AI wording is cached in memory for a day).
- Strings on the printable page are English only and not yet in the translation files.

**Example record (2026-10-16):** Mr Tan's record is read-only for everyone, with one exception: a visitor may make a doctor link from it (`POST /brief/shares`) and turn it off (`DELETE /brief/shares/{id}`), so a reviewer can open a dedicated report. The link shows the same report anyone already sees on his record. The guard is `EXAMPLE_MAY_SHARE_RE` in `app/main.py`; the test is in `tests/unit/test_share.py`.
