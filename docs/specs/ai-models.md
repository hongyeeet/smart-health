# AI models: provider and model decisions

Which AI model does each job, how the AI is called, what it costs, and how we keep the output good. This is the written decision for backlog task E0-3 (provider and model choice). Read it with [architecture.md](architecture.md) (where the gateway sits), [memory.md](memory.md) (JEV and the evidence packet) and [rules.md](rules.md) (what the AI may never do).

**Status: updated 2026-10-05. The text and photo model changed from Claude Sonnet 5.5 to Gemini 3.8 Flash (D-059, accepted by Hong Yi, reported by Joely). It replaces the model choice in D-047; D-048 (768-dimension embeddings) and D-049 (JEV) are unchanged.** The Gemini model names, the embedding size and the Vertex region were tested live on 2026-10-05 (section 10). ElevenLabs details and prices still come from public search summaries, not the vendors' own pages: **confirm them in the vendor consoles before the gateway is built.**

## 1. The decision in one paragraph

Everything runs through Google Cloud's Vertex AI (one project, one bill, one sign-in) except two things: speech (ElevenLabs) and the JEV decision model (the TypeSafe JEV model, hosted on OpenRouter). There is no Tencent fallback. Text work uses **Gemini 3.8 Flash** (`gemini-3.8-flash`) on Vertex AI. Embeddings use Gemini Embedding at 768 dimensions. Fixed text is translated by Google Cloud Translation. Photos (meals and medicine labels) also go to Gemini 3.8 Flash. No Claude model is used, so there is no Anthropic access form or Claude quota to wait for (section 10). Every call goes through one gateway, so a model can be swapped by changing configuration.

## 2. Model per job

| Job | Model | Via | Tasks |
|---|---|---|---|
| Chat, medicine explainer, onboarding chat, nudges, nightly reflection, question phrasing | **Gemini 3.8 Flash** (`gemini-3.8-flash`, tested in this project on 2026-10-05) | Vertex AI | E16, E4-1, E2-2, E12, E17-1 |
| Doctor brief narrative | **Gemini 3.8 Flash**; `gemini-2.5-pro` is the fallback if the brief reads thin | Vertex AI | E13-2 |
| Meal photo to estimated macros | **Gemini 3.8 Flash** | Vertex AI | E7-2 |
| Medicine label reading | Same model as meals (tested on a made-up label with a structured JSON answer: correct) | Vertex AI | E3-1 |
| Translation of fixed text (UI strings, refusal and urgent templates) | **Google Cloud Translation** (Advanced, with a glossary so drug names stay unchanged) | Google Cloud | E18-1 |
| Translation of explanations | **Gemini 3.8 Flash**, writing the explanation directly in the target language (Malay, Tamil and Chinese samples were fluent; a native speaker still has to review the medical wording) | Vertex AI | E4-1, E18-1 |
| Embeddings | **`gemini-embedding-001`** at **768 dimensions** | Vertex AI | E4-1, E16-3, E17-1 |
| Text to speech | **ElevenLabs**: `eleven_multilingual_v2` for cached explainers, `eleven_flash_v2_5` for live lines | ElevenLabs API | E4-1, E18-1 |
| Speech to text (voice questions and logging, stretch) | **ElevenLabs Scribe v2**, batch (not realtime) | ElevenLabs API | S3 |
| JEV typed decisions | **`typesafe/jev-1.13`** (snapshot `typesafe/jev-1.13-20260917`) | OpenRouter: `POST https://openrouter.ai/api/alpha/decisions` (see section 9) | E16-2, E17-1, E13-2 |

**Rejected, and why**
- **Claude Sonnet 5.5 on Vertex (the D-047 choice):** Google asks for a business form and Anthropic's terms before Claude can be enabled, and a new project's Claude quota is zero (every call returned HTTP 429 on 2026-10-05). Gemini needs neither, so the team chose Gemini only (D-059). A Claude model can be added back for one job by changing configuration.
- **Gemma 4** for images: needs our own GPU endpoint (cost while idle, one more service) and gives no proven gain on printed labels.
- **MedGemma, MedSigLIP, TxGemma, HeAR and the other Google health models:** built for medical images, clinical text or drug discovery. Our features are label reading, meal photos and plain-language explanation from cited sources only, and the rules forbid diagnosis. Revisit MedGemma only for the "later" idea of rewriting lab reports in plain language.
- **Hunyuan and Tencent Cloud TTS:** removed by the owner. There is no Tencent fallback.

**Photo model decision rule.** Run `gemini-3.8-flash` on 30 or more label photos and the same meal photos (task E3-3 and E7-2 checks). The target is at least 90% correct on medicine name and strength for printed labels; anything below 0.85 confidence is shown as "check this" and anything unreadable is `null`. If it misses the target, run `gemini-2.5-pro` (set in `LLM_VISION_CHALLENGER`) on the same photos and change `LLM_VISION_MODEL` only if it does better.

## 3. Cost control (all of this belongs in the gateway)

| Control | Detail |
|---|---|
| Code, not AI, for facts | Refusals, urgent screens, interaction look-ups and every number in the brief use no model |
| Cap every call | A maximum output length per task, and the evidence packet stays near 3,000 tokens |
| Prompt caching | The fixed system prompt and the safety rules are cached where Vertex offers context caching for the model (check this for `gemini-3.8-flash`) |
| Cache what repeats | Explainers (per medicine and language), TTS audio (by text hash) and translations are generated once |
| Log tokens | `agent_runs.input_tokens`, `output_tokens` and `latency_ms` on every call |
| Daily limits | A per-user and a per-day call cap in the gateway, plus a Google Cloud budget alert and an ElevenLabs usage limit |
| Fail cheap | Timeouts as in rules.md (chat 30 s, vision 45 s, TTS 10 s), at most one retry, never a retry loop |
| Batch the nightly work | Reflection and brief pre-generation can run in batch if the vendor offers a discount |

**Expected cost (indicative, verify):** the Gemini 3.8 Flash price has not been checked yet; read it from Google's Vertex AI pricing page before the gateway is built and write it here. Flash models are priced below the earlier Claude estimate (about $15 to $40 for a demo month of 2,000 mixed calls), but that is an expectation, not a measured figure. Embeddings cost about $0.15 per million tokens. A Google Cloud budget alert of S$15 a month is already set (section 10). ElevenLabs is about $0.10 per 1,000 characters (multilingual) and $0.05 (flash) for speech, and about $0.22 per hour for transcription; check whether it bills through a plan with included credits.

## 4. Keeping the output good

- Pin each model version and change it only after re-running the test sets.
- Strict JSON schemas for labels, meals and decisions, validated with Pydantic, one retry, then fail safe (rules.md section 4).
- Test sets: the 40-prompt safety set in four languages (must pass 100% with JEV on and off), the 30-photo label set, and the brief validator against deliberately bad drafts.
- The existing safety layers stay: input and output guards, the evidence-ID validator, and "Estimated" labels. The model is never the last line of defence.
- Translations and explanations in Chinese, Malay and Tamil are labelled unreviewed; no reviewed reference set exists.

## 5. How it is wired

- One gateway per capability in `services/api/app/llm/` (text, vision, embedding, translation, speech) and `app/decision/` (JEV). Screens and services never call a vendor SDK directly (rules.md section 4).
- One Google Cloud sign-in (a service account) covers Gemini on Vertex, Gemini embeddings and Cloud Translation. ElevenLabs and JEV have their own keys.
- Environment variables to add to `.env.example` in E0-3 (names are a proposal): `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_REGION`, `GOOGLE_APPLICATION_CREDENTIALS`, `LLM_CHAT_MODEL`, `LLM_VISION_MODEL`, `LLM_VISION_CHALLENGER`, `EMBED_MODEL`, `EMBED_DIM`, `TRANSLATE_GLOSSARY_ID`, `ELEVENLABS_API_KEY`, `ELEVENLABS_TTS_MODEL`, `ELEVENLABS_TTS_LIVE_MODEL`, `ELEVENLABS_STT_MODEL`, `JEV_BASE_URL`, `JEV_MODEL`, `JEV_API_KEY`, `AI_DAILY_CALL_CAP`, `AI_DAILY_BUDGET_USD`.
- If JEV is off or unreachable, every decision takes the conservative path already defined in [memory.md](memory.md) section 5: refusal template, "not checked", default route. There is no model fallback.

## 6. Privacy and data handling

- Names, NRIC, phone numbers and addresses never go to any model, translator or speech service (rules.md section 3). The evidence packet and the JEV state are de-identified.
- **Medicine photos (F2, D-063):** a label photo contains the patient's name and NRIC, so before it goes to Gemini a local, offline OCR blacks out NRIC and FIN numbers, name, birth-date, phone, email and address lines and any line carrying the user's own name. Only that blacked-out copy is sent and stored as the Bronze original. A printed name with no label is the known weak spot. If no text can be found the photo is refused. See [f2-scan.md](f2-scan.md) section 4.
- The tests used Vertex's `global` endpoint, which does not pin the data to one region. Before real data is sent, check Google's data-use terms for Vertex and, if needed, move to a regional endpoint (for example in Singapore) where `gemini-3.8-flash` is offered.
- JEV decisions are sent to OpenRouter and on to TypeSafe. The state is de-identified and kept short. Check OpenRouter's data policy for this model and turn on its no-retention setting if it has one.
- Voice clips go to ElevenLabs only after the person agrees. Transcribed speech passes the same input guard as typed text, and only final, guarded text is sent to text to speech (trust boundary TB-3).

## 7. Embedding size (768) and what it affects

The embedding size is how many numbers describe one piece of text (a medicine fact, a chat summary). We store these in Postgres with pgvector.

| What it affects | Effect |
|---|---|
| **The database column** | `knowledge_chunks.embedding` and `memory_episodes.embedding` are declared with a fixed size, for example `vector(768)`. Both must use the same value. Today `knowledge_chunks` is `vector(1024)` (a placeholder), so it needs one migration |
| **Search index** | pgvector's normal HNSW index only works up to 2,000 dimensions. Gemini Embedding's default of 3,072 cannot be indexed that way, which is why we use 768 |
| **Storage and speed** | A 768-number vector is about 3 KB. 1,536 is 6 KB and 3,072 is 12 KB. Smaller is faster to search and cheaper to store |
| **Quality** | Gemini Embedding is built so smaller sizes keep most of the quality. 768 is one of the sizes Google recommends |
| **Model switch later** | Vectors from different models or sizes cannot be compared. Changing either means re-embedding everything and altering the column and index |
| **API cost** | None. Embeddings are billed by input tokens, not by size |

**Action:** while the tables are empty, change `knowledge_chunks.embedding` to 768 in a new migration (drop the HNSW index, alter the column, recreate the index), set `EMBED_DIM=768` in `.env`, and create `memory_episodes.embedding` at 768 in E1-3. Tell Joely, who owns the migration that created the column. Embed documents and questions with the model's document and query modes.

## 8. Does this satisfy E0-3?

| E0-3 success criterion | State |
|---|---|
| Provider decision recorded in the repo (chat, vision, embeddings) | **Done by this document** |
| JEV option chosen and the data-handling note recorded | **Done.** Hosted on OpenRouter, model `typesafe/jev-1.13`, tested live on 2026-10-02 (section 9). Data-handling note in section 6 |
| One gateway keeps the OpenJev request and response shape and returns probability and confidence; keys only in settings | To build |
| Smoke test gets an answer from each kind of call; switching JEV off sends every call to the fallback | To build. "Fallback" now means the conservative path (section 5), not a model |

Open items: confirm Malay and Tamil on both ElevenLabs voice models, tune the JEV confidence floor (section 9), run the photo accuracy test, and finish the service-account setup in section 10.

## 9. JEV on OpenRouter (tested live on 2026-10-02, D-049)

| Item | What was found |
|---|---|
| Endpoint | `POST https://openrouter.ai/api/alpha/decisions` with `Authorization: Bearer <OpenRouter key>`. The URL, model and key are `JEV_BASE_URL`, `JEV_MODEL` and `JEV_API_KEY` in the private `.env`. The key is never committed |
| Model | `typesafe/jev-1.13`, which resolves to `typesafe/jev-1.13-20260917`. Pin the dated snapshot once tests pass |
| Request | `{ "model", "state", "questions": { "<id>": { "type": "noul" \| "choice" \| "score", "instructions", "criteria" } } }` |
| `noul` (yes or no) | `criteria` is an object, `{"true": "...", "false": "..."}`. The answer is `{"noul": 0.99}`: **a probability of yes only, with no confidence field** |
| `choice` | `criteria` is an object of option to description. The answer has `choice`, `probabilities` for every option, and `confidence` (for example 0.58) |
| `score` | `criteria` must be an **ordered array** of level descriptions (an object is rejected with HTTP 400). The answer has `score` (the chosen index), a `legend`, `probabilities` and `confidence` |
| Limits | 32,000 tokens for state and questions together; output tokens are free |
| Speed and cost | About 0.4 to 0.8 seconds a call; about $0.000014 a call (about $0.042 per million input tokens). Negligible |
| Sample result | "Can I skip my metformin tonight since my sugar looks fine?" gave `med_advice` = 0.99 (correct: this is a medication-advice request) |

**Confidence floor.** `memory.md` defines confidence as 1 minus the normalised entropy, with a starting floor of 0.8. For a yes or no answer that works out as: probability 0.97 or higher (or 0.03 or lower) passes; 0.04 gives 0.76 and does not. The gateway must compute confidence itself for `noul`, because the API does not return it. The 0.8 floor is a starting point: tune it on the 40-prompt safety set (rules.md section 1, rule 14) and write the final value here.

**Failure handling.** A timeout, an HTTP error or an answer below the floor takes the conservative path (memory.md section 5.1). There is no model fallback.

## 10. Vertex AI set-up and live test (2026-10-05, D-059)

Done by Joely with Claude Code on the team's Google Cloud project `smart-health-510414` (billing on, currency SGD).

| Item | State |
|---|---|
| APIs enabled | Vertex AI, Cloud Translation, Cloud Billing Budget (Text-to-Speech was already on) |
| Budget alert | S$15 a month, emails at 50%, 90% and 100% of spend. It warns only; it does not stop spending |
| Service account | `smart-health-backend@smart-health-510414.iam.gserviceaccount.com` created. **Still to do (Joely):** grant it `roles/aiplatform.user` and `roles/cloudtranslate.user`, and create a key for the deployed backend. The tests below ran on Joely's own login, not on this account |
| Endpoint | `global` (`https://aiplatform.googleapis.com/v1/projects/<project>/locations/global/publishers/google/models/<model>:generateContent`) |

**Models that answered a live call in this project:** `gemini-3.8-flash` (also 3.7, 3.6 and 3.5 Flash), `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-3-flash-preview`, `gemini-2.5-pro`, `gemini-2.5-flash`. **Not available (HTTP 404):** `gemini-3-pro`, `gemini-3-flash` (without "preview"), `gemini-2.0-flash`. No 3.x Pro model is available, so `gemini-2.5-pro` is the strongest option.

| Test | Result |
|---|---|
| Medication-pattern analysis (summary of simulated dose data to text) | Useful flags, hypotheses and questions, but one claim had the cause reversed (it said missed doses affect sleep when the summary said poor sleep came before the misses). Every number and causal claim must be checked in code against the summary before it is shown |
| Label image to structured JSON (made-up metformin and atorvastatin labels) | Correct drug, strength, instruction and quantity |
| Explanation in Malay, Tamil and Simplified Chinese | Fluent; the drug name stayed unchanged. Not reviewed by a native speaker |
| Embedding at 768 dimensions | `gemini-embedding-001` and `text-embedding-005` both returned 768 numbers (matches migration 0016) |
| Claude on Vertex | Not usable: every call returned HTTP 429 (quota is zero). Not needed after D-059 |

Test scripts were run from a scratch folder and are not in the repository. A first attempt that used PowerShell's web client got a Google "automated queries" page; calls through `curl` worked.
