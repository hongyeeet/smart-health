# Workout tracker

A live strength-session tracker: how long the person trains, what they do, every set with reps and weight, and a rest timer. When the session is saved, the server works out how hard it was from the watch heart rate and the person's own resting-heart-rate baseline, and the doctor brief and Insights can use the result. Read it with [prd.md](prd.md) (F6 workouts, F18 timeline), [schema.md](schema.md) section 14 and [memory.md](memory.md) (evidence statuses).

**Status (2026-10-03): scaffold.** The screen, the on-device session store, the effort calculation with tests, and the data contract exist. Nothing is saved to the database yet, because the tables for sets do not exist (schema.md section 14, approved by the owner on 2026-10-03) and the Gold tables are not built (task E1-3). Decision D-055.

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
| Whether the heart-rate data is good enough | **Code** | Under 70% of the expected 1-minute samples gives "insufficient" and no intensity. Unknown stays unknown |
| People on beta-blockers | **Code** | Heart rate is not a reliable effort signal there, so no intensity label is shown |
| One plain-language sentence about the session | **The model (Claude Sonnet 5.5)**, from the finished numbers only | Validated like the brief narrative: every number in the sentence must come from the computed summary. Optional; the screen works without it |
| Glucose change after the session | **Code**, from `event_windows` (Gold) | Worded "associated with", never "caused by". Needs at least 5 comparable sessions before it is shown as a pattern |

## 3. How it uses the Gold tables

Gold tables are derived values built from Silver (data-flow.md). They are not built yet (E1-3). Until then the effort is computed from Silver only (`health_samples` heart rate, and the profile's birth year for the age).

| Need | Source now | Source once Gold exists |
|---|---|---|
| Heart rate during the session | `health_samples` (heart_rate, 1-minute) | same |
| The person's own resting heart rate, to judge effort against | Not used yet (age-based maximum only) | `daily_aggregates.resting_hr` and `baselines` |
| Glucose change after a session | Not available | `event_windows` (anchor kind `workout`) |
| Pattern across many sessions ("on days you lift, evening readings are lower") | Not available | `pattern_candidates`, after 5 or more matched pairs, worded "associated with" and marked unverified |
| Session summary in the doctor brief | Not available | `briefs.data` (E13-1) |

## 4. Safety and honesty

- Heart rate gives an estimate of effort. It is not a medical measurement, and the screen says so.
- No advice about how much or how hard to train. The app records and describes.
- Not a diagnosis. Unwell after a session offers the symptom form; it never names a cause.
- The effort cut-offs (percent of maximum heart rate for each band) are placeholders and are not cited. They need a clinician (G1) before they are shown to real users.
- A heart rate that is missing is shown as missing, never as zero.

## 5. What exists and what is still to build

| Part | State |
|---|---|
| Screen `/log/workout/live` (registry id F2) in `apps/web`: timer, exercises, sets, rest timer, finish, summary | Built as a scaffold |
| On-device session store (`useWorkoutSession`) with a pending-upload list | Built |
| Data contract: `WorkoutSession`, `WorkoutSummary`, `saveWorkoutSession`, `getWorkoutSummary` | In the types and the `Api` interface; the HTTP client throws `NotWired` |
| Effort and volume calculation with 9 tests | Built, no database |
| Tables `workout_sets` and the new `workouts` columns | Specified and approved (schema.md section 14). Created by a migration after E1-3 |
| Save endpoint that reads heart rate, calls the calculation and stores the summary | Not built (needs E0-2, the API skeleton) |
| Gold inputs (resting heart rate, glucose after sessions) | Waits for E1-3 and E9-1 |
| Model sentence | Waits for E0-3, the gateway |
| Link from the Log hub (E1) and the cardio workout form (F1) | Not built; open `/log/workout/live` directly |

Backlog task: E7-5.
