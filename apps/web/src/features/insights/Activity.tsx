/**
 * C4 — Activity. One card with steps, what you did, heart rate and blood oxygen; then the minutes-by-effort bars (a bar per day, week or
 * month, following the period chosen) beside what the person's history shows; then the recent workouts.
 */
import { useTranslation } from 'react-i18next'
import { useInsightsActivity } from '@/data/hooks'
import { EffortBars } from '@/charts/small'
import { Split } from '@/ui/layout'
import { Card, SectionTitle } from '@/ui/primitives'
import { Findings, Gate, InsightsFrame, Plain, useInsightsDays } from './shared'
import { ActivityOverview } from './ActivityOverview'
import { RecentWorkouts } from './RecentWorkouts'
import { HeartBlock } from './heart/HeartBlock'

export function ActivityTab() {
  const days = useInsightsDays((s) => s.days)
  const { data, isError } = useInsightsActivity(days)
  const { t } = useTranslation()
  const noMinutes = !!data && data.bars.every((b) => b.light + b.moderate + b.vigorous === 0)
  const unitNote = {
    day: t('insights.activity.unitDay', 'One bar for each day.'),
    week: t('insights.activity.unitWeek', 'One bar for each week, Monday to Sunday. The latest week is not over yet.'),
    month: t('insights.activity.unitMonth', 'One bar for each calendar month. The latest month is not over yet.'),
  }

  const bars = data && (
    <section className="flex min-w-0 flex-col gap-3">
      <SectionTitle>{t('insights.activity.minutesTitle', 'Minutes of activity')}</SectionTitle>
      <Card tone="hero" className="flex flex-col gap-3">
        {noMinutes ? <Plain>{t('insights.activity.noWorkoutsPeriod', 'No workouts logged in this period.')}</Plain> : <EffortBars bars={data.bars} />}
      </Card>
      <p className="text-sub text-ink3">
        {unitNote[data.barUnit]}{' '}
        {t('insights.activity.effortNoteV2', 'Light, moderate and vigorous are as you rated the effort, not from your heart rate. A workout you did not rate is not counted.')}
      </p>
    </section>
  )

  return (
    <InsightsFrame tab="C4" period={data?.period} why="activity">
      <Gate data={data} isError={isError} empty={!!data && !data.period.hasData} emptyText={t('insights.activity.empty', 'Log a workout and your activity shows up here.')}>
        {data && (
          <div className="flex flex-col gap-4 lg:gap-6">
            <ActivityOverview data={data} days={days} />
            {data.patterns.length > 0 ? (
              <Split>
                {bars}
                <Findings items={data.patterns} whyLink={false} />
              </Split>
            ) : (
              bars
            )}
            <RecentWorkouts workouts={data.workouts} />
          </div>
        )}
      </Gate>
      {/* with data, the heart rate sits in the overview card above; otherwise (loading, error, nothing logged) it still shows here */}
      {!(data && !isError && data.period.hasData) && <HeartBlock days={days} />}
    </InsightsFrame>
  )
}
