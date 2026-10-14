/**
 * F1 — Log a workout.
 *
 * The form follows the approved mock: what was done, how long, when it ended or started, how hard it felt and how the
 * person felt afterwards. The right-hand column shows this week against the goal, the link to the live strength session
 * and the last five workouts. A recent workout can be loaded into the form to edit it (PUT /logs/workout/{id}).
 *
 * New workouts are saved to `exercise_logs` and stretch across the 5-minute buckets of the Gold timeline. The week, the
 * day bars and the recent list are read from the database.
 */
import { useRef, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '@/data/repositories'
import { useFinishLog } from '@/features/log/useFinishLog'
import { useInsightsActivity, useUpdateWorkout, useWeekWorkouts } from '@/data/hooks'
import type { WorkoutLogInput } from '@/data/repositories/types'
import type { ExerciseKind, RecentEntry } from '@/data/types'
import { useGo } from '@/app/navigation'
import { href } from '@/app/routeIds'
import { useUi } from '@/state/store'
import { dateLocale } from '@/lib/locale'
import { cn } from '@/lib/cn'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Skeleton } from '@/ui/primitives'
import {
  Barbell,
  Broom,
  CaretRight,
  DotsThree,
  FlowerLotus,
  Lightning,
  MusicNotes,
  PersonSimpleBike,
  PersonSimpleRun,
  PersonSimpleSwim,
  PersonSimpleTaiChi,
  PersonSimpleWalk,
  SoccerBall,
  type IconType,
} from '@/ui/icons'
import { useWorkoutSession } from './useWorkoutSession'

const KINDS: { id: ExerciseKind; icon: IconType; key: string; label: string }[] = [
  { id: 'walking', icon: PersonSimpleWalk, key: 'workout.log.kind.walking', label: 'Walking' },
  { id: 'running', icon: PersonSimpleRun, key: 'workout.log.kind.running', label: 'Running' },
  { id: 'cycling', icon: PersonSimpleBike, key: 'workout.log.kind.cycling', label: 'Cycling' },
  { id: 'swimming', icon: PersonSimpleSwim, key: 'workout.log.kind.swimming', label: 'Swimming' },
  { id: 'hiit', icon: Lightning, key: 'workout.log.kind.hiit', label: 'HIIT' },
  { id: 'sports', icon: SoccerBall, key: 'workout.log.kind.sports', label: 'Sports' },
  { id: 'yoga_pilates', icon: FlowerLotus, key: 'workout.log.kind.yogaPilates', label: 'Yoga or pilates' },
  { id: 'stretching_mobility', icon: PersonSimpleTaiChi, key: 'workout.log.kind.stretching', label: 'Stretching' },
  { id: 'dance', icon: MusicNotes, key: 'workout.log.kind.dance', label: 'Dance' },
  { id: 'household_gardening', icon: Broom, key: 'workout.log.kind.household', label: 'Housework' },
  { id: 'strength', icon: Barbell, key: 'workout.log.kind.strength', label: 'Strength' },
  { id: 'other', icon: DotsThree, key: 'workout.log.kind.other', label: 'Something else' },
]
const DURATIONS = [10, 20, 30, 45, 60, 90]
const MIN_MINUTES = 1
const MAX_MINUTES = 600
const EFFORT_EN = [
  'Barely moving. You could chat or sing.',
  'Light. You can sing.',
  'Moderate. You can talk but not sing.',
  'Hard. You can only say a few words.',
  'All-out. You cannot talk.',
]
const FEEL_LABELS: [string, string][] = [
  ['workout.log.feel1', 'Awful'],
  ['workout.log.feel2', 'Not great'],
  ['workout.log.feel3', 'Okay'],
  ['workout.log.feel4', 'Good'],
  ['workout.log.feel5', 'Great'],
]
/* the words the server writes into a recent entry: the title is the activity name, or the kind's word when none was typed */
const TITLE_KIND: Record<string, ExerciseKind> = {
  walking: 'walking',
  walk: 'walking',
  running: 'running',
  run: 'running',
  cycling: 'cycling',
  swimming: 'swimming',
  hiit: 'hiit',
  sports: 'sports',
  'yoga or pilates': 'yoga_pilates',
  stretching: 'stretching_mobility',
  dance: 'dance',
  housework: 'household_gardening',
  'housework or gardening': 'household_gardening',
  strength: 'strength',
  exercise: 'other',
  'something else': 'other',
}
const INTENSITY_OF: Record<string, number> = { 'very light': 1, light: 2, moderate: 3, hard: 4, 'all-out': 5 }
/** The chart's colour for each weekly pace level: in line, a little behind, behind, well behind (same thresholds as the mock). */
const PACE: { text: string; bar: string; key: string; fallback: string }[] = [
  { text: 'text-ok', bar: 'bg-ok', key: 'workout.log.pace0', fallback: 'In line with your weekly goal' },
  { text: 'text-brass', bar: 'bg-brass', key: 'workout.log.pace1', fallback: 'A little behind your weekly goal' },
  { text: 'text-warn', bar: 'bg-warn', key: 'workout.log.pace2', fallback: 'Behind your weekly goal' },
  { text: 'text-danger', bar: 'bg-danger', key: 'workout.log.pace3', fallback: 'Well behind your weekly goal' },
]

const pad = (n: number) => String(n).padStart(2, '0')
/** The local calendar day as YYYY-MM-DD (the same form the server sends as `date`). */
const isoOf = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const daysFrom = (d: Date, n: number) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n)
const dayName = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString(dateLocale('en-GB'), { weekday: 'short', day: 'numeric', month: 'short' })
const clockOf = (d: Date) => d.toLocaleTimeString(dateLocale('en-US'), { hour: 'numeric', minute: '2-digit' }).toLowerCase()
const CLOCK = /^(\d{1,2}):(\d{2})\s*(am|pm)$/i

/** A whole number of minutes from 1 to 600, or null: the form has no default length, so the person types or picks one. */
function minutesFrom(text: string): number | null {
  if (!/^\d+$/.test(text.trim())) return null
  const n = Number(text.trim())
  return n >= MIN_MINUTES && n <= MAX_MINUTES ? n : null
}

/**
 * What a recent entry can tell the form. The list gives the activity name (or kind word), the minutes in the title,
 * the effort word, the day and the clock time for today's entries. It does not give the kind code, the exact start
 * time for older days, or the feeling answer: those are left for the person to pick.
 */
function loadRecent(e: RecentEntry) {
  const m = /,\s*(\d+)\s*min$/i.exec(e.title)
  const prefix = (m ? e.title.slice(0, m.index) : e.title).trim()
  const kind = TITLE_KIND[prefix.toLowerCase()] ?? null
  const c = CLOCK.exec(e.when.trim())
  let clock = ''
  if (c) {
    const h = (Number(c[1]) % 12) + (c[3]!.toLowerCase() === 'pm' ? 12 : 0)
    clock = `${pad(h)}:${c[2]}`
  }
  return {
    kind,
    /* a typed activity name that is not a kind word is kept, so saving does not rename it */
    note: kind ? '' : prefix,
    minutes: m ? m[1]! : '',
    effort: INTENSITY_OF[e.detail.trim().toLowerCase()] ?? null,
    day: e.date,
    clock,
    clockText: c ? e.when.trim() : '',
  }
}

function Panel({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn('rounded-card border border-line bg-card shadow-lift', className)}>{children}</div>
}

export function LogWorkout() {
  const { t } = useTranslation()
  const go = useGo()
  const navigate = useNavigate()
  const setLast = useUi((s) => s.setLastLog)
  const { data: week } = useWeekWorkouts()
  const { data: days } = useInsightsActivity(7)
  const live = useWorkoutSession((s) => s.session)
  const { save, pending, error } = useFinishLog()
  const update = useUpdateWorkout()
  const formRef = useRef<HTMLElement>(null)

  const today = new Date()
  const todayIso = isoOf(today)
  const yesterdayIso = isoOf(daysFrom(today, -1))

  /* the recent workout being edited, or null for a new one */
  const [editing, setEditing] = useState<RecentEntry | null>(null)
  const [kind, setKind] = useState<ExerciseKind | null>(null)
  /* a typed activity name, kept only when editing a workout that had one; saved as the activity, otherwise the kind's name is used */
  const [note, setNote] = useState('')
  /* empty until the person picks a length or types one: there is no default, and Save waits for it */
  const [minutesText, setMinutesText] = useState('')
  const minutes = minutesFrom(minutesText)
  /* null until the person picks 1 to 5, and it may stay null: the server stores null as not rated */
  const [effort, setEffort] = useState<number | null>(null)
  /* null until the person answers, and it may stay null: the server stores null as not answered */
  const [feeling, setFeeling] = useState<number | null>(null)
  const [when, setWhen] = useState<'just' | 'at'>('just')
  const [day, setDay] = useState(todayIso)
  /* empty until the person picks a start time (asked for only when "Pick a start time" is chosen) */
  const [time, setTime] = useState('')

  const cfg = KINDS.find((k) => k.id === kind)
  const timeMissing = when === 'at' && time === ''
  /** why Save is off, in plain words; null when the form is complete */
  const saveBlocker = !cfg
    ? t('workout.log.blockKind', 'Pick what kind of exercise it was.')
    : minutes == null
      ? t('workout.log.blockMinutes', 'Enter how many minutes it lasted, from 1 to 600.')
      : timeMissing
        ? t('workout.log.blockTime', 'Pick the start time.')
        : null

  const kindName = cfg ? t(cfg.key, cfg.label) : ''
  /* light effort is saved but does not count toward the active minutes (moderate or harder count) */
  const active = minutes != null && (effort == null || effort >= 3) ? minutes : 0
  const summary =
    cfg && minutes != null ? `${kindName} · ${minutes} min${effort ? ` · ${t('workout.log.effortOf', 'effort {{n}} of 5', { n: effort })}` : ''}` : null
  const summarySub = saveBlocker
    ? saveBlocker
    : active
      ? t('workout.log.counts', 'Counts as {{n}} active minutes toward this week.', { n: active })
      : t('workout.log.lightNote', 'Light effort: it is saved, and does not count as active minutes.')

  const pickKind = (k: (typeof KINDS)[number]) => {
    setKind(k.id)
    setNote('')
  }
  const startAt = (mins: number) => {
    if (when === 'just') return new Date(Date.now() - mins * 60_000)
    const [h, m] = time.split(':').map(Number)
    const d = new Date(`${day}T00:00:00`)
    d.setHours(h ?? 0, m ?? 0, 0, 0)
    return d
  }
  const resetForm = () => {
    setEditing(null)
    setKind(null)
    setNote('')
    setMinutesText('')
    setEffort(null)
    setFeeling(null)
    setWhen('just')
    setDay(todayIso)
    setTime('')
  }
  const startEdit = (e: RecentEntry) => {
    const l = loadRecent(e)
    setEditing(e)
    setKind(l.kind)
    setNote(l.note)
    setMinutesText(l.minutes)
    setEffort(l.effort)
    setFeeling(null)
    setWhen('at')
    setDay(l.day)
    setTime(l.clock)
    update.reset()
    formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    /* the saved entry has the exact kind, start, length, effort and feeling: replace the guesses above with it */
    api
      .getWorkout(e.id)
      .then((w) => {
        const k = KINDS.find((x) => x.id === w.type)
        const d = new Date(w.startAt)
        setKind((k?.id ?? null) as typeof kind)
        setNote(k && w.activity && w.activity !== k.label ? w.activity : '')
        setMinutesText(String(w.minutes))
        setEffort(w.intensity)
        setFeeling(w.feeling)
        setDay(`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`)
        setTime(`${pad(d.getHours())}:${pad(d.getMinutes())}`)
      })
      .catch(() => {})
  }
  const onSave = () => {
    if (!cfg || minutes == null || saveBlocker) return
    const input: WorkoutLogInput = {
      kind: 'workout',
      type: cfg.id,
      activity: note.trim() || cfg.label,
      intensity: effort,
      startAt: startAt(minutes).toISOString(),
      minutes,
      feeling,
    }
    if (editing) {
      update.mutate(
        { id: editing.id, input },
        {
          onSuccess: (res) => {
            setLast(res)
            navigate(res.urgent ? `${href('J1')}?tier=${res.urgentTier ?? 2}` : href('E6'), { replace: true })
          },
        },
      )
    } else save(input)
  }

  /* this week: the server's total against the goal, and what saving this one would add */
  const goal = week?.goalMin ?? 0
  const now = week?.activeMin ?? 0
  const pct = goal ? Math.min(100, (now / goal) * 100) : 0
  const addPct = goal ? Math.min(100 - pct, (active / goal) * 100) : 0
  const pace = (5 / 7) * goal
  const level = now >= pace * 0.9 ? 0 : now >= pace * 0.7 ? 1 : now >= pace * 0.4 ? 2 : 3
  const bars = (days?.bars ?? []).map((b) => {
    const mins = b.moderate + b.vigorous
    const total = b.light + b.moderate + b.vigorous
    return {
      key: b.firstDay,
      h: Math.min(40, Math.max(4, Math.round((total / 60) * 40))),
      active: mins > 0,
      letter: new Date(`${b.firstDay}T00:00:00`).toLocaleDateString('en-US', { weekday: 'narrow' }),
    }
  })
  const rangeText =
    days && days.bars.length
      ? t('workout.log.range', '{{from}} to {{to}}', { from: dayName(days.bars[0]!.firstDay), to: dayName(days.bars[days.bars.length - 1]!.lastDay) })
      : ''
  const updateError = update.isError ? t('workout.log.updateError', 'It could not be saved just now. Check your connection and try again.') : null

  return (
    <Screen wide>
      <Header title={t('workout.log.title', 'Log a workout')} back backTo="E1" sub={t('workout.log.sub', 'So your doctor can see how you really move.')} />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_332px] lg:items-start">
        <Panel className="flex flex-col gap-5 px-5 py-5 md:px-6">
          <section ref={formRef} className="flex scroll-mt-4 flex-col gap-5">
            {editing && (
              <Alert tone="info" onClose={resetForm} closeLabel={t('workout.log.cancelEdit', 'Cancel edit')}>
                {t('workout.log.editing', 'Editing {{title}}. Save changes, or cancel to log a new workout.', { title: editing.title })}
              </Alert>
            )}

            <div>
              <div className="mb-2.5 flex items-baseline justify-between gap-3">
                <p className="text-sub font-bold">{t('workout.log.kindQ', 'What did you do?')}</p>
                <p className="text-micro text-ink2">{t('workout.log.pickOne', 'Pick one')}</p>
              </div>
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-6" role="radiogroup" aria-label={t('workout.log.kindLabel', 'Kind of exercise')}>
                {KINDS.map((k) => {
                  const on = kind === k.id
                  return (
                    <button
                      key={k.id}
                      type="button"
                      role="radio"
                      aria-checked={on}
                      onClick={() => pickKind(k)}
                      className={cn(
                        'press flex min-h-[58px] min-w-0 flex-col items-center justify-center gap-0.5 rounded-[14px] border-[1.5px] px-1 py-2 text-center text-micro leading-tight sm:text-sub',
                        on ? 'border-brand bg-brand-soft font-bold text-brand' : 'border-line bg-card text-ink',
                      )}
                    >
                      <k.icon size={20} aria-hidden />
                      <span className="[overflow-wrap:anywhere]">{t(k.key, k.label)}</span>
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="grid gap-7 md:grid-cols-2">
              <div className="flex flex-col">
                <p className="mb-2.5 text-sub font-bold">{t('workout.log.howLong', 'How long?')}</p>
                <div className="flex flex-wrap gap-2">
                  {DURATIONS.map((d) => {
                    const on = minutes === d
                    return (
                      <button
                        key={d}
                        type="button"
                        aria-pressed={on}
                        onClick={() => setMinutesText(String(d))}
                        className={cn(
                          'press inline-flex min-h-12 items-center rounded-chip border-[1.5px] px-4 text-sub',
                          on ? 'border-brand bg-brand font-bold text-on-brand' : 'border-line bg-card text-ink',
                        )}
                      >
                        {d < 60 ? `${d} min` : d === 60 ? t('workout.log.oneHour', '1 hour') : t('workout.log.oneHalfHours', '1.5 hours')}
                      </button>
                    )
                  })}
                </div>
                <label
                  className={cn(
                    'mt-2.5 flex h-12 w-[240px] max-w-full items-center justify-between gap-3 rounded-field border-[1.5px] bg-card px-3.5',
                    minutesText.trim() !== '' && minutes == null ? 'border-danger' : 'border-line',
                  )}
                >
                  <span className="flex-none text-micro text-ink2">{t('workout.log.minutesLabel', 'Minutes')}</span>
                  <span className="flex items-baseline gap-1">
                    <input
                      value={minutesText}
                      onChange={(e) => setMinutesText(e.target.value)}
                      inputMode="numeric"
                      placeholder={t('workout.log.minutesPh', 'e.g. 30')}
                      aria-label={t('workout.log.minutesLabel', 'Minutes')}
                      className="num w-20 min-w-0 bg-transparent text-right text-body font-bold text-ink placeholder:font-normal placeholder:text-ink3 focus:outline-none"
                    />
                    <span className="flex-none text-micro text-ink2">min</span>
                  </span>
                </label>
                {minutesText.trim() !== '' && minutes == null && (
                  <p className="mt-1.5 text-micro text-danger">{t('workout.log.minutesError', 'Use a whole number of minutes, from 1 to 600.')}</p>
                )}
              </div>

              <div className="flex flex-col">
                <p className="mb-2.5 text-sub font-bold">{t('workout.log.when', 'When?')}</p>
                <div role="radiogroup" aria-label={t('workout.log.whenLabel', 'When')} className="inline-flex w-max gap-0.5 rounded-chip bg-well p-1">
                  {(
                    [
                      ['just', t('workout.log.justFinished', 'I just finished')],
                      ['at', t('workout.log.pickStart', 'Pick a start time')],
                    ] as const
                  ).map(([v, label]) => (
                    <button
                      key={v}
                      type="button"
                      role="radio"
                      aria-checked={when === v}
                      onClick={() => setWhen(v)}
                      className={cn('press h-9 min-w-[78px] rounded-chip px-3 text-sub', when === v ? 'bg-card font-bold text-ink shadow-lift' : 'text-ink2')}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {when === 'at' ? (
                  <div className="mt-2.5 flex flex-wrap items-center gap-2">
                    {(
                      [
                        [todayIso, t('workout.log.today', 'Today')],
                        [yesterdayIso, t('workout.log.yesterday', 'Yesterday')],
                      ] as [string, string][]
                    ).map(([iso, label]) => (
                      <button
                        key={iso}
                        type="button"
                        aria-pressed={day === iso}
                        onClick={() => setDay(iso)}
                        className={cn(
                          'press inline-flex min-h-12 items-center rounded-chip border-[1.5px] px-4 text-sub',
                          day === iso ? 'border-brand bg-brand font-bold text-on-brand' : 'border-line bg-card text-ink',
                        )}
                      >
                        {label}
                      </button>
                    ))}
                    {day !== todayIso && day !== yesterdayIso && (
                      <span className="inline-flex min-h-12 items-center rounded-chip border-[1.5px] border-brand bg-brand px-4 text-sub font-bold text-on-brand">
                        {dayName(day)}
                      </span>
                    )}
                    <input
                      type="time"
                      value={time}
                      onChange={(e) => setTime(e.target.value)}
                      aria-label={t('workout.log.startTime', 'Start time')}
                      aria-invalid={timeMissing}
                      className={cn(
                        'h-12 w-[130px] rounded-field border-[1.5px] bg-card px-3 text-body font-bold text-ink focus:border-brand focus:outline-none',
                        timeMissing ? 'border-danger' : 'border-line',
                      )}
                    />
                  </div>
                ) : (
                  <p className="mt-3 text-micro text-ink2">{t('workout.log.savedEnding', 'Saved as ending now, {{time}}.', { time: clockOf(today) })}</p>
                )}
              </div>
            </div>

            <div className="grid gap-7 md:grid-cols-2">
              <div>
                <div className="mb-2.5 flex items-baseline justify-between gap-3">
                  <p className="text-sub font-bold">{t('workout.log.hard', 'How hard did it feel?')}</p>
                  <p className="flex-none text-micro text-ink2">{t('workout.log.optional', 'Optional')}</p>
                </div>
                <div role="radiogroup" aria-label={t('workout.log.hard', 'How hard did it feel?')} className="grid grid-cols-5 gap-2">
                  {[1, 2, 3, 4, 5].map((n) => {
                    const on = effort === n
                    return (
                      <button
                        key={n}
                        type="button"
                        role="radio"
                        aria-checked={on}
                        onClick={() => setEffort(on ? null : n)}
                        className={cn(
                          'press h-12 rounded-[12px] border-[1.5px] text-body font-bold',
                          on ? 'border-brand bg-brand text-on-brand' : 'border-line bg-card text-ink',
                        )}
                      >
                        {n}
                      </button>
                    )
                  })}
                </div>
                <p className="mt-2 min-h-[18px] text-micro text-ink2">
                  {effort == null
                    ? t('workout.log.optionalEffort', 'Pick a number from 1 to 5 if you want to note it.')
                    : t(`workout.log.effort${effort}`, EFFORT_EN[effort - 1]!)}
                </p>
              </div>

              <div>
                <div className="mb-2.5 flex items-baseline justify-between gap-3">
                  <p className="text-sub font-bold">{t('workout.log.feel', 'How did you feel after?')}</p>
                  <p className="flex-none text-micro text-ink2">{t('workout.log.optional', 'Optional')}</p>
                </div>
                <div role="radiogroup" aria-label={t('workout.log.feel', 'How did you feel after?')} className="grid grid-cols-5 gap-2">
                  {FEEL_LABELS.map(([key, fallback], i) => {
                    const n = i + 1
                    const on = feeling === n
                    return (
                      <button
                        key={key}
                        type="button"
                        role="radio"
                        aria-checked={on}
                        onClick={() => setFeeling(on ? null : n)}
                        className={cn(
                          'press flex min-h-12 items-center justify-center rounded-[12px] border-[1.5px] px-1 text-center text-micro font-bold leading-tight',
                          on ? 'border-brand bg-brand text-on-brand' : 'border-line bg-card text-ink',
                        )}
                      >
                        {t(key, fallback)}
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>

            {feeling === 1 && (
              <Alert tone="warn" onClick={() => go('E4')}>
                {t('workout.log.unwell', 'Feeling unwell after exercise? Tap to log a symptom.')}
              </Alert>
            )}
            {(error || updateError) && <Alert tone="danger">{error ?? updateError}</Alert>}

            <div className="flex flex-col gap-3 border-t border-line pt-4 sm:flex-row sm:items-center sm:gap-3.5">
              <div className="min-w-0 flex-1">
                <p className="text-body font-bold leading-snug">{summary ?? t('workout.log.nothing', 'Nothing to save yet')}</p>
                <p className="text-micro text-ink2">{summary ? summarySub : saveBlocker}</p>
              </div>
              <Button size="md" className="sm:w-auto sm:px-6" disabled={!!saveBlocker || pending || update.isPending} onClick={onSave}>
                {pending || update.isPending
                  ? t('workout.log.saving', 'Saving…')
                  : editing
                    ? t('workout.log.saveChanges', 'Save changes')
                    : t('workout.log.save', 'Save workout')}
              </Button>
            </div>
          </section>
        </Panel>

        <section className="flex flex-col gap-4">
          <Panel className="p-4">
            <div className="mb-2.5 flex items-baseline justify-between gap-2">
              <p className="text-sub font-bold">{t('workout.log.week', 'This week')}</p>
              <p className="text-micro text-ink2">{rangeText}</p>
            </div>
            {week ? (
              <>
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-micro text-ink2">{t('workout.log.activeMin', 'Active minutes')}</span>
                  <span className="num text-body font-bold">
                    {now} <span className="text-micro font-normal text-ink2">{t('workout.log.ofGoalMin', 'of {{goal}} min', { goal })}</span>
                  </span>
                </div>
                <div
                  className="relative my-2 h-2.5 overflow-hidden rounded-full bg-well"
                  role="progressbar"
                  aria-valuenow={now}
                  aria-valuemin={0}
                  aria-valuemax={goal}
                  aria-label={t('workout.log.activeMin', 'Active minutes')}
                >
                  <div
                    className={cn('absolute bottom-0 left-0 top-0 rounded-full transition-[width] duration-700', PACE[level]!.bar)}
                    style={{ width: `${pct}%` }}
                  />
                  {addPct > 0 && (
                    <div className={cn('absolute bottom-0 top-0 rounded-full opacity-40', PACE[level]!.bar)} style={{ left: `${pct}%`, width: `${addPct}%` }} />
                  )}
                </div>
                <p className={cn('flex items-center gap-1.5 text-micro font-bold', PACE[level]!.text)}>
                  <span className="h-2 w-2 flex-none rounded-full bg-current" aria-hidden />
                  {t(PACE[level]!.key, PACE[level]!.fallback)}
                  {active ? ` · ${t('workout.log.ifSave', '{{n}} min if you save', { n: now + active })}` : ''}
                </p>
                <div className="mt-3 flex h-[62px] items-end gap-[7px]">
                  {bars.map((b, i) => (
                    <div key={b.key} className="flex h-full flex-1 flex-col items-center justify-end gap-[3px]">
                      <div
                        className="w-full rounded-[5px]"
                        style={{
                          height: b.h,
                          background:
                            i === bars.length - 1 ? 'var(--c-brand)' : b.active ? 'color-mix(in oklab, var(--c-brand) 50%, var(--c-card))' : 'var(--c-line)',
                        }}
                      />
                      <span className="text-[10px] leading-[11px] text-ink2">{b.letter}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-3.5 flex items-baseline justify-between border-t border-line pt-3">
                  <span className="text-micro text-ink2">{t('workout.log.strength', 'Strength sessions')}</span>
                  <span className="num text-body font-bold">
                    {week.strengthSessions}{' '}
                    <span className="text-micro font-normal text-ink2">{t('workout.log.ofGoalPlain', 'of {{goal}}', { goal: week.goalStrength })}</span>
                  </span>
                </div>
                <p className={cn('mt-1 flex items-center gap-1.5 text-micro font-bold', week.strengthSessions ? 'text-brand' : 'text-warn')}>
                  <span className="h-2 w-2 flex-none rounded-full bg-current" aria-hidden />
                  {week.strengthSessions ? t('workout.log.strengthLogged', 'Logged this week') : t('workout.log.strengthNone', 'None yet this week')}
                </p>
                <p className="mt-2.5 text-[11px] leading-[14px] text-ink2">
                  {t('workout.log.activeNote', 'Active minutes count moderate effort or harder. Goals are placeholders, set with your doctor later.')}
                </p>
              </>
            ) : (
              <Skeleton className="h-48" />
            )}
          </Panel>

          <button
            type="button"
            onClick={() => go('F2')}
            className="press flex w-full items-center gap-3 rounded-card border border-line bg-card p-3.5 text-left shadow-lift"
          >
            <span className="flex h-10 w-10 flex-none items-center justify-center rounded-[12px] bg-brand-soft text-brand">
              <Barbell size={22} aria-hidden />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-body font-bold leading-snug">
                {live ? t('workout.log.resume', 'Resume your live session') : t('workout.log.liveSession', 'Live strength session')}
              </span>
              <span className="block text-micro text-ink2">{t('workout.log.liveSub', 'Timer, sets, weights and a rest timer.')}</span>
            </span>
            <CaretRight size={20} className="flex-none text-ink3" aria-hidden />
          </button>

          {week && (
            <Panel className="px-3.5 pb-2 pt-4">
              <div className="mb-1 flex items-baseline justify-between px-0.5">
                <p className="text-sub font-bold">{t('workout.log.recent', 'Recent workouts')}</p>
                <p className="text-micro text-ink2">{t('workout.log.last5', 'last 5')}</p>
              </div>
              {week.recent.length === 0 ? (
                <p className="px-0.5 py-3 text-micro text-ink2">{t('workout.log.noRecent', 'No workouts logged yet.')}</p>
              ) : (
                <ul className="divide-y divide-line">
                  {week.recent.slice(0, 5).map((e) => {
                    const l = loadRecent(e)
                    const Icon = KINDS.find((k) => k.id === l.kind)?.icon ?? DotsThree
                    const dayPart =
                      e.date === todayIso
                        ? t('workout.log.today', 'Today')
                        : e.date === yesterdayIso
                          ? t('workout.log.yesterday', 'Yesterday')
                          : dayName(e.date)
                    const sub = [dayPart, l.clockText].filter(Boolean).join(', ')
                    const isEditing = editing?.id === e.id
                    return (
                      <li key={e.id} className="flex items-center gap-3 py-2.5">
                        <span className="flex h-[34px] w-[34px] flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
                          <Icon size={18} aria-hidden />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block text-sub font-bold leading-snug [overflow-wrap:anywhere]">{e.title}</span>
                          <span className="block text-micro leading-snug text-ink2">{sub}</span>
                        </span>
                        <span className="flex-none whitespace-nowrap rounded-lg bg-well px-2 py-0.5 text-micro font-bold">
                          {l.effort == null ? t('workout.log.notRated', 'Not rated') : t('workout.log.effortChip', 'Effort {{n}}', { n: l.effort })}
                        </span>
                        <button
                          type="button"
                          onClick={() => startEdit(e)}
                          disabled={isEditing}
                          aria-label={t('workout.log.editAria', 'Edit {{title}}', { title: e.title })}
                          className="press min-h-10 flex-none px-1 text-micro font-bold text-brand underline underline-offset-4 disabled:text-ink3 disabled:no-underline"
                        >
                          {isEditing ? t('workout.log.editing_short', 'Editing') : t('workout.log.edit', 'Edit')}
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
            </Panel>
          )}

          <button
            type="button"
            onClick={() => go('K2')}
            className="press flex w-full items-center gap-3 rounded-card border border-line bg-card p-3.5 text-left shadow-lift"
          >
            <span className="min-w-0 flex-1 text-sub font-bold text-brand underline underline-offset-4">
              {t('workout.log.learnt', 'See what Smart Health has learnt')}
            </span>
            <CaretRight size={20} className="flex-none text-ink3" aria-hidden />
          </button>
        </section>
      </div>
    </Screen>
  )
}
