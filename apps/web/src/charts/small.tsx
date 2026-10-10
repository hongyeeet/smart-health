import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'
import type { DoseStatus, FoodResponse, GlucoseLevel, GridCell, WeekGrid } from '@/data/types'
import { signed } from '@/lib/format'
import { cn } from '@/lib/cn'
import { duration, ease } from '@/motion/tokens'
import { Check, Question, X } from '@/ui/icons'
import { linear, useMeasure } from './useMeasure'

const levelVar: Record<GlucoseLevel, string> = {
  very_low: 'var(--c-g-very-low)',
  low: 'var(--c-g-low)',
  in_range: 'var(--c-g-in)',
  high: 'var(--c-g-high)',
  very_high: 'var(--c-g-very-high)',
}

/* ---------------------------- time in range bar ---------------------------- */
/** Patterns keep it readable in grayscale: dots for low, lines for high, cross-hatch for very high. */
export function TirBar({ segments }: { segments: { level: GlucoseLevel; pct: number }[] }) {
  const { t } = useTranslation()
  const levelLabel: Record<GlucoseLevel, string> = {
    very_low: t('charts.level.veryLow', 'Very low'),
    low: t('charts.level.low', 'Low'),
    in_range: t('charts.level.inRange', 'In range'),
    high: t('charts.level.high', 'High'),
    very_high: t('charts.level.veryHigh', 'Very high'),
  }
  const uid = useId().replace(/:/g, '')
  const [ref, width] = useMeasure<HTMLDivElement>()
  let x = 0
  const total = segments.reduce((a, s) => a + s.pct, 0) || 100
  return (
    <div ref={ref} className="w-full">
      <svg
        width={width}
        height={30}
        role="img"
        aria-label={segments.map((s) => t('charts.tirItem', '{{label}} {{pct}}%', { label: levelLabel[s.level], pct: s.pct })).join(', ')}
        className="overflow-visible"
      >
        <defs>
          <pattern id={`dots-${uid}`} width="6" height="6" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r="1.3" fill="#fff" fillOpacity=".75" /></pattern>
          <pattern id={`lines-${uid}`} width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" stroke="#fff" strokeOpacity=".7" strokeWidth="2" /></pattern>
          <pattern id={`cross-${uid}`} width="7" height="7" patternUnits="userSpaceOnUse"><path d="M0 0L7 7M7 0L0 7" stroke="#fff" strokeOpacity=".7" strokeWidth="1.4" /></pattern>
          <clipPath id={`clip-${uid}`}><rect x="0" y="0" width={width} height="30" rx="10" /></clipPath>
        </defs>
        <g clipPath={`url(#clip-${uid})`}>
          {segments.map((s, i) => {
            const w = (s.pct / total) * width
            const rect = (
              <g key={i}>
                <motion.rect x={x} y={0} height={30} width={w} fill={levelVar[s.level]} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4, delay: i * 0.05 }} />
                {s.level === 'low' && <rect x={x} y={0} height={30} width={w} fill={`url(#dots-${uid})`} />}
                {s.level === 'high' && <rect x={x} y={0} height={30} width={w} fill={`url(#lines-${uid})`} />}
                {s.level === 'very_high' && <rect x={x} y={0} height={30} width={w} fill={`url(#cross-${uid})`} />}
                {i > 0 && <line x1={x} x2={x} y1={0} y2={30} stroke="var(--c-card)" strokeWidth="2" />}
              </g>
            )
            x += w
            return rect
          })}
        </g>
      </svg>
      <ul className="mt-3 flex flex-col gap-1.5">
        {segments.map((s) => (
          <li key={s.level} className="flex items-center gap-2.5 text-sub">
            <span className="h-3.5 w-3.5 flex-none rounded-[4px]" style={{ background: levelVar[s.level] }} aria-hidden />
            <span className="flex-1 text-ink">{levelLabel[s.level]}</span>
            <span className="num text-body">{s.pct}%</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/* ----------------------------------- ring ----------------------------------- */
export function Ring({ value, goal, size = 112, label, unit, caption }: { value: number; goal: number; size?: number; label: string; unit: string; caption: string }) {
  const { t } = useTranslation()
  const r = (size - 14) / 2
  const c = 2 * Math.PI * r
  const pct = Math.min(value / goal, 1)
  return (
    <div className="flex flex-col items-center gap-2 text-center">
      <div className="relative" style={{ width: size, height: size }} role="img" aria-label={t('charts.ringAria', '{{label}}: {{value}} of {{goal}} {{unit}}', { label, value, goal, unit })}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--c-well)" strokeWidth={10} />
          <motion.circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--c-brand)" strokeWidth={10} strokeLinecap="round" strokeDasharray={c} initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - pct) }} transition={{ duration: duration.chart, ease: ease.out }} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="num text-xl leading-none">{value}</span>
          <span className="text-micro text-ink3">{t('charts.ofGoal', 'of {{n}}', { n: goal })}</span>
        </div>
      </div>
      <p className="text-sub font-bold">{caption}</p>
    </div>
  )
}

/* ------------------------------ stacked weekly bars ------------------------------ */
export function IntensityBars({ weeks }: { weeks: { label: string; light: number; moderate: number; vigorous: number }[] }) {
  const { t } = useTranslation()
  const [ref, width] = useMeasure<HTMLDivElement>()
  const h = 170
  const max = Math.max(...weeks.map((w) => w.light + w.moderate + w.vigorous)) * 1.12
  const sy = linear(0, max, h - 28, 22)
  const bw = Math.min(40, (width / weeks.length) * 0.58)
  const uid = useId().replace(/:/g, '')
  return (
    <div ref={ref} className="w-full">
      <svg
        width={width}
        height={h}
        role="img"
        aria-label={t('charts.intensityAria', 'Minutes by intensity: {{list}}', {
          list: weeks.map((w) => t('charts.intensityItem', '{{label}} {{n}} moderate or vigorous', { label: w.label, n: w.moderate + w.vigorous })).join(', '),
        })}
        className="overflow-visible"
      >
        <defs>
          <pattern id={`l-${uid}`} width="6" height="6" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r="1.2" fill="var(--c-brand)" fillOpacity=".7" /></pattern>
          <pattern id={`v-${uid}`} width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="#fff" strokeWidth="2" strokeOpacity=".7" /></pattern>
        </defs>
        {weeks.map((w, i) => {
          const cx = ((i + 0.5) / weeks.length) * width
          const x = cx - bw / 2
          const tot = w.light + w.moderate + w.vigorous
          const yLight = sy(w.light)
          const yMod = sy(w.light + w.moderate)
          const yVig = sy(tot)
          const cur = i === weeks.length - 1
          return (
            <g key={w.label} opacity={cur ? 1 : 0.95}>
              <rect x={x} y={yLight} width={bw} height={h - 28 - yLight + 0.1 || 0} rx={4} fill="var(--c-brand-soft)" stroke="var(--c-brand)" strokeOpacity={0.5} />
              <rect x={x} y={yLight} width={bw} height={h - 28 - yLight} fill={`url(#l-${uid})`} />
              <rect x={x} y={yMod} width={bw} height={yLight - yMod} fill="var(--c-brand)" />
              {w.vigorous > 0 && (
                <>
                  <rect x={x} y={yVig} width={bw} height={yMod - yVig} fill="var(--c-brass)" />
                  <rect x={x} y={yVig} width={bw} height={yMod - yVig} fill={`url(#v-${uid})`} />
                </>
              )}
              <text x={cx} y={yVig - 6} textAnchor="middle" fill="var(--c-ink)" className="num" style={{ fontSize: 'calc(15px * var(--ts))', fontWeight: 600 }}>
                {w.moderate + w.vigorous}
              </text>
              <text x={cx} y={h - 6} textAnchor="middle" fill="var(--c-ink3)" style={{ fontSize: 'calc(12px * var(--ts))' }}>
                {w.label}
              </text>
            </g>
          )
        })}
      </svg>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sub text-ink2">
        <Legend swatch="bg-brand-soft border border-brand/50" label={t('charts.light', 'Light')} />
        <Legend swatch="bg-brand" label={t('charts.moderate', 'Moderate')} />
        <Legend swatch="bg-brass" label={t('charts.vigorous', 'Vigorous')} />
      </ul>
      <p className="mt-1 text-micro text-ink3">
        {t('charts.intensityNote', 'The number above a bar is moderate plus vigorous minutes, which is what counts towards the weekly goal.')}
      </p>
    </div>
  )
}
function Legend({ swatch, label }: { swatch: string; label: string }) {
  return (
    <li className="flex items-center gap-1.5">
      <span className={cn('h-3.5 w-3.5 rounded-[4px]', swatch)} aria-hidden />
      {label}
    </li>
  )
}

/* ------------------------------- meal response bars ------------------------------- */
export function FoodBars({ foods, onPick }: { foods: FoodResponse[]; onPick?: (f: FoodResponse) => void }) {
  const { t } = useTranslation()
  const max = 5
  return (
    <ul className="flex flex-col gap-3">
      {foods.map((f, i) => (
        <li key={f.id}>
          <button type="button" onClick={() => onPick?.(f)} disabled={!onPick} className={cn('flex w-full flex-col gap-1.5 text-left', onPick && 'press')}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-body font-bold leading-snug">{f.name}</span>
              <span className={cn('num text-h2', f.learning && 'text-ink3')}>{f.learning ? t('charts.learning', 'Learning') : signed(f.rise)}</span>
            </div>
            <div className="relative h-3 w-full overflow-hidden rounded-full bg-well" aria-hidden>
              <motion.div className={cn('h-full rounded-full', f.learning ? 'bg-ink3/40' : f.rise >= 3 ? 'bg-warn' : 'bg-brand')} initial={{ width: 0 }} animate={{ width: `${(f.rise / max) * 100}%` }} transition={{ duration: 0.5, ease: ease.out, delay: i * 0.04 }} />
            </div>
            <p className="text-sub text-ink2">
              {f.learning
                ? t('charts.foodLearning', 'Seen {{n}} time. Still learning, we need at least 2.', { n: f.n })
                : t('charts.foodSeen', 'Seen {{n}} times, rise {{min}} to {{max}} mmol/L', { n: f.n, min: f.min.toFixed(1), max: f.max.toFixed(1) })}
            </p>
          </button>
        </li>
      ))}
    </ul>
  )
}

/* ----------------------------------- week grid ----------------------------------- */
const cellClass: Record<GridCell['level'], string> = {
  good: 'bg-ok-soft text-ok',
  mid: 'bg-warn-soft text-warn [background-image:radial-gradient(var(--c-warn)_0.9px,transparent_1px)] [background-size:7px_7px]',
  low: 'bg-danger-soft text-danger [background-image:repeating-linear-gradient(45deg,transparent,transparent_4px,var(--c-danger)_4px,var(--c-danger)_5px)]',
  none: 'bg-well text-ink3',
}
export function WeekGridView({ grid, onDay }: { grid: WeekGrid; onDay: (date: string) => void }) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-7 gap-1.5" role="row">
        {grid.days.map((d) => (
          <button key={d.date} type="button" onClick={() => onDay(d.date)} className="press flex flex-col items-center rounded-field py-1 text-sub font-bold text-ink2" aria-label={t('charts.openDay', 'Open {{day}}', { day: d.short })}>
            {d.short.split(' ')[0]}
            <span className="num text-body font-normal text-ink">{d.short.split(' ')[1]}</span>
          </button>
        ))}
      </div>
      {grid.rows.map((row) => (
        <div key={row.key} className="flex flex-col gap-1">
          <p className="text-sub font-bold text-ink">{row.label}</p>
          <div className="grid grid-cols-7 gap-1.5">
            {row.cells.map((c, i) => (
              <button
                key={i}
                type="button"
                onClick={() => onDay(grid.days[i]!.date)}
                aria-label={t('charts.cellAria', '{{row}} {{day}}: {{text}}', { row: row.label, day: grid.days[i]!.short, text: c.text })}
                className={cn('press flex min-h-12 items-center justify-center rounded-field px-0.5 text-sub font-bold', cellClass[c.level])}
              >
                <span className="rounded bg-card/70 px-1">{c.text}</span>
              </button>
            ))}
          </div>
        </div>
      ))}
      <p className="text-sub text-ink3">{t('charts.gridKey', 'Dots mean a little off your usual. Lines mean further off. Grey means no activity logged.')}</p>
    </div>
  )
}

/* -------------------------------- prescription timeline -------------------------------- */
const doseStyle: Record<string, { cls: string; icon: React.ReactNode }> = {
  taken: { cls: 'bg-ok-soft text-ok border-ok/40', icon: <Check size={16} weight="bold" aria-hidden /> },
  taken_late_logged: { cls: 'bg-card text-ok border-ok', icon: <Check size={16} weight="bold" aria-hidden /> },
  unconfirmed: { cls: 'text-ink2 border-ink3/60 [background:repeating-linear-gradient(45deg,var(--c-well),var(--c-well)_4px,var(--c-line)_4px,var(--c-line)_6px)]', icon: <Question size={16} weight="bold" aria-hidden /> },
  missed: { cls: 'bg-danger-soft text-danger border-danger/40', icon: <X size={16} weight="bold" aria-hidden /> },
  due: { cls: 'bg-card text-brand border-brand border-dashed', icon: <span className="h-2 w-2 rounded-full bg-brand" aria-hidden /> },
  scheduled: { cls: 'bg-transparent text-ink3 border-line', icon: <span className="h-1.5 w-1.5 rounded-full bg-ink3/50" aria-hidden /> },
  skipped_by_plan: { cls: 'text-ink3 border-line', icon: <span aria-hidden>{'–'}</span> },
}
export function AdherenceTimeline({ days, rows, fasting }: { days: string[]; rows: { med: string; cells: DoseStatus[] }[]; fasting: number[] }) {
  const { t } = useTranslation()
  const doseLabel: Record<string, string> = {
    taken: t('charts.dose.taken', 'Taken'),
    taken_late_logged: t('charts.dose.takenLate', 'Taken, logged late'),
    unconfirmed: t('charts.dose.unconfirmed', 'Not confirmed'),
    missed: t('charts.dose.missed', 'Missed'),
    due: t('charts.dose.due', 'Due'),
    scheduled: t('charts.dose.later', 'Later'),
    skipped_by_plan: t('charts.dose.skipped', 'Skipped by plan'),
  }
  const [ref, width] = useMeasure<HTMLDivElement>()
  const labelW = 0
  const colW = (width - labelW) / days.length
  const sy = linear(6.4, 8.2, 58, 6)
  const path = fasting.map((v, i) => `${i ? 'L' : 'M'}${(colW * (i + 0.5)).toFixed(1)} ${sy(v).toFixed(1)}`).join(' ')
  return (
    <div ref={ref} className="flex w-full flex-col gap-3">
      <div className="grid grid-cols-7 gap-1.5 text-center text-sub font-bold text-ink2">
        {days.map((d) => (
          <span key={d}>{d.split(' ')[0]}</span>
        ))}
      </div>
      {rows.map((r) => (
        <div key={r.med} className="flex flex-col gap-1">
          <p className="text-sub font-bold text-ink">{r.med}</p>
          <div className="grid grid-cols-7 gap-1.5">
            {r.cells.map((c, i) => {
              const s = doseStyle[c]!
              return (
                <span key={i} role="img" aria-label={t('charts.doseAria', '{{med}}, {{day}}: {{label}}', { med: r.med, day: days[i], label: doseLabel[c] })} className={cn('flex h-11 items-center justify-center rounded-field border', s.cls)}>
                  {s.icon}
                </span>
              )
            })}
          </div>
        </div>
      ))}
      <div>
        <p className="mb-1 text-sub font-bold text-ink">{t('charts.fastingTitle', 'Fasting glucose (mmol/L)')}</p>
        <svg width={width} height={64} role="img" aria-label={t('charts.fastingAria', 'Fasting glucose across the week: {{list}}', { list: fasting.join(', ') })} className="overflow-visible">
          <path d={path} fill="none" stroke="var(--c-s1)" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
          {fasting.map((v, i) => (
            <g key={i}>
              <circle cx={colW * (i + 0.5)} cy={sy(v)} r={4} fill="var(--c-card)" stroke="var(--c-s1)" strokeWidth={2} />
              <text x={colW * (i + 0.5)} y={sy(v) - 9} textAnchor="middle" fill="var(--c-ink2)" className="num" style={{ fontSize: 'calc(12px * var(--ts))' }}>
                {v.toFixed(1)}
              </text>
            </g>
          ))}
        </svg>
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-sub text-ink2">
        {['taken', 'unconfirmed', 'missed'].map((k) => (
          <li key={k} className="flex items-center gap-1.5">
            <span className={cn('flex h-6 w-6 items-center justify-center rounded-[6px] border', doseStyle[k]!.cls)}>{doseStyle[k]!.icon}</span>
            {doseLabel[k]}
          </li>
        ))}
      </ul>
    </div>
  )
}

/* ------------------------------ mood and stress pairs ------------------------------ */
export function MoodStress({ data, label }: { data: { date: string; mood: number; stress: number }[]; label?: string }) {
  const { t } = useTranslation()
  const [ref, width] = useMeasure<HTMLDivElement>()
  const h = 132
  const sy = linear(1, 5, h - 18, 10)
  const colW = width / data.length
  return (
    <div ref={ref} className="w-full">
      <svg width={width} height={h} role="img" aria-label={label ?? t('charts.moodDefault', 'Mood and stress check-ins, 1 to 5, last 14 days')} className="overflow-visible">
        {[1, 3, 5].map((v) => (
          <line key={v} x1={0} x2={width} y1={sy(v)} y2={sy(v)} stroke="var(--c-line)" strokeDasharray="3 5" />
        ))}
        {data.map((d, i) => (
          <g key={d.date}>
            <circle cx={colW * (i + 0.5)} cy={sy(d.mood)} r={5.5} fill="var(--c-s1)" />
            <circle cx={colW * (i + 0.5)} cy={sy(d.stress)} r={5} fill="var(--c-card)" stroke="var(--c-s2)" strokeWidth={2.5} />
          </g>
        ))}
      </svg>
      <ul className="mt-2 flex gap-5 text-sub text-ink2">
        <li className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full bg-[var(--c-s1)]" aria-hidden />{t('charts.mood', 'Mood')}</li>
        <li className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full border-2 border-[var(--c-s2)] bg-card" aria-hidden />{t('charts.stress', 'Stress')}</li>
      </ul>
    </div>
  )
}
