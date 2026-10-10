/**
 * K10 — How it is going.
 *
 * Week by week: meals logged, the average calories and salt of the meals the person logged, and how many doses were taken on time. The
 * first two weeks are set against the latest two. This is what the person did. It does not claim the app caused any change.
 */
import { Trans, useTranslation } from 'react-i18next'
import { useProgress } from '@/data/hooks'
import { Header, Screen, Split } from '@/ui/layout'
import { Alert, Card, EmptyState, SectionTitle, Skeleton } from '@/ui/primitives'
import { ChartLineUp, Info } from '@/ui/icons'

const week = (iso: string) => new Date(iso).toLocaleDateString('en-US', { day: 'numeric', month: 'short' })

function Row({ label, first, latest, unit, lowerIsBetter }: { label: string; first: number | null | undefined; latest: number | null | undefined; unit: string; lowerIsBetter?: boolean }) {
  const { t } = useTranslation()
  if (first == null || latest == null) return null
  const diff = latest - first
  const better = lowerIsBetter ? diff < 0 : diff > 0
  return (
    <div className="flex items-baseline justify-between gap-3 py-2">
      <span className="text-body">{label}</span>
      <span className="num text-body">
        <Trans
          i18nKey="me.progress.range"
          defaults="{{first}} <s>to</s> <b>{{latest}}</b> {{unit}}"
          values={{ first: Math.round(first).toLocaleString('en-US'), latest: Math.round(latest).toLocaleString('en-US'), unit }}
          components={{ s: <span className="text-ink3" />, b: <b /> }}
        />
        <span className={diff === 0 ? 'ml-2 text-sub text-ink3' : better ? 'ml-2 text-sub text-ok' : 'ml-2 text-sub text-ink2'}>
          {diff === 0 ? t('me.progress.same', 'same') : `${diff > 0 ? '+' : ''}${Math.round(diff).toLocaleString('en-US')}`}
        </span>
      </span>
    </div>
  )
}

export function Progress() {
  const { t } = useTranslation()
  const { data, isError } = useProgress()
  const max = Math.max(1, ...(data?.weeks.map((w) => w.avgKcal ?? 0) ?? [1]))
  return (
    <Screen>
      <Header title={t('me.progress.title', 'How it is going')} back backTo="K1" sub={t('me.progress.sub', 'Week by week, what you logged and did.')} />
      {isError && <Alert tone="warn">{t('me.progress.loadError', 'We could not load this just now.')}</Alert>}
      {!data && !isError && <Skeleton className="h-56" />}
      {data && data.weeks.length === 0 && <EmptyState icon={ChartLineUp}>{t('me.progress.empty', 'Log a few weeks of meals and your progress appears here.')}</EmptyState>}
      {data && data.weeks.length > 0 && (
        <Split>
          <section className="flex flex-col gap-3">
            <Card tone="hero" className="flex flex-col">
              <SectionTitle>{t('me.progress.compare', 'First two weeks against the latest two')}</SectionTitle>
              {data.compare ? (
                <div className="divide-y divide-line">
                  <Row label={t('me.progress.kcalPerMeal', 'Calories per meal you logged')} first={data.compare.avgKcal.first} latest={data.compare.avgKcal.latest} unit="kcal" lowerIsBetter />
                  <Row label={t('me.progress.saltPerMeal', 'Salt per meal you logged')} first={data.compare.avgSodium.first} latest={data.compare.avgSodium.latest} unit="mg" lowerIsBetter />
                  <Row label={t('me.progress.onTime', 'Doses taken on time')} first={data.compare.onTimePct.first} latest={data.compare.onTimePct.latest} unit="%" />
                </div>
              ) : (
                <p className="py-2 text-body text-ink2">
                  {t('me.progress.needWeeks', 'It needs at least 4 weeks with 5 or more meals logged each before it can compare. Keep logging.')}
                </p>
              )}
            </Card>
            <Alert tone="info" icon={Info}>
              {data.note}
            </Alert>
          </section>
          <section className="flex flex-col gap-1">
            <SectionTitle>{t('me.progress.eachWeek', 'Each week')}</SectionTitle>
            <div className="divide-y divide-line rounded-card border border-line bg-card px-4">
              {data.weeks.map((w) => (
                <div key={w.weekStart} className="flex flex-col gap-1.5 py-3">
                  <div className="flex items-baseline justify-between text-sub">
                    <span className="font-bold">{t('me.progress.weekOf', 'Week of {{date}}', { date: week(w.weekStart) })}</span>
                    <span className="num text-ink2">
                      {w.onTimePct != null
                        ? t('me.progress.mealsOnTime', '{{meals}} meals, {{pct}}% doses on time', { meals: w.meals, pct: w.onTimePct })
                        : t('me.progress.meals', '{{meals}} meals', { meals: w.meals })}
                    </span>
                  </div>
                  <div
                    className="h-2 overflow-hidden rounded-full bg-well"
                    role="img"
                    aria-label={t('me.progress.avgAria', 'Average {{kcal}} kcal per meal', { kcal: w.avgKcal ?? 0 })}
                  >
                    <div className="h-full rounded-full bg-brand" style={{ width: `${Math.round(((w.avgKcal ?? 0) / max) * 100)}%` }} />
                  </div>
                  <p className="text-micro text-ink3">
                    {w.avgKcal != null ? `${w.avgKcal.toLocaleString('en-US')} kcal` : ''}
                    {w.avgSodium != null ? t('me.progress.saltSuffix', ', {{mg}} mg salt per meal', { mg: w.avgSodium.toLocaleString('en-US') }) : ''}
                  </p>
                </div>
              ))}
            </div>
          </section>
        </Split>
      )}
    </Screen>
  )
}
