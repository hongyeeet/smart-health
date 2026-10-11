import { useLayoutEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/cn'
import { useUi } from '@/state/store'
import { Check, Clock, ForkKnife, Heartbeat, PersonSimpleWalk, Question, Thermometer, X, type IconType } from '@/ui/icons'
import type { DayMarker, DayView, DoseState } from './api'
import { clockWords, doseWords, markerTone, timeInRange, type Tone } from './dayMath'

const PAD_R = 12
const DAY = 1440
const GLUCOSE_H = 196
const Y_MIN = 2
const Y_MAX = 16
const HR_MIN = 40
const HR_MAX = 140
const LANE_H = 48
/** A marker button is 48 px square, the touch size. */
const MARKER = 48

/** Measures the width this chart is given, so the SVG fills a phone, a tablet or a laptop column. */
function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(320)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    setWidth(Math.floor(el.getBoundingClientRect().width))
    const ro = new ResizeObserver(([entry]) => entry && setWidth(Math.floor(entry.contentRect.width)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, width] as const
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

/** Runs of slots with no glucose reading, as [startMinute, endMinute). Short runs (under 15 minutes) are normal sensor noise and are not drawn. */
function glucoseGaps(series: DayView['series']): [number, number][] {
  const gaps: [number, number][] = []
  let start: number | null = null
  for (const p of series) {
    if (p.glucoseMmol == null) {
      start ??= p.minute
    } else if (start != null) {
      if (p.minute - start >= 15) gaps.push([start, p.minute])
      start = null
    }
  }
  if (start != null) {
    const end = DAY
    if (end - start >= 15) gaps.push([start, end])
  }
  return gaps
}

/** A line path that lifts the pen wherever there is no value, so a gap is never joined across. */
function linePath(points: { x: number; y: number | null }[]): string {
  let d = ''
  let pen = false
  for (const p of points) {
    if (p.y == null) {
      pen = false
      continue
    }
    d += `${pen ? 'L' : 'M'}${p.x.toFixed(1)} ${p.y.toFixed(1)} `
    pen = true
  }
  return d
}

/**
 * One day on one clock: glucose with the person's range shaded, then lanes for meals, medicines, workouts and symptoms,
 * a blood pressure lane when there are readings that day, then heart rate, steps, sleep and mood. Missing data is a hatched gap,
 * never a joined line.
 */
export function DayTimeline({ day, onPick }: { day: DayView; onPick: (m: DayMarker) => void }) {
  const { t } = useTranslation()
  const ts = useUi((st) => st.textScale)
  // at 200% text the axis numbers are twice as wide: more room on the left, and only midnight, noon and midnight on the clock
  const padL = ts === 2 ? 68 : 40
  const clockHours = ts === 2 ? [0, 12, 24] : [0, 6, 12, 18, 24]
  const [ref, width] = useWidth<HTMLDivElement>()
  const innerW = Math.max(width - padL - PAD_R, 60)
  const sx = (minute: number) => padL + (clamp(minute, 0, DAY) / DAY) * innerW
  const sy = (v: number) => 8 + (1 - (clamp(v, Y_MIN, Y_MAX) - Y_MIN) / (Y_MAX - Y_MIN)) * (GLUCOSE_H - 30)
  const sh = (bpm: number) => 8 + (1 - (clamp(bpm, HR_MIN, HR_MAX) - HR_MIN) / (HR_MAX - HR_MIN)) * 52
  const hourLabel = (h: number) =>
    h % 24 === 0
      ? t('day.tl.midnight', '12 am')
      : h === 12
        ? t('day.tl.noon', '12 pm')
        : h < 12
          ? t('day.tl.am', '{{h}} am', { h })
          : t('day.tl.pm', '{{h}} pm', { h: h - 12 })

  const { series, markers, sleep, mood, targetLow, targetHigh } = day
  const glucosePoints = series.map((p) => ({ x: sx(p.minute), y: p.glucoseMmol == null ? null : sy(p.glucoseMmol) }))
  const hrPoints = series.map((p) => ({ x: sx(p.minute), y: p.heartRateBpm == null ? null : sh(p.heartRateBpm) }))
  const gaps = glucoseGaps(series)
  const hrGaps = glucoseGaps(series.map((p) => ({ ...p, glucoseMmol: p.heartRateBpm })))
  const inRange = timeInRange(series.map((p) => p.glucoseMmol), targetLow, targetHigh)

  // steps per hour, summed from the 5-minute slots; an hour with no step data stays empty rather than zero
  const stepsByHour = Array.from({ length: 24 }, (_, h) => {
    const slots = series.filter((p) => Math.floor(p.minute / 60) === h && p.steps != null)
    return slots.length ? slots.reduce((sum, p) => sum + (p.steps ?? 0), 0) : null
  })
  const maxSteps = Math.max(1, ...stepsByHour.map((v) => v ?? 0))
  const totalSteps = stepsByHour.reduce<number>((sum, v) => sum + (v ?? 0), 0)
  const hasSteps = stepsByHour.some((v) => v != null)
  const hasHr = series.some((p) => p.heartRateBpm != null)

  const lanes: { label: string; items: DayMarker[] }[] = [
    { label: t('day.tl.lanes.meals', 'Meals'), items: markers.filter((m) => m.kind === 'meal') },
    { label: t('day.tl.lanes.medicines', 'Medicines'), items: markers.filter((m) => m.kind === 'dose') },
    { label: t('day.tl.lanes.workouts', 'Workouts and symptoms'), items: markers.filter((m) => m.kind === 'workout' || m.kind === 'symptom') },
  ]
  // the blood pressure lane is only there on a day with readings, so a day without any shows no empty lane
  const pressure = markers.filter((m) => m.kind === 'pressure')
  if (pressure.length) lanes.push({ label: t('day.tl.lanes.pressure', 'Blood pressure'), items: pressure })

  return (
    <div ref={ref} className="w-full">
      <svg
        role="img"
        aria-label={t('day.tl.glucoseAria', 'Glucose on this day: {{summary}}', {
          summary:
            inRange == null
              ? t('day.tl.noReadings', 'no readings')
              : t('day.tl.rangeWords', '{{pct}}% of readings in your range, {{low}} to {{high}} mmol/L', { pct: inRange, low: targetLow, high: targetHigh }),
        })}
        width={width}
        height={GLUCOSE_H}
        className="block overflow-visible"
      >
        <defs>
          <pattern id="day-gap" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="8" stroke="var(--c-ink3)" strokeWidth="1.5" strokeOpacity="0.5" />
          </pattern>
        </defs>
        {/* range shading: a calm band for the person's range, tints for above and below */}
        <rect x={padL} y={sy(targetHigh)} width={innerW} height={sy(targetLow) - sy(targetHigh)} fill="var(--c-g-in)" fillOpacity={0.16} />
        <rect x={padL} y={sy(Y_MAX)} width={innerW} height={sy(targetHigh) - sy(Y_MAX)} fill="var(--c-g-high)" fillOpacity={0.1} />
        <rect x={padL} y={sy(targetLow)} width={innerW} height={sy(Y_MIN) - sy(targetLow)} fill="var(--c-g-low)" fillOpacity={0.12} />
        {[targetLow, targetHigh].map((v) => (
          <g key={v}>
            <line x1={padL} x2={width - PAD_R} y1={sy(v)} y2={sy(v)} stroke="var(--c-ink3)" strokeOpacity={0.5} strokeDasharray="4 5" />
            <text x={padL - 6} y={sy(v) + 4} textAnchor="end" fill="var(--c-ink2)" style={{ fontSize: 'calc(13px * var(--ts))' }}>
              {v.toFixed(1)}
            </text>
          </g>
        ))}
        {gaps.map(([a, b]) => (
          <g key={`${a}-${b}`}>
            <rect x={sx(a)} y={4} width={Math.max(sx(b) - sx(a), 1)} height={GLUCOSE_H - 26} fill="url(#day-gap)" rx={6} />
            <rect x={sx(a)} y={4} width={Math.max(sx(b) - sx(a), 1)} height={GLUCOSE_H - 26} fill="none" stroke="var(--c-ink3)" strokeOpacity={0.5} strokeDasharray="3 4" rx={6} />
            {sx(b) - sx(a) > 90 && (
              <text x={(sx(a) + sx(b)) / 2} y={(GLUCOSE_H - 26) / 2} textAnchor="middle" fill="var(--c-ink2)" style={{ fontSize: 'calc(13px * var(--ts))', fontWeight: 700 }}>
                {t('day.tl.noSensor', 'No sensor data')}
              </text>
            )}
          </g>
        ))}
        <path d={linePath(glucosePoints)} fill="none" stroke="var(--c-s1)" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
        {clockHours.map((h) => (
          <g key={h}>
            <line x1={sx(h * 60)} x2={sx(h * 60)} y1={GLUCOSE_H - 26} y2={GLUCOSE_H - 20} stroke="var(--c-ink3)" />
            <text x={sx(h * 60)} y={GLUCOSE_H - 4} textAnchor={h === 0 ? 'start' : h === 24 ? 'end' : 'middle'} fill="var(--c-ink2)" style={{ fontSize: 'calc(13px * var(--ts))' }}>
              {hourLabel(h)}
            </text>
          </g>
        ))}
      </svg>
      <p className="mt-1 text-sub text-ink3">{t('day.tl.gapNote', 'Hatched areas have no sensor reading. The line is broken there, never joined.')}</p>

      {lanes.map((lane) =>
        lane.items.length === 0 ? (
          // a lane with nothing in it is one quiet line, so a sparse day does not stack up empty 48 px rows
          <div key={lane.label} className="mt-2 flex items-baseline justify-between gap-3 border-b border-line/70 pb-1.5">
            <p className="text-sub font-bold text-ink2">{lane.label}</p>
            <span className="text-sub text-ink3">{t('day.tl.nothing', 'Nothing logged')}</span>
          </div>
        ) : (
          <Lane key={lane.label} label={lane.label} items={lane.items} sx={sx} width={width} onPick={onPick} />
        ),
      )}

      <p className="mt-4 text-sub font-bold text-ink2">{t('day.tl.hr', 'Heart rate, beats a minute')}</p>
      {hasHr ? (
        <svg width={width} height={64} role="img" aria-label={t('day.tl.hrAria', 'Heart rate across the day')} className="block overflow-visible">
          {hrGaps.map(([a, b]) => (
            <rect key={`${a}-${b}`} x={sx(a)} y={4} width={Math.max(sx(b) - sx(a), 1)} height={56} fill="url(#day-gap)" rx={4} />
          ))}
          <path d={linePath(hrPoints)} fill="none" stroke="var(--c-s3)" strokeWidth={2} strokeLinejoin="round" />
          <text x={padL - 6} y={sh(120) + 4} textAnchor="end" fill="var(--c-ink2)" style={{ fontSize: 'calc(13px * var(--ts))' }}>
            120
          </text>
          <text x={padL - 6} y={sh(60) + 4} textAnchor="end" fill="var(--c-ink2)" style={{ fontSize: 'calc(13px * var(--ts))' }}>
            60
          </text>
        </svg>
      ) : (
        <p className="text-sub text-ink3">{t('day.tl.noHr', 'No heart rate recorded for this day.')}</p>
      )}

      <p className="mt-3 text-sub font-bold text-ink2">
        {t('day.tl.steps', 'Steps each hour')}
        {hasSteps ? t('day.tl.stepsTotal', ', {{n}} in all', { n: totalSteps.toLocaleString('en-US') }) : ''}
      </p>
      {hasSteps ? (
        <svg
          width={width}
          height={56}
          role="img"
          aria-label={t('day.tl.stepsAria', 'Steps each hour, {{n}} in all', { n: totalSteps.toLocaleString('en-US') })}
          className="block overflow-visible"
        >
          {stepsByHour.map((s, h) => {
            const bw = Math.max(innerW / 24 - 3, 3)
            const bh = s == null ? 0 : (s / maxSteps) * 46
            return s == null ? (
              <line key={h} x1={sx(h * 60) + 1.5} x2={sx(h * 60) + 1.5 + bw} y1={50} y2={50} stroke="var(--c-ink3)" strokeWidth={2} strokeDasharray="2 3" />
            ) : (
              <rect key={h} x={sx(h * 60) + 1.5} y={50 - bh} width={bw} height={Math.max(bh, s ? 2 : 0)} rx={2} fill="var(--c-s2)" fillOpacity={0.85} />
            )
          })}
        </svg>
      ) : (
        <p className="text-sub text-ink3">{t('day.tl.noSteps', 'No steps recorded for this day.')}</p>
      )}

      <p className="mt-3 text-sub font-bold text-ink2">{t('day.tl.sleep', 'Sleep')}</p>
      <svg
        width={width}
        height={30}
        role="img"
        aria-label={
          sleep.length
            ? t('day.tl.asleep', 'Asleep {{times}}', {
                times: sleep.map((b) => t('day.tl.sleepRange', '{{from}} to {{to}}', { from: clockWords(b.startMinute), to: clockWords(b.endMinute) })).join(t('day.tl.thenJoin', ', then ')),
              })
            : t('day.tl.noSleepAria', 'No sleep recorded')
        }
        className="block overflow-visible"
      >
        <rect x={padL} y={4} width={innerW} height={22} rx={8} fill="var(--c-well)" />
        {sleep.map((b) => (
          <rect key={b.startMinute} x={sx(b.startMinute)} y={4} width={Math.max(sx(b.endMinute) - sx(b.startMinute), 2)} height={22} rx={8} fill="var(--c-s3)" fillOpacity={0.55} />
        ))}
      </svg>
      {!sleep.length && <p className="text-sub text-ink3">{t('day.tl.noSleep', 'No sleep recorded for this day.')}</p>}

      <p className="mt-3 text-sub font-bold text-ink2">{t('day.tl.mood', 'Mood and stress check-ins')}</p>
      <div className="relative h-11 border-b border-line/70">
        {[6, 12, 18].map((h) => (
          <span key={h} aria-hidden className="pointer-events-none absolute inset-y-0 w-px bg-line/70" style={{ left: sx(h * 60) }} />
        ))}
        {mood.length === 0 && <span className="absolute inset-y-0 left-0 flex items-center text-sub text-ink3">{t('day.tl.noCheckins', 'No check-ins')}</span>}
        {mood.map((d) => (
          <span
            key={d.id}
            role="img"
            aria-label={
              t('day.tl.checkinAt', 'Check-in at {{clock}}: {{mood}}', {
                clock: d.clock,
                mood: d.mood == null ? t('day.tl.moodNot', 'mood not recorded') : t('day.tl.moodOf', 'mood {{n}} of 5', { n: d.mood }),
              }) + (d.stressSelf == null ? '' : t('day.tl.stressOf', ', stress {{n}} of 5', { n: d.stressSelf }))
            }
            className="absolute top-1.5 flex h-8 w-8 -translate-x-1/2 items-center justify-center rounded-full border border-brand/50 bg-brand-soft text-sub font-bold text-brand"
            style={{ left: clamp(sx(d.minute), 16, Math.max(16, width - 16)) }}
          >
            {d.mood ?? '-'}
          </span>
        ))}
      </div>
    </div>
  )
}

/**
 * One lane of markers on the day's clock. Each marker sits at its own time. Markers that would overlap (three doses in two hours on a
 * phone) go on a second row, so none hides another and each stays a 48 px target.
 */
function Lane({ label, items, sx, width, onPick }: { label: string; items: DayMarker[]; sx: (minute: number) => number; width: number; onPick: (m: DayMarker) => void }) {
  const GAP = 4
  const ends: number[] = []
  const placed = [...items]
    .sort((a, b) => a.minute - b.minute)
    .map((m) => {
      const x = sx(m.minute)
      const span = m.endMinute != null ? sx(m.endMinute) - x : 0
      const wide = span > MARKER
      const w = wide ? span : MARKER
      const left = clamp(wide ? x : x - MARKER / 2, 0, Math.max(0, width - w))
      let row = ends.findIndex((end) => end + GAP <= left)
      if (row === -1) row = ends.length
      ends[row] = left + w
      return { m, left, w, row }
    })
  const rows = Math.max(1, ends.length)
  return (
    <div className="mt-3">
      <p className="text-sub font-bold text-ink2">{label}</p>
      <div className="relative border-b border-line/70" style={{ height: rows * LANE_H + (rows - 1) * GAP }}>
        {[6, 12, 18].map((h) => (
          <span key={h} aria-hidden className="pointer-events-none absolute inset-y-0 w-px bg-line/70" style={{ left: sx(h * 60) }} />
        ))}
        {placed.map(({ m, left, w, row }) => (
          <MarkerButton key={m.id} marker={m} left={left} width={w} top={row * (LANE_H + GAP)} onClick={() => onPick(m)} />
        ))}
      </div>
    </div>
  )
}

const TONE: Record<Tone, string> = {
  brass: 'bg-brass-soft text-brass border-brass/50',
  ok: 'bg-ok-soft text-ok border-ok/50',
  late: 'bg-card text-ok border-2 border-ok',
  unconfirmed: 'text-ink2 border-ink3/60 [background:repeating-linear-gradient(45deg,var(--c-well),var(--c-well)_4px,var(--c-line)_4px,var(--c-line)_6px)]',
  missed: 'bg-danger-soft text-danger border-danger/60 [background-image:repeating-linear-gradient(-45deg,transparent,transparent_3px,var(--c-danger)_3px,var(--c-danger)_4px)]',
  brand: 'bg-brand-soft text-brand border-brand/50',
  warn: 'bg-warn-soft text-warn border-warn/50',
  plain: 'bg-card text-ink border-ink3/60',
}

const STATE_ICON: Record<DoseState, IconType> = { taken: Check, late: Clock, not_confirmed: Question, missed: X }

/** `left`, `width` and `top` come from the lane, which keeps the button inside the lane and off its neighbours. */
function MarkerButton({ marker, left, width: w, top, onClick }: { marker: DayMarker; left: number; width: number; top: number; onClick: () => void }) {
  const { t } = useTranslation()
  const tone = markerTone(marker)
  const Icon: IconType =
    marker.kind === 'meal'
      ? ForkKnife
      : marker.kind === 'workout'
        ? PersonSimpleWalk
        : marker.kind === 'symptom'
          ? Thermometer
          : marker.kind === 'pressure'
            ? Heartbeat
            : STATE_ICON[marker.status ?? 'taken']
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={t('day.tl.markerAria', '{{title}} at {{clock}}{{state}}. Open details', {
        title: marker.title,
        clock: marker.clock,
        state:
          marker.kind === 'dose' && marker.status
            ? t('day.tl.statePart', ', {{words}}', { words: doseWords(marker.status) })
            : marker.kind === 'pressure' && marker.subtitle
              ? t('day.tl.readingPart', ', {{reading}}', { reading: marker.subtitle })
              : '',
      })}
      className={cn('press absolute top-0 flex h-12 min-w-12 items-center justify-center rounded-field border', TONE[tone])}
      style={{ left, top, width: w }}
    >
      <Icon size={18} weight="bold" aria-hidden />
    </button>
  )
}
