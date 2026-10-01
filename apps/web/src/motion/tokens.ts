/**
 * Motion source of truth. Rules (see design.md):
 *  - Frequent actions (tab bar switches) do not animate.
 *  - UI motion stays under 300 ms. Entering uses ease-out; nothing starts from scale(0).
 *  - Exit is faster than enter. Only transform and opacity animate.
 *  - prefers-reduced-motion removes movement and keeps fades.
 */
export const duration = {
  press: 0.14,
  fast: 0.16,
  page: 0.19,
  sheet: 0.27,
  sheetExit: 0.2,
  chart: 0.7,
  stagger: 0.04,
} as const

export const ease = {
  out: [0.23, 1, 0.32, 1],
  inOut: [0.77, 0, 0.175, 1],
  drawer: [0.32, 0.72, 0, 1],
} as const
