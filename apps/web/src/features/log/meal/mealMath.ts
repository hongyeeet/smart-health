import type { Macros } from '@/data/types'
import { dateLocale } from '@/lib/locale'

/** The nutrient keys in the order the macro card shows them (after calories, which is shown big). */
export type NutrientKey = keyof Macros

export const round1 = (v: number) => Math.round(v * 10) / 10

/** Scales the numbers for one portion to the amount eaten. A value that is not known stays not known (null). */
export function scaleMacros(m: Macros, portion: number): Macros {
  const f = (v: number | null) => (v == null ? null : round1(v * portion))
  return { kcal: f(m.kcal), carbsG: f(m.carbsG), proteinG: f(m.proteinG), fatG: f(m.fatG), fibreG: f(m.fibreG), sugarG: f(m.sugarG), sodiumMg: f(m.sodiumMg) }
}

/** Shows a number the way the card does: one decimal at most, blank when unknown. */
export const fmtAmount = (v: number | null) => (v == null ? '' : String(round1(v)))

export const fmtPortion = (v: number) => (v === 0.5 ? '½' : v === 1.5 ? '1½' : v === 2.5 ? '2½' : String(v))

export const mmss = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

export const clock = (iso: string | number | Date) => new Date(iso).toLocaleTimeString(dateLocale('en-US'), { hour: 'numeric', minute: '2-digit' }).toLowerCase()

/**
 * Reads what the person typed in a number box. A blank box means "not known" (null), never 0.
 * Anything that is not a number from 0 to 100000 is refused, so the screen can ask again.
 */
export function parseAmount(text: string): { ok: true; value: number | null } | { ok: false } {
  const s = text.trim().replace(',', '.')
  if (s === '') return { ok: true, value: null }
  const n = Number(s)
  if (!Number.isFinite(n) || n < 0 || n > 100000) return { ok: false }
  return { ok: true, value: round1(n) }
}
