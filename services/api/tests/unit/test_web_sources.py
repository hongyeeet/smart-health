"""The shape of the web sources shown with a medicine explanation or a clash alert (app/services/web_sources.py).

Run from services/api:  python -m pytest tests/unit/test_web_sources.py -q
"""
from app.agents import med_explainer as x
from app.llm.vertex import WebSource
from app.services.web_sources import OPENFDA_TITLE, clean

REDIRECT = "https://vertexaisearch.cloud.google.com/grounding-api-redirect/abc"


def test_a_grounded_redirect_keeps_its_link_and_is_named_by_the_site():
    assert clean([{"title": "www.nhs.uk", "url": REDIRECT}]) == [{"title": "nhs.uk", "url": REDIRECT}]


def test_a_real_page_keeps_its_link_and_a_page_title_is_replaced_by_the_site_name():
    assert clean([{"title": "Crestor uses and side effects", "url": "https://www.drugs.com/crestor.html"}]) == [
        {"title": "drugs.com", "url": "https://www.drugs.com/crestor.html"}]


def test_openfda_has_no_link_under_its_plain_name_old_and_new():
    old = {"title": "Drug label information (openFDA)", "url": "https://api.fda.gov/drug/label.json?search=x"}
    new = {"title": OPENFDA_TITLE, "url": ""}
    assert clean([old]) == [{"title": OPENFDA_TITLE, "url": ""}] == clean([new])


def test_each_site_is_shown_once_even_with_two_addresses():
    out = clean([{"title": "drugs.com", "url": REDIRECT + "1"}, {"title": "www.drugs.com", "url": REDIRECT + "2"}, {"title": "nhs.uk", "url": REDIRECT + "3"}])
    assert [s["title"] for s in out] == ["drugs.com", "nhs.uk"] and out[0]["url"] == REDIRECT + "1"


def test_a_source_without_a_web_address_has_no_link():
    assert clean([{"title": "someone.org", "url": "javascript:alert(1)"}]) == [{"title": "someone.org", "url": ""}]


def test_the_explainer_picks_site_names_for_its_sources():
    found = [WebSource("www.medlineplus.gov", REDIRECT + "1"), WebSource("Medlineplus.gov page", REDIRECT + "2")]
    assert [(s.title, s.url) for s in x.pick_sources(found)] == [("medlineplus.gov", REDIRECT + "1")]


def test_a_null_part_in_the_answer_is_an_empty_part_not_an_unreadable_answer():
    raw = x.parse_answer('{"identified": true, "what_it_is_for": "Lowers cholesterol.", "how_it_works": null, '
                         '"what_you_may_notice": "", "why_timing_matters": null, "side_effects": null, "tell_doctor": null}')
    assert raw.identified is True and raw.how_it_works == "" and raw.side_effects == [] and raw.tell_doctor == ""
    assert x.parse_answer('{"identified": null}').identified is False
