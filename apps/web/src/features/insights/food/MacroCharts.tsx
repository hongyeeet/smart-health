/**
 * Calories, carbohydrate, protein, fat and salt for each day of the period. A day with no value is a gap, never a zero. There are no
 * goal lines: no goal for these is stored, and none is invented here.
 */
import { useTranslation } from 'react-i18next'
import type { DietDay, DietTotals } from '@/data/types'
import { cn } from '@/lib/cn'
import { Alert, Card, Skeleton } from '@/ui/primitives'
import { DailyBars, type DayValue } from './DailyBars'

const toInt = (n: number) => Math.round(n).toLocaleString('en-US')
const toGrams = (n: number) => (n < 10 ? n.toFixed(1) : toInt(n))

/** One column on a phone, two on a tablet (the fifth chart takes the last row), three on a laptop (three above, two below, each of those wider). */
const GRID = 'grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-6'
const SPAN = ['lg:col-span-2', 'lg:col-span-2', 'lg:col-span-2', 'lg:col-span-3', 'md:col-span-2 lg:col-span-3']

export function MacroCharts({ days, isError }: { days: DietDay[] | undefined; isError: boolean }) {
  const { t } = useTranslation()
  const metrics: { key: string; label: string; unit: string; pick: (x: DietTotals) => number | null; format: (n: number) => string }[] = [
    { key: 'kcal', label: t('insights.food.kcalDay', 'Calories'), unit: 'kcal', pick: (x) => x.kcal, format: toInt },
    { key: 'carbs', label: t('insights.food.carbsDay', 'Carbohydrate'), unit: 'g', pick: (x) => x.carbsG, format: toGrams },
    { key: 'protein', label: t('insights.food.proteinDay', 'Protein'), unit: 'g', pick: (x) => x.proteinG, format: toGrams },
    { key: 'fat', label: t('insights.food.fatDay', 'Fat'), unit: 'g', pick: (x) => x.fatG, format: toGrams },
    { key: 'salt', label: t('insights.food.saltChart', 'Salt (sodium)'), unit: 'mg', pick: (x) => x.sodiumMg, format: toInt },
  ]

  if (isError) return <Alert tone="warn">{t('insights.food.dayError', 'We could not load the totals for each day just now.')}</Alert>
  if (!days)
    return (
      <div className={GRID}>
        {metrics.map((m, i) => (
          <Skeleton key={m.key} className={cn('h-56', SPAN[i])} />
        ))}
      </div>
    )

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sub text-ink2">{t('insights.food.gapNote', 'A gap means that day has no value for it, which is not the same as zero.')}</p>
      <div className={cn(GRID, '[&>*]:min-w-0')}>
        {metrics.map((m, i) => {
          const values: DayValue[] = days.map((d) => ({ date: d.date, value: m.pick(d.totals) }))
          const known = values.flatMap((v) => (v.value == null ? [] : [v.value]))
          const avg = known.length ? known.reduce((a, b) => a + b, 0) / known.length : null
          return (
            <Card key={m.key} className={cn('flex flex-col gap-3', SPAN[i])}>
              <div className="flex flex-col gap-0.5">
                <h3 className="text-body font-bold">{m.label}</h3>
                <p className="num text-sub text-ink2">
                  {avg == null
                    ? t('insights.food.noValuesYet', 'No values yet')
                    : t('insights.food.avgPerDay', 'Average {{value}} {{unit}} a day', { value: m.format(avg), unit: m.unit })}
                </p>
                {avg != null && (
                  <p className="text-micro text-ink3">{t('insights.food.avgOf', 'From the {{n}} days with a value.', { n: known.length })}</p>
                )}
              </div>
              <DailyBars days={values} unit={m.unit} label={m.label} format={m.format} />
            </Card>
          )
        })}
      </div>
    </div>
  )
}
