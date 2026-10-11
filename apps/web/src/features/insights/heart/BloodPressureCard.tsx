/** Blood pressure the person logged by hand (C5). A small table of the newest readings: top, bottom and pulse. No judgement wording. */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useGo } from '@/app/navigation'
import { useInsightsBloodPressure } from '@/data/hooks'
import type { InsightsDays } from '@/data/types'
import { shortDate } from '@/lib/format'
import { Alert, Button, Card, SectionTitle, Skeleton } from '@/ui/primitives'
import { num } from '../shared'

const SHOW_FIRST = 5

export function BloodPressureCard({ days }: { days: InsightsDays }) {
  const { t } = useTranslation()
  const go = useGo()
  const { data, isError } = useInsightsBloodPressure(days)
  const [showAll, setShowAll] = useState(false)

  const logButton = (
    <Button variant="secondary" size="md" onClick={() => go('E3')}>
      {t('insights.bp.log', 'Log blood pressure')}
    </Button>
  )

  return (
    <section className="flex flex-col gap-3">
      <SectionTitle>{t('insights.bp.title', 'Blood pressure')}</SectionTitle>
      {isError ? (
        <Alert tone="warn">{t('insights.bp.error', 'We could not load blood pressure just now. Please try again in a moment.')}</Alert>
      ) : !data ? (
        <Skeleton className="h-40" />
      ) : data.count === 0 ? (
        <Card tone="soft" className="flex flex-col gap-3">
          <p className="text-body font-bold">{t('insights.bp.none', 'No blood pressure logged')}</p>
          <p className="text-sub text-ink2">{t('insights.bp.noneSub', 'Readings you log by hand show here.')}</p>
          {logButton}
        </Card>
      ) : (
        <Card tone="hero" className="flex flex-col gap-3">
          <p className="text-sub text-ink2">
            {t('insights.bp.count', '{{n}} readings in the last {{days}} days, in mmHg.', { n: num(data.count), days })}
            {data.count > data.readings.length && ' ' + t('insights.bp.newestOnly', 'The newest {{n}} are listed.', { n: data.readings.length })}
          </p>
          {data.latest && (
            <p className="text-sub font-bold text-ink2">{t('insights.bp.latest', 'Latest reading: {{date}}', { date: shortDate(data.latest) })}</p>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-body">
              <thead>
                <tr className="text-sub text-ink2">
                  <th scope="col" className="py-2 font-normal">{t('insights.bp.when', 'When')}</th>
                  <th scope="col" className="py-2 text-right font-normal">{t('insights.bp.top', 'Top')}</th>
                  <th scope="col" className="py-2 text-right font-normal">{t('insights.bp.bottom', 'Bottom')}</th>
                  <th scope="col" className="py-2 text-right font-normal">{t('insights.bp.pulse', 'Pulse')}</th>
                </tr>
              </thead>
              <tbody>
                {(showAll ? data.readings : data.readings.slice(0, SHOW_FIRST)).map((r, i) => (
                  <tr key={`${r.date}-${r.time}-${i}`} className="border-t border-line">
                    <td className="num py-2">{shortDate(r.date)}, {r.time}</td>
                    <td className="num py-2 text-right">{r.systolic}</td>
                    <td className="num py-2 text-right">{r.diastolic}</td>
                    <td className="num py-2 text-right">{r.pulse ?? '–'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.readings.length > SHOW_FIRST && (
            <button type="button" onClick={() => setShowAll((v) => !v)} className="press min-h-11 self-start rounded-chip px-2 text-sub font-bold text-brand">
              {showAll ? t('insights.bp.showFewer', 'Show fewer') : t('insights.bp.showAll', 'Show all {{n}}', { n: data.readings.length })}
            </button>
          )}
          {logButton}
        </Card>
      )}
    </section>
  )
}
