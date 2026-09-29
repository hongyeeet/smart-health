# Smart Health

An AI health companion for adults with Type 2 diabetes. It learns each person from their own food, watch, glucose and exercise data, helps them every day (medication understanding, reminders, tracking), and turns the weeks between visits into a clear, evidence-backed brief for their doctor. It explains, organises and reminds. It never advises on medication and never diagnoses.

Built for the AI CAN DO IT Tencent Cloud Hackathon Singapore 2026, Healthcare track (NTU LKC Medicine), Challenge 2: *AI Healthier Every Day*, Scenario 2 (Type 2 diabetes self-care).

## Specs

| File | What it covers |
|---|---|
| [prd.md](prd.md) | What we are building and why: users, features F1-F18 with acceptance criteria, scope, data source policy |
| [architecture.md](architecture.md) | Tech stack, trust boundaries, folder structure, data flows, agent harness and memory |
| [flow.md](flow.md) | User journeys, screens, event logging, demo script |
| [schema.md](schema.md) | Database tables, columns, constraints, consistency rules |
| [design.md](design.md) | UI/UX system: colours, type, components, accessibility, doctor-brief style |
| [rules.md](rules.md) | Boundaries for AI coding agents: safety invariants, data source policy, error handling, definition of done |
| [backlog.md](backlog.md) | Task backlog: 22 epics (E2-E19 = features F1-F18), stories with success criteria, milestones, integration checkpoints, capacity check |

## Data

Data comes only from the datasets listed in the hackathon download manifest and the GlucoBench Kaggle dataset. See [data/smart_health_data_plan.xlsx](data/smart_health_data_plan.xlsx) (Use now / Still missing / Domain knowledge). Raw datasets are never committed: several carry licences (for example CGMacros is CC BY-NC-SA 4.0) and are large.

## Status

Specification phase. No application code yet.
