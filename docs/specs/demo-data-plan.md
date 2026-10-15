# Demo data plan: Mr Tan, 91 days

Status: **built and loaded into the shared Supabase project on 2026-10-05** (section 12 has what was built and how it differs from the plan); the data model (`data-model-v2.md`) still waits for team approval. Written 2026-10-05 with Hong Yi.

## 1. Goal and key idea

One demo patient with at least 3 months of data (91 days, about 26,000 five-minute rows per sensor stream) that lets stakeholders **see how everything we track moves together**: what a meal does to glucose, what exercise does to heart rate and glucose, how mood, stress, sleep, missed doses and symptoms line up with the physiology. Every item on the chart overlay must have a visible, believable relationship with at least one measured signal, and the analysis must be able to find those relationships again from the data.

Because of that, the data is built as a **layered cause-and-effect simulation**, not as independent random streams (section 5).

## 2. Persona

**Mr Tan**, 51, Singapore, type 2 diabetes. This is CGMacros participant 046, already in the database (id `dc48e209-5731-5b3d-89d9-986242c54368`) with about 10 real days.

- Works Monday to Friday, 08:30 to 17:30, a standing job (invented). Emergency contact: spouse, with a made-up number (invented).
- Medicines: metformin 500 mg at 08:00 and 20:00 with food, amlodipine 5 mg at 08:00, atorvastatin 20 mg at 22:00, plus a fish-oil supplement and a herbal tonic with no drug match.
- Wears a CGM that reports every 5 minutes, and a watch.
- Eats local food (kopi, teh, chicken rice, nasi lemak, char kway teow, yong tau foo, brown rice options).

## 3. What is real, borrowed and simulated

| Data | Source | Label |
|---|---|---|
| Glucose, heart rate, 29 meals with macros, HbA1c, fasting glucose and insulin, age, gender | Mr Tan's own CGMacros data (last ~10 days of the window) | real |
| HRV | derived from a BIG IDEAs participant's beat intervals (allowed: a different person is fine if labelled) | borrowed, `demo_dataset` |
| The other ~80 days of glucose, heart rate, meals | built from Mr Tan's own real days and meal responses, adjusted by story phase | simulated, `demo_dataset` |
| SpO2, blood pressure, steps, sleep, medication log, symptoms, mood, exercise, work schedule, appointments, questions | invented for the persona | simulated, `demo_dataset` |
| Macros of local dishes without a measured value | team-written table of about 25 dishes, shown as estimates | simulated |

The window ends on the demo end date (a parameter, today 2026-10-02) and all simulated rows carry `source = 'demo_dataset'`. A disclosure file lists real versus simulated per column. Exactly which real files exist for Mr Tan (device overlap, heart-rate resolution) is confirmed in step 1 of section 7.

## 4. The 13-week story

All numbers are starting values to tune, not clinical facts.

| Phase | Days | What happens | Targets |
|---|---|---|---|
| A. Settling in | 1-14 | Steady routine; this period builds the baseline | glucose mean ~8.4 mmol/L, time in range ~70%, fasting ~7.2, adherence ~92%, resting HR ~70, HRV ~38 ms, BP ~135/84, steps ~8,000, sleep ~6 h 50 |
| B. Evening walks | 15-56 | Walks after dinner from about day 22, 4 to 5 evenings a week | fasting 7.3 to 6.4 (-12%), time in range ~80%, steps ~9,000, resting HR -2, one low after a long walk with a skipped dinner |
| C. Disruption | 57-70 | Busy period: eating out, sweet kopi and teh, late nights, walks stop | adherence ~75% (evening metformin missed on work days: "forgot", "away from home"), sleep ~5 h 50, stress up |
| D. Drift | 71-91 | A one-week clarithromycin course (days ~72-78), then slow worsening | resting HR +5, HRV -8, BP to ~146/90, glucose mean ~9.6, tingling in the left foot logged 3 times with notes |

On the last day the numbers match the existing mock: 5,840 steps, 5 h 50 min sleep, missed metformin on 27 and 29 Sep, mood 3 and stress 4, eye check overdue, foot check due in 3 weeks, diabetes review in 9 days, flu shot not recorded. The last ~10 days of glucose are real (time in range 64%, mean 9.6), so the simulated days before them must blend into that level.

## 5. Correlation design: what is planted

The generator first draws a hidden state for each day (sleep, stress, illness, whether the dose was taken, whether he walked), then builds each hour from it, then the logs. The links below are planted with realistic size and direction, plus noise so no relationship is perfect. Effect sizes are starting values; the meal link is **fitted on his 29 real meals**.

| Driver | Outcome | Planted link |
|---|---|---|
| **Meal** (carbs net of fibre, sugar, fat and protein, time of day) | **CGM** | glucose rises after the meal start, peaks at 45-60 min, is back near baseline in 2-3 h; the rise grows with carbs and sugar and shrinks with fibre, protein and fat; sugary drinks rise faster; evening meals rise more than morning ones |
| Meal sodium | blood pressure | a small rise in the next readings after high-sodium meals |
| **Exercise** (type, intensity) | **heart rate** | rises during the session in line with intensity, falls back within ~30 minutes |
| Exercise | **CGM** | an aerobic walk after dinner lowers that meal's peak by about a quarter; steady exercise lowers glucose during and for hours after; strength work has a small delayed lowering; hard intervals can raise it briefly |
| Evening walks (repeated) | next-morning fasting glucose | gradually lower, which produces the -12% story |
| Exercise | mood and sleep | mood up after exercise; deeper sleep that night |
| **Sleep** (minutes asleep) | next-day fasting glucose, HRV, mood, energy, steps | less than about 7 h raises fasting glucose, lowers HRV, mood and energy |
| **Stress** (work days, busy period, poor sleep) | glucose, heart rate, HRV, adherence | higher stress raises glucose and heart rate, lowers HRV, and makes missed doses more likely |
| **Mood** | steps, symptoms | low mood on bad-sleep and high-stress days; tracks with fewer steps |
| **Missed dose** | glucose, BP | missed evening metformin raises the post-dinner peak and the next morning's fasting glucose; missed morning amlodipine raises BP |
| **Work schedule** | steps, stress, adherence | work days have more steps and stress and more missed evening doses than weekends |
| **High-glucose days** | symptoms | tingling and fatigue are logged more on days with sustained high glucose; shaky or sweaty after a low |
| Illness (antibiotic week) | heart rate, HRV, glucose, steps, mood | resting heart rate up, HRV down, glucose up, steps and mood down; a deliberate confounder |
| Night | SpO2 | small dips during sleep; no strong link to the other signals |
| Dawn | glucose | a mild rise from 04:00 to 07:00 |

Realism rules: day-to-day variation and a few bad days, weekdays differ from weekends, device noise and a few short sensor gaps, no perfectly repeating days, and logs are not complete (not every meal photographed, the morning wellbeing log is missing on about 30% of days).

## 6. Expected volume

| Table | Rows |
|---|---|
| `watch_readings` | ~26,200 (one per five minutes, 91 days) |
| `cgm_readings` | ~26,200 at 5 minutes |
| `bronze_watch` / `bronze_cgm` | ~360 watch syncs (four a day), ~91 CGM batches |
| `food_logs` | ~300 (29 real, the rest simulated) |
| `medication_log` | ~380 (four daily doses plus the antibiotic course) |
| `exercise_logs` | ~45 (about 25 evening walks, the rest other sessions) |
| `wellbeing_logs` | ~150 (an evening log daily, a morning log most days) |
| `blood_pressure_readings` | ~35 |
| `symptom_logs` | ~15 |
| `timeline_5min` | ~26,200 |
| `baselines` | ~100 rows per baseline |

## 7. Steps

1. **Profile Mr Tan's real files:** which devices overlap, heart-rate resolution, meals, labs, gender. This sets how the real window joins the simulated days.
2. **Write the persona sheet and story config:** phases, targets, weekly routine, the dish table, showcase days.
3. **Build the generator** with a fixed seed. It writes local files first (not the database) so it can be reviewed before the migration exists: a glucose model fitted on the real days, then the other signals and logs driven by the same hidden daily state.
4. **Checks before loading** (section 8).
5. **Load after the migration** into the new Bronze, Silver and Gold tables; simulated Bronze payloads are the generated device batches. Update `verify_loaded.py` and the disclosure file.
6. **Date handling:** because the end date is a parameter and the generator is deterministic, moving the demo to a new date means regenerating. Decide the final date before the demo (Nov 3).

## 8. Checks

- **Shape:** about 26,000 buckets, no gaps beyond the planned ones, nothing in the future, a smooth join where the simulated days meet the real ones.
- **Fit to real days:** on his real days, simulated-style days match on glucose mean, spread, time in range and meal rise.
- **Planted versus recovered:** compute each link from the finished `timeline_5min` and compare with what was planted, for example the slope of meal rise against carbs, post-dinner peak on walk days versus non-walk days, heart-rate curve during exercise, mood after exercise, fasting after a missed dose, and the effect of sleep on next-day fasting and HRV. The pattern and flag logic must also find them on its own (at least 5 events). This is a consistency test of the data and the logic, not clinical validation.
- **Story targets:** fasting -12% from the start of walks to week 8, the decline flag fires only in phase D and not in phase A, baseline-period days are about 10% outside the usual range.
- **Charts:** the four report charts render with all overlays on the showcase days.

## 9. Showcase days for stakeholders

| Day | What it shows |
|---|---|
| ~12 | A normal baseline-period day: meals and the glucose line, work-hours shading |
| ~34 | A walk day: lower post-dinner peak than a non-walk day, heart-rate curve, mood up |
| ~41 | A low after a long walk with a skipped dinner: glucose event, shaky symptom, "check with your doctor" wording |
| ~62 | A disruption day: sweet drink, missed evening metformin, poor sleep and stress, the biggest spike, the barrier reason |
| ~75 | The antibiotic course and the "possible interaction, check with your pharmacist" message |
| ~88 | Foot tingling note, "outside your usual range" flags, the doctor brief with its supporting events, overdue eye check |

## 10. Challenge features covered

| Feature | Shown by |
|---|---|
| Medication understanding | plain-language medicine explanations; the herbal tonic gets "I can't identify that, please check with your pharmacist" |
| Medication management and adherence | `medication_schedule`, missed doses with reasons, `care_summary` (main barrier, most-missed time), refill warning |
| Health tracking | meal and exercise responses, the fasting drop after walks, the four charts with overlays |
| Longitudinal and personalised | fixed baseline and the decline flag in phase D only |
| Preventive health | eye and foot checks, flu shot, HbA1c due, prompted by the tingling |
| Healthcare preparation | logged questions, the appointment, the brief |
| Safe and honest | interaction wording with no advice to change anything; unknown medicine admitted |

## 11. Decisions and open items

| Decision | Status |
|---|---|
| Use Mr Tan | decided, Hong Yi 2026-10-05 |
| CGM at 5 minutes throughout | decided, Hong Yi 2026-10-05 |
| Improve-then-decline story | chosen by the assistant, not objected to (Hong Yi: "whatever works best") |
| No baseline reset in the demo data; the clarithromycin interaction scenario is kept; the end date stays 2026-10-02 as a parameter | defaults, not objected to |
| PRD changed to follow the new baseline values | decided, Hong Yi 2026-10-05 (done, `prd.md` F8 and section 7) |

Open:
1. **Sensor sprints:** the PRD (F7 and other places) still describes 14-day CGM "sprints" and the data model drops `cgm_sprints` because this persona wears a sensor continuously. The PRD needs a decision on whether sprints stay as a product idea.
2. **Real-file profile (step 1)** may change the details in sections 3 and 7.
3. **Risk:** only about 10 days are real, so the simulated 80 days must carry realistic day-to-day variation, or they will look too regular. That is why the checks compare them with his real days.

## 12. As built (2026-10-05)

Generated by `scripts/generate_mr_tan.py` (fixed seed), loaded by `scripts/load_mr_tan_v2.py`, Gold built by `scripts/build_gold_v2.py`. Charts for checking: `scripts/plot_mr_tan.py` (one day) and `scripts/plot_report_charts.py` (the four report charts for a date range); images go to `data/processed/demo_v2/plots/` (git-ignored).

**Window:** 2026-07-04 00:00 to 2026-10-02 07:40 Singapore time (26,013 five-minute buckets). The last 9.9 days of glucose are his real Dexcom G6; heart rate is real in the same days; sleep, steps and exercise there are derived from his real activity. Everything before 2026-09-22 is simulated from his own meal responses and the story.

**Glucose by phase, planned against built** (his real days are the high end, mean 10.3 and 55% in range with the Dexcom, as in `mr-tan-profile.md`):

| Phase | Days | Planned mean / in range | Built mean / in range | Built fasting (05:00 to 07:00) |
|---|---|---|---|---|
| A. Settling in | 1-14 | 8.8 / 62% | 9.3 / 70% | 7.7 |
| B. Evening walks | 15-56 | 7.9 / 75% | 8.1 / 83% | 7.7 down to 6.8 (week 8): **-12%** |
| C. Disruption | 57-70 | 9.3 / 58% | 10.1 / 61% | 8.0 |
| D. Drift, simulated part | 71-80 | ~9.8 | 10.2 / 58% | 8.6 |
| D. Drift, real part | 81-91 | 10.3 | 10.3 / 55% | 8.6 |

Weekly fasting glucose: 7.8, 7.7, 7.7 | 7.2, 7.0, 7.1, 7.0, 6.8 (walks) | 7.8, 8.2, 8.8 (disruption) | 7.8, 9.2 (drift and real days).

**Adherence (prescription medicines):** about 96% in phase B, about 63% in phase C; 374 prescription doses, 49 missed (reasons: forgot, away from home, felt fine, ran out on days 60-61, side effects twice).

**What the analysis found again** (`pattern_candidates`, each seen at least 5 times, wording "associated with", unverified): a missed evening metformin goes with a post-dinner rise 1.9 mmol/L higher (n = 18); an evening walk goes with next-morning fasting 0.7 mmol/L lower (n = 28); meals with 60 g or more of net carbohydrate rise 2.1 mmol/L more than meals under 40 g (n = 107); a night under 6 hours goes with fasting 0.7 mmol/L higher (n = 13); a high-stress day goes with HRV 13 ms lower (n = 22); meals with a sweet drink rise 1.5 mmol/L more (n = 43).

**Decline flag:** first fires for glucose on 2 Sep (phase C), HRV on 11 Sep, heart rate and SpO2 on 15 Sep; it never fires in phases A and B. The rule is worse-side only at 20% (`data-model-v2.md` 5.3); the first version flagged both sides and flagged his improvement.

**Showcase days (dates):** day 12 = Wed 15 Jul; day 34 = Thu 6 Aug (a walk day); day 43 = Sat 15 Aug (the low after a long walk); day 62 = Thu 3 Sep (the worst day); day 75 = Wed 16 Sep (the antibiotic course, interaction alert on 13 Sep); day 88 = Tue 29 Sep (real glucose, missed evening dose, foot tingling).

**Known limits:** race is empty and there is no fasting insulin (needs `bio.csv`, not downloaded); the real days make the end of the story harsher than planned (11 days at 55% in range); sleep in the real window comes from resting activity and can run long (11 hours on 27 Sep); the weekly shape of simulated days is regular (the same few dishes, regular walks) although each day varies; SpO2, blood pressure, HRV before the real window, symptoms, mood and every medication entry are simulated.
