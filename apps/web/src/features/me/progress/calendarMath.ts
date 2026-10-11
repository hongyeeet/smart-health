/**
 * Calendar helpers for Diet tracking (K10). Days are Singapore days written YYYY-MM-DD, so "today" and the months do not depend on
 * the clock zone of the phone or laptop. Pure functions, no React.
 */
import type { DietDay } from '@/data/types'

export interface Month {
  year: number
  /** 1 to 12 */
  month: number
}

const pad = (n: number) => String(n).padStart(2, '0')

/** Today in Singapore as YYYY-MM-DD. */
export function sgToday(now: Date = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Singapore', year: 'numeric', month: '2-digit', day: '2-digit' }).format(now)
}

export const monthOf = (iso: string): Month => ({ year: Number(iso.slice(0, 4)), month: Number(iso.slice(5, 7)) })

export function addMonths(m: Month, n: number): Month {
  const x = m.year * 12 + (m.month - 1) + n
  return { year: Math.floor(x / 12), month: (x % 12) + 1 }
}

/** Negative when `a` is earlier than `b`. */
export const compareMonths = (a: Month, b: Month) => a.year * 12 + a.month - (b.year * 12 + b.month)

export function daysInMonth(m: Month): number {
  return new Date(Date.UTC(m.year, m.month, 0)).getUTCDate()
}

/** First and last day of the month, as YYYY-MM-DD. */
export function monthRange(m: Month): { start: string; end: string } {
  return { start: `${m.year}-${pad(m.month)}-01`, end: `${m.year}-${pad(m.month)}-${pad(daysInMonth(m))}` }
}

/** Empty cells before the 1st, so that Monday is the first column. */
export function leadingBlanks(m: Month): number {
  return (new Date(Date.UTC(m.year, m.month - 1, 1)).getUTCDay() + 6) % 7
}

/** The day numbers' ISO dates for the month, in order. */
export function isoDays(m: Month): string[] {
  return Array.from({ length: daysInMonth(m) }, (_, i) => `${m.year}-${pad(m.month)}-${pad(i + 1)}`)
}

export function monthLabel(m: Month, locale = 'en-GB'): string {
  return new Date(Date.UTC(m.year, m.month - 1, 1)).toLocaleDateString(locale, { month: 'long', year: 'numeric', timeZone: 'UTC' })
}

/** Weekday names for a Monday-first header, short form. */
export function weekdayHeaders(locale = 'en-GB'): string[] {
  // 2026-10-05 is a Monday
  return Array.from({ length: 7 }, (_, i) => new Date(Date.UTC(2026, 9, 5 + i)).toLocaleDateString(locale, { weekday: 'short', timeZone: 'UTC' }))
}

/** Calories (kcal) at which the colour steps change, for one day. Amounts only, not a target or a verdict. */
export const KCAL_STEPS = [1000, 1500, 2000] as const

/**
 * How much was logged that day, as a colour step from 1 (least) to 4 (most). 0 means no colour: no meals logged, or the
 * calories are not known for that day. Unknown is never shown as zero.
 */
export function levelOf(day: DietDay | undefined): number {
  const kcal = day?.totals.kcal
  if (!day || day.meals === 0 || kcal == null) return 0
  if (kcal < KCAL_STEPS[0]) return 1
  if (kcal < KCAL_STEPS[1]) return 2
  if (kcal < KCAL_STEPS[2]) return 3
  return 4
}
