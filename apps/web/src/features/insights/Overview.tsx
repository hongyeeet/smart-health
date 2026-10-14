/** C1 — Overview. A calendar of your days (one square per day for the measure you pick), what moved against the days before, and what the person's own history shows. */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useInsightsOverview, useInsightsOverviewDays, useInsightsTimeline } from '@/data/hooks'
import type { InsightsGridKey } from '@/data/types'
import { useGo } from '@/app/navigation'
import { cn } from '@/lib/cn'
import { Alert, Card, SectionTitle, Skeleton } from '@/ui/primitives'
import { ArrowDown, ArrowUp, CaretLeft, CaretRight } from '@/ui/icons'
import { Gate, InsightsFrame, Plain, num, useInsightsDays } from './shared'
import { HealthOverview } from './HealthOverview'
import { LearntCard } from './LearntCard'
import { BaselineCompare, OverviewTimeline } from './Timeline'
import { DayCalendar, monthRange, monthTitle, shiftMonth } from './grids'

const MEASURES: InsightsGridKey[] = ['meals', 'activity', 'sleep', 'stress', 'doses']

export function Overview() {
  const { days, setDays } = useInsightsDays()
  // the last day of the 7 days shown (a date picked in the calendar); null is "this week", the latest 7 days
  const [endIso, setEndIso] = useState<string | null>(null)
  const { data } = useInsightsOverview(days)
  const tl = useInsightsTimeline(days, days === 7 ? (endIso ?? undefined) : undefined)
  const pickDays = (d: typeof days) => {
    setEndIso(null)
    setDays(d)
  }
  // from a one-point-a-day view: show the 7 days ending on a day
  const openWeek = (iso: string) => {
    setEndIso(iso)
    setDays(7)
  }
  const [browsed, setBrowsed] = useState<string | null>(null)
  const [measure, setMeasure] = useState<InsightsGridKey>('meals')
  const go = useGo()
  const { t } = useTranslation()

  // The calendar opens on the month of the latest day with data, and moves by arrows. It never goes past the current month.
  const month = browsed ?? data?.period.end.slice(0, 7) ?? null
  const range = month ? monthRange(month) : null
  const cal = useInsightsOverviewDays(range?.start ?? '', range?.end ?? '', !!range)
  const todayMonth = cal.data?.today.slice(0, 7)
  const calReady = !!cal.data && !!range && cal.data.start === range.start
  const calRow = calReady ? cal.data?.rows.find((r) => r.key === measure) : undefined

  const measureName: Record<InsightsGridKey, string> = {
    glucose: t('insights.overview.measure.glucose', 'Glucose in range'),
    meals: t('insights.overview.measure.meals', 'Meals logged'),
    activity: t('insights.overview.measure.activity', 'Active minutes'),
    sleep: t('insights.overview.measure.sleep', 'Sleep'),
    stress: t('insights.overview.measure.stress', 'Stress'),
    doses: t('insights.overview.measure.doses', 'Doses taken'),
  }
  const measureHint: Record<InsightsGridKey, string> = {
    glucose: t('insights.overview.hint.glucose', 'Share of the day’s readings in range, as a percentage.'),
    meals: t('insights.overview.hint.meals', 'Meals logged that day.'),
    activity: t('insights.overview.hint.activity', 'Minutes of activity that day.'),
    sleep: t('insights.overview.hint.sleep', 'Hours slept, from your watch.'),
    stress: t('insights.overview.hint.stress', 'Your stress rating that day, from 1 (low) to 5 (high).'),
    doses: t('insights.overview.hint.doses', 'Share of that day’s scheduled doses you took.'),
  }
  const tlData = tl.data
  // what changed: this period against the period of the same length just before it (from the timeline answer, so it follows the week picked)
  const prev = tlData?.previous
  const cur = tlData?.values
  const moves: { key: string; name: string; note: string; delta: string; dir: 'up' | 'down' | 'same' }[] = []
  if (cur && prev) {
    const add = (key: string, name: string, now: number | null, before: number | null, digits: number, unit: string) => {
      if (now == null || before == null) return
      const d = Number((now - before).toFixed(digits))
      moves.push({
        key,
        name,
        note: t('insights.chg.note', '{{now}} now, {{before}} before', { now: `${num(now, digits)}${unit}`, before: `${num(before, digits)}${unit}` }),
        delta: d === 0 ? t('insights.chg.same', 'About the same') : `${d > 0 ? '+' : '−'}${num(Math.abs(d), digits)}${unit === '%' ? ' pts' : ''}`,
        dir: d === 0 ? 'same' : d > 0 ? 'up' : 'down',
      })
    }
    add('glucose', t('insights.chg.glucose', 'Average glucose'), cur.avgGlucose, prev.avgGlucose, 1, '')
    add('steps', t('insights.chg.steps', 'Steps a day'), cur.stepsPerDay, prev.stepsPerDay, 0, '')
    add('doses', t('insights.chg.doses', 'Doses taken'), cur.dosesTakenPct, prev.dosesTakenPct, 0, '%')
  }
  const changeCard = (
    <section
      className="flex flex-col gap-1 rounded-card border border-line bg-card px-3.5 pb-1.5 pt-3.5 shadow-lift"
      aria-label={t('insights.overview.whatChanged', 'What changed')}
    >
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-body font-bold">{t('insights.overview.whatChanged', 'What changed')}</h2>
        <span className="text-[11px] text-ink3">{t('insights.chg.vs', 'vs the {{n}} days before', { n: days })}</span>
      </div>
      {moves.length === 0 ? (
        <p className="pb-2 text-sub text-ink2">{t('insights.chg.none', 'There is no earlier period with data to compare with.')}</p>
      ) : (
        <ul className="flex flex-col">
          {moves.map((m) => (
            <li key={m.key} className="flex min-h-[3.1rem] items-center gap-2.5 border-t border-line py-1.5 first:border-t-0">
              <span className="flex h-7 w-7 flex-none items-center justify-center rounded-full bg-well text-ink2" aria-hidden>
                {m.dir === 'same' ? <span className="h-0.5 w-3 rounded bg-current" /> : m.dir === 'up' ? <ArrowUp size={15} /> : <ArrowDown size={15} />}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sub font-bold leading-tight">{m.name}</p>
                <p className="truncate text-[11px] leading-tight text-ink2">{m.note}</p>
              </div>
              <span className="num flex-none text-right text-sub font-bold">{m.delta}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )

  return (
    <InsightsFrame tab="C1" period={data?.period ?? tlData?.period} why="week" filter={false} wide>
      <Gate
        data={tlData}
        isError={tl.isError && !tlData}
        empty={!!tlData && !tlData.period.hasData}
        emptyText={t('insights.overview.empty', 'Log a few meals, a workout or a check-in and your week fills in here.')}
      >
        {tlData && (
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_16.5rem] xl:grid-cols-[minmax(0,1fr)_19rem] lg:items-start lg:gap-6 [&>*]:min-w-0">
            <div className="flex flex-col gap-6">
              <Card className="!px-3 sm:!px-4">
                <OverviewTimeline
                  data={tlData}
                  days={days}
                  setDays={pickDays}
                  endIso={endIso}
                  setEnd={setEndIso}
                  openWeek={openWeek}
                  openDay={(date) => go('D1', { params: { date } })}
                />
              </Card>
              <section className="flex flex-col gap-3">
                <SectionTitle>{t('insights.overview.yourDays', 'Your days')}</SectionTitle>
                <Plain>{t('insights.overview.calendarPlain', 'One square for each day. Pick a measure, then tap a day to open it.')}</Plain>
                <div role="radiogroup" aria-label={t('insights.overview.measureLabel', 'Measure')} className="flex flex-wrap gap-2">
                  {MEASURES.map((k) => {
                    const on = k === measure
                    return (
                      <button
                        key={k}
                        type="button"
                        role="radio"
                        aria-checked={on}
                        onClick={() => setMeasure(k)}
                        className={cn(
                          'press min-h-11 rounded-chip border-[1.5px] px-3.5 py-1.5 text-sub',
                          on ? 'border-brand bg-brand-soft font-bold text-brand' : 'border-line bg-card text-ink',
                        )}
                      >
                        {measureName[k]}
                      </button>
                    )
                  })}
                </div>
                <Card tone="hero" className="flex flex-col gap-3 !px-3 sm:!px-4">
                  <div className="flex items-center justify-between gap-2">
                    <button
                      type="button"
                      onClick={() => month && setBrowsed(shiftMonth(month, -1))}
                      disabled={!month}
                      aria-label={t('insights.overview.prevMonth', 'Previous month')}
                      className="press flex min-h-12 min-w-12 items-center justify-center rounded-chip text-ink2 disabled:opacity-40"
                    >
                      <CaretLeft size={24} aria-hidden />
                    </button>
                    <p className="text-center font-serif text-h2 font-medium" aria-live="polite">
                      {month ? monthTitle(month) : ''}
                    </p>
                    <button
                      type="button"
                      onClick={() => month && setBrowsed(shiftMonth(month, 1))}
                      disabled={!month || !todayMonth || month >= todayMonth}
                      aria-label={t('insights.overview.nextMonth', 'Next month')}
                      className="press flex min-h-12 min-w-12 items-center justify-center rounded-chip text-ink2 disabled:opacity-40"
                    >
                      <CaretRight size={24} aria-hidden />
                    </button>
                  </div>
                  {cal.isError ? (
                    <Alert tone="warn">{t('insights.shared.loadError', 'We could not load this just now. Please try again in a moment.')}</Alert>
                  ) : calRow && month && cal.data ? (
                    <DayCalendar month={month} cells={calRow.cells} today={cal.data.today} measure={measureName[measure]} />
                  ) : (
                    <Skeleton className="h-64" />
                  )}
                </Card>
                <p className="text-sub text-ink3">{measureHint[measure]}</p>
              </section>
            </div>
            <aside className="flex flex-col gap-4">
              <HealthOverview data={tlData} />
              <BaselineCompare data={tlData} />
              {changeCard}
              {data ? <LearntCard items={data.patterns} onOpen={(to) => go(to)} onAll={() => go('K2')} /> : <Skeleton className="h-40" />}
            </aside>
          </div>
        )}
      </Gate>
    </InsightsFrame>
  )
}
