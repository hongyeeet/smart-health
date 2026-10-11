"""Onboarding answers and medicine stock: the columns and the four small tables the onboarding rewrite needs, plus the stock columns.

Revision ID: 0032
Revises: 0031

Decided by Joely on 2026-10-11 (docs/specs/implementation-plan-2026-10-11.md, section 13, item 1): onboarding answers go into the
user tables, and medicine stock is kept on `medications` itself (no stock events table).

Checked against the live database at 0031 on 2026-10-11. Four tables the plan assumed existed were dropped by 0018 (the data
model v2 rebuild) and never recreated, so this migration creates them: body_measurements (waist), conditions, allergies and
devices. Nothing is dropped here, and every statement can run twice.

Rows written from onboarding carry source 'onboarding' (a new entry_source value). A save replaces only its own rows (soft
delete, then insert), so rows entered on another screen are never touched and saving the same answers twice leaves one copy.
Each of the four tables keeps `bronze_id`, the onboarding form submission it came from (bronze_profile), as the v2 design asks.

lab_results is not changed: it already holds HbA1c, fasting glucose and fasting insulin. Cholesterol is neither in the table nor
in the onboarding form, so it is not added here.

`user_profile.hypo_symptoms` is a jsonb object because the low-glucose answers are not one column each: the awareness score
(1 always notices a hypo coming, 7 never) and whether help was needed in the last 12 months are stored under its keys.
`onboarding_completed_at` is not added to user_profile: users.onboarding_completed_at already exists (0002).

Downgrade drops only what this migration adds. The enum value 'onboarding' stays (PostgreSQL cannot remove an enum value),
and dropping the four tables or the new columns deletes the data in them.
"""
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None

UP = [
    # the marker for every row written from onboarding; PostgreSQL needs this in its own statement (0017 does the same)
    "ALTER TYPE entry_source ADD VALUE IF NOT EXISTS 'onboarding'",
    # diabetes history and low glucose history (user_profile)
    "ALTER TABLE user_profile ADD COLUMN IF NOT EXISTS diagnosed_year smallint CHECK (diagnosed_year BETWEEN 1900 AND 2100)",
    "ALTER TABLE user_profile ADD COLUMN IF NOT EXISTS care_setting text CHECK (care_setting IN ('polyclinic','gp','hospital','none'))",
    "ALTER TABLE user_profile ADD COLUMN IF NOT EXISTS healthier_sg text CHECK (healthier_sg IN ('yes','no','unsure'))",
    "ALTER TABLE user_profile ADD COLUMN IF NOT EXISTS hypo_last_3m text CHECK (hypo_last_3m IN ('0','1-2','3+','unsure'))",
    "ALTER TABLE user_profile ADD COLUMN IF NOT EXISTS hypo_symptoms jsonb CHECK (hypo_symptoms IS NULL OR jsonb_typeof(hypo_symptoms) = 'object')",
    # medicine stock (medications)
    "ALTER TABLE medications ADD COLUMN IF NOT EXISTS stock_count numeric CHECK (stock_count IS NULL OR stock_count >= 0)",
    "ALTER TABLE medications ADD COLUMN IF NOT EXISTS stock_unit text",
    "ALTER TABLE medications ADD COLUMN IF NOT EXISTS stock_updated_at timestamptz",
    # waist (and weight, for the same table's rule that a row holds at least one measurement)
    """CREATE TABLE IF NOT EXISTS body_measurements (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        measured_at timestamptz NOT NULL DEFAULT now(),
        weight_kg numeric(5,1) CHECK (weight_kg BETWEEN 25 AND 300),
        waist_cm numeric(5,1) CHECK (waist_cm BETWEEN 40 AND 200),
        source entry_source NOT NULL,
        bronze_id uuid NOT NULL REFERENCES bronze_profile(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        deleted_at timestamptz,
        CHECK (weight_kg IS NOT NULL OR waist_cm IS NOT NULL)
    )""",
    "CREATE INDEX IF NOT EXISTS body_measurements_user_measured ON body_measurements (user_id, measured_at DESC)",
    # other conditions: one row per condition (code is the form's code; code null is the free-text 'other' condition)
    """CREATE TABLE IF NOT EXISTS conditions (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name text NOT NULL,
        code text,
        source entry_source NOT NULL,
        bronze_id uuid NOT NULL REFERENCES bronze_profile(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        deleted_at timestamptz
    )""",
    "CREATE INDEX IF NOT EXISTS conditions_user ON conditions (user_id, created_at)",
    # allergies: one row per allergy
    """CREATE TABLE IF NOT EXISTS allergies (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        substance text NOT NULL,
        reaction text,
        source entry_source NOT NULL,
        bronze_id uuid NOT NULL REFERENCES bronze_profile(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        deleted_at timestamptz
    )""",
    "CREATE INDEX IF NOT EXISTS allergies_user ON allergies (user_id, created_at)",
    # the chosen watch or glucose sensor. status null: chosen during onboarding, not connected yet
    """CREATE TABLE IF NOT EXISTS devices (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        kind text NOT NULL CHECK (kind IN ('watch','cgm')),
        label text NOT NULL,
        status text CHECK (status IN ('connected','disconnected')),
        source entry_source NOT NULL,
        bronze_id uuid NOT NULL REFERENCES bronze_profile(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        deleted_at timestamptz
    )""",
    "CREATE INDEX IF NOT EXISTS devices_user ON devices (user_id, kind)",
    # every new table: row-level security on, as on every other table (no policies: only the backend connects)
    "ALTER TABLE body_measurements ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE conditions ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE allergies ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE devices ENABLE ROW LEVEL SECURITY",
    # updated_at kept by the shared trigger (body_measurements rows are not edited, so it has none)
    ("DO $$ BEGIN CREATE TRIGGER trg_updated_at BEFORE UPDATE ON conditions FOR EACH ROW EXECUTE FUNCTION set_updated_at(); "
    "EXCEPTION WHEN duplicate_object THEN NULL; END $$"),
    ("DO $$ BEGIN CREATE TRIGGER trg_updated_at BEFORE UPDATE ON allergies FOR EACH ROW EXECUTE FUNCTION set_updated_at(); "
    "EXCEPTION WHEN duplicate_object THEN NULL; END $$"),
    ("DO $$ BEGIN CREATE TRIGGER trg_updated_at BEFORE UPDATE ON devices FOR EACH ROW EXECUTE FUNCTION set_updated_at(); "
    "EXCEPTION WHEN duplicate_object THEN NULL; END $$"),
    "COMMENT ON TABLE body_measurements IS 'Layer: Silver. Body measurements. Onboarding writes the waist (source onboarding), one row per save only when the value changed.'",
    "COMMENT ON TABLE conditions IS 'Layer: Silver. Conditions the person has. Onboarding replaces its own rows (source onboarding) on each save; code null is the free-text other condition.'",
    "COMMENT ON TABLE allergies IS 'Layer: Silver. Allergies, one row each. Onboarding replaces its own rows (source onboarding) on each save.'",
    "COMMENT ON TABLE devices IS 'Layer: Silver. The watch or glucose sensor the person chose. Status null: chosen, not connected yet.'",
    "COMMENT ON COLUMN user_profile.diagnosed_year IS 'Year the person was told they have type 2 diabetes (onboarding).'",
    "COMMENT ON COLUMN user_profile.care_setting IS 'Where the person usually goes for diabetes care: polyclinic, gp, hospital or none (onboarding).'",
    "COMMENT ON COLUMN user_profile.healthier_sg IS 'Healthier SG enrolment: yes, no or unsure (onboarding).'",
    "COMMENT ON COLUMN user_profile.hypo_last_3m IS 'Hypos in the last 3 months: 0, 1-2, 3+ or unsure (onboarding).'",
    "COMMENT ON COLUMN user_profile.hypo_symptoms IS 'Low glucose answers (onboarding): awareness (1 always notices a hypo coming, 7 never) and needed_help_12m (yes or no).'",
    "COMMENT ON COLUMN medications.stock_count IS 'Tablets, capsules or doses left in hand. Goes down by one dose each time a dose is marked taken. Never negative.'",
    "COMMENT ON COLUMN medications.stock_unit IS 'What stock_count counts, for example tablets or capsules.'",
    "COMMENT ON COLUMN medications.stock_updated_at IS 'When stock_count last changed (a purchase, a dose taken, or a number typed in).'",
]

DOWN = [
    "DROP TABLE IF EXISTS devices",
    "DROP TABLE IF EXISTS allergies",
    "DROP TABLE IF EXISTS conditions",
    "DROP TABLE IF EXISTS body_measurements",
    "ALTER TABLE medications DROP COLUMN IF EXISTS stock_updated_at, DROP COLUMN IF EXISTS stock_unit, DROP COLUMN IF EXISTS stock_count",
    ("ALTER TABLE user_profile DROP COLUMN IF EXISTS hypo_symptoms, DROP COLUMN IF EXISTS hypo_last_3m, "
    "DROP COLUMN IF EXISTS healthier_sg, DROP COLUMN IF EXISTS care_setting, DROP COLUMN IF EXISTS diagnosed_year"),
]


def upgrade():
    c = op.get_bind()
    for s in UP:
        c.exec_driver_sql(s)


def downgrade():
    # The enum value 'onboarding' is left in place: PostgreSQL cannot remove an enum value (0017 does the same).
    c = op.get_bind()
    for s in DOWN:
        c.exec_driver_sql(s)
