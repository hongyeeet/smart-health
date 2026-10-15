import type { LogInput } from '@/data/repositories/types'
import type { Macros, MealAnalysis } from '@/data/types'

/**
 * A meal the person is about to save: from a photo reading (`analysis` set) or typed in by hand (`analysis` null).
 * `macros` are the numbers for the amount eaten, already scaled by the portion.
 */
export interface MealDraft {
  name: string
  description: string
  portion: number
  macros: Macros
  analysis: MealAnalysis | null
  /** true once the person has changed a number or the name */
  edited: boolean
  valuesFrom: 'ai' | 'user'
}

/** The meal payload for POST /logs. Unknown values go as null, so the database never stores a guessed 0. */
export function mealPayload(d: MealDraft, startAt: string, endAt: string): Extract<LogInput, { kind: 'meal' }> {
  const m = d.macros
  return {
    kind: 'meal',
    name: d.name.trim() || d.analysis?.name || 'Your meal',
    description: d.description.trim() || undefined,
    startAt,
    endAt,
    portion: d.portion,
    kcal: m.kcal,
    carbsG: m.carbsG,
    proteinG: m.proteinG,
    fatG: m.fatG,
    sugarG: m.sugarG,
    fibreG: m.fibreG,
    sodiumMg: m.sodiumMg,
    analysisId: d.analysis?.analysisId,
    edited: d.edited,
    valuesFrom: d.valuesFrom,
  }
}
