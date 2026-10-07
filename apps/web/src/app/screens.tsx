import type { ComponentType } from 'react'
import { NotBuilt } from './NotBuilt'
import { WorkoutTracker } from '@/features/workout/WorkoutTracker'
import { ScanFrame } from '@/features/scan/ScanFrame'
import { ScanReview } from '@/features/scan/ScanReview'
import { ScanPlan } from '@/features/scan/ScanPlan'
import { AddByHand } from '@/features/meds/AddByHand'
import { MedList } from '@/features/meds/MedList'
import { LogHub } from '@/features/log/LogHub'
import { LogDone } from '@/features/log/LogDone'
import { LogSymptom } from '@/features/log/LogSymptom'
import { LogCheckin } from '@/features/log/LogCheckin'
import { LogMeal } from '@/features/log/LogMeal'
import { LogWorkout } from '@/features/workout/LogWorkout'
import { Home } from '@/features/home/Home'
import { Me } from '@/features/me/Me'
import { Learned } from '@/features/me/Learned'
import { Progress } from '@/features/me/Progress'
import { LunchIdeas } from '@/features/log/LunchIdeas'
import { Notifications } from '@/features/home/Notifications'
import { ROUTES, routeIds, type RouteId } from './routeIds'

/**
 * Built screens, by route id. Anything not listed here shows the "not built yet" placeholder, so the whole
 * navigation works from day one and each screen is swapped in as it is built.
 *
 *   import { Home } from '@/features/home/Home'
 *   export const built: Partial<Record<RouteId, ComponentType>> = { B1: Home }
 */
export const built: Partial<Record<RouteId, ComponentType>> = {
  B1: Home,
  B2: Notifications,
  K1: Me,
  K2: Learned,
  K10: Progress,
  F1: LogWorkout,
  F2: WorkoutTracker,
  H1: MedList,
  H2: ScanFrame,
  H3: ScanReview,
  H4: ScanPlan,
  H8: AddByHand,
  E1: LogHub,
  E2: LogMeal,
  E4: LogSymptom,
  E5: LogCheckin,
  E6: LogDone,
  E8: LunchIdeas,
}

export function screenFor(id: RouteId): ComponentType {
  return built[id] ?? (() => <NotBuilt id={id} />)
}

/** Screens that are routes (not sheets, not pages outside the app frame). */
export const routedIds: RouteId[] = routeIds.filter((id) => ROUTES[id].kind === 'tab' || ROUTES[id].kind === 'screen')
