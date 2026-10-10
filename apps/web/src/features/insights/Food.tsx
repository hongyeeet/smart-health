/** C3 — Food. What was eaten (salt and sugar flagged) and how each food moved glucose, gentlest to biggest rise. Foods seen once are not ranked. */
import { useState } from 'react'
import { motion } from 'motion/react'
import { useInsightsFood } from '@/data/hooks'
import { signed } from '@/lib/format'
import { ease } from '@/motion/tokens'
import { Split } from '@/ui/layout'
import { Button, Card, Chip, SectionTitle, StatusPill } from '@/ui/primitives'
import { Findings, Gate, InsightsFrame, Plain, Tile, num, useInsightsDays } from './shared'

type R = { name: string; n: number; medianRise: number; low: number; high: number }

function Bars({ rows, max }: { rows: R[]; max: number }) {
  return (
    <ul className="flex flex-col gap-3">
      {rows.map((f, i) => (
        <li key={f.name} className="flex flex-col gap-1.5">
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-body font-bold leading-snug">{f.name}</span>
            <span className="num flex-none text-h2">{signed(f.medianRise)}</span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-well" aria-hidden>
            <motion.div
              className={f.medianRise >= 3 ? 'h-full rounded-full bg-warn' : 'h-full rounded-full bg-brand'}
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(100, (f.medianRise / max) * 100)}%` }}
              transition={{ duration: 0.5, ease: ease.out, delay: i * 0.04 }}
            />
          </div>
          <p className="text-sub text-ink2">
            Seen {f.n} times, rise {f.low.toFixed(1)} to {f.high.toFixed(1)} mmol/L
          </p>
        </li>
      ))}
    </ul>
  )
}

export function FoodTab() {
  const days = useInsightsDays((s) => s.days)
  const { data, isError } = useInsightsFood(days)
  const [all, setAll] = useState(false)
  const r = data?.responses ?? []
  const max = Math.max(3, Math.ceil(Math.max(0, ...r.map((x) => x.medianRise))))
  const gentle = r.slice(0, 5)
  const spiky = r.length > 5 ? r.slice(-5).reverse() : []
  return (
    <InsightsFrame tab="C3" period={data?.period}>
      <Gate data={data} isError={isError} empty={!!data && data.totals.meals === 0} emptyText="Log a few meals and what you eat shows up here, with how each one moved your glucose.">
        {data && (
          <Split>
            <div className="flex flex-col gap-4">
              <section className="flex flex-col gap-3">
                <SectionTitle>What you ate</SectionTitle>
                <Plain why="food">
                  {data.totals.meals} meals logged. {data.totals.highSaltMeals} were high in salt and {data.totals.highSugarMeals} high in sugar.
                </Plain>
                <div className="grid grid-cols-2 gap-2">
                  <Tile label="Calories a day" value={num(data.totals.avgKcalPerDay)} unit="kcal" sub="from the meals you logged" />
                  <Tile label="Salt (sodium) a day" value={num(data.totals.avgSodiumPerDay)} unit="mg" sub="from the meals you logged" />
                </div>
              </section>
              <section className="flex flex-col gap-1">
                <SectionTitle>Recent meals</SectionTitle>
                <div className="divide-y divide-line rounded-card border border-line bg-card px-4">
                  {data.meals.map((m) => (
                    <div key={m.id} className="flex flex-col gap-1 py-3">
                      <div className="flex items-baseline justify-between gap-3">
                        <span className="text-body font-bold leading-snug">{m.name}</span>
                        {m.rise != null && <span className="num flex-none text-body">{signed(m.rise)} mmol/L</span>}
                      </div>
                      <p className="text-sub text-ink2">
                        {m.when}
                        {m.kcal != null ? `, ${m.kcal} kcal` : ''}
                        {m.sodiumMg != null ? `, ${Math.round(m.sodiumMg)} mg salt` : ''}
                      </p>
                      {m.flags.length > 0 && (
                        <div className="flex gap-2">
                          {m.flags.includes('high_salt') && <StatusPill tone="warn">High salt</StatusPill>}
                          {m.flags.includes('high_sugar') && <StatusPill tone="warn">High sugar</StatusPill>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            </div>
            <div className="flex flex-col gap-4">
              <section className="flex flex-col gap-3">
                <SectionTitle>How foods moved your glucose</SectionTitle>
                <Plain why="food">The rise in glucose in the 2 hours after each food, from your sensor. Gentlest first.</Plain>
                {r.length === 0 ? (
                  <Card tone="soft">
                    <p className="text-body text-ink2">A food needs to be logged at least twice, with the sensor on, before it is ranked here.</p>
                  </Card>
                ) : (
                  <Card tone="hero" className="flex flex-col gap-4">
                    <p className="text-sub font-bold text-ink3">{all ? 'All foods, gentlest first' : 'Gentlest on your glucose'}</p>
                    <Bars rows={all ? r : gentle} max={max} />
                    {!all && spiky.length > 0 && (
                      <>
                        <p className="text-sub font-bold text-ink3">Biggest rises</p>
                        <Bars rows={spiky} max={max} />
                      </>
                    )}
                    {r.length > 10 && (
                      <Button variant="secondary" onClick={() => setAll((v) => !v)}>
                        {all ? 'Show fewer' : `Show all ${r.length}`}
                      </Button>
                    )}
                  </Card>
                )}
                {data.stillLearning.length > 0 && (
                  <div className="flex flex-col gap-2">
                    <p className="text-sub text-ink2">Still learning (seen once, not ranked yet):</p>
                    <div className="flex flex-wrap gap-2">
                      {data.stillLearning.map((n) => (
                        <Chip key={n}>{n}</Chip>
                      ))}
                    </div>
                  </div>
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
