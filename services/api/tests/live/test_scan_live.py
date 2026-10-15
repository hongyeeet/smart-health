"""The scan pipeline against the real model (Gemini on Vertex) and the real drug list, on made-up labels.
Costs a few cents and takes about a minute, so it only runs when asked:  RUN_LIVE=1 python -m pytest tests/live -q
Needs GOOGLE_API_KEY and DATABASE_URL in the private .env. Nothing is saved."""
import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("RUN_LIVE") != "1", reason="live model test: set RUN_LIVE=1")

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fixtures"))
import make_label_images as labels  # noqa: E402

from app.agents.scan_extractor import extract_scan  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.llm.vertex import VertexClient  # noqa: E402
from app.services.scan_privacy import default_ocr  # noqa: E402


@pytest.fixture(scope="module")
def env():
    s = get_settings()
    client = VertexClient(s.google_api_key.get_secret_value(), s.google_cloud_project, s.google_cloud_region)
    return {"client": client, "model": s.llm_vision_model, "ocr": default_ocr()}


def scan(env, sample, **kw):
    return extract_scan(labels.ALL[sample](), **env, **kw)


def value(out, field):
    return out.items[0].fields[field].value


def test_clear_prescription_is_read_correctly_and_goes_to_confirm(env):
    out, _ = scan(env, "metformin_prescription")
    assert (out.status, out.review_mode) == ("needs_review", "confirm")
    assert (value(out, "name"), value(out, "strength"), value(out, "times_per_day")) == ("METFORMIN", "500 mg", "2")
    assert value(out, "meal_relation") == "after_meal"


def test_identity_never_appears_in_the_result(env):
    out, _ = scan(env, "metformin_prescription")
    assert out.mask_summary == {"name_label": 1, "nric": 1}
    dump = out.model_dump_json().upper()
    assert "TAN AH KOW" not in dump and "S1234567D" not in dump


def test_a_second_prescription(env):
    out, _ = scan(env, "atorvastatin_prescription")
    assert out.review_mode == "confirm" and value(out, "name") == "ATORVASTATIN" and value(out, "times_per_day") == "1"
    assert "LEE MEI LING" not in out.model_dump_json().upper()


def test_a_drug_not_in_our_list_is_simply_read(env):
    out, _ = scan(env, "unknown_drug")
    assert out.review_mode == "confirm" and value(out, "name") == "ZORBLAXINE"


def test_text_on_the_label_cannot_change_the_result(env):
    out, _ = scan(env, "injection_label")
    assert value(out, "strength") == "500 mg"          # not the 5000 mg the label tells the model to report


def test_a_supplement_is_read(env):
    out, _ = scan(env, "supplement")
    assert out.items[0].item_type == "supplement" and value(out, "times_per_day") == "1"


def test_bad_photos_fail_safe(env):
    assert scan(env, "not_a_medicine")[0].reasons == ["not_a_medicine"]
    assert scan(env, "blank")[0].reasons == ["ocr_empty"]
    assert scan(env, "blurry")[0].reasons == ["ocr_empty"]
