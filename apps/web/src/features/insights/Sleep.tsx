/**
 * C5 — Sleep and stress. One card with sleep, heart rate and blood oxygen, mood and stress, and blood pressure; then what the person's
 * own history shows.
 */
import { useTranslation } from 'react-i18next'
import { useInsightsSleep } from '@/data/hooks'
import { Alert, Skeleton } from '@/ui/primitives'
import { Findings, InsightsFrame, useInsightsDays } from './shared'
import { SleepOverview } from './SleepOverview'

export function SleepTab() {
  const days = useInsightsDays((s) => s.days)
  const { data, isError } = useInsightsSleep(days)
  const { t } = useTranslation()
  return (
    <InsightsFrame tab="C5" period={data?.period} why="sleep">
      {isError ? (
        <Alert tone="warn">{t('insights.shared.loadError', 'We could not load this just now. Please try again in a moment.')}</Alert>
      ) : !data ? (
        <Skeleton className="h-96" />
      ) : (
        <div className="flex flex-col gap-4 lg:gap-6">
          <SleepOverview data={data} days={days} />
          <Findings items={data.patterns} whyLink={false} twoColumns />
        </div>
      )}
    </InsightsFrame>
  )
}
