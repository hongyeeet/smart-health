# Questions for Damien (clinical review)

Written for Damien on 2026-10-03 by Hong Yi's assistant. Damien is the team's doctor. These are the clinical points that must be settled before the work they affect is built. **The related work is on hold** (decision D-054): tasks E1-7, E11-2, E7-4 and E13-4, plus the low-glucose tiers, emergency contact and symptom changes in [prd.md](../specs/prd.md) F6, F10 and F12.

Where we stand: the clickable mock in `apps/mock` already shows the changes so you can see them (run `cd apps/mock && npm run dev`, then use the Demo panel to open the low-reading screens). Nothing is built in the real app, and nothing is in the database. Every number below is a placeholder, not advice, and is marked "clinical validation pending".

**How to answer:** reply in this file or in chat with the number and your decision. A one-line answer is enough. Where you think our placeholder is right, just write "agree".

## A. Low-glucose alerts (prd F10, flow J8)

Background from the feedback we received: below about 4 mmol/L people start to feel lightheaded but can still treat it with sweets or sugar; below 3.0 they may be unable to function; around 2.8 they may faint or be unconscious.

| # | Question | Our placeholder now |
|---|---|---|
| A1 | Are these the right alert levels for adults 45 to 65 with type 2 diabetes: tier 1 "low" below 4.0, tier 2 "very low" below 3.0? Should tier 1 be 3.9 (the usual "level 1" line)? | Tier 1 below 4.0, tier 2 below 3.0. Time in range stays 3.9 to 10.0 |
| A2 | Our demo patient takes metformin, amlodipine and atorvastatin, which rarely cause lows. Should low alerts switch on only for people on medicines that can cause lows, or for everyone with a sensor? | Everyone, for now |
| A3 | What may the app say on the tier 1 screen about treating a low (which fast sugar, how much, what next)? We have no approved source, so today it only says to take the fast-acting sugar listed in the patient's own doctor's low-sugar plan | A pointer to the doctor's plan, no amounts |
| A4 | Is a 15-minute recheck right? If the reading is still below 4.0 after the recheck, do we move to tier 2, repeat the recheck once, or call the clinic? | Still low, "same" or "worse", or no answer moves to tier 2 |
| A5 | On the very low screen, what should we say besides "call 995 or the clinic" (do not be alone, do not drive, sit or lie down)? | "Get help now", call buttons, follow the plan's first steps if you can |
| A6 | Night-time lows: should a sleeping patient's very low reading alert the contact straight away? | Same as daytime |
| A7 | Is the list of "get help now" symptoms complete? We have chest pain, confusion, fainting, breathlessness at rest, and sudden vision loss or a curtain across the vision. What else belongs (for example one-sided weakness, drooping face, severe abdominal pain)? | The five listed |
| A8 | Vomiting together with high glucose should say "get care today". What glucose number should count as high here, and what should the screen say? | No number set. The configurable "high" threshold is not decided |
| A9 | What value should count as repeated high readings that need care today (how high, how many, over what time)? | Not decided (`HIGH_URGENT` is a placeholder) |

## B. Emergency contact (prd F10, A14)

| # | Question | Our placeholder now |
|---|---|---|
| B1 | Is it appropriate to alert one named contact on a very low reading, by message and email at once and a phone call if there is no reply in 5 minutes? Is 5 minutes right? | Yes, 5 minutes |
| B2 | What may the message say? We keep it to one sentence and share nothing else | "Mr Tan's glucose reading is very low. Please check on him now, or call 995." |
| B3 | Should the contact also have to agree to being alerted, or is the patient's consent enough? | The patient's consent only |
| B4 | For a tier 1 low, should the contact be alerted only if the 15-minute check-in goes unanswered and the reading is still low? | Yes |

## C. Symptom logging (prd F6, F9)

The new form fills in the sensor glucose and trend at the time, lets the person say when it happened (just now, earlier today, last night, a set time), and offers optional detail. It never names a cause.

| # | Question | Our placeholder now |
|---|---|---|
| C1 | Are these detail fields the right ones and enough: how long it lasted (a few minutes, about an hour, most of the day), left or right side for numbness and pain, relation to a meal or exercise? Anything missing? | As listed |
| C2 | For dizziness we ask what it felt like (when I stand up, shaky or sweaty, spinning) so the doctor can tell low glucose from low blood pressure on standing. Is that wording useful and safe, and should we also ask for a blood pressure reading? | The three choices, no blood pressure prompt |
| C3 | Night sweats and disturbed sleep are logged in the morning. Is "last night" enough, or do you want a time? | "Last night" or a set time |
| C4 | Which symptom questions should the app ask unprompted (the F9 check-ins, for example feet tingling, thirst, passing more urine), and how often? We cap it at one a day and three a week | One a day, three a week |
| C5 | Hypoglycaemia awareness: we ask once after a low, "Did you feel it before your sensor alerted you?" Should we use a validated questionnaire instead, how often, and how should the doctor see the answer? | One question after each low, shown as a self-report in the brief |

## D. Doctor brief (prd F12)

| # | Question | Our placeholder now |
|---|---|---|
| D1 | We now draw fasting glucose, resting heart rate and SpO2 on the same dates. Is that useful in a 10-minute consult? What other watch data would you want beside glucose (sleep, steps, heart rate variability)? | Glucose, resting heart rate, SpO2 |
| D2 | SpO2 is simulated in the demo. Which SpO2 values should we show as worth mentioning, if any? | None. Shown with the person's own baseline band only |
| D3 | The brief says "associated with" and labels patterns unverified. Is the wording right for a clinician? | As written |

## E. Other clinical placeholders still waiting for a clinician

| # | Question | Our placeholder now |
|---|---|---|
| E1 | Check-up intervals: eye 12 months, foot 12, kidney 12, HbA1c 6, flu vaccine 12, diabetes review 6. Are these right for this group? | As listed (placeholders approved by Hong Yi, not clinically reviewed) |
| E2 | Interaction wording: "Possible interaction between X and Y. Please check with your pharmacist or doctor before continuing." Is that safe and clear? The demo pair is clarithromycin and atorvastatin | The fixed wording above |
| E3 | Lifestyle and nudge text has no approved source (for example after-dinner walk, swap tips). May we use team-written templates, and who approves the wording? | Team-written templates, reviewed by you |
| E4 | Weekly goals: 150 moderate minutes and 2 strength sessions are defaults "to set with your doctor". Do you agree as defaults? | 150 and 2 |

## F. Logging effort

A report we were sent says logging in an app like this should take 60 to 90 seconds. Our symptom path is built for about 30 seconds with detail optional.

| # | Question | Our placeholder now |
|---|---|---|
| F1 | What is the minimum a symptom entry must contain to be clinically useful? Anything we ask that you would drop? | Symptom, strength, time, and the sensor glucose filled in automatically |

## G. Workout tracker (workout-tracker.md)

| # | Question | Our placeholder now |
|---|---|---|
| G1 | The tracker judges effort from heart rate: maximum heart rate 208 minus 0.7 times age, then bands of percent of maximum (below 57 light, 57 to 63 light, 64 to 76 moderate, 77 to 95 vigorous, 96 and above near maximal). Is this an acceptable method for adults 45 to 65 with type 2 diabetes? | As listed, placeholders from common exercise conventions, not cited data |
| G2 | Heart rate is unreliable on beta-blockers (and some other medicines). We switch the effort label off for people on them. Which medicines should switch it off? | Beta-blockers only |
| G3 | For strength training, should the app say anything about blood pressure or glucose around a session (for example check glucose before and after), or stay silent unless the person asks? | Silent. It only shows the glucose change that followed, worded "associated with" |
| G4 | Is a 90-second rest timer a sensible default, or should the app not suggest a rest length? | 90 seconds, skippable |

## Decisions we still need from the team, not from Damien

- Which service sends the text messages, emails and calls (and who holds the keys).
- Who builds E1-7 (the database changes) and how E11-2 and E7-4 split with Joely's E11-1 and E7-1.
- Migration numbering, because Hong Yi's E1-3 and Joely's follow-up both start at 0008.
- Whether to approve the workout tracker tables (schema.md section 14), which are new tables outside E1 and so need the owner's OK.
