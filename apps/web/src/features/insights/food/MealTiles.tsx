/**
 * The four numbers at the top of Food: meals logged in the period, meals high in salt and high in sugar (each with its share of the
 * meals), and the average calories a day. The calories tile is "In baseline" when the period average is within 10% of the starting
 * point (the first two full weeks); otherwise it shows the starting point. Colour follows the same rule as the mock, nothing else.
 */
import { useTranslation } from 'react-i18next'
import type { InsightsFood } from '@/data/types'
import { cn } from '@/lib/cn'
import { num } from '../shared'
import { TONE, type Tone } from './tones'

function MiniTile({ label, value, unit, sub, tone }: { label: string; value: string; unit?: string; sub: string; tone: Tone }) {
  const fg = TONE[tone].fg
  return (
    <div className={cn('flex min-w-0 flex-col gap-1 rounded-card p-3', TONE[tone].bg)}>
      <span className="text-micro text-ink2">{label}</span>
      <span className={cn('num flex items-baseline gap-1 whitespace-nowrap text-h2 font-bold leading-tight', fg)}>
        {value}
        {unit && <span className="text-micro font-normal">{unit}</span>}
      </span>
      <span className={cn('flex min-w-0 items-center gap-1.5 text-micro font-bold', fg)}>
        <span className="h-2 w-2 flex-none rounded-full bg-current" aria-hidden />
        <span className="min-w-0">{sub}</span>
      </span>
    </div>
  )
}

export function MealTiles({ totals, days, kcalStart }: { totals: InsightsFood['totals']; days: number; kcalStart: number | null }) {
  const { t } = useTranslation()
  const share = (n: number) => (totals.meals > 0 ? t('insights.food.tilePercent', '{{n}}% of your meals', { n: Math.round((n / totals.meals) * 100) }) : '–')
  const avg = totals.avgKcalPerDay
  const inBaseline = avg != null && kcalStart != null && kcalStart > 0 && Math.abs(avg - kcalStart) / kcalStart <= 0.1
  const kcalSub = inBaseline
    ? t('insights.ho.key0', 'In baseline')
    : kcalStart == null
      ? t('insights.food.tileAverage', 'Average a day')
      : t('insights.food.tileStart', 'Starting point: {{n}} kcal', { n: num(kcalStart) })
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <MiniTile
        label={t('insights.food.tileLogged', 'Meals logged')}
        value={num(totals.meals)}
        sub={t('insights.food.tileLast', 'Last {{n}} days', { n: days })}
        tone="neutral"
      />
      <MiniTile
        label={t('insights.food.tileSalt', 'High in salt')}
        value={num(totals.highSaltMeals)}
        unit={t('insights.food.tileMeals', 'meals')}
        sub={share(totals.highSaltMeals)}
        tone="warn"
      />
      <MiniTile
        label={t('insights.food.tileSugar', 'High in sugar')}
        value={num(totals.highSugarMeals)}
        unit={t('insights.food.tileMeals', 'meals')}
        sub={share(totals.highSugarMeals)}
        tone="brass"
      />
      <MiniTile
        label={t('insights.food.tileKcal', 'Calories a day')}
        value={num(avg)}
        unit={avg != null ? 'kcal' : undefined}
        sub={kcalSub}
        tone={inBaseline ? 'ok' : 'neutral'}
      />
    </div>
  )
}
