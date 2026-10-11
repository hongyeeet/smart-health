/** C6 — Medication. Day by day for each medicine, adherence for prescription medicines, and why doses were missed. */
import { useTranslation } from 'react-i18next'
import { useInsightsMedication } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { Split } from '@/ui/layout'
import { Card, SectionTitle, TextLink } from '@/ui/primitives'
import { Pill } from '@/ui/icons'
import { Findings, Gate, InsightsFrame, Plain, useInsightsDays } from './shared'
import { DoseGrid } from './grids'

export function MedicationTab() {
  const days = useInsightsDays((s) => s.days)
  const { data, isError } = useInsightsMedication(days)
  const go = useGo()
  const { t } = useTranslation()
  const totalMissed = data?.reasons.reduce((a, r) => a + r.count, 0) ?? 0
  const maxReason = Math.max(1, ...(data?.reasons.map((r) => r.count) ?? [1]))
  return (
    <InsightsFrame tab="C6" period={data?.period} why="medication">
      <Gate data={data} isError={isError} empty={!!data && data.meds.length === 0} emptyText={t('insights.medication.empty', 'Add a medicine and your doses show up here, day by day.')}>
        {data && (
          <>
            <section className="flex flex-col gap-3">
              <SectionTitle>{t('insights.medication.yourDoses', 'Your doses')}</SectionTitle>
              <Plain>
                {data.adherencePct != null
                  ? data.unconfirmed > 0
                    ? data.unconfirmed === 1
                      ? t('insights.medication.tookNotConfirmedOne', 'You took {{pct}}% of your prescription doses ({{taken}} of {{scheduled}}). {{n}} was not confirmed.', {
                          pct: data.adherencePct,
                          taken: data.taken,
                          scheduled: data.scheduled,
                          n: data.unconfirmed,
                        })
                      : t('insights.medication.tookNotConfirmedMany', 'You took {{pct}}% of your prescription doses ({{taken}} of {{scheduled}}). {{n}} were not confirmed.', {
                          pct: data.adherencePct,
                          taken: data.taken,
                          scheduled: data.scheduled,
                          n: data.unconfirmed,
                        })
                    : t('insights.medication.took', 'You took {{pct}}% of your prescription doses ({{taken}} of {{scheduled}}).', {
                        pct: data.adherencePct,
                        taken: data.taken,
                        scheduled: data.scheduled,
                      })
                  : data.unconfirmed > 0
                    ? t('insights.medication.notConfirmedYet', 'Not confirmed yet. {{n}} prescription doses are waiting for an answer.', { n: data.unconfirmed })
                    : t('insights.medication.noDoses', 'There are no prescription doses to count in this period.')}
                {data.shownDays < data.period.days && <> {t('insights.medication.gridShows', 'The grid shows the last {{n}} days.', { n: data.shownDays })}</>}
              </Plain>
              <Card tone="hero">
                <DoseGrid dates={data.dates} rows={data.meds} />
              </Card>
            </section>
            <Split>
            <div className="flex flex-col gap-4">
              <section className="flex flex-col gap-1">
                <SectionTitle>{t('insights.medication.eachMedicine', 'Each medicine')}</SectionTitle>
                <div className="divide-y divide-line rounded-card border border-line bg-card px-4">
                  {data.meds.map((m) => (
                    <div key={m.id} className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 py-3">
                      <span className="min-w-0">
                        <span className="block text-body font-bold">{m.name}</span>
                        <span className="block text-sub text-ink2">{m.regimen}</span>
                      </span>
                      <span className="max-w-full text-right">
                        {!m.counted ? (
                          <span className="block text-sub text-ink3">{t('insights.medication.notCounted', 'Not counted in adherence')}</span>
                        ) : m.adherencePct != null ? (
                          <span className="num block text-body">{`${m.adherencePct}%`}</span>
                        ) : (
                          <span className="block text-sub text-ink2">
                            <span className="num text-body">–</span> {t('insights.medication.notConfirmedYetShort', 'Not confirmed yet')}
                          </span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              </section>
              <TextLink icon={Pill} onClick={() => go('H1')}>
                {t('insights.medication.openMedicines', 'Open my medicines')}
              </TextLink>
            </div>
            <div className="flex flex-col gap-4">
              {data.reasons.length > 0 && (
                <section className="flex flex-col gap-3">
                  <SectionTitle>{t('insights.medication.whyMissed', 'Why doses were missed')}</SectionTitle>
                  <Plain>{t('insights.medication.reasons', 'The reasons you gave for {{n}} missed prescription doses.', { n: totalMissed })}</Plain>
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
              <Findings items={data.patterns} whyLink={false} />
              <p className="text-sub text-ink3">
                {t('insights.medication.adherenceNote', 'Adherence counts prescription medicines only. A dose that was not answered is counted as not taken.')}
              </p>
            </div>
            </Split>
          </>
        )}
      </Gate>
    </InsightsFrame>
  )
}
