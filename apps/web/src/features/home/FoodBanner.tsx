/**
 * The food banner on Home: one plain line when a meal is due and not logged, or when a food habit is high in salt or sugar.
 * Only one banner shows at a time, the meal first. It shows nothing when there is nothing to say. "Not now" hides that banner for
 * the rest of the day on this device only (the next day, or a different meal, brings it back).
 * The choice is made by the server (GET /home/banner); the words are written here, with no advice in them.
 */
import { useReducer } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { request } from '@/data/repositories/http'
import { useGo } from '@/app/navigation'
import { cn } from '@/lib/cn'
import { useUi } from '@/state/store'
import { ForkKnife } from '@/ui/icons'
import { Button } from '@/ui/primitives'

export interface HomeFoodBanner {
  /** the mealtime that is open now and not logged yet, or null */
  meal: 'breakfast' | 'lunch' | 'dinner' | null
  /** a food habit high in salt or sugar (the same habits as GET /nutrition/flags), or null */
  flag: { kind: 'salt' | 'sugar'; type: string; label: string; n: number } | null
}

export function useFoodBanner() {
  return useQuery({ queryKey: ['homeBanner'], queryFn: () => request<HomeFoodBanner>('/home/banner'), refetchInterval: 60_000 })
}

/** One copy per person on this device, so one person's "Not now" never hides the banner for another. */
const STORE = 'smart-health-home-banners'
const storeKey = (user: string) => `${STORE}:${user}`

// the old copy had no person in its key; it is dropped, not moved
try {
  window.localStorage.removeItem(STORE)
} catch {
  /* storage is blocked: nothing to remove */
}

function todayKey(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** Banner ids this person dismissed today on this device, read from { [bannerId]: 'YYYY-MM-DD' }. If storage is blocked, nothing is hidden. */
function dismissedToday(user: string): Set<string> {
  try {
    const map = JSON.parse(window.localStorage.getItem(storeKey(user)) ?? '{}') as Record<string, string>
    const today = todayKey()
    return new Set(Object.entries(map).filter(([, day]) => day === today).map(([id]) => id))
  } catch {
    return new Set()
  }
}

function rememberDismissed(user: string, id: string) {
  try {
    const map = JSON.parse(window.localStorage.getItem(storeKey(user)) ?? '{}') as Record<string, string>
    window.localStorage.setItem(storeKey(user), JSON.stringify({ ...map, [id]: todayKey() }))
  } catch {
    /* storage is blocked: the banner comes back on the next visit, which is harmless */
  }
}

type Line = { id: string; tone: 'brand' | 'brass'; title: string; body: string }

export function FoodBanner({ banner }: { banner: HomeFoodBanner | undefined }) {
  const { t } = useTranslation()
  const go = useGo()
  const user = useUi((s) => s.userKey)
  const [, redraw] = useReducer((n: number) => n + 1, 0)
  if (!banner) return null
  const hidden = dismissedToday(user)

  const lines: Line[] = []
  if (banner.meal) {
    const titles = {
      breakfast: t('home.food.meal.breakfast', 'Time to log breakfast?'),
      lunch: t('home.food.meal.lunch', 'Time to log lunch?'),
      dinner: t('home.food.meal.dinner', 'Time to log dinner?'),
    }
    lines.push({ id: `meal:${banner.meal}`, tone: 'brand', title: titles[banner.meal], body: t('home.food.meal.body', 'Take a photo before you eat, or type it in.') })
  }
  if (banner.flag) {
    const food = banner.flag.label.toLowerCase()
    const title = banner.flag.kind === 'salt' ? t('home.food.salt.title', 'Your {{food}} is often high in salt.', { food }) : t('home.food.sugar.title', 'Your {{food}} is often high in sugar.', { food })
    lines.push({
      id: `flag:${banner.flag.kind}:${banner.flag.type}`,
      tone: 'brass',
      title,
      body: t('home.food.flag.body', 'Based on {{n}} of your logged meals in the last 2 weeks.', { n: banner.flag.n }),
    })
  }

  const line = lines.find((l) => !hidden.has(l.id))
  if (!line) return null

  const dismiss = () => {
    rememberDismissed(user, line.id)
    redraw()
  }

  return (
    <section aria-label={t('home.food.label', 'Food')} className={cn('flex flex-col gap-3 rounded-card border p-4', line.tone === 'brand' ? 'border-brand/30 bg-brand-soft' : 'border-brass/40 bg-brass-soft')}>
      <div className="flex items-start gap-3">
        <span className={cn('flex h-11 w-11 flex-none items-center justify-center rounded-full', line.tone === 'brand' ? 'bg-brand text-on-brand' : 'bg-card text-brass')}>
          <ForkKnife size={22} aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <p className="break-words text-body font-bold">{line.title}</p>
          <p className="text-sub text-ink2">{line.body}</p>
        </div>
      </div>
      <div className="flex flex-col gap-2 min-[380px]:flex-row [[data-ts='2']_&]:flex-col!">
        <Button icon={ForkKnife} onClick={() => go('E2')} className="flex-1">
          {t('home.action.meal', 'Log a meal')}
        </Button>
        <Button variant="ghost" onClick={dismiss} className="min-[380px]:!w-auto min-[380px]:flex-none min-[380px]:px-6 [[data-ts='2']_&]:!w-full">
          {t('home.food.notNow', 'Not now')}
        </Button>
      </div>
    </section>
  )
}
