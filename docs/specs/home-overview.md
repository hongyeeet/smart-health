# GET /api/v1/home/overview

One read for the new Home page: today's plan, four KPI cards and a 7-day chart. Header `X-User` as usual. Always 200, every field present, unknown values are `null` (never 0). Code: `app/services/home_overview.py`, shapes in `app/schemas/home.py` (camelCase), route in `app/api/routers/home.py`. The banner route is unchanged.

Read only. Nothing is written for Mr Tan. For other people the only write is today's dose rows (`dose_store.ensure_rows`, the same call the dose banner makes). No model, JEV or embedding call. The response holds no name, phone, email or NRIC (medicine names are the person's own labels).

## Fields

- `asOf`: newest date among the cards that have data; `null` when none.
- `plan`: see below.
- `glucose`: `value` is the daily mean of the latest day with sensor data, `day` that date, `inRangePct` that day's time in range, `spark` the last 7 daily means, `status`. `null` when the person has no glucose data at all.
- `steps`: `avg` is the mean daily steps over the 7 days (days with data), `spark`, `status`. `null` with no steps data.
- `calories`: `avgKcal` is the mean daily energy over days that have a logged meal. A day with a meal whose macros are unknown is left out, so is a day with no meal. `sugar` and `salt` are `{state, highMeals, meals}`. `null` when no meal is logged in the last 67 days.
- `heart`: `bpm` and `spo2` are the heart insight's 7-day averages from the watch, `restingBpm` the average of the daily resting values, `status` for heart rate and `spo2Status` for SpO2. `null` with no watch data.
- `chart`: `days` are 7 ISO dates; `glucose`, `steps`, `calories`, `heartRate` have 7 entries each, `null` for a missing day.

Each card ends on the latest day with its own data (the Insights rule: `insights.anchor`; heart ends on the last watch day). The chart and the food card end on the overall latest day. For a person whose sensors stop at different days, a card and the chart can end on different days; the chart's `days` says which.

## Status (`status`, `spo2Status`)

`{state, usualLow, usualHigh, usualMedian, delta}`. The 7-day value is compared with the person's OWN daily values over the 60 days before the 7-day window (`insights.BASELINE_DAYS`): usual range = 25th to 75th percentile, median for `delta` (value minus median, same unit as the value).

| state | when |
| --- | --- |
| `within` | low <= value <= high |
| `above` | value > high |
| `below` | value < low |
| `unknown` | fewer than 3 days with data in the window, or fewer than 7 days with data in the 60 before |

With fewer than 7 prior days the usual numbers are `null` too. With 7 or more prior days but fewer than 3 window days, the usual numbers are given and `state` is `unknown` with `delta` `null`. Glucose compares the mean of the window's daily means with the usual daily means. Heart and SpO2 compare the window's daily watch averages with the daily watch averages of the 60 days before.

## Salt and sugar

Counted over the meals of the same 7 days. A meal is over the limit at sodium >= `meal_high_sodium_mg` (1000 mg) or sugar >= `meal_high_sugar_g` (25 g), the limits Food insights and `/nutrition/flags` use. `unknown` when no meal in the window has the value (`highMeals` is then `null`, never 0). A meal without the value is not counted as over. `high` when at least 2 meals are over the limit (`HIGH_MEALS_FOR_HIGH`, a placeholder for the owner), otherwise `ok`.

## Plan

Today's date in Singapore. Items that share a clock time share one step; steps are in time order; inside a step the meals come first, then the medicines.

- Meals sit at the start of the mealtime windows the app already uses for meal reminders (`logstore.MEAL_WINDOWS`): Breakfast 07:00 (window 7:00 to 10:30), Lunch 11:30 (to 2:30 pm), Dinner 18:00 (to 9:30 pm). `done` when a meal of that type is logged today; else `later` before the window, `due` while it is open, `missed` after it closes.
- Medicines come from the person's scheduled medicines: not as-needed, not deleted, not ended (`end_date` before today), with a dose time. A medicine created after today's dose time has no step (unless a dose row exists). Title is the person's own label, "Metformin 500 mg".
- Dose window: from the dose time to 60 minutes after it (`dose_timing.WINDOW_MIN`, which is `insights.LATE_AFTER_MIN`). Dose row taken = `done`; answered missed = `missed`; otherwise by the clock: before the dose time `later`, inside the window `due`, after it `missed` (not answered). Note the Taken button itself is accepted from 2 hours before (`dose_store.WINDOW`); the plan simply calls those `later`.
- `doseId` is the dose row that Taken sends: set for a dose that is still waiting (later, due, or past its window), `null` once answered or when no row exists. Mr Tan: rows already in the table are used; a dose with no row has `doseId` `null` because nothing is created for him.
- Step `state`: `done` when all items are done; `now` when any item is `due`; `later` when no item is due and any is `later`; else `missed`.
- `done` and `total` count items. `nowIndex` is the index of the first `now` step, else the first `later` step, else `null`.

## Caching and speed

The cards and chart are cached 20 seconds per person and cleared when `logstore.log_epoch` changes (a meal or workout logged). The plan is read fresh on every request so a dose marked Taken shows at once. One database connection per request (`logstore.one_connection`).

## What is unknown when

- No history before the window: `status.state` `unknown`, usual numbers `null`.
- No meal with sugar or sodium (Mr Tan's logged meals have none today): `sugar` / `salt` `unknown`.
- Calories with a meal missing carbs, protein or fat: that day is `null` in the spark and chart and left out of the mean.
- No watch data: `heart` is `null`. No glucose / steps / meals: that card is `null`.
- A card, chart day or plan item never turns a missing value into 0.
