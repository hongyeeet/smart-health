import { useSyncExternalStore } from 'react'
import { useUi } from '@/state/store'
import type { MealDraft } from './meal/mealDraft'

/** A meal the person has started eating but not yet finished (from a photo reading or typed in by hand). */
export interface MealInProgress extends MealDraft {
  startedAt: string
}

/** One copy per person on this device: `smart-health-meal-in-progress:<user>`. */
const PREFIX = 'smart-health-meal-in-progress'
const keyFor = (user: string) => `${PREFIX}:${user}`

/** The old copy had no person in its key, so it may belong to anyone who used the device. It is dropped, not moved. */
try {
  window.localStorage.removeItem(PREFIX)
} catch {
  /* storage is blocked: nothing to remove */
}

const cache = new Map<string, MealInProgress | null>()
const listeners = new Set<() => void>()

function readStored(user: string): MealInProgress | null {
  try {
    const raw = window.localStorage.getItem(keyFor(user))
    return raw ? (JSON.parse(raw) as MealInProgress) : null
  } catch {
    return null
  }
}

function load(user: string): MealInProgress | null {
  if (!cache.has(user)) cache.set(user, readStored(user))
  return cache.get(user) ?? null
}

function save(user: string, meal: MealInProgress | null) {
  cache.set(user, meal)
  try {
    if (meal) window.localStorage.setItem(keyFor(user), JSON.stringify(meal))
    else window.localStorage.removeItem(keyFor(user))
  } catch {
    /* storage is blocked: the meal still lasts until the page is closed */
  }
  listeners.forEach((l) => l())
}

const subscribe = (l: () => void) => {
  listeners.add(l)
  return () => {
    listeners.delete(l)
  }
}

/**
 * Kept on the device (and across a refresh) from "Start eating" until "I've finished eating", because the finish time is
 * when the person taps, which can be half an hour later. Only then is the meal written to the database.
 * Each person has their own meal: switching the person shows only that person's meal, and start, clear and finish act on
 * the person who started the meal.
 */
export function useMealSession() {
  const user = useUi((s) => s.userKey)
  const meal = useSyncExternalStore(subscribe, () => load(user))
  return {
    meal,
    start: (m: MealInProgress) => save(user, m),
    clear: () => save(user, null),
  }
}
