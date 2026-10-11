# Smart Health web app (production): design and build notes

> This is the production app. It has the shell, design system, charts and the data layer, and **no screens**: every screen shows a "not built yet" placeholder until you build it. The finished clickable version, with every screen on demo data, is in [apps/mock](../mock). Copy a screen from there, point it at real data, and register it in `src/app/screens.tsx`. The design system is duplicated between the two apps for now; when it starts to drift, move `theme`, `motion`, `ui` and `charts` into a shared package.

This file is for whoever builds screens in `apps/web`. The product-level design rules (who it is for, tone of voice, accessibility checklist, doctor brief style) are in [docs/specs/design.md](../../docs/specs/design.md). Where the two disagree, `docs/specs/design.md` wins and this file needs fixing. This file holds the detail that belongs next to the code: tokens, motion, components and how to extend them.

## 1. Direction

Calm, precise and private, like a good clinic or a private bank, not a wellness app. That comes from five choices:

1. **Colour.** Deep pine green on warm ivory, a muted brass for the rare warm accent, quiet status colours. No bright mint, no gradients, no emoji.
2. **Type.** Atkinson Hyperlegible for everything you read (it was drawn for low vision). A serif, Newsreader, for titles and every number you glance at. The contrast between the two is what makes it feel edited.
3. **Surfaces.** Flat cards with a hairline border. One soft shadow (`shadow-lift`) for the hero card and one for sheets. Nothing glows.
4. **Motion.** Fast, small, and only where it explains something (section 5).
5. **Language.** Short sentences, units always shown, "higher than your usual" and "associated with", never "normal", "abnormal" or "caused by".

## 2. Tokens (single source of truth)

| What | Where | Used as |
|---|---|---|
| Colour, light and dark | `src/theme/palettes.ts` | CSS variables `--c-*`, written onto `<html>` by `applyPalette`. Tailwind reads them through `@theme inline` in `src/index.css` (`bg-canvas`, `text-ink`, `border-line`, `bg-brand`, ...) |
| Type scale | `src/index.css` (`--text-*`) | `text-display`, `text-xl`, `text-h1`, `text-h2`, `text-body`, `text-sub`, `text-micro`. Every size is `calc(Npx * var(--ts))` so the 200% text setting scales everything |
| Radii, shadows, easing | `src/index.css` | `rounded-card`, `rounded-sheet`, `shadow-lift`, `--ease-out` |
| Motion durations and curves | `src/motion/tokens.ts` | Imported by components that use `motion` |
| App configuration | `src/config/app.ts` | Demo clock, glucose ranges, goals, demo tools switch |

**Rule: no hard-coded colours, sizes or durations inside screens.** If a screen needs a value that is not a token, add the token first.

### Palette

| Token | Light | Dark | Use |
|---|---|---|---|
| `canvas` | `#F6F4EE` | `#0D1411` | App background |
| `card` | `#FFFEFB` | `#141D19` | Cards and sheets |
| `well` | `#EFECE3` | `#1B2621` | Inset areas, inputs at rest |
| `line` | `#E1DDD0` | `#2A3731` | Hairlines |
| `ink` / `ink2` / `ink3` | `#16201B` / `#46524B` / `#5F6B64` | `#ECEFE8` / `#B3BEB7` / `#8D9993` | Text. `ink3` only at 16 px or larger |
| `brand` (pine) | `#1D4A3C` | `#86C9AA` | Primary action, active state, links |
| `brass` | `#7A5C22` | `#D8B46C` | Estimates, proposed facts, safety messages. Sparingly |
| `ok` `warn` `danger` `info` | `#2B6B47` `#935812` `#A12B2B` `#2E5A85` | lighter tints | Status. Always with an icon and a word |
| Glucose fills | `#6B1D1D` `#B8372C` `#4C9168` `#D3A21F` `#CC6A1F` | lighter | Very low, low, in range, high, very high. Always with a pattern in charts |

Contrast is checked against `canvas` and `card`: `ink` above 12:1, `ink2` above 7:1, `ink3` above 4.5:1, `brand` above 9:1 in light.

To add a theme (for example high contrast), add one object to `palettes.ts` and one option in the display settings. Nothing else changes.

## 3. Layout

- Mobile first. On a phone or iPad the app fills the screen; on a wide window it sits in a centred 480 px column (set `appConfig.frame` to `'device'` for a phone frame). The shell is `src/app/Shell.tsx`.
- One screen is one `Screen` (scroll container, 20 px side padding, content centred and capped at 720 px on a tablet and 1040 px on a laptop; pass `narrow` for a form or single-task page: 640 px) with a `Header`. Pass `tabs` when the bottom bar is showing: the page then keeps `--tab-space` (the tab bar) plus `--ask-space` (the phone Ask button) free at its end. A `Footer` or onboarding `Dock` carries `data-dock`, which removes the page's bottom padding so the bar sits on the true bottom edge.
- Tablet and laptop use a side rail instead of the bottom bar; the Ask button lives in the rail there. On a phone it floats above the tab bar and steps aside while the page is scrolled down. Setup and the urgent screen have no rail.
- Tiles in a list use `TileGrid` (1, 2, 3 columns, equal heights); two-column pages use `Split`, which only goes to two columns from 1024 px.
- One primary action per screen: full width, 56 px high, `Footer` keeps it on screen.
- Touch targets are at least 48 px. Chips are 48 px high.
- Layouts must reflow at 200% text: use `flex-wrap`, `min-w-0`, `break-words`, and for two-column grids add `[[data-ts='2']_&]:grid-cols-1`.

## 4. Components

All in `src/ui`. Import from there, never restyle in a screen.

| Component | File | Notes |
|---|---|---|
| `Card` | `primitives.tsx` | `tone`: plain, soft, hero. Pass `onClick` to make it pressable |
| `Button`, `TextLink`, `Chip` | `primitives.tsx` | Variants primary, secondary, ghost, danger. All press with `scale(0.97)` |
| `StatusPill`, `Alert` | `primitives.tsx` | Tone plus icon plus words, never colour alone |
| `EstimateBadge`, `ConfidenceChip`, `UnverifiedTag`, `SourceTag`, `Dots` | `primitives.tsx` | The honesty vocabulary: estimated, check this, unverified, source, confidence |
| `Field`, `Stepper`, `Toggle` | `primitives.tsx` | Form pieces. `Field` takes `type` (text, date, time, tel), a unit `suffix` shown inside the field, and an `error` that replaces the hint and outlines the field |
| `Segmented`, `TabStrip`, `NumberPad`, `ChoiceCards`, `Rating` | `controls.tsx` | The segment and tab indicators slide |
| `Sheet` | `Sheet.tsx` | Bottom sheet: drawer curve, velocity-based dismiss, Escape, focus return |
| `Screen`, `Header`, `Footer`, `Reveal` | `layout.tsx` | `Reveal` animates a section the first time it is seen and never again |
| Charts | `src/charts` | Hand-built SVG: `TrendChart`, `DayChart`, `TirBar`, `Ring`, `IntensityBars`, `FoodBars`, `WeekGridView`, `AdherenceTimeline`, `MoodStress` |

Charts follow four rules: the personal baseline band is shaded behind the line, gaps are drawn as gaps (never interpolated), every fill has a pattern so it reads in grayscale, and every chart has a text label for screen readers and a plain sentence above it.

## 5. Motion

Questions to ask before animating anything, in order: how often will a person see this, what does it explain, and what is the cheapest way to do it.

| Situation | Decision |
|---|---|
| Bottom bar tab switch, insights tab switch | No animation. Used all day. |
| Pushed screen | 190 ms fade and 8 px rise, `ease-out` |
| Bottom sheet | 270 ms in on `cubic-bezier(0.32, 0.72, 0, 1)`, 200 ms out. Draggable, dismisses on a quick flick as well as on distance |
| Press on any tappable thing | `scale(0.97)`, 140 ms, `ease-out` |
| Segment and tab indicator | Slides, 200 ms, `ease-in-out` |
| First view of a chart | Line draws in over 700 ms. Never replays |
| Section entrance on Home | 40 ms stagger, first view only |
| Urgent screen | No motion at all |
| `prefers-reduced-motion` | Movement removed, fades kept (`MotionConfig reducedMotion="user"`) |

Only `transform` and `opacity` animate (plus `clip-path` and `stroke-dashoffset` for charts, which only repaint). Never animate from `scale(0)`. Exit is faster than enter. Hover styles are used only where a hover exists (Tailwind does this for `hover:`).

If an animation freezes while you test in a hidden browser window, open the app with `?fakeRaf` on localhost. It drives animation from a timer.

## 6. Data and services

```
screens  ->  data/hooks.ts (TanStack Query)  ->  data/repositories/index.ts  ->  http.ts  (production, this app)
                                                                              ->  mock.ts  (apps/mock)
```

- `data/types.ts` holds the types and mirrors `docs/specs/schema.md`.
- `data/repositories/types.ts` is the `Api` interface: the contract between screens and data. **Screens only ever call hooks.**
- `data/repositories/http.ts` implements `Api` against the backend. `getPatient` is wired as an example; every other method throws `NotWired` until its endpoint exists. Wire one at a time.
- Analysis, models and predictions belong behind the backend (or behind a service interface in `src/services`), never inside a screen. `apps/mock/src/services` shows the two interfaces the mock uses (meal analysis, food-response note).
- Every write invalidates every read (`useWrite` in `hooks.ts`). Narrow the keys later if it matters.

## 7. Routing

`src/app/routeIds.ts` lists every planned screen and sheet once, with its path, group, where it opens from and where it links. `src/app/App.tsx` makes a route for every one of them. A screen that is not built yet renders `NotBuilt`, which shows its notes from the registry. To build a screen:

1. Build the component in `src/features/<group>/`.
2. Register it in `src/app/screens.tsx` (`built = { B1: Home }`) or, for a sheet, in `src/app/sheetRegistry.tsx`.
3. Navigate with `useGo()`: `go('D1', { params: { date } })`. Sheets open with `go('H7', { sheet: { doseId } })`.

## 8. Language and copy

Strings are written in components as `t('screen.key', 'English text')`. The English text is the default, so everything renders now. `npm run i18n:extract` collects every key into `src/i18n/locales/en.generated.json` (git-ignored) for translators. Chinese is filled for the medicine page first. Never build a sentence by joining strings.

**Known gap:** the wiring works, but only the Home section titles, the Estimated badge and the Metformin page are wrapped in `t()` so far. Every other string is still a literal. Wrap them as each screen is finished, before translation starts.

Voice: plain, short, kind. "Not confirmed", not "you missed it". "Worth mentioning to your doctor", not "warning". No emoji, no exclamation marks, no all caps.

## 9. Checks before a screen is done

- [ ] Works at 100% and 200% text, light and dark
- [ ] Every tappable thing is at least 48 px and has a label
- [ ] Status is never colour alone
- [ ] Anything estimated says so; anything compared says "associated with" and is marked unverified
- [ ] Empty, loading and error states exist
- [ ] Motion follows section 5
- [ ] The route is in `routeIds.ts` and registered in `screens.tsx`
