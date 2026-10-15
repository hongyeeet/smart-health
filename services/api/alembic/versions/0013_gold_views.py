"""Gold views (E1-3 step 6): timeline_events, health_state, trends, adherence_summary, insight_context, jev_decisions.

Source: docs/specs/schema.md sections 9b and 9c (the five views) plus jev_decisions, added on the owner's yes of
2026-10-03: a view over agent_steps (node = 'jev', tool = 'decide') so JEV answers can be queried to tune the
confidence floor and watch cost. It is a view, not a table (schema consistency rule 19).

Every view is created WITH (security_invoker = on), so row-level security of the caller applies and the public API
key reads nothing. The views carry calc_version, evidence_window, freshness and quality_status (schema.md 9c).

jev_decisions reads these keys from agent_steps.output (the JEV gateway writes them): question_id, type, answer,
probability, confidence, passed_floor, model, cost_usd.

Revision ID: 0013
Revises: 0012
"""
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

VIEWS = ["timeline_events", "health_state", "trends", "adherence_summary", "insight_context", "jev_decisions"]


def run(statements):
    conn = op.get_bind()
    for s in statements:
        conn.exec_driver_sql(s)


def upgrade():
    run([
        # One time-ordered stream per user. Raw CGM and heart-rate points are not in it (too many); glucose_event holds
        # only lows and highs: glucometer readings outside 3.9 to 10.0 and sensor readings below 3.9 or above 13.9.
        """CREATE VIEW timeline_events WITH (security_invoker = on) AS
SELECT t.*, '1'::text AS calc_version, 'all'::text AS evidence_window, now() AS freshness, 'sufficient'::text AS quality_status
FROM (
        SELECT m.user_id, m.eaten_at AS occurred_at, NULL::timestamptz AS end_at, 'meal'::timeline_stream AS stream,
               'meals'::text AS ref_table, m.id AS ref_id, 'timeline.meal'::text AS label_key,
               (SELECT sum(mi.carbs_g) FROM meal_items mi WHERE mi.meal_id = m.id)::numeric AS magnitude
          FROM meals m WHERE m.deleted_at IS NULL
        UNION ALL
        SELECT d.user_id, d.scheduled_at, NULL::timestamptz, 'dose', 'dose_events', d.id, 'timeline.dose.' || d.status::text, NULL::numeric
          FROM dose_events d
        UNION ALL
        SELECT w.user_id, w.started_at, w.started_at + make_interval(secs => w.duration_s), 'workout', 'workouts', w.id,
               'timeline.workout', (w.duration_s / 60.0)::numeric
          FROM workouts w WHERE w.deleted_at IS NULL
        UNION ALL
        SELECT s.user_id, s.start_at, s.end_at, 'sleep', 'sleep_sessions', s.id, 'timeline.sleep', s.asleep_min::numeric
          FROM sleep_sessions s
        UNION ALL
        SELECT l.user_id, l.occurred_at, NULL::timestamptz, 'symptom', 'symptom_logs', l.id, 'timeline.symptom', l.severity::numeric
          FROM symptom_logs l WHERE l.deleted_at IS NULL
        UNION ALL
        SELECT c.user_id, (c.checked_on::timestamp AT TIME ZONE 'Asia/Singapore'), NULL::timestamptz, 'checkin', 'mood_checkins', c.id,
               'timeline.checkin', c.mood::numeric
          FROM mood_checkins c
        UNION ALL
        SELECT e.user_id, e.shown_at, NULL::timestamptz, 'urgent', 'urgent_events', e.id, 'timeline.urgent.' || e.tier::text, NULL::numeric
          FROM urgent_events e
        UNION ALL
        SELECT g.user_id, g.measured_at, NULL::timestamptz, 'glucose_event', 'glucose_readings', g.id,
               CASE WHEN g.value_mmol < 3.9 THEN 'timeline.glucose.low' ELSE 'timeline.glucose.high' END, g.value_mmol::numeric
          FROM glucose_readings g
         WHERE g.deleted_at IS NULL AND g.quality_ok
           AND ((g.context <> 'cgm' AND (g.value_mmol < 3.9 OR g.value_mmol > 10.0))
             OR (g.context = 'cgm' AND (g.value_mmol < 3.9 OR g.value_mmol > 13.9)))
) t""",
        """CREATE VIEW trends WITH (security_invoker = on) AS
        SELECT ms.user_id, ms.metric, ms.day, ms.value, b.median AS baseline_median, b.mad AS baseline_mad,
               ms.z, ms.ewma, ms.slope, ms.accel,
               '1'::text AS calc_version,
               ((ms.day - 27)::text || ' to ' || ms.day::text) AS evidence_window,
               ((ms.day + 1)::timestamptz) AS freshness,
               CASE WHEN b.status = 'ready' THEN 'sufficient' WHEN b.status = 'learning' THEN 'learning' ELSE 'no_baseline' END AS quality_status
          FROM momentum_snapshots ms
          LEFT JOIN LATERAL (
            SELECT bb.median, bb.mad, bb.status FROM baselines bb
             WHERE bb.user_id = ms.user_id AND bb.metric = ms.metric AND bb.computed_on <= ms.day
             ORDER BY bb.computed_on DESC LIMIT 1) b ON true""",
        # Doses whose window has closed: taken, taken late, unconfirmed or missed. Future and skipped doses are not counted.
        """CREATE VIEW adherence_summary WITH (security_invoker = on) AS
        SELECT d.user_id, p.period,
               count(*) FILTER (WHERE d.status IN ('taken','taken_late_logged','unconfirmed','missed')) AS scheduled,
               count(*) FILTER (WHERE d.status IN ('taken','taken_late_logged')) AS taken,
               count(*) FILTER (WHERE d.status = 'unconfirmed') AS unconfirmed,
               count(*) FILTER (WHERE d.status = 'missed') AS missed,
               round(100.0 * count(*) FILTER (WHERE d.status IN ('taken','taken_late_logged'))
                     / NULLIF(count(*) FILTER (WHERE d.status IN ('taken','taken_late_logged','unconfirmed','missed')), 0), 1) AS adherence_pct,
               (SELECT coalesce(jsonb_agg(jsonb_build_object('reason', r.miss_reason, 'count', r.n) ORDER BY r.n DESC), '[]'::jsonb)
                  FROM (SELECT d2.miss_reason, count(*) AS n FROM dose_events d2
                         WHERE d2.user_id = d.user_id AND d2.miss_reason IS NOT NULL
                           AND d2.scheduled_at >= now() - p.days * interval '1 day' AND d2.scheduled_at <= now()
                         GROUP BY d2.miss_reason) r) AS top_reasons,
               '1'::text AS calc_version,
               p.period AS evidence_window,
               now() AS freshness,
               CASE WHEN count(*) FILTER (WHERE d.status IN ('taken','taken_late_logged','unconfirmed','missed')) >= 5 THEN 'sufficient' ELSE 'insufficient' END AS quality_status
          FROM dose_events d
         CROSS JOIN (VALUES ('7d', 7), ('28d', 28)) AS p(period, days)
         WHERE d.scheduled_at >= now() - p.days * interval '1 day' AND d.scheduled_at <= now()
         GROUP BY d.user_id, p.period, p.days""",
        """CREATE VIEW health_state WITH (security_invoker = on) AS
        SELECT a.user_id, now() AS as_of,
               jsonb_build_object('fasting_mean', a.fasting_glucose_mean, 'postmeal_mean', a.postmeal_glucose_mean,
                                  'tir_pct', a.tir_pct, 'readings_n', a.glucose_readings_n) AS glucose_state,
               jsonb_build_object('sleep_min', a.sleep_min, 'sleep_midpoint_min', a.sleep_midpoint_min) AS sleep_state,
               jsonb_build_object('steps', a.steps, 'workout_min', a.workout_min, 'resting_hr', a.resting_hr) AS activity_state,
               jsonb_build_object('carbs_g', a.carbs_g, 'sugar_g', a.sugar_g, 'sodium_mg', a.sodium_mg, 'meals_n', a.meals_n) AS nutrition_state,
               jsonb_build_object('doses_scheduled', a.doses_scheduled, 'doses_taken', a.doses_taken, 'adherence_pct', a.adherence_pct) AS adherence_state,
               (SELECT jsonb_build_object('last_7_days', count(*), 'latest', max(s.occurred_at))
                  FROM symptom_logs s WHERE s.user_id = a.user_id AND s.deleted_at IS NULL AND s.occurred_at >= now() - interval '7 days') AS symptom_state,
               CASE WHEN a.day >= current_date - 2 THEN 'sufficient' ELSE 'stale' END AS quality_status,
               '1'::text AS calc_version,
               a.day::text AS evidence_window,
               a.computed_at AS freshness
          FROM (SELECT DISTINCT ON (user_id) * FROM daily_aggregates ORDER BY user_id, day DESC) a""",
        """CREATE VIEW insight_context WITH (security_invoker = on) AS
        SELECT u.id AS user_id, now() AS as_of,
               (SELECT coalesce(jsonb_agg(jsonb_build_object('id', f.id, 'kind', f.kind, 'metric', f.metric, 'severity', f.severity,
                                                              'status', f.status, 'last_seen_on', f.last_seen_on)), '[]'::jsonb)
                  FROM clinical_flags f WHERE f.user_id = u.id AND f.status IN ('open','in_brief')) AS open_flags,
               (SELECT coalesce(jsonb_agg(jsonb_build_object('id', m.id, 'key', m.key, 'category', m.category, 'statement', m.statement,
                                                              'confidence', m.confidence, 'evidence_status', m.evidence_status)
                                          ORDER BY m.confidence DESC), '[]'::jsonb)
                  FROM (SELECT * FROM memory_facts mf WHERE mf.user_id = u.id AND mf.status = 'active'
                         ORDER BY mf.confidence DESC LIMIT 20) m) AS active_facts,
               (SELECT coalesce(jsonb_agg(jsonb_build_object('id', p.id, 'pattern_key', p.pattern_key, 'n_pairs', p.n_pairs,
                                                              'median_delta', p.median_delta, 'relationship_type', p.relationship_type,
                                                              'evidence_status', p.evidence_status)
                                          ORDER BY p.updated_at DESC), '[]'::jsonb)
                  FROM (SELECT * FROM pattern_candidates pc WHERE pc.user_id = u.id AND pc.status = 'open'
                         ORDER BY pc.updated_at DESC LIMIT 5) p) AS latest_patterns,
               (SELECT coalesce(jsonb_agg(jsonb_build_object('food_id', r.food_id, 'n', r.n, 'mean_iauc', r.mean_iauc,
                                                              'mean_peak_rise', r.mean_peak_rise, 'rank_pct', r.rank_pct)
                                          ORDER BY r.rank_pct), '[]'::jsonb)
                  FROM (SELECT * FROM food_responses fr WHERE fr.user_id = u.id AND fr.n >= 2 ORDER BY fr.rank_pct LIMIT 5) r) AS latest_food_responses,
               (SELECT jsonb_build_object('day', a.day, 'logged_streams', a.logged_streams)
                  FROM daily_aggregates a WHERE a.user_id = u.id ORDER BY a.day DESC LIMIT 1) AS completeness,
               '1'::text AS calc_version,
               'current'::text AS evidence_window,
               now() AS freshness,
               CASE WHEN EXISTS (SELECT 1 FROM daily_aggregates a2 WHERE a2.user_id = u.id AND a2.day >= current_date - 2)
                    THEN 'sufficient' ELSE 'insufficient' END AS quality_status
          FROM users u""",
        """CREATE VIEW jev_decisions WITH (security_invoker = on) AS
        SELECT s.id AS step_id, s.agent_run_id, r.user_id, s.seq, s.created_at,
               s.output ->> 'question_id' AS question_id,
               s.output ->> 'type' AS question_type,
               s.output ->> 'answer' AS answer,
               nullif(s.output ->> 'probability', '')::numeric AS probability,
               nullif(s.output ->> 'confidence', '')::numeric AS confidence,
               (s.output ->> 'passed_floor')::boolean AS passed_floor,
               s.output ->> 'model' AS model,
               nullif(s.output ->> 'cost_usd', '')::numeric AS cost_usd,
               s.latency_ms
          FROM agent_steps s JOIN agent_runs r ON r.id = s.agent_run_id
         WHERE s.node = 'jev' AND s.tool = 'decide'""",
    ])


def downgrade():
    run([f"DROP VIEW IF EXISTS {v}" for v in reversed(VIEWS)])
