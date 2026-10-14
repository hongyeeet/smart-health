/**
 * Recent meals, the three latest, beside the day-by-day chart on a laptop. Each row shows the dish, when it was eaten, the calories
 * and the rise after it from the sensor (colour only). Tapping a row opens the edit and delete sheet (E7). "See all" scrolls down to
 * the full Recent entries list, which keeps every kind of entry.
 */
import { useTranslation } from 'react-i18next'
import { useRecent } from '@/data/hooks'
import type { RecentEntry } from '@/data/types'
import { useGo } from '@/app/navigation'
import { cn } from '@/lib/cn'
import { shortDate, signed } from '@/lib/format'
import { Alert, Card, Skeleton } from '@/ui/primitives'
import { TONE, riseTone } from './tones'

function MealRow({ entry, onOpen }: { entry: RecentEntry; onOpen: () => void }) {
  const { t } = useTranslation()
  const meal = entry.meal!
  const rise = meal.response?.riseMmol ?? null
  const when = t('insights.food.dateTime', '{{date}}, {{time}}', { date: shortDate(entry.date), time: meal.when })
  const sub = meal.kcal == null ? when : `${when} · ${t('insights.food.kcalValue', '{{n}} kcal', { n: Math.round(meal.kcal).toLocaleString('en-US') })}`
  const tone = rise == null ? null : TONE[riseTone(rise)]
  return (
    <li className="border-t border-line">
      <button type="button" onClick={onOpen} className="press flex min-h-11 w-full items-start gap-3 py-2.5 text-left">
        <span className="min-w-0 flex-1">
          <span className="block text-sub font-bold leading-snug">{meal.name ?? t('insights.food.untitled', 'Meal')}</span>
          <span className="block text-micro text-ink2">{sub}</span>
        </span>
        {rise != null && tone && (
          <span className={cn('num flex-none whitespace-nowrap rounded-full px-2.5 py-0.5 text-micro font-bold', tone.bg, tone.fg)}>{signed(rise)}</span>
        )}
      </button>
    </li>
  )
}

export function RecentMeals() {
  const { t } = useTranslation()
  const go = useGo()
  const { data, isError } = useRecent()
  const meals = (data ?? []).filter((e) => e.kind === 'meal' && e.meal).slice(0, 3)
  const seeAll = () => document.getElementById('food-recent')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  return (
    <Card className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-body font-bold">{t('insights.food.recentMeals', 'Recent meals')}</h3>
        <button type="button" onClick={seeAll} className="press min-h-11 rounded-chip px-1 text-sub font-bold text-brand underline">
          {t('insights.food.seeAll', 'See all')}
        </button>
      </div>
      {isError ? (
        <Alert tone="warn">{t('insights.food.recentError', 'We could not load your recent entries just now.')}</Alert>
      ) : !data ? (
        <Skeleton className="h-32" />
      ) : meals.length === 0 ? (
        <p className="py-2 text-sub text-ink2">{t('insights.food.recentMealsEmpty', 'No meals logged yet.')}</p>
      ) : (
        <ul>
          {meals.map((e) => (
            <MealRow key={e.id} entry={e} onOpen={() => go('E7', { sheet: { entry: e } })} />
          ))}
        </ul>
      )}
    </Card>
  )
}
