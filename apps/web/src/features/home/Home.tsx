/**
 * B1 — Home, top to bottom:
 *   1. the header (greeting and date, the bell, the person switch)
 *   2. the alert strip: the active low-glucose alert, then open medicine clash alerts
 *   3. up to two thin banners, each with an x: a dose due now, then the food banner (HomeBanners)
 *   4. "Today's plan": the day's meals and medicines as one flow (a brand-new person sees "Start here")
 *   5. "Your numbers": four cards compared with the person's own usual range
 *   6. "Health overview": the 7-day bar chart
 * Plan, numbers and chart come from one read (GET /home/overview, refreshed every minute); the bell opens the reminders (B2).
 * A phone stacks everything; a laptop (lg) spreads the plan across and puts the four cards in one row.
 */
import { dateLocale } from '@/lib/locale'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { useClash, useHomeOverview, useNotices, useUsers } from '@/data/hooks'
import { useDismissed } from '@/features/alerts/pieces'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { useSavedOnboarding } from '@/features/onboarding/api'
import { Header, Screen } from '@/ui/layout'
import { Alert } from '@/ui/primitives'
import { Bell } from '@/ui/icons'
import { UserSwitch } from './UserSwitch'
import { AlertStrip } from './AlertStrip'
import { HomeBanners } from './HomeBanners'
import { TodayPlan } from './TodayPlan'
import { KpiCards, KpiCardsSkeleton } from './KpiCards'
import { HealthOverview, HealthOverviewSkeleton } from './HealthOverview'
import { YourDays } from '@/features/insights/YourDays'

function greeting(h: number, t: TFunction) {
  return h < 12
    ? t('home.greeting.morning', 'Good morning')
    : h < 18
      ? t('home.greeting.afternoon', 'Good afternoon')
      : t('home.greeting.evening', 'Good evening')
}

export function Home() {
  const { t } = useTranslation()
  const go = useGo()
  const { data, isError, refetch } = useHomeOverview()
  const { data: notices } = useNotices()
  const { data: clash } = useClash()
  const setAside = useDismissed((s) => s.ids)
  const userKey = useUi((s) => s.userKey)
  const { data: users } = useUsers()
  const saved = useSavedOnboarding()
  /** the person's name: from the list the avatar uses (Mr Tan), else the name they gave in set-up; nothing is said when it is not known yet */
  const name = users?.users.find((u) => u.key === userKey)?.label?.trim() || saved.data?.profile?.displayName?.trim() || null

  /** medicine alerts the person has not set aside */
  const openAlerts = (clash?.alerts ?? []).filter((a) => !setAside.includes(a.id))
  /** unread reminders plus open medicine alerts */
  const unread = (notices?.filter((n) => n.unread).length ?? 0) + openAlerts.length
  const now = new Date()
  const dateLabel = now.toLocaleDateString(dateLocale('en-SG'), { weekday: 'long', day: 'numeric', month: 'long' })

  return (
    <Screen tabs>
      <Header
        title={name ? t('home.greeting.named', '{{greeting}}, {{name}}', { greeting: greeting(now.getHours(), t), name }) : greeting(now.getHours(), t)}
        sub={dateLabel}
        trailing={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => go('B2')}
              aria-label={t('home.bell', 'Notifications and alerts, {{n}} new', { n: unread })}
              className="press relative flex h-12 w-12 items-center justify-center rounded-full border border-line bg-card"
            >
              <Bell size={24} aria-hidden />
              {unread > 0 && <span className="absolute right-2.5 top-2.5 h-2.5 w-2.5 rounded-full bg-brass ring-2 ring-card" />}
            </button>
            <UserSwitch />
          </div>
        }
      />

      {/* 2. alerts */}
      <AlertStrip clashAlerts={openAlerts} />

      {/* 3. the dose banner, then the food banner */}
      <HomeBanners />

      {/* 4. today's plan */}
      <TodayPlan plan={data?.plan} loading={!data && !isError} error={isError && !data} onRetry={() => void refetch()} />

      {/* 5. your numbers */}
      <div className="mt-0.5 flex flex-wrap items-baseline justify-between gap-x-3">
        <h2 className="text-h2 font-bold">{t('home.numbers.title', "Today's summary")}</h2>
        <p className="text-sub text-ink2">{t('home.numbers.sub', 'Compared with your usual')}</p>
      </div>
      {data ? (
        <KpiCards data={data} />
      ) : isError ? (
        <Alert tone="warn" onClick={() => void refetch()}>
          {t('home.numbers.loadError', 'We could not load your numbers. Tap to try again.')}
        </Alert>
      ) : (
        <KpiCardsSkeleton />
      )}

      {/* 6. health overview */}
      <div className="grid gap-4 lg:grid-cols-2 [&>*]:min-w-0">
        {data ? <HealthOverview chart={data.chart} /> : isError ? null : <HealthOverviewSkeleton />}
        <YourDays />
      </div>

    </Screen>
  )
}
