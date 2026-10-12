"""The signpost sentences carry [[ROUTE|words]] markers that the app shows as links inside the reply."""
import re

from app.services import texts

SIGNS = ["chat.sign_insights", "chat.sign_food", "chat.sign_meds", "chat.sign_care"]
MARK = re.compile(r"\[\[([A-Z][A-Z0-9]*)\|([^\]]+)\]\]")


def test_every_language_marks_the_same_screens_in_the_same_order():
    for key in SIGNS:
        routes = {lang: [m.group(1) for m in MARK.finditer(texts.tr(lang, key))] for lang in texts.LANGS}
        assert routes["en"], key
        assert all(r == routes["en"] for r in routes.values()), (key, routes)


def test_the_marked_screens_are_the_ones_the_signposts_open():
    from app.services import chat_guard as G
    opened = {"chat.sign_food": {"K11", "E8"}, "chat.sign_insights": {"C1"}, "chat.sign_meds": {"H1"}, "chat.sign_care": {"K3"}}
    for key, want in opened.items():
        assert {m.group(1) for m in MARK.finditer(texts.tr("en", key))} == want
    assert {p.to for p in G.signposts("diet", True, True)} <= {"K11", "E8", "C1"}


def test_strip_links_leaves_only_the_words():
    assert texts.strip_links(texts.tr("en", "chat.sign_food")) == "You can find more ideas under Me, Review suggestions, and in Lunch ideas."
    assert "[[" not in texts.strip_links(texts.tr("zh", "chat.sign_meds"))
    assert texts.strip_links("no markers here") == "no markers here"


def test_the_doctor_question_offer_is_one_whole_link_in_every_language():
    for lang in texts.LANGS:
        sentence = texts.tr(lang, "chat.offer_question")
        m = MARK.fullmatch(sentence)
        assert m and m.group(1) == "DQ", (lang, sentence)
        assert texts.strip_links(sentence) == m.group(2)
