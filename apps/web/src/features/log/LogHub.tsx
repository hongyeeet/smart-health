/**
 * E1 — Log hub.
 *
 * One tile per log kind. Each tile shows where today stands (done, due now, or not yet) from the database, so the
 * person can see at a glance what is still worth logging. The recent entries are on Insights, Food (C3).
 */
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { useLogProgress } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { MealBanner } from './MealBanner'
import type { ProgressItem } from '@/data/types'
import type { RouteId } from '@/app/routeIds'
import { Header, Screen, Reveal } from '@/ui/layout'
import { Card, TextLink } from '@/ui/primitives'
import { cn } from '@/lib/cn'
import { UserSwitch } from '@/features/home/UserSwitch'
import { ForkKnife, Heartbeat, PersonSimpleWalk, Smiley, Thermometer, type IconType } from '@/ui/icons'

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

/** The fifth tile fills the last row on a phone and tablet; its text then sits beside the icon, so the row reads as a deliberate wide tile. */
const wide = (key: string) => key === 'checkin'

export function LogHub() {
  const { t } = useTranslation()
  const tiles: { id: RouteId; key: ProgressItem['key'] | 'blood_pressure'; title: string; sub: string; icon: IconType }[] = [
    { id: 'E2', key: 'meals', title: t('log.hub.meal', 'Meal'), sub: t('log.hub.mealSub', 'Photo of your food'), icon: ForkKnife },
    { id: 'F1', key: 'workout', title: t('log.hub.workout', 'Workout'), sub: t('log.hub.workoutSub', 'Walk, strength, yoga'), icon: PersonSimpleWalk },
    { id: 'E4', key: 'symptom', title: t('log.hub.symptom', 'Symptom'), sub: t('log.hub.symptomSub', 'How you feel'), icon: Thermometer },
    { id: 'E3', key: 'blood_pressure', title: t('log.hub.bp', 'Blood pressure'), sub: t('log.hub.bpSub', 'Top and bottom numbers'), icon: Heartbeat },
    { id: 'E5', key: 'checkin', title: t('log.hub.checkin', 'Mood and sleep'), sub: t('log.hub.checkinSub', 'Thirty seconds'), icon: Smiley },
  ]
  const go = useGo()
  const { data: progress } = useLogProgress()
  return (
    <Screen tabs>
      <Header title={t('log.hub.title', 'Log')} sub={t('log.hub.sub', 'Add what happened. It all lands on one timeline.')} trailing={<UserSwitch />} />
      <MealBanner />
      <Reveal id="log-tiles">
        {/* phone and tablet: two columns, and the fifth tile ("Mood and sleep") takes its own full row; a laptop shows one even row of five;
            at 200% text every tile is one column. Titles start at the top of each tile, so they line up when a subtitle wraps. */}
        <div className="grid grid-cols-2 items-stretch gap-3 lg:grid-cols-5 [[data-ts='2']_&]:grid-cols-1">
          {tiles.map((tile) => {
            const item = progress?.items.find((i) => i.key === tile.key)
            return (
            <Card key={tile.id} onClick={() => go(tile.id)} className={cn('relative flex min-h-[124px] flex-col items-start gap-3 lg:min-h-40', wide(tile.key) && "col-span-2 lg:col-span-1 max-lg:min-h-0 max-lg:flex-row max-lg:items-center max-lg:gap-4 [[data-ts='2']_&]:col-span-1 [[data-ts='2']_&]:min-h-[124px] [[data-ts='2']_&]:flex-col [[data-ts='2']_&]:items-start [[data-ts='2']_&]:gap-3")}>
              <span className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
                <tile.icon size={24} aria-hidden />
              </span>
              <span className="absolute right-4 top-4">{chip(item, t)}</span>
              <span className="flex min-w-0 flex-col">
                <span className="block text-body font-bold">{tile.title}</span>
                <span className="block text-sub text-ink2">{item?.status === 'due' && item.window ? t('log.hub.usually', 'Usually {{window}}', { window: item.window }) : tile.key === 'blood_pressure' && progress?.bloodPressure.latest ? progress.bloodPressure.latest : tile.sub}</span>
              </span>
            </Card>
            )
          })}
        </div>
      </Reveal>
      <div className="flex flex-col items-start">
        <p className="text-sub text-ink2">{t('log.hub.seeFoodLead', 'Your recent entries and what you ate are in Insights.')}</p>
        <TextLink onClick={() => go('C3')}>{t('log.hub.seeFood', 'See what you ate in Insights → Food')}</TextLink>
      </div>
    </Screen>
  )
}
