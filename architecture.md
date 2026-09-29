# Architecture — Smart Health

Blueprint for AI coding agents and humans. Read [prd.md](prd.md) for the *what/why*, [schema.md](schema.md) for tables, [flow.md](flow.md) for journeys, [rules.md](rules.md) for coding boundaries, [design.md](design.md) for UI.

---

> **Platform decisions (2026-09-29, override anything below that disagrees):**
> - **Front end is a mobile-first web app shown in a phone-sized frame or WebView**, not a store-published native app (no store fees). Wherever this document says Expo / React Native / Health Connect / HealthKit, read "mobile-first web app". Device data arrives by replay of the cited datasets and file import, not live phone-health APIs.
> - **No Docker required.** Use a hosted Postgres (with pgvector) and a free web host. Docker Compose is optional for anyone who wants a local database.
> - **No sign-up/sign-in flows.** A "Start as demo patient" button creates a session, and every query is scoped by the session's user id. Consent records, the audit log and doctor share-link tokens stay.
> - **LLM/AI provider is undecided.** It is chosen in backlog story E0-9. Everything calls it through the gateway in `llm/gateway.py`.

## 1. System overview

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
│             context builder ─► INPUT GUARD ─► router ─► specialist agent   │
│             ─► OUTPUT GUARD (safety gate) ─► persist + event log           │
│             tools = typed wrappers over domain services (least privilege)  │
│                                                                            │
│  Worker (APScheduler): reminders · window close · nightly momentum ·       │
│          reflection (memory) · brief pre-generation · replay feeder         │
│                                                                            │
│  PostgreSQL 16 + pgvector   ·   Object storage (images, PDFs, audio)       │
└───────┬───────────────────────┬──────────────────────┬─────────────────────┘
        │ TB-2 (outbound only)  │ TB-3                 │ TB-4
┌───────▼───────┐    ┌──────────▼─────────┐   ┌────────▼──────────────┐
│ LLM gateway → │    │ Tencent Cloud TTS  │   │ Google Calendar API   │
│ Hunyuan (chat,│    │ (speech synthesis) │   │ (user OAuth, opt-in)  │
│ vision, embed)│    └────────────────────┘   └───────────────────────┘
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
| TB-6 | Agent ↔ tools | Agent overreach | Per-agent tool allowlist; tools are read-only except explicitly listed writes (e.g. `log_symptom`, `add_doctor_question`, `propose_memory_fact`) |

**Core rule:** *The LLM generates language; code generates facts.* Interactions, thresholds, adherence stats, trends and brief numbers are computed by deterministic services.

---

## 2. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Front end | **Mobile-first web app (React + TypeScript, strict)** shown in a phone frame / WebView | No store publishing cost; runs anywhere for the demo. (Earlier Expo plan superseded, see note above) |
| State / data | TanStack Query (server state), Zustand (UI state), react-hook-form + zod | Caching, offline, typed forms |
| Charts (app) | `react-native-gifted-charts` (or Victory Native) | Line/bar/heat-cell charts |
| Health data | `react-native-health-connect` (Android), `@kingstinct/react-native-healthkit` (iOS) | Device-agnostic wearables |
| Camera / media | `expo-camera`, `expo-image-picker`, `expo-audio` | Rx scans, meal photos, TTS playback |
| Notifications | `expo-notifications` (local schedule plus server push) | Dose reminders, nudges |
| i18n | `i18next` + `react-i18next` (en, zh, ms, ta) | Multilingual |
| Backend | **Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic** | Typed APIs; strong data/ML ecosystem |
| Agents | **LangGraph** (state graphs, checkpoints) + own guardrail and memory layer | Observable, controllable agent flows |
| LLM | **Tencent Hunyuan** (chat, vision, embeddings) via an OpenAI-compatible client, wrapped by `llm/gateway.py` | Tencent ecosystem; swappable provider |
| Vector search | **pgvector** in Postgres | One DB for relational and vectors |
| DB | PostgreSQL 16 | JSONB, enums, pgvector |
| Jobs | APScheduler in a separate worker process, jobs persisted in Postgres | Simple, no Redis needed |
| Brief rendering | Jinja2 HTML + Matplotlib (SVG charts) → WeasyPrint PDF | Deterministic, printable, no headless browser |
| TTS | Tencent Cloud TTS (fallback: device TTS via `expo-speech`) | Multilingual speech |
| Calendar | Google Calendar API (OAuth, user-initiated) + `.ics` fallback | Scheduling |
| Storage | Tencent Cloud COS (prod) / local MinIO or filesystem (dev) | Images, PDFs, audio |
| Deploy | Hosted Postgres + free web host for the demo (Docker optional locally) | Zero-cost demo; Tencent Cloud hosting optional |
| Quality | Backend: ruff, mypy (strict), pytest, pytest-asyncio. App: eslint, prettier, tsc, jest + RNTL | See rules.md |

> Verify current package names and Hunyuan model IDs and endpoint in the official docs at setup time; keep them in `.env`, never hard-coded.

---

## 3. Repository structure

```
smart-health/
├─ prd.md  architecture.md  flow.md  schema.md  design.md  rules.md
├─ README.md                         # setup + run in 5 commands
├─ .env.example                      # every env var documented
├─ docker-compose.yml                # postgres(pgvector), api, worker, minio
│
├─ apps/
│  └─ mobile/                        # Expo app
│     ├─ app/                        # Expo Router (file = route)
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
│     │  ├─ memory.tsx               # "What Smart Health has learned about you"
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
│     │  │  ├─ momentum.py           # baselines, EWMA slope, acceleration, flags
│     │  │  ├─ food_response.py      # iAUC, peak rise per meal/food
│     │  │  ├─ nutrition.py          # food DB lookup, flags
│     │  │  ├─ preventive.py         # due/overdue
│     │  │  ├─ nudge_policy.py       # adaptive timing (epsilon-greedy)
│     │  │  ├─ aggregates.py         # daily rollups for charts/brief
│     │  │  ├─ timeline.py           # timeline_events queries, day-trace assembly, best/worst/typical day
│     │  │  ├─ event_windows.py      # meal/workout/dose/sleep anchors → outcomes; pattern_candidates (n>=5, quality gates)
│     │  │  ├─ labs.py               # lab_results, eGFR (CKD-EPI 2021), population_priors lookup
│     │  │  └─ events.py             # append-only event log writer
│     │  ├─ agents/
│     │  │  ├─ graph.py              # main LangGraph (chat + tasks)
│     │  │  ├─ state.py              # AgentState TypedDict
│     │  │  ├─ context.py            # context builder (memory + data, token budget)
│     │  │  ├─ router.py             # intent → specialist
│     │  │  ├─ specialists/          # onboarding, med_explainer, extractor, adherence_coach,
│     │  │  │                        # lifestyle_coach, checkin, scheduler, question_helper,
│     │  │  │                        # brief_writer, reflection
│     │  │  ├─ tools/                # typed tool wrappers → services (allowlists per agent)
│     │  │  ├─ guardrails/           # input_guard.py, output_guard.py, policies.yaml, templates/
│     │  │  ├─ memory/               # store.py, reflection.py, retrieval.py, episodes.py
│     │  │  └─ prompts/              # *.md prompt files, versioned
│     │  ├─ llm/                     # gateway.py (retry, timeout, logging), providers/hunyuan.py
│     │  ├─ knowledge/               # ingest.py, chunk.py, retrieve.py (pgvector)
│     │  ├─ brief/                   # builder.py (data), narrative.py (LLM+validator),
│     │  │                           # charts.py (matplotlib SVG), templates/*.html, pdf.py
│     │  ├─ integrations/            # tts_tencent.py, google_calendar.py, ics.py, storage.py
│     │  └─ workers/                 # scheduler.py, jobs/*.py
│     └─ tests/
│        ├─ unit/  integration/
│        └─ redteam/                 # guardrail suite: must be 100% pass
│
├─ data/
│  ├─ knowledge/                     # approved corpus only: drug facts from 250k Medicines (+ sources.csv listing manifest # and licence). No other source without approval (prd.md A10)
│  ├─ reference/                     # interactions.csv, foods.csv, preventive_items.csv
│  ├─ mock/                          # cgm/, watch_export/, demo_patient.json
│  └─ README.md                      # provenance + licences
│
└─ scripts/
   ├─ seed_reference.py              # load interactions, foods, preventive items
   ├─ ingest_knowledge.py            # chunk + embed corpus
   ├─ import_watch_export.py         # Xiaomi/Apple export → health_samples, sleep_sessions
   ├─ import_cgmacros.py             # CGMacros → glucose_readings, meals, health_samples, lab_results (time-shift, mg/dL→mmol/L)
   ├─ import_bigideas.py             # BIG IDEAs subset → glucose_readings, meals, health_samples
   ├─ import_nhanes_priors.py        # NHANES → population_priors + persona sampling
   ├─ import_fitbit_kaggle.py        # second wearable format (parser test / fallback stream)
   ├─ simulate_persona.py            # 60-day synthetic history: doses, mood, BP, symptoms, glucometer (params documented)
   ├─ seed_data_sources.py           # data source catalogue (manifest #, licence, url) → data_sources (attribution)
   ├─ seed_demo.py                   # demo patient with 90 days of history
   └─ replay.py                      # stream mock CGM/watch data in "real time" for demo
```

---

## 4. Data flows

### 4.1 Prescription scan (F2 → F4, F5)
```
camera → POST /scans (image) → storage → extractor agent (Hunyuan vision, JSON schema output)
→ scan_extractions (fields + confidence) → app review screen → user confirms/edits
→ POST /scans/{id}/confirm → patient_medications + dose_schedules (adherence.py)
→ clash.check(patient) → interaction_alerts → notification if hit → event_log
```
Extraction uses a strict JSON schema; unknown or low-confidence fields become `null` with confidence 0, never guessed.

### 4.2 Dose loop (F4)
```
worker: every minute → due dose_events → push reminder (T), re-nudge (T+60m)
app: "Taken" → PATCH /doses/{id} status=taken → event_log
worker: window_end passed & no confirm → status=unconfirmed
app open → pending reasons → user taps reason → status=missed|taken_late_logged + miss_reason
nightly → adherence aggregates → momentum + brief
```

### 4.3 Wearables and CGM ingest (F6, F7)
```
Health Connect/HealthKit (on app foreground + background fetch) ─┐
file import (Xiaomi/Apple export) ───────────────────────────────┼→ POST /health/import (batch, idempotent by source+external_id)
replay.py (demo: mock CGM + watch) ──────────────────────────────┘      → health_samples / glucose_readings
                                                                        → thresholds.check() (sync, per glucose reading) → urgent?
                                                                        → food_response.update() when post-meal window completes
```

### 4.4 Nightly pipeline (worker, 02:00 local)
```
aggregates.rollup(day) → momentum.compute(all metrics) → momentum_snapshots + clinical_flags
→ checkin planner (pick ≤1 targeted question for tomorrow)
→ reflection agent (propose/update memory_facts from the day) → nudge_policy.update()
→ preventive.recompute() → if appointment in 48h: brief.generate()
```

### 4.4b Lifestyle timeline (F18), part of the nightly job
```
for each new meal / workout / dose / sleep session (anchors):
  window = anchor_time .. +N (meal 0–120 min, workout 0–120, dose +2h/+4h, sleep → next fasting)
  outcome = glucose delta vs pre-anchor baseline (quality_ok readings only; need ≥ 70% expected points)
  → event_windows (quality_ok=false rows kept but excluded from stats)
group windows by pattern_key → if n_pairs ≥ 5: median delta + IQR → pattern_candidates (open)
brief.builder picks best/worst/typical day → day_traces (glucose + markers + HR/steps + sleep)
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
| Time of day (needs ≥ 10 valid days) | Median and IQR glucose by clock hour | sprint or 14+ days |
| Weekday vs weekend (needs ≥ 3 weekends) | Adherence, steps, glucose | weekly |

### 4.5 Chat turn (F15), the agent harness path
```
user msg → input_guard (rules + classifier)
   ├─ urgent → thresholds/red-flag template → urgent screen (no LLM)
   ├─ med_advice_request → refusal template + "add to doctor questions?" (no LLM needed)
   └─ ok → context.build(user) → router → specialist (tools) → draft
           → output_guard (policy checks) ─ pass → reply (+TTS optional)
                                           └ fail → safe template + log guardrail_event
→ persist message, episode summary (async), event_log
```

### 4.6 Brief generation (F12)
```
brief.builder (deterministic): profile, meds, adherence matrix, glucose stats, nutrition,
  exercise, sleep, mood, symptoms, flags, preventive, questions, completeness → BriefData (Pydantic)
→ charts.py → SVGs (prescription timeline, glucose trend, TIR bar, food leaderboard, activity, sleep)
→ narrative.py: LLM writes "Top 3" + section summaries + suggested questions,
  each sentence tagged [ev:<evidence_id>]; validator rejects untagged or unknown ids or numbers not in BriefData
→ Jinja2 HTML → WeasyPrint PDF → storage → briefs row → share link (optional, consented)
```

---

## 5. Agent harness and memory ("grows with the user")

### 5.1 Graph
```
START → load_context → guard_input ─┬─ urgent → END (template)
                                    ├─ blocked → END (template)
                                    └─ route → {specialist} → guard_output ─┬─ ok → persist → END
                                                                            └─ fail → fallback → persist → END
```
- `AgentState`: user_id, locale, messages, intent, context (profile, facts, episodes, recent aggregates), tool_results, draft, guard_verdicts, run_id.
- Every node writes an `agent_steps` row (inputs hash, outputs, latency, tokens).

### 5.2 Specialists and tool allowlists
| Agent | Purpose | Tools (R = read, W = write) |
|---|---|---|
| onboarding | Conversational onboarding → structured profile | W `upsert_profile`, W `add_condition`, W `add_medication_draft` |
| extractor | Vision → JSON medication fields | none (pure function) |
| med_explainer | Explain a med from corpus | R `get_patient_meds`, R `search_knowledge(type=drug)` |
| adherence_coach | Supportive talk about routines/barriers | R `get_adherence_summary`, W `add_doctor_question` |
| lifestyle_coach | Nudges from reviewed templates (approved corpus if added) | R `get_aggregates`, R `get_food_responses`, R `search_knowledge(type=lifestyle)` |
| checkin | Ask targeted symptom question, record answer | R `get_flags`, W `log_symptom` |
| scheduler | Suggest visit/screening, create event after confirmation | R `get_preventive_status`, W `create_calendar_event` (requires `user_confirmed=true`) |
| question_helper | Rephrase patient questions | W `add_doctor_question` |
| brief_writer | Narrative for brief | R `get_brief_data` (only) |
| reflection | Nightly memory consolidation | R day data, R episodes, W `propose_memory_fact` |

No agent can write medications, doses or thresholds. Those paths are user- or code-only.

### 5.3 Memory tiers
| Tier | Store | Written by | Used for |
|---|---|---|---|
| Profile (authoritative) | relational tables (patient_profiles, patient_medications, conditions…) | user and onboarding | every context |
| Observations | glucose_readings, health_samples, meals, dose_events, … + daily_aggregates | ingest and user | trends, brief |
| **User model** | `memory_facts` (key, value, category, confidence, evidence_refs, status, version) | reflection agent (proposes); user (confirms/edits) | personalisation, nudges, chat |
| Episodic | `memory_episodes` (summary + embedding) | async after each chat session | recall in chat |

**Fact lifecycle:** `proposed` (confidence < 0.7) → `active` (confidence ≥ 0.7 or user-confirmed) → `superseded` (new version) / `rejected` (user deleted, never re-proposed with same key+value). Confidence rises with repeated evidence and decays when there's no supporting evidence for 30 days.

**Context builder** (token budget ~3k): profile summary → active facts (top 20 by relevance/recency) → top-5 episodes by vector similarity → last 7-day aggregates → relevant flags. Never includes name, NRIC, phone or email.

### 5.4 Adaptive nudging (nudge_policy.py)
State per user: (nudge_type × time_slot) → {sent, acted}. Choose slot = argmax Beta-smoothed act-rate with ε = 0.15 exploration. Hard caps: ≤ 3 nudges/day, quiet hours 22:00–07:00. Updated nightly.

---

## 6. Deterministic engines (formulas)

- **Baseline** (per metric): rolling 28-day median `m` and MAD `d` (require ≥ 10 data days; else "learning").
- **z-score:** `z = (x_today − m) / (1.4826·d)`.
- **Momentum:** slope of 7-day EWMA (α = 0.3) via least squares over the last 7 days, normalised by `1.4826·d`.
- **Change of momentum:** `accel = slope_last7 − slope_prev7`.
- **Flag rule:** `|z| ≥ 2` on ≥ 3 of last 5 days **or** `|accel| ≥ 1.0` (normalised) with ≥ 14 days of data. Severity: `review` (brief only + neutral patient note) or `watch` (brief only).
- **Metrics:** fasting glucose, post-meal glucose, daily steps, workout minutes, sleep duration, sleep midpoint variability, resting HR, HRV (if any), mood, stress, adherence %.
- **Food response:** for a meal at t0 during a CGM sprint, baseline g0 = mean CGM over [t0−15m, t0]; `iAUC` = trapezoid area above g0 over [t0, t0+120m]; `peak_rise = max − g0`. Per food: mean, min–max, n. Surface when n ≥ 2. Multi-item meals attribute to the dominant-carb item and mark as `mixed`.
- **Urgent thresholds** (config `thresholds.yaml`, clinical validation pending): `glucose < 3.0` → urgent_now; `glucose < 3.9` → hypo_selfcare (+ urgent if symptoms); `glucose ≥ HIGH_URGENT` twice within 6h → seek_care_today; red-flag symptoms → urgent_now.
- **Adherence %:** taken + taken_late_logged ÷ scheduled (excluding doses whose window hasn't closed).

---

## 7. API surface (REST, JSON, `/api/v1`)
`auth/*` · `onboarding/{profile,consents,complete}` · `meds` CRUD · `scans` (POST image, GET, POST confirm) · `doses` (GET today, PATCH status/reason) · `logs/{glucose,meals,workouts,symptoms,checkins}` CRUD · `health/import` (batch) · `insights/{trends,momentum,food-responses}` · `memory/facts` (GET, PATCH confirm/edit, DELETE) · `chat` (POST message, SSE stream) · `briefs` (POST generate, GET, GET pdf, POST share, DELETE share) · `appointments` CRUD · `preventive` GET · `questions` CRUD · `events` (POST client events batch) · `share/brief/{token}` (public, read-only).

OpenAPI is the contract; the mobile client is generated from it (`openapi-typescript`).

---

## 8. Configuration (`.env.example`)
`DATABASE_URL`, `JWT_SECRET`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_CHAT_MODEL`, `LLM_VISION_MODEL`, `EMBED_MODEL`, `EMBED_DIM`, `TENCENT_SECRET_ID`, `TENCENT_SECRET_KEY`, `TTS_REGION`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `STORAGE_BACKEND`, `STORAGE_BUCKET`, `SHARE_LINK_TTL_HOURS`, `TZ=Asia/Singapore`, `DEMO_MODE`.

## 9. Demo mode
`DEMO_MODE=true` → seed demo patient ("Uncle Tan", 90 days history incl. one CGM sprint), `replay.py` streams today's CGM/watch data at 1× or accelerated speed, and a hidden debug menu in the app lets you trigger: a missed dose, a hypo reading, a momentum flag, a clash, and brief generation. See flow.md §5.

## 10. Build order (critical path)
1. Repo, hosted DB and migrations baseline, demo session, event log
2. Reference data + knowledge ingest + LLM gateway + guardrails + red-team tests (safety first)
3. Onboarding (form) → meds (manual) → dose loop → notifications
4. Scan + extractor → clash checker → explainer (+TTS, i18n)
5. Logging (glucose, meals, workouts, check-ins, symptoms) → health import + replay
6. Aggregates → momentum → thresholds/urgent → check-ins
7. Food response (CGM sprint) → lifestyle coach → nudge policy
8. Brief (data → charts → narrative + validator → PDF → share)
9. Memory (episodes, reflection, memory screen) → chat
10. Preventive + calendar → onboarding chat → polish, demo script, video
