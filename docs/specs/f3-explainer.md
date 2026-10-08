# F3 Medicine explainer: what it is, how it works, what is still open

**Status (2026-10-08): F3 done (approved by Joely).** English page only. Text-to-speech (Listen) and the other languages are not part of F3 for now: Joely will discuss them with the team first.

## 1. What the person sees (screen H6, `/meds/:id`)

Tap a medicine on the Meds page. The page shows, in this order:

1. **What it is for**: one to three plain sentences.
2. **How you take it (from your own label)**: times a day and the label's own words. This is built from the saved schedule and the label text, never from the model.
3. **Common side effects**: three to six short items.
4. **When to tell your doctor**: signs that mean contacting a doctor or pharmacist.
5. **Runs out in about N days** (when there is a supply estimate).
6. **Where this comes from**: links to the web pages used, then "Not an authoritative drug label".
7. **Ask your doctor**: a box; the question is saved to the doctor-question list (`doctor_questions`, origin `user`, status `open`) with the medicine's name in front, so it shows up in the care plan and the doctor brief when those pages exist.

If the product could not be identified (for example the herbal tonic whose label could not be read), the page says "We could not tell exactly what this product is, so we are not guessing" and still offers the question box.

## 2. Why the 250k Medicines file is not used (D-071)

The file has 248,218 rows and is a general medicine list, mostly Indian brand names: anti-infectives 57,503, gastro-intestinal 33,630, pain 32,267, neuro 23,319, cardiac 18,381, anti-diabetic 11,679 (under 5%). It has no supplements or herbal products at all, and Crestor has only 4 rows. So the explanation is written from the medicine's name and label text after a web search. The PRD's earlier plan (retrieve from that file with citations) was replaced on 2026-10-08.

## 3. How an explanation is made

```
open the page -> GET /medications/{id}            the medicine and its saved explanation, if there is one
no explanation -> POST /medications/{id}/explanation
    read the person's own medicine (name, strength, type, label text)
    saved copy for the same name, strength, type and label text?  -> return it (no search)
    daily AI limit reached? -> refuse in plain words
    VertexClient.generate_grounded: Gemini with Google Search grounding, plain-text JSON answer
    code checks (below) -> save in medication_explanations with the web pages used -> return it
```

- **What leaves the machine:** only the medicine's name, strength, type and the label directions (passed through the same name scrubber as the scan answer), plus the instructions. No name, NRIC, address, phone or other person detail. Nothing from the prompt or answer is logged.
- **Why plain text and not forced JSON:** the model cannot be forced into JSON while it searches (a forced-JSON search call timed out in testing), so the prompt asks for one JSON object, code extracts it, and an unreadable answer is retried once, then fails safe.
- **First open takes about 10 to 30 seconds** (measured 16 s for Crestor); after that it is instant. One search at a time per medicine, so a double tap or a page that renders twice costs one search.
- **Cost accounting:** each call is counted in `ai_usage_daily` under `vertex_vision` (the table only allows three providers, and this is the nearest; a separate provider name needs a small migration if wanted) and respects the daily call cap.

## 4. What code checks before anything is saved or shown

| Check | What happens |
|---|---|
| No web page was used | Nothing is saved; the page says it could not find reliable information (HTTP 502) |
| The model says it cannot identify the product | Saved as `not_identified`; no text is shown as fact |
| A sentence gives a dose, a number of tablets or a schedule (`10 mg`, `once a day`, `2 tablets`) | The sentence is dropped |
| A sentence tells the person to stop, skip, double, increase, reduce, change or swap, calls it "safe", says "do not take/avoid", or says it can be taken with something | The sentence is dropped |
| Nothing is left of "what it is for" after that | Failed (`unusable_answer`); not saved |
| Side effects: duplicates, over 80 characters, numbers or advice | Dropped; at most 6 kept |
| Sources | Reliable medical sites (health authorities, hospitals, makers' patient information, established drug-information sites; list `TRUSTED_SITES` in `app/agents/med_explainer.py`) are preferred, and are the only ones shown when any were used. At most 5 |
| The label text on the medicine tells the model to do something | The prompt says label text is data, not instructions |

The explanation is shown with "Not an authoritative drug label" and "This is not medical advice". Supplements and herbal products are described as having limited evidence and not being checked like a prescription medicine. Nothing here compares medicines with each other: interactions are F5.

## 5. Where things are

| What | Where |
|---|---|
| Table | `medication_explanations` (App layer), Alembic `0025_medication_explanations.py` |
| Model client with search | `VertexClient.generate_grounded` in `app/llm/vertex.py` |
| The explainer and its checks | `app/agents/med_explainer.py`; instructions `app/agents/prompts/med_explain.md` (version 1); wiring `app/agents/med_explain_pipeline.py` |
| Database code | `app/services/med_explain_store.py` |
| Routes | `app/api/routers/med_explain.py`: `GET /medications/{id}`, `POST /medications/{id}/explanation[?refresh=true]`, `POST /medications/{id}/questions` |
| Screen | `apps/web/src/features/meds/MedDetail.tsx` (H6); the cards on `MedList.tsx` open it |
| Tests | `tests/unit/test_med_explainer.py` (20), `tests/unit/test_vertex_client.py` (grounded), `tests/db/test_med_explain_route.py` (9) |

## 6. Tried for real on 2026-10-08

- **Crestor 10 mg (prescription):** purpose, five side effects, a doctor-contact paragraph, sources webmd.com, nhs.uk, mayoclinic.org, healthhub.sg. 16 s first time, 0.6 s after.
- **Fish oil (supplement):** said evidence is limited and it is not checked like a prescription medicine; side effects fishy aftertaste, bad breath, burping, heartburn, nausea, loose stools; sources mayoclinic.org, medlineplus.gov and others.
- **Herbal tonic (label not readable):** `not_identified`, nothing explained.
- A first Crestor run cited a newspaper (express.co.uk); the reliable-sources preference was added after that.

## 7. Not built yet, and open

- **Listen and languages** (English, Chinese, Malay, Tamil; the mock-up has a Listen button and an English or Chinese toggle on Metformin). Left out on purpose: Joely will discuss text-to-speech with the team before anything is built. It would need the text-to-speech service and reviewed translations.
- **Refusal template** for "can I stop, double or skip" questions (belongs to the chat, F12).
- **Someone should check the wording clinically.** The explanations are model summaries of web pages, labelled as such, but a pharmacist or doctor has not reviewed the prompt or sample outputs.
- **Refresh:** the page has no "refresh" button; `?refresh=true` on the endpoint makes it again.
- A medicine whose search fails shows "We could not look this up" with a Try again button; nothing is saved.
