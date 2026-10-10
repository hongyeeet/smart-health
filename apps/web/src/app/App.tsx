import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Providers } from './Providers'
import { Shell } from './Shell'
import { routedIds, screenFor } from './screens'
import { ROUTES } from './routeIds'
import { ReportA4 } from '@/features/brief/ReportA4'
import { SharedReport } from '@/features/brief/SharedReport'
import { Day } from '@/features/day/Day'

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
              return path === '/' ? <Route key={id} index element={<Comp />} /> : <Route key={id} path={path.slice(1)} element={<Comp />} />
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
