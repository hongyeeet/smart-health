/**
 * The two thin banners under the alert strip on Home, each with an x. At most these two, in this order:
 *   (a) the dose banner: a dose due now ("<Medicine> due now", its time, one Taken button that marks it taken);
 *   (b) directly below it, the food banner: an unfinished meal (MealBanner, which replaces it) or else the first of
 *       a lighter lunch idea (inside the lunch window), "Time to log <meal>?" (the open mealtime), a food habit high in salt or sugar,
 *       and ideas Smart Health noticed and is waiting for the person to check.
 * The x hides that banner for the rest of the day for that person on this device (storage in FoodBanner.tsx). The words are written
 * here and give no advice; the numbers come from the person's own data.
 */
import { useReducer, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useDoses, useLearned, useLunchIdeas, useMarkTaken, useMealIdeas } from '@/data/hooks'
import type { LunchIdeas } from '@/data/types'
import { useGo } from '@/app/navigation'
import { MealBanner } from '@/features/log/MealBanner'
import { useMealSession } from '@/features/log/useMealSession'
import { cn } from '@/lib/cn'
import { useUi } from '@/state/store'
import { Bell, ForkKnife, Pill, X } from '@/ui/icons'
import { dismissedToday, rememberDismissed, useFoodBanner } from './FoodBanner'

/** Lunch ideas are only offered inside the person's lunch window (times from the server, never hard-coded here). */
export function lunchOpenNow(d: LunchIdeas, now = new Date()): boolean {
  const mins = now.getHours() * 60 + now.getMinutes()
  const [sh, sm] = d.windowStart.split(':').map(Number)
  const [eh, em] = d.windowEnd.split(':').map(Number)
  return mins >= (sh ?? 0) * 60 + (sm ?? 0) && mins <= (eh ?? 0) * 60 + (em ?? 0)
}

function Banner({ tone, icon, title, sub, action, onClose, closeLabel }: { tone: 'dark' | 'brass' | 'brand'; icon: ReactNode; title: string; sub?: string; action: ReactNode; onClose: () => void; closeLabel: string }) {
  return (
    <div
      className={cn(
        'flex min-h-[68px] flex-nowrap items-center gap-x-2.5 gap-y-1 rounded-[18px] py-1.5 pl-3 pr-1 [[data-ts=\'2\']_&]:flex-wrap',
        tone === 'dark' && 'bg-brand text-on-brand',
        tone === 'brass' && 'border border-brass/40 bg-brass-soft text-ink',
        tone === 'brand' && 'border border-brand/30 bg-brand-soft text-ink',
      )}
    >
      <span className={cn('flex h-9 w-9 flex-none items-center justify-center rounded-full', tone === 'dark' ? 'bg-on-brand/15' : tone === 'brass' ? 'bg-card text-brass' : 'bg-brand text-on-brand')}>{icon}</span>
      <div className="min-w-0 flex-1 basis-36">
        <p className="break-words text-sub font-bold leading-tight">{title}</p>
        {sub && <p className={cn('break-words text-micro', tone === 'dark' ? 'opacity-90' : 'text-ink2')}>{sub}</p>}
      </div>
      <div className="flex flex-none items-center">
        {action}
        <button type="button" onClick={onClose} aria-label={closeLabel} className="press flex h-11 w-11 flex-none items-center justify-center rounded-full">
          <X size={20} aria-hidden />
        </button>
      </div>
    </div>
  )
}

const BTN = 'press min-h-11 flex-none rounded-[12px] px-3.5 text-btn-sm font-bold'

export function HomeBanners() {
  const { t } = useTranslation()
  const go = useGo()
  const user = useUi((s) => s.userKey)
  const { meal } = useMealSession()
  const { data: doses } = useDoses()
  const { data: food } = useFoodBanner()
  const { data: lunch } = useLunchIdeas()
  const { data: dinner } = useMealIdeas(food?.meal === 'dinner' ? 'dinner' : null)
  const { data: learned } = useLearned()
  const mark = useMarkTaken()
  const [, redraw] = useReducer((n: number) => n + 1, 0)
  const hidden = dismissedToday(user)
  const hide = (id: string) => {
    rememberDismissed(user, id)
    redraw()
  }

  /* (a) a dose due now */
  const due = doses?.due[0]
  const doseId = due ? `dose:${due.id}` : null
  const dose =
    due && doseId && !hidden.has(doseId) ? (
      <Banner
        tone="dark"
        icon={<Pill size={20} aria-hidden />}
        title={t('home.banner.doseDue', '{{medicine}} due now', { medicine: due.title })}
        sub={due.withFood ? t('home.banner.doseFood', '{{time}}, with food', { time: due.time }) : due.time}
        action={
          <button type="button" disabled={mark.isPending} onClick={() => mark.mutate(due.id)} className={cn(BTN, 'bg-on-brand text-brand disabled:opacity-70')}>
            {t('home.dose.taken', 'Taken')}
          </button>
        }
        onClose={() => hide(doseId)}
        closeLabel={t('home.banner.closeReminder', 'Close this reminder')}
      />
    ) : null

  /* (b) the food banner */
  let foodBanner: ReactNode = null
  if (meal) foodBanner = <MealBanner />
  else {
    const close = t('home.banner.closeSuggestion', 'Close this suggestion')
    const ideaNames = lunch && lunch.options.length > 0 && lunchOpenNow(lunch) ? lunch.options.slice(0, 2).map((o) => o.name).join(', ') : null
    const mealTitles = {
      breakfast: t('home.food.meal.breakfast', 'Time to log breakfast?'),
      lunch: t('home.food.meal.lunch', 'Time to log lunch?'),
      dinner: t('home.food.meal.dinner', 'Time to log dinner?'),
    }
    const flag = food?.flag
    const candidates: { id: string; node: ReactNode }[] = []
    if (ideaNames)
      candidates.push({
        id: 'idea:lunch',
        node: (
          <Banner
            tone="brass"
            icon={<ForkKnife size={20} aria-hidden />}
            title={t('home.banner.lighterLunch', 'Lighter lunch idea')}
            sub={ideaNames}
            action={
              <button type="button" onClick={() => go('E8')} className={cn(BTN, 'bg-brand text-on-brand')}>
                {t('home.banner.seeIdeas', 'See ideas')}
              </button>
            }
            onClose={() => hide('idea:lunch')}
            closeLabel={close}
          />
        ),
      })
    /* the open dinner time: a suggested dinner from the person's own past dinners, when there is one; the plain prompt below covers the rest */
    const dinnerTop = food?.meal === 'dinner' ? dinner?.options[0] : undefined
    if (dinnerTop)
      candidates.push({
        id: 'idea:dinner',
        node: (
          <Banner
            tone="brass"
            icon={<ForkKnife size={20} aria-hidden />}
            title={t('home.banner.suggestedDinner', 'Suggested dinner')}
            sub={dinnerTop.name}
            action={
              <button type="button" onClick={() => go('E2')} className={cn(BTN, 'bg-brand text-on-brand')}>
                {t('home.banner.logDinner', 'Log dinner')}
              </button>
            }
            onClose={() => hide('idea:dinner')}
            closeLabel={close}
          />
        ),
      })
    if (food?.meal && !(food.meal === 'dinner' && dinnerTop))
      candidates.push({
        id: `meal:${food.meal}`,
        node: (
          <Banner
            tone="brand"
            icon={<ForkKnife size={20} aria-hidden />}
            title={mealTitles[food.meal]}
            sub={t('home.food.meal.body', 'Take a photo before you eat, or type it in.')}
            action={
              <button type="button" onClick={() => go('E2')} className={cn(BTN, 'bg-brand text-on-brand')}>
                {t('home.action.meal', 'Log a meal')}
              </button>
            }
            onClose={() => hide(`meal:${food.meal}`)}
            closeLabel={close}
          />
        ),
      })
    if (flag) {
      const id = `flag:${flag.kind}:${flag.type}`
      const label = flag.label.toLowerCase()
      candidates.push({
        id,
        node: (
          <Banner
            tone="brass"
            icon={<ForkKnife size={20} aria-hidden />}
            title={flag.kind === 'salt' ? t('home.food.salt.title', 'Your {{food}} is often high in salt.', { food: label }) : t('home.food.sugar.title', 'Your {{food}} is often high in sugar.', { food: label })}
            sub={t('home.food.flag.body', 'Based on {{n}} of your logged meals in the last 2 weeks.', { n: flag.n })}
            action={
              <button type="button" onClick={() => go('E8')} className={cn(BTN, 'bg-brand text-on-brand')}>
                {t('home.banner.seeIdeas', 'See ideas')}
              </button>
            }
            onClose={() => hide(id)}
            closeLabel={close}
          />
        ),
      })
    }
    if (learned && learned.toConfirm > 0)
      candidates.push({
        id: 'confirm',
        node: (
          <Banner
            tone="brass"
            icon={<Bell size={20} aria-hidden />}
            title={learned.toConfirm === 1 ? t('home.noticed.one', 'Smart Health noticed something') : t('home.noticed.many', 'Smart Health noticed {{n}} things', { n: learned.toConfirm })}
            sub={t('home.noticed.check', 'Check it is right. You can confirm, change or delete it.')}
            action={
              <button type="button" onClick={() => go('K2')} className={cn(BTN, 'bg-brand text-on-brand')}>
                {t('home.banner.check', 'Check')}
              </button>
            }
            onClose={() => hide('confirm')}
            closeLabel={close}
          />
        ),
      })
    foodBanner = candidates.find((c) => !hidden.has(c.id))?.node ?? null
  }

  if (!dose && !foodBanner) return null
  return (
    <div className="flex flex-col gap-3">
      {dose}
      {foodBanner}
    </div>
  )
}
