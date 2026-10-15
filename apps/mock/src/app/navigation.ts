import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ROUTES, href, type RouteId } from './routeIds'
import { useUi, type SheetId } from '@/state/store'

/**
 * go('D1', { date }) navigates to a screen or opens a sheet, depending on what the registry says.
 * Screens never build URLs by hand, so a path change is one edit in routeIds.ts.
 */
export function useGo() {
  const navigate = useNavigate()
  const openSheet = useUi((s) => s.openSheet)
  return useCallback(
    (id: RouteId, opts?: { params?: Record<string, string>; sheet?: Record<string, unknown>; replace?: boolean }) => {
      const def = ROUTES[id]
      if (def.kind === 'sheet') {
        openSheet(id as SheetId, opts?.sheet)
        return
      }
      navigate(href(id, opts?.params), { replace: opts?.replace })
    },
    [navigate, openSheet],
  )
}

export function useBack(fallback: RouteId = 'B1') {
  const navigate = useNavigate()
  return useCallback(() => {
    if (window.history.state && window.history.state.idx > 0) navigate(-1)
    else navigate(href(fallback), { replace: true })
  }, [navigate, fallback])
}
