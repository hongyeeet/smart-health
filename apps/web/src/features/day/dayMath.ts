import i18n from '@/i18n'
import { dateLocale } from '@/lib/locale'
import { clock } from '@/lib/format'
import type { DayMarker, DoseState } from './api'

/** Pure helpers for the Day view. No React here, so they can be checked on their own. */

export type Tone = 'brass' | 'ok' | 'late' | 'unconfirmed' | 'missed' | 'brand' | 'warn' | 'plain'

/** "7:40 am" for a minute after midnight. */
export const clockWords = (minute: number) => clock(minute)

/** The words for a dose state. Colour and icon are never the only signal. */
export function doseWords(state: DoseState): string {
  switch (state) {
    case 'taken':
      return i18n.t('day.dose.taken', 'taken on time')
    case 'late':
      return i18n.t('day.dose.late', 'taken late')
    case 'not_confirmed':
      return i18n.t('day.dose.notConfirmed', 'not confirmed yet')
    case 'missed':
      return i18n.t('day.dose.missed', 'missed')
  }
}

/** Which look a marker gets. Doses follow their state; the rest follow their kind. */
export function markerTone(m: Pick<DayMarker, 'kind' | 'status'>): Tone {
  if (m.kind === 'meal') return 'brass'
  if (m.kind === 'workout') return 'brand'
  if (m.kind === 'symptom') return 'warn'
  if (m.kind === 'pressure') return 'plain'
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
  return i18n.t('day.glucoseSummary', '{{pct}}% of readings in your range, {{low}} to {{high}} mmol/L', {
    pct,
    low: low.toFixed(1),
    high: high.toFixed(1),
  })
}

/** The day before or after, as "Wed 30 Sep", for the date arrows. Parsed as a calendar date, so no time zone shift. */
export function dayLabel(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  const date = new Date(y!, (m ?? 1) - 1, d ?? 1)
  return date.toLocaleDateString(dateLocale('en-GB'), { weekday: 'short', day: 'numeric', month: 'short' })
}

/** Counts of what was logged, in words: "2 meals, 3 medicine times, 1 symptom". */
export function loggedSummary(markers: Pick<DayMarker, 'kind'>[]): string {
  const count = (k: DayMarker['kind']) => markers.filter((m) => m.kind === k).length
  const meals = count('meal')
  const doses = count('dose')
  const workouts = count('workout')
  const symptoms = count('symptom')
  const readings = count('pressure')
  const parts = [
    meals === 1 ? i18n.t('day.logged.mealOne', '{{n}} meal', { n: meals }) : meals > 1 ? i18n.t('day.logged.mealMany', '{{n}} meals', { n: meals }) : '',
    doses === 1 ? i18n.t('day.logged.doseOne', '{{n}} medicine time', { n: doses }) : doses > 1 ? i18n.t('day.logged.doseMany', '{{n}} medicine times', { n: doses }) : '',
    workouts === 1 ? i18n.t('day.logged.workoutOne', '{{n}} workout', { n: workouts }) : workouts > 1 ? i18n.t('day.logged.workoutMany', '{{n}} workouts', { n: workouts }) : '',
    symptoms === 1 ? i18n.t('day.logged.symptomOne', '{{n}} symptom', { n: symptoms }) : symptoms > 1 ? i18n.t('day.logged.symptomMany', '{{n}} symptoms', { n: symptoms }) : '',
    readings === 1 ? i18n.t('day.logged.pressureOne', '{{n}} blood pressure reading', { n: readings }) : readings > 1 ? i18n.t('day.logged.pressureMany', '{{n}} blood pressure readings', { n: readings }) : '',
  ].filter((p) => p !== '')
  return parts.length ? parts.join(', ') : i18n.t('day.logged.none', 'Nothing logged')
}
