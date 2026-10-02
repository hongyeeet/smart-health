# AI models: provider and model decisions

Which AI model does each job, how the AI is called, what it costs, and how we keep the output good. This is the written decision for backlog task E0-3 (provider and model choice). Read it with [architecture.md](architecture.md) (where the gateway sits), [memory.md](memory.md) (JEV and the evidence packet) and [rules.md](rules.md) (what the AI may never do).

**Status: proposed by the owner on 2026-10-02; recorded as D-047 and D-048 (Pending).** Prices and model names below come from public search summaries, not Google's or ElevenLabs' own pages. **Confirm every model ID, region and price in the vendor consoles before the gateway is built.**

## 1. The decision in one paragraph

Everything runs through Google Cloud's Vertex AI (one project, one bill, one sign-in) except two things: speech (ElevenLabs) and the JEV decision model (the TypeSafe JEV model). There is no Tencent fallback. Text work uses Claude Sonnet 5.5 served from Vertex AI. Embeddings use Gemini Embedding at 768 dimensions. Fixed text is translated by Google Cloud Translation. Photos (meals and medicine labels) go to Claude Sonnet 5.5, with Gemini 3.6 Flash as the challenger in the accuracy test. Every call goes through one gateway, so a model can be swapped by changing configuration.

## 2. Model per job

| Job | Model | Via | Tasks |
|---|---|---|---|
| Chat, medicine explainer, onboarding chat, nudges, nightly reflection, question phrasing | **Claude Sonnet 5.5** (`claude-sonnet-5-5` on the Anthropic API; confirm the Vertex model ID in Model Garden) | Vertex AI | E16, E4-1, E2-2, E12, E17-1 |
| Doctor brief narrative | **Claude Sonnet 5.5** | Vertex AI | E13-2 |
| Meal photo to estimated macros | **Claude Sonnet 5.5** by default; **Gemini 3.6 Flash** is the challenger | Vertex AI | E7-2 |
| Medicine label reading | Same model as meals | Vertex AI | E3-1 |
| Translation of fixed text (UI strings, refusal and urgent templates) | **Google Cloud Translation** (Advanced, with a glossary so drug names stay unchanged) | Google Cloud | E18-1 |
| Translation of explanations | **Claude Sonnet 5.5**, writing the explanation directly in the target language | Vertex AI | E4-1, E18-1 |
| Embeddings | **`gemini-embedding-001`** at **768 dimensions** | Vertex AI | E4-1, E16-3, E17-1 |
| Text to speech | **ElevenLabs**: `eleven_multilingual_v2` for cached explainers, `eleven_flash_v2_5` for live lines | ElevenLabs API | E4-1, E18-1 |
| Speech to text (voice questions and logging, stretch) | **ElevenLabs Scribe v2**, batch (not realtime) | ElevenLabs API | S3 |
| JEV typed decisions | **The TypeSafe JEV model** | Its own server or API (deployment still to be confirmed, see section 7) | E16-2, E17-1, E13-2 |

**Rejected, and why**
- **Gemma 4** for images: needs our own GPU endpoint (cost while idle, one more service) and gives no proven gain on printed labels.
- **MedGemma, MedSigLIP, TxGemma, HeAR and the other Google health models:** built for medical images, clinical text or drug discovery. Our features are label reading, meal photos and plain-language explanation from cited sources only, and the rules forbid diagnosis. Revisit MedGemma only for the "later" idea of rewriting lab reports in plain language.
- **Hunyuan and Tencent Cloud TTS:** removed by the owner. There is no Tencent fallback.

**Photo model decision rule.** Run both candidates on the same 30 or more label photos and the same meal photos (task E3-3 and E7-2 checks). Keep the winner. The target is at least 90% correct on medicine name and strength for printed labels; anything below 0.85 confidence is shown as "check this" and anything unreadable is `null`. If Gemini 3.6 Flash wins, change `LLM_VISION_MODEL` only.

## 3. Cost control (all of this belongs in the gateway)

| Control | Detail |
|---|---|
| Code, not AI, for facts | Refusals, urgent screens, interaction look-ups and every number in the brief use no model |
| Cap every call | A maximum output length per task, and the evidence packet stays near 3,000 tokens |
| Prompt caching | The fixed system prompt and the safety rules are cached, not re-billed each turn |
| Cache what repeats | Explainers (per medicine and language), TTS audio (by text hash) and translations are generated once |
| Log tokens | `agent_runs.input_tokens`, `output_tokens` and `latency_ms` on every call |
| Daily limits | A per-user and a per-day call cap in the gateway, plus a Google Cloud budget alert and an ElevenLabs usage limit |
| Fail cheap | Timeouts as in rules.md (chat 30 s, vision 45 s, TTS 10 s), at most one retry, never a retry loop |
| Batch the nightly work | Reflection and brief pre-generation can run in batch if the vendor offers a discount |

**Expected cost (indicative, verify):** Claude Sonnet 5 on Vertex is listed at about $2 per million input tokens and $10 per million output tokens. A chat turn is about $0.01, a brief about $0.03, a photo about $0.007. A demo month of about 2,000 mixed calls is roughly $15 to $40. Embeddings cost about $0.15 per million tokens. ElevenLabs is about $0.10 per 1,000 characters (multilingual) and $0.05 (flash) for speech, and about $0.22 per hour for transcription; check whether it bills through a plan with included credits.

## 4. Keeping the output good

- Pin each model version and change it only after re-running the test sets.
- Strict JSON schemas for labels, meals and decisions, validated with Pydantic, one retry, then fail safe (rules.md section 4).
- Test sets: the 40-prompt safety set in four languages (must pass 100% with JEV on and off), the 30-photo label set, and the brief validator against deliberately bad drafts.
- The existing safety layers stay: input and output guards, the evidence-ID validator, and "Estimated" labels. The model is never the last line of defence.
- Translations and explanations in Chinese, Malay and Tamil are labelled unreviewed; no reviewed reference set exists.

## 5. How it is wired

- One gateway per capability in `services/api/app/llm/` (text, vision, embedding, translation, speech) and `app/decision/` (JEV). Screens and services never call a vendor SDK directly (rules.md section 4).
- One Google Cloud sign-in (a service account) covers Claude on Vertex, Gemini embeddings and Cloud Translation. ElevenLabs and JEV have their own keys.
- Environment variables to add to `.env.example` in E0-3 (names are a proposal): `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_REGION`, `GOOGLE_APPLICATION_CREDENTIALS`, `LLM_CHAT_MODEL`, `LLM_VISION_MODEL`, `LLM_VISION_CHALLENGER`, `EMBED_MODEL`, `EMBED_DIM`, `TRANSLATE_GLOSSARY_ID`, `ELEVENLABS_API_KEY`, `ELEVENLABS_TTS_MODEL`, `ELEVENLABS_TTS_LIVE_MODEL`, `ELEVENLABS_STT_MODEL`, `JEV_BASE_URL`, `JEV_API_KEY`, `AI_DAILY_CALL_CAP`, `AI_DAILY_BUDGET_USD`.
- If JEV is off or unreachable, every decision takes the conservative path already defined in [memory.md](memory.md) section 5: refusal template, "not checked", default route. There is no model fallback.

## 6. Privacy and data handling

- Names, NRIC, phone numbers and addresses never go to any model, translator or speech service (rules.md section 3). The evidence packet and the JEV state are de-identified.
- Pick a Singapore or nearby Vertex region if the model is offered there, and check Google's data-use terms for Vertex before real data is sent.
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
| JEV option chosen and the data-handling note recorded | **Partly.** The model is chosen (TypeSafe JEV) and the data-handling note is in section 6. Still to confirm: how it is deployed (hosted service, or run on our own machine) |
| One gateway keeps the OpenJev request and response shape and returns probability and confidence; keys only in settings | To build |
| Smoke test gets an answer from each kind of call; switching JEV off sends every call to the fallback | To build. "Fallback" now means the conservative path (section 5), not a model |

Open items: confirm the Vertex model IDs and region for Claude Sonnet 5.5, confirm Malay and Tamil on both ElevenLabs voice models, confirm the JEV deployment, and run the photo comparison.
