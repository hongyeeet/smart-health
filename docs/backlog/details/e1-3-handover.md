# E1-3 handover: Bronze, Silver and Reference are built, start here

Written by Joely (with Claude) on 2026-10-02 for **Hong Yi**, who builds E1-3 (the Gold and Operations tables and views). It stands alone: you do not need the chat history. Hong Yi agreed to the plan in this document on 2026-10-02 (the three points in section 8).

## 1. What exists now

The shared Supabase project (`smart-health`, Postgres 17, region ap-southeast-1) holds **43 tables and 33 enum types**, created by seven Alembic migrations. Nothing is loaded yet (E1-4 loads values). The tables match `docs/specs/schema.md`; `python scripts/check_schema.py` proves it. The column-by-column list is [../../data_dictionary.md](../../data_dictionary.md); how the layers work and how every column links is explained, with diagrams, in [../../specs/bronze-silver.md](../../specs/bronze-silver.md).

| Layer | Tables |
|---|---|
| Bronze (1) | `ingestion_events` |
| Silver (31) | `users`, `patient_profiles`, `conditions`, `allergies`, `family_history`, `consents`, `prescription_scans`, `patient_medications`, `medication_ingredients`, `dose_events`, `refill_forecasts`, `glucose_readings`, `cgm_sprints`, `health_samples`, `sleep_sessions`, `meals`, `meal_items`, `meal_analyses`, `workouts`, `mood_checkins`, `symptom_logs`, `symptom_checkins`, `lab_results`, `blood_pressure_readings`, `body_measurements`, `appointments`, `doctor_questions`, `patient_preventive_status`, `devices`, `health_goals`, `notifications` |
| Reference (11) | `drug_reference`, `drug_aliases`, `drug_side_effects`, `interaction_rules`, `foods`, `preventive_items`, `routing_rules`, `population_priors`, `knowledge_documents`, `knowledge_chunks`, `data_sources` |

Also: the three extensions (`vector`, `citext`, `pg_trgm`, in the `extensions` schema), the function `set_updated_at()`, row-level security on every table (no policies), and a **private storage bucket** `smart-health-originals` (10 MB, jpeg, png, heic, csv, zip, xml).

| Migration | File in `services/api/alembic/versions/` | What it does |
|---|---|---|
| 0001 | `0001_extensions_enums.py` | Extensions, all 33 enums (including the Gold ones you need), `set_updated_at()` |
| 0002 | `0002_users_reference.py` | `users` and the 11 Reference tables |
| 0003 | `0003_bronze_ingestion_events.py` | `ingestion_events` and its immutability guard |
| 0004 | `0004_silver_profile_medications.py` | Profile, consents, scans, medications, doses (10) |
| 0005 | `0005_silver_measurements.py` | Meals, glucose, wearables, workouts, symptoms, labs, BP, body (14) |
| 0006 | `0006_silver_care_devices.py` | Appointments, questions, preventive status, devices, goals, notifications (6) |
| 0007 | `0007_row_level_security.py` | `ENABLE ROW LEVEL SECURITY` on every table in `public` |

## 2. Run it and check it

You need the shared `.env` (Joely sends it privately; it is never committed). Variables are documented in `.env.example`.

```bash
python scripts/check_supabase.py          # does your .env work? (database, pgvector, storage, RLS)
cd services/api && python -m alembic current          # should print 0007 (head)
python scripts/check_schema.py            # database matches the layer map (43 of 43)
python -m pytest services/api/tests/db -q # 10 constraint tests, each rolled back
python scripts/bronze.py --selftest       # storage and Bronze helper checks
pip install -r services/api/requirements-db.txt   # if packages are missing
```

Use the **Session pooler** connection string (port 5432) in `DATABASE_URL`. Supabase's default Transaction pooler string ends in `?pgbouncer=true`, which Python's driver rejects; `scripts/check_supabase.py` and `alembic/env.py` strip it, but use 5432 for migrations anyway.

## 3. Your E1-3 job

Create the **Gold and Operations tables and views** from `docs/specs/schema.md` as **new migrations numbered 0008 onwards** in `services/api/alembic/versions/` (copy the pattern of 0006). **Never edit 0001 to 0007**: they are applied and others depend on them. Run `python -m alembic upgrade head` from `services/api`.

### Tables to create (23) and where each is specified

| Layer | Table | schema.md |
|---|---|---|
| Gold | `daily_aggregates`, `baselines`, `momentum_snapshots`, `clinical_flags`, `urgent_events` | section 5 |
| Gold | `meal_responses`, `food_responses` | section 4 |
| Gold | `sprint_summaries`, `event_windows`, `pattern_candidates` | section 9b |
| Gold | `interaction_alerts` | section 3 |
| Gold | `memory_facts`, `memory_episodes`, `nudge_stats` | section 8 |
| Gold | `briefs`, `brief_shares`, `brief_share_access` | section 7 |
| Operations | `agent_runs`, `agent_steps`, `guardrail_events`, `conversations`, `messages` | section 8 |
| Operations | `event_log` | section 9 |

Views (plain names, same schema, section 9b and 9c): `timeline_events`, `health_state`, `trends`, `adherence_summary`, `insight_context`. Each carries calculation version, evidence window, freshness timestamp and quality status (rule in schema.md 9c and data-flow.md section 2).

### Suggested creation order (so no foreign key points at a table that does not exist yet)

1. `agent_runs`, then `agent_steps`, `guardrail_events`.
2. `briefs` (it points at `appointments` and `agent_runs`, both exist), then `brief_shares`, `brief_share_access`.
3. `clinical_flags` (its `brief_id` points at `briefs`), `urgent_events`, `daily_aggregates`, `baselines`, `momentum_snapshots`, `meal_responses`, `food_responses`, `sprint_summaries`, `event_windows`, `pattern_candidates`, `interaction_alerts`.
4. `conversations` **without** its `summary_episode_id` foreign key, then `memory_facts`, `memory_episodes` (its `conversation_id` points at `conversations`), `nudge_stats`, `messages`, `event_log`.
5. The views.
6. **Add the foreign keys listed next, at the end.**

### The foreign keys you must add (copy and paste)

Four Silver columns were created as plain nullable `uuid` columns because their target tables did not exist. **Joely created them; you add the constraints** once the targets exist:

```sql
ALTER TABLE symptom_checkins   ADD CONSTRAINT symptom_checkins_triggered_by_flag_id_fkey FOREIGN KEY (triggered_by_flag_id) REFERENCES clinical_flags(id);
ALTER TABLE appointments       ADD CONSTRAINT appointments_brief_id_fkey                  FOREIGN KEY (brief_id)              REFERENCES briefs(id);
ALTER TABLE doctor_questions   ADD CONSTRAINT doctor_questions_brief_id_fkey              FOREIGN KEY (brief_id)              REFERENCES briefs(id);
ALTER TABLE prescription_scans ADD CONSTRAINT prescription_scans_agent_run_id_fkey        FOREIGN KEY (agent_run_id)          REFERENCES agent_runs(id);
-- the loop inside your own tables:
ALTER TABLE conversations      ADD CONSTRAINT conversations_summary_episode_id_fkey       FOREIGN KEY (summary_episode_id)    REFERENCES memory_episodes(id);
```

`prescription_scans.agent_run_id` is new: `schema.md` and `data-flow.md` originally listed only three. They now say four.

### Rules for your migrations (so everything stays consistent)

- One statement per call, using the helper `run([...])` from the 0006 pattern (`op.get_bind().exec_driver_sql`). **Do not put a `%` character in SQL** (the driver reads it as a placeholder; use `quote_ident(...)` and `||` instead, as 0007 does).
- Every table gets row-level security **on, with no policies**. 0007 only covers tables that existed when it ran, so add `ALTER TABLE x ENABLE ROW LEVEL SECURITY` for each new table (or a final migration that repeats the DO block).
- Tables with `updated_at` get `CREATE TRIGGER trg_updated_at BEFORE UPDATE ON t FOR EACH ROW EXECUTE FUNCTION set_updated_at()`.
- Everything lives in `public`; no `gold.`, `silver.` or `bronze.` prefixes. Use the enums that already exist (`flag_severity`, `flag_status`, `urgent_tier`, `fact_category`, `fact_status`, `brief_status`, `actor_type`, `guard_verdict`, `evidence_status`, `relationship_type`, `timeline_stream`, ...).
- Vectors: `extensions.vector(n)` and `USING hnsw (embedding extensions.vector_cosine_ops)`. Read the size from `os.environ.get("EMBED_DIM", "1024")` as 0002 does for `knowledge_chunks`; `memory_episodes.embedding` must use the same value.
- Add a test per hard constraint in `services/api/tests/db/` (copy `test_schema_constraints.py`; tests run inside a rolled-back transaction).
- Do not run `alembic downgrade base` once anyone has loaded data (E1-4 loads data). Downgrade only your own newest revisions (`downgrade -1`).

### `event_log` must be append-only (careful: Supabase detail)

The spec says the app role has `INSERT, SELECT` only. But the backend connects as the `postgres` pooler role, which owns the tables and ignores grants. So enforce append-only with a **`BEFORE UPDATE OR DELETE` trigger that raises**, plus `REVOKE ALL ... FROM anon, authenticated`. Account deletion nulls `user_id` and strips `payload` (schema.md consistency rule 9), so either allow that one pseudonymisation path in the trigger or do it with a `SECURITY DEFINER` function. Implement the per-user hash chain (`prev_hash`, `hash`) as in schema.md section 9; E0-8's test must prove a tampered row is detected.

### Finish E1-3 by updating

- `scripts/check_schema.py`: change the default layers to `all` (one line: `DEFAULT = LAYERS`), run it, expect all 66 tables.
- `scripts/make_data_dictionary.py`: change `LAYERS` to include `gold`, `operations`, add a one-line `PURPOSE` for each new table, re-run it.
- `docs/specs/schema.md` section 12: add a note for anything you did differently from the spec.
- Your tasks in `hongyi.md` and `python scripts/update_tracker.py`, the session log, `project-memory.md`.
- Check with Supabase's advisor: no "RLS disabled" findings (the "RLS enabled, no policies" notes are intended).

## 4. Things already decided that affect you

| Decision | What it means for you | Record |
|---|---|---|
| `EMBED_DIM` is **1024, a placeholder** | You decide the real size in E0-3 (embedding model). If it changes while tables are empty: one migration that alters `knowledge_chunks.embedding` and `memory_episodes.embedding`, plus the value in `.env` | Joely and Hong Yi, 2026-10-02 |
| Migrations live in `services/api/alembic/` | Build the API skeleton (E0-2) around this folder; do not create a second Alembic setup | Hong Yi agreed 2026-10-02 |
| Drug interactions come from the **openFDA** drug-label text (250k Medicines has no interactions column) | Joely loads it into `interaction_rules` in E1-4. E6-1's clash checker reads `interaction_rules` and shows "not checked" for anything missing | D-036, session log joely_2026-10-01_1454 |
| The `substitute*` columns of 250k Medicines are dropped at load | Never surface a substitute | D-038 |
| `ingestion_events` rows are immutable except `processing_status` | Enforced by a trigger; use `scripts/bronze.py` (`store_original`, `delete_original`) for every photo, scan or import | schema.md 12 |
| Deleting an original should also be written to `event_log` | `delete_original()` has a `TODO(decision)`: once `event_log` exists, write an `ingestion.original.deleted` event there in the same transaction (add the name to the catalogue in flow.md section 4 first, as E0-11 requires) | scripts/bronze.py |
| Postgres is version 17 | schema.md and architecture.md say 16; nothing used depends on it | schema.md 12 |

## 5. Using the Bronze helpers (E3-1 scans, E7-2 meals)

```python
import sys; sys.path.insert(0, "scripts")
from bronze import store_original, delete_original
event_id, created = store_original(conn, user_id, "meal_photo", "manual", image_bytes, "lunch.jpg")
```

It hashes the bytes, uploads to `{user_id}/meals/<sha256>.jpg` **without overwriting**, and inserts the `ingestion_events` row. The same bytes for the same user return the existing row and upload nothing. You own the transaction (commit or roll back). Text-only meals use `source_type="meal_text"` (no file). Allowed types: jpeg, png, heic, csv, zip, xml; limit 10 MB.

## 6. Gotchas found while building

- The Python driver rejects the `pgbouncer` URL setting and treats `%` in SQL as a placeholder (see rules above).
- Alembic's own table `alembic_version` is in `public` and also has RLS on. It is the only table not in the layer map; `check_schema.py` ignores it.
- `check_supabase.py` is the quickest way to find out why a teammate's `.env` fails.
- The shared `.env` must not be committed, pasted into chat or put in `apps/web`.

## 7. What Joely does next (so you can plan)

E1-4 loads every value: datasets (CGMacros, BIG IDEAs, Fitbit, NHANES, GlucoBench), reference data (medicines, openFDA interactions, foods, check-ups, routing), the demo patient with a simulated 60-day history, devices and goals, the replay tool and the medicine knowledge index (that last step needs your AI gateway from E0-3). E1-4 does not need E1-3, but E19-1 and others need both.

## 8. What Hong Yi agreed (2026-10-02)

**Update:** E1-4 (the data load) has since run: see [e1-4-handover.md](e1-4-handover.md) for what is in every table, the demo patient, and what is placeholder or missing. The tables you build in E1-3 (Gold, Operations) read from that data.

1. Migrations live in `services/api/alembic/`; the API skeleton is built around that folder.
2. Hong Yi adds the four foreign keys at the end of E1-3 (section 3).
3. `EMBED_DIM=1024` is a placeholder until E0-3 chooses the embedding model.
