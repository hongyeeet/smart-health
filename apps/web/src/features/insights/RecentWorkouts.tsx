/** Recent workouts as one compact list: the first three, then a green underlined "See more" link that shows the rest. */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { InsightsActivity } from '@/data/types'
import { SectionTitle, ProseLink } from '@/ui/primitives'

const SHOWN = 3

export function RecentWorkouts({ workouts }: { workouts: InsightsActivity['workouts'] }) {
  const { t } = useTranslation()
  const [all, setAll] = useState(false)
  if (!workouts.length) return null
  const rows = all ? workouts : workouts.slice(0, SHOWN)
  const more = workouts.length - SHOWN
  return (
    <section className="flex flex-col gap-2">
      <SectionTitle>{t('insights.activity.recentWorkouts', 'Recent workouts')}</SectionTitle>
      <div className="rounded-card border border-line bg-card px-4 py-1">
        <ul className="divide-y divide-line">
          {rows.map((w) => (
            <li key={w.id} className="flex items-baseline justify-between gap-3 py-2.5">
              <span className="min-w-0">
                <span className="block text-body font-bold">{w.label}</span>
                <span className="block text-sub text-ink2">
                  {w.intensity == null
                    ? t('insights.activity.workoutLineUnrated', '{{date}}, {{min}} min, not rated', { date: w.date, min: w.minutes })
                    : t('insights.activity.workoutLine', '{{date}}, {{min}} min, effort {{effort}} of 5 as you rated it', { date: w.date, min: w.minutes, effort: w.intensity })}
                </span>
              </span>
              {w.glucoseChange2h != null && (
                <span className="num flex-none text-sub text-ink2">
                  {t('insights.activity.glucoseChange', '{{sign}}{{n}} mmol/L in 2 h', {
                    sign: w.glucoseChange2h > 0 ? '+' : '−',
                    n: Math.abs(w.glucoseChange2h).toFixed(1),
                  })}
                </span>
              )}
            </li>
          ))}
        </ul>
        {more > 0 && (
          <p className="border-t border-line py-2.5 text-body">
            <ProseLink onClick={() => setAll((v) => !v)}>
              {all ? t('insights.activity.seeLess', 'See less') : t('insights.activity.seeMoreWorkouts', 'See more ({{n}})', { n: more })}
            </ProseLink>
          </p>
        )}
      </div>
    </section>
  )
}
