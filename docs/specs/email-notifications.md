# Reminder emails (Workato)

Decided by Hong Yi on 2026-10-10. The app already writes every reminder to the `notifications` table for the in-app list. This adds a second way
to reach the person: a gentle email, in the spirit of a habit app's reminder, sent through a Workato recipe. Our API pushes each email to the
recipe's webhook. Workato never reads our database and never holds database credentials.

## Flow

```
agent / app logic  ->  notifications row (delivery_status = 'pending')
scheduler, every minute  ->  dispatcher (app/services/notify_email.py)
   decides per row: send / skip / wait   ->  POST to the Workato email webhook  ->  recipe sends it from Gmail
dispatcher records: delivery_status = sent | failed | skipped, delivered_at, delivery_attempts, delivery_error
```

## Who gets an email

| Rule | Detail |
|---|---|
| Address | The person gave one at onboarding (`user_profile.notification_email`) and has not turned emails off (`email_opt_in`). They can change both in Me, Privacy. |
| Before a profile exists | The address lives on the profile row, which the first onboarding save creates. `PUT /notify/email` answers **409** until then, and nothing is stored. The onboarding screens keep the email and save it with page 3, with Finish, or in the chat with its first save (fix wave, 2026-10-11). |
| Lunch | The lunch reminder and the lunch ideas share one slot a day, so the person gets at most one lunch nudge email (see learning-loop 12.3). |
| Kinds | `nudge` (meal, workout, lunch ideas, salt prompt), `checkin`, `refill`, `appointment`, `urgent`. Dose reminders are not emailed (they have the calendar events and the Home card). Everything else is `skipped`. |
| Not late | A reminder with an expiry (`payload.until`) is not sent after it. One without an expiry is not sent after 6 hours (an urgent alert after 2). One already done in the app (`acted_at`) is not sent. |
| Limits | At most `EMAIL_DAILY_CAP` (3) emails per person per day, and none in quiet hours (22:00 to 07:00 Singapore time); a quiet-hours row waits and is sent after 07:00 only if it has not expired. |
| Urgent | An `urgent` row with `delivery_to = 'contact'` goes to the EMERGENCY CONTACT's address (`emergency_contact_email`), ignoring the daily limit and quiet hours. It never carries an unsubscribe link. |
| Never twice | Each row ends as `sent`, `failed` or `skipped` and is never picked up again. A failed send is retried on the next minute up to 3 times (a refusal by the recipe is final at once). |

Existing notifications at the time of migration 0031 were all marked `skipped`, so no old reminder is ever emailed.

## The webhook (the message the recipe receives)

A new recipe, separate from the calendar one. Trigger: webhook, "auth token" mode, header `API-TOKEN` (the same convention as the calendar recipe).
Our API sets `WORKATO_EMAIL_WEBHOOK_URL` and `WORKATO_EMAIL_WEBHOOK_TOKEN`.

Request body (JSON):

```json
{
  "to": "tan@gmail.com",
  "toName": "Mr Tan",
  "subject": "Log your lunch? One photo is all it takes",
  "preheader": "Take a photo and tell us when you finish eating.",
  "text": "plain text version",
  "html": "<!doctype html>... full email, inline styles, one button",
  "tags": { "kind": "nudge", "key": "meal-2-2026-10-10", "audience": "person" },
  "idempotencyKey": "<notification id>"
}
```

`idempotencyKey` is the notification id: if the recipe can, drop a repeat of the same key (a retry after a timeout could otherwise send twice).
`audience` is `person` for a reminder and `contact` for an urgent alert to an emergency contact.

## Build the recipe in Workato (step by step)

In the same Workato project as the calendar recipe (`smart-health`, sandbox `app.trial.workato.com`). Two steps only; **no "respond to webhook" step is needed**,
because a plain webhook trigger answers `200 {"status":"ok"}` by itself (the same finding as the calendar recipe, see f4-calendar.md).

1. **Create a recipe** named "Reminder emails". **Trigger:** Webhooks, "New event via webhook". Under Authentication choose **Auth token** and set a long random token. Keep the header name `API-TOKEN`.
   Paste this sample into "Event structure" (or use "Generate schema from JSON") so the fields appear as data pills:
   `{"to":"a@b.com","toName":"Mr Tan","subject":"s","preheader":"p","text":"t","html":"<p>h</p>","tags":{"kind":"nudge","key":"meal-2-2026-10-10","audience":"person"},"idempotencyKey":"id"}`
2. **Action:** Gmail, "Send email" (connect the shared demo Gmail account once). Map **To** = `to`, **Subject** = `subject`, **Body** = `html` and set the body type to **HTML**.
   Map the plain-text alternative to `text` if the connector shows that field. Leave CC and BCC empty.
3. **Start the recipe** and copy the webhook address from the trigger.

Optional but wise: add a first step "Lookup / dedupe" on `idempotencyKey` if you want repeats dropped. The app already never sends the same notification twice in the normal case; a retry after a timeout is the only repeat.

## Switch it on (checklist)

1. Put `WORKATO_EMAIL_WEBHOOK_URL` and `WORKATO_EMAIL_WEBHOOK_TOKEN` in `.env` (see Settings). For the unsubscribe link also set `API_PUBLIC_URL` and `NOTIFY_SECRET`; set `APP_BASE_URL` to where the email's button should open.
2. `python scripts/email_recipe_check.py --fake` proves our side with no network. It must say "Our side is fine."
3. `python scripts/email_recipe_check.py --to you@example.com` sends ONE real test email (subject starts with "[Test]"). If nothing arrives, open the recipe's job history in Workato.
4. Restart the API. The dispatcher runs every minute from the scheduler and sends nothing until both settings are present.
5. In the app, Me, Privacy, "send a test email" (`POST /api/v1/notify/test`) checks the saved address end to end.

**What happens to reminders already waiting.** The first run after the webhook is set works through the `pending` rows. A row with no expiry that is more than 6 hours old (2 for urgent) is skipped as "too old"; an
expired one is skipped; the rest go to people who have an address and have not turned emails off, within the daily limit and outside quiet hours. So the first minute can send a few real reminders to the addresses on file.
Check who has an address first (`user_profile.notification_email`), or switch the recipe on only after the test above passed.

## Settings (`.env`)

`WORKATO_EMAIL_WEBHOOK_URL`, `WORKATO_EMAIL_WEBHOOK_TOKEN`, `WORKATO_EMAIL_TOKEN_HEADER` (default `API-TOKEN`), `APP_BASE_URL` (where the email's button opens),
`API_PUBLIC_URL` and `NOTIFY_SECRET` (both needed for the unsubscribe link; without them emails carry no link and say where to turn them off), `EMAIL_DAILY_CAP`.
With the webhook blank nothing is sent and nothing is lost: rows stay `pending` until they expire.

## Endpoints

`GET/PUT /api/v1/notify/email` (address and on/off; PUT answers 409 when the person has no profile yet), `POST /api/v1/notify/test` (send one test email to the saved address), and the public
`GET /api/v1/notify/unsubscribe?t=<signed token>`.

## Not built

Dose-reminder emails; an email digest; a bounce or "opened" signal back from Workato; per-kind email preferences; translations of the email text.
