/** C5 — Sleep and stress. Hours slept against the person's own usual, mood and stress check-ins, heart rate and SpO2, and blood pressure. */
import { useTranslation } from 'react-i18next'
import { useInsightsSleep } from '@/data/hooks'
import type { InsightsSleep } from '@/data/types'
import { shortDate } from '@/lib/format'
import { MoodStress } from '@/charts/small'
import { TrendChart } from '@/charts/TrendChart'
import { Split } from '@/ui/layout'
import { Alert, Card, SectionTitle, Skeleton, UnverifiedTag } from '@/ui/primitives'
import { InsightsFrame, Tile, TileGrid, num, useInsightsDays } from './shared'
import { HeartBlock } from './heart/HeartBlock'
import { BloodPressureCard } from './heart/BloodPressureCard'

export function SleepTab() {
  const days = useInsightsDays((s) => s.days)
  const { data, isError } = useInsightsSleep(days)
  return (
    <InsightsFrame tab="C5" period={data?.period} why="sleep">
      <Split>
        <div className="flex flex-col gap-4">
          <SleepSection data={data} isError={isError} />
          <HeartBlock days={days} />
        </div>
        <div className="flex flex-col gap-4">
          <MoodSection data={data} isError={isError} />
          <BloodPressureCard days={days} />
        </div>
      </Split>
    </InsightsFrame>
  )
}

function LoadError() {
  const { t } = useTranslation()
  return <Alert tone="warn">{t('insights.shared.loadError', 'We could not load this just now. Please try again in a moment.')}</Alert>
}

function SleepSection({ data, isError }: { data: InsightsSleep | undefined; isError: boolean }) {
  const { t } = useTranslation()
  if (isError) return <LoadError />
  if (!data) return <Skeleton className="h-64" />
  const hasSleep = data.sleepAvg != null
  return (
    <section className="flex flex-col gap-3">
      <SectionTitle>{t('insights.sleep.sleep', 'Sleep')}</SectionTitle>
      {hasSleep ? (
        <>
          <Card tone="hero">
            <TrendChart
              label={t('insights.sleep.chart', 'Hours slept by night')}
              points={data.days.map((d) => ({ date: d.date, v: d.hours }))}
              format={(v) => `${Math.round(v * 10) / 10} h`}
              endLabel={shortDate(data.period.end)}
              drawKey={`sleep-${data.period.days}`}
            />
          </Card>
          <TileGrid>
            <Tile label={t('insights.sleep.averageSleep', 'Average, hours')} value={num(data.sleepAvg, 1)} />
            <Tile label={t('insights.sleep.usual', 'Your usual, hours')} value={num(data.sleepBaseline, 1)} />
            <Tile className="col-span-2" label={t('insights.sleep.nightsUnder6', 'Nights under 6 hours')} value={String(data.shortNights)} />
          </TileGrid>
          {data.sleepBaseline != null && (
            <p className="text-sub text-ink3">{t('insights.sleep.usualNote', 'Your usual is the average of the 60 days before this period.')}</p>
          )}
        </>
      ) : (
        <Card tone="soft">
          <p className="text-body text-ink2">{t('insights.sleep.noSleep', 'No sleep data in this period. It comes from a connected watch.')}</p>
        </Card>
      )}
    </section>
  )
}

function MoodSection({ data, isError }: { data: InsightsSleep | undefined; isError: boolean }) {
  const { t } = useTranslation()
  if (isError) return <LoadError />
  if (!data) return <Skeleton className="h-64" />
  const checkins = data.days.flatMap((d) => (d.mood != null && d.stress != null ? [{ date: d.date, mood: d.mood, stress: d.stress }] : []))
  return (
    <section className="flex flex-col gap-3">
      <SectionTitle>{t('insights.sleep.moodStress', 'Mood and stress')}</SectionTitle>
      {checkins.length > 0 ? (
        <>
          <Card tone="hero">
            <MoodStress data={checkins} from={data.period.start} to={data.period.end} label={t('insights.sleep.moodChart', 'Mood and stress check-ins, 1 to 5, {{n}} days', { n: checkins.length })} />
          </Card>
          <p className="text-sub text-ink2">
            {t('insights.sleep.stressLine', 'Stress was 4 or 5 out of 5 on {{high}} of the {{logged}} days you checked in.', {
              high: data.highStressDays,
              logged: data.loggedDays,
            })}
          </p>
        </>
      ) : (
        <Card tone="soft">
          <p className="text-body text-ink2">{t('insights.sleep.noCheckins', 'No mood or stress check-ins in this period. Log one and it shows here.')}</p>
        </Card>
      )}
      {data.patterns.map((p) => (
        <Card key={p.key} className="flex flex-col gap-2">
          <p className="text-body">{p.text}</p>
          <div className="flex flex-wrap items-center gap-2">
            <UnverifiedTag />
            <span className="text-sub text-ink3">{t('insights.sleep.patternBasis', 'Associated with, not proven. Based on {{n}} matched events.', { n: p.n })}</span>
          </div>
        </Card>
      ))}
    </section>
  )
}
