# AI models: provider and model decisions

Which AI model does each job, how the AI is called, what it costs, and how we keep the output good. This is the written decision for backlog task E0-3 (provider and model choice). Read it with [architecture.md](architecture.md) (where the gateway sits), [memory.md](memory.md) (JEV and the evidence packet) and [rules.md](rules.md) (what the AI may never do).

**Status: updated 2026-10-15 against the code (`services/api/app/llm/gateway.py`, `app/llm/vertex.py`, `app/core/config.py`, `app/services/usage.py`).** The text below was first written on 2026-10-05.

**Status of the choice (2026-10-05). The text and photo model changed from Claude Sonnet 5.5 to Gemini 3.8 Flash (D-059, accepted by Hong Yi, reported by Joely). It replaces the model choice in D-047; D-048 (768-dimension embeddings) and D-049 (JEV) are unchanged.** The Gemini model names, the embedding size and the Vertex region were tested live on 2026-10-05 (section 10). Speech (ElevenLabs) was dropped on 2026-10-16: the product has no text to speech and no voice input.

**What the code does today (2026-10-15).** Built: Gemini 3.8 Flash for chat, photos, wording and the translation of model-written explanations (`app/services/ui_translate.py`, through the gateway); `gemini-embedding-001` at 768 dimensions for food search; `gemini-2.5-flash-image` for dish pictures; JEV on OpenRouter. Fixed screen text is translated from a reviewed catalogue (`app/services/texts.py`, `texts_ui.json`), not by a live call. **Not found in the code:** Google Cloud Translation calls; they remain planned (their rows below are the decision, not a built feature). The `gemini-2.5-pro` challenger is set in configuration but no call site uses it in this pass.

## 1. The decision in one paragraph

Everything runs through Google Cloud's Vertex AI (one project, one bill, one sign-in) except one thing: the JEV decision model (the TypeSafe JEV model, hosted on OpenRouter). There is no Tencent fallback. Text work uses **Gemini 3.8 Flash** (`gemini-3.8-flash`) on Vertex AI. Embeddings use Gemini Embedding at 768 dimensions. Fixed text is translated by Google Cloud Translation. Photos (meals and medicine labels) also go to Gemini 3.8 Flash. Dish pictures for the Meal suggestions page are made by `gemini-2.5-flash-image` (Gemini 3.8 Flash first writes a one-sentence description of the dish; see [menu.md](menu.md)). No Claude model is used, so there is no Anthropic access form or Claude quota to wait for (section 10). Every call goes through one gateway, so a model can be swapped by changing configuration.

## 2. Model per job

| Job | Model | Via | Tasks |
|---|---|---|---|
| Chat, medicine explainer, onboarding chat, nudges, nightly reflection, question phrasing | **Gemini 3.8 Flash** (`gemini-3.8-flash`, tested in this project on 2026-10-05) | Vertex AI | E16, E4-1, E2-2, E12, E17-1 |
| Doctor brief narrative | **Gemini 3.8 Flash**; `gemini-2.5-pro` is the fallback if the brief reads thin | Vertex AI | E13-2 |
| Meal photo to estimated macros | **Gemini 3.8 Flash** | Vertex AI | E7-2 |
| Medicine label reading | Same model as meals (tested on a made-up label with a structured JSON answer: correct) | Vertex AI | E3-1 |
| Translation of fixed text (UI strings, refusal and urgent templates) | **Google Cloud Translation** (Advanced, with a glossary so drug names stay unchanged) | Google Cloud | E18-1 |
| Translation of explanations | **Gemini 3.8 Flash**, writing the explanation directly in the target language (Malay, Tamil and Chinese samples were fluent; a native speaker still has to review the medical wording) | Vertex AI | E4-1, E18-1 |
| Dish pictures (Meal suggestions) | **`gemini-2.5-flash-image`** (`FOOD_IMAGE_MODEL`; the only image model this project can reach, checked 2026-10-14: Imagen and the Gemini 3 image models answer 404). Gemini 3.8 Flash writes the one-sentence description first. One picture per dish, made once and stored | Vertex AI | menu.md |
| Embeddings | **`gemini-embedding-001`** at **768 dimensions** (built: food search, `app/agents/food.py`) | Vertex AI | E4-1, E16-3, E17-1 |
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
| Daily limits | **Built** (`app/services/usage.py`, counted in `ai_usage_daily`): one cap per kind of call, each counted and blocked on its own, set in `app/core/config.py` as `AI_CAP_VERTEX_VISION` 300 (photo and label reads), `AI_CAP_VERTEX_GENERATE` 500 (text the person sees), `AI_CAP_VERTEX_IMAGE` 60 (dish pictures), `AI_CAP_VERTEX_EMBED` 2000 (embeddings, fall back to text search) and `AI_CAP_JEV` 500 (JEV decisions). A provider with no cap of its own uses `AI_DAILY_CALL_CAP` (500). `AI_DAILY_BUDGET_USD` (5.0) is checked per provider against its own reported cost (only JEV reports cost). When a cap is reached the call is refused and the caller takes its conservative path. There is also a Google Cloud budget alert |
| Fail cheap | Timeouts as in rules.md (chat 30 s, vision 45 s, TTS 10 s; `LLM_TIMEOUT_S` is 45 in the code), at most one retry (`LLM_MAX_RETRIES` is 1), never a retry loop |
| Batch the nightly work | Reflection and brief pre-generation can run in batch if the vendor offers a discount |

**Expected cost (indicative, verify):** the Gemini 3.8 Flash price has not been checked yet; read it from Google's Vertex AI pricing page before the gateway is built and write it here. Flash models are priced below the earlier Claude estimate (about $15 to $40 for a demo month of 2,000 mixed calls), but that is an expectation, not a measured figure. Embeddings cost about $0.15 per million tokens. A Google Cloud budget alert of S$15 a month is already set (section 10). 

## 4. Keeping the output good

- Pin each model version and change it only after re-running the test sets.
- Strict JSON schemas for labels, meals and decisions, validated with Pydantic, one retry, then fail safe (rules.md section 4).
- Test sets: the 40-prompt safety set in four languages (must pass 100% with JEV on and off), the 30-photo label set, and the brief validator against deliberately bad drafts.
- The existing safety layers stay: input and output guards, the evidence-ID validator, and "Estimated" labels. The model is never the last line of defence.
- Translations and explanations in Chinese, Malay and Tamil are labelled unreviewed; no reviewed reference set exists.

## 5. How it is wired

- The gateway is `services/api/app/llm/gateway.py` (vision and text with a validated JSON answer, and dish pictures through `generate_image`), with `app/llm/vertex.py` (the Vertex HTTP client with retry for 429 and 5xx, and web-grounded calls for the medicine explainer and clash checker), `app/llm/chat.py` (chat) and `app/llm/jev.py` (JEV). Embeddings are called from `app/agents/food.py` with the same Vertex key. There is no speech or Cloud Translation gateway in the code yet (see the status note below). Screens and services never call a vendor SDK directly (rules.md section 4).
- One Google Cloud sign-in (a service account) covers Gemini on Vertex, Gemini embeddings and Cloud Translation. JEV has its own key.
- Environment variables the code reads today: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_REGION`, `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_API_KEY` (Vertex AI express-mode key, used when no service-account file is set), `LLM_CHAT_MODEL`, `LLM_VISION_MODEL`, `LLM_VISION_CHALLENGER`, `LLM_TIMEOUT_S`, `LLM_MAX_RETRIES`, `FOOD_IMAGE_MODEL`, `JEV_BASE_URL`, `JEV_MODEL`, `JEV_TIMEOUT_S`, `OPEN_ROUTER_API_KEY` (or `OPENROUTER_API_KEY`) for JEV, `AI_CAP_VERTEX_VISION`, `AI_CAP_VERTEX_GENERATE`, `AI_CAP_VERTEX_IMAGE`, `AI_CAP_VERTEX_EMBED`, `AI_CAP_JEV`, `AI_DAILY_CALL_CAP`, `AI_DAILY_BUDGET_USD`. Still proposals (not read by the code): `EMBED_MODEL`, `EMBED_DIM` (the model name and 768 are fixed in `app/agents/food.py`), `TRANSLATE_GLOSSARY_ID`.
- If JEV is off or unreachable, every decision takes the conservative path already defined in [memory.md](memory.md) section 5: refusal template, "not checked", default route. There is no model fallback.

## 6. Privacy and data handling

- Names, NRIC, phone numbers and addresses never go to any model, translator or speech service (rules.md section 3). The evidence packet and the JEV state are de-identified.
- **Medicine photos (F2, D-063):** a label photo contains the patient's name and NRIC, so before it goes to Gemini a local, offline OCR blacks out NRIC and FIN numbers, name, birth-date, phone, email and address lines and any line carrying the user's own name. Only that blacked-out copy is sent and stored as the Bronze original. A printed name with no label is the known weak spot. If no text can be found the photo is refused. See [f2-scan.md](f2-scan.md) section 4.
- The tests used Vertex's `global` endpoint, which does not pin the data to one region. Before real data is sent, check Google's data-use terms for Vertex and, if needed, move to a regional endpoint (for example in Singapore) where `gemini-3.8-flash` is offered.
- JEV decisions are sent to OpenRouter and on to TypeSafe. The state is de-identified and kept short. Check OpenRouter's data policy for this model and turn on its no-retention setting if it has one.

## 7. Embedding size (768) and what it affects

The embedding size is how many numbers describe one piece of text (a medicine fact, a chat summary). We store these in Postgres with pgvector.

| What it affects | Effect |
|---|---|
| **The database column** | `knowledge_chunks.embedding` and `memory_episodes.embedding` are declared with a fixed size, for example `vector(768)`. Both must use the same value. `knowledge_chunks` was a `vector(1024)` placeholder and was changed to 768 by migration `0016_embedding_768` |
| **Search index** | pgvector's normal HNSW index only works up to 2,000 dimensions. Gemini Embedding's default of 3,072 cannot be indexed that way, which is why we use 768 |
| **Storage and speed** | A 768-number vector is about 3 KB. 1,536 is 6 KB and 3,072 is 12 KB. Smaller is faster to search and cheaper to store |
| **Quality** | Gemini Embedding is built so smaller sizes keep most of the quality. 768 is one of the sizes Google recommends |
| **Model switch later** | Vectors from different models or sizes cannot be compared. Changing either means re-embedding everything and altering the column and index |
| **API cost** | None. Embeddings are billed by input tokens, not by size |

**Done:** migration `0016_embedding_768` changed `knowledge_chunks.embedding` to 768, and the later migrations create the other embedding columns at 768 (for example `0021_learning_loop`). Embed documents and questions with the model's document and query modes.

## 8. Does this satisfy E0-3?

| E0-3 success criterion | State |
|---|---|
| Provider decision recorded in the repo (chat, vision, embeddings) | **Done by this document** |
| JEV option chosen and the data-handling note recorded | **Done.** Hosted on OpenRouter, model `typesafe/jev-1.13`, tested live on 2026-10-02 (section 9). Data-handling note in section 6 |
| One gateway keeps the OpenJev request and response shape and returns probability and confidence; keys only in settings | **Built** (`app/llm/jev.py`, `app/llm/gateway.py`; keys in settings) |
| Smoke test gets an answer from each kind of call; switching JEV off sends every call to the fallback | Not verified in this pass. "Fallback" now means the conservative path (section 5), not a model |

Open items: tune the JEV confidence floor (section 9), run the photo accuracy test, and finish the service-account setup in section 10.

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
