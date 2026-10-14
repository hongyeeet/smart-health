/**
 * Day by day: one chart at a time (calories, carbohydrate, protein, fat or salt) for each day of the period, with the average of the
 * days that have a value. A day with no value is a gap, never a zero. There are no goal lines: no goal for these is stored, and none
 * is invented here.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { DietDay, DietTotals } from '@/data/types'
import { cn } from '@/lib/cn'
import { Alert, Card, Skeleton } from '@/ui/primitives'
import { DailyBars } from './DailyBars'

const toInt = (n: number) => Math.round(n).toLocaleString('en-US')
const toGrams = (n: number) => (n < 10 ? n.toFixed(1) : toInt(n))

type Key = 'kcal' | 'carbs' | 'protein' | 'fat' | 'salt'

export function MacroCharts({ days, isError }: { days: DietDay[] | undefined; isError: boolean }) {
  const { t } = useTranslation()
  const [key, setKey] = useState<Key>('kcal')
  const metrics: { key: Key; label: string; unit: string; pick: (x: DietTotals) => number | null; format: (n: number) => string }[] = [
    { key: 'kcal', label: t('insights.food.tabCalories', 'Calories'), unit: 'kcal', pick: (x) => x.kcal, format: toInt },
    { key: 'carbs', label: t('insights.food.tabCarbs', 'Carbs'), unit: 'g', pick: (x) => x.carbsG, format: toGrams },
    { key: 'protein', label: t('insights.food.tabProtein', 'Protein'), unit: 'g', pick: (x) => x.proteinG, format: toGrams },
    { key: 'fat', label: t('insights.food.tabFat', 'Fat'), unit: 'g', pick: (x) => x.fatG, format: toGrams },
    { key: 'salt', label: t('insights.food.tabSalt', 'Salt'), unit: 'mg', pick: (x) => x.sodiumMg, format: toInt },
  ]

  if (isError) return <Alert tone="warn">{t('insights.food.dayError', 'We could not load the totals for each day just now.')}</Alert>
  if (!days) return <Skeleton className="h-80" />

  const m = metrics.find((x) => x.key === key) ?? metrics[0]
  const values = days.map((d) => ({ date: d.date, value: m.pick(d.totals) }))
  const known = values.flatMap((v) => (v.value == null ? [] : [v.value]))
  const avg = known.length ? known.reduce((a, b) => a + b, 0) / known.length : null

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h3 className="text-body font-bold">{t('insights.food.dayByDay', 'Day by day')}</h3>
          <p className="text-sub text-ink2">{t('insights.food.gapNoteDashed', 'A dashed gap means nothing was logged that day.')}</p>
        </div>
        <div
          role="radiogroup"
          aria-label={t('insights.food.metricPick', 'What to chart')}
          className="flex flex-wrap gap-1 rounded-chip border border-line bg-well p-1"
        >
          {metrics.map((x) => {
            const on = x.key === m.key
            return (
              <button
                key={x.key}
                type="button"
                role="radio"
                aria-checked={on}
                onClick={() => setKey(x.key)}
                className={cn(
                  'press min-h-11 flex-1 whitespace-nowrap rounded-chip px-3 text-sub sm:flex-none',
                  on ? 'bg-card font-bold text-ink shadow-lift' : 'text-ink2',
                )}
              >
                {x.label}
              </button>
            )
          })}
        </div>
      </div>
      <div className="flex flex-wrap items-baseline gap-x-2.5">
        {avg == null ? (
          <span className="text-sub text-ink2">{t('insights.food.noValuesYet', 'No values yet')}</span>
        ) : (
          <>
            <span className="num text-h2 font-bold">
              {m.format(avg)} {m.unit}
            </span>
            <span className="text-sub text-ink2">{t('insights.food.avgLine', 'average a day.')}</span>
          </>
        )}
      </div>
      <DailyBars days={values} unit={m.unit} label={m.label} format={m.format} avg={avg} />
      <p className="text-micro text-ink3">
        {t('insights.food.avgLegend', 'Dashed line: your average.')}
        {avg != null && ' ' + t('insights.food.avgOf', 'From the {{n}} days with a value.', { n: known.length })}
      </p>
    </Card>
  )
}
