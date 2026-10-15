# F3 Medicine explainer: what it is, how it works, what is still open

**Status (2026-10-08): F3 done (approved by Joely).** Updated 2026-10-11: the explanation has **four labelled parts** (prompt version 2, migration 0033), the page says **"Additional information"**, the older layout is made again, and the cost is counted under its own kind of AI call. Fix wave (evening of 2026-10-11): sources are shown once per site, the "no reliable page" answer is a 404 with a plain sentence, and a failed update has its own alert. English page only. Text-to-speech (Listen) and the other languages are not part of F3 for now: Joely will discuss them with the team first.

## 1. What the person sees (screen H6, `/meds/:id`)

Tap a medicine on the Meds page. The page shows, in this order:

1. **What it is for in your diabetes**: one to three plain sentences.
2. **How it works**: one sentence, plain words.
3. **What you may notice**: the common effects, in plain words.
4. **Why timing matters**: why the time of the dose can matter, without any dose or time of day.

These four are the **parts** (`parts` in the database, keys `for_diabetes`, `how_it_works`, `what_you_may_notice`, `why_timing_matters`). A part the pages read do not give is shown as "Not found in the pages we read." It is never filled with a guess.

5. **How you take it (from your own label)**: times a day and the label's own words. This is built from the saved schedule and the label text, never from the model.
6. **Side effects**: three to six short items, the common ones only.
7. **Tell your doctor if…**: signs that mean contacting a doctor or pharmacist.
8. **Refill**: the stock-based or estimated "may run out in about N days" (regular medicines only).
9. **Additional information**: links to the web pages used. Under it, in small grey type: "Not an authoritative drug label". Then "This is not medical advice".
10. **Ask your doctor**: a box; the question is saved to the doctor-question list (`doctor_questions`, origin `user`, status `open`) with the medicine's name in front, so it shows up in the care plan (K12) and the doctor brief.

**An explanation in the older layout** (made before 2026-10-11, no `parts`) still shows, with the note "This was written in an older layout. Update it to see the four short parts." Its "what it is for" text is the old single paragraph. See section 3 for when it is made again.

If the product could not be identified (for example the herbal tonic whose label could not be read), the page says "We could not tell exactly what this product is, so we are not guessing" and still offers the question box.

## 2. Why the 250k Medicines file is not used (D-071)

The file has 248,218 rows and is a general medicine list, mostly Indian brand names: anti-infectives 57,503, gastro-intestinal 33,630, pain 32,267, neuro 23,319, cardiac 18,381, anti-diabetic 11,679 (under 5%). It has no supplements or herbal products at all, and Crestor has only 4 rows. So the explanation is written from the medicine's name and label text after a web search. The PRD's earlier plan (retrieve from that file with citations) was replaced on 2026-10-08.

## 3. How an explanation is made

```
open the page -> GET /medications/{id}            the medicine and its saved explanation, if there is one
no explanation -> POST /medications/{id}/explanation
    read the person's own medicine (name, strength, type, label text)
    saved copy for the same name, strength, type and label text, in the four-part layout?  -> return it (no search)
    saved copy in the older layout, and the database has the `parts` column (migration 0033)?  -> make it again
    daily AI limit for text reached (vertex_generate)? -> refuse in plain words
    VertexClient.generate_grounded: Gemini with Google Search grounding, plain-text JSON answer
    code checks (below) -> save in medication_explanations with the web pages used and the four parts -> return it
```

- **What leaves the machine:** only the medicine's name, strength, type and the label directions (passed through the same name scrubber as the scan answer), plus the instructions. No name, NRIC, address, phone or other person detail. Nothing from the prompt or answer is logged.
- **Why plain text and not forced JSON:** the model cannot be forced into JSON while it searches (a forced-JSON search call timed out in testing), so the prompt asks for one JSON object, code extracts it, and an unreadable answer is retried once, then fails safe.
- **First open takes about 10 to 30 seconds** (measured 16 s for Crestor); after that it is instant. One search at a time per medicine, so a double tap or a page that renders twice costs one search.
- **Cost accounting:** each call is counted in `ai_usage_daily` under **`vertex_generate`** (text the person sees; this provider was added by migration 0034 on 2026-10-11). It was counted under `vertex_vision` before that, and older rows are not moved. It respects its own daily cap, `AI_CAP_VERTEX_GENERATE` (default 500). A refused call returns HTTP 429 with the sentence "The daily limit for looking things up has been reached. Please try again tomorrow."
- **Regenerate rule:** the explanation is kept until the medicine's name, strength, type or label text changes. It is also made again when the saved one is in the older layout and the database can keep the four parts. `?refresh=true` makes it again at any time.

## 4. What code checks before anything is saved or shown

| Check | What happens |
|---|---|
| No web page was used, or the answer had nothing usable in it | Nothing is saved; the page says "We could not find a reliable page for this medicine yet. Please ask your pharmacist." (HTTP 404). An answer in a shape that cannot be read gives HTTP 502 with "We could not read the information for this medicine just now" |
| The model says it cannot identify the product | Saved as `not_identified`; no text is shown as fact |
| A sentence gives a dose, a number of tablets or a schedule (`10 mg`, `once a day`, `2 tablets`) | The sentence is dropped |
| A sentence tells the person to stop, skip, double, increase, reduce, change or swap, calls it "safe", says "do not take/avoid", or says it can be taken with something | The sentence is dropped |
| Nothing is left of "what it is for" after that | Failed (`unusable_answer`); not saved |
| Each of the other three parts | Sentences that break the rules above are dropped; a part with nothing left is saved empty and shown as "Not found in the pages we read" |
| Side effects: duplicates, over 80 characters, numbers or advice | Dropped; at most 6 kept |
| Sources | Reliable medical sites (health authorities, hospitals, makers' patient information, established drug-information sites; list `TRUSTED_SITES` in `app/agents/med_explainer.py`) are preferred, and are the only ones shown when any were used. At most 5. Shown once per site, by the site's name (`app/services/web_sources.py`); a link only where there is a page |
| The label text on the medicine tells the model to do something | The prompt says label text is data, not instructions |

The explanation is shown with "Additional information" and "Not an authoritative drug label". Supplements and herbal products are described as having limited evidence and not being checked like a prescription medicine. Nothing here compares medicines with each other: interactions are F5.

## 5. Where things are

| What | Where |
|---|---|
| Table | `medication_explanations` (App layer), Alembic `0025_medication_explanations.py`; the four parts in `parts` (jsonb), `0033_medication_explanation_parts.py` |
| Model client with search | `VertexClient.generate_grounded` in `app/llm/vertex.py` |
| The explainer and its checks | `app/agents/med_explainer.py`; instructions `app/agents/prompts/med_explain.md` (**version 2**, four parts; version 1 before 2026-10-11); wiring `app/agents/med_explain_pipeline.py` |
| Database code | `app/services/med_explain_store.py` (reads and writes `parts` only when the column exists) |
| Routes | `app/api/routers/med_explain.py`: `GET /medications/{id}`, `POST /medications/{id}/explanation[?refresh=true]`, `POST /medications/{id}/questions` |
| Screen | `apps/web/src/features/meds/MedDetail.tsx` (H6); the cards on `MedList.tsx` open it |
| Tests | `tests/unit/test_med_explainer.py` (20), `tests/unit/test_med_explain_store.py` (added 2026-10-11), `tests/unit/test_vertex_client.py` (grounded), `tests/db/test_med_explain_route.py` (9) |

## 6. Tried for real on 2026-10-08

- **Crestor 10 mg (prescription):** purpose, five side effects, a doctor-contact paragraph, sources webmd.com, nhs.uk, mayoclinic.org, healthhub.sg. 16 s first time, 0.6 s after. (This run was before the four parts existed.)
- **Fish oil (supplement):** said evidence is limited and it is not checked like a prescription medicine; side effects fishy aftertaste, bad breath, burping, heartburn, nausea, loose stools; sources mayoclinic.org, medlineplus.gov and others.
- **Herbal tonic (label not readable):** `not_identified`, nothing explained.
- A first Crestor run cited a newspaper (express.co.uk); the reliable-sources preference was added after that.

**Not run on 2026-10-11:** the four-part layout has not been generated against the live model in this pass.

## 7. Not built yet, and open

- **Listen and languages** (English, Chinese, Malay, Tamil; the mock-up has a Listen button and an English or Chinese toggle on Metformin). Left out on purpose: Joely will discuss text-to-speech with the team before anything is built. It would need the text-to-speech service and reviewed translations.
- **Refusal template** for "can I stop, double or skip" questions (belongs to the chat, F12).
- **Someone should check the wording clinically.** The explanations are model summaries of web pages, labelled as such, but a pharmacist or doctor has not reviewed the prompt (version 2) or sample outputs. The four-part wording is new and not reviewed.
- **Refresh button:** the page has no "refresh" button; `?refresh=true` on the endpoint makes it again.
- A medicine whose search fails shows "We could not look this up" with a Try again button; nothing is saved. When an explanation already exists and an update fails, the alert reads "We could not update this information" (button "Update this information"). Found with no reliable page: "We could not find a reliable page for this medicine yet" (404). Both are plain sentences, not codes.
- Whether migration 0033 is applied to the shared database is not verified. Until it is, the four parts are neither read nor written, and the page shows the older layout.
