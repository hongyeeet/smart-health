# F4 calendar reminders through Workato: how it works and what is open

**Status (2026-10-09): our side (backend) built; the Workato recipe is created in the sandbox but not final; the loading page is not built yet.** Decided by Joely.

> **Found on 2026-10-09 while building the recipe (not yet reflected in the code below):** a plain Workato webhook can only answer `{"status":"ok"}`; it cannot return the calendar event id (that needs Workato's API Platform, which the sandbox API role cannot reach). The backend client in `app/integrations/workato.py` still expects `{"status":"ok","event_id":...}` in the reply, so against the real webhook it would report every event as failed. Workato's regular "Create event" step also ignores a repeat rule and always uses the calendar's default reminder. Two ways forward were put to Joely: (A) one event per day for the next 14 days, topped up daily, using the step that already works; or (B) one repeating event through Workato's "Custom action" step, which needs one step built by hand in Workato first. The code will change to match the choice (for A: no event id needed in the reply, the client treats a 200 as accepted and confirms through Workato's job status). Test recipe: id 383748 in the project `smart-health` (script `scripts/workato_recipe.ps1`); three marked "[TEST]" events were made on the shared demo calendar and are to be deleted.

## 1. What it should do

After a person confirms a medicine (scanned or typed), the app shows a loading page while the backend adds that medicine's dose times to Google Calendar through a Workato recipe. Each dose time becomes one **repeating** calendar event with a reminder at the dose time, so the phone's calendar app gives the notification. Only-when-needed medicines have no dose times, so they get no events.

Joely's choices (2026-10-08): Workato sandbox workspace (`app.trial.workato.com`); one shared demo Google account connected once in Workato (so every app user's reminders land on that one calendar: a demo set-up, not one calendar per patient).

## 2. How it runs

```
medicine saved (POST /medications, or POST /scans/{id}/confirm)
  -> the medicine is in the database first; nothing below can undo or hide it
  -> calendar_syncs row made (queued)        loading page polls GET /medications/{id}/calendar
  -> background job, one dose time at a time:
       POST the Workato recipe's webhook  -> recipe makes the Google Calendar event -> answers with the event id
       progress saved after every event (events_done of events_total)
  -> done, or failed (retryable: POST /medications/{id}/calendar/retry makes only the missing events)
```

One repeating event per dose time (not one per day), so a medicine takes a few seconds. A retry never makes an event twice (the event ids are kept on the row).

## 3. The message between our backend and the Workato recipe (the contract)

The recipe starts from a **webhook** (Workato "New event via webhook" trigger, authentication by auth token). Our backend sends the token in the header named by `WORKATO_TOKEN_HEADER` (default `API-TOKEN`). One request per dose time:

```json
{
  "request_id": "<medication id>:<schedule id>",
  "source": "smart-health",
  "schedule_id": "<uuid>",
  "time": "08:00",
  "title": "Take CRESTOR, 1 Tab",
  "description": "CRESTOR, 1 Tab. From your Smart Health medicine list.",
  "start": "2026-10-09T08:00:00+08:00",
  "end": "2026-10-09T08:15:00+08:00",
  "timezone": "Asia/Singapore",
  "recurrence": "RRULE:FREQ=DAILY",
  "reminder_minutes": 0
}
```

`recurrence` has `;UNTIL=YYYYMMDDTHHMMSSZ` added when the medicine has an end date (a short course). `start` is the next time the dose is due (a start date in the future is respected). The title is what to take, never a strength the label did not give. No patient name, ID, note or label text is sent.

(As noted at the top, the real webhook cannot do this: it answers `{"status":"ok"}` only.) The recipe was meant to answer **HTTP 200 with JSON** `{"status": "ok", "event_id": "<Google event id>", "link": "<https link to the event>"}`. Anything else (a non-200, `status` not `ok`, a missing event id) counts as a failure and is shown as "could not add all your reminders". Timeout 30 seconds per call; timeouts, connection errors, 429 and 5xx are retried twice with backoff; other 4xx are not retried.

## 4. Where things are

| What | Where |
|---|---|
| Settings (blank means skipped) | `WORKATO_WEBHOOK_URL`, `WORKATO_WEBHOOK_TOKEN`, `WORKATO_TOKEN_HEADER` in `.env` (see `.env.example`); read in `app/core/settings.py` |
| The call to Workato | `app/integrations/workato.py` (`WorkatoClient`) |
| Planning, queue, run, progress | `app/services/calendar_sync.py` |
| Table | `calendar_syncs` (App layer, Alembic 0029): one row per medicine, status queued, running, done, failed or skipped, the events made, progress, last error code |
| Routes | `app/api/routers/calendar.py`: `GET /medications/{id}/calendar`, `POST /medications/{id}/calendar/retry`; both save endpoints call `schedule_sync` |
| Tests | `tests/unit/test_workato_client.py` (11), `tests/db/test_calendar_sync.py` (18) |

## 5. Safety and privacy

- The medicine is saved before anything calendar-related starts; a calendar failure never stops, delays or hides a medicine.
- If Workato is not set up the sync is `skipped` with the reason `not_configured`, and the app carries on.
- Only the medicine's name and amount go to Workato and Google. The address, the token and the payload are never logged; errors carry codes only; the event log holds counts and codes (`calendar.sync.finished`).
- **Open:** the architecture (TB-4) said calendar events need explicit confirmation per event and a scoped sign-in. This build adds events right after the person confirms the medicine, to one shared demo calendar. A real version needs each person's own Google sign-in and a clear consent (and an "off" switch).

## 6. Not built yet, and open

- The Workato recipe (waiting for a Google Calendar connection inside the smart-health project) and the real webhook address and token.
- The loading page in the app (after "Confirm" on the scan plan and after typing a medicine in).
- Removing the calendar events when a medicine is deleted or its times change (the event ids are kept for this; there is no delete screen yet).
- One calendar per person instead of the shared demo calendar.
- AIRO MCP is not enabled on the sandbox workspace ("AiroMCP is not available for this workspace"), so the recipe is created through Workato's regular developer API with an API client token.
