/**
 * The first block of the Activity tab (C4): one card with four visuals — Steps, What you did, Heart rate, Blood oxygen.
 * Phone: one column in that order. Laptop: two columns, steps and heart rate (the two charts) on top, the two small ones below.
 */
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useInsightsHeart } from '@/data/hooks'
import type { InsightsActivity, InsightsDays } from '@/data/types'
import { shortDate } from '@/lib/format'
import { TrendChart } from '@/charts/TrendChart'
import { cn } from '@/lib/cn'
import { Card, SectionTitle, Skeleton } from '@/ui/primitives'
import { Plain, num } from './shared'
import { HeartPanel, Spo2Panel } from './heart/HeartBlock'

/** One of the four sections: a hairline above it on a phone; on a laptop the bottom row has one and the right column a rule on its left. */
function Section({ title, className, children }: { title: string; className?: string; children: ReactNode }) {
  return (
    <section className={cn('flex min-w-0 flex-col gap-3 border-t border-line pt-5 first:border-t-0 first:pt-0', className)}>
      <SectionTitle>{title}</SectionTitle>
      {children}
    </section>
  )
}

/** "This period 7,036 a day  vs  Your usual 7,797 a day" as one visual. */
function StepsCompare({ avg, usual }: { avg: number; usual: number }) {
  const { t } = useTranslation()
  const unit = t('insights.activity.aDay', 'a day')
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-card border border-line bg-card p-3 [[data-ts='2']_&]:max-lg:flex-col [[data-ts='2']_&]:max-lg:items-start">
      <span className="sr-only">
        {t('insights.activity.stepsCompareSr', 'This period {{avg}} steps a day, against your usual {{usual}} a day.', { avg: num(avg), usual: num(usual) })}
      </span>
      <div className="min-w-0 flex-1 basis-28" aria-hidden>
        <span className="block text-sub text-ink2">{t('insights.activity.thisPeriod', 'This period')}</span>
        <span className="num whitespace-nowrap text-xl leading-tight">
          {num(avg)}
          <span className="ml-1 text-sub text-ink3">{unit}</span>
        </span>
      </div>
      <span className="flex-none text-sub font-bold uppercase tracking-wide text-ink3" aria-hidden>
        {t('insights.activity.vs', 'vs')}
      </span>
      <div className="min-w-0 flex-1 basis-28" aria-hidden>
        <span className="block text-sub text-ink2">{t('insights.activity.yourUsual', 'Your usual')}</span>
        <span className="num whitespace-nowrap text-xl leading-tight">
          {num(usual)}
          <span className="ml-1 text-sub text-ink3">{unit}</span>
        </span>
      </div>
    </div>
  )
}

export function ActivityOverview({ data, days }: { data: InsightsActivity; days: InsightsDays }) {
  const { t } = useTranslation()
  const heart = useInsightsHeart(days)
  const hasSteps = data.stepsAvg != null
  return (
    <Card tone="hero" className="grid gap-5 lg:grid-cols-2 lg:gap-x-8 lg:gap-y-0">
      <Section title={t('insights.activity.steps', 'Steps')} className="lg:order-1 lg:border-t-0 lg:pb-6 lg:pt-0">
        {hasSteps ? (
          <>
            <TrendChart
              label={t('insights.activity.stepsChart', 'Steps by day')}
              points={data.steps.map((s) => ({ date: s.date, v: s.steps }))}
              format={(v) => num(v)}
              endLabel={shortDate(data.period.end)}
              drawKey={`steps-${days}`}
              color="var(--c-s2)"
            />
            {data.stepsBaseline != null ? (
              <>
                <StepsCompare avg={data.stepsAvg!} usual={data.stepsBaseline} />
                <p className="text-sub text-ink3">{t('insights.activity.usualNote', 'Your usual is from the 60 days before this period.')}</p>
              </>
            ) : (
              <Plain>{t('insights.activity.stepsAvg', 'You averaged {{avg}} steps a day.', { avg: num(data.stepsAvg) })}</Plain>
            )}
          </>
        ) : (
          <Plain>{t('insights.activity.noSteps', 'No step data in this period.')}</Plain>
        )}
      </Section>

      <Section title={t('insights.activity.whatYouDid', 'What you did')} className="lg:order-3">
        {data.mix.length === 0 ? (
          <Plain>{t('insights.activity.noMix', 'No workouts logged in this period.')}</Plain>
        ) : (
          <div className="divide-y divide-line">
            {data.mix.map((m) => (
              <div key={m.type} className="flex items-baseline justify-between gap-3 py-2.5 text-body first:pt-0 last:pb-0">
                <span className="font-bold">{m.label}</span>
                <span className="num text-right text-ink2">
                  {m.count === 1
                    ? t('insights.activity.mixOne', '{{n}} session, {{min}} min', { n: m.count, min: m.minutes })
                    : t('insights.activity.mixMany', '{{n}} sessions, {{min}} min', { n: m.count, min: m.minutes })}
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title={t('insights.activity.heartTitle', 'Heart rate')} className="lg:order-2 lg:border-l lg:border-t-0 lg:pb-6 lg:pl-8 lg:pt-0">
        {heart.isError ? (
          <Plain>{t('insights.heart.error', 'We could not load heart rate just now. Please try again in a moment.')}</Plain>
        ) : !heart.data ? (
          <Skeleton className="h-56" />
        ) : !heart.data.hasData ? (
          <Plain>{t('insights.heart.noWatchSub', 'Heart rate and SpO2 come from a connected watch.')}</Plain>
        ) : (
          <HeartPanel data={heart.data} />
        )}
      </Section>

      <Section title={t('insights.heart.spo2', 'Blood oxygen (SpO2)')} className="lg:order-4 lg:border-l lg:pl-8">
        {heart.isError ? null : !heart.data ? (
          <Skeleton className="h-28" />
        ) : !heart.data.hasData ? (
          <Plain>{t('insights.heart.noWatchSub', 'Heart rate and SpO2 come from a connected watch.')}</Plain>
        ) : (
          <Spo2Panel data={heart.data} showTitle={false} />
        )}
      </Section>
    </Card>
  )
}
