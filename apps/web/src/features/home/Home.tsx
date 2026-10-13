/**
 * B1 — Home: what to do now, in order of importance.
 *
 * At most five blocks show at once, top to bottom (the order is the point: the most urgent thing is always first):
 *   1. the alert strip: the active low-glucose alert, then open medicine clash alerts
 *   2. one banner: an unfinished meal, or else the food banner (a meal due and not logged, or a food habit high in salt or sugar)
 *   3. the dose card: what to take now, or the next dose (a first-time person sees "Start here" instead)
 *   4. today's logging ring with the single next thing to log
 *   5. one "for you" card: to-confirm ideas, then a lunch idea, then a food habit worth a look (the first with content)
 * Everything else sits behind "See more" (collapsed by default, remembered on this device): this week's bars, the full list of
 * what to log today, and any other "for you" cards. Each block still decides for itself whether it has something to say.
 * Everything comes from the database; the bell opens the reminders (B2).
 */
import { dateLocale } from '@/lib/locale'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { useClash, useDoses, useLogProgress, useNotices, useRecent } from '@/data/hooks'
import { useDismissed } from '@/features/alerts/pieces'
import { useMealSession } from '@/features/log/useMealSession'
import { useGo } from '@/app/navigation'
import { MealBanner } from '@/features/log/MealBanner'
import { useUi } from '@/state/store'
import { cn } from '@/lib/cn'
import { Header, Screen } from '@/ui/layout'
import { Alert, Skeleton } from '@/ui/primitives'
import { Bell } from '@/ui/icons'
import { DoseCard } from './DoseCard'
import { UserSwitch } from './UserSwitch'
import { AlertStrip } from './AlertStrip'
import { FoodBanner, useFoodBanner } from './FoodBanner'
import { TodayCard, TodayCardSkeleton } from './TodayCard'
import { useForYou } from './ForYou'
import { ProgressDetails } from './ProgressDetails'
import { SeeMoreButton, useSeeMore } from './SeeMore'
import { StartHere } from './StartHere'
import { useSimulate } from '@/features/urgent/api'

function greeting(h: number, t: TFunction) {
  return h < 12 ? t('home.greeting.morning', 'Good morning') : h < 18 ? t('home.greeting.afternoon', 'Good afternoon') : t('home.greeting.evening', 'Good evening')
}

export function Home() {
  const { t } = useTranslation()
  const go = useGo()
  const { data, isError, refetch } = useLogProgress()
  const { data: notices } = useNotices()
  const { data: clash } = useClash()
  const { data: doses } = useDoses()
  const { data: recent } = useRecent()
  const { data: food } = useFoodBanner()
  const forYou = useForYou()
  const { meal } = useMealSession()
  const setAside = useDismissed((s) => s.ids)
  const userKey = useUi((s) => s.userKey)
  const [moreOpen, toggleMore] = useSeeMore()

  /** medicine alerts the person has not set aside */
  const openAlerts = (clash?.alerts ?? []).filter((a) => !setAside.includes(a.id))
  /** unread reminders plus open medicine alerts */
  const unread = (notices?.filter((n) => n.unread).length ?? 0) + openAlerts.length
  const now = new Date()
  const dateLabel = now.toLocaleDateString(dateLocale('en-SG'), { weekday: 'long', day: 'numeric', month: 'long' })
  /** nothing logged yet and no medicines: show "Start here" instead of an empty page */
  const firstTime = !!data && !!doses && !!recent && data.done === 0 && !doses.hasMedicines && recent.length === 0

  return (
    <Screen tabs>
      <Header
        title={greeting(now.getHours(), t)}
        sub={dateLabel}
        trailing={
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => go('B2')} aria-label={t('home.bell', 'Notifications and alerts, {{n}} new', { n: unread })} className="press relative flex h-12 w-12 items-center justify-center rounded-full border border-line bg-card">
              <Bell size={24} aria-hidden />
              {unread > 0 && <span className="absolute right-2.5 top-2.5 h-2.5 w-2.5 rounded-full bg-brass ring-2 ring-card" />}
            </button>
            <UserSwitch />
          </div>
        }
      />

      {/* 1. alerts */}
      <AlertStrip clashAlerts={openAlerts} />

      {/* 2. one banner: an unfinished meal first, otherwise the food banner */}
      {meal ? <MealBanner /> : <FoodBanner banner={food} />}

      {/* 3. medicines */}
      {isError && (
        <Alert tone="warn" onClick={() => void refetch()}>
          {t('home.loadError', "We could not load today's logs. Tap to try again.")}
        </Alert>
      )}
      {/* 3 to 5: a phone and a tablet stack them in this order; a laptop puts the dose card beside today's logging and the "for you" card, the same height */}
      <div className="grid gap-4 lg:grid-cols-2 [&>*]:min-w-0">
        <div className="flex">{firstTime ? <StartHere /> : <DoseCard />}</div>
        <div className="flex flex-col gap-4">
          {data ? (
            <div className="flex flex-1">
              <TodayCard data={data} />
            </div>
          ) : isError ? null : (
            <TodayCardSkeleton />
          )}
          {forYou.cards[0] ?? (forYou.loading ? <Skeleton className="h-24" /> : null)}
        </div>
        <div className="lg:col-span-2">
          <SeeMoreButton open={moreOpen} onToggle={toggleMore} />
        </div>
        <section id="home-more" className={cn('gap-4 lg:col-span-2 lg:grid-cols-2 [&>*:last-child:nth-child(odd)]:lg:col-span-2', moreOpen ? 'grid' : 'hidden')}>
          {moreOpen && data && <ProgressDetails data={data} />}
          {moreOpen && forYou.cards.slice(1)}
        </section>
      </div>

      {userKey === 'demo' && <DemoLowLink />}
    </Screen>
  )
}

/** Demo only: the sample data stops on 2 Oct, so a real low reading cannot happen on stage. */
function DemoLowLink() {
  const { t } = useTranslation()
  const sim = useSimulate()
  const go = useGo()
  return (
    <p className="px-1 text-center text-micro text-ink3">
      {t('home.demo.label', 'Demo:')}{' '}
      <button type="button" disabled={sim.isPending} onClick={() => sim.mutate(3.4, { onSuccess: () => go('J1') })} className="press min-h-12 px-2 font-bold underline">
        {t('home.demo.simulate', 'Simulate a low reading')}
      </button>
    </p>
  )
}
