/**
 * "Today's plan" on Home: the day's meals and medicines as ONE flow in time order, with a line joining the steps that is filled up
 * to the current one. The current step ("now") is highlighted and holds the buttons (Log <meal>, Taken). The steps sit in ONE straight
 * line (never a second row) that scrolls sideways, with a back and a forward arrow to move along it; it opens on the current step.
 * As-needed medicines are never in the plan (the server leaves them out).
 * A brand-new person (no medicines, nothing logged) sees Start here instead.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { useMarkTaken } from '@/data/hooks'
import type { HomePlan, PlanItem, PlanStep } from '@/data/types'
import { useGo } from '@/app/navigation'
import { cn } from '@/lib/cn'
import { CaretLeft, CaretRight, Check, ForkKnife, Pill, X } from '@/ui/icons'
import { Alert, Skeleton } from '@/ui/primitives'
import { StartHere } from './StartHere'

const MEAL_NAME = (t: TFunction, m: PlanItem['mealType']) =>
  m === 'breakfast' ? t('home.plan.breakfast', 'breakfast') : m === 'lunch' ? t('home.plan.lunch', 'lunch') : m === 'dinner' ? t('home.plan.dinner', 'dinner') : t('home.plan.meal', 'meal')

function ItemRow({ item, now }: { item: PlanItem; now: boolean }) {
  const { t } = useTranslation()
  const go = useGo()
  const mark = useMarkTaken()
  const meal = item.kind === 'meal'
  const Icon = meal ? ForkKnife : Pill
  const due = item.status === 'due'
  const status =
    item.status === 'done' ? (meal ? t('home.plan.logged', 'Logged') : t('home.plan.taken', 'Taken')) : item.status === 'missed' ? t('home.plan.missed', 'Missed') : t('home.plan.later', 'Later')
  return (
    <div className={cn('flex min-h-9 flex-wrap items-center gap-x-2.5 gap-y-1', due && 'min-h-11')}>
      <span className={cn('flex h-7 w-7 flex-none items-center justify-center rounded-full', now ? 'bg-card' : item.status === 'later' ? 'bg-well' : meal ? 'bg-brass-soft' : 'bg-info-soft', item.status === 'later' ? 'text-ink2' : meal ? 'text-brass' : 'text-info')}>
        <Icon size={16} aria-hidden />
      </span>
      <span className={cn('min-w-0 flex-1 basis-24 break-words text-sub', (due || now) && 'font-bold', item.status === 'later' && 'text-ink2')}>{item.title}</span>
      {due && meal && (
        <button type="button" onClick={() => go('E2')} className="press min-h-11 flex-none rounded-[12px] border-[1.5px] border-transparent bg-brand px-3.5 text-btn-sm font-bold text-on-brand">
          {t('home.plan.logMeal', 'Log {{meal}}', { meal: MEAL_NAME(t, item.mealType) })}
        </button>
      )}
      {due && !meal && (
        <button
          type="button"
          disabled={mark.isPending || !item.doseId}
          onClick={() => item.doseId && mark.mutate(item.doseId)}
          className="press min-h-11 flex-none rounded-[12px] border-[1.5px] border-brand bg-card px-3.5 text-btn-sm font-bold text-brand disabled:border-line disabled:bg-well disabled:text-ink2"
        >
          {t('home.plan.takenBtn', 'Taken')}
        </button>
      )}
      {!due && <span className="flex-none text-micro text-ink2">{status}</span>}
    </div>
  )
}

function Node({ state }: { state: PlanStep['state'] }) {
  if (state === 'done')
    return (
      <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-ok text-card">
        <Check size={14} weight="bold" aria-hidden />
      </span>
    )
  if (state === 'now') return <span className="h-6 w-6 flex-none rounded-full border-[3px] border-brand bg-card" aria-hidden />
  if (state === 'missed')
    return (
      <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full border-2 border-line bg-card text-ink3">
        <X size={12} weight="bold" aria-hidden />
      </span>
    )
  return <span className="h-6 w-6 flex-none rounded-full border-2 border-ink3/40 bg-card" aria-hidden />
}

function Step({ step, last }: { step: PlanStep; last: boolean }) {
  const { t } = useTranslation()
  const now = step.state === 'now'
  // the line leaving a step is filled once that step is done: so it is filled up to the current step
  const filled = step.state === 'done'
  return (
    <li data-step className="flex w-[82%] flex-none snap-start flex-col gap-2 pr-3 min-[480px]:w-[260px] lg:w-1/3" aria-current={now ? 'step' : undefined}>
      <div className="flex w-full items-center">
        <Node state={step.state} />
        <span className={cn('h-0.5 flex-1', filled ? 'bg-ok' : 'bg-line', last && 'invisible')} aria-hidden />
      </div>
      <div className="min-w-0 flex-1">
        <div className={cn(now && 'rounded-card bg-brand-soft px-3 py-2.5')}>
          <p className={cn('mb-1 text-sub font-bold', now ? 'text-brand' : step.state === 'later' ? 'text-ink2' : 'text-ink2')}>
            {now ? t('home.plan.nowAt', '{{time}}, now', { time: step.label }) : step.label}
          </p>
          <div className="flex flex-col">
            {step.items.map((it, i) => (
              <ItemRow key={`${it.kind}:${it.doseId ?? it.mealType ?? i}`} item={it} now={now} />
            ))}
          </div>
        </div>
      </div>
    </li>
  )
}

export function PlanCard({ plan }: { plan: HomePlan }) {
  const { t } = useTranslation()
  const n = plan.steps.length
  const track = useRef<HTMLOListElement>(null)
  const [edge, setEdge] = useState({ start: true, end: false })

  /** Which ends of the line can still be moved towards: sets the two arrows. */
  const measure = useCallback(() => {
    const el = track.current
    if (!el) return
    setEdge({ start: el.scrollLeft <= 2, end: el.scrollLeft + el.clientWidth >= el.scrollWidth - 2 })
  }, [])

  /** The step in view is the current one when the page opens, and again when the current step changes. */
  const nowIndex = plan.nowIndex ?? Math.max(0, plan.steps.findIndex((s) => s.state === 'now'))
  useEffect(() => {
    const el = track.current
    const step = el?.querySelectorAll<HTMLElement>('[data-step]')[nowIndex]
    if (el && step) el.scrollTo({ left: Math.max(0, step.offsetLeft - el.offsetLeft), behavior: 'auto' })
    measure()
  }, [nowIndex, n, measure])
  useEffect(() => {
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [measure])

  /** One step along the line, forward or back. */
  const move = (dir: 1 | -1) => {
    const el = track.current
    const first = el?.querySelector<HTMLElement>('[data-step]')
    if (el && first) el.scrollBy({ left: dir * first.offsetWidth, behavior: 'smooth' })
  }
  const arrow = 'press flex h-11 w-11 flex-none items-center justify-center rounded-full border border-line bg-card text-ink disabled:opacity-35'

  return (
    <section aria-label={t('home.plan.title', "Today's plan")} className="flex flex-col gap-3 rounded-card border border-line bg-card p-4 shadow-lift">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-h2 font-bold">{t('home.plan.title', "Today's plan")}</h2>
          <p className="text-sub text-ink2">{t('home.plan.done', '{{done}} of {{total}} done', { done: plan.done, total: plan.total })}</p>
        </div>
        {n > 1 && (
          <div className="flex flex-none gap-2">
            <button type="button" onClick={() => move(-1)} disabled={edge.start} aria-label={t('home.plan.back', 'Earlier in the day')} className={arrow}>
              <CaretLeft size={20} aria-hidden />
            </button>
            <button type="button" onClick={() => move(1)} disabled={edge.end} aria-label={t('home.plan.forward', 'Later in the day')} className={arrow}>
              <CaretRight size={20} aria-hidden />
            </button>
          </div>
        )}
      </div>
      <div className="flex gap-1" role="img" aria-label={t('home.plan.done', '{{done}} of {{total}} done', { done: plan.done, total: plan.total })}>
        {Array.from({ length: plan.total }, (_, i) => (
          <span key={i} className={cn('h-1.5 flex-1 rounded-[3px]', i < plan.done ? 'bg-ok' : 'bg-line')} />
        ))}
      </div>
      <ol ref={track} onScroll={measure} className="flex snap-x snap-mandatory overflow-x-auto pt-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {plan.steps.map((s, i) => (
          <Step key={s.time} step={s} last={i === n - 1} />
        ))}
      </ol>
    </section>
  )
}

/** The plan, or Start here for a brand-new person, with its loading and error states. */
export function TodayPlan({ plan, loading, error, onRetry }: { plan: HomePlan | undefined; loading: boolean; error: boolean; onRetry: () => void }) {
  const { t } = useTranslation()
  if (plan) {
    // nothing scheduled and nothing logged today (a brand-new person has no medicines and no meal times yet): Start here, not an empty card
    if (plan.steps.length === 0) return <StartHere />
    return <PlanCard plan={plan} />
  }
  if (error)
    return (
      <Alert tone="warn" onClick={onRetry}>
        {t('home.plan.loadError', "We could not load today's plan. Tap to try again.")}
      </Alert>
    )
  return loading ? <Skeleton className="h-64" /> : null
}
