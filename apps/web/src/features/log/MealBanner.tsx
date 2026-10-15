import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMealSession } from './useMealSession'
import { mmss } from './meal/mealMath'
import { useGo } from '@/app/navigation'
import { CaretRight, ForkKnife } from '@/ui/icons'

/** Shown on Home and the Log hub while a meal has been started but not finished, so the finish tap is never forgotten. */
export function MealBanner() {
  const { t } = useTranslation()
  const { meal } = useMealSession()
  const go = useGo()
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!meal) return
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [meal])
  if (!meal) return null
  const elapsed = Math.max(0, Math.round((now - new Date(meal.startedAt).getTime()) / 1000))
  return (
    <button type="button" onClick={() => go('E2')} className="press flex min-h-16 w-full items-center gap-3 rounded-card border border-brand/30 bg-brand-soft p-4 text-left">
      <span className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-brand text-on-brand">
        <ForkKnife size={22} aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block break-words text-body font-bold text-brand">{t('log.meal.eating', 'Eating: {{name}}', { name: meal.name })}</span>
        <span className="block text-sub text-ink2">
          {t('log.meal.soFar', '{{time}} so far. Tap when you have finished.', { time: mmss(elapsed) })}
        </span>
      </span>
      <CaretRight size={20} className="flex-none text-brand" aria-hidden />
    </button>
  )
}
