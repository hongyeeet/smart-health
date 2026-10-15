/**
 * Pure helpers for Home's "Your numbers" and "Health overview": the status line under each card, the mini bars, the sparkline
 * points and the bar heights. No React here, so the rules can be read (and tested) in one place.
 *
 * Wording rule: a status only compares the person with THEIR OWN usual range. No verdict words, no advice. Unknown stays unknown.
 */
import type { TFunction } from 'i18next'
import type { KpiStatus, Nutrient } from '@/data/types'

export type StatusTone = 'ok' | 'warn' | 'info' | 'neutral'
export type StatusIcon = 'smiley' | 'up' | 'down' | null
export interface StatusLine {
  tone: StatusTone
  icon: StatusIcon
  text: string
}

const num = (n: number) => Math.round(n).toLocaleString('en-US')

/** the icon and colour for a range state: within is the smiley, above is an up arrow (warn), below is a down arrow (info) */
function look(state: KpiStatus['state']): { tone: StatusTone; icon: StatusIcon } {
  if (state === 'within') return { tone: 'ok', icon: 'smiley' }
  if (state === 'above') return { tone: 'warn', icon: 'up' }
  if (state === 'below') return { tone: 'info', icon: 'down' }
  return { tone: 'neutral', icon: null }
}

const unknownLine = (t: TFunction): StatusLine => ({ tone: 'neutral', icon: null, text: t('home.status.unknown', 'Not enough history yet to compare') })

/** Glucose: within, above or below the usual range, or unknown. */
export function rangeLine(t: TFunction, s: KpiStatus): StatusLine {
  if (s.state === 'unknown') return unknownLine(t)
  const text = s.state === 'within' ? t('home.status.within', 'Within your usual range') : s.state === 'above' ? t('home.status.above', 'Above your usual range') : t('home.status.below', 'Below your usual range')
  return { ...look(s.state), text }
}

/** Steps: the usual number is named, "Below your usual 7,284". Without a usual median it falls back to the plain range wording. */
export function stepsLine(t: TFunction, s: KpiStatus): StatusLine {
  if (s.state === 'unknown') return unknownLine(t)
  if (s.state === 'within' || s.usualMedian == null) return rangeLine(t, s)
  const n = num(s.usualMedian)
  const text = s.state === 'below' ? t('home.status.stepsBelow', 'Below your usual {{n}}', { n }) : t('home.status.stepsAbove', 'Above your usual {{n}}', { n })
  return { ...look(s.state), text }
}

/** how far a status is outside the usual range, in widths of that range (so bpm and SpO2 points can be compared); 0 when inside or unknown */
export function notability(s: KpiStatus): number {
  if (s.state !== 'above' && s.state !== 'below') return 0
  const d = Math.abs(s.delta ?? 0)
  const width = s.usualLow != null && s.usualHigh != null ? s.usualHigh - s.usualLow : 0
  return width > 0 ? d / width : d
}

/** Heart and oxygen: the more notable of the two, in plain numbers ("Average heart rate up 4 bpm from your usual"). */
/** A change smaller than this is read as within the usual range: 3 bpm of heart rate, 1 point of oxygen (the usual ranges are narrow, so a hair outside them is not a change). */
const MIN_BPM_CHANGE = 3
const MIN_O2_CHANGE = 1
function ignoreTiny(s: KpiStatus, min: number): KpiStatus {
  return (s.state === 'above' || s.state === 'below') && s.delta != null && Math.abs(s.delta) < min ? { ...s, state: 'within' } : s
}

export function heartLine(t: TFunction, hr0: KpiStatus, spo20: KpiStatus): StatusLine {
  const hr = ignoreTiny(hr0, MIN_BPM_CHANGE)
  const spo2 = ignoreTiny(spo20, MIN_O2_CHANGE)
  if (hr.state === 'unknown' && spo2.state === 'unknown') return unknownLine(t)
  const nh = notability(hr)
  const ns = notability(spo2)
  const pickSpo2 = ns > nh
  const s = pickSpo2 ? spo2 : hr
  if (s.state === 'unknown') return rangeLine(t, hr.state === 'unknown' ? spo2 : hr)
  if (s.state === 'within') return rangeLine(t, hr.state === 'within' ? hr : s)
  const n = Math.round(Math.abs(s.delta ?? 0))
  // a change that rounds to nothing is not worth a number: say it plainly
  if (n === 0) return rangeLine(t, s)
  const up = s.state === 'above'
  const text = pickSpo2
    ? up ? t('home.status.o2Up', 'Average oxygen up {{n}} points from your usual', { n }) : t('home.status.o2Down', 'Average oxygen down {{n}} points from your usual', { n })
    : up ? t('home.status.hrUp', 'Average heart rate up {{n}} bpm from your usual', { n }) : t('home.status.hrDown', 'Average heart rate down {{n}} bpm from your usual', { n })
  return { ...look(s.state), text }
}

/** Calories: a high salt or sugar nudge wins over the calories status; otherwise the calories status. */
export function caloriesLine(t: TFunction, status: KpiStatus, sugar: Nutrient, salt: Nutrient): StatusLine {
  const hs = salt.state === 'high'
  const hg = sugar.state === 'high'
  if (hs || hg) {
    const text = hs && hg ? t('home.status.saltSugarHigh', 'Salt and sugar are high. Go lighter on food.') : hs ? t('home.status.saltHigh', 'Salt is high. Go lighter on food.') : t('home.status.sugarHigh', 'Sugar is high. Go lighter on food.')
    return { tone: 'warn', icon: 'up', text }
  }
  return rangeLine(t, status)
}

/** A mini bar for Sugar or Salt: the share of the last 7 days' meals that were high. `null` width means no data (shown as a dash, never an empty bar). */
export function meterFill(n: Nutrient): { pct: number | null; high: boolean } {
  if (n.state === 'unknown' || n.highMeals == null || n.meals <= 0) return { pct: null, high: false }
  const share = Math.min(1, Math.max(0, n.highMeals / n.meals))
  // a few high meals must still be visible, and none at all must stay empty
  return { pct: share === 0 ? 0 : Math.max(6, Math.round(share * 100)), high: n.state === 'high' }
}

/** Points for a sparkline (SVG viewBox w x h). Missing days leave a gap: the line is split into runs, never drawn through a missing day. */
export function sparkRuns(values: (number | null)[], w: number, h: number, pad = 3): string[] {
  const real = values.filter((v): v is number => v != null)
  if (real.length === 0) return []
  const lo = Math.min(...real)
  const hi = Math.max(...real)
  const span = hi - lo
  const x = (i: number) => (values.length <= 1 ? w / 2 : pad + (i * (w - 2 * pad)) / (values.length - 1))
  const y = (v: number) => (span === 0 ? h / 2 : h - pad - ((v - lo) / span) * (h - 2 * pad))
  const runs: string[] = []
  let cur: string[] = []
  values.forEach((v, i) => {
    if (v == null) {
      if (cur.length) runs.push(cur.join(' '))
      cur = []
    } else cur.push(`${x(i).toFixed(1)},${y(v).toFixed(1)}`)
  })
  if (cur.length) runs.push(cur.join(' '))
  return runs
}

/** Heights (0 to 1) for a row of bars, scaled to the largest value; a missing day is null. A real value is never drawn below `floor`. */
export function barScale(values: (number | null)[], floor = 0.04): (number | null)[] {
  const real = values.filter((v): v is number => v != null)
  const max = real.length ? Math.max(...real) : 0
  return values.map((v) => (v == null ? null : max <= 0 ? floor : Math.max(floor, v / max)))
}

/** The bar shown selected at first: the newest day that has a value, or the last one. */
export function defaultSelected(values: (number | null)[]): number {
  for (let i = values.length - 1; i >= 0; i--) if (values[i] != null) return i
  return Math.max(0, values.length - 1)
}
