import { useEffect, useMemo, useState } from 'react'
import { api } from '@/data/repositories'
import type { Felt, WorkoutExercise, WorkoutSession, WorkoutSummary } from '@/data/types'
import { Footer, Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, Chip, Field, SectionTitle, StatusPill, Stepper } from '@/ui/primitives'
import { Barbell, CheckCircle, Heartbeat, Timer, Trash } from '@/ui/icons'
import { useWorkoutSession } from './useWorkoutSession'

const COMMON = ['Squat', 'Bench press', 'Deadlift', 'Shoulder press', 'Barbell row', 'Lat pulldown', 'Leg press', 'Biceps curl', 'Triceps pushdown', 'Plank', 'Treadmill', 'Cycling']
const REST_SECONDS = 90
const FEELS: { id: Felt; label: string }[] = [
  { id: 'energised', label: 'Energised' },
  { id: 'fine', label: 'Fine' },
  { id: 'tired', label: 'Tired' },
  { id: 'unwell', label: 'Unwell' },
]

const mmss = (total: number) => `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
const hhmmss = (total: number) => (total >= 3600 ? `${Math.floor(total / 3600)}:${mmss(total % 3600)}` : mmss(total))
const clockOf = (iso: string) => new Date(iso).toLocaleTimeString('en-GB', { hour: 'numeric', minute: '2-digit', hour12: true }).toLowerCase()

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
  const { session, pending, start, addExercise, removeExercise, addSet, removeSet, restUntil, startRest, stopRest, finish, discard, clearPending } = useWorkoutSession()
  const [now, setNow] = useState(Date.now())
  const [finishing, setFinishing] = useState(false)
  const [felt, setFelt] = useState<Felt | null>(null)
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
      <Screen>
        <Header title="Workout tracker" back backTo="E1" sub="Track how long you train, what you do and every set." />
        <Card className="flex flex-col gap-3">
          <p className="text-body">Log each exercise with its reps and weight. A rest timer starts after every set. When you finish, your heart rate from the watch is used to work out how hard the session was.</p>
          <Button icon={Barbell} onClick={start}>
            Start workout
          </Button>
        </Card>
        {pending.length > 0 && (
          <Card tone="soft" className="flex flex-col gap-2">
            <p className="text-body font-bold">Waiting to upload</p>
            {pending.map((p) => (
              <div key={p.id} className="flex items-center justify-between gap-3 text-body">
                <span>
                  {clockOf(p.startedAt)}, {totals(p).sets} sets
                </span>
                <Button size="md" variant="secondary" className="!w-auto" onClick={() => setResult({ session: p, summary: null, error: 'Not uploaded yet.' })}>
                  Open
                </Button>
              </div>
            ))}
            <p className="text-sub text-ink3">Saved on this device until the server is connected.</p>
          </Card>
        )}
      </Screen>
    )

  const t = totals(session)
  const elapsed = Math.max(0, Math.round((now - new Date(session.startedAt).getTime()) / 1000))
  const restLeft = restUntil ? Math.max(0, Math.round((restUntil - now) / 1000)) : 0
  const used = new Set(session.exercises.map((e) => e.name.toLowerCase()))

  const save = async () => {
    const done = finish(felt ?? undefined, note || undefined)
    if (!done) return
    try {
      const summary = await api.saveWorkoutSession(done)
      clearPending(done.id)
      setResult({ session: done, summary, error: null })
    } catch (e) {
      setResult({ session: done, summary: null, error: e instanceof Error && e.name === 'NotWired' ? 'The server is not connected yet.' : 'It could not be saved just now.' })
    }
  }

  return (
    <Screen>
      <Header title="Workout" back backTo="E1" />
      <Card tone="hero" className="flex flex-col gap-3">
        <div className="flex items-end justify-between gap-3">
          <div>
            <p className="text-sub font-bold text-ink2">Time</p>
            <p className="num text-display tabular-nums" aria-live="off">
              {hhmmss(elapsed)}
            </p>
          </div>
          <div className="text-right text-sub text-ink2">
            <p>Started {clockOf(session.startedAt)}</p>
            <p>
              <b className="text-ink">{t.sets}</b> sets, <b className="text-ink">{Math.round(t.volume).toLocaleString('en-US')}</b> kg lifted
            </p>
          </div>
        </div>
        {restLeft > 0 && (
          <div className="flex items-center justify-between gap-3 rounded-card bg-brand-soft p-3.5">
            <span className="flex items-center gap-2 text-body font-bold text-brand">
              <Timer size={22} aria-hidden /> Rest <span className="num text-h2">{mmss(restLeft)}</span>
            </span>
            <Button size="md" variant="ghost" className="!w-auto" onClick={stopRest}>
              Skip rest
            </Button>
          </div>
        )}
        {restUntil && restLeft === 0 && <StatusPill tone="ok">Rest is over. Ready for the next set.</StatusPill>}
      </Card>

      {session.exercises.map((e) => (
        <ExerciseCard key={e.id} e={e} onSet={(reps, w) => { addSet(e.id, reps, w); startRest(REST_SECONDS) }} onRemoveSet={(sid) => removeSet(e.id, sid)} onRemove={() => removeExercise(e.id)} />
      ))}

      <section className="flex flex-col gap-3">
        <SectionTitle>Add an exercise</SectionTitle>
        <div className="flex flex-wrap gap-2">
          {COMMON.filter((n) => !used.has(n.toLowerCase())).map((n) => (
            <Chip key={n} onClick={() => addExercise(n)}>
              {n}
            </Chip>
          ))}
        </div>
        <Field label="Something else" value={custom} onChange={setCustom} placeholder="Name the exercise" />
        <Button variant="secondary" disabled={!custom.trim()} onClick={() => { addExercise(custom.trim()); setCustom('') }}>
          Add exercise
        </Button>
      </section>

      {finishing && (
        <Card className="flex flex-col gap-3">
          <SectionTitle>How did it feel?</SectionTitle>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="How you felt">
            {FEELS.map((f) => (
              <Chip key={f.id} on={felt === f.id} onClick={() => setFelt(f.id)}>
                {f.label}
              </Chip>
            ))}
          </div>
          <Field label="Note (optional)" value={note} onChange={setNote} multiline />
          <Button icon={CheckCircle} onClick={() => void save()}>
            Save workout
          </Button>
          <Button variant="ghost" onClick={() => setFinishing(false)}>
            Keep training
          </Button>
        </Card>
      )}

      <Footer>
        {!finishing && (
          <Button icon={CheckCircle} disabled={t.sets === 0} onClick={() => setFinishing(true)}>
            Finish workout
          </Button>
        )}
        <Button variant="ghost" icon={Trash} onClick={() => { if (window.confirm('Discard this workout?')) discard() }}>
          Discard workout
        </Button>
      </Footer>
    </Screen>
  )
}

function ExerciseCard({ e, onSet, onRemoveSet, onRemove }: { e: WorkoutExercise; onSet: (reps: number, weightKg: number | null) => void; onRemoveSet: (id: string) => void; onRemove: () => void }) {
  const last = e.sets[e.sets.length - 1]
  const [reps, setReps] = useState(last?.reps ?? 10)
  const [weight, setWeight] = useState(last?.weightKg ?? 20)
  const [bodyweight, setBodyweight] = useState(last ? last.weightKg === null : false)
  const volume = useMemo(() => volumeOf(e), [e])
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-h2 font-bold leading-tight">{e.name}</p>
          <p className="text-sub text-ink2">
            {e.sets.length} sets{volume > 0 ? `, ${Math.round(volume).toLocaleString('en-US')} kg` : ''}
          </p>
        </div>
        <button type="button" aria-label={`Remove ${e.name}`} onClick={onRemove} className="press flex h-12 w-12 flex-none items-center justify-center rounded-full text-ink3 hover:bg-well">
          <Trash size={22} aria-hidden />
        </button>
      </div>
      {e.sets.length > 0 && (
        <ol className="divide-y divide-line">
          {e.sets.map((s, i) => (
            <li key={s.id} className="flex items-center justify-between gap-3 py-2.5 text-body">
              <span>
                <span className="text-ink3">Set {i + 1}</span> <span className="num text-h2">{s.reps}</span> reps {s.weightKg === null ? '(bodyweight)' : `at ${s.weightKg} kg`}
              </span>
              <button type="button" aria-label={`Remove set ${i + 1}`} onClick={() => onRemoveSet(s.id)} className="press flex h-10 w-10 flex-none items-center justify-center rounded-full text-ink3 hover:bg-well">
                <Trash size={18} aria-hidden />
              </button>
            </li>
          ))}
        </ol>
      )}
      <div className="flex flex-col gap-2">
        <Stepper label="reps" value={reps} onChange={setReps} min={1} max={100} step={1} format={(v) => `${v} reps`} />
        {!bodyweight && <Stepper label="weight" value={weight} onChange={setWeight} min={0} max={300} step={2.5} format={(v) => `${v} kg`} />}
        <Chip on={bodyweight} onClick={() => setBodyweight((b) => !b)} className="self-start">
          Bodyweight
        </Chip>
      </div>
      <Button onClick={() => onSet(reps, bodyweight ? null : weight)}>Log set</Button>
    </Card>
  )
}

function Summary({ r, onDone }: { r: { session: WorkoutSession; summary: WorkoutSummary | null; error: string | null }; onDone: () => void }) {
  const t = totals(r.session)
  const s = r.summary
  return (
    <Screen>
      <Header title="Workout saved" sub={r.error ? 'Kept on this device.' : undefined} />
      {r.error && <Alert tone="info">{r.error} It will be uploaded when the server is connected, and nothing is lost.</Alert>}
      <Card tone="hero" className="grid grid-cols-3 gap-3 text-center [[data-ts='2']_&]:grid-cols-1">
        <div>
          <p className="text-sub text-ink2">Time</p>
          <p className="num text-xl">{hhmmss(s ? s.durationS : durationOf(r.session))}</p>
        </div>
        <div>
          <p className="text-sub text-ink2">Sets</p>
          <p className="num text-xl">{s ? s.setsN : t.sets}</p>
        </div>
        <div>
          <p className="text-sub text-ink2">Lifted</p>
          <p className="num text-xl">
            {Math.round(s ? s.volumeKg : t.volume).toLocaleString('en-US')}
            <span className="text-sub text-ink3"> kg</span>
          </p>
        </div>
      </Card>
      <Card className="flex flex-col gap-1">
        <SectionTitle>Exercises</SectionTitle>
        <ul className="divide-y divide-line">
          {r.session.exercises.map((e) => {
            const fromServer = s?.exercises.find((x) => x.name === e.name)
            return (
              <li key={e.id} className="flex items-center justify-between gap-3 py-3 text-body">
                <span>
                  <b>{e.name}</b>
                  <span className="block text-sub text-ink2">
                    {e.sets.length} sets, {Math.round(volumeOf(e)).toLocaleString('en-US')} kg
                  </span>
                </span>
                {fromServer?.avgHr != null && (
                  <span className="text-right">
                    <span className="num text-h2">{Math.round(fromServer.avgHr)}</span>
                    <span className="block text-sub text-ink3">avg bpm</span>
                  </span>
                )}
              </li>
            )
          })}
        </ul>
      </Card>
      <Card className="flex flex-col gap-2">
        <p className="flex items-center gap-2 text-body font-bold">
          <Heartbeat size={22} className="text-brand" aria-hidden /> Heart-rate effort
        </p>
        {s && s.effort.quality === 'ok' ? (
          <>
            <p className="text-body">
              Average {Math.round(s.effort.avgHr ?? 0)} bpm, peak {Math.round(s.effort.maxHr ?? 0)} bpm. Overall effort: <b>{s.effort.intensity}</b>.
            </p>
            {s.glucoseChange2h != null && <p className="text-body">Your glucose changed by {s.glucoseChange2h > 0 ? '+' : ''}{s.glucoseChange2h.toFixed(1)} mmol/L over the next 2 hours (associated with, not proven).</p>}
            {s.narrative && <p className="text-body text-ink2">{s.narrative}</p>}
          </>
        ) : (
          <p className="text-body text-ink2">{s?.effort.note ?? 'Effort appears here once this is saved to the server and your watch heart rate is available. It is worked out by code from your heart rate and your resting baseline, not guessed.'}</p>
        )}
        <p className="text-sub text-ink3">Heart rate is an estimate of effort. It is not a medical measurement.</p>
      </Card>
      <Footer>
        <Button onClick={onDone}>Done</Button>
      </Footer>
    </Screen>
  )
}
