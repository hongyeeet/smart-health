/** Heart rate and SpO2 from the watch. One block, used by Activity (C4) and Sleep and stress (C5). Gaps stay gaps, and nothing is judged. */
import { useTranslation } from 'react-i18next'
import { useInsightsHeart } from '@/data/hooks'
import type { InsightsDays, InsightsHeart } from '@/data/types'
import { shortDate } from '@/lib/format'
import { Alert, Card, SectionTitle, Skeleton } from '@/ui/primitives'
import { Tile, TileGrid, num } from '../shared'
import { HeartChart } from './HeartChart'

export function HeartBlock({ days }: { days: InsightsDays }) {
  const { t } = useTranslation()
  const { data, isError } = useInsightsHeart(days)
  return (
    <section className="flex flex-col gap-3">
      <SectionTitle>{t('insights.heart.title', 'Heart rate and SpO2')}</SectionTitle>
      {isError ? (
        <Alert tone="warn">{t('insights.heart.error', 'We could not load heart rate just now. Please try again in a moment.')}</Alert>
      ) : !data ? (
        <Skeleton className="h-64" />
      ) : !data.hasData ? (
        <Card tone="soft" className="flex flex-col gap-1">
          <p className="text-body font-bold">{t('insights.heart.noWatch', 'No watch data')}</p>
          <p className="text-sub text-ink2">{t('insights.heart.noWatchSub', 'Heart rate and SpO2 come from a connected watch.')}</p>
        </Card>
      ) : (
        <HeartContent data={data} />
      )}
    </section>
  )
}

function HeartContent({ data }: { data: InsightsHeart }) {
  const { t } = useTranslation()
  const hr = data.heartRate
  const sp = data.spo2
  // SpO2 is shown while asleep when the watch has it, otherwise across every reading in the period
  const asleep = sp.asleepAvg != null
  const scope = asleep ? t('insights.heart.scopeAsleep', 'While asleep') : t('insights.heart.scopeAll', 'All readings in this period')
  const spAvg = asleep ? sp.asleepAvg : sp.avg
  const spLow = asleep ? sp.asleepLow : sp.low

  return (
    <>
      <Card tone="hero" className="flex flex-col gap-3">
        {data.endNote && (
          <p className="text-sub font-bold text-ink2">{t('insights.heart.endNote', 'Showing your watch data up to {{date}}', { date: shortDate(data.period.end) })}</p>
        )}
        <TileGrid>
          <Tile
            label={t('insights.heart.avg', 'Average, bpm')}
            value={num(hr.avg)}
            sub={hr.asleepAvg != null ? t('insights.heart.asleepSub', 'Asleep: {{n}} bpm', { n: num(hr.asleepAvg) }) : undefined}
          />
          <Tile label={t('insights.heart.restingAvg', 'Resting, bpm')} value={num(hr.restingAvg)} />
          <Tile label={t('insights.heart.high', 'Highest, bpm')} value={num(hr.high)} sub={t('insights.heart.oneReading', 'one reading')} />
          <Tile label={t('insights.heart.low', 'Lowest, bpm')} value={num(hr.low)} sub={t('insights.heart.oneReading', 'one reading')} />
        </TileGrid>
        <HeartChart
          days={data.days}
          label={t('insights.heart.chartLabel', 'Average and resting heart rate by day, in beats per minute')}
        />
        <p className="text-sub text-ink3">
          {t('insights.heart.daysWith', 'Watch data on {{n}} of {{total}} days. A blank day had none.', { n: data.daysWithData, total: data.days.length })}
        </p>
      </Card>
      <Card tone="soft" className="flex flex-col gap-3">
        <p className="text-body font-bold">{t('insights.heart.spo2', 'Blood oxygen (SpO2)')}</p>
        <TileGrid>
          <Tile label={t('insights.heart.spo2Avg', 'Average, %')} value={num(spAvg, 1)} sub={scope} />
          <Tile label={t('insights.heart.spo2Low', 'Lowest, %')} value={num(spLow, 1)} sub={scope} />
        </TileGrid>
        <p className="text-sub text-ink2">
          {t('insights.heart.spo2Note', 'A watch on the wrist is less accurate than a fingertip meter.')}
        </p>
      </Card>
    </>
  )
}
