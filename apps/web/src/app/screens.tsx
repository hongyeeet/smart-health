import type { ComponentType } from 'react'
import { NotBuilt } from './NotBuilt'
import { ROUTES, routeIds, type RouteId } from './routeIds'

/**
 * Built screens, by route id. Anything not listed here shows the "not built yet" placeholder, so the whole
 * navigation works from day one and each screen is swapped in as it is built.
 *
 *   import { Home } from '@/features/home/Home'
 *   export const built: Partial<Record<RouteId, ComponentType>> = { B1: Home }
 */
export const built: Partial<Record<RouteId, ComponentType>> = {}

export function screenFor(id: RouteId): ComponentType {
  return built[id] ?? (() => <NotBuilt id={id} />)
}

/** Screens that are routes (not sheets, not pages outside the app frame). */
export const routedIds: RouteId[] = routeIds.filter((id) => ROUTES[id].kind === 'tab' || ROUTES[id].kind === 'screen')
