"""Data model v2 rebuild: per-source Bronze and Silver tables, the master timeline and the other Gold tables.

DESTRUCTIVE AND NOT REVERSIBLE. Drops the 34 old Bronze, Silver and Gold tables and their rows, the five old views,
and nine enum types, then creates the v2 design from docs/specs/data-model-v2.md. Take the backup first
(python scripts/v2_backup.py). Reference, Operations and App tables are kept; two of them are re-pointed:
refill_forecasts (column renamed to medication_id) and interaction_alerts (foreign keys now reach medications).

Revision ID: 0018
Revises: 0017
"""
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

OLD_VIEWS = ["timeline_events", "health_state", "trends", "adherence_summary", "insight_context"]

OLD_TABLES = [
    "ingestion_events",
    # old Silver
    "allergies", "blood_pressure_readings", "body_measurements", "cgm_sprints", "conditions", "devices", "dose_events",
    "family_history", "glucose_readings", "health_goals", "health_samples", "lab_results", "meal_analyses", "meal_items",
    "meals", "medication_ingredients", "mood_checkins", "patient_medications", "patient_profiles", "sleep_sessions",
    "symptom_checkins", "symptom_logs", "workout_sets", "workouts",
    # old Gold
    "baselines", "daily_aggregates", "event_windows", "food_responses", "meal_responses", "momentum_snapshots",
    "nudge_stats", "sprint_summaries", "urgent_events",
]
OLD_ENUMS = ["device_kind", "dose_status", "glucose_context", "goal_kind", "lab_kind", "med_status", "sample_metric",
             "urgent_tier", "workout_intensity"]

NEW_ENUMS = [
    ("yes_no_unsure", "'yes','no','not_sure'"),
    ("gender_type", "'female','male','other','prefer_not_to_say'"),
    ("work_type", "'desk','mixed','standing','physical','shift','not_working'"),
    ("symptom_kind", "'numbness','tingling','blurred_vision','fatigue','thirst','frequent_urination','dizziness','headache',"
                     "'shaky_sweaty','nausea','foot_pain','slow_healing_wound','other'"),
    ("exercise_kind", "'strength','walking','running','cycling','swimming','hiit','sports','yoga_pilates',"
                      "'stretching_mobility','dance','household_gardening','other'"),
    ("lab_test", "'hba1c','fasting_glucose','fasting_insulin'"),
    ("meal_relation", "'before_meal','after_meal','na'"),
    ("dose_status", "'pending','taken','missed','skipped'"),
    ("dose_outcome", "'taken','late','missed','skipped'"),
    ("estimated_by_kind", "'user','llm_text','llm_photo','database'"),
    ("baseline_metric", "'heart_rate','hrv','spo2','glucose','systolic','diastolic'"),
    ("baseline_reset_reason", "'first_14_days','doctor_review','medication_change','user_reset'"),
    ("glucose_zone", "'low','in_range','high','very_high'"),
    ("glucose_event_kind", "'spike','sustained_high','low'"),
]

BRONZE = ["profile", "medication", "lab", "watch", "cgm", "blood_pressure", "exercise", "food", "symptom", "wellbeing"]

# Tables with updated_at maintained by trigger
UPDATED_AT = ["user_profile", "medications", "medication_schedule", "medication_log", "exercise_logs", "food_logs",
              "symptom_logs", "wellbeing_logs"]

LAYERS = {
    "Bronze": [f"bronze_{b}" for b in BRONZE],
    "Silver": ["user_profile", "medications", "medication_schedule", "medication_log", "lab_results", "watch_readings",
               "cgm_readings", "blood_pressure_readings", "exercise_logs", "exercise_sets", "food_logs", "symptom_logs",
               "wellbeing_logs"],
    "Gold": ["timeline_5min", "baselines", "daily_summary", "care_summary", "meal_response", "exercise_response",
             "glucose_events", "clinical_flags", "pattern_candidates", "briefs", "brief_shares", "brief_share_access",
             "memory_facts", "memory_episodes", "interaction_alerts"],
    "App": ["users", "consents", "notifications", "refill_forecasts", "patient_preventive_status", "doctor_questions",
            "appointments", "prescription_scans"],
    "Reference": ["data_sources", "drug_aliases", "drug_reference", "drug_side_effects", "foods", "interaction_rules",
                  "knowledge_chunks", "knowledge_documents", "population_priors", "preventive_items", "routing_rules"],
    "Operations": ["agent_runs", "agent_steps", "conversations", "messages", "event_log", "guardrail_events"],
}

BRONZE_NOTES = {
    "profile": "one onboarding or profile form submission",
    "medication": "one medication entry with its schedule, a dose confirmation, or a prescription scan",
    "lab": "one lab entry or lab document",
    "watch": "one watch sync (a whole batch)",
    "cgm": "one CGM push or file",
    "blood_pressure": "one blood pressure entry or device sync",
    "exercise": "one exercise entry including its sets",
    "food": "one food entry: text or photo and the raw LLM answer",
    "symptom": "one symptom entry",
    "wellbeing": "one mood / stress / sleep-quality / energy entry",
}


def run(statements):
    conn = op.get_bind()
    for s in statements:
        conn.exec_driver_sql(s)


def bronze_tables():
    stmts = []
    for b in BRONZE:
        t = f"bronze_{b}"
        stmts += [
            f"""CREATE TABLE {t} (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                received_at timestamptz NOT NULL DEFAULT now(),
                source entry_source NOT NULL,
                payload jsonb NOT NULL,
                object_key text,
                checksum text NOT NULL,
                processing_status text NOT NULL DEFAULT 'received'
                    CHECK (processing_status IN ('received','processed','failed','deleted')),
                UNIQUE (user_id, checksum)
            )""",
            f"CREATE INDEX {t}_user_received ON {t} (user_id, received_at DESC)",
            f"CREATE TRIGGER trg_{t}_guard BEFORE UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION bronze_guard()",
        ]
    return stmts


SILVER = [
    # ------------------------------------------------------------------ one-time records
    """CREATE TABLE user_profile (
        user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        display_name text NOT NULL,
        language locale_code NOT NULL DEFAULT 'en',
        has_diabetes yes_no_unsure NOT NULL,
        birth_year smallint NOT NULL CHECK (birth_year BETWEEN 1900 AND 2100),
        gender gender_type,
        race text,
        height_cm numeric(4,1) CHECK (height_cm BETWEEN 100 AND 250),
        weight_kg numeric(5,1) CHECK (weight_kg BETWEEN 25 AND 300),
        work_type work_type,
        work_days smallint[] CHECK (work_days <@ ARRAY[1,2,3,4,5,6,7]::smallint[]),
        work_start time,
        work_end time,
        emergency_contact_name text,
        emergency_contact_phone text,
        emergency_contact_relation text,
        watch_model text,
        cgm_model text,
        timezone text NOT NULL DEFAULT 'Asia/Singapore',
        glucose_target_low numeric(3,1) NOT NULL DEFAULT 3.9,
        glucose_target_high numeric(3,1) NOT NULL DEFAULT 10.0,
        allergies_note text,
        conditions_note text,
        bronze_id uuid NOT NULL REFERENCES bronze_profile(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        CHECK (glucose_target_low < glucose_target_high)
    )""",
    """CREATE TABLE medications (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name text NOT NULL,
        kind med_kind NOT NULL DEFAULT 'prescription',
        strength text,
        frequency smallint NOT NULL CHECK (frequency BETWEEN 1 AND 6),
        description text,
        start_date date,
        end_date date,
        drug_reference_id uuid REFERENCES drug_reference(id),
        source entry_source NOT NULL,
        bronze_id uuid NOT NULL REFERENCES bronze_medication(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        deleted_at timestamptz,
        CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
    )""",
    "CREATE INDEX medications_user ON medications (user_id) WHERE deleted_at IS NULL",
    """CREATE TABLE medication_schedule (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        medication_id uuid NOT NULL REFERENCES medications(id) ON DELETE CASCADE,
        dose_time time NOT NULL,
        quantity numeric(4,1) NOT NULL CHECK (quantity > 0),
        meal_relation meal_relation NOT NULL DEFAULT 'na',
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        deleted_at timestamptz
    )""",
    "CREATE UNIQUE INDEX medication_schedule_one_per_time ON medication_schedule (medication_id, dose_time) WHERE deleted_at IS NULL",
    """CREATE TABLE medication_log (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        medication_id uuid NOT NULL REFERENCES medications(id) ON DELETE CASCADE,
        schedule_id uuid REFERENCES medication_schedule(id),
        scheduled_at timestamptz,
        taken_at timestamptz,
        status dose_status NOT NULL DEFAULT 'pending',
        miss_reason miss_reason,
        source entry_source NOT NULL,
        bronze_id uuid REFERENCES bronze_medication(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        CHECK (scheduled_at IS NOT NULL OR taken_at IS NOT NULL),
        CHECK (status <> 'taken' OR taken_at IS NOT NULL),
        UNIQUE (schedule_id, scheduled_at)
    )""",
    "CREATE INDEX medication_log_user_time ON medication_log (user_id, scheduled_at DESC)",
    """CREATE TABLE lab_results (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        measured_at timestamptz NOT NULL,
        test lab_test NOT NULL,
        value numeric NOT NULL CHECK (value > 0),
        unit text NOT NULL,
        source entry_source NOT NULL,
        bronze_id uuid NOT NULL REFERENCES bronze_lab(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        deleted_at timestamptz,
        CHECK ((test = 'hba1c' AND unit = '%%') OR (test = 'fasting_glucose' AND unit IN ('mg/dL','mmol/L'))
               OR (test = 'fasting_insulin' AND unit = 'mcU/mL'))
    )""",
    "CREATE INDEX lab_results_user_time ON lab_results (user_id, measured_at DESC)",
    # ------------------------------------------------------------------ passive recording
    """CREATE TABLE watch_readings (
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        recorded_at timestamptz NOT NULL,
        heart_rate_bpm smallint CHECK (heart_rate_bpm BETWEEN 20 AND 250),
        hrv_rmssd_ms numeric(5,1) CHECK (hrv_rmssd_ms > 0),
        spo2_pct numeric(4,1) CHECK (spo2_pct BETWEEN 50 AND 100),
        steps integer CHECK (steps >= 0),
        sleep_minutes smallint CHECK (sleep_minutes BETWEEN 0 AND 5),
        source entry_source NOT NULL,
        bronze_id uuid NOT NULL REFERENCES bronze_watch(id),
        PRIMARY KEY (user_id, recorded_at),
        CHECK (extract(epoch FROM recorded_at)::bigint %% 300 = 0),
        CHECK (num_nonnulls(heart_rate_bpm, hrv_rmssd_ms, spo2_pct, steps, sleep_minutes) > 0)
    )""",
    "CREATE INDEX watch_readings_bronze ON watch_readings (bronze_id)",
    """CREATE TABLE cgm_readings (
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        recorded_at timestamptz NOT NULL,
        glucose_mmol numeric(4,1) NOT NULL CHECK (glucose_mmol BETWEEN 1.0 AND 33.3),
        quality_ok boolean NOT NULL DEFAULT true,
        source entry_source NOT NULL,
        bronze_id uuid NOT NULL REFERENCES bronze_cgm(id),
        PRIMARY KEY (user_id, recorded_at)
    )""",
    "CREATE INDEX cgm_readings_bronze ON cgm_readings (bronze_id)",
    """CREATE TABLE blood_pressure_readings (
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        recorded_at timestamptz NOT NULL,
        systolic_mmhg smallint NOT NULL CHECK (systolic_mmhg BETWEEN 60 AND 260),
        diastolic_mmhg smallint NOT NULL CHECK (diastolic_mmhg BETWEEN 30 AND 160),
        source entry_source NOT NULL,
        bronze_id uuid NOT NULL REFERENCES bronze_blood_pressure(id),
        deleted_at timestamptz,
        PRIMARY KEY (user_id, recorded_at),
        CHECK (systolic_mmhg > diastolic_mmhg)
    )""",
    # ------------------------------------------------------------------ active recording
    """CREATE TABLE exercise_logs (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        start_at timestamptz NOT NULL,
        end_at timestamptz NOT NULL,
        type exercise_kind NOT NULL,
        intensity smallint NOT NULL CHECK (intensity BETWEEN 1 AND 5),
        feeling smallint CHECK (feeling BETWEEN 1 AND 5),
        note text,
        source entry_source NOT NULL,
        bronze_id uuid NOT NULL REFERENCES bronze_exercise(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        deleted_at timestamptz,
        CHECK (end_at > start_at)
    )""",
    "CREATE INDEX exercise_logs_user_start ON exercise_logs (user_id, start_at DESC)",
    """CREATE TABLE exercise_sets (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        exercise_log_id uuid NOT NULL REFERENCES exercise_logs(id) ON DELETE CASCADE,
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        exercise text NOT NULL,
        exercise_order smallint NOT NULL,
        set_no smallint NOT NULL,
        reps smallint NOT NULL CHECK (reps BETWEEN 1 AND 200),
        weight_kg numeric(5,1) CHECK (weight_kg BETWEEN 0 AND 500),
        rest_s smallint,
        rpe smallint CHECK (rpe BETWEEN 1 AND 10),
        performed_at timestamptz NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (exercise_log_id, exercise_order, set_no)
    )""",
    "CREATE INDEX exercise_sets_user_performed ON exercise_sets (user_id, performed_at DESC)",
    """CREATE TABLE food_logs (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        start_at timestamptz NOT NULL,
        end_at timestamptz NOT NULL,
        meal_type meal_type,
        food text NOT NULL,
        protein_g numeric(5,1) CHECK (protein_g >= 0),
        carbs_g numeric(5,1) CHECK (carbs_g >= 0),
        fat_g numeric(5,1) CHECK (fat_g >= 0),
        sugar_g numeric(5,1) CHECK (sugar_g >= 0),
        fibre_g numeric(5,1) CHECK (fibre_g >= 0),
        sodium_mg numeric(6,0) CHECK (sodium_mg >= 0),
        estimated_by estimated_by_kind NOT NULL,
        source entry_source NOT NULL,
        bronze_id uuid NOT NULL REFERENCES bronze_food(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        deleted_at timestamptz,
        CHECK (end_at >= start_at),
        CHECK (sugar_g IS NULL OR carbs_g IS NULL OR sugar_g <= carbs_g),
        CHECK (fibre_g IS NULL OR carbs_g IS NULL OR fibre_g <= carbs_g)
    )""",
    "CREATE INDEX food_logs_user_start ON food_logs (user_id, start_at DESC)",
    """CREATE TABLE symptom_logs (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        occurred_at timestamptz NOT NULL,
        symptom_type symptom_kind NOT NULL,
        severity smallint NOT NULL CHECK (severity BETWEEN 1 AND 5),
        duration_min integer CHECK (duration_min > 0),
        note text,
        source entry_source NOT NULL,
        bronze_id uuid NOT NULL REFERENCES bronze_symptom(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        deleted_at timestamptz
    )""",
    "CREATE INDEX symptom_logs_user_time ON symptom_logs (user_id, occurred_at DESC)",
    """CREATE TABLE wellbeing_logs (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        recorded_at timestamptz NOT NULL,
        mood smallint CHECK (mood BETWEEN 1 AND 5),
        stress_self smallint CHECK (stress_self BETWEEN 1 AND 5),
        sleep_quality smallint CHECK (sleep_quality BETWEEN 1 AND 5),
        energy smallint CHECK (energy BETWEEN 1 AND 5),
        source entry_source NOT NULL,
        bronze_id uuid NOT NULL REFERENCES bronze_wellbeing(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        deleted_at timestamptz,
        CHECK (num_nonnulls(mood, stress_self, sleep_quality, energy) > 0)
    )""",
    "CREATE INDEX wellbeing_logs_user_time ON wellbeing_logs (user_id, recorded_at DESC)",
]

GOLD = [
    """CREATE TABLE timeline_5min (
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        bucket_start timestamptz NOT NULL,
        local_date date NOT NULL,
        hour_of_day smallint NOT NULL,
        heart_rate_bpm smallint,
        hrv_rmssd_ms numeric(5,1),
        spo2_pct numeric(4,1),
        steps integer,
        sleep_minutes smallint,
        steps_day_cum integer,
        sleep_min_night_cum integer,
        hr_vs_baseline numeric(5,1),
        hrv_vs_baseline numeric(5,1),
        spo2_vs_baseline numeric(4,1),
        glucose_vs_baseline numeric(4,1),
        systolic_mmhg smallint,
        diastolic_mmhg smallint,
        glucose_mmol numeric(4,1),
        glucose_change_1h numeric(4,1),
        glucose_zone glucose_zone,
        meal_id uuid,
        meal_type meal_type,
        food text,
        carbs_g numeric(5,1),
        protein_g numeric(5,1),
        fat_g numeric(5,1),
        sugar_g numeric(5,1),
        fibre_g numeric(5,1),
        sodium_mg numeric(6,0),
        exercise_id uuid,
        exercise_type exercise_kind,
        exercise_intensity smallint,
        medication_names text,
        dose_status dose_outcome,
        meal_relation text CHECK (meal_relation IN ('before_meal','after_meal','na','mixed')),
        doses jsonb,
        mood smallint,
        stress_self smallint,
        sleep_quality smallint,
        energy smallint,
        symptom_type symptom_kind,
        symptom_severity smallint,
        symptom_duration_min integer,
        symptom_note text,
        at_work boolean,
        work_type work_type,
        PRIMARY KEY (user_id, bucket_start)
    )""",
    "CREATE INDEX timeline_5min_user_date ON timeline_5min (user_id, local_date)",
    """CREATE TABLE baselines (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        anchor_start date NOT NULL,
        anchor_end date NOT NULL,
        metric baseline_metric NOT NULL,
        hour_of_day smallint CHECK (hour_of_day BETWEEN 0 AND 23),
        p05 numeric(6,1) NOT NULL,
        p25 numeric(6,1) NOT NULL,
        p50 numeric(6,1) NOT NULL,
        p75 numeric(6,1) NOT NULL,
        p95 numeric(6,1) NOT NULL,
        n_days smallint NOT NULL,
        n_points integer NOT NULL,
        reset_reason baseline_reset_reason NOT NULL,
        UNIQUE NULLS NOT DISTINCT (user_id, anchor_start, metric, hour_of_day),
        CHECK (anchor_end >= anchor_start),
        CHECK (p05 <= p25 AND p25 <= p50 AND p50 <= p75 AND p75 <= p95),
        CHECK ((metric IN ('systolic','diastolic')) = (hour_of_day IS NULL))
    )""",
    "CREATE INDEX baselines_user_metric ON baselines (user_id, metric, anchor_end DESC)",
    """CREATE TABLE daily_summary (
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        local_date date NOT NULL,
        glucose_mean_mmol numeric(4,1), glucose_sd_mmol numeric(4,1), glucose_min_mmol numeric(4,1), glucose_max_mmol numeric(4,1),
        tir_pct numeric(4,1), tbr_pct numeric(4,1), tar_pct numeric(4,1), cgm_coverage_pct numeric(4,1),
        steps_total integer, sleep_hours numeric(3,1), resting_hr_bpm smallint, hrv_mean_ms numeric(5,1),
        spo2_mean_pct numeric(4,1), bp_systolic_mean numeric(4,0), bp_diastolic_mean numeric(4,0),
        meals_n smallint, carbs_g numeric(6,1), protein_g numeric(6,1), fat_g numeric(6,1), sugar_g numeric(6,1),
        fibre_g numeric(6,1), sodium_mg numeric(6,0),
        exercise_min integer, exercise_sessions_n smallint,
        doses_scheduled smallint, doses_taken smallint, doses_missed smallint,
        symptoms_n smallint, symptom_worst_severity smallint,
        mood_avg numeric(2,1), stress_self_avg numeric(2,1), energy_avg numeric(2,1), sleep_quality_avg numeric(2,1),
        work_day boolean,
        hr_outside_pct numeric(4,1), hrv_outside_pct numeric(4,1), spo2_outside_pct numeric(4,1), glucose_outside_pct numeric(4,1),
        declining_metrics text[],
        data_quality jsonb,
        built_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (user_id, local_date)
    )""",
    """CREATE TABLE care_summary (
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        local_date date NOT NULL,
        adherence_7d_pct numeric(4,1), adherence_30d_pct numeric(4,1),
        doses_missed_7d smallint, longest_miss_streak_days smallint,
        top_miss_reason_30d miss_reason, most_missed_time time, days_to_runout smallint,
        preventive_overdue text[], preventive_due_soon text[], hba1c_days_since smallint,
        open_questions_n smallint, next_appointment_at timestamptz, next_appointment_kind appointment_kind, brief_status text,
        open_flags_n smallint, top_flag_severity flag_severity, declining_metrics text[],
        built_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (user_id, local_date)
    )""",
    """CREATE TABLE meal_response (
        food_log_id uuid PRIMARY KEY REFERENCES food_logs(id) ON DELETE CASCADE,
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        pre_glucose_mmol numeric(4,1), peak_glucose_mmol numeric(4,1), minutes_to_peak integer, rise_mmol numeric(4,1),
        glucose_1h_mmol numeric(4,1), glucose_2h_mmol numeric(4,1), iauc_2h_mmol_min numeric(7,1),
        minutes_to_baseline integer, steps_next_2h integer, spike_flag boolean,
        built_at timestamptz NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX meal_response_user ON meal_response (user_id)",
    """CREATE TABLE exercise_response (
        exercise_log_id uuid PRIMARY KEY REFERENCES exercise_logs(id) ON DELETE CASCADE,
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        hr_pre_bpm smallint, hr_avg_bpm smallint, hr_peak_bpm smallint, hr_30min_after_bpm smallint,
        glucose_pre_mmol numeric(4,1), glucose_min_during_mmol numeric(4,1), glucose_change_at_end numeric(4,1),
        glucose_1h_mmol numeric(4,1), glucose_2h_mmol numeric(4,1), glucose_12h_mmol numeric(4,1),
        post_exercise_low_flag boolean,
        built_at timestamptz NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX exercise_response_user ON exercise_response (user_id)",
    """CREATE TABLE glucose_events (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        event_type glucose_event_kind NOT NULL,
        started_at timestamptz NOT NULL, extreme_at timestamptz NOT NULL, ended_at timestamptz NOT NULL,
        duration_min integer NOT NULL,
        start_glucose_mmol numeric(4,1), extreme_glucose_mmol numeric(4,1), rise_mmol numeric(4,1),
        ctx_meal_id uuid REFERENCES food_logs(id) ON DELETE SET NULL,
        ctx_exercise_id uuid REFERENCES exercise_logs(id) ON DELETE SET NULL,
        ctx_dose_status dose_outcome,
        ctx_heart_rate_bpm smallint, ctx_stress_self smallint, ctx_symptom_type symptom_kind,
        built_at timestamptz NOT NULL DEFAULT now(),
        CHECK (ended_at >= started_at)
    )""",
    "CREATE INDEX glucose_events_user_start ON glucose_events (user_id, started_at DESC)",
]

VIEWS = [
    # One time-ordered stream per user. Raw CGM and heart-rate points are not in it (too many); glucose_event holds
    # only the spikes, sustained highs and lows found in glucose_events.
    """CREATE VIEW timeline_events WITH (security_invoker = on) AS
SELECT t.*, '2'::text AS calc_version, 'all'::text AS evidence_window, now() AS freshness, 'sufficient'::text AS quality_status
FROM (
        SELECT f.user_id, f.start_at AS occurred_at, f.end_at AS end_at, 'meal'::timeline_stream AS stream,
               'food_logs'::text AS ref_table, f.id AS ref_id, 'timeline.meal'::text AS label_key, f.carbs_g::numeric AS magnitude
          FROM food_logs f WHERE f.deleted_at IS NULL
        UNION ALL
        SELECT l.user_id, coalesce(l.taken_at, l.scheduled_at), NULL::timestamptz, 'dose', 'medication_log', l.id,
               'timeline.dose.' || l.status::text, NULL::numeric
          FROM medication_log l WHERE l.status <> 'pending'
        UNION ALL
        SELECT e.user_id, e.start_at, e.end_at, 'workout', 'exercise_logs', e.id, 'timeline.workout',
               (extract(epoch FROM (e.end_at - e.start_at)) / 60.0)::numeric
          FROM exercise_logs e WHERE e.deleted_at IS NULL
        UNION ALL
        SELECT s.user_id, s.occurred_at, NULL::timestamptz, 'symptom', 'symptom_logs', s.id, 'timeline.symptom', s.severity::numeric
          FROM symptom_logs s WHERE s.deleted_at IS NULL
        UNION ALL
        SELECT w.user_id, w.recorded_at, NULL::timestamptz, 'checkin', 'wellbeing_logs', w.id, 'timeline.checkin', w.mood::numeric
          FROM wellbeing_logs w WHERE w.deleted_at IS NULL
        UNION ALL
        SELECT g.user_id, g.started_at, g.ended_at, 'glucose_event', 'glucose_events', g.id,
               CASE WHEN g.event_type = 'low' THEN 'timeline.glucose.low' ELSE 'timeline.glucose.high' END,
               g.extreme_glucose_mmol::numeric
          FROM glucose_events g
) t""",
    # Daily values of the main metrics with the share of readings outside the person's usual range and the decline flag.
    """CREATE VIEW trends WITH (security_invoker = on) AS
SELECT d.user_id, m.metric, d.local_date AS day, m.value, m.outside_pct,
       (m.metric = ANY (coalesce(d.declining_metrics, ARRAY[]::text[]))) AS declining,
       '2'::text AS calc_version, 'daily'::text AS evidence_window, d.built_at AS freshness,
       CASE WHEN m.value IS NULL THEN 'no_data' ELSE 'sufficient' END AS quality_status
  FROM daily_summary d
 CROSS JOIN LATERAL (VALUES
        ('glucose'::text, d.glucose_mean_mmol::numeric, d.glucose_outside_pct),
        ('heart_rate', d.resting_hr_bpm::numeric, d.hr_outside_pct),
        ('hrv', d.hrv_mean_ms::numeric, d.hrv_outside_pct),
        ('spo2', d.spo2_mean_pct::numeric, d.spo2_outside_pct)) AS m(metric, value, outside_pct)""",
    # Doses whose time has passed: taken, missed or skipped. Pending and extra (unscheduled) doses are not counted.
    """CREATE VIEW adherence_summary WITH (security_invoker = on) AS
SELECT d.user_id, p.period,
       count(*) FILTER (WHERE d.status IN ('taken','missed','skipped')) AS scheduled,
       count(*) FILTER (WHERE d.status = 'taken') AS taken,
       count(*) FILTER (WHERE d.status = 'missed') AS missed,
       count(*) FILTER (WHERE d.status = 'skipped') AS skipped,
       round(100.0 * count(*) FILTER (WHERE d.status = 'taken')
             / NULLIF(count(*) FILTER (WHERE d.status IN ('taken','missed','skipped')), 0), 1) AS adherence_pct,
       (SELECT coalesce(jsonb_agg(jsonb_build_object('reason', r.miss_reason, 'count', r.n) ORDER BY r.n DESC), '[]'::jsonb)
          FROM (SELECT d2.miss_reason, count(*) AS n FROM medication_log d2
                 WHERE d2.user_id = d.user_id AND d2.miss_reason IS NOT NULL
                   AND d2.scheduled_at >= now() - p.days * interval '1 day' AND d2.scheduled_at <= now()
                 GROUP BY d2.miss_reason) r) AS top_reasons,
       '2'::text AS calc_version,
       p.period AS evidence_window,
       now() AS freshness,
       CASE WHEN count(*) FILTER (WHERE d.status IN ('taken','missed','skipped')) >= 5 THEN 'sufficient' ELSE 'insufficient' END AS quality_status
  FROM medication_log d
 CROSS JOIN (VALUES ('7d', 7), ('28d', 28)) AS p(period, days)
 WHERE d.scheduled_at IS NOT NULL AND d.scheduled_at >= now() - p.days * interval '1 day' AND d.scheduled_at <= now()
 GROUP BY d.user_id, p.period, p.days""",
    """CREATE VIEW health_state WITH (security_invoker = on) AS
SELECT a.user_id, now() AS as_of,
       jsonb_build_object('mean', a.glucose_mean_mmol, 'tir_pct', a.tir_pct, 'tbr_pct', a.tbr_pct, 'tar_pct', a.tar_pct,
                          'coverage_pct', a.cgm_coverage_pct) AS glucose_state,
       jsonb_build_object('sleep_hours', a.sleep_hours) AS sleep_state,
       jsonb_build_object('steps', a.steps_total, 'exercise_min', a.exercise_min, 'resting_hr', a.resting_hr_bpm,
                          'hrv_mean_ms', a.hrv_mean_ms, 'spo2_mean_pct', a.spo2_mean_pct) AS activity_state,
       jsonb_build_object('carbs_g', a.carbs_g, 'sugar_g', a.sugar_g, 'fibre_g', a.fibre_g, 'sodium_mg', a.sodium_mg,
                          'meals_n', a.meals_n) AS nutrition_state,
       jsonb_build_object('doses_scheduled', a.doses_scheduled, 'doses_taken', a.doses_taken, 'doses_missed', a.doses_missed) AS adherence_state,
       (SELECT jsonb_build_object('last_7_days', count(*), 'latest', max(s.occurred_at))
          FROM symptom_logs s WHERE s.user_id = a.user_id AND s.deleted_at IS NULL AND s.occurred_at >= now() - interval '7 days') AS symptom_state,
       CASE WHEN a.local_date >= current_date - 2 THEN 'sufficient' ELSE 'stale' END AS quality_status,
       '2'::text AS calc_version,
       a.local_date::text AS evidence_window,
       a.built_at AS freshness
  FROM (SELECT DISTINCT ON (user_id) * FROM daily_summary ORDER BY user_id, local_date DESC) a""",
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
       (SELECT coalesce(jsonb_agg(jsonb_build_object('food', r.food, 'n', r.n, 'mean_iauc', r.mean_iauc,
                                                      'mean_peak_rise', r.mean_rise) ORDER BY r.mean_rise), '[]'::jsonb)
          FROM (SELECT lower(fl.food) AS food, count(*) AS n, round(avg(mr.iauc_2h_mmol_min), 1) AS mean_iauc,
                       round(avg(mr.rise_mmol), 1) AS mean_rise
                  FROM meal_response mr JOIN food_logs fl ON fl.id = mr.food_log_id
                 WHERE mr.user_id = u.id GROUP BY lower(fl.food) HAVING count(*) >= 2
                 ORDER BY avg(mr.rise_mmol) LIMIT 5) r) AS latest_food_responses,
       (SELECT jsonb_build_object('day', a.local_date, 'data_quality', a.data_quality)
          FROM daily_summary a WHERE a.user_id = u.id ORDER BY a.local_date DESC LIMIT 1) AS completeness,
       '2'::text AS calc_version,
       'current'::text AS evidence_window,
       now() AS freshness,
       CASE WHEN EXISTS (SELECT 1 FROM daily_summary a2 WHERE a2.user_id = u.id AND a2.local_date >= current_date - 2)
            THEN 'sufficient' ELSE 'insufficient' END AS quality_status
  FROM users u""",
]


def upgrade():
    # 1. old views, old tables (CASCADE removes the foreign keys other tables had into them), old enums, old function
    run([f"DROP VIEW IF EXISTS {v}" for v in OLD_VIEWS])
    run([f"DROP TABLE IF EXISTS {t} CASCADE" for t in OLD_TABLES])
    run(["DROP FUNCTION IF EXISTS ingestion_events_guard()"])
    run([f"DROP TYPE IF EXISTS {e}" for e in OLD_ENUMS])

    # 2. new enums, the shared Bronze guard, Bronze, Silver, Gold
    run([f"CREATE TYPE {name} AS ENUM ({values})" for name, values in NEW_ENUMS])
    run(["""CREATE FUNCTION bronze_guard() RETURNS trigger LANGUAGE plpgsql
           SET search_path = ''
           AS $$
           BEGIN
             IF (NEW.id, NEW.user_id, NEW.received_at, NEW.source, NEW.payload, NEW.checksum)
                IS DISTINCT FROM
                (OLD.id, OLD.user_id, OLD.received_at, OLD.source, OLD.payload, OLD.checksum) THEN
               RAISE EXCEPTION '%% is immutable: only processing_status may change', TG_TABLE_NAME;
             END IF;
             IF OLD.object_key IS NOT NULL AND NEW.object_key IS DISTINCT FROM OLD.object_key THEN
               RAISE EXCEPTION '%%.object_key cannot be changed once set', TG_TABLE_NAME;
             END IF;
             IF OLD.processing_status = 'deleted' AND NEW.processing_status <> 'deleted' THEN
               RAISE EXCEPTION 'a deleted Bronze row cannot be restored';
             END IF;
             RETURN NEW;
           END $$"""])
    run(bronze_tables())
    run(SILVER)
    run([f"CREATE TRIGGER trg_updated_at BEFORE UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION set_updated_at()" for t in UPDATED_AT])
    run(GOLD)

    # 3. kept tables that pointed at patient_medications now point at medications
    run([
        "ALTER TABLE refill_forecasts RENAME COLUMN patient_medication_id TO medication_id",
        "ALTER TABLE refill_forecasts ADD CONSTRAINT refill_forecasts_medication_id_fkey "
        "FOREIGN KEY (medication_id) REFERENCES medications(id) ON DELETE CASCADE",
        "ALTER TABLE interaction_alerts ADD CONSTRAINT interaction_alerts_med_a_id_fkey "
        "FOREIGN KEY (med_a_id) REFERENCES medications(id) ON DELETE CASCADE",
        "ALTER TABLE interaction_alerts ADD CONSTRAINT interaction_alerts_med_b_id_fkey "
        "FOREIGN KEY (med_b_id) REFERENCES medications(id) ON DELETE CASCADE",
    ])

    # 4. views over the new tables
    run(VIEWS)

    # 5. row-level security on every table (no policies: only the backend connects), and the layer of every table
    run(["""DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE 'ALTER TABLE public.' || quote_ident(r.tablename) || ' ENABLE ROW LEVEL SECURITY';
  END LOOP;
END $$"""])
    comments = []
    for layer, tables in LAYERS.items():
        for t in tables:
            note = f"Layer: {layer}."
            if layer == "Bronze":
                note += " Raw input as received, never edited: " + BRONZE_NOTES[t.removeprefix("bronze_")] + "."
            comments.append(f"COMMENT ON TABLE public.{t} IS '{note}'")
    run(comments)


def downgrade():
    raise RuntimeError(
        "0018 (data model v2) cannot be undone: it dropped the old tables and their rows. "
        "Restore from the CSV backup (python scripts/v2_backup.py wrote data/processed/db_backup_*) after "
        "recreating the old schema with migrations 0001 to 0016.")
