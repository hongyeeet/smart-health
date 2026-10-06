import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { MealAnalysis } from '@/data/types'

/** A meal the person has photographed and started eating but not yet finished. */
export interface MealInProgress {
  startedAt: string
  description: string
  analysis: MealAnalysis
  portion: number
  /** the numbers as the person last saw them (after edits), already scaled by the portion */
  name: string
  macros: MealAnalysis['macros']
  edited: boolean
  valuesFrom: 'ai' | 'user'
}

interface State {
  meal: MealInProgress | null
  start: (m: MealInProgress) => void
  clear: () => void
}

/**
 * Kept on the device (and across a refresh) from "Start eating" until "I've finished eating", because the finish time is
 * when the person taps, which can be half an hour later. Only then is the meal written to the database.
 */
export const useMealSession = create<State>()(
  persist(
    (set) => ({
      meal: null,
      start: (meal) => set({ meal }),
      clear: () => set({ meal: null }),
    }),
    { name: 'smart-health-meal-in-progress' },
  ),
)
