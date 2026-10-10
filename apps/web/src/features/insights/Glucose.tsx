/** C2 — Glucose. Time in range, the usual morning (fasting) level and whether it has drifted, and how steady the day is. From the sensor only. */
import { useInsightsGlucose } from '@/data/hooks'
import type { GlucoseLevel } from '@/data/types'
import { shortDate } from '@/lib/format'
import { useGo } from '@/app/navigation'
import { TirBar } from '@/charts/small'
import { TrendChart } from '@/charts/TrendChart'
import { Split } from '@/ui/layout'
import { Alert, Card, SectionTitle, TextLink } from '@/ui/primitives'
import { Drop } from '@/ui/icons'
import { Findings, Gate, InsightsFrame, Plain, Tile, num, useInsightsDays } from './shared'

const ORDER: GlucoseLevel[] = ['very_low', 'low', 'in_range', 'high', 'very_high']

export function GlucoseTab() {
  const days = useInsightsDays((s) => s.days)
  const { data, isError } = useInsightsGlucose(days)
  const go = useGo()
  const inRange = data?.bands.find((b) => b.key === 'in_range')?.pct
  const segments = data ? ORDER.map((k) => ({ level: k, pct: data.bands.find((b) => b.key === k)?.pct ?? 0 })) : []
  const end = data ? shortDate(data.period.end) : ''
  return (
    <InsightsFrame tab="C2" period={data?.period}>
      <Gate data={data} isError={isError} empty={!!data && !data.hasData} emptyText="There are no sensor readings in this period. Once a glucose sensor is connected, your readings appear here.">
        {data && (
          <Split>
            <div className="flex flex-col gap-4">
              <section className="flex flex-col gap-3">
                <SectionTitle>Time in range</SectionTitle>
                <Plain why="glucose">{inRange != null ? `${Math.round(inRange)}% of your readings were between ${data.low} and ${data.high} mmol/L.` : ''}</Plain>
                <Card tone="hero">
                  <TirBar segments={segments} />
                </Card>
                <div className="grid grid-cols-2 gap-2">
                  <Tile label="Average" value={num(data.metrics.mean, 1)} unit="mmol/L" />
                  <Tile label="Estimated A1c (GMI)" value={data.metrics.gmi != null ? `${num(data.metrics.gmi, 1)}%` : '–'} sub="Worked out from your average" />
                  <Tile label="Ups and downs (CV)" value={data.metrics.cv != null ? `${num(data.metrics.cv)}%` : '–'} sub="Lower is steadier" />
                  <Tile label="Sensor worn" value={data.metrics.coverage != null ? `${num(data.metrics.coverage)}%` : '–'} sub="of this period" />
                </div>
              </section>
              <Card tone="soft" className="flex flex-col gap-1">
                <p className="text-body font-bold">In this period</p>
                <p className="text-body text-ink2">
                  {data.events.spikes} sharp rises, {data.events.sustainedHigh} long stretches above range, {data.events.lows} low readings.
                </p>
              </Card>
              <TextLink icon={Drop} onClick={() => go('C8')}>
                See your latest 14 days of sensor data
              </TextLink>
            </div>
            <div className="flex flex-col gap-4">
              <section className="flex flex-col gap-3">
                <SectionTitle>Morning (fasting) glucose</SectionTitle>
                <Plain why="glucose">
                  The average of your readings between 5 and 7 am each day.{data.baseline ? ' The shaded band is your usual range from the 60 days before.' : ''}
                </Plain>
                {data.drift && <Alert tone="info">{data.drift.text} Worth mentioning to your doctor.</Alert>}
                <Card tone="hero">
                  <TrendChart
                    label="Morning fasting glucose by day, mmol/L"
                    points={data.days.map((d) => ({ date: d.date, v: d.fasting }))}
                    baseline={data.baseline ? [data.baseline.p25, data.baseline.p75] : undefined}
                    endLabel={end}
                    drawKey={`fasting-${days}`}
                  />
                </Card>
              </section>
              <section className="flex flex-col gap-3">
                <SectionTitle>Average each day</SectionTitle>
                <Card tone="hero">
                  <TrendChart label="Average glucose by day, mmol/L" points={data.days.map((d) => ({ date: d.date, v: d.mean }))} endLabel={end} color="var(--c-s2)" drawKey={`mean-${days}`} />
                </Card>
              </section>
              <Findings items={data.patterns} />
            </div>
          </Split>
        )}
      </Gate>
    </InsightsFrame>
  )
}
