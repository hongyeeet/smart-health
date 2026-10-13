/**
 * What is behind "See more" on Home: this week's bars and the full "What to log today" list (GET /logs/today).
 * Rows and bars are the ones Home always had; only where they sit has changed.
 */
import { progressLabel } from './labels'
import { useTranslation } from 'react-i18next'
import { useGo } from '@/app/navigation'
import { cn } from '@/lib/cn'
import type { LogProgress, ProgressItem } from '@/data/types'
import { Barbell, CaretRight, CheckCircle, Circle, ForkKnife, PersonSimpleWalk, Smiley, Thermometer, type IconType } from '@/ui/icons'
import { Card, SectionTitle } from '@/ui/primitives'

const ICON: Record<ProgressItem['key'], IconType> = { meals: ForkKnife, checkin: Smiley, workout: PersonSimpleWalk, symptom: Thermometer }

/**
 * One log in "What to log today". A log that is worth doing right now is lifted quietly: a soft pine tint, a filled icon and a
 * "Log" action, with the time it is usually done in the hint. Nothing turns amber, because late is not a warning.
 */
function Row({ item, onOpen }: { item: ProgressItem; onOpen: () => void }) {
  const { t } = useTranslation()
  const Icon = ICON[item.key]
  const status = item.status
  const now = status === 'due'
  return (
    <button type="button" onClick={onOpen} aria-label={now ? t('home.row.due', '{{label}}. A good time to log this.', { label: progressLabel(t, item.key, item.label) }) : undefined} className={cn('press flex min-h-12 items-center gap-3 py-3 text-left', now ? '-mx-4 w-[calc(100%+2rem)] rounded-[14px] bg-brand-soft/70 px-4' : 'w-full')}>
      <span className={cn('flex h-11 w-11 flex-none items-center justify-center rounded-full', status === 'done' ? 'bg-ok-soft text-ok' : now ? 'bg-brand text-on-brand' : 'bg-well text-ink2')}>
        <Icon size={22} aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-2 text-body font-bold leading-snug">
          {progressLabel(t, item.key, item.label)}
          {item.target != null && (
            <span className="num text-sub font-normal text-ink3">
              {Math.min(item.count, item.target)} of {item.target}
            </span>
          )}
        </span>
        <span className="block text-sub text-ink2">{item.hint}</span>
      </span>
      {status === 'done' ? (
        <CheckCircle size={24} weight="fill" className="flex-none text-ok" aria-label={t('home.done', 'Done')} />
      ) : now ? (
        <span className="flex-none rounded-chip border-[1.5px] border-brand px-3 py-1 text-sub font-bold text-brand">{t('home.log', 'Log')}</span>
      ) : (
        <Circle size={24} className="flex-none text-ink3" aria-label={t('home.notYet', 'Not yet')} />
      )}
      <CaretRight size={18} className="flex-none text-ink3" aria-hidden />
    </button>
  )
}

function Bar({ label, value, goal, unit }: { label: string; value: number; goal: number; unit: string }) {
  const { t } = useTranslation()
  const pct = Math.min(100, goal ? (value / goal) * 100 : 0)
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 text-sub">
        <span className="font-bold">{label}</span>
        <span className="num text-ink2">
          {t('home.bar.ofGoal', '{{value}} of {{goal}}', { value, goal })}
          {unit && ` ${unit}`}
        </span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-well" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={goal} aria-label={label}>
        <div className="h-full rounded-full bg-brand transition-[width] duration-700" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export function ProgressDetails({ data }: { data: LogProgress }) {
  const { t } = useTranslation()
  const go = useGo()
  return (
    <>
      <Card className="flex flex-col gap-2">
        <SectionTitle>{t('home.week', 'This week')}</SectionTitle>
        <Bar label={t('home.bar.activeMin', 'Active minutes')} value={data.weekActivityMin} goal={data.weekActivityGoal} unit="min" />
        <Bar label={t('home.bar.strength', 'Strength sessions')} value={data.weekStrengthSessions} goal={data.weekStrengthGoal} unit="" />
        <button type="button" onClick={() => go('F1')} className="press mt-1 flex min-h-12 items-center gap-2 self-start text-sub font-bold text-brand">
          <Barbell size={18} aria-hidden /> {t('home.action.workout', 'Log a workout')}
        </button>
      </Card>
      <Card className="flex flex-col gap-1">
        <SectionTitle>{t('home.whatToLog', 'What to log today')}</SectionTitle>
        <div className="divide-y divide-line">
          {data.items.map((i) => (
            <Row key={i.key} item={i} onOpen={() => go(i.to)} />
          ))}
        </div>
        <p className="pt-1 text-sub text-ink3">{t('home.sensor', 'Glucose comes from your sensor, so there is nothing to type.')}</p>
      </Card>
    </>
  )
}
