import { useId, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { motion } from 'motion/react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/cn'
import { Check, Info, Question, WarningCircle, Warning, CheckCircle, type IconType } from './icons'

/* ---------------------------------- Card ---------------------------------- */
export function Card({
  children,
  className,
  onClick,
  tone = 'plain',
  as = 'div',
}: {
  children: ReactNode
  className?: string
  onClick?: () => void
  tone?: 'plain' | 'soft' | 'hero'
  as?: 'div' | 'section'
}) {
  const base = cn(
    'block w-full rounded-card border text-left',
    tone === 'plain' && 'border-line bg-card',
    tone === 'soft' && 'border-transparent bg-well',
    tone === 'hero' && 'border-line bg-card shadow-lift',
    onClick && 'press',
    className,
  )
  if (onClick)
    return (
      <button type="button" onClick={onClick} className={cn(base, 'p-4')}>
        {children}
      </button>
    )
  const Tag = as
  return <Tag className={cn(base, 'p-4')}>{children}</Tag>
}

/* --------------------------------- Button --------------------------------- */
type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
export function Button({
  variant = 'primary',
  size = 'lg',
  icon: Icon,
  children,
  className,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: 'xl' | 'lg' | 'md'; icon?: IconType }) {
  return (
    <button
      type="button"
      {...rest}
      className={cn(
        'press flex w-full items-center justify-center gap-2 rounded-[14px] border-2 text-center font-bold',
        size === 'xl' ? 'min-h-16 px-4 py-3 text-btn' : size === 'lg' ? 'min-h-14 px-4 py-3 text-btn' : 'min-h-12 px-3.5 py-2 text-btn-sm',
        variant === 'primary' && 'border-transparent bg-brand text-on-brand hover:bg-brand-press',
        variant === 'secondary' && 'border-brand bg-card text-brand hover:bg-brand-soft',
        variant === 'ghost' && 'border-transparent text-brand hover:bg-brand-soft',
        variant === 'danger' && 'border-transparent bg-danger text-card',
        // a disabled button keeps a readable pair in both themes (ink2 on well is about 6.9:1 light, 8.2:1 dark); opacity would wash it out
        'disabled:pointer-events-none disabled:border-line disabled:bg-well disabled:text-ink2 disabled:hover:bg-well',
        className,
      )}
    >
      {Icon && <Icon size={22} weight="regular" aria-hidden />}
      <span>{children}</span>
    </button>
  )
}

export function TextLink({ children, onClick, icon: Icon, className }: { children: ReactNode; onClick?: () => void; icon?: IconType; className?: string }) {
  return (
    <button type="button" onClick={onClick} className={cn('press inline-flex min-h-12 items-center gap-1.5 text-sub font-bold text-brand underline decoration-1 underline-offset-4', className)}>
      {Icon && <Icon size={20} aria-hidden />}
      {children}
    </button>
  )
}

/* ---------------------------------- Chip ---------------------------------- */
export function Chip({ children, on, onClick, icon: Icon, className }: { children: ReactNode; on?: boolean; onClick?: () => void; icon?: IconType; className?: string }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={!!on}
      onClick={onClick}
      className={cn(
        'press inline-flex min-h-12 items-center gap-2 rounded-chip border-[1.5px] px-4 py-2 text-sub',
        on ? 'border-brand bg-brand-soft font-bold text-brand' : 'border-line bg-card text-ink',
        className,
      )}
    >
      {on ? <Check size={18} weight="bold" aria-hidden /> : Icon ? <Icon size={20} aria-hidden /> : null}
      {children}
    </button>
  )
}

/* ------------------------------- Status pill ------------------------------- */
export type Tone = 'ok' | 'warn' | 'danger' | 'info' | 'neutral' | 'brand' | 'brass'
const toneClass: Record<Tone, string> = {
  ok: 'bg-ok-soft text-ok',
  warn: 'bg-warn-soft text-warn',
  danger: 'bg-danger-soft text-danger',
  info: 'bg-info-soft text-info',
  neutral: 'bg-well text-ink2',
  brand: 'bg-brand-soft text-brand',
  brass: 'bg-brass-soft text-brass',
}
const toneIcon: Record<Tone, IconType> = { ok: CheckCircle, warn: Warning, danger: WarningCircle, info: Info, neutral: Info, brand: Info, brass: Info }

/** Never colour alone: every pill carries an icon and a word. */
export function StatusPill({ tone = 'neutral', children, icon, bare }: { tone?: Tone; children: ReactNode; icon?: IconType; bare?: boolean }) {
  const Icon = icon ?? toneIcon[tone]
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-chip px-2.5 py-1 text-sub font-bold leading-tight', toneClass[tone])}>
      {!bare && <Icon size={16} weight="bold" aria-hidden />}
      {children}
    </span>
  )
}

export function EstimateBadge() {
  const { t } = useTranslation()
  return (
    <span className="inline-flex items-center gap-1 rounded-chip border border-brass/40 bg-brass-soft px-2 py-0.5 text-micro font-bold text-brass">{t('common.estimated', 'Estimated')}</span>
  )
}

export function ConfidenceChip({ level }: { level: 'high' | 'check' | 'unreadable' }) {
  const map = {
    high: { tone: 'ok' as Tone, text: 'High confidence', icon: CheckCircle },
    check: { tone: 'warn' as Tone, text: 'Check this', icon: Warning },
    unreadable: { tone: 'danger' as Tone, text: "Can't read", icon: Question },
  }[level]
  return (
    <StatusPill tone={map.tone} icon={map.icon}>
      {map.text}
    </StatusPill>
  )
}

export function SourceTag({ children }: { children: ReactNode }) {
  return <span className="inline-flex items-center gap-1 text-micro text-ink3">Source: {children}</span>
}

export function UnverifiedTag() {
  return <StatusPill tone="brass" icon={Info}>Unverified. Associated with, not a cause.</StatusPill>
}

/* ------------------------------- Confidence dots ------------------------------- */
export function Dots({ n, of = 3, label }: { n: number; of?: number; label?: string }) {
  return (
    <span role="img" aria-label={label ?? `Confidence ${n} of ${of}`} className="inline-flex gap-1">
      {Array.from({ length: of }, (_, i) => (
        <span key={i} className={cn('h-2.5 w-2.5 rounded-full border border-brand', i < n ? 'bg-brand' : 'bg-transparent')} />
      ))}
    </span>
  )
}

/* ---------------------------------- Alert ---------------------------------- */
export function Alert({ tone = 'warn', icon, children, onClick, title }: { tone?: Exclude<Tone, 'neutral' | 'brand' | 'brass'>; icon?: IconType; children: ReactNode; onClick?: () => void; title?: string }) {
  const Icon = icon ?? toneIcon[tone]
  const color = { ok: 'border-ok/50 bg-ok-soft', warn: 'border-warn/50 bg-warn-soft', danger: 'border-danger/50 bg-danger-soft', info: 'border-info/40 bg-info-soft' }[tone]
  const iconColor = { ok: 'text-ok', warn: 'text-warn', danger: 'text-danger', info: 'text-info' }[tone]
  const body = (
    <>
      <Icon size={24} weight="regular" className={cn('mt-0.5 flex-none', iconColor)} aria-hidden />
      <div className="min-w-0 flex-1">
        {title && <p className="mb-0.5 text-body font-bold">{title}</p>}
        <div className="text-sub text-ink">{children}</div>
      </div>
    </>
  )
  const cls = cn('flex w-full items-start gap-3 rounded-card border-[1.5px] p-3.5 text-left', color, onClick && 'press')
  return onClick ? (
    <button type="button" onClick={onClick} className={cls}>
      {body}
    </button>
  ) : (
    <div className={cls}>{body}</div>
  )
}

/* ------------------------------- Section title ------------------------------- */
export function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-end justify-between gap-3 pt-2">
      <h2 className="font-serif text-h2 font-medium tracking-tight text-ink">{children}</h2>
      {action}
    </div>
  )
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="text-sub font-bold text-ink3">{children}</p>
}

/* ----------------------------------- Toggle ----------------------------------- */
export function Toggle({ on, onChange, label }: { on: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    // the button is the 64 x 48 target; the visible switch (56 x 32) sits inside it
    <button type="button" role="switch" aria-checked={on} aria-label={label} onClick={() => onChange(!on)} className="press flex h-12 w-16 flex-none items-center justify-end">
      <span className="relative block h-8 w-14 rounded-chip border border-line transition-colors" style={{ background: on ? 'var(--c-brand)' : 'var(--c-well)' }}>
        <motion.span className="absolute left-1 top-1 h-6 w-6 rounded-full bg-card shadow" animate={{ x: on ? 24 : 0 }} transition={{ duration: 0.18, ease: [0.23, 1, 0.32, 1] }} />
      </span>
    </button>
  )
}

/* ------------------------------------ Field ------------------------------------ */
export function Field({
  label,
  value,
  onChange,
  placeholder,
  hint,
  inputMode,
  multiline,
  type = 'text',
  suffix,
  error,
  large,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  hint?: string
  inputMode?: 'text' | 'numeric' | 'decimal' | 'tel'
  multiline?: boolean
  type?: 'text' | 'date' | 'time' | 'tel'
  /** unit shown inside the field, on the right (cm, kg, %) */
  suffix?: string
  /** shown instead of the hint, with the field outlined, when the value cannot be used */
  error?: string
  /** a big number-entry field (for example a blood pressure reading) */
  large?: boolean
}) {
  const id = useId()
  const cls = cn(
    'min-h-12 w-full rounded-field border-[1.5px] bg-card px-3.5 py-3 text-body text-ink placeholder:text-ink3 focus:border-brand focus:outline-none',
    large && 'min-h-16 text-xl font-bold tabular-nums',
    error ? 'border-danger' : 'border-line',
    suffix && 'pr-14',
  )
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <label htmlFor={id} className="text-sub font-bold text-ink">
        {label}
      </label>
      {multiline ? (
        <textarea id={id} rows={3} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className={cls} />
      ) : (
        <div className="relative">
          <input id={id} type={type} value={value} inputMode={inputMode} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} aria-invalid={!!error} aria-describedby={error || hint ? `${id}-note` : undefined} className={cls} />
          {suffix && <span className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-sub text-ink3">{suffix}</span>}
        </div>
      )}
      {error ? (
        <p id={`${id}-note`} className="flex items-start gap-1.5 text-sub text-danger">
          <WarningCircle size={18} className="mt-0.5 flex-none" aria-hidden />
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-note`} className="text-sub text-ink3">
          {hint}
        </p>
      ) : null}
    </div>
  )
}

/* ----------------------------------- Stepper ----------------------------------- */
export function Stepper({ value, onChange, min = 0, max = 999, step = 1, format, label }: { value: number; onChange: (v: number) => void; min?: number; max?: number; step?: number; format?: (v: number) => string; label: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-card border border-line bg-card p-2" role="group" aria-label={label}>
      <button type="button" aria-label={`Less ${label}`} onClick={() => onChange(Math.max(min, value - step))} className="press flex h-12 w-12 items-center justify-center rounded-full bg-well text-h2 font-bold text-ink">
        {'−'}
      </button>
      <span className="num text-xl">{format ? format(value) : value}</span>
      <button type="button" aria-label={`More ${label}`} onClick={() => onChange(Math.min(max, value + step))} className="press flex h-12 w-12 items-center justify-center rounded-full bg-well text-h2 font-bold text-ink">
        +
      </button>
    </div>
  )
}

/* ---------------------------------- Skeleton ---------------------------------- */
export function Skeleton({ className }: { className?: string }) {
  // a loading block is named for screen readers; sighted users see the pulse
  return <div className={cn('animate-pulse rounded-card bg-well', className)} role="status" aria-label="Loading" />
}

export function EmptyState({ icon: Icon, children, action }: { icon: IconType; children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-3 px-6 py-10 text-center">
      <Icon size={36} className="text-ink3" aria-hidden />
      <p className="text-body text-ink2">{children}</p>
      {action}
    </div>
  )
}

export function Divider() {
  return <div className="h-px w-full bg-line" role="separator" />
}

/* ---------------------------------- List row ---------------------------------- */
export function ListRow({ icon: Icon, title, sub, trailing, onClick, tone }: { icon?: IconType; title: ReactNode; sub?: ReactNode; trailing?: ReactNode; onClick?: () => void; tone?: 'danger' }) {
  const inner = (
    <>
      {Icon && (
        <span className={cn('flex h-11 w-11 flex-none items-center justify-center rounded-full bg-brand-soft text-brand', tone === 'danger' && 'bg-danger-soft text-danger')}>
          <Icon size={22} aria-hidden />
        </span>
      )}
      <span className="min-w-0 flex-1">
        <span className="block text-body font-bold leading-snug text-ink">{title}</span>
        {sub && <span className="mt-0.5 block text-sub text-ink2">{sub}</span>}
      </span>
      {trailing}
    </>
  )
  const cls = 'flex w-full items-center gap-3 py-3 text-left'
  return onClick ? (
    <button type="button" onClick={onClick} className={cn(cls, 'press')}>
      {inner}
    </button>
  ) : (
    <div className={cls}>{inner}</div>
  )
}

/** Green, underlined text that acts as a link or an offer inside a sentence or under a list. Not a button: no box, no fill. */
export function ProseLink({ onClick, disabled, children }: { onClick: () => void; disabled?: boolean; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="press inline cursor-pointer p-0 text-left font-semibold text-brand underline decoration-brand/60 underline-offset-[3px] hover:decoration-brand disabled:cursor-default disabled:no-underline disabled:opacity-60"
    >
      {children}
    </button>
  )
}
