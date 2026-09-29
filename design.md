# Design — Smart Health UI/UX system

Design rules for the patient app and the doctor brief. Tokens here are mirrored in `apps/mobile/src/theme/tokens.ts` and `services/api/app/brief/templates/brief.css`; change them here first.

## 1. Who we're designing for

Adults 45–65 with Type 2 diabetes. Many have early presbyopia, some have reduced dexterity or diabetic eye changes, many aren't confident with tech, and many use more than one language. The app sits in their daily routine, so it must feel **calm, quick and kind**, never clinical or nagging.

### Principles
1. **One screen, one job.** A single primary action per screen, visually obvious.
2. **Big, legible, tappable.** Body text ≥ 18 px, touch targets ≥ 48 × 48 dp, generous spacing.
3. **Log in seconds.** Any daily log must be doable in ≤ 3 taps and ≤ 15 s.
4. **Explain, don't alarm.** Neutral language for trends; urgent styling is reserved for real urgency (F10).
5. **Never colour alone.** Every status pairs colour with an icon and a text label (and a pattern in charts).
6. **Show the source.** Health content always shows where it came from.
7. **No blame.** "Not confirmed" rather than "You failed". Missed doses are information, not failures.
8. **Same truth for patient and doctor.** The brief the doctor sees is viewable by the patient.

## 2. Colour

### 2.1 Core tokens
| Token | Light | Dark | Use |
|---|---|---|---|
| `bg` | `#FAFAF7` | `#0F1416` | App background (warm off-white) |
| `surface` | `#FFFFFF` | `#172024` | Cards, sheets |
| `surfaceAlt` | `#F1F5F4` | `#1E2A2E` | Subtle sections, input fills |
| `border` | `#E3E7E6` | `#2A3A3F` | Hairlines, dividers |
| `text` | `#1C2426` | `#E7ECEC` | Primary text |
| `textSecondary` | `#4B5563` | `#A7B0B2` | Secondary text (still AA) |
| `textMuted` | `#6B7280` | `#8A9496` | Hints, timestamps (≥ 16 px only) |
| `primary` | `#0F766E` | `#2DD4BF` | Primary buttons, active tab, links |
| `primaryPressed` | `#115E59` | `#5EEAD4` | Pressed state |
| `primarySoft` | `#E6F4F1` | `#12302C` | Selected chips, highlight backgrounds |
| `onPrimary` | `#FFFFFF` | `#062522` | Text on primary |
| `accent` | `#C2410C` | `#FB923C` | Warm highlights, streaks (sparingly) |

Primary teal reads as calm and health-related without the "hospital blue" look. `#0F766E` on white ≈ 5.5:1 (AA).

### 2.2 Semantic status
| Token | Light | Dark | Icon | Use |
|---|---|---|---|---|
| `success` | `#15803D` | `#4ADE80` | check-circle | Taken, in range, completed |
| `warning` | `#B45309` | `#FBBF24` | alert-triangle | Trending, due soon, not checked |
| `danger` | `#B91C1C` | `#F87171` | alert-octagon | Urgent, missed, clash |
| `info` | `#1D4ED8` | `#60A5FA` | info | Tips, sources |
| `*Soft` variants | 8–10% tint of each | 15% tint | | Card backgrounds for the status |

### 2.3 Glucose range colours (AGP convention, familiar to clinicians)
| Range (mmol/L, default targets) | Token | Fill | Pattern (charts/print) |
|---|---|---|---|
| Very low < 3.0 | `gVeryLow` | `#7F1D1D` | solid dark |
| Low 3.0–3.8 | `gLow` | `#DC2626` | dense dots |
| In range 3.9–10.0 | `gInRange` | `#16A34A` | none |
| High 10.1–13.9 | `gHigh` | `#EAB308` | diagonal lines |
| Very high > 13.9 | `gVeryHigh` | `#EA580C` | cross-hatch |

These are **fills only**. Text labels on or next to them use `text` or the status token, and ranges come from the patient's `targets` when set.

### 2.4 Adherence cells (prescription timeline)
| Status | Fill | Mark |
|---|---|---|
| taken | `success` | ✓ |
| taken_late_logged | `success` at 45% | ✓ outline |
| unconfirmed | `#D1D5DB` | diagonal hatch, "?" |
| missed | `danger` | ✕ |
| skipped_by_plan | none | "–" |
| future | outline only | — |

## 3. Typography

**Typeface:** **Atkinson Hyperlegible Next** (Google Fonts, designed for low-vision legibility, with distinct letterforms like 1/l/I and 0/O). Numeric readouts use `fontVariant: ['tabular-nums']`. Fallbacks: system (Roboto / SF Pro). CJK and Tamil fall back to Noto Sans SC / Noto Sans Tamil; test line heights per locale.

| Style | Size / line height | Weight | Use |
|---|---|---|---|
| `display` | 40 / 48 | 700 | Big readings (glucose value) |
| `h1` | 28 / 36 | 700 | Screen titles |
| `h2` | 22 / 30 | 700 | Section / card titles |
| `h3` | 20 / 28 | 600 | Sub-sections |
| `body` | **18 / 28** | 400 | Default text |
| `bodyStrong` | 18 / 28 | 600 | Emphasis, button labels |
| `secondary` | 16 / 24 | 400 | Metadata, helper text (minimum size in app) |
| `label` | 16 / 20 | 600 | Chips, tabs, form labels |

- Respect OS font scaling up to 200%; layouts must reflow (no fixed-height text containers).
- Sentence case everywhere. No ALL CAPS.
- Reading level target: grade 6–8. Short sentences, common words, units always shown.

## 4. Layout, spacing, shape

- **Spacing scale (4-pt):** 4, 8, 12, 16, 20, 24, 32, 40, 48. Screen padding 20; card padding 20; gap between cards 16.
- **Radii:** 8 (inputs, chips), 16 (cards, sheets), 999 (pills, FAB).
- **Elevation:** flat by default; cards use `border` hairline. One shadow level only for bottom sheets and the FAB.
- **Grid:** single column on phones; max content width 560 on tablets/web.
- **Touch:** targets ≥ 48 dp, ≥ 8 dp apart; primary buttons full-width, 56 dp tall, fixed at the bottom of forms.
- **Iconography:** `lucide-react-native`, outline, 24 px (28 px in tabs), always with a text label except universally understood close/back.

## 5. Components (design-system primitives)

| Component | Notes |
|---|---|
| `Button` | variants: primary, secondary (outline), ghost, danger. Loading state keeps width. Never two primaries on one screen |
| `Card` | title, optional status stripe (left 4 px, colour and icon), body, footer action |
| `DoseCard` | med name, strength, "with food" tag, time, big **Taken** button; states scheduled / taken / unconfirmed |
| `ReasonSheet` | bottom sheet, one-tap reason chips (icons + labels), optional note, "Skip" |
| `ReadingInput` | numeric keypad, big value display, context segmented control, unit shown, range feedback after save |
| `FoodSearch` | local-food autocomplete (multilingual aliases), recent and favourites first, portion stepper (½, 1, 1½, 2) |
| `ConfidenceChip` | high (success) / check this (warning) / unknown (danger) with icon; used in scan review |
| `SourceTag` | small "Source: Your data" / "Source: <approved dataset>" chip on all health content |
| `TrendCard` | sparkline + plain-language line ("Higher than your usual this week") + "Why am I seeing this?" |
| `FoodResponseBar` | horizontal bar of personal response with n and range, gentlest to spikiest |
| `MemoryFactRow` | statement, category icon, confidence dots (●●○), "Why I think this", confirm / edit / delete |
| `UrgentScreen` | full-screen, `dangerSoft` background, h1 instruction, max 3 steps, 64 dp call buttons, no dismiss for 5 s on urgent_now |
| `ChatBubble` | user / assistant / system-template (distinct style for guardrail templates, with shield icon) |
| `EmptyState` | illustration-free: icon, one sentence, one action |
| `Banner` | offline, syncing, sync failed (with retry) |

## 6. Screen patterns

- **Today:** greeting + date → "Due now" dose cards → one nudge or check-in card → alerts → next appointment. Nothing below the fold is essential.
- **Log:** 5 large tiles (Glucose, Meal, Workout, Symptom, Mood), then recent entries timeline.
- **Meds:** list with clash badge and "not checked" badge; FAB "Scan".
- **Insights:** period switch (7 / 30 / 90 days) → glucose → food responses → activity → sleep → adherence. Every chart has a one-line plain summary above it.
- **Me:** grouped list rows; "What Smart Health has learned" is prominent.
- **Forms:** one question per step for onboarding; progress indicator; "Save and continue later".
- **Bottom sheets** for quick actions (reason capture, clash info); full screens for multi-field entry.

## 7. Data visualisation rules

- Line charts for trends, with the personal baseline band (median ± MAD) shaded `primarySoft` and target range as dashed lines.
- Bars for daily totals (steps, workout minutes, sodium). Avoid pie charts.
- Always label axes with units; show "no data" gaps as breaks, never interpolate across them.
- Max 2 series per chart in-app; the brief may use overlays (glucose over adherence).
- Tap a point → tooltip with exact value, time, source.
- Charts must be understandable in grayscale (patterns in §2.3/2.4).

## 8. Motion and feedback

- Durations 150–250 ms, ease-out; respect OS "reduce motion" (disable non-essential animation).
- Haptic light tap on confirm (Taken, Save). No celebratory confetti; a subtle check animation is enough.
- Toasts for non-blocking confirmation ("Saved"); never for errors that need action (use inline or banner).

## 9. Voice and tone

| Do | Don't |
|---|---|
| "Time for your Metformin (1 tablet, with food)." | "REMINDER: TAKE MEDICATION NOW" |
| "Your morning readings have been a bit higher than usual this week. Worth mentioning to your doctor." | "Warning: your diabetes is getting worse." |
| "I can't advise on changing your medication, but your doctor or pharmacist can. Want me to add this to your questions?" | "You should not skip your dose." (still advice) |
| "I'm not able to identify this medication. Please check with your pharmacist." | "This looks like Panadol." (guessing) |
| "Not checked: we don't have interaction data for this item." | "No interactions found." (when unknown) |

Glossary: "doctor brief" (not "report"), "readings", "doses", "check-in", "what Smart Health has learned".

## 10. Accessibility checklist (every screen)
- [ ] Text contrast ≥ 4.5:1 (≥ 3:1 for ≥ 24 px); UI component contrast ≥ 3:1
- [ ] Works at 200% font scale without truncation of essential info
- [ ] All interactive elements have `accessibilityLabel` and role; charts have a text summary
- [ ] Screen-reader order matches visual order
- [ ] No colour-only meaning
- [ ] Targets ≥ 48 dp
- [ ] All strings via i18n (EN / ZH / MS / TA); no concatenated sentences (use ICU placeholders)
- [ ] TTS available for explanations and reminders

## 11. Doctor brief (print/web) style

Audience: a clinician scanning in < 2 minutes. **Dense, structured, printable.**
- A4 portrait, 12 mm margins, 2-column grid for stats; base 10.5 pt Atkinson Hyperlegible Next, headings 13 pt bold.
- Header band: patient initials + birth year (no full name unless patient opts in), period, generated date, data completeness bar.
- "Top 3 to discuss" box at top, each item with a jump link to evidence.
- Prescription timeline: rows = medications, columns = days, cells per §2.4, glucose line (fasting) overlaid on a secondary axis at the bottom.
- AI-written sentences carry a small "AI summary" marker; patterns section header reads **"Patterns for clinician review (unverified, generated from patient-logged data)"**.
- Grayscale-safe (patterns), black text, no background fills heavier than 10%.
- Footer on every page: "Generated by Smart Health from patient-reported and device data. Not a diagnosis. Numbers computed deterministically; see data completeness."

## 12. Brand
- Name: Smart Health. Logo: a simple rounded speech-bubble + leaf mark in `primary`.
- Cover image (16:9, 380×216 for submission): Today screen + brief page side by side on `bg`, with the tagline "Your everyday buddy. Your doctor's missing notes."
