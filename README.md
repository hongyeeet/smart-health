# Smart Health

An AI health companion for adults with Type 2 diabetes. It learns each person from their own food, watch, glucose and exercise data, helps them every day (medication understanding, reminders, tracking), and turns the weeks between visits into a clear, evidence-backed brief for their doctor. It explains, organises and reminds. It never advises on medication and never diagnoses.

Built for the AI CAN DO IT Tencent Cloud Hackathon Singapore 2026, Healthcare track (NTU LKC Medicine), Challenge 2: *AI Healthier Every Day*, Scenario 2 (Type 2 diabetes self-care).

## Start here

New to the repo, human or AI assistant? Read **[docs/handover/HANDOVER.md](docs/handover/HANDOVER.md)** first. It says what to read, what to ask, how to find your task, and how to leave a record of your session.

## Repository layout

```
README.md
docs/                     all documents
  specs/                  prd, architecture, flow, schema, design, rules, memory
  backlog/backlog.md      the live task list
  handover/               HANDOVER.md (start here), session-log-template.md, sessions/
  mockup/                 prompt and outputs for the design mockup
  reference/              superseded starting templates
data/                     all data (see data/README.md)
  plan/                   the datasets plan workbook
  raw/  processed/        downloads and importer output (gitignored)
  reference/  knowledge/  demo/
.github/                  pull request template, CODEOWNERS
scripts/                  verify_docs.py checks the documents; more scripts arrive with development
apps/  services/          created when development starts (planned layout: docs/specs/architecture.md section 3)
```

## Documents

| File | What it covers |
|---|---|
| [docs/specs/prd.md](docs/specs/prd.md) | What we are building and why: users, features F1-F18 with acceptance criteria, scope, assumptions |
| [docs/specs/architecture.md](docs/specs/architecture.md) | Tech stack, trust boundaries, folder structure, data flows, agent harness |
| [docs/specs/memory.md](docs/specs/memory.md) | Standard names, data layers, memory planes, evidence model, the JEV decision layer, Memory Service, meal analysis |
| [docs/specs/schema.md](docs/specs/schema.md) | Database tables, layer map, consistency rules |
| [docs/specs/flow.md](docs/specs/flow.md) | User journeys, screens, event logging, demo script |
| [docs/specs/design.md](docs/specs/design.md) | UI/UX system: colours, type, components, accessibility |
| [docs/specs/rules.md](docs/specs/rules.md) | Boundaries for AI coding agents: safety rules, data source policy, definition of done |
| [docs/backlog/backlog.md](docs/backlog/backlog.md) | The live task list: epics E0-E22 (E2-E19 are features F1-F18), tasks and subtasks with owner, status and completion boxes |
| [docs/handover/project-memory.md](docs/handover/project-memory.md) | Team memory: current state, decisions register, session index, spec change log, open questions. Read at the start of a session, update at the end. (Not the same as `docs/specs/memory.md`, which is the app's memory design) |
| [docs/mockup/mockup-prompt.md](docs/mockup/mockup-prompt.md) | The prompt for the interactive design mockup |
| [docs/reference/](docs/reference/) | The two starting-template documents that `memory.md` and `schema.md` grew from |

## Branches

| Branch | Purpose |
|---|---|
| `dev` | Where the team works. Commit straight to `dev` (small commits, `git pull --rebase origin dev` before pushing); feature branches are optional |
| `uat` | Acceptance testing. The owner promotes `dev` into `uat` |
| `main` | Production, the submitted and demoed version. The owner promotes `uat` into `main` |

`dev` is the default branch, so a fresh clone lands on it. Never commit directly to `uat` or `main`. After cloning, run once: `git config core.hooksPath .githooks` (blocks commits and pushes to `uat` and `main`). Details: [docs/handover/HANDOVER.md](docs/handover/HANDOVER.md) section 3.

## Data

Data comes only from the datasets in the hackathon download manifest and the GlucoBench Kaggle dataset. See [data/README.md](data/README.md) and [data/plan/smart_health_data_plan.xlsx](data/plan/smart_health_data_plan.xlsx). Raw datasets are never committed: several carry licences (for example CGMacros is CC BY-NC-SA 4.0) and are large.

## Runtime

The web app and API run locally on each developer's machine. The database is Supabase (Postgres with pgvector), one shared project, reached through a private `.env` that is never committed. The other outbound calls are the AI APIs.

## Status

Specification phase. No application code yet.
