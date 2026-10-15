import { useEffect, useId, useRef, type ReactNode } from 'react'
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
          <button key={String(o.value)} type="button" role="radio" aria-checked={on} onClick={() => onChange(o.value)} className="press relative min-h-11 flex-1 rounded-chip px-3 text-sub font-bold">
            {on && <motion.span layoutId={`seg-${id}`} className="absolute inset-0 rounded-chip bg-card shadow-lift" transition={{ duration: 0.2, ease: ease.inOut }} />}
            <span className={cn('relative text-center', on ? 'text-ink' : 'text-ink2')}>{o.label}</span>
          </button>
        )
      })}
    </div>
  )
}

/** Scrollable tab strip with a sliding underline. */
export function TabStrip<T extends string>({ tabs, value, onChange, label }: { tabs: { value: T; label: string }[]; value: T; onChange: (v: T) => void; label: string }) {
  const id = useId()
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const box = ref.current
    const el = box?.querySelector<HTMLElement>('[aria-selected="true"]')
    if (box && el) box.scrollTo({ left: el.offsetLeft - (box.clientWidth - el.offsetWidth) / 2 })
  }, [value])
  return (
    <div ref={ref} role="tablist" aria-label={label} className="hide-scroll relative -mx-5 flex gap-1 overflow-x-auto border-b border-line px-5">
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
  const press = (k: string) => {
    if (k === 'back') return onChange(value.slice(0, -1))
    if (k === '.' && value.includes('.')) return
    if (value.replace('.', '').length >= max) return
    onChange(value === '0' && k !== '.' ? k : value + k)
  }
  const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', 'back']
  return (
    <div className="grid grid-cols-3 gap-2" role="group" aria-label="Number pad">
      {keys.map((k) => (
        <button key={k} type="button" onClick={() => press(k)} aria-label={k === 'back' ? 'Delete' : k === '.' ? 'Decimal point' : k} className="press flex min-h-16 items-center justify-center rounded-card border border-line bg-card font-serif text-xl font-medium text-ink">
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
export function Rating({ value, onChange, label, lowLabel, highLabel }: { value: number; onChange: (n: number) => void; label: string; lowLabel: string; highLabel: string }) {
  return (
    <div className="flex flex-col gap-2" role="radiogroup" aria-label={label}>
      <p className="text-body font-bold">{label}</p>
      <div className="flex gap-2">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" role="radio" aria-checked={value === n} aria-label={`${label} ${n} of 5`} onClick={() => onChange(n)} className={cn('press flex min-h-14 flex-1 items-center justify-center rounded-card border-[1.5px] font-serif text-h2 font-medium', value === n ? 'border-brand bg-brand text-on-brand' : 'border-line bg-card text-ink')}>
            {n}
          </button>
        ))}
      </div>
      <div className="flex justify-between text-sub text-ink3">
        <span>{lowLabel}</span>
        <span>{highLabel}</span>
      </div>
    </div>
  )
}
