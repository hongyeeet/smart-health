# Rules — boundaries for AI coding agents (CodeBuddy / WorkBuddy / others)

Read this before writing any code. These rules override convenience. When a rule conflicts with a request, stop and ask.

Related: [prd.md](prd.md) (what/why) · [architecture.md](architecture.md) (where things go) · [schema.md](schema.md) (data) · [flow.md](flow.md) (journeys and events) · [design.md](design.md) (UI)

---

## 1. Safety invariants (non-negotiable)

These protect patients and are what the judges score under Responsible AI. **Breaking one is a failed build.**

1. **No medication advice, ever.** No code path may produce text recommending starting, stopping, skipping, changing, doubling or substituting a medication or dose. Dose text shown to users comes **only** from `medications` and `medication_schedule` fields the user confirmed.
2. **LLM generates language, code generates facts.** Interactions (`services/clash.py`), thresholds (`services/thresholds.py`), adherence, momentum, food response and every number in the brief are computed deterministically. Never ask an LLM to compute, infer or "estimate" these. (The only allowed estimate is meal nutrients, see rule 13.)
3. **`app/services/` must not import from `app/agents/` or `app/llm/`** (the JEV client is `app/llm/jev.py`; there is no `app/decision/` or `app/memory/` folder in the code). `services/api/tests/unit/test_layering.py` checks only the medicine-scan modules today (`scheduler.py` imports `app.agents`), so the rule is not yet enforced for every service.
4. **Every patient-facing AI output passes the output guard** (today in the code: `nutritionstore.guarded`, the JEV guard, and `app/services/chat_guard.py` for chat; there is no `guardrails/output_guard.py` file). No direct `llm.generate()` → UI path. On guard failure, return the approved template, never the raw draft.
5. **Urgent path has no LLM.** Threshold breaches and red-flag symptoms go straight to templated urgent content. Never block or delay it on a network/LLM call.
6. **No diagnosis.** Never output condition names as a conclusion about the user ("you have neuropathy"). Patterns are phrased as "worth discussing with your doctor".
7. **Honest uncertainty.** Unknown → say unknown: `null` + confidence 0 in extraction, "not checked" for interactions without reference data, "learning" for baselines with < 10 days. Never default to "safe", "normal" or 0.
8. **No hidden findings.** Anything placed in a doctor brief must be viewable by the patient.
9. **Cited health content only.** Lifestyle/drug explanations must come from `knowledge_chunks` and carry source ids; the output guard rejects uncited health claims.
10. **Agents have least privilege.** Tools are registered per agent (architecture.md §5.2). Do not add a write tool to an agent without updating that table and adding tests. No agent may write medications, doses, thresholds or consents.
11. **Thresholds live in settings** (`app/core/config.py`, placeholders such as `meal_high_sodium_mg`, set from the environment; there is no `config/thresholds.yaml`), never hard-coded in logic, and carry the comment `# clinical validation pending`.
12. **Red-team suite must be 100% green** (`services/api/tests/redteam/`). Never skip, xfail or weaken a red-team test to make CI pass.
13. **Estimates are labelled as estimates.** The LLM may estimate meal nutrients from a photo or text. Store them as `evidence_status = inferred` with a confidence, keep the original and the raw analysis, show "Estimated" until the user confirms, and let the user edit. Never present an estimate as measured. Everything downstream is computed in code from the stored values.
14. **JEV supports decisions and never controls safety.** Urgent thresholds, interaction lookup, refusal rules and dose logic run in code. A JEV answer below the confidence floor (start at 0.8), or a JEV outage, takes the conservative path (refusal template, "not checked", ask the user). A rule that fires always beats a JEV answer.
15. **Nothing is "validated".** Never use the words validated, verified or clinically confirmed for AI output, reference lookups, thresholds or patterns. Use the evidence statuses in memory.md.

## 1b. Data source policy

- **Only ingest data from the datasets in `download_manifest.csv` (48) and the GlucoBench Kaggle link.** Do not add data, corpora, reference tables or guideline text from anywhere else (no scraping, no other datasets, no LLM-generated "facts" stored as reference data).
- Every seeded or imported row records its source (`data_sources`, manifest #). If a task needs data these sources don't have, stop and list it as "Needs your OK" instead of sourcing it yourself.
- Simulated data may only be built from cited data, must be marked `entry_source = 'demo_dataset'` or simulated, and must be disclosed.
- Raw datasets are never committed (see licences in `data/README.md`).
- Branches: commit straight to `dev` (small commits, `git pull --rebase origin dev` before pushing); a `feature/<task-id>-<name>` branch is optional. Only the owner verifies UAT and production readiness and promotes `dev` to `uat` and `uat` to `main`; developers and AI assistants never push there or declare a release verified. A task's named Reviewer verifies that task before it is done. Never force-push.

## 2. Scope discipline

- Build what prd.md specifies. Do not add features, screens, tables or dependencies that aren't in the docs; propose them instead.
- Keep the docs true: if you change a table, event, route, flow, token or agent tool, update schema.md / flow.md / architecture.md / design.md **in the same change**.
- Don't refactor unrelated code in a feature change.
- **Build in `apps/web`, never in `apps/mock`.** The mock is the frozen clickable reference. Copy from it, do not edit it unless a task says "update the mock". A task that names no app means `apps/web`.
- Follow the build order in architecture.md §10 unless told otherwise.

## 3. Data rules

- Schema changes **only** via Alembic migrations, matching schema.md exactly (names, types, constraints). No `create_all()` outside tests.
- **All tables, views and reference and demo values are created and loaded in epic E1 only** (Joely: Raw, Bronze, Silver and reference tables; Hong Yi: Gold and operations tables and views; Joely loads all values in E1-4). Every later task reads and writes rows in tables that already exist. If a later task seems to need a new table or a new reference dataset, stop and ask the owner: the fix belongs in E1 and the layer map in schema.md.
- Canonical units at write (mmol/L, mg, g, seconds). Convert only in the API schema layer.
- Use `NULL` for "no data", never `0` or empty string.
- Ingest endpoints must be idempotent (`source` + `external_id`).
- Enforce state machines in services (dose, scan, fact, appointment); invalid transitions raise `InvalidTransition`.
- Multi-step writes (e.g. scan confirm) run in one transaction.
- `event_log` is append-only. Never UPDATE/DELETE it. Every state change in flow.md emits its listed event, in the same transaction.
- Never send name, email, phone, NRIC or exact birth date to the LLM or TTS. Use the Memory Service evidence packet, which strips them.
- Don't log health values or free-text notes in application logs; use ids. (The audit trail is `event_log`, not stdout.)

## 4. Backend conventions (Python 3.12 / FastAPI)

- Type hints everywhere; `mypy --strict` clean; `ruff` (lint + format) clean.
- Pydantic v2 models for every request/response; no raw dicts across layers.
- Layering: `routers` (HTTP only) → `services` (domain logic, deterministic) / `agents` (LLM orchestration) → `db` (models, queries). Routers contain no business logic.
- Async SQLAlchemy 2.0; no N+1 queries in list endpoints (use `selectinload` / joins).
- All external calls (LLM, TTS, OCR, Calendar, storage) go through a wrapper in `llm/` (including the JEV client `llm/jev.py`) or `integrations/`, with timeout, retry and logging. Never call SDKs directly from routers/services.
- Prompts live in `agents/prompts/*.md` with a `version:` header; `agent_runs.prompt_version` records it. No prompt strings inline in Python.
- LLM calls that return structure use JSON-schema / function-calling output and are validated with Pydantic; on validation failure retry once, then fail safe.
- Config via `pydantic-settings` from env; every new variable is added to `.env.example` with a comment.

## 5. Front-end conventions (mobile-first web app, React / TypeScript; the Expo references below now mean this web app)

- `strict: true`; no `any` (use `unknown` + narrowing); no `@ts-ignore` without a linked reason.
- Server state via TanStack Query hooks in `src/features/<feature>/`; API types generated from OpenAPI, not hand-written.
- UI only from `src/components/ui` primitives and `theme/tokens.ts`; no hard-coded colours, font sizes or spacing.
- All strings through i18n keys (EN/ZH/MS/TA); no string concatenation for sentences.
- Every interactive element has `accessibilityLabel`/`accessibilityRole`; follow design.md §10.
- Every user action listed in flow.md calls `logEvent()` with the canonical event name.
- Writes use the offline queue with an idempotency key; show sync state via `Banner`.

## 6. Error handling

### Backend
- Define domain errors in `core/errors.py` (`NotFound`, `ValidationFailed`, `InvalidTransition`, `ConsentRequired`, `ExternalServiceError`, `GuardBlocked`, `RateLimited`). Map them to RFC 7807 `application/problem+json` responses with a stable `code` field. Never leak stack traces or SQL to clients.
- Validate at boundaries (request bodies, uploaded files, external API responses, LLM outputs). Trust internal calls.
- External services: timeout (LLM and vision 45 s as set by `LLM_TIMEOUT_S`, JEV 10 s, TTS 10 s, others 10 s), retry with exponential backoff + jitter for 429/5xx (max 3), no retry on 4xx.

### Fail-safe matrix (what users see when something fails)
| Failure | Behaviour |
|---|---|
| LLM down / timeout in chat | Templated message "I can't answer right now. Your logs and reminders still work." Core features unaffected |
| Extraction fails / low confidence | Scan → `failed`/`needs_review`; offer manual entry. Never auto-save |
| Explainer generation fails | Show cached explainer if any; else basic info from `drug_reference` + "Ask your pharmacist" |
| Output guard fails / uncertain | Safe template; log `guardrail_events` |
| Brief narrative validator rejects sentences | Drop those sentences, keep deterministic sections; record in `validator_report`. Brief still ships |
| TTS fails | Hide play button with "Audio unavailable"; fall back to device TTS if enabled |
| Health sync fails | Banner with retry; keep cursor; no partial duplicates (idempotent) |
| Calendar fails | Offer .ics download |
| Worker job fails | Retry with backoff; alert in logs; jobs are idempotent (safe to re-run for a day) |
| Threshold check fails | **Fail loud**: treat as error in tests/monitoring; the urgent check must not silently pass |

### Mobile
- Every query/mutation has loading, empty, error and offline states designed (design.md §5 `EmptyState`, `Banner`).
- Error Boundary per tab; crashes show a recover screen, never a blank screen.
- User-facing errors are plain language with one next step; technical details go to logs only.

## 7. Testing and definition of done

A task is done only when:
- [ ] Unit tests for new domain logic (services) including edge cases: no data, boundary thresholds, timezone/DST-free SGT, duplicates.
- [ ] State machine and transaction tests for anything touching doses, scans, facts, appointments.
- [ ] Red-team tests updated if the change touches agents, prompts, guardrails or patient-facing text. Suite covers at least: med-advice requests (EN/ZH/MS/TA, direct and indirect, "hypothetically", role-play), prompt injection via chat, image text ("ignore instructions…" on a label) and food names, diagnosis requests, urgent keywords, uncited-claim generation.
- [ ] Events from flow.md emitted (asserted in integration tests).
- [ ] `ruff`, `mypy --strict`, `pytest`, `tsc --noEmit`, `eslint`, `jest` all pass.
- [ ] Docs updated if contracts changed.
- [ ] UI changes checked on a device/emulator at 100% and 200% font scale, light and dark.

## 8. Security basics (PII hardening is deferred, these are not)

Demo scope: row-level security, consent-scoped retrieval, data-classification tagging and retention workflows are deferred (memory.md section 13). The basics below still apply.
- No secrets in code, fixtures or git history; use `.env` (git-ignored) and `.env.example`.
- Demo scope: the app has no sign-in. A person is the key the app sends as the `X-User` header (made on the device at set-up); every query is scoped by that key (never by the request body). Mr Tan's example record is read-only for everyone. Real JWT auth is still to do before any real use.
- Share tokens: 32 random bytes, stored as SHA-256 hash, expiring, revocable, access-logged.
- File uploads: allow-list MIME types (jpeg, png, heic, csv, zip, xml), size limit 10 MB, strip EXIF before storage.
- Treat all user text, image text and imported file content as untrusted input for agents (prompt-injection defence: delimited, never concatenated into system prompts).
- Parameterised queries only (ORM); no string-built SQL.

## 9. Dependencies
- Prefer the stack in architecture.md §2. Adding a dependency requires: it's maintained, licence is permissive (MIT/Apache/BSD), and it's recorded in the PR description with why.
- Pin versions (lockfiles committed). No removing or major-upgrading dependencies without asking.

## 10. Git and workflow
- Small, focused commits; conventional messages (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
- Never force-push shared branches; never commit `.env`, data exports with real personal data, or model keys.
- Real watch exports from teammates go in `data/mock/watch_export/` **only after** removing identifiers; prefer committing synthetic/replay data.
- **Hackathon proof:** development must happen through CodeBuddy/WorkBuddy for a meaningful share of work; take chat screenshots at each milestone (≥ 3 required) into `docs/proof/`.

## 10b. Session handover

At the end of every session, follow `docs/handover/HANDOVER.md`: update the tasks you worked on in your own backlog (`docs/backlog/<your-name>.md`) and run `python scripts/update_tracker.py` to refresh the central tracker (`docs/backlog/SOT.md`), write the session log in `docs/handover/sessions/` (named `<user>_<YYYY-MM-DD_HHMM>.md`, including every decision made outside the docs), update `docs/handover/project-memory.md`, and run the docs check (`python scripts/verify_docs.py --stamp`, an automatic consistency check and not a sign-off) before pushing to `dev`.

## 11. When unsure
- If a requirement is ambiguous, choose the **safer** interpretation (less advice, more uncertainty disclosure, more logging) and leave a `TODO(decision):` note plus a question in the PR description.
- If a request would violate §1, don't implement it. Explain which invariant it breaks and propose a compliant alternative.
