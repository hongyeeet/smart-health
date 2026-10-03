"""event_log (E1-3 step 5): the append-only, tamper-evident audit trail.

Source: docs/specs/schema.md section 9 and consistency rules 6 and 9.

Supabase detail: the backend connects as the table owner, which ignores grants, so "INSERT and SELECT only" cannot
be enforced with GRANT alone. It is enforced here by triggers:
  - a BEFORE INSERT trigger fills prev_hash and hash (sha256 chain per user, system events share one chain);
  - a BEFORE UPDATE OR DELETE trigger raises, except for the one allowed path: account deletion, done through the
    SECURITY DEFINER function pseudonymise_event_log(user), which nulls user_id and empties payload and stamps
    pseudonymised_at (consistency rule 9);
  - a BEFORE TRUNCATE trigger raises.
verify_event_log_chain(user) returns the id of the first row whose link or hash does not match, or NULL.

Differences from the spec text (recorded in schema.md section 12): `user_id` and `agent_run_id` are plain uuid
columns with no foreign key (a foreign key's ON DELETE action would be an UPDATE the guard blocks), and there is
an extra column `pseudonymised_at`.

Revision ID: 0012
Revises: 0011
"""
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def run(statements):
    conn = op.get_bind()
    for s in statements:
        conn.exec_driver_sql(s)


def upgrade():
    run([
        """CREATE TABLE event_log (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            occurred_at timestamptz NOT NULL DEFAULT now(),
            user_id uuid,
            actor actor_type NOT NULL,
            event text NOT NULL,
            entity_table text,
            entity_id uuid,
            payload jsonb NOT NULL DEFAULT '{}'::jsonb,
            client_event_id uuid UNIQUE,
            agent_run_id uuid,
            prev_hash text,
            hash text NOT NULL,
            pseudonymised_at timestamptz
        )""",
        "CREATE INDEX event_log_user_occurred ON event_log (user_id, occurred_at DESC)",
        "CREATE INDEX event_log_user_id_desc ON event_log (user_id, id DESC)",
        "CREATE INDEX event_log_event ON event_log (event)",
        # the content that is hashed: stable text for every column except the two hash columns
        """CREATE FUNCTION event_log_row_hash(prev text, r event_log) RETURNS text LANGUAGE sql IMMUTABLE AS $f$
          SELECT encode(sha256(convert_to(
            coalesce(prev, '') || '|' || r.id::text || '|' ||
            to_char(r.occurred_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') || '|' ||
            coalesce(r.user_id::text, '') || '|' || r.actor::text || '|' || r.event || '|' ||
            coalesce(r.entity_table, '') || '|' || coalesce(r.entity_id::text, '') || '|' ||
            r.payload::text || '|' || coalesce(r.client_event_id::text, '') || '|' || coalesce(r.agent_run_id::text, ''),
            'UTF8')), 'hex')
        $f$""",
        """CREATE FUNCTION event_log_chain() RETURNS trigger LANGUAGE plpgsql AS $f$
        DECLARE prev text;
        BEGIN
          PERFORM pg_advisory_xact_lock(hashtextextended(coalesce(NEW.user_id::text, 'system'), 0));
          SELECT hash INTO prev FROM event_log
            WHERE user_id IS NOT DISTINCT FROM NEW.user_id AND pseudonymised_at IS NULL
            ORDER BY id DESC LIMIT 1;
          NEW.prev_hash := prev;
          NEW.pseudonymised_at := NULL;
          NEW.hash := event_log_row_hash(prev, NEW);
          RETURN NEW;
        END
        $f$""",
        "CREATE TRIGGER trg_event_log_chain BEFORE INSERT ON event_log FOR EACH ROW EXECUTE FUNCTION event_log_chain()",
        """CREATE FUNCTION event_log_guard() RETURNS trigger LANGUAGE plpgsql AS $f$
        BEGIN
          IF TG_OP = 'UPDATE' AND current_setting('app.pseudonymise', true) = 'on'
             AND NEW.id = OLD.id AND NEW.occurred_at = OLD.occurred_at AND NEW.actor = OLD.actor AND NEW.event = OLD.event
             AND NEW.entity_table IS NOT DISTINCT FROM OLD.entity_table AND NEW.entity_id IS NOT DISTINCT FROM OLD.entity_id
             AND NEW.client_event_id IS NOT DISTINCT FROM OLD.client_event_id AND NEW.agent_run_id IS NOT DISTINCT FROM OLD.agent_run_id
             AND NEW.prev_hash IS NOT DISTINCT FROM OLD.prev_hash AND NEW.hash = OLD.hash
             AND NEW.user_id IS NULL AND NEW.payload = '{}'::jsonb AND NEW.pseudonymised_at IS NOT NULL THEN
            RETURN NEW;
          END IF;
          RAISE EXCEPTION 'event_log is append-only: rows cannot be updated or deleted';
        END
        $f$""",
        "CREATE TRIGGER trg_event_log_guard BEFORE UPDATE OR DELETE ON event_log FOR EACH ROW EXECUTE FUNCTION event_log_guard()",
        """CREATE FUNCTION event_log_no_truncate() RETURNS trigger LANGUAGE plpgsql AS $f$
        BEGIN
          RAISE EXCEPTION 'event_log is append-only: it cannot be truncated';
        END
        $f$""",
        "CREATE TRIGGER trg_event_log_no_truncate BEFORE TRUNCATE ON event_log FOR EACH STATEMENT EXECUTE FUNCTION event_log_no_truncate()",
        """CREATE FUNCTION pseudonymise_event_log(p_user uuid) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $f$
        DECLARE n integer;
        BEGIN
          PERFORM set_config('app.pseudonymise', 'on', true);
          UPDATE event_log SET user_id = NULL, payload = '{}'::jsonb, pseudonymised_at = now() WHERE user_id = p_user;
          GET DIAGNOSTICS n = ROW_COUNT;
          PERFORM set_config('app.pseudonymise', 'off', true);
          RETURN n;
        END
        $f$""",
        """CREATE FUNCTION verify_event_log_chain(p_user uuid) RETURNS bigint LANGUAGE plpgsql STABLE AS $f$
        DECLARE r event_log; prev text := NULL;
        BEGIN
          FOR r IN SELECT * FROM event_log WHERE user_id IS NOT DISTINCT FROM p_user AND pseudonymised_at IS NULL ORDER BY id LOOP
            IF r.prev_hash IS DISTINCT FROM prev OR r.hash <> event_log_row_hash(prev, r) THEN
              RETURN r.id;
            END IF;
            prev := r.hash;
          END LOOP;
          RETURN NULL;
        END
        $f$""",
        "ALTER TABLE event_log ENABLE ROW LEVEL SECURITY",
        # the public API roles get nothing (Supabase only; skipped on plain Postgres)
        """DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
            EXECUTE 'REVOKE ALL ON TABLE event_log FROM anon, authenticated';
            EXECUTE 'REVOKE ALL ON FUNCTION pseudonymise_event_log(uuid) FROM PUBLIC, anon, authenticated';
            EXECUTE 'REVOKE ALL ON FUNCTION verify_event_log_chain(uuid) FROM PUBLIC, anon, authenticated';
          END IF;
        END $$""",
    ])


def downgrade():
    run([
        "DROP TABLE IF EXISTS event_log CASCADE",
        "DROP FUNCTION IF EXISTS verify_event_log_chain(uuid)",
        "DROP FUNCTION IF EXISTS pseudonymise_event_log(uuid)",
        "DROP FUNCTION IF EXISTS event_log_no_truncate()",
        "DROP FUNCTION IF EXISTS event_log_guard()",
        "DROP FUNCTION IF EXISTS event_log_chain()",
        "DROP FUNCTION IF EXISTS event_log_row_hash(text, event_log)",
    ])
