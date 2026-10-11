/**
 * E2 — Log a meal.
 *
 * Steps: 1 photo (and an optional description), 2 "Reading your meal…" with Cancel, 3 the estimate as a macro card with
 * a portion stepper and the two actions. Any failure offers: try again, choose another photo, or enter the meal by hand.
 * "Start eating" begins a timer (kept until "I've finished eating"); "I already finished" saves straight away. Every
 * number is an estimate until the person confirms it; a value the reading could not judge is "Not judged", never 0.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import { useFinishLog } from './useFinishLog'
import { useMealSession } from './useMealSession'
import { useAnalyzeMeal } from '@/data/hooks'
import { api } from '@/data/repositories'
import { MealReadError } from '@/data/repositories/types'
import type { FoodNote, Macros, MealAnalysis } from '@/data/types'
import { shrinkImage } from '@/lib/image'
import { Header, Footer, Screen, Split } from '@/ui/layout'
import { Alert, Button, Card, TextLink } from '@/ui/primitives'
import { CheckCircle, Clock, ForkKnife } from '@/ui/icons'
import { clock, mmss, scaleMacros, type NutrientKey } from './meal/mealMath'
import { mealPayload, type MealDraft } from './meal/mealDraft'
import { useIsTouch } from './meal/useIsTouch'
import { MealPhotoStep, PhotoPreview } from './meal/MealPhotoStep'
import { MealReading } from './meal/MealReading'
import { MealResult } from './meal/MealResult'
import { MealError } from './meal/MealError'
import { MealManualForm } from './meal/MealManualForm'

/** Start-to-finish used when the person taps "I already finished eating": the start time is not asked for, so it is assumed. */
const ASSUMED_MEAL_MINUTES = 15

export function LogMeal() {
  const { meal } = useMealSession()
  return meal ? <Eating /> : <Capture />
}

type Step = 'photo' | 'reading' | 'result' | 'error' | 'manual'

/* ------------------------------------------------------------------------------------------------ 1 to 3: photo, reading, result */
function Capture() {
  const { t } = useTranslation()
  const analyze = useAnalyzeMeal()
  const { start: startMeal } = useMealSession()
  const { save, error: saveError } = useFinishLog()
  const isTouch = useIsTouch()
  const cameraRef = useRef<HTMLInputElement>(null)
  const galleryRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  const [step, setStep] = useState<Step>('photo')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [description, setDescription] = useState('')
  const [res, setRes] = useState<MealAnalysis | null>(null)
  const [readError, setReadError] = useState<MealReadError | null>(null)
  const [name, setName] = useState('')
  /** the numbers for ONE portion, as the reading (or the person) gave them; the shown numbers are these times the portion */
  const [base, setBase] = useState<Macros | null>(null)
  const [portion, setPortion] = useState(1)
  const [touched, setTouched] = useState<Partial<Record<NutrientKey, true>>>({})
  const [nameEdited, setNameEdited] = useState(false)
  const [note, setNote] = useState<FoodNote | null>(null)

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview)
  }, [preview])
  useEffect(() => () => abortRef.current?.abort(), [])

  const shown = useMemo(() => (base ? scaleMacros(base, portion) : null), [base, portion])
  const edited = nameEdited || Object.keys(touched).length > 0

  const pick = async (picked: File | undefined) => {
    if (!picked) return
    // the smaller copy is what is sent and shown, so a photo the browser cannot display (HEIC) still gets a preview when it can be shrunk
    const small = await shrinkImage(picked)
    setFile(small)
    setPreview(URL.createObjectURL(small))
    setRes(null)
    setReadError(null)
    setNote(null)
    setStep('photo')
  }

  const read = async (photo: File, text: string) => {
    const ctrl = new AbortController()
    abortRef.current = ctrl
    setStep('reading')
    setReadError(null)
    try {
      const r = await analyze.mutateAsync({ file: photo, description: text, signal: ctrl.signal })
      if (abortRef.current !== ctrl) return
      setRes(r)
      setName(r.name)
      setBase(r.macros)
      setPortion(1)
      setTouched({})
      setNameEdited(false)
      setNote(null)
      setStep('result')
      api.getFoodNote(r.name).then((n) => setNote(n)).catch(() => setNote(null))
    } catch (e) {
      // the person pressed Cancel: the screen has already moved on, so nothing is shown
      if (abortRef.current !== ctrl) return
      setReadError(e instanceof MealReadError ? e : new MealReadError('bad_response', t('log.meal.readError', 'We could not read the photo. Please try again.')))
      setStep('error')
    } finally {
      if (abortRef.current === ctrl) abortRef.current = null
    }
  }

  const cancelReading = () => {
    abortRef.current?.abort()
    abortRef.current = null
    setStep('photo')
  }

  /** Changing a number: the box shows the amount for the chosen portion, and the stored value is for one portion. */
  const setAmount = (k: NutrientKey, v: number | null) => {
    if (!base) return
    const next: Macros = { ...base, [k]: v == null ? null : v / portion }
    // sugar and fibre are parts of the carbs, so they can never be larger than the carbs
    if (next.carbsG != null) {
      if (next.sugarG != null) next.sugarG = Math.min(next.sugarG, next.carbsG)
      if (next.fibreG != null) next.fibreG = Math.min(next.fibreG, next.carbsG)
    }
    setBase(next)
    setTouched((tc) => ({ ...tc, [k]: true }))
  }

  const draft = (): MealDraft | null =>
    res && shown
      ? { name: name.trim() || res.name, description, portion, macros: shown, analysis: res, edited, valuesFrom: edited ? 'user' : 'ai' }
      : null

  const begin = () => {
    const d = draft()
    if (d) startMeal({ ...d, startedAt: new Date().toISOString() })
  }
  const alreadyAte = () => {
    const d = draft()
    if (!d) return
    const end = new Date()
    save(mealPayload(d, new Date(end.getTime() - ASSUMED_MEAL_MINUTES * 60_000).toISOString(), end.toISOString()))
  }

  const openCamera = () => cameraRef.current?.click()
  const openGallery = () => galleryRef.current?.click()
  const changePhoto = () => (isTouch ? openCamera() : openGallery())
  const retry = () => {
    if (file) void read(file, description)
    else setStep('photo')
  }
  const goManual = () => setStep('manual')

  const inputs = (
    <>
      {isTouch && (
        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(e) => {
            void pick(e.target.files?.[0])
            e.target.value = ''
          }}
        />
      )}
      <input
        ref={galleryRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          void pick(e.target.files?.[0])
          e.target.value = ''
        }}
      />
    </>
  )

  const subs: Record<Step, string> = {
    photo: t('log.meal.sub', 'Take a photo of your food. We read it and estimate the nutrients.'),
    reading: t('log.meal.subReading', 'This usually takes a few seconds.'),
    result: t('log.meal.subResult', 'These numbers are estimates. Change anything that is not right, then save.'),
    error: t('log.meal.subError', 'The photo could not be read. Choose one of the ways forward below.'),
    manual: t('log.meal.subManual', 'Type in what you ate. Leave a number blank if you do not know it.'),
  }

  return (
    <Screen>
      <Header title={t('log.meal.title', 'Log a meal')} back backTo="E1" sub={subs[step]} />
      {inputs}

      {step === 'photo' && (
        <MealPhotoStep
          preview={preview}
          isTouch={isTouch}
          description={description}
          onDescription={setDescription}
          onOpenCamera={openCamera}
          onOpenGallery={openGallery}
          onRead={() => {
            if (file) void read(file, description)
          }}
          onManual={goManual}
        />
      )}

      {step === 'reading' && <MealReading preview={preview} onCancel={cancelReading} />}

      {step === 'error' && readError && (
        <Split>
          <section className="flex flex-col gap-3">
            {preview && <PhotoPreview key={preview} src={preview} onChange={changePhoto} />}
          </section>
          <section className="flex flex-col gap-4">
            <MealError error={readError} onTryAgain={retry} onChoosePhoto={openGallery} onManual={goManual} />
          </section>
        </Split>
      )}

      {step === 'result' && res && shown && (
        // A phone and a tablet: photo, the macro card, then the action bar, with only the primary button kept on screen (the "already
        // finished" link sits on its own line in the scroll area above it). A laptop: the photo and the one action bar on the left,
        // the macro card on the right; the action bar follows the scroll.
        <div className="grid gap-4 lg:grid-cols-2 lg:grid-rows-[auto_1fr] lg:items-start lg:gap-6 [&>*]:min-w-0">
          <section className="flex flex-col gap-3 lg:col-start-1 lg:row-start-1">
            {preview && <PhotoPreview key={preview} src={preview} onChange={changePhoto} />}
          </section>
          <section className="flex flex-col gap-4 lg:col-start-2 lg:row-span-2 lg:row-start-1">
            <MealResult
              name={name}
              onName={(v) => {
                setName(v)
                setNameEdited(true)
              }}
              items={res.items}
              confidence={res.confidence}
              shown={shown}
              touched={touched}
              onAmount={setAmount}
              flags={res.flags}
              changed={edited}
              portionNote={res.portionNote}
              portion={portion}
              onPortion={setPortion}
              note={note}
            />
            {saveError && <Alert tone="danger">{saveError}</Alert>}
          </section>
          <div className="contents lg:col-start-1 lg:row-start-2 lg:sticky lg:top-1 lg:flex lg:flex-col lg:items-stretch lg:gap-2">
            <TextLink onClick={alreadyAte} className="justify-self-center self-center text-center">
              {t('log.meal.alreadyAte', 'I already finished eating')}
            </TextLink>
            <div data-dock className="sticky bottom-0 -mx-5 flex flex-col bg-gradient-to-t from-canvas from-70% to-transparent px-5 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-4 md:static md:mx-0 md:bg-none md:px-0 md:pb-10 md:pt-0 lg:pb-0">
              <Button icon={Clock} onClick={begin}>
                {t('log.meal.startEating', 'Start eating')}
              </Button>
            </div>
          </div>
        </div>
      )}

      {step === 'manual' && (
        <>
          {saveError && <Alert tone="danger">{saveError}</Alert>}
          <MealManualForm
            onBack={preview ? () => setStep('photo') : undefined}
            onStart={(d) => startMeal({ ...d, startedAt: new Date().toISOString() })}
            onFinish={(d) => {
              const end = new Date()
              save(mealPayload(d, new Date(end.getTime() - ASSUMED_MEAL_MINUTES * 60_000).toISOString(), end.toISOString()))
            }}
          />
        </>
      )}
    </Screen>
  )
}

/* ------------------------------------------------------------------------------------------------ eating, then finish */
function Eating() {
  const { t } = useTranslation()
  const { meal: current, clear } = useMealSession()
  const meal = current!
  const { save, pending, error } = useFinishLog()
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])
  const elapsed = Math.max(0, Math.round((now - new Date(meal.startedAt).getTime()) / 1000))
  const m = meal.macros

  const finish = () => save(mealPayload(meal, meal.startedAt, new Date().toISOString()), clear)

  return (
    <Screen>
      <Header title={t('log.meal.enjoy', 'Enjoy your meal')} back backTo="E1" sub={t('log.meal.enjoySub', 'Tap the button when you are done. That time goes on your timeline.')} />
      <Card tone="hero" className="flex flex-col items-center gap-3 py-8 text-center">
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-soft text-brand">
          <ForkKnife size={28} aria-hidden />
        </span>
        <p className="text-h2 font-bold break-words">{meal.name}</p>
        <p className="num text-display tabular-nums" aria-live="off">
          {mmss(elapsed)}
        </p>
        <p className="text-sub text-ink2">{t('log.meal.startedAt', 'Started at {{time}}', { time: clock(meal.startedAt) })}</p>
        {m.carbsG != null && (
          <p className="text-sub text-ink2">
            {/* a meal the person typed or changed is shown with their own numbers, never as an estimate */}
            {meal.valuesFrom === 'user' ? (
              <Trans i18nKey="log.meal.aboutYours" defaults="About <0>{{carbs}} g</0> carbs{{kcal}} (your numbers)" values={{ carbs: Math.round(m.carbsG), kcal: m.kcal != null ? t('log.meal.kcal', ', {{n}} kcal', { n: Math.round(m.kcal) }) : '' }} components={[<b key="0" className="text-ink" />]} />
            ) : (
              <Trans i18nKey="log.meal.about" defaults="About <0>{{carbs}} g</0> carbs{{kcal}} (estimate)" values={{ carbs: Math.round(m.carbsG), kcal: m.kcal != null ? t('log.meal.kcal', ', {{n}} kcal', { n: Math.round(m.kcal) }) : '' }} components={[<b key="0" className="text-ink" />]} />
            )}
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
