"""Email notifications: a Gmail address per person, and a delivery marker on every notification.

Revision ID: 0031
Revises: 0030

Decided by Hong Yi on 2026-10-10. A reminder is an in-app notification first. When the person gave an email address at onboarding (and
has not turned emails off), a dispatcher also sends it as an email through a Workato recipe. To do that without ever sending the same
thing twice, each notification now records what happened to its email:

  delivery_status   null = not an email candidate yet, 'pending' = to be sent, 'sent', 'failed', 'skipped' (nothing to send to, or history)
  delivered_at      when the recipe accepted it
  delivery_attempts how many times it was tried (a failed one is retried a few times, then left as failed)
  delivery_error    a short reason, never an address or a token
  delivery_to       'person' (their own address) or 'contact' (their emergency contact's address, for an urgent alert)

Every notification that already exists is history and is marked 'skipped', so turning this on can never send old reminders.
`user_profile` gets the person's email, an on/off switch, and the emergency contact's email (the name and phone were already there).
Written so it can run twice.
"""
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None

UP = [
    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS delivery_status text",
    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS delivered_at timestamptz",
    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS delivery_attempts integer NOT NULL DEFAULT 0",
    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS delivery_error text",
    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS delivery_to text NOT NULL DEFAULT 'person'",
    "UPDATE notifications SET delivery_status = 'skipped' WHERE delivery_status IS NULL",
    "DO $$ BEGIN ALTER TABLE notifications ADD CONSTRAINT notifications_delivery_status_chk "
    "CHECK (delivery_status IN ('pending','sent','failed','skipped')); EXCEPTION WHEN duplicate_object THEN NULL; END $$",
    "DO $$ BEGIN ALTER TABLE notifications ADD CONSTRAINT notifications_delivery_to_chk "
    "CHECK (delivery_to IN ('person','contact')); EXCEPTION WHEN duplicate_object THEN NULL; END $$",
    "CREATE INDEX IF NOT EXISTS notifications_delivery_pending ON notifications (scheduled_for) WHERE delivery_status = 'pending'",
    "ALTER TABLE user_profile ADD COLUMN IF NOT EXISTS notification_email text",
    "ALTER TABLE user_profile ADD COLUMN IF NOT EXISTS email_opt_in boolean NOT NULL DEFAULT true",
    "ALTER TABLE user_profile ADD COLUMN IF NOT EXISTS emergency_contact_email text",
    "COMMENT ON COLUMN notifications.delivery_status IS 'Email delivery: pending (to send), sent, failed, skipped (nothing to send to, or history). null never occurs after 0031 for new rows written by the app.'",
    "COMMENT ON COLUMN user_profile.notification_email IS 'Where reminder emails go (a Gmail address given at onboarding). Null: no emails.'",
    "COMMENT ON COLUMN user_profile.email_opt_in IS 'false: the person turned reminder emails off. Urgent alerts to the emergency contact are not affected.'",
]


def upgrade():
    c = op.get_bind()
    for s in UP:
        c.exec_driver_sql(s)


def downgrade():
    c = op.get_bind()
    for s in (
        "DROP INDEX IF EXISTS notifications_delivery_pending",
        "ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_delivery_to_chk",
        "ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_delivery_status_chk",
        "ALTER TABLE notifications DROP COLUMN IF EXISTS delivery_to, DROP COLUMN IF EXISTS delivery_error, DROP COLUMN IF EXISTS delivery_attempts, "
        "DROP COLUMN IF EXISTS delivered_at, DROP COLUMN IF EXISTS delivery_status",
        "ALTER TABLE user_profile DROP COLUMN IF EXISTS emergency_contact_email, DROP COLUMN IF EXISTS email_opt_in, DROP COLUMN IF EXISTS notification_email",
    ):
        c.exec_driver_sql(s)
