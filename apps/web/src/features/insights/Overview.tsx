/** C1 — Overview. The week as one chart with the logs under it, how the person's health compares with their own baseline, what moved against the days before, and what the person's own history shows. (The "Your days" calendar is on Home.) */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useInsightsOverview, useInsightsTimeline } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { Card, Skeleton } from '@/ui/primitives'
import { ArrowDown, ArrowUp } from '@/ui/icons'
import { Gate, InsightsFrame, num, useInsightsDays } from './shared'
import { HealthOverview } from './HealthOverview'
import { LearntCard } from './LearntCard'
import { BaselineCompare, OverviewTimeline } from './Timeline'

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
  const go = useGo()
  const { t } = useTranslation()

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
