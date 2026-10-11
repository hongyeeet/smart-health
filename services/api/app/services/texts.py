"""Fixed wording in the person's language: notifications, reminder emails, the urgent alert and the chat's fixed replies.

English is the source of truth. Every text is one key with one entry per language, and the English entry is the exact wording the app
used before this module existed (tests check it byte for byte). A missing key, language or placeholder falls back to English, never an error.

Safety: the output guard (nutritionstore.guarded, the JEV guard) always runs on the ENGLISH text. The translation is a fixed mapping of
that exact English text, filled with the same variables, so a checked English text can only become its own translation. Model replies
are not in this file: the model answers in the person's language and the guard runs on that reply as it always did.

Never translated: numbers, units, dates' meaning, medicine names, dish names, the emergency number 995, and any text from the database or
the model (a note the person typed, a label from a medicine box). Those come in as variables, unchanged.

Translations for zh, ms and ta are machine translations. They are listed in docs/review/translations.md for a native and clinical review.
"""
from __future__ import annotations

import logging
import string
import uuid
from typing import Any

logger = logging.getLogger(__name__)

LANGS = ("en", "zh", "ms", "ta")
DEFAULT_LANG = "en"
LANG_NAMES = {"en": "English", "zh": "Simplified Chinese", "ms": "Malay", "ta": "Tamil"}

CATALOG: dict[str, dict[str, str]] = {
    # ------------------------------------------------------------------ in-app reminders (logstore.notifications)
    "nudge.meal.title": {"en": "Log your {meal}", "zh": "记录你的{meal}", "ms": "Catat {meal} anda", "ta": "உங்கள் {meal} பதிவு செய்யுங்கள்"},
    "meal.word.breakfast": {"en": "breakfast", "zh": "早餐", "ms": "sarapan", "ta": "காலை உணவு"},
    "meal.word.lunch": {"en": "lunch", "zh": "午餐", "ms": "makan tengah hari", "ta": "மதிய உணவு"},
    "meal.word.dinner": {"en": "dinner", "zh": "晚餐", "ms": "makan malam", "ta": "இரவு உணவு"},
    "meal.label.breakfast": {"en": "Breakfast", "zh": "早餐", "ms": "Sarapan", "ta": "காலை உணவு"},
    "meal.label.lunch": {"en": "Lunch", "zh": "午餐", "ms": "Makan tengah hari", "ta": "மதிய உணவு"},
    "meal.label.dinner": {"en": "Dinner", "zh": "晚餐", "ms": "Makan malam", "ta": "இரவு உணவு"},
    "meal.label.other": {"en": "Meal", "zh": "这餐", "ms": "Makanan", "ta": "உணவு"},
    "nudge.meal.body": {
        "en": "Take a photo and tell us when you finish eating. It lands on your timeline.",
        "zh": "拍一张照片，吃完后告诉我们。它会出现在你的时间线上。",
        "ms": "Ambil gambar dan beritahu kami bila anda habis makan. Ia akan masuk ke garis masa anda.",
        "ta": "ஒரு படம் எடுத்து, சாப்பிட்டு முடித்ததும் எங்களுக்குச் சொல்லுங்கள். அது உங்கள் காலவரிசையில் சேரும்.",
    },
    "nudge.checkin.title": {"en": "How did you sleep?", "zh": "你昨晚睡得怎么样？", "ms": "Bagaimana tidur anda?", "ta": "நீங்கள் எப்படித் தூங்கினீர்கள்?"},
    "nudge.checkin.body": {
        "en": "A thirty-second mood and sleep check-in.", "zh": "30 秒的心情和睡眠记录。",
        "ms": "Semakan mood dan tidur selama 30 saat.", "ta": "30 வினாடி மனநிலை மற்றும் தூக்கப் பதிவு.",
    },
    "nudge.workout.title": {"en": "Any movement today?", "zh": "今天有活动吗？", "ms": "Ada bergerak hari ini?", "ta": "இன்று ஏதேனும் நடமாடினீர்களா?"},
    "nudge.workout.body": {
        "en": "{done} of {goal} active minutes this week. A walk counts.", "zh": "本周已完成 {done}/{goal} 分钟活动。散步也算。",
        "ms": "{done} daripada {goal} minit aktif minggu ini. Berjalan kaki pun kira.", "ta": "இந்த வாரம் {done} / {goal} சுறுசுறுப்பு நிமிடங்கள். நடப்பதும் கணக்கில் வரும்.",
    },
    "refill.title": {"en": "Time to refill {name}", "zh": "该续领{name}了", "ms": "Masa untuk isi semula {name}", "ta": "{name} மருந்தை மீண்டும் வாங்க வேண்டிய நேரம்"},
    "refill.low": {
        "en": "Your supply is running low. Ask your pharmacy or clinic for a refill.", "zh": "你的药快用完了。请向药房或诊所申请续领。",
        "ms": "Bekalan anda hampir habis. Minta isi semula daripada farmasi atau klinik anda.",
        "ta": "உங்கள் மருந்து குறைந்து வருகிறது. உங்கள் மருந்தகம் அல்லது கிளினிக்கில் மீண்டும் வாங்கக் கேளுங்கள்.",
    },
    "refill.used_up": {
        "en": "Your supply may already be used up. Ask your pharmacy or clinic for a refill.", "zh": "你的药可能已经用完了。请向药房或诊所申请续领。",
        "ms": "Bekalan anda mungkin sudah habis. Minta isi semula daripada farmasi atau klinik anda.",
        "ta": "உங்கள் மருந்து ஏற்கனவே தீர்ந்திருக்கலாம். உங்கள் மருந்தகம் அல்லது கிளினிக்கில் மீண்டும் வாங்கக் கேளுங்கள்.",
    },
    "refill.days": {
        "en": "About {days} days of {name} left at your usual dose times. Ask your pharmacy or clinic for a refill.",
        "zh": "按你平时的服药时间，{name}约剩 {days} 天。请向药房或诊所申请续领。",
        "ms": "Kira-kira {days} hari {name} tinggal pada waktu dos biasa anda. Minta isi semula daripada farmasi atau klinik anda.",
        "ta": "உங்கள் வழக்கமான மருந்து நேரங்களின்படி {name} சுமார் {days} நாட்களுக்கு உள்ளது. உங்கள் மருந்தகம் அல்லது கிளினிக்கில் மீண்டும் வாங்கக் கேளுங்கள்.",
    },
    "question.added.title": {
        "en": "A question for your doctor was added", "zh": "已为你添加一个给医生的问题",
        "ms": "Satu soalan untuk doktor anda telah ditambah", "ta": "உங்கள் மருத்துவருக்கான ஒரு கேள்வி சேர்க்கப்பட்டது",
    },
    "question.added.body": {
        "en": "We added this to your questions for your doctor: {text}", "zh": "我们已将此项加入你给医生的问题：{text}",
        "ms": "Kami telah menambahkan ini pada soalan anda untuk doktor: {text}", "ta": "இதை உங்கள் மருத்துவருக்கான கேள்விகளில் சேர்த்துள்ளோம்: {text}",
    },
    "lunch.title": {"en": "Lunch ideas for you", "zh": "为你推荐的午餐", "ms": "Idea makan tengah hari untuk anda", "ta": "உங்களுக்கான மதிய உணவு யோசனைகள்"},
    "lunch.body": {
        "en": "Ideas that suit you: {names}.", "zh": "适合你的选择：{names}。", "ms": "Idea yang sesuai untuk anda: {names}.", "ta": "உங்களுக்கு ஏற்ற யோசனைகள்: {names}.",
    },
    "salt.title.walk": {
        "en": "A short walk after that meal?", "zh": "餐后散步一小会儿？", "ms": "Berjalan kaki sebentar selepas makan itu?", "ta": "அந்த உணவுக்குப் பிறகு சிறிது நடக்கலாமா?",
    },
    "salt.title.no_walk": {"en": "A salty meal today", "zh": "今天有一餐偏咸", "ms": "Makanan masin hari ini", "ta": "இன்று ஒரு உப்பான உணவு"},
    "salt.body": {
        "en": "That meal was high in salt (about {mg} mg).", "zh": "那一餐盐分偏高（约 {mg} 毫克）。",
        "ms": "Makanan itu tinggi garam (kira-kira {mg} mg).", "ta": "அந்த உணவில் உப்பு அதிகம் (சுமார் {mg} மி.கி).",
    },
    "salt.swap": {
        "en": " Next time, try {name}: it {saving}.", "zh": " 下次可以试试{name}：它{saving}。",
        "ms": " Lain kali, cuba {name}: ia {saving}.", "ta": " அடுத்த முறை {name} முயற்சி செய்யுங்கள்: அது {saving}.",
    },
    "salt.walk": {
        "en": " For now, an easy 10-minute walk is a good habit after meals. If you are unsure, check with your doctor.",
        "zh": " 现在，饭后轻松散步 10 分钟是个好习惯。如果不确定，请问你的医生。",
        "ms": " Buat masa ini, berjalan kaki mudah selama 10 minit selepas makan ialah tabiat yang baik. Jika tidak pasti, tanya doktor anda.",
        "ta": " இப்போதைக்கு, உணவுக்குப் பிறகு 10 நிமிட எளிய நடை நல்ல பழக்கம். உறுதியில்லை என்றால், உங்கள் மருத்துவரிடம் கேளுங்கள்.",
    },
    # ------------------------------------------------------------------ food nudges and habits (nutritionstore)
    "saving.saves": {"en": "saves about {items}", "zh": "大约可节省{items}", "ms": "menjimatkan kira-kira {items}", "ta": "சுமார் {items} மிச்சமாகும்"},
    "saving.lighter": {"en": "is lighter", "zh": "更清淡", "ms": "lebih ringan", "ta": "இலகுவானது"},
    "saving.protein": {
        "en": "; protein goes from {a} g to {b} g", "zh": "；蛋白质从 {a} 克变为 {b} 克",
        "ms": "; protein daripada {a} g kepada {b} g", "ta": "; புரதம் {a} கி முதல் {b} கி வரை",
    },
    "unit.kcal": {"en": "{n} kcal", "zh": "{n} 千卡", "ms": "{n} kcal", "ta": "{n} kcal"},
    "unit.salt": {"en": "{n} mg salt", "zh": "{n} 毫克盐", "ms": "{n} mg garam", "ta": "{n} மி.கி உப்பு"},
    "unit.carbs": {"en": "{n} g carbs", "zh": "{n} 克碳水", "ms": "{n} g karbohidrat", "ta": "{n} கி கார்போஹைட்ரேட்"},
    "unit.sugar": {"en": "{n} g sugar", "zh": "{n} 克糖", "ms": "{n} g gula", "ta": "{n} கி சர்க்கரை"},
    "list.comma": {"en": ", ", "zh": "，", "ms": ", ", "ta": ", "},
    "list.and": {"en": " and ", "zh": "和", "ms": " dan ", "ta": " மற்றும் "},
    "habit.body": {
        "en": "You have had {label} {n} times in the last 2 weeks, about {kcal} kcal and {salt} mg salt each (from your logged meals).",
        "zh": "过去 2 周你吃过{label} {n} 次，每次约 {kcal} 千卡和 {salt} 毫克盐（来自你记录的餐食）。",
        "ms": "Anda makan {label} {n} kali dalam 2 minggu lepas, kira-kira {kcal} kcal dan {salt} mg garam setiap kali (daripada makanan yang anda catatkan).",
        "ta": "கடந்த 2 வாரங்களில் நீங்கள் {label} {n} முறை சாப்பிட்டுள்ளீர்கள், ஒவ்வொரு முறையும் சுமார் {kcal} kcal மற்றும் {salt} மி.கி உப்பு (நீங்கள் பதிவு செய்த உணவிலிருந்து).",
    },
    "habit.swap": {
        "en": " Your {dish} ({n} times, about {kcal} kcal) is the heaviest. Next time, try {alt} instead: it {saving}.",
        "zh": " 你的{dish}（{n} 次，约 {kcal} 千卡）是最重的。下次可以改试{alt}：它{saving}。",
        "ms": " {dish} anda ({n} kali, kira-kira {kcal} kcal) paling berat. Lain kali, cuba {alt} sebagai ganti: ia {saving}.",
        "ta": " உங்கள் {dish} ({n} முறை, சுமார் {kcal} kcal) மிக அதிகம். அடுத்த முறை அதற்குப் பதிலாக {alt} முயற்சி செய்யுங்கள்: அது {saving}.",
    },
    "habit.reflect": {
        "en": "Often eats {label}: {n} meals in the last 2 weeks, about {kcal} kcal each. The heaviest is {dish}.",
        "zh": "经常吃{label}：过去 2 周 {n} 餐，每餐约 {kcal} 千卡。最重的是{dish}。",
        "ms": "Kerap makan {label}: {n} kali makan dalam 2 minggu lepas, kira-kira {kcal} kcal setiap kali. Yang paling berat ialah {dish}.",
        "ta": "அடிக்கடி {label} சாப்பிடுகிறார்: கடந்த 2 வாரங்களில் {n} உணவுகள், ஒவ்வொன்றும் சுமார் {kcal} kcal. மிக அதிகமானது {dish}.",
    },
    "food.type.fried_food": {"en": "fried food", "zh": "炸物", "ms": "makanan goreng", "ta": "பொரித்த உணவு"},
    "food.type.rice_dish": {"en": "rice dishes", "zh": "饭类", "ms": "hidangan nasi", "ta": "சோற்று உணவுகள்"},
    "food.type.noodle_dish": {"en": "noodle dishes", "zh": "面类", "ms": "hidangan mi", "ta": "நூடுல்ஸ் உணவுகள்"},
    "food.type.soup_or_porridge": {"en": "soup or porridge", "zh": "汤或粥", "ms": "sup atau bubur", "ta": "சூப் அல்லது கஞ்சி"},
    "food.type.bread_or_pastry": {"en": "bread or pastry", "zh": "面包或糕点", "ms": "roti atau pastri", "ta": "ரொட்டி அல்லது பேஸ்ட்ரி"},
    "food.type.sweet_drink_or_dessert": {
        "en": "sweet drinks or desserts", "zh": "甜饮或甜点", "ms": "minuman manis atau pencuci mulut", "ta": "இனிப்பு பானங்கள் அல்லது இனிப்புகள்",
    },
    "food.type.vegetables_or_fruit": {"en": "vegetables or fruit", "zh": "蔬菜或水果", "ms": "sayur atau buah", "ta": "காய்கறி அல்லது பழம்"},
    "food.type.other": {"en": "other food", "zh": "其他食物", "ms": "makanan lain", "ta": "மற்ற உணவு"},
    "lunch.why_swap": {
        "en": "Instead of your usual {dish}: it {saving}.", "zh": "代替你平时常吃的{dish}：它{saving}。",
        "ms": "Sebagai ganti {dish} biasa anda: ia {saving}.", "ta": "உங்கள் வழக்கமான {dish} பதிலாக: அது {saving}.",
    },
    "lunch.why_general": {
        "en": "About {carbs} g carbs and {salt} mg salt per serving. A general idea from the food database, not personalised yet.",
        "zh": "每份约 {carbs} 克碳水和 {salt} 毫克盐。来自食物数据库的一般建议，尚未个性化。",
        "ms": "Kira-kira {carbs} g karbohidrat dan {salt} mg garam setiap hidangan. Idea umum daripada pangkalan data makanan, belum diperibadikan.",
        "ta": "ஒரு பரிமாறலுக்குச் சுமார் {carbs} கி கார்போஹைட்ரேட் மற்றும் {salt} மி.கி உப்பு. உணவுத் தரவுத்தளத்தின் பொதுவான யோசனை, இன்னும் தனிப்பயனாக்கப்படவில்லை.",
    },
    # outcome of a swap (nutritionstore.outcome_text)
    "outcome.since": {
        "en": "Since then you have had {dish} {n} {times}.", "zh": "从那时起，你吃过{dish} {n} {times}。",
        "ms": "Sejak itu anda telah makan {dish} {n} {times}.", "ta": "அதன் பிறகு நீங்கள் {dish} {n} {times} சாப்பிட்டுள்ளீர்கள்.",
    },
    "word.time.one": {"en": "time", "zh": "次", "ms": "kali", "ta": "முறை"},
    "word.time.many": {"en": "times", "zh": "次", "ms": "kali", "ta": "முறை"},
    "outcome.kcal": {
        "en": " Your logged meals were about {kcal} kcal {dir}", "zh": " 你记录的餐食约 {kcal} 千卡，{dir}",
        "ms": " Makanan yang anda catatkan kira-kira {kcal} kcal {dir}", "ta": " நீங்கள் பதிவு செய்த உணவுகள் சுமார் {kcal} kcal {dir}",
    },
    "outcome.salt": {
        "en": " and {mg} mg salt {dir}", "zh": "，盐分{dir} {mg} 毫克", "ms": " dan garam {dir} {mg} mg", "ta": " மற்றும் உப்பு {dir} {mg} மி.கி",
    },
    "outcome.than": {"en": " than your {usual}.", "zh": "，相比你平时的{usual}。", "ms": " berbanding {usual} biasa anda.", "ta": " உங்கள் வழக்கமான {usual} உடன் ஒப்பிடுகையில்."},
    "outcome.rise": {
        "en": " Your glucose rose {swapped} on average after it, against {usual_rise} after {usual} ({n_swapped} and {n_usual} meals), ",
        "zh": " 吃完后你的血糖平均上升 {swapped}，吃{usual}后为 {usual_rise}（分别为 {n_swapped} 餐和 {n_usual} 餐），",
        "ms": " Glukosa anda naik {swapped} secara purata selepas itu, berbanding {usual_rise} selepas {usual} ({n_swapped} dan {n_usual} kali makan), ",
        "ta": " அதன் பிறகு உங்கள் குளுக்கோஸ் சராசரியாக {swapped} அதிகரித்தது; {usual} பிறகு {usual_rise} ({n_swapped} மற்றும் {n_usual} உணவுகள்), ",
    },
    "outcome.rise.same": {"en": "about the same.", "zh": "基本相同。", "ms": "lebih kurang sama.", "ta": "ஏறக்குறைய ஒரே அளவு."},
    "outcome.rise.lower": {
        "en": "lower, associated with the swap, not proven.", "zh": "更低，与此次替换有关联，但未经证实。",
        "ms": "lebih rendah, dikaitkan dengan pertukaran ini, belum terbukti.", "ta": "குறைவு; இந்த மாற்றத்துடன் தொடர்புடையது, ஆனால் நிரூபிக்கப்படவில்லை.",
    },
    "outcome.rise.higher": {"en": "higher this time.", "zh": "这次更高。", "ms": "lebih tinggi kali ini.", "ta": "இந்த முறை அதிகம்."},
    "dir.lower": {"en": "lower", "zh": "更少", "ms": "lebih rendah", "ta": "குறைவாக"},
    "dir.higher": {"en": "higher", "zh": "更多", "ms": "lebih tinggi", "ta": "அதிகமாக"},
    "dir.same": {"en": "the same", "zh": "一样", "ms": "sama", "ta": "ஒரே அளவு"},
    # ------------------------------------------------------------------ glucose observations (glucose_feedback)
    "glucose.less": {"en": "less", "zh": "更少", "ms": "kurang", "ta": "குறைவாக"},
    "glucose.more": {"en": "more", "zh": "更多", "ms": "lebih", "ta": "அதிகமாக"},
    "glucose.swap.same": {
        "en": "After you switched to {dish}, your glucose rise after {kind} was about the same (based on {nb} meals before and {na} after). This is an observation from your data, not proof.",
        "zh": "你改吃{dish}后，吃{kind}后的血糖升幅与之前大致相同（基于之前 {nb} 餐和之后 {na} 餐）。这是来自你自己数据的观察，不是证明。",
        "ms": "Selepas anda beralih kepada {dish}, kenaikan glukosa selepas {kind} kurang lebih sama (berdasarkan {nb} kali makan sebelum dan {na} selepas). Ini ialah pemerhatian daripada data anda, bukan bukti.",
        "ta": "நீங்கள் {dish} க்கு மாறிய பிறகு, {kind} சாப்பிட்ட பின் உங்கள் குளுக்கோஸ் உயர்வு ஏறக்குறைய ஒரே அளவு (மாற்றத்திற்கு முன் {nb} உணவுகள், பின் {na} உணவுகள் அடிப்படையில்). இது உங்கள் தரவிலிருந்து ஒரு அவதானிப்பு, நிரூபணம் அல்ல.",
    },
    "glucose.swap.changed": {
        "en": "After you switched to {dish}, your glucose rose {diff} mmol/L {dir} on average after {kind} (based on {nb} meals before and {na} after). This is an observation from your data, not proof.",
        "zh": "你改吃{dish}后，吃{kind}后的血糖平均升幅比之前{dir} {diff} mmol/L（基于之前 {nb} 餐和之后 {na} 餐）。这是来自你自己数据的观察，不是证明。",
        "ms": "Selepas anda beralih kepada {dish}, glukosa anda naik {diff} mmol/L {dir} secara purata selepas {kind} (berdasarkan {nb} kali makan sebelum dan {na} selepas). Ini ialah pemerhatian daripada data anda, bukan bukti.",
        "ta": "நீங்கள் {dish} க்கு மாறிய பிறகு, {kind} சாப்பிட்ட பின் உங்கள் குளுக்கோஸ் சராசரியாக {diff} mmol/L {dir} உயர்ந்தது ({nb} உணவுகள் முன், {na} பின் அடிப்படையில்). இது உங்கள் தரவிலிருந்து ஒரு அவதானிப்பு, நிரூபணம் அல்ல.",
    },
    "glucose.walk.same": {
        "en": "On mornings after an evening walk, your fasting glucose was about the same (based on {n} evenings). This is an observation from your data, not proof.",
        "zh": "晚上散步后的早晨，你的空腹血糖大致相同（基于 {n} 个晚上）。这是来自你自己数据的观察，不是证明。",
        "ms": "Pada waktu pagi selepas berjalan kaki petang, glukosa puasa anda kurang lebih sama (berdasarkan {n} petang). Ini ialah pemerhatian daripada data anda, bukan bukti.",
        "ta": "மாலை நடைக்குப் பிறகு வரும் காலைகளில், உங்கள் வெறும் வயிற்றுக் குளுக்கோஸ் ஏறக்குறைய ஒரே அளவு ({n} மாலைகள் அடிப்படையில்). இது உங்கள் தரவிலிருந்து ஒரு அவதானிப்பு, நிரூபணம் அல்ல.",
    },
    "glucose.walk.changed": {
        "en": "On mornings after an evening walk, your fasting glucose was {diff} mmol/L {dir} (based on {n} evenings). This is an observation from your data, not proof.",
        "zh": "晚上散步后的早晨，你的空腹血糖比之前{dir} {diff} mmol/L（基于 {n} 个晚上）。这是来自你自己数据的观察，不是证明。",
        "ms": "Pada waktu pagi selepas berjalan kaki petang, glukosa puasa anda {dir} {diff} mmol/L (berdasarkan {n} petang). Ini ialah pemerhatian daripada data anda, bukan bukti.",
        "ta": "மாலை நடைக்குப் பிறகு வரும் காலைகளில், உங்கள் வெறும் வயிற்றுக் குளுக்கோஸ் {diff} mmol/L {dir} ({n} மாலைகள் அடிப்படையில்). இது உங்கள் தரவிலிருந்து ஒரு அவதானிப்பு, நிரூபணம் அல்ல.",
    },
    # ------------------------------------------------------------------ dose reminders (dose_timing)
    "dose.title": {"en": "Time for your {name}", "zh": "该服用{name}了", "ms": "Masa untuk {name} anda", "ta": "உங்கள் {name} மருந்துக்கான நேரம்"},
    "dose.renudge_title": {"en": "Still time for your {name}", "zh": "仍可服用{name}", "ms": "Masih ada masa untuk {name} anda", "ta": "உங்கள் {name} மருந்துக்கு இன்னும் நேரம் உள்ளது"},
    "dose.meal.before_meal": {"en": "Take it before a meal.", "zh": "请在饭前服用。", "ms": "Ambil sebelum makan.", "ta": "உணவுக்கு முன் எடுத்துக்கொள்ளுங்கள்."},
    "dose.meal.after_meal": {"en": "Take it after a meal.", "zh": "请在饭后服用。", "ms": "Ambil selepas makan.", "ta": "உணவுக்குப் பின் எடுத்துக்கொள்ளுங்கள்."},
    "dose.fact.period": {
        "en": "You usually take your {period} {name} about {usual} minutes after the set time. We remind you {offset} minutes after it.",
        "zh": "你通常在设定时间后约 {usual} 分钟服用{period}的{name}。我们会在之后 {offset} 分钟提醒你。",
        "ms": "Anda biasanya mengambil {name} {period} anda kira-kira {usual} minit selepas masa yang ditetapkan. Kami ingatkan anda {offset} minit selepasnya.",
        "ta": "பொதுவாக நீங்கள் உங்கள் {period} {name} மருந்தை அமைக்கப்பட்ட நேரத்திலிருந்து சுமார் {usual} நிமிடங்களுக்குப் பின் எடுக்கிறீர்கள். அதன் பின் {offset} நிமிடங்களுக்குப் பிறகு நினைவூட்டுகிறோம்.",
    },
    "dose.fact.plain": {
        "en": "You usually take your {name} about {usual} minutes after the set time. We remind you {offset} minutes after it.",
        "zh": "你通常在设定时间后约 {usual} 分钟服用你的{name}。我们会在之后 {offset} 分钟提醒你。",
        "ms": "Anda biasanya mengambil {name} anda kira-kira {usual} minit selepas masa yang ditetapkan. Kami ingatkan anda {offset} minit selepasnya.",
        "ta": "பொதுவாக நீங்கள் உங்கள் {name} மருந்தை அமைக்கப்பட்ட நேரத்திலிருந்து சுமார் {usual} நிமிடங்களுக்குப் பின் எடுக்கிறீர்கள். அதன் பின் {offset} நிமிடங்களுக்குப் பிறகு நினைவூட்டுகிறோம்.",
    },
    "period.morning": {"en": "morning", "zh": "早上", "ms": "pagi", "ta": "காலை"},
    "period.afternoon": {"en": "afternoon", "zh": "下午", "ms": "tengah hari", "ta": "மதியம்"},
    "period.evening": {"en": "evening", "zh": "晚上", "ms": "petang", "ta": "மாலை"},
    "period.bedtime": {"en": "bedtime", "zh": "睡前", "ms": "waktu tidur", "ta": "உறங்கும் நேரம்"},
    "dose.anchor.body": {
        "en": "{meal} logged. Time for your {part} {name}?", "zh": "已记录{meal}。该服用你的{part}{name}了吗？",
        "ms": "{meal} telah direkodkan. Masa untuk {name} {part} anda?", "ta": "{meal} பதிவானது. உங்கள் {part} {name} மருந்துக்கான நேரமா?",
    },
    "dose.anchor.title": {"en": "Your {part} dose", "zh": "你的{part}剂量", "ms": "Dos {part} anda", "ta": "உங்கள் {part} டோஸ்"},
    # ------------------------------------------------------------------ habit proposals from barriers and anchors (barrier_actions)
    "action.forgot.most": {
        "en": "Forgot is your most common reason ({n} times in 4 weeks).", "zh": "忘记是你最常见的原因（4 周内 {n} 次）。",
        "ms": "Terlupa ialah sebab paling kerap anda ({n} kali dalam 4 minggu).", "ta": "மறந்துவிடுவது உங்கள் மிகப் பொதுவான காரணம் (4 வாரங்களில் {n} முறை).",
    },
    "action.forgot.some": {
        "en": "You forgot {n} doses in the last 4 weeks.", "zh": "过去 4 周你漏服了 {n} 次。",
        "ms": "Anda terlupa {n} dos dalam 4 minggu lepas.", "ta": "கடந்த 4 வாரங்களில் நீங்கள் {n} டோஸ்களை மறந்துவிட்டீர்கள்.",
    },
    "action.forgot.tail": {
        "en": " Link your reminder to something you already do, such as breakfast?", "zh": " 要把提醒和你已经习惯做的事联系起来吗，比如早餐？",
        "ms": " Kaitkan peringatan anda dengan sesuatu yang anda sudah buat, seperti sarapan?",
        "ta": " உங்கள் நினைவூட்டலை நீங்கள் ஏற்கனவே செய்யும் ஒன்றுடன் இணைக்கவா, எடுத்துக்காட்டாக காலை உணவுடன்?",
    },
    "action.ran_out": {
        "en": "You ran out {n} times. Get a refill reminder {days} days before you run out?",
        "zh": "你断药了 {n} 次。要在药快用完前 {days} 天设置续领提醒吗？",
        "ms": "Anda kehabisan ubat {n} kali. Dapatkan peringatan isi semula {days} hari sebelum habis?",
        "ta": "நீங்கள் {n} முறை மருந்து தீர்ந்துவிட்டது. மருந்து தீர்வதற்கு {days} நாட்களுக்கு முன் மீண்டும் வாங்க நினைவூட்டல் அமைக்கவா?",
    },
    "action.away": {
        "en": "You missed {n} doses when you were away. Keep a note on your phone for those days?",
        "zh": "你外出时漏服了 {n} 次。要在手机上为这些日子做个备注吗？",
        "ms": "Anda terlepas {n} dos semasa berada di luar. Simpan nota pada telefon anda untuk hari-hari itu?",
        "ta": "நீங்கள் வெளியில் இருந்தபோது {n} டோஸ்களைத் தவறவிட்டீர்கள். அந்த நாட்களுக்கு உங்கள் தொலைபேசியில் குறிப்பு வைக்கவா?",
    },
    "anchor.suggest": {
        "en": "Your {part} {name} dose is usually taken within {minutes} minutes of finishing a meal ({hits} of {days} days). Remind you right after that meal?",
        "zh": "你通常在吃完一餐后 {minutes} 分钟内服用你的{part}{name}（{days} 天中有 {hits} 天）。要在那餐后立即提醒你吗？",
        "ms": "Dos {part} {name} anda biasanya diambil dalam {minutes} minit selepas makan ({hits} daripada {days} hari). Ingatkan anda sejurus selepas makan itu?",
        "ta": "உங்கள் {part} {name} டோஸ் பொதுவாக ஒரு உணவை முடித்த {minutes} நிமிடங்களுக்குள் எடுக்கப்படுகிறது ({days} நாட்களில் {hits}). அந்த உணவுக்குப் பின் உடனே நினைவூட்டவா?",
    },
    # ------------------------------------------------------------------ care checks (preventive)
    "check.gp_review": {"en": "GP review", "zh": "家庭医生检查", "ms": "Semakan GP", "ta": "GP மதிப்பாய்வு"},
    "check.diabetes_review": {"en": "Diabetes review", "zh": "糖尿病复查", "ms": "Semakan diabetes", "ta": "நீரிழிவு மதிப்பாய்வு"},
    "check.eye_screening": {"en": "Eye screening", "zh": "眼睛检查", "ms": "Saringan mata", "ta": "கண் பரிசோதனை"},
    "check.foot_screening": {"en": "Foot check", "zh": "足部检查", "ms": "Pemeriksaan kaki", "ta": "பாத பரிசோதனை"},
    "check.kidney_test": {"en": "Kidney test", "zh": "肾功能检查", "ms": "Ujian buah pinggang", "ta": "சிறுநீரக பரிசோதனை"},
    "check.hba1c_test": {"en": "HbA1c blood test", "zh": "糖化血红蛋白血液检查", "ms": "Ujian darah HbA1c", "ta": "HbA1c இரத்தப் பரிசோதனை"},
    "check.vaccination": {"en": "Vaccination", "zh": "疫苗接种", "ms": "Vaksinasi", "ta": "தடுப்பூசி"},
    "check.dental": {"en": "Dental check", "zh": "牙科检查", "ms": "Pemeriksaan pergigian", "ta": "பல் பரிசோதனை"},
    "check.other": {"en": "Other visit", "zh": "其他就诊", "ms": "Lawatan lain", "ta": "மற்ற வருகை"},
    "preventive.overdue": {
        "en": "Your {name} was due on {day}. Plan one?", "zh": "你的{name}应在{day}进行。要安排一次吗？",
        "ms": "{name} anda sepatutnya pada {day}. Rancang satu?", "ta": "உங்கள் {name} {day} அன்று செய்திருக்க வேண்டும். ஒன்றைத் திட்டமிடவா?",
    },
    "nudge.check_due.title": {"en": "A check is due", "zh": "有一项检查到期了", "ms": "Satu pemeriksaan sudah tiba", "ta": "ஒரு பரிசோதனை செய்ய வேண்டிய நேரம்"},
    "preventive.due": {
        "en": "Your {name} is due. You can plan it in your care plan.", "zh": "你的{name}到期了。你可以在护理计划中安排。",
        "ms": "{name} anda sudah tiba masanya. Anda boleh merancangnya dalam pelan penjagaan anda.",
        "ta": "உங்கள் {name} செய்ய வேண்டிய நேரம். உங்கள் பராமரிப்பு திட்டத்தில் திட்டமிடலாம்.",
    },
    # ------------------------------------------------------------------ reminder emails (notify_email)
    "email.subject.urgent": {
        "en": "Please check on {name}: possible low glucose", "zh": "请帮忙看看{name}：可能血糖偏低",
        "ms": "Tolong periksa {name}: mungkin gula darah rendah", "ta": "{name} அவர்களைச் சரிபார்க்கவும்: குளுக்கோஸ் குறைவாக இருக்கலாம்",
    },
    "email.name.contact_default": {"en": "your contact", "zh": "你的联系人", "ms": "kenalan anda", "ta": "உங்கள் தொடர்பாளர்"},
    "email.subject.meal": {"en": "{title}? One photo is all it takes", "zh": "{title}？拍一张照片就够了", "ms": "{title}? Satu gambar sahaja sudah cukup", "ta": "{title}? ஒரு படம் போதும்"},
    "email.subject.checkin": {
        "en": "How did you sleep? It takes thirty seconds", "zh": "你昨晚睡得怎么样？只需三十秒",
        "ms": "Bagaimana tidur anda? Hanya tiga puluh saat", "ta": "நீங்கள் எப்படித் தூங்கினீர்கள்? முப்பது வினாடிகள் போதும்",
    },
    "email.subject.workout": {"en": "A short walk counts today", "zh": "今天散个短步也算", "ms": "Berjalan kaki sebentar pun kira hari ini", "ta": "இன்று ஒரு சிறிய நடையும் கணக்கில் வரும்"},
    "email.subject.lunch": {"en": "Lunch ideas picked for you", "zh": "为你挑选的午餐建议", "ms": "Idea makan tengah hari pilihan untuk anda", "ta": "உங்களுக்காகத் தேர்ந்தெடுக்கப்பட்ட மதிய உணவு யோசனைகள்"},
    "email.subject.default": {"en": "A reminder from Smart Health", "zh": "来自 Smart Health 的提醒", "ms": "Peringatan daripada Smart Health", "ta": "Smart Health இலிருந்து ஒரு நினைவூட்டல்"},
    "email.greeting.plain": {"en": "Hi,", "zh": "你好，", "ms": "Hai,", "ta": "வணக்கம்,"},
    "email.greeting.named": {"en": "Hi {name},", "zh": "{name}，你好，", "ms": "Hai {name},", "ta": "வணக்கம் {name},"},
    "email.button.E2": {"en": "Log my meal", "zh": "记录我的餐食", "ms": "Catat makanan saya", "ta": "என் உணவைப் பதிவு செய்"},
    "email.button.E5": {"en": "Start my check-in", "zh": "开始我的记录", "ms": "Mula semakan saya", "ta": "என் பதிவைத் தொடங்கு"},
    "email.button.F1": {"en": "Log a workout", "zh": "记录一次运动", "ms": "Catat senaman", "ta": "ஒரு உடற்பயிற்சியைப் பதிவு செய்"},
    "email.button.E8": {"en": "See my lunch ideas", "zh": "查看我的午餐建议", "ms": "Lihat idea makan tengah hari saya", "ta": "என் மதிய உணவு யோசனைகளைப் பார்"},
    "email.button.H1": {"en": "Open my medicines", "zh": "打开我的药物", "ms": "Buka ubat saya", "ta": "என் மருந்துகளைத் திற"},
    "email.button.K3": {"en": "Open my care plan", "zh": "打开我的护理计划", "ms": "Buka pelan penjagaan saya", "ta": "என் பராமரிப்பு திட்டத்தைத் திற"},
    "email.button.default": {"en": "Open Smart Health", "zh": "打开 Smart Health", "ms": "Buka Smart Health", "ta": "Smart Health ஐத் திற"},
    "email.foot.contact": {
        "en": "You are getting this because someone added you as their emergency contact in Smart Health.",
        "zh": "你收到此邮件，是因为有人在 Smart Health 中将你添加为紧急联系人。",
        "ms": "Anda menerima ini kerana seseorang menambah anda sebagai kenalan kecemasan mereka dalam Smart Health.",
        "ta": "Smart Health இல் ஒருவர் உங்களை அவசரத் தொடர்பாளராகச் சேர்த்ததால் இந்தச் செய்தி உங்களுக்கு வந்துள்ளது.",
    },
    "email.foot.person": {
        "en": "You are getting this because you turned on reminder emails. You can turn them off any time in Me, then Privacy.",
        "zh": "你收到此邮件，是因为你开启了提醒邮件。你可以随时在“我的”，然后“隐私”中关闭。",
        "ms": "Anda menerima ini kerana anda menghidupkan e-mel peringatan. Anda boleh mematikannya bila-bila masa dalam Saya, kemudian Privasi.",
        "ta": "நினைவூட்டல் மின்னஞ்சல்களை இயக்கியதால் இது உங்களுக்கு வந்துள்ளது. நான், பிறகு தனியுரிமை என்பதில் எப்போது வேண்டுமானாலும் அணைக்கலாம்.",
    },
    "email.unsubscribe.line": {"en": "Unsubscribe: {url}", "zh": "退订：{url}", "ms": "Nyahlanggan: {url}", "ta": "குழுவிலிருந்து விலகு: {url}"},
    "email.unsubscribe": {"en": "Unsubscribe", "zh": "退订", "ms": "Nyahlanggan", "ta": "விலகு"},
    # ------------------------------------------------------------------ urgent low-glucose alert (urgent)
    "urgent.title.very_low": {"en": "Very low glucose", "zh": "血糖非常低", "ms": "Gula darah sangat rendah", "ta": "குளுக்கோஸ் மிகக் குறைவு"},
    "urgent.title.low": {"en": "Low glucose", "zh": "血糖偏低", "ms": "Gula darah rendah", "ta": "குளுக்கோஸ் குறைவு"},
    "urgent.demo_prefix": {"en": "Demo: ", "zh": "演示：", "ms": "Demo: ", "ta": "டெமோ: "},
    "urgent.alert_body": {
        "en": "Your glucose looks low: {value} mmol/L.", "zh": "你的血糖看起来偏低：{value} mmol/L。",
        "ms": "Gula darah anda nampak rendah: {value} mmol/L.", "ta": "உங்கள் குளுக்கோஸ் குறைவாகத் தெரிகிறது: {value} mmol/L.",
    },
    "urgent.contact.unnamed": {
        "en": "A person who listed you as their emergency contact", "zh": "一位将你列为紧急联系人的人",
        "ms": "Seseorang yang menyenaraikan anda sebagai kenalan kecemasan", "ta": "உங்களை அவசரத் தொடர்பாளராகப் பட்டியலிட்ட ஒருவர்",
    },
    "urgent.contact.title": {
        "en": "Possible low glucose: {who}", "zh": "可能血糖偏低：{who}", "ms": "Kemungkinan gula darah rendah: {who}", "ta": "குளுக்கோஸ் குறைவாக இருக்கலாம்: {who}",
    },
    "urgent.contact.body": {
        "en": "{who} may have low glucose ({value} mmol/L at {clock}). Please check on them. If they cannot answer, call {number}.",
        "zh": "{who}的血糖可能偏低（{clock} 时为 {value} mmol/L）。请查看他们的情况。如果他们无法回应，请拨打 {number}。",
        "ms": "{who} mungkin mempunyai gula darah rendah ({value} mmol/L pada {clock}). Sila periksa keadaannya. Jika mereka tidak dapat menjawab, telefon {number}.",
        "ta": "{who} அவர்களுக்குக் குளுக்கோஸ் குறைவாக இருக்கலாம் ({clock} மணிக்கு {value} mmol/L). தயவுசெய்து அவர்களைச் சரிபாருங்கள். பதிலளிக்க முடியவில்லை என்றால் {number} ஐ அழையுங்கள்.",
    },
    "urgent.demo.title": {"en": "DEMO. {title}", "zh": "演示。{title}", "ms": "DEMO. {title}", "ta": "டெமோ. {title}"},
    "urgent.demo.body": {
        "en": "This is a demo test, not a real reading. {body}", "zh": "这是演示测试，不是真实读数。{body}",
        "ms": "Ini ujian demo, bukan bacaan sebenar. {body}", "ta": "இது ஒரு டெமோ சோதனை, உண்மையான அளவீடு அல்ல. {body}",
    },
    # ------------------------------------------------------------------ chat fixed replies (services/chat)
    "chat.urgent": {
        "en": "This sounds urgent. Call 995 now, or ask someone near you to call.",
        "zh": "这听起来很紧急。请立即拨打 995，或请身边的人帮你打电话。",
        "ms": "Ini kedengaran mendesak. Telefon 995 sekarang, atau minta seseorang berdekatan menelefon.",
        "ta": "இது அவசரமாகத் தெரிகிறது. இப்போதே 995 ஐ அழையுங்கள், அல்லது அருகில் உள்ள ஒருவரை அழைக்கச் சொல்லுங்கள்.",
    },
    "chat.refused": {
        "en": "I cannot advise on medicines or diagnose. This is worth asking your doctor.",
        "zh": "我不能就药物提供建议，也不能做诊断。这个问题值得问问你的医生。",
        "ms": "Saya tidak boleh memberi nasihat tentang ubat atau membuat diagnosis. Elok tanya doktor anda.",
        "ta": "மருந்துகள் பற்றி ஆலோசனை வழங்கவோ நோயறிதல் செய்யவோ என்னால் முடியாது. இதை உங்கள் மருத்துவரிடம் கேட்பது நல்லது.",
    },
    "chat.caution": {
        "en": "I am not able to answer that here. If you feel unwell, call 995 or contact your doctor.",
        "zh": "我无法在这里回答这个问题。如果你觉得不舒服，请拨打 995 或联系你的医生。",
        "ms": "Saya tidak dapat menjawab soalan itu di sini. Jika anda rasa tidak sihat, telefon 995 atau hubungi doktor anda.",
        "ta": "இதற்கு இங்கே என்னால் பதில் அளிக்க முடியவில்லை. உடல்நிலை சரியில்லை என்றால் 995 ஐ அழையுங்கள் அல்லது உங்கள் மருத்துவரைத் தொடர்பு கொள்ளுங்கள்.",
    },
    "chat.unavailable": {
        "en": "I cannot answer right now. Please try again in a little while. If it is urgent, call 995.",
        "zh": "我现在无法回答。请稍后再试。如果情况紧急，请拨打 995。",
        "ms": "Saya tidak dapat menjawab sekarang. Sila cuba sebentar lagi. Jika mendesak, telefon 995.",
        "ta": "இப்போது என்னால் பதில் அளிக்க முடியவில்லை. சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும். அவசரம் என்றால் 995 ஐ அழையுங்கள்.",
    },
    "chat.guard_down": {
        "en": "I cannot check this question right now, so I will not answer it. Please try again in a little while. If it is urgent, call 995.",
        "zh": "我现在无法检查这个问题，所以不会回答。请稍后再试。如果情况紧急，请拨打 995。",
        "ms": "Saya tidak dapat menyemak soalan ini sekarang, jadi saya tidak akan menjawabnya. Sila cuba sebentar lagi. Jika mendesak, telefon 995.",
        "ta": "இந்தக் கேள்வியை இப்போது என்னால் சரிபார்க்க முடியாது, எனவே பதில் அளிக்க மாட்டேன். சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும். அவசரம் என்றால் 995 ஐ அழையுங்கள்.",
    },
    "chat.blocked_reply": {
        "en": "I am not able to share that answer. Please ask your doctor or pharmacist.",
        "zh": "我无法分享这个回答。请咨询你的医生或药剂师。",
        "ms": "Saya tidak dapat berkongsi jawapan itu. Sila tanya doktor atau ahli farmasi anda.",
        "ta": "அந்தப் பதிலை என்னால் பகிர முடியாது. உங்கள் மருத்துவர் அல்லது மருந்தாளுநரிடம் கேளுங்கள்.",
    },
    "chat.empty": {
        "en": "I do not have that in your data yet. Once you log meals, doses or glucose, I can answer questions about them.",
        "zh": "你的数据里还没有这些信息。你记录餐食、剂量或血糖后，我就能回答相关问题。",
        "ms": "Saya belum ada maklumat itu dalam data anda. Apabila anda merekodkan makanan, dos atau gula darah, saya boleh menjawab soalan tentangnya.",
        "ta": "உங்கள் தரவில் அது இன்னும் இல்லை. உணவு, டோஸ் அல்லது குளுக்கோஸ் பதிவு செய்த பிறகு, அவை பற்றிய கேள்விகளுக்கு நான் பதில் அளிக்கலாம்.",
    },
    "chat.help": {
        "en": ("I can answer questions about your own data: your glucose, meals, activity, sleep, medicines and doctor questions. "
               "I cannot give medical advice or diagnose. For emergencies call 995."),
        "zh": "我可以回答关于你自己数据的问题：血糖、餐食、活动、睡眠、药物和给医生的问题。我不能提供医疗建议或做诊断。紧急情况请拨打 995。",
        "ms": "Saya boleh menjawab soalan tentang data anda sendiri: gula darah, makanan, aktiviti, tidur, ubat dan soalan untuk doktor. Saya tidak boleh memberi nasihat perubatan atau membuat diagnosis. Untuk kecemasan, telefon 995.",
        "ta": "உங்கள் சொந்தத் தரவு பற்றிய கேள்விகளுக்கு நான் பதில் அளிக்கலாம்: உங்கள் குளுக்கோஸ், உணவு, செயல்பாடு, தூக்கம், மருந்துகள் மற்றும் மருத்துவருக்கான கேள்விகள். மருத்துவ ஆலோசனை அல்லது நோயறிதல் வழங்க முடியாது. அவசரநிலைக்கு 995 ஐ அழையுங்கள்.",
    },
    "chat.off_scope": {
        "en": "I can only help with your own Smart Health data: your glucose, meals, activity, sleep, medicines, symptoms you logged, and your doctor questions. I cannot help with that.",
        "zh": "我只能帮助处理你自己的 Smart Health 数据：血糖、餐食、活动、睡眠、药物、你记录的症状，以及给医生的问题。这个问题我无法帮忙。",
        "ms": "Saya hanya boleh membantu dengan data Smart Health anda sendiri: gula darah, makanan, aktiviti, tidur, ubat, gejala yang anda catat dan soalan untuk doktor. Saya tidak dapat membantu dengan itu.",
        "ta": "உங்கள் சொந்த Smart Health தரவில் மட்டுமே என்னால் உதவ முடியும்: குளுக்கோஸ், உணவு, செயல்பாடு, தூக்கம், மருந்துகள், நீங்கள் பதிவு செய்த அறிகுறிகள் மற்றும் மருத்துவரிடம் கேட்க வேண்டிய கேள்விகள். அதில் என்னால் உதவ முடியாது.",
    },
    "chat.injection": {
        "en": "I cannot follow that request. I can only answer questions about your own Smart Health data.",
        "zh": "我无法按这个要求去做。我只能回答与你自己的 Smart Health 数据有关的问题。",
        "ms": "Saya tidak dapat mengikut permintaan itu. Saya hanya boleh menjawab soalan tentang data Smart Health anda sendiri.",
        "ta": "அந்தக் கோரிக்கையை என்னால் பின்பற்ற முடியாது. உங்கள் சொந்த Smart Health தரவு பற்றிய கேள்விகளுக்கு மட்டுமே என்னால் பதில் அளிக்க முடியும்.",
    },
    "chat.harmful": {
        "en": "I cannot change, send or share anything from here. You can do that yourself in the app, and I can point you to the right screen.",
        "zh": "我无法在这里更改、发送或分享任何内容。你可以自己在应用里操作，我可以告诉你该去哪个页面。",
        "ms": "Saya tidak boleh mengubah, menghantar atau berkongsi apa-apa dari sini. Anda boleh melakukannya sendiri dalam aplikasi, dan saya boleh tunjukkan skrin yang betul.",
        "ta": "இங்கிருந்து எதையும் மாற்றவோ, அனுப்பவோ, பகிரவோ என்னால் முடியாது. நீங்களே செயலியில் அதைச் செய்யலாம்; சரியான திரையை நான் காட்டுகிறேன்.",
    },
    "chat.other_person": {
        "en": "I can only talk about your own data. I cannot share anyone else's information, and I never ask for passwords or ID numbers.",
        "zh": "我只能谈论你自己的数据。我不能分享其他任何人的信息，也不会向你索要密码或证件号码。",
        "ms": "Saya hanya boleh bercakap tentang data anda sendiri. Saya tidak boleh berkongsi maklumat orang lain, dan saya tidak pernah meminta kata laluan atau nombor pengenalan.",
        "ta": "உங்கள் சொந்தத் தரவைப் பற்றி மட்டுமே என்னால் பேச முடியும். வேறொருவரின் தகவலை நான் பகிர மாட்டேன்; கடவுச்சொல் அல்லது அடையாள எண்களை ஒருபோதும் கேட்க மாட்டேன்.",
    },
    "chat.diagnosis": {
        "en": "I cannot diagnose or say what is causing how you feel. Please talk to your doctor about it. If you feel very unwell, call 995.",
        "zh": "我不能做诊断，也不能说明你的感觉是什么原因造成的。请和你的医生谈谈。如果你感到非常不适，请拨打 995。",
        "ms": "Saya tidak boleh membuat diagnosis atau mengatakan apa yang menyebabkan perasaan anda. Sila berbincang dengan doktor anda. Jika anda berasa sangat tidak sihat, hubungi 995.",
        "ta": "என்னால் நோயைக் கண்டறிய முடியாது; நீங்கள் உணர்வதற்கான காரணத்தையும் சொல்ல முடியாது. தயவுசெய்து உங்கள் மருத்துவரிடம் பேசுங்கள். நீங்கள் மிகவும் உடல்நலக் குறைவாக உணர்ந்தால் 995-ஐ அழையுங்கள்.",
    },
    "chat.med_change": {
        "en": "I cannot advise on starting, stopping or changing a medicine or its dose. Please ask your doctor or pharmacist.",
        "zh": "我不能就开始、停用或更改药物或剂量给出建议。请咨询你的医生或药剂师。",
        "ms": "Saya tidak boleh menasihati tentang memulakan, menghentikan atau menukar ubat atau dosnya. Sila tanya doktor atau ahli farmasi anda.",
        "ta": "மருந்தை தொடங்குவது, நிறுத்துவது அல்லது அதன் அளவை மாற்றுவது குறித்து என்னால் ஆலோசனை சொல்ல முடியாது. உங்கள் மருத்துவர் அல்லது மருந்தாளுநரிடம் கேளுங்கள்.",
    },
    "chat.symptom_refer": {
        "en": "I cannot tell what is causing a symptom. Please talk to your doctor about it. If you feel very unwell, call 995.",
        "zh": "我无法判断症状的原因。请和你的医生谈谈。如果你感到非常不适，请拨打 995。",
        "ms": "Saya tidak dapat memberitahu apa yang menyebabkan sesuatu gejala. Sila berbincang dengan doktor anda. Jika anda berasa sangat tidak sihat, hubungi 995.",
        "ta": "ஓர் அறிகுறிக்கு என்ன காரணம் என்று என்னால் சொல்ல முடியாது. தயவுசெய்து உங்கள் மருத்துவரிடம் பேசுங்கள். நீங்கள் மிகவும் உடல்நலக் குறைவாக உணர்ந்தால் 995-ஐ அழையுங்கள்.",
    },
    "chat.med_refer": {
        "en": "This is general information about your medicine. Your pharmacist or doctor can tell you more.",
        "zh": "这是关于你的药物的一般信息。你的药剂师或医生可以告诉你更多。",
        "ms": "Ini ialah maklumat am tentang ubat anda. Ahli farmasi atau doktor anda boleh memberitahu lebih lanjut.",
        "ta": "இது உங்கள் மருந்து பற்றிய பொதுவான தகவல். உங்கள் மருந்தாளுநர் அல்லது மருத்துவர் மேலும் சொல்ல முடியும்.",
    },
    "chat.offer_question": {
        "en": "Would you like to add this to your doctor questions?",
        "zh": "要把这个加到你给医生的问题里吗？",
        "ms": "Adakah anda mahu menambah ini ke soalan untuk doktor anda?",
        "ta": "இதை உங்கள் மருத்துவரிடம் கேட்கும் கேள்விகளில் சேர்க்க விரும்புகிறீர்களா?",
    },
    "chat.sign_insights": {
        "en": "You can see more on the Insights tab, under Overview.",
        "zh": "你可以在“洞察”标签的“概览”中查看更多。",
        "ms": "Anda boleh melihat lebih lanjut di tab Insight, di bawah Gambaran.",
        "ta": "மேலும் விவரங்களை Insights தாவலில், Overview பகுதியில் பார்க்கலாம்.",
    },
    "chat.sign_food": {
        "en": "You can find more ideas under Me, Review suggestions, and in Lunch ideas.",
        "zh": "你可以在“我”里的“查看建议”和“午餐灵感”中找到更多想法。",
        "ms": "Anda boleh mendapatkan lebih banyak idea di bawah Saya, Semak cadangan, dan di Idea makan tengah hari.",
        "ta": "மேலும் யோசனைகளை Me தாவலில் Review suggestions பகுதியிலும், Lunch ideas பகுதியிலும் காணலாம்.",
    },
    "chat.sign_meds": {
        "en": "You can see each medicine on the Meds tab.",
        "zh": "你可以在“药物”标签中查看每种药物。",
        "ms": "Anda boleh melihat setiap ubat di tab Ubat.",
        "ta": "ஒவ்வொரு மருந்தையும் Meds தாவலில் பார்க்கலாம்.",
    },
    "chat.sign_care": {
        "en": "You can see your next visit and checks in your care plan, under Me.",
        "zh": "你可以在“我”里的护理计划中查看下次就诊和检查。",
        "ms": "Anda boleh melihat lawatan seterusnya dan pemeriksaan dalam pelan penjagaan anda, di bawah Saya.",
        "ta": "உங்கள் அடுத்த சந்திப்பையும் பரிசோதனைகளையும் Me தாவலில் உள்ள உங்கள் பராமரிப்புத் திட்டத்தில் பார்க்கலாம்.",
    },
    "chat.greet": {
        "en": "Hello. I can answer questions about your own Smart Health data. What would you like to know?",
        "zh": "你好。我可以回答关于你自己 Smart Health 数据的问题。你想了解什么？",
        "ms": "Helo. Saya boleh menjawab soalan tentang data Smart Health anda sendiri. Apa yang anda ingin tahu?",
        "ta": "வணக்கம். உங்கள் சொந்த Smart Health தரவு பற்றிய கேள்விகளுக்கு நான் பதில் அளிக்க முடியும். நீங்கள் என்ன தெரிந்துகொள்ள விரும்புகிறீர்கள்?",
    },
    "chat.rate": {
        "en": "You are sending messages very quickly. Please wait a moment and try again.",
        "zh": "你发送消息太快了。请稍等片刻再试。",
        "ms": "Anda menghantar mesej terlalu pantas. Sila tunggu sebentar dan cuba lagi.",
        "ta": "நீங்கள் மிக வேகமாக செய்திகளை அனுப்புகிறீர்கள். சிறிது நேரம் காத்திருந்து மீண்டும் முயலுங்கள்.",
    },
    "chat.unclear": {
        "en": "I did not quite understand. You can ask about your glucose, meals, activity, sleep, medicines, symptoms you logged or your doctor questions.",
        "zh": "我没有完全明白。你可以问关于血糖、餐食、活动、睡眠、药物、你记录的症状或给医生的问题。",
        "ms": "Saya kurang faham. Anda boleh bertanya tentang gula darah, makanan, aktiviti, tidur, ubat, gejala yang anda catat atau soalan untuk doktor.",
        "ta": "எனக்கு முழுமையாகப் புரியவில்லை. குளுக்கோஸ், உணவு, செயல்பாடு, தூக்கம், மருந்துகள், நீங்கள் பதிவு செய்த அறிகுறிகள் அல்லது மருத்துவரிடம் கேட்க வேண்டிய கேள்விகள் பற்றி கேட்கலாம்.",
    },
    "chat.fallback_intro": {
        "en": "Here is what your own data shows:",
        "zh": "以下是你自己的数据显示的内容：",
        "ms": "Ini yang ditunjukkan oleh data anda sendiri:",
        "ta": "உங்கள் சொந்தத் தரவு காட்டுவது இதுதான்:",
    },
    "chat.self_harm": {
        "en": "I am sorry you feel this way. You do not have to face this alone. If you are in danger right now, call 995. You can also call the Samaritans of Singapore on 1767 at any time, or tell someone near you.",
        "zh": "听到你有这样的感受，我很难过。你不必独自面对。如果你现在有危险，请拨打 995。你也可以随时致电新加坡援助会（Samaritans of Singapore）1767，或告诉身边的人。",
        "ms": "Saya bersimpati dengan perasaan anda. Anda tidak perlu menghadapinya sendirian. Jika anda dalam bahaya sekarang, hubungi 995. Anda juga boleh menelefon Samaritans of Singapore di 1767 pada bila-bila masa, atau beritahu seseorang yang berdekatan.",
        "ta": "நீங்கள் இவ்வாறு உணர்வதற்காக வருந்துகிறேன். இதை நீங்கள் தனியாக எதிர்கொள்ள வேண்டாம். நீங்கள் இப்போது ஆபத்தில் இருந்தால் 995-ஐ அழையுங்கள். எந்த நேரத்திலும் சிங்கப்பூர் சமாரிட்டன்ஸ் (Samaritans of Singapore) 1767-ஐயும் அழைக்கலாம்; அல்லது அருகிலுள்ள ஒருவரிடம் சொல்லுங்கள்.",
    },
    "chat.thanks": {
        "en": "You are welcome. Ask me any time about your own Smart Health data.",
        "zh": "不客气。你可以随时询问关于你自己 Smart Health 数据的问题。",
        "ms": "Sama-sama. Tanya saya bila-bila masa tentang data Smart Health anda sendiri.",
        "ta": "பரவாயில்லை. உங்கள் சொந்த Smart Health தரவு பற்றி எப்போது வேண்டுமானாலும் கேளுங்கள்.",
    },
    "chat.verdict_note": {
        "en": "I cannot say whether a number is normal, good or bad. Your doctor can tell you what your numbers mean for you.",
        "zh": "我不能说某个数值是否正常、好或不好。你的医生可以告诉你这些数值对你意味着什么。",
        "ms": "Saya tidak boleh mengatakan sama ada sesuatu nombor itu normal, baik atau buruk. Doktor anda boleh memberitahu maksud nombor anda untuk anda.",
        "ta": "ஓர் எண் இயல்பானதா, நல்லதா அல்லது மோசமானதா என்று என்னால் சொல்ல முடியாது. உங்கள் எண்கள் உங்களுக்கு என்ன பொருள் தருகின்றன என்பதை உங்கள் மருத்துவர் சொல்ல முடியும்.",
    },
}


# ---------------------------------------------------------------------- lookup
def _fields(text: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


def tr(lang: str | None, key: str, **vars: Any) -> str:
    """The text for `key` in `lang`, filled with `vars` ({name} placeholders).

    Falls back to English when the language is unknown, the key has no entry for it, or its placeholders do not match the English ones.
    A key with no English entry at all returns the key itself (a programming slip shows, it does not crash the app).
    """
    entry = CATALOG.get(key)
    if entry is None:
        logger.warning("unknown text key %s", key)
        return key
    en = entry["en"]
    text = en
    if lang in LANGS and lang != "en":
        cand = entry.get(lang)
        if cand and _fields(cand) == _fields(en):
            text = cand
    try:
        return text.format(**vars)
    except (KeyError, IndexError, ValueError):
        return en.format(**vars)


def has(key: str) -> bool:
    return key in CATALOG


def label(lang: str | None, prefix: str, value: str) -> str:
    """A word from a family of keys (a period of the day, a food type), or the value itself when there is no key for it."""
    k = f"{prefix}.{value}"
    return tr(lang, k) if k in CATALOG else value


# ---------------------------------------------------------------------- the person's language
def person_language(user: Any = None, conn: Any = None) -> str:
    """The language saved on the person's profile (user_profile.language). English when there is no profile row, no user, or any problem.

    Pass `conn` to reuse an open connection (no second connection is opened). Never raises: a language lookup must not break a reminder.
    """
    try:
        if user is None:
            return DEFAULT_LANG
        uid = str(uuid.UUID(str(user)))            # a non-UUID (a test name) is simply English, no database call
    except (ValueError, TypeError, AttributeError):
        return DEFAULT_LANG
    try:
        if conn is not None:
            return _language_from(conn, uid)
        from app.db.logstore import tx

        with tx() as c:
            return _language_from(c, uid)
    except Exception:  # a failed lookup is English, never a failed reminder
        logger.exception("could not read the person's language; using English")
        return DEFAULT_LANG


def _language_from(conn: Any, uid: str) -> str:
    row = conn.execute("select language::text l from user_profile where user_id=%s", (uid,)).fetchone()
    lang = row["l"] if row else None
    return lang if lang in LANGS else DEFAULT_LANG
