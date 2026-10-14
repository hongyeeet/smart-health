/**
 * "Your days": a calendar with one square per day for the measure you pick (meals, active minutes, sleep, stress, doses). Tap a day to open it.
 * It opens on the current month and moves by arrows, never past the current month. It lives on Home, beside the Health overview.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useInsightsOverviewDays } from '@/data/hooks'
import type { InsightsGridKey } from '@/data/types'
import { cn } from '@/lib/cn'
import { Alert, Skeleton } from '@/ui/primitives'
import { CaretLeft, CaretRight } from '@/ui/icons'
import { DayCalendar, monthRange, monthTitle, shiftMonth } from './grids'

const MEASURES: InsightsGridKey[] = ['meals', 'activity', 'sleep', 'stress', 'doses']

/** The current month in Singapore, as YYYY-MM. */
const thisMonth = () => new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Singapore' }).slice(0, 7)

export function YourDays() {
  const { t } = useTranslation()
  const [browsed, setBrowsed] = useState<string | null>(null)
  const [measure, setMeasure] = useState<InsightsGridKey>('meals')
  const month = browsed ?? thisMonth()
  const range = monthRange(month)
  const cal = useInsightsOverviewDays(range.start, range.end, true)
  const todayMonth = cal.data?.today.slice(0, 7) ?? thisMonth()
  const calReady = !!cal.data && cal.data.start === range.start
  const calRow = calReady ? cal.data?.rows.find((r) => r.key === measure) : undefined

  const measureName: Record<InsightsGridKey, string> = {
    glucose: t('insights.overview.measure.glucose', 'Glucose in range'),
    meals: t('insights.overview.measure.meals', 'Meals logged'),
    activity: t('insights.overview.measure.activity', 'Active minutes'),
    sleep: t('insights.overview.measure.sleep', 'Sleep'),
    stress: t('insights.overview.measure.stress', 'Stress'),
    doses: t('insights.overview.measure.doses', 'Doses taken'),
  }
  // short names, so the five choices fit on one row
  const pillName: Record<InsightsGridKey, string> = {
    glucose: t('insights.overview.pill.glucose', 'Glucose'),
    meals: t('insights.overview.pill.meals', 'Meals'),
    activity: t('insights.overview.pill.activity', 'Activity'),
    sleep: t('insights.overview.pill.sleep', 'Sleep'),
    stress: t('insights.overview.pill.stress', 'Stress'),
    doses: t('insights.overview.pill.doses', 'Doses'),
  }

  return (
    <section
      aria-label={t('insights.overview.yourDays', 'Your days')}
      className="flex min-w-0 flex-col gap-3 rounded-card border border-line bg-card p-4 shadow-lift"
    >
      <div className="flex flex-col gap-0.5">
        <h2 className="text-h2 font-bold">{t('insights.overview.yourDays', 'Your days')}</h2>
        <p className="text-sub text-ink2">{t('insights.overview.calendarPlain', 'One square for each day. Pick a measure, then tap a day to open it.')}</p>
      </div>
      <div role="radiogroup" aria-label={t('insights.overview.measureLabel', 'Measure')} className="flex flex-nowrap gap-1.5">
        {MEASURES.map((k) => {
          const on = k === measure
          return (
            <button
              key={k}
              type="button"
              role="radio"
              aria-checked={on}
              aria-label={measureName[k]}
              onClick={() => setMeasure(k)}
              className={cn(
                'press min-h-10 min-w-0 flex-1 whitespace-nowrap rounded-chip border-[1.5px] px-2 py-1 text-sub',
                on ? 'border-brand bg-brand-soft font-bold text-brand' : 'border-line bg-card text-ink',
              )}
            >
              {pillName[k]}
            </button>
          )
        })}
      </div>
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => setBrowsed(shiftMonth(month, -1))}
          aria-label={t('insights.overview.prevMonth', 'Previous month')}
          className="press flex min-h-11 min-w-11 items-center justify-center rounded-chip text-ink2"
        >
          <CaretLeft size={22} aria-hidden />
        </button>
        <p className="text-center font-serif text-h2 font-medium" aria-live="polite">
          {monthTitle(month)}
        </p>
        <button
          type="button"
          onClick={() => setBrowsed(shiftMonth(month, 1))}
          disabled={month >= todayMonth}
          aria-label={t('insights.overview.nextMonth', 'Next month')}
          className="press flex min-h-11 min-w-11 items-center justify-center rounded-chip text-ink2 disabled:opacity-40"
        >
          <CaretRight size={22} aria-hidden />
        </button>
      </div>
      {cal.isError ? (
        <Alert tone="warn">{t('insights.shared.loadError', 'We could not load this just now. Please try again in a moment.')}</Alert>
      ) : calRow && cal.data ? (
        <DayCalendar month={month} cells={calRow.cells} today={cal.data.today} measure={measureName[measure]} />
      ) : (
        <Skeleton className="h-64" />
      )}
    </section>
  )
}
