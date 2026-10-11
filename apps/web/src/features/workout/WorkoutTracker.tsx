import { useEffect, useMemo, useState } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import { api } from '@/data/repositories'
import type { Felt, WorkoutExercise, WorkoutSession, WorkoutSummary } from '@/data/types'
import { Footer, Header, Screen } from '@/ui/layout'
import { Rating } from '@/ui/controls'
import { Alert, Button, Card, Chip, Field, SectionTitle, StatusPill } from '@/ui/primitives'
import { Barbell, CheckCircle, Heartbeat, Timer, Trash } from '@/ui/icons'
import { useWorkoutSession } from './useWorkoutSession'

const LIBRARY: { group: string; items: string[] }[] = [
  { group: 'Legs', items: ['Squat', 'Leg press', 'Lunge', 'Deadlift', 'Romanian deadlift', 'Calf raise', 'Leg curl', 'Leg extension'] },
  { group: 'Chest', items: ['Bench press', 'Incline press', 'Push-up', 'Chest fly', 'Machine chest press'] },
  { group: 'Back', items: ['Lat pulldown', 'Barbell row', 'Seated row', 'Pull-up', 'Back extension'] },
  { group: 'Shoulders', items: ['Shoulder press', 'Lateral raise', 'Face pull', 'Shrug'] },
  { group: 'Arms', items: ['Biceps curl', 'Hammer curl', 'Triceps pushdown', 'Triceps dip'] },
  { group: 'Core', items: ['Plank', 'Crunch', 'Dead bug', 'Leg raise', 'Russian twist'] },
  { group: 'Cardio', items: ['Treadmill', 'Cycling', 'Rowing machine', 'Cross-trainer'] },
]
const REST_SECONDS = 90
const FEELS: { id: Felt }[] = [{ id: 'energised' }, { id: 'fine' }, { id: 'tired' }, { id: 'unwell' }]

/** A whole number from lo to hi, or null (the person has not typed one, or it is out of range). */
const wholeIn = (text: string, lo: number, hi: number): number | null => {
  if (!/^\d+$/.test(text.trim())) return null
  const n = Number(text.trim())
  return n >= lo && n <= hi ? n : null
}
/** A number (decimals allowed) from lo to hi, or null. */
const numberIn = (text: string, lo: number, hi: number): number | null => {
  if (text.trim() === '') return null
  const n = Number(text.trim())
  return Number.isFinite(n) && n >= lo && n <= hi ? n : null
}

const mmss = (total: number) => `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
const hhmmss = (total: number) => (total >= 3600 ? `${Math.floor(total / 3600)}:${mmss(total % 3600)}` : mmss(total))
const clockOf = (iso: string) => new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }).toLowerCase()

/** Reps times weight, summed. Plain arithmetic on what the person typed; bodyweight sets add nothing. */
const volumeOf = (e: WorkoutExercise) => e.sets.reduce((a, s) => a + (s.weightKg ? s.reps * s.weightKg : 0), 0)
const totals = (s: WorkoutSession) => ({ sets: s.exercises.reduce((a, e) => a + e.sets.length, 0), volume: s.exercises.reduce((a, e) => a + volumeOf(e), 0) })
const durationOf = (s: WorkoutSession) => Math.max(0, Math.round(((s.endedAt ? new Date(s.endedAt).getTime() : Date.now()) - new Date(s.startedAt).getTime()) / 1000))

/**
 * Strength session tracker: how long, what was done, every set with reps and weight, and a rest timer.
 * Heart-rate effort is worked out by the server after the session is saved (it reads the watch data and the
 * resting-heart-rate baseline). The model may then add one plain sentence from the finished numbers; it never
 * calculates them. This screen only records.
 */
export function WorkoutTracker() {
  const { t } = useTranslation()
  const feelLabel: Record<Felt, string> = { energised: t('workout.tracker.energised', 'Energised'), fine: t('workout.tracker.fine', 'Fine'), tired: t('workout.tracker.tired', 'Tired'), unwell: t('workout.tracker.unwell', 'Unwell') }
  const groupName: Record<string, string> = { Legs: t('workout.tracker.legs', 'Legs'), Chest: t('workout.tracker.chest', 'Chest'), Back: t('workout.tracker.back', 'Back'), Shoulders: t('workout.tracker.shoulders', 'Shoulders'), Arms: t('workout.tracker.arms', 'Arms'), Core: t('workout.tracker.core', 'Core'), Cardio: t('workout.tracker.cardio', 'Cardio') }
  const { session, pending, start, addExercise, removeExercise, addSet, removeSet, restUntil, startRest, stopRest, finish, discard, clearPending } = useWorkoutSession()
  const [now, setNow] = useState(Date.now())
  const [finishing, setFinishing] = useState(false)
  const [felt, setFelt] = useState<Felt | null>(null)
  /* null until the person picks 1 to 5. It may stay null: there is no default, and the server stores null as not rated */
  const [intensity, setIntensity] = useState<number | null>(null)
  const [note, setNote] = useState('')
  const [custom, setCustom] = useState('')
  const [result, setResult] = useState<{ session: WorkoutSession; summary: WorkoutSummary | null; error: string | null } | null>(null)

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [])

  if (result) return <Summary r={result} onDone={() => setResult(null)} />

  if (!session)
    return (
      <Screen narrow>
        <Header title={t('workout.tracker.startTitle', 'Workout tracker')} back backTo="F1" sub={t('workout.tracker.startSub', 'Track how long you train, what you do and every set.')} />
        <Card className="flex flex-col gap-3">
          <p className="text-body">{t('workout.tracker.intro', 'Log each exercise with its reps and weight. A rest timer starts after every set. When you finish, your heart rate from the watch is used to work out how hard the session was.')}</p>
          <Button icon={Barbell} onClick={start}>
            {t('workout.tracker.start', 'Start workout')}
          </Button>
        </Card>
        {pending.length > 0 && (
          <Card tone="soft" className="flex flex-col gap-2">
            <p className="text-body font-bold">{t('workout.tracker.waiting', 'Waiting to upload')}</p>
            {pending.map((p) => (
              <div key={p.id} className="flex items-center justify-between gap-3 text-body">
                <span>
                  {totals(p).sets === 1
                    ? t('workout.tracker.pendingItemOne', '{{time}}, 1 set', { time: clockOf(p.startedAt) })
                    : t('workout.tracker.pendingItem', '{{time}}, {{n}} sets', { time: clockOf(p.startedAt), n: totals(p).sets })}
                </span>
                <Button size="md" variant="secondary" className="!w-auto" onClick={() => setResult({ session: p, summary: null, error: t('workout.tracker.notUploaded', 'Not uploaded yet.') })}>
                  {t('workout.tracker.open', 'Open')}
                </Button>
              </div>
            ))}
            <p className="text-sub text-ink3">{t('workout.tracker.savedHere', 'Saved on this device until it can be uploaded.')}</p>
          </Card>
        )}
      </Screen>
    )

  const tot = totals(session)
  const elapsed = Math.max(0, Math.round((now - new Date(session.startedAt).getTime()) / 1000))
  const restLeft = restUntil ? Math.max(0, Math.round((restUntil - now) / 1000)) : 0
  const used = new Set(session.exercises.map((e) => e.name.toLowerCase()))

  const save = async () => {
    const finished = finish(felt ?? undefined, note || undefined)
    if (!finished) return
    const done = { ...finished, intensity }
    try {
      const summary = await api.saveWorkoutSession(done)
      clearPending(done.id)
      setResult({ session: done, summary, error: null })
    } catch (e) {
      setResult({ session: done, summary: null, error: t('workout.tracker.saveError', 'It could not be saved just now.') })
    }
  }

  return (
    <Screen narrow>
      <Header title={t('workout.tracker.title', 'Workout')} back backTo="F1" />
      <Card tone="hero" className="flex flex-col gap-3">
        <div className="flex items-end justify-between gap-3">
          <div>
            <p className="text-sub font-bold text-ink2">{t('workout.tracker.time', 'Time')}</p>
            <p className="num text-display tabular-nums" aria-live="off">
              {hhmmss(elapsed)}
            </p>
          </div>
          <div className="text-right text-sub text-ink2">
            <p>{t('workout.tracker.started', 'Started {{time}}', { time: clockOf(session.startedAt) })}</p>
            <p>
              <Trans i18nKey="workout.tracker.totals" defaults="<0>{{sets}}</0> sets, <1>{{kg}}</1> kg lifted" values={{ sets: tot.sets, kg: Math.round(tot.volume).toLocaleString('en-US') }} components={[<b key="0" className="text-ink" />, <b key="1" className="text-ink" />]} />
            </p>
          </div>
        </div>
        {restLeft > 0 && (
          <div className="flex items-center justify-between gap-3 rounded-card bg-brand-soft p-3.5">
            <span className="flex items-center gap-2 text-body font-bold text-brand">
              <Timer size={22} aria-hidden /> {t('workout.tracker.rest', 'Rest')} <span className="num text-h2">{mmss(restLeft)}</span>
            </span>
            <Button size="md" variant="ghost" className="!w-auto" onClick={stopRest}>
              {t('workout.tracker.endRest', 'End rest')}
            </Button>
          </div>
        )}
        {restUntil && restLeft === 0 && <StatusPill tone="ok">{t('workout.tracker.restOver', 'Rest is over. Ready for the next set.')}</StatusPill>}
      </Card>

      {session.exercises.map((e) => (
        <ExerciseCard key={e.id} e={e} onSet={(reps, w) => { addSet(e.id, reps, w); startRest(REST_SECONDS) }} onRemoveSet={(sid) => removeSet(e.id, sid)} onRemove={() => removeExercise(e.id)} />
      ))}

      <section className="flex flex-col gap-3">
        <SectionTitle>{t('workout.tracker.addEx', 'Add an exercise')}</SectionTitle>
        <div className="flex flex-col gap-3">
          {LIBRARY.map((g) => (
            <div key={g.group} className="flex flex-col gap-1.5">
              <p className="text-sub font-bold text-ink3">{groupName[g.group] ?? g.group}</p>
              <div className="flex flex-wrap gap-2">
                {g.items.filter((n) => !used.has(n.toLowerCase())).map((n) => (
                  <Chip key={n} onClick={() => addExercise(n)}>
                    {n}
                  </Chip>
                ))}
              </div>
            </div>
          ))}
        </div>
        <Field label={t('workout.tracker.other', 'Something else')} value={custom} onChange={setCustom} placeholder={t('workout.tracker.otherPh', 'Name the exercise')} />
        <Button variant="secondary" disabled={!custom.trim()} onClick={() => { addExercise(custom.trim()); setCustom('') }}>
          {t('workout.tracker.addButton', 'Add exercise')}
        </Button>
      </section>

      {finishing && (
        <Card className="flex flex-col gap-3">
          <Rating label={t('workout.tracker.hard', 'How hard did it feel?')} value={intensity} onChange={setIntensity} lowLabel={t('workout.tracker.veryLight', 'Very light')} highLabel={t('workout.tracker.allOut', 'All-out')} />
          <p className="text-sub text-ink2">{t('workout.tracker.optionalRating', 'Optional. Pick a number from 1 to 5 if you want to note it.')}</p>
          <SectionTitle>{t('workout.tracker.feel', 'How did it feel?')}</SectionTitle>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t('workout.tracker.feelLabel', 'How you felt')}>
            {FEELS.map((f) => (
              <Chip key={f.id} on={felt === f.id} onClick={() => setFelt(f.id)}>
                {feelLabel[f.id]}
              </Chip>
            ))}
          </div>
          <Field label={t('workout.tracker.note', 'Note (optional)')} value={note} onChange={setNote} multiline />
          <Button icon={CheckCircle} onClick={() => void save()}>
            {t('workout.tracker.save', 'Save workout')}
          </Button>
          <Button variant="ghost" onClick={() => setFinishing(false)}>
            {t('workout.tracker.keep', 'Keep training')}
          </Button>
        </Card>
      )}

      <Footer>
        {!finishing && (
          <Button icon={CheckCircle} disabled={tot.sets === 0} onClick={() => setFinishing(true)}>
            {t('workout.tracker.finish', 'Finish workout')}
          </Button>
        )}
        <Button variant="ghost" icon={Trash} onClick={() => { if (window.confirm(t('workout.tracker.discardConfirm', 'Discard this workout?'))) discard() }}>
          {t('workout.tracker.discard', 'Discard workout')}
        </Button>
      </Footer>
    </Screen>
  )
}

function ExerciseCard({ e, onSet, onRemoveSet, onRemove }: { e: WorkoutExercise; onSet: (reps: number, weightKg: number | null) => void; onRemoveSet: (id: string) => void; onRemove: () => void }) {
  const { t } = useTranslation()
  /* empty until the person types them: there is no default number of reps or weight, and Log set waits for them */
  const [repsText, setRepsText] = useState('')
  const [weightText, setWeightText] = useState('')
  const [bodyweight, setBodyweight] = useState(false)
  const volume = useMemo(() => volumeOf(e), [e])
  const reps = wholeIn(repsText, 1, 100)
  const weight = numberIn(weightText, 0, 300)
  /** why Log set is off, in plain words; null when the set is complete */
  const blocker = reps == null
    ? t('workout.tracker.blockReps', 'Enter how many reps you did, from 1 to 100.')
    : !bodyweight && weight == null
      ? t('workout.tracker.blockWeight', 'Enter the weight in kg, from 0 to 300, or tap Bodyweight.')
      : null
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-h2 font-bold leading-tight">{e.name}</p>
          <p className="text-sub text-ink2">
            {e.sets.length === 1 ? t('workout.tracker.oneSet', '1 set') : t('workout.tracker.setCount', '{{n}} sets', { n: e.sets.length })}{volume > 0 ? t('workout.tracker.volumeKg', ', {{kg}} kg', { kg: Math.round(volume).toLocaleString('en-US') }) : ''}
          </p>
        </div>
        <button type="button" aria-label={t('workout.tracker.removeEx', 'Remove {{name}}', { name: e.name })} onClick={onRemove} className="press flex h-12 w-12 flex-none items-center justify-center rounded-full text-ink3 hover:bg-well">
          <Trash size={22} aria-hidden />
        </button>
      </div>
      {e.sets.length > 0 && (
        <ol className="divide-y divide-line">
          {e.sets.map((s, i) => (
            <li key={s.id} className="flex items-center justify-between gap-3 py-2.5 text-body">
              <span>
                <span className="text-ink3">{t('workout.tracker.setN', 'Set {{n}}', { n: i + 1 })}</span> <span className="num text-h2">{s.reps}</span> {t('workout.tracker.reps', 'reps')} {s.weightKg === null ? t('workout.tracker.bodyweightSet', '(bodyweight)') : t('workout.tracker.atKg', 'at {{kg}} kg', { kg: s.weightKg })}
              </span>
              <button type="button" aria-label={t('workout.tracker.removeSet', 'Remove set {{n}}', { n: i + 1 })} onClick={() => onRemoveSet(s.id)} className="press flex h-10 w-10 flex-none items-center justify-center rounded-full text-ink3 hover:bg-well">
                <Trash size={18} aria-hidden />
              </button>
            </li>
          ))}
        </ol>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        <Field
          label={t('workout.tracker.repsField', 'Reps')}
          value={repsText}
          onChange={setRepsText}
          inputMode="numeric"
          suffix={t('workout.tracker.repsSuffix', 'reps')}
          placeholder={t('workout.tracker.repsPh', 'For example 10')}
          error={repsText.trim() !== '' && reps == null ? t('workout.tracker.repsError', 'Use a whole number, from 1 to 100.') : undefined}
        />
        {!bodyweight && (
          <Field
            label={t('workout.tracker.weightField', 'Weight')}
            value={weightText}
            onChange={setWeightText}
            inputMode="decimal"
            suffix="kg"
            placeholder={t('workout.tracker.weightPh', 'For example 20')}
            error={weightText.trim() !== '' && weight == null ? t('workout.tracker.weightError', 'Use a number from 0 to 300.') : undefined}
          />
        )}
      </div>
      <Chip on={bodyweight} onClick={() => setBodyweight((b) => !b)} className="self-start">
        {t('workout.tracker.bodyweight', 'Bodyweight')}
      </Chip>
      {blocker && <p className="text-sub text-ink2">{blocker}</p>}
      <Button disabled={!!blocker} onClick={() => {
        if (reps == null) return
        onSet(reps, bodyweight ? null : weight)
        // the next set starts empty, so each set's numbers are typed for that set
        setRepsText('')
        setWeightText('')
      }}>{t('workout.tracker.logSet', 'Log set')}</Button>
    </Card>
  )
}

function Summary({ r, onDone }: { r: { session: WorkoutSession; summary: WorkoutSummary | null; error: string | null }; onDone: () => void }) {
  const { t } = useTranslation()
  const tot = totals(r.session)
  const s = r.summary
  const effortName: Record<string, string> = { light: t('workout.tracker.light', 'light'), moderate: t('workout.tracker.moderate', 'moderate'), vigorous: t('workout.tracker.vigorous', 'vigorous') }
  return (
    <Screen narrow>
      <Header title={t('workout.tracker.savedTitle', 'Workout saved')} sub={r.error ? t('workout.tracker.keptHere', 'Kept on this device.') : undefined} />
      {r.error && <Alert tone="info">{t('workout.tracker.staysHere', '{{error}} It stays on this device and can be uploaded again from the workout screen.', { error: r.error })}</Alert>}
      {r.session.intensity == null && <p className="text-body text-ink2">{t('workout.tracker.unratedNote', 'No effort rating was given, so this workout is not counted toward your active minutes.')}</p>}
      <Card tone="hero" className="grid grid-cols-3 gap-3 text-center [[data-ts='2']_&]:grid-cols-1">
        <div>
          <p className="text-sub text-ink2">{t('workout.tracker.timeLabel', 'Time')}</p>
          <p className="num text-xl">{hhmmss(s ? s.durationS : durationOf(r.session))}</p>
        </div>
        <div>
          <p className="text-sub text-ink2">{t('workout.tracker.setsLabel', 'Sets')}</p>
          <p className="num text-xl">{s ? s.setsN : tot.sets}</p>
        </div>
        <div>
          <p className="text-sub text-ink2">{t('workout.tracker.liftedLabel', 'Lifted')}</p>
          <p className="num text-xl">
            {Math.round(s ? s.volumeKg : tot.volume).toLocaleString('en-US')}
            <span className="text-sub text-ink3"> kg</span>
          </p>
        </div>
      </Card>
      <Card className="flex flex-col gap-1">
        <SectionTitle>{t('workout.tracker.exercises', 'Exercises')}</SectionTitle>
        <ul className="divide-y divide-line">
          {r.session.exercises.map((e) => {
            const fromServer = s?.exercises.find((x) => x.name === e.name)
            return (
              <li key={e.id} className="flex items-center justify-between gap-3 py-3 text-body">
                <span>
                  <b>{e.name}</b>
                  <span className="block text-sub text-ink2">
                    {e.sets.length === 1
                      ? t('workout.tracker.oneSetKg', '1 set, {{kg}} kg', { kg: Math.round(volumeOf(e)).toLocaleString('en-US') })
                      : t('workout.tracker.setsKg', '{{n}} sets, {{kg}} kg', { n: e.sets.length, kg: Math.round(volumeOf(e)).toLocaleString('en-US') })}
                  </span>
                </span>
                {fromServer?.avgHr != null && (
                  <span className="text-right">
                    <span className="num text-h2">{Math.round(fromServer.avgHr)}</span>
                    <span className="block text-sub text-ink3">{t('workout.tracker.avgBpm', 'avg bpm')}</span>
                  </span>
                )}
              </li>
            )
          })}
        </ul>
      </Card>
      <Card className="flex flex-col gap-2">
        <p className="flex items-center gap-2 text-body font-bold">
          <Heartbeat size={22} className="text-brand" aria-hidden /> {t('workout.tracker.hrEffort', 'Heart-rate effort')}
        </p>
        {!s && <p className="text-body text-ink2">{t('workout.tracker.effortWait', 'Effort appears here once this is saved to the server and your watch heart rate is available. It is worked out by code from your heart rate and your resting baseline, not guessed.')}</p>}
        {s && s.effort.avgHr != null && (s.effort.quality === 'ok' || s.effort.betaBlocker) && (
          <p className="text-body">{t('workout.tracker.hrSummary', 'Average {{avg}} bpm, peak {{peak}} bpm.', { avg: Math.round(s.effort.avgHr), peak: Math.round(s.effort.maxHr ?? 0) })}</p>
        )}
        {s && s.effort.quality === 'ok' && s.effort.intensity && (
          <>
            <p className="text-body font-bold">{t('workout.tracker.estimate', 'Estimated from your heart rate: {{effort}}', { effort: effortName[s.effort.intensity] ?? s.effort.intensity })}</p>
            <p className="text-sub text-ink2">{t('workout.tracker.estimateHow', 'Worked out from your watch heart rate and a maximum heart rate estimated from your age.')}</p>
          </>
        )}
        {s && (s.effort.quality !== 'ok' || s.effort.betaBlocker) && (
          <p className="text-body text-ink2">{s.effort.note ?? t('workout.tracker.effortWait', 'Effort appears here once this is saved to the server and your watch heart rate is available. It is worked out by code from your heart rate and your resting baseline, not guessed.')}</p>
        )}
        {s && (s.effort.quality === 'ok' || s.effort.betaBlocker) && (
          <>
            {s.glucoseChange2h != null && <p className="text-body">{t('workout.tracker.glucose', 'Your glucose changed by {{change}} mmol/L over the next 2 hours (associated with, not proven).', { change: `${s.glucoseChange2h > 0 ? '+' : ''}${s.glucoseChange2h.toFixed(1)}` })}</p>}
            {s.narrative && <p className="text-body text-ink2">{s.narrative}</p>}
          </>
        )}
        <p className="text-sub text-ink3">{t('workout.tracker.hrNote', 'Heart rate is an estimate of effort. It is not a medical measurement.')}</p>
      </Card>
      <Footer>
        <Button onClick={onDone}>{t('workout.tracker.done', 'Done')}</Button>
      </Footer>
    </Screen>
  )
}
