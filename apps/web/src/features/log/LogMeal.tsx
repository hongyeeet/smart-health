/**
 * E2 — Log a meal.
 *
 * Starts from a photo (there is no text-only entry). An optional description goes to the model with the photo, for
 * things the camera cannot see ("half the rice", "no gravy"). The vision model on Vertex AI reads both and estimates
 * the nutrients; the person can correct them. "Start eating" begins the meal; "I've finished eating" stamps the
 * finish time and writes it to the database. All nutrients are estimates until the person confirms them.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import { useFinishLog } from './useFinishLog'
import { useMealSession } from './useMealSession'
import { useAnalyzeMeal } from '@/data/hooks'
import { api } from '@/data/repositories'
import type { FoodNote, MealAnalysis, Macros } from '@/data/types'
import { shrinkImage } from '@/lib/image'
import { Header, Footer, Screen, Split } from '@/ui/layout'
import { Alert, Button, Card, EstimateBadge, Field, Skeleton, Stepper, StatusPill, TextLink } from '@/ui/primitives'
import { Camera, CheckCircle, Clock, ForkKnife, Image as ImageIcon, Info, PencilSimple } from '@/ui/icons'

const clock = (iso: string | number | Date) => new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }).toLowerCase()
const mmss = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
const r1 = (v: number | null) => (v == null ? null : Math.round(v * 10) / 10)
const fmtPortion = (v: number) => (v === 0.5 ? '½' : v === 1.5 ? '1½' : v === 2.5 ? '2½' : String(v))

function scale(m: Macros, p: number): Macros {
  const f = (v: number | null) => (v == null ? null : r1(v * p))
  return { kcal: f(m.kcal), carbsG: f(m.carbsG), proteinG: f(m.proteinG), fatG: f(m.fatG), fibreG: f(m.fibreG), sugarG: f(m.sugarG), sodiumMg: f(m.sodiumMg) }
}

export function LogMeal() {
  const session = useMealSession((s) => s.meal)
  return session ? <Eating /> : <Capture />
}

/* ------------------------------------------------------------------------------------------------ 1 + 2: photo, then review */
function Capture() {
  const { t } = useTranslation()
  const MACRO_ROWS: [keyof Macros, string, string][] = [
    ['kcal', t('log.meal.calories', 'Calories'), 'kcal'],
    ['carbsG', t('log.meal.carbs', 'Carbs'), 'g'],
    ['proteinG', t('log.meal.protein', 'Protein'), 'g'],
    ['fatG', t('log.meal.fat', 'Fat'), 'g'],
    ['fibreG', t('log.meal.fibre', 'Fibre'), 'g'],
    ['sugarG', t('log.meal.sugar', 'Sugar'), 'g'],
    ['sodiumMg', t('log.meal.saltSodium', 'Salt (sodium)'), 'mg'],
  ]
  const EDITABLE: [keyof Macros, string][] = [
    ['kcal', t('log.meal.caloriesKcal', 'Calories (kcal)')],
    ['carbsG', t('log.meal.carbsG', 'Carbs (g)')],
    ['proteinG', t('log.meal.proteinG', 'Protein (g)')],
    ['fatG', t('log.meal.fatG', 'Fat (g)')],
    ['sodiumMg', t('log.meal.saltMg', 'Salt (mg)')],
  ]
  const analyze = useAnalyzeMeal()
  const startMeal = useMealSession((s) => s.start)
  const { save, pending, error: saveError } = useFinishLog()
  const cameraRef = useRef<HTMLInputElement>(null)
  const galleryRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [description, setDescription] = useState('')
  const [res, setRes] = useState<MealAnalysis | null>(null)
  const [name, setName] = useState('')
  const [macros, setMacros] = useState<Macros | null>(null)
  const [portion, setPortion] = useState(1)
  const [edited, setEdited] = useState(false)
  const [editing, setEditing] = useState(false)
  const [note, setNote] = useState<FoodNote | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])

  const pick = async (f: File | undefined) => {
    if (!f) return
    setRes(null)
    setError(null)
    setFile(await shrinkImage(f))
    setPreview(URL.createObjectURL(f))
  }

  const run = async () => {
    if (!file) return
    setError(null)
    try {
      const r = await analyze.mutateAsync({ file, description })
      setRes(r)
      setName(r.name)
      setMacros(r.macros)
      setPortion(1)
      setEdited(false)
      setEditing(false)
      setNote(null)
      api.getFoodNote(r.name).then(setNote).catch(() => setNote(null))
    } catch (e) {
      setError(e instanceof Error ? e.message : t('log.meal.readError', 'We could not read the photo. Please try again.'))
    }
  }

  const reset = () => {
    setFile(null)
    setPreview(null)
    setRes(null)
    setError(null)
    setDescription('')
  }

  const shown = useMemo(() => (macros ? scale(macros, portion) : null), [macros, portion])
  const change = (k: keyof Macros, v: string) => {
    if (!macros) return
    const n = v.trim() === '' ? null : Math.max(0, Number(v) || 0)
    const next = { ...macros, [k]: n }
    // sugar and fibre are parts of the carbs, so they can never be larger than the carbs
    if (next.carbsG != null) {
      if (next.sugarG != null) next.sugarG = Math.min(next.sugarG, next.carbsG)
      if (next.fibreG != null) next.fibreG = Math.min(next.fibreG, next.carbsG)
    }
    setMacros(next)
    setEdited(true)
  }

  const payload = (startAt: Date, endAt: Date) => ({
    kind: 'meal' as const,
    name: name.trim() || res!.name,
    description: description.trim() || undefined,
    startAt: startAt.toISOString(),
    endAt: endAt.toISOString(),
    portion,
    kcal: shown!.kcal,
    carbsG: shown!.carbsG,
    proteinG: shown!.proteinG,
    fatG: shown!.fatG,
    sugarG: shown!.sugarG,
    fibreG: shown!.fibreG,
    sodiumMg: shown!.sodiumMg,
    analysisId: res!.analysisId,
    edited,
    valuesFrom: edited ? ('user' as const) : ('ai' as const),
  })

  const begin = () => {
    if (!res || !shown) return
    startMeal({ startedAt: new Date().toISOString(), description, analysis: res, portion, name: name.trim() || res.name, macros: shown, edited, valuesFrom: edited ? 'user' : 'ai' })
  }
  const alreadyAte = () => {
    if (!res || !shown) return
    const end = new Date()
    save(payload(new Date(end.getTime() - 15 * 60_000), end))
  }

  const busy = analyze.isPending
  return (
    <Screen>
      <Header title={t('log.meal.title', 'Log a meal')} back backTo="E1" sub={t('log.meal.sub', 'Take a photo of your food. We read it and estimate the nutrients.')} />
      <Split>
        <section className="flex flex-col gap-3">
          {preview ? (
            <div className="relative overflow-hidden rounded-card border border-line bg-well">
              <img src={preview} alt={t('log.meal.alt', 'Your meal')} className="max-h-80 w-full object-cover" />
              {!busy && (
                <button type="button" onClick={reset} className="press absolute right-3 top-3 rounded-chip bg-ink/80 px-3 py-1.5 text-sub font-bold text-canvas">
                  {t('log.meal.retake', 'Retake')}
                </button>
              )}
            </div>
          ) : (
            <div className="flex min-h-56 flex-col items-center justify-center gap-3 rounded-card border-2 border-dashed border-line bg-well p-6 text-center">
              <ForkKnife size={40} className="text-brand" aria-hidden />
              <p className="text-body font-bold">{t('log.meal.photograph', 'Photograph your meal')}</p>
              <p className="text-sub text-ink2">{t('log.meal.photoTip', 'One photo of the whole plate or bowl works best. Good light helps.')}</p>
            </div>
          )}
          {!preview && (
            <div className="flex flex-col gap-2 md:flex-row md:[&>*]:flex-1">
              <Button icon={Camera} onClick={() => cameraRef.current?.click()}>
                {t('log.meal.takePhoto', 'Take photo')}
              </Button>
              <Button variant="secondary" icon={ImageIcon} onClick={() => galleryRef.current?.click()}>
                {t('log.meal.upload', 'Upload a photo')}
              </Button>
            </div>
          )}
          {preview && !res && (
            <>
              <Field label={t('log.meal.anything', "Anything the photo can't show? (optional)")} value={description} onChange={setDescription} multiline placeholder={t('log.meal.anythingPh', 'For example: only ate half the rice, no gravy, teh kosong')} />
              <Button onClick={() => void run()} disabled={busy}>
                {busy ? t('log.meal.reading', 'Reading your meal…') : t('log.meal.analyse', 'Analyse my meal')}
              </Button>
            </>
          )}
          {error && (
            <Alert tone="danger" title={t('log.meal.couldNotRead', 'We could not read that')}>
              {error}
            </Alert>
          )}
          <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => { void pick(e.target.files?.[0]); e.target.value = '' }} />
          <input ref={galleryRef} type="file" accept="image/*" className="hidden" onChange={(e) => { void pick(e.target.files?.[0]); e.target.value = '' }} />
        </section>

        <section className="flex flex-col gap-3">
          {busy && (
            <Card tone="soft" className="flex flex-col gap-3">
              <Skeleton className="h-6 w-2/3" />
              <Skeleton className="h-28 w-full" />
              <p className="text-sub text-ink2">{t('log.meal.readingAi', 'Reading your photo with AI. This takes a few seconds.')}</p>
            </Card>
          )}
          {res && shown && !busy && (
            <>
              <Card className="flex flex-col gap-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="break-words text-h2 font-bold">{name}</p>
                    <p className="text-sub text-ink2">{res.items.join(', ')}</p>
                  </div>
                  <EstimateBadge />
                </div>
                {res.confidence === 'check' && <StatusPill tone="warn">{t('log.meal.checkPortion', 'Check this: we are less sure about the portion')}</StatusPill>}
                <dl className="grid grid-cols-2 gap-x-4 gap-y-3 [[data-ts='2']_&]:grid-cols-1">
                  {MACRO_ROWS.map(([k, label, unit]) => (
                    <div key={k}>
                      <dt className="text-sub text-ink2">{label}</dt>
                      <dd className="num text-h2">
                        {shown[k] ?? '—'} <span className="text-sub text-ink3">{unit}</span>
                      </dd>
                    </div>
                  ))}
                </dl>
                {editing && macros && (
                  <div className="flex flex-col gap-3 border-t border-line pt-3">
                    <Field label={t('log.meal.name', 'Name')} value={name} onChange={(v) => { setName(v); setEdited(true) }} />
                    <div className="grid grid-cols-2 gap-3">
                      {EDITABLE.map(([k, label]) => (
                        <Field key={k} label={label} inputMode="decimal" value={macros[k] == null ? '' : String(macros[k])} onChange={(v) => change(k, v)} />
                      ))}
                    </div>
                    <p className="text-sub text-ink3">{t('log.meal.onePortion', 'These are for one portion. The portion below scales them.')}</p>
                  </div>
                )}
                <div className="flex flex-wrap gap-2">
                  {res.flags.includes('high_salt') && <StatusPill tone="warn">{t('log.meal.highSalt', 'High salt')}</StatusPill>}
                  {res.flags.includes('high_sugar') && <StatusPill tone="warn">{t('log.meal.highSugar', 'High sugar')}</StatusPill>}
                </div>
                <Button size="md" variant="secondary" icon={PencilSimple} onClick={() => setEditing((e) => !e)}>
                  {editing ? t('log.meal.doneEditing', 'Done editing') : t('log.meal.correct', 'Correct the numbers')}
                </Button>
                {res.portionNote && <p className="text-sub text-ink3">{res.portionNote}</p>}
                <p className="text-sub text-ink3">{t('log.meal.estimates', 'Nutrients are estimates until you confirm them. Your glucose rise will come from the sensor.')}</p>
              </Card>

              <div className="flex flex-col gap-2">
                <p className="text-body font-bold">{t('log.meal.portion', 'Portion')}</p>
                <Stepper label="portion" value={portion} onChange={setPortion} min={0.5} max={3} step={0.5} format={fmtPortion} />
              </div>

              {note && (
                <Alert tone={note.kind === 'higher' ? 'warn' : 'info'} icon={Info} title={t('log.meal.usual', 'Your usual response')}>
                  {note.text}
                  {note.range && (
                    <span className="mt-1 block text-ink2">
                      {t('log.meal.seen', 'Seen {{n}} times, rise {{from}} to {{to}} mmol/L.', { n: note.n, from: note.range[0].toFixed(1), to: note.range[1].toFixed(1) })}
                    </span>
                  )}
                </Alert>
              )}
            </>
          )}
        </section>
      </Split>
      {res && shown && !busy && (
        <>
        {saveError && <Alert tone="danger">{saveError}</Alert>}
        <Footer>
          <Button icon={Clock} disabled={pending} onClick={begin}>
            {t('log.meal.startEating', 'Start eating')}
          </Button>
          <TextLink onClick={alreadyAte} className="self-center">
            {t('log.meal.alreadyAte', 'I already finished eating')}
          </TextLink>
        </Footer>
        </>
      )}
    </Screen>
  )
}

/* ------------------------------------------------------------------------------------------------ 3: eating, then finish */
function Eating() {
  const { t } = useTranslation()
  const meal = useMealSession((s) => s.meal)!
  const clear = useMealSession((s) => s.clear)
  const { save, pending, error } = useFinishLog()
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [])
  const elapsed = Math.max(0, Math.round((now - new Date(meal.startedAt).getTime()) / 1000))
  const m = meal.macros

  const finish = () =>
    save(
      {
        kind: 'meal',
        name: meal.name,
        description: meal.description.trim() || undefined,
        startAt: meal.startedAt,
        endAt: new Date().toISOString(),
        portion: meal.portion,
        kcal: m.kcal,
        carbsG: m.carbsG,
        proteinG: m.proteinG,
        fatG: m.fatG,
        sugarG: m.sugarG,
        fibreG: m.fibreG,
        sodiumMg: m.sodiumMg,
        analysisId: meal.analysis.analysisId,
        edited: meal.edited,
        valuesFrom: meal.valuesFrom,
      },
      clear,
    )

  return (
    <Screen>
      <Header title={t('log.meal.enjoy', 'Enjoy your meal')} back backTo="E1" sub={t('log.meal.enjoySub', 'Tap the button when you are done. That time goes on your timeline.')} />
      <Card tone="hero" className="flex flex-col items-center gap-3 py-8 text-center">
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-soft text-brand">
          <ForkKnife size={28} aria-hidden />
        </span>
        <p className="text-h2 font-bold">{meal.name}</p>
        <p className="num text-display tabular-nums" aria-live="off">
          {mmss(elapsed)}
        </p>
        <p className="text-sub text-ink2">{t('log.meal.startedAt', 'Started at {{time}}', { time: clock(meal.startedAt) })}</p>
        {m.carbsG != null && (
          <p className="text-sub text-ink2">
            <Trans i18nKey="log.meal.about" defaults="About <0>{{carbs}} g</0> carbs{{kcal}} (estimate)" values={{ carbs: Math.round(m.carbsG), kcal: m.kcal != null ? t('log.meal.kcal', ', {{n}} kcal', { n: Math.round(m.kcal) }) : '' }} components={[<b key="0" className="text-ink" />]} />
          </p>
        )}
      </Card>
      {error && <Alert tone="danger">{error}</Alert>}
      <Footer>
        <Button icon={CheckCircle} disabled={pending} onClick={finish}>
          {pending ? t('log.meal.saving', 'Saving…') : t('log.meal.finished', "I've finished eating")}
        </Button>
        <TextLink onClick={clear} className="self-center">
          {t('log.meal.cancel', 'Cancel this meal')}
        </TextLink>
      </Footer>
    </Screen>
  )
}
