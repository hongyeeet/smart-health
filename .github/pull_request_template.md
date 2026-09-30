## What this changes
<!-- One or two sentences. -->

## Backlog tasks
<!-- IDs and new status, for example: E9-2 in progress, E9-1 done -->

## Target branch
- [ ] This PR goes into `dev`. (Only the owner opens `dev` to `uat` and `uat` to `main` promotions.)

## Checklist
- [ ] `docs/backlog/backlog.md` is updated (subtasks ticked, Status, Owner, Note)
- [ ] Session log added in `docs/handover/sessions/` (`<user>_<YYYY-MM-DD_HHMM>.md`)
- [ ] `docs/handover/project-memory.md` updated (session index, decisions, spec change log)
- [ ] `python scripts/verify_docs.py` passes
- [ ] Decisions made outside the docs are recorded in the session log
- [ ] Specs in `docs/specs/` updated if a table, event, route or rule changed
- [ ] Tests run and results noted
- [ ] No medication advice, no diagnosis, nothing labelled "validated"
- [ ] Only the cited data sources are used; simulated data is flagged
- [ ] AI-estimated values are labelled as estimates
- [ ] No names or identifiers in prompts, no secrets or raw datasets committed
