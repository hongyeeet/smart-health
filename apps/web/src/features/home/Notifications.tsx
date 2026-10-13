/**
 * B2 — Notifications and alerts.
 *
 * Two kinds of item, following Damien's alert design: medicine-interaction alerts (from the clash check, GET /interactions)
 * at the top, then reminders (GET /notifications/history), grouped by day, newest day first. Nothing is ever cleared from this page:
 * opening a reminder marks it seen (the dot goes) and goes to the matching log, even when it is done or from an earlier day. Refill and dose reminders
 * belong to the Medicines group with the interaction alerts.
 * The design's care-team notes and pharmacy pick-up cards are not here: Smart Health has no care-team or pharmacy link.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useClash, useNoticeHistory, useOpenNotice } from '@/data/hooks'
import type { Notice } from '@/data/types'
import { sgToday } from '@/features/me/progress/calendarMath'
import { shortDate } from '@/lib/format'
import { useGo } from '@/app/navigation'
import { cn } from '@/lib/cn'
import { Header, Screen } from '@/ui/layout'
import { Alert, Chip, EmptyState, Skeleton, TextLink } from '@/ui/primitives'
import { Bell, CaretRight, CheckCircle, ClipboardText, ListChecks, ShieldCheck } from '@/ui/icons'
import { InteractionCard } from '@/features/alerts/InteractionCard'
import { useDismissed } from '@/features/alerts/pieces'

type Filter = 'all' | 'medicines' | 'reminders'

/** Refill and dose reminders are about medicines, so they sit with the interaction alerts in the Medicines group. */
const MEDICINE_KINDS: Notice['kind'][] = ['refill', 'dose', 'dose_reminder', 'dose_renudge']

const dayBefore = (iso: string) => {
  const d = new Date(iso + 'T00:00:00Z')
  d.setUTCDate(d.getUTCDate() - 1)
  return d.toISOString().slice(0, 10)
}

export function Notifications() {
  const { t } = useTranslation()
  const { data, isError } = useNoticeHistory()
  const clash = useClash()
  const open = useOpenNotice()
  const go = useGo()
  const dismissedIds = useDismissed((s) => s.ids)
  const restore = useDismissed((s) => s.restore)
  const [filter, setFilter] = useState<Filter>('all')

  const allAlerts = clash.data?.alerts ?? []
  const alerts = allAlerts.filter((a) => !dismissedIds.includes(a.id))
  const setAside = allAlerts.filter((a) => dismissedIds.includes(a.id))
  const all = data ?? []
  const medicineNotices = all.filter((n) => MEDICINE_KINDS.includes(n.kind))
  const otherNotices = all.filter((n) => !MEDICINE_KINDS.includes(n.kind))
  const notices = filter === 'medicines' ? medicineNotices : filter === 'reminders' ? otherNotices : all
  const unread = all.filter((n) => n.unread)
  const loading = !data && !isError && clash.isLoading
  const showAlerts = filter !== 'reminders'
  const showNotices = filter !== 'medicines' || medicineNotices.length > 0
  const nothing = !loading && (showAlerts ? alerts.length : 0) + notices.length === 0

  const today = sgToday()
  const dayLabel = (iso: string) => {
    const date = shortDate(iso)
    if (iso === today) return t('alerts.day.today', 'Today, {{date}}', { date })
    if (iso === dayBefore(today)) return t('alerts.day.yesterday', 'Yesterday, {{date}}', { date })
    return date
  }
  const days: { date: string; items: Notice[] }[] = []
  for (const n of notices) {
    const date = n.date ?? today
    const last = days[days.length - 1]
    if (last && last.date === date) last.items.push(n)
    else days.push({ date, items: [n] })
  }

  const chips: { value: Filter; label: string }[] = [
    { value: 'all', label: t('alerts.filter.all', 'All ({{n}})', { n: alerts.length + all.length }) },
    { value: 'medicines', label: t('alerts.filter.medicines', 'Medicines ({{n}})', { n: alerts.length + medicineNotices.length }) },
    { value: 'reminders', label: t('alerts.filter.reminders', 'Reminders ({{n}})', { n: otherNotices.length }) },
  ]

  return (
    <Screen narrow>
      <Header
        title={t('alerts.title', 'Notifications and alerts')}
        back
        backTo="B1"
        sub={t('alerts.sub', 'Alerts about your medicines, and gentle nudges to keep your log complete.')}
        trailing={
          unread.length > 0 ? (
            <button type="button" aria-label={t('alerts.markRead', 'Mark all reminders as read')} onClick={() => unread.forEach((n) => open.mutate(n.id))} className="press flex h-12 w-12 items-center justify-center rounded-full text-brand hover:bg-well">
              <ListChecks size={24} aria-hidden />
            </button>
          ) : undefined
        }
      />

      <div className="flex flex-wrap gap-2" role="group" aria-label={t('alerts.filter.label', 'Show')}>
        {chips.map((c) => (
          <Chip key={c.value} on={filter === c.value} onClick={() => setFilter(c.value)}>
            {c.label}
          </Chip>
        ))}
      </div>

      {isError && showNotices && <Alert tone="warn">{t('alerts.remindersError', 'We could not load your reminders.')}</Alert>}
      {clash.isError && showAlerts && <Alert tone="warn">{t('alerts.clashError', 'We could not load your medicine alerts. This is not the same as all clear.')}</Alert>}
      {loading && <Skeleton className="h-48" />}

      {showAlerts &&
        setAside.map((a) => (
          <div key={a.id} className="flex flex-wrap items-center justify-between gap-x-3 rounded-card border border-line bg-well px-4 py-1.5">
            <p className="flex min-w-0 items-center gap-2 text-sub text-ink2">
              <ClipboardText size={18} className="flex-none" aria-hidden />
              <span className="break-words">{t('alerts.setAside', '{{a}} and {{b}}: set aside, on your doctor questions', { a: a.medA, b: a.medB })}</span>
            </p>
            <TextLink onClick={() => restore(a.id)}>{t('alerts.restore', 'Restore')}</TextLink>
          </div>
        ))}

      {showAlerts && clash.data?.checking && <p className="px-1 text-sub text-ink3">{t('alerts.checking', 'Checking your medicines for clashes…')}</p>}
      {showAlerts && clash.data && !clash.data.checking && clash.data.checkIncomplete && (
        <Alert tone="info">{t('alerts.incomplete', 'The latest check of your medicines could not finish, so there may be more to see later. This is not the same as all clear.')}</Alert>
      )}

      {showAlerts && alerts.map((a) => <InteractionCard key={a.id} alert={a} />)}

      {showNotices &&
        days.map((day) => (
          <section key={day.date} className="flex flex-col gap-2">
            <h2 className="px-1 text-sub font-bold text-ink2">{dayLabel(day.date)}</h2>
            <ul className="divide-y divide-line rounded-card border border-line bg-card px-4">
              {day.items.map((n) => (
                <li key={n.id}>
                  <button
                    type="button"
                    onClick={() => {
                      if (n.unread) open.mutate(n.id)
                      if (n.to) go(n.to)
                    }}
                    className="press flex w-full items-start gap-3 py-3.5 text-left"
                  >
                    <span className={cn('mt-0.5 flex h-11 w-11 flex-none items-center justify-center rounded-full', n.unread ? 'bg-brass-soft text-brass' : 'bg-well text-ink2')}>
                      <Bell size={22} aria-hidden />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className={cn('block text-body leading-snug', n.unread ? 'font-bold' : '')}>{n.title}</span>
                      <span className="block text-sub text-ink2">{n.body}</span>
                      <span className="block pt-0.5 text-sub text-ink3">{n.when}</span>
                    </span>
                    {n.unread && <span className="mt-2 h-2.5 w-2.5 flex-none rounded-full bg-brass" aria-label={t('alerts.new', 'New')} />}
                    {n.to && <CaretRight size={18} className="mt-2 flex-none text-ink3" aria-hidden />}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))}

      {nothing && !isError && !clash.isError && <EmptyState icon={CheckCircle}>{t('alerts.empty', 'Nothing here right now. New alerts and reminders appear here.')}</EmptyState>}

      <p className="flex items-start justify-center gap-2 rounded-card bg-well p-4 text-center text-sub text-ink2">
        <ShieldCheck size={18} className="mt-0.5 flex-none" aria-hidden />
        {t('alerts.footer', 'Medicine alerts come from drug-label rules and an AI web search of your saved medicines. They are not medical advice. No alert does not mean a combination was checked and cleared.')}
      </p>
    </Screen>
  )
}
