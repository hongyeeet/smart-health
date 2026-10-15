"""Extensions, the 33 enum types and the updated_at trigger function.

Source: docs/specs/schema.md sections 0 and 1. Nothing in this project is "validated":
evidence_status has no such value.

Revision ID: 0001
Revises: (none)
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# (type name, values) copied from docs/specs/schema.md section 1
ENUMS = [
    ("locale_code", "'en','zh','ms','ta'"),
    ("sex_type", "'female','male','other','undisclosed'"),
    ("med_kind", "'prescription','otc','supplement','tcm'"),
    ("med_status", "'active','paused','stopped'"),
    ("entry_source", "'manual','scan','onboarding_chat','health_connect','healthkit','file_import','cgm','replay','demo_dataset','system'"),
    ("scan_status", "'uploaded','extracting','needs_review','confirmed','rejected','failed'"),
    ("dose_status", "'scheduled','taken','taken_late_logged','unconfirmed','missed','skipped_by_plan'"),
    ("miss_reason", "'forgot','side_effects','ran_out','felt_fine','cost','away_from_home','other'"),
    ("interaction_severity", "'minor','moderate','major','unknown'"),
    ("glucose_context", "'fasting','pre_meal','post_meal_2h','bedtime','random','cgm'"),
    ("meal_type", "'breakfast','lunch','dinner','snack','drink'"),
    ("gi_category", "'low','medium','high','unknown'"),
    ("sample_metric", "'steps','heart_rate','resting_heart_rate','hrv_rmssd','sleep_session','spo2','stress_score','active_energy','distance','skin_temp','eda'"),
    ("lab_kind", "'hba1c','fasting_glucose','total_chol','ldl','hdl','triglycerides','creatinine','uacr','egfr_reported'"),
    ("timeline_stream", "'meal','dose','workout','glucose_event','symptom','sleep','checkin','urgent'"),
    ("workout_intensity", "'light','moderate','vigorous'"),
    ("flag_severity", "'watch','review','urgent'"),
    ("flag_status", "'open','acknowledged','in_brief','resolved','dismissed'"),
    ("urgent_tier", "'hypo_selfcare','seek_care_today','urgent_now'"),
    ("fact_category", "'preference','routine','barrier','food_response','goal','context'"),
    ("fact_status", "'proposed','active','superseded','rejected'"),
    ("appointment_kind", "'gp_review','diabetes_review','eye_screening','foot_screening','kidney_test','hba1c_test','vaccination','dental','other'"),
    ("appointment_status", "'suggested','planned','completed','cancelled','missed'"),
    ("brief_status", "'generating','ready','failed','superseded'"),
    ("consent_kind", "'data_processing','brief_sharing','calendar_access','caregiver_view','research_use'"),
    ("notification_kind", "'dose_reminder','dose_renudge','miss_reason','checkin','nudge','refill','appointment','urgent','clash','brief_ready'"),
    ("actor_type", "'user','agent','system','clinician_link'"),
    ("guard_verdict", "'pass','blocked_med_advice','blocked_diagnosis','urgent','blocked_injection','blocked_uncited','blocked_other'"),
    ("knowledge_kind", "'drug','lifestyle','hypo_guidance','condition_education','food'"),
    ("evidence_status", "'observed','derived','inferred','reference_matched'"),
    ("relationship_type", "'user_reported','temporal_association','observed_association','repeated_observation'"),
    ("goal_kind", "'weekly_moderate_minutes','weekly_strength_sessions','daily_steps','sleep_hours','fasting_glucose_range','custom'"),
    ("device_kind", "'watch','cgm','glucometer','phone_camera','other'"),
]


def run(statements):
    conn = op.get_bind()
    for s in statements:
        conn.exec_driver_sql(s)


def upgrade():
    assert len(ENUMS) == 33
    run([
        "CREATE SCHEMA IF NOT EXISTS extensions",
        # Extensions live in the "extensions" schema (Supabase convention); types are used as extensions.vector, extensions.citext.
        "CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions",
        "CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA extensions",
        "CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA extensions",
    ])
    run([f"CREATE TYPE {name} AS ENUM ({values})" for name, values in ENUMS])
    run([
        # Used by every mutable table: updated_at is maintained by trigger (schema.md section 0).
        """CREATE FUNCTION set_updated_at() RETURNS trigger LANGUAGE plpgsql
           SET search_path = ''
           AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END $$""",
    ])


def downgrade():
    run(["DROP FUNCTION IF EXISTS set_updated_at()"])
    run([f"DROP TYPE IF EXISTS {name}" for name, _ in reversed(ENUMS)])
    run([
        "DROP EXTENSION IF EXISTS pg_trgm",
        "DROP EXTENSION IF EXISTS citext",
        "DROP EXTENSION IF EXISTS vector",
    ])
