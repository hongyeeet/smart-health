/**
 * Block 4 on Home: today's logging ring, with the single next thing to log (GET /logs/today). Moved out of Home.tsx unchanged in
 * its wording; Home decides where it sits.
 */
import { useTranslation } from 'react-i18next'
import { useGo } from '@/app/navigation'
import type { LogProgress } from '@/data/types'
import { Lightning } from '@/ui/icons'
import { Button, Card, Skeleton } from '@/ui/primitives'

export function Ring({ done, total }: { done: number; total: number }) {
  const { t } = useTranslation()
  const r = 34
  const c = 2 * Math.PI * r
  const f = total ? done / total : 0
  return (
    <div className="relative h-24 w-24 flex-none" role="img" aria-label={t('home.ring.label', '{{done}} of {{total}} logs done today', { done, total })}>
      <svg viewBox="0 0 80 80" className="h-full w-full -rotate-90">
        <circle cx="40" cy="40" r={r} fill="none" strokeWidth="8" className="stroke-line" />
        <circle cx="40" cy="40" r={r} fill="none" strokeWidth="8" strokeLinecap="round" className="stroke-brand transition-[stroke-dashoffset] duration-700" strokeDasharray={c} strokeDashoffset={c * (1 - f)} />
      </svg>
      <span className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="num font-serif text-h1 leading-none">{done}</span>
        <span className="text-micro text-ink3">{t('home.ring.of', 'of {{total}}', { total })}</span>
      </span>
    </div>
  )
}

/** The reserved space while today's logging loads, so the page does not jump when it arrives. */
export function TodayCardSkeleton() {
  return <Skeleton className="h-52 lg:h-full" />
}

export function TodayCard({ data }: { data: LogProgress }) {
  const { t } = useTranslation()
  const go = useGo()
  return (
    <Card tone="hero" className="flex flex-col gap-4">
      <div className="flex items-center gap-4 [[data-ts='2']_&]:flex-col [[data-ts='2']_&]:items-start">
        <Ring done={data.done} total={data.total} />
        <div className="min-w-0 flex-1">
          <p className="text-sub font-bold text-ink3">{data.nextUp?.prompt ? t('home.hero.goodTime', 'A good time to log') : t('home.hero.today', "Today's logging")}</p>
          <p className="break-words text-h2 font-bold leading-snug">
            {data.done === data.total
              ? t('home.hero.caughtUp', 'All caught up. Well done.')
              : data.nextUp?.prompt
                ? data.nextUp.prompt
                : data.nextUp
                  ? t('home.hero.next', 'Next: {{label}}', { label: data.nextUp.label.toLowerCase() })
                  : t('home.hero.nothingDue', 'Nothing more is due for now.')}
          </p>
          {data.streakDays > 0 && (
            <p className="mt-1 flex items-center gap-1 text-sub text-ink2">
              <Lightning size={16} weight="fill" className="text-brass" aria-hidden />
              {data.streakDays === 1 ? t('home.streak.one', '{{n}} day in a row', { n: data.streakDays }) : t('home.streak.many', '{{n}} days in a row', { n: data.streakDays })}
            </p>
          )}
        </div>
      </div>
      {data.nextUp && <Button className="mt-auto" variant={data.nextUp.prompt ? 'primary' : 'secondary'} onClick={() => go(data.nextUp!.to)}>{data.nextUp.key === 'meals' ? t('home.action.meal', 'Log a meal') : data.nextUp.key === 'checkin' ? t('home.action.checkin', 'Do the check-in') : t('home.action.workout', 'Log a workout')}</Button>}
    </Card>
  )
}
