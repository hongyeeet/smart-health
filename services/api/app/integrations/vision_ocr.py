"""Google Cloud Vision as the text reader of the medicine scanner (decision of Joely, 2026-10-14: Vision reads the label, replacing the offline reader as the first choice).

Vision gets the ORIGINAL photo (after the scanner's own clean-up: rotation, no EXIF or GPS, size limit), because the name, NRIC and phone numbers
have to be read before they can be blacked out. Only the blacked-out copy then goes to the AI model and is stored as the Bronze original, exactly
as before; the original photo is never stored by this app. Google processes it to return text (Vision does not keep the image).

It answers like the offline reader (`scan_privacy.RapidOcrAdapter`): a call with a BGR image returns ([[corners, text, confidence], ...], None), one
entry per printed line. If Vision cannot be used (no credentials on this machine, the project refuses, a timeout, an error), `FallbackOcr` reads the
photo with the offline reader instead, so a scan never fails only because Google was unreachable and the photo never needs to leave the machine then.

Credentials: none are stored in the repository or .env. Vision refuses API keys, so it uses Google's "application default credentials": on a
laptop `gcloud auth application-default login` (then `gcloud auth application-default set-quota-project <project>`); on a server a service account
(`GOOGLE_APPLICATION_CREDENTIALS`). The project billed is `GOOGLE_CLOUD_PROJECT`. Nothing from a photo (text, names, the address of the request) is ever logged.
"""
from __future__ import annotations

import base64
import io
import logging
import random
import statistics
import time
from typing import Any, Callable

import requests

from app.core.errors import ExternalServiceError

logger = logging.getLogger(__name__)

ANNOTATE_URL = "https://vision.googleapis.com/v1/images:annotate"
SCOPES = ["https://www.googleapis.com/auth/cloud-vision"]
RETRY_STATUS = {429, 500, 502, 503, 504}
# a break after a word's last character: the word is followed by a space, a line wrap or the end of a paragraph
_SPACE_AFTER = {"SPACE", "EOL_SURE_SPACE", "LINE_BREAK"}
_LINE_END = {"EOL_SURE_SPACE", "LINE_BREAK"}


def parse_lines(resp: dict[str, Any]) -> list[list[Any]]:
    """Vision's fullTextAnnotation as printed lines: [[four corners, text, mean word confidence], ...]. A line ends where Vision marks a line wrap or the
    end of a paragraph, so the lines are the lines on the label, and each box covers its own words only."""
    out: list[list[Any]] = []
    for page in (resp.get("fullTextAnnotation") or {}).get("pages", []):
        for block in page.get("blocks", []):
            for para in block.get("paragraphs", []):
                text, confs, xs, ys = "", [], [], []

                def flush() -> None:
                    nonlocal text, confs, xs, ys
                    if text.strip() and xs:
                        box = [[min(xs), min(ys)], [max(xs), min(ys)], [max(xs), max(ys)], [min(xs), max(ys)]]
                        out.append([box, " ".join(text.split()), statistics.mean(confs) if confs else 0.0])
                    text, confs, xs, ys = "", [], [], []

                for w in para.get("words", []):
                    symbols = w.get("symbols", [])
                    text += "".join(s.get("text", "") for s in symbols)
                    last_break = ((symbols[-1].get("property") or {}).get("detectedBreak") or {}).get("type", "") if symbols else ""
                    if last_break in _SPACE_AFTER:
                        text += " "
                    confs.append(float(w.get("confidence", 0.0)))
                    for v in (w.get("boundingBox") or {}).get("vertices", []):
                        xs.append(float(v.get("x", 0)))
                        ys.append(float(v.get("y", 0)))
                    if last_break in _LINE_END:
                        flush()
                flush()
    return out


class VisionOcr:
    def __init__(self, project: str = "", *, session: Any = None, language_hints: tuple[str, ...] = ("en",), timeout_s: float = 20.0, max_retries: int = 1,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self._project = project
        self._session = session
        self._hints = list(language_hints)
        self._timeout, self._retries, self._sleep = timeout_s, max_retries, sleep

    @classmethod
    def from_settings(cls) -> "VisionOcr":
        from app.core.settings import get_settings

        return cls(get_settings().google_cloud_project)

    def _get_session(self) -> Any:
        if self._session is None:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession

            cred, default_project = google.auth.default(scopes=SCOPES)      # raises DefaultCredentialsError when this machine has none
            session = AuthorizedSession(cred)
            project = self._project or default_project
            if project:
                session.headers["x-goog-user-project"] = project            # bill and enable-check on the app's project
            self._session = session
        return self._session

    def __call__(self, bgr: Any) -> tuple[list[Any] | None, None]:
        from PIL import Image

        buf = io.BytesIO()
        Image.fromarray(bgr[:, :, ::-1]).save(buf, "JPEG", quality=90)
        body = {"requests": [{"image": {"content": base64.b64encode(buf.getvalue()).decode()}, "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                              "imageContext": {"languageHints": self._hints}}]}
        session = self._get_session()
        last = "no attempt"
        for attempt in range(self._retries + 1):
            try:
                r = session.post(ANNOTATE_URL, json=body, timeout=self._timeout)
            except requests.RequestException as e:
                last = type(e).__name__
            else:
                if r.status_code == 200:
                    resp = (r.json().get("responses") or [{}])[0]
                    if "error" in resp:
                        raise ExternalServiceError("Vision could not read the photo", code="vision_error")
                    return parse_lines(resp), None
                last = f"HTTP {r.status_code}"
                if r.status_code not in RETRY_STATUS:
                    raise ExternalServiceError(f"Vision refused the request ({last})", code="vision_refused")
            if attempt < self._retries:
                self._sleep(min(4.0, 0.5 * (2 ** attempt)) + random.uniform(0, 0.25))
        raise ExternalServiceError(f"Vision did not answer ({last})", code="vision_unavailable")


class FallbackOcr:
    """Reads with `primary` (Vision) and, when that cannot be used, with `fallback()` (the offline reader, loaded the first time it is needed).
    After a failure the primary is not tried again for `cooldown_s`, so a machine with no credentials does not pay for a failed attempt on every photo."""

    def __init__(self, primary: Callable[[Any], Any], fallback: Callable[[], Callable[[Any], Any]], *, cooldown_s: float = 60.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._primary, self._make_fallback, self._cooldown, self._clock = primary, fallback, cooldown_s, clock
        self._fallback: Callable[[Any], Any] | None = None
        self._down_until = 0.0
        self.last_engine = ""

    def __call__(self, bgr: Any) -> Any:
        if self._clock() >= self._down_until:
            try:
                out = self._primary(bgr)
                self.last_engine = "vision"
                return out
            except Exception as e:   # noqa: BLE001 - any reason Vision cannot be used leads to the offline reader; only the kind of error is logged
                self._down_until = self._clock() + self._cooldown
                logger.warning("Vision text reading unavailable (%s); using the offline reader", getattr(e, "code", type(e).__name__))
        if self._fallback is None:
            self._fallback = self._make_fallback()
        self.last_engine = "local"
        return self._fallback(bgr)
