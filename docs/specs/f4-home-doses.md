# F4 on the Home page: due now, next dose, and "why was it not confirmed?"

**Status (2026-10-08): built, pending Joely's testing.** This is the first part of F4 (the adherence engine): what to take now, the next dose, the missed-dose question and its sheet H7. Reminders and notifications, refill reminders and the adherence timeline are not part of this build.

## 1. What the person sees (Home, screen B1)

A card at the top of Home, above the logging card:

| Situation | What it shows |
|---|---|
| A dose is due now (from 2 hours before its time to 2 hours after) | "Due now", the dose named by what to take ("Metformin, 1 Tab"), its time and "with food" when it applies, and a **Taken** button |
| Nothing is due | "Your medicines" and "Next: CRESTOR, 1 Tab, tomorrow at 8:00 am." (or "today at 8:00 pm") |
| Today's doses were taken and nothing is due | The same, with an "All done for now" pill |
| A dose was never answered and its window closed | A grey box inside the card: "Yesterday's evening dose is not confirmed." with the dose below it and **Tell us why**. Not shown when nothing is unconfirmed |
| No medicines with set times | "Add your medicines" (opens the Meds page). Only-when-needed medicines never appear here: they have no dose time |

**The dose name (Joely, 2026-10-08).** The title says what to take, not how strong it is: "Metformin, 1 Tab", "CRESTOR, 1 Tab", "Fish oil, 2 Capsules", "Cough syrup, 5 ml". The strength is taken out of the name ("Metformin 500 mg" becomes "Metformin"). The unit is not stored in the database, so it is read from the label's own words ("Take 1 tab/s") and otherwise chosen by type: tablets for prescription and over-the-counter, capsules for supplements, "Dose" for herbal products.

## 2. "Tell us why" (sheet H7)

Opens as a sheet over Home, as in the mock-up: "Why was it not confirmed?", the dose named, eight one-tap answers, an optional note, **Save** and **Skip for now**.

| Answer | What is saved |
|---|---|
| I took it, forgot to log (added to the mock-up's seven, from the PRD) | The dose becomes `taken`, with its taken time set to its scheduled time (the real time is unknown) |
| I forgot, Side effects, I ran out, I felt fine, Cost, Away from home, Something else | The dose becomes `missed` with that reason (`miss_reason`) |
| Side effects | Also adds a doctor question ("I missed a dose of X because of side effects. Can we talk about them?", origin `agent_suggested`), and offers "Add a symptom" |
| The note | `medication_log.miss_note` (migration 0027), for the doctor brief. Never copied to event_log or logs |

Answering twice is refused ("already answered"), and a dose that can still be taken cannot be given a reason.

## 3. The rules (code: `app/services/dose_store.py`)

- **Rows.** One `medication_log` row per scheduled dose, made for today and tomorrow when the app asks (idempotent, unique on schedule and time).
- **No made-up misses.** A row is not made for a time whose window had already closed when it was first looked at, or from before the medicine existed. So a dose is only ever "not confirmed" if the person had a chance to answer. A person who opens the app only after the whole day has passed will not be asked about that day.
- **Window.** 2 hours either side (a constant, `WINDOW`; "configurable per medicine" in the PRD is not built). Taken is refused before the window opens.
- **Late.** A dose taken more than 60 minutes after its time is recorded as late in the event log (`dose.taken`, `late: true`); the status stays `taken`.
- **Lookback.** An unanswered dose older than 2 days is no longer asked about. At most the 3 most recent are shown.
- **Pending rows** do not count against the person: the adherence percentage and the timeline only count answered doses (taken, missed, skipped).
- **Event log** entries `dose.taken` and `dose.reason.saved` hold ids, the reason code and flags only, never names or notes.

## 4. API and screens

| What | Where |
|---|---|
| `GET /doses/today` | `app/api/routers/doses.py`: due, unconfirmed (up to 3), next dose, doses taken today, whether there are medicines with set times |
| `POST /doses/{id}/taken` | marks taken now (idempotent) |
| `POST /doses/{id}/reason` | `{reason, note}` as above |
| Home card | `apps/web/src/features/home/DoseCard.tsx`, refreshed every minute |
| Sheet H7 | `apps/web/src/features/sheets/MissSheet.tsx`, registered in `app/sheetRegistry.tsx` |
| Tests | `tests/unit/test_dose_text.py` (18), `tests/db/test_dose_store.py` (16) |

## 5. Tried on 2026-10-08

Real browser, phone size, Demo account (one medicine, CRESTOR at 8:00 am): the card says "Next: CRESTOR, 1 Tab, tomorrow at 8:00 am." With three planted test doses (one open now, one from this morning, one from yesterday): "Due now" with Taken, then two "not confirmed" notes; "Side effects" with a note saved the dose as missed, kept the note and added the doctor question; "I took it, forgot to log" and Taken both worked and the card ended on "All done for now". The test rows and question were removed afterwards (the append-only event log keeps its entries). Mr Tan's own history (554 doses) was not touched; the app made pending rows for today and tomorrow when his Home was opened, and they were removed again after testing.

## 6. Not built, and open

- Reminders at the dose time and one hour later (notifications), and refill reminders 7 days ahead.
- The adherence timeline and reason breakdown in the doctor brief (the brief should read `medication_log` and `miss_note`).
- A per-medicine window length.
- Nothing yet turns a long-unanswered dose into `missed` by itself: it stays "not confirmed" for 2 days, then is simply not asked about.
- Mr Tan: his record ends on 1 October, so the app has no history for 2 to 7 October and does not invent any.
