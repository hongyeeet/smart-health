# Ask Equinox: guidance reading (knowledge base)

Status: spec only. Nothing is loaded and no loader exists yet. The chat already reads from this table if it has rows (see `passages()` in
`services/api/app/services/chat.py`), and quotes what it finds as general information, never as something about the person.

## What the chat does with it

For a question that asks for general reading ("what is a glucose spike", "why does sleep matter"), the chat turns the question into a
meaning vector and takes the nearest chunks. If there are no vectors, no embedding is allowed (daily cap `AI_CAP_VERTEX_EMBED`), or anything
fails, it falls back to a word search over the same chunks. Plain questions about the person's own numbers do not search at all.
The model sees each chunk as quoted text with its document title in brackets, and is told it is general information.

## Sources that would be acceptable

Only text we may legally copy and that a clinician is willing to stand behind:

- Singapore Ministry of Health and Health Promotion Board public patient pages (Healthier SG, diabetes, healthy diet), if their terms allow reuse.
- National and international patient-education pages with a clear open licence or written permission (record the licence).
- Text written by our own clinical adviser for this app.

Not acceptable: forum posts, blogs, product pages, anything without a licence we can record, anything that gives a dose, tells the reader to
change a medicine, diagnoses, or says a number is "normal" or "bad". Plain educational wording only.

## How to prepare it

1. Pick a source page and copy the text into a working file (not into the database). Keep the source organisation, URL, licence, version and the date retrieved.
2. Remove anything that is advice for a particular person, a dose, a medicine change, or a diagnosis. Keep the explanations.
3. Split into chunks of about 150 to 300 words, one idea each, cut at paragraph ends. Number them in order (`seq`).
4. Embed each chunk with `gemini-embedding-001` at 768 dimensions (the size of `knowledge_chunks.embedding`). Use the same call as `services/api/app/services/chat.py embed_question`, with document-style input, and count it under the `vertex_embed` cap.
5. A clinician reads every chunk and signs it off (name and date written in the review note below) before the document is switched on.
6. Load with `active = false`, check a few questions with `services/api/scripts/chat_before_after.py`, then set `active = true`.

## Review step (clinician)

For each document, the reviewer confirms: the source and licence are right; no chunk gives a dose or a medicine change; no chunk diagnoses or
gives a verdict on a number; the wording is plain; Singapore context fits. The review note (reviewer, date, outcome, any chunks removed) is kept
in the working file next to the source text (the table has no notes column, and this spec does not add one). A document that is not signed off stays `active = false`.

## Tables and columns (already in the database; no migration needed)

`knowledge_documents`: `id`, `kind` (`drug`, `lifestyle`, `hypo_guidance`, `condition_education`, `food`), `title` (shown to the person as the source label, keep it short), `source_org`, `source_url`, `licence`, `locale`, `version`, `retrieved_on`, `active`.

`knowledge_chunks`: `id`, `document_id`, `seq`, `content` (the chunk text, the first 330 characters are quoted), `locale`, `embedding vector(768)`, `tokens`. Unique on (`document_id`, `seq`). Cosine index on `embedding`.

The chat reads only chunks of documents with `active = true`. Closeness limit: cosine distance 0.6 (`MAX_VECTOR_DISTANCE`, a placeholder to tune on real content).

## Not decided (owner)

- Which sources, and who the reviewing clinician is.
- Whether the vector search should also rank by `kind`, for example never quote `drug` chunks in a food question.
- The distance limit, once there is content to test on.
