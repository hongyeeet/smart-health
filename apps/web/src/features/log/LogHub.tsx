/**
 * E1 — Log hub.
 *
 * One tile per log kind. Each tile shows where today stands (done, due now, or not yet) from the database, so the
 * person can see at a glance what is still worth logging. Tapping a recent entry opens the edit/delete sheet (E7).
 */
import { useLogProgress, useRecent } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { MealBanner } from './MealBanner'
import type { LogKind, ProgressItem } from '@/data/types'
import type { RouteId } from '@/app/routeIds'
import { cn } from '@/lib/cn'
import { Header, Screen, Reveal } from '@/ui/layout'
import { Card, EmptyState, SectionTitle, Skeleton } from '@/ui/primitives'
import { UserSwitch } from '@/features/home/UserSwitch'
import { Barbell, CaretRight, ForkKnife, PersonSimpleWalk, Smiley, Thermometer, type IconType } from '@/ui/icons'

const tiles: { id: RouteId; key: ProgressItem['key']; title: string; sub: string; icon: IconType }[] = [
  { id: 'E2', key: 'meals', title: 'Meal', sub: 'Photo of your food', icon: ForkKnife },
  { id: 'F1', key: 'workout', title: 'Workout', sub: 'Walk, strength, yoga', icon: PersonSimpleWalk },
  { id: 'E4', key: 'symptom', title: 'Symptom', sub: 'How you feel', icon: Thermometer },
  { id: 'E5', key: 'checkin', title: 'Mood and sleep', sub: 'Thirty seconds', icon: Smiley },
]

const kindIcon: Record<LogKind, IconType> = { meal: ForkKnife, workout: Barbell, symptom: Thermometer, checkin: Smiley }

function chip(i: ProgressItem | undefined) {
  if (!i) return null
  if (i.status === 'done') return <span className="rounded-chip bg-ok-soft px-2 py-0.5 text-micro font-bold text-ok">{i.target != null && i.target > 1 ? `${Math.min(i.count, i.target)} of ${i.target}` : 'Done'}</span>
  // inside its time window: a calm pine dot, never an amber warning or the words "due now". The tile's subtitle gives the
  // usual time, and screen readers hear "a good time to log".
  if (i.status === 'due')
    return (
      <span className="mt-1 flex h-3 w-3 flex-none items-center justify-center rounded-full bg-brand-soft ring-1 ring-brand/30" role="img" aria-label="A good time to log">
        <span className="h-1.5 w-1.5 rounded-full bg-brand" />
      </span>
    )
  if (i.key === 'meals' && i.count > 0) return <span className="rounded-chip bg-well px-2 py-0.5 text-micro font-bold text-ink2">{i.count} of {i.target}</span>
  return null
}

export function LogHub() {
  const go = useGo()
  const { data, isError } = useRecent()
  const { data: progress } = useLogProgress()
  return (
    <Screen tabs>
      <Header title="Log" sub="Add what happened. It all lands on one timeline." trailing={<UserSwitch />} />
      <MealBanner />
      <Reveal id="log-tiles">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 [[data-ts='2']_&]:grid-cols-1">
          {tiles.map((t) => {
            const item = progress?.items.find((i) => i.key === t.key)
            return (
            <Card key={t.id} onClick={() => go(t.id)} className="flex min-h-[124px] flex-col justify-between">
              <span className="flex items-start justify-between">
                <span className="flex h-11 w-11 items-center justify-center rounded-full bg-brand-soft text-brand">
                  <t.icon size={24} aria-hidden />
                </span>
                {chip(item)}
              </span>
              <span>
                <span className="block text-body font-bold">{t.title}</span>
                <span className="block text-sub text-ink2">{item?.status === 'due' && item.window ? `Usually ${item.window}` : t.sub}</span>
              </span>
            </Card>
            )
          })}
        </div>
      </Reveal>
      <section className="flex flex-col gap-1">
        <SectionTitle>Recent entries</SectionTitle>
        {isError ? (
          <p className="text-body text-ink2">We could not load your entries.</p>
        ) : !data ? (
          <Skeleton className="h-40" />
        ) : data.length === 0 ? (
          <EmptyState icon={ForkKnife}>Nothing logged yet. Start with a meal or a quick check-in.</EmptyState>
        ) : (
          <ul className="divide-y divide-line">
            {data.map((e) => {
              const Icon = kindIcon[e.kind]
              return (
                <li key={e.id}>
                  <button type="button" onClick={() => go('E7', { sheet: { entry: e } })} className="press flex w-full items-center gap-3 py-3 text-left">
                    <span className={cn('flex h-11 w-11 flex-none items-center justify-center rounded-full bg-well text-ink2')}>
                      <Icon size={22} aria-hidden />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-body font-bold leading-snug">{e.title}</span>
                      <span className="block text-sub text-ink2">{e.detail}</span>
                    </span>
                    <span className="flex-none text-sub text-ink3">{e.when}</span>
                    <CaretRight size={18} className="flex-none text-ink3" aria-hidden />
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </section>
    </Screen>
  )
}
