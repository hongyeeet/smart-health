import { useNavigate } from 'react-router-dom'
import { appConfig } from '@/config/app'
import { useUi, type SheetId } from '@/state/store'
import { useSync } from '@/data/hooks'
import { Segmented } from '@/ui/controls'
import { Button, Card } from '@/ui/primitives'
import { ROUTES, routeIds, href, type RouteId } from './routeIds'
import { X } from '@/ui/icons'

const groups = Array.from(new Set(routeIds.filter((id) => ROUTES[id].kind !== 'external' || id === 'L3').map((id) => ROUTES[id].group)))

/**
 * Prototype controls. They live outside the phone and are not part of the product.
 * Remove the panel by setting appConfig.demoTools to false.
 */
export function DemoPanel({ onClose }: { onClose?: () => void }) {
  const navigate = useNavigate()
  const { theme, setTheme, textScale, setTextScale, openSheet, showToast } = useUi()
  const sync = useSync()
  if (!appConfig.demoTools) return null

  const jump = (id: RouteId) => {
    const def = ROUTES[id]
    if (def.kind === 'sheet') {
      openSheet(id as SheetId, id === 'H7' ? { doseId: 'd-met-pm-y' } : undefined)
      onClose?.()
      return
    }
    const path = href(id, { date: appConfig.demo.today, id: 'metformin' })
    if (id === 'L3' || id === 'X1') window.open(path, '_blank')
    else navigate(path)
    onClose?.()
  }

  return (
    <aside aria-label="Prototype controls" className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-serif text-h1 font-medium tracking-tight">Smart Health</p>
          <p className="text-sub text-ink2">Prototype controls. These are not part of the app.</p>
        </div>
        {onClose && (
          <button type="button" aria-label="Close controls" onClick={onClose} className="press flex h-12 w-12 flex-none items-center justify-center rounded-full hover:bg-well">
            <X size={24} />
          </button>
        )}
      </div>

      <Card className="flex flex-col gap-3">
        <p className="text-sub font-bold">Display</p>
        <Segmented label="Colour theme" value={theme} onChange={setTheme} options={[{ value: 'light', label: 'Light' }, { value: 'dark', label: 'Dark' }]} />
        <Segmented label="Text size" value={textScale} onChange={setTextScale} options={[{ value: 1, label: 'Text 100%' }, { value: 2, label: 'Text 200%' }]} />
      </Card>

      <Card className="flex flex-col gap-2">
        <p className="text-sub font-bold">Simulate</p>
        <Button variant="secondary" size="md" onClick={() => jump('J1')}>
          A very low reading (2.8 mmol/L)
        </Button>
        <Button
          variant="secondary"
          size="md"
          onClick={() =>
            sync.mutate(undefined, {
              onSuccess: () => showToast('Watch and sensor synced'),
            })
          }
        >
          A sensor sync
        </Button>
        <Button variant="secondary" size="md" onClick={() => jump('A1')}>
          Start from onboarding
        </Button>
        <Button variant="ghost" size="md" onClick={() => window.location.assign('/')}>
          Reset the demo data
        </Button>
      </Card>

      <Card className="flex flex-col gap-2">
        <p className="text-sub font-bold">Jump to a screen</p>
        <div className="flex flex-col gap-3">
          {groups.map((g) => (
            <div key={g}>
              <p className="text-sub text-ink3">{g}</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {routeIds
                  .filter((id) => ROUTES[id].group === g && ROUTES[id].kind !== 'external' || (ROUTES[id].group === g && id === 'L3'))
                  .map((id) => (
                    <button key={id} type="button" onClick={() => jump(id)} className="press min-h-11 rounded-chip border border-line bg-card px-3 text-sub hover:bg-brand-soft">
                      <span className="font-bold text-brand">{id}</span> {ROUTES[id].title.length > 22 ? ROUTES[id].title.slice(0, 20) + '…' : ROUTES[id].title}
                    </button>
                  ))}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div className="flex flex-col gap-2">
        <Button variant="ghost" size="md" onClick={() => jump('X1')}>
          Open the screen index
        </Button>
        <Button variant="ghost" size="md" onClick={() => jump('L3')}>
          Open the A4 doctor brief
        </Button>
      </div>
    </aside>
  )
}
