/** K10 baseline: one card with the first two full weeks (calories and salt per meal, and the on-time share of doses). Not a score. */
import { useTranslation } from 'react-i18next'
import type { Progress } from '@/data/types'
import { shortDate } from '@/lib/format'
import { Card, SectionTitle } from '@/ui/primitives'

function Row({ label, value, sub }: { label: string; value: string | null; sub?: string }) {
  const { t } = useTranslation()
  return (
    <div className="flex items-baseline justify-between gap-3 py-3">
      <dt className="text-body">{label}</dt>
      <dd className="num text-right text-body font-bold">
        {value ?? '–'}
        {value == null && <span className="block text-micro font-normal text-ink3">{sub ?? t('me.learned.noDataYet', 'No data yet')}</span>}
      </dd>
    </div>
  )
}

export function BaselineCard({ progress }: { progress: Progress }) {
  const { t } = useTranslation()
  const b = progress.baseline
  return (
    <Card tone="hero" as="section" className="flex flex-col gap-2 lg:max-w-3xl">
      <SectionTitle>{t('me.diet.baselineTitle', 'Your starting point')}</SectionTitle>
      {!b ? (
        <p className="text-body text-ink2">
          {t('me.diet.needWeeks', 'Not enough data yet. A starting point needs two full weeks, with at least 5 meals logged in each. You have {{n}} so far.', { n: progress.fullWeeks })}
        </p>
      ) : (
        <>
          <dl className="divide-y divide-line">
            <Row
              label={t('me.diet.kcalPerMeal', 'Calories per meal')}
              value={b.avgKcal == null ? null : t('me.diet.kcalValue', '{{n}} kcal', { n: Math.round(b.avgKcal).toLocaleString('en-US') })}
            />
            <Row
              label={t('me.diet.saltPerMeal', 'Salt per meal')}
              value={b.avgSodium == null ? null : t('me.diet.mgValue', '{{n}} mg', { n: Math.round(b.avgSodium).toLocaleString('en-US') })}
            />
            <Row
              label={t('me.diet.onTime', 'Doses taken on time')}
              value={b.onTimePct == null ? null : `${Math.round(b.onTimePct)}%`}
              sub={t('me.diet.noDoses', 'No doses logged in these weeks')}
            />
          </dl>
          <p className="text-sub text-ink2">
            {t('me.diet.madeFrom', 'Made from {{meals}} meals in the first two full weeks you logged, the weeks of {{first}} and {{second}}.', {
              meals: b.meals,
              first: shortDate(b.weeks[0]!),
              second: shortDate(b.weeks[1]!),
            })}
            {b.doses != null && ' ' + t('me.diet.dosesIn', 'The log has {{n}} doses for those weeks.', { n: b.doses })}
          </p>
        </>
      )}
      <p className="text-micro text-ink3">
        {t('me.diet.note', 'This shows what you logged and did. It does not show that Equinox caused any change.')}
      </p>
    </Card>
  )
}
