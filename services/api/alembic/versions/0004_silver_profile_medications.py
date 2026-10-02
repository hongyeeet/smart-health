"""Silver, part 1: profile, consents, prescription scans, medications, doses (10 tables).

Source: docs/specs/schema.md sections 2, 3 and 9b (prescription_scans changes, medication_ingredients).

NOTE: prescription_scans.agent_run_id points at agent_runs, an Operations table created in E1-3.
It is a plain nullable uuid here; Hong Yi adds the foreign key at the end of E1-3
(docs/backlog/details/e1-3-handover.md).

Revision ID: 0004
Revises: 0003
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

TABLES = [
    "patient_profiles", "conditions", "allergies", "family_history", "consents", "prescription_scans",
    "patient_medications", "medication_ingredients", "dose_events", "refill_forecasts",
]
UPDATED_AT = ["patient_profiles", "conditions", "allergies", "prescription_scans", "patient_medications"]


def run(statements):
    conn = op.get_bind()
    for s in statements:
        conn.exec_driver_sql(s)


def upgrade():
    run([
        """CREATE TABLE patient_profiles (
            user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            display_name text NOT NULL,
            birth_year smallint CHECK (birth_year BETWEEN 1900 AND 2100),
            sex sex_type NOT NULL DEFAULT 'undisclosed',
            height_cm numeric(5,1) CHECK (height_cm BETWEEN 100 AND 250),
            weight_kg numeric(5,1) CHECK (weight_kg BETWEEN 25 AND 300),
            diabetes_type text NOT NULL CHECK (diabetes_type = 'type2'),
            diagnosed_year smallint,
            last_hba1c_pct numeric(3,1) CHECK (last_hba1c_pct BETWEEN 4.0 AND 20.0),
            last_hba1c_on date,
            targets jsonb,
            smoker boolean,
            onboarding_method text CHECK (onboarding_method IN ('form','chat')),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )""",
        """CREATE TABLE conditions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name text NOT NULL,
            code text,
            since_year smallint,
            notes text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            deleted_at timestamptz
        )""",
        "CREATE INDEX conditions_user ON conditions (user_id, created_at)",
        """CREATE TABLE allergies (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            substance text NOT NULL,
            reaction text,
            severity text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            deleted_at timestamptz
        )""",
        "CREATE INDEX allergies_user ON allergies (user_id, created_at)",
        """CREATE TABLE family_history (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            relation text NOT NULL,
            condition text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )""",
        "CREATE INDEX family_history_user ON family_history (user_id, created_at)",
        """CREATE TABLE consents (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            kind consent_kind NOT NULL,
            version text NOT NULL,
            granted_at timestamptz NOT NULL,
            revoked_at timestamptz
        )""",
        "CREATE UNIQUE INDEX consents_one_active_per_kind ON consents (user_id, kind) WHERE revoked_at IS NULL",
        # section 3 plus the 9b additions (item_type, photo_count, quality_ok, prompt_version, extraction_review)
        """CREATE TABLE prescription_scans (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            image_key text NOT NULL,
            status scan_status NOT NULL DEFAULT 'uploaded',
            extraction jsonb,
            model_id text,
            agent_run_id uuid,
            error text,
            item_type text CHECK (item_type IN ('prescription_label','blister_or_box','supplement','tcm','otc','unknown')),
            photo_count smallint NOT NULL DEFAULT 1,
            quality_ok boolean,
            prompt_version text,
            extraction_review jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )""",
        "CREATE INDEX prescription_scans_user ON prescription_scans (user_id, created_at DESC)",
        """CREATE TABLE patient_medications (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            drug_reference_id uuid REFERENCES drug_reference(id),
            display_name text NOT NULL,
            kind med_kind NOT NULL,
            strength text,
            dose_amount numeric(6,2),
            dose_unit text,
            times_per_day smallint CHECK (times_per_day BETWEEN 1 AND 6),
            schedule_times time[] NOT NULL,
            with_food boolean NOT NULL DEFAULT false,
            window_minutes smallint NOT NULL DEFAULT 120 CHECK (window_minutes BETWEEN 30 AND 360),
            instructions text,
            prescriber text,
            prescribed_on date,
            start_on date NOT NULL,
            end_on date,
            quantity_dispensed integer,
            status med_status NOT NULL DEFAULT 'active',
            source entry_source NOT NULL,
            scan_id uuid REFERENCES prescription_scans(id),
            confirmed_by_user_at timestamptz NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CHECK (end_on IS NULL OR end_on >= start_on),
            CHECK (times_per_day IS NULL OR cardinality(schedule_times) = times_per_day)
        )""",
        "CREATE INDEX patient_medications_user ON patient_medications (user_id, status)",
        """CREATE TABLE medication_ingredients (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_medication_id uuid NOT NULL REFERENCES patient_medications(id) ON DELETE CASCADE,
            ingredient_name text NOT NULL,
            drug_reference_id uuid REFERENCES drug_reference(id),
            amount numeric,
            unit text,
            source text CHECK (source IN ('label_photo','user'))
        )""",
        "CREATE INDEX medication_ingredients_med ON medication_ingredients (patient_medication_id)",
        """CREATE TABLE dose_events (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            patient_medication_id uuid NOT NULL REFERENCES patient_medications(id) ON DELETE CASCADE,
            scheduled_at timestamptz NOT NULL,
            window_end_at timestamptz NOT NULL,
            status dose_status NOT NULL DEFAULT 'scheduled',
            confirmed_at timestamptz,
            miss_reason miss_reason,
            miss_note text,
            reason_captured_at timestamptz,
            UNIQUE (patient_medication_id, scheduled_at),
            CHECK (window_end_at > scheduled_at),
            CHECK (status <> 'missed' OR miss_reason IS NOT NULL),
            CHECK (status NOT IN ('taken','taken_late_logged') OR confirmed_at IS NOT NULL)
        )""",
        "CREATE INDEX dose_events_user_scheduled ON dose_events (user_id, scheduled_at DESC)",
        """CREATE TABLE refill_forecasts (
            patient_medication_id uuid PRIMARY KEY REFERENCES patient_medications(id) ON DELETE CASCADE,
            remaining_units numeric,
            runs_out_on date,
            reminder_sent_at timestamptz,
            computed_at timestamptz NOT NULL DEFAULT now()
        )""",
    ])
    run([f"CREATE TRIGGER trg_updated_at BEFORE UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION set_updated_at()" for t in UPDATED_AT])


def downgrade():
    run([f"DROP TABLE IF EXISTS {t} CASCADE" for t in reversed(TABLES)])
