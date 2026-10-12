/**
 * C6 — Medication. A month calendar of doses (a marker per medicine in every day), then why doses were missed beside what the person's
 * history shows, then the link to their medicines. There is no 7, 30 or 90 day choice: the person browses month by month, and the numbers
 * on the page are for the month on screen.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useInsightsMedication } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { Split } from '@/ui/layout'
import { Card, SectionTitle, TextLink } from '@/ui/primitives'
import { Pill } from '@/ui/icons'
import { Findings, Gate, InsightsFrame, Plain } from './shared'
import { DoseCalendar } from './DoseCalendar'
import { monthTitle } from './grids'

export function MedicationTab() {
  const [month, setMonth] = useState<string | undefined>(undefined)
  const { data, isError } = useInsightsMedication(month)
  const go = useGo()
  const { t } = useTranslation()
  const totalMissed = data?.reasons.reduce((a, r) => a + r.count, 0) ?? 0
  const maxReason = Math.max(1, ...(data?.reasons.map((r) => r.count) ?? [1]))
  // nothing at all on record (no month has a dose) is the only "empty" page; an empty month still shows the calendar so you can browse away from it
  const nothing = !!data && data.meds.length === 0 && !data.prevMonth && !data.nextMonth
  const when = data?.month ? monthTitle(data.month) : ''
  return (
    <InsightsFrame tab="C6" period={data?.period} why="medication" filter={false}>
      <Gate data={data} isError={isError} empty={nothing} emptyText={t('insights.medication.empty', 'Add a medicine and your doses show up here, day by day.')}>
        {data && (
          <div className="flex flex-col gap-4 lg:gap-6">
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
                    : t('insights.medication.noDosesMonth', 'There are no prescription doses to count in {{month}}.', { month: when })}
              </Plain>
              <Card tone="hero" className="!px-2 sm:!px-4">
                <DoseCalendar data={data} onMonth={setMonth} />
              </Card>
            </section>

            <Split>
              <section className="flex flex-col gap-3">
                <SectionTitle>{t('insights.medication.whyMissed', 'Why doses were missed')}</SectionTitle>
                {data.reasons.length > 0 ? (
                  <>
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
                  </>
                ) : (
                  <Plain>{t('insights.medication.noReasons', 'No reasons for missed prescription doses were given in {{month}}.', { month: when })}</Plain>
                )}
              </section>
              <div className="flex flex-col gap-3">
                <Findings items={data.patterns} whyLink={false} />
                <p className="text-sub text-ink3">
                  {t('insights.medication.adherenceNote', 'Adherence counts prescription medicines only. A dose that was not answered is counted as not taken.')}
                </p>
              </div>
            </Split>

            <TextLink icon={Pill} onClick={() => go('H1')}>
              {t('insights.medication.openMedicines', 'Open my medicines')}
            </TextLink>
          </div>
        )}
      </Gate>
    </InsightsFrame>
  )
}
