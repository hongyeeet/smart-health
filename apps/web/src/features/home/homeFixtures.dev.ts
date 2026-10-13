/**
 * Dev-only fixtures: typed HomeOverview values to read the Home states against (nothing imports this file, so it is not in the build).
 * To see one on screen, temporarily return it from `useHomeOverview`.
 */
import type { HomeOverview, KpiStatus, Nutrient } from '@/data/types'

const unknown: KpiStatus = { state: 'unknown', usualLow: null, usualHigh: null, usualMedian: null, delta: null }
const st = (state: KpiStatus['state'], median: number, delta: number): KpiStatus => ({ state, usualLow: median * 0.8, usualHigh: median * 1.2, usualMedian: median, delta })
const days = ['2026-10-07', '2026-10-08', '2026-10-09', '2026-10-10', '2026-10-11', '2026-10-12', '2026-10-13']
const ok: Nutrient = { state: 'ok', highMeals: 1, meals: 10 }
const high: Nutrient = { state: 'high', highMeals: 8, meals: 10 }
const noNutrient: Nutrient = { state: 'unknown', highMeals: null, meals: 0 }

/** Mr Tan on a Tuesday lunchtime: a plan with a `now` step, glucose above, steps below, salt high, heart within */
export const fullDay: HomeOverview = {
  asOf: '2026-10-13',
  plan: {
    date: '2026-10-13',
    done: 2,
    total: 6,
    nowIndex: 1,
    steps: [
      { time: '08:00', label: '8:00 am', state: 'done', items: [{ kind: 'meal', title: 'Breakfast', status: 'done', doseId: null, mealType: 'breakfast' }, { kind: 'dose', title: 'Metformin 500 mg', status: 'done', doseId: null, mealType: null }] },
      { time: '13:00', label: '1:00 pm', state: 'now', items: [{ kind: 'meal', title: 'Lunch', status: 'due', doseId: null, mealType: 'lunch' }, { kind: 'dose', title: 'Metformin 500 mg', status: 'due', doseId: 'dose-1', mealType: null }] },
      { time: '20:00', label: '8:00 pm', state: 'later', items: [{ kind: 'meal', title: 'Dinner', status: 'later', doseId: null, mealType: 'dinner' }] },
      { time: '21:00', label: '9:00 pm', state: 'later', items: [{ kind: 'dose', title: 'Atorvastatin 20 mg', status: 'later', doseId: 'dose-2', mealType: null }] },
    ],
  },
  glucose: { value: 10.5, unit: 'mmol/L', day: '2026-10-02', inRangePct: 40, spark: [11, 11.9, 14, 10.5, 10.1, 9.4, 10.5], status: st('above', 8, 2.5) },
  steps: { avg: 3984, spark: [2000, 6000, 1200, 8000, 7000, 4500, 400], status: st('below', 7284, -3300) },
  calories: { avgKcal: 1723, sugar: ok, salt: high, spark: [], status: st('within', 1800, -77) },
  heart: { bpm: 85, restingBpm: 70, spo2: 96, status: st('within', 84, 1), spo2Status: st('within', 96, 0) },
  chart: { days, glucose: [11, 11.9, 14, 10.5, 10.1, 9.4, 10.5], steps: [2000, 6000, 1200, 8000, 7000, 4500, 400], calories: [1700, null, 1800, 1650, null, 1900, 1723], heartRate: [80, 82, 90, 85, 84, 83, null] },
}

/** A person with a little history: every status is unknown, a nutrient has no data, a day is missing, no `now` step */
export const unknownStates: HomeOverview = {
  ...fullDay,
  plan: { ...fullDay.plan, done: 0, nowIndex: 0, steps: fullDay.plan.steps.map((s) => ({ ...s, state: 'later' as const, items: s.items.map((i) => ({ ...i, status: 'later' as const })) })) },
  glucose: { value: 7.2, unit: 'mmol/L', day: '2026-10-13', inRangePct: null, spark: [null, null, 7, 7.4, null, 7.1, 7.2], status: unknown },
  steps: { avg: 5100, spark: [null, null, null, 5000, 5200, 5100, null], status: unknown },
  calories: { avgKcal: null, sugar: noNutrient, salt: noNutrient, spark: [], status: unknown },
  heart: { bpm: null, restingBpm: null, spo2: null, status: unknown, spo2Status: unknown },
  chart: { days, glucose: [null, null, 7, 7.4, null, 7.1, 7.2], steps: [null, null, null, 5000, 5200, 5100, null], calories: Array(7).fill(null), heartRate: Array(7).fill(null) },
}

/** A brand-new person: no medicines, no meal steps, no data at all (Start here, and "No data yet" on each card) */
export const brandNew: HomeOverview = {
  asOf: null,
  plan: { date: '2026-10-13', done: 0, total: 0, nowIndex: null, steps: [] },
  glucose: null,
  steps: null,
  calories: null,
  heart: null,
  chart: { days, glucose: Array(7).fill(null), steps: Array(7).fill(null), calories: Array(7).fill(null), heartRate: Array(7).fill(null) },
}

/** The other status wording: glucose below, steps above, sugar and salt both high, heart rate up / oxygen down */
export const otherStates: HomeOverview = {
  ...fullDay,
  glucose: { ...fullDay.glucose!, status: st('below', 10, -2) },
  steps: { ...fullDay.steps!, status: st('above', 3000, 2000) },
  calories: { ...fullDay.calories!, sugar: high, salt: high, status: st('above', 1500, 223) },
  heart: { bpm: 92, restingBpm: 70, spo2: 93, status: st('above', 84, 8), spo2Status: st('below', 96, -3) },
}
