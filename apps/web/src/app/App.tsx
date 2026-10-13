import { useEffect, useState, type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { Providers } from './Providers'
import { Shell } from './Shell'
import { routedIds, screenFor } from './screens'
import { ROUTES, href } from './routeIds'
import { ReportA4 } from '@/features/brief/ReportA4'
import { SharedReport } from '@/features/brief/SharedReport'
import { Day } from '@/features/day/Day'
import { request } from '@/data/repositories/http'
import { useUi } from '@/state/store'
import type { SavedOnboarding } from '@/features/onboarding/api'
import { NEW_PERSON_PREFIX, needsSetup, startsInSetup } from '@/features/onboarding/startGate'

/* Set when the app opened at "/": only that first visit is checked. Later visits to Home (for example "Go to Home" from setup) are not. */
const openedAtHome = typeof window !== 'undefined' && window.location.pathname === '/'
let startChecked = false

/**
 * Home, after the start-up check. A new person who has not finished setup is sent to Welcome once, when the app opens on Home. The demo
 * user is sent there every time the app opens on Home (set-up has a Skip link for it). If the record cannot be read, Home opens as usual,
 * so no one is kept from it.
 */
function StartGate({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const user = useUi((s) => s.userKey)
  const [checking, setChecking] = useState(() => openedAtHome && !startChecked && (user.startsWith(NEW_PERSON_PREFIX) || startsInSetup(user)))
  useEffect(() => {
    startChecked = true
    if (!checking) return
    if (startsInSetup(user)) {                      // the demo user does not need the record read: set-up opens first
      navigate(href('A1'), { replace: true })
      setChecking(false)
      return
    }
    let live = true
    request<SavedOnboarding>('/onboarding')
      .then((saved) => {
        if (live && needsSetup(user, saved)) navigate(href('A1'), { replace: true })
      })
      .catch(() => {
        /* the record could not be read: Home opens */
      })
      .finally(() => {
        if (live) setChecking(false)
      })
    return () => {
      live = false
    }
  }, [checking, user, navigate])
  if (checking) return <div role="status" aria-live="polite" className="h-full"><span className="sr-only">Loading</span></div>
  return <>{children}</>
}

/** Every routed screen in routeIds.ts gets a route. Unbuilt ones show a placeholder (see screens.tsx). */
export function App() {
  return (
    <Providers>
      <BrowserRouter>
        <Routes>
          {/* The printable report is a paper page, outside the app frame. */}
          <Route path={ROUTES.L3.path} element={<ReportA4 />} />
          {/* What a doctor sees from a share link: read-only, outside the app frame, no sign-in. */}
          <Route path="/s/:token" element={<SharedReport />} />
          <Route element={<Shell />}>
            {routedIds.map((id) => {
              const Comp = screenFor(id)
              const path = ROUTES[id].path
              const element = path === '/' ? <StartGate><Comp /></StartGate> : <Comp />
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
