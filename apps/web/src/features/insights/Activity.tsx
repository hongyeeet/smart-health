/** C4 — Activity. Weekly goals, minutes by intensity for the last four weeks, the mix, workouts with the glucose change after them, and steps. */
import { useTranslation } from 'react-i18next'
import { useInsightsActivity } from '@/data/hooks'
import { shortDate } from '@/lib/format'
import { useGo } from '@/app/navigation'
import { IntensityBars, Ring } from '@/charts/small'
import { TrendChart } from '@/charts/TrendChart'
import { Split } from '@/ui/layout'
import { Button, Card, SectionTitle } from '@/ui/primitives'
import { Barbell } from '@/ui/icons'
import { Findings, Gate, InsightsFrame, Plain, Tile, num, useInsightsDays } from './shared'

export function ActivityTab() {
  const days = useInsightsDays((s) => s.days)
  const { data, isError } = useInsightsActivity(days)
  const go = useGo()
  const { t } = useTranslation()
  const noMinutes = !!data && data.weeks.every((w) => w.light + w.moderate + w.vigorous === 0)
  return (
    <InsightsFrame tab="C4" period={data?.period}>
      <Gate data={data} isError={isError} empty={!!data && !data.period.hasData} emptyText={t('insights.activity.empty', 'Log a workout and your activity shows up here.')}>
        {data && (
          <Split>
            <div className="flex flex-col gap-4">
              <section className="flex flex-col gap-3">
                <SectionTitle>{t('insights.activity.thisWeek', 'This week')}</SectionTitle>
                <Plain why="activity">{t('insights.activity.weekPlain', 'Moderate or vigorous minutes, and strength sessions, against the weekly goals.')}</Plain>
                <Card tone="hero" className="grid grid-cols-2 gap-3">
                  <Ring
                    value={data.moderateMin}
                    goal={data.moderateGoal}
                    label={t('insights.activity.ringMinutes', 'Moderate or vigorous minutes')}
                    unit={t('insights.activity.unitMinutes', 'minutes')}
                    caption={t('insights.activity.captionActive', 'Active minutes')}
                  />
                  <Ring
                    value={data.strength}
                    goal={data.strengthGoal}
                    label={t('insights.activity.ringStrength', 'Strength sessions')}
                    unit={t('insights.activity.unitSessions', 'sessions')}
                    caption={t('insights.activity.captionStrength', 'Strength')}
                  />
                </Card>
              </section>
              <section className="flex flex-col gap-3">
                <SectionTitle>{t('insights.activity.last4', 'Last 4 weeks')}</SectionTitle>
                <Card tone="hero">
                  {noMinutes ? <p className="text-body text-ink2">{t('insights.activity.noWorkouts4', 'No workouts logged in the last 4 weeks.')}</p> : <IntensityBars weeks={data.weeks} />}
                </Card>
              </section>
              {data.mix.length > 0 && (
                <section className="flex flex-col gap-1">
                  <SectionTitle>{t('insights.activity.whatYouDid', 'What you did')}</SectionTitle>
                  <div className="divide-y divide-line rounded-card border border-line bg-card px-4">
                    {data.mix.map((m) => (
                      <div key={m.type} className="flex items-baseline justify-between py-3 text-body">
                        <span className="font-bold">{m.label}</span>
                        <span className="num text-ink2">
                          {m.count === 1
                            ? t('insights.activity.mixOne', '{{n}} session, {{min}} min', { n: m.count, min: m.minutes })
                            : t('insights.activity.mixMany', '{{n}} sessions, {{min}} min', { n: m.count, min: m.minutes })}
                        </span>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </div>
            <div className="flex flex-col gap-4">
              {data.workouts.length > 0 && (
                <section className="flex flex-col gap-1">
                  <SectionTitle>{t('insights.activity.recentWorkouts', 'Recent workouts')}</SectionTitle>
                  <div className="divide-y divide-line rounded-card border border-line bg-card px-4">
                    {data.workouts.map((w) => (
                      <div key={w.id} className="flex items-baseline justify-between gap-3 py-3">
                        <span className="min-w-0">
                          <span className="block text-body font-bold">{w.label}</span>
                          <span className="block text-sub text-ink2">
                            {t('insights.activity.workoutLine', '{{date}}, {{min}} min, effort {{effort}} of 5', { date: w.date, min: w.minutes, effort: w.intensity })}
                          </span>
                        </span>
                        {w.glucoseChange2h != null && (
                          <span className="num flex-none text-sub text-ink2">
                            {t('insights.activity.glucoseChange', '{{sign}}{{n}} mmol/L in 2 h', {
                              sign: w.glucoseChange2h > 0 ? '+' : '−',
                              n: Math.abs(w.glucoseChange2h).toFixed(1),
                            })}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}
              <section className="flex flex-col gap-3">
                <SectionTitle>{t('insights.activity.steps', 'Steps')}</SectionTitle>
                <Plain why="activity">
                  {data.stepsAvg != null && data.stepsBaseline != null
                    ? t('insights.activity.stepsBoth', 'You averaged {{avg}} steps a day. Your usual from the 60 days before is about {{base}}.', {
                        avg: num(data.stepsAvg),
                        base: num(data.stepsBaseline),
                      })
                    : data.stepsAvg != null
                      ? t('insights.activity.stepsAvg', 'You averaged {{avg}} steps a day.', { avg: num(data.stepsAvg) })
                      : t('insights.activity.noSteps', 'No step data in this period.')}
                </Plain>
                {data.stepsAvg != null && (
                  <Card tone="hero">
                    <TrendChart
                      label={t('insights.activity.stepsChart', 'Steps by day')}
                      points={data.steps.map((s) => ({ date: s.date, v: s.steps }))}
                      format={(v) => num(v)}
                      endLabel={shortDate(data.period.end)}
                      drawKey={`steps-${days}`}
                      color="var(--c-s2)"
                    />
                  </Card>
                )}
                {data.stepsAvg != null && data.stepsBaseline != null && (
                  <div className="grid grid-cols-2 gap-2">
                    <Tile label={t('insights.activity.thisPeriod', 'This period')} value={num(data.stepsAvg)} unit={t('insights.activity.aDay', 'a day')} />
                    <Tile label={t('insights.activity.yourUsual', 'Your usual')} value={num(data.stepsBaseline)} unit={t('insights.activity.aDay', 'a day')} />
                  </div>
                )}
              </section>
              <Findings items={data.patterns} />
              <Button icon={Barbell} onClick={() => go('F1')}>
                {t('insights.activity.logWorkout', 'Log a workout')}
              </Button>
            </div>
          </Split>
        )}
      </Gate>
    </InsightsFrame>
  )
}
