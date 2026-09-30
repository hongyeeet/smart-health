# Project memory

The one place that consolidates the state of the project: what is decided, what has changed, and what is open. Every AI assistant and developer reads it at the start of a session and updates it at the end. It sits above the per-session logs: logs hold the detail, this file holds the summary and points to them.

> Not to be confused with `docs/specs/memory.md`, which describes how the *app* stores what it learns about a patient.

**Last verification:** 2026-09-30 12:11: PASS (21 of 21 checks passed)

To verify, run `python scripts/verify_docs.py --stamp`. It checks links, stale names, secrets, backlog integrity, the schema layer map, that every session log is listed here, and the dev-only hooks. Fix any FAIL before you push.

## How to update this file (end of every session)

1. Add one row to **Session index** for your session (use the `user_time` id, for example `alex_2026-10-01_1430`, and link the log).
2. Add every decision made outside the docs to the **Decisions register** with the next `D-` number, and set `Recorded in` to where it now lives (a spec section, or the session log until a spec is updated).
3. Add one row to **Spec change log** for each spec you edited.
4. Refresh **Current state** and **Open questions and blockers**.
5. Run `python scripts/verify_docs.py --stamp` and commit this file with your work.

## Current state

- **Phase:** specification is written; development has not started (as of 2026-09-30).
- **Branches:** `dev` is the default branch and where everyone works. The owner promotes `dev` to `uat`, then `uat` to `main`. `main` and `uat` still hold the first commit until then.
- **Runtime:** the web app and API run locally on each machine. The database is Supabase (Postgres with pgvector). AI calls (Hunyuan, JEV) go to their services. Connection details are shared privately and never committed.
- **Backlog:** 118 tasks in `docs/backlog/backlog.md`, none started, none assigned yet.
- **Team:** hongyeeet (owner), chua-damien, joelyhee, all with write access.

## Decisions register

| ID | Date | Decision | Why | Recorded in | Verified |
|---|---|---|---|---|---|
| D-001 | 2026-09-28 | Build for Healthcare track Challenge 2, Scenario 2 (Type 2 diabetes, adults 45-65) | The team's chosen track | prd.md | Yes |
| D-002 | 2026-09-29 | Project name is Smart Health (replaces the placeholder Kaki) | Owner's choice | all specs | Yes |
| D-003 | 2026-09-28 | The doctor brief is the headline output and the patient sees exactly what the doctor sees | Useful in a 10-minute consult, no hidden AI conclusions | prd.md F12, memory.md 11 | Yes |
| D-004 | 2026-09-28 | No Hermes agent; own lightweight personalisation layer | Autonomy conflicts with "strictly bounded" | prd.md 7 | Yes |
| D-005 | 2026-09-29 | Front end is a mobile-first web app in a phone frame, not a store app | No store fees | architecture.md | Yes |
| D-006 | 2026-09-29 | Data comes only from the download manifest datasets and the GlucoBench link. Anything else needs the owner's OK | Owner's instruction | prd.md A10, rules.md 1b, data/README.md | Yes |
| D-007 | 2026-09-29 | Demo history beyond the real 14-day sprint is simulated from cited data and disclosed | No open dataset covers 60 days | prd.md A8, data plan workbook | Yes |
| D-008 | 2026-09-30 | JEV is OpenJev, a typed decision layer (yes/no, choice, score with confidence). It is not a memory governor. Which deployment option is undecided (task E0-12) | Verified against the OpenJev README | memory.md 5 | Yes |
| D-009 | 2026-09-30 | Nothing is "validated". Evidence statuses are observed, derived, inferred, reference_matched | Nothing has been clinically reviewed | memory.md 4, rules.md 15 | Yes |
| D-010 | 2026-09-30 | Standard naming: one `public` schema, layer shown in a layer map, `supersedes_id`, one table per job | Avoid parallel tables and prefixes | memory.md 1, schema.md 0b | Yes |
| D-011 | 2026-09-30 | Meal photos and text are analysed by the LLM for macros, stored as estimates until the user confirms. Glucose response is always measured | Lets local dishes be logged | memory.md 9, rules.md 13 | Yes |
| D-012 | 2026-09-30 | Security is demo-grade. Per-user row-level security, consent-scoped retrieval, classification and retention are deferred. The clinical safety path is never deferred | Owner's instruction | memory.md 13, prd.md A12 | Yes |
| D-013 | 2026-09-30 | The database is Supabase. The app and API run locally. Row-level security is turned on with no policies, so the public key cannot read or write tables, and only the backend connects | Owner's instruction, plus a minimal guard for a shared database | architecture.md, prd.md A13 | Yes |
| D-014 | 2026-09-30 | Branches: `dev` (default, team works here), `uat`, `main`. Everyone may commit straight to `dev`; only the owner promotes to `uat` and `main`. Hooks block commits and pushes to `uat` and `main` | Best practice with a small team | HANDOVER.md 4, rules.md | Yes |
| D-015 | 2026-09-30 | Session logs are named `<user>_<YYYY-MM-DD_HHMM>` and this file consolidates them | Owner's instruction | HANDOVER.md, this file | Yes |
| D-016 | 2026-09-30 | GitHub cannot protect branches on a private free-plan repo, so dev-only working is enforced by the default branch, the hooks and convention | GitHub plan limit | HANDOVER.md 4 | Yes |

## Session index

| Session | Developer | Date | Tasks | Summary | Decisions | Verified |
|---|---|---|---|---|---|---|
| setup (no log) | hongyeeet with Claude | 2026-09-28 to 2026-09-30 | none (planning) | Wrote the PRD, architecture, flow, schema, design, rules, memory design, data plan, backlog, mockup prompt, handover, repo layout and branches | D-001 to D-016 | Yes |

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

## Open questions and blockers

- **E0-12:** choose the JEV deployment (hosted OpenJev, small CPU models, self-hosted, or only the Hunyuan fallback). Not decided yet.
- **E0-9:** choose the AI provider and gateway settings.
- **Supabase:** the project is still named `smart-health-backlog`. The owner renames it to `smart-health` in the Supabase dashboard. Storage for photos and exports: Supabase Storage is the default unless the owner says otherwise.
- **Workload split:** the owner assigns owners in the backlog.
- **Needs the owner's OK** (outside the cited data): clinical thresholds and screening intervals, supplement and TCM interaction data, medication label photos for testing, lifestyle guidance text, a Mi Watch export.
