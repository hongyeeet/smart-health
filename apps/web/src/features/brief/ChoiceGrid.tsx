/**
 * A row of choices for the period (L1, L2) and the link length. Two columns on phones and at large text (so 7, 14, 30 and 90 days
 * never overflow or wrap into two lines), four columns from the small tablet width. Every choice is at least 48 px tall.
 */
import { cn } from '@/lib/cn'

export function ChoiceGrid<T extends string | number>({ options, value, onChange, label, showLabel }: { options: { value: T; label: string }[]; value: T; onChange: (v: T) => void; label: string; /** write the label above the choices as well as announcing it */ showLabel?: boolean }) {
  const grid = (
    <div
      role="radiogroup"
      aria-label={label}
      className={cn(
        'grid gap-2',
        // three choices sit in one row (no orphan on a second row); four make two rows of two on a phone and at large text, one row of four from a small tablet
        options.length === 3 ? "grid-cols-3 [[data-ts='2']_&]:grid-cols-1" : "grid-cols-2 sm:grid-cols-4 [[data-ts='2']_&]:sm:grid-cols-2",
      )}
    >
      {options.map((o) => {
        const on = o.value === value
        return (
          <button
            key={String(o.value)}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => onChange(o.value)}
            className={cn(
              'press flex min-h-12 items-center justify-center rounded-chip border px-3 py-2 text-center text-sub font-bold',
              on ? 'border-brand bg-card text-ink shadow-lift' : 'border-line bg-well text-ink2',
            )}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
  if (!showLabel) return grid
  return (
    <div className="flex flex-col gap-2">
      <p aria-hidden className="text-sub font-bold text-ink">
        {label}
      </p>
      {grid}
    </div>
  )
}
