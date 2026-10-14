"""Check the reminder-email path to the Workato recipe (docs/specs/email-notifications.md, "Switch it on").

    cd services/api
    python scripts/email_recipe_check.py --fake                       # no network: a local stand-in for the recipe, must end "Our side is fine."
    python scripts/email_recipe_check.py --to you@example.com         # sends ONE real test email through the real recipe ([Test] in the subject)

--fake starts a small web server on this machine that behaves like the recipe (checks the API-TOKEN header, the fields, answers {"status": "ok"})
and sends every kind of reminder through the same WorkatoEmail client and message builder the app uses. It also tries the failure paths: a wrong
token (refused at once), a 500 (retried, then reported), a reply that is not ok (reported). It reads no database and sends nothing outside.
--to needs WORKATO_EMAIL_WEBHOOK_URL and WORKATO_EMAIL_WEBHOOK_TOKEN in .env.
"""
from __future__ import annotations

import json
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.errors import ExternalServiceError  # noqa: E402
from app.integrations.workato_email import WorkatoEmail  # noqa: E402
from app.services import notify_email as svc  # noqa: E402

TOKEN = "fake-token"
REQUIRED = ["to", "toName", "subject", "preheader", "text", "html", "tags", "idempotencyKey"]
KINDS = [("nudge", "person", "B1"), ("checkin", "person", "B1"), ("refill", "person", "H1"), ("appointment", "person", "K3"), ("urgent", "contact", "J1")]


class Recipe(BaseHTTPRequestHandler):
    mode = "ok"            # ok | fail500 | notok
    received: list[dict] = []

    def log_message(self, *a) -> None:  # keep the output readable
        pass

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.headers.get("API-TOKEN") != TOKEN:
            self.send_response(401)
            self.end_headers()
            return
        if Recipe.mode == "fail500":
            self.send_response(500)
            self.end_headers()
            return
        Recipe.received.append(body)
        out = json.dumps({"status": "ok" if Recipe.mode == "ok" else "error"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)


def _row(kind: str, audience: str, route: str) -> svc.Row:
    return svc.Row(f"{kind}-id", "user-1", kind, datetime.now(svc.TZ), None, {"key": f"{kind}-1", "title": f"A {kind} reminder", "body": "This is a made-up reminder body for the check.", "to": route},
                   0, audience, "Mr Tan", "tan@example.com", True, "Mrs Tan", "mrs.tan@example.com")


def fake() -> int:
    server = HTTPServer(("127.0.0.1", 0), Recipe)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/hook"
    problems: list[str] = []
    ok = WorkatoEmail(url, TOKEN, sleep=lambda s: None, max_retries=1)

    for kind, audience, route in KINDS:
        msg = svc.build_message(_row(kind, audience, route))
        miss = [k for k in REQUIRED if not msg.get(k)]
        if miss:
            problems.append(f"{kind}: message is missing {miss}")
        if audience == "contact" and msg["to"] != "mrs.tan@example.com":
            problems.append("urgent alert did not go to the emergency contact")
        try:
            ok.send(msg)
        except ExternalServiceError as e:
            problems.append(f"{kind}: send failed ({e.code})")
    print(f"sent {len(Recipe.received)} of {len(KINDS)} reminder kinds to the stand-in recipe")

    def expect(label: str, client: WorkatoEmail, code: str) -> None:
        try:
            client.send(svc.build_message(_row("nudge", "person", "B1")))
        except ExternalServiceError as e:
            if e.code != code:
                problems.append(f"{label}: expected {code}, got {e.code}")
            else:
                print(f"{label}: reported as {code}, as it should be")
        else:
            problems.append(f"{label}: should have failed but did not")

    expect("wrong token", WorkatoEmail(url, "wrong", sleep=lambda s: None), "workato_refused")
    Recipe.mode = "fail500"
    expect("recipe down (500)", WorkatoEmail(url, TOKEN, sleep=lambda s: None, max_retries=1), "workato_unavailable")
    Recipe.mode = "notok"
    expect("reply is not ok", WorkatoEmail(url, TOKEN, sleep=lambda s: None), "workato_failed")
    expect("not set up", WorkatoEmail("", ""), "workato_not_configured")
    server.shutdown()

    if problems:
        print("\nPROBLEMS")
        for p in problems:
            print(" -", p)
        return 1
    print("\nOur side is fine.")
    return 0


def real(to: str) -> int:
    client = WorkatoEmail.from_settings()
    if not client.configured:
        print("WORKATO_EMAIL_WEBHOOK_URL and WORKATO_EMAIL_WEBHOOK_TOKEN are not both set in .env.")
        return 2
    row = svc.Row("test", "check", "nudge", datetime.now(svc.TZ), None,
                  {"key": "check", "title": "[Test] Your reminders are working", "body": "This is a test email from Equinox. If you can read it, reminders will reach you here.", "to": "B1"},
                  0, "person", None, to, True, None, None)
    msg = svc.build_message(row)
    msg["subject"] = "[Test] " + msg["subject"] if not msg["subject"].startswith("[Test]") else msg["subject"]
    try:
        client.send(msg)
    except ExternalServiceError as e:
        print(f"The recipe did not accept it: {e.code}. Open the recipe's job history in Workato.")
        return 1
    print(f"The recipe said ok. Check {to} (it can take a minute).")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--fake"]:
        raise SystemExit(fake())
    if a[:1] == ["--to"] and len(a) == 2:
        raise SystemExit(real(a[1]))
    print(__doc__)
    raise SystemExit(2)
