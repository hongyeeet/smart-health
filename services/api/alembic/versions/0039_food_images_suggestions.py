"""Meal suggestions with dish pictures: `food_images` and `food_suggestions`.

Revision ID: 0039
Revises: 0038

Decided by Hong Yi on 2026-10-14 (the menu-style Meal suggestions page).

`food_images`: ONE row per dish (`dish_key` is the dish name made lower case, letters and digits joined by dashes), shared by every person.
The picture is made once by a Gemini image model and kept in the private `food-images` storage bucket; a row that is `ready` is never
generated again. `status` is pending (waiting), generating (a worker has it), ready, or failed (tried again later, at most 3 times).

`food_suggestions`: the dishes shown to one person for one meal on one day, stored when the menu is built, so what was suggested is
on record (for the learning loop and for "what did we show on Tuesday"). `picked_at` is set when the person adds the dish to their picks.

Written so it can run twice. The downgrade drops both tables (the bucket is not touched).
"""
from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None

UP = [
    """CREATE TABLE IF NOT EXISTS food_images (
        dish_key text PRIMARY KEY,
        name text NOT NULL,
        status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','generating','ready','failed')),
        storage_key text,
        content_type text,
        model text,
        prompt_hash text,
        attempts int NOT NULL DEFAULT 0,
        last_error text,
        requested_at timestamptz NOT NULL DEFAULT now(),
        generated_at timestamptz,
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX IF NOT EXISTS food_images_waiting ON food_images (requested_at) WHERE status IN ('pending','failed','generating')",
    """CREATE TABLE IF NOT EXISTS food_suggestions (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        day date NOT NULL,
        meal text NOT NULL CHECK (meal IN ('breakfast','lunch','dinner','snack')),
        suggestion_key text NOT NULL,
        section text NOT NULL CHECK (section IN ('own','swap','general')),
        dish_key text NOT NULL REFERENCES food_images (dish_key),
        name text NOT NULL,
        payload jsonb NOT NULL DEFAULT '{}'::jsonb,
        picked_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (user_id, day, meal, suggestion_key)
    )""",
    "CREATE INDEX IF NOT EXISTS food_suggestions_user_day ON food_suggestions (user_id, day DESC)",
    "ALTER TABLE food_images ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE food_suggestions ENABLE ROW LEVEL SECURITY",
    "COMMENT ON TABLE food_images IS 'Layer: Reference. One AI-made picture per dish name, shared by everyone. Made once and kept in the private food-images bucket; a ready row is never generated again.'",
    "COMMENT ON TABLE food_suggestions IS 'Layer: App. The dishes shown to one person for one meal on one day (own meals, lighter swaps, general ideas), with the numbers shown. picked_at is set when the person adds it to their picks.'",
]


def upgrade():
    c = op.get_bind()
    for s in UP:
        c.exec_driver_sql(s)


def downgrade():
    c = op.get_bind()
    c.exec_driver_sql("DROP TABLE IF EXISTS food_suggestions")
    c.exec_driver_sql("DROP TABLE IF EXISTS food_images")
