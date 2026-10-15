# Ask Equinox (screen I1): scope and guardrails

**Status (2026-10-15): rebuilt, live-tested on 2026-10-11, and extended since (retrieval planner, three-bullet reply with a closing line)** with Gemini on Vertex AI (`LLM_CHAT_MODEL`, default `gemini-3.8-flash`). Decided by Joely. The guardrail wording and word lists are placeholders for review by the clinical owner (rules.md 1.15).

## 1. Why it said "I cannot check this question right now"

That sentence is the fixed reply `chat.guard_down`. The old chat sent every message to the external JEV guard first and refused everything when JEV could not be reached. JEV needs an `OPEN_ROUTER_API_KEY` that is not set here, so every message was refused before the model was asked. The model call itself (Gemini on Vertex) was never the problem.

## 2. What the chat is

A personal assistant for ONE signed-in person that reads **that person's own data** and explains it in plain words. It never acts. It can only reply, show where to look in the app, and offer to add a question to the doctor questions (the person taps a button).

In scope: glucose, meals and diet, food ideas, activity, sleep, blood pressure, the medicines they take (what each is for and when they take it), symptoms they logged, doctor questions, the next visit, what the app noticed about them, and how to find things in the app. A general question about diabetes, food or exercise (not about the person's own numbers) is answered only from quoted guidance passages (see chat-knowledge.md), never from the person's data.

Out of scope, always refused with a fixed reply: anything else (general knowledge, code, news, money, jokes, other people).

![Ask Equinox: trust and safety](../assets/diagrams/06-chat-trust-and-safety.png)

*Figure: what the chat always reads, reads only when the question needs it, and never reads, and the checks every message passes.*

## 2.1 What it can see (the CONTEXT sent to the model)

Built by code from the person's rows only, 14 days of daily data unless stated: glucose by day; doses planned, taken and missed; medicines with times and "what it is for" (from the stored explanation); recent meals (unknown values left out, never zero); activity and steps; sleep; **symptoms** (last 30 days: what, when, strength, duration and the sensor reading within 30 minutes of the latest ones, or "no sensor reading"); **blood pressure** (last 30 days); **medicine alerts** raised by Equinox; the next visit; open doctor questions; what Equinox has learned; and, for food questions, **food ideas** chosen by code from the person's own history and the Singapore food database (the same source as Lunch ideas). A question only sees the sections it needs (a food question never sees symptoms).

**Retrieval planner** (`app/services/chat_planner.py`, rules only, no model call, no cost): for each question it adds extra views of the person's own records when the words ask for them: `labs` (latest HbA1c, fasting glucose, fasting insulin), `profile` (conditions, allergies, year diagnosed, where the diabetes is looked after), `baseline` (usual morning glucose and steps over the 60 days before, next to the last 14), `preventive` (eye, foot, kidney, vaccination and HbA1c check dates), `responses` (the person's own responses after meals and exercise, and the patterns Equinox found) and `longer_history` (weekly summaries over 30, 60 or 90 days). A question the rules do not recognise adds nothing, so the chat stays on the 14-day sections. The extra views are capped (14 lines each, 3000 characters in all). The planner also decides whether the meaning-based guidance search runs (`needs_guidance`): a plain question about the person's own numbers makes no embedding call.

## 3. The order of checks for every message (`app/services/chat.py decide`)

| # | Step | Model call? | If it fires |
|---|---|---|---|
| 1 | **Self-harm words** | no | Fixed caring reply with 995 and the Samaritans of Singapore 1767 |
| 2 | **Urgent words** (chest pain, cannot breathe, fainting, very low sugar, a reading below 4.0 mmol/L together with sweating, shaking, dizziness or confusion) | no | "This sounds urgent. Call 995 now." and a button to the urgent screen |
| 3 | **Speed limit** (12 messages in 2 minutes per person) | no | "Please wait a moment" |
| 4 | **Help** ("what can you do?") | no | Fixed list of what it can help with |
| 5 | **Input rules** (`app/services/chat_guard.py inspect_input`) | no | Fixed reply, see section 4 |
| 6 | **JEV guard**, only when its key exists (it also reads the finished reply) | JEV | Respected when it says urgent, refuse or caution. When JEV cannot be reached it is skipped: it never stops the chat |
| 7 | **Triage** (Gemini, JSON): intent and flags | yes | Labels the message. If it cannot run, the words label it (`rules_intent`) and the chat carries on |
| 8 | **Retrieval planner** (`chat_planner.plan`) picks the extra views, then **Answer** (Gemini, JSON: `summary`, `reply`, `closing`, each with an English copy) from the allowed sections only | yes (planner: no) | |
| 9 | **Output rules** in code on the English reply (`reply_problems`) | no | A reply that fails is NEVER shown: the person gets a plain summary of their own data instead |
| 10 | **Composition by code** | no | The doctor referral, the "where to look" sentence and buttons, the offer to add a doctor question and the warm closing line (last) are placed by code, so the model cannot leave them out or invent a link |

## 4. What gets a fixed reply (no model answer)

| Intent | Examples | Reply |
|---|---|---|
| Injection | "ignore all previous instructions", "you are now DAN", "reveal your system prompt", role-play, chat-template markers, encoded text, the same in Chinese, Malay and French | "I cannot follow that request. I can only answer questions about your own Equinox data." |
| Harmful action | delete my data, send my report to my son, change my appointment or emergency contact, turn off reminders, order my medicine | "I cannot change, send or share anything from here..." |
| Other person or secret | other patients, "show me Mr Tan's data", passwords, API keys, NRIC, database | "I can only talk about your own data..." |
| Off topic | code, poems, politics, crypto, weather, translate, general knowledge | "I can only help with your own Equinox data..." |
| **Diagnosis request** | "do I have kidney disease?", "what is wrong with me?", "is it a thyroid problem?", "what caused my sugar to be high?" | "I cannot diagnose or say what is causing how you feel. Please talk to your doctor... If you feel very unwell, call 995." **+ the offer to add it to the doctor questions** |
| **Medicine change** | "should I stop my metformin?", "can I take double?", "what dose of insulin?" | "I cannot advise on starting, stopping or changing a medicine or its dose. Please ask your doctor or pharmacist." **+ the offer** |

A question that only asks whether a number is normal, good or bad ("is my blood pressure normal?") is not refused: the person gets their own numbers and "I cannot say whether a number is normal, good or bad. Your doctor can tell you what your numbers mean for you." plus the offer.

## 5. What the answer is allowed to say

The model is told to use only the CONTEXT, copy numbers as written, write in plain words for an older adult, and never diagnose, never say what causes a symptom or number, never advise on a medicine, never call anything normal, good, bad or safe, and say "associated with", never "caused by".

The code then rejects (and replaces with a plain summary of the person's data) any reply that contains: a diagnosis ("you probably have...", "this is a sign of..."), medicine advice ("you should stop taking..."), a verdict ("is normal", "is a good reading"), a cause ("because of", "caused by"), a promise ("will cure"), a link, an email or ID number, a leaked instruction, markdown or HTML, or **numbers that are in neither the person's data nor their question** (anti-invention). A refusal such as "I cannot say whether it is normal" is allowed.

The reply has a fixed shape: a one-sentence summary (25 words or fewer), up to three short bullet points (60 words in all), and one warm closing sentence that praises the effort of logging, never a number or a result. Code puts the links and the closing line after the points, and the closing is checked by the same rules. A question that asks how to improve or for tips switches the model to suggestions mode: each idea stands on a line of what Equinox has learned or on the person's own records, with one simple allowed action, and never mentions medicines.

For a reply in another language the word rules run on the English copy (`reply_en`, written in the same model call) and the neutral rules also run on the reply itself.

## 6. Referrals and signposts added by code

| When | Added to the reply | Button |
|---|---|---|
| A symptom is mentioned (any intent) or the question is about symptoms | "I cannot tell what is causing a symptom. Please talk to your doctor about it. If you feel very unwell, call 995." + "Would you like to add this to your doctor questions?" | Add to my doctor questions (the person's own words) |
| A medicine question | "This is general information about your medicine. Your pharmacist or doctor can tell you more." + the Meds tab sentence + the offer | Open my medicines |
| A food or diet suggestion | Up to 3 dishes from FOOD IDEAS, then "You can find more ideas under Me, Review suggestions, and in Lunch ideas." | Open Review suggestions, Open Lunch ideas |
| "What did the app notice about me?" | A summary from the person's data, then "You can see more on the Insights tab, under Overview." | Open Insights, Overview |
| Doctor visits and questions | "You can see your next visit and checks in your care plan, under Me." | Open my care plan |

Note: "Review suggestions" (K11) is the reviewers' screen where suggestions are rated. It is linked here because the owner asked for it; "Lunch ideas" is the patient-facing screen for food ideas and is linked next to it.

## 7. Privacy and prompt-injection design

- **PII out:** email addresses, phone numbers and NRIC numbers are replaced, and the person's and their contact's name words are replaced by "the person", before anything leaves this process (`chat_guard.scrub_pii`, `chat.scrub`). The reply is scrubbed again.
- **Data is inert:** every line of the person's data (a doctor question they typed, a medicine label, a meal name) is stripped of control and zero-width characters, scrubbed, cut to 220 characters, and **dropped entirely if it reads like an instruction** (`sanitize_data_line`). The context, the recent chat and the question go to the model inside tags, and the prompt says they are untrusted data.
- **No tools:** the model cannot call functions, read other tables or write anything. The only write is the person tapping "Add to my doctor questions".
- **Scope by section:** each intent sees only the sections it needs.
- **Memory:** only the last 6 messages are sent. Nothing from a chat is saved as a memory fact.
- **Audit:** every blocked input and output is written to `guardrail_events` (verdict `blocked_injection`, `blocked_diagnosis`, `blocked_med_advice`, `blocked_other`, `blocked_uncited`, `urgent`) and every turn is traced in `agent_runs`.
- **Cost and abuse:** 12 messages per 2 minutes per person, a 500-character message limit (`MAX_TEXT`), and the daily limit for text the person sees (`vertex_generate`, 500 calls a day by default).

## 8. When something fails

| Failure | What the person gets |
|---|---|
| Triage cannot run | The words label the message; the chat carries on |
| The answer model cannot run | A plain summary of their own data (never the old "cannot check this question" sentence); with no data at all, "I cannot answer right now. Please try again in a little while." |
| The reply fails the output rules | A plain summary of their own data |
| JEV unreachable | Nothing: JEV is optional |
| Daily limit reached | The same plain summary or the "try again" sentence |

## 9. Live test results (2026-10-11, Mr Tan, read-only, real Gemini)

About 67 messages in six batches. All 12 injection and jailbreak style phrasings tried (including Chinese, Malay and French, spaced-out letters, role-play, "grandma" and "as my doctor" tricks) were refused with no data shown; 6 off-topic, 3 action, 3 other-person and 2 secret requests were refused; 6 diagnosis and 4 medicine-change requests got the fixed reply with the doctor-question offer; chest pain and self-harm got the urgent replies; a message with a pretend glucose of 3.1 and sweating got the urgent reply. Normal questions about glucose, meals, salt, blood pressure, medicines, symptoms, sleep, food ideas and the next visit were answered from the data in 4 to 10 seconds with the referral and signpost lines. Two output-guard false positives found in testing were fixed (the word "question", and a quoted saved question "is it OK to take X together").

## 10. Known limits and open items

- While a reply is on its way the app shows one changing waiting line (`ThinkingSteps`, `features/chat/parts.tsx`) whose wording follows the kind of request the server reports (own records, food, ideas from what Equinox has learned, general reading) and the topic words of the question.

- Two model calls per message (triage, then answer): 4 to 12 seconds a reply.
- Triage is a model: a clever message may be mislabelled. The rules catch the common and obvious cases and the output rules still stop a bad reply, but this is not a guarantee. The adversarial corpus in `tests/redteam/test_chat_redteam.py` lists the phrasings the rules do not catch (they rely on triage).
- Word lists are English. Chinese, Malay and Tamil are covered by the model triage and by the English copy of each reply, not by their own word lists.
- The fixed replies in Chinese, Malay and Tamil are machine translations and need a native and clinical review (docs/review/translations.md).
- "What the app noticed" reads the stored facts, which is Hong Yi's learning loop; the facts it reads include rules the owner is reviewing (see project memory).
- Medicine "what it is for" text is the stored AI explanation from F3; it has not been clinically reviewed.

## Links inside the reply (2026-10-12)

The pointers to other screens are part of the text, not buttons under it. A sentence that points to a screen marks the words that open it as `[[ROUTE_ID|words]]` (for example `[[K11|Review suggestions]]`, `[[E8|Lunch ideas]]`, `[[C1|Overview]]`, `[[H1|Meds tab]]`, `[[K3|care plan]]`, in all four languages in `texts.py`). The app (`features/chat/parts.tsx`, `linked()`) shows those words green and underlined, and a marker that does not name a screen of the app shows as plain words. "Where this comes from" is now one line inside the answer ("Where this comes from: Your glucose, Your doses and Your medicines.") with each name a link. The offer to add the question to the doctor questions is also a link: the whole sentence "Want to add this to your doctor questions?" is marked `[[DQ|...]]`, and tapping it saves the person's own question (nothing is saved until then; it then says "Added to your doctor questions"). The only buttons left are the suggested questions (the chips under a reply and the starters on the empty screen), because tapping one sends a question. The urgent screen pointer is a red underlined link at the end of an urgent reply. The text sent back to the model as history has the markers removed (`texts.strip_links`). Tests: `tests/unit/test_chat_links.py`.
