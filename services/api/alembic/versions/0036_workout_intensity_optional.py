"""Workout rating optional: exercise_logs.intensity may be null, meaning "not rated".

Revision ID: 0036
Revises: 0035

Until now `exercise_logs.intensity` was NOT NULL (migration 0018), so a workout could not be saved without a 1 to 5 rating and the
app filled in nothing. This migration drops the NOT NULL. The 1 to 5 CHECK stays: a null passes a CHECK in Postgres, so a rating
that is given is still kept within 1 to 5. Nothing is filled in for existing or new workouts.

`exercise_logs.feeling` (how the person felt afterwards) is already nullable since migration 0018, so it needs no change. A null feeling
means "not answered".

The app code (app/db/logstore.py, app/api/routers/workouts.py, app/api/routers/logs.py) checks whether the column is nullable. Until
this migration is applied it keeps asking for the rating, with the same message as before.

Every statement can run twice: dropping a NOT NULL that is already gone, or setting one that is already there, does nothing.

Downgrade restores NOT NULL only when no workout has a null rating. If any does, it stops with a clear error and changes nothing, because
a rating cannot be made up afterwards (no value is invented).
"""
from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None

UP = [
    "ALTER TABLE exercise_logs ALTER COLUMN intensity DROP NOT NULL",
    "COMMENT ON COLUMN exercise_logs.intensity IS 'Layer: Silver. How hard the workout felt, 1 (very light) to 5 (all-out), as the person rated it. "
    "Null when the workout was not rated. Null is never counted as moderate or vigorous.'",
]

DOWN_GUARD = "SELECT count(*) FROM exercise_logs WHERE intensity IS NULL"
DOWN = [
    "ALTER TABLE exercise_logs ALTER COLUMN intensity SET NOT NULL",
    "COMMENT ON COLUMN exercise_logs.intensity IS 'Layer: Silver. How hard the workout felt, 1 (very light) to 5 (all-out), as the person rated it.'",
]


def upgrade():
    conn = op.get_bind()
    for s in UP:
        conn.exec_driver_sql(s)


def downgrade():
    conn = op.get_bind()
    unrated = conn.exec_driver_sql(DOWN_GUARD).scalar()
    if unrated:
        raise RuntimeError(
            f"Cannot restore NOT NULL on exercise_logs.intensity: {unrated} workout(s) have no rating. "
            "A rating is not invented, so these rows must be rated or removed by hand before this downgrade can run."
        )
    for s in DOWN:
        conn.exec_driver_sql(s)
