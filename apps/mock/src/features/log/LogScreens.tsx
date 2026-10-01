import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLog } from '@/data/hooks'
import type { LogInput } from '@/data/repositories/types'
import { useGo } from '@/app/navigation'
import { href } from '@/app/routeIds'
import { useUi } from '@/state/store'
import { mealAnalysisService, type MealAnalysis } from '@/services/mealAnalysis'
import { predictionService, type FoodNote } from '@/services/prediction'
import { glucoseLevel, levelText } from '@/lib/format'
import { Header, Footer, Screen } from '@/ui/layout'
import { NumberPad, Rating, Segmented } from '@/ui/controls'
import { Alert, Button, Card, Chip, EstimateBadge, Field, SectionTitle, Skeleton, Stepper, StatusPill, TextLink } from '@/ui/primitives'
import { Camera, CheckCircle, Info, PencilSimple } from '@/ui/icons'

/** Saves an entry, remembers the result for the confirmation screen, and routes. Urgent readings go straight to J1. */
export function useFinishLog() {
  const log = useLog()
  const navigate = useNavigate()
  const setLast = useUi((s) => s.setLastLog)
  return {
    pending: log.isPending,
    save: (input: LogInput) =>
      log.mutate(input, {
        onSuccess: (res) => {
          setLast(res)
          navigate(res.urgent ? href('J1') : href('E6'), { replace: true })
        },
      }),
  }
}

/* ------------------------------------- E2 meal ------------------------------------- */
const quick = ['Chicken rice', 'Kaya toast', 'Laksa', 'Vegetable and egg breakfast']
const macroLabels: [keyof MealAnalysis['macros'], string, string][] = [
  ['kcal', 'Calories', 'kcal'],
  ['carbsG', 'Carbs', 'g'],
  ['proteinG', 'Protein', 'g'],
  ['fatG', 'Fat', 'g'],
  ['fibreG', 'Fibre', 'g'],
  ['sugarG', 'Sugar', 'g'],
  ['saltMg', 'Salt (sodium)', 'mg'],
]

export function LogMeal() {
  const [mode, setMode] = useState<'photo' | 'text'>('text')
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [res, setRes] = useState<MealAnalysis | null>(null)
  const [portion, setPortion] = useState(1)
  const [confirmed, setConfirmed] = useState(false)
  const [editing, setEditing] = useState(false)
  const [note, setNote] = useState<FoodNote | null>(null)
  const { save, pending } = useFinishLog()

  const analyse = async (p: Promise<MealAnalysis>) => {
    setBusy(true)
    setConfirmed(false)
    const r = await p
    setRes(r)
    setBusy(false)
    setNote(await predictionService.foodNote(r.name))
  }
  useEffect(() => {
    setRes(null)
  }, [mode])

  const scaled = (v: number) => Math.round(v * portion)
  return (
    <Screen>
      <Header title="Log a meal" back backTo="E1" />
      <Segmented label="How to add" value={mode} onChange={setMode} options={[{ value: 'text', label: 'Describe it' }, { value: 'photo', label: 'Photo' }]} />

      {mode === 'text' ? (
        <div className="flex flex-col gap-3">
          <Field label="What did you eat?" value={text} onChange={setText} placeholder="For example, chicken rice" />
          <div className="flex flex-wrap gap-2">
            {quick.map((q) => (
              <Chip key={q} onClick={() => { setText(q); void analyse(mealAnalysisService.fromText(q)) }}>
                {q}
              </Chip>
            ))}
          </div>
          <Button variant="secondary" disabled={!text.trim() || busy} onClick={() => void analyse(mealAnalysisService.fromText(text))}>
            {busy ? 'Reading your meal...' : 'Estimate nutrients'}
          </Button>
        </div>
      ) : (
        <button type="button" onClick={() => void analyse(mealAnalysisService.fromPhoto())} className="press flex min-h-44 flex-col items-center justify-center gap-3 rounded-card border-2 border-dashed border-line bg-well p-6 text-center">
          <Camera size={36} className="text-brand" aria-hidden />
          <span className="text-body font-bold">{busy ? 'Reading your photo...' : 'Take or choose a photo'}</span>
          <span className="text-sub text-ink2">Prototype: tapping uses a sample photo of chicken rice.</span>
        </button>
      )}

      {busy && <Skeleton className="h-52" />}

      {res && !busy && (
        <>
          <Card className="flex flex-col gap-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-h2 font-bold">{res.name}</p>
                <p className="text-sub text-ink2">{res.items.join(', ')}</p>
              </div>
              {!confirmed && <EstimateBadge />}
            </div>
            {res.confidence === 'check' && !confirmed && <StatusPill tone="warn">Check this: we are less sure about the portion</StatusPill>}
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 [[data-ts='2']_&]:grid-cols-1">
              {macroLabels.map(([k, label, unit]) => (
                <div key={k}>
                  <dt className="text-sub text-ink2">{label}</dt>
                  <dd className="num text-h2">
                    {scaled(res.macros[k])} <span className="text-sub text-ink3">{unit}</span>
                  </dd>
                </div>
              ))}
            </dl>
            {editing && (
              <div className="grid grid-cols-2 gap-3 border-t border-line pt-3">
                <Field label="Carbs (g)" inputMode="numeric" value={String(res.macros.carbsG)} onChange={(v) => setRes({ ...res, macros: { ...res.macros, carbsG: Number(v) || 0 } })} />
                <Field label="Salt (mg)" inputMode="numeric" value={String(res.macros.saltMg)} onChange={(v) => setRes({ ...res, macros: { ...res.macros, saltMg: Number(v) || 0 } })} />
              </div>
            )}
            {res.flags.includes('high_salt') && <StatusPill tone="warn">High salt</StatusPill>}
            {res.flags.includes('high_sugar') && <StatusPill tone="warn">High sugar</StatusPill>}
            <div className="flex gap-2">
              <Button size="md" variant={confirmed ? 'secondary' : 'primary'} icon={CheckCircle} onClick={() => setConfirmed(true)}>
                {confirmed ? 'Confirmed' : 'Looks right'}
              </Button>
              <Button size="md" variant="secondary" icon={PencilSimple} onClick={() => setEditing((e) => !e)}>
                {editing ? 'Done' : 'Edit'}
              </Button>
            </div>
            <p className="text-sub text-ink3">Nutrients are estimates until you confirm them. Your glucose rise will come from the sensor.</p>
          </Card>

          <div className="flex flex-col gap-2">
            <p className="text-body font-bold">Portion</p>
            <Stepper label="portion" value={portion} onChange={setPortion} min={0.5} max={3} step={0.5} format={(v) => (v === 0.5 ? '½' : v === 1.5 ? '1½' : v === 2.5 ? '2½' : String(v))} />
          </div>

          {note && (
            <Alert tone={note.kind === 'higher' ? 'warn' : 'info'} icon={Info} title="Your usual response">
              {note.text}
              {note.range && (
                <span className="mt-1 block text-ink2">
                  Seen {note.n} times, rise {note.range[0].toFixed(1)} to {note.range[1].toFixed(1)} mmol/L.
                </span>
              )}
            </Alert>
          )}

          <Footer>
            <Button disabled={pending} onClick={() => save({ kind: 'meal', name: res.name, portion, viaPhoto: mode === 'photo' })}>
              Save meal
            </Button>
          </Footer>
        </>
      )}
    </Screen>
  )
}

/* ------------------------------------ E3 glucose ------------------------------------ */
const contexts = ['Fasting', 'Before a meal', '2 h after a meal', 'Bedtime', 'Random']
export function LogGlucose() {
  const [v, setV] = useState('')
  const [ctx, setCtx] = useState('Fasting')
  const { save, pending } = useFinishLog()
  const n = Number(v)
  const valid = v !== '' && n >= 1 && n <= 35
  const level = valid ? glucoseLevel(n) : null
  return (
    <Screen>
      <Header title="Log glucose" back backTo="E1" />
      <div className="flex flex-col items-center gap-1 rounded-card border border-line bg-card py-6" aria-live="polite">
        <span className="num text-display tabular-nums">{v || '0.0'}</span>
        <span className="text-body text-ink2">mmol/L</span>
        {level && <span className="mt-1 text-sub text-ink3">{levelText[level]}</span>}
      </div>
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="When was it taken">
        {contexts.map((c) => (
          <Chip key={c} on={ctx === c} onClick={() => setCtx(c)}>
            {c}
          </Chip>
        ))}
      </div>
      <NumberPad value={v} onChange={setV} max={4} />
      <Footer>
        <Button disabled={!valid || pending} onClick={() => save({ kind: 'glucose', value: Math.round(n * 10) / 10, context: ctx })}>
          Save reading
        </Button>
      </Footer>
    </Screen>
  )
}

/* ------------------------------------ E4 symptom ------------------------------------ */
const symptoms = ['More thirsty than usual', 'Passing more urine', 'Tingling or numbness in my feet', 'Blurry vision', 'Tired more than usual', 'Dizzy', 'Headache', 'Upset stomach', 'Something else']
const redFlags = ['Chest pain', 'Confusion', 'Fainting']
export function LogSymptom() {
  const [label, setLabel] = useState<string | null>(null)
  const [sev, setSev] = useState(2)
  const [note, setNote] = useState('')
  const navigate = useNavigate()
  const { save, pending } = useFinishLog()
  const red = label ? redFlags.includes(label) : false
  return (
    <Screen>
      <Header title="Log a symptom" back backTo="E1" />
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Symptom">
        {symptoms.map((s) => (
          <Chip key={s} on={label === s} onClick={() => setLabel(s)}>
            {s}
          </Chip>
        ))}
      </div>
      <Card tone="soft" className="flex flex-col gap-2">
        <p className="text-sub font-bold text-ink2">Need help right now?</p>
        <div className="flex flex-wrap gap-2">
          {redFlags.map((s) => (
            <Chip key={s} on={label === s} onClick={() => setLabel(s)}>
              {s}
            </Chip>
          ))}
        </div>
      </Card>
      <div className="flex flex-col gap-2">
        <Rating label="How strong" value={sev} onChange={setSev} lowLabel="Mild" highLabel="Very strong" />
      </div>
      <Field label="Add a note (optional)" value={note} onChange={setNote} multiline />
      <Footer>
        <Button
          variant={red ? 'danger' : 'primary'}
          disabled={!label || pending}
          onClick={() => (red ? navigate(href('J1')) : label && save({ kind: 'symptom', label, severity: sev, note }))}
        >
          {red ? 'Get help now' : 'Save symptom'}
        </Button>
      </Footer>
    </Screen>
  )
}

/* ------------------------------------ E5 check-in ------------------------------------ */
export function LogCheckin() {
  const [mood, setMood] = useState(3)
  const [stress, setStress] = useState(4)
  const [sleep, setSleep] = useState(2)
  const [energy, setEnergy] = useState(3)
  const { save, pending } = useFinishLog()
  return (
    <Screen>
      <Header title="Mood and sleep" back backTo="E1" sub="Thirty seconds. Tap a number for each." />
      <Rating label="Mood" value={mood} onChange={setMood} lowLabel="Low" highLabel="Great" />
      <Rating label="Stress" value={stress} onChange={setStress} lowLabel="Calm" highLabel="Very stressed" />
      <Rating label="Sleep quality" value={sleep} onChange={setSleep} lowLabel="Poor" highLabel="Very good" />
      <Rating label="Energy" value={energy} onChange={setEnergy} lowLabel="Drained" highLabel="Full" />
      <Footer>
        <Button disabled={pending} onClick={() => save({ kind: 'checkin', mood, stress, sleep, energy })}>
          Save check-in
        </Button>
      </Footer>
    </Screen>
  )
}

/* ----------------------------------- E6 confirmation ----------------------------------- */
const relatedLabel: Record<string, string> = { C2: 'See your glucose insights', C3: 'See your food insights', C4: 'See your activity', C5: 'See your sleep and stress' }
export function LogDone() {
  const last = useUi((s) => s.lastLog)
  const go = useGo()
  const navigate = useNavigate()
  useEffect(() => {
    if (!last) navigate(href('E1'), { replace: true })
  }, [last, navigate])
  if (!last) return null
  const tone = last.flag?.level === 'in_range' ? 'ok' : last.flag?.level === 'info' ? 'warn' : 'warn'
  return (
    <Screen>
      <div className="flex flex-col items-center gap-3 pb-1 pt-6 text-center">
        <span className="flex h-16 w-16 items-center justify-center rounded-full bg-ok-soft text-ok">
          <CheckCircle size={38} weight="regular" aria-hidden />
        </span>
        <h1 className="font-serif text-h1 font-medium tracking-tight">{last.title}</h1>
        <p className="text-body text-ink2">{last.detail}</p>
      </div>
      <Card className="flex flex-col gap-3">
        <div>
          <p className="text-sub text-ink3">Added to</p>
          <p className="text-body font-bold">{last.landedIn}</p>
        </div>
        {last.lines.map((l) => (
          <p key={l} className="text-body">
            {l}
          </p>
        ))}
        {last.flag && (
          <Alert tone={tone as 'ok' | 'warn'} icon={last.flag.level === 'in_range' ? CheckCircle : Info}>
            {last.flag.text}
          </Alert>
        )}
      </Card>
      {last.swap && (
        <Card tone="soft" className="flex flex-col gap-1">
          <SectionTitle>A swap to consider</SectionTitle>
          <p className="text-body">{last.swap.text}</p>
          <p className="text-sub text-ink3">{last.swap.source}</p>
        </Card>
      )}
      <div className="flex flex-col gap-2">
        <Button onClick={() => go('D1', { params: { date: last.day } })}>See your day</Button>
        <Button variant="secondary" onClick={() => go(last.related)}>
          {relatedLabel[last.related] ?? 'See insights'}
        </Button>
        {last.urgent && (
          <Button variant="danger" onClick={() => go('J1')}>
            Get help now
          </Button>
        )}
        <TextLink onClick={() => go('B1')} className="self-center">
          Done
        </TextLink>
      </div>
    </Screen>
  )
}

