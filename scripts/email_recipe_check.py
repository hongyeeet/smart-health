#!/usr/bin/env python3
"""Check the reminder-email link to the Workato recipe (docs/specs/email-notifications.md). Touches no notification and no database row.

Usage (from the repository root):
  python scripts/email_recipe_check.py --fake          prove our side against a pretend recipe on this machine (no network, no Workato needed)
  python scripts/email_recipe_check.py --print         show the exact message our API would send (no sending)
  python scripts/email_recipe_check.py --to you@x.com  send ONE test email through the real recipe (needs WORKATO_EMAIL_WEBHOOK_URL and
                                                       WORKATO_EMAIL_WEBHOOK_TOKEN in .env). The subject starts with "[Test]".

The address, the webhook address and the token are never printed.
"""
import argparse
import json
import sys
import threading
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

from app.core.config import settings  # noqa: E402
from app.core.errors import DomainError  # noqa: E402
from app.db.logstore import TZ  # noqa: E402
from app.integrations.workato_email import WorkatoEmail  # noqa: E402
from app.services import notify_email  # noqa: E402

REQUIRED = ("to", "toName", "subject", "preheader", "text", "html", "tags", "idempotencyKey")


def sample_message(to: str) -> dict:
    """A realistic lunch reminder, built by the same code the dispatcher uses."""
    now = datetime.now(TZ)
    row = notify_email.Row(
        id=str(uuid.uuid4()), user_id=str(uuid.uuid4()), kind="nudge", scheduled_for=now, acted_at=None,
        payload={"key": f"meal-2-{now.date()}", "title": "Log your lunch",
                 "body": "Take a photo and tell us when you finish eating.", "to": "E2"},
        attempts=0, delivery_to="person", name="Mr Tan", email=to, opt_in=True, contact_name=None, contact_email=None, language="en")
    msg = notify_email.build_message(row)
    msg["subject"] = "[Test] " + msg["subject"]
    return msg


def show(ok: bool, what: str) -> bool:
    print(("PASS  " if ok else "FAIL  ") + what)
    return ok


def run_fake() -> int:
    token, header = "FAKE-TOKEN", "API-TOKEN"
    seen: list[dict] = []

    class Recipe(BaseHTTPRequestHandler):
        def do_POST(self):                                   # what the Workato recipe does: check the token, take the JSON, answer ok
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if self.headers.get(header) != token:
                self.send_response(401)
                self.end_headers()
                return
            seen.append(body)
            out = json.dumps({"status": "ok"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), Recipe)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}/hook"
    msg = sample_message("someone@example.com")
    ok = True
    try:
        WorkatoEmail(url, token, header, max_retries=0).send(msg)
        ok &= show(len(seen) == 1, "the recipe received the message")
        got = seen[0] if seen else {}
        ok &= show(all(k in got for k in REQUIRED), "it holds every field the recipe maps: " + ", ".join(REQUIRED))
        ok &= show(got.get("to") == "someone@example.com" and got.get("html", "").startswith("<!doctype html>") and bool(got.get("text")), "address, HTML and plain text are filled")
        ok &= show(got.get("tags", {}).get("kind") == "nudge" and got.get("idempotencyKey") == msg["idempotencyKey"], "tags and the idempotency key are set")
        try:
            WorkatoEmail(url, "WRONG", header, max_retries=0).send(msg)
            ok &= show(False, "a wrong token is refused")
        except DomainError as e:
            ok &= show(e.code == "workato_refused", "a wrong token is refused at once (code workato_refused)")
    finally:
        srv.shutdown()
    print("\nOur side is fine." if ok else "\nSomething on our side is wrong.")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--fake", action="store_true", help="test against a pretend recipe")
    g.add_argument("--print", dest="show", action="store_true", help="print the message, send nothing")
    g.add_argument("--to", metavar="ADDRESS", help="send one real test email to this address")
    args = ap.parse_args()
    if args.fake:
        return run_fake()
    if args.show:
        print(json.dumps(sample_message("someone@example.com"), indent=2, ensure_ascii=False))
        return 0
    if not notify_email.is_valid_email(args.to):
        print("That does not look like an email address.")
        return 2
    sender = WorkatoEmail.from_settings()
    if not sender.configured:
        print("Not set up: put WORKATO_EMAIL_WEBHOOK_URL and WORKATO_EMAIL_WEBHOOK_TOKEN in .env (see docs/specs/email-notifications.md, 'Build the recipe').")
        return 1
    try:
        sender.send(sample_message(args.to))
    except DomainError as e:
        print(f"The recipe did not send it: {e.code}. {e}")
        hints = {"workato_refused": "Workato answered with an error. Check the token, the header name and that the recipe is running.",
                 "workato_unavailable": "No answer. Check the webhook address and that the recipe is started.",
                 "workato_bad_answer": "The recipe answered with something that is not JSON. A plain webhook answers {\"status\":\"ok\"} by itself.",
                 "workato_failed": "The recipe answered, but not with status ok."}
        if e.code in hints:
            print(hints[e.code])
        return 1
    print("The recipe said ok. Look in the inbox (and spam) of the address you gave. If nothing arrives, open the recipe's job history in Workato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
