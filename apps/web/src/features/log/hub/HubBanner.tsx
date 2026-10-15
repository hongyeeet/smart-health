/** The banner at the top of the Log page. It changes with what is true now (see banner.ts): the next meal, a symptom to update, a log that is due, or all done. */
import { useTranslation } from 'react-i18next'
import { useLogProgress, useMenu, useRecent } from '@/data/hooks'
import type { MenuItem, MenuMeal, RecentEntry } from '@/data/types'
import { useGo } from '@/app/navigation'
import type { RouteId } from '@/app/routeIds'
import { appConfig } from '@/config/app'
import { Button } from '@/ui/primitives'
import { Camera, CheckCircle, ForkKnife, Heartbeat, Smiley, Thermometer, PersonSimpleWalk, type IconType } from '@/ui/icons'
import { MealBanner } from '../MealBanner'
import { mealNow } from '../MealMenu'
import { useMealSession } from '../useMealSession'
import { pickBanner, type Banner } from './banner'

const sg = (d: Date, opts: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Singapore', ...opts }).format(d)
const isoDay = (d: Date) => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Singapore' }).format(d)

/** One suggested dish for the meal: the first of the person's own meals, otherwise the first general idea. */
function suggestion(items: MenuItem[] | undefined): MenuItem | undefined {
  return items?.find((i) => i.section === 'swap') ?? items?.[0]
}

function Panel({ icon: Icon, picture, tint }: { icon: IconType; picture?: string | null; tint: string }) {
  return (
    <div className={`relative hidden min-h-[11rem] w-[18rem] flex-none sm:block ${tint}`}>
      {picture ? (
        <img src={picture} alt="" className="absolute inset-0 h-full w-full object-cover" />
      ) : (
        <span className="absolute inset-0 flex items-center justify-center text-brand/60">
          <Icon size={72} aria-hidden />
        </span>
      )}
    </div>
  )
}

export function HubBanner() {
  const { t } = useTranslation()
  const go = useGo()
  const { meal: session } = useMealSession()
  const { data: progress } = useLogProgress()
  const { data: recent } = useRecent()
  const nowMeal: MenuMeal = mealNow()
  const menu = useMenu(nowMeal)
  const now = new Date()
  const hour = Number(sg(now, { hour: 'numeric', hour12: false }))
  const nowMin = hour * 60 + Number(sg(now, { minute: 'numeric' }))
  const today = isoDay(now)
  const yesterday = isoDay(new Date(now.getTime() - 864e5))
  const banner: Banner = pickBanner({ progress, recent, eating: !!session, nowMeal, hour, today, yesterday, nowMin })

  if (banner.kind === 'eating') return <MealBanner />

  const dish = suggestion(menu.data?.sections.flatMap((s) => s.items))
  const dishPicture = dish?.image.url ? `${appConfig.apiBaseUrl}${dish.image.url}` : null
  const mealName = t(`log.menu.${nowMeal}`, nowMeal).toLowerCase()
  const when = `${sg(now, { weekday: 'long' })}, ${sg(now, { hour: 'numeric', minute: '2-digit', hour12: true }).toLowerCase()}`

  let eyebrow = when
  let title = ''
  let body = ''
  let icon: IconType = ForkKnife
  let picture: string | null = null
  let primary: { label: string; to: RouteId } | null = null
  let secondary: { label: string; to: RouteId } | null = null

  switch (banner.kind) {
    case 'meal':
      title = t('log.hub.b.mealTitle', 'It is {{meal}} time', { meal: mealName })
      body = [
        banner.window ? t('log.hub.b.mealWindow', 'Your usual window is {{window}}.', { window: banner.window }) : '',
        dish
          ? t('log.hub.b.mealDish', 'An idea from your menu: {{name}}{{kcal}}.', { name: dish.name, kcal: dish.kcal != null ? `, ${dish.kcal} kcal` : '' })
          : '',
      ]
        .filter(Boolean)
        .join(' ')
      picture = dishPicture
      primary = { label: t('log.hub.b.logMeal', 'Log {{meal}}', { meal: mealName }), to: 'E2' }
      secondary = { label: t('log.hub.b.seeIdeas', 'See {{meal}} ideas', { meal: mealName }), to: 'E9' }
      break
    case 'symptom': {
      const e: RecentEntry = banner.entry
      icon = Thermometer
      title = t('log.hub.b.symptomTitle', 'How is the {{name}} now?', { name: e.title.toLowerCase() })
      body = t('log.hub.b.symptomBody', 'You logged it today at {{when}}. An update helps your doctor see how it went.', { when: e.when })
      primary = { label: t('log.hub.b.symptomCta', 'Add an update'), to: 'E4' }
      break
    }
    case 'due': {
      const k = banner.item.key
      icon = k === 'checkin' ? Smiley : k === 'workout' ? PersonSimpleWalk : ForkKnife
      title =
        k === 'checkin'
          ? t('log.hub.b.checkinTitle', 'How are you today?')
          : k === 'workout'
            ? t('log.hub.b.workoutTitle', 'Time for a workout?')
            : banner.item.label
      body = banner.item.prompt ?? (banner.item.window ? t('log.hub.b.dueWindow', 'Your usual time is {{window}}.', { window: banner.item.window }) : '')
      primary = { label: t('log.hub.b.dueCta', 'Log it'), to: banner.item.to }
      break
    }
    case 'bp':
      icon = Heartbeat
      title = t('log.hub.b.bpTitle', 'No blood pressure reading today')
      body = t('log.hub.b.bpBody', 'A reading today keeps your doctor brief up to date.')
      primary = { label: t('log.hub.b.bpCta', 'Log blood pressure'), to: 'E3' }
      break
    case 'done':
      icon = CheckCircle
      title = t('log.hub.b.doneTitle', 'Everything is logged for now')
      body = t('log.hub.b.doneBody', 'Your day is up to date. Add anything else that happens.')
      secondary = { label: t('log.hub.b.seeIdeas', 'See {{meal}} ideas', { meal: mealName }), to: 'E9' }
      break
    default:
      icon = Camera
      title = t('log.hub.b.calmTitle', 'Add what happened')
      body = t('log.hub.b.calmBody', 'Nothing is due right now. Pick a log below and it lands on your timeline.')
  }

  return (
    <section aria-label={title} className="flex overflow-hidden rounded-card border border-brand/20 bg-brand-soft shadow-lift">
      <div className="flex min-w-0 flex-1 flex-col justify-center gap-1.5 p-5 sm:p-6">
        <p className="num text-micro font-bold uppercase tracking-wide text-ink2">{eyebrow}</p>
        <h2 className="font-serif text-h1 font-medium leading-tight">{title}</h2>
        {body && <p className="break-words text-body text-ink">{body}</p>}
        {(primary || secondary) && (
          <div className="mt-2 flex flex-wrap gap-2.5">
            {primary && (
              <Button size="md" className="!w-auto" onClick={() => go(primary!.to)}>
                {primary.label}
              </Button>
            )}
            {secondary && (
              <Button size="md" variant="secondary" className="!w-auto" onClick={() => go(secondary!.to)}>
                {secondary.label}
              </Button>
            )}
          </div>
        )}
      </div>
      <Panel icon={icon} picture={picture} tint="bg-well" />
    </section>
  )
}
