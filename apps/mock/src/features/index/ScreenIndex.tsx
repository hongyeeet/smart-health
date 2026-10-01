import { useEffect } from 'react'
import { applyPalette, palettes } from '@/theme/palettes'
import { ROUTES, routeIds, href, checkRegistry, type RouteId } from '@/app/routeIds'
import { clickPaths } from '@/app/clickPaths'
import { appConfig } from '@/config/app'

const groups = Array.from(new Set(routeIds.map((id) => ROUTES[id].group)))

/** Generated from the route registry, so it always matches the app. */
export function ScreenIndex() {
  useEffect(() => {
    applyPalette(document.documentElement, palettes.light)
    document.documentElement.dataset.theme = 'light'
    const bad = checkRegistry()
    if (bad.length) console.warn('Registry links to unknown ids:', bad)
  }, [])
  const open = (id: RouteId) => href(id, { date: appConfig.demo.today, id: 'metformin' })
  const label = (id: RouteId) => `${id} ${ROUTES[id].title}`
  return (
    <div className="mx-auto max-w-[1280px] px-6 py-10">
      <h1 className="font-serif text-display font-medium tracking-tight">Smart Health: screen index</h1>
      <p className="mt-3 max-w-3xl text-body text-ink2">
        Every screen and sheet, where it opens from and where it links. Generated from the route registry in <code>src/app/routeIds.ts</code>, so adding a screen there adds it here. Demo date: {appConfig.demo.dateLabel} 2026.
      </p>
      <div className="mt-8 columns-1 gap-6 md:columns-2 xl:columns-3">
        {groups.map((g) => (
          <section key={g} className="mb-6 break-inside-avoid rounded-card border border-line bg-card p-5">
            <h2 className="font-serif text-h1 font-medium">{g}</h2>
            <ul className="mt-2 divide-y divide-line">
              {routeIds
                .filter((id) => ROUTES[id].group === g)
                .map((id) => {
                  const r = ROUTES[id]
                  const isSheet = r.kind === 'sheet'
                  return (
                    <li key={id} className="py-3">
                      <div className="flex items-center gap-2">
                        <span className="min-w-9 rounded-md bg-brand-soft px-1.5 text-center text-sub font-bold text-brand">{id}</span>
                        {isSheet ? <span className="text-body font-bold">{r.title}</span> : <a className="text-body font-bold underline decoration-1 underline-offset-4" href={open(id)} target="_blank" rel="noreferrer">{r.title}</a>}
                        <span className="rounded-chip bg-well px-2 text-micro text-ink2">{r.kind}</span>
                      </div>
                      <p className="mt-1 text-sub text-ink2">
                        <b className="text-ink">From:</b> {r.from}
                      </p>
                      {r.links.length > 0 && (
                        <p className="text-sub text-ink2">
                          <b className="text-ink">Links:</b> {r.links.map((l) => `${l.label} (${l.to})`).join('. ')}
                        </p>
                      )}
                      {'note' in r && r.note && <p className="text-sub text-ink3">{r.note}</p>}
                    </li>
                  )
                })}
            </ul>
          </section>
        ))}
      </div>
      <h2 className="mt-4 font-serif text-h1 font-medium">The 9 click paths</h2>
      <div className="mt-3 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {clickPaths.map((p) => (
          <div key={p.title} className="rounded-card border border-line bg-card p-4">
            <h3 className="text-body font-bold">{p.title}</h3>
            <ol className="mt-1.5 list-decimal pl-5 text-sub text-ink2">
              {p.steps.map((s, i) => (
                <li key={i}>
                  <span className="font-bold text-ink">{label(s.id)}</span>: {s.action}
                </li>
              ))}
            </ol>
          </div>
        ))}
      </div>
    </div>
  )
}
