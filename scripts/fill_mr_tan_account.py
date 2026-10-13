#!/usr/bin/env python3
"""Fill in the Data and account answers Mr Tan was missing (Joely's request, 2026-10-13; every value below was chosen by her).

Usage (from the repository root):
  python scripts/fill_mr_tan_account.py            dry run: show what would be saved, change nothing
  python scripts/fill_mr_tan_account.py --yes      do it (one transaction)

It uses the same save routine as the app (`onboarding.save_profile`), so the answers are written the way the set-up screens write
them (profile columns, history rows marked as from set-up, a raw copy of the request). Mr Tan's other data is not touched. Saving again
replaces the same set-up rows, so running it twice changes nothing. The two email addresses are FAKE (example.com is reserved and
never delivers): they exist so the screens and the reminder-email switch have an address to show.
"""
import argparse
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

from app.db import logstore  # noqa: E402
from app.services import onboarding as ob  # noqa: E402

ANSWERS = {
    "race": "Chinese",
    "waist_cm": 94,
    "diagnosed_year": 2020,
    "care_setting": "polyclinic",
    "healthier_sg": "yes",
    "hypo_last3m": "1-2",
    "hypo_awareness": "2",
    "hypo_needed_help": "no",
    "conditions": ["hypertension", "high_cholesterol"],
    "allergies": [],
    "eye_check": "over_year",
    "foot_check": "within_year",
    "lab_date": date(2026, 9, 22),
    "hba1c": 7.4,
    "hba1c_unit": "%",
    "fasting_glucose": 8.56,
    "glucose_unit": "mmol/L",
    "emergency_contact_email": "mdm.lim.demo@example.com",
}
REMINDER_EMAIL = "mr.tan.demo@example.com"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="write the answers (without it: a dry run)")
    args = ap.parse_args()
    user = logstore.MR_TAN_USER
    now = datetime.now(logstore.TZ)
    for k, v in ANSWERS.items():
        print(f"set      {k}: {v}")
    print(f"set      reminder email: {REMINDER_EMAIL} (reminders on)")
    if not args.yes:
        print("Dry run: nothing was changed. Run again with --yes to write these.")
        return 0
    with logstore.tx() as c:
        labels = ob.enum_labels(c)
        out = ob.save_profile(c, user, ANSWERS, labels, now.year, now.date())
        if out["not_saved"]:
            raise SystemExit(f"Not saved: {out['not_saved']}")
        c.execute("update user_profile set notification_email = %s, email_opt_in = true, updated_at = now() where user_id = %s", (REMINDER_EMAIL, str(user)))
        c.execute("insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'user', 'notify.email_changed', 'user_profile', %s, %s::jsonb)",
                  (str(user), str(user), '{"set": true, "opt_in": true}'))
    print("Saved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
