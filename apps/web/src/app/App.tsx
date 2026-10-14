import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Providers } from './Providers'
import { Shell } from './Shell'
import { routedIds, screenFor } from './screens'
import { ROUTES } from './routeIds'
import { ReportA4 } from '@/features/brief/ReportA4'
import { SharedReport } from '@/features/brief/SharedReport'
import { Day } from '@/features/day/Day'
import { useUi } from '@/state/store'
import { dropPendingPerson } from '@/features/onboarding/newPerson'

/**
 * A new person whose set-up is open exists only inside set-up (the /welcome screens). If the app goes anywhere else before Finish (the
 * address bar, a link, the browser's back button), the new person is dropped and the person shown before comes back.
 */
function NewPersonGuard() {
  const { pathname } = useLocation()
  const qc = useQueryClient()
  useEffect(() => {
    const { pending, setUserKey } = useUi.getState()
    if (!pending || pathname.startsWith('/welcome')) return
    dropPendingPerson()
    setUserKey(pending.returnTo)
    void qc.resetQueries()
  }, [pathname, qc])
  return null
}

/** Every routed screen in routeIds.ts gets a route. Unbuilt ones show a placeholder (see screens.tsx). */
export function App() {
  return (
    <Providers>
      <BrowserRouter>
        <NewPersonGuard />
        <Routes>
          {/* The printable report is a paper page, outside the app frame. */}
          <Route path={ROUTES.L3.path} element={<ReportA4 />} />
          {/* What a doctor sees from a share link: read-only, outside the app frame, no sign-in. */}
          <Route path="/s/:token" element={<SharedReport />} />
          <Route element={<Shell />}>
            {routedIds.map((id) => {
              const Comp = screenFor(id)
              const path = ROUTES[id].path
              const element = <Comp />
              return path === '/' ? <Route key={id} index element={element} /> : <Route key={id} path={path.slice(1)} element={element} />
            })}
            {/* /day with no date opens the latest day that has data (Day redirects) */}
            <Route path="day" element={<Day />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </Providers>
  )
}
