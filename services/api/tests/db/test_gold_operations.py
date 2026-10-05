"""Tests for the Gold and Operations tables, the views and the new foreign keys (E1-3).

Each test runs inside a transaction that is rolled back, so the shared database is left untouched.
Run from the repo root:  python -m pytest services/api/tests/db -q   (needs DATABASE_URL in the private .env)
"""
import json
import os
import sys
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg import errors

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

GOLD_AND_OPS = [
    "timeline_5min", "baselines", "daily_summary", "care_summary", "meal_response", "exercise_response", "glucose_events",
    "clinical_flags", "pattern_candidates", "interaction_alerts", "memory_facts", "memory_episodes",
    "briefs", "brief_shares", "brief_share_access", "agent_runs", "agent_steps", "guardrail_events", "conversations", "messages", "event_log",
]
VIEWS = ["timeline_events", "health_state", "trends", "adherence_summary", "insight_context", "jev_decisions"]


@pytest.fixture()
def conn():
    load_env()
    c = psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20)
    try:
        yield c
    finally:
        c.rollback()
        c.close()


def user(conn):
    return conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0]


def rejected(conn, error, sql, params=()):
    try:
        with conn.transaction():
            conn.execute(sql, params)
    except error:
        return True
    return False


def one(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()[0]


def vec(n):
    return "[" + ",".join(["0.1"] * n) + "]"


# ---------------------------------------------------------------- structure
def test_new_tables_have_rls_on_and_no_policies(conn):
    rows = conn.execute("select relname, relrowsecurity from pg_class where relnamespace = 'public'::regnamespace and relname = any(%s)", (GOLD_AND_OPS,)).fetchall()
    assert len(rows) == len(GOLD_AND_OPS)
    assert all(r[1] for r in rows)
    assert one(conn, "select count(*) from pg_policies where schemaname = 'public' and tablename = any(%s)", (GOLD_AND_OPS,)) == 0


def test_views_exist_and_use_security_invoker(conn):
    rows = conn.execute("select relname, 'security_invoker=on' = any(reloptions) from pg_class where relnamespace = 'public'::regnamespace and relkind = 'v'").fetchall()
    assert sorted(r[0] for r in rows) == sorted(VIEWS)
    assert all(r[1] for r in rows)
    for v in VIEWS:
        conn.execute(f"select * from {v} limit 1")


def test_foreign_keys_from_silver_up_to_gold_exist(conn):
    names = {
        "appointments_brief_id_fkey", "doctor_questions_brief_id_fkey", "prescription_scans_agent_run_id_fkey",
        "conversations_summary_episode_id_fkey", "refill_forecasts_medication_id_fkey", "interaction_alerts_med_a_id_fkey",
        "interaction_alerts_med_b_id_fkey",
    }
    have = {r[0] for r in conn.execute("select conname from pg_constraint where contype = 'f' and conname = any(%s)", (list(names),)).fetchall()}
    assert have == names


def test_embedding_sizes_match(conn):
    sizes = {r[0]: r[1] for r in conn.execute(
        "select cl.relname, format_type(a.atttypid, a.atttypmod) from pg_attribute a join pg_class cl on cl.oid = a.attrelid "
        "where cl.relnamespace = 'public'::regnamespace and a.attname = 'embedding' and cl.relname in ('knowledge_chunks', 'memory_episodes')").fetchall()}
    assert sizes["knowledge_chunks"].endswith("(768)") and sizes["memory_episodes"].endswith("(768)")


def test_a_foreign_key_rejects_a_missing_target(conn):
    u = user(conn)
    conv = one(conn, "insert into conversations (user_id) values (%s) returning id", (u,))
    assert rejected(conn, errors.ForeignKeyViolation, "update conversations set summary_episode_id = %s where id = %s", (str(uuid.uuid4()), conv))


# ---------------------------------------------------------------- event_log
def add_events(conn, u, n=3):
    for i in range(n):
        conn.execute("insert into event_log (user_id, actor, event, payload) values (%s, 'user', %s, %s::jsonb)", (u, f"test.event.{i}", json.dumps({"n": i})))


def test_event_log_cannot_be_updated_deleted_or_truncated(conn):
    u = user(conn)
    add_events(conn, u, 1)
    assert rejected(conn, errors.RaiseException, "update event_log set event = 'x' where user_id = %s", (u,))
    assert rejected(conn, errors.RaiseException, "delete from event_log where user_id = %s", (u,))
    assert rejected(conn, errors.RaiseException, "truncate event_log")


def test_event_log_builds_a_hash_chain_and_detects_a_tampered_row(conn):
    u = user(conn)
    add_events(conn, u, 3)
    rows = conn.execute("select id, prev_hash, hash from event_log where user_id = %s order by id", (u,)).fetchall()
    assert rows[0][1] is None and rows[1][1] == rows[0][2] and rows[2][1] == rows[1][2]
    assert one(conn, "select verify_event_log_chain(%s)", (u,)) is None
    # a privileged edit that bypasses the guard must still be caught
    conn.execute("alter table event_log disable trigger trg_event_log_guard")
    conn.execute("update event_log set payload = '{\"n\": 99}'::jsonb where id = %s", (rows[1][0],))
    conn.execute("alter table event_log enable trigger trg_event_log_guard")
    assert one(conn, "select verify_event_log_chain(%s)", (u,)) == rows[1][0]


def test_event_log_rejects_a_duplicate_client_event_id(conn):
    u = user(conn)
    cid = str(uuid.uuid4())
    sql = "insert into event_log (user_id, actor, event, client_event_id) values (%s, 'user', 'test.dup', %s)"
    conn.execute(sql, (u, cid))
    assert rejected(conn, errors.UniqueViolation, sql, (u, cid))


def test_account_deletion_pseudonymises_instead_of_deleting(conn):
    u = user(conn)
    add_events(conn, u, 2)
    assert one(conn, "select pseudonymise_event_log(%s)", (u,)) == 2
    assert one(conn, "select count(*) from event_log where user_id = %s", (u,)) == 0
    assert one(conn, "select count(*) from event_log where user_id is null and pseudonymised_at is not null and payload = '{}'::jsonb and event like 'test.event.%%'") >= 2
    # the setting that allows the change is local to that call: a direct edit is refused again
    assert rejected(conn, errors.RaiseException, "update event_log set payload = '{}'::jsonb where user_id is null and pseudonymised_at is not null")


# ---------------------------------------------------------------- Gold rules
def new_brief(conn, u, status="ready"):
    return one(conn, "insert into briefs (user_id, period_start, period_end, status, data) values (%s, '2026-09-01', '2026-09-28', %s, '{\"a\": 1}'::jsonb) returning id", (u, status))


def test_a_ready_brief_cannot_be_changed_but_can_be_superseded(conn):
    u = user(conn)
    b = new_brief(conn, u)
    assert rejected(conn, errors.RaiseException, "update briefs set data = '{\"a\": 2}'::jsonb where id = %s", (b,))
    assert rejected(conn, errors.RaiseException, "update briefs set status = 'generating' where id = %s", (b,))
    conn.execute("update briefs set status = 'superseded' where id = %s", (b,))
    draft = new_brief(conn, u, "generating")
    conn.execute("update briefs set data = '{\"a\": 3}'::jsonb where id = %s", (draft,))  # drafts may change


def test_brief_period_must_not_end_before_it_starts(conn):
    u = user(conn)
    assert rejected(conn, errors.CheckViolation, "insert into briefs (user_id, period_start, period_end, status) values (%s, '2026-09-28', '2026-09-01', 'generating')", (u,))


def test_a_share_link_needs_consent_and_a_unique_hashed_token(conn):
    u = user(conn)
    b = new_brief(conn, u)
    assert rejected(conn, errors.NotNullViolation, "insert into brief_shares (brief_id, token_hash, expires_at) values (%s, 'h1', now())", (b,))
    cons = one(conn, "insert into consents (user_id, kind, version, granted_at) values (%s, 'brief_sharing', 'v1', now()) returning id", (u,))
    conn.execute("insert into brief_shares (brief_id, token_hash, expires_at, consent_id) values (%s, 'h1', now() + interval '72 hours', %s)", (b, cons))
    assert rejected(conn, errors.UniqueViolation, "insert into brief_shares (brief_id, token_hash, expires_at, consent_id) values (%s, 'h1', now(), %s)", (b, cons))


def test_a_pattern_needs_at_least_five_pairs(conn):
    u = user(conn)
    sql = ("insert into pattern_candidates (user_id, pattern_key, n_pairs, median_delta, relationship_type, evidence, status) "
           "values (%s, 'k', %s, 0.5, 'repeated_observation', '[]'::jsonb, 'open')")
    assert rejected(conn, errors.CheckViolation, sql, (u, 4))
    conn.execute(sql, (u, 5))
    assert rejected(conn, errors.UniqueViolation, sql, (u, 6))  # one open pattern per key


def test_only_one_active_memory_fact_per_key_and_superseding_works(conn):
    u = user(conn)
    sql = ("insert into memory_facts (user_id, key, category, value, confidence, evidence_status, evidence_refs, status, last_evidence_at) "
           "values (%s, 'routine.walk', 'routine', '{}'::jsonb, %s, 'inferred', '[]'::jsonb, %s, now()) returning id")
    first = one(conn, sql, (u, 0.8, "active"))
    assert rejected(conn, errors.UniqueViolation, sql, (u, 0.9, "active"))
    assert rejected(conn, errors.CheckViolation, sql, (u, 1.5, "proposed"))
    conn.execute("update memory_facts set status = 'superseded' where id = %s", (first,))
    second = one(conn, sql, (u, 0.9, "active"))
    conn.execute("update memory_facts set supersedes_id = %s where id = %s", (first, second))


def test_there_is_no_validated_evidence_status(conn):
    labels = [r[0] for r in conn.execute("select unnest(enum_range(null::evidence_status))::text").fetchall()]
    assert "validated" not in labels and set(labels) == {"observed", "derived", "inferred", "reference_matched"}


def test_updated_at_is_kept_by_the_trigger(conn):
    u = user(conn)
    f = one(conn, "insert into clinical_flags (user_id, kind, severity, evidence, first_seen_on, last_seen_on) values (%s, 'momentum_drift', 'review', '{}'::jsonb, '2026-10-01', '2026-10-01') returning id", (u,))
    conn.execute("update clinical_flags set updated_at = '2000-01-01' where id = %s", (f,))
    conn.execute("update clinical_flags set status = 'acknowledged' where id = %s", (f,))
    assert one(conn, "select updated_at > '2020-01-01' from clinical_flags where id = %s", (f,))


def test_a_flag_needs_a_severity_and_evidence(conn):
    u = user(conn)
    assert rejected(conn, errors.NotNullViolation, "insert into clinical_flags (user_id, kind, severity, first_seen_on, last_seen_on) values (%s, 'outside_usual_range', 'review', '2026-10-01', '2026-10-01')", (u,))


# ---------------------------------------------------------------- Operations
def test_agent_steps_are_ordered_and_unique_per_run(conn):
    u = user(conn)
    run = one(conn, "insert into agent_runs (user_id, agent, trigger, status) values (%s, 'router', 'chat', 'running') returning id", (u,))
    sql = "insert into agent_steps (agent_run_id, seq, node) values (%s, %s, 'guard')"
    conn.execute(sql, (run, 1))
    assert rejected(conn, errors.UniqueViolation, sql, (run, 1))
    assert rejected(conn, errors.CheckViolation, "insert into agent_runs (agent, trigger) values ('x', 'telepathy')")


def test_a_guardrail_excerpt_is_capped_at_300_characters(conn):
    u = user(conn)
    sql = "insert into guardrail_events (user_id, stage, verdict, rule_id, excerpt) values (%s, 'input', 'blocked_med_advice', 'r1', %s)"
    assert rejected(conn, errors.CheckViolation, sql, (u, "x" * 301))
    conn.execute(sql, (u, "x" * 300))


def test_memory_episode_needs_a_768_number_embedding(conn):
    u = user(conn)
    sql = "insert into memory_episodes (user_id, summary, embedding) values (%s, 's', %s::extensions.vector)"
    assert rejected(conn, errors.DataException, sql, (u, vec(1024)))
    conn.execute(sql, (u, vec(768)))


def test_jev_decisions_view_reads_jev_steps_only(conn):
    u = user(conn)
    run = one(conn, "insert into agent_runs (user_id, agent, trigger, status) values (%s, 'guard', 'chat', 'ok') returning id", (u,))
    out = json.dumps({"question_id": "med_advice", "type": "noul", "answer": "yes", "probability": 0.99, "confidence": 0.92, "passed_floor": True, "model": "typesafe/jev-1.13-20260917", "cost_usd": 0.0000144})
    conn.execute("insert into agent_steps (agent_run_id, seq, node, tool, output, latency_ms) values (%s, 1, 'jev', 'decide', %s::jsonb, 640)", (run, out))
    conn.execute("insert into agent_steps (agent_run_id, seq, node, tool, output) values (%s, 2, 'memory', 'get_context', '{}'::jsonb)", (run,))
    rows = conn.execute("select question_id, question_type, probability, confidence, passed_floor, latency_ms from jev_decisions where user_id = %s", (u,)).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "med_advice" and float(rows[0][2]) == 0.99 and float(rows[0][3]) == 0.92 and rows[0][4] is True and rows[0][5] == 640


# ---------------------------------------------------------------- views over Silver
def bronze(conn, table, u):
    return one(conn, f"insert into {table} (user_id, source, payload, checksum) values (%s, 'manual', '{{}}'::jsonb, %s) returning id", (u, str(uuid.uuid4())))


def test_adherence_summary_counts_closed_prescription_doses_only(conn):
    u = user(conn)
    b = bronze(conn, "bronze_medication", u)
    rx = one(conn, "insert into medications (user_id, name, kind, frequency, source, bronze_id) values (%s, 'Test', 'prescription', 1, 'manual', %s) returning id", (u, b))
    sup = one(conn, "insert into medications (user_id, name, kind, frequency, source, bronze_id) values (%s, 'Fish oil', 'supplement', 1, 'manual', %s) returning id", (u, b))
    rows = [(rx, "taken", 1), (rx, "taken", 2), (rx, "missed", 3), (rx, "skipped", 4), (rx, "pending", -2), (sup, "missed", 1)]
    for med, status, days_ago in rows:
        taken = "now()" if status == "taken" else "NULL"
        conn.execute(f"insert into medication_log (user_id, medication_id, scheduled_at, taken_at, status, source) "
                     f"values (%s, %s, now() - make_interval(days => %s), {taken}, %s, 'manual')", (u, med, days_ago, status))
    r = conn.execute("select scheduled, taken, missed, skipped, adherence_pct, quality_status from adherence_summary where user_id = %s and period = '7d'", (u,)).fetchone()
    assert r[:4] == (4, 2, 1, 1) and float(r[4]) == 50.0 and r[5] == "insufficient"   # the future and the supplement doses are not counted


def test_timeline_events_combines_streams_and_hides_soft_deleted_rows(conn):
    u = user(conn)
    bf, bs = bronze(conn, "bronze_food", u), bronze(conn, "bronze_symptom", u)
    conn.execute("insert into food_logs (user_id, start_at, end_at, food, carbs_g, estimated_by, source, bronze_id) values (%s, now(), now() + interval '20 minutes', 'rice', 60, 'user', 'manual', %s)", (u, bf))
    conn.execute("insert into symptom_logs (user_id, occurred_at, symptom_type, severity, source, bronze_id, deleted_at) values (%s, now(), 'fatigue', 2, 'manual', %s, now())", (u, bs))
    rows = conn.execute("select stream::text, magnitude from timeline_events where user_id = %s", (u,)).fetchall()
    assert rows == [("meal", 60)]


def test_trends_flags_a_declining_metric(conn):
    u = user(conn)
    conn.execute("insert into daily_summary (user_id, local_date, glucose_mean_mmol, glucose_worse_pct, declining_metrics) values (%s, '2026-10-01', 10.2, 40, ARRAY['glucose'])", (u,))
    r = conn.execute("select metric, value, worse_pct, declining from trends where user_id = %s and metric = 'glucose'", (u,)).fetchone()
    assert r[0] == "glucose" and float(r[1]) == 10.2 and float(r[2]) == 40 and r[3] is True
