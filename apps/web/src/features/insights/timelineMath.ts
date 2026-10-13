/**
 * The arithmetic behind the Overview charts, with no React in it: where a time sits on the shared axis, a person's baseline at that time of
 * day, and how a reading compares with it. All numbers come from the server (GET /insights/timeline); nothing is judged here, only
 * "above", "below" or "within" the person's own usual range, and by how much against their own baseline.
 */
import type { InsightsHourly, InsightsTimeline } from '@/data/types'

export const DAY_MIN = 1440

/** The baseline (or one end of the usual range) at a minute of the day: a straight line between the hour centres, round the clock. A daily bucket has no hour, so it gets the average of the 24. */
export function hourlyAt(arr: (number | null)[], minOfDay: number, daily = false): number | null {
  if (daily) {
    const present = arr.filter((v): v is number => v != null)
    return present.length ? present.reduce((a, b) => a + b, 0) / present.length : null
  }
  const p = minOfDay / 60 - 0.5
  const h0 = ((Math.floor(p) % 24) + 24) % 24
  const h1 = (h0 + 1) % 24
  const f = p - Math.floor(p)
  const a = arr[h0]
  const b = arr[h1]
  if (a == null || b == null) return a ?? b ?? null
  return a + (b - a) * f
}

export type Compare = 'above' | 'below' | 'within' | 'unknown'

export interface Reading {
  value: number | null
  baseline: number | null
  lo: number | null
  hi: number | null
  /** value minus baseline */
  diff: number | null
  /** against the usual range (middle half of the person's own hours); 'unknown' when there is no value or no range */
  compare: Compare
}

/** What the marker reads on one chart at `m` minutes from the start. */
export function readAt(series: (number | null)[], h: InsightsHourly, step: number, m: number): Reading {
  const k = Math.min(series.length - 1, Math.max(0, Math.floor(m / step)))
  const value = series[k] ?? null
  const daily = step >= DAY_MIN
  // the centre of the bucket, so a 2-hour bucket is compared with the baseline at its middle
  const mid = (k * step + step / 2) % DAY_MIN
  const baseline = hourlyAt(h.mean, mid, daily)
  const lo = hourlyAt(h.lo, mid, daily)
  const hi = hourlyAt(h.hi, mid, daily)
  let compare: Compare = 'unknown'
  if (value != null && lo != null && hi != null) compare = value > hi ? 'above' : value < lo ? 'below' : 'within'
  return {
    value,
    baseline,
    lo,
    hi,
    diff: value != null && baseline != null ? value - baseline : null,
    compare,
  }
}

/** The nearest blood pressure reading to the marker, and how many minutes before (negative) or after (positive) it is. */
export function nearestBp(bp: InsightsTimeline['bp'], m: number): { reading: InsightsTimeline['bp'][number]; gap: number } | null {
  let best: InsightsTimeline['bp'][number] | null = null
  for (const r of bp) if (!best || Math.abs(r.m - m) < Math.abs(best.m - m)) best = r
  return best ? { reading: best, gap: best.m - m } : null
}

/** "2 h 10 min", "45 min", "0 min" for a gap in minutes (sign ignored). */
export function gapText(mins: number): { h: number; min: number } {
  const a = Math.abs(Math.round(mins))
  return { h: Math.floor(a / 60), min: a % 60 }
}

/** ISO weekday of the local date `iso` plus `dayIndex` days: 1 = Monday ... 7 = Sunday. */
export function isoWeekday(iso: string, dayIndex = 0): number {
  const d = new Date(`${iso}T12:00:00`)
  d.setDate(d.getDate() + dayIndex)
  return ((d.getDay() + 6) % 7) + 1
}

export const clockMin = (hhmm: string | null): number | null => {
  if (!hhmm) return null
  const [h, m] = hhmm.split(':').map(Number)
  return (h ?? 0) * 60 + (m ?? 0)
}

/** Are we inside the person's work hours at `m` minutes from the start? */
export function atWork(work: InsightsTimeline['work'], startIso: string, m: number): 'during' | 'outside' | 'off' | 'unset' {
  if (!work.set) return 'unset'
  const day = Math.floor(m / DAY_MIN)
  if (!work.days.includes(isoWeekday(startIso, day))) return 'off'
  const s = clockMin(work.start)
  const e = clockMin(work.end)
  const t = m % DAY_MIN
  return s != null && e != null && t >= s && t < e ? 'during' : 'outside'
}

/** Round axis numbers inside [lo, hi]: about `count` of them, on 1, 2 or 5 steps. */
export function niceTicks(lo: number, hi: number, count = 3): number[] {
  const span = hi - lo
  if (!(span > 0)) return [lo]
  const raw = span / count
  const pow = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 5, 10].map((x) => x * pow).find((s) => s >= raw) ?? raw
  const out: number[] = []
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(Math.round(v * 1e6) / 1e6)
  return out
}

/** A vertical domain that holds every value (and the baseline), with room. */
export function domain(values: (number | null | undefined)[], pad = 0.08, floor?: number, ceil?: number): [number, number] {
  const present = values.filter((v): v is number => v != null)
  if (!present.length) return [0, 1]
  let lo = Math.min(...present)
  let hi = Math.max(...present)
  if (hi === lo) {
    lo -= 1
    hi += 1
  }
  const room = (hi - lo) * pad
  lo -= room
  hi += room
  if (floor != null) lo = Math.max(floor, lo)
  if (ceil != null) hi = Math.min(ceil, hi)
  return [lo, hi]
}

/** Build the `d` of a polyline over buckets; a missing bucket breaks the line (never a 0). `x(k)` and `y(v)` are in chart units. */
export function linePath(values: (number | null)[], x: (k: number) => number, y: (v: number) => number): string {
  let d = ''
  let pen = false
  values.forEach((v, k) => {
    if (v == null) {
      pen = false
      return
    }
    d += `${pen ? 'L' : 'M'}${x(k).toFixed(1)} ${y(v).toFixed(1)}`
    pen = true
  })
  return d
}

/** The part of a line outside the usual range, drawn thicker: pieces of consecutive buckets whose value is above `hi` or below `lo` at that time of day. */
export function outsidePath(values: (number | null)[], h: InsightsHourly, step: number, x: (k: number) => number, y: (v: number) => number): string {
  const daily = step >= DAY_MIN
  const out = values.map((v, k) => {
    if (v == null) return null
    const mid = (k * step + step / 2) % DAY_MIN
    const lo = hourlyAt(h.lo, mid, daily)
    const hi = hourlyAt(h.hi, mid, daily)
    return lo != null && hi != null && (v > hi || v < lo) ? v : null
  })
  return linePath(out, x, y)
}

/** The baseline across the whole period as a line, one point every half hour of the day (a daily view gets one flat line). */
export function baselinePath(h: InsightsHourly, days: number, step: number, x: (m: number) => number, y: (v: number) => number): string {
  if (step >= DAY_MIN) {
    const v = hourlyAt(h.mean, 0, true)
    return v == null ? '' : `M${x(0).toFixed(1)} ${y(v).toFixed(1)}L${x(days * DAY_MIN).toFixed(1)} ${y(v).toFixed(1)}`
  }
  const pts: (number | null)[] = []
  const at: number[] = []
  for (let m = 0; m <= days * DAY_MIN; m += 30) {
    pts.push(hourlyAt(h.mean, m % DAY_MIN))
    at.push(m)
  }
  return linePath(pts, (k) => x(at[k] ?? 0), y)
}

/** The usual range as a filled band over the whole period (hourly points); empty in a daily view, where a band by hour has no meaning. */
export function bandPath(h: InsightsHourly, days: number, step: number, x: (m: number) => number, y: (v: number) => number): string {
  if (step >= DAY_MIN) return ''
  const top: string[] = []
  const bottom: string[] = []
  for (let m = 0; m <= days * DAY_MIN; m += 60) {
    const hi = hourlyAt(h.hi, m % DAY_MIN)
    const lo = hourlyAt(h.lo, m % DAY_MIN)
    if (hi == null || lo == null) return ''
    top.push(`${x(m).toFixed(1)} ${y(hi).toFixed(1)}`)
    bottom.push(`${x(m).toFixed(1)} ${y(lo).toFixed(1)}`)
  }
  return `M${top.join('L')}L${bottom.reverse().join('L')}Z`
}
