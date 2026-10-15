/**
 * Recent entries, on Insights, Food (moved from the Log hub). Meals come first, each with its full detail: the dish, the time,
 * the macros, the salt and sugar notes, and how glucose moved after it from the sensor. Other kinds (symptoms, check-ins, workouts,
 * blood pressure) are compact rows. Tapping an entry opens the edit and delete sheet (E7). An unknown value is "Not judged", never 0.
 */
import { useTranslation } from 'react-i18next'
import { useRecent } from '@/data/hooks'
import type { LogKind, RecentEntry, RecentMeal } from '@/data/types'
import { useGo } from '@/app/navigation'
import { shortDate, signed } from '@/lib/format'
import { Alert, Card, EmptyState, SectionTitle, Skeleton, StatusPill } from '@/ui/primitives'
import { NumbersTag } from './NumbersTag'
import { Barbell, CaretRight, ForkKnife, Heartbeat, Smiley, Thermometer, type IconType } from '@/ui/icons'

const kindIcon: Record<LogKind, IconType> = { meal: ForkKnife, workout: Barbell, symptom: Thermometer, checkin: Smiley, blood_pressure: Heartbeat }

const toInt = (n: number) => Math.round(n).toLocaleString('en-US')

function Nutrient({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-field bg-well px-3 py-2">
      <dt className="text-sub text-ink2">{label}</dt>
      <dd className="num text-body font-bold">{value}</dd>
    </div>
  )
}

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5 [[data-ts='2']_&]:flex-col [[data-ts='2']_&]:items-start [[data-ts='2']_&]:gap-0">
      <dt className="min-w-0 text-sub text-ink2">
        {label}
        {note && <span className="block text-micro text-ink3">{note}</span>}
      </dt>
      <dd className="num text-body font-bold sm:flex-none">{value}</dd>
    </div>
  )
}

function MealCard({ entry, meal, onOpen }: { entry: RecentEntry; meal: RecentMeal; onOpen: () => void }) {
  const { t } = useTranslation()
  const na = t('insights.food.notJudged', 'Not judged')
  const grams = (v: number | null) => (v == null ? na : t('insights.food.gramsValue', '{{n}} g', { n: v < 10 ? v.toFixed(1) : toInt(v) }))
  const mmol = (v: number | null) => (v == null ? na : t('insights.food.mmolValue', '{{n}} mmol/L', { n: v.toFixed(1) }))
  const r = meal.response
  const nutrients: [string, string][] = [
    [t('insights.food.calories', 'Calories'), meal.kcal == null ? na : t('insights.food.kcalValue', '{{n}} kcal', { n: toInt(meal.kcal) })],
    [t('insights.food.carbohydrate', 'Carbohydrate'), grams(meal.carbsG)],
    [t('insights.food.protein', 'Protein'), grams(meal.proteinG)],
    [t('insights.food.fat', 'Fat'), grams(meal.fatG)],
    [t('insights.food.sugar', 'Sugar'), grams(meal.sugarG)],
    [t('insights.food.fibre', 'Fibre'), grams(meal.fibreG)],
    [t('insights.food.saltSodium', 'Salt (sodium)'), meal.sodiumMg == null ? na : t('insights.food.mgValue', '{{n}} mg', { n: toInt(meal.sodiumMg) })],
  ]
  return (
    <li>
      <Card as="section" className="flex h-full flex-col gap-3">
        <button type="button" onClick={onOpen} className="press -m-1 flex min-h-11 items-start justify-between gap-3 rounded-field p-1 text-left">
          <span className="min-w-0">
            <span className="block text-body font-bold leading-snug">{meal.name ?? t('insights.food.untitled', 'Meal')}</span>
            <span className="block text-sub text-ink2">{t('insights.food.dateTime', '{{date}}, {{time}}', { date: shortDate(entry.date), time: meal.when })}</span>
          </span>
          <CaretRight size={18} className="mt-1 flex-none text-ink3" aria-hidden />
        </button>

        {(meal.flags.length > 0 || meal.numbersFrom) && (
          <div className="flex flex-wrap gap-2">
            {meal.flags.includes('salt') && <StatusPill tone="warn">{t('insights.food.highSalt', 'High salt')}</StatusPill>}
            {meal.flags.includes('sugar') && <StatusPill tone="warn">{t('insights.food.highSugar', 'High sugar')}</StatusPill>}
            <NumbersTag from={meal.numbersFrom} />
          </div>
        )}

        {/* seven values: two columns, and the last (salt) takes the full width of its row so no cell sits alone */}
        <dl className="grid grid-cols-2 gap-2 [&>*:last-child]:col-span-2 [[data-ts='2']_&]:grid-cols-1">
          {nutrients.map(([label, value]) => (
            <Nutrient key={label} label={label} value={value} />
          ))}
        </dl>

        <div className="mt-auto flex flex-col gap-1 rounded-field border border-line px-3 py-2.5">
          <p className="text-sub font-bold text-ink2">{t('insights.food.glucoseAfter', 'Glucose after this meal')}</p>
          {r == null ? (
            <p className="text-body text-ink2">{t('insights.food.noSensor', 'No sensor data')}</p>
          ) : (
            <dl className="flex flex-col divide-y divide-line">
              <Stat label={t('insights.food.riseLabel', 'Rise in the 2 hours')} value={r.riseMmol == null ? na : t('insights.food.signedMmol', '{{n}} mmol/L', { n: signed(r.riseMmol) })} />
              <Stat
                label={t('insights.food.peakLabel', 'Peak')}
                note={r.minutesToPeak != null ? t('insights.food.peakAfter', '{{n}} min after eating', { n: r.minutesToPeak }) : undefined}
                value={mmol(r.peakMmol)}
              />
              <Stat label={t('insights.food.beforeLabel', 'Before the meal')} value={mmol(r.preMmol)} />
            </dl>
          )}
        </div>
      </Card>
    </li>
  )
}

function CompactRow({ entry, onOpen }: { entry: RecentEntry; onOpen: () => void }) {
  const Icon = kindIcon[entry.kind]
  return (
    <li>
      <button type="button" onClick={onOpen} className="press flex w-full items-center gap-3 py-3 text-left">
        <span className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-well text-ink2">
          <Icon size={22} aria-hidden />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-body font-bold leading-snug">{entry.title}</span>
          <span className="block text-sub text-ink2">{entry.detail}</span>
        </span>
        <span className="flex-none text-sub text-ink3">{entry.when}</span>
        <CaretRight size={18} className="flex-none text-ink3" aria-hidden />
      </button>
    </li>
  )
}

export function RecentEntries() {
  const { t } = useTranslation()
  const go = useGo()
  const { data, isError } = useRecent()
  const open = (entry: RecentEntry) => go('E7', { sheet: { entry } })
  const meals = (data ?? []).filter((e) => e.kind === 'meal' && e.meal)
  const others = (data ?? []).filter((e) => !(e.kind === 'meal' && e.meal))
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <SectionTitle>{t('insights.food.recent', 'Recent entries')}</SectionTitle>
        <p className="text-sub text-ink2">{t('insights.food.recentSub', 'The latest entries, newest first. Tap one to edit or delete it.')}</p>
      </div>
      {isError ? (
        <Alert tone="warn">{t('insights.food.recentError', 'We could not load your recent entries just now.')}</Alert>
      ) : !data ? (
        <Skeleton className="h-40" />
      ) : data.length === 0 ? (
        <EmptyState icon={ForkKnife}>{t('insights.food.recentEmpty', 'Nothing logged yet. Start with a meal or a quick check-in.')}</EmptyState>
      ) : (
        <>
          {meals.length > 0 && (
            <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 [&>li]:min-w-0">
              {meals.map((e) => (
                <MealCard key={e.id} entry={e} meal={e.meal!} onOpen={() => open(e)} />
              ))}
            </ul>
          )}
          {others.length > 0 && (
            <ul className="divide-y divide-line rounded-card border border-line bg-card px-4">
              {others.map((e) => (
                <CompactRow key={e.id} entry={e} onOpen={() => open(e)} />
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  )
}
