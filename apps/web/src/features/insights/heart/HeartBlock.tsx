/**
 * Heart rate and SpO2 from the watch. Used by Sleep and stress (C5) as two cards (`HeartBlock`) and by Activity (C4) as two sections of its
 * overview card (`HeartPanel`, `Spo2Panel`). Gaps stay gaps, and nothing is judged.
 */
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
        <NoWatch />
      ) : (
        <>
          <Card tone="hero">
            <HeartPanel data={data} />
          </Card>
          <Card tone="soft">
            <Spo2Panel data={data} />
          </Card>
        </>
      )}
    </section>
  )
}

export function NoWatch() {
  const { t } = useTranslation()
  return (
    <Card tone="soft" className="flex flex-col gap-1">
      <p className="text-body font-bold">{t('insights.heart.noWatch', 'No watch data')}</p>
      <p className="text-sub text-ink2">{t('insights.heart.noWatchSub', 'Heart rate and SpO2 come from a connected watch.')}</p>
    </Card>
  )
}

/** Average and resting heart rate (the day's highest and lowest single readings in small grey text under resting) and the day-by-day chart. */
export function HeartPanel({ data }: { data: InsightsHeart }) {
  const { t } = useTranslation()
  const hr = data.heartRate
  return (
    <div className="flex flex-col gap-3">
      {data.endNote && (
        <p className="text-sub font-bold text-ink2">{t('insights.heart.endNote', 'Showing your watch data up to {{date}}', { date: shortDate(data.period.end) })}</p>
      )}
      <TileGrid>
        <Tile
          label={t('insights.heart.avg', 'Average, bpm')}
          value={num(hr.avg)}
          sub={hr.asleepAvg != null ? t('insights.heart.asleepSub', 'Asleep: {{n}} bpm', { n: num(hr.asleepAvg) }) : undefined}
        />
        <Tile
          label={t('insights.heart.restingAvg', 'Resting, bpm')}
          value={num(hr.restingAvg)}
          sub={t('insights.heart.highLow', 'Highest {{high}} · Lowest {{low}} bpm', { high: num(hr.high), low: num(hr.low) })}
        />
      </TileGrid>
      <HeartChart days={data.days} label={t('insights.heart.chartLabel', 'Average and resting heart rate by day, in beats per minute')} />
      <p className="text-sub text-ink3">
        {t('insights.heart.daysWith', 'Watch data on {{n}} of {{total}} days. A blank day had none.', { n: data.daysWithData, total: data.days.length })}{' '}
        {t('insights.heart.singleReadings', 'Highest and lowest are single readings.')}
      </p>
    </div>
  )
}

/** Blood oxygen: while asleep when the watch has it, otherwise across every reading in the period. */
export function Spo2Panel({ data, showTitle = true }: { data: InsightsHeart; showTitle?: boolean }) {
  const { t } = useTranslation()
  const sp = data.spo2
  const asleep = sp.asleepAvg != null
  const scope = asleep ? t('insights.heart.scopeAsleep', 'While asleep') : t('insights.heart.scopeAll', 'All readings in this period')
  return (
    <div className="flex flex-col gap-3">
      {showTitle && <p className="text-body font-bold">{t('insights.heart.spo2', 'Blood oxygen (SpO2)')}</p>}
      <TileGrid>
        <Tile label={t('insights.heart.spo2Avg', 'Average, %')} value={num(asleep ? sp.asleepAvg : sp.avg, 1)} sub={scope} />
        <Tile label={t('insights.heart.spo2Low', 'Lowest, %')} value={num(asleep ? sp.asleepLow : sp.low, 1)} sub={scope} />
      </TileGrid>
      <p className="text-sub text-ink2">{t('insights.heart.spo2Note', 'A watch on the wrist is less accurate than a fingertip meter.')}</p>
    </div>
  )
}
