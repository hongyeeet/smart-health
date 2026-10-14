"""Ask Smart Health (I1): urgent bypass, self-harm words, the speed limit, identifiers, the fallback when the model is down, storage through
send(), starters and the 8-message limit.

No database and no network: the model (AI.triage, AI.answer), JEV, storage and the trace are fakes. The rules themselves are tested in
test_chat_guard.py and the decision order in test_chat_flow.py.
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.agents import chat_assistant as AI  # noqa: E402
from app.llm import chat as chat_llm  # noqa: E402
from app.llm import jev  # noqa: E402
from app.llm.gateway import LLMUnavailable  # noqa: E402
from app.services import chat as C  # noqa: E402
from app.services import chat_guard as G  # noqa: E402
from app.services import texts  # noqa: E402

REAL_ANSWER = AI.answer
TODAY = date(2026, 10, 10)
CLEAN = {"med_advice": 0.01, "diagnosis": 0.01, "urgent": 0.01}
ANSWER = "Your average glucose was 9.4 mmol/L on 1 day."


class FakeRun:
    id = None

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
    """A world where everything works and JEV is not configured; each test breaks one piece."""
    G.LIMITER.reset()
    calls = {"triage": [], "model": [], "guard": []}
    monkeypatch.setattr(C, "tx", fake_tx)
    monkeypatch.setattr(C, "_log_guard", lambda *a, **k: None)
    monkeypatch.setattr(C, "load_rows", lambda conn, uid, today, text: ROWS)
    monkeypatch.setattr(C, "load_names", lambda uid: C.name_tokens(*ROWS["names"]))
    monkeypatch.setattr(C.nutritionstore, "lunch_options", lambda *a, **k: [])
    monkeypatch.setattr(jev, "_key", lambda: "")
    monkeypatch.setattr(jev, "guard", lambda t: calls["guard"].append(t) or dict(CLEAN))

    def triage(safe):
        calls["triage"].append(safe)
        return AI.Triage(intent="data_summary")

    def answer(lang_name, context_text, history, safe_text):
        calls["model"].append((lang_name, context_text, history, safe_text))
        return AI.Reply(reply=ANSWER, reply_en=ANSWER)

    monkeypatch.setattr(AI, "triage", triage)
    monkeypatch.setattr(AI, "answer", answer)
    # any model call that is not faked fails loudly here, never reaches the network
    monkeypatch.setattr(chat_llm, "generate", lambda *a, **k: pytest.fail("a live model call was made in a unit test"))
    yield calls
    G.LIMITER.reset()


def run_decide(text, history=None):
    return C.decide("u1", text, history or [], FakeRun(), TODAY)


# ----------------------------------------------------------------------------- urgent
@pytest.mark.parametrize("text", ["I have chest pain", "I can't breathe", "my dad fainted", "my sugar is very low and I feel confused",
                                  "Very low glucose now", "I am confused and my glucose is low"])
def test_urgent_words_bypass_the_model_and_jev(env, text):
    o = run_decide(text)
    assert (o.kind, o.text, o.open_urgent) == ("urgent", C.URGENT_TEXT, True)
    assert env["model"] == [] and env["guard"] == [] and env["triage"] == []


@pytest.mark.parametrize("text", ["I feel suicidal", "I want to die", "I want to end my life"])
def test_self_harm_words_get_the_caring_reply_and_no_model_call(env, text):
    o = run_decide(text)
    assert (o.kind, o.text) == ("urgent", texts.tr("en", "chat.self_harm"))
    assert env["model"] == [] and env["triage"] == [] and env["guard"] == []


def test_confused_alone_is_not_urgent():
    assert not C.is_urgent_text("I am confused about my appointment")
    assert not C.is_urgent_text("How was my glucose this week?")


def test_a_low_reading_with_a_sign_of_a_low_is_urgent(env):
    o = run_decide("My glucose was 3.4 and I am sweating")
    assert (o.kind, o.text, o.open_urgent) == ("urgent", C.URGENT_TEXT, True)
    assert env["model"] == [] and env["triage"] == []


def test_jev_urgent_probability_also_bypasses_the_model(env, monkeypatch):
    monkeypatch.setattr(jev, "_key", lambda: "k")
    monkeypatch.setattr(jev, "guard", lambda t: {"med_advice": 0.0, "diagnosis": 0.0, "urgent": 0.6})
    o = run_decide("I feel strange")
    assert o.kind == "urgent" and o.open_urgent and env["model"] == [] and env["triage"] == []


def test_urgent_edge_between_floor_and_urgent_p_is_a_caution_not_an_answer(env, monkeypatch):
    monkeypatch.setattr(jev, "_key", lambda: "k")
    monkeypatch.setattr(jev, "guard", lambda t: {"med_advice": 0.0, "diagnosis": 0.0, "urgent": 0.3})
    o = run_decide("I feel a bit off")
    assert (o.kind, o.text) == ("refused", C.CAUTION_TEXT) and env["model"] == []
    monkeypatch.setattr(jev, "guard", lambda t: {"med_advice": 0.0, "diagnosis": 0.0, "urgent": 0.19})
    assert run_decide("How was my week?").kind == "answer"   # just under the floor


# ----------------------------------------------------------------------------- privacy
def test_identifiers_never_reach_the_model_or_jev(env, monkeypatch):
    monkeypatch.setattr(jev, "_key", lambda: "k")
    # (the word NRIC itself is refused by the rules before any model call: see test_chat_flow; here the number must be scrubbed)
    text = "I am Tan, my ID is S1234567D, call 91234567 or tan@example.com. How was my glucose?"
    run_decide(text, history=[("user", "Mdm Lim phone 81234567"), ("assistant", "ok")])
    lang, ctx, hist, safe = env["model"][0]
    sent = " ".join([*env["triage"], ctx, *[t for _, t in hist], safe, *env["guard"]])
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


def test_one_day_of_data_reads_in_the_singular():
    text = C.build_sections(ROWS, TODAY).text()          # ROWS has one day with glucose and sleep
    assert "1 day with glucose readings" in text and "on 1 night" in text
    assert "1 days" not in text and "1 nights" not in text


@pytest.mark.parametrize("phrase", ["1 dose planned", "1 meal logged"])
def test_one_dose_and_one_meal_read_in_the_singular(phrase):
    rows = dict(ROWS, daily=[dict(ROWS["daily"][0], doses_scheduled=1, doses_taken=1, doses_missed=0, meals_n=1)])
    assert phrase in C.build_sections(rows, TODAY).text()


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


# ----------------------------------------------------------------------------- send(): storage, model failure, cap
@pytest.fixture
def stored(env, monkeypatch):
    saved = []
    monkeypatch.setattr(C, "Run", FakeRun)
    monkeypatch.setattr(C, "_conversation", lambda uid, cid: "conv-1")
    monkeypatch.setattr(C, "_history", lambda conv: [])
    monkeypatch.setattr(C, "_save", lambda conv, role, text, at, verdict=None, run_id=None: saved.append((role, text, verdict)) or {"id": f"m{len(saved)}", "at": datetime(2026, 10, 10).isoformat()})
    monkeypatch.setattr(C, "starter_facts", lambda conn, uid, today: {"cgm_days": 7, "medicines": ["Metformin 500 mg"], "questions": 0})
    return saved


def test_send_stores_the_exchange_and_never_raises(env, stored, monkeypatch):
    out = C.send("person-0123456789ab", "u1", "How was my glucose this week?", None)
    assert out["conversation_id"] == "conv-1" and out["reply"]["kind"] == "answer"
    assert [r for r, _, _ in stored] == ["user", "assistant"]
    assert out["follow_ups"] == ["What is Metformin for?"]
    # a medicine change is stored as a fixed template and offers the action with the person's own words
    out = C.send("person-0123456789ab", "u1", "Can I double my dose?", "conv-1")
    assert out["reply"]["text"].startswith(texts.tr("en", "chat.med_change")) and stored[-1][0] == "system_template"
    assert out["actions"] == [{"kind": "doctor_question", "label": "Add to my doctor questions", "to": None, "text": "Can I double my dose?"}]
    # urgent opens J1 and gives no follow-ups
    out = C.send("person-0123456789ab", "u1", "I have chest pain", "conv-1")
    assert out["actions"][0]["to"] == "J1" and out["follow_ups"] == []
    # an unexpected error inside a turn becomes a calm reply
    monkeypatch.setattr(C, "decide", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    out = C.send("person-0123456789ab", "u1", "hello there", "conv-1")
    assert out["reply"]["text"] == C.UNAVAILABLE_TEXT


def test_model_failure_gives_the_persons_own_summary_through_send(env, stored, monkeypatch):
    def down(*a):
        raise LLMUnavailable("down")

    monkeypatch.setattr(AI, "answer", down)
    out = C.send("person-0123456789ab", "u1", "How was my glucose this week?", None)
    assert out["reply"]["kind"] == "answer" and out["reply"]["text"].startswith(texts.tr("en", "chat.fallback_intro"))
    assert "Your glucose:" in out["reply"]["text"]
    assert C.GUARD_DOWN_TEXT not in out["reply"]["text"] and [r for r, _, _ in stored] == ["user", "assistant"]


def test_daily_cap_gives_a_calm_reply_through_the_real_answer_path(env, stored, monkeypatch):
    monkeypatch.setattr(AI, "answer", REAL_ANSWER)            # the real function, which checks the daily cap before any call
    monkeypatch.setattr(chat_llm.usage, "allowed", lambda p: False)
    out = C.send("person-0123456789ab", "u1", "How was my glucose this week?", None)
    assert out["reply"]["text"].startswith(texts.tr("en", "chat.fallback_intro"))
    assert env["model"] == [] and "Your glucose:" in out["reply"]["text"]


def test_empty_message_is_rejected():
    with pytest.raises(ValueError):
        C.send("person-0123456789ab", "u1", "   ", None)


def test_model_is_never_asked_for_a_non_text_helper():
    # the chat model name comes from LLM_CHAT_MODEL, with the vision model as a fallback
    assert chat_llm.model_name()


def test_a_polite_pointer_to_the_doctor_is_not_a_source():
    ctx = C.build_sections(ROWS, TODAY)
    got = C.pick_sources(ctx.sections, "How was my glucose?", "Your mean was 9.4. It is worth asking your doctor.", [])
    assert [s.to for s in got] == ["C2"]
    got = C.pick_sources(ctx.sections, "What should I ask my doctor?", "You wrote one question about your morning.", [])
    assert [s.to for s in got] == ["K3"]
