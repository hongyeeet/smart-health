# Insights tab (screens C1 to C6, C7 and C8)

What the person sees, where each number comes from, and what is not built yet. Built 2026-10-10.

## Rule

Every number is computed by the server from stored data (`app/services/insights.py`). No model is called. The screens only lay the numbers out.
A comparison is "associated with", never "caused by", and carries the "Unverified" tag. A finding is shown only when the nightly job
(`pattern_candidates`) had at least 5 matching events. A food is ranked only after it has been seen twice.

## Period

7, 30 or 90 days, one switch shared by all tabs. The period ends on the latest day that has any data (today if there is none), the same rule
as the doctor report, so a loaded patient whose data stops earlier still sees a full period. "What changed" compares the period with the
same number of days before it.

## Endpoints (read-only, `X-User` header like every other route)

| Route | Screen | Reads |
|---|---|---|
| `GET /insights/overview?days=` | C1 week grid (always the last 7 days), what changed, findings | `daily_summary`, `cgm_readings`, `pattern_candidates` |
| `GET /insights/glucose?days=` | C2 time in range, GMI, CV, fasting line with the usual band, drift card, event counts | `cgm_readings`, `daily_summary`, `glucose_events`, `user_profile` targets |
| `GET /insights/food?days=` | C3 totals, recent meals with salt and sugar flags, food responses | `food_logs`, `meal_response`, `daily_summary` |
| `GET /insights/activity?days=` | C4 goal rings, 4 weeks by intensity, mix, workouts, steps | `exercise_logs`, `exercise_response`, `daily_summary` |
| `GET /insights/sleep?days=` | C5 sleep, mood and stress | `daily_summary` |
| `GET /insights/medication?days=` | C6 dose grid (last 30 days shown), adherence, reasons | `medications`, `medication_log`, `cgm_readings` |
| `GET /insights/sprint` | C8 latest 14 days of sensor data | `cgm_readings`, `meal_response` |
| (screen only) | C7 "Why am I seeing this?" sheet, opened from every chart | static text per topic |

## Definitions

- **Fasting glucose**: the average of readings between 05:00 and 07:00 local. The same definition the nightly job uses.
- **Usual range**: the 25th to 75th percentile of fasting glucose in the 60 days before the period (needs 7 days of it). The drift card appears when the weekly median has been above the 75th percentile for 2 or more weeks in a row.
- **Time in range**: the person's own targets from `user_profile`, else 3.9 to 10.0 mmol/L.
- **GMI**: 3.31 + 0.02392 x mean glucose in mg/dL. An estimate, not a lab A1c.
- **Late dose**: taken more than 60 minutes after its time. **Unconfirmed**: the window passed and nobody answered; it counts as not taken.
- **Adherence**: prescription medicines only, taken out of taken + missed + unconfirmed.
- **Active minutes**: intensity 3 or more. Light is 1 to 2, moderate 3, vigorous 4 or 5. Goals 150 minutes and 2 strength sessions a week.
- **Food ranking**: median rise (2 hours after the meal, from `meal_response`) per food name, gentlest first, only foods seen at least twice. `spike_flag` is not used: it is set for nearly every meal.

## Not built

- **D1 / D2 Day view** and tapping a day in the week grid. The grid squares are not links yet.
- **A timed sensor sprint** (start, status, end). C8 summarises the latest 14 days and says so. It needs the sensor connection (K4).
- **Bedtime regularity** and a sleep baseline band. There is no bedtime in the data model yet.
- **Heart rate and SpO2** beside glucose (E13-4). SpO2 has no real source.
- **Languages**: English only.
