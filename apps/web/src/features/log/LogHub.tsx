/**
 * E1 — Log hub.
 *
 * A banner that changes with what is true now (the next meal, a symptom to update, a log that is due, all done), then one tile per log kind:
 * a large Meal tile and four smaller ones, each with where today stands and the last entry. On a laptop the right column shows today as a
 * timeline, what is still to log, and the last entries (tap Edit to change or delete one). The meal ideas menu is the strip under the tiles.
 */
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { useLogProgress, useMenu, useRecent } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import type { MenuItem, ProgressItem, RecentEntry } from '@/data/types'
import type { RouteId } from '@/app/routeIds'
import { appConfig } from '@/config/app'
import { Header, Screen, Reveal } from '@/ui/layout'
import { Button, Card, TextLink } from '@/ui/primitives'
import { cn } from '@/lib/cn'
import { UserSwitch } from '@/features/home/UserSwitch'
import { Camera, CaretRight, ForkKnife, Heartbeat, PersonSimpleWalk, Smiley, Thermometer, type IconType } from '@/ui/icons'
import { HubBanner } from './hub/HubBanner'
import { mealNow } from './MealMenu'

/** The little status pill on a tile: Done, N of M, Good time, or nothing. */
function chip(i: ProgressItem | undefined, t: TFunction, extra?: { done: boolean; label: string }) {
  if (extra) {
    return (
      <span className={cn('whitespace-nowrap rounded-chip px-2.5 py-0.5 text-micro font-bold', extra.done ? 'bg-ok-soft text-ok' : 'bg-brass-soft text-brass')}>
        {extra.label}
      </span>
    )
  }
  if (!i) return null
  if (i.status === 'done')
    return (
      <span className="whitespace-nowrap rounded-chip bg-ok-soft px-2.5 py-0.5 text-micro font-bold text-ok">
        {i.target != null && i.target > 1
          ? t('log.hub.ofTarget', '{{count}} of {{target}}', { count: Math.min(i.count, i.target), target: i.target })
          : t('log.hub.done', 'Done')}
      </span>
    )
  if (i.status === 'due')
    return (
      <span className="whitespace-nowrap rounded-chip bg-brand-soft px-2.5 py-0.5 text-micro font-bold text-brand">
        {t('log.hub.goodTimeShort', 'Good time')}
      </span>
    )
  if (i.key === 'meals' && i.count > 0)
    return (
      <span className="whitespace-nowrap rounded-chip bg-well px-2.5 py-0.5 text-micro font-bold text-ink2">
        {t('log.hub.ofTarget', '{{count}} of {{target}}', { count: i.count, target: i.target })}
      </span>
    )
  return <span className="whitespace-nowrap rounded-chip bg-well px-2.5 py-0.5 text-micro font-bold text-ink2">{t('log.hub.notYet', 'Not yet')}</span>
}

const isoDay = (d: Date) => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Singapore' }).format(d)
const KIND_ICON: Record<RecentEntry['kind'], IconType> = {
  meal: ForkKnife,
  workout: PersonSimpleWalk,
  symptom: Thermometer,
  checkin: Smiley,
  blood_pressure: Heartbeat,
}

/** "Last: Walking, 30 min, Sat 10 Oct" for one kind of log, from the recent entries. */
function lastLine(recent: RecentEntry[] | undefined, kind: RecentEntry['kind'], t: TFunction): string {
  const e = recent?.find((x) => x.kind === kind)
  return e ? t('log.hub.last', 'Last: {{what}}, {{when}}', { what: e.title.toLowerCase(), when: e.when }) : t('log.hub.noneYet', 'Nothing logged yet')
}

function SmallTile({
  id,
  icon: Icon,
  title,
  sub,
  pill,
  last,
}: {
  id: RouteId
  icon: IconType
  title: string
  sub: string
  pill: React.ReactNode
  last: string
}) {
  const { t } = useTranslation()
  const go = useGo()
  return (
    <Card onClick={() => go(id)} className="flex min-h-[10.5rem] flex-col justify-between gap-2 !p-4">
      <div className="flex items-start justify-between gap-2">
        <span className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
          <Icon size={24} aria-hidden />
        </span>
        {pill}
      </div>
      <div className="min-w-0">
        <p className="text-body font-bold leading-tight">{title}</p>
        <p className="text-sub text-ink2">{sub}</p>
      </div>
      <p className="flex items-center justify-between gap-2 border-t border-line pt-2 text-micro text-ink2">
        <span className="min-w-0 truncate">{last}</span>
        <span className="flex-none font-bold text-brand">{t('log.hub.add', 'Add')} ›</span>
      </p>
    </Card>
  )
}

function MealTile({ progress, recent }: { progress: ProgressItem | undefined; recent: RecentEntry[] | undefined }) {
  const { t } = useTranslation()
  const go = useGo()
  const sub =
    progress?.status === 'due' && progress.window
      ? t('log.hub.usually', 'Usually {{window}}', { window: progress.window })
      : t('log.hub.mealBig', 'One photo is enough. We read it and estimate the nutrients.')
  return (
    <div className="col-span-2 flex flex-col gap-4 rounded-card border border-brand bg-brand p-5 text-on-brand shadow-lift sm:flex-row sm:items-center sm:justify-between sm:p-6">
      <div className="flex min-w-0 flex-1 items-center gap-4">
        <span className="flex h-14 w-14 flex-none items-center justify-center rounded-full bg-on-brand/15">
          <ForkKnife size={30} aria-hidden />
        </span>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-serif text-h1 font-medium leading-tight">{t('log.hub.meal', 'Meal')}</p>
            {progress && (
              <span className="whitespace-nowrap rounded-chip bg-on-brand px-3 py-0.5 text-micro font-bold text-brand">
                {progress.status === 'due'
                  ? t('log.hub.goodTimeShort', 'Good time')
                  : progress.count > 0
                    ? t('log.hub.ofTarget', '{{count}} of {{target}}', { count: progress.count, target: progress.target })
                    : t('log.hub.notYet', 'Not yet')}
              </span>
            )}
          </div>
          <p className="mt-0.5 text-body opacity-90">{sub}</p>
          <p className="mt-1 text-micro opacity-75">{lastLine(recent, 'meal', t)}</p>
        </div>
      </div>
      <div className="flex flex-none flex-wrap gap-2.5 sm:flex-col sm:items-stretch">
        <button
          type="button"
          onClick={() => go('E2')}
          className="press flex min-h-11 items-center justify-center gap-2 whitespace-nowrap rounded-field bg-on-brand px-4 text-btn-sm font-bold text-brand"
        >
          <Camera size={20} aria-hidden />
          {t('log.hub.takePhoto', 'Take a photo')}
        </button>
        <button
          type="button"
          onClick={() => go('E9')}
          className="press flex min-h-11 items-center justify-center whitespace-nowrap rounded-field border-[1.5px] border-on-brand/50 px-4 text-btn-sm font-bold"
        >
          {t('log.hub.pickMenu', 'Pick from the menu')}
        </button>
      </div>
    </div>
  )
}

/** The right column: today as a timeline, what is still to log, and the last three entries with Edit. */
function SidePanels({ recent, items, bpDone }: { recent: RecentEntry[] | undefined; items: ProgressItem[]; bpDone: boolean }) {
  const { t } = useTranslation()
  const go = useGo()
  const today = isoDay(new Date())
  const todays = (recent ?? [])
    .filter((e) => e.date === today)
    .slice(0, 6)
    .reverse()
  const todo: { label: string; to: RouteId }[] = [
    ...items
      .filter((i) => !i.done)
      .map((i) => ({
        label:
          i.key === 'meals'
            ? t('log.hub.meal', 'Meal')
            : i.key === 'workout'
              ? t('log.hub.workout', 'Workout')
              : i.key === 'symptom'
                ? t('log.hub.symptom', 'Symptom')
                : t('log.hub.checkin', 'Mood and sleep'),
        to: i.to,
      })),
    ...(bpDone ? [] : [{ label: t('log.hub.bp', 'Blood pressure'), to: 'E3' as RouteId }]),
  ].filter((x) => x.label)
  const lastThree = (recent ?? []).slice(0, 3)
  return (
    <aside className="flex flex-col gap-4">
      <Card className="flex flex-col gap-3">
        <div className="flex items-baseline justify-between">
          <h2 className="text-body font-bold">{t('log.hub.todaySoFar', 'Today so far')}</h2>
          <span className="text-sub text-ink3">{t('log.hub.entries', '{{n}} entries', { n: todays.length })}</span>
        </div>
        {todays.length === 0 && <p className="text-sub text-ink2">{t('log.hub.todayEmpty', 'Nothing logged yet today.')}</p>}
        <ol className="flex flex-col">
          {todays.map((e, i) => {
            const Icon = KIND_ICON[e.kind]
            return (
              <li key={e.id} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <span className="flex h-8 w-8 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
                    <Icon size={16} aria-hidden />
                  </span>
                  {i < todays.length - 1 && <span className="my-0.5 w-0.5 flex-1 bg-line" />}
                </div>
                <div className={cn('min-w-0 flex-1', i < todays.length - 1 && 'pb-3')}>
                  <div className="flex items-baseline justify-between gap-2">
                    <p className="min-w-0 break-words text-sub font-bold leading-tight">{e.title}</p>
                    <span className="num flex-none text-micro text-ink3">{e.when}</span>
                  </div>
                  <p className="text-micro text-ink2">{e.detail}</p>
                </div>
              </li>
            )
          })}
        </ol>
      </Card>
      {todo.length > 0 && (
        <Card className="flex flex-col gap-2.5">
          <h2 className="text-body font-bold">{t('log.hub.stillToLog', 'Still to log')}</h2>
          <div className="flex flex-wrap gap-2">
            {todo.map((x) => (
              <button
                key={x.label}
                type="button"
                onClick={() => go(x.to)}
                className="press min-h-9 whitespace-nowrap rounded-chip bg-brass-soft px-3.5 text-sub font-bold text-brass"
              >
                {x.label}
              </button>
            ))}
          </div>
          <p className="text-micro text-ink3">{t('log.hub.notOverdue', 'Nothing is overdue. These are the ones you usually log around now.')}</p>
        </Card>
      )}
      {lastThree.length > 0 && (
        <Card className="flex flex-col gap-1">
          <div className="flex items-baseline justify-between">
            <h2 className="text-body font-bold">{t('log.hub.recent', 'Recent entries')}</h2>
            <TextLink onClick={() => go('C3')}>{t('log.hub.seeAll', 'See all')}</TextLink>
          </div>
          {lastThree.map((e) => (
            <div key={e.id} className="flex items-center gap-3 border-t border-line py-2 first:border-t-0">
              <div className="min-w-0 flex-1">
                <p className="break-words text-sub font-bold leading-tight">{e.title}</p>
                <p className="text-micro text-ink2">{[e.when, e.detail].filter(Boolean).join(' · ')}</p>
              </div>
              <Button size="md" variant="secondary" className="!w-auto flex-none" onClick={() => go('E7', { sheet: { entry: e } })}>
                {t('log.hub.edit', 'Edit')}
              </Button>
            </div>
          ))}
        </Card>
      )}
    </aside>
  )
}

/** The menu strip: three dish pictures, the title and a chevron. */
function MenuStrip() {
  const { t } = useTranslation()
  const go = useGo()
  const { data } = useMenu(mealNow())
  const dishes: MenuItem[] = (data?.sections.flatMap((s) => s.items) ?? []).filter((i) => i.image.url).slice(0, 3)
  return (
    <Card onClick={() => go('E9')} className="flex items-center gap-4 !p-4">
      {dishes.length > 0 ? (
        <div className="hidden flex-none gap-1.5 sm:flex">
          {dishes.map((d) => (
            <img key={d.key} src={`${appConfig.apiBaseUrl}${d.image.url}`} alt="" className="h-[3.9rem] w-[5.25rem] rounded-[12px] object-cover" />
          ))}
        </div>
      ) : (
        <span className="flex h-12 w-12 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
          <ForkKnife size={24} aria-hidden />
        </span>
      )}
      <span className="min-w-0 flex-1">
        <span className="block text-body font-bold">{t('log.hub.menu', 'Meal suggestions')}</span>
        <span className="block text-sub text-ink2">{t('log.hub.menuSub', 'A menu of ideas for your next meal, with pictures and the glucose rise.')}</span>
      </span>
      <CaretRight size={20} className="flex-none text-ink3" aria-hidden />
    </Card>
  )
}

export function LogHub() {
  const { t } = useTranslation()
  const go = useGo()
  const { data: progress } = useLogProgress()
  const { data: recent } = useRecent()
  const item = (key: ProgressItem['key']) => progress?.items.find((i) => i.key === key)
  const bpCount = progress?.bloodPressure.count ?? 0
  return (
    <Screen tabs wide>
      <Header title={t('log.hub.title', 'Log')} sub={t('log.hub.sub', 'Add what happened. It all lands on one timeline.')} trailing={<UserSwitch />} />
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_332px] [&>*]:min-w-0">
        <div className="flex flex-col gap-4">
          <HubBanner />
          <Reveal id="log-tiles" className="flex flex-col gap-2.5">
            <div className="flex items-baseline justify-between">
              <h2 className="text-h2 font-bold">{t('log.hub.addToDay', 'Add to your day')}</h2>
              {progress && (
                <span className="text-sub text-ink3">
                  {t('log.hub.doneToday', '{{done}} of {{total}} done today', { done: progress.done, total: progress.total })}
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3.5">
              <MealTile progress={item('meals')} recent={recent} />
              <SmallTile
                id="F1"
                icon={PersonSimpleWalk}
                title={t('log.hub.workout', 'Workout')}
                sub={t('log.hub.workoutSub', 'Walk, strength, yoga')}
                pill={chip(item('workout'), t)}
                last={lastLine(recent, 'workout', t)}
              />
              <SmallTile
                id="E4"
                icon={Thermometer}
                title={t('log.hub.symptom', 'Symptom')}
                sub={t('log.hub.symptomSub', 'How you feel')}
                pill={chip(undefined, t, { done: false, label: t('log.hub.noneToday', 'None today') })}
                last={lastLine(recent, 'symptom', t)}
              />
              <SmallTile
                id="E3"
                icon={Heartbeat}
                title={t('log.hub.bp', 'Blood pressure')}
                sub={progress?.bloodPressure.latest ?? t('log.hub.bpSub', 'Top and bottom numbers')}
                pill={chip(undefined, t, { done: bpCount > 0, label: bpCount > 0 ? t('log.hub.done', 'Done') : t('log.hub.notYet', 'Not yet') })}
                last={lastLine(recent, 'blood_pressure', t)}
              />
              <SmallTile
                id="E5"
                icon={Smiley}
                title={t('log.hub.checkin', 'Mood and sleep')}
                sub={t('log.hub.checkinSub', 'Thirty seconds')}
                pill={chip(item('checkin'), t)}
                last={lastLine(recent, 'checkin', t)}
              />
            </div>
          </Reveal>
          <MenuStrip />
          <p className="px-1 text-sub text-ink2">
            {t('log.hub.seeFoodLead', 'Your recent entries and what you ate are in Insights.')}{' '}
            <TextLink onClick={() => go('C3')}>{t('log.hub.seeFood', 'See what you ate in Insights → Food')}</TextLink>
            {' · '}
            <TextLink onClick={() => go('K11')}>{t('log.hub.suggestions', 'Rate the meal ideas')}</TextLink>
          </p>
        </div>
        <SidePanels recent={recent} items={progress?.items ?? []} bpDone={bpCount > 0} />
      </div>
    </Screen>
  )
}
