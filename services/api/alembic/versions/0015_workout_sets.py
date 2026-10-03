"""Workout tracker tables (approved by the owner on 2026-10-03, D-056): workout_sets and new workouts columns.

Source: docs/specs/schema.md section 14 and docs/specs/workout-tracker.md. Silver layer. `workout_sets` holds one row
per set (reps, weight, time). `workouts` gains the workout type (so the weekly strength-session goal can be counted),
the end time, perceived effort, how the person felt, and a note. Heart-rate effort is derived data and is stored in
Gold (event_windows with anchor_kind = 'workout'), not here.

Revision ID: 0015
Revises: 0014
"""
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def run(statements):
    conn = op.get_bind()
    for s in statements:
        conn.exec_driver_sql(s)


def upgrade():
    run([
        "ALTER TABLE workouts ADD COLUMN workout_type text CHECK (workout_type IN ('aerobic','strength','mixed','flexibility'))",
        "ALTER TABLE workouts ADD COLUMN ended_at timestamptz",
        "ALTER TABLE workouts ADD CONSTRAINT workouts_ended_after_start CHECK (ended_at IS NULL OR ended_at > started_at)",
        "ALTER TABLE workouts ADD COLUMN perceived_effort smallint CHECK (perceived_effort BETWEEN 1 AND 10)",
        "ALTER TABLE workouts ADD COLUMN felt text CHECK (felt IN ('energised','fine','tired','unwell'))",
        "ALTER TABLE workouts ADD COLUMN note text",
        """CREATE TABLE workout_sets (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workout_id uuid NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
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
            UNIQUE (workout_id, exercise_order, set_no)
        )""",
        "CREATE INDEX workout_sets_user_performed ON workout_sets (user_id, performed_at DESC)",
        "ALTER TABLE workout_sets ENABLE ROW LEVEL SECURITY",
    ])


def downgrade():
    run([
        "DROP TABLE IF EXISTS workout_sets",
        "ALTER TABLE workouts DROP COLUMN IF EXISTS note",
        "ALTER TABLE workouts DROP COLUMN IF EXISTS felt",
        "ALTER TABLE workouts DROP COLUMN IF EXISTS perceived_effort",
        "ALTER TABLE workouts DROP CONSTRAINT IF EXISTS workouts_ended_after_start",
        "ALTER TABLE workouts DROP COLUMN IF EXISTS ended_at",
        "ALTER TABLE workouts DROP COLUMN IF EXISTS workout_type",
    ])
