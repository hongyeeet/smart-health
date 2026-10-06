import { useEffect, useState } from 'react'
import { useMealSession } from './useMealSession'
import { useGo } from '@/app/navigation'
import { CaretRight, ForkKnife } from '@/ui/icons'

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

/** Shown on Home and the Log hub while a meal has been started but not finished, so the finish tap is never forgotten. */
export function MealBanner() {
  const meal = useMealSession((s) => s.meal)
  const go = useGo()
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!meal) return
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [meal])
  if (!meal) return null
  const elapsed = Math.max(0, Math.round((now - new Date(meal.startedAt).getTime()) / 1000))
  return (
    <button type="button" onClick={() => go('E2')} className="press flex w-full items-center gap-3 rounded-card border border-brand/30 bg-brand-soft p-4 text-left">
      <span className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-brand text-on-brand">
        <ForkKnife size={22} aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-body font-bold text-brand">Eating: {meal.name}</span>
        <span className="block text-sub text-ink2">
          {mmss(elapsed)} so far. Tap when you have finished.
        </span>
      </span>
      <CaretRight size={20} className="flex-none text-brand" aria-hidden />
    </button>
  )
}
