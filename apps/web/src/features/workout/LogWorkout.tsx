/**
 * F1 — Log a workout.
 *
 * Two ways in: a live strength session with sets and weights (F2), or a quick log for anything else. Both are saved to
 * `exercise_logs` and stretch across the 5-minute buckets of the Gold timeline. The week's progress and the recent
 * sessions are read from the database.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useFinishLog } from '@/features/log/useFinishLog'
import { useWeekWorkouts } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useWorkoutSession } from './useWorkoutSession'
import type { ExerciseKind } from '@/data/types'
import { cn } from '@/lib/cn'
import { Header, Footer, Screen, Split } from '@/ui/layout'
import { Rating } from '@/ui/controls'
import { Alert, Button, Card, Chip, Field, SectionTitle, Skeleton } from '@/ui/primitives'
import { Barbell, Broom, CaretRight, DotsThree, FlowerLotus, Lightning, MusicNotes, PersonSimpleBike, PersonSimpleRun, PersonSimpleSwim, PersonSimpleTaiChi, PersonSimpleWalk, SoccerBall, type IconType } from '@/ui/icons'

const KINDS: { id: ExerciseKind; label: string; icon: IconType; names: string[] }[] = [
  { id: 'walking', label: 'Walking', icon: PersonSimpleWalk, names: ['Brisk walk', 'Easy walk', 'Hike'] },
  { id: 'running', label: 'Running', icon: PersonSimpleRun, names: ['Jog', 'Run', 'Treadmill'] },
  { id: 'cycling', label: 'Cycling', icon: PersonSimpleBike, names: ['Outdoor ride', 'Stationary bike'] },
  { id: 'swimming', label: 'Swimming', icon: PersonSimpleSwim, names: ['Laps', 'Water aerobics'] },
  { id: 'hiit', label: 'HIIT', icon: Lightning, names: ['Circuit', 'Intervals'] },
  { id: 'sports', label: 'Sports', icon: SoccerBall, names: ['Badminton', 'Basketball', 'Football', 'Tennis', 'Table tennis'] },
  { id: 'yoga_pilates', label: 'Yoga or pilates', icon: FlowerLotus, names: ['Yoga', 'Pilates', 'Tai chi'] },
  { id: 'stretching_mobility', label: 'Stretching', icon: PersonSimpleTaiChi, names: ['Stretching', 'Mobility', 'Balance'] },
  { id: 'dance', label: 'Dance', icon: MusicNotes, names: ['Zumba', 'Line dance', 'Social dance'] },
  { id: 'household_gardening', label: 'Housework or gardening', icon: Broom, names: ['Cleaning', 'Gardening', 'Carrying shopping'] },
  { id: 'strength', label: 'Strength', icon: Barbell, names: ['Weights', 'Resistance bands', 'Bodyweight'] },
  { id: 'other', label: 'Something else', icon: DotsThree, names: [] },
]
const PRESETS = [15, 20, 30, 45, 60, 90]
const MIN_MINUTES = 1
const MAX_MINUTES = 600

/** A whole number of minutes from 1 to 600, or null: the form has no default length, so the person types or picks one. */
function minutesFrom(text: string): number | null {
  if (!/^\d+$/.test(text.trim())) return null
  const n = Number(text.trim())
  return n >= MIN_MINUTES && n <= MAX_MINUTES ? n : null
}

function Bar({ label, value, goal, unit }: { label: string; value: number; goal: number; unit?: string }) {
  const { t } = useTranslation()
  const pct = Math.min(100, goal ? (value / goal) * 100 : 0)
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between text-sub">
        <span className="font-bold">{label}</span>
        <span className="num text-ink2">
          {t('workout.log.ofGoal', '{{value}} of {{goal}}', { value, goal })}
          {unit ? ` ${unit}` : ''}
        </span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-well" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={goal} aria-label={label}>
        <div className="h-full rounded-full bg-brand transition-[width] duration-700" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export function LogWorkout() {
  const { t } = useTranslation()
  const EFFORT_HELP: Record<number, string> = {
    1: t('workout.log.effort1', 'Barely moving. You could chat or sing.'),
    2: t('workout.log.effort2', 'Light. You can sing.'),
    3: t('workout.log.effort3', 'Moderate. You can talk but not sing.'),
    4: t('workout.log.effort4', 'Hard. You can only say a few words.'),
    5: t('workout.log.effort5', 'All-out. You cannot talk.'),
  }
  /* display names only: the English kind is what is saved when no name is typed */
  const kindLabel: Record<ExerciseKind, string> = {
    walking: t('workout.log.kind.walking', 'Walking'),
    running: t('workout.log.kind.running', 'Running'),
    cycling: t('workout.log.kind.cycling', 'Cycling'),
    swimming: t('workout.log.kind.swimming', 'Swimming'),
    hiit: t('workout.log.kind.hiit', 'HIIT'),
    sports: t('workout.log.kind.sports', 'Sports'),
    yoga_pilates: t('workout.log.kind.yogaPilates', 'Yoga or pilates'),
    stretching_mobility: t('workout.log.kind.stretching', 'Stretching'),
    dance: t('workout.log.kind.dance', 'Dance'),
    household_gardening: t('workout.log.kind.household', 'Housework or gardening'),
    strength: t('workout.log.kind.strength', 'Strength'),
    other: t('workout.log.kind.other', 'Something else'),
  }
  const go = useGo()
  const { data: week } = useWeekWorkouts()
  const live = useWorkoutSession((s) => s.session)
  const { save, pending, error } = useFinishLog()
  const [kind, setKind] = useState<ExerciseKind | null>(null)
  const [name, setName] = useState('')
  /* empty until the person types or picks a length: there is no default, and Save waits for it */
  const [minutesText, setMinutesText] = useState('')
  const minutes = minutesFrom(minutesText)
  /* null until the person picks 1 to 5, and it may stay null: no default. The server stores null as not rated. */
  const [effort, setEffort] = useState<number | null>(null)
  /* null until the person answers, and it may stay null: no default. The server stores null as not answered. */
  const [feeling, setFeeling] = useState<number | null>(null)
  const [when, setWhen] = useState<'just' | 'at'>('just')
  const [day, setDay] = useState<'today' | 'yesterday'>('today')
  /* empty until the person picks a start time (only asked for when "Pick a start time" is chosen) */
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

  const pickKind = (k: (typeof KINDS)[number]) => {
    setKind(k.id)
    setName('')
  }
  const startAt = (mins: number) => {
    if (when === 'just') return new Date(Date.now() - mins * 60_000)
    const [h, m] = time.split(':').map(Number)
    const d = new Date()
    if (day === 'yesterday') d.setDate(d.getDate() - 1)
    d.setHours(h ?? 0, m ?? 0, 0, 0)
    return d
  }

  return (
    <Screen>
      <Header title={t('workout.log.title', 'Log a workout')} back backTo="E1" sub={t('workout.log.sub', 'So your doctor can see how you really move.')} />

      <Split>
        <section className="flex flex-col gap-4">
          <Card tone="hero" className="flex flex-col gap-3">
            <SectionTitle>{t('workout.log.week', 'This week')}</SectionTitle>
            {week ? (
              <>
                <Bar label={t('workout.log.activeMin', 'Active minutes')} value={week.activeMin} goal={week.goalMin} unit="min" />
                <Bar label={t('workout.log.strength', 'Strength sessions')} value={week.strengthSessions} goal={week.goalStrength} />
                <p className="text-sub text-ink3">{t('workout.log.activeNote', 'Active minutes count moderate effort or harder. Goals are placeholders, set with your doctor.')}</p>
              </>
            ) : (
              <Skeleton className="h-24" />
            )}
          </Card>

          <Card onClick={() => go('F2')} className="flex items-center gap-3">
            <span className="flex h-12 w-12 flex-none items-center justify-center rounded-full bg-brand text-on-brand">
              <Barbell size={26} aria-hidden />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-body font-bold">{live ? t('workout.log.resume', 'Resume your live session') : t('workout.log.liveSession', 'Live strength session')}</span>
              <span className="block text-sub text-ink2">{t('workout.log.liveSub', 'Timer, sets, weights and a rest timer.')}</span>
            </span>
            <CaretRight size={20} className="flex-none text-ink3" aria-hidden />
          </Card>

          {week && week.recent.length > 0 && (
            <section className="flex flex-col gap-1">
              <SectionTitle>{t('workout.log.recent', 'Recent workouts')}</SectionTitle>
              <ul className="divide-y divide-line rounded-card border border-line bg-card px-4">
                {week.recent.map((e) => (
                  <li key={e.id} className="flex items-center justify-between gap-3 py-3">
                    <span className="min-w-0">
                      <span className="block text-body font-bold leading-snug">{e.title}</span>
                      <span className="block text-sub text-ink2">{e.detail}</span>
                    </span>
                    <span className="flex-none text-sub text-ink3">{e.when}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </section>

        <section className="flex flex-col gap-4">
          <SectionTitle>{t('workout.log.quick', 'Quick log')}</SectionTitle>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3" role="radiogroup" aria-label={t('workout.log.kindLabel', 'Kind of exercise')}>
            {KINDS.map((k) => {
              const on = kind === k.id
              return (
                <button
                  key={k.id}
                  type="button"
                  role="radio"
                  aria-checked={on}
                  onClick={() => pickKind(k)}
                  className={cn('press flex min-h-[72px] min-w-0 flex-col items-start justify-between gap-1 rounded-card border-[1.5px] p-3 text-left', on ? 'border-brand bg-brand-soft text-brand' : 'border-line bg-card text-ink')}
                >
                  <k.icon size={22} aria-hidden />
                  <span className="min-w-0 [overflow-wrap:anywhere] text-sub font-bold leading-tight">{kindLabel[k.id]}</span>
                </button>
              )
            })}
          </div>

          {cfg && (
            <>
              {kind === 'strength' && (
                <Alert tone="info" icon={Barbell} onClick={() => go('F2')}>
                  {t('workout.log.strengthTip', 'Want every set and weight? Tap here to track a live strength session instead.')}
                </Alert>
              )}
              {cfg.names.length > 0 && (
                <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t('workout.log.which', 'Which one')}>
                  {cfg.names.map((n) => (
                    <Chip key={n} on={name === n} onClick={() => setName(name === n ? '' : n)}>
                      {n}
                    </Chip>
                  ))}
                </div>
              )}
              <Field label={cfg.names.length ? t('workout.log.orName', 'Or name it (optional)') : t('workout.log.name', 'Name it')} value={name} onChange={setName} placeholder={t('workout.log.namePh', 'For example, evening walk with Ah Ma')} />

              <section className="flex flex-col gap-2">
                <p className="text-body font-bold">{t('workout.log.howLong', 'How long?')}</p>
                <div className="flex flex-wrap gap-2">
                  {PRESETS.map((p) => (
                    <Chip key={p} on={minutes === p} onClick={() => setMinutesText(String(p))}>
                      {p < 60 ? `${p} min` : p === 60 ? t('workout.log.oneHour', '1 hour') : t('workout.log.oneHalfHours', '1.5 hours')}
                    </Chip>
                  ))}
                </div>
                <Field
                  label={t('workout.log.minutesLabel', 'Minutes')}
                  value={minutesText}
                  onChange={setMinutesText}
                  inputMode="numeric"
                  suffix="min"
                  placeholder={t('workout.log.minutesPh', 'For example 30')}
                  error={minutesText.trim() !== '' && minutes == null ? t('workout.log.minutesError', 'Use a whole number of minutes, from 1 to 600.') : undefined}
                />
              </section>

              <section className="flex flex-col gap-2">
                <p className="text-body font-bold">{t('workout.log.when', 'When?')}</p>
                <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t('workout.log.whenLabel', 'When')}>
                  <Chip on={when === 'just'} onClick={() => setWhen('just')}>
                    {t('workout.log.justFinished', 'I just finished')}
                  </Chip>
                  <Chip on={when === 'at'} onClick={() => setWhen('at')}>
                    {t('workout.log.pickStart', 'Pick a start time')}
                  </Chip>
                </div>
                {when === 'at' && (
                  <div className="flex flex-wrap items-center gap-2">
                    <Chip on={day === 'today'} onClick={() => setDay('today')}>
                      {t('workout.log.today', 'Today')}
                    </Chip>
                    <Chip on={day === 'yesterday'} onClick={() => setDay('yesterday')}>
                      {t('workout.log.yesterday', 'Yesterday')}
                    </Chip>
                    <input type="time" value={time} onChange={(e) => setTime(e.target.value)} aria-label={t('workout.log.startTime', 'Start time')} aria-invalid={timeMissing} className="min-h-12 rounded-field border-[1.5px] border-line bg-card px-3.5 text-body text-ink focus:border-brand focus:outline-none" />
                  </div>
                )}
              </section>

              <div className="flex flex-col gap-1">
                <Rating label={t('workout.log.hard', 'How hard did it feel?')} value={effort} onChange={setEffort} lowLabel={t('workout.log.veryLight', 'Very light')} highLabel={t('workout.log.allOut', 'All-out')} />
                <p className="text-sub text-ink2">{effort == null ? t('workout.log.optionalEffort', 'Optional. Pick a number from 1 to 5 if you want to note it.') : EFFORT_HELP[effort]}</p>
              </div>
              <div className="flex flex-col gap-1">
                <Rating label={t('workout.log.feel', 'How did you feel afterwards?')} value={feeling} onChange={setFeeling} lowLabel={t('workout.log.awful', 'Awful')} highLabel={t('workout.log.great', 'Great')} />
                <p className="text-sub text-ink2">{t('workout.log.optional', 'Optional')}</p>
              </div>
              {feeling === 1 && (
                <Alert tone="warn" onClick={() => go('E4')}>
                  {t('workout.log.unwell', 'Feeling unwell after exercise? Tap to log a symptom.')}
                </Alert>
              )}
            </>
          )}
          {error && <Alert tone="danger">{error}</Alert>}
        </section>
      </Split>

      <Footer>
        {saveBlocker && <p className="text-sub text-ink2">{saveBlocker}</p>}
        <Button disabled={!!saveBlocker || pending} onClick={() => cfg && minutes != null && save({ kind: 'workout', type: cfg.id, activity: name.trim() || cfg.label, intensity: effort, startAt: startAt(minutes).toISOString(), minutes, feeling })}>
          {pending ? t('workout.log.saving', 'Saving…') : t('workout.log.save', 'Save workout')}
        </Button>
      </Footer>
    </Screen>
  )
}
