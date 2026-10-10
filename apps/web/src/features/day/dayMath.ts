import { clock } from '@/lib/format'
import type { DayMarker, DoseState } from './api'

/** Pure helpers for the Day view. No React here, so they can be checked on their own. */

export type Tone = 'brass' | 'ok' | 'late' | 'unconfirmed' | 'missed' | 'brand' | 'warn'

/** "7:40 am" for a minute after midnight. */
export const clockWords = (minute: number) => clock(minute)

/** The words for a dose state. Colour and icon are never the only signal. */
export function doseWords(state: DoseState): string {
  switch (state) {
    case 'taken':
      return 'taken on time'
    case 'late':
      return 'taken late'
    case 'not_confirmed':
      return 'not confirmed yet'
    case 'missed':
      return 'missed'
  }
}

/** Which look a marker gets. Doses follow their state; the rest follow their kind. */
export function markerTone(m: Pick<DayMarker, 'kind' | 'status'>): Tone {
  if (m.kind === 'meal') return 'brass'
  if (m.kind === 'workout') return 'brand'
  if (m.kind === 'symptom') return 'warn'
  switch (m.status) {
    case 'late':
      return 'late'
    case 'not_confirmed':
      return 'unconfirmed'
    case 'missed':
      return 'missed'
    default:
      return 'ok'
  }
}

/** Share of readings inside the range, as a whole number. Edges count as in range. Null when there are no readings, never zero. */
export function timeInRange(values: (number | null)[], low: number, high: number): number | null {
  const readings = values.filter((v): v is number => v != null)
  if (!readings.length) return null
  const inside = readings.filter((v) => v >= low && v <= high).length
  return Math.round((100 * inside) / readings.length)
}

/** The day's glucose in words for the summary line. Null when the sensor gave nothing. */
export function glucoseSummary(values: (number | null)[], low: number, high: number): string | null {
  const pct = timeInRange(values, low, high)
  if (pct == null) return null
  return `${pct}% of readings in your range, ${low.toFixed(1)} to ${high.toFixed(1)} mmol/L`
}

/** The day before or after, as "Wed 30 Sep", for the date arrows. Parsed as a calendar date, so no time zone shift. */
export function dayLabel(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  const date = new Date(y!, (m ?? 1) - 1, d ?? 1)
  return date.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })
}

/** Counts of what was logged, in words: "2 meals, 3 medicine times, 1 symptom". */
export function loggedSummary(markers: Pick<DayMarker, 'kind'>[]): string {
  const count = (k: DayMarker['kind']) => markers.filter((m) => m.kind === k).length
  const parts: string[] = []
  const add = (n: number, one: string, many: string) => {
    if (n) parts.push(`${n} ${n === 1 ? one : many}`)
  }
  add(count('meal'), 'meal', 'meals')
  add(count('dose'), 'medicine time', 'medicine times')
  add(count('workout'), 'workout', 'workouts')
  add(count('symptom'), 'symptom', 'symptoms')
  return parts.length ? parts.join(', ') : 'Nothing logged'
}
