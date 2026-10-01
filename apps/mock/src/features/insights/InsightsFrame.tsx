import type { ReactNode } from 'react'
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom'
import type { Period } from '@/data/types'
import { href, type RouteId } from '@/app/routeIds'
import { useGo } from '@/app/navigation'
import { Header, Screen } from '@/ui/layout'
import { Segmented, TabStrip } from '@/ui/controls'
import { TextLink } from '@/ui/primitives'
import { Question } from '@/ui/icons'

const TABS: { value: RouteId; label: string }[] = [
  { value: 'C1', label: 'Overview' },
  { value: 'C2', label: 'Glucose' },
  { value: 'C3', label: 'Food' },
  { value: 'C4', label: 'Activity' },
  { value: 'C5', label: 'Sleep and stress' },
  { value: 'C6', label: 'Medication' },
]

export function usePeriod(): [Period, (p: Period) => void] {
  const [sp, setSp] = useSearchParams()
  const raw = Number(sp.get('period'))
  const period: Period = raw === 7 || raw === 30 || raw === 90 ? raw : 30
  return [period, (p) => setSp({ period: String(p) }, { replace: true })]
}

/** Shared frame: title, the six tabs, and (where it makes sense) the 7 / 30 / 90 day switch. */
export function InsightsFrame({ children, period = true }: { children: ReactNode; period?: boolean }) {
  const navigate = useNavigate()
  const { pathname, search } = useLocation()
  const [p, setP] = usePeriod()
  const current = (TABS.find((t) => href(t.value) === pathname)?.value ?? 'C1') as RouteId
  return (
    <Screen tabs>
      <Header title="Insights" />
      <TabStrip label="Insights sections" tabs={TABS} value={current} onChange={(v) => navigate(href(v) + search, { replace: true })} />
      {period && <Segmented<Period> label="Period" value={p} onChange={setP} options={[{ value: 7, label: '7 days' }, { value: 30, label: '30 days' }, { value: 90, label: '90 days' }]} />}
      {children}
    </Screen>
  )
}

export function WhyLink({ topic }: { topic?: string }) {
  const go = useGo()
  return (
    <TextLink icon={Question} onClick={() => go('C7', { sheet: { topic } })} className="self-start">
      Why am I seeing this?
    </TextLink>
  )
}

/** One plain sentence above every chart. */
export function Summary({ children }: { children: ReactNode }) {
  return <p className="text-body text-ink">{children}</p>
}
