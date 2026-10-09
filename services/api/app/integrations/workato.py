"""Workato: the recipe that puts one dose time on Google Calendar (docs/specs/f4-calendar.md, D-074).

One call makes one repeating calendar event. The call is a POST of JSON to the recipe's webhook, with the token in a header. The recipe
answers with the id of the event it made. Timeout and retry follow rules.md section 6: timeouts, connection errors and 429 and 5xx are
retried with backoff, any other 4xx is refused at once. The address, the token and the payload (which holds a medicine name) are never
logged, and an error message never contains them.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import requests

from app.core.errors import ExternalServiceError
from app.core.settings import Settings, get_settings

RETRY_STATUS = {429, 500, 502, 503, 504}
USER_AGENT = "smart-health-backend/0.1"


@dataclass(frozen=True)
class CalendarEvent:
    event_id: str
    link: str | None = None


class WorkatoClient:
    def __init__(self, url: str, token: str, header: str = "API-TOKEN", *, timeout_s: float = 30.0, max_retries: int = 2,
                 session: requests.Session | None = None, sleep: Callable[[float], None] = time.sleep) -> None:
        self._url, self._token, self._header = url, token, header
        self._timeout, self._retries = timeout_s, max_retries
        self._session = session or requests.Session()
        self._sleep = sleep

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "WorkatoClient":
        s = settings or get_settings()
        return cls(s.workato_webhook_url, s.workato_webhook_token.get_secret_value(), s.workato_token_header)

    @property
    def configured(self) -> bool:
        return bool(self._url and self._token)

    def create_event(self, payload: Mapping[str, Any]) -> CalendarEvent:
        """Ask the recipe to make one repeating event. Returns its id, or raises ExternalServiceError with a code and no private detail."""
        if not self.configured:
            raise ExternalServiceError("Workato is not set up", code="workato_not_configured")
        headers = {self._header: self._token, "Content-Type": "application/json", "User-Agent": USER_AGENT}
        last = "no attempt"
        for attempt in range(self._retries + 1):
            try:
                r = self._session.post(self._url, json=dict(payload), headers=headers, timeout=self._timeout)
            except requests.RequestException as e:
                last = type(e).__name__
            else:
                if r.status_code == 200:
                    return self._parse(r)
                last = f"HTTP {r.status_code}"
                if r.status_code not in RETRY_STATUS:
                    raise ExternalServiceError(f"Workato refused the request ({last})", code="workato_refused")
            if attempt < self._retries:
                self._sleep(min(8.0, 0.5 * (2 ** attempt)) + random.uniform(0, 0.25))
        raise ExternalServiceError(f"Workato did not answer ({last})", code="workato_unavailable")

    @staticmethod
    def _parse(r: requests.Response) -> CalendarEvent:
        """The recipe answers {"status": "ok", "event_id": "...", "link": "..."}; anything else is an error, not a guess."""
        try:
            body = r.json()
        except ValueError:
            raise ExternalServiceError("Workato answered with something unreadable", code="workato_bad_answer") from None
        if not isinstance(body, dict) or str(body.get("status", "")).lower() != "ok":
            raise ExternalServiceError("Workato said the event was not made", code="workato_failed")
        event_id = body.get("event_id")
        if not isinstance(event_id, str) or not event_id.strip():
            raise ExternalServiceError("Workato did not return an event id", code="workato_bad_answer")
        link = body.get("link")
        return CalendarEvent(event_id=event_id.strip(), link=link if isinstance(link, str) and link.startswith("https://") else None)
