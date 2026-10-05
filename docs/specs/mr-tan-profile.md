# Mr Tan: demo patient profile

Written 2026-10-05 from the database before the v2 reset (backup in `data/processed/db_backup_2026-10-05/`, git-ignored). Numbers come from `python scripts/profile_mr_tan.py`, which writes `data/processed/mr_tan_profile.json` for the demo-data generator. **Mr Tan is CGMacros participant 046**, a real, anonymous person in a public dataset (CC BY-NC-SA 4.0). The name, job, family and routine in the story are invented.

## 1. Who he is

| | |
|---|---|
| Name in the app | Mr Tan (invented) |
| Born / age | 1975 / 51 (real) |
| Gender | male (real) |
| Height / weight | 170.2 cm / 81.6 kg on 2026-09-22 (real) |
| Diabetes | type 2, diagnosed 2020 (placeholder year), non-smoker |
| Other conditions | high blood pressure; father had type 2 diabetes (simulated history) |
| Race | not in the database (it is in the CGMacros `bio.csv`, which is not on this machine) |
| Home | Singapore, timezone Asia/Singapore, language English |
| Work (v2, invented) | Monday to Friday 08:30 to 17:30, standing job |
| Emergency contact (v2, invented) | spouse, made-up phone number |
| Devices | watch: Fitbit Sense (the CGMacros wearable); CGM: Dexcom G6, 5-minute readings (a Libre Pro was worn at the same time and is not used in v2) |
| Goals | 150 moderate minutes a week, 2 strength sessions a week (simulated) |

## 2. Medicines

All simulated in E1-4 except that the drug names match the reference list. v2 adds a schedule row per dose time with quantity and before / after meal.

| Medicine | Kind | Dose | Times | Meal relation (v2) |
|---|---|---|---|---|
| Metformin 500 mg | prescription | 1 tablet | 08:00, 20:00 | after meal (with food) |
| Amlodipine 5 mg | prescription | 1 tablet | 08:00 | n/a |
| Atorvastatin 20 mg | prescription | 1 tablet | 22:00 | n/a |
| Fish oil | supplement | 1 capsule | with a meal | after meal |
| Herbal tonic (label not readable) | TCM | unknown | unknown | n/a; no drug match, so the app says "not checked" |

Demo interaction: clarithromycin interacts with atorvastatin and with amlodipine in the openFDA label text.

## 3. What is real and what is not

| Data | Status | Coverage |
|---|---|---|
| CGM glucose, Dexcom G6 | **real** | 2026-09-22 09:45 to 2026-10-02 07:40 Singapore time: 9.9 days, 2,856 five-minute buckets |
| CGM glucose, Libre Pro | real, not used in v2 | 15-minute readings over the same days; reads about 0.7 mmol/L lower |
| Heart rate | **real** (Fitbit Sense) | 2,733 five-minute buckets over the same days |
| Active energy | real | per minute over the same days |
| Meals with macros | **real**: 29 meals | 2026-09-22 to 2026-10-01 (the other 147 meals in the database are copies, simulated) |
| Labs | **real**: HbA1c 7.4% (2026-09-22), fasting glucose 8.56 mmol/L, total cholesterol 8.92, LDL 6.72, HDL 1.6, triglycerides 1.42 mmol/L | HbA1c 6.9% (2025-09-25) and 7.1% (2026-03-26) are simulated history; fasting insulin is in `bio.csv` and not available here |
| Weight | real on 2026-09-22; earlier values simulated | |
| Everything else in his 60-day history | **simulated**: steps, sleep, doses, mood, workouts, blood pressure, symptoms, appointments, preventive status | not used as a model for the new data |
| Not available at all | HRV, SpO2, blood pressure from the dataset | HRV will be borrowed from another participant; SpO2 and blood pressure simulated |

## 4. His real glucose

Dexcom G6, 5-minute buckets, 9.9 days.

| Measure | Value |
|---|---|
| Mean / SD / coefficient of variation | 10.33 mmol/L / 3.13 / 30.3% |
| Range | 3.2 to 21.2 |
| Time in range (3.9 to 10.0) | **53.3%** |
| Time above 10.0 / above 13.9 / below 3.9 | 46.4% / 13.0% / 0.3% |
| Libre Pro for comparison | mean 9.60, time in range 63.7% |

Daily mean: 8.4 to 9.5 on 22 to 25 Sep, rising to 11.0, 11.9 and **14.0** on 26 to 28 Sep, then back to 10.5, 10.1, 9.4 and 10.5. So the real days are the "worse" end of the story, and one very high stretch (26 to 28 Sep) is real.

Typical day (median by local hour, mmol/L): night 0 to 2 h about 11 to 12; falls to 8.4 to 8.8 at 5 to 7 h (his real "fasting" level, 05:00 to 07:00); breakfast spike to 11.1 and 13.0 at 8 to 9 h; lowest 7.3 to 7.6 at 11 to 14 h; evening 10.2 to 11.4 from 16 h to midnight.

## 5. How he responds to meals (29 real meals)

- Mean rise **4.8 mmol/L**, mean time to peak 111 minutes. Peaks are long and late.
- Breakfast is the worst: 66 g carbohydrate with no fibre (a recurring meal) rose 5.9 to 9.1 mmol/L within 35 to 90 minutes, peaking at 14.6 to 18.4.
- Meals with fibre of 10 g or more rose 0.5 to 3.2. Lunches are gentler than breakfasts.
- Carbohydrate alone explains little in his data (r = 0.24 across the 29 meals; slope 0.033 mmol/L per net gram of carbohydrate, intercept 3.1). Fibre, time of day and the glucose level before the meal matter more, and logged meal times are approximate. The generator therefore uses a response that depends on carbohydrate, fibre, time of day and starting glucose, and plants a clearer carbohydrate effect than 0.24 so the link is visible in the charts.

| Meal (local time) | Carbs g | Fibre g | Pre | Peak | Rise | Minutes to peak |
|---|---|---|---|---|---|---|
| 22 Sep 11:58 lunch | 81 | 18 | 9.0 | 9.5 | 0.5 | 175 |
| 23 Sep 08:00 breakfast | 66 | 0 | 6.7 | 14.6 | 7.9 | 70 |
| 24 Sep 08:00 breakfast | 66 | 0 | 7.4 | 14.7 | 7.4 | 60 |
| 25 Sep 08:06 breakfast | 66 | 0 | 7.8 | 13.7 | 5.9 | 35 |
| 26 Sep 08:00 breakfast | 73 | 7 | 7.3 | 16.4 | 9.1 | 90 |
| 26 Sep 19:30 dinner | 44 | 0 | 7.2 | 20.4 | 13.2 | 180 |
| 27 Sep 12:00 lunch | 93 | 4 | 7.7 | 16.1 | 8.4 | 85 |
| 28 Sep 07:55 breakfast | 66 | 0 | 9.4 | 18.4 | 8.9 | 70 |
| 29 Sep 11:43 lunch | 40 | 13 | 7.3 | 7.8 | 0.5 | 5 |
| 30 Sep 07:59 breakfast | 66 | 0 | 9.3 | 16.5 | 7.2 | 65 |
| 1 Oct 11:46 lunch | 94 | 4 | 6.7 | 9.4 | 2.7 | 90 |

(A selection; all 29 are in `mr_tan_profile.json`. The dataset's "dinner" meals are logged between 14:28 and 19:30, so they are not always evening.)

## 6. Heart rate

Mean 87 bpm (SD 10.9). Lowest in the small hours: median 70 to 71 bpm at 4 to 6 h, 73 to 83 bpm from midnight to 3 h. Daytime medians 88 to 93 bpm, and evenings run **98 to 100 bpm at 17 to 21 h**. The 10th percentile is 71 and the 90th is 101. Heart rate and glucose are almost uncorrelated at the 5-minute level in his real days (r = 0.04), so the demo's heart-rate links come from planted effects (exercise, stress, illness), not from this data.

## 7. What this means for the 91-day story

His real end state is hyperglycaemic (mean 10.3, 53% in range, fasting about 8.5). The earlier plan assumed the last days had mean 9.6 and 64% in range, which is the Libre sensor. With the Dexcom the targets move:

| Phase | Days | Mean glucose | Time in range | Fasting (05:00 to 07:00) |
|---|---|---|---|---|
| A. Settling in (baseline) | 1 to 14 | ~8.8 | ~62% | ~7.6 |
| B. Evening walks | 15 to 56 | ~7.9 | ~75% | 7.6 down to 6.7 (-12%) |
| C. Disruption | 57 to 70 | ~9.3 | ~58% | ~7.8 |
| D. Drift (the last ~10 days are his real data) | 71 to 91 | ~10.3 at the end | ~53% | up to ~8.5 |

Resting heart rate (small hours) stays near 70 bpm early on and drifts up; his daytime and evening heart rate is high already (88 to 100), so "usual range" by hour matters more than one number. Targets are starting values to tune.

## 8. Gaps and what I need from you

1. **Race and fasting insulin** are in CGMacros `bio.csv`, which is a small file on PhysioNet's S3 mirror (the project's cited source), but nothing under `data/raw/` is on this machine and I have not downloaded it. Until then, race is left empty and fasting insulin is simulated, labelled `demo_dataset`.
2. **Lipids** are real but are not kept in v2 (only HbA1c, fasting glucose and fasting insulin). They stay in the backup.
3. **Libre Pro** readings are real but not used in v2; Dexcom is the single glucose stream.
