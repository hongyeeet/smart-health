# Translation review

Each area appends its own section. Strings are machine translations for zh, ms and ta and wait for a native speaker. English is the source of truth.

## Home and logging

Machine-translated (zh, ms, ta). A native speaker must review every string before release. English is the source of truth.

**Files:** `apps/web/src/i18n/locales/zh/log.json`, `ms/log.json`, `ta/log.json` (390 keys, prefixes `home.`, `log.`, `workout.`). Screens: `features/home/Home.tsx`, `features/home/DoseCard.tsx`, `features/log/*` (hub, meal, symptom, check-in, saved, lunch ideas, meal banner, finish hook), `features/workout/LogWorkout.tsx`, `features/workout/WorkoutTracker.tsx`, `features/sheets/EntrySheet.tsx`, `features/sheets/MissSheet.tsx`.

### Safety-relevant strings (review first)

| Key | English | Why it matters |
|---|---|---|
| `home.urgent.veryLow`, `home.urgent.low`, `home.urgent.body` | Very low glucose alert / Low glucose alert / Your glucose looks low ... Tap to see what to do. | Urgent banner on Home |
| `log.getHelp` | Get help now | Red-flag button (symptom and saved screens) |
| `log.sym.*` (chest pain, confusion, fainting, breathlessness at rest, sudden vision loss) | Red-flag symptom names | These English names are still the saved and checked values; only the display is translated |
| `log.sym.vomitWarn` | If you are vomiting and your glucose is high, get care today. Tell your clinic. | Medical advice wording |
| `home.dose.taken` | Taken | Medicine "Taken" button. Must mean the person has taken the dose |
| `home.dose.dueNow`, `home.dose.notConfirmed`, `home.dose.tellUs`, `home.dose.next`, `home.dose.after`, `home.dose.saveError`, `home.dose.loadError` | Due now / {{when}} is not confirmed. / Tell us why / Next: ... | Medicine status on Home |
| `log.miss.*` (reasons, `log.miss.helps`, `log.miss.noteDoctor`, `log.miss.questionAdded`, `log.miss.saveError`) | Why was it not confirmed? and the reason list | Missed-dose reasons, which go to the doctor brief |
| `log.finish.error`, `log.meal.readError`, `log.entry.error` | Could not save / read / delete | Failure messages |
| `log.meal.estimates`, `log.meal.checkPortion` | Nutrients are estimates ... / Check this: we are less sure about the portion | Estimate wording |
| `log.lunch.typical` | ... Ideas only, not medical advice. | Disclaimer |
| `workout.tracker.glucose` | ... (associated with, not proven). | Keeps "associated with", never "caused by" |
| `workout.tracker.hrNote` | Heart rate is an estimate of effort. It is not a medical measurement. | Disclaimer |
| `home.worth.notAdvice` | An idea for next time, not advice. ... | Disclaimer on food suggestions |

### Notes for the reviewer

- Numbers, units (kcal, g, mg, mmol/L, kg, min, bpm), and `995` are not translated. Placeholders such as `{{n}}` are unchanged.
- Sentences with bold words use `<Trans>` with indexed tags (`<0>`, `<1>`). Keep the tags when editing.
- Plurals are two keys (for example `home.streak.one` / `home.streak.many`, `home.noticed.one` / `home.noticed.many`).

### Not translated (on purpose or still English)

- Text the server sends: the saved screen title, detail and lines, the flag and swap text, the lunch option names and reasons, the glucose trend word, the heart-rate effort note and narrative, and error text from the server. These need a server-side translation, not a client key.
- Exercise names, food names, medicine names, activity names saved with a workout, and the symptom and check-in values that are stored. The display can be translated; the stored value stays English.
- Date and time formatting (`en-SG` and `en-US` locale strings in the code).
- Notifications.tsx and UserSwitch.tsx belong to another package and are not in this section.

## Backend nudges, emails and chat replies

Machine-translated (zh, ms, ta). A native speaker must review every string, and a clinician must review the medicine, dose, refill and urgent texts, before release. English is the source of truth. The text is in `services/api/app/services/texts.py` (one `CATALOG` entry per key, `en`/`zh`/`ms`/`ta`). The output guard always runs on the English text, and the translation is a fixed mapping of that exact text, so a checked English text can only become its own translation.

**Not translated (data):** the number 995, numbers, units, medicine and dish names, and the label's own directions on a medicine box. Dates keep English month abbreviations (a gap, see below).

### Safety-relevant keys (review first)

| Key | English | Why it matters |
|---|---|---|
| `chat.urgent` | This sounds urgent. Call 995 now, or ask someone near you to call. | Urgent reply in the chat |
| `chat.caution` | I am not able to answer that here. If you feel unwell, call 995 or contact your doctor. | Refusal that points to emergency care |
| `chat.unavailable`, `chat.guard_down` | I cannot answer right now ... If it is urgent, call 995. | Fixed reply when the model or the guard is down |
| `chat.refused` | I cannot advise on medicines or diagnose. This is worth asking your doctor. | Refusal on medicine or diagnosis |
| `chat.blocked_reply` | I am not able to share that answer. Please ask your doctor or pharmacist. | Reply blocked by the output guard |
| `chat.empty`, `chat.help` | No data yet / what I can answer; for emergencies call 995. | Scope statements |
| `urgent.title.very_low`, `urgent.title.low`, `urgent.alert_body`, `urgent.demo_prefix` | Very low glucose / Low glucose / Your glucose looks low: {value} mmol/L. | Low-glucose alert on screen J1 |
| `urgent.contact.body`, `urgent.contact.title`, `urgent.contact.unnamed`, `urgent.demo.*` | {who} may have low glucose ({value} mmol/L at {clock}). Please check on them. If they cannot answer, call {number}. | Email to the emergency contact, in the PERSON's language |
| `email.subject.urgent`, `email.foot.contact`, `email.name.contact_default` | Please check on {name}: possible low glucose | Contact email subject and footer |
| `dose.title`, `dose.renudge_title` | Time for your {name} / Still time for your {name} | Dose reminder title |
| `dose.meal.before_meal`, `dose.meal.after_meal` | Take it before/after a meal. | Dose timing wording (the label's own directions are never translated) |
| `dose.fact.period`, `dose.fact.plain` | You usually take your ... about {usual} minutes after the set time. We remind you {offset} minutes after it. | Memory fact about dose timing |
| `dose.anchor.body`, `dose.anchor.title`, `anchor.suggest` | {meal} logged. Time for your {part} {name}? | Dose right after a meal |
| `period.morning`, `period.afternoon`, `period.evening`, `period.bedtime` | morning / afternoon / evening / bedtime | Dose time words |
| `refill.title`, `refill.low`, `refill.used_up`, `refill.days` | Time to refill {name} / supply running low / days left | Refill reminders |
| `action.ran_out`, `action.away`, `action.forgot.*` | Refill reminder / missed doses wording | Barrier action proposals (shown to confirm) |
| `question.added.body`, `question.added.title` | We added this to your questions for your doctor: {text} | The doctor question text itself stays English (see below) |
| `salt.body`, `salt.swap`, `salt.walk`, `salt.title.*` | A salty meal today ... an easy 10-minute walk ... check with your doctor. | Salt-day prompt with walking advice |
| `habit.body`, `habit.swap`, `habit.reflect`, `outcome.*`, `saving.*` | Food habit and swap wording with the person's own numbers | Association wording ("associated with", "not proven") must stay honest |
| `glucose.swap.*`, `glucose.walk.*` | ... This is an observation from your data, not proof. | Glucose observation wording |
| `email.unsubscribe`, `email.foot.person`, `email.button.*` | Unsubscribe, footers and button labels | Reminder email footer and links |

### Decisions a reviewer should know about

- **Doctor question text stays English.** `barrier_actions._question_reminders` finds these questions by their English words, and the list is a clinical record the doctor reads. Only the wording around it is translated.
- **Text already stored keeps its language.** A reminder is written in the person's language when it is created. A reminder created before a language change keeps its old wording until it expires (at most the same day).
- **Not covered in this section (still English):** the relative day labels "Yesterday" and the date format ("2 Sep 2025"), the food type names on other screens (the habit text in these reminders is translated), the chat's starter questions and source names, the model's own error messages (they are logs, not shown), and the urgent word rule in the chat, which only recognises English words.

## Me pages, urgent alert, chat, sharing and setup

Machine-translated (zh, ms, ta). A native speaker must review every string before release. English is the source of truth.

**Files:** `apps/web/src/i18n/locales/zh/me.json`, `ms/me.json`, `ta/me.json` (379 keys each, prefixes `me.`, `urgent.`, `chat.`, `share.`, `setup.`). Screens: `features/me/*` (Me, Learned, Progress, Care, Appointment, Sources, Language, Privacy, DataAccount, Contact), `features/me/care/parts.tsx`, `features/me/settings/EmailCard.tsx` and `rules.ts`, `features/urgent/Urgent.tsx` and `parts.tsx`, `features/chat/Chat.tsx`, `parts.tsx` and `api.ts` (two toasts), `features/brief/ShareSheet.tsx` and `SharedReport.tsx`, `features/onboarding/ChatSetup.tsx` and `chat/steps.ts`.

### Notes for the reviewer

- The chat setup's keys moved from `onboarding.chat.*` to `setup.*` (same English). The `onboarding.*` keys used by the other onboarding files are not touched.
- `DELETE` stays in English in the delete-account confirmation. The person must type it exactly; only the words around it are translated.
- Kept as they are in every language: `995`, `DELETE`, `mmol/L`, `kcal`, `mg`, `cm`, `kg`, `%`, the example addresses and numbers in placeholders, and the `{{...}}` values.
- Rich text tags stay where they are: `<b>` (bold numbers), `<s>` (a faded word) and `<n>` (the sample reading).
- The "Language" note now says Chinese, Malay and Tamil are machine translated and still being checked by native speakers. It is in all four languages.
- Dates stay in the English format (for example `en-US` and `en-SG` month names). Only the words around them are translated.
- Some screens use plural wording as separate sentences (for example "1 minute ago" and "{{n}} minutes ago"), so each language can word its own plural.

### Safety-relevant strings (review first)

Every urgent-alert, chat refusal and emergency wording, emergency-contact and delete-account string, and the consent wording that turns health data off, is listed here with the English next to it.

| Key | English | 中文 (zh) | Bahasa Melayu (ms) | தமிழ் (ta) |
|---|---|---|---|---|
| `chat.failedText` | We could not reach Smart Health. Your question was not answered. | 无法联系 Smart Health。您的问题没有得到回答。 | Kami tidak dapat hubungi Smart Health. Soalan anda tidak dijawab. | Smart Health ஐ அடைய முடியவில்லை. உங்கள் கேள்விக்குப் பதில் அளிக்கப்படவில்லை. |
| `chat.failedTitle` | That did not go through | 没有成功 | Tidak berjaya | அது வெற்றிபெறவில்லை |
| `chat.intro` | Ask about your own glucose, meals, activity, sleep or medicines. I answer from what you have logged. | 可以问关于您自己的血糖、饮食、活动、睡眠或药物的问题。我只根据您记录的内容回答。 | Tanya tentang gula darah, makanan, aktiviti, tidur atau ubat anda sendiri. Saya menjawab berdasarkan apa yang anda telah rekodkan. | உங்கள் சொந்த இரத்தச் சர்க்கரை, உணவு, நடவடிக்கை, தூக்கம் அல்லது மருந்துகள் பற்றிக் கேளுங்கள். நீங்கள் பதிவு செய்தவற்றிலிருந்து நான் பதிலளிக்கிறேன். |
| `chat.note` | Smart Health answers from your own data. It cannot give medical advice. For emergencies call 995. | Smart Health 只根据您自己的数据回答。它不能提供医疗建议。紧急情况请拨打 995。 | Smart Health menjawab berdasarkan data anda sendiri. Ia tidak boleh memberi nasihat perubatan. Untuk kecemasan, telefon 995. | Smart Health உங்கள் சொந்தத் தரவிலிருந்து மட்டுமே பதிலளிக்கும். அது மருத்துவ ஆலோசனை வழங்க முடியாது. அவசரநிலைக்கு 995 ஐ அழைக்கவும். |
| `me.contact.details` | Their details | 他们的资料 | Maklumat mereka | அவர்களின் விவரங்கள் |
| `me.contact.email` | Email address | 电邮地址 | Alamat e-mel | மின்னஞ்சல் முகவரி |
| `me.contact.emailHint` | The alert is sent to this address. | 提醒会发送到这个地址。 | Amaran dihantar ke alamat ini. | இந்த முகவரிக்கு எச்சரிக்கை அனுப்பப்படும். |
| `me.contact.emailNotYet` | Email for your emergency contact is not set up yet, so it cannot be saved. The name and phone number can still be saved. | 紧急联络人的电邮功能尚未设置，因此无法保存电邮。姓名和电话仍可保存。 | E-mel untuk kenalan kecemasan anda belum disediakan, jadi ia tidak dapat disimpan. Nama dan nombor telefon masih boleh disimpan. | உங்கள் அவசரத் தொடர்புக்கான மின்னஞ்சல் இன்னும் அமைக்கப்படவில்லை, எனவே சேமிக்க முடியாது. பெயரையும் தொலைபேசி எண்ணையும் இன்னும் சேமிக்கலாம். |
| `me.contact.explain` | If your glucose looks very low and you do not answer, we email this person. | 如果您的血糖很低，而您没有回应，我们会向此人发送电邮。 | Jika gula darah anda sangat rendah dan anda tidak menjawab, kami akan e-mel orang ini. | உங்கள் குளுக்கோஸ் மிகக் குறைவாக இருந்து, நீங்கள் பதிலளிக்காவிட்டால், இவருக்கு மின்னஞ்சல் அனுப்புவோம். |
| `me.contact.explainTwo` | The email asks them to check on you, or to call 995. Add their email address so the alert can reach them. | 电邮会请他们来看看您的情况，或拨打 995。请添加他们的电邮地址，以便提醒能送达。 | E-mel itu meminta mereka menjenguk anda, atau telefon 995. Tambah alamat e-mel mereka supaya amaran boleh sampai kepada mereka. | மின்னஞ்சல் அவர்களை உங்களைச் சரிபார்க்கச் சொல்லும், அல்லது 995 ஐ அழைக்கச் சொல்லும். எச்சரிக்கை அவர்களைச் சென்றடைய அவர்களின் மின்னஞ்சல் முகவரியைச் சேர்க்கவும். |
| `me.contact.loadError` | We could not load your emergency contact just now. Please try again in a moment. | 暂时无法加载您的紧急联络人。请稍后再试。 | Kami tidak dapat memuatkan kenalan kecemasan anda sekarang. Sila cuba lagi sebentar lagi. | உங்கள் அவசரத் தொடர்பை இப்போது ஏற்ற முடியவில்லை. சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும். |
| `me.contact.name` | Name | 姓名 | Nama | பெயர் |
| `me.contact.namePlaceholder` | For example, Mdm Lim | 例如：Lim 太太 | Contoh: Puan Lim | எடுத்துக்காட்டு: திருமதி லிம் |
| `me.contact.notSaved` | Your contact was not saved. | 您的联络人未能保存。 | Kenalan anda tidak dapat disimpan. | உங்கள் தொடர்பு சேமிக்கப்படவில்லை. |
| `me.contact.phone` | Mobile number | 手机号码 | Nombor telefon bimbit | கைபேசி எண் |
| `me.contact.phoneHint` | Digits only, with an optional + at the start. | 只能填数字，开头可加一个 +。 | Nombor sahaja, dengan + di awal jika mahu. | இலக்கங்கள் மட்டும், தொடக்கத்தில் விருப்பமான + உடன். |
| `me.contact.relation` | Relationship to you | 与您的关系 | Hubungan dengan anda | உங்களுடனான உறவு |
| `me.contact.relationPlaceholder` | For example, spouse | 例如：配偶 | Contoh: suami atau isteri | எடுத்துக்காட்டு: மனைவி |
| `me.contact.save` | Save contact | 保存联络人 | Simpan kenalan | தொடர்பைச் சேமி |
| `me.contact.saved` | Emergency contact saved | 紧急联络人已保存 | Kenalan kecemasan disimpan | அவசரத் தொடர்பு சேமிக்கப்பட்டது |
| `me.contact.sub` | Someone who can check on you if your glucose is very low. | 如果您的血糖很低，可以请一位能来看看您的人。 | Seseorang yang boleh menjenguk anda jika gula darah anda sangat rendah. | உங்கள் குளுக்கோஸ் மிகக் குறைவாக இருந்தால் உங்களைச் சரிபார்க்கக்கூடிய ஒருவர். |
| `me.contact.title` | Emergency contact | 紧急联络人 | Kenalan kecemasan | அவசரத் தொடர்பு |
| `me.data.deleteTitle` | Delete my account and data | 删除我的账户和数据 | Padam akaun dan data saya | என் கணக்கையும் தரவையும் நீக்கு |
| `me.data.deleteWhat` | This removes your logs, your medicines and doses, your profile, and what Smart Health has learned about you. It cannot be undone. | 这会删除您的记录、药物和剂量、个人资料，以及 Smart Health 对您的了解。此操作无法撤销。 | Ini akan memadam rekod, ubat dan dos anda, profil anda, dan apa yang Smart Health telah pelajari tentang anda. Ia tidak boleh dibatalkan. | இது உங்கள் பதிவுகள், மருந்துகள் மற்றும் அளவுகள், உங்கள் சுயவிவரம், மற்றும் Smart Health உங்களைப் பற்றி அறிந்தவற்றை நீக்கும். இதை மீட்க முடியாது. |
| `me.data.download` | Download my data | 下载我的数据 | Muat turun data saya | என் தரவைப் பதிவிறக்கு |
| `me.data.downloadButton` | Download my data | 下载我的数据 | Muat turun data saya | என் தரவைப் பதிவிறக்கு |
| `me.data.downloadFailed` | The file could not be downloaded. | 无法下载文件。 | Fail tidak dapat dimuat turun. | கோப்பைப் பதிவிறக்க முடியவில்லை. |
| `me.data.downloadInfo` | Get a file with what you have logged, your profile, your consent history, and your medicines and doses. You can keep it or share it with someone you trust. | 获取一个文件，内含您记录的内容、个人资料、同意记录，以及您的药物和剂量。您可以保留它，也可以与您信任的人分享。 | Dapatkan fail yang mengandungi apa yang anda telah rekodkan, profil anda, sejarah persetujuan anda, serta ubat dan dos anda. Anda boleh simpannya atau kongsikannya dengan orang yang anda percaya. | நீங்கள் பதிவு செய்தவை, உங்கள் சுயவிவரம், உங்கள் ஒப்புதல் வரலாறு, உங்கள் மருந்துகள் மற்றும் அளவுகள் அடங்கிய ஒரு கோப்பைப் பெறுங்கள். அதை வைத்துக்கொள்ளலாம் அல்லது நம்பும் ஒருவருடன் பகிரலாம். |
| `me.data.downloadNotStarted` | The download did not start. | 下载没有开始。 | Muat turun tidak bermula. | பதிவிறக்கம் தொடங்கவில்லை. |
| `me.data.downloading` | Your file is downloading | 您的文件正在下载 | Fail anda sedang dimuat turun | உங்கள் கோப்பு பதிவிறக்கப்படுகிறது |
| `me.data.keepAccount` | Keep my account | 保留我的账户 | Simpan akaun saya | என் கணக்கை வைத்துக்கொள் |
| `me.data.log` | Requests and changes to your settings are kept in an activity log that cannot be changed. | 有关您设置的请求和更改，会记录在一份无法更改的活动日志中。 | Permintaan dan perubahan kepada tetapan anda disimpan dalam log aktiviti yang tidak boleh diubah. | உங்கள் அமைப்புகளுக்கான கோரிக்கைகளும் மாற்றங்களும் மாற்ற முடியாத செயல்பாட்டுப் பதிவில் வைக்கப்படும். |
| `me.data.notRecorded` | The request was not recorded. | 请求未能记录。 | Permintaan tidak direkodkan. | கோரிக்கை பதிவு செய்யப்படவில்லை. |
| `me.data.preparing` | Preparing your file | 正在准备您的文件 | Menyediakan fail anda | உங்கள் கோப்பைத் தயார் செய்கிறது |
| `me.data.received` | Request received | 已收到请求 | Permintaan diterima | கோரிக்கை பெறப்பட்டது |
| `me.data.received2` | Your request is recorded. We will process it within 30 days, by {{date}}. Nothing has been deleted yet. | 您的请求已记录。我们会在 30 天内处理，即 {{date}} 前。目前尚未删除任何内容。 | Permintaan anda telah direkodkan. Kami akan memprosesnya dalam masa 30 hari, menjelang {{date}}. Belum ada apa-apa yang dipadamkan. | உங்கள் கோரிக்கை பதிவு செய்யப்பட்டுள்ளது. 30 நாட்களுக்குள், {{date}} க்குள் செயல்படுத்துவோம். இதுவரை எதுவும் நீக்கப்படவில்லை. |
| `me.data.requestDeletion` | Request deletion | 提出删除请求 | Minta pemadaman | நீக்கக் கோரு |
| `me.data.title` | Data and account | 资料与账户 | Data dan akaun | தரவும் கணக்கும் |
| `me.data.typeLabel` | Type DELETE to confirm | 输入 DELETE 以确认 | Taip DELETE untuk mengesahkan | உறுதிசெய்ய DELETE என தட்டச்சு செய்யவும் |
| `me.data.typeToConfirm` | To confirm, type DELETE in capital letters. We will then record your request, and process it within 30 days. | 为确认，请用大写字母输入 DELETE。随后我们会记录您的请求，并在 30 天内处理。 | Untuk mengesahkan, taip DELETE dengan huruf besar. Kami kemudian akan merekodkan permintaan anda, dan memprosesnya dalam masa 30 hari. | உறுதிசெய்ய, பெரிய எழுத்துகளில் DELETE என தட்டச்சு செய்யவும். பின்னர் உங்கள் கோரிக்கையைப் பதிவு செய்து, 30 நாட்களுக்குள் செயல்படுத்துவோம். |
| `me.learned.notDiagnosis` | These are patterns in your own logs, not a diagnosis. If a delete is wrong for you, nothing is lost: it just stops being used. | 这些是您自己记录中的规律，并不是诊断。如果删除对您不正确，不会有损失：它只是不再被使用。 | Ini ialah corak daripada rekod anda sendiri, bukan diagnosis. Jika padam itu tidak betul untuk anda, tiada apa yang hilang: ia cuma tidak lagi digunakan. | இவை உங்கள் சொந்தப் பதிவுகளில் உள்ள வடிவங்கள், நோயறிதல் அல்ல. நீக்குவது உங்களுக்குத் தவறு என்றால், எதுவும் இழக்கப்படாது: அது இனி பயன்படுத்தப்படாது. |
| `me.learned.onlySuggests` | It only suggests. It never changes your medicines, your numbers or its own safety rules. | 它只提出建议。它绝不会更改您的药物、数字或它自己的安全规则。 | Ia hanya mencadangkan. Ia tidak sekali-kali menukar ubat, nombor atau peraturan keselamatannya sendiri. | இது பரிந்துரைக்க மட்டுமே செய்கிறது. உங்கள் மருந்துகளையும், எண்களையும், அதன் சொந்தப் பாதுகாப்பு விதிகளையும் ஒருபோதும் மாற்றாது. |
| `me.privacy.askOffText` | Smart Health will stop reading what you log and what your devices send. Insights, reminders and the doctor brief will stop until you turn this on again. Nothing is deleted. | Smart Health 将停止读取您记录的内容和您的设备发送的数据。洞察、提醒和医生摘要会一直停止，直到您重新开启为止。不会删除任何内容。 | Smart Health akan berhenti membaca apa yang anda rekodkan dan apa yang dihantar oleh peranti anda. Wawasan, peringatan dan laporan doktor akan berhenti sehingga anda menghidupkannya semula. Tiada apa yang dipadamkan. | நீங்கள் பதிவு செய்வதையும், உங்கள் சாதனங்கள் அனுப்புவதையும் Smart Health படிப்பதை நிறுத்தும். நீங்கள் மீண்டும் இயக்கும் வரை நுண்ணறிவுகளும், நினைவூட்டல்களும், மருத்துவர் சுருக்கமும் நிறுத்தப்படும். எதுவும் நீக்கப்படாது. |
| `me.privacy.askOffTitle` | Turn off using your health data? | 要关闭使用您的健康数据吗？ | Matikan penggunaan data kesihatan anda? | உங்கள் உடல்நலத் தரவைப் பயன்படுத்துவதை நிறுத்தவா? |
| `me.privacy.dataSub` | Lets Smart Health read what you log and what your devices send, so it can show your insights, reminders and doctor brief. | 让 Smart Health 读取您记录的内容和您的设备发送的数据，以便显示您的洞察、提醒和医生摘要。 | Benarkan Smart Health membaca apa yang anda rekodkan dan apa yang dihantar peranti anda, supaya ia dapat menunjukkan wawasan, peringatan dan laporan doktor anda. | நீங்கள் பதிவு செய்வதையும் உங்கள் சாதனங்கள் அனுப்புவதையும் Smart Health படிக்க அனுமதிக்கிறது, அதனால் உங்கள் நுண்ணறிவுகள், நினைவூட்டல்கள், மருத்துவர் சுருக்கத்தைக் காட்ட முடியும். |
| `me.privacy.dataTitle` | Use my health data | 使用我的健康数据 | Guna data kesihatan saya | என் உடல்நலத் தரவைப் பயன்படுத்து |
| `me.privacy.keepOn` | Keep it on | 保持开启 | Biarkan dihidupkan | இயக்கத்திலேயே வை |
| `me.privacy.required` | Required to use the app.  | 使用本应用所必需。  | Diperlukan untuk guna aplikasi.  | செயலியைப் பயன்படுத்த இது தேவை.  |
| `me.privacy.turnOff` | Turn off | 关闭 | Matikan | அணை |
| `urgent.addContact` | Add an emergency contact | 添加紧急联络人 | Tambah kenalan kecemasan | அவசரத் தொடர்பைச் சேர் |
| `urgent.askedEmail` | We have asked to email {{name}} that you may have low glucose. | 我们已请求向 {{name}} 发送电邮，告知您可能血糖偏低。 | Kami telah meminta untuk e-mel {{name}} bahawa anda mungkin mempunyai gula darah rendah. | நீங்கள் குறைந்த குளுக்கோஸில் இருக்கலாம் என்று {{name}} க்கு மின்னஞ்சல் அனுப்ப கேட்டுள்ளோம். |
| `urgent.backHome` | Back to Home | 返回主页 | Kembali ke Laman Utama | முகப்புக்குத் திரும்பு |
| `urgent.beingTold` | Your contact is being told | 正在通知您的联络人 | Kenalan anda sedang dimaklumkan | உங்கள் தொடர்புக்குத் தெரிவிக்கப்படுகிறது |
| `urgent.call` | Call {{n}} | 拨打 {{n}} | Telefon {{n}} | {{n}} ஐ அழை |
| `urgent.callMyContact` | Call my contact | 拨打我的联络人 | Telefon kenalan saya | என் தொடர்பை அழை |
| `urgent.callNamed` | Call {{name}} (my contact) | 拨打 {{name}}（我的联络人） | Telefon {{name}} (kenalan saya) | {{name}} ஐ அழை (என் தொடர்பு) |
| `urgent.canDo` | What you can do | 您可以做的事 | Apa yang boleh anda buat | நீங்கள் செய்யக்கூடியவை |
| `urgent.checkFailed` | We could not check just now. If you feel unwell or confused, call 995 now. Tap here to try again. | 我们暂时无法检查。如果您感到不适或神志不清，请立即拨打 995。点击此处再试一次。 | Kami tidak dapat semak sekarang. Jika anda rasa tidak sihat atau keliru, telefon 995 sekarang. Ketik di sini untuk cuba lagi. | இப்போது சரிபார்க்க முடியவில்லை. உடல்நலக் குறைவாகவோ குழப்பமாகவோ உணர்ந்தால், இப்போதே 995 ஐ அழைக்கவும். மீண்டும் முயற்சிக்க இங்கே தட்டவும். |
| `urgent.demo` | DEMO, not a real reading | 演示，并非真实读数 | DEMO, bukan bacaan sebenar | DEMO, உண்மையான அளவீடு அல்ல |
| `urgent.emailIn` | If you do not answer in {{time}}, we will email {{name}}. | 如果您在 {{time}} 内没有回应，我们将向 {{name}} 发送电邮。 | Jika anda tidak menjawab dalam {{time}}, kami akan e-mel {{name}}. | {{time}} க்குள் நீங்கள் பதிலளிக்கவில்லை என்றால், {{name}} க்கு மின்னஞ்சல் அனுப்புவோம். |
| `urgent.failed` | That did not go through. If you feel unwell or confused, call {{n}} now, then try again. | 没有成功。如果您感到不适或神志不清，请立即拨打 {{n}}，然后再试一次。 | Itu tidak berjaya. Jika anda rasa tidak sihat atau keliru, telefon {{n}} sekarang, kemudian cuba lagi. | அது வெற்றிபெறவில்லை. உடல்நலக் குறைவாகவோ குழப்பமாகவோ உணர்ந்தால், இப்போதே {{n}} ஐ அழைத்து, பின்னர் மீண்டும் முயற்சிக்கவும். |
| `urgent.imOkay` | I'm okay now | 我现在没事了 | Saya okay sekarang | நான் இப்போது நலமாக இருக்கிறேன் |
| `urgent.justNow` | just now | 刚刚 | sebentar tadi | இப்போதுதான் |
| `urgent.limits` | These limits are placeholders and have not had clinical review. | 这些限制是暂定的，尚未经过临床审核。 | Had ini ialah tempat letak sementara dan belum disemak secara klinikal. | இந்த வரம்புகள் தற்காலிகமானவை, இன்னும் மருத்துவ மதிப்பாய்வு செய்யப்படவில்லை. |
| `urgent.low` | low | 偏低 | rendah | குறைவு |
| `urgent.minutesAgo` | {{n}} minutes ago | {{n}} 分钟前 | {{n}} minit yang lalu | {{n}} நிமிடங்களுக்கு முன் |
| `urgent.noEmail` | No emergency contact email is saved, so we cannot email anyone for you. | 没有保存紧急联络人的电邮，因此我们无法为您发送电邮。 | Tiada e-mel kenalan kecemasan disimpan, jadi kami tidak dapat e-mel sesiapa untuk anda. | அவசரத் தொடர்பின் மின்னஞ்சல் சேமிக்கப்படவில்லை, எனவே உங்களுக்காக யாருக்கும் மின்னஞ்சல் அனுப்ப முடியாது. |
| `urgent.nobodyEmailed` | There is no emergency contact email saved, so nobody was emailed. Use the call buttons below. | 没有保存紧急联络人的电邮，因此没有人收到电邮。请使用下方的拨号按钮。 | Tiada e-mel kenalan kecemasan disimpan, jadi tiada siapa dihantar e-mel. Guna butang panggilan di bawah. | அவசரத் தொடர்பின் மின்னஞ்சல் சேமிக்கப்படவில்லை, எனவே யாருக்கும் மின்னஞ்சல் அனுப்பப்படவில்லை. கீழுள்ள அழைப்பு பொத்தான்களைப் பயன்படுத்துங்கள். |
| `urgent.none` | No low glucose right now. | 目前没有血糖偏低。 | Tiada gula darah rendah sekarang. | இப்போது குறைந்த குளுக்கோஸ் இல்லை. |
| `urgent.notSent` | No email could be sent | 无法发送电邮 | E-mel tidak dapat dihantar | மின்னஞ்சல் அனுப்ப முடியவில்லை |
| `urgent.okayText` | You said you are okay. We will look at your sensor again in {{minutes}} minutes. If it is still low, we will alert you again. | 您表示您没事。我们会在 {{minutes}} 分钟后再次查看您的传感器。如果仍然偏低，我们会再次提醒您。 | Anda kata anda okay. Kami akan semak sensor anda semula dalam {{minutes}} minit. Jika masih rendah, kami akan memberi amaran semula. | நீங்கள் நலமாக இருப்பதாகச் சொன்னீர்கள். {{minutes}} நிமிடங்களில் உங்கள் சென்சாரை மீண்டும் பார்ப்போம். இன்னும் குறைவாக இருந்தால், மீண்டும் எச்சரிப்போம். |
| `urgent.oneMinuteAgo` | 1 minute ago | 1 分钟前 | 1 minit yang lalu | 1 நிமிடத்துக்கு முன் |
| `urgent.pillLow` | Low | 偏低 | Rendah | குறைவு |
| `urgent.pillVeryLow` | Very low | 非常低 | Sangat rendah | மிகக் குறைவு |
| `urgent.rechecking` | Checking again in {{time}} | 将在 {{time}} 后再次检查 | Menyemak semula dalam {{time}} | {{time}} இல் மீண்டும் சரிபார்க்கிறது |
| `urgent.sentence` | Your glucose looks {{level}}: {{value}} mmol/L, {{ago}} | 您的血糖{{level}}：{{value}} mmol/L，{{ago}} | Gula darah anda {{level}}: {{value}} mmol/L, {{ago}} | உங்கள் குளுக்கோஸ் {{level}}: {{value}} mmol/L, {{ago}} |
| `urgent.tellNow` | Tell my contact now | 立即告诉我的联络人 | Maklumkan kenalan saya sekarang | இப்போதே என் தொடர்புக்குத் தெரிவி |
| `urgent.tellingNow` | Telling {{name}} now. | 现在通知 {{name}}。 | Memaklumkan {{name}} sekarang. | இப்போது {{name}} க்குத் தெரிவிக்கிறது. |
| `urgent.title` | Low glucose alert | 低血糖警示 | Amaran gula darah rendah | குறைந்த குளுக்கோஸ் எச்சரிக்கை |
| `urgent.unwell` | If you feel unwell or confused, call {{n}} now. Follow the plan your doctor gave you. | 如果您感到不适或神志不清，请立即拨打 {{n}}。请遵照您的医生给您的方案。 | Jika anda rasa tidak sihat atau keliru, telefon {{n}} sekarang. Ikut pelan yang doktor anda beri. | உடல்நலக் குறைவாகவோ குழப்பமாகவோ உணர்ந்தால், இப்போதே {{n}} ஐ அழைக்கவும். உங்கள் மருத்துவர் கொடுத்த திட்டத்தைப் பின்பற்றுங்கள். |
| `urgent.veryLow` | very low | 非常低 | sangat rendah | மிகக் குறைவு |
| `urgent.yourContact` | your emergency contact | 您的紧急联络人 | kenalan kecemasan anda | உங்கள் அவசரத் தொடர்பு |

### Server texts that stay English (not translated here)

These come from the server, so they are not in this file. Each one still needs a translation on the server side or from the owner of that area:

- Chat: every answer, refusal and emergency reply, the starter questions, the follow-up questions, the action labels and the source chip labels.
- Urgent: the emergency number value (`995` from the server) and the contact's name as stored.
- Care plan: check and screening labels and details, next-visit dates and places, the origin of each question, and the reason a visit was suggested.
- Connected sources: source names, models, status labels and notes.
- Learned: what each fact says and why, its category, the names of suggestions in the digest, the run steps and the run status words.
- Progress: the note under the comparison.
- Sharing: the report itself (the same report as the doctor brief) and the day counts from the share API.

## Insights, Day view, review and charts

Machine-translated (zh, ms, ta). A native speaker must review every string before release. English is the source of truth.

**Files:** `apps/web/src/i18n/locales/zh/insights.json`, `ms/insights.json`, `ta/insights.json` (378 keys, prefixes `insights.`, `day.`, `review.`, `charts.`). Screens: `features/insights/*` (Overview, Glucose, Food, Activity, Sleep, Medication, Sprint, WhySheet, grids, shared), `features/day/*` (Day, MarkerSheet, DayTimeline, dayMath), `features/review/*` (Review, SuggestionCard), `charts/small.tsx`, `charts/TrendChart.tsx`, `charts/DayChart.tsx`.

### Safety-relevant strings (review first)

| Key | English | Why it matters |
|---|---|---|
| `insights.why.findings.limit` | These are associated with, not proven. They do not show that one thing causes the other. Worth mentioning to your doctor... | Must keep the "associated with, not proven" meaning |
| `insights.why.footer` | Every number is worked out by the app from your own data. Nothing here is advice or a diagnosis. | Not-advice wording |
| `insights.why.findings.shows`, `insights.why.findings.from` | Things that tend to go together in your own data... / at least 5 matching events | Findings explanation |
| `insights.shared.basedOn` | Based on {{n}} matched events in your own history. | Findings count |
| `insights.glucose.worthDoctor` | Worth mentioning to your doctor. | Appended after the server drift sentence |
| `insights.glucose.gmi`, `insights.glucose.gmiSub`, `insights.why.glucose.limit` | Estimated A1c (GMI) ... not a lab result | Must not read as a lab result |
| `insights.glucose.inRange`, `insights.glucose.events` | % in range between low and high / sharp rises, low readings | Numbers and glucose band wording |
| `insights.glucose.fastingPlain`, `insights.glucose.fastingPlainBand` | 5 to 7 am average; shaded band is the usual range | Definition of fasting |
| `insights.sleep.nightOne`, `insights.sleep.nightMany`, `insights.sleep.avg*` | nights under 6 hours | Sleep threshold wording |
| `insights.medication.took`, `insights.medication.tookNotConfirmedOne`, `insights.medication.tookNotConfirmedMany`, `insights.medication.noDoses` | You took X% of your prescription doses ... not confirmed | Adherence wording; medicine doses |
| `insights.medication.fastingPlain` | ... Looking at them together does not show that one causes the other. | Association, not cause |
| `insights.medication.adherenceNote`, `insights.why.medication.limit` | Adherence counts prescription medicines only ... not a score | Missed doses are for the doctor, not a score |
| `insights.why.medication.from` | A dose counts as late when taken more than an hour after its time. | Late-dose rule |
| `insights.why.week.limit`, `insights.why.food.limit`, `insights.why.activity.limit` | A dash means no data, not zero / One meal is not a pattern / Goals here are general | Gap and limit wording |
| `insights.grid.doseMissed`, `insights.grid.doseLate`, `insights.grid.doseUnconfirmed`, `insights.grid.doseNone` | Missed / Taken late / Not confirmed / No dose | Dose state words (also in the shape legend) |
| `insights.sprint.wornPartial`, `insights.sprint.notYetTimed` | treat the numbers as a rough guide / not yet a timed sprint | Limits of the sensor summary |
| `day.dose.taken`, `day.dose.late`, `day.dose.notConfirmed`, `day.dose.missed` | taken on time / taken late / not confirmed yet / missed | Dose state on the Day view |
| `day.flag.salt`, `day.flag.sugar` | High salt / High sugar for one meal | Food flags |
| `day.sheet.notProof` | Things that happen close together are not proof that one caused the other. | Association, not cause |
| `day.glucoseSummary`, `day.tl.rangeWords`, `day.tl.gapNote`, `day.tl.noSensor` | % in range / hatched areas have no reading, never joined | Gaps are never drawn as a line |
| `review.intro`, `review.score.ratingsSoFar` | ... The target and the count of 20 are placeholders pending review. | Placeholder target and count (85% and 20 stay as they are) |
| `review.score.met`, `review.score.notMet`, `review.score.unsafeOne`, `review.score.unsafeMany`, `review.score.metTitle`, `review.score.notMetTitle` | % judged reasonable / aim is none | Target and unsafe rule |
| `review.verdict.unsafeHint` | Could harm someone with type 2 diabetes | Meaning of the Unsafe rating |
| `review.problemUnsafe`, `review.card.commentNeeded`, `review.card.commentPhUnsafe` | Unsafe needs a comment. Say what could harm someone. | Unsafe must have a reason |
| `review.card.workedOut`, `review.sourceSample` | Not a health claim / typical hawker dishes, not anyone's logged meals | Scope of the suggestions |
| `charts.dose.missed`, `charts.dose.unconfirmed`, `charts.dose.skipped`, `charts.day.stateMissed`, `charts.day.stateUnconfirmed` | Missed / Not confirmed / Skipped by plan | Dose states in charts |
| `charts.level.veryLow`, `charts.level.low`, `charts.level.high`, `charts.level.veryHigh`, `charts.tirItem` | Very low / Low / High / Very high | Glucose band names |
| `charts.intensityNote`, `charts.gridKey`, `charts.noSensor`, `insights.sleep.noSleep` | Counts toward the weekly goal / shade meaning / No sensor data | Chart reading guides |

**Units and numbers are not translated:** mmol/L, kcal, mg, g, %, the signs + and − and the number 20 and 85% targets. Medicine names are data and are not in these files.

### Still English on purpose (built by the server)

These sentences and labels come from `services/api/app/services/insights.py` and `day.py` (or from the data) and are not yet translated:

- Insights: "What changed" lines (`changes[].text`), findings text (`patterns[].text`), the drift sentence before "Worth mentioning to your doctor." (`drift.text`), the period label (`period.label`).
- Insights data labels: medicine names and regimens, reason labels for missed doses, activity type and workout labels, symptom labels, grid cell labels, meal times and food names.
- Day view: marker titles and sub-titles, the outcome sentence in "What the data shows" (`marker.outcome`), and the row labels in that sheet (`rows[].label`).
- Review: the suggestion change sentence (`item.change`) and the server message when the queue is empty (`queue.message`). The fallback "There is nothing to review yet." is translated.
- The Day view date label uses the en-GB date format (`dayLabel`) and is not translated.

### Notes for the reviewer

- Plural lines use separate keys for one and many (`insights.activity.mixOne`/`mixMany`, `insights.sleep.nightOne`/`nightMany`, `day.logged.*`, `charts.day.dosesOne`/`dosesMany`, and the review unsafe lines). Chinese has no plural, so both keys are the same in zh.
- Tamil "a day" is placed after the number, as in English (`insights.activity.aDay`).

## Whole app (2026-10-13)

Joely asked that choosing Chinese, Malay or Tamil in Language and display changes everything in the app. Every string in the web app that had no translation (about 1,100 per language) was machine translated with `scripts/translate_locales.py` (Gemini `gemini-3.8-flash`; each batch keeps the placeholders and the numbered tags, uses a glossary from the earlier translations, and is refused if the English comes back unchanged). **All of these are machine translations that a native speaker still has to review**, like the sections above.

**Files:** `apps/web/src/i18n/locales/<zh|ms|ta>/` now has `app.json` (alerts, brief, common, switch and the small areas), `meds.json` (add by hand, medicine detail, stock, scan screens, medicines list), `onboarding.json`, and the earlier `insights.json`, `log.json`, `me.json` (new keys were added to those). To fill future gaps: `npm run i18n:extract` in `apps/web`, then `python scripts/translate_locales.py` from the repository root (a dry run first with `--dry-run`).

**Also changed:** dates, weekdays, months and clock times follow the chosen language (`apps/web/src/lib/locale.ts`, `dateLocale()`); numbers and units stay the same everywhere. The bottom tabs, Back, Close, Loading and similar labels are now translatable.

**Still English on purpose:** the printable doctor report (L3) and the shared doctor page, because the doctor reads them. Medicine and food names, and names of devices.

### Wording the server builds (2026-10-13)

The web app now sends the chosen language with every call (header `X-Lang`), and changing the language reloads the screens' data. The server follows it for the wording it builds: dose units and phrases ("1 Tab", "today at 8:00 pm", "This morning's dose"), the Care plan labels and dates, connected-source labels, the Insights period label, the chat starter chips and the meal-swap messages. Those texts are in `services/api/app/services/texts_ui.json` (machine translated by `scripts/translate_server_texts.py`); month and weekday names are tables in `texts.py`.

- A reminder stored in English is shown in the chosen language by finding its wording again in the catalog (`texts.retranslate`), so the reviewed translation is used, never a new guess.
- The medicine explanation (written by the model in English) is translated when the page is opened in another language (`services/ui_translate.py`): translation only, numbers must survive or English is kept, and the result is remembered in memory. It is the one place a model translates health text, so a clinician/native reviewer should look at a few.

**Still English:** the printable doctor report and the page the doctor opens, names and notes the person typed, medicine and dish names, error messages that come from the server for rare problems, and any text in a part of the app nobody has opened yet in another language (check with the crawl described in the session notes).
