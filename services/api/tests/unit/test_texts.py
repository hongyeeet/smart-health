"""The fixed wording in four languages (app/services/texts.py).

English is the source: its output must stay exactly what the app said before, so these tests keep the old literal texts.
"""
import string
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.services import texts as T

TZ = ZoneInfo("Asia/Singapore")


def _fields(text):
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


# ---------------------------------------------------------------------- the catalogue itself
@pytest.mark.parametrize("key", sorted(T.CATALOG))
def test_every_key_has_all_four_languages_and_no_empty_text(key):
    entry = T.CATALOG[key]
    assert set(entry) == set(T.LANGS), key
    for lang, text in entry.items():
        assert text.strip(), (key, lang)


@pytest.mark.parametrize("key", sorted(T.CATALOG))
def test_every_language_uses_the_same_placeholders_as_english(key):
    entry = T.CATALOG[key]
    for lang in T.LANGS:
        assert _fields(entry[lang]) == _fields(entry["en"]), (key, lang)


def test_langs_and_names():
    assert T.LANGS == ("en", "zh", "ms", "ta")
    assert set(T.LANG_NAMES) == set(T.LANGS)


# ---------------------------------------------------------------------- tr(): lookup and fallbacks
def test_a_translation_is_returned_for_its_language():
    assert T.tr("zh", "nudge.checkin.title") == "你昨晚睡得怎么样？"
    assert T.tr("ta", "nudge.checkin.title") != T.tr("en", "nudge.checkin.title")


def test_an_unknown_language_falls_back_to_english():
    assert T.tr("fr", "nudge.checkin.title") == "How did you sleep?"
    assert T.tr(None, "nudge.checkin.title") == "How did you sleep?"
    assert T.tr("", "nudge.checkin.title") == "How did you sleep?"


def test_a_missing_placeholder_in_a_translation_falls_back_to_english():
    key = "test.placeholder.fallback"
    T.CATALOG[key] = {"en": "Hello {name}, you have {n} doses.", "zh": "你好，你有 {n} 次。", "ms": "Hai {name}, {n} dos.", "ta": "வணக்கம் {name}, {n}."}
    try:
        # zh is missing {name}: English is used, filled with the same variables
        assert T.tr("zh", key, name="Mr Tan", n=3) == "Hello Mr Tan, you have 3 doses."
        # ms and ta have all placeholders: their own text
        assert T.tr("ms", key, name="Mr Tan", n=3) == "Hai Mr Tan, 3 dos."
    finally:
        del T.CATALOG[key]


def test_a_translation_with_an_extra_placeholder_falls_back_to_english_too():
    key = "test.extra.placeholder"
    T.CATALOG[key] = {"en": "Hi {name}.", "zh": "你好 {name} {extra}。", "ms": "Hai {name}.", "ta": "வணக்கம் {name}."}
    try:
        assert T.tr("zh", key, name="Mei") == "Hi Mei."
    finally:
        del T.CATALOG[key]


def test_a_missing_key_returns_the_key_and_never_raises():
    assert T.tr("zh", "no.such.key") == "no.such.key"


def test_label_returns_the_word_or_the_value_when_there_is_no_key():
    assert T.label("zh", "period", "morning") == "早上"
    assert T.label("en", "period", "morning") == "morning"
    assert T.label("zh", "period", "unknown-part") == "unknown-part"


# ---------------------------------------------------------------------- English is byte-for-byte the old wording
OLD_ENGLISH = [
    # in-app reminders (logstore.notifications)
    ("nudge.meal.title", {"meal": "breakfast"}, "Log your breakfast"),
    ("nudge.meal.body", {}, "Take a photo and tell us when you finish eating. It lands on your timeline."),
    ("nudge.checkin.title", {}, "How did you sleep?"),
    ("nudge.checkin.body", {}, "A thirty-second mood and sleep check-in."),
    ("nudge.workout.body", {"done": 40, "goal": 150}, "40 of 150 active minutes this week. A walk counts."),
    ("refill.title", {"name": "Metformin"}, "Time to refill Metformin"),
    ("refill.low", {}, "Your supply is running low. Ask your pharmacy or clinic for a refill."),
    # nutrition
    ("lunch.body", {"names": "Chicken rice, Laksa"}, "Ideas that suit you: Chicken rice, Laksa."),
    ("salt.title.walk", {}, "A short walk after that meal?"),
    ("salt.title.no_walk", {}, "A salty meal today"),
    ("salt.body", {"mg": "1,230"}, "That meal was high in salt (about 1,230 mg)."),
    ("salt.walk", {}, " For now, an easy 10-minute walk is a good habit after meals. If you are unsure, check with your doctor."),
    ("saving.saves", {"items": "230 kcal and 600 mg salt"}, "saves about 230 kcal and 600 mg salt"),
    ("saving.protein", {"a": 31, "b": 22}, "; protein goes from 31 g to 22 g"),
    ("outcome.since", {"dish": "Fried rice", "n": 1, "times": "time"}, "Since then you have had Fried rice 1 time."),
    ("outcome.rise.lower", {}, "lower, associated with the swap, not proven."),
    ("habit.reflect", {"label": "rice dishes", "n": 4, "kcal": "610", "dish": "Chicken rice"},
     "Often eats rice dishes: 4 meals in the last 2 weeks, about 610 kcal each. The heaviest is Chicken rice."),
    # dose timing
    ("dose.title", {"name": "Metformin"}, "Time for your Metformin"),
    ("dose.renudge_title", {"name": "Metformin"}, "Still time for your Metformin"),
    ("dose.meal.before_meal", {}, "Take it before a meal."),
    ("dose.fact.period", {"period": "evening", "name": "Amlodipine", "usual": 20, "offset": 30},
     "You usually take your evening Amlodipine about 20 minutes after the set time. We remind you 30 minutes after it."),
    ("dose.fact.plain", {"name": "Amlodipine", "usual": 20, "offset": 30},
     "You usually take your Amlodipine about 20 minutes after the set time. We remind you 30 minutes after it."),
    ("dose.anchor.body", {"meal": "Breakfast", "part": "morning", "name": "Metformin"}, "Breakfast logged. Time for your morning Metformin?"),
    ("dose.anchor.title", {"part": "morning"}, "Your morning dose"),
    # barrier actions and preventive
    ("action.forgot.most", {"n": 5}, "Forgot is your most common reason (5 times in 4 weeks)."),
    ("action.forgot.tail", {}, " Link your reminder to something you already do, such as breakfast?"),
    ("action.ran_out", {"n": 2, "days": 7}, "You ran out 2 times. Get a refill reminder 7 days before you run out?"),
    ("action.away", {"n": 3}, "You missed 3 doses when you were away. Keep a note on your phone for those days?"),
    ("preventive.overdue", {"name": "eye screening", "day": "2 Sep 2025"}, "Your eye screening was due on 2 Sep 2025. Plan one?"),
    ("preventive.due", {"name": "HbA1c blood test"}, "Your HbA1c blood test is due. You can add a visit in Track appointments."),
    ("check.gp_review", {}, "GP review"),
    ("glucose.swap.same", {"dish": "Laksa", "kind": "noodle dishes", "nb": 5, "na": 6},
     "After you switched to Laksa, your glucose rise after noodle dishes was about the same (based on 5 meals before and 6 after). This is an observation from your data, not proof."),
    ("glucose.walk.changed", {"diff": "0.7", "dir": "lower", "n": 9},
     "On mornings after an evening walk, your fasting glucose was 0.7 mmol/L lower (based on 9 evenings). This is an observation from your data, not proof."),
    ("question.added.body", {"text": "I noticed side effects after taking Amlodipine. I would like to talk about this at my next visit."},
     "We added this to your questions for your doctor: I noticed side effects after taking Amlodipine. I would like to talk about this at my next visit."),
    # reminder emails
    ("email.subject.urgent", {"name": "Mei"}, "Please check on Mei: possible low glucose"),
    ("email.subject.meal", {"title": "Log your lunch"}, "Log your lunch? One photo is all it takes"),
    ("email.subject.checkin", {}, "How did you sleep? It takes thirty seconds"),
    ("email.subject.workout", {}, "A short walk counts today"),
    ("email.subject.lunch", {}, "Lunch ideas picked for you"),
    ("email.subject.default", {}, "A reminder from Smart Health"),
    ("email.greeting.named", {"name": "Mr Tan"}, "Hi Mr Tan,"),
    ("email.greeting.plain", {}, "Hi,"),
    ("email.button.E2", {}, "Log my meal"),
    ("email.button.default", {}, "Open Smart Health"),
    ("email.foot.contact", {}, "You are getting this because someone added you as their emergency contact in Smart Health."),
    ("email.unsubscribe.line", {"url": "https://x.test/u?t=1"}, "Unsubscribe: https://x.test/u?t=1"),
    # urgent alert and the contact's email
    ("urgent.title.very_low", {}, "Very low glucose"),
    ("urgent.demo_prefix", {}, "Demo: "),
    ("urgent.alert_body", {"value": "2.9"}, "Your glucose looks low: 2.9 mmol/L."),
    ("urgent.contact.unnamed", {}, "A person who listed you as their emergency contact"),
    ("urgent.contact.body", {"who": "Mr Tan", "value": "3.4", "clock": "14:05", "number": "995"},
     "Mr Tan may have low glucose (3.4 mmol/L at 14:05). Please check on them. If they cannot answer, call 995."),
    ("urgent.demo.title", {"title": "Possible low glucose: Mr Tan"}, "DEMO. Possible low glucose: Mr Tan"),
    # chat fixed replies
    ("chat.urgent", {}, "This sounds urgent. Call 995 now, or ask someone near you to call."),
    ("chat.refused", {}, "I cannot advise on medicines or diagnose. This is worth asking your doctor."),
    ("chat.caution", {}, "I am not able to answer that here. If you feel unwell, call 995 or contact your doctor."),
    ("chat.unavailable", {}, "I cannot answer right now. Please try again in a little while. If it is urgent, call 995."),
    ("chat.guard_down", {}, "I cannot check this question right now, so I will not answer it. Please try again in a little while. If it is urgent, call 995."),
    ("chat.blocked_reply", {}, "I am not able to share that answer. Please ask your doctor or pharmacist."),
    ("chat.empty", {}, "I do not have that in your data yet. Once you log meals, doses or glucose, I can answer questions about them."),
    ("chat.help", {}, "I can answer questions about your own data: your glucose, meals, activity, sleep, medicines and doctor questions. "
                      "I cannot give medical advice or diagnose. For emergencies call 995."),
]


@pytest.mark.parametrize("key,vars_,expected", OLD_ENGLISH, ids=[k for k, _, _ in OLD_ENGLISH])
def test_english_is_the_wording_the_app_used_before(key, vars_, expected):
    assert T.tr("en", key, **vars_) == expected


def test_english_is_used_when_no_language_is_given():
    assert T.tr(None, "chat.urgent") == T.tr("en", "chat.urgent")


def test_chinese_malay_and_tamil_are_really_different_from_english():
    for key in ("nudge.checkin.title", "chat.urgent", "urgent.alert_body", "email.button.E2", "dose.title"):
        en = T.tr("en", key, name="X", value="1.0")
        for lang in ("zh", "ms", "ta"):
            assert T.tr(lang, key, name="X", value="1.0") != en, (key, lang)


def test_safety_texts_keep_the_emergency_number():
    for key in ("chat.urgent", "chat.caution", "chat.unavailable", "chat.guard_down", "chat.help", "urgent.contact.body"):
        for lang in T.LANGS:
            text = T.tr(lang, key, who="X", value="1.0", clock="10:00", number="995")
            assert "995" in text, (key, lang)


# ---------------------------------------------------------------------- person_language
class FakeCursor:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConn:
    def __init__(self, row=None, error=None):
        self.row, self.error, self.calls = row, error, 0

    def execute(self, sql, params=None):
        self.calls += 1
        if self.error:
            raise self.error
        return FakeCursor(self.row)


def test_person_language_is_english_with_no_profile_row():
    assert T.person_language(uuid.uuid4(), conn=FakeConn(row=None)) == "en"


def test_person_language_reads_the_profile_language():
    assert T.person_language(uuid.uuid4(), conn=FakeConn(row={"l": "zh"})) == "zh"
    assert T.person_language(uuid.uuid4(), conn=FakeConn(row={"l": "ta"})) == "ta"


def test_person_language_ignores_a_language_it_does_not_know():
    assert T.person_language(uuid.uuid4(), conn=FakeConn(row={"l": "fr"})) == "en"


def test_person_language_never_fails():
    assert T.person_language(uuid.uuid4(), conn=FakeConn(error=RuntimeError("db down"))) == "en"
    assert T.person_language(None) == "en"
    assert T.person_language("not-a-uuid") == "en"          # a test name is English, with no database call


def test_person_language_with_a_non_uuid_does_not_touch_the_database():
    conn = FakeConn(row={"l": "zh"})
    assert T.person_language("u1", conn=conn) == "en"
    assert conn.calls == 0


# ---------------------------------------------------------------------- the pure builders keep their English output
def test_dose_helpers_default_to_english():
    from app.agents import dose_timing as D

    assert D.reminder_title("Metformin") == "Time for your Metformin"
    assert D.reminder_body(None, "before_meal") == "Take it before a meal."
    assert D.reminder_body("Take 1 tab every morning", "before_meal") == "Take 1 tab every morning"   # the label's own text is never translated
    assert D.fact_text("Amlodipine", "", 20, 30).startswith("You usually take your Amlodipine about 20 minutes")
    assert D.reminder_title("Metformin", "zh") == "该服用Metformin了"


def test_barrier_and_preventive_helpers_default_to_english():
    from app.agents import barrier_actions as B
    from app.agents import preventive as P

    assert B.action_text("forgot", 5, True).startswith("Forgot is your most common reason (5 times in 4 weeks).")
    assert B.action_text("ran_out", 2, False) == "You ran out 2 times. Get a refill reminder 7 days before you run out?"
    assert B.meal_label("breakfast") == "Breakfast" and B.meal_label("supper") == "Meal"
    assert P.overdue_statement("gp_review", date(2025, 9, 2)) == "Your GP review was due on 2 Sep 2025. Plan one?"
    assert P.nudge_text("gp_review", "zh") == "你的家庭医生检查到期了。你可以在“预约追踪”中添加就诊。"


def test_glucose_observations_keep_the_english_text_for_the_guard():
    from app.agents import glucose_feedback as G

    before, after = [5.0] * 5, [5.0 + 0.8] * 5
    o = G.swap_observation("Laksa", "noodle dishes", before, after, "zh")
    assert o["text_en"].startswith("After you switched to Laksa, your glucose rose 0.8 mmol/L more")
    assert o["text"] != o["text_en"] and "Laksa" in o["text"]
    w = G.walk_observation(-0.7, 9)
    assert w["text"] == w["text_en"]


def test_saving_phrase_and_habit_text_default_to_english():
    from app.db import nutritionstore as N

    alt = {"changes": [{"nutrient": "kcal", "change": -230, "from": 600, "to": 370}, {"nutrient": "sodium_mg", "change": -600, "from": 1500, "to": 900}]}
    assert N.saving_phrase(alt) == "saves about 230 kcal and 600 mg salt"
    assert N.saving_phrase(alt, "zh") == "大约可节省230 千卡和600 毫克盐"
    h = {"type": "rice_dish", "label": "rice dishes", "n": 3, "avg": {"kcal": 610, "sodium_mg": 1200}, "alternatives": [], "topDish": "Chicken rice",
         "topDishN": 2, "topAvg": {"kcal": 640}}
    assert N.habit_text(h) == "You have had rice dishes 3 times in the last 2 weeks, about 610 kcal and 1,200 mg salt each (from your logged meals)."
    assert N.habit_text(h, "zh").startswith("过去 2 周你吃过饭类 3 次")


def test_chat_kind_of_knows_the_fixed_replies_in_every_language():
    from app.services import chat as C

    assert C.KIND_OF[C.URGENT_TEXT] == "urgent"
    for lang in T.LANGS:
        assert C.KIND_OF[T.tr(lang, "chat.urgent")] == "urgent"
        assert C.KIND_OF[T.tr(lang, "chat.empty")] == "empty"


def test_the_model_prompt_is_unchanged_for_english_and_asks_for_the_language_otherwise():
    from app.services import chat as C

    assert C.system_for("en") == C.SYSTEM
    assert C.system_for("zh") .startswith(C.SYSTEM) and "Simplified Chinese" in C.system_for("zh")
    assert C.system_for("xx") == C.SYSTEM


# ---------------------------------------------------------------------- reminder emails follow the recipient's language
def _mail_row(**kw):
    from app.services import notify_email as N

    base = dict(id="n1", user_id="u1", kind="nudge", scheduled_for=datetime(2026, 10, 10, 12, 0, tzinfo=TZ), acted_at=None,
                payload={"key": "meal-2-2026-10-10", "title": "Log your lunch", "body": "Take a photo.", "to": "E2"},
                attempts=0, delivery_to="person", name="Mr Tan", email="tan@gmail.com", opt_in=True, contact_name="Mei",
                contact_email="mei@gmail.com", language="en")
    base.update(kw)
    return N.Row(**base)


def test_the_reminder_email_is_in_the_recipients_language():
    from app.services import notify_email as N

    en = N.build_message(_mail_row())
    assert en["subject"] == "Log your lunch? One photo is all it takes"
    assert en["text"].startswith("Hi Mr Tan,")
    assert "Log my meal:" in en["text"]

    zh = N.build_message(_mail_row(language="zh"))
    assert zh["subject"] == "Log your lunch？拍一张照片就够了"
    assert zh["text"].startswith("Mr Tan，你好，")
    assert "记录我的餐食:" in zh["text"]
    assert "Take a photo." in zh["text"]          # the body is the stored text, as before
    assert zh["to"] == "tan@gmail.com" and zh["idempotencyKey"] == "n1"


def test_the_contact_email_uses_the_persons_language():
    from app.services import notify_email as N

    contact = N.build_message(_mail_row(kind="urgent", delivery_to="contact", language="ms",
                                        payload={"key": "urgent-x-contact", "title": "T", "body": "B", "to": "J1"}))
    assert contact["to"] == "mei@gmail.com"
    assert contact["text"].startswith("Hai,")
    assert contact["subject"] == "Tolong periksa Mei: mungkin gula darah rendah"
    assert "Buka Smart Health:" in contact["text"]


def test_an_unknown_recipient_language_is_english():
    from app.services import notify_email as N

    m = N.build_message(_mail_row(language="fr"))
    assert m["text"].startswith("Hi Mr Tan,")
