/**
 * B2 — Reminders.
 *
 * Reminders come from the server (GET /notifications) and are rule-based on what has been logged today, so a meal
 * reminder disappears once the meal is logged. Opening one records it as read and goes to the matching log.
 */
import { useNotices, useOpenNotice } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { cn } from '@/lib/cn'
import { Header, Screen } from '@/ui/layout'
import { Alert, EmptyState, Skeleton } from '@/ui/primitives'
import { Bell, CaretRight, CheckCircle } from '@/ui/icons'

export function Notifications() {
  const { data, isError } = useNotices()
  const open = useOpenNotice()
  const go = useGo()
  return (
    <Screen>
      <Header title="Reminders" back backTo="B1" sub="Gentle nudges to keep your log complete." />
      {isError && <Alert tone="warn">We could not load your reminders.</Alert>}
      {!data && !isError && <Skeleton className="h-48" />}
      {data && data.length === 0 && <EmptyState icon={CheckCircle}>You are all caught up. New reminders appear here when a log is due.</EmptyState>}
      {data && data.length > 0 && (
        <ul className="divide-y divide-line rounded-card border border-line bg-card px-4">
          {data.map((n) => (
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
                {n.unread && <span className="mt-2 h-2.5 w-2.5 flex-none rounded-full bg-brass" aria-label="New" />}
                {n.to && <CaretRight size={18} className="mt-2 flex-none text-ink3" aria-hidden />}
              </button>
            </li>
          ))}
        </ul>
      )}
    </Screen>
  )
}
