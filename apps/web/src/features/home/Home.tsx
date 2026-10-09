/**
 * B1 — Home: today's logging at a glance.
 *
 * Shows what has been logged today against what is expected by this time of day, a streak, the week's activity, and one
 * clear "next up" action, so the person always knows which log to do next. Everything comes from the database
 * (GET /logs/today); the bell opens the reminders (B2).
 */
import { useClash, useDismissSuggestion, useFoodFlags, useLearned, useLogProgress, useLunchIdeas, useNotices } from '@/data/hooks'
import { useDismissed } from '@/features/alerts/pieces'
import { useGo } from '@/app/navigation'
import { MealBanner } from '@/features/log/MealBanner'
import { DoseCard } from './DoseCard'
import type { ProgressItem } from '@/data/types'
import { cn } from '@/lib/cn'
import { Header, Reveal, Screen, Split } from '@/ui/layout'
import { Alert, Button, Card, SectionTitle, Skeleton } from '@/ui/primitives'
import { UserSwitch } from './UserSwitch'
import { Barbell, Bell, CaretRight, CheckCircle, Circle, ForkKnife, Lightning, PersonSimpleWalk, Smiley, Thermometer, type IconType } from '@/ui/icons'

const ICON: Record<ProgressItem['key'], IconType> = { meals: ForkKnife, checkin: Smiley, workout: PersonSimpleWalk, symptom: Thermometer }

function greeting(h: number) {
  return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'
}

function Ring({ done, total }: { done: number; total: number }) {
  const r = 34
  const c = 2 * Math.PI * r
  const f = total ? done / total : 0
  return (
    <div className="relative h-24 w-24 flex-none" role="img" aria-label={`${done} of ${total} logs done today`}>
      <svg viewBox="0 0 80 80" className="h-full w-full -rotate-90">
        <circle cx="40" cy="40" r={r} fill="none" strokeWidth="8" className="stroke-line" />
        <circle cx="40" cy="40" r={r} fill="none" strokeWidth="8" strokeLinecap="round" className="stroke-brand transition-[stroke-dashoffset] duration-700" strokeDasharray={c} strokeDashoffset={c * (1 - f)} />
      </svg>
      <span className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="num font-serif text-h1 leading-none">{done}</span>
        <span className="text-micro text-ink3">of {total}</span>
      </span>
    </div>
  )
}

/**
 * One log in "What to log today". A log that is worth doing right now is lifted quietly: a soft pine tint, a filled icon and a
 * "Log" action, with the time it is usually done in the hint. Nothing turns amber, because late is not a warning.
 */
function Row({ item, onOpen }: { item: ProgressItem; onOpen: () => void }) {
  const Icon = ICON[item.key]
  const status = item.status
  const now = status === 'due'
  return (
    <button type="button" onClick={onOpen} aria-label={now ? `${item.label}. A good time to log this.` : undefined} className={cn('press flex items-center gap-3 py-3 text-left', now ? '-mx-4 w-[calc(100%+2rem)] rounded-[14px] bg-brand-soft/70 px-4' : 'w-full')}>
      <span className={cn('flex h-11 w-11 flex-none items-center justify-center rounded-full', status === 'done' ? 'bg-ok-soft text-ok' : now ? 'bg-brand text-on-brand' : 'bg-well text-ink2')}>
        <Icon size={22} aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2 text-body font-bold leading-snug">
          {item.label}
          {item.target != null && (
            <span className="num text-sub font-normal text-ink3">
              {Math.min(item.count, item.target)} of {item.target}
            </span>
          )}
        </span>
        <span className="block text-sub text-ink2">{item.hint}</span>
      </span>
      {status === 'done' ? (
        <CheckCircle size={24} weight="fill" className="flex-none text-ok" aria-label="Done" />
      ) : now ? (
        <span className="flex-none rounded-chip border-[1.5px] border-brand px-3 py-1 text-sub font-bold text-brand">Log</span>
      ) : (
        <Circle size={24} className="flex-none text-ink3" aria-label="Not yet" />
      )}
      <CaretRight size={18} className="flex-none text-ink3" aria-hidden />
    </button>
  )
}

export function Home() {
  const go = useGo()
  const { data, isError, refetch } = useLogProgress()
  const { data: notices } = useNotices()
  const { data: clash } = useClash()
  const setAside = useDismissed((s) => s.ids)
  /** unread reminders plus medicine alerts the person has not set aside */
  const unread = (notices?.filter((n) => n.unread).length ?? 0) + (clash?.alerts.filter((a) => !setAside.includes(a.id)).length ?? 0)
  const now = new Date()
  const dateLabel = now.toLocaleDateString('en-SG', { weekday: 'long', day: 'numeric', month: 'long' })

  return (
    <Screen tabs>
      <Header
        title={greeting(now.getHours())}
        sub={dateLabel}
        trailing={
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => go('B2')} aria-label={`Notifications and alerts, ${unread} new`} className="press relative flex h-12 w-12 items-center justify-center rounded-full border border-line bg-card">
              <Bell size={24} aria-hidden />
              {unread > 0 && <span className="absolute right-2.5 top-2.5 h-2.5 w-2.5 rounded-full bg-brass ring-2 ring-card" />}
            </button>
            <UserSwitch />
          </div>
        }
      />
      <MealBanner />
      <DoseCard />
      {isError && (
        <Alert tone="warn" onClick={() => void refetch()}>
          We could not load today's logs. Tap to try again.
        </Alert>
      )}
      {!data && !isError && (
        <>
          <Skeleton className="h-36" />
          <Skeleton className="h-64" />
        </>
      )}
      {data && (
        <Reveal id="home-progress">
          <Split>
            <section className="flex flex-col gap-4">
              <Card tone="hero" className="flex flex-col gap-4">
                <div className="flex items-center gap-4">
                  <Ring done={data.done} total={data.total} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sub font-bold text-ink3">{data.nextUp?.prompt ? 'A good time to log' : "Today's logging"}</p>
                    <p className="text-h2 font-bold leading-snug">
                      {data.done === data.total
                        ? 'All caught up. Well done.'
                        : data.nextUp?.prompt
                          ? data.nextUp.prompt
                          : data.nextUp
                            ? `Next: ${data.nextUp.label.toLowerCase()}`
                            : 'Nothing more is due for now.'}
                    </p>
                    {data.streakDays > 0 && (
                      <p className="mt-1 flex items-center gap-1 text-sub text-ink2">
                        <Lightning size={16} weight="fill" className="text-brass" aria-hidden />
                        {data.streakDays} {data.streakDays === 1 ? 'day' : 'days'} in a row
                      </p>
                    )}
                  </div>
                </div>
                {data.nextUp && <Button variant={data.nextUp.prompt ? 'primary' : 'secondary'} onClick={() => go(data.nextUp!.to)}>{data.nextUp.key === 'meals' ? 'Log a meal' : data.nextUp.key === 'checkin' ? 'Do the check-in' : 'Log a workout'}</Button>}
              </Card>
              <Card className="flex flex-col gap-2">
                <SectionTitle>This week</SectionTitle>
                <Bar label="Active minutes" value={data.weekActivityMin} goal={data.weekActivityGoal} unit="min" />
                <Bar label="Strength sessions" value={data.weekStrengthSessions} goal={data.weekStrengthGoal} unit="" />
                <button type="button" onClick={() => go('F1')} className="press mt-1 flex items-center gap-2 self-start text-sub font-bold text-brand">
                  <Barbell size={18} aria-hidden /> Log a workout
                </button>
              </Card>
              <ToConfirmCard />
              <FoodFlagCard />
              <LunchCard />
            </section>
            <section className="flex flex-col gap-1">
              <SectionTitle>What to log today</SectionTitle>
              <div className="divide-y divide-line rounded-card border border-line bg-card px-4">
                {data.items.map((i) => (
                  <Row key={i.key} item={i} onOpen={() => go(i.to)} />
                ))}
              </div>
              <p className="px-1 pt-1 text-sub text-ink3">Glucose comes from your sensor, so there is nothing to type.</p>
            </section>
          </Split>
        </Reveal>
      )}
    </Screen>
  )
}

function Bar({ label, value, goal, unit }: { label: string; value: number; goal: number; unit: string }) {
  const pct = Math.min(100, goal ? (value / goal) * 100 : 0)
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between text-sub">
        <span className="font-bold">{label}</span>
        <span className="num text-ink2">
          {value} of {goal}
          {unit && ` ${unit}`}
        </span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-well" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={goal} aria-label={label}>
        <div className="h-full rounded-full bg-brand transition-[width] duration-700" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

const NUTRIENT: Record<string, [string, string]> = { kcal: ['calories', 'kcal'], sodium_mg: ['salt', 'mg'], carbs_g: ['carbs', 'g'], sugar_g: ['sugar', 'g'], protein_g: ['protein', 'g'], fat_g: ['fat', 'g'], fibre_g: ['fibre', 'g'] }

/** A food habit the memory loop noticed, with a lighter dish to try next time and exactly what it would change. */
function FoodFlagCard() {
  const { data } = useFoodFlags()
  const dismiss = useDismissSuggestion()
  const go = useGo()
  const h = data?.find((x) => x.alternatives.length > 0) ?? data?.[0]
  if (!h) return null
  const alt = h.alternatives[0]
  return (
    <Card className="flex flex-col gap-3">
      <SectionTitle>Worth a look</SectionTitle>
      <p className="text-body">
        You have had {h.label} <b>{h.n} times</b> in the last 2 weeks, about <b className="num">{Math.round(h.avg.kcal ?? 0).toLocaleString('en-US')}</b> kcal and <b className="num">{Math.round(h.avg.sodium_mg ?? 0).toLocaleString('en-US')}</b> mg salt each. Those are your own logged numbers.
      </p>
      {alt && (
        <div className="flex flex-col gap-2 rounded-card bg-well p-3.5">
          <p className="text-sub text-ink2">Your {h.topDish} ({h.topDishN} times) is the heaviest. Next time you could try</p>
          <p className="text-h2 font-bold leading-snug">{alt.name}</p>
          <ul className="grid grid-cols-2 gap-x-4 gap-y-1 text-sub">
            {alt.changes
              .filter((c) => ['kcal', 'protein_g', 'carbs_g', 'sodium_mg', 'sugar_g'].includes(c.nutrient) && Math.abs(c.change) >= (c.nutrient === 'kcal' ? 50 : c.nutrient === 'sodium_mg' ? 100 : 3))
              .map((c) => (
                <li key={c.nutrient} className="flex justify-between gap-2">
                  <span className="text-ink2">{NUTRIENT[c.nutrient]![0]}</span>
                  <span className="num">
                    {Math.round(c.from).toLocaleString('en-US')} to {Math.round(c.to).toLocaleString('en-US')} {NUTRIENT[c.nutrient]![1]}
                  </span>
                </li>
              ))}
          </ul>
          <p className="text-micro text-ink3">
            {alt.serving} {alt.sourceGrade ? `· from the Singapore food database (${alt.sourceGrade.replace('_', ' ')})` : ''}. Typical values, so your portion may differ.
          </p>
        </div>
      )}
      {h.outcomeText && <p className="rounded-card bg-ok-soft p-3.5 text-sub text-ink">{h.outcomeText}</p>}
      <p className="text-sub text-ink3">An idea for next time, not advice. Your logged meals are never changed.</p>
      {alt && (
        <button type="button" onClick={() => dismiss.mutate(`swap:${alt.foodId}`)} className="press self-start text-sub font-bold text-ink2">
          Not for me
        </button>
      )}
      <button type="button" onClick={() => go('E2')} className="press flex items-center gap-2 self-start text-sub font-bold text-brand">
        <ForkKnife size={18} aria-hidden /> Log a meal
      </button>
    </Card>
  )
}

/** Shown only inside the person's lunch window. */
function LunchCard() {
  const { data } = useLunchIdeas()
  const go = useGo()
  if (!data || data.options.length === 0) return null
  const now = new Date()
  const mins = now.getHours() * 60 + now.getMinutes()
  const [sh, sm] = data.windowStart.split(':').map(Number)
  const [eh, em] = data.windowEnd.split(':').map(Number)
  if (mins < (sh ?? 0) * 60 + (sm ?? 0) || mins > (eh ?? 0) * 60 + (em ?? 0)) return null
  return (
    <Card onClick={() => go('E8')} className="flex items-center gap-3">
      <span className="flex h-12 w-12 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
        <ForkKnife size={24} aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-body font-bold">Lunch ideas for you</span>
        <span className="block text-sub text-ink2">{data.options.map((o) => o.name).join(', ')}</span>
      </span>
      <CaretRight size={20} className="flex-none text-ink3" aria-hidden />
    </Card>
  )
}

/** Shown when the agent has noticed something and is waiting for the person to confirm, edit or delete it. */
function ToConfirmCard() {
  const { data } = useLearned()
  const go = useGo()
  if (!data || data.toConfirm === 0) return null
  return (
    <Card onClick={() => go('K2')} className="flex items-center gap-3">
      <span className="flex h-12 w-12 flex-none items-center justify-center rounded-full bg-brass-soft text-brass">
        <Bell size={24} aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-body font-bold">
          Smart Health noticed {data.toConfirm === 1 ? 'something' : `${data.toConfirm} things`}
        </span>
        <span className="block text-sub text-ink2">Check it is right. You can confirm, change or delete it.</span>
      </span>
      <CaretRight size={20} className="flex-none text-ink3" aria-hidden />
    </Card>
  )
}
