/**
 * Shared pieces of the medicine-interaction alert (prd F5), used by the card on the alerts page (B2) and the details
 * page (H5). The layout follows Damien's alert design (Stitch export, 2026-10-09).
 *
 * Wording rules that hold everywhere here: the alert says two medicines "may" interact and who to ask. It never says to
 * stop, skip or change a medicine, and it never says a combination is safe (rules.md 1.1, 1.7; docs/specs/f5-clash.md).
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { useTranslation } from 'react-i18next'
import type { ClashAlert } from '@/data/types'
import { Info, Pill, Warning } from '@/ui/icons'

/**
 * Alerts the person has set aside "for now" on this device. The alert itself stays open on the server (and in the box on
 * the Medications page) until they say they have checked with their doctor; this only tidies the alerts page.
 */
interface DismissedState {
  ids: string[]
  dismiss: (id: string) => void
  restore: (id: string) => void
}
export const useDismissed = create<DismissedState>()(
  persist(
    (set) => ({
      ids: [],
      dismiss: (id) => set((s) => ({ ids: s.ids.includes(id) ? s.ids : [...s.ids, id] })),
      restore: (id) => set((s) => ({ ids: s.ids.filter((x) => x !== id) })),
    }),
    { name: 'smart-health-alerts-dismissed' },
  ),
)

/** "Today, 10:24 am", "Yesterday, 3:15 pm" or "7 Oct, 9:00 am". Empty when the server sent no time. */
export function whenRaised(iso: string | null | undefined, today: string, yesterday: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const time = d.toLocaleTimeString('en-SG', { hour: 'numeric', minute: '2-digit', hour12: true }).toLowerCase()
  const day = (x: Date) => x.toLocaleDateString('sv-SE')
  const now = new Date()
  const y = new Date(now)
  y.setDate(now.getDate() - 1)
  const label = day(d) === day(now) ? today : day(d) === day(y) ? yesterday : d.toLocaleDateString('en-SG', { day: 'numeric', month: 'short' })
  return `${label}, ${time}`
}

/** The two medicines, one above the other, joined by a "possible interaction" marker. */
export function MedPair({ alert }: { alert: ClashAlert }) {
  const { t } = useTranslation()
  const row = (name: string) => (
    <div className="flex items-center gap-2.5">
      <span className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
        <Pill size={20} aria-hidden />
      </span>
      <span className="min-w-0 break-words text-body font-bold text-ink">{name}</span>
    </div>
  )
  return (
    <div className="flex flex-col gap-2 rounded-field border border-line bg-well p-3">
      {row(alert.medA)}
      <div className="flex items-center gap-2 pl-[18px]">
        <span className="h-5 w-0.5 flex-none bg-warn" aria-hidden />
        <span className="inline-flex items-center gap-1.5 rounded-chip border border-line bg-card px-2.5 py-1 text-sub font-bold text-warn">
          <Warning size={16} weight="bold" aria-hidden />
          {t('alerts.pair.marker', 'Possible interaction')}
        </span>
      </div>
      {row(alert.medB)}
    </div>
  )
}

/**
 * The reassurance note under every alert. It says what the alert is not, and who can advise. It deliberately does not
 * tell the person what to do with their medicines: "do not stop your medicine" is still advice (docs/specs/design.md 9).
 */
export function NotAdviceNote() {
  const { t } = useTranslation()
  return (
    <div className="flex items-start gap-2.5 rounded-field bg-info-soft p-3">
      <Info size={20} className="mt-0.5 flex-none text-info" aria-hidden />
      <p className="text-sub text-ink">{t('alerts.note', 'This alert is not a diagnosis. Your pharmacist or doctor can review your medicines.')}</p>
    </div>
  )
}

/** Where a flag came from, in words. Shown as a tag, never as a severity: the sources are not clinically reviewed. */
export function originLabel(origin: ClashAlert['origin'], t: (k: string, d: string) => string): string {
  if (origin === 'database') return t('alerts.origin.database', 'Drug-label rules')
  if (origin === 'ai') return t('alerts.origin.ai', 'AI web search')
  return t('alerts.origin.both', 'Drug-label rules and AI web search')
}
