# Memory, evidence and decisions

How Smart Health stores what it learns about a person, how that memory is read and written, and where fast typed decisions (JEV) fit. This replaces the two starting-template documents (kept in `docs/reference/`). Read it with [architecture.md](architecture.md) (system), [schema.md](schema.md) (tables) and [rules.md](rules.md) (boundaries).

> **Nothing in this project is clinically validated yet.** No status, label or table in this document means "validated". Reference lookups are matched against unreviewed data, thresholds are marked "clinical validation pending", and every learned pattern is an association.

---

## 1. Standard terms and naming

One vocabulary for every document, table and prompt.

| Term | Meaning |
|---|---|
| **Bronze / Silver / Gold** | Data layers. Bronze = raw source as received. Silver = canonical, cleaned, user-confirmed records. Gold = derived values, views and application memory |
| **Memory planes** | The four ways Gold memory is organised: **semantic** (meaning, preferences, routines), **temporal** (what happened when), **entity** (medications, foods, devices, goals, appointments), **relationship** (evidence-backed associations). Episodic recall (past chat summaries) is part of semantic |
| **Memory Service** | Our scoped read/write API over Gold and approved Silver. Every read and write goes through it |
| **JEV** | The typed decision layer, implemented with [OpenJev](https://github.com/razorback16/openjev), a "System One" decision server. You send it a state and typed questions (`noul` yes/no, `choice`, `score`, optionally with images). It returns a probability and a confidence for each answer, read directly from the model's probabilities, so an answer cannot go off-schema. It does not store memory, run analytics or decide safety |
| **Decision gateway** | Our adapter (`app/decision/`) that calls JEV. If JEV is off or unreachable, the conservative path applies (no model fallback) |
| **Evidence packet** | The structured input the LLM answers from (section 7) |
| **Evidence status** | `observed`, `derived`, `inferred`, `reference_matched` (section 4) |
| **Confidence** | A 0 to 1 number, separate from evidence status |

**Naming rules**

- Tables: plural `snake_case`, all in the `public` schema. Views use plain names (like `timeline_events`). No `bronze.` / `silver.` / `gold.` prefixes; the layer of each table is in the layer map in [schema.md](schema.md).
- Enum values, JSON keys and event names: lowercase `snake_case` (events are dotted, `domain.object.action`).
- IDs: features `F1`-`F18`, epics `E0`-`E22`, tasks `E9-2`.
- Timestamps in UTC, canonical units (mmol/L, g, mg, kcal, seconds, metres).
- Supersession column: `supersedes_id`.

**What the template documents called things, and what we use**

| Template name | Standard name |
|---|---|
| `gold.health_facts`, `gold.user_preferences`, `gold.health_context`, `gold.ai_memories`, `memory_facts` | `memory_facts` (one table) |
| `gold.health_timeline`, `gold.health_events` | `timeline_events` (view) |
| `gold.daily_snapshots` | `daily_aggregates` |
| `gold.health_state`, `gold.trends`, `gold.adherence_summary`, `gold.insight_context` | views `health_state`, `trends`, `adherence_summary`, `insight_context` |
| `gold.anomalies` | `clinical_flags` |
| `gold.food_response` | `food_responses` |
| `gold.doctor_brief_context` | `briefs.data` (BriefData snapshot) |
| `gold.entities`, `gold.entity_relationships` | ordinary foreign keys plus `pattern_candidates` for associations |
| `bronze.ingestion_events` | `ingestion_events` |
| `supersedes_memory_id` | `supersedes_id` |
| evidence status `VALIDATED`; relationship types `clinically_validated`, `causal_evidence` | removed |

---

## 2. Data layers

```
SOURCES  wearable / CGM files, glucometer, manual entry, meal photos and text,
         medication and supplement photos, demo datasets
            |
            v
BRONZE   original object + ingestion_events row (checksum, source, time, schema version)
            |
            v
SILVER   canonical records: units, UTC time, deduplicated, validated, confirmed by the user
            |
            v
GOLD     derived tables and views + application memory
         (aggregates, baselines, momentum, event windows, patterns, food responses,
          memory_facts, briefs)
            |
            v
         dashboards, deterministic services, Memory Service, JEV, LLM
```

**Bronze** keeps exactly what was received. No AI edits it, no derived values live there, and nothing is silently overwritten. If an image was processed badly, keep the original and run a new analysis with a new model or prompt version. Bronze is immutable in normal operation; the only exceptions are a user-initiated deletion and retention expiry, both of which are logged in `event_log`.

**Silver** is the canonical form of every source. It may contain AI extraction candidates (a scanned medication, an estimated meal), but a candidate is never treated as confirmed until the user confirms it, and a low-confidence extraction is never turned into a fact.

**Gold** is built only from Silver and always keeps: the calculation or model version, the evidence window, a freshness timestamp, source references, a quality status, and what invalidates it. Gold views are derived, never a second source of truth.

**Demo scope:** Bronze is the stored original (photo, export file) plus a slim `ingestion_events` row. Silver is the existing canonical tables. Gold is the derived tables plus four views.

---

## 3. Memory planes and where they live

| Plane | Question it answers | Stored in | Built by |
|---|---|---|---|
| Semantic | What does this mean for this person? | `memory_facts`, `memory_episodes`, `health_goals`, `patient_profiles` | User onboarding, nightly reflection (proposes), user (confirms) |
| Temporal | What happened, when, and around what? | `timeline_events` (view), `event_windows`, `daily_aggregates`, `meal_responses` | Deterministic services |
| Entity | What exists in this person's health world? | `patient_medications`, `medication_ingredients`, `foods`, `meals`, `devices`, `health_goals`, `appointments` | User confirmation, importers |
| Relationship | What is linked to what, and how well supported is it? | `pattern_candidates`, `interaction_alerts`, `food_responses` | Deterministic services (associations), lookups (interactions) |

Relationships use these types, never anything causal:

| `relationship_type` | Meaning |
|---|---|
| `user_reported` | The user said it |
| `temporal_association` | Two things happened close together once |
| `observed_association` | A measured difference between matched situations |
| `repeated_observation` | The same association met the minimum sample threshold |

The distinction is kept everywhere: **observation is not association, association is not inference, inference is not proof.** The app says "associated with" or "your readings were higher after", never "caused by".

---

## 4. Evidence model

Two independent fields on anything the system stores or shows.

| `evidence_status` | Meaning | Example |
|---|---|---|
| `observed` | Recorded directly by a device or the user | Glucose 8.1 mmol/L, a logged dose |
| `derived` | A reproducible calculation from observed data | 7-day average, baseline, momentum, food response |
| `inferred` | Produced by a model, not confirmed | A meal's estimated macros, a proposed memory fact |
| `reference_matched` | Deterministically matched against reference data that has **not** been clinically reviewed | An interaction hit from the reference table |

`confidence` (0 to 1) says how strongly the extraction or pattern is supported. A high confidence never upgrades the status, and no status means clinically validated. Rules that follow:

- `inferred` items show as "estimated" or "proposed" in the app and need user confirmation before they drive anything.
- `reference_matched` results use the approved wording and are labelled as unreviewed in the brief.
- Patterns in the brief carry `unverified pattern` and the framing "worth discussing with your clinician".

---

## 5. Decision layer (JEV)

### 5.1 What we use it for

JEV answers small typed questions quickly, with a calibrated confidence (1 minus normalised entropy). Use it only where a fast, bounded classification helps.

| Decision | Type | Example question | Low confidence or JEV unavailable |
|---|---|---|---|
| Memory route | `choice` (semantic / temporal / entity / relationship) | "Which kind of memory does this question need?" | Retrieve semantic plus temporal, small limits |
| Message intent | `choice` | "Is the user asking about a reading, a medicine, food, exercise or something else?" | Route to general companion, no tools with writes |
| Guard: medication advice | `noul` | "Is the user asking whether to stop, skip, double or change a medicine?" | Treat as **yes** (refusal template) |
| Guard: diagnosis | `noul` | "Is the user asking what condition they have?" | Treat as **yes** (non-diagnostic template) |
| Guard: urgent wording | `noul` | "Does the message describe an urgent symptom?" | Treat as **yes** and show the urgent path |
| Memory candidate type | `choice` (preference / routine / barrier / food_response / goal / context) | "What kind of fact is this?" | Store as `context`, `proposed`, needs confirmation |
| Relevance | `noul` | "Does this evidence support this statement?" | Drop the statement |
| Contradiction (stretch) | `noul` | "Do these two facts conflict?" | Keep both, ask the user |
| Item type from an image | `choice` | "Is this a prescription label, box, supplement, TCM product or food?" | Ask the user |

### 5.2 What it never decides

- Any number, threshold, aggregate, baseline, slope or food response.
- Urgent escalation, interaction lookup, dose schedules, adherence status.
- Meal nutrients (those are LLM estimates, section 9).
- Anything that suppresses or overrides a safety output.

**Rules always win.** A rule that fires beats any JEV answer. A JEV answer below the confidence floor (start at 0.8, tune on the red-team set) or a JEV outage takes the conservative path in the table above. JEV is a second opinion, not a gate that can be walked around.

### 5.3 Contract

Our decision gateway keeps OpenJev's wire shape so the provider can change:

```json
{
  "state": "Can I skip my metformin tonight since my sugar looks fine?",
  "questions": {
    "med_advice": {"type": "noul", "instructions": "Is the user asking whether to stop, skip, double or change a medicine?"},
    "route": {"type": "choice", "instructions": "Which memory does this need?",
              "criteria": {"semantic": "preferences and routines", "temporal": "what happened when",
                           "entity": "a medicine, food, device or goal", "relationship": "links between events"}}
  }
}
```

Response per question: `noul` gives the probability of yes; `choice` gives the chosen option, probabilities and confidence; `score` gives an expected level. The state sent to JEV never contains a name, NRIC, phone number or address.

### 5.4 Deployment options (decide in E0-12)

The owner chose the TypeSafe JEV model on 2026-10-02 (D-047); how it is deployed is still to be confirmed in E0-3. The options below remain the reference for that choice. The app runs locally for now, so prefer options that run on a developer's machine; the hosted option is a convenience, not a requirement.

| Option | Good for | Watch out for |
|---|---|---|
| Hosted OpenJev on Codiv (`api.codiv.ai/v1/systemone`) | Fastest start, no GPU | Third-party service: send only de-identified state; check current terms and limits before relying on the free allowance |
| Small encoder models behind OpenJev (Laya 421M, Verdict 151M) | Runs on a CPU, cheap | Text only; at most about 255 (Laya) or 24 (Verdict) options; short states (512 to 1,024 tokens) |
| Self-hosted DiffusionGemma via OpenJev | Text plus images | Needs an NVIDIA GPU with 24 GB or Apple silicon with about 16 GB free |
| **No model fallback** (decided 2026-10-02) | Nothing else to run or pay for | When JEV is off or unreachable, the conservative path applies to every decision (refusal template, "not checked", default route) |

OpenJev is an independent, recent open-source project and is not affiliated with TypeSafe. Keep it behind the gateway so nothing else depends on it.

---

## 6. Memory Service

Our own code, not JEV. It is the only path to memory for agents, the LLM, JEV and the dashboards. Standard functions:

| Function | Returns |
|---|---|
| `get_context(purpose)` | Profile summary, active facts, recent aggregates, open flags |
| `get_timeline(window)` | `timeline_events` for a window plus quality flags |
| `get_entities(ids)` | Medications, foods, devices, goals, appointments with confirmed fields |
| `get_relationships(filters)` | `pattern_candidates`, `food_responses`, `interaction_alerts` with evidence status |
| `search_memories(query, types)` | Facts and episodes by relevance (vector plus filters) |
| `propose_memory(candidate)` | Validates and inserts a `proposed` fact |
| `supersede_memory(old_id, new_id, reason)` | Creates the new version and links `supersedes_id` |

Requirements for every call:

- The user id comes from the demo session, never from the caller's arguments.
- Only the memory types allowed for that caller, with result-size and depth limits.
- Returns minimal fields with source ids, evidence status, confidence and freshness. Never returns a name, email, phone, NRIC or address.
- Writes an `agent_steps` row (route, tool, counts, ids).

No caller (JEV, agents, LLM) gets free SQL.

---

## 7. Retrieval and the evidence packet

Standard flow:

1. The app resolves the user from the session.
2. Input guard: rules first, then JEV questions (section 5.1). Urgent and refusal paths return templates and stop here.
3. JEV picks the memory route (or the default route on low confidence).
4. The Memory Service returns the smallest useful context: precomputed views first (`health_state`, `insight_context`, `trends`, `adherence_summary`), then timeline, food responses or entities.
5. Expand only when a feature threshold is unmet, a relationship needs its supporting observations, a source record must be shown, or freshness is stale. Stop when the feature's threshold is met, more records would not change the answer, the question is outside the data, or a safety engine has answered.
6. If evidence is insufficient the packet says so. Nothing is invented.
7. The LLM writes from the packet only. Output guard checks: no medication advice, no diagnosis, no invented citations, no contradiction of an urgent output.

**Evidence packet (standard shape)**

```json
{
  "purpose": "food_response_explanation",
  "route": ["temporal", "relationship"],
  "window": {"start": "2026-09-01T00:00:00Z", "end": "2026-09-14T23:59:59Z"},
  "observations": [
    {"source_id": "glucose_reading:...", "observed_at": "...", "value": 8.1, "unit": "mmol/L", "evidence_status": "observed"}
  ],
  "relationships": [
    {"relationship_type": "repeated_observation", "evidence_status": "derived", "confidence": 0.82,
     "evidence_ids": ["event_window:...", "event_window:..."], "n": 3}
  ],
  "quality_status": "sufficient",
  "permitted_framing": "associated_with",
  "uncertainties": [],
  "safety_flags": []
}
```

The LLM is never asked to infer source ids or redo calculations from prose.

---

## 8. Memory write path and lifecycle

```
new observation or conversation
   -> candidate (rule or reflection agent proposes; JEV types it)
   -> Memory Service validates (user owns sources, sources exist, confidence range,
      schema, feature threshold, conflict with an active fact)
   -> insert as proposed, or supersede
```

- A candidate carries: type, value, source ids, `evidence_status`, confidence, creator, model or rule version, validity period, and whether user confirmation is required.
- **Lifecycle:** `proposed` (confidence below 0.7) → `active` (0.7 or more, or user-confirmed) → `superseded` (a newer version exists) or `rejected` (the user deleted it; never proposed again with the same key and value).
- Never overwrite silently. Create a new version and link it with `supersedes_id`. Example: "prefers evening reminders" becomes "responds better to 7:30 pm reminders on weekdays".
- Confidence rises with repeated evidence and decays after 30 days without supporting evidence.
- **Conflicts (stretch):** prefer the newer record only if its evidence is as good; prefer direct observation over inference; prefer the user's correction over an AI proposal; never merge conflicting medical records; mark the conflict and ask the user; recompute dependent summaries after a correction.

---

## 9. Meal analysis (LLM macros)

Food is stored as the original photo or text, then analysed by the LLM for macros.

```
photo or text -> Bronze: original + ingestion_events row
   -> LLM analysis: items + estimated kcal, carbs, protein, fat, fibre, sugar, sodium,
      confidence per field (meal_analyses row with model_id and prompt_version)
   -> Silver: meal_items (estimated_by = 'llm_estimate', evidence_status = 'inferred')
   -> user confirms or edits (estimated_by becomes 'user')
   -> deterministic services use the stored values: flags, aggregates, food response
```

- The UI shows **Estimated** until the user confirms. An estimate is never presented as measured.
- Local dish names are allowed. The LLM estimates macros for any described food; Open Food Facts and NHANES dietary values are only a sanity check that can add a "check this" flag.
- Re-running with a newer model or prompt creates a new `meal_analyses` row; the original is untouched.
- Glucose response is always measured (CGM or glucometer). Only the macros are estimated, so the food-response leaderboard says so and still needs at least 2 observations with `n` and range.
- Dataset meals (CGMacros, BIG IDEAs) keep their measured macros and are labelled `demo_dataset`.

---

## 10. Feature behaviour (F1-F18)

| Feature | Layers and planes | JEV role | Deterministic control |
|---|---|---|---|
| F1 Onboarding | Silver profile; semantic + entity | Optional: type onboarding answers | Eligibility, consent |
| F2 Medication capture | Bronze image; Silver medication; entity | Item type from image | Confidence gate, user confirmation, sig parser |
| F3 Explainer | Reference; semantic | Route | Dose text only from the confirmed prescription |
| F4 Adherence | Silver doses; temporal | None | Schedule engine and status machine |
| F5 Clash checker | Reference; relationship (`reference_matched`) | None | Interaction lookup, "not checked" for unknowns |
| F6 Tracking | Bronze; Silver; temporal; entity | Meal analysis is LLM, not JEV | Validation, units, quality flags |
| F7 CGM sprint | Silver; temporal; relationship | None | Windowing, sample thresholds |
| F8 Momentum | Gold; temporal | None | Baseline, slope, thresholds |
| F9 Check-ins | Silver; semantic | Pick question type (optional) | Anti-nag caps, neutral wording |
| F10 Urgent | Silver; Gold `urgent_events` | None, cannot override | Rule engine |
| F11 Lifestyle coach | Semantic | Route, relevance | Reviewed templates, caps, quiet hours |
| F12 Doctor brief | All planes | Relevance of statements | Numbers by code, evidence-id validator |
| F13 Preventive care | Silver; entity | None | Due/overdue from configured intervals; no booking without confirmation |
| F14 Healthcare prep | Silver; semantic | Route; phrasing type | Questions stored as written; routing rules by lookup |
| F15 Chat | All planes via Memory Service | Route, intent, guards | Refusal templates, urgent path, output guard |
| F16 Transparent memory | Semantic | Candidate type | User confirm, edit, delete; versions |
| F17 Multilingual and TTS | Presentation | None | Approved templates translated once and reviewed |
| F18 Timeline | Temporal; relationship | None | Quality gates, minimum pairs, association wording |

---

## 11. Doctor brief governance

The Memory Service assembles evidence, deterministic services compute numbers, the LLM writes constrained narrative.

- Every number carries: source or aggregate id, calculation version, period, quality status, unit, and missing-data status.
- Every narrative sentence carries an evidence id or the validator rejects it.
- Each item shows its `evidence_status`; patterns read "unverified pattern".
- The patient sees exactly what the clinician sees. No hidden AI conclusions.

```json
{
  "sentence": "Fasting readings were higher than your recent baseline this week.",
  "evidence_ids": ["momentum_snapshot:...", "baseline:...", "glucose_reading:..."],
  "evidence_status": "derived",
  "permitted_framing": "worth_discussing_with_clinician"
}
```

---

## 12. Observability

Log control decisions, not health content, using existing tables:

| What | Where |
|---|---|
| Agent and JEV calls (route chosen, question ids, answers, confidence, latency) | `agent_steps` (`node` = `jev`, `tool` = `decide`) |
| Memory Service calls (function, counts, source ids) | `agent_steps` (`node` = `memory`) |
| Guard outcomes | `guardrail_events` |
| Candidate created, rejected, superseded | `event_log` (`memory.fact.*`) |
| Model, prompt and rule versions | `agent_runs.model_id`, `agent_runs.prompt_version`, `meal_analyses`, `prescription_scans` |

---

## 13. Demo scope

**Build now:** Memory Service functions with user scope from the session; evidence packet; `memory_facts` lifecycle with `evidence_status`; the decision gateway with JEV and the conservative path; meal analysis with `meal_analyses`; the layer map; four Gold views.

**Minimum now:** row-level security is enabled on every table with no policies, so the public Supabase key can do nothing, and only the backend connects with server-side credentials.

**Deferred until after the demo** (security and governance depth that does not change what the demo shows): Supabase row-level security per user, consent-scoped retrieval, data-classification tagging at ingestion, purpose-limitation policy engine, short-lived signed URLs, retention and deletion workflows beyond a user deleting their own logs, audit dashboards, contradiction detection.

**Never deferred:** the clinical safety path (urgent rules, interaction lookup with "not checked", refusal templates, no medication advice, no diagnosis), keeping names and identifiers out of prompts, and the evidence-status rules above.
