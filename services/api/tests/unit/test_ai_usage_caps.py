"""Per-kind AI daily caps (services/usage.py): each provider has its own count and cap, the old AI_DAILY_CALL_CAP is the default
for any other provider, and one kind being used up never blocks another. The counter is a fake: no database and no network.
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

import pytest
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.config import Settings, settings  # noqa: E402
from app.llm import chat as chat_llm  # noqa: E402
from app.llm import gateway  # noqa: E402
from app.llm.gateway import LLMUnavailable  # noqa: E402
from app.services import usage  # noqa: E402


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class FakeDB:
    """Stands in for the ai_usage_daily table: one dict row per (day, provider), with the SQL the usage module sends."""

    def __init__(self):
        self.rows: dict[tuple, dict] = {}

    def seed(self, provider, calls=0, blocked=0, cost=None):
        self.rows[(usage._day(), provider)] = {"provider": provider, "calls": calls, "blocked": blocked, "input_tokens": 0,
                                               "output_tokens": 0, "cost_usd": cost}

    def count(self, provider):
        return self.rows.get((usage._day(), provider), {"calls": 0})["calls"]

    def blocked(self, provider):
        return self.rows.get((usage._day(), provider), {"blocked": 0})["blocked"]

    def tx(self):
        db = self

        @contextmanager
        def cm():
            yield _Conn(db)

        return cm()


class _Conn:
    def __init__(self, db: FakeDB):
        self.db = db

    def execute(self, sql, params=()):
        s = " ".join(sql.split()).lower()
        if s.startswith("insert into ai_usage_daily"):
            day, provider, calls, blocked, inp, out, cost = params
            r = self.db.rows.setdefault((day, provider), {"provider": provider, "calls": 0, "blocked": 0, "input_tokens": 0,
                                                         "output_tokens": 0, "cost_usd": None})
            r["calls"] += calls
            r["blocked"] += blocked
            r["input_tokens"] += inp
            r["output_tokens"] += out
            if cost is not None:
                r["cost_usd"] = (r["cost_usd"] or 0) + cost
            return _Result([])
        if "and provider=%s" in s:
            day, provider = params
            r = self.db.rows.get((day, provider))
            return _Result([{"calls": r["calls"], "cost_usd": r["cost_usd"], "blocked": r["blocked"]}] if r else [])
        (day,) = params
        return _Result([dict(r) for (d, _), r in self.db.rows.items() if d == day])


@pytest.fixture()
def db(monkeypatch):
    fake = FakeDB()
    monkeypatch.setattr(usage, "tx", fake.tx)
    return fake


class Out(BaseModel):
    x: str


def test_each_kind_has_its_own_default_cap():
    assert Settings.model_fields["ai_cap_vertex_vision"].default == 300
    assert Settings.model_fields["ai_cap_vertex_generate"].default == 500
    assert Settings.model_fields["ai_cap_vertex_embed"].default == 2000
    assert Settings.model_fields["ai_cap_jev"].default == 500
    assert usage.cap_for("vertex_vision") == settings.ai_cap_vertex_vision
    assert usage.cap_for("vertex_generate") == settings.ai_cap_vertex_generate
    assert usage.cap_for("vertex_embed") == settings.ai_cap_vertex_embed
    assert usage.cap_for("jev") == settings.ai_cap_jev


def test_old_shared_cap_is_the_default_for_any_other_provider(monkeypatch):
    monkeypatch.setattr(settings, "ai_daily_call_cap", 7)
    assert usage.cap_for("some_future_provider") == 7
    assert usage.cap_for("jev") == settings.ai_cap_jev  # a kind with its own cap ignores the old one


def test_a_provider_is_refused_only_at_its_own_cap(db):
    db.seed("vertex_vision", calls=settings.ai_cap_vertex_vision)
    assert usage.allowed("vertex_vision") is False
    assert db.blocked("vertex_vision") == 1
    assert db.count("vertex_vision") == settings.ai_cap_vertex_vision  # the refusal is not a call
    assert usage.allowed("vertex_generate") is True
    assert db.blocked("vertex_generate") == 0


def test_embeddings_stay_open_when_photo_reads_are_full_and_the_old_cap_is_passed(db, monkeypatch):
    monkeypatch.setattr(settings, "ai_daily_call_cap", 500)
    db.seed("vertex_vision", calls=settings.ai_cap_vertex_vision)
    db.seed("vertex_embed", calls=600)  # above the old shared cap of 500, below its own cap
    assert usage.allowed("vertex_vision") is False
    assert usage.allowed("vertex_embed") is True
    assert db.blocked("vertex_embed") == 0


def test_full_embeddings_do_not_block_photo_reads(db):
    db.seed("vertex_embed", calls=settings.ai_cap_vertex_embed, blocked=1300)
    assert usage.allowed("vertex_embed") is False
    assert usage.allowed("vertex_vision") is True
    assert db.blocked("vertex_vision") == 0
    assert db.blocked("vertex_embed") == 1301


def test_one_blocked_provider_does_not_block_another(db):
    db.seed("vertex_vision", calls=settings.ai_cap_vertex_vision)
    db.seed("jev", calls=settings.ai_cap_jev)
    db.seed("vertex_generate", calls=10)
    assert usage.allowed("vertex_vision") is False
    assert usage.allowed("jev") is False
    assert usage.allowed("vertex_generate") is True
    assert usage.allowed("vertex_embed") is True


def test_jev_cost_cap_is_checked_on_jev_alone(db, monkeypatch):
    monkeypatch.setattr(settings, "ai_daily_budget_usd", 5.0)
    db.seed("jev", calls=1, cost=5.0)
    assert usage.allowed("jev") is False
    assert usage.allowed("vertex_vision") is True


def test_today_reports_per_provider_calls_caps_blocked_and_over_cap(db):
    db.seed("vertex_vision", calls=settings.ai_cap_vertex_vision, blocked=4)
    db.seed("vertex_embed", calls=1200)
    t = usage.today()
    by = {p["provider"]: p for p in t["providers"]}
    assert by["vertex_vision"]["overCap"] is True and by["vertex_vision"]["blocked"] == 4
    assert by["vertex_vision"]["cap"] == settings.ai_cap_vertex_vision
    assert by["vertex_embed"]["overCap"] is False and by["vertex_embed"]["calls"] == 1200
    assert by["vertex_generate"]["calls"] == 0  # every known kind is listed, even with no calls yet
    assert t["caps"] == {"vertex_vision": settings.ai_cap_vertex_vision, "vertex_generate": settings.ai_cap_vertex_generate,
                         "vertex_embed": settings.ai_cap_vertex_embed, "vertex_image": settings.ai_cap_vertex_image, "jev": settings.ai_cap_jev}
    assert t["calls"] == settings.ai_cap_vertex_vision + 1200 and t["blocked"] == 4
    assert t["callCap"] == sum(t["caps"].values())
    assert t["overCap"] is True
    for key in ("day", "calls", "callCap", "costUsd", "budgetUsd", "blocked", "overCap", "providers", "note"):
        assert key in t


def test_today_is_not_over_cap_when_no_kind_is_full(db):
    db.seed("vertex_embed", calls=5)
    assert usage.today()["overCap"] is False


def test_record_counts_under_the_named_provider(db):
    usage.record("vertex_generate", 120, 40)
    usage.record("vertex_vision", blocked=True)
    assert db.count("vertex_generate") == 1
    assert db.rows[(usage._day(), "vertex_generate")]["input_tokens"] == 120
    assert db.count("vertex_vision") == 0 and db.blocked("vertex_vision") == 1


def test_over_cap_keeps_its_shared_signature():
    assert not usage.over_cap(10, 0.2)
    assert usage.over_cap(10, 0.2, cap=10)
    assert usage.over_cap(settings.ai_daily_call_cap, 0)
    assert usage.over_cap(1, settings.ai_daily_budget_usd)


def test_database_unreachable_does_not_stop_the_call(monkeypatch):
    def boom():
        raise RuntimeError("database down")

    monkeypatch.setattr(usage, "tx", boom)
    assert usage.allowed("vertex_vision") is True


def test_photo_read_is_checked_under_vertex_vision(monkeypatch):
    seen = []
    monkeypatch.setattr(usage, "allowed", lambda p: seen.append(p) or False)
    with pytest.raises(LLMUnavailable) as e:
        gateway.vision_json(b"img", "image/jpeg", "prompt", Out)
    assert seen == ["vertex_vision"] and e.value.code == "daily_limit"


def test_brief_findings_text_is_checked_under_vertex_generate(monkeypatch):
    seen = []
    monkeypatch.setattr(usage, "allowed", lambda p: seen.append(p) or False)
    with pytest.raises(LLMUnavailable) as e:
        gateway.text_json("system", "prompt", Out)
    assert seen == ["vertex_generate"] and e.value.code == "daily_limit"


def test_chat_text_is_checked_under_vertex_generate(monkeypatch):
    seen = []
    monkeypatch.setattr(usage, "allowed", lambda p: seen.append(p) or False)
    with pytest.raises(LLMUnavailable):
        chat_llm.generate("system", [], "hello")
    assert seen == ["vertex_generate"]
