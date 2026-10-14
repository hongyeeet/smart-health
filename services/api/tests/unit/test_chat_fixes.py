"""Fix wave (12 Oct 2026), Ask Smart Health, English only: urgent words, imperative dosing, the diagnosis line, honest no-data replies,
JEV off or capped, and the scrubbed stored message. Everything is stubbed: no model, no JEV, no database."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.agents import chat_assistant as AI  # noqa: E402
from app.llm.gateway import LLMUnavailable  # noqa: E402
from app.services import chat as C  # noqa: E402
from app.services import chat_guard as G  # noqa: E402
from app.services import texts  # noqa: E402
from test_chat_flow import ANSWER, CLEAN, STEADY, storage, turn, world  # noqa: E402,F401  (fixtures)

URGENT_PHRASES = [
    "I think I'm having a heart attack", "Am I having a heart attack?", "my chest hurts and my left arm is numb", "I have chest tightness",
    "there is pressure in my chest", "my chest feels tight", "I cannot breathe", "I can't catch my breath", "I am short of breath", "shortness of breath since morning",
    "my face is drooping", "my speech is slurred", "I think I am having a stroke", "suddenly weak on one side", "my sugar is low and I am shaky",
    "my glucose is low and I feel confused", "very low sugar and I feel faint", "he is unconscious", "she had a seizure", "I took too many tablets",
    "I think I overdosed", "my left arm is numb", "I feel dizzy and sweating, my sugar is low",
]
SELF_HARM_PHRASES = [
    "I want to kill myself", "I want to end my life", "I don't want to live anymore", "I do not want to live", "I want to hurt myself",
    "thinking about suicide", "I can't go on", "I want to take my own life",
]
CALM_PHRASES = [
    "my sugar was low yesterday", "chest day at the gym", "How was my glucose this week?", "How is my blood pressure lately?", "arm day at the gym",
    "what is a heart attack", "I had a heart attack in 2019", "backstroke swimming at the pool", "What did Smart Health learn about me?",
    "my low sugar readings this week", "the fitting room", "What is Metformin for?",
]


@pytest.mark.parametrize("text", URGENT_PHRASES)
@pytest.mark.parametrize("jev_on", [False, True])
def test_english_urgent_phrases_always_get_995_and_never_reach_a_model(world, text, jev_on):
    world["key"] = "k" if jev_on else ""
    world["res"] = dict(CLEAN)                     # JEV scoring nothing must not matter
    o = turn(text)
    assert o.kind == "urgent" and o.text == texts.tr("en", "chat.urgent") and "995" in o.text
    assert world["triage"] == [] and world["answer"] == [] and world["guard"] == []


@pytest.mark.parametrize("text", SELF_HARM_PHRASES)
@pytest.mark.parametrize("jev_on", [False, True])
def test_english_self_harm_phrases_get_the_caring_reply_never_a_model(world, text, jev_on):
    world["key"] = "k" if jev_on else ""
    o = turn(text)
    assert (o.kind, o.text) == ("urgent", texts.tr("en", "chat.self_harm")) and "995" in o.text
    assert world["triage"] == [] and world["answer"] == [] and world["guard"] == []


@pytest.mark.parametrize("text", CALM_PHRASES)
def test_ordinary_phrases_are_not_urgent(text):
    assert not C.is_urgent_text(text) and not G.is_self_harm(text)


@pytest.mark.parametrize("reply", ["Take 2 tablets of Atorvastatin tonight", "Double your dose tomorrow.", "Please skip the evening tablet.",
                                   "Your readings were steady. Reduce your insulin by 2 units.", "Stop your medicines for a week.", "Halve the dose of Metformin 500 mg."])
def test_the_reply_guard_blocks_an_imperative_dosing_sentence(reply):
    assert "medicine_advice" in G.reply_problems(reply)


@pytest.mark.parametrize("reply", ["Your medicines: Metformin 500 mg at 08:00", "You take Metformin 500 mg at 08:00 and 20:00.", "2 doses taken, 1 marked missed.",
                                   "Your glucose: 3 days with readings; average 7.9 mmol/L", "You missed 1 dose on 3 Oct."])
def test_the_reply_guard_lets_the_grounded_medicine_lines_through(reply):
    assert G.reply_problems(reply) == []


def test_an_imperative_dosing_reply_is_replaced_by_the_persons_own_summary(world):
    world["ans"] = AI.Reply(reply="Take 2 tablets of Atorvastatin tonight", reply_en="Take 2 tablets of Atorvastatin tonight")
    o = turn("How was my glucose this week?")
    assert "Atorvastatin" not in o.text and o.text.startswith(texts.tr("en", "chat.fallback_intro"))
    assert o.verdict == "blocked_med_advice"


@pytest.mark.parametrize("question", ["How is my blood pressure lately?", "How was my glucose this week?", "What did Smart Health learn about me?"])
def test_ordinary_questions_scored_between_the_strict_and_the_diagnosis_line_are_answered(world, question):
    world["key"] = "k"
    world["res"] = {"med_advice": 0.0, "diagnosis": 0.42, "urgent": 0.0}
    o = turn(question)
    assert o.kind == "answer" and world["answer"] != []


def test_a_high_jev_diagnosis_score_on_a_message_still_refuses(world):
    world["key"] = "k"
    world["res"] = {"med_advice": 0.0, "diagnosis": 0.7, "urgent": 0.0}
    assert turn("How is my blood pressure lately?").kind == "refused"


def test_the_medicine_and_urgent_lines_on_a_message_stay_strict():
    assert C.classify_message({"med_advice": 0.25, "diagnosis": 0.0, "urgent": 0.0}) == "refuse"
    assert C.classify_message({"med_advice": 0.0, "diagnosis": 0.0, "urgent": 0.5}) == "urgent"
    assert C.classify_message({"med_advice": 0.0, "diagnosis": 0.0, "urgent": 0.25}) == "caution"
    assert C.classify_message({"med_advice": 0.0, "diagnosis": 0.42, "urgent": 0.0}) == "ok"


def test_the_reply_guard_keeps_the_strict_diagnosis_line():
    assert C.classify_message({"med_advice": 0.0, "diagnosis": 0.42, "urgent": 0.0}, reply=True) == "refuse"


def test_a_reply_scored_0_42_for_diagnosis_by_jev_is_still_blocked(world):
    world["key"] = "k"
    world["res_by_text"][STEADY] = {"med_advice": 0.0, "diagnosis": 0.42, "urgent": 0.0}
    world["ans"] = AI.Reply(reply=STEADY, reply_en=STEADY)
    o = turn("How was my glucose this week?")
    assert STEADY not in o.text


@pytest.mark.parametrize("question", ["do I have kidney disease", "what is wrong with me", "is this neuropathy", "Is it kidney disease?", "Is there something wrong with my feet?"])
@pytest.mark.parametrize("jev_on", [False, True])
def test_real_diagnosis_questions_are_refused_by_our_own_words_whatever_jev_scores(world, question, jev_on):
    world["key"] = "k" if jev_on else ""
    world["res"] = dict(CLEAN)                      # JEV would let it pass; the local rule must not
    o = turn(question)
    assert (o.kind, o.verdict) == ("refused", "blocked_diagnosis") and world["answer"] == []


def test_an_honest_no_data_reply_is_shown_even_when_jev_dislikes_it(world):
    sentence = "I do not have that in your data."
    world["key"] = "k"
    world["res_by_text"][sentence] = {"med_advice": 0.0, "diagnosis": 0.9, "urgent": 0.0}
    world["ans"] = AI.Reply(reply=sentence, reply_en=sentence)
    o = turn("How was my blood pressure this week?")
    assert o.kind == "empty" and o.text.startswith(sentence) and o.verdict == "pass"
    assert "Metformin" not in o.text


def test_a_no_data_sentence_that_also_gives_advice_is_still_blocked(world):
    reply = "I do not have that in your data, but you should stop your metformin."
    world["ans"] = AI.Reply(reply=reply, reply_en=reply)
    assert reply not in turn("How was my glucose this week?").text


@pytest.mark.parametrize("reply, ok", [("I do not have that in your data yet.", True), ("I don't have any information about your blood pressure in your data.", True),
                                       ("Smart Health has no data on that yet.", True), ("I do not have 5 readings in your data.", False), ("Your glucose was steady.", False)])
def test_is_no_data_reply(reply, ok):
    assert G.is_no_data_reply(reply) is ok


def test_when_nothing_matches_the_question_it_says_there_is_no_data_not_unrelated_sections(world):
    world["ans_exc"] = LLMUnavailable("down")
    o = turn("Tell me about my feet")
    assert o.text.startswith(texts.tr("en", "chat.empty"))
    assert "Metformin" not in o.text and "Your medicines" not in o.text and "Why is my morning sugar high" not in o.text


def test_a_blocked_reply_with_no_matching_section_also_says_no_data(world):
    world["ans"] = AI.Reply(reply="You probably have neuropathy.", reply_en="You probably have neuropathy.")
    o = turn("Tell me about my feet")
    assert o.text.startswith(texts.tr("en", "chat.empty")) and "neuropathy" not in o.text


# ----------------------------------------------------------------------------- JEV off or capped: the local rules still run and the chat still answers
@pytest.mark.parametrize("jev_state", ["off", "capped"])
def test_with_jev_off_or_capped_a_grounded_question_is_answered(world, jev_state):
    world["key"] = "" if jev_state == "off" else "k"
    world["res"] = {"med_advice": None, "diagnosis": None, "urgent": None}      # capped: every answer is missing
    o = turn("How was my glucose this week?")
    assert o.kind == "answer" and ANSWER in o.text and texts.tr("en", "chat.guard_down") not in o.text


@pytest.mark.parametrize("jev_state", ["off", "capped"])
def test_with_jev_off_or_capped_a_medicine_advice_question_is_still_refused(world, jev_state):
    world["key"] = "" if jev_state == "off" else "k"
    world["res"] = {"med_advice": None, "diagnosis": None, "urgent": None}
    o = turn("Should I skip my metformin tonight?")
    assert (o.kind, o.verdict) == ("refused", "blocked_med_advice") and world["answer"] == []


@pytest.mark.parametrize("jev_state", ["off", "capped"])
def test_with_jev_off_or_capped_an_urgent_phrase_still_gets_995(world, jev_state):
    world["key"] = "" if jev_state == "off" else "k"
    world["res"] = {"med_advice": None, "diagnosis": None, "urgent": None}
    o = turn("I think I'm having a heart attack")
    assert o.kind == "urgent" and "995" in o.text and world["answer"] == []


# ----------------------------------------------------------------------------- the stored message is scrubbed
def test_the_stored_message_has_no_nric_phone_or_email(world, storage):
    out = C.send("person-0123456789ab", "u1", "My NRIC is S1234567D, call 91234567 or mail tan@example.com. How was my glucose this week?", None)
    stored = storage[0]
    assert stored[0] == "user"
    for secret in ("S1234567D", "91234567", "tan@example.com"):
        assert secret not in stored[1] and secret not in out["message"]["text"]
    assert "How was my glucose this week?" in stored[1]


def test_a_doctor_question_offer_carries_the_scrubbed_words(world, storage):
    out = C.send("person-0123456789ab", "u1", "Should I stop my pills? My email is tan@example.com", None)
    offer = [a for a in out["actions"] if a["kind"] == "doctor_question"]
    assert offer and "tan@example.com" not in offer[0]["text"]
