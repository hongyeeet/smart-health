# Architecture — Equinox

Blueprint for AI coding agents and humans. Read [prd.md](prd.md) for the *what/why*, [schema.md](schema.md) for tables, [flow.md](flow.md) for journeys, [rules.md](rules.md) for coding boundaries, [design.md](design.md) for UI, [memory.md](memory.md) for memory, evidence and the JEV decision layer.

---

> **Platform decisions (2026-09-29, override anything below that disagrees):**
> - **Front end is a mobile-first web app shown in a phone-sized frame or WebView**, not a store-published native app (no store fees). Wherever this document says Expo / React Native / Health Connect / HealthKit, read "mobile-first web app". Device data arrives by replay of the cited datasets and file import, not live phone-health APIs.
> - **Local app, Supabase database (hosting update 2026-10-15: the plan is Firebase Hosting for the web app and Cloud Run for the API and the worker, see [../handover/deployment-gcp.md](../handover/deployment-gcp.md)).** The web app and API run on each developer's machine. The database is Supabase (Postgres 16 with pgvector): every developer uses the same project through a private `.env` that is never committed. Row-level security is enabled on every table with no policies, so the public API key cannot read or write anything, and only the backend connects (direct connection string or service key, server-side only). Photos and exports go to a private Supabase Storage bucket. The only other outbound calls are the AI APIs (Vertex AI, ElevenLabs and JEV), the Workato reminder webhooks and, if switched on, Google Cloud Vision. For local work there is no Docker requirement. Postgres is standard, so the database can move later without a redesign.
> - **No sign-up/sign-in flows (updated 2026-10-15).** The app opens on Mr Tan's example record, which is read-only for everyone (any write is refused with a plain message), and anyone can create their own user from the avatar menu. The person is chosen by an `X-User` header (demo-grade, no real login), and every query is scoped by that user id. There is no demo user and no "Start as demo patient" button any more. Consent records, the audit log and doctor share-link tokens stay.
> - **AI provider (decided 2026-10-02, D-047; see [ai-models.md](ai-models.md)).** Everything runs through Google Cloud Vertex AI (Gemini 3.8 Flash for text and photos, which replaced Claude Sonnet 5.5 in D-059; Gemini Embedding; `gemini-2.5-flash-image` for dish pictures; Cloud Translation) except speech (ElevenLabs) and the JEV decision model (TypeSafe). There is no Tencent fallback. Everything calls the AI through the gateway in `llm/gateway.py`.
> - **JEV** is the typed decision layer ([OpenJev](https://github.com/razorback16/openjev): yes/no, choice and score answers with calibrated confidence). It is wired in backlog task E0-3 and always called through `decision/`. If JEV is off or unreachable, every decision takes the conservative path (no model fallback). See [memory.md](memory.md) and [ai-models.md](ai-models.md).
> - **Security is demo-grade.** Row-level security, consent-scoped retrieval, data-classification tagging and retention workflows are deferred (memory.md section 13). The clinical safety path is never deferred.

## 1. System overview

![System architecture: the person, web app, API, scheduler, database and outside services](../assets/diagrams/03-system-architecture.png)

*Figure: system architecture, updated 2026-10-15. The text diagram below shows the same system in more detail.*


```
┌──────────────────────── Patient device (untrusted) ────────────────────────┐
│  Expo app (React Native, TS)                                               │
│  • UI (tabs: Today · Log · Meds · Insights · Me) • camera • notifications  │
│  • Health Connect / HealthKit reader • offline queue • TTS audio player    │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │ HTTPS + JWT (TB-1)
┌───────────────────────────────▼──────────── Backend (trusted) ─────────────┐
│  FastAPI  ──►  Domain services (deterministic)                             │
│     │          adherence · momentum · food-response · clash · thresholds   │
│     │          · preventive schedule · brief data builder                  │
│     │                                                                      │
│     └──►  Agent harness (LangGraph)                                        │
│             Memory Service ─► INPUT GUARD ─► router ─► specialist agent    │
│             (JEV decisions in guard, router) ─► OUTPUT GUARD ─► log        │
│             tools = typed wrappers over services and the Memory Service    │
│                                                                            │
│  Scheduler (APScheduler, in the API process; own worker service in         │
│          production): tick · emails · food_pictures · nightly · calendar    │
│                                                                            │
│  PostgreSQL 16 + pgvector   ·   Object storage (images, PDFs, audio)       │
└───────┬───────────────────────┬──────────────────────┬─────────────────────┘
        │ TB-2 (outbound only)  │ TB-3                 │ TB-4
┌───────▼───────┐    ┌──────────▼─────────┐   ┌────────▼──────────────┐
│ LLM gateway → │    │ ElevenLabs speech  │   │ Google Calendar API   │
│ Vertex AI     │    │ (TTS and STT)      │   │ (user OAuth, opt-in)  │
│ (text, vision)│    └────────────────────┘   └───────────────────────┘
└───────────────┘
        ▲
┌───────┴────────────── Doctor (read-only) ────────────────┐
│ Share link /brief/{token} → server-rendered HTML / PDF   │ (TB-5, token + expiry)
└──────────────────────────────────────────────────────────┘
```

### Trust boundaries (include in the submission diagram)
| ID | Boundary | Threat | Control |
|---|---|---|---|
| TB-1 | App ↔ API | Tampered client, replay, prompt injection via user text/images | JWT auth, server-side validation (Pydantic), rate limits, input guard, idempotency keys |
| TB-2 | API ↔ LLM | Hallucination, unsafe advice, data leakage to provider | LLM never has write access; outputs pass output guard; minimal context (no name/NRIC); all numbers come from DB, not model |
| TB-3 | API ↔ TTS | Speaking unsafe text | Only guarded, final text is synthesised |
| TB-4 | API ↔ Calendar | Unwanted bookings | Explicit user confirmation per event; scoped OAuth |
| TB-5 | Doctor ↔ Brief | Unauthorised access | Consent record, random 32-byte token (hashed at rest), expiry, revocation, access logged |
| TB-7 | API ↔ JEV decision server | Sending health text to a third party; wrong or low-confidence decision | State is de-identified; a JEV answer below the confidence floor, or an outage, takes the conservative path; rules always override JEV; provider swappable behind `decision/` |
| TB-8 | API ↔ Supabase | Public API key used to read tables; leaked service key | RLS on with no policies; service key and connection string only in the server environment; only the backend connects |
| TB-6 | Agent ↔ tools | Agent overreach | Per-agent tool allowlist; tools are read-only except explicitly listed writes (e.g. `log_symptom`, `add_doctor_question`, `propose_memory_fact`) |

**Core rule:** *The LLM generates language; code generates facts.* Interactions, thresholds, adherence stats, trends and brief numbers are computed by deterministic services. The one allowed model estimate is meal nutrients: stored as `inferred`, shown as "Estimated" until the user confirms, then used by code like any other value.

### Data layers
Bronze (one `bronze_*` table per source: the input as received) → Silver (typed facts, each with a `bronze_id`) → Gold (the master timeline, fixed baselines, summaries and responses, application memory, six views). App, Reference and Operations tables sit beside the pipeline. Every table is in the `public` schema; the layer of each table is a comment on the table and in the table index in [data-model-v2.md](data-model-v2.md) (data model v2, built 2026-10-05; the older [schema.md](schema.md) describes v1). Feature-to-table routing is in [data-flow.md](data-flow.md) section 6. Full rules, memory planes and evidence statuses are in [memory.md](memory.md).

```
storage/{user_id}/
├── meals/          # original meal photos
├── medications/    # prescription, box, supplement and TCM images
├── documents/
└── exports/        # wearable and dataset files
```
Originals are never overwritten. A better analysis is a new record that links to the same original.

---

## 2. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Front end | **Mobile-first web app: Vite, React, TypeScript (strict), React Router, Tailwind v4 over CSS-variable tokens, `motion`** shown in a phone frame on a laptop and full screen on a phone or iPad | No store publishing cost; runs anywhere for the demo. (Earlier Expo plan superseded, see note above) |
| State / data | TanStack Query (server state), Zustand (UI state), react-hook-form + zod | Caching, offline, typed forms |
| Charts (app) | Hand-built SVG chart components in `src/charts` | One consistent look, grayscale patterns, no chart-library styling |
| Health data | `react-native-health-connect` (Android), `@kingstinct/react-native-healthkit` (iOS) | Device-agnostic wearables |
| Camera / media | `expo-camera`, `expo-image-picker`, `expo-audio` | Rx scans, meal photos, TTS playback |
| Notifications | `expo-notifications` (local schedule plus server push) | Dose reminders, nudges |
| i18n | `i18next` + `react-i18next` (en, zh, ms, ta); keys written as `t('key', 'English default')`, extracted with `i18next-parser` | Multilingual |
| Backend | **Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic** | Typed APIs; strong data/ML ecosystem |
| Agents | **LangGraph** (state graphs, checkpoints) + own guardrail and memory layer | Observable, controllable agent flows |
| LLM | **Gemini 3.8 Flash** (chat, explainer, brief narrative, photos; Claude Sonnet 5.5 was replaced in D-059), **`gemini-2.5-flash-image`** (dish pictures) and **Gemini Embedding** (768 dimensions) on Google Cloud Vertex AI, **Google Cloud Translation** for fixed text, wrapped by `llm/gateway.py` | One cloud, one bill; model chosen per job (ai-models.md); swappable by configuration |
| Decision layer (JEV) | **OpenJev** typed decisions (`noul`, `choice`, `score`) behind `decision/`; hosted, small CPU models, or self-hosted; if it is off or unreachable, the conservative path applies | Fast, bounded, calibrated classification for routing and guards. The TypeSafe JEV model (`typesafe/jev-1.13`) is used, hosted on OpenRouter |
| Vector search | **pgvector** in Postgres | One DB for relational and vectors |
| DB | Supabase (managed PostgreSQL 16 with pgvector), one shared project | JSONB, enums, pgvector; RLS on with no policies |
| Jobs | APScheduler (`AsyncIOScheduler`) inside the API process, switched by `SCHEDULER_ENABLED`; in production it runs in a separate single-instance worker service. Jobs: `tick`, `emails`, `food_pictures`, `nightly`, `calendar_top_up`. Reminder e-mails and Google Calendar dose reminders go through Workato (recipes owned by Joely, not finished) | Simple, no Redis needed |
| Brief rendering | Jinja2 HTML + Matplotlib (SVG charts) → WeasyPrint PDF | Deterministic, printable, no headless browser |
| TTS and STT | **ElevenLabs** (`eleven_multilingual_v2` for cached explainers, `eleven_flash_v2_5` for live lines, Scribe v2 for transcription) | Multilingual speech; audio is cached by text hash |
| Calendar | Google Calendar API (OAuth, user-initiated) + `.ics` fallback | Scheduling |
| Storage | Supabase Storage, private bucket (`STORAGE_BACKEND=supabase`) | Images, PDFs, audio, exports |
| Runtime | Locally: web app and API on each machine. Planned hosting: Firebase Hosting (web) plus Cloud Run (API and worker), see [../handover/deployment-gcp.md](../handover/deployment-gcp.md). Database and file storage on Supabase (Postgres 16 + pgvector, private Storage buckets) | One shared database with the same seeded example record (Mr Tan) for everyone |
| Quality | Backend: ruff, mypy (strict), pytest, pytest-asyncio. App: eslint, prettier, tsc, jest + RNTL | See rules.md |

> Verify current package names, model IDs, regions and prices in the vendor consoles at setup time; keep them in `.env`, never hard-coded.

---

## 3. Repository structure

```
TencentHackathon/                   # the Equinox repository (the tree below is the original blueprint; the code now differs in detail)
├─ README.md                         # what this is, where to start, branches
├─ docs/                             # ALL documents
│  ├─ specs/                         # prd, architecture, flow, schema, design, rules, memory
│  ├─ backlog/                        # SOT.md tracker + one backlog per person
│  ├─ handover/                      # HANDOVER.md (start here), session-log-template.md, sessions/
│  ├─ mockup/                        # prompt and outputs for the design mockup
│  └─ reference/                     # superseded starting templates
├─ .github/                          # pull request template, CODEOWNERS
├─ .env.example                      # every env var documented
│
├─ apps/
│  ├─ mock/                          # clickable mock version, every screen on demo data (see apps/mock/design.md)
│  └─ web/                           # production app: shell, design system, data layer; screens are built here (see apps/web/design.md)
│     ├─ src/app/                    # shell, router, route registry (routeIds.ts)
│     │  ├─ _layout.tsx              # providers: query, theme, i18n, auth
│     │  ├─ (auth)/sign-in.tsx
│     │  ├─ onboarding/              # index (choose form|chat), form/[step].tsx, chat.tsx, consent.tsx
│     │  ├─ (tabs)/
│     │  │  ├─ _layout.tsx           # 5 tabs
│     │  │  ├─ today.tsx             # doses due, check-in, nudges, alerts
│     │  │  ├─ log.tsx               # glucose, meal, workout, symptom, mood
│     │  │  ├─ meds.tsx              # med list, scan, clash status
│     │  │  ├─ insights.tsx          # trends, momentum, food responses
│     │  │  └─ me.tsx                # profile, memory, devices, settings, brief
│     │  ├─ scan/                    # camera.tsx, review.tsx (confirm extracted fields)
│     │  ├─ meds/[id].tsx            # explainer + TTS + history
│     │  ├─ log/{glucose,meal,workout,symptom,checkin}.tsx
│     │  ├─ brief/[id].tsx           # patient view of brief + share
│     │  ├─ memory.tsx               # "What Equinox has learned about you"
│     │  ├─ appointments/            # list, new
│     │  ├─ questions.tsx            # questions for my doctor
│     │  ├─ chat.tsx                 # companion chat
│     │  └─ urgent.tsx               # full-screen escalation (modal route)
│     ├─ src/
│     │  ├─ components/ui/           # design-system primitives (see design.md)
│     │  ├─ components/charts/
│     │  ├─ features/<feature>/      # hooks, api calls, components per feature
│     │  ├─ lib/api/                 # typed client generated from OpenAPI
│     │  ├─ lib/health/              # healthConnect.ts, healthKit.ts, importFile.ts, types.ts
│     │  ├─ lib/offline/             # queue + idempotency keys
│     │  ├─ lib/telemetry/           # logEvent() → /events (see flow.md)
│     │  ├─ i18n/{en,zh,ms,ta}.json
│     │  └─ theme/tokens.ts          # from design.md
│     └─ app.config.ts
│
├─ services/
│  └─ api/
│     ├─ pyproject.toml
│     ├─ alembic/                    # migrations (only way to change schema)
│     ├─ app/
│     │  ├─ main.py                  # FastAPI app factory
│     │  ├─ core/                    # config.py (pydantic-settings), security.py, errors.py, logging.py
│     │  ├─ db/                      # session.py, models/*.py (1 file per domain), base.py
│     │  ├─ schemas/                 # Pydantic request/response models
│     │  ├─ api/routers/             # auth, onboarding, meds, scans, doses, logs, health_import,
│     │  │                           # insights, memory, chat, briefs, appointments, questions, events, share
│     │  ├─ services/                # DETERMINISTIC domain logic (no LLM imports allowed)
│     │  │  ├─ adherence.py          # schedules, windows, statuses, refill prediction
│     │  │  ├─ clash.py              # interaction lookup
│     │  │  ├─ thresholds.py         # urgent tiers (config-driven)
│     │  │  ├─ baselines.py          # fixed baselines (first 14 days), worse-side check, decline flags
│     │  │  ├─ meal_response.py      # level before, peak rise, iAUC, recovery per meal; per-food grouping
│     │  │  ├─ nutrition.py          # food DB lookup, flags
│     │  │  ├─ preventive.py         # due/overdue
│     │  │  ├─ nudge_policy.py       # adaptive timing (epsilon-greedy)
│     │  │  ├─ aggregates.py         # daily_summary and care_summary
│     │  │  ├─ timeline.py           # builds timeline_5min (44 features), day-trace assembly, best/worst/typical day
│     │  │  ├─ responses.py          # meal_response, exercise_response, glucose_events; pattern_candidates (n>=5, quality gates)
│     │  │  ├─ labs.py               # lab_results (HbA1c, fasting glucose, fasting insulin), population_priors lookup
│     │  │  └─ events.py             # append-only event log writer
│     │  ├─ agents/
│     │  │  ├─ graph.py              # main LangGraph (chat + tasks)
│     │  │  ├─ state.py              # AgentState TypedDict
│     │  │  ├─ context.py            # asks the Memory Service for the evidence packet (token budget)
│     │  │  ├─ router.py             # intent → specialist
│     │  │  ├─ specialists/          # onboarding, med_explainer, extractor, adherence_coach,
│     │  │  │                        # lifestyle_coach, checkin, scheduler, question_helper,
│     │  │  │                        # brief_writer, reflection
│     │  │  ├─ tools/                # typed tool wrappers → services (allowlists per agent)
│     │  │  ├─ guardrails/           # input_guard.py, output_guard.py, policies.yaml, templates/
│     │  │  ├─ memory/               # reflection.py, episodes.py (read and write only through the Memory Service)
│     │  │  └─ prompts/              # *.md prompt files, versioned
│     │  ├─ llm/                     # gateway.py (retry, timeout, logging), providers/ (vertex_claude.py, vertex_embeddings.py, translate.py, elevenlabs.py), meal_analysis.py (photo/text → macros)
│     │  ├─ decision/                # jev_client.py (JEV wire API), conservative.py (the no-model fallback path), questions.py (typed question sets)
│     │  ├─ memory/                  # service.py (scoped reads/writes), evidence_packet.py, lifecycle.py (propose, supersede)
│     │  ├─ knowledge/               # ingest.py, chunk.py, retrieve.py (pgvector)
│     │  ├─ brief/                   # builder.py (data), narrative.py (LLM+validator),
│     │  │                           # charts.py (matplotlib SVG), templates/*.html, pdf.py
│     │  ├─ integrations/            # (speech is in llm/providers/elevenlabs.py), google_calendar.py, ics.py, storage.py
│     │  └─ workers/                 # scheduler.py, jobs/*.py
│     └─ tests/
│        ├─ unit/  integration/
│        └─ redteam/                 # guardrail suite: must be 100% pass
│
├─ data/                             # ALL data (see data/README.md)
│  ├─ README.md                      # what lives where, licences, rules
│  ├─ plan/                          # smart_health_data_plan.xlsx
│  ├─ raw/                           # downloaded datasets (gitignored, never committed)
│  ├─ processed/                     # importer outputs (gitignored)
│  ├─ reference/                     # small seed tables: interactions, foods, preventive items
│  ├─ knowledge/                     # approved corpus only: drug facts from 250k Medicines (+ sources.csv listing manifest # and licence). No other source without approval (prd.md A10)
│  └─ demo/                          # small synthetic demo data (simulated 60-day history)
│
└─ scripts/
   ├─ seed_reference.py              # load interactions, foods, preventive items
   ├─ ingest_knowledge.py            # chunk + embed corpus
   ├─ import_watch_export.py         # Xiaomi/Apple export → bronze_watch → watch_readings (5-minute buckets)
   ├─ import_cgmacros.py             # LEGACY (v1 tables, no longer run). Mr Tan comes from generate_mr_tan.py + load_mr_tan_v2.py + build_gold_v2.py
   ├─ import_bigideas.py             # LEGACY (v1 tables, no longer run)
   ├─ import_nhanes_priors.py        # NHANES → population_priors + persona sampling
   ├─ import_fitbit_kaggle.py        # second wearable format (parser test / fallback stream)
   ├─ simulate_persona.py            # LEGACY (60-day v1 history); replaced by generate_mr_tan.py (91 days, planted cause-and-effect links)
   ├─ seed_data_sources.py           # data source catalogue (manifest #, licence, url) → data_sources (attribution)
   ├─ seed_demo.py                   # LEGACY; see load_mr_tan_v2.py and build_gold_v2.py
   └─ replay.py                      # stream mock CGM/watch data in "real time" for demo
```

---

## 4. Data flows

### 4.1 Prescription scan (F2 → F4, F5)
```
camera → POST /scans (image) → storage + bronze_medication → extractor agent (vision model, JSON schema output)
→ scan_extractions (fields + confidence) → app review screen → user confirms/edits
→ POST /scans/{id}/confirm → medications + medication_schedule + medication_log (adherence.py)
→ clash.check(patient) → interaction_alerts → notification if hit → event_log
```
Extraction uses a strict JSON schema; unknown or low-confidence fields become `null` with confidence 0, never guessed.

### 4.2 Dose loop (F4)
```
worker: every minute → due medication_log rows (status pending) → push reminder (T), re-nudge (T+60m)
app: "Taken" → PATCH /doses/{id} status=taken, taken_at → bronze_medication + event_log
worker: window_end passed & no confirm → the row stays pending and is shown as unconfirmed
app open → pending reasons → user taps reason → status=missed + miss_reason, or taken (late if > 60 min after the time, computed)
nightly → care_summary (adherence over prescription medicines, main barrier, refill) → decline flags + brief
```

### 4.3 Wearables and CGM ingest (F6, F7)
```
Health Connect/HealthKit (on app foreground + background fetch) ─┐
file import (Xiaomi/Apple export) ───────────────────────────────┼→ POST /health/import (batch, idempotent by source+external_id)
replay.py (demo: mock CGM + watch) ──────────────────────────────┘      → bronze_watch / bronze_cgm → watch_readings / cgm_readings
                                                                        → thresholds.check() (sync, per glucose reading) → urgent?
                                                                        → meal_response when 3 hours of CGM exist after a meal
```

### 4.4 Nightly pipeline (worker, 02:00 local)
```
timeline.build(day) → timeline_5min → baselines (built once, reset only on purpose) → daily_summary (worse-side share, declining_metrics) → clinical_flags
→ checkin planner (pick ≤1 targeted question for tomorrow)
→ reflection agent (propose/update memory_facts from the day) → nudge_policy.update()
→ care_summary (adherence, preventive, questions, flags) → preventive.recompute() → if appointment in 48h: brief.generate()
```

### 4.4b Lifestyle timeline (F18), part of the nightly job
```
timeline_5min: every Silver stream on one 5-minute clock (watch, CGM, blood pressure, food, exercise, medication, mood, symptoms, work hours)
for each meal / exercise session (anchors):
  window = anchor_time .. +N (meal 0–180 min, exercise 0–12 h)
  outcome = glucose and heart-rate change vs the level before (valid CGM readings only; need enough points)
  → meal_response / exercise_response; excursions → glucose_events with their context
group events by pattern_key → if n_pairs ≥ 5: median delta + IQR → pattern_candidates (open)
brief.builder picks best/worst/typical day → day_traces (the four charts + overlay for those days)
```
No LLM is involved; the brief narrative may only cite these results by evidence id. Event-window catalogue (each needs ≥ 5 matched pairs unless stated; results are associations, never causes):

| Anchor event | Outcome | Window |
|---|---|---|
| Meal | Glucose peak rise and iAUC (existing food response; needs ≥ 2 per food) | 0–120 min |
| Late meal (after 21:00) | Next-morning fasting glucose | overnight |
| Workout or post-meal walk | Glucose change vs matched meals without one | 0–120 min |
| Dose taken vs missed/unconfirmed | Glucose at +2 h / +4 h and next fasting | 0–4 h, next morning |
| Missed-dose streak (≥ 3 days) | 7-day glucose drift (one streak is shown, not concluded on) | 7 days |
| Short or irregular sleep (< 6 h vs ≥ 7 h) | Next-morning fasting glucose | overnight |
| Low mood / high stress / low HRV | Daily glucose variability (CV%, needs ≥ 14 days, descriptive only) | same day |
| High-sodium meals | Next-day BP (only if BP logged) | 24 h |
| Alcohol logged (needs ≥ 3 nights) | Overnight minimum glucose | overnight |
| Symptom entry | Context card of prior 24 h: glucose, meals, doses, sleep (retrieval only, no inference) | prior 24 h |
| Time of day (needs ≥ 10 valid days) | Median and IQR glucose by clock hour (this is the fixed `baselines` table) | 14+ days |
| Weekday vs weekend (needs ≥ 3 weekends) | Adherence, steps, glucose | weekly |

### 4.5 Chat turn (F15), the agent harness path
```
user msg → input_guard (rules first, then JEV yes/no questions; rules always win)
   ├─ urgent → thresholds/red-flag template → urgent screen (no LLM)
   ├─ med_advice_request → refusal template + "add to doctor questions?" (no LLM needed)
   └─ ok → JEV route → memory_service.get_* → evidence packet → specialist (tools) → draft
           → output_guard (policy checks) ─ pass → reply (+TTS optional)
                                           └ fail → safe template + log guardrail_event
→ persist message, episode summary (async), event_log
```

### 4.6 Brief generation (F12)
```
brief.builder (deterministic): profile, meds, adherence matrix, glucose stats, nutrition,
  exercise, sleep, mood, symptoms, flags, preventive, questions, completeness → BriefData (Pydantic)
→ charts.py → SVGs (the four report charts from timeline_5min: heart rate, SpO2 and glucose with the usual range, blood pressure scatter; prescription timeline, TIR bar, food leaderboard, activity, sleep)
→ narrative.py: LLM writes "Top 3" + section summaries + suggested questions,
  each sentence tagged [ev:<evidence_id>]; validator rejects untagged or unknown ids or numbers not in BriefData
→ Jinja2 HTML → WeasyPrint PDF → storage → briefs row → share link (optional, consented)
```

### 4.7 Meal analysis (F6, F7)
```
photo or text → storage + bronze_food (Bronze)
→ llm/meal_analysis.py (vision or text model): items + estimated kcal, carbs, protein, fat, fibre, sugar, sodium, confidence per field
→ the raw answer (model_id, prompt_version) stays in the bronze_food payload
→ food_logs (estimated_by = llm_photo or llm_text, source llm_estimate) shown with an "Estimated" badge
→ user confirms or edits → estimated_by='user'
→ nutrition flags (code) · meal_response (needs measured CGM glucose; per food n ≥ 2) · daily_summary
```
Open Food Facts and NHANES dietary values are only a sanity check that can add a "check this" flag. Re-running with a newer model or prompt writes a new `bronze_food` row; the log keeps its original `bronze_id` unless the user accepts the new estimate.

---

## 5. Agent harness and memory ("grows with the user")

### 5.1 Graph
```
START → guard_input (rules + JEV) ─┬─ urgent → END (template)
                                   ├─ blocked → END (template)
                                   └─ route (JEV) → memory_service → {specialist} → guard_output ─┬─ ok → persist → END
                                                                            └─ fail → fallback → persist → END
```
- `AgentState`: user_id, locale, messages, intent, route, evidence_packet, tool_results, draft, guard_verdicts, run_id.
- JEV and the Memory Service are called as graph nodes; each writes an `agent_steps` row (`node` = `jev` or `memory`). See [memory.md](memory.md) sections 5 to 7.
- Every node writes an `agent_steps` row (inputs hash, outputs, latency, tokens).

### 5.2 Specialists and tool allowlists
| Agent | Purpose | Tools (R = read, W = write) |
|---|---|---|
| onboarding | Conversational onboarding → structured profile | W `upsert_profile`, W `add_condition`, W `add_medication_draft` |
| extractor | Vision → JSON medication fields | none (pure function) |
| med_explainer | Explain a med from corpus | R `get_patient_meds`, R `search_knowledge(type=drug)` |
| adherence_coach | Supportive talk about routines/barriers | R `get_adherence_summary`, W `add_doctor_question` |
| lifestyle_coach | Nudges from reviewed templates (approved corpus if added) | R `get_daily_summary`, R `get_meal_responses`, R `search_knowledge(type=lifestyle)` |
| checkin | Ask targeted symptom question, record answer | R `get_flags`, W `log_symptom` |
| scheduler | Suggest visit/screening, create event after confirmation | R `get_preventive_status`, W `create_calendar_event` (requires `user_confirmed=true`) |
| question_helper | Rephrase patient questions | W `add_doctor_question` |
| brief_writer | Narrative for brief | R `get_brief_data` (only) |
| reflection | Nightly memory consolidation | R day data, R episodes, W `propose_memory_fact` |

No agent can write medications, doses or thresholds. Those paths are user- or code-only.

### 5.3 Memory planes and lifecycle
Full design in [memory.md](memory.md). Summary:

| Plane | Stored in | Written by |
|---|---|---|
| Semantic | `memory_facts`, `memory_episodes`, `user_profile` | User, nightly reflection (proposes), user confirms |
| Temporal | `timeline_events` (view), `timeline_5min`, `daily_summary`, `meal_response`, `exercise_response`, `glucose_events` | Deterministic services |
| Entity | `medications`, `medication_schedule`, `foods`, `food_logs`, `appointments`, `care_summary` | User confirmation, importers |
| Relationship | `pattern_candidates`, `clinical_flags`, `interaction_alerts` | Deterministic services and lookups |

**Fact lifecycle:** `proposed` (confidence < 0.7) → `active` (confidence ≥ 0.7 or user-confirmed) → `superseded` (linked by `supersedes_id`) / `rejected` (never re-proposed with the same key and value). Confidence rises with repeated evidence and decays after 30 days without support. Every fact carries `evidence_status` (`inferred` when proposed by reflection, `observed` when the user confirms). Nothing is `validated`.

**Evidence packet** replaces the old context builder (budget about 3k tokens): profile summary, active facts (top 20), top 5 episodes by similarity, last 7 days of aggregates, open flags, and the evidence for the question, each with source ids, status and confidence. It never includes a name, NRIC, phone or email. The LLM answers from the packet only.

### 5.4 Adaptive nudging (nudge_policy.py)
State per user: (nudge_type × time_slot) → {sent, acted}, counted from `notifications` (kind `nudge`: sent, opened, acted). Choose slot = argmax Beta-smoothed act-rate with ε = 0.15 exploration. Hard caps: ≤ 3 nudges/day, quiet hours 22:00–07:00. Updated nightly.

---

## 6. Deterministic engines (formulas)

- **Baseline** (per metric, `baselines`): the person's usual range by hour of day (p05, p25, p50, p75, p95) from the **first 14 days** with data (at least 5 days); blood pressure: one range from the first 5 readings. Heart-rate and HRV buckets inside logged exercise are left out. It applies from the day after its window and never moves; a new one is built only on a reset (doctor review, medication change, user).
- **Worse-side share:** per day and metric, the share of readings above p95 (heart rate, glucose) or below p05 (HRV, SpO2) for that hour → `daily_summary.*_worse_pct`.
- **Decline flag:** a day is flagged when more than 20% are on the worse side; a metric is declining when 3 of the last 5 days are flagged (`declining_metrics`). Severity: `review` (brief only + neutral patient note) or `watch` (brief only). Getting better is not flagged. Starting values, not clinically validated.
- **Metrics:** heart rate, HRV, SpO2, glucose, blood pressure (systolic and diastolic). Steps, sleep, exercise minutes, mood, stress and adherence are summarised in `daily_summary` and `care_summary` but not flagged.
- **Meal response** (`meal_response`): for a meal at t0 with CGM data, baseline g0 = mean CGM over [t0−30m, t0]; `iauc_2h` = area above g0 over [t0, t0+120m]; `rise = max over 3 h − g0` (never below zero); time to peak; time to recover. Per food: group by food, mean, min–max, n. Surface when n ≥ 2.
- **Urgent thresholds** (config `thresholds.yaml`, clinical validation pending): `glucose < 3.0` → urgent_now; `glucose < 3.9` → hypo_selfcare (+ urgent if symptoms); `glucose ≥ HIGH_URGENT` twice within 6h → seek_care_today; red-flag symptoms → urgent_now.
- **Adherence %:** `taken` ÷ (`taken` + `missed` + `skipped`) over scheduled doses of prescription medicines whose window has closed (`pending` doses and extra doses are not counted).

---

## 7. API surface (REST, JSON, `/api/v1`)
`auth/*` · `onboarding/{profile,consents,complete}` · `meds` CRUD · `scans` (POST image, GET, POST confirm) · `doses` (GET today, PATCH status/reason) · `logs/{glucose,meals,exercise,symptoms,wellbeing,blood-pressure,labs}` CRUD · `health/import` (batch) · `insights/{trends,timeline,food-responses}` · `memory/facts` (GET, PATCH confirm/edit, DELETE) · `chat` (POST message, SSE stream) · `briefs` (POST generate, GET, GET pdf, POST share, DELETE share) · `appointments` CRUD · `preventive` GET · `questions` CRUD · `events` (POST client events batch) · `share/brief/{token}` (public, read-only).

OpenAPI is the contract; the mobile client is generated from it (`openapi-typescript`).

---

## 8. Configuration (`.env.example`)
`DATABASE_URL` (Supabase direct connection string), `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (server only, never in the web app), `JWT_SECRET`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_REGION`, `GOOGLE_APPLICATION_CREDENTIALS`, `LLM_CHAT_MODEL`, `LLM_VISION_MODEL`, `LLM_VISION_CHALLENGER`, `EMBED_MODEL`, `EMBED_DIM`, `TRANSLATE_GLOSSARY_ID`, `ELEVENLABS_API_KEY`, `ELEVENLABS_TTS_MODEL`, `ELEVENLABS_TTS_LIVE_MODEL`, `ELEVENLABS_STT_MODEL`, `JEV_BASE_URL`, `JEV_API_KEY`, `AI_DAILY_CALL_CAP`, `AI_DAILY_BUDGET_USD`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `STORAGE_BACKEND`, `STORAGE_BUCKET`, `FOOD_IMAGE_BUCKET`, `FOOD_IMAGE_MODEL`, `SCHEDULER_ENABLED`, `WORKATO_EMAIL_WEBHOOK_URL`, `SHARE_LINK_TTL_HOURS`, `TZ=Asia/Singapore`, `DEMO_MODE`.

## 9. Demo mode
`DEMO_MODE` (default `true`) → the example patient (Mr Tan, 91 days of history with continuous CGM: `scripts/load_mr_tan_v2.py` then `scripts/build_gold_v2.py`), `replay.py` streams today's CGM/watch data at 1× or accelerated speed, and a hidden debug menu in the app lets you trigger: a missed dose, a hypo reading, a momentum flag, a clash, and brief generation. See flow.md §5.

## 10. Build order (critical path)
1. Repo, Supabase connection and migrations baseline, demo session, event log
2. Reference data + knowledge ingest + LLM gateway + guardrails + red-team tests (safety first)
3. Onboarding (form) → meds (manual) → dose loop → notifications
4. Scan + extractor → clash checker → explainer (+TTS, i18n)
5. Logging (glucose, meals, exercise, check-ins, symptoms, blood pressure, labs) → health import + replay
6. Timeline → baselines → daily summary and flags → thresholds/urgent → check-ins
7. Meal response (CGM) → lifestyle coach → nudge policy
8. Brief (data → charts → narrative + validator → PDF → share)
9. Memory (episodes, reflection, memory screen) → chat
10. Preventive + calendar → onboarding chat → polish, demo script, video
