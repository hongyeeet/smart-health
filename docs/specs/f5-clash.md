# F5 Medicine clash box: how it works and what is open

**Status (2026-10-08): F5 clash flagging done (approved by Joely).** Updated 2026-10-11: the doctor questions are on K12, the AI calls are counted under `vertex_generate`, and the Meds page checks for the result every 3 seconds only while a check is running (fix wave). Nothing about how a pair is flagged changed. Decided by Joely. It departs from the team's rule that interactions are never decided by an AI (see section 6): Hong Yi has not confirmed that yet.

## 1. What the person sees (Meds page, H1)

Right below the blue "may run out" box. **No box when nothing may clash.** When two saved medicines may clash:

- Title: "Medicines may clash. Check with your doctor."
- For each pair: the fixed sentence "Possible interaction between X and Y. Please check with your pharmacist or doctor before continuing.", then one or two plain sentences on why, where it came from (the drug-label link and/or the web pages the AI used), and "Not medical advice".
- Two buttons: **Add to my doctor questions** (saves "Is it OK to take X and Y together? They may interact." to the doctor-question list; asking twice saves it once, and after it is saved the button turns into "Added to your doctor questions" with a green tick, which stays after a reload. The question shows on the doctor-question page (K12, built 2026-10-11, reached from Me and the care plan K3)) and **I have checked with my doctor** (the box for that pair goes away; the alert is kept as acknowledged).
- An AI flag with no web page found says so: "No web page was found for this. It is an AI suggestion, so please check it with your pharmacist."
- While a check runs: "Checking your medicines for clashes…". If the AI half could not finish and nothing else is flagged: "We could not finish checking for clashes. This is not the same as all clear." with a **Check again** button. The box never says to stop a medicine and never says anything is safe. Supplements and herbal products keep their "Not checked" badge.

## 2. When it runs

Every time a medicine is saved (typed in with `POST /medications`, or confirmed from a scan with `POST /scans/{id}/confirm`), the app runs a check in the background right after the response. The check always looks at **all** the person's saved medicines, not just the new one. It takes about 10 to 45 seconds; the Meds page asks for the result every 3 seconds **only while a check is running** (it stops when the check finishes), so the box appears by itself. `POST /interactions/check` runs one on demand (used by "Check again").

## 3. The two ways a pair is flagged (either is enough)

| Half | How | Strength |
|---|---|---|
| **Drug-pair rules** (`interaction_rules`, 238 pairs from the openFDA drug labels, D-036) | Each medicine is matched to a drug by name in code: the drug's generic name (or a short alias) must appear in the medicine's name as whole words, or the medicine is already linked to a drug. A brand name with no generic in it (CRESTOR) is not matched | Deterministic. Always runs and is always saved, even if the AI part fails |
| **The AI model with a web search** (Gemini with Google Search, `app/agents/clash_checker.py`, instructions `prompts/clash_check.md`) | Given the numbered list of names, strengths and types (no personal details), it names pairs by number with a reason | Can only **add** a flag. It can never remove one the rules found |

Checks on what the AI says, in code:
- A number outside the list, or a medicine paired with itself, is dropped. Reasons that use the list numbers ("6 can raise the level of 2") get the medicine names put back.
- Any sentence with a dose, or telling the person to stop, skip, change or swap, or calling something "safe", is dropped (the same filter as the medicine explainer).
- **Flags need a web page.** If the model names pairs without one, a second call (`prompts/clash_verify.md`) is made with search on about exactly those pairs. Pairs it confirms are kept (with the page if the search found one, otherwise labelled as an AI suggestion). Pairs it does not confirm are dropped. If that second call cannot be made, the flags are dropped and the check is reported incomplete. A single unchecked answer from memory is never kept.
- A daily AI limit or an AI outage never blocks the rules half.

## 4. Saving

`interaction_alerts` (Gold; migration 0028 added `origin` database, ai or both, `summary`, `sources` and `model_id`, and a unique index so a pair has one alert whichever order it is stored in). New alerts are `open`. A later check strengthens an alert (database plus AI becomes `both`; the AI's newest reason replaces its older one; the database never overwrites the AI's reason) and never removes one. An alert disappears from the box when the person acknowledges it or a medicine is deleted. Event log entries `interaction.checked` (counts and codes), `interaction.alert.raised`, `interaction.alert.acknowledged` hold ids and codes only, never names or reasons.

## 5. Where things are

| What | Where |
|---|---|
| Rules half, saving, listing, buttons | `app/services/clash_store.py` |
| AI half and its checks | `app/agents/clash_checker.py`; instructions `prompts/clash_check.md` (v3) and `prompts/clash_verify.md` (v1) |
| Running a check (one at a time per person) | `app/agents/clash_pipeline.py` |
| Routes | `app/api/routers/interactions.py`: `GET /interactions`, `POST /interactions/check`, `POST /interactions/{id}/question`, `POST /interactions/{id}/acknowledge` |
| Screen | `apps/web/src/features/meds/ClashBox.tsx` in `MedList.tsx` |
| Replay for a person's medicines in the order they were started | `scripts/replay_clash_checks.py --user mr-tan [--reset]` |
| Try the AI on made-up lists with known answers | `scripts/try_clash_lists.py` |
| Tests | `tests/unit/test_clash_checker.py` (22), `tests/db/test_clash_store.py` (18) |

## 6. Why this is a departure, and what protects the person anyway

`rules.md` rules 2, 7 and 14 and the PRD say interaction checks are a database lookup, never an AI guess, and that an AI can only rephrase a confirmed hit. Joely decided on 2026-10-08 that an AI model should study the medicines and flag possible clashes, with the database as a second source. What keeps this safe: the database half always runs and cannot be overruled; the AI can only add a flag, never remove one; the wording is fixed and says "may" and "check with your pharmacist or doctor", never "stop" or "safe"; a check that could not finish says so instead of looking like all clear; every flag is labelled with where it came from. **Hong Yi should confirm the departure from the rules**, and `rules.md` and PRD F5 should then be updated by him if he agrees.

## 7. Tried on 2026-10-08

- **Mr Tan, replayed one by one in the order started** (Metformin, Amlodipine, Atorvastatin, Fish oil, the herbal tonic, then Clarithromycin): no box at steps 1 to 5 (the AI looked each time and found nothing); at step 6 the box shows Clarithromycin with Atorvastatin and Clarithromycin with Amlodipine, each found by both the rules and the AI. His medicines and 90-day dose history were not touched.
- **Demo account** (CRESTOR, then Clarithromycin typed in): the background check ran by itself after the save; the AI flagged the pair, a brand-name pair the rules cannot match, with an nih.gov source; the two buttons worked. The test medicine was then removed.
- **Seven made-up lists with known answers:** Warfarin with Aspirin, Simvastatin with Clarithromycin, CRESTOR with Gemfibrozil flagged; a plain Metformin, Amlodipine and Atorvastatin list, an unreadable herbal product, and supplements with paracetamol not flagged. Extra real interactions the AI added (Simvastatin with Amlodipine, Clarithromycin with Amlodipine) are genuine. **Missed once:** Ginkgo with Warfarin (the model could not confirm it with a reliable page), so the page said the check could not finish rather than showing nothing. The AI's answers differ a little from run to run: the same list gave a flag once and none another time (Amlodipine with Atorvastatin).
- **Found and fixed while testing:** a source link lost when the AI added its reason to a rules alert; flags dropped because the search sometimes returns no page; reasons written with list numbers.

## 8. Not built, and open

- Hong Yi's confirmation of the departure (section 6).
- The box on Home. (The alerts page and the "Possible interaction" details page were added on 2026-10-09, section 9.)
- A way to un-acknowledge, and a recheck when a medicine's name is edited (there is no edit screen yet). Deleting a medicine removes its alerts, but nothing re-runs the check for the rest.
- A pharmacist's review of the prompts and a sample of results.
- The AI is not repeatable: the same medicines can give slightly different flags on different runs. The rules half is repeatable.
- Cost: each check is one to three Gemini calls with search, counted under `vertex_generate` (text the person sees, its own daily cap `AI_CAP_VERTEX_GENERATE`, default 500; this kind of call was added to the daily limit on 2026-10-11, migration 0034). Before 2026-10-11 the same calls were counted under `vertex_vision`; older rows are not moved.

## 9. Alerts page and details page (added 2026-10-09, Damien's alert design)

Built from Damien's notification design (a Stitch export) on top of the same alerts. Nothing about how a pair is flagged changed.

**Alerts page (B2, `/notifications`, was "Reminders").** Now "Notifications and alerts": open clash alerts on top, then the reminders, with filter chips (All, Medicines, Reminders) and a "mark all reminders as read" button. The bell on Home counts open alerts as well as unread reminders. Each alert is a card with:

- the tag "Medication review", the time the alert was raised, the two medicines joined by a "Possible interaction" marker;
- the fixed sentence from the server (section 1), unchanged;
- a note: "This alert does not mean the two medicines are unsafe together. Smart Health cannot advise on your medicines; your pharmacist or doctor can.";
- **Review interaction** (opens the details page), **Contact clinic** (says Smart Health has no clinic or pharmacy number yet and to use the one on the appointment card or medicine label), **Ask a question** (a text box; the question is saved in the person's own words to the doctor-question list);
- **Dismiss for now and add to my doctor questions**: saves the ready-made question for the pair and hides the card on this device, with **Restore**. The alert stays `open` on the server and in the Meds page box until "I have checked with my doctor" is used there.

**Details page (H5, `/meds/interaction/:id`, was planned as a sheet).** The pair and the fixed sentence; where the flag came from (drug-label rules, AI web search, or both) with the tag "Not reviewed by a clinician"; "Why this was flagged" (the server's `summary`); a suggested next step ("Ask your pharmacist or doctor to review your medicines... bring your full medicine list"); the same contact, add-question and typed-question actions; and the sources behind a fold. The Meds page box has a **Review interaction** button that opens it.

**Left out of the design, and why.** A severity grade and "verified source" label (nothing is clinically reviewed, rules.md 1.15; the origin is shown instead). The pharmacology paragraph and the report line "consider an alternative" medicine (medication advice and uncited health content, rules.md 1.1 and 1.9). "Do not stop or change your prescribed medicines" and "stopping abruptly can lead to..." (design.md section 9 counts "you should not skip your dose" as advice; the note above replaces it). Care-team notes, pharmacy pick-up cards, a clinic hotline and the "DiaCare" name (Smart Health has no care-team or pharmacy link). The report download (waits for the doctor brief, L1). "New" and "Active" tags on each medicine (the alert does not carry them).

**API changes (small, additive).** `GET /interactions` alerts gain `raisedAt` (the alert's `created_at`). `POST /interactions/{id}/question` accepts an optional body `{"text": "..."}`: with it, the person's own question is saved (`origin = 'user'`, every time, 3 to 500 characters) and the ready-made question is untouched; without it, behaviour is as before.

**Where things are.** `apps/web/src/features/alerts/` (`InteractionCard.tsx`, `InteractionDetail.tsx`, `pieces.tsx`), `apps/web/src/features/home/Notifications.tsx`. Test added: `tests/db/test_clash_store.py` (typed question and `raisedAt`); **it was written but not run**, because the session had no database connection.

**Open.** The wording of the note and the next step needs the same pharmacist or clinician review as the rest of F5. "Dismiss for now" is per device; a server-side state (and un-acknowledge, section 8) would make it follow the person. Events for the new actions are not in flow.md section 4 and are not emitted.
