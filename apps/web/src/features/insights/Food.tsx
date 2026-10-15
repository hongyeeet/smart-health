/**
 * C3 — Food. Day by day (calories, carbohydrate, protein, fat and salt) and how each food moved glucose, on the left; on the right the
 * recent meals, your starting point (the first two full weeks against now), what the history shows and the menu nudge. Below: the
 * full recent entries and the diet calendar (tap a day for its meals). The one "Why am I seeing this?" link is at the top.
 */
import { useTranslation } from 'react-i18next'
import { useDietDaysFor, useInsightsFood, useProgress } from '@/data/hooks'
import type { InsightsPattern } from '@/data/types'
import { useGo } from '@/app/navigation'
import { cn } from '@/lib/cn'
import { Button, Card, UnverifiedTag } from '@/ui/primitives'
import { DietCalendar } from '@/features/me/progress/DietCalendar'
import { Gate, InsightsFrame, useInsightsDays } from './shared'
import { MacroCharts } from './food/MacroCharts'
import { MealTiles } from './food/MealTiles'
import { FoodRanking } from './food/Ranking'
import { RecentEntries } from './food/RecentEntries'
import { RecentMeals } from './food/RecentMeals'
import { StartingPoint } from './food/StartingPoint'

/** The patterns from the person's own history, in one card. Always unverified: they compare two things and do not prove a cause. */
function FoodFindings({ items }: { items: InsightsPattern[] }) {
  const { t } = useTranslation()
  if (!items.length) return null
  return (
    <Card className="flex flex-col gap-3">
      <h3 className="text-body font-bold">{t('insights.shared.findings', 'What your history shows')}</h3>
      {items.map((p, i) => (
        <div key={p.key} className={cn('flex flex-col gap-2', i > 0 && 'border-t border-line pt-3')}>
          <p className="text-sub">{p.text}</p>
          <p className="num text-micro text-ink3">{t('insights.shared.basedOn', 'Based on {{n}} matched events in your own history.', { n: p.n })}</p>
          <div>
            <UnverifiedTag />
          </div>
        </div>
      ))}
    </Card>
  )
}

/** Ideas for the next meal. The lunch ideas screen (E8) is the nearest existing screen; the full menu is not built yet. */
function MenuNudge() {
  const { t } = useTranslation()
  const go = useGo()
  return (
    <div className="flex flex-col gap-3 rounded-card border border-line bg-brand-soft p-4">
      <div className="min-w-0 flex-1">
        <p className="text-sub font-bold">{t('insights.food.nextTitle', 'Not sure what to eat next?')}</p>
        <p className="text-sub text-ink2">{t('insights.food.nextSub', 'Ideas that fit you, as a menu.')}</p>
      </div>
      <Button size="md" className="self-start" onClick={() => go('E9')}>
        {t('insights.food.openMenu', 'Open menu')}
      </Button>
    </div>
  )
}

export function FoodTab() {
  const days = useInsightsDays((s) => s.days)
  const { data, isError } = useInsightsFood(days)
  // the day totals use the same period as the food read, so the charts and the ranking cover the same days
  const diet = useDietDaysFor(data?.period.start, data?.period.end)
  const progress = useProgress()
  const { t } = useTranslation()
  return (
    <InsightsFrame tab="C3" period={data?.period} why="food">
      <Gate
        data={data}
        isError={isError}
        empty={!!data && data.totals.meals === 0}
        emptyText={t('insights.food.empty', 'Log a few meals and what you eat shows up here, with how each one moved your glucose.')}
      >
        {data && (
          <>
            <MealTiles totals={data.totals} days={data.period.days} kcalStart={progress.data?.compare?.avgKcal.first ?? null} />
            <div className="flex flex-col gap-4 xl:grid xl:grid-cols-[minmax(0,1fr)_332px] xl:items-start xl:gap-6">
              <div className="flex min-w-0 flex-col gap-4">
                <MacroCharts days={diet.data?.days} isError={diet.isError} />
                <FoodRanking responses={data.responses} stillLearning={data.stillLearning} />
              </div>
              <div className="flex min-w-0 flex-col gap-4">
                <RecentMeals />
                {progress.data && <StartingPoint progress={progress.data} />}
                <FoodFindings items={data.patterns} />
                <MenuNudge />
              </div>
            </div>
          </>
        )}
      </Gate>
      <section id="food-recent" className="scroll-mt-4">
        <RecentEntries />
      </section>
      <DietCalendar />
    </InsightsFrame>
  )
}
