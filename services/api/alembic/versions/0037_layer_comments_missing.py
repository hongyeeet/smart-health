"""Layer comments on the four tables that had none (comments only: no data and no structure change).

Revision ID: 0037
Revises: 0036

The test `test_every_table_says_which_layer_it_belongs_to` needs every table to start its comment with "Layer: ". Four tables made
in migrations 0021 and 0023 never got one: nudge_policy, adherence_barriers, content_proposals and ai_usage_daily. All four are
written by the backend (the learning loop and the daily AI limit counter), not raw or cleaned person data, so they are "App".

Each statement can run twice (a comment is simply set again). The downgrade removes the four comments.
"""
from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None

COMMENTS = {
    "nudge_policy": "Layer: App. Per person: how often each reminder slot, template or suggestion was tried and acted on. The learning loop reads it to pick the next one (bandit state). Written by the backend only.",
    "adherence_barriers": "Layer: App. Per person per week: the pattern behind missed doses (for example evenings or weekends), worked out from the dose log. A pattern the person has not confirmed is never shown as fact.",
    "content_proposals": "Layer: App. Wording or routines drafted by an agent that wait for the person or the team to approve. Nothing here is shown as final until it is approved.",
    "ai_usage_daily": "Layer: App. One row per day and kind of AI call: how many calls were made and blocked, the tokens used and the cost. The daily limits per kind are checked against it.",
}


def upgrade():
    conn = op.get_bind()
    for table, text in COMMENTS.items():
        conn.exec_driver_sql(f"COMMENT ON TABLE {table} IS '{text.replace(chr(39), chr(39) * 2)}'")


def downgrade():
    conn = op.get_bind()
    for table in COMMENTS:
        conn.exec_driver_sql(f"COMMENT ON TABLE {table} IS NULL")
