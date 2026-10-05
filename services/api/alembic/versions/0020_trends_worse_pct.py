"""Data model v2, step 4: the trends view column outside_pct becomes worse_pct (it now means the share on the worse side).

Revision ID: 0020
Revises: 0019
"""
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

VIEW = """CREATE VIEW trends WITH (security_invoker = on) AS
SELECT d.user_id, m.metric, d.local_date AS day, m.value, m.worse_pct,
       (m.metric = ANY (coalesce(d.declining_metrics, ARRAY[]::text[]))) AS declining,
       '2'::text AS calc_version, 'daily'::text AS evidence_window, d.built_at AS freshness,
       CASE WHEN m.value IS NULL THEN 'no_data' ELSE 'sufficient' END AS quality_status
  FROM daily_summary d
 CROSS JOIN LATERAL (VALUES
        ('glucose'::text, d.glucose_mean_mmol::numeric, d.glucose_worse_pct),
        ('heart_rate', d.resting_hr_bpm::numeric, d.hr_worse_pct),
        ('hrv', d.hrv_mean_ms::numeric, d.hrv_worse_pct),
        ('spo2', d.spo2_mean_pct::numeric, d.spo2_worse_pct)) AS m(metric, value, worse_pct)"""


def upgrade():
    conn = op.get_bind()
    conn.exec_driver_sql("DROP VIEW IF EXISTS trends")
    conn.exec_driver_sql(VIEW)


def downgrade():
    conn = op.get_bind()
    conn.exec_driver_sql("DROP VIEW IF EXISTS trends")
    conn.exec_driver_sql(VIEW.replace("worse_pct", "outside_pct"))
