"""Meal photo reading (E7-2): the model gateway and POST /meals/analyze, with the model, the usage counter, the database and the run trace faked.

Covers: success, model error, bad JSON, timeout, daily limit, not food, a missing google-genai package, the run record closed on every path,
and the rule that a sugar or fibre value is never above carbs. No database and no network.
"""
from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.agents import meal  # noqa: E402
from app.api.routers import meals  # noqa: E402
from app.llm import gateway  # noqa: E402
from app.llm.gateway import LLMUnavailable  # noqa: E402
from app.services import usage  # noqa: E402

PHOTO = b"\xff\xd8\xff fake jpeg bytes for the stub"
GOOD_JSON = (
    '{"is_food": true, "meal_name": "Chicken rice", "items": [{"name": "rice", "grams": 200}], '
    '"kcal": 650, "carbs_g": 80, "protein_g": 30, "fat_g": 20, "sugar_g": 90, "fibre_g": 2, "sodium_mg": 1100, '
    '"confidence": 0.9, "portion_note": "One plate."}'
)


class FakeResponse:
    def __init__(self, text: str):
        self.text = text
        self.parsed = None
        self.usage_metadata = None


class FakeModels:
    def __init__(self, answer=None, error: Exception | None = None):
        self.answer, self.error, self.calls = answer, error, 0

    def generate_content(self, **kwargs):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return FakeResponse(self.answer)


class FakeClient:
    def __init__(self, models: FakeModels):
        self.models = models


@pytest.fixture()
def no_db(monkeypatch):
    """The usage counter and the cost record are fakes: nothing is written."""
    monkeypatch.setattr(usage, "record", lambda *a, **k: None)
    monkeypatch.setattr(usage, "allowed", lambda provider: True)


def use_model(monkeypatch, models: FakeModels) -> FakeModels:
    monkeypatch.setattr(gateway, "_client", lambda: FakeClient(models))
    return models


class FakeRun:
    """Stands in for app.agents.trace.Run: records how the run was closed."""

    last = None

    def __init__(self, *a, **k):
        self.finished: list[tuple] = []
        FakeRun.last = self

    def finish(self, status, error, keep, acc, model):
        self.finished.append((status, error, model))


@pytest.fixture()
def router(monkeypatch, no_db):
    """The meals router alone, with the run trace, the database writes and the food guard faked."""
    monkeypatch.setattr(meals, "Run", FakeRun)
    monkeypatch.setattr(meals.logstore, "current_user", lambda: uuid.UUID(int=1))
    monkeypatch.setattr(meals.logstore, "save_meal_analysis", lambda payload: str(uuid.UUID(int=2)))
    monkeypatch.setattr("app.db.nutritionstore.guarded", lambda *a, **k: True)
    app = FastAPI()
    app.include_router(meals.router)
    return TestClient(app)


def post_photo(client: TestClient):
    return client.post("/meals/analyze", files={"file": ("meal.jpg", PHOTO, "image/jpeg")})


# --- the model gateway, through analyse_meal ---

def test_success_returns_the_estimate_and_codes_the_flags(monkeypatch, no_db):
    use_model(monkeypatch, FakeModels(answer=GOOD_JSON))
    est = meal.analyse_meal(PHOTO, "image/jpeg", "half portion")
    assert est.is_food and est.meal_name == "Chicken rice" and est.kcal == 650
    assert est.items[0].name == "rice" and est.carbs_g == 80
    assert meal.flags_for(est.carbs_g, est.sugar_g, est.sodium_mg) == ["high_salt", "high_sugar"]  # sugar 80 g is at least 25 g


def test_sugar_and_fibre_are_never_above_carbs(monkeypatch, no_db):
    use_model(monkeypatch, FakeModels(answer=GOOD_JSON))  # sugar_g 90 against carbs_g 80
    est = meal.analyse_meal(PHOTO, "image/jpeg", None)
    assert est.sugar_g == 80  # clamped to carbs
    assert est.fibre_g == 2


def test_unjudged_values_stay_null_not_zero(monkeypatch, no_db):
    use_model(monkeypatch, FakeModels(answer='{"is_food": true, "meal_name": "Soup", "kcal": null, "carbs_g": 20}'))
    est = meal.analyse_meal(PHOTO, "image/jpeg", None)
    assert est.kcal is None and est.sodium_mg is None and est.protein_g is None


def test_model_error_is_model_unavailable(monkeypatch, no_db):
    use_model(monkeypatch, FakeModels(error=RuntimeError("HTTP 500 from the service")))
    with pytest.raises(LLMUnavailable) as e:
        meal.analyse_meal(PHOTO, "image/jpeg", None)
    assert e.value.code == "model_unavailable"


def test_missing_google_package_is_model_unavailable_not_a_crash(monkeypatch, no_db):
    """The root cause of the broken screen: google-genai missing made the import escape as an unhandled error."""
    monkeypatch.setitem(sys.modules, "google.genai", None)
    with pytest.raises(LLMUnavailable) as e:
        meal.analyse_meal(PHOTO, "image/jpeg", None)
    assert e.value.code == "model_unavailable"


def test_bad_json_is_bad_response(monkeypatch, no_db):
    use_model(monkeypatch, FakeModels(answer="Sorry, here is a lovely meal!"))
    with pytest.raises(LLMUnavailable) as e:
        meal.analyse_meal(PHOTO, "image/jpeg", None)
    assert e.value.code == "bad_response"


def test_timeout_is_timeout(monkeypatch, no_db):
    use_model(monkeypatch, FakeModels(error=TimeoutError("The read operation timed out")))
    with pytest.raises(LLMUnavailable) as e:
        meal.analyse_meal(PHOTO, "image/jpeg", None)
    assert e.value.code == "timeout"


def test_daily_limit_refuses_before_the_model_is_called(monkeypatch):
    monkeypatch.setattr(usage, "record", lambda *a, **k: None)
    monkeypatch.setattr(usage, "allowed", lambda provider: False)
    models = use_model(monkeypatch, FakeModels(answer=GOOD_JSON))
    with pytest.raises(LLMUnavailable) as e:
        meal.analyse_meal(PHOTO, "image/jpeg", None)
    assert e.value.code == "daily_limit"
    assert models.calls == 0


def test_not_food_is_returned_as_an_answer(monkeypatch, no_db):
    use_model(monkeypatch, FakeModels(answer='{"is_food": false}'))
    est = meal.analyse_meal(PHOTO, "image/jpeg", None)
    assert est.is_food is False and est.kcal is None


# --- POST /meals/analyze ---

def test_endpoint_success_returns_macros_and_closes_the_run(monkeypatch, router):
    use_model(monkeypatch, FakeModels(answer=GOOD_JSON))
    r = post_photo(router)
    assert r.status_code == 200
    d = r.json()
    assert d["name"] == "Chicken rice" and d["macros"]["kcal"] == 650 and d["analysisId"]
    assert d["flags"] == ["high_salt", "high_sugar"] and d["modelId"]
    assert FakeRun.last.finished == [("ok", None, meal.settings.llm_vision_model)]


@pytest.mark.parametrize(
    "error, code, status",
    [
        (RuntimeError("HTTP 500"), "model_unavailable", 503),
        (TimeoutError("timed out"), "timeout", 503),
    ],
)
def test_endpoint_model_failures_are_json_with_a_code(monkeypatch, router, error, code, status):
    use_model(monkeypatch, FakeModels(error=error))
    r = post_photo(router)
    assert r.status_code == status
    assert r.json()["code"] == code and r.json()["detail"]
    assert FakeRun.last.finished[-1][0:2] == ("error", code)  # the run record is closed


def test_endpoint_bad_json_is_503_bad_response(monkeypatch, router):
    use_model(monkeypatch, FakeModels(answer="not json at all"))
    r = post_photo(router)
    assert r.status_code == 503 and r.json()["code"] == "bad_response"
    assert FakeRun.last.finished[-1][0:2] == ("error", "bad_response")


def test_endpoint_daily_limit_is_503_daily_limit(monkeypatch, router):
    monkeypatch.setattr(usage, "allowed", lambda provider: False)
    use_model(monkeypatch, FakeModels(answer=GOOD_JSON))
    r = post_photo(router)
    assert r.status_code == 503 and r.json()["code"] == "daily_limit"


def test_endpoint_not_food_is_422(monkeypatch, router):
    use_model(monkeypatch, FakeModels(answer='{"is_food": false}'))
    r = post_photo(router)
    assert r.status_code == 422 and r.json()["code"] == "not_food"


def test_endpoint_unexpected_crash_still_returns_json_and_closes_the_run(monkeypatch, router):
    def boom(*a, **k):
        raise KeyError("something unexpected")

    monkeypatch.setattr(meals, "analyse_meal", boom)
    r = post_photo(router)
    assert r.status_code == 503 and r.json()["code"] == "model_unavailable"
    assert FakeRun.last.finished[-1][0:2] == ("error", "model_unavailable")


def test_endpoint_slow_analysis_gives_up_within_the_limit(monkeypatch, router):
    def slow(*a, **k):
        time.sleep(1.0)
        return meal.MealEstimate(is_food=True)

    monkeypatch.setattr(meals, "analyse_meal", slow)
    monkeypatch.setattr(meals, "ANALYSIS_LIMIT_S", 0.05)
    t0 = time.monotonic()
    r = post_photo(router)
    assert r.status_code == 503 and r.json()["code"] == "timeout"
    assert time.monotonic() - t0 < 0.9  # did not wait for the slow model
    assert FakeRun.last.finished[-1][0:2] == ("error", "timeout")


@pytest.mark.parametrize(
    "content_type, data, status, code",
    [
        ("text/plain", PHOTO, 415, "bad_photo"),
        ("image/jpeg", b"", 400, "bad_photo"),
        ("image/jpeg", b"x" * 11, 413, "bad_photo"),  # the size limit is lowered below, so no large upload is sent
    ],
    ids=["not-an-image", "empty", "too-large"],
)
def test_endpoint_bad_photo_is_a_json_error(monkeypatch, router, content_type, data, status, code):
    monkeypatch.setattr(meals, "MAX_BYTES", 10)
    r = router.post("/meals/analyze", files={"file": ("x", data, content_type)})
    assert r.status_code == status and r.json()["code"] == code
