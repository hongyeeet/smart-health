"""The language of a request: units, dates, labels and stored reminders follow the language the person chose (X-Lang)."""
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.services import care, dose_store, texts, ui_translate


@pytest.fixture(autouse=True)
def _english_after():
    yield
    texts.set_request_language(None)
    ui_translate._CACHE.clear()


def test_the_request_language_is_english_by_default_and_ignores_unknown_codes():
    assert texts.request_lang() == "en"
    texts.set_request_language("fr")
    assert texts.request_lang() == "en"
    texts.set_request_language("zh")
    assert texts.request_lang() == "zh"


def test_dose_wording_follows_the_language():
    assert dose_store.dose_title("Metformin 500 mg", "500 mg", "prescription", None, Decimal(1)) == "Metformin, 1 Tab"
    assert dose_store.dose_title("Metformin 500 mg", "500 mg", "prescription", None, Decimal(2)) == "Metformin, 2 Tabs"
    texts.set_request_language("zh")
    assert dose_store.dose_title("Metformin 500 mg", "500 mg", "prescription", None, Decimal(1)) == "Metformin, 1 片"
    now = datetime(2026, 10, 13, 6, 0, tzinfo=timezone.utc)
    when = dose_store.when_phrase(datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc), now)
    assert "下午" in when and when.startswith("今天")


def test_care_wording_follows_the_language_and_english_is_unchanged():
    assert care.preventive_detail("overdue", date(2024, 9, 2), date(2025, 9, 2)) == "Last done 2 Sep 2024. Was due 2 Sep 2025."
    assert care.preventive_detail("unknown", None, None) == "No date on record yet."
    texts.set_request_language("zh")
    assert "2024年9月2日" in care.preventive_detail("overdue", date(2024, 9, 2), date(2025, 9, 2))
    row = {"id": 1, "text": "x", "origin": "user", "status": "open", "created_at": None}
    assert care.question_out(row)["origin_label"] == texts.tr("zh", "care.origin.user") != "Added by you"


def test_visit_dates_use_the_languages_own_names():
    when = datetime(2026, 10, 11, 2, 0, tzinfo=timezone.utc)          # Sunday 11 Oct, 10:00 in Singapore
    assert care.scheduled_label(when) == "Sun 11 Oct, 10:00 am"
    texts.set_request_language("ms")
    assert care.scheduled_label(when) == "Ahd 11 Okt, 10:00 pagi"


def test_a_reminder_stored_in_english_is_shown_in_the_chosen_language():
    assert texts.retranslate("zh", "Log your lunch") == "记录你的午餐"
    assert texts.retranslate("en", "Log your lunch") == "Log your lunch"
    assert texts.retranslate("zh", "A sentence that is not in the catalog.") == "A sentence that is not in the catalog."
    assert texts.retranslate("ms", "Time for your Metformin") == texts.tr("ms", "dose.title", name="Metformin")


def test_translation_of_model_text_keeps_numbers_and_falls_back_to_english(monkeypatch):
    class Out:
        def __init__(self, items):
            self.items = items

    calls = []

    def fake(system, prompt, schema, model=None):
        calls.append(prompt)
        return Out(["第一句 20 mg", "第二句 995"])

    monkeypatch.setattr(ui_translate.gateway, "text_json", fake)
    got = ui_translate.translate("zh", ["First sentence 20 mg", "Second sentence 995"])
    assert got == ["第一句 20 mg", "第二句 995"]
    ui_translate.translate("zh", ["First sentence 20 mg"])                      # kept: no second model call
    assert len(calls) == 1
    monkeypatch.setattr(ui_translate.gateway, "text_json", lambda *a, **k: Out(["丢了数字"]))
    assert ui_translate.translate("zh", ["Take 30 mg"]) == ["Take 30 mg"]          # a number went missing: English is kept
    monkeypatch.setattr(ui_translate.gateway, "text_json", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    assert ui_translate.translate("ta", ["Hello there friend"]) == ["Hello there friend"]
    assert ui_translate.translate("en", ["Hello"]) == ["Hello"]
