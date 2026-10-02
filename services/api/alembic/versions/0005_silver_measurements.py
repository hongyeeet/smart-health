"""Silver, part 2: meals, glucose, wearables, workouts, symptoms, labs, BP, body (14 tables).

Source: docs/specs/schema.md sections 4, 9b and 9c (meal_analyses).

NOTE: symptom_checkins.triggered_by_flag_id points at clinical_flags (Gold, E1-3). It is a plain
nullable uuid here; Hong Yi adds the foreign key at the end of E1-3.
Small tightenings beyond the spec text: blood_pressure_readings.systolic and diastolic are NOT NULL.

Revision ID: 0005
Revises: 0004
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

TABLES = [
    "cgm_sprints", "meals", "meal_analyses", "meal_items", "glucose_readings", "health_samples", "sleep_sessions",
    "workouts", "mood_checkins", "symptom_checkins", "symptom_logs", "lab_results", "blood_pressure_readings",
    "body_measurements",
]
UPDATED_AT = ["meals"]


def run(statements):
    conn = op.get_bind()
    for s in statements:
        conn.exec_driver_sql(s)


def upgrade():
    run([
        """CREATE TABLE cgm_sprints (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            device text,
            started_at timestamptz NOT NULL,
            ended_at timestamptz,
            planned_days smallint DEFAULT 14,
            purpose text,
            created_at timestamptz NOT NULL DEFAULT now()
        )""",
        # at most one open sprint per user
        "CREATE UNIQUE INDEX cgm_sprints_one_open_per_user ON cgm_sprints (user_id) WHERE ended_at IS NULL",
        """CREATE TABLE meals (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            eaten_at timestamptz NOT NULL,
            meal_type meal_type NOT NULL,
            photo_key text,
            description text,
            source entry_source NOT NULL,
            deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )""",
        "CREATE INDEX meals_user_eaten ON meals (user_id, eaten_at DESC)",
        """CREATE TABLE meal_analyses (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            meal_id uuid NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
            ingestion_event_id uuid REFERENCES ingestion_events(id),
            model_id text NOT NULL,
            prompt_version text NOT NULL,
            raw_output jsonb NOT NULL,
            status text NOT NULL DEFAULT 'ok' CHECK (status IN ('ok','failed','superseded')),
            created_at timestamptz NOT NULL DEFAULT now()
        )""",
        "CREATE INDEX meal_analyses_meal ON meal_analyses (meal_id, created_at DESC)",
        """CREATE TABLE meal_items (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            meal_id uuid NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
            food_id uuid REFERENCES foods(id),
            custom_name text,
            portion_multiplier numeric(4,2) NOT NULL DEFAULT 1.0 CHECK (portion_multiplier BETWEEN 0.1 AND 5),
            carbs_g numeric,
            sugar_g numeric,
            sodium_mg numeric,
            kcal numeric,
            protein_g numeric,
            fat_g numeric,
            fibre_g numeric,
            alcohol_units numeric(3,1) NOT NULL DEFAULT 0,
            estimated_by text CHECK (estimated_by IN ('dataset','llm_estimate','user','food_db')),
            estimate_confidence numeric(3,2) CHECK (estimate_confidence BETWEEN 0 AND 1),
            evidence_status evidence_status NOT NULL DEFAULT 'inferred',
            analysis_id uuid REFERENCES meal_analyses(id),
            CHECK (food_id IS NOT NULL OR custom_name IS NOT NULL)
        )""",
        "CREATE INDEX meal_items_meal ON meal_items (meal_id)",
        """CREATE TABLE glucose_readings (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            measured_at timestamptz NOT NULL,
            value_mmol numeric(4,1) NOT NULL CHECK (value_mmol BETWEEN 1.0 AND 35.0),
            context glucose_context NOT NULL,
            source entry_source NOT NULL,
            external_id text,
            cgm_sprint_id uuid REFERENCES cgm_sprints(id),
            device text,
            quality_ok boolean NOT NULL DEFAULT true,
            native_interval_min smallint,
            meal_id uuid REFERENCES meals(id),
            note text,
            deleted_at timestamptz,
            UNIQUE (user_id, source, external_id)
        )""",
        "CREATE INDEX glucose_readings_user_measured ON glucose_readings (user_id, measured_at DESC)",
        """CREATE TABLE health_samples (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            metric sample_metric NOT NULL,
            start_at timestamptz NOT NULL,
            end_at timestamptz NOT NULL,
            value numeric NOT NULL,
            unit text NOT NULL,
            detail jsonb,
            source entry_source NOT NULL,
            device text,
            external_id text NOT NULL,
            CHECK (end_at >= start_at),
            UNIQUE (user_id, source, external_id)
        )""",
        "CREATE INDEX health_samples_user_metric_start ON health_samples (user_id, metric, start_at DESC)",
        """CREATE TABLE sleep_sessions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            start_at timestamptz NOT NULL,
            end_at timestamptz NOT NULL,
            asleep_min integer NOT NULL,
            awake_min integer,
            light_min integer,
            deep_min integer,
            rem_min integer,
            efficiency_pct numeric(4,1),
            source entry_source NOT NULL,
            device text,
            external_id text NOT NULL,
            CHECK (end_at > start_at),
            UNIQUE (user_id, source, external_id)
        )""",
        "CREATE INDEX sleep_sessions_user_start ON sleep_sessions (user_id, start_at DESC)",
        """CREATE TABLE workouts (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            started_at timestamptz NOT NULL,
            duration_s integer NOT NULL CHECK (duration_s > 0),
            activity text NOT NULL,
            intensity workout_intensity NOT NULL,
            kcal numeric,
            avg_hr numeric,
            source entry_source NOT NULL,
            external_id text,
            deleted_at timestamptz,
            UNIQUE (user_id, source, external_id)
        )""",
        "CREATE INDEX workouts_user_started ON workouts (user_id, started_at DESC)",
        """CREATE TABLE mood_checkins (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            checked_on date NOT NULL,
            mood smallint CHECK (mood BETWEEN 1 AND 5),
            stress smallint CHECK (stress BETWEEN 1 AND 5),
            sleep_quality smallint CHECK (sleep_quality BETWEEN 1 AND 5),
            energy smallint CHECK (energy BETWEEN 1 AND 5),
            note text,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (user_id, checked_on)
        )""",
        """CREATE TABLE symptom_checkins (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            question_key text NOT NULL,
            triggered_by_flag_id uuid,
            asked_at timestamptz,
            answered_at timestamptz,
            answer jsonb,
            skipped boolean DEFAULT false
        )""",
        "CREATE INDEX symptom_checkins_user_asked ON symptom_checkins (user_id, asked_at DESC)",
        """CREATE TABLE symptom_logs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            occurred_at timestamptz NOT NULL,
            symptom text NOT NULL,
            symptom_code text,
            severity smallint CHECK (severity BETWEEN 1 AND 5),
            note text,
            source text CHECK (source IN ('user','checkin')),
            checkin_id uuid REFERENCES symptom_checkins(id),
            deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        )""",
        "CREATE INDEX symptom_logs_user_occurred ON symptom_logs (user_id, occurred_at DESC)",
        """CREATE TABLE lab_results (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            kind lab_kind NOT NULL,
            value numeric NOT NULL,
            unit text NOT NULL,
            taken_on date NOT NULL,
            source entry_source NOT NULL,
            external_id text,
            note text,
            deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (user_id, source, external_id)
        )""",
        "CREATE INDEX lab_results_user_kind_taken ON lab_results (user_id, kind, taken_on DESC)",
        """CREATE TABLE blood_pressure_readings (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            measured_at timestamptz NOT NULL,
            systolic smallint NOT NULL CHECK (systolic BETWEEN 60 AND 260),
            diastolic smallint NOT NULL CHECK (diastolic BETWEEN 30 AND 160),
            pulse smallint CHECK (pulse BETWEEN 30 AND 220),
            context text CHECK (context IN ('home','clinic')),
            source entry_source NOT NULL,
            external_id text,
            deleted_at timestamptz,
            CHECK (diastolic < systolic),
            UNIQUE (user_id, source, external_id)
        )""",
        "CREATE INDEX bp_user_measured ON blood_pressure_readings (user_id, measured_at DESC)",
        """CREATE TABLE body_measurements (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            measured_at timestamptz NOT NULL,
            weight_kg numeric(5,1) CHECK (weight_kg BETWEEN 25 AND 300),
            waist_cm numeric(5,1) CHECK (waist_cm BETWEEN 40 AND 200),
            source entry_source NOT NULL,
            external_id text,
            deleted_at timestamptz,
            CHECK (weight_kg IS NOT NULL OR waist_cm IS NOT NULL),
            UNIQUE (user_id, source, external_id)
        )""",
        "CREATE INDEX body_user_measured ON body_measurements (user_id, measured_at DESC)",
    ])
    run([f"CREATE TRIGGER trg_updated_at BEFORE UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION set_updated_at()" for t in UPDATED_AT])


def downgrade():
    run([f"DROP TABLE IF EXISTS {t} CASCADE" for t in reversed(TABLES)])
