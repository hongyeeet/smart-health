/** The totals and meals of the day picked on the K10 calendar, with a link to that day in the Day view (D1). */
import { dateLocale } from '@/lib/locale'
import { useTranslation } from 'react-i18next'
import type { DietDay } from '@/data/types'
import { useGo } from '@/app/navigation'
import { NumbersTag } from '@/features/insights/food/NumbersTag'
import { Button, Card, Skeleton } from '@/ui/primitives'

const longDate = (iso: string) => new Date(iso + 'T00:00:00').toLocaleDateString(dateLocale('en-GB'), { weekday: 'long', day: 'numeric', month: 'long' })

function Total({ label, value, unit }: { label: string; value: number | null; unit: string }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-field bg-well px-3 py-2">
      <dt className="text-sub text-ink2">{label}</dt>
      <dd className="num text-body font-bold">
        {value == null ? (
          <span className="text-ink3">–</span>
        ) : (
          <>
            {Math.round(value).toLocaleString('en-US')} <span className="text-sub font-normal text-ink3">{unit}</span>
          </>
        )}
      </dd>
    </div>
  )
}

export function DayPanel({ iso, day }: { iso: string | null; day: DietDay | undefined }) {
  const { t } = useTranslation()
  const go = useGo()
  if (!iso) {
    return (
      <Card tone="soft">
        <p className="text-body text-ink2">{t('me.diet.tapDay', 'Tap a day to see its totals and meals.')}</p>
      </Card>
    )
  }
  if (!day) return <Skeleton className="h-48" />
  const totals: { label: string; value: number | null; unit: string }[] = [
    { label: t('me.diet.kcal', 'Calories'), value: day.totals.kcal, unit: 'kcal' },
    { label: t('me.diet.carbs', 'Carbohydrate'), value: day.totals.carbsG, unit: 'g' },
    { label: t('me.diet.protein', 'Protein'), value: day.totals.proteinG, unit: 'g' },
    { label: t('me.diet.fat', 'Fat'), value: day.totals.fatG, unit: 'g' },
    { label: t('me.diet.sugar', 'Sugar'), value: day.totals.sugarG, unit: 'g' },
    { label: t('me.diet.fibre', 'Fibre'), value: day.totals.fibreG, unit: 'g' },
    { label: t('me.diet.sodium', 'Salt (sodium)'), value: day.totals.sodiumMg, unit: 'mg' },
  ]
  const someUnknown = day.meals > 0 && totals.some((x) => x.value == null)
  const MEAL: Record<string, string> = {
    breakfast: t('me.diet.breakfast', 'Breakfast'),
    lunch: t('me.diet.lunch', 'Lunch'),
    dinner: t('me.diet.dinner', 'Dinner'),
    snack: t('me.diet.snack', 'Snack'),
    drink: t('me.diet.drink', 'Drink'),
  }
  return (
    <Card tone="hero" as="section" className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <h3 className="text-sub font-bold text-ink2">{longDate(iso)}</h3>
        <p className="text-body">
          {day.meals === 0
            ? t('me.diet.nothingThatDay', 'Nothing logged on this day.')
            : t('me.diet.mealCount', '{{n}} meals logged', { n: day.meals })}
        </p>
      </div>
      {day.meals > 0 && (
        <>
          <dl className="grid grid-cols-2 gap-2 [&>*:last-child]:col-span-2 [[data-ts='2']_&]:grid-cols-1">
            {totals.map((x) => (
              <Total key={x.label} label={x.label} value={x.value} unit={x.unit} />
            ))}
          </dl>
          {someUnknown && <p className="text-micro text-ink3">{t('me.diet.someUnknown', 'Some meals do not have every value recorded, so a total shows a dash.')}</p>}
          <ul className="divide-y divide-line">
            {day.mealList.map((m) => (
              <li key={m.id} className="flex flex-col gap-0.5 py-2">
                <p className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 text-body">
                  <span className="font-bold">{m.name ?? t('me.diet.untitled', 'Meal')}</span>
                  <span className="num text-sub text-ink2">{m.kcal == null ? '–' : t('me.diet.kcalValue', '{{n}} kcal', { n: m.kcal.toLocaleString('en-US') })}</span>
                </p>
                <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-micro text-ink3">
                  <span>
                    {m.when}
                    {m.mealType && MEAL[m.mealType] ? ` · ${MEAL[m.mealType]}` : ''}
                  </span>
                  <NumbersTag from={m.numbersFrom} />
                </p>
              </li>
            ))}
          </ul>
        </>
      )}
      <Button variant="secondary" size="md" className="!w-auto self-start" onClick={() => go('D1', { params: { date: iso } })}>
        {t('me.diet.openDay', 'Open this day')}
      </Button>
    </Card>
  )
}
