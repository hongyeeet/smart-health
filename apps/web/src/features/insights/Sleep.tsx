/** C5 — Sleep and stress. Hours slept against the person's own usual, the mood and stress check-ins, and what their history shows. */
import { useTranslation } from 'react-i18next'
import { useInsightsSleep } from '@/data/hooks'
import { shortDate } from '@/lib/format'
import { MoodStress } from '@/charts/small'
import { TrendChart } from '@/charts/TrendChart'
import { Split } from '@/ui/layout'
import { Card, SectionTitle } from '@/ui/primitives'
import { Findings, Gate, InsightsFrame, Plain, Tile, num, useInsightsDays } from './shared'

export function SleepTab() {
  const days = useInsightsDays((s) => s.days)
  const { data, isError } = useInsightsSleep(days)
  const { t } = useTranslation()
  const checkins = (data?.days ?? []).flatMap((d) => (d.mood != null && d.stress != null ? [{ date: d.date, mood: d.mood, stress: d.stress }] : []))
  const hasSleep = !!data && data.sleepAvg != null
  return (
    <InsightsFrame tab="C5" period={data?.period}>
      <Gate data={data} isError={isError} empty={!!data && !data.period.hasData} emptyText={t('insights.sleep.empty', 'Log a mood and sleep check-in and your sleep and stress show up here.')}>
        {data && (
          <Split>
            <section className="flex flex-col gap-3">
              <SectionTitle>{t('insights.sleep.sleep', 'Sleep')}</SectionTitle>
              {hasSleep ? (
                <>
                  <Plain why="sleep">
                    {data.sleepBaseline != null
                      ? t('insights.sleep.avgWithBaseline', 'You slept {{avg}} hours a night on average. Your usual from the 60 days before is {{base}}.', {
                          avg: num(data.sleepAvg, 1),
                          base: num(data.sleepBaseline, 1),
                        })
                      : t('insights.sleep.avg', 'You slept {{avg}} hours a night on average.', { avg: num(data.sleepAvg, 1) })}{' '}
                    {data.shortNights === 1
                      ? t('insights.sleep.nightOne', '{{n}} night was under 6 hours.', { n: data.shortNights })
                      : t('insights.sleep.nightMany', '{{n}} nights were under 6 hours.', { n: data.shortNights })}
                  </Plain>
                  <Card tone="hero">
                    <TrendChart
                      label={t('insights.sleep.chart', 'Hours slept by night')}
                      points={data.days.map((d) => ({ date: d.date, v: d.hours }))}
                      format={(v) => `${Math.round(v * 10) / 10} h`}
                      endLabel={shortDate(data.period.end)}
                      drawKey={`sleep-${days}`}
                    />
                  </Card>
                  <div className="grid grid-cols-2 gap-2">
                    <Tile label={t('insights.sleep.averageSleep', 'Average sleep')} value={num(data.sleepAvg, 1)} unit={t('insights.sleep.hours', 'hours')} />
                    <Tile label={t('insights.sleep.nightsUnder6', 'Nights under 6 hours')} value={String(data.shortNights)} />
                  </div>
                </>
              ) : (
                <Card tone="soft">
                  <p className="text-body text-ink2">{t('insights.sleep.noSleep', 'No sleep data in this period. It comes from a connected watch.')}</p>
                </Card>
              )}
            </section>
            <div className="flex flex-col gap-4">
              <section className="flex flex-col gap-3">
                <SectionTitle>{t('insights.sleep.moodStress', 'Mood and stress')}</SectionTitle>
                {checkins.length > 0 ? (
                  <>
                    <Plain why="sleep">
                      {t('insights.sleep.stressPlain', 'Your stress rating averaged {{avg}} out of 5. It was 4 or 5 on {{high}} of {{logged}} days you checked in.', {
                        avg: num(data.stressAvg, 1),
                        high: data.highStressDays,
                        logged: data.loggedDays,
                      })}
                    </Plain>
                    <Card tone="hero">
                      <MoodStress data={checkins} label={t('insights.sleep.moodChart', 'Mood and stress check-ins, 1 to 5, {{n}} days', { n: checkins.length })} />
                    </Card>
                  </>
                ) : (
                  <Card tone="soft">
                    <p className="text-body text-ink2">{t('insights.sleep.noCheckins', 'No mood or stress check-ins in this period.')}</p>
                  </Card>
                )}
              </section>
              <Findings items={data.patterns} />
            </div>
          </Split>
        )}
      </Gate>
    </InsightsFrame>
  )
}
