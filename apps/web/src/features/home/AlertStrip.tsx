/**
 * Block 1 on Home: the alert strip. The active low-glucose alert comes first (red, opens J1), then the open medicine clash alerts
 * the person has not set aside (opens B2, where each has its own actions). Renders nothing when there is no alert.
 */
import { useTranslation } from 'react-i18next'
import { useGo } from '@/app/navigation'
import { useStock } from '@/data/hooks'
import type { ClashAlert, MedicineStock } from '@/data/types'
import { useUrgentState } from '@/features/urgent/api'
import { WarningCircle } from '@/ui/icons'
import { Alert } from '@/ui/primitives'

/** Shown first on Home while a low glucose alert is open. */
function UrgentBanner() {
  const { t } = useTranslation()
  const { data } = useUrgentState()
  const go = useGo()
  if (!data || (data.status !== 'active' && data.status !== 'escalated')) return null
  return (
    <Alert tone="danger" icon={WarningCircle} title={data.tier === 'very_low' ? t('home.urgent.veryLow', 'Very low glucose alert') : t('home.urgent.low', 'Low glucose alert')} onClick={() => go('J1')}>
      {t('home.urgent.body', 'Your glucose looks low: {{value}} mmol/L{{demo}}. Tap to see what to do.', { value: data.value?.toFixed(1) ?? '', demo: data.demo ? t('home.urgent.demo', ' (demo)') : '' })}
    </Alert>
  )
}

/** The first open clash alert, with its fixed sentence (never reworded here), and a count of any others. */
function ClashStrip({ alerts }: { alerts: ClashAlert[] }) {
  const { t } = useTranslation()
  const go = useGo()
  const first = alerts[0]
  if (!first) return null
  const more = alerts.length - 1
  return (
    <Alert tone="warn" title={t('home.clash.title', 'Medicines may clash. Check with your doctor.')} onClick={() => go('B2')}>
      <span className="block">{first.text}</span>
      {more > 0 && <span className="mt-1 block font-bold text-ink2">{t('home.clash.more', '{{n}} more to review.', { n: more })}</span>}
    </Alert>
  )
}

/**
 * The medicine running lowest (7 days or fewer, from GET /medications/stock). Only real stock counts: nothing is shown when stock
 * is not set up yet (ready is false) or when a medicine has no count or no days figure.
 */
function LowStockStrip({ items }: { items: MedicineStock[] }) {
  const { t } = useTranslation()
  const go = useGo()
  const low = items
    .filter((i) => (i.status === 'low' || i.status === 'out') && i.daysLeft != null)
    .sort((a, b) => (a.daysLeft ?? 0) - (b.daysLeft ?? 0))
  const first = low[0]
  if (!first) return null
  const more = low.length - 1
  const line =
    first.status === 'out'
      ? t('home.stock.out', '{{name}} may have run out. Check your stock.', { name: first.name })
      : first.daysLeft === 1
        ? t('home.stock.lowOne', '{{name}} is running low: about 1 day left', { name: first.name })
        : t('home.stock.low', '{{name}} is running low: about {{n}} days left', { name: first.name, n: first.daysLeft })
  return (
    <Alert tone="info" title={t('home.stock.title', 'Medicine stock')} onClick={() => go('H1')}>
      <span className="block">{line}</span>
      {more > 0 && <span className="mt-1 block font-bold text-ink2">{t('home.stock.more', '{{n}} more running low.', { n: more })}</span>}
    </Alert>
  )
}

export function AlertStrip({ clashAlerts }: { clashAlerts: ClashAlert[] }) {
  const { t } = useTranslation()
  const { data } = useUrgentState()
  const { data: stock } = useStock()
  const urgent = !!data && (data.status === 'active' || data.status === 'escalated')
  const lowItems = stock?.ready ? stock.items : []
  const lowAny = lowItems.some((i) => (i.status === 'low' || i.status === 'out') && i.daysLeft != null)
  if (!urgent && clashAlerts.length === 0 && !lowAny) return null
  return (
    <section aria-label={t('home.alerts.label', 'Alerts')} className="flex flex-col gap-3">
      <UrgentBanner />
      <ClashStrip alerts={clashAlerts} />
      <LowStockStrip items={lowItems} />
    </section>
  )
}
