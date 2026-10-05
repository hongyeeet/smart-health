"""Data model v2, step 3: the decline flag looks only at the worse side of the usual range, and adherence counts prescription medicines only.

- daily_summary.{hr,hrv,spo2,glucose}_outside_pct become *_worse_pct: the share of readings on the worse side of the person's
  usual range (above p95 for heart rate and glucose, below p05 for HRV and SpO2). Getting better (lower glucose, lower heart rate)
  is not flagged.
- adherence_summary counts doses of prescription medicines only (supplements and TCM are taken less regularly and are not the point).

Revision ID: 0019
Revises: 0018
"""
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

RENAMES = [("hr_outside_pct", "hr_worse_pct"), ("hrv_outside_pct", "hrv_worse_pct"), ("spo2_outside_pct", "spo2_worse_pct"), ("glucose_outside_pct", "glucose_worse_pct")]

VIEW = """CREATE OR REPLACE VIEW adherence_summary WITH (security_invoker = on) AS
SELECT d.user_id, p.period,
       count(*) FILTER (WHERE d.status IN ('taken','missed','skipped')) AS scheduled,
       count(*) FILTER (WHERE d.status = 'taken') AS taken,
       count(*) FILTER (WHERE d.status = 'missed') AS missed,
       count(*) FILTER (WHERE d.status = 'skipped') AS skipped,
       round(100.0 * count(*) FILTER (WHERE d.status = 'taken')
             / NULLIF(count(*) FILTER (WHERE d.status IN ('taken','missed','skipped')), 0), 1) AS adherence_pct,
       (SELECT coalesce(jsonb_agg(jsonb_build_object('reason', r.miss_reason, 'count', r.n) ORDER BY r.n DESC), '[]'::jsonb)
          FROM (SELECT d2.miss_reason, count(*) AS n FROM medication_log d2 JOIN medications m2 ON m2.id = d2.medication_id AND m2.kind = 'prescription'
                 WHERE d2.user_id = d.user_id AND d2.miss_reason IS NOT NULL
                   AND d2.scheduled_at >= now() - p.days * interval '1 day' AND d2.scheduled_at <= now()
                 GROUP BY d2.miss_reason) r) AS top_reasons,
       '2'::text AS calc_version,
       p.period AS evidence_window,
       now() AS freshness,
       CASE WHEN count(*) FILTER (WHERE d.status IN ('taken','missed','skipped')) >= 5 THEN 'sufficient' ELSE 'insufficient' END AS quality_status
  FROM medication_log d
  JOIN medications m ON m.id = d.medication_id AND m.kind = 'prescription'
 CROSS JOIN (VALUES ('7d', 7), ('28d', 28)) AS p(period, days)
 WHERE d.scheduled_at IS NOT NULL AND d.scheduled_at >= now() - p.days * interval '1 day' AND d.scheduled_at <= now()
 GROUP BY d.user_id, p.period, p.days"""


def upgrade():
    conn = op.get_bind()
    for a, b in RENAMES:
        conn.exec_driver_sql(f"ALTER TABLE daily_summary RENAME COLUMN {a} TO {b}")
    conn.exec_driver_sql(VIEW.replace("%", "%%"))


def downgrade():
    conn = op.get_bind()
    for a, b in RENAMES:
        conn.exec_driver_sql(f"ALTER TABLE daily_summary RENAME COLUMN {b} TO {a}")
