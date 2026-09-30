# Start here: developer and AI handover

For each of the three developers and the AI coding assistant working with them (CodeBuddy, WorkBuddy or any other). Every session follows the same loop: **read, ask, find the task, build, log, hand over.**

## 1. The short version

- **Product:** Smart Health is an AI companion for adults with Type 2 diabetes. It learns each person from their food, glucose, watch, exercise and medication data, supports them daily, and produces a doctor brief. It explains, organises and reminds. It never advises on medication and never diagnoses.
- **Work on the `dev` branch** (or a `feature/<task-id>-<name>` branch cut from `dev`). Never work directly on `uat` or `main`. See section 4.
- **The plan is `docs/backlog/backlog.md`.** Tasks have IDs like `E9-2` and subtasks with success criteria.
- **Every session leaves two records:** the updated backlog, and a session log in `docs/handover/sessions/`.

## 2. Copy-paste start prompt for your AI

```
You're helping me on the Smart Health repo. We only develop on the dev branch, never on uat or main: run "git checkout dev" and "git pull" first.
Then follow docs/handover/HANDOVER.md: read every document it lists and tell me in about 10 lines what you understood, then ask me what task I'm assigned this session.
Once I answer, find it in docs/backlog/backlog.md, check what it depends on, propose a plan, and guide me one subtask at a time.
Keep a session log in docs/handover/sessions/ as we go, including any decision we make that isn't in the docs.
```

**One-time setup per clone (each developer runs this once):** `git config core.hooksPath .githooks`. It blocks commits and pushes to `uat` and `main`.

## 3. What the AI does, step by step

### Step 0. Set up the session
1. Run `git status` and `git branch --show-current`. If you are on `uat` or `main`, stop and switch to `dev` (`git checkout dev`). Run `git pull` so you start from the latest. Also run `git config core.hooksPath`: if it does not print `.githooks`, ask the user to run `git config core.hooksPath .githooks` (do not change git settings yourself).
2. Ask the user for their first name in lowercase with no spaces. This is `user`.
3. Take the current local time as `YYYY-MM-DD_HHMM`. The session id is `user_time`, for example `alex_2026-10-01_1430`.
4. Copy `docs/handover/session-log-template.md` to `docs/handover/sessions/<user_time>.md` now, not at the end. Fill it in as you go so nothing is lost if the session stops suddenly.

### Step 1. Read the required documents
Read these in order. Do not skip any.

| Order | File | What to take from it |
|---|---|---|
| 1 | `README.md` | Repository layout and branches |
| 2 | `docs/specs/prd.md` | The product, users, features F1-F18 with acceptance criteria, safety principles, assumptions A1-A13 |
| 3 | `docs/specs/architecture.md` | Tech stack, trust boundaries, folder layout, data flows. The "Platform decisions" note at the top overrides anything below it |
| 4 | `docs/specs/memory.md` | Standard terms and names, Bronze/Silver/Gold layers, evidence statuses, the JEV decision layer, the Memory Service, meal analysis |
| 5 | `docs/specs/schema.md` | Tables, the layer map, data consistency rules |
| 6 | `docs/specs/rules.md` | Safety rules that are never broken, the data source policy, coding conventions, definition of done |
| 7 | `docs/specs/flow.md` | User journeys, screens, the event names, the demo script |
| 8 | `docs/specs/design.md` | Colours, type, components, accessibility |
| 9 | `data/README.md` and `data/plan/smart_health_data_plan.xlsx` | Which datasets are allowed, what is still missing, what strengthens the AI |
| 10 | `docs/backlog/backlog.md` | All tasks, their status and owners |

Then tell the user in about ten lines: what the product is, the hard rules (no medication advice, no diagnosis, only the cited data sources, nothing is "validated", AI estimates are labelled), which branch you are on, and where the backlog stands.

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
Whenever a decision is made that is not in the docs, or that changes them, add it straight away to "Decisions made outside the docs" in the session log: what was decided, why, the alternatives, who decided, and which document needs updating. If the user agrees and the change is small, update the spec in the same pull request and say so. If it is large or affects others, leave a `TODO(decision)` and tell the owner.

### Step 5. End the session
1. Update `docs/backlog/backlog.md` for every task touched: tick finished subtasks, set `Status:` (`backlog`, `in progress`, `blocked` or `done`), put your name in `Owner:` if unassigned, and write a one-line `Note:` for what is left or what blocks you. Tick the task's own box only when all its subtasks are done.
2. Finish the session log: files changed, tables and endpoints touched, tests run and results, decisions, open questions, next steps.
3. Commit with `type(task-id): summary` (for example `feat(E9-2): baseline and momentum flags`).
4. Push your branch and open a pull request **into `dev`** using the template. List the tasks you moved.
5. Tell the user what was done and what comes next. Never merge into `uat` or `main`.

## 4. Branches and promotion

| Branch | Purpose | Who moves code in |
|---|---|---|
| `dev` | Where the team works. Integration of everyone's changes | All developers, by pull request from `feature/<task-id>-<name>` branches (or small direct commits if the team agrees) |
| `uat` | Acceptance testing of what is in `dev` | The owner only, by promoting `dev` into `uat` after a check that the demo script works |
| `main` | Production: the version that is submitted and demoed | The owner only, by promoting `uat` into `main` after UAT passes. Tag releases here |

Rules: nothing goes directly into `uat` or `main`. Never force-push. Promotion is a pull request from the previous branch (`dev` to `uat`, then `uat` to `main`). A fix found in `uat` or `main` is made on `dev` and promoted again. GitHub does not offer automatic branch protection on a private repository on the free plan (it becomes available if the repo is made public, which is planned for the submission, or with GitHub Pro), so for now these rules are enforced by convention and the pull request template.

## 5. For the developer (human)

1. Clone the repo and run `git checkout dev` and `git pull`.
2. Open your AI assistant in the repository root and paste the start prompt from section 2.
3. Answer its questions, review its plan before it builds, and check each subtask against its success criterion.
4. At the end, read the session log it wrote. Fix anything wrong, then open the pull request into `dev`.
