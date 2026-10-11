/** The "What gets in the way" number row on K2. Every number comes from GET /memory/barriers/summary; no data shows a dash and "No data yet". */
import { useTranslation } from 'react-i18next'
import { useBarrierSummary } from '@/data/hooks'
import { Tile, TileGrid, num } from '@/features/insights/shared'
import { Alert, Skeleton } from '@/ui/primitives'

export function BarrierKpis() {
  const { t } = useTranslation()
  const { data, isError } = useBarrierSummary()
  if (isError) return <Alert tone="warn">{t('me.learned.kpiError', 'We could not load these numbers just now.')}</Alert>
  if (!data) return <Skeleton className="h-28" />
  const noData = t('me.learned.noDataYet', 'No data yet')
  const top = data.topReason
  return (
    <TileGrid className="gap-x-3 gap-y-3 lg:grid-cols-4 [[data-ts='2']_&]:lg:grid-cols-2">
      <Tile
        label={t('me.learned.kpiMissed', 'Doses missed this week')}
        value={data.missedThisWeek == null ? '–' : num(data.missedThisWeek)}
        sub={data.missedThisWeek == null ? noData : t('me.learned.kpiMissedSub', 'Out of {{n}} doses this week', { n: data.scheduledThisWeek })}
      />
      <Tile
        label={t('me.learned.kpiOnTime', 'Doses taken on time')}
        value={data.onTimePct == null ? '–' : `${data.onTimePct}%`}
        sub={data.onTimePct == null ? noData : t('me.learned.kpiOnTimeSub', 'Last {{days}} days, of {{n}} confirmed doses', { days: data.windowDays, n: data.confirmedDoses })}
      />
      <Tile
        label={t('me.learned.kpiReason', 'Most common reason')}
        value={top ? top.label : '–'}
        sub={top ? t('me.learned.kpiReasonSub', '{{count}} of {{missed}} missed doses, last {{days}} days', { count: top.count, missed: top.missed, days: data.windowDays }) : noData}
      />
      <Tile
        label={t('me.learned.kpiConfirmed', 'Confirmed ideas')}
        value={num(data.confirmedBarriers)}
        sub={t('me.learned.kpiConfirmedSub', '{{n}} waiting for you', { n: data.waitingBarriers })}
      />
    </TileGrid>
  )
}
