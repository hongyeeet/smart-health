/** C4 — Activity. Weekly goals, minutes by intensity for the last four weeks, the mix, workouts with the glucose change after them, and steps. */
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
  const noMinutes = !!data && data.weeks.every((w) => w.light + w.moderate + w.vigorous === 0)
  return (
    <InsightsFrame tab="C4" period={data?.period}>
      <Gate data={data} isError={isError} empty={!!data && !data.period.hasData} emptyText="Log a workout and your activity shows up here.">
        {data && (
          <Split>
            <div className="flex flex-col gap-4">
              <section className="flex flex-col gap-3">
                <SectionTitle>This week</SectionTitle>
                <Plain why="activity">Moderate or vigorous minutes, and strength sessions, against the weekly goals.</Plain>
                <Card tone="hero" className="grid grid-cols-2 gap-3">
                  <Ring value={data.moderateMin} goal={data.moderateGoal} label="Moderate or vigorous minutes" unit="minutes" caption="Active minutes" />
                  <Ring value={data.strength} goal={data.strengthGoal} label="Strength sessions" unit="sessions" caption="Strength" />
                </Card>
              </section>
              <section className="flex flex-col gap-3">
                <SectionTitle>Last 4 weeks</SectionTitle>
                <Card tone="hero">{noMinutes ? <p className="text-body text-ink2">No workouts logged in the last 4 weeks.</p> : <IntensityBars weeks={data.weeks} />}</Card>
              </section>
              {data.mix.length > 0 && (
                <section className="flex flex-col gap-1">
                  <SectionTitle>What you did</SectionTitle>
                  <div className="divide-y divide-line rounded-card border border-line bg-card px-4">
                    {data.mix.map((m) => (
                      <div key={m.type} className="flex items-baseline justify-between py-3 text-body">
                        <span className="font-bold">{m.label}</span>
                        <span className="num text-ink2">
                          {m.count} {m.count === 1 ? 'session' : 'sessions'}, {m.minutes} min
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
                  <SectionTitle>Recent workouts</SectionTitle>
                  <div className="divide-y divide-line rounded-card border border-line bg-card px-4">
                    {data.workouts.map((w) => (
                      <div key={w.id} className="flex items-baseline justify-between gap-3 py-3">
                        <span className="min-w-0">
                          <span className="block text-body font-bold">{w.label}</span>
                          <span className="block text-sub text-ink2">
                            {w.date}, {w.minutes} min, effort {w.intensity} of 5
                          </span>
                        </span>
                        {w.glucoseChange2h != null && (
                          <span className="num flex-none text-sub text-ink2">
                            {w.glucoseChange2h > 0 ? '+' : '−'}
                            {Math.abs(w.glucoseChange2h).toFixed(1)} mmol/L in 2 h
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}
              <section className="flex flex-col gap-3">
                <SectionTitle>Steps</SectionTitle>
                <Plain why="activity">
                  {data.stepsAvg != null ? `You averaged ${num(data.stepsAvg)} steps a day.` : 'No step data in this period.'}
                  {data.stepsAvg != null && data.stepsBaseline != null ? ` Your usual from the 60 days before is about ${num(data.stepsBaseline)}.` : ''}
                </Plain>
                {data.stepsAvg != null && (
                  <Card tone="hero">
                    <TrendChart label="Steps by day" points={data.steps.map((s) => ({ date: s.date, v: s.steps }))} format={(v) => num(v)} endLabel={shortDate(data.period.end)} drawKey={`steps-${days}`} color="var(--c-s2)" />
                  </Card>
                )}
                {data.stepsAvg != null && data.stepsBaseline != null && (
                  <div className="grid grid-cols-2 gap-2">
                    <Tile label="This period" value={num(data.stepsAvg)} unit="a day" />
                    <Tile label="Your usual" value={num(data.stepsBaseline)} unit="a day" />
                  </div>
                )}
              </section>
              <Findings items={data.patterns} />
              <Button icon={Barbell} onClick={() => go('F1')}>
                Log a workout
              </Button>
            </div>
          </Split>
        )}
      </Gate>
    </InsightsFrame>
  )
}
