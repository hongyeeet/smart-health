import { useId } from 'react'
import { motion } from 'motion/react'
import type { DayDose, DayMeal, DaySymptom, DayTimeline, DayWorkout } from '@/data/types'
import { clock } from '@/lib/format'
import { duration, ease } from '@/motion/tokens'
import { cn } from '@/lib/cn'
import { Check, ForkKnife, PersonSimpleWalk, Pill, Question, Thermometer, X } from '@/ui/icons'
import { linear, useMeasure } from './useMeasure'

export type MarkerPick =
  | { type: 'meal'; items: DayMeal[] }
  | { type: 'dose'; items: DayDose[] }
  | { type: 'workout'; items: DayWorkout[] }
  | { type: 'symptom'; items: DaySymptom[] }

const PAD_L = 38
const PAD_R = 10
const DAY = 1440

/**
 * The multimodal day: glucose with range shading on one clock, then lanes for meals, doses, workouts and
 * symptoms, then heart rate, steps and sleep underneath. Missing data is a labelled gap, never a line.
 */
export function DayChart({ day, onPick, compact = false }: { day: DayTimeline; onPick?: (p: MarkerPick) => void; compact?: boolean }) {
  const [ref, width] = useMeasure<HTMLDivElement>()
  const uid = useId().replace(/:/g, '')
  const gh = compact ? 112 : 224
  const innerW = width - PAD_L - PAD_R
  const sx = linear(0, DAY, PAD_L, width - PAD_R)
  const yMin = 3
  const yMax = 14
  const sy = linear(yMin, yMax, gh - 24, 8)

  // split the glucose line wherever the sensor dropped out
  const segs: string[] = []
  let cur = ''
  let prevT = -999
  for (const p of day.glucose) {
    if (p.t - prevT > 20 && cur) {
      segs.push(cur)
      cur = ''
    }
    cur += `${cur ? 'L' : 'M'}${sx(p.t).toFixed(1)} ${sy(p.v).toFixed(1)} `
    prevT = p.t
  }
  if (cur) segs.push(cur)

  const group = <T extends { t: number }>(items: T[], tol = 25): T[][] => {
    const out: T[][] = []
    for (const it of [...items].sort((a, b) => a.t - b.t)) {
      const g = out[out.length - 1]
      if (g && it.t - g[0]!.t <= tol) g.push(it)
      else out.push([it])
    }
    return out
  }

  const hrMin = 50
  const hrMax = 120
  const sh = linear(hrMin, hrMax, 52, 4)
  const hrPath = day.hr.map((p, i) => `${i ? 'L' : 'M'}${sx(p.t).toFixed(1)} ${sh(p.v).toFixed(1)}`).join(' ')
  const maxSteps = Math.max(...day.stepsByHour, 1)

  const hours = [0, 6, 12, 18]
  const first = true

  return (
    <div ref={ref} className="w-full">
      <svg role="img" aria-label={`Glucose on ${day.weekday} ${day.label}, ${day.inRangePct}% in range`} width={width} height={gh} className="overflow-visible">
        <defs>
          <pattern id={`gap-${uid}`} width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="8" stroke="var(--c-ink3)" strokeWidth="1.5" strokeOpacity="0.45" />
          </pattern>
        </defs>
        {/* range shading: a calm band for the person's range, quiet tints either side */}
        <rect x={PAD_L} y={sy(10)} width={innerW} height={sy(3.9) - sy(10)} fill="var(--c-g-in)" fillOpacity={0.14} />
        <rect x={PAD_L} y={sy(yMax)} width={innerW} height={sy(10) - sy(yMax)} fill="var(--c-g-high)" fillOpacity={0.1} />
        <rect x={PAD_L} y={sy(3.9)} width={innerW} height={sy(yMin) - sy(3.9)} fill="var(--c-g-low)" fillOpacity={0.12} />
        {[3.9, 10].map((v) => (
          <g key={v}>
            <line x1={PAD_L} x2={width - PAD_R} y1={sy(v)} y2={sy(v)} stroke="var(--c-ink3)" strokeOpacity={0.5} strokeDasharray="4 5" />
            <text x={PAD_L - 6} y={sy(v) + 4} textAnchor="end" fill="var(--c-ink3)" style={{ fontSize: 'calc(13px * var(--ts))' }}>
              {v.toFixed(1)}
            </text>
          </g>
        ))}
        {day.endT < DAY - 30 && <rect x={sx(day.endT)} y={4} width={width - PAD_R - sx(day.endT)} height={gh - 28} fill="var(--c-well)" fillOpacity={0.7} rx={6} />}
        {day.glucoseGaps.map(([a, b], i) => (
          <g key={i}>
            <rect x={sx(a)} y={4} width={sx(b) - sx(a)} height={gh - 28} fill={`url(#gap-${uid})`} rx={6} />
            <rect x={sx(a)} y={4} width={sx(b) - sx(a)} height={gh - 28} fill="none" stroke="var(--c-ink3)" strokeOpacity={0.5} strokeDasharray="3 4" rx={6} />
            {!compact && (
              <text x={(sx(a) + sx(b)) / 2} y={gh / 2} textAnchor="middle" fill="var(--c-ink2)" style={{ fontSize: 'calc(13px * var(--ts))', fontWeight: 700 }}>
                No sensor data
              </text>
            )}
          </g>
        ))}
        {segs.map((d, i) => (
          <motion.path key={i} d={d} fill="none" stroke="var(--c-s1)" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" initial={first ? { opacity: 0 } : false} animate={{ opacity: 1 }} transition={{ duration: duration.chart, ease: ease.out }} />
        ))}
        {hours.map((h) => (
          <text key={h} x={sx(h * 60)} y={gh - 4} textAnchor={h === 0 ? 'start' : 'middle'} fill="var(--c-ink3)" style={{ fontSize: 'calc(13px * var(--ts))' }}>
            {clock(h * 60).replace(':00', '')}
          </text>
        ))}
      </svg>

      {!compact && (
        <>
          <Lane label="Meals">
            {group(day.meals).map((g, i) => (
              <Marker key={i} x={sx(g[0]!.t)} label={`Meal at ${clock(g[0]!.t)}: ${g.map((m) => m.name).join(', ')}`} onClick={() => onPick?.({ type: 'meal', items: g })} tone="brass">
                <ForkKnife size={18} aria-hidden />
              </Marker>
            ))}
          </Lane>
          <Lane label="Medicines">
            {group(day.doses, 5).map((g, i) => {
              const worst = g.find((d) => d.status === 'missed') ? 'missed' : g.find((d) => d.status === 'unconfirmed') ? 'unconfirmed' : g.find((d) => d.status === 'due') ? 'due' : 'taken'
              const tone = worst === 'missed' ? 'danger' : worst === 'unconfirmed' ? 'hatch' : worst === 'due' ? 'outline' : 'ok'
              const Icon = worst === 'missed' ? X : worst === 'unconfirmed' ? Question : worst === 'due' ? Pill : Check
              return (
                <Marker key={i} x={sx(g[0]!.t)} label={`${g.length} dose${g.length > 1 ? 's' : ''} at ${clock(g[0]!.t)}, ${worst}`} onClick={() => onPick?.({ type: 'dose', items: g })} tone={tone} badge={g.length > 1 ? g.length : undefined}>
                  <Icon size={18} weight="bold" aria-hidden />
                </Marker>
              )
            })}
          </Lane>
          <Lane label="Workouts and symptoms">
            {day.workouts.map((w) => (
              <Marker key={w.id} x={sx(w.t)} wide={Math.max((w.minutes / DAY) * innerW, 32)} label={`${w.label}, ${w.minutes} minutes at ${clock(w.t)}`} onClick={() => onPick?.({ type: 'workout', items: [w] })} tone="brand">
                <PersonSimpleWalk size={18} aria-hidden />
              </Marker>
            ))}
            {day.symptoms.map((s) => (
              <Marker key={s.id} x={sx(s.t)} label={`Symptom at ${clock(s.t)}: ${s.label}`} onClick={() => onPick?.({ type: 'symptom', items: [s] })} tone="warn">
                <Thermometer size={18} aria-hidden />
              </Marker>
            ))}
          </Lane>

          <p className="mt-3 text-sub font-bold text-ink2">Heart rate (beats a minute)</p>
          <svg width={width} height={60} role="img" aria-label="Heart rate across the day" className="overflow-visible">
            <line x1={PAD_L} x2={width - PAD_R} y1={sh(70)} y2={sh(70)} stroke="var(--c-line)" strokeDasharray="3 5" />
            <path d={hrPath} fill="none" stroke="var(--c-s3)" strokeWidth={2} strokeLinejoin="round" />
            <text x={PAD_L - 6} y={sh(120) + 10} textAnchor="end" fill="var(--c-ink3)" style={{ fontSize: 'calc(13px * var(--ts))' }}>
              120
            </text>
            <text x={PAD_L - 6} y={sh(50)} textAnchor="end" fill="var(--c-ink3)" style={{ fontSize: 'calc(13px * var(--ts))' }}>
              50
            </text>
          </svg>
          <p className="mt-2 text-sub font-bold text-ink2">Steps each hour</p>
          <svg width={width} height={56} role="img" aria-label="Steps each hour" className="overflow-visible">
            {day.stepsByHour.map((s, h) => {
              const bw = Math.max(innerW / 24 - 3, 3)
              const bh = (s / maxSteps) * 48
              return <rect key={h} x={sx(h * 60) + 1.5} y={52 - bh} width={bw} height={Math.max(bh, s ? 2 : 0)} rx={2} fill="var(--c-s2)" fillOpacity={0.85} />
            })}
          </svg>
          <p className="mt-2 text-sub font-bold text-ink2">Sleep</p>
          <svg width={width} height={30} role="img" aria-label={day.sleep ? `Slept ${day.sleep.label}` : 'No sleep data'} className="overflow-visible">
            <rect x={PAD_L} y={4} width={innerW} height={22} rx={8} fill="var(--c-well)" />
            {day.sleep && <rect x={sx(day.sleep.start)} y={4} width={sx(day.sleep.end) - sx(day.sleep.start)} height={22} rx={8} fill="var(--c-s3)" fillOpacity={0.55} />}
            {day.sleep && (
              <text x={sx(day.sleep.start) + 8} y={20} fill="var(--c-ink)" style={{ fontSize: 'calc(13px * var(--ts))', fontWeight: 700 }}>
                {day.sleep.label}
              </text>
            )}
          </svg>
        </>
      )}
    </div>
  )
}

function Lane({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mt-2">
      <p className="text-sub font-bold text-ink2">{label}</p>
      <div className="relative h-11 border-b border-line/70">{children}</div>
    </div>
  )
}

type MarkerTone = 'brass' | 'ok' | 'danger' | 'hatch' | 'outline' | 'brand' | 'warn'
const markerClass: Record<MarkerTone, string> = {
  brass: 'bg-brass-soft text-brass border-brass/40',
  ok: 'bg-ok-soft text-ok border-ok/40',
  danger: 'bg-danger-soft text-danger border-danger/40',
  hatch: 'text-ink2 border-ink3/60 [background:repeating-linear-gradient(45deg,var(--c-well),var(--c-well)_4px,var(--c-line)_4px,var(--c-line)_6px)]',
  outline: 'bg-card text-brand border-brand',
  brand: 'bg-brand-soft text-brand border-brand/40',
  warn: 'bg-warn-soft text-warn border-warn/40',
}

function Marker({ x, label, onClick, tone, children, badge, wide }: { x: number; label: string; onClick: () => void; tone: MarkerTone; children: React.ReactNode; badge?: number; wide?: number }) {
  return (
    <button type="button" aria-label={label} onClick={onClick} className="press absolute top-0 flex h-11 items-center justify-center" style={{ left: x - (wide ? 0 : 22), width: wide ? wide : 44 }}>
      <span className={cn('relative flex h-8 items-center justify-center rounded-full border', wide ? 'w-full rounded-chip' : 'w-8', markerClass[tone])}>
        {children}
        {badge && <span className="absolute -right-1.5 -top-1.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-ink px-1 text-micro font-bold text-canvas">{badge}</span>}
      </span>
    </button>
  )
}
