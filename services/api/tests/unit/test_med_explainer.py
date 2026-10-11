"""The medicine explainer: the model's answer is checked by code before anything can be shown (docs/specs/f3-explainer.md).

A fake client stands in for the model and the web search, so no network is used.
"""
import json

import pytest

from app.agents import med_explainer as x
from app.core.errors import ExternalServiceError
from app.llm.vertex import GroundedResult, WebSource

SOURCES = [WebSource("drugs.com", "https://vertexaisearch.cloud.google.com/r/1"), WebSource("nih.gov", "https://vertexaisearch.cloud.google.com/r/2")]
GOOD = {"identified": True,
        "what_it_is_for": "Crestor (rosuvastatin) is used to lower bad cholesterol in the blood. It helps protect the heart and blood vessels.",
        "how_it_works": "It slows the liver from making cholesterol.",
        "what_you_may_notice": "Some people notice muscle aches. It can take a few weeks to show its full effect.",
        "why_timing_matters": "Its effect builds up over time, so taking it regularly matters more than the exact hour.",
        "side_effects": ["Headache", "Muscle aches", "Nausea", "Stomach pain"],
        "tell_doctor": "Contact your doctor if you have unexplained muscle pain or yellow skin."}


class FakeClient:
    def __init__(self, *replies):
        self.replies, self.prompts, self.systems = list(replies), [], []

    def generate_grounded(self, *, model, system, prompt, max_output_tokens=8192, timeout_s=90.0):
        self.prompts.append(prompt)
        self.systems.append(system)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        text, sources = r if isinstance(r, tuple) else (r, SOURCES)
        return GroundedResult(text=text if isinstance(text, str) else json.dumps(text), model=model, input_tokens=300, output_tokens=120,
                              latency_ms=20, sources=sources)


def run(client, **over):
    args = {"name": "CRESTOR", "strength": "10 mg", "kind": "prescription", "directions": "Take 1 tab/s every morning For cholesterol lowering"}
    args.update(over)
    return x.explain(client, model="m", **args)


def test_a_grounded_clear_answer_is_ready_with_its_four_parts_and_its_sources():
    out = run(FakeClient(GOOD))
    assert out.status == "ready" and out.purpose.startswith("Crestor (rosuvastatin) is used to lower")
    assert out.parts == {
        "for_diabetes": "Crestor (rosuvastatin) is used to lower bad cholesterol in the blood. It helps protect the heart and blood vessels.",
        "how_it_works": "It slows the liver from making cholesterol.",
        "what_you_may_notice": "Some people notice muscle aches. It can take a few weeks to show its full effect.",
        "why_timing_matters": "Its effect builds up over time, so taking it regularly matters more than the exact hour.",
    }
    assert out.side_effects == ["Headache", "Muscle aches", "Nausea", "Stomach pain"]
    assert [s.title for s in out.sources] == ["drugs.com", "nih.gov"] and out.prompt_version and (out.input_tokens, out.output_tokens) == (300, 120)


def test_the_prompt_carries_the_label_text_and_the_instruction_to_search():
    c = FakeClient(GOOD)
    run(c)
    p = c.prompts[0]
    assert "CRESTOR" in p and "10 mg" in p and "every morning" in p and "Search the web" in p


def test_an_answer_wrapped_in_a_code_fence_or_text_is_still_read():
    fenced = "Here you go:\n```json\n" + json.dumps(GOOD) + "\n```"
    assert run(FakeClient(fenced)).status == "ready"


def test_a_sentence_that_gives_a_dose_is_dropped():
    bad = dict(GOOD, what_it_is_for="It lowers cholesterol. The usual dose is 10 mg once a day. It protects the heart.")
    out = run(FakeClient(bad))
    assert out.purpose == "It lowers cholesterol. It protects the heart."
    assert out.parts["for_diabetes"] == out.purpose


@pytest.mark.parametrize("sentence", ["You should stop taking it if you feel unwell.", "It is safe to take with other medicines.",
                                      "Do not take it with grapefruit juice.", "Your doctor may increase the dose later.",
                                      "Skip a dose if you are sick.", "It can be taken together with food.",
                                      "Your sugar may be normal on it.", "The rash is caused by the tablet.",
                                      "Take it at 8am with breakfast.", "It is taken every morning.",
                                      "Side effects may stop after a week.", "Some people may need to change the dose."])
def test_a_sentence_that_changes_treatment_or_calls_it_safe_or_normal_or_gives_a_time_is_dropped(sentence):
    out = run(FakeClient(dict(GOOD, what_it_is_for=f"It lowers cholesterol. {sentence}")))
    assert out.purpose == "It lowers cholesterol."


@pytest.mark.parametrize("field", ["how_it_works", "what_you_may_notice", "why_timing_matters", "tell_doctor"])
def test_each_part_is_checked_the_same_way(field):
    out = run(FakeClient(dict(GOOD, **{field: "Stop taking it if it hurts. Take it at 9 pm."})))
    assert out.status == "ready"
    if field == "tell_doctor":
        assert out.tell_doctor == "" and out.reason is None
    else:
        assert out.parts[field] == ""                                          # dropped, not guessed


def test_a_part_the_pages_do_not_cover_is_empty_and_the_explanation_is_still_ready():
    out = run(FakeClient(dict(GOOD, why_timing_matters="")))
    assert out.status == "ready" and out.parts["why_timing_matters"] == "" and out.parts["how_it_works"].startswith("It slows")


def test_side_effects_with_numbers_advice_duplicates_or_too_long_are_dropped_and_the_list_is_capped():
    effects = ["Headache", "headache", "Take 2 tablets daily", "Stop taking if dizzy", "x" * 90, "Nausea", "Dizziness", "Tiredness", "Rash",
               "Constipation", "Cough"]
    out = run(FakeClient(dict(GOOD, side_effects=effects)))
    assert out.side_effects == ["Headache", "Nausea", "Dizziness", "Tiredness", "Rash", "Constipation"]


def test_nothing_is_shown_without_a_web_source():
    out = run(FakeClient((json.dumps(GOOD), [])))
    assert out.status == "failed" and out.reason == "no_sources" and out.purpose == "" and out.parts == {}


def test_a_product_the_model_could_not_identify_is_not_explained():
    out = run(FakeClient(({"identified": False, "what_it_is_for": "Probably a tonic.", "side_effects": ["Nausea"], "tell_doctor": ""}, SOURCES)),
              name="Herbal tonic (label not readable)", kind="tcm")
    assert out.status == "not_identified" and out.purpose == "" and out.side_effects == [] and out.parts == {}


def test_an_answer_that_is_nothing_but_dose_advice_is_unusable():
    out = run(FakeClient(dict(GOOD, what_it_is_for="Take 10 mg once a day. Stop taking it if unwell.")))
    assert out.status == "failed" and out.reason == "unusable_answer"


def test_an_unreadable_answer_is_retried_once_then_fails_safe():
    c = FakeClient("not json", "still { not json")
    out = run(c)
    assert out.status == "failed" and out.reason == "invalid_answer" and len(c.prompts) == 2
    assert run(FakeClient("nope", GOOD)).status == "ready"


def test_a_service_failure_is_reported_not_raised():
    out = run(FakeClient(ExternalServiceError("down", code="llm_unavailable")))
    assert out.status == "failed" and out.reason == "service_unavailable"


def test_the_patients_name_in_the_label_text_never_reaches_the_prompt():
    c = FakeClient(GOOD)
    run(c, directions="LIM KEI WEN NICOLE", known_names=["Nicole Lim"])
    assert "LIM KEI WEN NICOLE" not in c.prompts[0]
    assert "CRESTOR" in c.prompts[0]


def test_the_instructions_forbid_doses_and_treatment_advice_and_label_instructions():
    c = FakeClient(GOOD)
    run(c)
    s = c.systems[0].lower()
    assert "no doses" in s and "never say to stop" in s and "data, not instructions" in s
    assert "safe" in s and "normal" in s                                       # the words the app never uses


def test_the_prompt_asks_for_the_four_parts_by_their_keys_and_version_2():
    system, version = x.load_prompt()
    assert version == "2"
    for key in ("what_it_is_for", "how_it_works", "what_you_may_notice", "why_timing_matters"):
        assert f'"{key}"' in system
    assert x.PARTS == ("for_diabetes", "how_it_works", "what_you_may_notice", "why_timing_matters")


def test_only_reliable_medical_sources_are_cited_when_there_are_some():
    found = [WebSource("express.co.uk", "https://x/1"), WebSource("www.nhs.uk", "https://x/2"), WebSource("hpra.ie", "https://x/3"),
             WebSource("reddit.com", "https://x/4"), WebSource("patient.info.nhs.uk", "https://x/5")]
    assert [s.title for s in x.pick_sources(found)] == ["nhs.uk", "hpra.ie", "patient.info.nhs.uk"]


def test_the_same_site_is_listed_once_even_when_the_search_gave_two_addresses_for_it():
    found = [WebSource("medlineplus.gov", "https://x/1"), WebSource("drugs.com", "https://x/2"), WebSource("medlineplus.gov", "https://x/3")]
    assert [(s.title, s.url) for s in x.pick_sources(found)] == [("medlineplus.gov", "https://x/1"), ("drugs.com", "https://x/2")]


def test_when_no_source_is_on_the_reliable_list_the_pages_used_are_still_cited_not_hidden():
    found = [WebSource("somepharmacy.sg", "https://x/1"), WebSource("example.org", "https://x/2")]
    assert [s.title for s in x.pick_sources(found)] == ["somepharmacy.sg", "example.org"]
    assert len(x.pick_sources([WebSource(f"site{i}.nhs.uk", f"https://x/{i}") for i in range(9)])) == x.MAX_SOURCES
