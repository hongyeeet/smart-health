# Flow — Smart Health user journeys, screens and event logging

How users move through the product, which tools and services each step touches, and **what gets logged at every step**. Screen and route names match [architecture.md](architecture.md) §3; event names are written to `event_log` ([schema.md](schema.md) §9). Feature IDs (F#) refer to [prd.md](prd.md).

**Tables.** The "System" column names the tables of data model v2 ([data-model-v2.md](data-model-v2.md)). Every typed entry or upload first lands in a Bronze row (`bronze_*`, the input as received) and then in its Silver table; Gold is built by code and never written by the app. Which feature reads and writes which table is in [data-flow.md](data-flow.md) section 6.

## 0. Logging contract

- **Every step in this document emits at least one event.** Client events go through `logEvent(name, payload)` → batched `POST /events` (with `client_event_id` for dedupe, and offline-queued). Server events are written in the same DB transaction as the change they describe.
- Payloads carry **ids, enums and counts only**, never free-text health notes or names.
- Naming: `domain.object.action` (past tense), e.g. `dose.event.confirmed`.
- Agent activity is also written to `agent_runs` / `agent_steps` / `guardrail_events`; the event log links to it via `agent_run_id`.

---

## 1. Screen map

```
Launch
 ├─ (auth) Sign in / Sign up
 ├─ Onboarding ─ Choose method ─┬─ Form (steps 1–7)
 │                              └─ Chat (onboarding agent)
 │              → Review summary → Consents → Devices → Reminder times → Done
 └─ Tabs
    ├─ Today      doses due · evening check-in · nudge card · open alerts · next appointment
    ├─ Log        [+] glucose · meal · workout · symptom · mood/sleep ; recent entries
    ├─ Meds       med list (with clash badge) · [Scan] · [Add manually] → Med detail (explainer, TTS, history, refill)
    ├─ Insights   glucose trend · momentum cards · food responses · activity · sleep · adherence
    └─ Me         profile · "What Smart Health has learned" · appointments · doctor questions · briefs · devices · language · consents
 Global: Chat (floating button) · Urgent (full-screen modal, can open over anything) · Notifications
```

Navigation rule: every feature is reachable in ≤ 2 taps from a tab; chat is optional, never required.

---

## 2. Journeys

Each journey lists: **Trigger → Steps (screen · system action · events)**.

### J1 First launch and onboarding (F1)
| # | Screen | System | Events |
|---|---|---|---|
| 1 | Welcome, language picker | set `users.locale` | `app.opened`, `user.locale.set` |
| 2 | Sign up | create user | `user.account.created` |
| 3 | Eligibility (T2D? age ≥ 18? pregnant?) | out-of-scope → info screen, stop | `onboarding.eligibility.checked` {eligible} |
| 4 | Choose **Form** or **Chat** | | `onboarding.method.chosen` {method} |
| 5a | Form steps: about you (birth year, gender, race, height, weight) → diagnosis and HbA1c → conditions and allergies (two free-text notes; family history is no longer a separate step) → work week (days, hours, type) → emergency contact (name, phone and relationship, all required in the form) → meds (manual or scan → J2) → watch and CGM model | each step is saved to `bronze_profile` and upserts `user_profile` (resume-able) | `onboarding.step.completed` {step} |
| 5b | Chat: onboarding agent asks the same fields conversationally; shows a live "captured so far" card | agent tools `upsert_profile`, `add_condition` (appends to `conditions_note`), `add_medication_draft` | `agent.run.started/finished`, `onboarding.field.captured` {field} |
| 6 | Review summary (editable) | | `onboarding.summary.reviewed` |
| 7 | Consents: data processing (required), brief sharing (optional), research (optional) | `consents` rows | `consent.granted` {kind, version} |
| 8 | Devices: connect Health Connect / HealthKit, or import file, or skip; ask which watch and CGM model | permission request; `user_profile.watch_model`, `cgm_model` | `device.permission.requested/granted/denied`, `device.connected` {type} |
| 9 | Reminder preferences, quiet hours | | `settings.reminders.set` |
| 10 | Done → Today | generate 7 days of `pending` `medication_log` rows from `medication_schedule`; preventive status (`patient_preventive_status`) | `onboarding.completed` |

### J2 Scan a prescription / supplement / TCM (F2 → F4, F5)
| # | Screen | System | Events |
|---|---|---|---|
| 1 | Meds → Scan → camera (guide overlay, tips) | | `scan.camera.opened` |
| 2 | Capture → upload | `bronze_medication` (the photo is the `object_key`) and `prescription_scans` status `uploaded` → `extracting` | `scan.image.uploaded` |
| 3 | Loading ("Reading your label…") | extractor agent (vision, JSON schema) | `agent.run.*`, `scan.extraction.completed` {items_n, min_confidence} |
| 4 | **Review**: fields with confidence chips; low-confidence fields highlighted, must be tapped to confirm | | `scan.review.opened` |
| 4b | Unrecognised: "I'm not able to identify this medication, please check with your pharmacist." → manual entry | | `scan.item.unrecognised` |
| 5 | Confirm | one transaction: `medications` + `medication_schedule` (dose time, quantity, before / after meal) + `medication_log` + clash check | `medication.created` {kind, source=scan}, `dose.schedule.generated`, `clash.check.run` {hits_n, not_checked_n} |
| 6 | If clash hit → clash sheet: "Possible interaction between X and Y. Please check with your pharmacist or doctor before continuing." [Add to doctor questions] [OK] | `interaction_alerts` | `clash.alert.shown`, `clash.alert.acknowledged`, `question.created` {origin} |

### J3 Understand a medication (F3, F17)
| # | Screen | System | Events |
|---|---|---|---|
| 1 | Med detail | load cached explainer or generate (RAG) | `med.explainer.viewed` {med_id} |
| 2 | Sections: What it's for · How you take it (from **your** label) · Common side effects · When to call your doctor · Sources | output guard | `agent.run.*`, `guard.output.checked` |
| 3 | Tap Listen (speaker icon) / change language | ElevenLabs TTS, cached audio | `tts.played` {locale} |
| 4 | "Ask about this med" → chat pre-filled | | `chat.opened` {entry=med_detail} |

### J4 Daily dose loop (F4)
| # | Trigger / Screen | System | Events |
|---|---|---|---|
| 1 | T: push "Time for Metformin 500 mg (1 tablet, with food)" | worker | `notification.sent` {kind=dose_reminder} |
| 1b | Meal logged within 30 min before T for a with-food med → early prompt | | `dose.prompt.meal_triggered` |
| 2 | Tap notification or Today card → **Taken** | `medication_log` status `taken`, `taken_at` (and a `bronze_medication` row) | `notification.opened`, `dose.event.confirmed` {on_time} |
| 3 | T+60m no action → re-nudge | | `notification.sent` {kind=dose_renudge} |
| 4 | Window closes with no confirmation → the row stays `pending` and is shown as unconfirmed | worker | `dose.event.unconfirmed` |
| 5 | Next app open → sheet "Did you take your evening Metformin?" one-tap reasons | | `dose.reason.prompted` |
| 6 | "Took it, forgot to log" → `taken` with the time (shown as late if more than 60 minutes after the scheduled time; computed, not stored); otherwise `missed` + `miss_reason` | `medication_log` | `dose.reason.captured` {reason} |
| 7 | Reason = side_effects → "Want to note this for your doctor?" → symptom log + question | | `symptom.logged` {source=user}, `question.created` |
| 8 | Refill forecast ≤ 7 days → reminder | `refill_forecasts` (by `medication_id`), `notifications` | `refill.reminder.sent` |

### J5 Logging (F6)
| Log | Path | System | Events |
|---|---|---|---|
| Glucose | Log → Glucose → value (a finger-prick; the context fasting / pre / post is no longer stored, it is worked out from the time of day and the last meal) | `bronze_cgm` → `cgm_readings` (`source = manual`); thresholds check (sync) → maybe J8 | `glucose.reading.logged` {context, source}, `threshold.checked` {tier} |
| Meal | Log → Meal → photo or text → AI estimates the meal's macros (shown as "Estimated") → edit or confirm → portion → save | `bronze_food` (original and raw LLM answer) → `food_logs`; nutrition flags in code; when 3 hours of CGM exist, `meal_response` is computed | `meal.logged` {items_n, flags}, `meal.analysis.completed` {items_n, min_confidence}, `meal.estimate.confirmed`, `meal.estimate.edited`, `food.flag.shown` {flag} |
| Exercise | Log → Exercise → type, start and end, intensity 1 to 5, how it felt (or auto from wearable); strength sessions add sets | `bronze_exercise` → `exercise_logs` (+ `exercise_sets`) | `workout.logged` {source} |
| Symptom | Log → Symptom → picker + how strong + how long + a note (for numbness: which part of the body) | `bronze_symptom` → `symptom_logs`; red-flag symptom → J8 | `symptom.logged` |
| Mood/sleep | Evening check-in card (30 s: mood, stress, energy) and a morning sleep-quality question, 1 to 5 | `bronze_wellbeing` → `wellbeing_logs` | `checkin.mood.completed` / `checkin.mood.skipped` |
| Blood pressure | Log → Blood pressure → systolic and diastolic (a few times a week) | `bronze_blood_pressure` → `blood_pressure_readings` | `bp.reading.logged` |
| Lab result | Me → Labs → HbA1c (%), fasting glucose or fasting insulin, with date | `bronze_lab` → `lab_results` | `lab.result.logged` |
| Edit/delete | Long-press entry | soft delete (`deleted_at`) / update; Bronze is never changed | `log.entry.edited` / `log.entry.deleted` {table} |

### J6 Wearable sync and continuous CGM (F6, F7)
| # | Step | System | Events |
|---|---|---|---|
| 1 | App foreground / background fetch | read Health Connect / HealthKit since last cursor → `POST /health/import` → one `bronze_watch` row per sync → `watch_readings` (5-minute buckets: heart rate, HRV, SpO2, steps, minutes asleep) | `health.sync.started`, `health.sync.completed` {samples_n, metrics} / `health.sync.failed` {code} |
| 2 | File import (Me → Devices → Import) | parse Xiaomi/Apple export | `health.import.file.completed` {rows_n} |
| 3 | Connect a CGM sensor (Me → Devices → CGM model) | `user_profile.cgm_model`; wear periods simply show as continuous data with natural gaps (there is no sprint table) | `cgm.sensor.connected` |
| 4 | CGM readings stream (real or replay) | `bronze_cgm` → `cgm_readings`; thresholds check per reading | `glucose.reading.logged` {source=cgm} (batched count) |
| 5 | 3 hours after a meal | `meal_response` row (before, peak, rise, area over 2 hours, recovery); the per-food view is `meal_response` grouped by food | `food.response.computed` {n} |
| 6 | Sensor removed, or 14 days of data → summary screen "Your gentlest and spikiest foods" (each food needs at least 2 meals) | | `cgm.sensor.removed`, `food.response.summary.viewed` |
| 7 | Later (no CGM): logging a known high-response food → factual note | | `food.response.note.shown` |

### J7 Momentum flag → targeted check-in (F8, F9)
| # | Step | System | Events |
|---|---|---|---|
| 1 | Nightly: for each of heart rate, HRV, SpO2 and glucose, the share of the day's readings on the worse side of the person's fixed usual range (`baselines`) is stored in `daily_summary`; more than 20% on 3 of the last 5 days puts the metric in `declining_metrics` | `daily_summary` → `clinical_flags` (review) | `decline.checked` {metrics_n}, `flag.created` {kind, metric, severity} |
| 2 | Checkin planner picks ≤ 1 question for tomorrow (respecting caps and learned timing) | `notifications` (kind `checkin`; payload: question key and flag id) | `checkin.symptom.planned` |
| 3 | Today card: "Your morning readings have been a bit higher this week, worth mentioning to your doctor. Quick question: have you been more thirsty than usual?" | | `flag.patient_note.shown`, `checkin.symptom.asked` |
| 4 | Answer / skip | `bronze_symptom` → `symptom_logs`; the `notifications` row gets `acted_at` and `action` | `checkin.symptom.answered` / `.skipped` |
| 5 | Flag + answer land in the next brief (§10 and §9) | | `flag.added_to_brief` |

### J8 Urgent escalation (F10), no LLM in this path
> **On hold (2026-10-03, D-054):** pending clinical review by Damien (`docs/handover/questions-for-damien.md`). The tiers, contact alerts and awareness question in steps 2 to 4 are placeholders. Do not build E1-7, E11-2, E7-4 or E13-4 until it is cleared.

| # | Step | System | Events |
|---|---|---|---|
| 1 | Reading < 4.0 (tier 1) or < 3.0 (tier 2), or repeated high, or a red-flag symptom (chest pain, confusion, fainting, breathlessness at rest, sudden vision loss) or chat keyword | `thresholds.py` / input guard | `threshold.breached` {tier, rule_id} |
| 2a | **Tier 1, low:** plain screen: take the fast-acting sugar in your doctor's low-sugar plan, 15-minute recheck countdown | `event_log`; the low is a `glucose_events` row | `urgent.shown` {tier} |
| 2b | **Tier 2, very low:** full-screen **Urgent**: [Call 995] [Call my clinic]; the emergency contact is alerted by message and email at once, by call after 5 minutes with no reply | `event_log`; `glucose_events` (low) and a `clinical_flags` row | `urgent.shown` {tier}, `urgent.contact.alerted` {channels}, `urgent.contact.called` |
| 3 | At 15 minutes (tier 1): "How do you feel?" better, about the same, worse. Same, worse, or still low moves to tier 2. No answer alerts the contact | | `urgent.checkin.answered` {answer}, `urgent.tier.escalated` |
| 4 | "I'm okay now" (held 5 seconds on tier 2), then one question: did you feel it before your sensor alerted you? | | `urgent.action.taken` {action}, `awareness.answered` {answer} |
| 5 | Added to the brief as a `hypo_event` / `high_repeat` flag, with the awareness answer | | `flag.created` |

### J9 Lifestyle nudges (F11)
| # | Step | System | Events |
|---|---|---|---|
| 1 | Nudge policy picks type and time slot (learned from `notifications` of kind `nudge`: sent, opened, acted, and from `memory_facts` such as "usually walks after dinner") | `notifications` | `nudge.planned` {type, slot, explore} |
| 2 | Lifestyle coach fills a reviewed template with the user's own data (or an approved corpus, cited) → output guard | | `agent.run.*`, `guard.output.checked` |
| 3 | Deliver (push / Today card) e.g. "You walked after dinner 3 times this week, and your evening readings were lower on those days. [Your data]" | | `notification.sent` {kind=nudge} |
| 4 | User acts ("Done", logs walk) or dismisses | update act-rate | `nudge.acted` / `nudge.dismissed` |
| 5 | High-salt meal logged → swap suggestion card (cited) | | `food.swap.shown`, `food.swap.accepted` |

### J10 Preventive care and scheduling (F13)
| # | Step | System | Events |
|---|---|---|---|
| 1 | Me → Appointments: preventive checklist (eye / foot / kidney / HbA1c / flu) with due status | `patient_preventive_status`, `preventive_items`; `care_summary` (overdue, due soon) | `preventive.viewed` |
| 2 | Item overdue or flag suggests review → "Suggested: book a diabetes review" card | `appointments` status `suggested` | `appointment.suggested` {kind, reason} |
| 3 | User taps Plan → date/time/location → **explicit confirm** → Add to Google Calendar (OAuth) or download .ics | | `calendar.oauth.granted`, `appointment.planned`, `calendar.event.created` / `ics.downloaded` |
| 4 | T−48h: brief auto-generated → "Your doctor brief is ready" | J11 | `brief.generated` {trigger=appointment} |
| 5 | After visit: "How did it go?" → mark completed, update last_done, new HbA1c, med changes (→ J2) | `appointments` (completed), `patient_preventive_status.last_done_on`, `bronze_lab` → `lab_results` (HbA1c) | `appointment.completed`, `lab.result.logged` |

### J11 Doctor brief (F12, F14)
| # | Step | System | Events |
|---|---|---|---|
| 1 | Me → Briefs → Generate (period picker, default since last visit) or auto (J10.4) | builder (reads `timeline_5min` for the four charts and `baselines`, plus `daily_summary`, `care_summary`, `meal_response`, `exercise_response`, `glucose_events`, `lab_results`, `clinical_flags`, `pattern_candidates`, `interaction_alerts`, `doctor_questions`) → charts → narrative + validator → HTML/PDF | `brief.generation.started`, `agent.run.*`, `brief.validator.completed` {rejected_n}, `brief.generated` |
| 2 | Patient view: same content as doctor (no hidden findings); patterns shown as "worth discussing" | | `brief.viewed` {by=patient} |
| 3 | Add/edit own questions (Me → Doctor questions) | `doctor_questions` | `question.created/edited` |
| 4 | Share: requires `brief_sharing` consent → link (expiry 72h default) / QR / PDF | `brief_shares` | `consent.granted`, `brief.share.created` {ttl_h}, `brief.pdf.downloaded` |
| 5 | Doctor opens link | read-only page | `brief.share.accessed` (actor = clinician_link) |
| 6 | Patient revokes | | `brief.share.revoked` |

### J12 Companion chat and guardrails (F15)
| # | Step | System | Events |
|---|---|---|---|
| 1 | Open chat (floating button / contextual entry) | new or resume conversation | `chat.opened` {entry} |
| 2 | Send message | input guard | `chat.message.sent`, `guard.input.checked` {verdict} |
| 3a | Normal → context build → router → specialist → output guard → reply (+TTS) | | `agent.run.*`, `guard.output.checked`, `chat.reply.shown` |
| 3b | Med-advice request ("Can I skip metformin today since my sugar is fine?") → refusal template: explains why the app can't advise, suggests asking the doctor/pharmacist, [Add to doctor questions] | no LLM needed | `guard.blocked` {verdict=blocked_med_advice}, `question.created` {origin=refused_chat} |
| 3c | Diagnosis request ("Do I have nerve damage?") → non-diagnostic template + offer to log symptom and add question | | `guard.blocked` {verdict=blocked_diagnosis} |
| 3d | Urgent keywords → J8 | | `guard.urgent` |
| 4 | Session ends (idle 10 min) → episode summary + embedding (async) | | `memory.episode.created` |

### J13 "What Smart Health has learned about you" (F16)
| # | Step | System | Events |
|---|---|---|---|
| 1 | Nightly reflection proposes/updates facts with evidence | `memory_facts` | `memory.fact.proposed/activated/superseded` |
| 2 | New active fact → gentle card "I've noticed you usually walk after dinner. Is that right?" [Yes] [Not really] | | `memory.fact.prompted` |
| 3 | Me → What Smart Health has learned: list by category (routines, preferences, barriers, food responses) with "why I think this" (evidence) | | `memory.screen.viewed` |
| 4 | Confirm / edit / delete | status change + version | `memory.fact.confirmed` / `.edited` / `.rejected` |

### J15 Lifestyle timeline and day traces (F18)
| # | Screen | System | Events |
|---|---|---|---|
| 1 | Insights → Day view (date picker, default today) | load `timeline_5min` for the day | `timeline.day.viewed` {date} |
| 2 | The four charts on one time axis: heart rate, SpO2 and glucose as lines (each with the person's usual range from `baselines`; readings on the worse side marked) and blood pressure as a scatter; overlay of meals, doses (taken / late / missed), exercise, symptoms (with the note), mood, steps, sleep and scheduled work hours; "no data" gaps shown as gaps | | `timeline.marker.opened` {stream} |
| 3 | Tap a marker → detail sheet with the log and its outcome ("2 h after this meal your glucose rose by X, similar to / more than your usual") | reads `meal_response` / `exercise_response` | `timeline.window.viewed` {anchor_kind} |
| 4 | Nightly, or after each sync: `timeline_5min`, summaries, responses and pattern candidates rebuilt | worker (`build_gold_v2.py` today) | `timeline.rebuilt` {days_n}, `pattern.candidate.created` {pattern_key} |
| 5 | Candidate with n ≥ 5 → patient sees neutral card "Nights after late dinners, your morning readings were higher. Worth mentioning to your doctor."; same item lands in the brief | | `pattern.patient_note.shown`, `pattern.added_to_brief` |
| 6 | Brief generation picks best / worst / typical day by fixed rules | | `brief.day_traces.selected` {dates} |

### J14 Settings, data and consent
Language change → `user.locale.set`; notification prefs → `settings.reminders.set`; revoke consent → `consent.revoked` {kind} (revoking brief_sharing revokes all live links → `brief.share.revoked`); export my data → `data.export.requested`; delete account → `account.deletion.requested/completed`.

---

## 3. A day in the life (how the pieces interlock)

```
07:00  Fasting glucose logged (J5) → threshold ok → momentum input
07:30  Breakfast logged → meal-triggered metformin prompt (J4.1b) → Taken
12:30  Hawker lunch: char kway teow → high-sodium flag + swap card (J9.5); CGM worn → `meal_response` computed 3 h later (J6.5)
19:00  Metformin reminder (J4) → no response → 20:00 re-nudge → 21:00 window closes → unconfirmed
19:45  Learned slot: walk nudge (J9) → user logs 20-min walk (J5)
21:30  Evening check-in (mood 3, stress 4, sleep 3) (J5)
08:00+ Next open: "Did you take your evening Metformin?" → "Forgot" (J4.5–6)
02:00  Nightly: timeline → daily summary and worse-side check → flags → check-in plan → reflection ("misses evening dose on busy days") → nudge policy (J7, J13)
T−48h  Appointment → brief generated (J11) → shared with doctor
```

---

## 4. Event catalogue (canonical names)

`app.opened` · `user.account.created` · `user.locale.set` · `onboarding.{eligibility.checked,method.chosen,step.completed,field.captured,summary.reviewed,completed}` · `consent.{granted,revoked}` · `device.{permission.requested,permission.granted,permission.denied,connected}` · `settings.reminders.set` · `scan.{camera.opened,image.uploaded,extraction.completed,review.opened,item.unrecognised}` · `medication.{created,updated,stopped}` · `dose.{schedule.generated,prompt.meal_triggered,event.confirmed,event.unconfirmed,reason.prompted,reason.captured}` · `refill.reminder.sent` · `clash.{check.run,alert.shown,alert.acknowledged}` · `med.explainer.viewed` · `tts.played` · `glucose.reading.logged` · `threshold.{checked,breached}` · `meal.logged` · `food.{flag.shown,swap.shown,swap.accepted,response.computed,response.summary.viewed,response.note.shown}` · `workout.logged` · `symptom.logged` · `checkin.{mood.completed,mood.skipped,symptom.planned,symptom.asked,symptom.answered,symptom.skipped}` · `log.entry.{edited,deleted}` · `health.{sync.started,sync.completed,sync.failed,import.file.completed}` · `cgm.sensor.{connected,removed}` · `decline.checked` · `flag.{created,patient_note.shown,added_to_brief}` · `urgent.{shown,action.taken,recheck.prompted,tier.escalated,contact.alerted,contact.called,checkin.answered}` · `awareness.answered` · `contact.{saved,test.sent}` · `nudge.{planned,acted,dismissed}` · `notification.{sent,opened}` · `preventive.viewed` · `appointment.{suggested,planned,completed}` · `calendar.{oauth.granted,event.created}` · `ics.downloaded` · `brief.{generation.started,validator.completed,generated,viewed,pdf.downloaded,share.created,share.accessed,share.revoked}` · `question.{created,edited}` · `chat.{opened,message.sent,reply.shown}` · `guard.{input.checked,output.checked,blocked,urgent}` · `agent.run.{started,finished,failed}` · `memory.{episode.created,fact.proposed,fact.activated,fact.superseded,fact.prompted,fact.confirmed,fact.edited,fact.rejected,screen.viewed}` · `timeline.{day.viewed,marker.opened,window.viewed}` · `timeline.rebuilt` · `baseline.{built,reset}` · `work.schedule.set` · `pattern.{candidate.created,patient_note.shown,added_to_brief}` · `brief.day_traces.selected` · `lab.result.{logged,edited}` · `bp.reading.logged` · `meal.{analysis.completed,estimate.confirmed,estimate.edited}` · `data.export.requested` · `ingestion.original.deleted` · `account.deletion.{requested,completed}`

Adding a new event = add it here first, then implement.

---

## 5. Demo script (≈ 6 min, `DEMO_MODE=true`, patient Mr Tan, CGMacros participant 046, 91 days)

1. **Hook (30 s):** "10 minutes with the doctor, 364 days alone." Show the Today screen.
2. **Scan (60 s):** scan a real metformin label → review with confidence chips → confirm → a fish-oil + TCM item triggers the clash sheet, and one unknown TCM item says "not checked", honestly.
3. **Explain (30 s):** Metformin explainer in Mandarin with TTS; sources visible.
4. **Guardrail moment (45 s):** chat "My sugar is fine today, can I skip metformin?" → refusal + "Added to your doctor questions."
5. **Adherence why (30 s):** debug-trigger a missed dose → reason sheet → "Side effects" → symptom + question logged.
6. **Food response (45 s):** Insights → food responses from the CGM days (gentlest and spikiest foods, from `meal_response`): chicken rice vs yong tau foo; log chicken rice → factual note.
7. **Decline flag and check-in (30 s):** the "outside your usual range" card (fires from early September in the demo data) → targeted question about the tingling in his left foot.
8. **Urgent (20 s):** replay a 2.8 mmol/L reading → urgent screen (no AI in the loop, by design).
9. **Memory (20 s):** "What Smart Health has learned" → confirm a fact.
10. **Doctor brief (60 s, finale):** open brief: the four charts (heart rate, SpO2, glucose, blood pressure) with his usual range and the day's overlay, prescription timeline with glucose overlay, miss reasons, food leaderboard, patterns labelled unverified with evidence, completeness bar → share link opened on a second device ("the doctor's view").
11. **Close (10 s):** trust-boundary diagram + "Explain, organise, remind. Never advise."
