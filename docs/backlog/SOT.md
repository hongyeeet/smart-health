# Smart Health: central tracker

The single place to see where the project stands. **Everything between the generated markers is rewritten by `python scripts/update_tracker.py`. Do not edit it by hand.** Progress comes from the three personal backlogs: [Hong Yi](hongyi.md), [Joely](joely.md) and [Damien](damien.md). Each person edits only their own file, then runs the script.

How a task moves: `backlog`, then `in progress`, then `in review` (only if it has a Reviewer) or straight to `done`. A task is **ready** when everything in its "Needs first" list is done. Details for the data foundation are in [details/e1-data-foundation.md](details/e1-data-foundation.md). Only the owner promotes `dev` to `uat` and `main`.

The text in the notes block below is written by hand (by the owner or an AI assistant at the owner's request) and survives regeneration.

<!-- NOTES:START -->
### Allocation and workload (confirmed by the owner on 2026-10-01)

51 tasks. Effort is a relative measure carried over from the old size ratings (not a time estimate), so only the shares matter.

| Person | Tasks | Share of effort | Notes |
|---|---|---|---|
| Hong Yi | 27 | about 49% | Mockup, app skeleton, AI services, Gold tables, scan, explainer, doses, insights, brief, chat and memory, gates. Also the owner: verifies and promotes |
| Joely | 14 | about 35% | Raw, Bronze, Silver, reference and all value ingestion (E1), clash checker, logging, urgent alerts, languages, timeline and patterns |
| Damien | 10 | about 16% | Onboarding, food response, check-ins, nudges, recurring checks, doctor questions. Also reviews E4-1 and E13-1 to E13-3 (about another 10% of the total) |

Points to watch:

- **The critical path is E1 (Joely) and E0-2/E0-3 (Hong Yi).** E1-1, E1-2 and E1-4 are about 17 units of effort that almost every feature waits on. E0-2, E0-3 and E1-3 are about 6 for Hong Yi, on top of the mockup (E0-1).
- **Damien has almost nothing he can start** until E0-2 and E1-2 are done. Only E21-1 is free today. Joely's first tasks (E1-1, E1-2) and Hong Yi's E0-2 unblock him.
- **Hong Yi carries about half the effort and the review and promotion duties.** If the load needs to be lighter, the cleanest moves are E5-1 and E5-2 (doses and refills, Hong Yi to Damien: 45% / 35% / 20%), then E9-2 and E17-2 (screens): 43% / 35% / 22%.
- **Assumptions to confirm:** E0-2 and E0-3 stay with Hong Yi (they were missing from the pasted list); E1-5 is provisionally Joely; leads for the team tasks E21-1 (Damien), E21-2 (Joely), E21-3 (Hong Yi) and for E20-1 (Hong Yi) and E20-2 (Joely).
<!-- NOTES:END -->

<!-- GENERATED:START -->
## Progress

| | Tasks done | Subtasks ticked | Progress |
|---|---|---|---|
| **Whole project** | 0 of 51 | 2 of 254 | `[--------------------] 1%` |
| Hong Yi | 0 of 27 | 2 of 134 | `[--------------------] 1%` |
| Joely | 0 of 14 | 0 of 71 | `[--------------------] 0%` |
| Damien | 0 of 10 | 0 of 49 | `[--------------------] 0%` |

## Gates

| Gate | Status | Still waiting for |
|---|---|---|
| CP0 Gate 0: mockup and data ready | blocked | E0-1, E0-2, E1-4 |
| CP1 Gate 1: thin working slice | blocked | CP0, E3-2, E5-1, E7-2, E8-1, E11-1, E16-2 |
| CP2 Gate 2: all features and the brief | blocked | CP1, E13-3, E17-3, E19-2 |
| CP3 Gate 3: submission ready | blocked | CP2, E21-1, E21-2, E21-3 |

## Who can start now

Tasks whose **Needs first** are all done. Sorted by how many other tasks they unblock.

| Person | Ready now | Blocked | In progress or review | Done |
|---|---|---|---|---|
| Hong Yi | none | 25 | 2 | 0 |
| Joely | E1-2 (39), E1-1 (28), E11-1 (4), E21-2 (1) | 10 | 0 | 0 |
| Damien | E21-1 (1) | 9 | 0 | 0 |

The number in brackets is how many other tasks are waiting, directly or indirectly, on that task.

## All tasks

| ID | Task | Owner | Priority | State | Subtasks | Waiting for | Reviewer |
|---|---|---|---|---|---|---|---|
| E0-1 | Hardcoded mockup | Hong Yi | P0 | in progress | 1/3 | none |  |
| E0-2 | App skeleton and design kit | Hong Yi | P0 | in progress | 1/7 | none |  |
| E0-3 | AI services | Hong Yi | P0 | blocked | 0/4 | E0-2 |  |
| E1-1 | Raw and Bronze | Joely | P0 | ready | 0/4 | none |  |
| E1-2 | Silver and reference tables | Joely | P0 | ready | 0/5 | none |  |
| E1-3 | Gold and operations tables and views | Hong Yi | P0 | blocked | 0/5 | E1-2 |  |
| E1-4 | Ingestion | Joely | P0 | blocked | 0/6 | E1-1, E1-2 |  |
| E1-5 | Analysis data and baseline model | Joely | P1 | blocked | 0/2 | E1-4 |  |
| E2-1 | Onboarding flow | Damien | P0 | blocked | 0/10 | E0-2, E1-2 |  |
| E2-2 | Chat onboarding | Damien | P1 | blocked | 0/2 | E2-1, E16-1, E0-3 |  |
| E3-1 | Scan and read | Hong Yi | P0 | blocked | 0/9 | E0-2, E0-3 |  |
| E3-2 | Match, parse and save | Hong Yi | P0 | blocked | 0/9 | E3-1, E1-2, E1-4 |  |
| E3-3 | Accuracy report (needs OK) | Hong Yi | P1 | blocked | 0/1 | E3-1 |  |
| E4-1 | Medicine explainer | Hong Yi | P0 | blocked | 0/5 | E0-3, E1-4, E16-2 | Damien |
| E5-1 | Doses and reminders | Hong Yi | P0 | blocked | 0/9 | E0-2, E1-2 |  |
| E5-2 | Missed doses and refills | Hong Yi | P0 | blocked | 0/5 | E5-1 |  |
| E6-1 | Clash checker | Joely | P0 | blocked | 0/9 | E3-2, E1-4 |  |
| E7-1 | Quick logs | Joely | P0 | blocked | 0/4 | E0-2, E1-2 |  |
| E7-2 | Meal logging with AI macros | Joely | P0 | blocked | 0/6 | E0-3, E1-1, E1-2, E1-4 |  |
| E7-3 | Connected sources and log upkeep | Joely | P0 | blocked | 0/4 | E7-1, E1-4 |  |
| E8-1 | Sprint and meal response | Damien | P0 | blocked | 0/7 | E1-2, E1-4 |  |
| E8-2 | Food leaderboard | Damien | P0 | blocked | 0/4 | E8-1 |  |
| E9-1 | Daily totals, baseline and flags | Hong Yi | P0 | blocked | 0/6 | E1-3, E1-4 |  |
| E9-2 | Insights screen | Hong Yi | P0 | blocked | 0/2 | E9-1, E0-2 |  |
| E10-1 | Check-ins (needs OK) | Damien | P0 | blocked | 0/5 | E9-1 |  |
| E11-1 | Urgent alerts (needs OK) | Joely | P0 | ready | 0/9 | none |  |
| E12-1 | Nudge messages and learning (needs OK) | Damien | P0 | blocked | 0/4 | E9-1 |  |
| E12-2 | Nudge cards and food swaps | Damien | P0 | blocked | 0/2 | E12-1, E0-2 |  |
| E13-1 | Brief data and charts | Hong Yi | P0 | blocked | 0/5 | E1-4, E9-1 | Damien |
| E13-2 | Narrative and PDF | Hong Yi | P0 | blocked | 0/7 | E13-1, E0-3 | Damien |
| E13-3 | Brief screens and sharing | Hong Yi | P0 | blocked | 0/4 | E13-2 | Damien |
| E14-1 | Recurring checks and appointments (needs OK) | Damien | P1 | blocked | 0/7 | E1-2 |  |
| E15-1 | Doctor questions | Damien | P0 | blocked | 0/5 | E1-2, E0-2 |  |
| E16-1 | Chat pipeline and Memory Service | Hong Yi | P0 | blocked | 0/4 | E0-3, E1-2, E1-3 |  |
| E16-2 | Safety net and JEV decisions | Hong Yi | P0 | blocked | 0/7 | E16-1, E0-3 |  |
| E16-3 | Chat screen, helpers and chat memory | Hong Yi | P0 | blocked | 0/5 | E16-1, E0-2 |  |
| E17-1 | Memory and nightly reflection | Hong Yi | P0 | blocked | 0/10 | E1-3, E1-4, E16-1 |  |
| E17-2 | What it learned screen | Hong Yi | P0 | blocked | 0/2 | E17-1, E0-2 |  |
| E17-3 | Week 1 versus week 8 | Hong Yi | P0 | blocked | 0/1 | E17-1, E9-1 |  |
| E18-1 | Languages, audio and translation review | Joely | P0 | blocked | 0/7 | E0-2 |  |
| E19-1 | Timeline and Day view | Joely | P0 | blocked | 0/5 | E1-3, E1-4, E0-2 |  |
| E19-2 | Pattern finder and brief day traces | Joely | P0 | blocked | 0/4 | E19-1, E8-1 |  |
| E20-1 | Safety and engine tests | Hong Yi + Joely | P1 | blocked | 0/4 | E16-2, E9-1, E8-1 |  |
| E20-2 | Demo and device checks | Joely + Hong Yi | P1 | blocked | 0/4 | CP1 |  |
| E21-1 | Submission text and visuals | Damien (team task) | P0 | ready | 0/3 | none |  |
| E21-2 | Build proof and video | Joely (team task) | P0 | ready | 0/2 | none |  |
| E21-3 | Public-ready repo and rehearsals | Hong Yi (team task) | P0 | blocked | 0/4 | E0-2 |  |
| CP0 | Gate 0: mockup and data ready | Hong Yi | P0 | blocked | 0/4 | E0-1, E0-2, E1-4 |  |
| CP1 | Gate 1: thin working slice | Hong Yi | P0 | blocked | 0/6 | CP0, E3-2, E5-1, E7-2, E8-1, E11-1, E16-2 |  |
| CP2 | Gate 2: all features and the brief | Hong Yi | P0 | blocked | 0/4 | CP1, E13-3, E17-3, E19-2 |  |
| CP3 | Gate 3: submission ready | Hong Yi | P0 | blocked | 0/2 | CP2, E21-1, E21-2, E21-3 |  |

## Open flags

- **E0-2** (Hong Yi): Missing from your pasted list; kept because most tasks depend on it. Confirm it stays with Hong Yi.
- **E0-3** (Hong Yi): Missing from your pasted list; kept because chat, scanning, meal logging and the brief depend on it. Confirm it stays with Hong Yi.
- **E1-5** (Joely): Owner was 'to decide' in your list. Provisionally Joely (data work); change if you prefer.
- **E20-1** (Hong Yi): Your list said Hong Yi and Joely for E20. Hong Yi leads this one; Joely leads E20-2.
- **E21-1** (Damien): Your list said the team. Damien is the lead here; everyone contributes. Change the lead if you prefer.
- **E21-2** (Joely): Team task. Joely is the lead here; everyone contributes. Change the lead if you prefer.
- **E21-3** (Hong Yi): Team task. Hong Yi is the lead here; everyone contributes. Change the lead if you prefer.

## Needs the owner's OK before work starts

- E3-3 Accuracy report (Hong Yi)
- E10-1 Check-ins (Damien)
- E11-1 Urgent alerts (Joely)
- E12-1 Nudge messages and learning (Damien)
- E14-1 Recurring checks and appointments (Damien)

## Consistency warnings

- None.
<!-- GENERATED:END -->
