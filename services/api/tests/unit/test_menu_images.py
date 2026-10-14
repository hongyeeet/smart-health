"""Dish pictures and the menu (docs/specs/menu.md): the rules that need no database."""
from __future__ import annotations

import io

import pytest
from PIL import Image

from app.core.errors import ExternalServiceError
from app.llm import gateway
from app.services import food_images as fi
from app.services import menu


def test_dish_key_is_stable_and_safe():
    assert fi.dish_key("Chicken rice (regular)") == "chicken-rice-regular"
    assert fi.dish_key("  Fish soup, with a LITTLE rice!! ") == "fish-soup-with-a-little-rice"
    assert fi.dish_key("../etc/passwd") == "etc-passwd"
    assert fi.dish_key("") == ""
    assert len(fi.dish_key("x" * 300)) <= 80
    k = fi.dish_key("Mee rebus")
    assert fi.dish_key(k) == k          # a key is its own key, which the picture route relies on


def test_prompt_holds_only_the_dish_name():
    p = fi.prompt_for("Fish soup  with a little rice")
    assert "Fish soup with a little rice" in p
    assert "no text" in p.lower() and "no people" in p.lower()
    assert fi.prompt_hash("A") != fi.prompt_hash("B")
    assert fi.prompt_hash("A") == fi.prompt_hash("A")


def _png(w: int, h: int) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (w, h), (200, 120, 60)).save(out, "PNG")
    return out.getvalue()


def test_description_goes_into_the_prompt_and_a_failed_description_does_not_stop_the_picture(monkeypatch):
    _Rec(monkeypatch)
    seen = []

    def make(p):
        seen.append(p)
        return _png(800, 600)

    fi.generate_one({"dish_key": "a", "name": "A"}, make=make, put=lambda *a, **k: None, describe=lambda n: "a white bowl of clear soup")
    assert "It looks like this: a white bowl of clear soup" in seen[0]

    def no_text(n):
        raise gateway.LLMUnavailable("down", code="timeout")

    assert fi.generate_one({"dish_key": "b", "name": "B"}, make=make, put=lambda *a, **k: None, describe=no_text) == "ready"
    assert "It looks like" not in seen[1]


@pytest.mark.parametrize("size", [(1024, 1024), (1600, 900), (500, 900)])
def test_picture_is_shrunk_to_a_small_4_by_3_jpeg(size):
    jpeg = fi.to_jpeg(_png(*size))
    img = Image.open(io.BytesIO(jpeg))
    assert img.format == "JPEG" and img.size == fi.SIZE
    assert len(jpeg) < 200_000


class _Rec:
    def __init__(self, monkeypatch):
        self.calls = []
        monkeypatch.setattr(fi, "_finish", lambda key, **kw: self.calls.append(("finish", key, kw)))
        monkeypatch.setattr(fi, "_release", lambda key: self.calls.append(("release", key)))


def test_generate_one_stores_and_marks_ready(monkeypatch):
    rec = _Rec(monkeypatch)
    stored = {}
    out = fi.generate_one({"dish_key": "fish-soup", "name": "Fish soup"}, make=lambda p: _png(1024, 1024), put=lambda k, d, ct, bucket=None: stored.update(k=k, ct=ct, bucket=bucket), describe=lambda n: "a white bowl of clear soup")
    assert out == "ready"
    assert stored["k"] == "fish-soup.jpg" and stored["ct"] == "image/jpeg" and stored["bucket"] == "food-images"
    assert rec.calls[-1][0] == "finish" and rec.calls[-1][2]["ok"] is True


def test_daily_limit_puts_the_dish_back_without_counting_the_try(monkeypatch):
    rec = _Rec(monkeypatch)

    def make(p):
        raise gateway.LLMUnavailable("limit", code="daily_limit")

    assert fi.generate_one({"dish_key": "a", "name": "A"}, make=make, put=lambda *a, **k: None, describe=lambda n: "") == "limit"
    assert rec.calls == [("release", "a")]


def test_model_or_storage_failure_marks_failed_with_a_code_only(monkeypatch):
    rec = _Rec(monkeypatch)

    def bad_model(p):
        raise gateway.LLMUnavailable("secret details here", code="timeout")

    assert fi.generate_one({"dish_key": "a", "name": "A"}, make=bad_model, put=lambda *a, **k: None, describe=lambda n: "") == "failed"
    assert rec.calls[-1][2] == {"ok": False, "error": "timeout"}

    def bad_put(*a, **k):
        raise ExternalServiceError("no", code="storage_refused")

    assert fi.generate_one({"dish_key": "b", "name": "B"}, make=lambda p: _png(800, 600), put=bad_put, describe=lambda n: "") == "failed"
    assert rec.calls[-1][2]["error"] == "storage_refused"

    assert fi.generate_one({"dish_key": "c", "name": "C"}, make=lambda p: b"not an image", put=lambda *a, **k: None, describe=lambda n: "") == "failed"


def test_generate_pending_stops_at_the_daily_limit(monkeypatch):
    rows = iter([{"dish_key": "a", "name": "A"}, {"dish_key": "b", "name": "B"}, {"dish_key": "c", "name": "C"}])
    monkeypatch.setattr(fi, "_claim", lambda: next(rows, None))
    seq = iter(["ready", "limit", "ready"])
    monkeypatch.setattr(fi, "generate_one", lambda row, **kw: next(seq))
    assert fi.generate_pending(limit=5) == {"ready": 1, "failed": 0, "limit": 1}


def test_tags_use_the_placeholder_cutoffs():
    assert menu.tags_for(30, 500, True) == ["lowSalt", "lowCarb", "hawker"]
    assert menu.tags_for(60, 1200, False) == ["home"]
    assert menu.tags_for(30, 500, None) == ["lowSalt", "lowCarb"]       # the person's own meal: no hawker or home tag
    assert menu.tags_for(None, None, None) == []


def test_estimate_needs_the_persons_own_history():
    assert menu.estimate_rise(40, None) is None           # no history: no number, never a guess
    assert menu.estimate_rise(None, 0.07) is None
    assert menu.estimate_rise(0, 0.07) is None
    lo, hi = menu.estimate_rise(40, 0.07)
    assert lo < 2.8 < hi and hi - lo == pytest.approx(1.0, abs=0.11)
    assert menu.estimate_rise(2, 0.07)[0] == 0.0            # never below zero


def test_clock_text():
    assert menu._clock(12 * 60 + 15) == "12:15 pm"
    assert menu._clock(7 * 60 + 30) == "7:30 am"
    assert menu._clock(0) == "12:00 am"
