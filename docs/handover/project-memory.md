# Project memory

The one place that consolidates the state of the project: what is decided, what has changed, and what is open. Every AI assistant and developer reads it at the start of a session and updates it at the end. It sits above the per-session logs: logs hold the detail, this file holds the summary and points to them.

> Not to be confused with `docs/specs/memory.md`, which describes how the *app* stores what it learns about a patient.

**Last docs check:** 2026-10-01 13:54: PASS (22 of 22 checks passed)

The docs check is automatic: `python scripts/verify_docs.py --stamp`. It checks links, stale names, secrets, backlog integrity, the schema layer map, that every session log is listed here, and the dev-only hooks. Fix any FAIL before you push. **It is not a sign-off.** Only the owner verifies, and only the owner sets the "Owner confirmed" and "Owner verified" columns below. Developers and AI assistants always add new rows as `Pending`.

## How to update this file (end of every session)

1. Add one row to **Session index** for your session (use the `user_time` id, for example `alex_2026-10-01_1430`, and link the log).
2. Add every decision made outside the docs to the **Decisions register** with the next `D-` number, and set `Recorded in` to where it now lives (a spec section, or the session log until a spec is updated).
3. Add one row to **Spec change log** for each spec you edited.
4. Refresh **Current state** and **Open questions and blockers**.
5. Run the docs check (`python scripts/verify_docs.py --stamp`) and commit this file with your work. Never mark anything as owner confirmed or verified.

## Current state

- **Phase:** specification is written. The front end is built as a clickable app on demo data in `apps/web` (as of 2026-10-01); the backend has not started.
- **Branches:** `dev` is the default branch and where everyone works. The owner promotes `dev` to `uat`, then `uat` to `main`. `main` and `uat` still hold the first commit until then.
- **Runtime:** the web app and API run locally on each machine. The database is Supabase (Postgres with pgvector). AI calls (Hunyuan, JEV) go to their services. Connection details are shared privately and never committed.
- **Backlog:** 51 tasks split across three personal backlogs (`docs/backlog/hongyi.md`, `joely.md`, `damien.md`) plus a generated central tracker (`docs/backlog/SOT.md`); E0-1 and E0-2 are in progress, none done. Every task has a plain-language Ask, a Needs-first list and subtasks. Each person edits only their own file and runs `python scripts/update_tracker.py`. Estimates were removed.
- **Timeline:** two weeks to the submission on 16 October 2026.
- **Team:** Hong Yi (hongyeeet, owner, 27 tasks), Joely (joelyhee, 14 tasks), Damien (chua-damien, 10 tasks and reviewer for E4-1 and E13-1 to E13-3), all with write access. The task-level split is in `docs/backlog/SOT.md`. All tables and values are created and loaded in epic E1 only.

## Decisions register

| ID | Date | Decision | Why | Recorded in | Owner confirmed |
|---|---|---|---|---|---|
| D-001 | 2026-09-28 | Build for Healthcare track Challenge 2, Scenario 2 (Type 2 diabetes, adults 45-65) | The team's chosen track | prd.md | Yes |
| D-002 | 2026-09-29 | Project name is Smart Health (replaces the placeholder Kaki) | Owner's choice | all specs | Yes |
| D-003 | 2026-09-28 | The doctor brief is the headline output and the patient sees exactly what the doctor sees | Useful in a 10-minute consult, no hidden AI conclusions | prd.md F12, memory.md 11 | Pending |
| D-004 | 2026-09-28 | No Hermes agent; own lightweight personalisation layer | Autonomy conflicts with "strictly bounded" | prd.md 7 | Pending |
| D-005 | 2026-09-29 | Front end is a mobile-first web app in a phone frame, not a store app | No store fees | architecture.md | Yes |
| D-006 | 2026-09-29 | Data comes only from the download manifest datasets and the GlucoBench link. Anything else needs the owner's OK | Owner's instruction | prd.md A10, rules.md 1b, data/README.md | Yes |
| D-007 | 2026-09-29 | Demo history beyond the real 14-day sprint is simulated from cited data and disclosed | No open dataset covers 60 days | prd.md A8, data plan workbook | Pending |
| D-008 | 2026-09-30 | JEV is OpenJev, a typed decision layer (yes/no, choice, score with confidence). It is not a memory governor. Which deployment option is undecided (task E0-12) | Verified against the OpenJev README | memory.md 5 | Yes |
| D-009 | 2026-09-30 | Nothing is "validated". Evidence statuses are observed, derived, inferred, reference_matched | Nothing has been clinically reviewed | memory.md 4, rules.md 15 | Yes |
| D-010 | 2026-09-30 | Standard naming: one `public` schema, layer shown in a layer map, `supersedes_id`, one table per job | Avoid parallel tables and prefixes | memory.md 1, schema.md 0b | Pending |
| D-011 | 2026-09-30 | Meal photos and text are analysed by the LLM for macros, stored as estimates until the user confirms. Glucose response is always measured | Lets local dishes be logged | memory.md 9, rules.md 13 | Yes |
| D-012 | 2026-09-30 | Security is demo-grade. Per-user row-level security, consent-scoped retrieval, classification and retention are deferred. The clinical safety path is never deferred | Owner's instruction | memory.md 13, prd.md A12 | Yes |
| D-013 | 2026-09-30 | The database is Supabase. The app and API run locally. Row-level security is turned on with no policies, so the public key cannot read or write tables, and only the backend connects | Owner's instruction, plus a minimal guard for a shared database | architecture.md, prd.md A13 | Pending |
| D-014 | 2026-09-30 | Branches: `dev` (default, team works here), `uat`, `main`. Everyone may commit straight to `dev`; only the owner promotes to `uat` and `main`. Hooks block commits and pushes to `uat` and `main` | Best practice with a small team | HANDOVER.md 3, rules.md | Yes |
| D-015 | 2026-09-30 | Session logs are named `<user>_<YYYY-MM-DD_HHMM>` and this file consolidates them | Owner's instruction | HANDOVER.md, this file | Yes |
| D-016 | 2026-09-30 | GitHub cannot protect branches on a private free-plan repo, so dev-only working is enforced by the default branch, the hooks and convention | GitHub plan limit | HANDOVER.md 3 | Pending |
| D-017 | 2026-09-30 | HANDOVER.md is written only for the AI assistant. It contains no copy-paste prompt and no human-facing steps; the owner gives developers the start prompt separately | Owner's instruction | HANDOVER.md | Yes |
| D-018 | 2026-09-30 | Only the owner verifies UAT and production readiness, promotes `dev` to `uat` and `main`, and marks items owner confirmed or verified. Developers and AI assistants never do. The docs check script is an automatic consistency check only | Owner's instruction | HANDOVER.md 3, rules.md, this file | Yes |
| D-019 | 2026-09-30 | Each developer starts with one first prompt that clones the repo in Claude Code, checks out `dev`, sets the hooks and starts the handover. The prompt is kept by the owner, not in the repo | Owner's instruction | HANDOVER.md 2 (Step 0) | Yes |
| D-020 | 2026-10-01 | Workload split by epic: Hong Yi E0, E3, E4, E5, E9, E13, E16, E17, E22; Joely E1, E6, E7, E11, E18, E19; Damien E2, E8, E10, E12, E14, E15; E20 Hong Yi and Joely; E21 team. Refined at task level by D-023 | Owner's assignment | SOT.md | Yes |
| D-021 | 2026-10-01 | Damien is the Reviewer for E4-1 and E13-1 to E13-3. A task with a Reviewer goes to `in review` and only the Reviewer or the owner moves it to done (the Reviewer may set Status and Note of the task they review). New status `in review`. Promotion to uat and main stays owner-only (D-018) | Owner's instruction | personal backlogs, HANDOVER.md, rules.md | Yes |
| D-022 | 2026-10-01 | Estimates (sizes and days) are removed from the backlog; there are two weeks to deliver. Each task has a plain-language Ask | Owner's instruction | personal backlogs | Yes |
| D-023 | 2026-10-01 | The backlog is consolidated from 118 to 51 tasks (similar work merged, for example all ingestion into E1-4) and split into one backlog per person plus a generated central tracker, `SOT.md`. Each person edits only their own file; `scripts/update_tracker.py` regenerates the tracker and each person's blocker check | Owner's instruction | docs/backlog/, HANDOVER.md | Yes |
| D-024 | 2026-10-01 | All tables, views, reference data and demo data are created and loaded in epic E1 only. Joely creates Raw, Bronze, Silver and reference tables and loads every value (E1-1, E1-2, E1-4); Hong Yi creates the Gold (JEV and memory) and operations tables and views (E1-3). Later tasks only read and write rows | Owner's instruction | rules.md 3, schema.md 0b, details/e1-data-foundation.md | Yes |
| D-025 | 2026-10-01 | Epic E0 reduces to E0-1, a hardcoded visual mockup (no logic, no backend), assigned to Hong Yi. Onboarding (E2) stays with Damien and uses medical domain knowledge for past illnesses and history | Owner's instruction | mockup-prompt.md, hongyi.md, damien.md | Yes |
| D-026 | 2026-10-01 | E0-2 (app skeleton and design kit) and E0-3 (AI services, including the JEV option) were missing from the owner's pasted list and were kept under Hong Yi because most tasks depend on them. E1-5 is provisionally Joely. Leads for team tasks are provisional: E21-1 Damien, E21-2 Joely, E21-3 Hong Yi, E20-1 Hong Yi, E20-2 Joely | Assistant's assumption, to confirm | SOT.md notes | Pending |
| D-027 | 2026-10-01 | Three Silver columns that point at Gold tables (`symptom_checkins.triggered_by_flag_id`, `appointments.brief_id`, `doctor_questions.brief_id`) are created as plain uuid columns in E1-2 and their foreign keys are added at the end of E1-3, so Silver and Gold do not wait on each other. JEV has no tables of its own; its calls are logged in `agent_steps` | Assistant's fix for a circular dependency found while drawing the data flow | data-flow.md 6, details/e1-data-foundation.md | Pending |
| D-028 | 2026-10-01 | The web app was first built in `apps/web` (since D-034 that folder is the production app and the first build is `apps/mock`) (Vite, React, TypeScript, React Router, Tailwind v4 on CSS-variable tokens, `motion`, TanStack Query, Zustand). It is both the mockup and the main app: screens call hooks, hooks call a repository interface, a mock implements it now and the real API later | Owner: one app, not a throwaway mockup | architecture.md, apps/web/design.md | Pending |
| D-029 | 2026-10-01 | New look: deep pine green on warm ivory with a brass accent, Atkinson Hyperlegible plus Newsreader for titles and numbers, Phosphor icons, no emoji. The old teal is retired | Owner wanted a high-class look that is not generic | docs/specs/design.md | Pending |
| D-030 | 2026-10-01 | A Demo panel outside the phone holds prototype controls (dark mode, text size, simulate a low reading or a sync, jump to a screen). It is removed after the owner vets it | E0-1 says no simulator panel; owner asked to add first and vet | hongyi.md E0-1 | Pending |
| D-031 | 2026-10-01 | Screens added beyond the reference so every feature F1 to F18 appears: eligibility, chat onboarding, add medicine by hand, sensor sprint, notifications, plan an appointment, data and account, edit or delete an entry, the targeted check-in card and the high-salt swap card | Owner: all features must be in the app | apps/web/src/app/routeIds.ts | Pending |
| D-032 | 2026-10-01 | `reference/` (the three design exports) is git-ignored; the owner deletes it later | Owner's instruction | .gitignore | Yes |
| D-033 | 2026-10-01 | The demo scan uses Clarithromycin against the demo patient's Atorvastatin to show the interaction sheet. Demo data only; needs the owner's OK and a check against the cited reference data when E6-1 loads it | A believable demo using a well known interaction | session log hongyi_2026-10-01_1143 | Pending |
| D-034 | 2026-10-01 | Two apps: `apps/mock` is the clickable mock version (every screen, demo data, Demo panel). `apps/web` is the production app: the same shell, design system and data layer with no screens, a `NotWired` http data layer, and placeholders for every route in the registry. Real data, models and analysis are connected in `apps/web`. Replaces the single-app part of D-028 | Owner: keep the mock as a reference and build production separately | architecture.md, README.md, apps/*/design.md | Pending |

## Session index

| Session | Developer | Date | Tasks | Summary | Decisions | Owner verified |
|---|---|---|---|---|---|---|
| setup (no log) | hongyeeet with Claude | 2026-09-28 to 2026-10-01 | none (planning) | Wrote the PRD, architecture, flow, schema, design, rules, memory design, data plan, mockup prompt, handover, repo layout and branches; consolidated and split the backlog into three personal backlogs and a tracker | D-001 to D-027 | Pending |
| [hongyi_2026-10-01_1143](sessions/hongyi_2026-10-01_1143.md) | Hong Yi with Claude | 2026-10-01 | E0-1, E0-2 (both in progress) | Built the whole front end in `apps/web`: design tokens, UI kit, charts, mock data layer, 40 screens and 6 sheets, A4 brief, generated screen index, design.md. Specs updated for the new look and folder | D-028 to D-034 | Pending |

## Spec change log

| Date | Document | Change | Source |
|---|---|---|---|
| 2026-09-30 | docs/specs/memory.md | New: standard names, layers, evidence model, JEV decision layer, Memory Service, meal analysis | D-008 to D-012 |
| 2026-09-30 | docs/specs/schema.md | Layer map, evidence and relationship enums, `ingestion_events`, `meal_analyses`, `devices`, `health_goals`, four views, consistency rules 17 to 20 | D-009 to D-011 |
| 2026-09-30 | docs/specs/architecture.md | Layers, Memory Service and JEV in the harness, meal analysis flow, repo layout | D-008, D-010, D-013 |
| 2026-09-30 | docs/specs/prd.md | Assumptions A11 to A13, LLM macros in F6, evidence line in F16 | D-011 to D-013 |
| 2026-09-30 | docs/specs/rules.md | Rules 13 to 15, branch rule, handover rule | D-009, D-011, D-014 |
| 2026-09-30 | docs/specs/flow.md, design.md | Meal analysis events, Estimated badge | D-011 |
| 2026-09-30 | docs/backlog/backlog.md | Tasks E0-12, E1-13 to E1-15, E16-6, E17-5; E7-2 rewritten | D-008, D-011 |
| 2026-09-30 | docs/handover/HANDOVER.md | Rewritten as AI-only: removed the start prompt and the human section, renumbered sections | D-017 |
| 2026-09-30 | docs/handover/HANDOVER.md, docs/specs/rules.md, this file | Owner-only verification and promotion; the script is a docs check, not a sign-off; owner-confirmed columns | D-018 |
| 2026-09-30 | docs/handover/HANDOVER.md | Step 0 lets the AI set the hooks when the first prompt says to set the repo up | D-019 |
| 2026-10-01 | docs/backlog/backlog.md, docs/handover/HANDOVER.md, docs/specs/rules.md, this file | Owners and reviewers assigned, sizes removed, plain-language Ask lines, `in review` status | D-020 to D-022 |
| 2026-10-01 | docs/backlog/ (SOT.md, hongyi.md, joely.md, damien.md, details/), scripts/update_tracker.py, scripts/verify_docs.py | Old backlog.md retired; 51 tasks in three personal backlogs, generated tracker, E1 detail file; docs check updated | D-023 to D-026 |
| 2026-10-01 | docs/specs/data-flow.md (new), docs/backlog/details/e1-data-foundation.md, joely.md, hongyi.md, README.md, HANDOVER.md | One-page Bronze, Silver, Gold and JEV flow with table build order; Silver-to-Gold foreign keys deferred to the end of E1-3 | D-027 |
| 2026-10-01 | docs/specs/rules.md, schema.md, architecture.md, prd.md, README.md, HANDOVER.md, PR template | New rule that tables and reference data are created only in E1; schema ownership note; links and task ids (E0-9 and E0-12 are now E0-3) updated | D-023, D-024 |
| 2026-10-01 | docs/specs/design.md | Palette, typeface, icons and motion updated for the new look; points to apps/web/design.md | D-029 |
| 2026-10-01 | docs/specs/architecture.md, README.md | App folders `apps/mock` and `apps/web`; front-end, charts and i18n rows; status line | D-028, D-034 |

## Open questions and blockers

- **Demo panel (D-030):** the owner vets it, then it is removed. Also confirm D-033 (the demo interaction pair).
- **Front end gaps:** only a few strings are wrapped for translation; Malay and Tamil are empty; the iPad layout and touch gestures are untested on a real device.
- **E0-3:** choose the AI provider and gateway settings, and the JEV deployment (hosted OpenJev, small CPU models, self-hosted, or only the Hunyuan fallback). Not decided yet.
- **Confirm the assumptions in D-026:** E0-2 and E0-3 stay with Hong Yi, E1-5 owner, leads for E20 and E21 tasks.
- **Workload:** Damien has almost nothing ready until E0-2 and E1-2 are done, and Hong Yi carries about half the effort. See the notes in `docs/backlog/SOT.md` for rebalancing options.
- **Supabase:** the project is still named `smart-health-backlog`. The owner renames it to `smart-health` in the Supabase dashboard. Storage for photos and exports: Supabase Storage is the default unless the owner says otherwise.
- **Needs the owner's OK** (outside the cited data): clinical thresholds and screening intervals, supplement and TCM interaction data, medication label photos for testing, lifestyle guidance text, a Mi Watch export.
