"""Experiment: Google Cloud Vision OCR against the local OCR (RapidOCR) on medicine labels. NOT part of the app; nothing here is imported by it.

What it answers: does Vision (DOCUMENT_TEXT_DETECTION) read a medicine label better, and how fast, than the offline reader the scanner uses now
(app/services/scan_privacy.py)? It runs both on the same photos and prints, per photo: time, number of lines, mean confidence, how many of the
expected words each reader found, and how alike the two texts are. It also shows what the app's privacy masking would have hidden in Vision's
text (the name and ID lines) so you can see exactly what the photo had already revealed to Google by then.

PRIVACY. Vision needs the ORIGINAL photo, with the patient's name and ID on it (decision D-063: photos are blacked out before they leave the
machine). So this script only runs on the made-up labels (tests/fixtures/make_label_images.py) unless you pass --allow-real-photos for photos you
own and accept uploading. Never use a real patient's label.

Credentials (an API key is refused by Vision; it needs a principal):
    gcloud auth application-default login            # your own Google account, or
    python scripts/vision_ocr_experiment.py --credentials path/to/service-account.json ...
The project that is billed is --project, GOOGLE_CLOUD_PROJECT, or the credentials' own project. The Vision API must be enabled on it
(console: APIs and Services > Library > Cloud Vision API > Enable). Free tier: the first 1,000 images a month.

Run:
    cd services/api
    python scripts/vision_ocr_experiment.py --synthetic --out ../../docs/review/vision-ocr
    python scripts/vision_ocr_experiment.py --synthetic --dry-run            # no Google call: shows the plan and the local reader only
    python scripts/vision_ocr_experiment.py --allow-real-photos photo1.jpg photo2.png
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests" / "fixtures"))

from rapidfuzz import fuzz  # noqa: E402

from app.services import scan_privacy as P  # noqa: E402

ANNOTATE_URL = "https://vision.googleapis.com/v1/images:annotate"
SCOPES = ["https://www.googleapis.com/auth/cloud-vision"]

# the made-up labels and the words a reader should find on each (lower case, compared on letters and digits only)
SYNTHETIC: dict[str, list[str]] = {
    "metformin_prescription": ["metformin", "500", "twice", "meals"],
    "atorvastatin_prescription": ["atorvastatin", "20", "night"],
    "unknown_drug": ["zorblaxine", "75", "capsule", "T0123456Z"],
    "injection_label": ["metformin", "500", "twice", "5000"],
    "supplement": ["omega", "fish", "1000", "EPA 180"],
    "blurry": ["metformin"],
}


@dataclass
class Reading:
    reader: str
    seconds: float
    lines: list[P.OcrLine]
    error: str | None = None
    found: dict[str, bool] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return "\n".join(ln.text for ln in self.lines)

    @property
    def mean_conf(self) -> float | None:
        c = [ln.confidence for ln in self.lines]
        return round(statistics.mean(c), 3) if c else None


def _squash(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def _check(reading: Reading, expect: list[str]) -> None:
    blob = _squash(reading.text)
    reading.found = {w: _squash(w) in blob for w in expect}


def read_local(data: bytes) -> Reading:
    t = time.perf_counter()
    try:
        img = P.normalise_image(data)
        lines = P.read_lines(P.default_ocr(), img)
        return Reading("local (RapidOCR)", time.perf_counter() - t, lines)
    except Exception as e:  # noqa: BLE001 - report, do not stop the experiment
        return Reading("local (RapidOCR)", time.perf_counter() - t, [], error=type(e).__name__)


def _session(credentials: str | None, project: str | None):
    import google.auth
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account

    if credentials:
        cred = service_account.Credentials.from_service_account_file(credentials, scopes=SCOPES)
        proj = project or cred.project_id
    else:
        cred, proj_default = google.auth.default(scopes=SCOPES)
        proj = project or proj_default or os.environ.get("GOOGLE_CLOUD_PROJECT")
    return AuthorizedSession(cred), proj


def _vision_lines(resp: dict) -> list[P.OcrLine]:
    """Group Vision's words into lines the way the scanner's own OcrLine works (text, box, confidence, corners)."""
    lines: list[P.OcrLine] = []
    for page in (resp.get("fullTextAnnotation") or {}).get("pages", []):
        for block in page.get("blocks", []):
            for para in block.get("paragraphs", []):
                words, confs, pts = [], [], []
                cur_y = None
                for w in para.get("words", []):
                    text = "".join(s.get("text", "") + {"SPACE": " ", "EOL_SURE_SPACE": " ", "LINE_BREAK": "\n"}.get((s.get("property", {}).get("detectedBreak") or {}).get("type", ""), "") for s in w.get("symbols", []))
                    box = [(v.get("x", 0), v.get("y", 0)) for v in w.get("boundingBox", {}).get("vertices", [])]
                    top = min((y for _, y in box), default=0)
                    if cur_y is not None and words and top - cur_y > 0.6 * (max(y for _, y in box) - top or 1) + 8:
                        lines.append(_make_line(words, confs, pts))
                        words, confs, pts = [], [], []
                    if not words:
                        cur_y = top
                    words.append(text)
                    confs.append(float(w.get("confidence", 0.0)))
                    pts.extend(box)
                if words:
                    lines.append(_make_line(words, confs, pts))
    return lines


def _make_line(words: list[str], confs: list[float], pts: list[tuple[int, int]]) -> P.OcrLine:
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    box = (min(xs), min(ys), max(xs), max(ys))
    corners = ((box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3]))
    return P.OcrLine(" ".join("".join(words).split()), box, statistics.mean(confs) if confs else 0.0, tuple((float(x), float(y)) for x, y in corners))


def read_vision(data: bytes, session, language_hints: list[str]) -> Reading:
    t = time.perf_counter()
    try:
        img = P.normalise_image(data)           # the same clean-up the scanner does (rotation, no EXIF, size limit)
        import io

        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=90)
        body = {"requests": [{"image": {"content": base64.b64encode(buf.getvalue()).decode()}, "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                              "imageContext": {"languageHints": language_hints}}]}
        r = session.post(ANNOTATE_URL, json=body, timeout=60)
        if r.status_code != 200:
            return Reading("Google Vision", time.perf_counter() - t, [], error=f"HTTP {r.status_code}: {r.json().get('error', {}).get('message', '')[:200]}")
        resp = r.json()["responses"][0]
        if "error" in resp:
            return Reading("Google Vision", time.perf_counter() - t, [], error=resp["error"].get("message", "error")[:200])
        return Reading("Google Vision", time.perf_counter() - t, _vision_lines(resp))
    except Exception as e:  # noqa: BLE001
        return Reading("Google Vision", time.perf_counter() - t, [], error=f"{type(e).__name__}: {str(e)[:160]}")


def private_in(reading: Reading) -> dict[str, str]:
    """What the app's masking rules would black out in this reader's lines: the lines that had already been uploaded when Vision is used."""
    hits = P.find_private_lines(reading.lines)
    return {reading.lines[i].text: kind for i, kind in hits.items()}


def collect(paths: list[str], synthetic: bool) -> list[tuple[str, bytes, list[str]]]:
    items: list[tuple[str, bytes, list[str]]] = []
    if synthetic:
        import make_label_images as M

        for name, expect in SYNTHETIC.items():
            items.append((name, getattr(M, name)(), expect))
    for p in paths:
        items.append((Path(p).name, Path(p).read_bytes(), []))
    return items


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photos", nargs="*", help="your own photos (needs --allow-real-photos)")
    ap.add_argument("--synthetic", action="store_true", help="use the made-up test labels")
    ap.add_argument("--allow-real-photos", action="store_true", help="I accept uploading these UNMASKED photos to Google")
    ap.add_argument("--credentials", help="service-account JSON; otherwise application-default credentials")
    ap.add_argument("--project", help="project to bill (default: from the credentials or GOOGLE_CLOUD_PROJECT)")
    ap.add_argument("--lang", default="en", help="Vision language hint, e.g. en or en,zh (default en)")
    ap.add_argument("--out", help="folder for report.json and report.md")
    ap.add_argument("--dry-run", action="store_true", help="no Google call: run the local reader only")
    a = ap.parse_args(argv)
    if a.photos and not a.allow_real_photos:
        sys.stderr.write("Real photos carry the patient's name and ID and would be uploaded unmasked. Re-run with --allow-real-photos if they are yours.\n")
        return 2
    items = collect(a.photos, a.synthetic)
    if not items:
        sys.stderr.write("Nothing to read: pass --synthetic or photo files.\n")
        return 2

    session = project = None
    if not a.dry_run:
        try:
            session, project = _session(a.credentials, a.project)
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"No Google credentials ({type(e).__name__}). Run `gcloud auth application-default login` or pass --credentials. Use --dry-run to skip Google.\n")
            return 2
        sys.stdout.write(f"Billing project: {project or '(not set)'}\n")
        if project and hasattr(session, "headers"):
            session.headers["x-goog-user-project"] = project

    rows = []
    for name, data, expect in items:
        local = read_local(data)
        _check(local, expect)
        vis = None
        if session is not None:
            vis = read_vision(data, session, [x.strip() for x in a.lang.split(",") if x.strip()])
            _check(vis, expect)
        rows.append((name, local, vis, expect))
        sys.stdout.write(f"\n== {name}\n")
        for r in (local, vis):
            if r is None:
                continue
            hit = f"{sum(r.found.values())}/{len(r.found)}" if r.found else "-"
            sys.stdout.write(f"  {r.reader:18s} {r.seconds:5.2f}s  lines={len(r.lines):2d}  conf={r.mean_conf}  expected found={hit}" + (f"  ERROR {r.error}" if r.error else "") + "\n")
        if vis and not vis.error and not local.error:
            sys.stdout.write(f"  text similarity (token set): {fuzz.token_set_ratio(local.text, vis.text):.0f}/100\n")
            priv = private_in(vis)
            if priv:
                sys.stdout.write(f"  lines the app would have masked before upload (Vision saw them): {len(priv)}\n")

    summary = {}
    for label, pick in (("local", lambda r: r[1]), ("vision", lambda r: r[2])):
        rs = [pick(r) for r in rows if pick(r) is not None and not pick(r).error]
        if rs:
            ok = sum(sum(x.found.values()) for x in rs)
            tot = sum(len(x.found) for x in rs)
            summary[label] = {"photos": len(rs), "mean_seconds": round(statistics.mean(x.seconds for x in rs), 2), "expected_words_found": f"{ok}/{tot}"}
    sys.stdout.write("\nSUMMARY\n" + json.dumps(summary, indent=2) + "\n")

    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").write_text(json.dumps({
            "summary": summary,
            "photos": [{"name": n, "expect": e, "local": {"seconds": l.seconds, "conf": l.mean_conf, "found": l.found, "text": l.text, "error": l.error},
                        "vision": None if v is None else {"seconds": v.seconds, "conf": v.mean_conf, "found": v.found, "text": v.text, "error": v.error,
                                                          "private_lines_seen": private_in(v) if not v.error else {}}} for n, l, v, e in rows]}, indent=2), encoding="utf-8")
        sys.stdout.write(f"Wrote {out / 'report.json'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
