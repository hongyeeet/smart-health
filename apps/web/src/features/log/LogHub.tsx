/**
 * E1 — Log hub.
 *
 * One tile per log kind. Each tile shows where today stands (done, due now, or not yet) from the database, so the
 * person can see at a glance what is still worth logging. Tapping a recent entry opens the edit/delete sheet (E7).
 */
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
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

const kindIcon: Record<LogKind, IconType> = { meal: ForkKnife, workout: Barbell, symptom: Thermometer, checkin: Smiley }

function chip(i: ProgressItem | undefined, t: TFunction) {
  if (!i) return null
  if (i.status === 'done') return <span className="rounded-chip bg-ok-soft px-2 py-0.5 text-micro font-bold text-ok">{i.target != null && i.target > 1 ? t('log.hub.ofTarget', '{{count}} of {{target}}', { count: Math.min(i.count, i.target), target: i.target }) : t('log.hub.done', 'Done')}</span>
  // inside its time window: a calm pine dot, never an amber warning or the words "due now". The tile's subtitle gives the
  // usual time, and screen readers hear "a good time to log".
  if (i.status === 'due')
    return (
      <span className="mt-1 flex h-3 w-3 flex-none items-center justify-center rounded-full bg-brand-soft ring-1 ring-brand/30" role="img" aria-label={t('log.hub.goodTime', 'A good time to log')}>
        <span className="h-1.5 w-1.5 rounded-full bg-brand" />
      </span>
    )
  if (i.key === 'meals' && i.count > 0) return <span className="rounded-chip bg-well px-2 py-0.5 text-micro font-bold text-ink2">{t('log.hub.ofTarget', '{{count}} of {{target}}', { count: i.count, target: i.target })}</span>
  return null
}

export function LogHub() {
  const { t } = useTranslation()
  const tiles: { id: RouteId; key: ProgressItem['key']; title: string; sub: string; icon: IconType }[] = [
    { id: 'E2', key: 'meals', title: t('log.hub.meal', 'Meal'), sub: t('log.hub.mealSub', 'Photo of your food'), icon: ForkKnife },
    { id: 'F1', key: 'workout', title: t('log.hub.workout', 'Workout'), sub: t('log.hub.workoutSub', 'Walk, strength, yoga'), icon: PersonSimpleWalk },
    { id: 'E4', key: 'symptom', title: t('log.hub.symptom', 'Symptom'), sub: t('log.hub.symptomSub', 'How you feel'), icon: Thermometer },
    { id: 'E5', key: 'checkin', title: t('log.hub.checkin', 'Mood and sleep'), sub: t('log.hub.checkinSub', 'Thirty seconds'), icon: Smiley },
  ]
  const go = useGo()
  const { data, isError } = useRecent()
  const { data: progress } = useLogProgress()
  return (
    <Screen tabs>
      <Header title={t('log.hub.title', 'Log')} sub={t('log.hub.sub', 'Add what happened. It all lands on one timeline.')} trailing={<UserSwitch />} />
      <MealBanner />
      <Reveal id="log-tiles">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 [[data-ts='2']_&]:grid-cols-1">
          {tiles.map((tile) => {
            const item = progress?.items.find((i) => i.key === tile.key)
            return (
            <Card key={tile.id} onClick={() => go(tile.id)} className="flex min-h-[124px] flex-col justify-between">
              <span className="flex items-start justify-between">
                <span className="flex h-11 w-11 items-center justify-center rounded-full bg-brand-soft text-brand">
                  <tile.icon size={24} aria-hidden />
                </span>
                {chip(item, t)}
              </span>
              <span>
                <span className="block text-body font-bold">{tile.title}</span>
                <span className="block text-sub text-ink2">{item?.status === 'due' && item.window ? t('log.hub.usually', 'Usually {{window}}', { window: item.window }) : tile.sub}</span>
              </span>
            </Card>
            )
          })}
        </div>
      </Reveal>
      <section className="flex flex-col gap-1">
        <SectionTitle>{t('log.hub.recent', 'Recent entries')}</SectionTitle>
        {isError ? (
          <p className="text-body text-ink2">{t('log.hub.loadError', 'We could not load your entries.')}</p>
        ) : !data ? (
          <Skeleton className="h-40" />
        ) : data.length === 0 ? (
          <EmptyState icon={ForkKnife}>{t('log.hub.empty', 'Nothing logged yet. Start with a meal or a quick check-in.')}</EmptyState>
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
