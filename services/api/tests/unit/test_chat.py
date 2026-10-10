"""Ask Smart Health (I1): urgent bypass, refusals, guard on the reply, the conservative paths, scrubbing, starters and the 8-message limit.

No database and no network: the model, JEV, storage and the trace are fakes.
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.llm import chat as chat_llm  # noqa: E402
from app.llm import jev  # noqa: E402
from app.llm.gateway import LLMUnavailable  # noqa: E402
from app.services import chat as C  # noqa: E402

REAL_GENERATE = chat_llm.generate
TODAY = date(2026, 10, 10)
CLEAN = {"med_advice": 0.01, "diagnosis": 0.01, "urgent": 0.01}


class FakeRun:
    id = "run-1"

    def __init__(self, *a, **k):
        self.steps, self.finished = [], None

    def step(self, node, tool, inp, fn):
        self.steps.append(node)
        return fn()

    def finish(self, status="ok", error=None, keep=True, tokens=None, model_id=None):
        self.finished = status


@contextmanager
def fake_tx():
    yield None


ROWS = {
    "daily": [{"local_date": date(2026, 10, 2), "glucose_mean_mmol": 9.4, "tir_pct": 70, "tbr_pct": 0, "tar_pct": 30, "steps_total": 5000, "sleep_hours": 6.5,
               "meals_n": 3, "exercise_min": 20, "doses_scheduled": 3, "doses_taken": 2, "doses_missed": 1}],
    "anchor": date(2026, 10, 2), "meds": [{"name": "Metformin 500 mg", "times": ["08:00", None], "as_needed": False, "purpose": "Helps lower blood sugar."}],
    "meals": [{"day": date(2026, 10, 2), "meal_type": "lunch", "food": "Chicken rice", "carbs_g": 60, "sodium_mg": 900}], "workouts": [],
    "questions": ["Why is my morning sugar high?"], "facts": ["Walks after dinner"], "names": ["Mr Tan", "Mdm Lim Mei Ling"], "passages": [],
}


@pytest.fixture
def env(monkeypatch):
    """A world where everything works; each test breaks one piece."""
    calls = {"model": [], "guard": []}
    monkeypatch.setattr(C, "tx", fake_tx)
    monkeypatch.setattr(C, "_log_guard", lambda *a, **k: None)
    monkeypatch.setattr(C, "load_rows", lambda conn, uid, today, text: ROWS)
    monkeypatch.setattr(C, "load_names", lambda uid: C.name_tokens(*ROWS["names"]))
    monkeypatch.setattr(jev, "guard", lambda t: calls["guard"].append(t) or dict(CLEAN))
    monkeypatch.setattr(jev, "guard_blocks", lambda t: (False, dict(CLEAN)))
    monkeypatch.setattr(jev, "choice", lambda s, i, c: jev.Choice("nutrition", {}, 0.9))

    def gen(system, history, user):
        calls["model"].append((system, history, user))
        return "Your average glucose was 9.4 mmol/L on 1 day."

    monkeypatch.setattr(chat_llm, "generate", gen)
    return calls


def run_decide(text, history=None):
    return C.decide("u1", text, history or [], FakeRun(), TODAY)


# ----------------------------------------------------------------------------- urgent
@pytest.mark.parametrize("text", ["I have chest pain", "I can't breathe", "my dad fainted", "my sugar is very low and I feel confused", "I feel suicidal",
                                  "Very low glucose now", "I am confused and my glucose is low"])
def test_urgent_words_bypass_the_model_and_jev(env, text):
    o = run_decide(text)
    assert (o.kind, o.text, o.open_urgent) == ("urgent", C.URGENT_TEXT, True)
    assert env["model"] == [] and env["guard"] == []


def test_confused_alone_is_not_urgent():
    assert not C.is_urgent_text("I am confused about my appointment")
    assert not C.is_urgent_text("How was my glucose this week?")


def test_jev_urgent_probability_also_bypasses_the_model(env, monkeypatch):
    monkeypatch.setattr(jev, "guard", lambda t: {"med_advice": 0.0, "diagnosis": 0.0, "urgent": 0.6})
    o = run_decide("I feel strange")
    assert o.kind == "urgent" and o.open_urgent and env["model"] == []


def test_urgent_edge_between_floor_and_urgent_p_is_a_caution_not_an_answer(env, monkeypatch):
    monkeypatch.setattr(jev, "guard", lambda t: {"med_advice": 0.0, "diagnosis": 0.0, "urgent": 0.3})
    o = run_decide("I feel a bit off")
    assert (o.kind, o.text) == ("refused", C.CAUTION_TEXT) and env["model"] == []
    monkeypatch.setattr(jev, "guard", lambda t: {"med_advice": 0.0, "diagnosis": 0.0, "urgent": 0.19})
    assert run_decide("How was my week?").kind == "answer"   # just under the floor


# ----------------------------------------------------------------------------- refusals
def test_medicine_question_is_refused_and_offers_the_doctor_question(env, monkeypatch):
    monkeypatch.setattr(jev, "guard", lambda t: {"med_advice": 0.95, "diagnosis": 0.0, "urgent": 0.0})
    o = run_decide("Should I stop taking metformin?")
    assert (o.kind, o.text, o.offer_question, o.verdict) == ("refused", C.REFUSED_TEXT, True, "blocked_med_advice")
    assert env["model"] == []


def test_diagnosis_question_is_refused(env, monkeypatch):
    monkeypatch.setattr(jev, "guard", lambda t: {"med_advice": 0.0, "diagnosis": 0.9, "urgent": 0.0})
    o = run_decide("Do I have kidney disease?")
    assert o.kind == "refused" and o.offer_question and o.verdict == "blocked_diagnosis" and env["model"] == []


def test_guard_edge_is_inclusive_at_one_minus_floor(env, monkeypatch):
    cut = 1 - C.settings.jev_guard_floor
    monkeypatch.setattr(jev, "guard", lambda t: {"med_advice": cut, "diagnosis": 0.0, "urgent": 0.0})
    assert run_decide("x question").kind == "refused"
    monkeypatch.setattr(jev, "guard", lambda t: {"med_advice": cut - 0.01, "diagnosis": 0.0, "urgent": 0.0})
    assert run_decide("x question").kind == "answer"


def test_unreachable_jev_takes_the_conservative_path_and_no_model_call(env, monkeypatch):
    monkeypatch.setattr(jev, "guard", lambda t: {"med_advice": None, "diagnosis": None, "urgent": None})
    o = run_decide("How was my glucose?")
    assert (o.kind, o.text) == ("unavailable", C.GUARD_DOWN_TEXT) and env["model"] == []
    monkeypatch.setattr(jev, "guard", lambda t: {"med_advice": 0.0, "diagnosis": None, "urgent": 0.0})   # one missing answer is enough
    assert run_decide("How was my glucose?").kind == "unavailable"


# ----------------------------------------------------------------------------- the reply
def test_a_blocked_reply_is_replaced(env, monkeypatch):
    monkeypatch.setattr(jev, "guard_blocks", lambda t: (True, {"med_advice": 0.9, "diagnosis": 0.0, "urgent": 0.0}))
    o = run_decide("How was my glucose?")
    assert (o.kind, o.text, o.offer_question) == ("refused", C.BLOCKED_REPLY_TEXT, True)
    assert "9.4" not in o.text


def test_reply_guard_unreachable_replaces_the_reply(env, monkeypatch):
    monkeypatch.setattr(jev, "guard_blocks", lambda t: (True, {"med_advice": None, "diagnosis": None, "urgent": None}))
    assert run_decide("How was my glucose?").text == C.BLOCKED_REPLY_TEXT


def test_a_good_answer_has_sources_from_the_data_used(env):
    o = run_decide("How was my glucose this week?")
    assert o.kind == "answer" and "9.4" in o.text
    assert [s.to for s in o.sources] == ["C2"]    # nutrition route sent glucose and food; only glucose is named


def test_model_failure_is_a_calm_reply(env, monkeypatch):
    def boom(*a):
        raise LLMUnavailable("down")

    monkeypatch.setattr(chat_llm, "generate", boom)
    o = run_decide("How was my glucose this week?")
    assert (o.kind, o.text) == ("unavailable", C.UNAVAILABLE_TEXT)


def test_daily_cap_reached_is_a_calm_reply(env, monkeypatch):
    monkeypatch.setattr(chat_llm.usage, "allowed", lambda p: False)
    monkeypatch.setattr(chat_llm, "generate", REAL_GENERATE)   # the real function, which checks the cap first
    o = run_decide("How was my glucose this week?")
    assert o.kind == "unavailable" and o.text == C.UNAVAILABLE_TEXT


def test_empty_data_gets_the_honest_reply_without_the_model(env, monkeypatch):
    empty = dict(ROWS, daily=[], meds=[], meals=[], workouts=[], questions=[], facts=[], anchor=None)
    monkeypatch.setattr(C, "load_rows", lambda *a: empty)
    o = run_decide("How was my glucose this week?")
    assert (o.kind, o.text) == ("empty", C.EMPTY_TEXT) and env["model"] == []


def test_help_question_is_answered_without_any_service(env):
    o = run_decide("What can you help me with?")
    assert (o.kind, o.text) == ("help", C.HELP_TEXT) and env["guard"] == [] and env["model"] == []


def test_low_confidence_route_uses_every_section(env, monkeypatch):
    monkeypatch.setattr(jev, "choice", lambda s, i, c: jev.Choice("adherence", {}, 0.59))
    run_decide("How was my glucose this week?")
    assert "YOUR GLUCOSE" in env["model"][0][2] and "YOUR MEDICINES" in env["model"][0][2]
    monkeypatch.setattr(jev, "choice", lambda s, i, c: None)   # JEV unreachable for routing: general path, not a failure
    assert run_decide("How was my glucose this week?").kind == "answer"


def test_confident_route_limits_the_sections(env, monkeypatch):
    monkeypatch.setattr(jev, "choice", lambda s, i, c: jev.Choice("adherence", {}, 0.9))
    run_decide("Did I take my tablets?")
    prompt = env["model"][0][2]
    assert "YOUR DOSES" in prompt and "YOUR MEALS" not in prompt


# ----------------------------------------------------------------------------- privacy
def test_identifiers_never_reach_the_model_or_jev(env):
    text = "I am Tan, my NRIC is S1234567D, call 91234567 or tan@example.com. How was my glucose?"
    run_decide(text, history=[("user", "Mdm Lim phone 81234567"), ("assistant", "ok")])
    system, history, user = env["model"][0]
    sent = " ".join([system, user, *[t for _, t in history], *env["guard"]])
    for secret in ("S1234567D", "91234567", "81234567", "tan@example.com", "Mei Ling", "Lim", "Tan"):
        assert secret not in sent, secret
    assert "Mr Tan" not in sent


def test_name_tokens_skip_titles_and_short_words():
    assert C.name_tokens("Mr Tan", "Mdm Lim Mei Ling", None) == ["Tan", "Lim", "Mei", "Ling"]
    assert C.name_tokens("Dr Ng") == []


def test_scrub_replaces_whole_words_only():
    assert C.scrub("Tanya and Tan", ["Tan"]) == "Tanya and the person"
    assert C.scrub("mail a.b@c.sg now") == "mail [email] now"


# ----------------------------------------------------------------------------- text limits and tidy
def test_clean_text_trims_and_limits():
    assert C.clean_text("  hello \n  there  ") == "hello there"
    assert len(C.clean_text("a" * 900)) == C.MAX_TEXT
    assert C.clean_text("   ") == ""


def test_tidy_strips_markdown_and_cuts_long_replies_at_a_sentence():
    assert C.tidy("**Hello** _there_") == "Hello there"
    long = ("This is a sentence. " * 60).strip()
    out = C.tidy(long)
    assert len(out.split()) <= C.MAX_REPLY_WORDS and out.endswith(".")


# ----------------------------------------------------------------------------- starters
def test_starters_come_from_the_persons_data():
    assert C.build_starters({"cgm_days": 0, "medicines": [], "questions": 0}) == ["What can you help me with?"]
    full = C.build_starters({"cgm_days": 7, "medicines": ["Metformin 500 mg"], "questions": 2})
    assert full == ["How was my glucose this week?", "What is Metformin for?", "What should I ask my doctor?"]
    assert C.build_starters({"cgm_days": 0, "medicines": ["CRESTOR"], "questions": 1}) == ["What is CRESTOR for?", "What should I ask my doctor?"]


def test_cgm_week_threshold_both_sides():
    assert "How was my glucose this week?" in C.build_starters({"cgm_days": C.STARTER_CGM_DAYS, "medicines": [], "questions": 0})
    assert "How was my glucose this week?" not in C.build_starters({"cgm_days": C.STARTER_CGM_DAYS - 1, "medicines": [], "questions": 0})


def test_unreadable_medicine_label_is_not_a_starter():
    assert C.build_starters({"cgm_days": 0, "medicines": ["Herbal tonic (label not readable)"], "questions": 0}) == ["What can you help me with?"]


def test_follow_ups_skip_the_question_just_asked():
    f = {"cgm_days": 7, "medicines": ["Metformin 500 mg"], "questions": 1}
    assert "How was my glucose this week?" not in C.follow_ups(f, "how was my glucose this week?")
    assert C.follow_ups({"cgm_days": 0, "medicines": [], "questions": 0}, "hi") == []


# ----------------------------------------------------------------------------- the context
def test_context_has_only_the_persons_rows_and_marks_missing_data():
    ctx = C.build_sections(ROWS, TODAY)
    text = ctx.text()
    assert "mean 9.4 mmol/L" in text and "times 08:00" in text and "None" not in text
    assert "Tan" not in text and "Lim" not in text
    sparse = C.build_sections(dict(ROWS, daily=[{**ROWS["daily"][0], "glucose_mean_mmol": None, "sleep_hours": None}]), TODAY)
    assert not next(s for s in sparse.sections if s.key == "glucose").lines and not next(s for s in sparse.sections if s.key == "sleep").lines


def test_history_is_limited_to_eight_messages(monkeypatch):
    seen = {}

    class Cur:
        def __init__(self, rows):
            self.rows = rows

        def fetchall(self):
            return self.rows

    class Conn:
        def execute(self, sql, params):
            seen["limit"] = params[1]
            return Cur([{"role": "assistant" if i % 2 else "user", "content": f"m{i}"} for i in range(params[1], 0, -1)])

    @contextmanager
    def tx():
        yield Conn()

    monkeypatch.setattr(C, "tx", tx)
    h = C._history("c1")
    assert seen["limit"] == 8 and len(h) == 8 and h[0][1] == "m1" and h[-1][1] == "m8"   # oldest first, never more than 8


# ----------------------------------------------------------------------------- the whole turn
def test_send_stores_the_exchange_and_never_raises(env, monkeypatch):
    saved = []
    monkeypatch.setattr(C, "Run", FakeRun)
    monkeypatch.setattr(C, "_conversation", lambda uid, cid: "conv-1")
    monkeypatch.setattr(C, "_history", lambda conv: [])
    monkeypatch.setattr(C, "_save", lambda conv, role, text, at, verdict=None, run_id=None: saved.append((role, text, verdict)) or {"id": f"m{len(saved)}", "at": datetime(2026, 10, 10).isoformat()})
    monkeypatch.setattr(C, "starter_facts", lambda conn, uid, today: {"cgm_days": 7, "medicines": ["Metformin 500 mg"], "questions": 0})
    out = C.send("demo", "u1", "How was my glucose this week?", None)
    assert out["conversation_id"] == "conv-1" and out["reply"]["kind"] == "answer"
    assert [r for r, _, _ in saved] == ["user", "assistant"]
    assert out["follow_ups"] == ["What is Metformin for?"]
    # a refusal is stored as a fixed template and offers the action with the person's own words
    monkeypatch.setattr(jev, "guard", lambda t: {"med_advice": 0.99, "diagnosis": 0.0, "urgent": 0.0})
    out = C.send("demo", "u1", "Can I double my dose?", "conv-1")
    assert out["reply"]["text"] == C.REFUSED_TEXT and saved[-1][0] == "system_template"
    assert out["actions"] == [{"kind": "doctor_question", "label": "Add to my doctor questions", "to": None, "text": "Can I double my dose?"}]
    # urgent opens J1 and gives no follow-ups
    out = C.send("demo", "u1", "I have chest pain", "conv-1")
    assert out["actions"][0]["to"] == "J1" and out["follow_ups"] == []
    # an unexpected error inside a turn becomes a calm reply
    monkeypatch.setattr(C, "decide", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    out = C.send("demo", "u1", "hello there", "conv-1")
    assert out["reply"]["text"] == C.UNAVAILABLE_TEXT


def test_empty_message_is_rejected():
    with pytest.raises(ValueError):
        C.send("demo", "u1", "   ", None)


def test_model_is_never_asked_for_a_non_text_helper():
    # the chat model name comes from LLM_CHAT_MODEL, with the vision model as a fallback
    assert chat_llm.model_name()


def test_a_polite_pointer_to_the_doctor_is_not_a_source():
    ctx = C.build_sections(ROWS, TODAY)
    got = C.pick_sources(ctx.sections, "How was my glucose?", "Your mean was 9.4. It is worth asking your doctor.", [])
    assert [s.to for s in got] == ["C2"]
    got = C.pick_sources(ctx.sections, "What should I ask my doctor?", "You wrote one question about your morning.", [])
    assert [s.to for s in got] == ["K3"]
