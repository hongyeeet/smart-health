/**
 * C8 — Glucose sensor sprint. A summary of the latest 14 days of sensor data: how many days it was worn, how steady the glucose was,
 * and which foods were gentlest and spikiest. A timed sprint with a start, a status and an end arrives with the sensor connection
 * (K4); until then this shows the most recent 14 days, and says so.
 */
import { useInsightsSprint } from '@/data/hooks'
import type { GlucoseLevel } from '@/data/types'
import { signed } from '@/lib/format'
import { useGo } from '@/app/navigation'
import { TirBar } from '@/charts/small'
import { Header, Screen, Split } from '@/ui/layout'
import { Alert, Card, EmptyState, SectionTitle, Skeleton, TextLink } from '@/ui/primitives'
import { Drop, ForkKnife } from '@/ui/icons'
import { Plain, Tile, num } from './shared'

const ORDER: GlucoseLevel[] = ['very_low', 'low', 'in_range', 'high', 'very_high']

function FoodList({ title, rows }: { title: string; rows: { name: string; medianRise: number; n: number }[] }) {
  if (!rows.length) return null
  return (
    <Card className="flex flex-col gap-2">
      <p className="text-sub font-bold text-ink3">{title}</p>
      {rows.map((f) => (
        <div key={f.name} className="flex items-baseline justify-between gap-3">
          <span className="text-body">{f.name}</span>
          <span className="num flex-none text-body">
            {signed(f.medianRise)} <span className="text-sub text-ink3">({f.n}x)</span>
          </span>
        </div>
      ))}
    </Card>
  )
}

export function Sprint() {
  const { data, isError } = useInsightsSprint()
  const go = useGo()
  return (
    <Screen>
      <Header title="Glucose sensor sprint" back backTo="C2" sub="Your latest 14 days of sensor data." />
      {isError && <Alert tone="warn">We could not load this just now. Please try again in a moment.</Alert>}
      {!data && !isError && <Skeleton className="h-64" />}
      {data && data.status === 'none' && <EmptyState icon={Drop}>No sensor readings yet. Once a glucose sensor is connected, a 14-day summary appears here.</EmptyState>}
      {data && data.status !== 'none' && (
        <Split>
          <section className="flex flex-col gap-3">
            <p className="text-sub text-ink3">{data.period.label}</p>
            <Plain why="sprint">
              The sensor was worn on {data.daysWorn} of {data.of} days.{data.status === 'partial' ? ' That is less than most of the period, so treat the numbers as a rough guide.' : ''}
            </Plain>
            <Card tone="hero">
              <TirBar segments={ORDER.map((k) => ({ level: k, pct: data.bands.find((b) => b.key === k)?.pct ?? 0 }))} />
            </Card>
            <div className="grid grid-cols-2 gap-2">
              <Tile label="Average" value={num(data.metrics.mean, 1)} unit="mmol/L" />
              <Tile label="Estimated A1c (GMI)" value={data.metrics.gmi != null ? `${num(data.metrics.gmi, 1)}%` : '–'} />
              <Tile label="Ups and downs (CV)" value={data.metrics.cv != null ? `${num(data.metrics.cv)}%` : '–'} sub="Lower is steadier" />
              <Tile label="Sensor worn" value={data.metrics.coverage != null ? `${num(data.metrics.coverage)}%` : '–'} />
            </div>
          </section>
          <section className="flex flex-col gap-3">
            <SectionTitle>Your foods in these 14 days</SectionTitle>
            <FoodList title="Gentlest on your glucose" rows={data.gentlest} />
            <FoodList title="Biggest rises" rows={data.spikiest} />
            {data.gentlest.length === 0 && (
              <Card tone="soft">
                <p className="text-body text-ink2">A food needs to be logged at least twice in these 14 days before it is ranked.</p>
              </Card>
            )}
            <TextLink icon={ForkKnife} onClick={() => go('C3')}>
              See all your foods
            </TextLink>
            <Alert tone="info">A timed sprint, with a start, a status and an end, comes with the sensor connection. Until then this shows your latest 14 days.</Alert>
          </section>
        </Split>
      )}
    </Screen>
  )
}
