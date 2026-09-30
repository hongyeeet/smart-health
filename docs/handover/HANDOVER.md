# AI handover: how to work in this repository

This document is for the AI coding assistant (CodeBuddy, WorkBuddy or any other) working with a developer on Smart Health. "You" means the assistant. "The user" means the developer you are working with. Every session follows the same loop: **read, ask, find the task, build, log, hand over.**

## 1. The short version

- **Product:** Smart Health is an AI companion for adults with Type 2 diabetes. It learns each person from their food, glucose, watch, exercise and medication data, supports them daily, and produces a doctor brief. It explains, organises and reminds. It never advises on medication and never diagnoses.
- **Work on the `dev` branch.** Committing straight to `dev` is fine: commit small and often, run `git pull --rebase origin dev` before every push, never force-push. A `feature/<task-id>-<name>` branch is optional for bigger changes. Never work directly on `uat` or `main`. See section 3.
- **The plan is `docs/backlog/backlog.md`.** Tasks have IDs like `E9-2` and subtasks with success criteria.
- **Every session leaves three records:** the updated backlog, a session log in `docs/handover/sessions/`, and an updated `docs/handover/project-memory.md` (the one place that consolidates the state, decisions and session index).

## 2. What you do, step by step

### Step 0. Set up the session
1. Run `git status` and `git branch --show-current`. If you are on `uat` or `main`, stop and switch to `dev` (`git checkout dev`). Run `git pull` so you start from the latest. Check for a `.env` (copy `.env.example` when it exists and ask the owner for the Supabase details; never commit them). Also run `git config core.hooksPath`: if it does not print `.githooks`, ask the user to run `git config core.hooksPath .githooks` (do not change git settings yourself). The hooks block commits and pushes to `uat` and `main`.
2. Ask the user for their first name in lowercase with no spaces. This is `user`.
3. Take the current local time as `YYYY-MM-DD_HHMM`. The session id is `user_time`, for example `alex_2026-10-01_1430`.
4. Copy `docs/handover/session-log-template.md` to `docs/handover/sessions/<user_time>.md` now, not at the end. Fill it in as you go so nothing is lost if the session stops suddenly.

### Step 1. Read the required documents
Read these in order. Do not skip any.

| Order | File | What to take from it |
|---|---|---|
| 1 | `README.md` | Repository layout and branches |
| 2 | `docs/handover/project-memory.md` | Current state, the decisions register, the session index (what earlier sessions did), spec change log and open questions |
| 3 | `docs/specs/prd.md` | The product, users, features F1-F18 with acceptance criteria, safety principles, assumptions A1-A13 |
| 4 | `docs/specs/architecture.md` | Tech stack, trust boundaries, folder layout, data flows. The "Platform decisions" note at the top overrides anything below it |
| 5 | `docs/specs/memory.md` | Standard terms and names, Bronze/Silver/Gold layers, evidence statuses, the JEV decision layer, the Memory Service, meal analysis |
| 6 | `docs/specs/schema.md` | Tables, the layer map, data consistency rules |
| 7 | `docs/specs/rules.md` | Safety rules that are never broken, the data source policy, coding conventions, definition of done |
| 8 | `docs/specs/flow.md` | User journeys, screens, the event names, the demo script |
| 9 | `docs/specs/design.md` | Colours, type, components, accessibility |
| 10 | `data/README.md` and `data/plan/smart_health_data_plan.xlsx` | Which datasets are allowed, what is still missing, what strengthens the AI |
| 11 | `docs/backlog/backlog.md` | All tasks, their status and owners |
| 12 | The two most recent files in `docs/handover/sessions/` | What the last sessions changed and decided, so you do not repeat or contradict it |

Then tell the user in about ten lines: what the product is, what the last sessions did, the hard rules (no medication advice, no diagnosis, only the cited data sources, nothing is "validated", AI estimates are labelled), which branch you are on, and where the backlog stands.

If two documents disagree, do not guess. Stop and tell the user. The order of authority is: `rules.md` safety rules first, then `memory.md` and `schema.md`, then `architecture.md`, then `prd.md`, then `flow.md` and `design.md`. A decision recorded in a session log applies until the spec is updated.

### Step 2. Ask what the user is assigned
Ask exactly this, then wait:

> What task are you assigned this session, or what do you want to finish? Give me a task ID (like E9-2), a feature (like F8), an epic, or just describe it.

Do not start coding before the user answers.

### Step 3. Find the task and guide the user
1. **Match it in `docs/backlog/backlog.md`.** By task ID first. Otherwise by feature or epic (epics E2-E19 are features F1-F18, so E9 is F8). Otherwise search the backlog for keywords. If several tasks match, list them and ask which one. If none matches, offer to add a new task with the next free ID and subtasks, and record that as a decision in the session log.
2. **Show the task:** its subtasks, priority, size, `Depends on`, spec references, current Status and Owner.
3. **Check dependencies.** If something it depends on is not done, say so and offer three options: do the dependency first, stub it, or proceed with a written assumption.
4. **Read what the task points to:** the cited section of the specs, the tables it touches in `schema.md`, the events in `flow.md`, and the rules that apply.
5. **Propose a plan and wait for a yes.** For each subtask: the files to create or change, the tables and events involved, and how you will check its success criterion.
6. **Guide or build one subtask at a time.** After each one, check it against its criterion, tick it in `docs/backlog/backlog.md` (`- [ ]` becomes `- [x]`), and note it in the session log.
7. **Follow the rules while you build.** Keep names and identifiers out of prompts, use only the cited data sources, label AI estimates as estimates, use the standard names in `memory.md`, and emit the events listed in `flow.md`.
8. **Stop and ask** if a subtask needs something outside the documents: data from another source, clinical wording or thresholds, or a change to a safety rule. Mark it `NEEDS OK` and record it in the session log.

### Step 4. Record decisions as they happen
Whenever a decision is made that is not in the docs, or that changes them, add it straight away to "Decisions made outside the docs" in the session log: what was decided, why, the alternatives, who decided, and which document needs updating. If the user agrees and the change is small, update the spec in the same commit and say so. If it is large or affects others, leave a `TODO(decision)` and tell the owner.

### Step 5. End the session
1. Update `docs/backlog/backlog.md` for every task touched: tick finished subtasks, set `Status:` (`backlog`, `in progress`, `blocked` or `done`), put the user's name in `Owner:` if unassigned, and write a one-line `Note:` for what is left or what blocks them. Tick the task's own box only when all its subtasks are done.
2. Finish the session log: files changed, tables and endpoints touched, tests run and results, decisions, open questions, next steps.
3. Update `docs/handover/project-memory.md`: add your row to the session index, add every decision made outside the docs to the decisions register, add a row per spec you edited to the spec change log, and refresh current state and open questions.
4. Run `python scripts/verify_docs.py --stamp`. Fix every FAIL, then run it again. Paste the result line into the session log.
5. Commit with `type(task-id): summary` (for example `feat(E9-2): baseline and momentum flags`). Run `git pull --rebase origin dev`, then `git push origin dev`. (If you used a `feature/` branch, push it and open a pull request into `dev` with the template instead.)
6. Tell the user what was done and what comes next. Never push to `uat` or `main`.

## 3. Branches and promotion

| Branch | Purpose | Who moves code in |
|---|---|---|
| `dev` | Where the team works. Integration of everyone's changes | All developers commit straight to `dev` (small commits, `git pull --rebase origin dev` before pushing). `feature/<task-id>-<name>` branches with a pull request are optional |
| `uat` | Acceptance testing of what is in `dev` | The owner only, by promoting `dev` into `uat` after a check that the demo script works |
| `main` | Production: the version that is submitted and demoed | The owner only, by promoting `uat` into `main` after UAT passes. Tag releases here |

Rules: nothing goes directly into `uat` or `main`. Never force-push. Promotion is a pull request from the previous branch (`dev` to `uat`, then `uat` to `main`). A fix found in `uat` or `main` is made on `dev` and promoted again. GitHub does not offer automatic branch protection on a private repository on the free plan (it becomes available if the repo is made public, which is planned for the submission, or with GitHub Pro), so for now these rules are enforced by the hooks, the default branch and convention.
