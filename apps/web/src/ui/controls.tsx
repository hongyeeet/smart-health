import { useTranslation } from 'react-i18next'
import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { motion } from 'motion/react'
import { cn } from '@/lib/cn'
import { ease } from '@/motion/tokens'
import { ArrowLeft } from './icons'

/** Equal-width segmented switch (period 7 / 30 / 90). The pill slides to the choice. */
export function Segmented<T extends string | number>({ options, value, onChange, label }: { options: { value: T; label: string }[]; value: T; onChange: (v: T) => void; label: string }) {
  const id = useId()
  return (
    <div role="radiogroup" aria-label={label} className="flex rounded-chip border border-line bg-well p-1">
      {options.map((o) => {
        const on = o.value === value
        return (
          <button key={String(o.value)} type="button" role="radio" aria-checked={on} onClick={() => onChange(o.value)} className="press relative min-h-11 flex-1 whitespace-nowrap rounded-chip px-2 text-sub font-bold sm:px-3">
            {on && <motion.span layoutId={`seg-${id}`} className="absolute inset-0 rounded-chip bg-card shadow-lift" transition={{ duration: 0.2, ease: ease.inOut }} />}
            <span className={cn('relative text-center', on ? 'text-ink' : 'text-ink2')}>{o.label}</span>
          </button>
        )
      })}
    </div>
  )
}

/** Scrollable tab strip with a sliding underline. */
export function TabStrip<T extends string>({ tabs, value, onChange, label, flush }: { tabs: { value: T; label: string }[]; value: T; onChange: (v: T) => void; label: string; /** Do not bleed into the screen padding from a tablet up, where the padding is wider than the strip assumes. */ flush?: boolean }) {
  const id = useId()
  const ref = useRef<HTMLDivElement>(null)
  /** more tabs off to the right: fade the edge so a cut-off tab reads as "scroll for more" */
  const [more, setMore] = useState(false)
  const measure = () => {
    const box = ref.current
    if (box) setMore(box.scrollLeft + box.clientWidth < box.scrollWidth - 4)
  }
  useEffect(() => {
    const box = ref.current
    const el = box?.querySelector<HTMLElement>('[aria-selected="true"]')
    if (box && el) box.scrollTo({ left: el.offsetLeft - (box.clientWidth - el.offsetWidth) / 2 })
    measure()
  }, [value])
  useEffect(() => {
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [])
  return (
    <div ref={ref} onScroll={measure} style={more ? { maskImage: 'linear-gradient(to right, black calc(100% - 28px), transparent)', WebkitMaskImage: 'linear-gradient(to right, black calc(100% - 28px), transparent)' } : undefined} role="tablist" aria-label={label} className={cn('hide-scroll relative -mx-5 flex gap-1 overflow-x-auto border-b border-line px-5', flush && 'md:mx-0 md:px-0')}>
      {tabs.map((t) => {
        const on = t.value === value
        return (
          <button key={t.value} type="button" role="tab" aria-selected={on} onClick={() => onChange(t.value)} className={cn('press relative flex-none whitespace-nowrap px-3 py-3 text-sub font-bold', on ? 'text-brand' : 'text-ink2')}>
            {t.label}
            {on && <motion.span layoutId={`tab-${id}`} className="absolute inset-x-2 -bottom-px h-[3px] rounded-full bg-brand" transition={{ duration: 0.2, ease: ease.inOut }} />}
          </button>
        )
      })}
    </div>
  )
}

/** Number pad for glucose and similar entries. */
export function NumberPad({ value, onChange, max = 5 }: { value: string; onChange: (v: string) => void; max?: number }) {
  const { t } = useTranslation()
  const press = (k: string) => {
    if (k === 'back') return onChange(value.slice(0, -1))
    if (k === '.' && value.includes('.')) return
    if (value.replace('.', '').length >= max) return
    onChange(value === '0' && k !== '.' ? k : value + k)
  }
  const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', 'back']
  return (
    <div className="grid grid-cols-3 gap-2" role="group" aria-label={t('controls.numberPad', 'Number pad')}>
      {keys.map((k) => (
        <button key={k} type="button" onClick={() => press(k)} aria-label={k === 'back' ? t('controls.delete', 'Delete') : k === '.' ? t('controls.decimal', 'Decimal point') : k} className="press flex min-h-16 items-center justify-center rounded-card border border-line bg-card font-serif text-xl font-medium text-ink">
          {k === 'back' ? <ArrowLeft size={24} aria-hidden /> : k}
        </button>
      ))}
    </div>
  )
}

/** A labelled group of single-choice cards (workout type, intensity). */
export function ChoiceCards<T extends string>({ options, value, onChange, label }: { options: { value: T; title: string; sub: string; icon?: ReactNode }[]; value: T | null; onChange: (v: T) => void; label: string }) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-col gap-2">
      {options.map((o) => {
        const on = o.value === value
        return (
          <button key={o.value} type="button" role="radio" aria-checked={on} onClick={() => onChange(o.value)} className={cn('press flex items-center gap-3 rounded-card border-[1.5px] p-3.5 text-left', on ? 'border-brand bg-brand-soft' : 'border-line bg-card')}>
            {o.icon && <span className={cn('flex h-11 w-11 flex-none items-center justify-center rounded-full', on ? 'bg-brand text-on-brand' : 'bg-well text-ink2')}>{o.icon}</span>}
            <span className="min-w-0 flex-1">
              <span className={cn('block text-body font-bold', on && 'text-brand')}>{o.title}</span>
              <span className="block text-sub text-ink2">{o.sub}</span>
            </span>
          </button>
        )
      })}
    </div>
  )
}

/** 1 to 5 rating row. */
/**
 * One colour ramp for every 1 to 5 scale (mood, stress, sleep, energy, how strong, how hard), so the same step is the
 * same colour in every row. It runs from a light tint at 1 to the full brand colour at 5. It is deliberately not
 * red-to-green: for stress, a high number is not "good", so the colour shows the amount, not a verdict.
 */
export const RAMP = [14, 32, 52, 76, 100] as const
const rampBg = (n: number) => `color-mix(in oklab, var(--c-brand) ${RAMP[n - 1]}%, var(--c-card))`

/** A 1 to 5 choice. `value` null means nothing chosen yet (no default is shown as chosen). */
export function Rating({ value, onChange, label, lowLabel, highLabel }: { value: number | null; onChange: (n: number) => void; label: string; lowLabel: string; highLabel: string }) {
  return (
    <div className="flex flex-col gap-2" role="radiogroup" aria-label={label}>
      <p className="text-body font-bold">{label}</p>
      <div className="flex gap-2">
        {[1, 2, 3, 4, 5].map((n) => {
          const on = value === n
          return (
            <button
              key={n}
              type="button"
              role="radio"
              aria-checked={on}
              aria-label={`${label} ${n} of 5`}
              onClick={() => onChange(n)}
              style={{ background: rampBg(n) }}
              className={cn('press flex min-h-14 flex-1 items-center justify-center rounded-card border-[1.5px] font-serif text-h2 font-medium transition-[box-shadow,transform]', RAMP[n - 1]! >= 52 ? 'text-on-brand' : 'text-ink', on ? 'scale-[1.04] border-ink shadow-[0_0_0_3px_var(--c-card),0_0_0_5px_var(--c-ink)]' : 'border-transparent opacity-80')}
            >
              {n}
            </button>
          )
        })}
      </div>
      <div className="flex justify-between text-sub text-ink3">
        <span>{lowLabel}</span>
        <span>{highLabel}</span>
      </div>
    </div>
  )
}
