"""The AI wording of the doctor report's key findings (app/agents/report_insight.py): the checks a line must pass, the fallback to the
code-written findings, the daily limit, and the cache. The model is never called: `_generate` and the gateway are replaced."""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.agents import report_insight as ri
from app.llm import gateway
from app.llm.gateway import LLMUnavailable
from app.services import usage

FACTS = [
    "Days in the period: 14",
    "Time in range: 62% of readings, target range 3.9 to 10.0 mmol/L",
    "Time below range: 8%, including 2.1% below 3.0 mmol/L (reference below 4%)",
    "Symptom entries logged: 5",
    "Symptom entries with glucose below 3.9 mmol/L: 2, between 08:00 and 22:00",
    "Metformin: 27 of 28 scheduled times marked taken (96%)",
]
FALLBACK = ["Time in range 62% (reference >70%); time below range 8%.", "2 of 5 symptom entries were logged with glucose below 3.9 mmol/L."]
GOOD = [
    ri.Finding(label="Glucose", text="Time in range was 62% of readings, against a target range of 3.9 to 10.0 mmol/L."),
    ri.Finding(label="Symptoms", text="2 of 5 symptom entries were logged with glucose below 3.9 mmol/L, between 08:00 and 22:00."),
    ri.Finding(label="Medicines", text="Metformin: 27 of 28 scheduled times were marked taken (96%)."),
]


@pytest.fixture(autouse=True)
def fresh_cache():
    ri._CACHE.clear()
    yield
    ri._CACHE.clear()


def out(*items: ri.Finding) -> ri.FindingsOut:
    return ri.FindingsOut(findings=list(items))


# ----------------------------------------------------------------------------------------------- the line checks
def test_a_number_that_is_not_in_the_facts_is_rejected_and_the_rest_is_kept() -> None:
    kept, rejected = ri.checked_lines(out(
        ri.Finding(label="Glucose", text="Time below range was 12%, which is more than the reference."),       # 10 is not a fact
        *GOOD,
    ), FACTS)
    assert len(kept) == 3 and "number" in rejected
    assert all("10%" not in line for line in kept)


def test_a_number_written_as_in_the_facts_is_kept_even_with_a_time() -> None:
    kept, _ = ri.checked_lines(out(ri.Finding(label="Symptoms", text="Symptom entries were logged between 08:00 and 22:00 with 2 low readings.")), FACTS)
    assert kept == ["Symptoms: Symptom entries were logged between 08:00 and 22:00 with 2 low readings."]


@pytest.mark.parametrize("text", [
    "Stop taking this medicine when the reading is low.",
    "Skip the evening dose on busy days.",
    "Change the morning dose if the readings stay high.",
    "This is safe to keep up with.",
    "Glucose was normal over the period.",
    "The readings were abnormal in the evening.",
    "The low readings were caused by the morning dose.",
    "The lows happened because of the lunch dose.",
    "Time in range should be above 70%.",
    "Metformin 500 mg is good for glucose.",
    "Take 500 mg of metformin with food.",
    "Take the medicine with food.",
    "Ask your doctor about the 2 low readings.",
])
def test_advice_dose_judgement_and_cause_words_are_never_shown(text: str) -> None:
    kept, rejected = ri.checked_lines(out(ri.Finding(label="Glucose", text=text)), FACTS + ["low readings: 2"])
    assert kept == [] and rejected == ["wording"]


def test_a_label_must_be_plain_words() -> None:
    kept, rejected = ri.checked_lines(out(ri.Finding(label="Glucose 2", text="Time in range was 62% of readings this period."),
                                          ri.Finding(label="Stop", text="Time in range was 62% of readings this period.")), FACTS)
    assert kept == [] and rejected == ["label", "wording"]


def test_a_sentence_must_be_short_but_not_empty_and_gets_a_full_stop() -> None:
    kept, rejected = ri.checked_lines(out(ri.Finding(label="Glucose", text="Too short"), ri.Finding(label="Glucose", text="x" * 250),
                                          ri.Finding(label="Glucose", text="Time in range was 62% of readings")), FACTS)
    assert kept == ["Glucose: Time in range was 62% of readings."] and rejected == ["length", "length"]


def test_at_most_five_lines_are_kept_and_repeats_are_dropped() -> None:
    items = [ri.Finding(label=f"Glucose", text=f"Time in range was {n}% of readings this period.") for n in (62, 62)]
    items += [ri.Finding(label="Glucose", text="Time in range was 8% of readings this period.")] * 2
    kept, _ = ri.checked_lines(out(*items, *GOOD, *GOOD), FACTS + ["Time in range was 8% of readings this period."])
    assert len(kept) == ri.MAX_FINDINGS and len(set(kept)) == len(kept)


def test_numbers_are_read_the_same_way_in_the_facts_and_the_sentence() -> None:
    assert ri.numbers("Time in range: 62% (reference >70%); 08:00 to 22:00") == [62.0, 70.0, 8.0, 0.0, 22.0, 0.0]


# ----------------------------------------------------------------------------------------------- what the report gets
def test_three_good_lines_are_the_ai_findings(monkeypatch) -> None:
    monkeypatch.setattr(ri, "_generate", lambda facts: out(*GOOD))
    lines, source = ri.key_findings(FACTS, FALLBACK, user_key="u1", days=14, start="2026-09-20", end="2026-10-03")
    assert source == "ai"
    assert lines[0] == "Glucose: Time in range was 62% of readings, against a target range of 3.9 to 10.0 mmol/L."
    assert len(lines) == 3


def test_fewer_than_three_good_lines_fall_back_to_the_code_written_findings(monkeypatch) -> None:
    monkeypatch.setattr(ri, "_generate", lambda facts: out(GOOD[0], ri.Finding(label="Glucose", text="Time below range was 10% of readings.")))
    lines, source = ri.key_findings(FACTS, FALLBACK, user_key="u2", days=14, start="a", end="b")
    assert source == "rules" and lines == FALLBACK


@pytest.mark.parametrize("code", ["model_unavailable", "timeout", "daily_limit", "bad_response"])
def test_a_failed_model_call_falls_back_and_never_breaks_the_report(monkeypatch, code: str) -> None:
    def fail(facts):
        raise LLMUnavailable("no", code=code)
    monkeypatch.setattr(ri, "_generate", fail)
    lines, source = ri.key_findings(FACTS, FALLBACK, user_key="u3", days=14, start="a", end="b")
    assert source == "rules" and lines == FALLBACK


def test_an_unexpected_error_also_falls_back(monkeypatch) -> None:
    def boom(facts):
        raise RuntimeError("network")
    monkeypatch.setattr(ri, "_generate", boom)
    assert ri.key_findings(FACTS, FALLBACK, user_key="u4", days=14, start="a", end="b") == (FALLBACK, "rules")


def test_the_daily_limit_is_checked_before_any_call_and_falls_back(monkeypatch) -> None:
    monkeypatch.setattr(usage, "allowed", lambda provider: False)

    def no_client():
        raise AssertionError("the model must not be reached when the daily limit is reached")
    monkeypatch.setattr(gateway, "_client", no_client)
    with pytest.raises(LLMUnavailable) as e:
        gateway.text_json("system", "prompt", ri.FindingsOut)
    assert e.value.code == "daily_limit"
    assert ri.key_findings(FACTS, FALLBACK, user_key="u5", days=14, start="a", end="b") == (FALLBACK, "rules")


def test_without_credentials_the_model_call_fails_into_the_fallback(monkeypatch) -> None:
    monkeypatch.setattr(usage, "allowed", lambda provider: True)

    def no_creds():
        raise LLMUnavailable("No Vertex AI credentials", code="model_unavailable")
    monkeypatch.setattr(gateway, "_client", no_creds)
    assert ri.key_findings(FACTS, FALLBACK, user_key="u6", days=14, start="a", end="b") == (FALLBACK, "rules")


def test_too_little_data_is_not_sent_to_the_model(monkeypatch) -> None:
    def never(facts):
        raise AssertionError("no facts worth wording")
    monkeypatch.setattr(ri, "_generate", never)
    assert ri.key_findings(["Days in the period: 14"], ["No sensor glucose readings in this period."], user_key="u7", days=14, start="a", end="b") == (
        ["No sensor glucose readings in this period."], "rules")


# ----------------------------------------------------------------------------------------------- the cache
def test_the_same_person_period_and_facts_do_not_call_the_model_again(monkeypatch) -> None:
    calls: list[int] = []

    def gen(facts):
        calls.append(1)
        return out(*GOOD)
    monkeypatch.setattr(ri, "_generate", gen)
    first = ri.key_findings(FACTS, FALLBACK, user_key="cache-a", days=14, start="s", end="e")
    second = ri.key_findings(FACTS, FALLBACK, user_key="cache-a", days=14, start="s", end="e")
    assert first == second and len(calls) == 1


def test_changed_facts_or_another_person_call_the_model_again(monkeypatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr(ri, "_generate", lambda facts: (calls.append(1), out(*GOOD))[1])
    ri.key_findings(FACTS, FALLBACK, user_key="cache-b", days=14, start="s", end="e")
    ri.key_findings(FACTS + ["Urgent alerts: 1"], FALLBACK, user_key="cache-b", days=14, start="s", end="e")
    ri.key_findings(FACTS, FALLBACK, user_key="cache-c", days=14, start="s", end="e")
    assert len(calls) == 3


def test_a_failure_is_not_repeated_on_every_page_load(monkeypatch) -> None:
    calls: list[int] = []

    def fail(facts):
        calls.append(1)
        raise LLMUnavailable("timed out", code="timeout")
    monkeypatch.setattr(ri, "_generate", fail)
    for _ in range(3):
        assert ri.key_findings(FACTS, FALLBACK, user_key="cache-d", days=14, start="s", end="e") == (FALLBACK, "rules")
    assert len(calls) == 1


def test_the_cache_is_bounded(monkeypatch) -> None:
    monkeypatch.setattr(ri, "_generate", lambda facts: out(*GOOD))
    monkeypatch.setattr(ri, "CACHE_MAX", 3)
    for k in range(5):
        ri.key_findings(FACTS, FALLBACK, user_key=f"bound-{k}", days=14, start="s", end="e")
    assert len(ri._CACHE) == 3


# ----------------------------------------------------------------------------------------------- the report
def test_the_report_carries_the_source_and_drops_the_internal_facts(monkeypatch) -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from app.services import doctor_report as dr

    tz = ZoneInfo("Asia/Singapore")
    t0 = datetime(2026, 10, 1, 0, 0, tzinfo=tz)
    cgm = [(t0.replace(day=1 + k // 96, hour=(k % 96) // 4, minute=(k % 4) * 15), 6.0 if k % 2 else 11.0) for k in range(192)]
    now = datetime(2026, 10, 3, 9, 0, tzinfo=tz)
    inputs = dr.Inputs(now=now, tz=tz, start=dr.date(2026, 10, 1), end=dr.date(2026, 10, 2), profile={"glucose_target_low": 3.9, "glucose_target_high": 10.0}, cgm=cgm)
    report = dr.build(inputs)
    report["_owner"], report["_days"] = "owner-x", 14
    no_numbers = out(ri.Finding(label="Glucose", text="Time in range was lower than the reference this period."),
                     ri.Finding(label="Symptoms", text="Symptoms were logged together with glucose readings in the period."),
                     ri.Finding(label="Medicines", text="Medicines were marked taken in most of the scheduled times."))
    monkeypatch.setattr(ri, "_generate", lambda facts: no_numbers)
    done = dr.word_findings(report)
    assert done["key_findings_source"] == "ai" and done["key_findings"][0].startswith("Glucose: ") and len(done["key_findings"]) == 3
    assert "_facts" not in done and "_owner" not in done and "_days" not in done


def test_the_report_keeps_the_rules_findings_when_the_model_is_not_reached(monkeypatch) -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from app.services import doctor_report as dr

    tz = ZoneInfo("Asia/Singapore")
    now = datetime(2026, 10, 3, 9, 0, tzinfo=tz)
    cgm = [(datetime(2026, 10, 1, tzinfo=tz) + timedelta(minutes=15 * k), 6.0) for k in range(192)]
    inputs = dr.Inputs(now=now, tz=tz, start=dr.date(2026, 10, 1), end=dr.date(2026, 10, 2), profile={"glucose_target_low": 3.9, "glucose_target_high": 10.0}, cgm=cgm)
    report = dr.build(inputs)
    before = list(report["key_findings"])
    report["_owner"], report["_days"] = "owner-y", 14

    def fail(facts):
        raise LLMUnavailable("no", code="model_unavailable")
    monkeypatch.setattr(ri, "_generate", fail)
    done = dr.word_findings(report)
    assert done["key_findings"] == before and done["key_findings_source"] == "rules"
