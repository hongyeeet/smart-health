/**
 * Pieces of the Log a symptom page (E4): the choice pills, the strength tiles, the red-flag card, the sensor card with its
 * two-hour sparkline, and the recent symptoms list. Each one takes plain props; the page does the state and saving.
 */
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/cn'
import type { GlucosePoint, RecentEntry } from '@/data/types'
import { STRENGTH } from './data'

/** A plain panel: the border and white card of the mock, with 16 px padding on a phone and 20 px on a laptop. */
export function Panel({ className, tone = 'card', children }: { className?: string; tone?: 'card' | 'danger'; children: ReactNode }) {
  return (
    <div className={cn('min-w-0 rounded-card border p-4 lg:p-5', tone === 'card' ? 'border-line bg-card' : 'border-danger/30 bg-danger-soft', className)}>
      {children}
    </div>
  )
}

/** A soft grey block with a small uppercase title, one per symptom group. */
export function GroupBlock({ name, children }: { name: string; children: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col gap-2 rounded-[16px] bg-well p-3">
      <p className="text-micro font-bold uppercase tracking-[0.04em] text-ink2">{name}</p>
      <div className="flex flex-wrap gap-1.5">{children}</div>
    </div>
  )
}

/** A choice pill: 48 px tall on a phone for touch, 36 px on a laptop as in the mock. Picked = solid brand (or solid red for a red flag). */
export function Pill({ text, on, onClick, red = false }: { text: string; on: boolean; onClick: () => void; red?: boolean }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={cn(
        'press inline-flex min-h-12 max-w-full items-center rounded-chip border-[1.5px] px-3.5 text-left text-sub lg:min-h-9 lg:py-1',
        on
          ? red
            ? 'border-danger bg-danger font-bold text-card'
            : 'border-brand bg-brand font-bold text-on-brand'
          : red
            ? 'border-danger/40 bg-card font-bold text-danger'
            : 'border-line bg-card text-ink',
      )}
    >
      <span className="min-w-0 break-words">{text}</span>
    </button>
  )
}

/** The five strength tiles: a number and its word, colour-coded. Three across on a phone, five across from a tablet up. */
export function StrengthTiles({ value, onChange, label }: { value: number; onChange: (n: number) => void; label: string }) {
  const { t } = useTranslation()
  return (
    <div role="radiogroup" aria-label={label} className="grid grid-cols-3 gap-1.5 sm:grid-cols-5">
      {STRENGTH.map((s) => {
        const on = value === s.n
        return (
          <button
            key={s.n}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => onChange(s.n)}
            className={cn(
              'press flex min-h-14 min-w-0 flex-col items-center justify-center rounded-[12px] border-[1.5px] px-1 py-1.5 leading-tight',
              on ? cn('border-transparent', s.solid) : cn('border-transparent', s.soft),
            )}
          >
            <span className="text-h2 font-bold">{s.n}</span>
            <span className="max-w-full break-words text-center text-micro">{t(s.key, s.word)}</span>
          </button>
        )
      })}
    </div>
  )
}

/** The red-flag card: a soft red panel with the emergency symptoms, always on screen. */
export function RedFlagCard({ title, sub, children }: { title: string; sub: string; children: ReactNode }) {
  return (
    <Panel tone="danger">
      <h2 className="text-body font-bold text-danger">{title}</h2>
      <p className="mb-2.5 mt-0.5 text-micro text-ink">{sub}</p>
      <div className="flex flex-wrap gap-1.5">{children}</div>
    </Panel>
  )
}

/** A small line chart of the last two hours of glucose. Points are minutes since midnight; `now` is the current minute. */
export function Sparkline({ points, now }: { points: GlucosePoint[]; now: number }) {
  const recent = points.filter((p) => p.t >= now - 120 && p.t <= now)
  if (recent.length < 2) return null
  const vs = recent.map((p) => p.v)
  const lo = Math.min(...vs)
  const hi = Math.max(...vs)
  const span = hi - lo || 1
  const xy = recent.map((p) => {
    const x = 4 + ((p.t - (now - 120)) / 120) * 192
    const y = 44 - ((p.v - lo) / span) * 36
    return [x, y] as const
  })
  const d = xy.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ')
  const last = xy[xy.length - 1]!
  return (
    <svg viewBox="0 0 200 52" width="100%" height="52" className="block text-info" role="img" aria-hidden>
      <path d={d} fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinejoin="round" />
      <circle cx={last[0]} cy={last[1]} r={4} fill="var(--c-card)" stroke="currentColor" strokeWidth={2.2} />
    </svg>
  )
}

/** The sensor card: the latest glucose reading, its sparkline and the sensor sentence. Shown only when the sensor has a reading. */
export function SensorCard({
  value,
  footer,
  points,
  now,
  title,
  from,
}: {
  value: number
  footer: ReactNode
  points: GlucosePoint[] | undefined
  now: number
  title: string
  from: string
}) {
  return (
    <Panel>
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="min-w-0 text-body font-bold">{title}</h2>
        <span className="flex-none text-micro text-ink2">{from}</span>
      </div>
      <div className="mt-1.5 flex items-baseline gap-2">
        <span className="num text-xl font-bold">{value.toFixed(1)}</span>
        <span className="text-micro text-ink2">mmol/L</span>
      </div>
      {points && (
        <div className="my-1.5">
          <Sparkline points={points} now={now} />
        </div>
      )}
      <p className="text-micro text-ink2">{footer}</p>
    </Panel>
  )
}

/** The three most recent symptoms from the log, newest first. */
export function RecentCard({
  title,
  entries,
  empty,
  detailOf,
}: {
  title: string
  entries: RecentEntry[]
  empty: string
  detailOf: (e: RecentEntry) => string
}) {
  return (
    <Panel>
      <h2 className="text-body font-bold">{title}</h2>
      {entries.length === 0 ? (
        <p className="mt-2 text-sub text-ink2">{empty}</p>
      ) : (
        <ul className="mt-1 flex flex-col">
          {entries.map((e, i) => (
            <li key={e.id} className={cn('min-w-0 py-2.5', i > 0 && 'border-t border-line')}>
              <p className="break-words text-sub font-bold">{e.title}</p>
              <p className="break-words text-micro text-ink2">{detailOf(e)}</p>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}
