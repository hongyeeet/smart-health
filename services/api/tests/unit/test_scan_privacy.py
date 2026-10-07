"""Identity must not reach the model: the masking of a label photo and the scrubbing of the model's answer.
Uses the offline OCR once for the photo tests (a few seconds); the rest is pure text. Run from services/api:  python -m pytest tests/unit -q"""
import io
import sys
from pathlib import Path

import pytest
from PIL import Image

from app.core.errors import ValidationFailed
from app.services import scan_privacy as p

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fixtures"))
import make_label_images as labels  # noqa: E402


@pytest.fixture(scope="module")
def ocr():
    return p.default_ocr()


def L(text: str, top: int, left: int = 40, h: int = 30) -> p.OcrLine:
    return p.OcrLine(text, (left, top, left + 8 * len(text), top + h), 0.9)


# --- photos -------------------------------------------------------------------------------------------------

def test_name_and_nric_are_blacked_out_and_the_drug_is_kept(ocr):
    m = p.mask_photo(labels.metformin_prescription(), ocr=ocr)
    assert m.masked == {"name_label": 1, "nric": 1}
    assert "METFORMIN" in m.ocr_text and "TAN" not in m.ocr_text and "S1234567D" not in m.ocr_text
    # the blacked-out copy really has black boxes where the two lines were
    again = [ln.text for ln in p.read_lines(ocr, Image.open(io.BytesIO(m.image)).convert("RGB"))]
    assert not any("TAN" in t or "S1234567" in t for t in again)
    assert any("METFORMIN" in t for t in again)


def test_a_known_name_is_blacked_out_wherever_it_appears(ocr):
    m = p.mask_photo(labels.unknown_drug(), ocr=ocr, known_names=["Mr Wong Kai"])
    assert "WONG" not in m.ocr_text


def test_no_text_means_the_photo_is_refused_not_sent(ocr):
    for img in (labels.blank(), labels.blurry()):
        with pytest.raises(ValidationFailed) as e:
            p.mask_photo(img, ocr=ocr)
        assert e.value.code == "ocr_empty"


def test_the_stored_copy_has_no_metadata():
    img = Image.new("RGB", (300, 200), "white")
    exif = Image.Exif()
    exif[0x010F] = "SomePhone"          # camera make
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    clean = p.normalise_image(buf.getvalue())
    out = io.BytesIO()
    clean.save(out, "JPEG")
    assert len(Image.open(io.BytesIO(out.getvalue())).getexif()) == 0


@pytest.mark.parametrize("case,code", [("empty", "file_empty"), ("text", "file_type_not_allowed"), ("huge", "file_too_large")])
def test_bad_files_are_refused(case, code):
    data = {"empty": b"", "text": b"not an image", "huge": b"x" * (p.MAX_BYTES + 1)}[case]
    with pytest.raises(ValidationFailed) as e:
        p.normalise_image(data)
    assert e.value.code == code


def test_gif_is_not_an_allowed_type():
    buf = io.BytesIO()
    Image.new("RGB", (20, 20)).save(buf, "GIF")
    with pytest.raises(ValidationFailed):
        p.normalise_image(buf.getvalue())


def test_large_photos_are_shrunk():
    buf = io.BytesIO()
    Image.new("RGB", (5000, 3000), "white").save(buf, "JPEG")
    assert max(p.normalise_image(buf.getvalue()).size) == p.MAX_SIDE


# --- which lines are private (no OCR needed) ------------------------------------------------------------------

@pytest.mark.parametrize("text,kind", [
    ("NRIC: S1234567D", "nric"), ("S7654321A", "nric"), ("t0123456z", "nric"), ("FIN G1234567X", "nric"),
    ("Patient: TAN AH KOW", "name_label"), ("Pt. Name: LEE", "name_label"), ("Name: LEE MEI LING", "name_label"), ("Nama: Siti", "name_label"),
    ("姓名：陈大文", "name_label"), ("DOB: 12/03/1966", "birth_date"), ("Date of birth 1966", "birth_date"),
    ("Tel 91234567", "phone"), ("+65 8123 4567", "phone"), ("tan@example.com", "email"),
    ("Blk 123 Ang Mo Kio Ave 3", "address"), ("#04-12", "address"), ("Singapore 560123", "address"),
])
def test_private_lines_are_recognised(text, kind):
    assert p.find_private_lines([L(text, 10)]) == {0: kind}


@pytest.mark.parametrize("text", ["METFORMIN 500 mg TABLET", "Take 1 tablet twice daily after meals", "Qty: 60 Date: 02/10/2026",
                                  "Dr Lim Wei Ming", "Ptyalin 10 mg", "Tablet", "Glucophage XR 1000 mg"])
def test_drug_lines_are_not_masked(text):
    assert p.find_private_lines([L(text, 10)]) == {}


def test_a_label_alone_on_its_line_hides_the_value_beside_it():
    lines = [L("Patient:", 10, left=40), L("TAN AH KOW", 10, left=200), L("METFORMIN 500 mg", 100)]
    assert set(p.find_private_lines(lines)) == {0, 1}


def test_a_stray_name_right_under_an_nric_is_masked_but_label_words_are_not():
    lines = [L("S1234567D", 10), L("TAN AH KOW", 50), L("Take 1 tablet twice daily", 90), L("METFORMIN 500 mg", 130)]
    assert set(p.find_private_lines(lines)) == {0, 1}
    close = [L("S1234567D", 10), L("Take 1 tablet", 50)]
    assert set(p.find_private_lines(close)) == {0}                       # label words: not a name
    drug = [L("S1234567D", 10), L("Glucophage Metformin", 50)]
    assert set(p.find_private_lines(drug, protect_words={"glucophage", "metformin"})) == {0}


# --- the model's answer ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["S1234567D", "Patient: TAN", "91234567", "a@b.com", "DOB 1960"])
def test_identity_is_removed_from_a_value(value):
    assert p.scrub_value(value) == (None, True)


def test_the_users_own_name_is_removed_but_the_doctor_is_not():
    assert p.scrub_value("Take for Siti Aminah", ["Mdm Siti Aminah"]) == (None, True)
    assert p.scrub_value("Dr Lim Wei Ming", ["Mdm Siti Aminah"]) == ("Dr Lim Wei Ming", False)
    assert p.scrub_value("500 mg") == ("500 mg", False)
    assert p.scrub_value(None) == (None, False)
