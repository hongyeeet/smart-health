"""Ask Smart Health, the retrieval planner (app/services/chat_planner.py): which extra views a question loads. Rules only, no model, no database."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services import chat_planner as P  # noqa: E402

CASES = [
    # labs
    ("What was my last HbA1c?", {"labs"}),
    ("What are my lab results?", {"labs"}),
    ("When was my last blood test?", {"labs"}),
    ("What was my fasting insulin?", {"labs"}),
    ("How is my cholesterol?", {"labs"}),
    # profile
    ("Do I have any allergies?", {"profile"}),
    ("What conditions did I list?", {"profile"}),
    ("When was I diagnosed?", {"profile"}),
    ("Who looks after my diabetes?", {"profile"}),
    ("Do I go to a polyclinic?", {"profile"}),
    # baseline
    ("Is my fasting glucose different from my usual?", {"baseline"}),
    ("How are my steps compared to my usual?", {"baseline", "longer_history"}),
    ("Is this higher than usual for me?", {"baseline"}),
    # longer history
    ("How was my glucose last month?", {"longer_history"}),
    ("Has my glucose improved over the past 3 months?", {"longer_history"}),
    ("Show my trend since June", {"longer_history"}),
    ("How many meals did I log in the last 60 days?", {"longer_history"}),
    # responses
    ("Did dinner affect my morning glucose?", {"responses"}),
    ("Which meals spike my glucose?", {"responses"}),
    ("What happens to my glucose after I walk?", {"responses"}),
    ("What patterns did you find in my data?", {"responses"}),
    # preventive
    ("When is my next eye screening?", {"preventive"}),
    ("When was my last foot check?", {"preventive"}),
    ("Am I due for a flu shot?", {"preventive"}),
    ("Is my kidney test overdue?", {"preventive"}),
    # plain 14-day questions: nothing extra
    ("How was my glucose this week?", set()),
    ("What did I eat yesterday?", set()),
    ("How many steps did I walk today?", set()),
    ("Did I take my tablets today?", set()),
    ("How is my blood pressure lately?", set()),
    ("How did I sleep last night?", set()),
    # medicine advice questions: nothing extra (the chat refuses these before any data is read)
    ("Should I stop taking metformin?", set()),
    ("Can I take more insulin tonight?", set()),
    # greetings and help
    ("hello", set()),
    ("thanks", set()),
    ("What can you help me with?", set()),
    ("", set()),
    # general-knowledge questions that never mention the person: nothing from their records
    ("What is a normal HbA1c?", set()),
    ("What is a glucose spike?", set()),
    ("Why does sleep matter for diabetes?", set()),
    # words that only look like a trigger
    ("What are the side effects of metformin?", set()),
    ("My flu symptoms started today", set()),
]


@pytest.mark.parametrize("text, want", CASES)
def test_planner_maps_the_question_to_views(text, want):
    assert P.plan(text) == want


def test_there_are_at_least_25_cases_and_every_view_is_reached():
    assert len(CASES) >= 25
    seen = set().union(*(w for _, w in CASES))
    assert seen == set(P.VIEWS)


def test_planner_is_deterministic_pure_and_only_returns_known_views():
    for text, _ in CASES:
        a, b = P.plan(text), P.plan(text)
        assert a == b and a <= set(P.VIEWS)


def test_planner_handles_odd_input_without_raising():
    for odd in (None, "   ", "\n\t", "a" * 5000, "’’", "HBA1C", "hba1c " * 200):
        assert isinstance(P.plan(odd), set)          # type: ignore[arg-type]
    assert P.plan("HBA1C") == {"labs"}


def test_a_curly_apostrophe_is_treated_like_a_straight_one():
    assert P.plan("what’s my usual morning glucose") == P.plan("what's my usual morning glucose") == {"baseline"}


def test_the_planner_makes_no_model_or_database_call():
    import inspect
    src = inspect.getsource(P)
    for banned in ("gateway", "chat_llm", "jev", "psycopg", "import requests", "execute("):
        assert banned not in src


@pytest.mark.parametrize("text, days", [
    ("How was my glucose last month?", 30), ("past month", 30), ("last 60 days", 60), ("over the last two months", 60),
    ("the past 3 months", 90), ("since June", 90), ("show my trend", 90), ("last 30 days", 30), ("last month and the three months before", 90),
])
def test_history_reaches_30_60_or_90_days(text, days):
    assert P.history_days(text) == days


@pytest.mark.parametrize("text", [
    "How was my glucose this week?", "What was my last HbA1c?", "Do I have any allergies?", "Did I take my tablets today?",
    "How many steps did I walk today?", "What are my lab results?", "When was I diagnosed?",
])
def test_plain_questions_about_the_persons_own_data_need_no_guidance(text):
    assert P.needs_guidance(text) is False


@pytest.mark.parametrize("text", [
    "What is a glucose spike?", "Why does sleep matter for diabetes?", "How can I lower my glucose?", "What is Metformin for?",
    "Tips for eating out", "Explain HbA1c", "What are the side effects of metformin?", "Is it safe to walk after dinner?", "healthy snacks",
])
def test_general_questions_do_want_guidance(text):
    assert P.needs_guidance(text) is True


def test_an_empty_question_needs_no_guidance():
    assert P.needs_guidance("") is False and P.needs_guidance(None) is False        # type: ignore[arg-type]
