/** C1 — Overview. A calendar of your days (one square per day for the measure you pick), what moved against the days before, and what the person's own history shows. */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useInsightsOverview, useInsightsOverviewDays, useInsightsTimeline } from '@/data/hooks'
import type { InsightsChange, InsightsGridKey } from '@/data/types'
import { useGo } from '@/app/navigation'
import { cn } from '@/lib/cn'
import { Alert, Card, SectionTitle, Skeleton } from '@/ui/primitives'
import { CaretLeft, CaretRight } from '@/ui/icons'
import { Findings, Gate, InsightsFrame, Plain, Tile, TileGrid, num, useInsightsDays } from './shared'
import { OverviewTimeline } from './Timeline'
import { DayCalendar, monthRange, monthTitle, shiftMonth } from './grids'

const MEASURES: InsightsGridKey[] = ['meals', 'activity', 'sleep', 'stress', 'doses']

export function Overview() {
  const days = useInsightsDays((s) => s.days)
  const { data } = useInsightsOverview(days)
  const tl = useInsightsTimeline(days)
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
  const changeName: Record<InsightsChange['id'], string> = {
    tir: measureName.glucose,
    fasting: t('insights.overview.change.fasting', 'Morning (fasting) glucose'),
    steps: t('insights.overview.change.steps', 'Steps a day'),
    exercise: measureName.activity,
    sleep: measureName.sleep,
    stress: measureName.stress,
    doses: measureName.doses,
  }

  // Numbers are written with their unit, so "62%" and "7.2 hours a night" read the same way everywhere.
  const valueText = (unit: InsightsChange['unit'], v: number) => {
    switch (unit) {
      case 'points':
        return t('insights.overview.valuePct', '{{n}}%', { n: num(v) })
      case 'mmol':
        return t('insights.overview.valueMmol', '{{n}} mmol/L', {
          n: num(v, 1),
        })
      case 'steps':
        return t('insights.overview.valueSteps', '{{n}} steps a day', {
          n: num(v),
        })
      case 'minutes':
        return t('insights.overview.valueMinutes', '{{n}} minutes', {
          n: num(v),
        })
      case 'hours':
        return t('insights.overview.valueHours', '{{n}} hours a night', {
          n: num(v, 1),
        })
      case 'score':
        return t('insights.overview.valueScore', '{{n}} out of 5', {
          n: num(v, 1),
        })
    }
  }
  const moveText = (unit: InsightsChange['unit'], d: number) => {
    const a = Math.abs(d)
    switch (unit) {
      case 'points':
        return t('insights.overview.amountPoints', '{{n}} points', {
          n: num(a),
        })
      case 'mmol':
        return t('insights.overview.amountMmol', '{{n}} mmol/L', {
          n: num(a, 1),
        })
      case 'steps':
        return t('insights.overview.amountSteps', '{{n}} steps a day', {
          n: num(a),
        })
      case 'minutes':
        return t('insights.overview.amountMinutes', '{{n}} minutes', {
          n: num(a),
        })
      case 'hours':
        return t('insights.overview.amountHours', '{{n}} hours', {
          n: num(a, 1),
        })
      case 'score':
        return t('insights.overview.amountPoints', '{{n}} points', {
          n: num(a, 1),
        })
    }
  }

  const n = data?.period.days ?? days
  const sentence = (c: InsightsChange) => {
    const curWhen = t('insights.overview.lastDays', 'in the last {{n}} days', {
      n,
    })
    const prevWhen = n === 7 ? t('insights.overview.before7', 'in the 7 days before') : t('insights.overview.beforeDays', 'in the {{n}} days before', { n })
    const amount = moveText(c.unit, c.delta ?? 0)
    const move = c.direction === 'up' ? t('insights.overview.up', 'Up {{amount}}', { amount }) : t('insights.overview.down', 'Down {{amount}}', { amount })
    return t('insights.overview.changeLine', '{{label}}: {{current}} {{curWhen}}, {{previous}} {{prevWhen}}. {{move}}.', {
      label: changeName[c.id],
      current: valueText(c.unit, c.current ?? 0),
      curWhen,
      previous: valueText(c.unit, c.previous ?? 0),
      prevWhen,
      move,
    })
  }
  const listOf = (xs: InsightsChange[]) => new Intl.ListFormat('en-GB', { style: 'long', type: 'conjunction' }).format(xs.map((c) => changeName[c.id]))

  // time in range is not shown on this page: the charts show the readings themselves against the person's own baseline
  const changes = (data?.changes ?? []).filter((c) => c.id !== 'tir')
  const moved = changes.filter((c) => c.direction === 'up' || c.direction === 'down')
  const same = changes.filter((c) => c.direction === 'same')
  const none = changes.filter((c) => c.direction === 'none')

  const tlData = tl.data
  const v = tlData?.values
  const valuesCard = (
    <Card className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-h2 font-bold">{t('insights.overview.valuesTitle', 'What the values show')}</h2>
        {tlData && <span className="text-sub text-ink3">{tlData.period.label}</span>}
      </div>
      <TileGrid>
        <Tile
          label={t('insights.overview.v.avg', 'Average glucose')}
          value={v?.avgGlucose != null ? num(v.avgGlucose, 1) : '–'}
          unit={v?.avgGlucose != null ? 'mmol/L' : undefined}
        />
        <Tile
          label={t('insights.overview.v.gmi', 'Estimated A1c (GMI)')}
          value={v?.gmi != null ? num(v.gmi, 1) : '–'}
          unit={v?.gmi != null ? '%' : undefined}
        />
        <Tile label={t('insights.overview.v.steps', 'Steps a day')} value={num(v?.stepsPerDay)} />
        <Tile
          label={t('insights.overview.v.cv', 'Glucose ups and downs (CV)')}
          value={v?.cv != null ? num(v.cv) : '–'}
          unit={v?.cv != null ? '%' : undefined}
        />
        <Tile
          label={t('insights.overview.v.doses', 'Doses taken')}
          value={v?.dosesTakenPct != null ? num(v.dosesTakenPct) : '–'}
          unit={v?.dosesTakenPct != null ? '%' : undefined}
        />
        <Tile
          label={t('insights.overview.v.sensor', 'Sensor worn')}
          value={v?.sensorWornPct != null ? num(v.sensorWornPct) : '–'}
          unit={v?.sensorWornPct != null ? '%' : undefined}
        />
      </TileGrid>
      <p className="text-sub text-ink3">{t('insights.overview.valuesNote', 'Your doctor reviews what these mean.')}</p>
    </Card>
  )

  return (
    <InsightsFrame tab="C1" period={data?.period ?? tlData?.period} why="week">
      <Gate
        data={tlData}
        isError={tl.isError && !tlData}
        empty={!!tlData && !tlData.period.hasData}
        emptyText={t('insights.overview.empty', 'Log a few meals, a workout or a check-in and your week fills in here.')}
      >
        {tlData && (
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_21rem] lg:items-start lg:gap-6 [&>*]:min-w-0">
            <div className="flex flex-col gap-6">
              <Card className="!px-3 sm:!px-4">
                <OverviewTimeline key={`${days}:${tlData.period.start}:${tlData.period.end}`} data={tlData} />
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
              {valuesCard}
              {data && (
                <section className="flex flex-col gap-2">
                  <SectionTitle>{t('insights.overview.whatChanged', 'What changed')}</SectionTitle>
                  {moved.map((c) => (
                    <Card key={c.id} onClick={() => go(c.to)} className="flex items-center gap-3">
                      <span className="flex-1 text-body">{sentence(c)}</span>
                      <CaretRight size={20} className="flex-none text-ink3" aria-hidden />
                    </Card>
                  ))}
                  {moved.length === 0 && same.length > 0 && (
                    <Card tone="soft">
                      <p className="text-body text-ink2">{t('insights.overview.nothingMoved', 'Nothing changed much from the {{n}} days before.', { n })}</p>
                    </Card>
                  )}
                  {moved.length > 0 && same.length > 0 && (
                    <p className="text-body text-ink2">
                      {t('insights.overview.alsoSame', 'About the same as the {{n}} days before: {{list}}.', { n, list: listOf(same) })}
                    </p>
                  )}
                  {moved.length === 0 && same.length === 0 && (
                    <Card tone="soft">
                      <p className="text-body text-ink2">{t('insights.overview.noCompare', 'There is not enough data in both periods to compare yet.')}</p>
                    </Card>
                  )}
                  {none.length > 0 && (
                    <p className="text-sub text-ink3">
                      {t('insights.overview.notEnough', 'Not enough data in one of the two periods to compare: {{list}}.', { list: listOf(none) })}
                    </p>
                  )}
                </section>
              )}
              {data ? (
                data.patterns.length > 0 ? (
                  <Findings title={t('insights.overview.learnt', 'What Smart Health has learnt')} items={data.patterns} onOpen={(to) => go(to)} />
                ) : (
                  <section className="flex flex-col gap-2">
                    <SectionTitle>{t('insights.overview.learnt', 'What Smart Health has learnt')}</SectionTitle>
                    <Card tone="soft">
                      <p className="text-body text-ink2">
                        {t(
                          'insights.overview.learntNone',
                          'Smart Health needs a few more matched meals and readings before it can show what it has learnt from your own history.',
                        )}
                      </p>
                    </Card>
                  </section>
                )
              ) : (
                <Skeleton className="h-40" />
              )}
            </aside>
          </div>
        )}
      </Gate>
    </InsightsFrame>
  )
}
