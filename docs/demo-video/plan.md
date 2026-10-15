# Smart Health demo video: approved plan (v2)

Runtime **7:40** (cap 8:00), 16:9, 1080p, 24 fps. Submission is **16 Oct 2026**. Approved by Hong Yi on 12 Oct 2026 with one note: **enticing, fast-paced, and every scene tells a story.**

## 1. The idea

> **Health rarely falls off a cliff. It slips a little each week, and nobody is watching.**
> Smart Health learns your normal, then catches the drift.

Tagline: **Catch the drift.** Product line: *Explain. Organise. Remind. Never advise.*

Recurring motif: a thin line drifting down about 1 percent per week, with a faint "baseline band" around it. It appears in the hook, the insights scene, the urgent scene and the doctor brief.

Key message to land: it is the slow deterioration we miss, and this is what the app catches and solves.

## 2. Pace and story rules (the approved note)

**Pace**
- Average shot length 1.5 to 3 seconds. Nothing sits still for more than 4 seconds.
- Motion is brisk, not floaty: reveals take 0.25 to 0.5 s, easing `cubic-bezier(0.16, 1, 0.3, 1)`; push-ins are fast and settle quickly.
- AI clips are generated at about 5 s but used at 2 to 3 s, sped up 1.25 to 1.5 times.
- App takes are speed-ramped: real speed on taps, 3 to 4 times through typing and scrolling, a hit of slow on the payoff.
- Cut on the beat. Every cut gets a sound (tap, whoosh, low hit). Music: minimal, with a pulse that builds from the reveal; one second of silence before the metformin refusal.
- Kinetic type: one to three words per beat, slammed in on the cut, never paragraphs.

**Story: every scene is a mini-story**
Each scene has three beats, written in the table in section 3:
1. **Setup:** a person and a small problem (3 to 5 s).
2. **Tension:** the problem gets worse or the viewer feels the gap (3 to 5 s).
3. **Payoff:** the app resolves it with something visible, then a "goes into his brief" tag.

If a scene has no tension, it is a feature list; rewrite it.

**Apple-style effects to use**
- Masked text reveals (words rise out of a line).
- Match cuts (a circle becomes a clock becomes a ring).
- Phone mockup with slight tilt, soft shadow, parallax between layers.
- Numbers count up; charts draw on.
- A soft radial glow behind the hero object only.
- Dip through black between acts; no wipes.

## 3. The approved timeline and story beats

| Time | Length | Scene | Story (setup, tension, payoff) | Source |
|---|---|---|---|---|
| **A. Project overview** | | | | |
| 0:00 to 0:20 | 20 s | **Hook** | Black. "Nobody collapses overnight." The line drifts down. Cut: Mr Tan at the kitchen table. Payoff: "One person could see it. He gets ten minutes." | M1 + A1 |
| 0:20 to 0:45 | 25 s | **The problem** | Same kitchen shot at week 1 (organiser full, he is rested), week 6 (slots left over), week 12 (nothing taken). Tension: clinic desk, empty page. Payoff: "The doctor sees one day, not the slope." | A1, A1b, A1c, A4, M2 |
| 0:45 to 0:55 | 10 s | **Who it is for** | Portrait. Chips fly in: 45 to 65, T2D, Singapore, four languages, large text | A5 + M4 |
| 0:55 to 1:15 | 20 s | **Reveal** | The line stops, locks into a ring, the logo appears. Tagline. Five icons. Payoff: "Learns your normal. Catches the drift." | M5 + R7 |
| **B. Core agent features** | | | | |
| 1:15 to 1:30 | 15 s | **Onboarding** | Fast montage of key questions: consent, about you, diabetes history, scan a medicine (3 s hold), low glucose, devices, emergency contact, summary. Caption: "Days 1 to 14: learning his normal" | App |
| 1:30 to 2:05 | 35 s | **Daily logging** | Setup: a busy day. Tension: five things to track. Payoff: one app, every entry ends on "you check, then it saves". Includes meal photo (10 s), dose + plain-language explanation + "Not checked" (10 s), BP / symptom / mood and sleep / workout montage (10 s), the confirmation line (5 s) | App |
| 2:05 to 2:50 | 45 s | **Seeing the drift** | Setup: his baseline band. Tension: the glucose and sleep lines slip, week by week. Payoff: the card says what changed and when it started, in plain words, no diagnosis. "Week 3. Not month 6." | App + M2 callouts |
| 2:50 to 3:15 | 25 s | **Ask** | "Why was I high this week?" answered from his logs. Tension: "Can I skip metformin?" Silence. Payoff: warm refusal, "Added to your doctor questions" | App |
| 3:15 to 4:25 | 70 s | **Memory agent** | See section 3.1 | App |
| 4:25 to 4:45 | 20 s | **Urgent** | Setup: the drift crosses a line fast. Tension: a red-flag symptom. Payoff: fixed-wording alert, then the emergency contact is told (check before filming: one tap vs automatic) | App |
| 4:45 to 5:55 | 70 s | **Doctor brief** | See section 3.2 | App |
| 5:55 to 6:15 | 20 s | **Why we stand out** | Four cards: learns your normal and catches the drift; a memory that grows inside strict limits; every log confirmed by you; the doctor sees the whole slope. Payoff: "Catch it at week 3, not month 6." | M7 + A7 |
| **C. Build reflection** | | | | |
| 6:15 to 6:30 | 15 s | **How we built it** | Screen recordings of CodeBuddy/WorkBuddy; specs written first | Your recordings |
| 6:30 to 6:50 | 20 s | **What kept the agent on track** | Rules file, handover log after every session, one backlog per person, tests (1,687 API tests; red-team set, 0 leaks) | Recordings + M8 |
| 6:50 to 7:10 | 20 s | **How we use AI differently** | On-screen: "AI proposes. People and code decide." Product: AI writes words, code computes numbers, the learner cannot edit its own guards or any medicine. Build: coding agent bound by a rules file and checked by tests | M8 |
| 7:10 to 7:30 | 20 s | **Limitations** | Demo data (not a real patient trial); thresholds are placeholders pending clinical review; proves it notices and explains, not that it improves outcomes. Next: clinician review and a small pilot | M8 |
| 7:30 to 7:40 | 10 s | **Close** | "Catch the drift." Then the tagline and logo | M9 |

### 3.1 Memory agent, 70 s (beats)

| Beat | Length | On screen |
|---|---|---|
| Overview | 10 s | "What Smart Health has learned": ideas, each with its evidence |
| Missed doses | 15 s | Pattern flagged, the reason he gave, a gentler reminder time proposed |
| Trends | 10 s | "After chicken rice, glucose rose"; the effect of a walk |
| Food recommendation | 15 s | Fried chicken rice, then a lighter dish for next time: steamed chicken rice |
| Notification engine | 15 s | A reminder at his learned best time, paired with a meal or a short walk; settings he can customise; caption "max 3 a day, quiet at night" |
| He decides | 5 s | Confirm, reword or delete an idea |

### 3.2 Doctor brief, 70 s (beats)

| Beat | Length | On screen |
|---|---|---|
| Brief home | 8 s | Home with how complete the data is |
| The timeline | 20 s | The whole slope on one page: food, sleep, doses, exercise side by side |
| Patterns and risks | 15 s | Patterns "worth discussing", with evidence; anything to flag for the next checkup |
| His questions | 10 s | His questions and worries already inside the report |
| Sharing | 10 s | Share link, then the doctor's phone with the read-only view |
| Payoff | 7 s | "He does not have to remember what to say. The doctor already knows." |

## 4. Required pain points: where each one is shown

| Required | Where |
|---|---|
| Medication understanding | Logging beat 2: explanation; onboarding scan |
| Medication management and adherence | Logging dose confirmation; memory agent missed-dose beat |
| Health tracking | Logging; Seeing the drift |
| Preventive health | Memory agent notification beat (walk, lighter food). Add a care-plan example if time allows |
| Healthcare preparation | Ask ("added to your doctor questions"); brief questions |
| Empowering, personalised, longitudinal | Memory agent "he decides"; baseline after 14 days |
| Safe and strictly bounded | Ask refusal; Urgent fixed-wording alert |
| Honest about uncertainty | "Not checked"; dashes for missing data; "Estimated" labels |
| Practical | One-tap logging with confirmation; a swap he can actually eat |
| Build approach and CodeBuddy/WorkBuddy | Part C |

## 5. Voiceover draft (about 2.6 words per second; trim to fit)

**Hook (20 s):** "Nobody collapses overnight. A missed dose. A short night. A little more glucose each week. Small enough to miss. Big enough to matter. And the one person who could see it? Gets ten minutes."

**Problem (25 s):** "Meet Mr Tan. Type 2 diabetes. Six medicines. Week one, he is on track. Week six, he is skipping. Week twelve, nobody noticed. The doctor sees one day. Not the slope."

**Who (10 s):** "Mr Tan is 58. Not technical. He needs plain words, big text, and his own language."

**Reveal (20 s):** "This is Smart Health. It learns what normal looks like for you. Then it catches the drift. It explains. It organises. It reminds. And it never advises."

**Onboarding (15 s):** "Setup takes minutes. His medicines, his history, his devices, who to call. Then, for two weeks, it simply learns what normal looks like for him."

**Logging (35 s):** "One app for everything. Snap a meal. Confirm a dose and understand what it is for. Log blood pressure, symptoms, sleep, mood, a workout. Every entry stops at one screen: you check, then it saves. And when it cannot identify something, it says so. Not checked is never safe."

**Drift (45 s):** "After two weeks, it knows his normal. Then it watches the line. His glucose after dinner creeps up. His sleep gets shorter. The app does not diagnose. It shows him, in plain words, what changed and when it started. Week three. Not month six."

**Ask (25 s):** "Ask anything about your own data. Why was I high this week? It answers from his logs. Can I skip metformin? [silence] It will not. It points him to his doctor, and adds the question to his list."

**Memory agent (70 s):** "This is the part that grows with him. It notices he forgets on busy weekdays, so it proposes a different reminder time. It sees glucose rise after fried chicken rice, and suggests steamed chicken rice next time, never a lecture. It learns when he actually reads a notification, and pairs a dose with a meal or a short walk when it is safe. No more than three a day. Quiet at night. And every idea is his to confirm, reword, or delete."

**Urgent (20 s):** "Some changes cannot wait. A sharp drop crosses his line. The alert uses fixed words, no AI guessing. One tap tells his family."

**Brief (70 s):** "Before every visit, three months of his life on one page. Food, sleep, doses, exercise, side by side, so the doctor sees patterns in seconds. What is worth discussing. What to watch. And the questions Mr Tan always forgets to ask, already written. He sees exactly what the doctor sees. One link, and the doctor knows him before he walks in."

**Stand out (20 s):** "Why is this different? It learns your normal. It remembers inside strict limits. You confirm every entry. And the doctor sees the whole slope. Catch it at week three, not month six."

**Build (15 s):** "We built Smart Health with CodeBuddy and WorkBuddy. Specs first, code second."

**Agent on track (20 s):** "A rules file the agent reads every session. A handover note after each one. One backlog per person. And tests that prove the boundaries hold."

**AI differently (20 s):** "We use AI differently. AI proposes. People and code decide. In the product, it writes words, and code computes every number. In the build, the agent follows rules we can check."

**Limits (20 s):** "What it is not, yet. The data is demo data. The thresholds are placeholders awaiting clinical review. We show it notices and explains, not that it improves outcomes. Next: clinicians and a small pilot."

**Close (10 s):** "Catch the drift. Explain. Organise. Remind. Never advise."

## 6. Visual style: illustrated (recommended)

Refined flat editorial illustration with soft gradients and grain, not a children's cartoon. Easier to keep Mr Tan consistent, hides AI mistakes in hands and pills, cannot be mistaken for a real patient, and sits well beside clean UI. Do a 30-minute test (kitchen shot in both styles) before committing; if you choose real human, use STYLE_B and expect more retries. Do not mix the two.

## 7. Generator workflow (Miora: https://miora.design/)

Miora is described as "The Agentic Creative Studio with Memory". Its page gave no details on clip length, resolution or prompt fields, so check those first. Use its memory to hold Mr Tan (R1) and the style frame (R0) so clips stay consistent. Generate stills first, then animate each still.

### Reference images (make these first)

| ID | What |
|---|---|
| R0 | Style frame: palette, line weight, mood (pick the best of 8) |
| R1 | Mr Tan character sheet: front, side, 3/4, same outfit |
| R2 | Kitchen table, morning light, pill organiser full, phone |
| R2b | Same kitchen, week 6: organiser half-used, tired posture |
| R2c | Same kitchen, week 12: organiser mostly untouched, slumped, plate heavier |
| R5 | Clinic desk, doctor's hands, empty clipboard, no face |
| R6 | Mr Tan, small warm smile, phone in hand, evening light |
| R7 | Real screenshot of the Home screen (390 x 844, `mr-tan`) |

**R1 prompt:**
> Character sheet of an older Singaporean Chinese man, about 58, short grey hair, round glasses, warm brown eyes, kind tired expression, light blue short-sleeve button shirt, grey trousers. Front view, side view and three-quarter view on a plain off-white background. Refined flat editorial illustration, soft gradients, subtle paper grain, limited warm palette. Same face and outfit in every view. No text.

**STYLE_A:**
> Refined flat editorial illustration, soft gradients, subtle paper grain, warm limited palette of cream, soft blue and muted orange, calm mood, quick confident camera, no text, no logos.

**STYLE_B (real human, only if the test passes):**
> Cinematic documentary look, natural window light, shallow depth of field, soft film grain, 35mm lens, muted warm colours, quick confident camera, no text, no logos, realistic Singapore HDB home.

**NEGATIVE:**
> text, captions, watermark, extra fingers, distorted hands, changing face, flickering, morphing, blurry.

### Clips (generate 5 s each, use 2 to 3 s)

**A1 (hook, week 1). Reference R2 + R1**
> {STYLE_A} The man from the reference sits at a kitchen table in the early morning, full pill organiser beside him, looking at his phone. A quick, smooth push-in on his face, steam rising, window light shifting. Keep his face, glasses, shirt and the table layout unchanged.

**A1b (week 6). Reference R2b + R1**
> {STYLE_A} The same kitchen and man, now with the pill organiser half untouched. He looks tired. Same camera push-in as the first shot, same framing. Keep his face, glasses, shirt and the table unchanged.

**A1c (week 12). Reference R2c + R1**
> {STYLE_A} The same kitchen and man, now with the pill organiser almost untouched and a heavier plate on the table. He is slumped. Same camera push-in, same framing. Keep his face, glasses, shirt and the table unchanged.

**A4 (clinic desk). Reference R5**
> {STYLE_A} A doctor's desk from the patient's side. The doctor's hands hold a pen over an empty page on a clipboard. Quick push-in on the empty page. No faces. Keep the desk and hands unchanged.

**A5 (who it is for). Reference R6**
> {STYLE_A} Portrait of the man looking up from his phone with a small warm smile. Brisk zoom-in, light shift behind him. Keep his face and outfit unchanged.

**A7 (stand out / impact). Reference R6**
> {STYLE_A} The man sits relaxed in a clinic waiting seat, calm and confident, phone in hand. A smooth arc to the left, warm light. Keep his face and outfit unchanged.

Optional: A2 (pill bottles with a blurred label, no readable text) as a one-second insert in the problem scene.

Keep the same camera and framing in A1, A1b and A1c; the viewer should notice only what changed. Never let AI make an app screen: use R7 in a phone mockup. Add a small "Illustration generated with AI" caption on AI scenes.

## 8. Motion pieces (Claude builds as HTML pages; you screen-record at 1920 x 1080, 60 fps)

| ID | Scene | What it does |
|---|---|---|
| M1 | Hook | "Nobody collapses overnight." Slams in; the drifting line draws on |
| M2 | Problem and drift | The line plus baseline band; the line slowly leaves the band; used again as callouts over the insights scene |
| M4 | Who | Chips snap in on the beat |
| M5 | Reveal | Line locks into a ring, logo, tagline, phone rises with a glow |
| M6 | Demo callouts | "You check, then it saves", "Not checked is never safe", "No AI in the loop", "He decides" |
| M7 | Stand out | Four cards slide in and stack |
| M8 | Build | Three cards (rules, handover, tests); "AI proposes. People and code decide."; one limitations card |
| M9 | Close | "Catch the drift." tagline, logo |

Each under 12 seconds.

## 9. App takes (record each as its own file, 10 s spare on both ends)

Set up: 390 x 844 at pixel ratio 2, light theme, text scale 100 percent, 60 fps in OBS, soft tap ripple instead of cursor. Use `mr-tan` for everything except the first label scan (use a blank `demo` user). Pre-seed a due dose, a missed dose, a half-finished meal, a clash alert and a populated brief. Clean up afterwards: opening Notifications writes reminder rows.

| Take | Scene | What to record | Length |
|---|---|---|---|
| T1 | Onboarding | Quick pass through key pages, scan, summary (record each page 2 s) | 25 s |
| T2 | Logging: meal | Photo, estimate, confirmation | 15 s |
| T3 | Logging: dose | Confirm, open medicine, explanation, an item marked "Not checked" | 20 s |
| T4 | Logging: montage | BP, symptom, mood and sleep, workout, each ending on its confirmation | 25 s |
| T5 | Drift | Insights: glucose, sleep, baseline flag card | 40 s |
| T6 | Ask | "Why was I high this week?"; "Can I skip metformin?"; refusal | 30 s |
| T7 | Memory: learned | "What Smart Health has learned", evidence, confirm / reword / delete | 20 s |
| T8 | Memory: missed doses | The pattern, the reason, the proposed reminder time | 15 s |
| T9 | Memory: trends and food | Food response, lighter-dish suggestion | 25 s |
| T10 | Memory: notifications | A reminder at the learned time, the walk prompt, notification settings | 20 s |
| T11 | Urgent | Decline card, low-glucose alert, emergency contact | 25 s |
| T12 | Brief | Home, timeline, patterns, questions, share link, doctor's phone | 80 s |
| T13 | Build | CodeBuddy/WorkBuddy sessions, repo files, tests running | 40 s |

For T13, also take at least 3 still screenshots for the hackathon build proof.

## 10. Edit

Tool: CapCut, DaVinci Resolve (free) or Premiere.

1. Voiceover first; cut every gap tighter than feels natural.
2. Lay clips to the voice; cut on the music beat; no shot over 4 s.
3. Speed-ramp app takes; zoom into the important part of the screen with fast keyframes.
4. App takes go in a tilted phone mockup on black.
5. Sound hit on every cut; one second of silence before the refusal.
6. Same grade and light grain on all AI clips; upscale to 1080p.
7. Burn in subtitles (judges may watch muted).
8. Export H.264, 1080p, 24 fps, under the platform size limit.
9. Watch it once at 1.25 times speed. If any part still drags, cut it.

## 11. Check before filming (say only what really runs)

- The baseline drift card appears for Mr Tan and reads in plain, non-diagnostic words (the old demo script says the "outside your usual range" card fires from early September in the demo data).
- Notification timing, meal pairing and the walk prompt run in the live app. The project notes listed the dose-time bandit and live anchoring as unfinished on 6 Oct; the related files are uncommitted changes.
- Walk prompts only appear when safety checks pass (no urgent flag, no recent low glucose, no dizziness, daytime); say "when it is safe".
- The emergency-contact message really sends, and whether it is one tap or automatic. Say only what is true.
- A sharp baseline decline escalates to the urgent screen, or only to an Insights flag. Say only what is true.

## 12. Schedule

| Day | Work |
|---|---|
| Mon 12 Oct | Style test; stills R0 to R7; final voiceover |
| Tue 13 Oct | Generate A1 to A7; record app takes T1 to T13; run the pre-filming checks |
| Wed 14 Oct | Build motion pieces M1 to M9; record voiceover |
| Thu 15 Oct | Edit, sound, subtitles, first full cut; team notes |
| Fri 16 Oct (morning) | Fixes, export, check playback, submit with proof screenshots |

If time runs short, cut in this order: A2, M4, the notification-settings beat, the "who it is for" scene.

## 13. Risks

- **Character drift:** always start from R1 or R2. If the face changes, regenerate.
- **Readable text in AI clips:** no drug names or fake labels; blur or crop.
- **Do not imply results:** say "notices and explains", not "improves adherence by X percent".
- **Demo data:** say once, in a small caption, that Mr Tan's 90 days are demo data.
- **"Full Jarvis" wording:** do not use it; it clashes with "strictly bounded". Say "a memory that learns your habits and proposes. You decide."
- **Tencent angle:** the app uses Gemini on Vertex AI, not Hunyuan. In Part C, say only what is true: CodeBuddy/WorkBuddy for the build, Miora for the clips.
- **Pace:** faster is not rushed. Keep the metformin refusal and the "week 3, not month 6" line to full beats, and cut everything else tight.
