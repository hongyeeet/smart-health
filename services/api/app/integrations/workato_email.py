"""Workato: the recipe that sends one reminder email (docs/specs/email-notifications.md).

One call is one email. The call is a POST of JSON to the recipe's webhook with the token in a header, the same way the calendar recipe is
called (app/integrations/workato.py). The recipe answers {"status": "ok"}. Timeouts, connection errors and 429 and 5xx are retried with
backoff; any other 4xx is refused at once. The address, the token and the message are never logged and an error text never holds them.
"""
from __future__ import annotations

import random
import time
from typing import Any, Callable, Mapping

import requests

from app.core.config import settings
from app.core.errors import ExternalServiceError

RETRY_STATUS = {429, 500, 502, 503, 504}
USER_AGENT = "smart-health-backend/0.1"


class WorkatoEmail:
    def __init__(self, url: str, token: str, header: str = "API-TOKEN", *, timeout_s: float = 30.0, max_retries: int = 2,
                 session: requests.Session | None = None, sleep: Callable[[float], None] = time.sleep) -> None:
        self._url, self._token, self._header = url, token, header
        self._timeout, self._retries = timeout_s, max_retries
        self._session = session or requests.Session()
        self._sleep = sleep

    @classmethod
    def from_settings(cls) -> "WorkatoEmail":
        # short timeouts: a send happens while a notification row is locked, so a slow recipe must not hold it for long
        return cls(settings.workato_email_webhook_url, settings.workato_email_webhook_token, settings.workato_email_token_header, timeout_s=15.0, max_retries=1)

    @property
    def configured(self) -> bool:
        return bool(self._url and self._token)

    def send(self, message: Mapping[str, Any]) -> None:
        """Ask the recipe to send one email. Returns when it said ok; raises ExternalServiceError (a code, no private detail) otherwise."""
        if not self.configured:
            raise ExternalServiceError("Workato email is not set up", code="workato_not_configured")
        headers = {self._header: self._token, "Content-Type": "application/json", "User-Agent": USER_AGENT}
        last = "no attempt"
        for attempt in range(self._retries + 1):
            try:
                r = self._session.post(self._url, json=dict(message), headers=headers, timeout=self._timeout)
            except requests.RequestException as e:
                last = type(e).__name__
            else:
                if r.status_code == 200:
                    self._check(r)
                    return
                last = f"HTTP {r.status_code}"
                if r.status_code not in RETRY_STATUS:
                    raise ExternalServiceError(f"Workato refused the email ({last})", code="workato_refused")
            if attempt < self._retries:
                self._sleep(min(8.0, 0.5 * (2 ** attempt)) + random.uniform(0, 0.25))
        raise ExternalServiceError(f"Workato did not answer ({last})", code="workato_unavailable")

    @staticmethod
    def _check(r: requests.Response) -> None:
        try:
            body = r.json()
        except ValueError:
            raise ExternalServiceError("Workato answered with something unreadable", code="workato_bad_answer") from None
        if not isinstance(body, dict) or str(body.get("status", "")).lower() != "ok":
            raise ExternalServiceError("Workato said the email was not sent", code="workato_failed")
