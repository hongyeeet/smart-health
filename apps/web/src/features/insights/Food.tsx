/**
 * C3 — Food. What was eaten, day by day (calories, carbohydrate, protein, fat and salt), how each food moved glucose, the recent
 * entries with the detail of every meal, and the macro calendar at the bottom (tap a day for its meals).
 */
import { useTranslation } from 'react-i18next'
import { useDietDaysFor, useInsightsFood } from '@/data/hooks'
import type { InsightsPattern } from '@/data/types'
import { Split } from '@/ui/layout'
import { Card, SectionTitle, UnverifiedTag } from '@/ui/primitives'
import { DietCalendar } from '@/features/me/progress/DietCalendar'
import { Gate, InsightsFrame, Plain, useInsightsDays } from './shared'
import { MacroCharts } from './food/MacroCharts'
import { FoodRanking } from './food/Ranking'
import { RecentEntries } from './food/RecentEntries'

/** The patterns from the person's own history. Always unverified: they compare two things and do not prove a cause. No link here, the one "Why am I seeing this?" is at the top. */
function FoodFindings({ items }: { items: InsightsPattern[] }) {
  const { t } = useTranslation()
  if (!items.length) return null
  return (
    <section className="flex flex-col gap-2">
      <SectionTitle>{t('insights.shared.findings', 'What your history shows')}</SectionTitle>
      {items.map((p) => (
        <Card key={p.key} className="flex flex-col gap-2">
          <p className="text-body">{p.text}</p>
          <p className="num text-sub text-ink3">{t('insights.shared.basedOn', 'Based on {{n}} matched events in your own history.', { n: p.n })}</p>
          <div>
            <UnverifiedTag />
          </div>
        </Card>
      ))}
    </section>
  )
}

export function FoodTab() {
  const days = useInsightsDays((s) => s.days)
  const { data, isError } = useInsightsFood(days)
  // the day totals use the same period as the food read, so the charts and the ranking cover the same days
  const diet = useDietDaysFor(data?.period.start, data?.period.end)
  const { t } = useTranslation()
  return (
    <InsightsFrame tab="C3" period={data?.period} why="food">
      <Gate data={data} isError={isError} empty={!!data && data.totals.meals === 0} emptyText={t('insights.food.empty', 'Log a few meals and what you eat shows up here, with how each one moved your glucose.')}>
        {data && (
          <>
            <Plain>
              {t('insights.food.mealsLogged', '{{meals}} meals logged. {{salt}} were high in salt and {{sugar}} high in sugar.', {
                meals: data.totals.meals,
                salt: data.totals.highSaltMeals,
                sugar: data.totals.highSugarMeals,
              })}
            </Plain>
            <section className="flex flex-col gap-3">
              <SectionTitle>{t('insights.food.dayByDay', 'Day by day')}</SectionTitle>
              <MacroCharts days={diet.data?.days} isError={diet.isError} />
            </section>
            <Split>
              <FoodRanking responses={data.responses} stillLearning={data.stillLearning} />
              <FoodFindings items={data.patterns} />
            </Split>
          </>
        )}
      </Gate>
      <RecentEntries />
      <DietCalendar />
    </InsightsFrame>
  )
}
