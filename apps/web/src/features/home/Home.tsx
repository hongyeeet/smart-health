/**
 * B1 — Home: today's logging at a glance.
 *
 * Shows what has been logged today against what is expected by this time of day, a streak, the week's activity, and one
 * clear "next up" action, so the person always knows which log to do next. Everything comes from the database
 * (GET /logs/today); the bell opens the reminders (B2).
 */
import { Trans, useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
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
import { useSimulate, useUrgentState } from '@/features/urgent/api'
import { Barbell, Bell, CaretRight, CheckCircle, Circle, ForkKnife, Lightning, PersonSimpleWalk, Smiley, Thermometer, WarningCircle, type IconType } from '@/ui/icons'

const ICON: Record<ProgressItem['key'], IconType> = { meals: ForkKnife, checkin: Smiley, workout: PersonSimpleWalk, symptom: Thermometer }

function greeting(h: number, t: TFunction) {
  return h < 12 ? t('home.greeting.morning', 'Good morning') : h < 18 ? t('home.greeting.afternoon', 'Good afternoon') : t('home.greeting.evening', 'Good evening')
}

function Ring({ done, total }: { done: number; total: number }) {
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
    <button type="button" onClick={onOpen} aria-label={now ? t('home.row.due', '{{label}}. A good time to log this.', { label: item.label }) : undefined} className={cn('press flex items-center gap-3 py-3 text-left', now ? '-mx-4 w-[calc(100%+2rem)] rounded-[14px] bg-brand-soft/70 px-4' : 'w-full')}>
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

export function Home() {
  const { t } = useTranslation()
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
        title={greeting(now.getHours(), t)}
        sub={dateLabel}
        trailing={
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => go('B2')} aria-label={t('home.bell', 'Notifications and alerts, {{n}} new', { n: unread })} className="press relative flex h-12 w-12 items-center justify-center rounded-full border border-line bg-card">
              <Bell size={24} aria-hidden />
              {unread > 0 && <span className="absolute right-2.5 top-2.5 h-2.5 w-2.5 rounded-full bg-brass ring-2 ring-card" />}
            </button>
            <UserSwitch />
          </div>
        }
      />
      <UrgentBanner />
      <MealBanner />
      <DoseCard />
      {isError && (
        <Alert tone="warn" onClick={() => void refetch()}>
          {t('home.loadError', "We could not load today's logs. Tap to try again.")}
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
                    <p className="text-sub font-bold text-ink3">{data.nextUp?.prompt ? t('home.hero.goodTime', 'A good time to log') : t('home.hero.today', "Today's logging")}</p>
                    <p className="text-h2 font-bold leading-snug">
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
                {data.nextUp && <Button variant={data.nextUp.prompt ? 'primary' : 'secondary'} onClick={() => go(data.nextUp!.to)}>{data.nextUp.key === 'meals' ? t('home.action.meal', 'Log a meal') : data.nextUp.key === 'checkin' ? t('home.action.checkin', 'Do the check-in') : t('home.action.workout', 'Log a workout')}</Button>}
              </Card>
              <Card className="flex flex-col gap-2">
                <SectionTitle>{t('home.week', 'This week')}</SectionTitle>
                <Bar label={t('home.bar.activeMin', 'Active minutes')} value={data.weekActivityMin} goal={data.weekActivityGoal} unit="min" />
                <Bar label={t('home.bar.strength', 'Strength sessions')} value={data.weekStrengthSessions} goal={data.weekStrengthGoal} unit="" />
                <button type="button" onClick={() => go('F1')} className="press mt-1 flex items-center gap-2 self-start text-sub font-bold text-brand">
                  <Barbell size={18} aria-hidden /> {t('home.action.workout', 'Log a workout')}
                </button>
              </Card>
              <ToConfirmCard />
              <FoodFlagCard />
              <LunchCard />
            </section>
            <section className="flex flex-col gap-1">
              <SectionTitle>{t('home.whatToLog', 'What to log today')}</SectionTitle>
              <div className="divide-y divide-line rounded-card border border-line bg-card px-4">
                {data.items.map((i) => (
                  <Row key={i.key} item={i} onOpen={() => go(i.to)} />
                ))}
              </div>
              <p className="px-1 pt-1 text-sub text-ink3">{t('home.sensor', 'Glucose comes from your sensor, so there is nothing to type.')}</p>
            </section>
          </Split>
        </Reveal>
      )}
      <DemoLowLink />
    </Screen>
  )
}

/** Shown first on Home while a low glucose alert is open. */
function UrgentBanner() {
  const { t } = useTranslation()
  const { data } = useUrgentState()
  const go = useGo()
  if (!data || (data.status !== 'active' && data.status !== 'escalated')) return null
  return (
    <Alert tone="danger" icon={WarningCircle} title={data.tier === 'very_low' ? t('home.urgent.veryLow', 'Very low glucose alert') : t('home.urgent.low', 'Low glucose alert')} onClick={() => go('J1')}>
      {t('home.urgent.body', 'Your glucose looks low: {{value}} mmol/L{{demo}}. Tap to see what to do.', { value: data.value?.toFixed(1) ?? '', demo: data.demo ? t('home.urgent.demo', ' (demo)') : '' })}
    </Alert>
  )
}

/** Demo only: the sample data stops on 2 Oct, so a real low reading cannot happen on stage. */
function DemoLowLink() {
  const { t } = useTranslation()
  const sim = useSimulate()
  const go = useGo()
  return (
    <p className="px-1 text-center text-micro text-ink3">
      {t('home.demo.label', 'Demo:')}{' '}
      <button type="button" disabled={sim.isPending} onClick={() => sim.mutate(3.4, { onSuccess: () => go('J1') })} className="press min-h-11 px-2 font-bold underline">
        {t('home.demo.simulate', 'Simulate a low reading')}
      </button>
    </p>
  )
}

function Bar({ label, value, goal, unit }: { label: string; value: number; goal: number; unit: string }) {
  const { t } = useTranslation()
  const pct = Math.min(100, goal ? (value / goal) * 100 : 0)
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between text-sub">
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

const NUTRIENT: Record<string, [string, string]> = { kcal: ['calories', 'kcal'], sodium_mg: ['salt', 'mg'], carbs_g: ['carbs', 'g'], sugar_g: ['sugar', 'g'], protein_g: ['protein', 'g'], fat_g: ['fat', 'g'], fibre_g: ['fibre', 'g'] }

/** A food habit the memory loop noticed, with a lighter dish to try next time and exactly what it would change. */
function FoodFlagCard() {
  const { t } = useTranslation()
  const { data } = useFoodFlags()
  const dismiss = useDismissSuggestion()
  const go = useGo()
  const h = data?.find((x) => x.alternatives.length > 0) ?? data?.[0]
  if (!h) return null
  const alt = h.alternatives[0]
  return (
    <Card className="flex flex-col gap-3">
      <SectionTitle>{t('home.worth.title', 'Worth a look')}</SectionTitle>
      <p className="text-body">
        <Trans i18nKey="home.worth.body" defaults="You have had {{label}} <0>{{n}} times</0> in the last 2 weeks, about <1>{{kcal}}</1> kcal and <2>{{sodium}}</2> mg salt each. Those are your own logged numbers." values={{ label: h.label, n: h.n, kcal: Math.round(h.avg.kcal ?? 0).toLocaleString('en-US'), sodium: Math.round(h.avg.sodium_mg ?? 0).toLocaleString('en-US') }} components={[<b key="0" />, <b key="1" className="num" />, <b key="2" className="num" />]} />
      </p>
      {alt && (
        <div className="flex flex-col gap-2 rounded-card bg-well p-3.5">
          <p className="text-sub text-ink2">{t('home.worth.heaviest', 'Your {{dish}} ({{n}} times) is the heaviest. Next time you could try', { dish: h.topDish, n: h.topDishN })}</p>
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
            {t('home.worth.servingNote', '{{serving}} {{source}}. Typical values, so your portion may differ.', { serving: alt.serving, source: alt.sourceGrade ? t('home.worth.sgDb', '· from the Singapore food database ({{grade}})', { grade: alt.sourceGrade.replace('_', ' ') }) : '' })}
          </p>
        </div>
      )}
      {h.outcomeText && <p className="rounded-card bg-ok-soft p-3.5 text-sub text-ink">{h.outcomeText}</p>}
      <p className="text-sub text-ink3">{t('home.worth.notAdvice', 'An idea for next time, not advice. Your logged meals are never changed.')}</p>
      {alt && (
        <button type="button" onClick={() => dismiss.mutate(`swap:${alt.foodId}`)} className="press self-start text-sub font-bold text-ink2">
          {t('home.worth.notForMe', 'Not for me')}
        </button>
      )}
      <button type="button" onClick={() => go('E2')} className="press flex items-center gap-2 self-start text-sub font-bold text-brand">
        <ForkKnife size={18} aria-hidden /> {t('home.action.meal', 'Log a meal')}
      </button>
    </Card>
  )
}

/** Shown only inside the person's lunch window. */
function LunchCard() {
  const { t } = useTranslation()
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
        <span className="block text-body font-bold">{t('home.lunch.title', 'Lunch ideas for you')}</span>
        <span className="block text-sub text-ink2">{data.options.map((o) => o.name).join(', ')}</span>
      </span>
      <CaretRight size={20} className="flex-none text-ink3" aria-hidden />
    </Card>
  )
}

/** Shown when the agent has noticed something and is waiting for the person to confirm, edit or delete it. */
function ToConfirmCard() {
  const { t } = useTranslation()
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
          {data.toConfirm === 1 ? t('home.noticed.one', 'Smart Health noticed something') : t('home.noticed.many', 'Smart Health noticed {{n}} things', { n: data.toConfirm })}
        </span>
        <span className="block text-sub text-ink2">{t('home.noticed.check', 'Check it is right. You can confirm, change or delete it.')}</span>
      </span>
      <CaretRight size={20} className="flex-none text-ink3" aria-hidden />
    </Card>
  )
}
