"""Keep the patient's identity out of the photo before it goes to any model (rules.md section 3, ai-models.md section 6).

How: a local OCR (nothing leaves the machine) finds every line of text with its position. Lines that carry an NRIC or
FIN, a name or birth-date label, a phone number, an email or an address are painted black. The model only ever sees the
blacked-out copy, and that copy is also the one stored as the Bronze original.

Limits (be honest about them): a printed name with no label next to it looks like any other words. It is caught only
when it sits right beside an NRIC or name label, or matches the name the user gave us. The prompt and `scrub_value`
are the second and third layers. If the OCR finds no text at all, the photo is refused instead of sent.
"""
from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from PIL import Image, ImageDraw, ImageOps
from rapidfuzz import fuzz

from app.core.errors import ValidationFailed

MAX_BYTES = 10 * 1024 * 1024        # rules.md section 8
MAX_SIDE = 2000                     # longest side after resizing, in pixels
ALLOWED_FORMATS = {"JPEG", "PNG", "MPO"}  # MPO is how some phones save JPEG

NRIC_RE = re.compile(r"(?<![A-Za-z0-9])[STFGMstfgm]\s?\d{7}\s?[A-Za-z](?![A-Za-z0-9])")
# Pharmacies print the ID partly hidden, for example TXXXX123A or S****567D.
# The OCR often misreads the last character and drops spaces, so this stays loose: one letter, X or * marks, then digits.
MASKED_ID_RE = re.compile(r"[STFGMstfgm]\s?[Xx*#]{3,6}\s?\d{2,4}\s?[A-Za-z0-9]?")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?65[\s-]?)?[689]\d{3}[\s-]?\d{4}(?!\d)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
ADDRESS_RE = re.compile(r"\b(?:blk|block)\s*\d+[a-z]?\b|#\d{2}-\d{2,4}\b|\bsingapore\s*\d{6}\b|(?<!\d)\d{6}(?!\d)", re.I)
DOB_RE = re.compile(r"\b(?:d\.?\s?o\.?\s?b\.?|date\s+of\s+birth|birth\s*date|born)\b", re.I)
NAME_LABEL_RE = re.compile(r"^\s*(?:(?:patient(?:\s*name)?|pt\.?\s*name|pt\.?|nama|姓名|病人)(?![A-Za-z])|name\s*[:：])\s*[:：\-]?\s*", re.I)
LABEL_ONLY_RE = re.compile(r"^\s*(?:patient(?:\s*name)?|pt\.?\s*name|pt\.?|nama|name|姓名|病人|nric|fin|ic|i/c|id)\s*[:：\-]?\s*$", re.I)
DATE_PREFIX_RE = re.compile(r"^[\d/.\- :]{5,}[-–]\s*(.+)$")
NUMBER_THEN_NAME_RE = re.compile(r"(?<![\d/])\d{3,}\s+([A-Z][A-Z'.\-]+(?:\s+[A-Z][A-Z'.\-]+){1,5})")
# Text the app needs: a strength, a quantity, directions. A line carrying any of it is never hidden as "a name".
NEEDED_TEXT_RE = re.compile(r"\d+(?:[.,]\d+)?\s?(?:mg|mcg|µg|ml|iu|g|%)\b|\b(?:tabs?|caps?|tablets?|capsules?|take|qty|quantity|daily|twice|once|"
                            r"morning|evening|night|dose|expiry|exp)\b", re.I)
LEADING_NUMBER_RE = re.compile(r"^\s*\d{3,}\s+")     # a patient or queue number printed before the name
DOCTOR_RE = re.compile(r"^\s*(?i:dr|prof|doctor)(?![A-Za-z])|^Dr[A-Z]")
HONORIFICS = {"mr", "mrs", "ms", "mdm", "madam", "miss", "dr", "encik", "puan", "cik"}
# Words that appear on labels. A line made only of these words and drug names is never treated as a stray name.
LABEL_WORDS = {
    "take", "tablet", "tablets", "capsule", "capsules", "tab", "cap", "twice", "daily", "once", "thrice", "after", "before",
    "meals", "meal", "food", "with", "morning", "night", "evening", "per", "day", "and", "or", "the", "for", "qty", "quantity",
    "date", "dose", "oral", "film", "coated", "extended", "release", "pharmacy", "hospital", "clinic", "general", "singapore",
    "polyclinic", "medicine", "drug", "mg", "ml", "mcg", "use", "only", "keep", "out", "reach", "children", "store", "exp",
    "expiry", "batch", "supplement", "herbal", "vitamin", "half", "hour", "hours", "an", "as", "needed", "necessary", "anti", "when", "if",
    "tabs", "caps", "medical", "centre", "center", "dispensary", "warning", "caution", "drowsiness", "alcohol", "machinery",
    "driving", "swallow", "whole", "shake", "well", "external", "inflammation", "abdominal", "fever", "pain", "cough", "allergy",
}


@dataclass
class OcrLine:
    text: str
    box: tuple[int, int, int, int]   # left, top, right, bottom
    confidence: float
    poly: tuple[tuple[float, float], ...] = ()   # the four corners as read, so slanted or sideways text is covered tightly


@dataclass
class MaskResult:
    image: bytes                      # the blacked-out JPEG: the only image that may leave the machine
    mime_type: str
    lines: list[OcrLine]
    ocr_text: str                     # the text of the lines that were NOT masked (used to check the model's quoted text)
    masked: dict[str, int] = field(default_factory=dict)   # counts by kind


def normalise_image(data: bytes) -> Image.Image:
    """Validate, apply the phone's rotation, drop metadata (EXIF and GPS), downscale. Raises ValidationFailed."""
    if not data:
        raise ValidationFailed("empty file", code="file_empty")
    if len(data) > MAX_BYTES:
        raise ValidationFailed("file is over the 10 MB limit", code="file_too_large")
    try:
        opened = Image.open(io.BytesIO(data))
        opened.load()
    except Exception:  # noqa: BLE001 - Pillow raises many types for a bad file
        raise ValidationFailed("this file is not a readable photo", code="file_type_not_allowed") from None
    if opened.format not in ALLOWED_FORMATS:
        raise ValidationFailed("only JPEG and PNG photos are accepted", code="file_type_not_allowed")
    img: Image.Image = ImageOps.exif_transpose(opened).convert("RGB")
    if max(img.size) > MAX_SIDE:
        scale = MAX_SIDE / max(img.size)
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.Resampling.LANCZOS)
    clean = Image.new("RGB", img.size)     # a fresh image carries no metadata
    clean.paste(img)
    return clean


class RapidOcrAdapter:
    """Wraps RapidOCR (package `rapidocr`, github.com/RapidAI/RapidOCR) so it answers like the older package did:
    a call with a BGR image returns ([[corners, text, score], ...], None). It keeps the spaces between words."""

    def __init__(self) -> None:
        from rapidocr import RapidOCR
        self._engine = RapidOCR()

    def __call__(self, bgr: Any) -> tuple[list[Any] | None, None]:
        out: Any = self._engine(bgr)
        if out.boxes is None or out.txts is None:
            return None, None
        return [[box.tolist(), str(txt), float(score)] for box, txt, score in zip(out.boxes, out.txts, out.scores, strict=False)], None


def default_ocr() -> Any:
    """RapidOCR runs offline on this machine. Imported lazily because it is slow to load."""
    return RapidOcrAdapter()


def read_lines(ocr: Any, img: Image.Image) -> list[OcrLine]:
    import numpy as np
    result, _ = ocr(np.asarray(img)[:, :, ::-1])      # RapidOCR expects BGR
    lines: list[OcrLine] = []
    for box, text, conf in result or []:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        lines.append(OcrLine(str(text), (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))), float(conf),
                             tuple((float(x), float(y)) for x, y in box)))
    return lines


def _name_tokens(known_names: Iterable[str]) -> set[str]:
    out: set[str] = set()
    for full in known_names:
        for tok in re.findall(r"[A-Za-z]+", full or ""):
            if len(tok) >= 3 and tok.lower() not in HONORIFICS:
                out.add(tok.lower())
    return out


def _letters(s: str) -> str:
    """Only the letters, lower case. The OCR drops spaces ("TAKEAFTERFOOD"), so word checks work on this form."""
    return re.sub(r"[^a-z]", "", s.lower())


def _known_hit(text: str, known: set[str]) -> bool:
    c = _letters(text)
    for tok in known:
        if len(tok) >= 4 and (tok in c or (len(tok) >= 5 and fuzz.partial_ratio(tok, c) >= 88)):
            return True
        if len(tok) == 3 and re.search(rf"\b{tok}\b", text.lower()):
            return True
    return False


def _kind(text: str, known: set[str]) -> str | None:
    if NRIC_RE.search(text) or MASKED_ID_RE.search(text):
        return "nric"
    if NAME_LABEL_RE.match(text) or LABEL_ONLY_RE.match(text):
        return "name_label"
    if DOB_RE.search(text):
        return "birth_date"
    if EMAIL_RE.search(text):
        return "email"
    if PHONE_RE.search(text):
        return "phone"
    if ADDRESS_RE.search(text):
        return "address"
    if known and _known_hit(text, known):
        return "known_name"
    return None


def _looks_like_name(text: str, protect: set[str], min_letters: int = 10) -> bool:
    """A line of only letters, spaces and brackets that contains no label word and no drug name: probably a person's name."""
    t = text.strip()
    dated = DATE_PREFIX_RE.match(t)       # "18/03/2026 - TAN AH KOW": a date, then the name
    if dated:
        t = dated.group(1).strip()
    numbered = LEADING_NUMBER_RE.match(t) is not None
    t = LEADING_NUMBER_RE.sub("", t)      # "84933 CHUA CHOR KIANG DEREK": a patient number, then the name
    if dated or numbered:
        min_letters = min(min_letters, 5)  # a number or date in front is a strong sign of a name, so a short one counts
    if not t or DOCTOR_RE.match(t) or re.search(r"[^A-Za-z\s()'.\-]", re.sub(r"\([^)]*\)", "", t)):
        return False
    words = re.findall(r"[A-Za-z]+", t)
    if len(words) < 2 and not (dated or numbered):
        return False                      # a person's name is two or more words; one word alone is packaging print or a brand
    if len(words) > 1 and not all(w[0].isupper() for w in words):
        return False                      # "For cholesterol lowering" is a sentence, not a name: names are written in capitals
    letters = _letters(t)
    return len(letters) >= min_letters and not any(w in letters for w in protect)


def _overlaps_row(a: OcrLine, b: OcrLine) -> bool:
    top, bottom = max(a.box[1], b.box[1]), min(a.box[3], b.box[3])
    return bottom - top > 0.5 * min(a.box[3] - a.box[1], b.box[3] - b.box[1])


def find_private_lines(lines: Sequence[OcrLine], known_names: Iterable[str] = (), protect_words: Iterable[str] = ()) -> dict[int, str]:
    """Return {line index: kind} for every line to paint over."""
    known = _name_tokens(known_names)
    protect = {w for w in (LABEL_WORDS | {x.lower() for x in protect_words}) if len(w) >= 4}
    hits: dict[int, str] = {}
    for i, ln in enumerate(lines):
        k = _kind(ln.text, known)
        if k:
            hits[i] = k
    # A label on its own line ("Patient:") hides the value beside it or just under it.
    for i, kind in list(hits.items()):
        if kind in ("name_label", "nric") and LABEL_ONLY_RE.match(lines[i].text):
            for j, other in enumerate(lines):
                if j != i and j not in hits and ((_overlaps_row(lines[i], other) and other.box[0] >= lines[i].box[0])
                                                 or 0 <= other.box[1] - lines[i].box[3] <= 0.8 * (lines[i].box[3] - lines[i].box[1]) and abs(other.box[0] - lines[i].box[0]) < 60):
                    hits[j] = "name_value"
    # A full name on a line of its own with no label: nothing but letters and no label word or drug name in it.
    for i, ln in enumerate(lines):
        if i not in hits and not NEEDED_TEXT_RE.search(ln.text) and _looks_like_name(ln.text, protect):
            hits[i] = "unlabelled_name"
    # The OCR sometimes joins the name to text beside it ("cted by the pres84933 CHUA CHOR KIANG DEREK"). A number followed by
    # two or more capitalised words, anywhere in a line, is looked at on its own.
    for i, ln in enumerate(lines):
        m = NUMBER_THEN_NAME_RE.search(ln.text) if i not in hits and not NEEDED_TEXT_RE.search(ln.text) else None
        if m and _looks_like_name(m.group(1), protect, min_letters=5):
            hits[i] = "unlabelled_name"
    # A shorter name printed straight above or below an ID or name-label line.
    for i, kind in list(hits.items()):
        if kind not in ("nric", "name_label"):
            continue
        h = lines[i].box[3] - lines[i].box[1]
        for j, other in enumerate(lines):
            if j in hits:
                continue
            gap = min(abs(other.box[1] - lines[i].box[3]), abs(lines[i].box[1] - other.box[3]))
            if gap <= 1.2 * h and not NEEDED_TEXT_RE.search(other.text) and _looks_like_name(other.text, protect, min_letters=5):
                hits[j] = "stray_name"
    return hits


def mask_photo(data: bytes, ocr: Any = None, known_names: Iterable[str] = (), protect_words: Iterable[str] = ()) -> MaskResult:
    img = normalise_image(data)
    lines = read_lines(ocr or default_ocr(), img)
    if not [ln for ln in lines if len(ln.text.strip()) >= 3]:
        raise ValidationFailed("no readable text found in the photo", code="ocr_empty")
    hits = find_private_lines(lines, known_names, protect_words)
    draw = ImageDraw.Draw(img)
    counts: dict[str, int] = {}
    pad = 6
    for i, kind in hits.items():
        ln = lines[i]
        if len(ln.poly) >= 3:
            pts = list(ln.poly)
            draw.polygon(pts, fill=(0, 0, 0))
            draw.line(pts + [pts[0]], fill=(0, 0, 0), width=2 * pad, joint="curve")    # a margin around the text
        else:
            left, top, right, bottom = ln.box
            draw.rectangle((max(0, left - pad), max(0, top - pad), min(img.width, right + pad), min(img.height, bottom + pad)), fill=(0, 0, 0))
        counts[kind] = counts.get(kind, 0) + 1
    out = io.BytesIO()
    img.save(out, "JPEG", quality=90)                  # no EXIF is written
    kept = " ".join(ln.text for i, ln in enumerate(lines) if i not in hits)
    return MaskResult(image=out.getvalue(), mime_type="image/jpeg", lines=lines, ocr_text=kept, masked=counts)


def unmasked_photo(data: bytes) -> MaskResult:
    """The photo as it is (rotated, metadata dropped, downscaled), with no text reading and nothing blacked out. Used only when the text
    reader is switched off (SCAN_OCR_ENABLED=false): what goes to the model then still carries the label's name and address."""
    img = normalise_image(data)
    out = io.BytesIO()
    img.save(out, "JPEG", quality=90)
    return MaskResult(image=out.getvalue(), mime_type="image/jpeg", lines=[], ocr_text="", masked={"ocr_off": 1})


def placeholder_photo(data: bytes) -> MaskResult:
    """What is STORED when the text reader is off: a small grey square that carries the photo's checksum in its comment, so each photo
    still gets its own scan, but nothing identifying is kept. The real photo is never saved."""
    out = io.BytesIO()
    Image.new("RGB", (8, 8), (200, 200, 200)).save(out, "JPEG", quality=80, comment=hashlib.sha256(data).hexdigest().encode())
    return MaskResult(image=out.getvalue(), mime_type="image/jpeg", lines=[], ocr_text="", masked={"ocr_off": 1})


def scrub_value(value: str | None, known_names: Iterable[str] = ()) -> tuple[str | None, bool]:
    """Remove identity from a string the model returned. Returns (clean value or None, whether anything was removed)."""
    if value is None:
        return None, False
    if _kind(value, _name_tokens(known_names)) is not None:
        return None, True
    return value, False
