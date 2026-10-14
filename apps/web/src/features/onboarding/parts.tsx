import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { appConfig } from '@/config/app'
import { href } from '@/app/routeIds'
import { cn } from '@/lib/cn'
import { useUi } from '@/state/store'
import { startsInSetup } from './startGate'
import { useCancelNewPerson, useIsNewPerson } from './newPerson'
import { Alert, Button, Card, Skeleton, StatusPill, TextLink } from '@/ui/primitives'
import { Check, Leaf, Lock } from '@/ui/icons'

/** The pages the person sees: Welcome (1), eligibility (2), About you (3 to 10). The summary (A6) comes after the last one and is not counted. */
export const TOTAL_STEPS = 10

/* ------------------------------------ frame ------------------------------------ */
/** Brand row at the top of every onboarding screen. */
export function TopBar() {
  const { t } = useTranslation()
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3 pt-2">
      <div className="flex items-center gap-2.5">
        <span className="flex h-9 w-9 items-center justify-center rounded-field bg-brand text-on-brand">
          <Leaf size={20} aria-hidden />
        </span>
        <span className="font-serif text-h2 font-medium tracking-tight">{appConfig.name}</span>
        <StatusPill tone="brand" bare>
          {t('onboarding.tag', 'Setup')}
        </StatusPill>
      </div>
      <StatusPill tone="neutral" icon={Lock}>
        {t('onboarding.yourAnswers', 'Your answers')}
      </StatusPill>
    </div>
  )
}

/**
 * A small "i" button that opens a short note. It opens on a click or tap, and with Enter or Space from the keyboard; Escape or a tap
 * outside closes it. It is not hover-only, so touch and keyboard users get the same note.
 */
export function InfoTip({ label, children }: { label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const id = useId()
  const box = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    if (!open) return
    const onDown = (e: PointerEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])
  return (
    <span ref={box} className="relative inline-flex align-middle">
      <button
        type="button"
        aria-label={label}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
        className="press flex h-12 w-12 flex-none items-center justify-center"
      >
        <span aria-hidden className="flex h-8 w-8 items-center justify-center rounded-full border-[1.5px] border-brand bg-card font-serif text-sub font-semibold text-brand">
          i
        </span>
      </button>
      {open && (
        <span id={id} className="absolute left-0 top-12 z-20 flex w-[min(20rem,calc(100vw-3rem))] flex-col gap-2 rounded-card border border-line bg-card p-3.5 text-left text-sub text-ink shadow-lift">
          {children}
        </span>
      )}
    </span>
  )
}

/** Step count, step name, segmented bar, then the screen title and what the step is for. */
export function StepHead({ step, name, title, sub }: { step: number; name: string; title: string; sub?: string }) {
  const { t } = useTranslation()
  const label = t('onboarding.progress', 'Step {{step}} of {{total}}', { step, total: TOTAL_STEPS })
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 text-sub">
          <span className="font-bold text-brand">{label}</span>
          <span className="text-ink2">{name}</span>
        </div>
        <div className="flex gap-1" role="img" aria-label={`${label}: ${name}`}>
          {Array.from({ length: TOTAL_STEPS }, (_, i) => (
            <span key={i} className={cn('h-1.5 flex-1 rounded-full', i < step - 1 ? 'bg-brand' : i === step - 1 ? 'bg-ok' : 'bg-line')} />
          ))}
        </div>
      </div>
      <div>
        <h1 className="break-words font-serif text-h1 font-medium tracking-tight text-ink">{title}</h1>
        {sub && <p className="mt-1.5 text-sub text-ink2">{sub}</p>}
      </div>
    </div>
  )
}

/** A white card that groups related questions, with an optional heading. */
export function Group({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <Card as="section" className="flex flex-col gap-5">
      {title && <h2 className="font-serif text-h2 font-medium tracking-tight text-ink">{title}</h2>}
      {children}
    </Card>
  )
}

/** Shown while the saved answers are read, so the form never shows another person's answers. */
export function LoadingAnswers() {
  const { t } = useTranslation()
  return (
    <div role="status" aria-live="polite" className="flex flex-col gap-3">
      <span className="sr-only">{t('onboarding.loading', 'Loading your answers')}</span>
      <Skeleton className="h-8 w-2/3" />
      <Skeleton className="h-40 w-full" />
    </div>
  )
}

/** The saved answers could not be read: the form shows what is on this device. */
export function LoadNotice() {
  const { t } = useTranslation()
  return <Alert tone="warn">{t('onboarding.loadFailed', 'We could not load your saved answers just now. The answers on this device are shown.')}</Alert>
}

/** Mr Tan is demo data: his answers can be read here, but nothing is saved to his record from onboarding. */
export function DemoNotice() {
  const { t } = useTranslation()
  return <Alert tone="info">{t('onboarding.demo.notice', 'Mr Tan is demo data. His record is not changed from here. To try setup, switch to the demo user or start as a new person.')}</Alert>
}

/**
 * Back and Continue, side by side, always on screen. It holds only the two buttons, so it stays short (about 80 px at 100% text,
 * about 100 px at 200%, because button text grows to 150% there). The bar never grows past 35% of the screen height. Its own space is part of the page, so
 * nothing at the end of a page is covered. The links ("Finish later" and the rest) sit in the page flow, above it: see Later.
 */
export function Dock({ onBack, onNext, nextLabel, nextDisabled }: { onBack?: () => void; onNext: () => void; nextLabel: string; nextDisabled?: boolean }) {
  const { t } = useTranslation()
  return (
    <div data-dock className="sticky bottom-0 -mx-5 mt-2 flex max-h-[35vh] flex-col overflow-y-auto bg-gradient-to-t from-canvas from-70% to-transparent px-5 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 md:-mx-8 md:px-8">
      <div className="flex gap-3">
        {onBack && (
          <Button variant="secondary" onClick={onBack} className="!w-auto flex-none px-6">
            {t('common.back', 'Back')}
          </Button>
        )}
        <Button disabled={nextDisabled} onClick={onNext}>
          {nextLabel}
        </Button>
      </div>
    </div>
  )
}

/**
 * The secondary links, in the page flow above the Dock (not inside the sticky bar). "Finish later" leaves for Home at any point:
 * each page is already saved when Continue works, and the rest can be changed later in Me, Data and account.
 */
export function Later({ children, label }: { children?: ReactNode; label?: string }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const demo = startsInSetup(useUi((s) => s.userKey))      // the demo user skips set-up instead of finishing it later
  const newPerson = useIsNewPerson()                       // a new person who leaves is not created at all
  const cancel = useCancelNewPerson()
  return (
    <div className="flex flex-col items-center gap-1 pt-2">
      {children}
      <TextLink onClick={newPerson ? cancel : () => navigate(href('B1'))} className="self-center">
        {newPerson ? t('onboarding.cancelNew', 'Cancel. Do not create this user') : demo ? t('onboarding.skipV2', 'Skip') : (label ?? t('onboarding.later', 'Finish later'))}
      </TextLink>
    </div>
  )
}

/** Unit choice (for example % or mmol/mol). The same look as the other choice bars, with a 48 px tap target. */
export function UnitToggle<T extends string>({ options, value, onChange, label }: { options: { value: T; label: string }[]; value: T; onChange: (v: T) => void; label: string }) {
  return (
    <div role="radiogroup" aria-label={label} className="flex rounded-chip border border-line bg-well p-1">
      {options.map((o) => {
        const on = o.value === value
        return (
          <button key={o.value} type="button" role="radio" aria-checked={on} onClick={() => onChange(o.value)} className={cn('press min-h-12 flex-1 rounded-chip px-3 text-sub font-bold', on ? 'bg-card text-ink shadow-lift' : 'text-ink2')}>
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

/* ------------------------------------ questions ------------------------------------ */
export interface Option<T extends string> {
  value: T
  label: string
  /** a second line: examples or a plain description */
  sub?: string
}

export function Question({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <p className="text-sub font-bold text-ink">{label}</p>
      {children}
      {hint && <p className="text-sub text-ink3">{hint}</p>}
    </div>
  )
}

/** One answer: a tick box, the answer and, when given, a second line. Pressed state is announced, never colour alone. */
function OptionChip({ on, onClick, label, sub, wide }: { on: boolean; onClick: () => void; label: string; sub?: string; wide?: boolean }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={cn('press flex min-h-12 items-center gap-2.5 rounded-field border-[1.5px] px-3.5 py-2 text-left text-sub', on ? 'border-brand bg-brand-soft text-brand' : 'border-line bg-card text-ink', wide && 'w-full')}
    >
      <span className={cn('flex h-5 w-5 flex-none items-center justify-center rounded-md border-[1.5px]', on ? 'border-brand bg-brand text-on-brand' : 'border-line bg-card')}>{on && <Check size={14} weight="bold" aria-hidden />}</span>
      <span className="min-w-0">
        <span className={cn('block break-words', on && 'font-bold')}>{label}</span>
        {sub && <span className="block break-words font-normal text-ink2">{sub}</span>}
      </span>
    </button>
  )
}

/** Pick one. Tapping the chosen answer again clears it, so every optional question can be left unanswered. */
export function PickOne<T extends string>({ label, hint, options, value, onChange, stack }: { label: string; hint?: string; options: Option<T>[]; value: T | null; onChange: (v: T | null) => void; stack?: boolean }) {
  return (
    <Question label={label} hint={hint}>
      <div className={cn('flex gap-2', stack ? 'flex-col' : 'flex-wrap')} role="group" aria-label={label}>
        {options.map((o) => (
          <OptionChip key={o.value} on={value === o.value} onClick={() => onChange(value === o.value ? null : o.value)} label={o.label} sub={o.sub} wide={stack} />
        ))}
      </div>
    </Question>
  )
}

/** Pick any. `none` is the value of a "None of these" answer: choosing it clears the rest, and choosing anything else clears it. */
export function PickMany<T extends string>({ label, hint, options, value, onChange, none, stack }: { label: string; hint?: string; options: Option<T>[]; value: T[]; onChange: (v: T[]) => void; none?: T; stack?: boolean }) {
  const toggle = (v: T) => {
    if (value.includes(v)) return onChange(value.filter((x) => x !== v))
    if (v === none) return onChange([v])
    onChange([...value.filter((x) => x !== none), v])
  }
  return (
    <Question label={label} hint={hint}>
      <div className={cn('flex gap-2', stack ? 'flex-col' : 'flex-wrap')} role="group" aria-label={label}>
        {options.map((o) => (
          <OptionChip key={o.value} on={value.includes(o.value)} onClick={() => toggle(o.value)} label={o.label} sub={o.sub} wide={stack} />
        ))}
      </div>
    </Question>
  )
}

/** A 1 to N number scale with a label at each end. The number is recorded as given; no meaning is attached to it here. */
export function Scale({ label, max, value, onChange, lowLabel, highLabel }: { label: string; max: number; value: string | null; onChange: (v: string | null) => void; lowLabel: string; highLabel: string }) {
  return (
    <Question label={label}>
      {/* more than 5 choices wrap to rows of 4 so each button is at least 44 px wide on a phone (seven in one row were 40 px) */}
      <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${max > 5 ? 4 : max}, minmax(0, 1fr))` }} role="group" aria-label={label}>
        {Array.from({ length: max }, (_, i) => String(i + 1)).map((n) => {
          const on = value === n
          return (
            <button key={n} type="button" aria-pressed={on} aria-label={`${n} of ${max}`} onClick={() => onChange(on ? null : n)} className={cn('press flex min-h-12 items-center justify-center rounded-field border-[1.5px] font-serif text-h2 font-medium', on ? 'border-brand bg-brand text-on-brand' : 'border-line bg-card text-ink')}>
              {n}
            </button>
          )
        })}
      </div>
      <div className="flex justify-between gap-3 text-sub text-ink2">
        <span>{lowLabel}</span>
        <span className="text-right">{highLabel}</span>
      </div>
    </Question>
  )
}

/* ------------------------------------ helpers ------------------------------------ */
/**
 * Where "Continue" goes. A step opened from the summary (?review=1) returns to the summary instead of walking the whole
 * flow again.
 */
export function useStepNav() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const review = params.get('review') === '1'
  return { review, next: (path: string) => navigate(review ? href('A6') : path) }
}

/** "07:00" to "7:00 am". */
export function clock(hhmm: string): string {
  const [h, m] = hhmm.split(':').map(Number)
  if (h === undefined || m === undefined || Number.isNaN(h) || Number.isNaN(m)) return hhmm
  return `${h % 12 === 0 ? 12 : h % 12}:${String(m).padStart(2, '0')} ${h < 12 ? 'am' : 'pm'}`
}
