# Workout tracker

A live strength-session tracker: how long the person trains, what they do, every set with reps and weight, and a rest timer. When the session is saved, the server works out how hard it was from the watch heart rate and the person's own resting-heart-rate baseline, and the doctor brief and Insights can use the result. Read it with [prd.md](prd.md) (F6 exercise, F18 timeline), [data-model-v2.md](data-model-v2.md) (the tables `exercise_logs` and `exercise_sets`) and [memory.md](memory.md) (evidence statuses). Since data model v2 (2026-10-05) the session is saved as a `bronze_exercise` row, then `exercise_logs` with its `exercise_sets`; the older `workouts` and `workout_sets` tables no longer exist.

**Status (2026-10-11): built and connected, not yet verified on the database.** The screen, the on-device session store, the effort calculation, the save endpoint (`POST /workouts`) and the week progress (`GET /workouts/week`) exist. The sets are saved in `exercise_sets` under `exercise_logs` (migration 0018). The **rating is optional** from 2026-10-11 (migration 0036), and the **honest label** and the **beta-blocker and coverage rules** are in section 4. Not built: the model sentence (section 2) and the Gold resting-heart-rate baseline. Originally decided on 2026-10-03 (D-055). **Quick log editing (checked 2026-10-15):** a workout saved from the quick log (F1, `LogWorkout.tsx`) can be read and edited: `GET /logs/workout/{id}` returns it and `PUT /logs/workout/{id}` updates it (title "Workout updated"); the app loads one of the last five workouts into the form. This is separate from the live session, which is saved once with `POST /workouts`.

## 1. What the person does

1. Start workout. A timer runs.
2. Add exercises (a list of common ones, or type a name).
3. For each exercise, log sets: reps and weight (or bodyweight). A 90-second rest timer starts after each set.
4. Finish, say how it felt (energised, fine, tired, unwell), optionally add a note, and save.
5. The summary shows time, sets, weight lifted and, once the server has the watch data, heart-rate effort per exercise and overall.

The live session is held on the device and survives a refresh. A finished session that cannot reach the server stays on the device, listed under "Waiting to upload", and nothing is lost.

## 2. Where "the AI" comes in, and where it does not

The rule is the same as everywhere else in the project: **the model writes language, code produces numbers** (rules.md 1, rule 2).

| Job | Done by | Notes |
|---|---|---|
| Average and peak heart rate, minutes in each band, overall intensity (light, moderate, vigorous) | **Code**: `services/api/app/services/workout_effort.py` | Uses an age-based maximum heart rate and fixed cut-offs. Placeholders pending clinical validation (questions-for-damien.md, G1) |
| Average heart rate per exercise | **Code**, from the time each exercise's sets were logged | Needs set times, which the app records |
| Volume (reps x weight) and set counts | **Code** | Bodyweight sets are counted but add no volume |
| Whether the heart-rate data is good enough | **Code** | Under 70% of the expected samples gives "insufficient" and no intensity. The expected count uses the person's own sampling interval (the median gap between samples, kept between 60 and 600 seconds; 60 seconds with fewer than three samples). Unknown stays unknown |
| People on beta-blockers | **Code** | Heart rate is not a reliable effort signal there, so no intensity label is shown. The rule is wired on `POST /workouts` (fix wave, 2026-10-11) |
| One plain-language sentence about the session | **Not built.** Planned for the model (the gateway exists), from the finished numbers only. Every number in the sentence must come from the computed summary. The workouts code makes no model call, so the screen shows the numbers only |
| Glucose change after the session | **Code**, from `exercise_response` (Gold) | Worded "associated with", never "caused by". Needs at least 5 comparable sessions before it is shown as a pattern |

## 3. How it uses the Gold tables

Gold tables are derived values built from Silver (data-flow.md). They are built today by `scripts/build_gold_v2.py` for Mr Tan's example record. The effort is computed from Silver (`watch_readings` heart rate, and `user_profile.birth_year` for the age) and can use the Gold inputs below.

| Need | Source now | Source once Gold exists |
|---|---|---|
| Heart rate during the session | `watch_readings.heart_rate_bpm` (5-minute buckets) | same |
| The person's own resting heart rate, to judge effort against | Not used yet (age-based maximum only) | `daily_summary.resting_hr_bpm` and the heart-rate rows of `baselines` |
| Glucose change after a session | Not available | `exercise_response` (`glucose_pre_mmol`, `glucose_change_at_end`, `glucose_1h_mmol`, `glucose_2h_mmol`) |
| Pattern across many sessions ("on days you lift, evening readings are lower") | Not available | `pattern_candidates`, after 5 or more matched pairs, worded "associated with" and marked unverified |
| Session summary in the doctor brief | Not available | `briefs.data` (E13-1) |

## 4. Safety and honesty

- Heart rate gives an estimate of effort. It is not a medical measurement, and the screen says so.
- No advice about how much or how hard to train. The app records and describes.
- Not a diagnosis. Unwell after a session offers the symptom form; it never names a cause.
- The effort cut-offs (percent of maximum heart rate for each band) are placeholders and are not cited. They need a clinician (G1) before they are shown to real users.
- A heart rate that is missing is shown as missing, never as zero.
- **Honest label (2026-10-11).** On the Activity tab the light, moderate and vigorous labels of the quick log are described as "as you rated the effort, not from your heart rate". The strength tracker's labels come from heart rate, and are only shown with the rules below.
- **Coverage rule.** Under 70% of the expected samples in the session gives "insufficient": no intensity label and the note "Heart rate was missing for too much of this time to judge effort". The expected count is set by the person's own sampling interval (fix wave, 2026-10-11). Before the fix it assumed one sample a minute, but watch heart rate is stored in 5-minute buckets, so the old count asked for five times too many samples.
- **Estimate label (fix wave).** The summary says "Estimated from your heart rate: {light, moderate or vigorous}" (`WorkoutTracker.tsx`).
- **Unrated workouts.** A workout saved without a rating is kept, is not counted toward active minutes, and the Saved summary says: "No effort rating was given, so this workout is not counted toward your active minutes." (Insights shows it as "not rated".)
- **Beta-blocker rule.** A medicine on the person's list whose generic name is a beta-blocker (placeholder list: atenolol, bisoprolol, metoprolol, propranolol, carvedilol, nebivolol, labetalol, sotalol; matched as whole words) gives no intensity label. The note says heart rate is not a reliable sign of effort for them. Brand names are not on the list yet. The list needs clinical review (questions-for-damien G1).
- **Optional rating (2026-10-11).** "How hard did it feel?" (1 to 5) is optional (requested with the 2026-10-11 work; no decision number yet). A workout without a rating is saved, and a null rating is never counted as moderate or vigorous. Migration 0036 allows the null; until it is applied the app keeps asking for the rating.

## 5. What exists and what is still to build

| Part | State |
|---|---|
| Screen `/log/workout/live` (registry id F2) in `apps/web`: timer, exercises, sets, rest timer, finish, summary | Built as a scaffold |
| On-device session store (`useWorkoutSession`) with a pending-upload list | Built |
| Data contract: `WorkoutSession`, `WorkoutSummary`, `saveWorkoutSession`, `getWorkoutSummary` | In the types and the HTTP client (`POST /workouts`, `GET /workouts/week`) |
| Effort and volume calculation | Built; unit tests (`tests/unit/test_workout_effort.py`, `test_workouts_router.py`). Not run against the database |
| Tables for the sets | `workout_sets` (migration 0015) became `exercise_sets` under `exercise_logs` in migration 0018 (2026-10-05); same columns |
| Save endpoint that reads heart rate, calls the calculation and stores the summary | Built: `POST /workouts` (`services/api/app/api/routers/workouts.py`), stored as `bronze_exercise`, then `exercise_logs` and `exercise_sets` |
| Gold inputs (resting heart rate, glucose after sessions) | Built for Mr Tan's example record (`daily_summary`, `exercise_response`); the nightly job that fills them is not built |
| Model sentence | Not built (section 2) |
| Link from the Log hub (E1) and the quick log (F1) | Built: the Workout tile on the Log hub opens F1, and F1 has "Start a live session" for `/log/workout/live` |

Backlog task: E7-5.
