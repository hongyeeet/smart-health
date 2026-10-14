/**
 * E2 — Log a meal.
 *
 * Two steps, as in the approved mock-up: 1 "Photo" (the photo, the tips and an optional note, with the recent meals and today so
 * far at the side), 2 "Check the numbers" (the dish and its items, the six totals and the fibre line, with the usual meal and a
 * lighter idea at the side). Reading the photo shows a waiting screen with Cancel. Any failure offers: try again, choose another
 * photo, or enter the meal by hand. "Start eating" begins a timer (kept until "I've finished eating"); "I already finished" saves
 * straight away. Every number is an estimate until the person confirms it; a value the reading could not judge is "Not judged",
 * never 0.
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
import { cn } from '@/lib/cn'
import { useBack } from '@/app/navigation'
import { Footer, Screen, Split } from '@/ui/layout'
import { Alert, Button, Card, TextLink } from '@/ui/primitives'
import { CaretLeft, CheckCircle, Clock, ForkKnife } from '@/ui/icons'
import { clock, mmss, scaleMacros, type NutrientKey } from './meal/mealMath'
import { mealPayload, type MealDraft } from './meal/mealDraft'
import { useIsTouch } from './meal/useIsTouch'
import { MealPhotoStep, PhotoPreview } from './meal/MealPhotoStep'
import { MealReading } from './meal/MealReading'
import { MealResult } from './meal/MealResult'
import { MealError } from './meal/MealError'
import { MealManualForm, type ManualPrefill } from './meal/MealManualForm'
import { PhotoSide, ResultSide } from './meal/MealSide'

/** Start-to-finish used when the person taps "I already finished eating": the start time is not asked for, so it is assumed. */
const ASSUMED_MEAL_MINUTES = 15

export function LogMeal() {
  const { meal } = useMealSession()
  return meal ? <Eating /> : <Capture />
}

type Step = 'photo' | 'reading' | 'result' | 'error' | 'manual'

/* ------------------------------------------------------------------------------------------------ 1 to 2: photo, reading, result */
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
  /** the manual form filled in from a recent meal ("Log again"); null for a blank form */
  const [prefill, setPrefill] = useState<ManualPrefill | null>(null)

  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview)
    },
    [preview],
  )
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
      api
        .getFoodNote(r.name)
        .then((n) => setNote(n))
        .catch(() => setNote(null))
    } catch (e) {
      // the person pressed Cancel: the screen has already moved on, so nothing is shown
      if (abortRef.current !== ctrl) return
      setReadError(
        e instanceof MealReadError ? e : new MealReadError('bad_response', t('log.meal.readError', 'We could not read the photo. Please try again.')),
      )
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
    res && shown ? { name: name.trim() || res.name, description, portion, macros: shown, analysis: res, edited, valuesFrom: edited ? 'user' : 'ai' } : null

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
  const goManual = () => {
    setPrefill(null)
    setStep('manual')
  }
  const logAgain = (p: ManualPrefill) => {
    setPrefill(p)
    setStep('manual')
  }

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
    photo: t('log.meal.sub', 'One photo is enough. We read it and estimate the nutrients, and you can correct anything.'),
    reading: t('log.meal.subReading', 'This usually takes a few seconds.'),
    result: t('log.meal.sub', 'One photo is enough. We read it and estimate the nutrients, and you can correct anything.'),
    error: t('log.meal.subError', 'The photo could not be read. Choose one of the ways forward below.'),
    manual: t('log.meal.subManual', 'Type in what you ate. Leave a number blank if you do not know it.'),
  }
  const stepNo: 1 | 2 = step === 'result' ? 2 : 1
  const withSide = step === 'photo' || (step === 'result' && !!res && !!shown)

  return (
    <Screen>
      <MealTitle title={t('log.meal.title', 'Log a meal')} sub={subs[step]} />
      {step !== 'manual' && <Steps on={stepNo} />}
      {inputs}

      <div className={cn('flex flex-col gap-4', withSide && 'xl:grid xl:grid-cols-[minmax(0,1fr)_332px] xl:items-start xl:gap-6')}>
        <div className="flex min-w-0 flex-col gap-4">
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
              <section className="flex flex-col gap-3">{preview && <PhotoPreview key={preview} src={preview} onChange={changePhoto} />}</section>
              <section className="flex flex-col gap-4">
                <MealError error={readError} onTryAgain={retry} onChoosePhoto={openGallery} onManual={goManual} />
              </section>
            </Split>
          )}

          {step === 'result' && res && shown && (
            <>
              <MealResult
                photo={
                  preview && <PhotoPreview key={preview} src={preview} onChange={changePhoto} compact changeLabel={t('log.meal.changePhotoShort', 'Change')} />
                }
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
              <p className="text-sub text-ink2">{t('log.meal.canChange', 'You can still change any number.')}</p>
              <Footer>
                <Button variant="secondary" onClick={() => setStep('photo')}>
                  {t('log.meal.backToPhoto', 'Back to the photo')}
                </Button>
                <Button variant="secondary" icon={CheckCircle} onClick={alreadyAte}>
                  {t('log.meal.alreadyAte', 'I already finished eating')}
                </Button>
                <Button icon={Clock} onClick={begin}>
                  {t('log.meal.startEating', 'Start eating')}
                </Button>
              </Footer>
            </>
          )}

          {step === 'manual' && (
            <>
              {saveError && <Alert tone="danger">{saveError}</Alert>}
              <MealManualForm
                key={prefill ? 'again' : 'blank'}
                initial={prefill ?? undefined}
                onBack={preview ? () => setStep('photo') : undefined}
                onStart={(d) => startMeal({ ...d, startedAt: new Date().toISOString() })}
                onFinish={(d) => {
                  const end = new Date()
                  save(mealPayload(d, new Date(end.getTime() - ASSUMED_MEAL_MINUTES * 60_000).toISOString(), end.toISOString()))
                }}
              />
            </>
          )}
        </div>

        {step === 'photo' && (
          <aside className="flex min-w-0 flex-col gap-4">
            <PhotoSide onLogAgain={logAgain} />
          </aside>
        )}
        {step === 'result' && res && shown && (
          <aside className="flex min-w-0 flex-col gap-4">
            <ResultSide shown={shown} />
          </aside>
        )}
      </div>
    </Screen>
  )
}

/** The title row of the meal screens: a "Back to Log" button, the serif title, and the one-line description under it. */
function MealTitle({ title, sub }: { title: string; sub: string }) {
  const { t } = useTranslation()
  const goBack = useBack('E1')
  return (
    <header className="flex flex-col gap-2 pb-1 pt-1">
      <div className="flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={goBack}
          className="press flex min-h-12 items-center gap-1.5 rounded-card border border-line bg-card px-4 text-sub font-bold text-ink"
        >
          <CaretLeft size={18} aria-hidden />
          {t('log.meal.backToLog', 'Back to Log')}
        </button>
        <h1 className="min-w-0 break-words font-serif text-h1 font-medium tracking-tight text-ink">{title}</h1>
      </div>
      <p className="text-sub text-ink2">{sub}</p>
    </header>
  )
}

/** "1 Photo, 2 Check the numbers": the current step is filled, the step before it is shown as done. */
function Steps({ on }: { on: 1 | 2 }) {
  const { t } = useTranslation()
  const item = (n: 1 | 2, label: string) => {
    const active = on === n
    const done = on > n
    return (
      <li
        aria-current={active ? 'step' : undefined}
        className={cn('flex items-center gap-2 text-sub font-bold', active ? 'text-ink' : done ? 'text-ink2' : 'text-ink3')}
      >
        <span
          className={cn(
            'flex h-6 w-6 items-center justify-center rounded-full text-micro font-bold',
            active ? 'bg-brand text-on-brand' : done ? 'bg-brand-soft text-brand' : 'bg-line text-ink2',
          )}
        >
          {n}
        </span>
        {label}
      </li>
    )
  }
  return (
    <ol className="flex flex-wrap items-center gap-x-3 gap-y-2" aria-label={t('log.meal.steps', 'Steps')}>
      {item(1, t('log.meal.step1', 'Photo'))}
      <li aria-hidden className="h-0.5 w-9 bg-line" />
      {item(2, t('log.meal.step2', 'Check the numbers'))}
    </ol>
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
      <MealTitle
        title={t('log.meal.enjoy', 'Enjoy your meal')}
        sub={t('log.meal.enjoySub', 'Tap the button when you are done. That time goes on your timeline.')}
      />
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
              <Trans
                i18nKey="log.meal.aboutYours"
                defaults="About <0>{{carbs}} g</0> carbs{{kcal}} (your numbers)"
                values={{ carbs: Math.round(m.carbsG), kcal: m.kcal != null ? t('log.meal.kcal', ', {{n}} kcal', { n: Math.round(m.kcal) }) : '' }}
                components={[<b key="0" className="text-ink" />]}
              />
            ) : (
              <Trans
                i18nKey="log.meal.about"
                defaults="About <0>{{carbs}} g</0> carbs{{kcal}} (estimate)"
                values={{ carbs: Math.round(m.carbsG), kcal: m.kcal != null ? t('log.meal.kcal', ', {{n}} kcal', { n: Math.round(m.kcal) }) : '' }}
                components={[<b key="0" className="text-ink" />]}
              />
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
