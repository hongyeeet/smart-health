"""Bronze layer: ingestion_events (raw-input log). Originals are never edited.

Source: docs/specs/schema.md section 9c and consistency rule 17; docs/specs/memory.md section 2.
Beyond the spec's column list this adds a guard trigger that makes rule 17 true in the database:
only processing_status may change (and object_key may be cleared when the user deletes the original).
A row is never deleted by the app; user deletion sets processing_status = 'deleted' and removes the object.

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def run(statements):
    conn = op.get_bind()
    for s in statements:
        conn.exec_driver_sql(s)


def upgrade():
    run([
        """CREATE TABLE ingestion_events (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            source_type text NOT NULL CHECK (source_type IN ('meal_photo','meal_text','prescription_image','medication_image','supplement_image','wearable_export','dataset_import','document')),
            object_key text,
            checksum text NOT NULL,
            received_at timestamptz NOT NULL,
            source_recorded_at timestamptz,
            source_timezone text,
            content_type text,
            schema_version text NOT NULL,
            processing_status text NOT NULL DEFAULT 'received' CHECK (processing_status IN ('received','processed','failed','deleted')),
            entry_source entry_source NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (user_id, checksum)
        )""",
        "CREATE INDEX ingestion_events_user_received ON ingestion_events (user_id, received_at DESC)",
        """CREATE FUNCTION ingestion_events_guard() RETURNS trigger LANGUAGE plpgsql
           SET search_path = ''
           AS $$
           BEGIN
             IF (NEW.id, NEW.user_id, NEW.source_type, NEW.checksum, NEW.received_at, NEW.source_recorded_at,
                 NEW.source_timezone, NEW.content_type, NEW.schema_version, NEW.entry_source, NEW.created_at)
                IS DISTINCT FROM
                (OLD.id, OLD.user_id, OLD.source_type, OLD.checksum, OLD.received_at, OLD.source_recorded_at,
                 OLD.source_timezone, OLD.content_type, OLD.schema_version, OLD.entry_source, OLD.created_at) THEN
               RAISE EXCEPTION 'ingestion_events is immutable: only processing_status may change';
             END IF;
             IF OLD.object_key IS NOT NULL AND NEW.object_key IS NOT NULL AND NEW.object_key <> OLD.object_key THEN
               RAISE EXCEPTION 'ingestion_events.object_key cannot be changed once set';
             END IF;
             IF OLD.processing_status = 'deleted' AND NEW.processing_status <> 'deleted' THEN
               RAISE EXCEPTION 'a deleted ingestion event cannot be restored';
             END IF;
             RETURN NEW;
           END $$""",
        "CREATE TRIGGER trg_ingestion_events_guard BEFORE UPDATE ON ingestion_events FOR EACH ROW EXECUTE FUNCTION ingestion_events_guard()",
    ])


def downgrade():
    run([
        "DROP TABLE IF EXISTS ingestion_events CASCADE",
        "DROP FUNCTION IF EXISTS ingestion_events_guard()",
    ])
