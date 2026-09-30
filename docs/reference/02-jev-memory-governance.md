> **Superseded.** This is a starting template. The maintained versions are `memory.md`, `schema.md` and `architecture.md` in `docs/specs/`. In `memory.md`, JEV is the OpenJev typed decision layer (not a memory governor), nothing is "validated", and table names are standardised. Kept for reference only.

# Smart Health: JEV Memory Governance

## 1. Purpose

This document defines how JEV governs application memory, retrieval, relationship discovery, memory updates, evidence quality, and downstream AI reasoning in Smart Health.

JEV is the **memory governor**, not the system of record. It operates above the Bronze, Silver, and Gold data architecture described in `01-overall-architecture-database-design.md`.

> JEV governs how application memory is created, retrieved, related, updated, and presented to downstream AI systems. It does not replace the database, identity service, deterministic analytics, or clinical safety engine.

## 2. JEV's position

```text
User request or application task
              |
              v
Identity, authorization, and consent context
              |
              v
JEV
- classify intent
- choose memory strategy
- retrieve relevant evidence
- follow allowed relationships
- detect contradictions
- control memory lifecycle
              |
              v
Scoped Memory Service
- enforce user scope
- enforce permissions and classification
- query Gold and approved Silver views
- validate memory candidates
              |
              v
Gold application memory
              |
       +------+------+
       |             |
       v             v
Dashboard       Constrained LLM
                answer synthesis
```

JEV should not have unrestricted SQL access. It receives controlled tools from the Memory Service, and every retrieval is scoped to the authenticated user, purpose, consent, data classification, and permitted memory types.

## 3. What JEV can and cannot do

| JEV can | JEV cannot |
| --- | --- |
| Classify memory candidates | Modify Bronze |
| Determine retrieval strategy | Bypass access controls, RLS, or consent |
| Select relevant memories | Retrieve another user's data |
| Follow permitted entity, temporal, and relationship links | Invent medical facts |
| Score evidence quality | Convert correlation into causation |
| Detect contradictions | Treat low-confidence extraction as confirmed |
| Determine retrieval depth | Independently change medication instructions |
| Decide when sufficient evidence exists | Override clinical safety rules |
| Propose new memory candidates | Suppress urgent escalation |
| Identify stale or superseded memories | Treat model output as clinically validated |
| Assemble evidence for a doctor brief | Become the system of record |

JEV can reason about memory governance. It cannot decide a medical intervention.

## 4. Why JEV improves the agent architecture

Without JEV, the LLM is asked to make every memory decision repeatedly:

```text
Query
  -> LLM decides what to search
  -> LLM decides how to search
  -> LLM decides whether the result is relevant
  -> LLM decides whether more context is needed
  -> LLM generates the answer
```

This creates repeated generation, more tokens, slower latency, and inconsistent memory behavior.

With JEV:

```text
Query
  -> JEV routes the memory task
  -> Memory Service retrieves structured evidence
  -> JEV checks relevance, links, and sufficiency
  -> LLM generates the answer once
```

For Smart Health, this is especially useful because the application has several memory dimensions:

- Semantic memory for goals, preferences, routines, barriers, and confirmed facts.
- Temporal memory for health events and time windows.
- Entity memory for medications, foods, devices, symptoms, and appointments.
- Relationship memory for evidence-backed associations.

JEV can select the appropriate memory path instead of making the LLM repeatedly search unrelated data.

## 5. Memory planes and JEV routing

### 5.1 Semantic route

Use when the user asks about meaning, preferences, context, goals, routines, or previously learned facts.

Examples:

- “What reminders work best for me?”
- “What has Smart Health learned about my routine?”
- “What is my current health goal?”
- “Why do I keep missing my evening dose?”

JEV retrieves semantic facts with confidence, evidence, date, status, and user-confirmation state.

### 5.2 Temporal route

Use when the user asks what happened, when it happened, or what occurred around an event.

Examples:

- “What happened to my glucose after dinner?”
- “Did I take my medication yesterday?”
- “How was my week?”
- “What happened on my worst day?”

JEV retrieves the relevant time window, timeline events, canonical measurements, and quality indicators.

### 5.3 Entity route

Use when the query concerns a medication, supplement, food, device, symptom, appointment, or health goal.

Examples:

- “What is this medicine for?”
- “Which foods have I logged most often?”
- “When is my next kidney screening due?”
- “What devices are connected?”

JEV resolves the appropriate entity and follows only authorized relationships.

### 5.4 Relationship route

Use when the user asks about links between events, foods, medication adherence, exercise, sleep, symptoms, or glucose.

Examples:

- “Do my evening walks line up with lower evening readings?”
- “What foods tend to produce a bigger response for me?”
- “Is there a pattern between missed doses and my readings?”

JEV must return the relationship type and evidence status. It should preserve whether the relationship is user-reported, temporal, observed, repeated, or clinically validated.

## 6. Memory Service API

JEV gets tools, not unrestricted database privileges.

Conceptual functions:

```text
retrieve_health_context(
  user_id,
  purpose,
  permission_scope
)

retrieve_temporal_context(
  user_id,
  time_window,
  purpose,
  permission_scope
)

retrieve_entity_context(
  user_id,
  entity_ids,
  purpose,
  permission_scope
)

retrieve_relationships(
  user_id,
  entity_ids,
  evidence_filters,
  permission_scope
)

retrieve_relevant_memories(
  user_id,
  query,
  memory_types,
  permission_scope
)

create_memory_candidate(
  user_id,
  proposed_memory,
  source_ids,
  evidence_status
)

update_memory_candidate(
  user_id,
  memory_id,
  proposed_change,
  source_ids
)

supersede_memory(
  user_id,
  old_memory_id,
  replacement_id,
  reason
)
```

These functions are conceptual contracts. The actual service must derive or verify user scope from trusted authentication context rather than blindly trusting a caller-supplied `user_id`.

### Memory Service requirements

Every request must enforce:

- Authenticated user or explicitly authorized service context.
- User scope and tenant scope.
- Purpose limitation.
- Consent state.
- Data-classification policy.
- Allowed memory types.
- Retrieval depth and result-size limits.
- Freshness and quality filters.
- Provenance availability.
- Audit logging.

Sensitive records should be returned minimally. JEV generally does not need a patient's name, email, phone number, NRIC, or address to answer a health-timeline question.

## 7. Retrieval flow

### 7.1 Standard flow

1. The application authenticates the user.
2. The application checks the request purpose and consent scope.
3. JEV classifies the query as semantic, temporal, entity, relationship, or a combination.
4. JEV chooses the initial retrieval depth and relevant Gold views.
5. The Memory Service validates authorization, classification, freshness, and user scope.
6. The Memory Service returns minimal records with provenance and evidence labels.
7. JEV checks relevance, contradictions, missing context, and evidence sufficiency.
8. JEV follows permitted relationships or expands the search only if the evidence is insufficient.
9. JEV checks whether a deterministic safety service must handle the request.
10. JEV produces a structured evidence packet.
11. The LLM generates a response from the evidence packet only.
12. Output guardrails validate that the response does not diagnose, advise on medication, invent citations, or contradict urgent safety output.

### 7.2 Structured evidence packet

A JEV response to the LLM should be structured rather than an unlabelled text dump:

```json
{
  "user_scope": "pseudonymous_internal_user_id",
  "purpose": "food_response_explanation",
  "memory_types": ["temporal", "relationship", "semantic"],
  "time_window": {
    "start": "2026-09-01T00:00:00Z",
    "end": "2026-09-14T23:59:59Z"
  },
  "observations": [
    {
      "source_id": "glucose_reading:...",
      "observed_at": "...",
      "value": 8.1,
      "unit": "mmol/L",
      "evidence_status": "OBSERVED"
    }
  ],
  "relationships": [
    {
      "relationship_type": "repeated_observation",
      "confidence": 0.82,
      "evidence_ids": ["event_window:...", "event_window:..."]
    }
  ],
  "sample_count": 3,
  "quality_status": "sufficient",
  "permitted_framing": "associated_with",
  "uncertainties": [],
  "safety_flags": []
}
```

The LLM should not be asked to infer missing source IDs or reconstruct calculations from prose.

## 8. Retrieval expansion and stopping

JEV should use bounded retrieval rather than repeatedly asking the LLM to search.

### Initial retrieval

Start with the smallest useful context:

- Precomputed `health_state` or `insight_context` for broad questions.
- `health_timeline` and `event_windows` for event-window questions.
- `food_response` for personal food-response questions.
- `adherence_summary` and dose events for adherence questions.
- Confirmed medication entities and reference data for medication explanations.

### Expansion triggers

Expand retrieval only when:

- Evidence count is below a feature's minimum.
- A relationship requires supporting observations.
- Contradictory records need resolution.
- A source record must be displayed to the user.
- A doctor brief needs traceability.
- Freshness is insufficient.
- A safety path requires deterministic inputs.

### Stop conditions

Stop when:

- The requested output has sufficient evidence.
- The feature's acceptance threshold is met.
- Additional records would not materially change the answer.
- The query is outside the available data.
- A safety engine has produced a controlling output.

If evidence is insufficient, JEV must return an insufficiency state rather than inventing a conclusion.

## 9. Feature-specific JEV behavior

### F1: Onboarding

JEV can retrieve onboarding context to personalize questions or explain the setup. It cannot enroll out-of-scope users, bypass consent, or infer a diagnosis.

### F2: Medication capture

After a user confirms extracted fields, JEV can retrieve the medication's entity context and propose memory updates. It cannot activate unconfirmed medication records or guess an unrecognized medication.

### F3: Medication explainer

JEV retrieves the approved drug facts and the user's confirmed prescription information. It must keep the user's actual dose separate from general drug facts. The LLM may explain the retrieved facts but cannot generate a new dose.

Questions such as “Can I stop, double, or skip this?” enter a refusal path and can be added to the doctor brief.

### F4: Adherence

JEV retrieves the dose schedule, dose events, adherence summary, and miss-reason patterns. The schedule engine, not JEV, determines whether a dose is late, unconfirmed, taken, or missed.

### F5: Clash checker

JEV may provide context for presenting a confirmed interaction result. It cannot decide the interaction. A deterministic reference lookup must produce the result; unknown items remain “not checked.”

### F6: Health tracking

JEV selects the relevant timeline or metric context. Aggregation, unit conversion, deduplication, and quality checks happen in deterministic services.

### F7: CGM sprint and food response

JEV retrieves meal-response evidence only when the acceptance criteria are satisfied. A personalized food response is not surfaced when there are fewer than two eligible observations. When shown, it includes `n`, range, time window, and cautious association wording.

### F8: Momentum engine

JEV retrieves already-computed momentum results and the evidence numbers that generated them. It does not calculate the baseline, slope, or acceleration inside a prompt.

### F9: Symptom check-ins

JEV may select a question based on a deterministic or reviewed trigger. It must ask neutrally and never diagnose. Anti-nag limits are enforced outside free-form LLM reasoning.

### F10: Urgent escalation

JEV cannot delay, suppress, downgrade, or reinterpret urgent events. The deterministic safety engine controls the response path. JEV and the LLM may help present an approved message only after the safety result is produced.

### F11: Lifestyle coach

JEV retrieves the user's preferences, routines, previous nudge responses, and approved content. Until an approved guideline corpus is available, the coach should use team-written templates grounded in the user's own data.

### F12: Doctor brief

JEV assembles authorized evidence from all relevant Gold dimensions. It does not calculate the numbers or hide findings from the patient. Every narrative claim must link to an evidence ID.

### F16: Transparent memory

JEV supports the user-facing list of learned facts. Each fact shows its statement, confidence, evidence, date, status, and version history. The user can confirm, correct, or delete it.

### F18: Timeline and day traces

JEV can select the most relevant representative days, event windows, and evidence for display. The fixed rules choosing best, worst, and typical days remain deterministic and auditable.

## 10. Memory write path

```text
New observation
      |
      v
JEV typing
What kind of memory might this support?
      |
      v
Candidate search
Find related memories and source records
      |
      v
JEV relationships
How does the new observation connect?
      |
      v
Validation and policy gate
Scope, evidence, confidence, status, confirmation
      |
      v
Insert or supersede Gold memory
```

### 10.1 Candidate creation

JEV may propose a candidate when it detects:

- A repeated user preference.
- A recurring routine.
- A repeated adherence barrier.
- A possible food-response association.
- A conversation fact worth remembering.
- A stale or contradictory existing memory.

The candidate must include:

- Proposed memory type.
- Proposed value.
- Source IDs.
- Evidence status.
- Confidence.
- Creation source.
- Model or rule version.
- Validity period.
- Whether user confirmation is required.

### 10.2 Candidate validation

The Memory Service validates:

- User ownership.
- Source existence.
- Source accessibility.
- Data classification.
- Evidence status.
- Confidence range.
- Schema shape.
- Relationship type.
- Required feature thresholds.
- Whether the proposed memory conflicts with an active memory.
- Whether the change requires user or clinical confirmation.

### 10.3 Updating and superseding

Do not silently overwrite a memory. Create a replacement version and link it with `supersedes_memory_id` or an equivalent relationship.

Examples:

```text
Memory v1: User prefers evening reminders.
Memory v2: User responds better to 7 p.m. reminders on weekdays.
Memory v1 -> superseded by -> Memory v2
```

For a correction:

```text
AI-proposed fact -> user rejects -> status: rejected
```

Rejected facts remain available to prevent repeated incorrect proposals, subject to deletion and retention policy.

## 11. Memory confidence and evidence model

Use two separate dimensions:

1. **Evidence status:** what kind of evidence supports the item.
2. **Confidence:** how strongly the system believes the extraction or pattern is supported.

| Evidence status | Meaning | Example |
| --- | --- | --- |
| `OBSERVED` | Directly recorded by a device or user | Glucose = 8.1 mmol/L |
| `DERIVED` | Reproducible calculation | Seven-day average or deterministic trend |
| `INFERRED` | Model-generated interpretation | A meal may be associated with a larger response |
| `VALIDATED` | Reviewed or supported by an approved authoritative process | Reference-based interaction result |

Important distinctions:

- A high-confidence extraction is not automatically clinically validated.
- A repeated association is not automatically causation.
- A user-confirmed preference is different from an AI-inferred preference.
- A deterministic calculation is not the same as a clinical conclusion.

## 12. Contradictions and stale memories

When JEV finds conflicting memories:

1. Prefer newer evidence only when the newer record has comparable or better evidence quality.
2. Prefer direct observation over unsupported inference.
3. Prefer user correction over an AI proposal for user preferences and personal facts.
4. Do not silently merge conflicting medical records.
5. Mark the conflict and request confirmation where needed.
6. Supersede stale memories instead of deleting their provenance.
7. Recompute dependent summaries after upstream corrections.

Example:

```text
Old memory: User prefers morning walks.
New observations: 10 evening walks and 1 morning walk over 30 days.
JEV action: propose a revised routine; do not silently rewrite the old memory.
```

## 13. PII minimization in JEV

JEV generally needs:

```text
pseudonymous user_id
health context
source IDs
time windows
memory types
permission scope
```

JEV generally does not need:

```text
name
email
phone
NRIC
home address
```

The identity service handles identity and authorization. The Memory Service passes the minimum information required for the task. The final presentation layer can resolve a display name only when authorized and necessary.

Do not place raw prescriptions, medical-document text, or unnecessary identifiers directly into prompts or embeddings. Prefer structured, redacted, source-linked representations.

## 14. Clinical safety boundary

```text
                         JEV / LLM
                             |
                +------------+------------+
                |                         |
          General AI path          Clinical safety path
                |                         |
                v                         v
        Explanation and recall     Deterministic services
                                    |
                         +----------+----------+
                         |                     |
                    F5 clash rules        F10 urgent rules
                         |                     |
                         v                     v
                    Approved output       Approved escalation
```

### F5 medication interactions

```text
Confirmed medication entities
        |
        v
Versioned interaction reference
        |
        v
Deterministic matching
        |
        v
Confirmed hit / not checked
        |
        v
LLM rephrases within approved template
```

JEV cannot invent an interaction, label an item safe when it was not found, or advise the user to stop a medication.

### F10 urgent events

```text
Glucose and symptom inputs
        |
        v
Validated measurements
        |
        v
Deterministic urgent-event rule engine
        |
        v
Approved urgent response
```

JEV cannot override the urgent result or wait until the next doctor brief.

## 15. Doctor-brief governance

JEV assembles context; deterministic services compute values; the LLM writes constrained narrative.

### Required brief evidence

Every number must include:

- Source record or aggregate ID.
- Calculation version.
- Time period.
- Quality status.
- Unit.
- Missing-data status where relevant.

Every narrative sentence must include an evidence ID or be rejected by a validator.

### Example

```json
{
  "sentence": "Your fasting readings were higher than your recent baseline this week.",
  "evidence_ids": [
    "momentum_snapshot:...",
    "baseline:...",
    "glucose_reading:..."
  ],
  "status": "unverified_pattern",
  "permitted_framing": "worth_discussing_with_clinician"
}
```

The patient must be able to view the same findings included in the clinician brief. There must be no hidden AI conclusions.

## 16. Observability and audit

Log JEV's control decisions without copying unnecessary health content:

- Request purpose.
- Authenticated subject and pseudonymous user scope.
- Consent and permission checks.
- Memory route selected.
- Tools called.
- Retrieval depth and result count.
- Source and memory IDs.
- Contradictions detected.
- Candidate created or rejected.
- Supersession decision.
- Model, prompt, rule, and reference-data versions.
- Safety gate result.
- Final response validator result.

Use an append-only event log. Avoid storing free-text medical notes in general-purpose audit payloads when IDs and enums are sufficient.

## 17. Suggested implementation sequence

1. Build scoped Memory Service endpoints with user ownership checks.
2. Implement temporal and entity retrieval first because F4, F6, F7, F8, F10, F12, and F18 depend on them.
3. Add semantic `memory_facts` with explicit confidence, evidence, status, and user confirmation.
4. Add relationship records and event-window evidence.
5. Add JEV routing and bounded retrieval expansion.
6. Add candidate creation and supersession workflows.
7. Add contradiction detection and stale-memory handling.
8. Connect the constrained LLM response layer.
9. Add output validation for medication advice, diagnosis, citations, and evidence IDs.
10. Add audit dashboards and red-team tests.

## 18. Example: food to CGM memory lifecycle

### Write path

```text
Food photo upload
        |
        v
Bronze: original image + metadata
        |
        v
Vision extraction candidate
        |
        v
Silver: meal items + nutrition + confidence
        |
        v
Normalized CGM stream
        |
        v
Deterministic event-window calculation
        |
        v
Temporal Gold: meal ↔ glucose window
        |
        v
Relationship Gold: repeated personal response
        |
        v
Semantic Gold: cautious user-facing memory
```

### Acceptance rule

```text
Eligible observations < 2
        |
        v
Do not surface a personalized food response

Eligible observations >= 2
        |
        v
Calculate response
Show n, range, window, and quality status
Use association wording
```

### Retrieval path

```text
User: "How does chicken rice affect my glucose?"
        |
        v
JEV classifies: entity + temporal + relationship
        |
        v
Memory Service retrieves chicken-rice meals,
CGM windows, food-response aggregate, and evidence
        |
        v
JEV checks n, quality, freshness, contradictions
        |
        v
LLM generates approved factual phrasing
```

Possible output:

> You logged chicken rice three times during the sprint. Your glucose rose more than after most of your logged meals on those occasions. This is an observed personal pattern, not proof that the food caused the change.

## 19. Summary architecture statement

> Medallion architecture gives Smart Health reliable and traceable data. Gold gives the application structured memory across semantic, temporal, entity, and relationship dimensions. JEV governs how that memory is retrieved, related, updated, and presented. The Memory Service enforces scope and policy. Deterministic services control calculations, medication-interaction checks, and urgent escalation. The LLM explains approved evidence but does not become the system of record or clinical decision-maker.
