import { useEffect } from 'react'
import { useMarkRead, useNotices } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import type { Notice } from '@/data/types'
import { Header, Screen } from '@/ui/layout'
import { Card, EmptyState, Skeleton } from '@/ui/primitives'
import { Bell, CalendarBlank, ChartLineUp, ClipboardText, Drop, FilePdf, Pill, Thermometer, type IconType } from '@/ui/icons'
import { cn } from '@/lib/cn'

const icon: Record<Notice['kind'], IconType> = { dose: Pill, checkin: Thermometer, nudge: ChartLineUp, brief: FilePdf, refill: ClipboardText, appointment: CalendarBlank }

export function Notifications() {
  const { data } = useNotices()
  const read = useMarkRead()
  const go = useGo()
  useEffect(() => {
    const t = setTimeout(() => read.mutate(), 1200)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return (
    <Screen>
      <Header title="Notifications" back />
      {!data ? (
        <Skeleton className="h-40" />
      ) : data.length === 0 ? (
        <EmptyState icon={Bell}>Nothing new. We will only message you when it helps.</EmptyState>
      ) : (
        <div className="flex flex-col gap-3">
          {data.map((n) => {
            const Icon = icon[n.kind]
            return (
              <Card key={n.id} onClick={n.to ? () => go(n.to!) : undefined} className="flex items-start gap-3">
                <span className={cn('mt-0.5 flex h-11 w-11 flex-none items-center justify-center rounded-full', n.unread ? 'bg-brand text-on-brand' : 'bg-well text-ink2')}>
                  <Icon size={22} aria-hidden />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-baseline justify-between gap-2">
                    <span className="text-body font-bold">{n.title}</span>
                    <span className="flex-none text-sub text-ink3">{n.when}</span>
                  </span>
                  <span className="block text-sub text-ink2">{n.body}</span>
                </span>
              </Card>
            )
          })}
          <p className="text-sub text-ink3">
            <Drop size={16} className="mr-1 inline" aria-hidden />
            Urgent readings never wait here. They open a full screen straight away.
          </p>
        </div>
      )}
    </Screen>
  )
}
