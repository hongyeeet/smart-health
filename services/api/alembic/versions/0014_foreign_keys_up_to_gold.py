"""Foreign keys that point from Silver up to Gold and Operations (E1-3 step 7).

Four Silver columns were created as plain nullable uuid columns because their targets did not exist (migrations
0004 to 0006); one Gold column breaks the conversations / memory_episodes loop (0011). They are added now.
Source: docs/specs/data-flow.md section 6 and docs/backlog/details/e1-3-handover.md section 3.

Revision ID: 0014
Revises: 0013
"""
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

CONSTRAINTS = [
    ("symptom_checkins", "symptom_checkins_triggered_by_flag_id_fkey", "FOREIGN KEY (triggered_by_flag_id) REFERENCES clinical_flags(id) ON DELETE SET NULL"),
    ("appointments", "appointments_brief_id_fkey", "FOREIGN KEY (brief_id) REFERENCES briefs(id) ON DELETE SET NULL"),
    ("doctor_questions", "doctor_questions_brief_id_fkey", "FOREIGN KEY (brief_id) REFERENCES briefs(id) ON DELETE SET NULL"),
    ("prescription_scans", "prescription_scans_agent_run_id_fkey", "FOREIGN KEY (agent_run_id) REFERENCES agent_runs(id) ON DELETE SET NULL"),
    ("conversations", "conversations_summary_episode_id_fkey", "FOREIGN KEY (summary_episode_id) REFERENCES memory_episodes(id) ON DELETE SET NULL"),
]


def run(statements):
    conn = op.get_bind()
    for s in statements:
        conn.exec_driver_sql(s)


def upgrade():
    run([f"ALTER TABLE {t} ADD CONSTRAINT {n} {d}" for t, n, d in CONSTRAINTS])


def downgrade():
    run([f"ALTER TABLE {t} DROP CONSTRAINT IF EXISTS {n}" for t, n, _ in reversed(CONSTRAINTS)])
