/** C1 — Overview. The last seven days at a glance, what moved against the days before, and what the person's own history shows. */
import { useTranslation } from 'react-i18next'
import { useInsightsOverview } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { Split } from '@/ui/layout'
import { Card, SectionTitle } from '@/ui/primitives'
import { CaretRight } from '@/ui/icons'
import { Findings, Gate, InsightsFrame, Plain, useInsightsDays } from './shared'
import { WeekGrid } from './grids'

export function Overview() {
  const days = useInsightsDays((s) => s.days)
  const { data, isError } = useInsightsOverview(days)
  const go = useGo()
  const { t } = useTranslation()
  return (
    <InsightsFrame tab="C1" period={data?.period}>
      <Gate data={data} isError={isError} empty={!!data && !data.period.hasData} emptyText={t('insights.overview.empty', 'Log a few meals, a workout or a check-in and your week fills in here.')}>
        {data && (
          <Split>
            <section className="flex flex-col gap-3">
              <SectionTitle>{t('insights.overview.yourWeek', 'Your week')}</SectionTitle>
              <Plain why="week">{t('insights.overview.weekPlain', 'The last 7 days of your data, one square per day.')}</Plain>
              <Card tone="hero">
                <WeekGrid rows={data.grid} />
              </Card>
            </section>
            <div className="flex flex-col gap-4">
              <section className="flex flex-col gap-2">
                <SectionTitle>{t('insights.overview.whatChanged', 'What changed')}</SectionTitle>
                {data.changes.length === 0 ? (
                  <Card tone="soft">
                    <p className="text-body text-ink2">{t('insights.overview.nothingMoved', 'Nothing moved much compared with the {{days}} days before.', { days })}</p>
                  </Card>
                ) : (
                  data.changes.map((c) => (
                    <Card key={c.id} onClick={() => go(c.to)} className="flex items-center gap-3">
                      <span className="flex-1 text-body">{c.text}</span>
                      <CaretRight size={20} className="flex-none text-ink3" aria-hidden />
                    </Card>
                  ))
                )}
              </section>
              <Findings items={data.patterns} onOpen={(to) => go(to)} />
            </div>
          </Split>
        )}
      </Gate>
    </InsightsFrame>
  )
}
