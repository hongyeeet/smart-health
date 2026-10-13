/**
 * Insights → Overview charts: glucose, heart rate, SpO2, blood pressure, and steps with mood, on ONE shared time axis, with a marker the
 * person can drag (or move with the arrow keys) to read every chart at the same moment. Under the charts are the meals, workouts,
 * symptoms, missed doses and work hours from the person's own logs and set-up.
 *
 * Each chart has a gauge: the person's usual range for that hour (the middle half of their last 60 days), their BASELINE (the average
 * for that hour of the day over the same days; blood pressure is one fixed number), and the reading at the marker. The words say how far
 * the reading is from the baseline and whether it is inside the usual range. No reading is called good or bad.
 * All numbers come from GET /insights/timeline; this file only lays them out.
 */
import { useMemo, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import type { InsightsHourly, InsightsTimeline } from '@/data/types'
import { cn } from '@/lib/cn'
import { dateLocale } from '@/lib/locale'
import { CaretLeft, CaretRight } from '@/ui/icons'
import {
  DAY_MIN,
  atWork,
  baselinePath,
  bandPath,
  clockMin,
  domain,
  gapText,
  isoWeekday,
  linePath,
  niceTicks,
  nearestBp,
  outsidePath,
  readAt,
  type Compare,
  type Reading,
} from './timelineMath'

const W = 1000
const AXIS = 'w-14'
const AXIS_PAD = 'pl-14'
const STEP_MIN = 30

type Key = 'glucose' | 'heart' | 'spo2'
interface Chart {
  key: Key
  height: number
  color: string
  digits: number
  floor?: number
  ceil?: number
}
const CHARTS: Chart[] = [
  { key: 'glucose', height: 190, color: 'var(--c-info)', digits: 1, floor: 0 },
  { key: 'heart', height: 120, color: 'var(--c-danger)', digits: 0, floor: 0 },
  { key: 'spo2', height: 100, color: 'var(--c-brass)', digits: 1, ceil: 100 },
]
const BP_COLOR = 'var(--c-warn)'
const STEPS_COLOR = 'var(--c-brand)'

const chartName = (t: TFunction, k: Key | 'bp' | 'steps') =>
  ({
    glucose: t('insights.tl.glucose', 'Glucose'),
    heart: t('insights.tl.heart', 'Heart rate'),
    spo2: t('insights.tl.spo2', 'SpO2'),
    bp: t('insights.tl.bp', 'Blood pressure'),
    steps: t('insights.tl.steps', 'Steps and mood'),
  })[k]
const chartUnit = (k: Key) => (k === 'glucose' ? 'mmol/L' : k === 'heart' ? 'bpm' : '%')

const human = (s: string) => {
  const x = s.replace(/_/g, ' ').trim()
  return x.charAt(0).toUpperCase() + x.slice(1)
}

/** the local clock time and date at `m` minutes after midnight of the first day */
function at(startIso: string, m: number): Date {
  const d = new Date(`${startIso}T00:00:00`)
  d.setMinutes(d.getMinutes() + Math.round(m))
  return d
}
const dayShort = (d: Date) =>
  d.toLocaleDateString(dateLocale('en-GB'), {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
const timeShort = (d: Date) =>
  d.toLocaleTimeString(dateLocale('en-US'), {
    hour: 'numeric',
    minute: '2-digit',
  })

const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v))

function agoText(t: TFunction, gap: number): string {
  const { h, min } = gapText(gap)
  if (h && min) return t('insights.tl.hm', '{{h}} h {{m}} min', { h, m: min })
  if (h) return t('insights.tl.h', '{{h}} h', { h })
  return t('insights.tl.m', '{{m}} min', { m: min })
}

const TONE: Record<Compare, string> = {
  above: 'text-warn',
  below: 'text-info',
  within: 'text-ok',
  unknown: 'text-ink3',
}

/** "0.6 above baseline 10.5, within usual range" */
function statusText(t: TFunction, r: Reading, digits: number, hasBaseline: boolean): string {
  if (r.value == null) return t('insights.tl.noReading', 'No reading at this moment')
  if (!hasBaseline || r.baseline == null || r.diff == null) return t('insights.tl.noBaseline', 'No baseline yet')
  const ad = Math.abs(r.diff).toFixed(digits)
  const base = r.baseline.toFixed(digits)
  const rel =
    Number(ad) === 0
      ? t('insights.tl.atBase', 'At baseline {{b}}', { b: base })
      : r.diff > 0
        ? t('insights.tl.aboveBase', '{{d}} above baseline {{b}}', {
            d: ad,
            b: base,
          })
        : t('insights.tl.belowBase', '{{d}} below baseline {{b}}', {
            d: ad,
            b: base,
          })
  const range = {
    above: t('insights.tl.aboveUsual', 'above usual range'),
    below: t('insights.tl.belowUsual', 'below usual range'),
    within: t('insights.tl.withinUsual', 'within usual range'),
    unknown: '',
  }[r.compare]
  return range ? `${rel}, ${range}` : rel
}

/** The gauge at the top right of a chart: the usual range as a bar, the baseline as a thin line, the reading as a block. */
function Gauge({
  min,
  max,
  lo,
  hi,
  baseline,
  value,
  color,
  label,
}: {
  min: number
  max: number
  lo: number | null
  hi: number | null
  baseline: number | null
  value: number | null
  color: string
  label: string
}) {
  const p = (v: number) => `${clamp((v - min) / (max - min), 0, 1) * 100}%`
  return (
    <div className="relative h-[18px] w-32 flex-none sm:w-40" role="img" aria-label={label}>
      <div className="absolute inset-x-0 top-[6px] h-[6px] rounded-full bg-line" />
      {lo != null && hi != null && (
        <div
          className="absolute top-[4px] h-[10px] rounded-full opacity-40"
          style={{
            left: p(lo),
            width: `max(6px, calc(${p(hi)} - ${p(lo)}))`,
            background: color,
          }}
        />
      )}
      {baseline != null && <div className="absolute top-[2px] h-[14px] w-[2px] -translate-x-1/2 bg-ink opacity-70" style={{ left: p(baseline) }} />}
      {value != null && <div className="absolute top-0 h-[18px] w-[5px] -translate-x-1/2 rounded-sm bg-ink" style={{ left: p(value) }} />}
    </div>
  )
}

function ChartHead({
  color,
  name,
  unit,
  value,
  status,
  tone,
  gauge,
}: {
  color: string
  name: string
  unit: string
  value: string
  status: string
  tone: Compare | 'plain'
  gauge: ReactNode
}) {
  return (
    <div className="mb-1.5 mt-4 flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
      <p className="flex items-center gap-2 font-bold">
        <span className="h-3 w-3 rounded-full" style={{ background: color }} aria-hidden />
        {name}
        <span className="text-sub font-normal text-ink3">{unit}</span>
      </p>
      <div className="flex items-center gap-3">
        <div className="text-right">
          <p className="num text-body font-bold">{value}</p>
          <p className={cn('text-micro font-bold', tone === 'plain' ? 'text-ink2' : TONE[tone])}>{status}</p>
        </div>
        {gauge}
      </div>
    </div>
  )
}

export function OverviewTimeline({ data }: { data: InsightsTimeline }) {
  const { t } = useTranslation()
  const { period, series, baseline, events, work, bp } = data
  const days = period.days
  const step = period.bucketMinutes
  const total = days * DAY_MIN
  const daily = step >= DAY_MIN

  // the marker opens on the latest glucose reading: the end of the data, where the person is "now"
  const lastK = (() => {
    for (let k = series.glucose.length - 1; k >= 0; k--) if (series.glucose[k] != null) return k
    return series.glucose.length - 1
  })()
  const [m, setM] = useState(() => clamp(lastK * step + step / 2, 0, total - 1))
  const dragging = useRef(false)
  const setClamped = (v: number) => setM(clamp(v, 0, total - 1))

  const x = (min: number) => (min / total) * W
  const xb = (k: number) => x(k * step + step / 2)
  const pct = (min: number) => `${(min / total) * 100}%`

  // ── the three line charts, built once per answer
  const built = useMemo(
    () =>
      CHARTS.map((c) => {
        const vals = series[c.key]
        const h: InsightsHourly = baseline[c.key]
        const lows = c.key === 'glucose' ? series.glucoseMin : vals
        const highs = c.key === 'glucose' ? series.glucoseMax : vals
        const [lo, hi] = domain([...lows, ...highs, ...h.mean, ...h.lo, ...h.hi], 0.1, c.floor, c.ceil)
        const pad = 8
        const y = (v: number) => pad + (1 - (v - lo) / (hi - lo)) * (c.height - pad * 2)
        const range = c.key === 'glucose' && daily
        let area = ''
        if (range) {
          const up: string[] = []
          const down: string[] = []
          for (let k = 0; k < vals.length; k++) {
            const a = series.glucoseMax[k]
            const b = series.glucoseMin[k]
            if (a == null || b == null) continue
            up.push(`${xb(k).toFixed(1)} ${y(a).toFixed(1)}`)
            down.push(`${xb(k).toFixed(1)} ${y(b).toFixed(1)}`)
          }
          if (up.length) area = `M${up.join('L')}L${down.reverse().join('L')}Z`
        }
        return {
          c,
          lo,
          hi,
          y,
          ticks: niceTicks(lo, hi, c.height > 150 ? 4 : 3),
          line: linePath(vals, xb, y),
          out: baseline.available && !daily ? outsidePath(vals, h, step, xb, y) : '',
          base: baseline.available ? baselinePath(h, days, step, x, y) : '',
          band: baseline.available ? bandPath(h, days, step, x, y) : '',
          area,
        }
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [data],
  )

  // ── shaded backgrounds: night (12 to 6 am) and work hours, one rectangle per day
  const startIso = period.start
  const shades = useMemo(() => {
    const night: number[] = []
    const wk: [number, number][] = []
    const ws = clockMin(work.start)
    const we = clockMin(work.end)
    for (let d = 0; d < days; d++) {
      if (!daily && days <= 30) night.push(d * DAY_MIN)
      if (work.set && ws != null && we != null && work.days.includes(isoWeekday(startIso, d))) wk.push([d * DAY_MIN + ws, d * DAY_MIN + we])
    }
    return { night, wk }
  }, [days, daily, work, startIso])

  const backdrop = (h: number) => (
    <>
      {shades.night.map((s) => (
        <rect key={`n${s}`} x={x(s)} y={0} width={x(360)} height={h} fill="var(--c-well)" opacity="0.7" />
      ))}
      {shades.wk.map(([a, b]) => (
        <rect key={`w${a}`} x={x(a)} y={0} width={x(b) - x(a)} height={h} fill="var(--c-info)" opacity="0.1" />
      ))}
      {days <= 30 &&
        Array.from({ length: days - 1 }, (_, i) => (
          <line
            key={`d${i}`}
            x1={x((i + 1) * DAY_MIN)}
            x2={x((i + 1) * DAY_MIN)}
            y1={0}
            y2={h}
            stroke="var(--c-line)"
            strokeWidth="1"
            vectorEffect="non-scaling-stroke"
          />
        ))}
    </>
  )

  // ── what the marker reads
  const label = (() => {
    const d = at(startIso, m)
    return daily ? dayShort(d) : `${dayShort(d)}, ${timeShort(d)}`
  })()
  const reads = {
    glucose: readAt(series.glucose, baseline.glucose, step, m),
    heart: readAt(series.heart, baseline.heart, step, m),
    spo2: readAt(series.spo2, baseline.spo2, step, m),
  }
  const near = nearestBp(bp, m)
  const wk = atWork(work, startIso, m)
  const workText = {
    during: t('insights.tl.work.during', 'During work hours'),
    outside: t('insights.tl.work.outside', 'Outside work hours'),
    off: t('insights.tl.work.off', 'Not a work day'),
    unset: '',
  }[wk]

  const mealType = (s: string) =>
    ({
      breakfast: t('insights.tl.meal.breakfast', 'Breakfast'),
      lunch: t('insights.tl.meal.lunch', 'Lunch'),
      dinner: t('insights.tl.meal.dinner', 'Dinner'),
      snack: t('insights.tl.meal.snack', 'Snack'),
    })[s] ?? human(s)
  const meals = events.meals
  let last: (typeof meals)[number] | null = null
  for (const e of meals) if (e.m <= m + 0.5) last = e
  const mealText = (() => {
    if (!last) return t('insights.tl.noMeal', 'No meal logged before this moment.')
    const when = timeShort(at(startIso, last.m))
    const line = t('insights.tl.mealLine', '{{meal}} at {{time}} ({{ago}} before){{food}}', {
      meal: mealType(last.type),
      time: when,
      ago: agoText(t, m - last.m),
      food: last.food ? `: ${last.food}` : '',
    })
    return m - last.m > 600 ? t('insights.tl.lastMeal', 'Last meal: {{line}}', { line }) : line
  })()
  const nearbyText = (() => {
    const w = 120
    const parts: string[] = []
    for (const s of events.symptoms) if (Math.abs(s.m - m) <= w) parts.push(t('insights.tl.symptomNoted', '{{s}} noted', { s: human(s.type) }))
    const missed = events.missed.filter((e) => Math.abs(e.m - m) <= w).length
    if (missed)
      parts.push(
        missed === 1
          ? t('insights.tl.missedOne', 'a dose marked missed')
          : t('insights.tl.missedMany', '{{n}} doses marked missed', {
              n: missed,
            }),
      )
    for (const e of events.exercise) if (e.m1 >= m - w && e.m0 <= m + w) parts.push(human(e.type).toLowerCase())
    return parts.length
      ? t('insights.tl.within2h', 'Within 2 hours: {{list}}.', {
          list: parts.join(', '),
        })
      : t('insights.tl.nothingNear', 'No symptoms, missed doses or exercise within 2 hours.')
  })()

  // steps at the marker, and the nearest mood check-in
  const stepsHere = series.steps[clamp(Math.floor(m / step), 0, series.steps.length - 1)] ?? null
  const bucketWord = daily
    ? t('insights.tl.thisDay', 'today')
    : step >= 120
      ? t('insights.tl.thisBlock', 'in this {{n}} hours', { n: step / 60 })
      : t('insights.tl.thisHalf', 'in this half hour')
  let nm: (typeof events.mood)[number] | null = null
  for (const e of events.mood) if (!nm || Math.abs(e.m - m) < Math.abs(nm.m - m)) nm = e
  const moodText = nm
    ? t('insights.tl.checkin', 'Nearest check-in: mood {{mood}}{{stress}} of 5, {{ago}} {{dir}}', {
        mood: nm.mood,
        stress: nm.stress != null ? t('insights.tl.stressPart', ', stress {{s}}', { s: nm.stress }) : '',
        ago: agoText(t, nm.m - m),
        dir: nm.m - m < 0 ? t('insights.tl.earlier', 'earlier') : t('insights.tl.later', 'later'),
      })
    : t('insights.tl.noCheckin', 'No mood check-in in this period')

  // ── moving the marker
  const surface = useRef<HTMLDivElement>(null)
  const fromEvent = (e: PointerEvent) => {
    const r = surface.current?.getBoundingClientRect()
    if (r && r.width > 0) setClamped(((e.clientX - r.left) / r.width) * total)
  }
  const jumpMeal = (dir: 1 | -1) => {
    let target: number | null = null
    for (const e of meals) {
      if (dir > 0 && e.m > m + 1 && (target == null || e.m < target)) target = e.m
      if (dir < 0 && e.m < m - 1 && (target == null || e.m > target)) target = e.m
    }
    if (target != null) setClamped(target)
  }
  const onKey = (e: KeyboardEvent) => {
    const big = e.shiftKey || e.key === 'PageUp' || e.key === 'PageDown' ? DAY_MIN : daily ? DAY_MIN : STEP_MIN
    if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === 'ArrowUp')
      setClamped(m + (e.key === 'ArrowRight' ? big : e.key === 'ArrowUp' ? STEP_MIN : DAY_MIN))
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp' || e.key === 'ArrowDown')
      setClamped(m - (e.key === 'ArrowLeft' ? big : e.key === 'ArrowDown' ? STEP_MIN : DAY_MIN))
    else if (e.key === 'Home') setClamped(0)
    else if (e.key === 'End') setClamped(total - 1)
    else return
    e.preventDefault()
  }

  // ── time axis
  const every = days <= 7 ? 1 : days <= 30 ? 5 : 15
  const ticks = Array.from({ length: days }, (_, i) => i).filter((i) => i % every === 0)
  const tickText = (i: number) => {
    const d = at(startIso, i * DAY_MIN)
    return days <= 7
      ? d.toLocaleDateString(dateLocale('en-GB'), {
          weekday: 'short',
          day: 'numeric',
        })
      : d.toLocaleDateString(dateLocale('en-GB'), {
          day: 'numeric',
          month: 'short',
        })
  }

  const hasBase = baseline.available
  const maxSteps = Math.max(1, ...series.steps.map((v) => v ?? 0))
  const lane = (name: string, children: ReactNode, key: string) => (
    <div key={key} className="relative h-[22px]">
      <span className={cn('absolute left-0 top-0 flex h-full items-center text-micro text-ink2', AXIS)}>{name}</span>
      <div className={cn('absolute inset-y-0 right-0', 'left-14')}>{children}</div>
    </div>
  )
  const dot = (left: number, color: string, ring = true, title = '') => (
    <span
      key={`${left}-${title}`}
      title={title}
      className={cn('absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full', ring && 'ring-2 ring-card')}
      style={{ left: pct(left), background: color }}
    />
  )

  const plot = (h: number, children: ReactNode, key?: string) => (
    <div key={key} className={cn('relative', AXIS_PAD)}>
      <svg viewBox={`0 0 ${W} ${h}`} preserveAspectRatio="none" className="block w-full" style={{ height: h }} aria-hidden>
        {backdrop(h)}
        {children}
      </svg>
    </div>
  )

  const gaugeLabel = (name: string, r: Reading, digits: number) => `${name}: ${statusText(t, r, digits, hasBase)}`

  return (
    <section aria-label={t('insights.tl.title', 'Your readings on one time axis')} className="flex flex-col gap-3">
      {/* the readout: what the marker is on */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-card bg-well p-3" aria-live="off">
        <div className="min-w-0 flex-1 basis-60">
          <p className="flex flex-wrap items-center gap-2">
            <span className="text-body font-bold">{label}</span>
            {workText && <span className="rounded-chip bg-info-soft px-2.5 py-0.5 text-sub font-bold text-info">{workText}</span>}
          </p>
          <p className="text-sub text-ink2">{mealText}</p>
          <p className="text-sub text-ink2">{nearbyText}</p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={() => jumpMeal(-1)}
            className="press flex min-h-11 items-center gap-1 rounded-[12px] border border-line bg-card px-3 text-btn-sm font-bold"
            aria-label={t('insights.tl.prevMeal', 'Go to the previous meal')}
          >
            <CaretLeft size={16} aria-hidden /> {t('insights.tl.mealWord', 'Meal')}
          </button>
          {!daily && (
            <>
              <button
                type="button"
                onClick={() => setClamped(m - STEP_MIN)}
                className="press min-h-11 rounded-[12px] border border-line bg-card px-3 text-btn-sm font-bold"
                aria-label={t('insights.tl.back30', 'Back 30 minutes')}
              >
                &minus;30 {t('insights.tl.min', 'min')}
              </button>
              <button
                type="button"
                onClick={() => setClamped(m + STEP_MIN)}
                className="press min-h-11 rounded-[12px] border border-line bg-card px-3 text-btn-sm font-bold"
                aria-label={t('insights.tl.fwd30', 'Forward 30 minutes')}
              >
                +30 {t('insights.tl.min', 'min')}
              </button>
            </>
          )}
          <button
            type="button"
            onClick={() => jumpMeal(1)}
            className="press flex min-h-11 items-center gap-1 rounded-[12px] border border-line bg-card px-3 text-btn-sm font-bold"
            aria-label={t('insights.tl.nextMeal', 'Go to the next meal')}
          >
            {t('insights.tl.mealWord', 'Meal')} <CaretRight size={16} aria-hidden />
          </button>
        </div>
      </div>

      <div className="relative">
        {/* lanes: meals, workouts, symptoms, missed doses, work */}
        <div className="flex flex-col gap-0 pb-1">
          {lane(
            t('insights.tl.lane.meals', 'Meals'),
            <>{meals.map((e) => dot(e.m, 'var(--c-brass)', true, `${mealType(e.type)}${e.food ? `: ${e.food}` : ''}`))}</>,
            'meals',
          )}
          {lane(
            t('insights.tl.lane.exercise', 'Exercise'),
            <>
              {events.exercise.map((e) => (
                <span
                  key={e.m0}
                  title={human(e.type)}
                  className="absolute top-1/2 h-3 -translate-y-1/2 rounded-full"
                  style={{
                    left: pct(e.m0),
                    width: `max(12px, calc(${pct(e.m1)} - ${pct(e.m0)}))`,
                    background: 'var(--c-ok)',
                  }}
                />
              ))}
            </>,
            'exercise',
          )}
          {lane(t('insights.tl.lane.symptoms', 'Symptoms'), <>{events.symptoms.map((e) => dot(e.m, 'var(--c-info)', true, human(e.type)))}</>, 'symptoms')}
          {lane(
            t('insights.tl.lane.missed', 'Missed'),
            <>{events.missed.map((e) => dot(e.m, 'var(--c-danger)', true, t('insights.tl.missedTitle', 'Dose marked missed')))}</>,
            'missed',
          )}
          {lane(
            t('insights.tl.lane.work', 'Work'),
            <>
              {shades.wk.map(([a, b]) => (
                <span
                  key={a}
                  className="absolute top-1/2 h-3.5 -translate-y-1/2 rounded-[4px] opacity-30"
                  style={{
                    left: pct(a),
                    width: `max(3px, calc(${pct(b)} - ${pct(a)}))`,
                    background: 'var(--c-info)',
                  }}
                />
              ))}
            </>,
            'work',
          )}
        </div>

        {/* glucose, heart rate and SpO2 */}
        {built.map((b) => {
          const c = b.c
          const r = reads[c.key]
          const gMin = b.lo
          const gMax = b.hi
          const name = chartName(t, c.key)
          return (
            <div key={c.key}>
              <ChartHead
                color={c.color}
                name={name}
                unit={chartUnit(c.key)}
                value={r.value == null ? t('insights.tl.noReadingShort', 'No reading') : `${r.value.toFixed(c.digits)} ${chartUnit(c.key)}`}
                status={statusText(t, r, c.digits, hasBase)}
                tone={hasBase ? r.compare : 'unknown'}
                gauge={
                  <Gauge
                    min={gMin}
                    max={gMax}
                    lo={hasBase ? r.lo : null}
                    hi={hasBase ? r.hi : null}
                    baseline={hasBase ? r.baseline : null}
                    value={r.value}
                    color={c.color}
                    label={gaugeLabel(name, r, c.digits)}
                  />
                }
              />
              <div className="relative">
                {b.ticks.map((v) => (
                  <span
                    key={v}
                    className={cn('num absolute z-[1] -translate-y-1/2 pr-2 text-right text-micro text-ink3', AXIS)}
                    style={{ top: b.y(v), left: 0 }}
                  >
                    {v.toFixed(c.digits)}
                  </span>
                ))}
                {plot(
                  c.height,
                  <>
                    {b.ticks.map((v) => (
                      <line
                        key={v}
                        x1="0"
                        x2={W}
                        y1={b.y(v)}
                        y2={b.y(v)}
                        stroke="var(--c-line)"
                        strokeWidth="1"
                        vectorEffect="non-scaling-stroke"
                        opacity="0.7"
                      />
                    ))}
                    {b.band && <path d={b.band} fill={c.color} opacity="0.13" />}
                    {b.area && <path d={b.area} fill={c.color} opacity="0.16" />}
                    {b.base && (
                      <path
                        d={b.base}
                        fill="none"
                        stroke="var(--c-ink)"
                        strokeWidth="2"
                        strokeDasharray="6 4"
                        opacity="0.7"
                        vectorEffect="non-scaling-stroke"
                      />
                    )}
                    {b.line && (
                      <path
                        d={b.line}
                        fill="none"
                        stroke={c.color}
                        strokeWidth="2"
                        strokeLinejoin="round"
                        strokeLinecap="round"
                        vectorEffect="non-scaling-stroke"
                      />
                    )}
                    {b.out && (
                      <path
                        d={b.out}
                        fill="none"
                        stroke={c.color}
                        strokeWidth="3.6"
                        strokeLinejoin="round"
                        strokeLinecap="round"
                        vectorEffect="non-scaling-stroke"
                      />
                    )}
                  </>,
                )}
                {r.value != null && (
                  <span
                    className="pointer-events-none absolute z-[1] h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-[2.5px] ring-card"
                    style={{
                      left: `calc(3.5rem + (100% - 3.5rem) * ${m / total})`,
                      top: b.y(r.value),
                      background: c.color,
                    }}
                  />
                )}
              </div>
            </div>
          )
        })}

        {/* blood pressure */}
        {(() => {
          const sy = bp.map((r) => r.systolic)
          const di = bp.map((r) => r.diastolic)
          const bs = baseline.bpAvailable ? baseline.bpSystolic : null
          const [lo, hi] = domain([...sy, ...di, bs, baseline.bpDiastolic], 0.12)
          const h = 110
          const y = (v: number) => 8 + (1 - (v - lo) / (hi - lo)) * (h - 16)
          const ticks = niceTicks(lo, hi, 3)
          const d = near ? near.reading.systolic - (bs ?? near.reading.systolic) : null
          const ad = d == null ? '' : String(Math.abs(Math.round(d)))
          const status = !near
            ? t('insights.tl.noBp', 'No blood pressure reading in this period')
            : bs == null || d == null
              ? t('insights.tl.noBaseline', 'No baseline yet')
              : d === 0
                ? t('insights.tl.atBase', 'At baseline {{b}}', { b: bs })
                : d > 0
                  ? t('insights.tl.aboveBase', '{{d}} above baseline {{b}}', {
                      d: ad,
                      b: bs,
                    })
                  : t('insights.tl.belowBase', '{{d}} below baseline {{b}}', {
                      d: ad,
                      b: bs,
                    })
          const value = near
            ? `${near.reading.systolic}/${near.reading.diastolic} mmHg, ${agoText(t, near.gap)} ${near.gap < 0 ? t('insights.tl.earlier', 'earlier') : t('insights.tl.later', 'later')}`
            : t('insights.tl.noReadingShort', 'No reading')
          return (
            <div>
              <ChartHead
                color={BP_COLOR}
                name={chartName(t, 'bp')}
                unit={t('insights.tl.bpUnit', 'mmHg, top number')}
                value={value}
                status={status}
                tone="plain"
                gauge={
                  <Gauge
                    min={lo}
                    max={hi}
                    lo={null}
                    hi={null}
                    baseline={bs}
                    value={near?.reading.systolic ?? null}
                    color={BP_COLOR}
                    label={`${chartName(t, 'bp')}: ${status}`}
                  />
                }
              />
              <div className="relative">
                {ticks.map((v) => (
                  <span key={v} className={cn('num absolute z-[1] -translate-y-1/2 pr-2 text-right text-micro text-ink3', AXIS)} style={{ top: y(v), left: 0 }}>
                    {Math.round(v)}
                  </span>
                ))}
                {plot(
                  h,
                  <>
                    {ticks.map((v) => (
                      <line key={v} x1="0" x2={W} y1={y(v)} y2={y(v)} stroke="var(--c-line)" strokeWidth="1" vectorEffect="non-scaling-stroke" opacity="0.7" />
                    ))}
                    {bs != null && (
                      <line
                        x1="0"
                        x2={W}
                        y1={y(bs)}
                        y2={y(bs)}
                        stroke="var(--c-ink)"
                        strokeWidth="2"
                        strokeDasharray="6 4"
                        opacity="0.7"
                        vectorEffect="non-scaling-stroke"
                      />
                    )}
                    {bp.map((r) => (
                      <line
                        key={`s${r.m}`}
                        x1={x(r.m)}
                        x2={x(r.m)}
                        y1={y(r.systolic)}
                        y2={y(r.diastolic)}
                        stroke="var(--c-line)"
                        strokeWidth="2"
                        vectorEffect="non-scaling-stroke"
                      />
                    ))}
                  </>,
                )}
                {bp.map((r) => (
                  <span key={r.m} className="pointer-events-none absolute">
                    <span
                      className="absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card"
                      style={{
                        left: `calc(3.5rem + (100% - 3.5rem) * ${r.m / total})`,
                        top: y(r.systolic),
                        background: BP_COLOR,
                      }}
                    />
                    <span
                      className="absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card"
                      style={{
                        left: `calc(3.5rem + (100% - 3.5rem) * ${r.m / total})`,
                        top: y(r.diastolic),
                        background: 'var(--c-info)',
                      }}
                    />
                  </span>
                ))}
              </div>
            </div>
          )
        })()}

        {/* steps and mood */}
        {(() => {
          const h = 110
          const bw = Math.max(1.5, (W / series.steps.length) * 0.7)
          return (
            <div>
              <ChartHead
                color={STEPS_COLOR}
                name={chartName(t, 'steps')}
                unit=""
                value={
                  stepsHere == null || stepsHere === 0
                    ? t('insights.tl.noSteps', 'No steps {{when}}', {
                        when: bucketWord,
                      })
                    : t('insights.tl.stepsHere', '{{n}} steps {{when}}', {
                        n: stepsHere.toLocaleString('en-US'),
                        when: bucketWord,
                      })
                }
                status={moodText}
                tone="plain"
                gauge={null}
              />
              <div className="relative">
                {[5, 1].map((v) => (
                  <span
                    key={v}
                    className={cn('num absolute z-[1] -translate-y-1/2 pr-2 text-right text-micro text-ink3', AXIS)}
                    style={{ top: 10 + (1 - (v - 1) / 4) * (h - 20), left: 0 }}
                  >
                    {v}
                  </span>
                ))}
                {plot(
                  h,
                  <>
                    {series.steps.map((v, k) =>
                      v ? (
                        <rect
                          key={k}
                          x={xb(k) - bw / 2}
                          y={h - (v / maxSteps) * (h - 6)}
                          width={bw}
                          height={(v / maxSteps) * (h - 6)}
                          fill={STEPS_COLOR}
                          opacity="0.7"
                        />
                      ) : null,
                    )}
                  </>,
                )}
                {events.mood.map((e) => (
                  <span key={e.m} className="pointer-events-none absolute">
                    <span
                      className="absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card"
                      style={{
                        left: `calc(3.5rem + (100% - 3.5rem) * ${e.m / total})`,
                        top: 10 + (1 - (e.mood - 1) / 4) * (h - 20),
                        background: 'var(--c-ok)',
                      }}
                    />
                    {e.stress != null && (
                      <span
                        className="absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card"
                        style={{
                          left: `calc(3.5rem + (100% - 3.5rem) * ${e.m / total})`,
                          top: 10 + (1 - (e.stress - 1) / 4) * (h - 20),
                          background: 'var(--c-warn)',
                        }}
                      />
                    )}
                  </span>
                ))}
              </div>
            </div>
          )
        })()}

        {/* the time axis */}
        <div className={cn('relative mt-1 h-5', AXIS_PAD)} aria-hidden>
          <div className="relative h-full">
            {ticks.map((i) => (
              <span
                key={i}
                className="absolute top-0 whitespace-nowrap text-micro text-ink2"
                style={{
                  left: pct((i + (days <= 7 ? 0.5 : 0)) * DAY_MIN),
                  transform: days <= 7 ? 'translateX(-50%)' : undefined,
                }}
              >
                {tickText(i)}
              </span>
            ))}
          </div>
        </div>

        {/* the marker: a line over every chart, a handle above, and a surface that takes the drag */}
        <div className={cn('pointer-events-none absolute inset-y-0 right-0 left-14')}>
          <div className="absolute inset-y-0 w-0 border-l-2 border-ink opacity-70" style={{ left: pct(m) }} />
          <div
            className="absolute -top-3 flex h-[26px] w-[26px] -translate-x-1/2 items-center justify-center rounded-full bg-ink text-canvas shadow-lift"
            style={{ left: pct(m) }}
            aria-hidden
          >
            <CaretLeft size={10} />
            <CaretRight size={10} />
          </div>
        </div>
        <div
          ref={surface}
          role="slider"
          tabIndex={0}
          aria-label={t('insights.tl.markerLabel', 'Time marker')}
          aria-orientation="horizontal"
          aria-valuemin={0}
          aria-valuemax={total - 1}
          aria-valuenow={Math.round(m)}
          aria-valuetext={`${label}. ${gaugeLabel(chartName(t, 'glucose'), reads.glucose, 1)}`}
          onKeyDown={onKey}
          onPointerDown={(e) => {
            dragging.current = true
            try {
              e.currentTarget.setPointerCapture(e.pointerId)
            } catch {
              /* capture is optional */
            }
            fromEvent(e)
          }}
          onPointerMove={(e) => dragging.current && fromEvent(e)}
          onPointerUp={() => (dragging.current = false)}
          onPointerCancel={() => (dragging.current = false)}
          className="absolute inset-y-0 right-0 left-14 cursor-col-resize rounded-card focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
          style={{ touchAction: 'pan-y' }}
        />
      </div>

      <div className="flex flex-col gap-1 text-sub text-ink2">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-6 rounded-full bg-info opacity-20" aria-hidden />
            {t('insights.tl.legend.usual', 'Your usual range: the middle half of your readings at that hour')}
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-6 border-t-2 border-dashed border-ink opacity-70" aria-hidden />
            {baseline.source === 'period'
              ? t('insights.tl.legend.basePeriod', 'Your baseline: your average for each hour of the day over this period (blood pressure: one fixed value)')
              : t(
                  'insights.tl.legend.base',
                  'Your baseline: your average for each hour of the day over the 60 days before this period (blood pressure: one fixed value)',
                )}
          </span>
          {!daily && (
            <span className="flex items-center gap-1.5">
              <span className="w-6 border-t-[3px] border-info" aria-hidden />
              {t('insights.tl.legend.outside', 'Thicker line: outside your usual range')}
            </span>
          )}
          {work.set && (
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-4 rounded-[3px] bg-info opacity-25" aria-hidden />
              {t('insights.tl.legend.work', 'Work hours {{s}} to {{e}}, from your set-up', { s: work.start, e: work.end })}
            </span>
          )}
          {shades.night.length > 0 && (
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-4 rounded-[3px] bg-well" aria-hidden />
              {t('insights.tl.legend.night', 'Night, 12 to 6 am')}
            </span>
          )}
        </div>
        {!hasBase && <p>{t('insights.tl.noBaselineNote', 'Not enough days yet to work out your baseline. It needs about a week of readings.')}</p>}
        <p className="text-ink3">
          {t(
            'insights.tl.help',
            'Drag the round marker, or click or tap anywhere on the charts. Arrow keys move it by 30 minutes. The gauge on each chart shows your usual range as a bar, your baseline as a thin line, and the reading at the marker as a block.',
          )}
        </p>
      </div>
    </section>
  )
}
