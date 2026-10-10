/** C6 — Medication. Day by day for each medicine, adherence for prescription medicines, why doses were missed, and the morning glucose beside it. */
import { useInsightsMedication } from '@/data/hooks'
import { shortDate } from '@/lib/format'
import { useGo } from '@/app/navigation'
import { TrendChart } from '@/charts/TrendChart'
import { Split } from '@/ui/layout'
import { Card, SectionTitle, TextLink } from '@/ui/primitives'
import { Pill } from '@/ui/icons'
import { Findings, Gate, InsightsFrame, Plain, useInsightsDays } from './shared'
import { DoseGrid } from './grids'

export function MedicationTab() {
  const days = useInsightsDays((s) => s.days)
  const { data, isError } = useInsightsMedication(days)
  const go = useGo()
  const totalMissed = data?.reasons.reduce((a, r) => a + r.count, 0) ?? 0
  const maxReason = Math.max(1, ...(data?.reasons.map((r) => r.count) ?? [1]))
  return (
    <InsightsFrame tab="C6" period={data?.period}>
      <Gate data={data} isError={isError} empty={!!data && data.meds.length === 0} emptyText="Add a medicine and your doses show up here, day by day.">
        {data && (
          <Split>
            <div className="flex flex-col gap-4">
              <section className="flex flex-col gap-3">
                <SectionTitle>Your doses</SectionTitle>
                <Plain why="medication">
                  {data.adherencePct != null
                    ? `You took ${data.adherencePct}% of your prescription doses (${data.taken} of ${data.scheduled}).${data.unconfirmed > 0 ? ` ${data.unconfirmed} ${data.unconfirmed === 1 ? 'was' : 'were'} not confirmed.` : ''}`
                    : 'There are no prescription doses to count in this period.'}
                  {data.shownDays < data.period.days ? ` The grid shows the last ${data.shownDays} days.` : ''}
                </Plain>
                <Card tone="hero">
                  <DoseGrid dates={data.dates} rows={data.meds} />
                </Card>
              </section>
              <section className="flex flex-col gap-1">
                <SectionTitle>Each medicine</SectionTitle>
                <div className="divide-y divide-line rounded-card border border-line bg-card px-4">
                  {data.meds.map((m) => (
                    <div key={m.id} className="flex items-baseline justify-between gap-3 py-3">
                      <span className="min-w-0">
                        <span className="block text-body font-bold">{m.name}</span>
                        <span className="block text-sub text-ink2">{m.regimen}</span>
                      </span>
                      <span className="num flex-none text-body">{m.adherencePct != null ? `${m.adherencePct}%` : '–'}</span>
                    </div>
                  ))}
                </div>
              </section>
              <TextLink icon={Pill} onClick={() => go('H1')}>
                Open my medicines
              </TextLink>
            </div>
            <div className="flex flex-col gap-4">
              {data.reasons.length > 0 && (
                <section className="flex flex-col gap-3">
                  <SectionTitle>Why doses were missed</SectionTitle>
                  <Plain why="medication">The reasons you gave for {totalMissed} missed doses.</Plain>
                  <Card tone="hero" className="flex flex-col gap-3">
                    {data.reasons.map((r) => (
                      <div key={r.key} className="flex flex-col gap-1">
                        <div className="flex items-baseline justify-between text-body">
                          <span className="font-bold">{r.label}</span>
                          <span className="num text-ink2">{r.count}</span>
                        </div>
                        <div className="h-3 overflow-hidden rounded-full bg-well" aria-hidden>
                          <div className="h-full rounded-full bg-brand" style={{ width: `${(r.count / maxReason) * 100}%` }} />
                        </div>
                      </div>
                    ))}
                  </Card>
                </section>
              )}
              {data.fasting.some((v) => v != null) && (
                <section className="flex flex-col gap-3">
                  <SectionTitle>Morning glucose over the same days</SectionTitle>
                  <Plain why="medication">
                    Your fasting glucose on the days shown in the grid, so you can look at the two side by side. Looking at them together does not show that one causes the other.
                  </Plain>
                  <Card tone="hero">
                    <TrendChart label="Fasting glucose by day, mmol/L" points={data.dates.map((d, i) => ({ date: d, v: data.fasting[i] ?? null }))} endLabel={shortDate(data.dates[data.dates.length - 1]!)} drawKey={`medfast-${days}`} />
                  </Card>
                </section>
              )}
              <Findings items={data.patterns} />
              <p className="text-sub text-ink3">Adherence counts prescription medicines only. A dose that was not answered is counted as not taken.</p>
            </div>
          </Split>
        )}
      </Gate>
    </InsightsFrame>
  )
}
