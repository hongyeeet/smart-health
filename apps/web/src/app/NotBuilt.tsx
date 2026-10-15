import { Header, Screen } from '@/ui/layout'
import { Card, EmptyState } from '@/ui/primitives'
import { ClipboardText } from '@/ui/icons'
import { ROUTES, type RouteId } from './routeIds'

/**
 * Placeholder for a screen that is in the route registry but not built yet. Its notes (where it opens from,
 * where it links) come from the registry, so whoever builds it has the brief on screen.
 */
export function NotBuilt({ id }: { id: RouteId }) {
  const r = ROUTES[id]
  const tabs = r.kind === 'tab'
  return (
    <Screen tabs={tabs}>
      <Header title={r.title} back={!tabs} />
      <EmptyState icon={ClipboardText}>This screen is not built yet.</EmptyState>
      <Card tone="soft" className="flex flex-col gap-1.5 text-sub">
        <p>
          <b>Screen {id}</b> in group {r.group}
        </p>
        <p>
          <b>Opens from:</b> {r.from}
        </p>
        {r.links.length > 0 && (
          <p>
            <b>Links to:</b> {r.links.map((l) => `${l.label} (${l.to})`).join('. ')}
          </p>
        )}
        {'note' in r && r.note && <p>{r.note}</p>}
        <p className="text-ink3">Build it in src/features, then add it to src/app/screens.tsx. The clickable version is in apps/mock.</p>
      </Card>
    </Screen>
  )
}
