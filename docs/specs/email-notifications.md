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
| Kinds | `nudge` (meal, workout, lunch ideas, salt prompt), `checkin`, `refill`, `appointment`, `urgent`. Dose reminders are not emailed (they have the calendar events and the Home card). Everything else is `skipped`. |
| Not late | A reminder with an expiry (`payload.until`) is not sent after it. One without an expiry is not sent after 6 hours (an urgent alert after 2). One already done in the app (`acted_at`) is not sent. |
| Limits | At most `EMAIL_DAILY_CAP` (3) emails per person per day, and none in quiet hours (22:00 to 07:00 Singapore time); a quiet-hours row waits and is sent after 07:00 only if it has not expired. |
| Urgent | An `urgent` row with `delivery_to = 'contact'` goes to the EMERGENCY CONTACT's address (`emergency_contact_email`), ignoring the daily limit and quiet hours. It never carries an unsubscribe link. |
| Never twice | Each row ends as `sent`, `failed` or `skipped` and is never picked up again. A failed send is retried on the next minute up to 3 times (a refusal by the recipe is final at once). |

Existing notifications at the time of migration 0031 were all marked `skipped`, so no old reminder is ever emailed.

## The webhook (what Joely builds in Workato)

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

Recipe steps: (1) webhook trigger; (2) Gmail "Send email": To = `to`, Subject = `subject`, Body (HTML) = `html`, plain-text alternative = `text` if the connector has one;
(3) respond to the webhook with HTTP 200 and `{"status": "ok"}`. Any other answer is treated as a failure: 4xx is final, 429 and 5xx are retried.
`idempotencyKey` is the notification id: if the recipe can, drop a repeat of the same key (a retry after a timeout could otherwise send twice).
`audience` is `person` for a reminder and `contact` for an urgent alert to an emergency contact.

## Settings (`.env`)

`WORKATO_EMAIL_WEBHOOK_URL`, `WORKATO_EMAIL_WEBHOOK_TOKEN`, `WORKATO_EMAIL_TOKEN_HEADER` (default `API-TOKEN`), `APP_BASE_URL` (where the email's button opens),
`API_PUBLIC_URL` and `NOTIFY_SECRET` (both needed for the unsubscribe link; without them emails carry no link and say where to turn them off), `EMAIL_DAILY_CAP`.
With the webhook blank nothing is sent and nothing is lost: rows stay `pending` until they expire.

## Endpoints

`GET/PUT /api/v1/notify/email` (address and on/off), `POST /api/v1/notify/test` (send one test email to the saved address), and the public
`GET /api/v1/notify/unsubscribe?t=<signed token>`.

## Not built

Dose-reminder emails; an email digest; a bounce or "opened" signal back from Workato; per-kind email preferences; translations of the email text.
