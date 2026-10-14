# Learning loop: a bounded, self-improving companion

Status: **proposal, with the first slices built locally on 2026-10-06 (section 14). Nothing is committed or pushed.** Written with Hong Yi. Read with [prd.md](prd.md) (section 7 "Grows with the user", F4, F7, F11, F13, F16), [memory.md](memory.md) (memory lifecycle, JEV) and [rules.md](rules.md). Where this document and those disagree, those win until the team approves a change.

---

## 1. The problem this answers

From the PRD (section 1): a person with Type 2 diabetes has about 10 minutes a quarter with their doctor and the other 364 days alone. In between they must take several medicines on time, make sense of glucose with no context, eat and move in ways that affect it, and keep track of screenings. The data exists but nobody joins it up, and generic reminders and generic diet advice do not fit one person's life.

The challenge asks the solution to support three things:

| Challenge capability | What it means here | Where the loop acts |
|---|---|---|
| **Medication management** | Help people remember and sustain treatment routines | LL2 morning-routine anchoring, refill timing |
| **Adherence support** | Identify the barriers to adherence, not just remind | LL3 barrier identification, LL1 adaptive nudging |
| **Preventive health** | Surface screening, vaccination, lifestyle and follow-up needs | LL4 food flag and alternatives, LL5 lunch suggestions, LL7 screening nudges |

(The brief lists medication management and adherence support with identical wording. This spec reads them as: management = schedule, refills, clashes; adherence = barriers and sustaining the routine.)

**The one-line idea.** Today's reminders are the same for everyone. This loop learns *this person's* routine and responses, acts only from a fixed list of safe actions, checks whether the action worked, and shows the person exactly what it learned. It improves visibly, but it can never change its own guardrails.

## 2. What "self-improving" means here (and does not)

| It does | It never does |
|---|---|
| Learn the best time and wording for each person's reminders | Rewrite its own prompts, rules or guards |
| Propose facts about routines, barriers and food responses, with evidence | Activate a fact without confidence plus evidence (and user confirmation for personal facts) |
| Draft new wordings or routine anchors into a **proposed queue** | Publish a draft to a patient before the user or team approves it |
| Rank food alternatives from the person's own measured data, then a Singapore food dataset | Give medicine, dose or diagnosis advice, or claim causation |
| Measure whether each action worked | Suppress or override a safety output, an urgent path or an interaction alert |

This keeps decision D-004 (no autonomous Hermes-style agent) intact: the agent adjusts a short list of per-person settings and proposes facts. It does not self-write.

## 3. Scope

| ID | Feature | Extends | Capability |
|---|---|---|---|
| LL1 | Learning core: outcomes, nightly reflection, nudge policy, proposed queue | prd section 7, F11, F16 | all three |
| LL2 | Morning-routine anchoring | F4 | medication management |
| LL3 | Barrier identification | F4 | adherence support |
| LL4 | Food flag and healthier alternatives (Singapore hawker dataset) | F7, F11 | preventive (lifestyle) |
| LL5 | Lunch-time suggestions ("what suits you today") | F11 | preventive (lifestyle) |
| LL6 | Your own glucose feedback | F7 | adherence support |
| LL7 | Preventive nudges with learned wording | F13 | preventive health |
| LL8 | "What I learned this week" digest | F16 | all three |
| LL9 | High-salt day: swap first, gentle activity second | F6, F11 | preventive (lifestyle) |

### LL1 Learning core
- **Sense:** `medication_log` (taken, late, missed, `miss_reason`), `food_logs`, `meal_response`, `notifications` (`opened_at`, `acted_at`), `appointments`.
- **Act, from a fixed list only:** send a reminder at a time; choose a template; ask "why missed?"; surface a due screening; suggest a meal; add a question to the doctor brief.
- **Measure:** dose taken within 60 minutes of a nudge; suggestion accepted; swap tried, and the measured rise afterwards.
- **Learn, fast:** per-person epsilon-greedy over time slot and template (15% exploration, 3 nudges a day, quiet hours, sick-day pause after an urgent symptom).
- **Learn, slow:** the nightly reflection proposes `memory_facts` (`proposed` under 0.7 confidence, `active` at 0.7 or when confirmed), never overwriting: new versions link by `supersedes_id`; rejected facts are never re-proposed (memory.md section 8).
- **AC:** every action and outcome is written to `notifications`; every learned fact shows its evidence in F16.

### LL2 Morning-routine anchoring
- The agent notices a stable anchor in real logs (breakfast finished, first CGM or watch wake time, work start) and **drafts** "tie your tablet to your breakfast". It is only offered when the schedule already says *after meals* (`medication_schedule.meal_relation`), so a dose is never moved across a meal.
- The person confirms. From then on, tapping "I've finished eating" triggers the reminder; if no breakfast is logged by a fallback time, a fixed-time reminder fires.
- **AC:** anchors are `proposed` until confirmed; the fixed-time fallback always exists; the agent cannot change the prescribed time or dose.
- **Signal that exists today:** the meal-finish tap in the Log feature (E2).

### LL3 Barrier identification
- Rules first: *forgot* (missed, no app activity), *ran out* (`refill_forecasts` empty before the miss), *side effects* (a symptom logged within hours of the dose, an association only), *busy or away* (misses cluster on weekday evenings or work hours), plus self-reported reasons.
- JEV labels free-text reasons into those categories. A barrier needs 3 or more occurrences before it is proposed.
- A barrier adapts the nudge or goes to the doctor brief as a question. It never produces advice.
- **AC:** reason breakdown and barrier pattern appear in the brief; meets the PRD target of 60% miss-reason capture.

### LL4 Food habit and lighter dishes for the next meal
**Design rule (owner correction, 2026-10-06): the food database never sets what a meal is logged as.** The calories and macros saved for a meal come from the photo model (Vertex AI) or from the person's own edits, always. The Singapore food tables are only a **shelf of lighter, similar dishes** that the memory loop offers for the *next* meal. A logged meal is never matched to a database row, and no database number is ever written to the person's log.
- **Dataset:** the Singapore food nutrition tables (Kaggle `adisongoh/singapore-hawker-food-nutritional-information`). **Approved by the owner on 2026-10-06 as an exception to the cited-datasets policy**; recorded in `data_sources` with licence marked unconfirmed. Raw files stay out of git. Use the **combined file** (2,689 rows, a superset of the 1,163-row hawker file).
- **The loop:**
  1. **Log:** the person logs meals as usual (photo, AI estimate, optional edits).
  2. **Notice (memory loop):** JEV `choice` labels each distinct meal name with a food type (fried food, rice dish, noodle dish, soup or porridge, bread or pastry, sweet drink or dessert, vegetables or fruit), so "fried chicken" and "fried chicken wings" are one habit.
  3. **Flag (code):** a type eaten at least *N* times in 14 days whose **logged** average is high in calories, salt or sugar is a habit worth a nudge. *N* and the limits are placeholders pending clinical review. The habit is also proposed as a memory fact (`food.habit.<type>`), never activated by the agent.
  4. **Offer (the shelf):** the person's heaviest repeated dish in that habit is looked up on the shelf (text plus embedding search, widened with lighter cooking styles of the same main ingredient: steamed, roasted, grilled, soup, boiled). This lookup only finds candidates.
  5. **Compare (code):** every candidate is compared with the person's **own logged average** for their usual dish, not with a database row for it. It must be a meal-sized replacement (roughly half to the same energy), improve a target nutrient by at least 20%, and not be meaningfully worse elsewhere. Savings are reported for calories, salt, carbs, sugar, and protein and fibre in both directions.
  6. **Check (JEV):** `noul` asks whether the candidate is a reasonable substitute (same kind of meal, similar main ingredient). Unsure or JEV unavailable means it is not offered.
  7. **Say it (template):** "Your Chicken rice (regular), 4 times, about 689 kcal, is the heaviest. Next time, try Steamed chicken rice instead: it saves about 204 kcal and 4 g sugar; protein goes from 39 g to 19 g." The model writes none of the numbers.
- **Where it shows:** Home ("Worth a look"), the lunch ideas and the reminder before the mealtime, and the high-salt prompt (LL9). It does not appear on the meal logging screen.
- **Wording:** an idea for next time, never "bad food", never advice. The person's logged meals are never changed.
- **Closing the loop:** which suggestions are chosen is counted in `nudge_policy` (15% exploration); when the person later logs the swapped dish, the new logged numbers (and measured rise, if a sensor is worn) show whether it worked for them.
- **AC:** the numbers on a suggestion come from the person's logs and the shelf row, side by side; "lighter" always names what is lower; protein trade-offs are shown, not hidden.

### LL5 Lunch-time suggestions
- **When:** the lunch window is learned from the person's own lunch log times, with a default of 12:00 to 13:30. One nudge, about 30 minutes before.
- **What:** up to 3 options that suit the person: their own best lunches (lowest measured rise, not eaten yesterday), then dataset dishes similar to what they usually choose but lower in carbs and sodium. Salt is weighted more when blood pressure flags are open.
- **Learns:** "I'll have this" and "Not today" feed the nudge policy; a suggestion that is never taken is shown less.
- **Honesty:** options, not instructions. No claim about what a nearby stall sells. Each option shows why it is suggested.
- **AC:** capped at one lunch nudge a day; every suggestion cites its source (own history or dataset row).

### LL6 Your own glucose feedback
- Compare the person's after-meal rise on days a routine was followed versus not, from `meal_response` and `medication_log`. Wording is "associated with", always with n; it stays silent below 5 days per side.
- **AC:** no causal wording; sample size always shown.

### LL7 Preventive nudges with learned wording
- Due and overdue items from `patient_preventive_status` surface with the wording the person has acted on before. Nothing is booked without explicit confirmation (F13).

### LL8 "What I learned this week"
- A weekly digest of every fact, anchor, flag and policy change, with evidence, and one tap to veto. Extends F16.

### LL9 High-salt day: swap first, gentle activity second
- **Detect (code):** the day's sodium from `food_logs.sodium_mg` (the numbers the person logged), compared with a placeholder daily limit and a per-meal limit (`meal_high_sodium_mg`). Both are **pending clinical review**.
- **First response is food, not exercise:** the lower-sodium alternative from LL4 for next time. The sodium source (soup, gravy, sauce) is named when the dataset item shows it.
- **Second, an optional gentle activity prompt**, 30 to 60 minutes after the meal: "an easy 10-minute walk". Where the person has data, the line is theirs ("on days you walked after eating, your glucose rose less, n = 6") from `exercise_response` and `meal_response`; where they do not, it says only that a short easy walk is a good habit and to check with the doctor if unsure. No claim that exercise cancels salt.
- **Gates (code, all must pass):** no open urgent or review flag in `clinical_flags`; no low glucose (`glucose_zone`) in the last 2 hours and no `shaky_sweaty` or `dizziness` symptom in the last 3 hours; not in sick-day pause; daytime only; at most one a day; never framed as "burn it off" or as a penalty. A recent high blood-pressure reading turns the prompt into "worth mentioning to your doctor", not exercise.
- **Learns:** whether the prompt was opened and followed by an `exercise_logs` entry; if never acted on, it is shown less (`nudge_policy`).
- **AC:** the prompt names the meal that triggered it and the data behind any claim; light activity only; the gates are tested.

## 4. Where JEV fits

JEV is a fast typed classifier called by our code at four checkpoints; the agent is only one caller.

| Checkpoint | Question to JEV | Low confidence or JEV down |
|---|---|---|
| Before the agent | Is this asking for medicine advice, a diagnosis, or is it urgent? | Treat as yes (refusal or urgent path) |
| Memory read | Which memory does this need? Which facts are relevant? | Default route, small limits |
| Memory write | What kind of fact is this? Does the evidence support it? | Store as `context` and `proposed`; drop the statement |
| After the agent drafts | Does the draft give medicine advice or a diagnosis? | Block the draft |
| Food type (LL4) | What type of meal is this name? | Type `other` (never grouped into a habit) |
| Substitute relevance (LL4) | Is this candidate a reasonable substitute for the usual meal? | Not offered |

## 5. Guardrails the learner cannot touch

1. Rules fire first and always win over JEV or learned values.
2. The guard questions are versioned **code**, not data. No learning path can write to them.
3. JEV only classifies and ranks. It is never asked to bypass or relax a guard.
4. `safety_flags`, urgent items and interaction alerts always reach the evidence packet, whatever the ranking says.
5. The learner writes only to: proposed facts, `nudge_policy` values inside allowed ranges, and `content_proposals`. It cannot change doses, schedules or thresholds.
6. Every agent-drafted word passes the output guard before entering the proposed queue.
7. **Invariant test:** run the red-team prompt set with learning on and off; the guard verdicts must be identical, and the build fails if they differ.
8. Every step is written to `agent_runs`, `agent_steps` and `guardrail_events`.

## 6. Data

Reuse what exists: `memory_facts`, `memory_episodes`, `pattern_candidates`, `notifications`, `refill_forecasts`, `preventive_items`, `patient_preventive_status`, `guardrail_events`, `agent_runs`, `agent_steps`, `adherence_summary`, `meal_response`.

Proposed additions (**need team approval; the schema is shared**):

| Change | Layer | Holds |
|---|---|---|
| `nudge_policy` | Gold / Operations | per person: slot, template, tries, acts, last updated |
| `adherence_barriers` | Gold | per person per week: barrier kind, count, evidence ids |
| `content_proposals` | Operations | agent drafts waiting for approval: kind, text, guard verdict, status, reviewer |
| Singapore food rows in `foods` (2,689) | Reference | existing columns plus `subgroup`, `sat_fat_g`, `potassium_mg`, `source_grade`, `data_year`, `embedding` (section 12.1) |

## 7. How it is measured

All targets are pilot hypotheses, not claims. The proof is a replay of Mr Tan's 91 days (`scripts/replay.py`) and the week-1 versus week-8 view.

| Measure | Target hypothesis |
|---|---|
| On-time dose rate, before and after the loop learns the routine (same days) | up, shown with the method |
| Miss-reason capture | 60% or more (PRD) |
| Nudge act rate by slot, with and without learning | up |
| Swap or lunch suggestion accepted | tracked, no target yet |
| Measured rise after an accepted swap | lower, shown with n |
| Substitutes judged reasonable by a reviewer on a sample of about 50 habits | at least 85% (placeholder) |
| Guard verdicts with learning on versus off | identical (100%) |
| Medicine-advice leakage in the red-team suite | 0 |

## 8. Plan to 16 October

| Order | Slice | Why this order |
|---|---|---|
| 1 | LL4 food habit and the shelf of lighter dishes | Real data supports it today; strongest demo |
| 2 | LL5 lunch suggestions | Reuses LL4 ranking |
| 3 | LL1 outcomes and nudge policy, LL2 anchoring | Needs the scheduler |
| 4 | LL3 barriers, LL6 glucose feedback, LL8 digest | Mostly queries over existing tables |
| 5 | LL7 preventive wording; invariant test and replay evaluation | Closing and proof |

## 9. Decisions needed from the team

| Decision | Suggested owner |
|---|---|
| Approve the three new tables and the `foods` extension | Hong Yi, with Joely |
| Flag thresholds (*N*, *X*), the daily and per-meal sodium limits, the LL9 gates and the lunch window default (clinical review pending) | Damien |
| Confirm the dataset's licence and publisher before it is cited in the pitch | Joely |
| Who reviews the swap list and agent-drafted wordings | Damien |
| Licence and quality check of the hawker dataset after profiling | Joely |
| Confirm D-004 stays: bounded learner plus a gated proposed queue | Whole team |

## 10. Key capabilities (what the agent can do)

1. **Remembers the person**, with evidence: facts about routines, barriers, food responses and preferences, each with confidence, version and a delete button (`memory_facts`, F16).
2. **Anchors medicine to the morning routine** using real logged events, with a fixed-time fallback.
3. **Finds adherence barriers** from the pattern of misses and the reasons given, and reports them to the doctor.
4. **Reads a meal photo** (Gemini on Vertex AI) and logs the calories and macros from the image. The food database never replaces those numbers.
5. **Notices a food habit** (a type of food eaten often and high in what the person logged) and **recommends similar, lighter dishes for the next meal** from the Singapore food database, with exactly what they would save (calories, salt, carbs, sugar) and what changes in protein.
6. **Suggests lunch** that suits the person at their usual lunch time.
7. **Responds to a salty day** with a swap for next time and a gated, gentle walk prompt.
8. **Shows the person's own glucose feedback** ("associated with", with n).
9. **Adapts timing and wording** per person (bandit), within caps and quiet hours, and measures whether each nudge worked.
10. **Drafts, never publishes:** new wording or routines go to a proposed queue.
11. **Explains itself** with a weekly digest, and logs every step (`agent_runs`, `agent_steps`, `guardrail_events`).
12. **Cannot touch its own guardrails** (section 5), proved by an invariant test.

## 11. Agents

Architecture image: [img/learning-loop-architecture.svg](img/learning-loop-architecture.svg) (real table names, `*` = proposed new).

| Agent | Role | Reads | Writes |
|---|---|---|---|
| **Orchestrator** (main) | Routes each event to one sub-agent (JEV `choice`), assembles the evidence packet, enforces caps and quiet hours | `notifications`, `memory_facts` (via Memory Service) | `agent_runs`, `agent_steps` |
| **Adherence agent** | Reminders, morning anchoring, barrier identification | `medication_log`, `medication_schedule`, `refill_forecasts` | `notifications`, `adherence_barriers*` |
| **Nutrition agent** | Notices food habits, offers lighter dishes for the next meal, lunch suggestions. Sub-steps: *Meal vision* (Gemini, logs the numbers), *Habit finder* (JEV food type, code counts), *Swap ranker* (code over the food database, JEV relevance check) | `food_logs`, `foods`, `meal_response` | `memory_facts` (proposed), `notifications` |
| **Activity agent** | High-salt walk prompt, movement nudges, gates | `food_logs`, `exercise_logs`, `exercise_response`, `blood_pressure_readings`, `clinical_flags` | `notifications` |
| **Preventive agent** | Screening and vaccination nudges with learned wording | `preventive_items`, `patient_preventive_status`, `appointments` | `notifications` |
| **Reflection agent** (nightly) | Reads outcomes and aggregates, **proposes** facts, wording and policy changes. Never activates them | `daily_summary`, `notifications`, `meal_response` | `memory_facts` (proposed), `content_proposals*`, `nudge_policy*` |

Not agents: the **input and output guards** (frozen code plus JEV `noul`), the **Swap ranker** and all calculations (code), the **scheduler** (rules).

## 12. Technical depth

### 12.1 The food dataset (profiled 2026-10-06)
- **Is it worth expanding? Yes.** `food_nutrition_sgfoodid_combined_202607.csv`: 2,689 rows, 94 columns, no duplicate names, per-100 and per-serving values; the hawker file is a subset (1,163 rows). Per-serving fill rates: energy, carbs, protein, fat 100%; saturated fat 98%; sugar 91%; fibre 88%; sodium 89%. Sources: lab analysis 999, borrowed 784, derived 519, label (NIP) 387. Years: mostly 2025 and 2026, but 438 rows are from 2010.
- **Covers:** laksa, char kway teow, nasi lemak, yong tau foo variants, prata, bak chor mee, economic rice, chicken rice in 6 variants. **Gaps:** oats and congee (hawker file), several composite sets, and about a tenth of rows lack sodium or fibre.
- **Why the database is not used to log meals:** the photo model lists ingredients and portions of the actual plate, while the database holds dishes at a typical serving. Replacing the plate's numbers with a typical row would make the log less true. The shelf is therefore used only to look for lighter, similar dishes.
- **Worked alternatives (Mr Tan, his own logged numbers against the shelf):** noodle habit (char kway teow, about 869 kcal logged): vegetarian kway teow saves about 247 kcal, 577 mg salt and 16 g carbs, protein goes from 18 g to 12 g; beef ball kway teow soup saves about 241 kcal and 467 mg salt, protein goes from 18 g to 38 g. Demo user, fried chicken with fries four times: grilled chicken salad saves about 174 kcal and 735 mg salt.
- **Import:** normalise (`-` to null, `Trace` to 0, parse `1 plate(s) = 363g` to `serving_g`), keep the source grade and year, embed name plus description and subgroup (768 dimensions), and load into `foods`. `foods` already has `serving_g`, `kcal`, `carbs_g`, `sugar_g`, `fibre_g`, `protein_g`, `fat_g`, `sodium_mg`, `category`, `aliases` and `locale_names`; add `subgroup`, `sat_fat_g`, `potassium_mg`, `source_grade`, `data_year` and `embedding`. The existing 53 Open Food Facts rows stay, marked as packaged.
- **Open before use:** the dataset's licence and original publisher must be confirmed and written into `data_sources`; the Kaggle page is the only provenance seen so far.

### 12.2 Swap ranking (code only)
Candidates are rows in the same category and subgroup, with energy within 25% of the source serving. A candidate must improve at least one target nutrient by 20% or more and worsen none by more than 15%. Targets follow the person: sodium first when a blood-pressure flag is open, carbs and sugar first when measured rises are high. The score is a weighted sum of relative changes (weights are placeholders). Where the person has measured rises for both dishes (n of 2 or more), the measured rise outranks any table value. The model only phrases the result.

### 12.3 Lunch suggestion
Window learned from the median start of logged lunches (default 12:00 to 13:30); one nudge about 30 minutes before. **One lunch slot a day** (fix wave, 2026-10-11): the "Log your lunch" reminder and the lunch ideas write to the same slot (`scheduler.lunch_slot_keys`); whichever is stored first takes it, and a lunch already logged for the day counts the day's lunch idea as done. Pool: first the lighter dish for a habit the loop noticed ("instead of your usual ..."), then own meals with measured rise below the person's median, then general hawker ideas for people with no history. Filters: not eaten in the last 2 days; sodium cap when a blood-pressure flag is open. Rank: own evidence, then nutrient fit, then novelty. A suggestion counts as acted on when the person taps "I'll have this" (recorded in `nudge_policy`).

### 12.4 Scheduler and agents
One scheduler tick per minute evaluates rules against the database (idempotent by a payload key, as `notifications` already does) and a nightly 02:00 job runs the reflection. Each agent is a LangGraph graph whose only tools are Memory Service functions and the decision gateway; none has free SQL. Time zone is Asia/Singapore.

### 12.5 AI cost and failure modes
Model calls happen only for photo reading, wording and the nightly reflection, under the daily call and budget cap already in the environment settings. JEV down: the safe path for every decision. Vertex down: the photo cannot be read and the person is told, other features keep working. Dish not in the dataset: the item falls back to the AI estimate, labelled as such.

### 12.6 Testing
Unit tests for the swap rules and the shelf; a test that no code path used to log a meal reads the food database; state tests for the memory lifecycle; the guard invariant test (learning on versus off); a gate test for LL9; and the Mr Tan replay for the week-1 versus week-8 comparison.

## 13. Out of scope

Autonomous prompt or rule rewriting; exercise framed as compensation or punishment for food; vigorous exercise prompts; dose or schedule changes; diagnosis; any claim that a food or action *causes* a glucose change; booking appointments without confirmation; menus or availability of specific stalls; caregiver alerts (stretch).

## 14. Build status (2026-10-06, local only)

**Design correction applied (owner, 2026-10-06):** the first build matched logged meals to database dishes and offered the database numbers. That was removed. Logged numbers are always the photo model's (or the person's). The database is a shelf for lighter dishes only. Unit test `test_logging_a_meal_never_touches_the_food_database` enforces it.

**Built and verified against the real database, Vertex AI and JEV:**
- Migrations `0021` and `0022` (additive; 0022 also widens the `agent_runs.trigger` check and drops the unused `food_matches`): new `foods` columns, `nudge_policy`, `adherence_barriers`, `content_proposals`; 2,689 Singapore food rows imported with 768-dimension embeddings (`scripts/import_sg_food.py`), the 1,163 hawker rows flagged `hawker`. Licence still unconfirmed in `data_sources`.
- **Orchestrator** (`app/agents/orchestrator.py`): a LangGraph graph that routes each event to one sub-agent by rule (or by JEV `choice` for free text, unrouted below 0.6 confidence). Every run and step is written to `agent_runs` and `agent_steps`; proposals, confirms, edits and deletes are appended to the hash-chained `event_log`.
- **Scheduler** (`app/services/scheduler.py`, APScheduler): a reminder tick every minute (quiet: only changes are traced) and a nightly 02:00 reflection with catch-up after a restart, both through the orchestrator, for Mr Tan (`SCHEDULER_USERS`) and every person who finished set-up (the demo user was removed on 2026-10-14).
- JEV gateway (`app/llm/jev.py`): `noul`, `choice`, `score`, batch calls, de-identification, conservative path, and the three frozen guard questions (`GUARD_VERSION`).
- Food habit loop (`app/agents/food.py`, `app/db/nutritionstore.py`): JEV food types, habit rule over the person's logged meals, shelf search, comparison against the person's own logged numbers, JEV substitute check, savings including protein; habits proposed as memory facts.
- **Memory lifecycle** (`app/db/memorystore.py`, `/memory/*`): list, confirm, edit (new version, in the person's words) and delete; a deleted idea is never proposed again, and the agent never supersedes a fact the person confirmed or edited (unit-tested with a fake connection).
- **Screens:** Me (K1), What Smart Health has learned (K2) with the weekly digest (LL8), the audit list and per-fact "why"; How it is going (K10) with first-two against latest-two weeks; Home cards for the habit, lunch ideas and "Smart Health noticed something".
- Lunch ideas (E8) with an "instead of your usual" tier; LL9 high-salt prompt with gates; learning policy in `nudge_policy` with 15% exploration.
- Adherence agent (barriers, anchor rule, proposals that stay `proposed`) as a replay: `python scripts/run_learning_replay.py`.
- 50 unit tests (`tests/unit/test_learning_loop.py`).
- Fixed on the way: saving an identical entry twice returned a 500 (Bronze is unique per person and content; it now reuses its row); the nightly job re-proposed a deleted fact because an edit flag broke the comparison.

**Findings worth knowing:**
- Mr Tan's habits (his own logged numbers): rice dishes 15 times, bread or pastry 12, soup or porridge 9, noodle dishes 6. Lighter dishes were found for rice (steamed chicken rice) and noodles; none passed the checks for bread (database rows are per slice, far below a meal) or soup.
- Mr Tan's morning dose is scheduled at a fixed 8:00 and his breakfast ends anywhere from 7:00 to 10:10, but on-time rate is the same on late-breakfast days (87% against 89%). The anchor rule correctly proposes nothing for him.
- The weekend-evening miss pattern is not clearly above the rest of the week, so it is not proposed. The barrier pattern is clear: forgot 43, felt fine 16, away from home 15, ran out 4.

**Built since (2026-10-07):**
- **Daily cap and quiet hours** (`nudge_daily_cap` 3, quiet 22:00 to 07:00 Singapore time): they apply to new extras only; dose reminders (keys `dose-`) and urgent messages (`urgent-`) are exempt. A sick-day pause is **not** used: nudges carry on, and only the walk prompt keeps its safety gates (owner decision, 2026-10-07).
- **"Not for me"** on lunch ideas and the Home habit card: a dismissed suggestion, or one shown six times and never chosen, is not shown again.
- **Closing the loop on swaps:** if the person has since eaten the lighter dish, the habit card compares it with the usual one using their own logged calories and salt, and their own measured rise when a sensor was worn (at least 2 meals of each); association only, honest when it is the same or worse.
- **Open (2026-10-11, Hong Yi's rule):** the barrier rule in `services/api/app/agents/adherence.py` still writes "Some missed doses were because of ... (n times)", counting missed doses with a reason over all time (`barrier_weeks` has no date window). Only the `barrier.ran_out` fact is hidden on K2. Not changed in this pass; Hong Yi to decide.
- **AI usage and cap:** `ai_usage_daily` (migration 0023) counts calls, tokens and cost per day and per kind of call. From 2026-10-11 there are four kinds (migration 0034 added text the person sees): photo and label reads (`vertex_vision`, `AI_CAP_VERTEX_VISION`, 300 a day; the medicine label scanner's reads are counted here too, and a refused read returns `daily_limit`), text the person sees (`vertex_generate`: brief findings, medicine explainer, clash checker, chat and onboarding answers; `AI_CAP_VERTEX_GENERATE`, 500 a day), background embeddings (`vertex_embed`, `AI_CAP_VERTEX_EMBED`, 2,000) and JEV (`AI_CAP_JEV`, 500). **Each kind has its own cap**, so one kind being used up never blocks another. A kind with no cap of its own uses `ai_daily_call_cap` (500). When a kind reaches its cap, its calls are refused, the refusal is counted against that kind only, and its caller takes its conservative path (decision D-082). `ai_daily_budget_usd` (5) applies to each kind's own cost. Agent runs record their tokens and model; each photo read is its own run. The guard asks its three questions in one JEV request. Gemini is not priced yet, so cost is only counted for JEV.
- **Safety:** the words the photo model writes back (meal name, portion note) now pass the frozen guard. The red-team set (`tests/redteam/prompts.py`, `scripts/run_redteam.py`) has 44 cases in English, Chinese, Malay and Tamil; result 0 leaks and 0 false blocks (small set: a baseline, not proof).
- **Reviewer sheet** (`scripts/make_review_sheet.py`, scored by `scripts/score_review_sheet.py`) for the 85% reasonable target.
- **Tests:** 60 unit tests and 9 API integration tests (`RUN_INTEGRATION=1`, real database as the demo user, model calls replaced).
- Dataset licence recorded in `data_sources`: CC0 Public Domain as declared on Kaggle by the uploader; the original compiler is not named.

**Decisions (owner, 2026-10-07):** dose reminders may only fall from the recorded dose time to 60 minutes after (after-meal medicines never before the meal is finished); the three-a-day cap exempts dose and urgent messages; quiet hours 22:00 to 07:00; the review screen for team-written wording waits until the agent drafts wording; languages are done for nudges and the new screens first, then the rest of the app.

**Not built yet:**
- Medicines in the app (E3-2 save, today's doses, "taken" taps, refill), then the **dose-reminder bandit** inside the allowed window and **live morning anchoring** (Mr Tan's data shows no stable anchor, so this needs a synthetic persona).
- **Barrier to action** (earlier or second reminder, refill reminder, doctor question).
- **Glucose feedback** (LL6) and **preventive nudges** (LL7; the preventive agent node is a stub).
- **Doctor brief** items ("worth discussing") and the brief screen.
- **Four-language** nudges and new screens (English only today); then the rest of the app.
- **Urgent screen (J1) and Your day (D1).**
- A reviewer's ratings on the sheet (target 85% reasonable), and a larger red-team set.
- Review screen for team-written wording drafts (postponed); thresholds are placeholders pending clinical review.
- Run the scheduler safely with more than one API worker; Vertex service-account login.
