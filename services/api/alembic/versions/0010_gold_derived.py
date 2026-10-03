"""Gold, derived tables (E1-3 step 3): 11 tables built by code from Silver.

Source: docs/specs/schema.md sections 3 (interaction_alerts), 4 (meal_responses, food_responses),
5 (daily_aggregates, baselines, momentum_snapshots, clinical_flags, urgent_events) and 9b (sprint_summaries,
event_windows, pattern_candidates). Everything is empty until services fill it (E9-1, E8-1, E19, E6-1).
Nulls mean "no data", never zero (schema consistency rule 2).

Revision ID: 0010
Revises: 0009
"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

TABLES = [
    "clinical_flags", "urgent_events", "daily_aggregates", "baselines", "momentum_snapshots",
    "meal_responses", "food_responses", "sprint_summaries", "event_windows", "pattern_candidates", "interaction_alerts",
]
UPDATED_AT = ["clinical_flags", "food_responses", "pattern_candidates"]


def run(statements):
    conn = op.get_bind()
    for s in statements:
        conn.exec_driver_sql(s)


def upgrade():
    run([
        """CREATE TABLE clinical_flags (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            kind text NOT NULL,
            metric text,
            severity flag_severity NOT NULL,
            status flag_status NOT NULL DEFAULT 'open',
            evidence jsonb NOT NULL,
            patient_message_key text,
            first_seen_on date NOT NULL,
            last_seen_on date NOT NULL,
            brief_id uuid REFERENCES briefs(id) ON DELETE SET NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )""",
        "CREATE INDEX clinical_flags_user_status ON clinical_flags (user_id, status, last_seen_on DESC)",
        """CREATE TABLE urgent_events (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            tier urgent_tier NOT NULL,
            trigger jsonb NOT NULL,
            shown_at timestamptz NOT NULL,
            acknowledged_at timestamptz,
            user_action text
        )""",
        "CREATE INDEX urgent_events_user_shown ON urgent_events (user_id, shown_at DESC)",
        """CREATE TABLE daily_aggregates (
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            day date NOT NULL,
            fasting_glucose_mean numeric,
            postmeal_glucose_mean numeric,
            glucose_readings_n integer,
            tir_pct numeric,
            tbr_pct numeric,
            tar_pct numeric,
            steps numeric,
            workout_min numeric,
            sleep_min numeric,
            sleep_midpoint_min numeric,
            resting_hr numeric,
            hrv_rmssd numeric,
            mood numeric,
            stress numeric,
            carbs_g numeric,
            sugar_g numeric,
            sodium_mg numeric,
            meals_n integer,
            doses_scheduled integer,
            doses_taken integer,
            adherence_pct numeric,
            logged_streams smallint,
            computed_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, day)
        )""",
        """CREATE TABLE baselines (
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            metric text NOT NULL,
            computed_on date NOT NULL,
            median numeric,
            mad numeric,
            n_days smallint,
            status text CHECK (status IN ('learning','ready')),
            PRIMARY KEY (user_id, metric, computed_on)
        )""",
        """CREATE TABLE momentum_snapshots (
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            metric text NOT NULL,
            day date NOT NULL,
            value numeric,
            z numeric,
            ewma numeric,
            slope numeric,
            accel numeric,
            PRIMARY KEY (user_id, metric, day)
        )""",
        """CREATE TABLE meal_responses (
            meal_id uuid PRIMARY KEY REFERENCES meals(id) ON DELETE CASCADE,
            baseline_mmol numeric(4,1),
            peak_rise_mmol numeric(4,1),
            iauc_mmol_min numeric(7,1),
            window_complete boolean NOT NULL,
            is_mixed boolean NOT NULL,
            dominant_food_id uuid REFERENCES foods(id) ON DELETE SET NULL,
            computed_at timestamptz NOT NULL DEFAULT now()
        )""",
        """CREATE TABLE food_responses (
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            food_id uuid NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
            n smallint NOT NULL,
            mean_iauc numeric,
            min_iauc numeric,
            max_iauc numeric,
            mean_peak_rise numeric,
            rank_pct numeric CHECK (rank_pct BETWEEN 0 AND 1),
            updated_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, food_id)
        )""",
        """CREATE TABLE sprint_summaries (
            cgm_sprint_id uuid PRIMARY KEY REFERENCES cgm_sprints(id) ON DELETE CASCADE,
            tir_pct numeric(4,1),
            tbr_pct numeric(4,1),
            tar_pct numeric(4,1),
            gmi_pct numeric(3,1),
            cv_pct numeric(4,1),
            mean_mmol numeric(4,1),
            n_valid_readings integer NOT NULL,
            computed_at timestamptz NOT NULL DEFAULT now(),
            status text CHECK (status IN ('ok','insufficient'))
        )""",
        """CREATE TABLE event_windows (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            anchor_kind text NOT NULL CHECK (anchor_kind IN ('meal','workout','dose','sleep','alcohol')),
            anchor_table text NOT NULL,
            anchor_id uuid NOT NULL,
            window_start timestamptz NOT NULL,
            window_end timestamptz NOT NULL,
            outcome_metric text NOT NULL,
            baseline_value numeric,
            outcome_value numeric,
            delta numeric,
            n_points integer NOT NULL,
            quality_ok boolean NOT NULL,
            computed_at timestamptz NOT NULL DEFAULT now(),
            CHECK (window_end > window_start),
            UNIQUE (anchor_table, anchor_id, outcome_metric)
        )""",
        "CREATE INDEX event_windows_user_kind ON event_windows (user_id, anchor_kind, window_start DESC)",
        """CREATE TABLE pattern_candidates (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            pattern_key text NOT NULL,
            anchor_kind text,
            outcome_metric text,
            n_pairs integer NOT NULL CHECK (n_pairs >= 5),
            median_delta numeric NOT NULL,
            iqr_low numeric,
            iqr_high numeric,
            first_seen_on date,
            last_seen_on date,
            status text CHECK (status IN ('open','in_brief','dismissed')),
            relationship_type relationship_type NOT NULL,
            evidence_status evidence_status NOT NULL DEFAULT 'derived',
            evidence jsonb NOT NULL,
            brief_id uuid REFERENCES briefs(id) ON DELETE SET NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )""",
        "CREATE UNIQUE INDEX pattern_candidates_open_uq ON pattern_candidates (user_id, pattern_key) WHERE status = 'open'",
        """CREATE TABLE interaction_alerts (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            med_a_id uuid NOT NULL REFERENCES patient_medications(id) ON DELETE CASCADE,
            med_b_id uuid REFERENCES patient_medications(id) ON DELETE CASCADE,
            interaction_rule_id uuid REFERENCES interaction_rules(id),
            status text NOT NULL DEFAULT 'open' CHECK (status IN ('open','acknowledged','resolved_by_clinician','not_checked')),
            created_at timestamptz NOT NULL DEFAULT now(),
            acknowledged_at timestamptz
        )""",
        "CREATE INDEX interaction_alerts_user_status ON interaction_alerts (user_id, status)",
    ])
    run([f"CREATE TRIGGER trg_updated_at BEFORE UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION set_updated_at()" for t in UPDATED_AT])
    run([f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY" for t in TABLES])


def downgrade():
    run([f"DROP TABLE IF EXISTS {t} CASCADE" for t in reversed(TABLES)])
