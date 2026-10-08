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


# --- a pharmacy label with a patient number before the name (found on a real photo) -------------------------------

def test_a_patient_number_followed_by_a_name_is_masked_but_the_clinic_and_the_directions_are_not():
    lines = [L("BERNARD KWOK CARDIOLOGY CLINIC", 10), L("CRESTOR 10mg - 168 Tabs", 50), L("Take 1 tab/s every morning", 90),
             L("For cholesterol lowering", 130), L("84933 CHUA CHOR KIANG DEREK", 170), L("03/06/2026", 210)]
    hits = p.find_private_lines(lines, protect_words={"crestor", "rosuvastatin"})
    assert hits == {4: "unlabelled_name"}            # only the patient line; the clinic name has a label word, the directions are sentences


@pytest.mark.parametrize("text", ["For cholesterol lowering", "Take with a full glass of water", "Keep out of reach of children",
                                  "Manufactured by IPR Pharmaceuticals Inc. Puerto Rico"])
def test_sentences_are_not_taken_for_names(text):
    assert p.find_private_lines([L(text, 10)]) == {}


@pytest.mark.parametrize("text", ["84933 CHUA CHOR KIANG DEREK", "10231 TAN AH KOW", "5521 Lim Mei Ling", "LEE MEI LING"])
def test_names_with_or_without_a_number_in_front_are_masked(text):
    assert p.find_private_lines([L(text, 10)]) == {0: "unlabelled_name"}


def test_a_name_the_ocr_joined_to_text_beside_it_is_still_masked():
    lines = [L("cted by the pres84933 CHUA CHOR KIANG DEREK", 10), L("Take 1 tab/s every morning", 50)]
    assert p.find_private_lines(lines) == {0: "unlabelled_name"}


@pytest.mark.parametrize("text", ["500 MG TABLET", "Take 168 TABS ONLY", "Qty 60 TABLETS DAILY", "Exp 2027 FILM COATED TABLET", "10 mg TWICE DAILY"])
def test_a_number_before_capital_letters_is_not_always_a_name(text):
    assert p.find_private_lines([L(text, 10)]) == {}


# --- precision: hide private lines, never the text the app needs --------------------------------------------------

@pytest.mark.parametrize("text", ["(ALVERSIME)", "COLODIUM", "PARACETAMOL", "SERRATIOPEPTIDASE", "VFCOL", "Lopeyad", "DEC 26",
                                  "CRESTOR 10mg - 168 Tabs", "MARY JANE 10 mg", "TAKE 2 TAB/S 4 times a day", "ATORVASTATIN 20 MG TABLET"])
def test_packaging_print_brand_names_and_needed_text_are_never_taken_for_names(text):
    assert p.find_private_lines([L(text, 10)]) == {}


def test_a_line_that_carries_a_strength_or_directions_is_not_hidden_even_if_it_looks_like_a_name_with_a_number():
    lines = [L("84933 TAKE 1 TAB DAILY", 10), L("5521 JANE MARY 10 mg", 50)]
    assert p.find_private_lines(lines) == {}


def test_real_names_are_still_hidden():
    lines = [L("LIM KEI WEN NICOLE", 10), L("84933 CHUA CHOR KIANG DEREK", 50), L("Patient: TAN AH KOW", 90)]
    assert set(p.find_private_lines(lines)) == {0, 1, 2}
