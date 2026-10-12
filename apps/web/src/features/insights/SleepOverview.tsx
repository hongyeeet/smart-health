/**
 * The first block of the Sleep and stress tab (C5): one card with four sections. Laptop: two rows of two — Sleep | Blood oxygen and heart
 * rate (from the watch), then Mood and stress | Blood pressure. Phone and tablet: one column in that order.
 */
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useInsightsBloodPressure, useInsightsHeart } from '@/data/hooks'
import type { InsightsDays, InsightsSleep } from '@/data/types'
import { shortDate } from '@/lib/format'
import { TrendChart } from '@/charts/TrendChart'
import { cn } from '@/lib/cn'
import { Card, SectionTitle, Skeleton } from '@/ui/primitives'
import { Plain, Tile, TileGrid, num } from './shared'
import { HeartPanel, Spo2Panel } from './heart/HeartBlock'
import { BloodPressureChart } from './heart/BloodPressureChart'
import { MoodStressChart } from './MoodStressChart'

function Section({ title, className, children, sectionRef }: { title: string; className?: string; children: ReactNode; sectionRef?: React.Ref<HTMLElement> }) {
  return (
    <section ref={sectionRef} className={cn('flex min-w-0 flex-col gap-3', className)}>
      <SectionTitle>{title}</SectionTitle>
      {children}
    </section>
  )
}

/**
 * On a laptop a chart grows to fill the row beside a taller section, up to a limit, so there is no big empty gap under it. `header` is the
 * height of everything in its own section except the chart. Returns the height to give the chart and a ref for the taller section it is
 * matched to. Below a laptop width the chart keeps its usual height.
 */
function useMatchedHeight(loaded: unknown, header: number, usual: number, max: number) {
  const ref = useRef<HTMLElement>(null)
  const [h, setH] = useState(usual)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const fit = () => setH(window.matchMedia('(min-width: 1024px)').matches ? Math.min(Math.max(usual, el.offsetHeight - header), max) : usual)
    fit()
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(fit) : null
    ro?.observe(el)
    window.addEventListener('resize', fit)
    return () => {
      ro?.disconnect()
      window.removeEventListener('resize', fit)
    }
    // `loaded` changes when the data arrives and the section grows: measure again then, whether or not the observer fires
  }, [loaded, header, usual, max])
  return [h, ref] as const
}

function MoodStressSection({ data }: { data: InsightsSleep }) {
  const { t } = useTranslation()
  const days = data.days.map((d) => ({ date: d.date, mood: d.mood, stress: d.stress }))
  if (!days.some((d) => d.mood != null || d.stress != null))
    return <Plain>{t('insights.sleep.noCheckins', 'No mood or stress check-ins in this period. Log one and it shows here.')}</Plain>
  const avg = (n: number | null) => (n != null ? num(n, 1) : '–')
  return (
    <>
      <p className="text-body text-ink">
        {t('insights.sleep.moodStressAvg', 'Mood averaged {{mood}} and stress {{stress}} out of 5.', { mood: avg(data.moodAvg), stress: avg(data.stressAvg) })}
      </p>
      <MoodStressChart days={days} label={t('insights.sleep.moodStressLabel', 'Mood and stress check-ins by day, 1 to 5')} />
      <p className="text-sub text-ink3">{t('insights.sleep.scaleNote', '1 is the lowest and 5 the highest, as you rated it.')}</p>
      <Plain>
        {t('insights.sleep.stressLine', 'Stress was 4 or 5 out of 5 on {{high}} of the {{logged}} days you checked in.', { high: data.highStressDays, logged: data.loggedDays })}
      </Plain>
    </>
  )
}

export function SleepOverview({ data, days }: { data: InsightsSleep; days: InsightsDays }) {
  const { t } = useTranslation()
  const heart = useInsightsHeart(days)
  const bp = useInsightsBloodPressure(days)
  const [sleepH, watchRef] = useMatchedHeight(heart.data, 207, 168, 520)
  const [bpH, moodRef] = useMatchedHeight(bp.data, 164, 176, 360)
  return (
    <Card tone="hero" className="flex flex-col gap-5 lg:grid lg:grid-cols-2 lg:items-start lg:gap-x-0 lg:gap-y-0">
      <Section title={t('insights.sleep.sleep', 'Sleep')} className="lg:pb-6 lg:pr-8">
        {data.sleepAvg != null ? (
          <>
            <TileGrid>
              <Tile label={t('insights.sleep.averageSleep', 'Average, hours')} value={num(data.sleepAvg, 1)} />
              <Tile label={t('insights.sleep.nightsUnder6', 'Nights under 6 hours')} value={String(data.shortNights)} />
            </TileGrid>
            <TrendChart
              label={t('insights.sleep.chart', 'Hours slept by night')}
              points={data.days.map((d) => ({ date: d.date, v: d.hours }))}
              format={(v) => `${Math.round(v * 10) / 10} h`}
              endLabel={shortDate(data.period.end)}
              drawKey={`sleep-${data.period.days}`}
              height={sleepH}
            />
          </>
        ) : (
          <Plain>{t('insights.sleep.noSleep', 'No sleep data in this period. It comes from a connected watch.')}</Plain>
        )}
      </Section>

      <Section sectionRef={watchRef} title={t('insights.sleep.watch', 'Watch readings')} className="border-t border-line pt-5 lg:border-l lg:border-t-0 lg:pb-6 lg:pl-8 lg:pt-0">
        {heart.isError ? (
          <Plain>{t('insights.heart.error', 'We could not load heart rate just now. Please try again in a moment.')}</Plain>
        ) : !heart.data ? (
          <Skeleton className="h-56" />
        ) : !heart.data.hasData ? (
          <Plain>{t('insights.heart.noWatchSub', 'Heart rate and SpO2 come from a connected watch.')}</Plain>
        ) : (
          <>
            <Spo2Panel data={heart.data} />
            <div className="border-t border-line pt-4">
              <HeartPanel data={heart.data} showTitle />
            </div>
          </>
        )}
      </Section>

      <Section sectionRef={moodRef} title={t('insights.sleep.moodStress', 'Mood and stress')} className="border-t border-line pt-5 lg:pr-8">
        <MoodStressSection data={data} />
      </Section>

      <Section title={t('insights.bp.title', 'Blood pressure')} className="border-t border-line pt-5 lg:border-l lg:pl-8">
        {bp.isError ? (
          <Plain>{t('insights.bp.error', 'We could not load blood pressure just now. Please try again in a moment.')}</Plain>
        ) : !bp.data ? (
          <Skeleton className="h-48" />
        ) : bp.data.count === 0 ? (
          <Plain>{t('insights.bp.noneSub', 'Readings you log by hand show here.')}</Plain>
        ) : (
          <>
            <p className="text-body text-ink">{t('insights.bp.count', '{{n}} readings in the last {{days}} days, in mmHg.', { n: num(bp.data.count), days })}</p>
            <BloodPressureChart height={bpH} readings={bp.data.readings} from={data.period.start} to={data.period.end} label={t('insights.bp.chartLabel', 'Blood pressure readings: top and bottom number for each reading')} />
          </>
        )}
      </Section>
    </Card>
  )
}
