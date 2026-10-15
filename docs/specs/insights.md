# Insights tab (screens C1 to C6, C7 and C8)

What the person sees, where each number comes from, and what is not built yet. Built 2026-10-10. **Updated 2026-10-11:** the Overview month calendar, the heart rate and SpO2 block, the blood pressure card, the Food tab with its macros, recent entries and calendar, and the Medication tab changes. **Updated 2026-10-15 from the code:** the Overview is now one shared-axis timeline (glucose, heart rate, SpO2, blood pressure) with a Health overview, a baseline comparison, What changed and What Equinox has learnt beside it; the month calendar moved to Home as "Your days"; Glucose, Food and Medication were rebuilt; Your day (D1) reads `GET /insights/day`.

## Rule

Every number is computed by the server from stored data (`app/services/insights.py`, `app/services/insights_heart.py`). No model is called. The screens only lay the numbers out.
A comparison is "associated with", never "caused by", and carries the "Unverified" tag. A finding is shown only when the nightly job
(`pattern_candidates`) had at least 5 matching events. A food is ranked only after it has been seen twice.

## Period

7, 30 or 90 days, one switch shared by the tabs (on the Overview the switch sits inside the timeline). The Medication tab has no such switch: it browses one calendar month at a time. The period ends on the latest day that has any data (today if there is none), the same rule
as the doctor report, so a loaded patient whose data stops earlier still sees a full period. "What changed" compares the period with the
same number of days before it.

**Exception:** the heart rate and SpO2 block ends on the day of the person's **last watch reading**, not on the end the other tabs use. The screen says so when the two differ.

## Endpoints (read-only, `X-User` header like every other route)

| Route | Screen | Reads |
|---|---|---|
| `GET /insights/overview?days=` | C1 "What changed" and findings | `daily_summary`, `cgm_readings`, `pattern_candidates` |
| `GET /insights/timeline?days=&end=` | C1 timeline: glucose, heart rate, SpO2 and blood pressure on one time axis, the person's own baseline, the Health overview tiles and the stats bar (`days` 7, 14, 30 or 90; `end` moves the period back, never later than the latest day with data) | `timeline_5min` (the Gold 5-minute table), plus the logs for the lanes |
| `GET /insights/overview/days?from=&to=` | "Your days" calendar on Home (one square per day, the measure picked; a month at a time; never a day after today) | `daily_summary`, and the logs for meals and active minutes (`food_logs`, `exercise_logs`) |
| `GET /insights/day?date=` | D1 "Your day": the 5-minute series, the hourly baseline, what was logged, two ideas for tomorrow (`app/services/insights_day.py`) | `timeline_5min`, the logs (not checked table by table) |
| `GET /insights/glucose?days=` | C2 time in range, the headline numbers (average, GMI, CV, sensor worn), glucose by day (average, morning, highest), the usual morning level, the hour-of-day pattern, findings | `cgm_readings`, `daily_summary`, `glucose_events`, `user_profile` targets |
| `GET /insights/food?days=` | C3 day-by-day macros, findings, food responses, recent meals, calendar (with `GET /memory/progress/days`) | `food_logs`, `meal_response`, `daily_summary` |
| `GET /insights/activity?days=` | C4 goal rings, 4 weeks by intensity, mix, workouts, steps. The heart rate and SpO2 block is loaded separately (see `/insights/heart`) | `exercise_logs`, `exercise_response`, `daily_summary` |
| `GET /insights/sleep?days=` | C5 sleep, mood and stress. The heart rate and SpO2 block and the blood pressure card are loaded separately (see the two rows below) | `daily_summary` |
| `GET /insights/heart?days=` | The heart rate and SpO2 block (C4 and C5) | `watch_readings`, `daily_summary` (resting heart rate) |
| `GET /insights/blood-pressure?days=` | The blood pressure card (C5) | `blood_pressure_readings` |
| `GET /insights/medication?month=` | C6 month calendar (a medicine filter and a day panel), adherence, the missed or unconfirmed list, reasons (`month=YYYY-MM` or `latest`; `?days=` still works) | `medications`, `medication_log` |
| `GET /insights/sprint` | C8 latest 14 days of sensor data | `cgm_readings`, `meal_response` |
| (screen only) | C7 "Why am I seeing this?" sheet, opened from every chart | static text per topic |

There is no separate web route for the heart rate or blood pressure endpoints. They are blocks inside Activity (C4) and Sleep and stress (C5).

## Definitions

- **Fasting glucose**: the average of readings between 05:00 and 07:00 local. The same definition the nightly job uses.
- **Usual range**: the 25th to 75th percentile of fasting glucose in the 60 days before the period (needs 7 days of it). The drift card appears when the weekly median has been above the 75th percentile for 2 or more weeks in a row.
- **Time in range**: the person's own targets from `user_profile`, else 3.9 to 10.0 mmol/L.
- **GMI**: 3.31 + 0.02392 x mean glucose in mg/dL. An estimate, not a lab A1c.
- **Late dose**: taken more than 60 minutes after its time. **Unconfirmed**: the window passed and nobody answered; it counts as not taken.
- **Adherence**: prescription medicines only, taken out of taken + missed + unconfirmed (`insights.py`, medication). A non-prescription row is listed as "Not counted in adherence". With nothing answered there is no percentage (a dash, never 0%). Whether pending doses belong in the denominator is an open owner decision (implementation plan, section 14.4).
- **Active minutes**: intensity 3 or more. Light is 1 to 2, moderate 3, vigorous 4 or 5. A workout with no rating (intensity null) is not counted. Goals 150 minutes and 2 strength sessions a week.
- **One "Why am I seeing this?" link per tab**, at the top of the tab, shown in every state (loading, empty, error, data). A chart's own copy has been removed.
- **Activity labels**: light, moderate and vigorous in the quick log are **as the person rated the effort**, not from heart rate. The strength tracker's labels come from heart rate (`workout_effort.py`, placeholders pending clinical review) and are not shown when heart-rate coverage is under 70% or a beta-blocker is on the medicine list.
- **Food ranking**: median rise (2 hours after the meal, from `meal_response`) per food name, gentlest first, only foods seen at least twice. `spike_flag` is not used: it is set for nearly every meal.
- **Macros**: calories (4, 4 and 9 kcal per gram for carbohydrate, protein and fat), carbohydrate, protein, fat and salt per day. A day with any meal whose value is unknown shows a gap, never a lower total. No goal lines.
- **Heart rate and SpO2 block**: the day's average and resting heart rate (`daily_summary.resting_hr_bpm`) and SpO2, from the watch's 5-minute rows. Heart rate and SpO2 while asleep use the same night rule as the doctor brief (a night belongs to the morning it ends on). A day without watch data is a gap. SpO2 from a wrist watch is less accurate than a fingertip meter, and the screen says so. Nothing is judged normal, high or low.
- **Blood pressure card**: the newest readings the person logged by hand (top, bottom and pulse), with the time. No judgement wording.
- **"Your days" calendar (on Home, not on C1 any more)**: one square for each day of the month for the measure picked (meals logged, active minutes, sleep, stress, doses taken; there is no glucose choice). A dash means no data. It opens on the current month and never goes past it. Tapping a day opens the Day view (D1).
- **Overview timeline (C1)**: the chart pills switch glucose, heart rate, SpO2, blood pressure and the log lanes (meals, exercise, symptoms, missed doses, work) on or off. At 7 days it shows every half hour and a day or a 7-day window can be picked in a calendar; at 30 and 90 days it shows one point a day and the days that stood out (the highest and lowest 5% of daily glucose) are circled. The only reference line is the person's baseline: their average for each hour over the 14 days before the period (blood pressure: one fixed number). Nothing is called good or bad.
- **Health overview (C1)**: six tiles for the period, each graded against the person's own baseline (the 14 days before the period); doses taken and sensor worn are graded by consistency (`healthGrade.ts`).

## Not built

- **Bedtime regularity** and a sleep baseline band. There is no bedtime in the data model yet.
- **A timed sensor sprint** (start, status, end). C8 summarises the latest 14 days and says so. It needs the sensor connection (K4).
- **Heart rate as a separate tab.** It is a block in Activity and Sleep (decision Q6).
- **SpO2 beside glucose on the glucose tab.** SpO2 has no real source in the demo data (simulated, prd A15). The Overview timeline and the heart rate block do show watch SpO2 where the person has it.
- **Languages**: Chinese, Malay and Tamil files exist per area (`i18n/locales/<lang>/`: app, insights, log, me, meds, onboarding). Translations are not reviewed, and strings added since may still be English only.
- **Sleep page copy**: the explanatory text was cut back on 2026-10-11 (not checked line by line against the previous version).
