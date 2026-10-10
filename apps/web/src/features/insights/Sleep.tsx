/** C5 — Sleep and stress. Hours slept against the person's own usual, the mood and stress check-ins, and what their history shows. */
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
  const checkins = (data?.days ?? []).flatMap((d) => (d.mood != null && d.stress != null ? [{ date: d.date, mood: d.mood, stress: d.stress }] : []))
  const hasSleep = !!data && data.sleepAvg != null
  return (
    <InsightsFrame tab="C5" period={data?.period}>
      <Gate data={data} isError={isError} empty={!!data && !data.period.hasData} emptyText="Log a mood and sleep check-in and your sleep and stress show up here.">
        {data && (
          <Split>
            <section className="flex flex-col gap-3">
              <SectionTitle>Sleep</SectionTitle>
              {hasSleep ? (
                <>
                  <Plain why="sleep">
                    You slept {num(data.sleepAvg, 1)} hours a night on average.
                    {data.sleepBaseline != null ? ` Your usual from the 60 days before is ${num(data.sleepBaseline, 1)}.` : ''} {data.shortNights} {data.shortNights === 1 ? 'night was' : 'nights were'} under 6 hours.
                  </Plain>
                  <Card tone="hero">
                    <TrendChart
                      label="Hours slept by night"
                      points={data.days.map((d) => ({ date: d.date, v: d.hours }))}
                      format={(v) => `${Math.round(v * 10) / 10} h`}
                      endLabel={shortDate(data.period.end)}
                      drawKey={`sleep-${days}`}
                    />
                  </Card>
                  <div className="grid grid-cols-2 gap-2">
                    <Tile label="Average sleep" value={num(data.sleepAvg, 1)} unit="hours" />
                    <Tile label="Nights under 6 hours" value={String(data.shortNights)} />
                  </div>
                </>
              ) : (
                <Card tone="soft">
                  <p className="text-body text-ink2">No sleep data in this period. It comes from a connected watch.</p>
                </Card>
              )}
            </section>
            <div className="flex flex-col gap-4">
              <section className="flex flex-col gap-3">
                <SectionTitle>Mood and stress</SectionTitle>
                {checkins.length > 0 ? (
                  <>
                    <Plain why="sleep">
                      Your stress rating averaged {num(data.stressAvg, 1)} out of 5. It was 4 or 5 on {data.highStressDays} of {data.loggedDays} days you checked in.
                    </Plain>
                    <Card tone="hero">
                      <MoodStress data={checkins} label={`Mood and stress check-ins, 1 to 5, ${checkins.length} days`} />
                    </Card>
                  </>
                ) : (
                  <Card tone="soft">
                    <p className="text-body text-ink2">No mood or stress check-ins in this period.</p>
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
