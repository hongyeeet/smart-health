/**
 * Insights → Overview charts: glucose, heart rate, SpO2 and blood pressure on ONE shared time axis (time across, the reading up), with a
 * marker the person can drag (or move with the arrow keys) to read every chart at the same moment, and a fixed-size stats bar for that day:
 * the day's glucose, heart rate, SpO2, blood pressure, steps, and the calories, sugar and salt eaten. Under the pills (which switch each
 * chart and each log lane on or off) are the meals, workouts, symptoms, missed doses and work hours from the person's own logs and set-up.
 *
 * 7 days is shown every half hour; 30 and 90 days are one point a day, so a drift over weeks is easy to see. Every chart has the person's
 * BASELINE (their average for each hour of the day over the 60 days before the period, or one fixed number for blood pressure, or the first
 * 30 days of a period that has nothing before it), the usual range, and a dotted trend line in the one-point-a-day views. A gauge on each
 * chart sets the reading at the marker against the baseline. The words say how far it is and whether it is inside the usual range; no
 * reading is called good or bad. All numbers come from GET /insights/timeline; this file only lays them out.
 */
import { useMemo, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import type { InsightsDays, InsightsTimeline } from '@/data/types'
import { cn } from '@/lib/cn'
import { dateLocale } from '@/lib/locale'
import { Segmented } from '@/ui/controls'
import { ArrowDown, ArrowUp, CaretLeft, CaretRight } from '@/ui/icons'
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
  trendPath,
  type Compare,
  type Reading,
} from './timelineMath'

const W = 1000
const AXIS = 'w-16'
const AXIS_PAD = 'pl-16'
const STEP_MIN = 30

type Key = 'glucose' | 'heart' | 'spo2'
export type PillKey = Key | 'bp' | 'meals' | 'exercise' | 'symptoms' | 'missed' | 'work'
const ALL_ON: Record<PillKey, boolean> = {
  glucose: true,
  heart: true,
  spo2: true,
  bp: true,
  meals: true,
  exercise: true,
  symptoms: true,
  missed: true,
  work: true,
}

interface ChartCfg {
  key: Key
  height: number
  color: string
  digits: number
  floor?: number
  ceil?: number
}
const CHARTS: ChartCfg[] = [
  { key: 'glucose', height: 190, color: 'var(--c-info)', digits: 1, floor: 0 },
  { key: 'heart', height: 130, color: 'var(--c-danger)', digits: 0, floor: 0 },
  { key: 'spo2', height: 110, color: 'var(--c-brass)', digits: 1, ceil: 100 },
]
const COLOR: Record<PillKey, string> = {
  glucose: 'var(--c-info)',
  heart: 'var(--c-danger)',
  spo2: 'var(--c-brass)',
  bp: 'var(--c-warn)',
  meals: 'var(--c-brass)',
  exercise: 'var(--c-ok)',
  symptoms: 'var(--c-info)',
  missed: 'var(--c-danger)',
  work: 'var(--c-info)',
}

const chartName = (t: TFunction, k: Key | 'bp') =>
  ({
    glucose: t('insights.tl.glucose', 'Glucose'),
    heart: t('insights.tl.heart', 'Heart rate'),
    spo2: t('insights.tl.spo2', 'SpO2'),
    bp: t('insights.tl.bp', 'Blood pressure'),
  })[k]
const chartUnit = (k: Key) => (k === 'glucose' ? 'mmol/L' : k === 'heart' ? 'bpm' : '%')

const human = (s: string) => {
  const x = s.replace(/_/g, ' ').trim()
  return x.charAt(0).toUpperCase() + x.slice(1)
}

/** the local date and clock time `m` minutes after midnight of the first day */
function at(startIso: string, m: number): Date {
  const d = new Date(`${startIso}T00:00:00`)
  d.setMinutes(d.getMinutes() + Math.round(m))
  return d
}
const dayShort = (d: Date) => d.toLocaleDateString(dateLocale('en-GB'), { weekday: 'short', day: 'numeric', month: 'short' })
const timeShort = (d: Date) => d.toLocaleTimeString(dateLocale('en-US'), { hour: 'numeric', minute: '2-digit' })
const dayMonth = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString(dateLocale('en-GB'), { day: 'numeric', month: 'short' })
const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v))
const fmt = (v: number | null | undefined, digits = 0) =>
  v == null ? '–' : v.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })

function agoText(t: TFunction, gap: number): string {
  const { h, min } = gapText(gap)
  if (h && min) return t('insights.tl.hm', '{{h}} h {{m}} min', { h, m: min })
  if (h) return t('insights.tl.h', '{{h}} h', { h })
  return t('insights.tl.m', '{{m}} min', { m: min })
}

const TONE: Record<Compare, string> = { above: 'text-warn', below: 'text-info', within: 'text-ok', unknown: 'text-ink3' }

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
        ? t('insights.tl.aboveBase', '{{d}} above baseline {{b}}', { d: ad, b: base })
        : t('insights.tl.belowBase', '{{d}} below baseline {{b}}', { d: ad, b: base })
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
    <div className="relative h-[18px] w-28 flex-none sm:w-40" role="img" aria-label={label}>
      <div className="absolute inset-x-0 top-[6px] h-[6px] rounded-full bg-line" />
      {lo != null && hi != null && (
        <div
          className="absolute top-[4px] h-[10px] rounded-full opacity-40"
          style={{ left: p(lo), width: `max(6px, calc(${p(hi)} - ${p(lo)}))`, background: color }}
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

/** One of the switches under the title: shows or hides a chart or a log lane. All on one line, scrolling sideways rather than wrapping on a narrow screen. */
function Pill({ on, color, label, onClick }: { on: boolean; color: string; label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={cn(
        'press flex min-h-10 flex-none items-center gap-1 whitespace-nowrap rounded-chip border px-1.5 text-[12px]',
        on ? 'border-line bg-card font-bold text-ink' : 'border-line bg-transparent text-ink3',
      )}
    >
      <span className="h-2 w-2 rounded-full" style={{ background: on ? color : 'transparent', boxShadow: `inset 0 0 0 1.5px ${color}` }} aria-hidden />
      {label}
    </button>
  )
}

export interface TimelineNav {
  canBack: boolean
  canForward: boolean
  onBack: () => void
  onForward: () => void
}

/** The header, the switches, and the charts. `days` and `setDays` are the 7, 30 or 90 day choice. */
export function OverviewTimeline({
  data,
  days,
  setDays,
  nav,
  onOpenDay,
}: {
  data: InsightsTimeline
  days: InsightsDays
  setDays: (d: InsightsDays) => void
  nav: TimelineNav
  onOpenDay: (iso: string) => void
}) {
  const { t } = useTranslation()
  const [show, setShow] = useState<Record<PillKey, boolean>>(ALL_ON)
  const flip = (k: PillKey) => setShow((s) => ({ ...s, [k]: !s[k] }))
  const daily = data.period.bucketMinutes >= DAY_MIN
  const pills: { key: PillKey; label: string }[] = [
    { key: 'glucose', label: t('insights.tl.glucose', 'Glucose') },
    { key: 'heart', label: t('insights.tl.heart', 'Heart rate') },
    { key: 'spo2', label: t('insights.tl.spo2', 'SpO2') },
    { key: 'bp', label: t('insights.tl.bp', 'Blood pressure') },
    { key: 'meals', label: t('insights.tl.lane.meals', 'Meals') },
    { key: 'exercise', label: t('insights.tl.lane.exercise', 'Exercise') },
    { key: 'symptoms', label: t('insights.tl.lane.symptoms', 'Symptoms') },
    { key: 'missed', label: t('insights.tl.lane.missedDoses', 'Missed doses') },
    { key: 'work', label: daily ? t('insights.tl.lane.workDays', 'Work days') : t('insights.tl.lane.work', 'Work') },
  ]
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <button
            type="button"
            onClick={nav.onBack}
            disabled={!nav.canBack}
            aria-label={t('insights.tl.earlier', 'Earlier period')}
            className="press flex h-11 w-11 flex-none items-center justify-center rounded-full border border-line bg-card text-ink disabled:opacity-40"
          >
            <CaretLeft size={20} aria-hidden />
          </button>
          <div className="min-w-0">
            <p className="text-h2 font-bold leading-tight" aria-live="polite">
              {t('insights.tl.periodTitle', '{{from}} to {{to}}', {
                from: dayMonth(data.period.start),
                to: new Date(`${data.period.end}T12:00:00`).toLocaleDateString(dateLocale('en-GB'), { day: 'numeric', month: 'short', year: 'numeric' }),
              })}
            </p>
            <p className="text-sub text-ink3">
              {t('insights.tl.latestData', 'Latest data, {{d}}.', { d: dayMonth(data.period.latest) })}{' '}
              {daily
                ? t('insights.tl.builtDaily', 'Built from your 5-minute timeline, shown as daily summaries.')
                : t('insights.tl.builtHalf', 'Built from your 5-minute timeline, shown every half hour.')}
            </p>
          </div>
          <button
            type="button"
            onClick={nav.onForward}
            disabled={!nav.canForward}
            aria-label={t('insights.tl.later', 'Later period')}
            className="press flex h-11 w-11 flex-none items-center justify-center rounded-full border border-line bg-card text-ink disabled:opacity-40"
          >
            <CaretRight size={20} aria-hidden />
          </button>
        </div>
        <div className="w-full sm:w-auto sm:min-w-[17rem]">
          <Segmented
            label={t('insights.shared.period', 'Period')}
            value={days}
            onChange={setDays}
            options={[
              { value: 7, label: t('insights.shared.days', '{{n}} days', { n: 7 }) },
              { value: 30, label: t('insights.shared.days', '{{n}} days', { n: 30 }) },
              { value: 90, label: t('insights.shared.days', '{{n}} days', { n: 90 }) },
            ]}
          />
        </div>
      </div>

      <div
        role="group"
        aria-label={t('insights.tl.pillsLabel', 'What to show')}
        className="-mx-1 flex flex-nowrap items-center gap-1 overflow-x-auto px-1 pb-1"
      >
        {pills.map((p, i) => (
          <span key={p.key} className="flex flex-none items-center gap-1">
            {i === 4 && <span className="mx-0.5 h-6 w-px bg-line" aria-hidden />}
            <Pill on={show[p.key]} color={COLOR[p.key]} label={p.label} onClick={() => flip(p.key)} />
          </span>
        ))}
      </div>

      <Plot key={`${days}:${data.period.start}:${data.period.end}`} data={data} show={show} onOpenDay={onOpenDay} />
    </div>
  )
}

function Plot({ data, show, onOpenDay }: { data: InsightsTimeline; show: Record<PillKey, boolean>; onOpenDay: (iso: string) => void }) {
  const { t } = useTranslation()
  const { period, series, baseline, events, work, bp, dayRows } = data
  const days = period.days
  const step = period.bucketMinutes
  const total = days * DAY_MIN
  const daily = step >= DAY_MIN
  const startIso = period.start
  const hasBase = baseline.available

  // the marker opens on the latest meal logged (so that day's calories, sugar and salt are there to read); with no meal anywhere, on the latest glucose reading
  const open = (() => {
    const lastMeal = events.meals[events.meals.length - 1]
    if (lastMeal) return daily ? Math.floor(lastMeal.m / DAY_MIN) * DAY_MIN + DAY_MIN / 2 : lastMeal.m
    for (let k = series.glucose.length - 1; k >= 0; k--) if (series.glucose[k] != null) return k * step + step / 2
    return total - 1
  })()
  const [m, setM] = useState(() => clamp(open, 0, total - 1))
  const dragging = useRef(false)
  // one point a day: the marker sits on the middle of a day
  const setClamped = (v: number) => {
    const c = clamp(v, 0, total - 1)
    setM(daily ? Math.floor(c / DAY_MIN) * DAY_MIN + DAY_MIN / 2 : c)
  }

  const x = (min: number) => (min / total) * W
  const xb = (k: number) => x(k * step + step / 2)
  const pct = (min: number) => `${(min / total) * 100}%`
  const left = (min: number) => `calc(4rem + (100% - 4rem) * ${min / total})`

  // ── the three line charts, built once per answer
  const built = useMemo(
    () =>
      CHARTS.map((c) => {
        const vals = series[c.key]
        const h = baseline[c.key]
        const du = baseline.daily[c.key]
        const lows = c.key === 'glucose' ? series.glucoseMin : c.key === 'heart' ? series.heartMin : series.spo2Min
        const highs = c.key === 'glucose' ? series.glucoseMax : c.key === 'heart' ? series.heartMax : series.spo2Max
        const [lo, hi] = domain([...(daily ? lows : vals), ...(daily ? highs : vals), ...h.mean, ...h.lo, ...h.hi, du.lo, du.hi], 0.1, c.floor, c.ceil)
        const pad = 8
        const y = (v: number) => pad + (1 - (v - lo) / (hi - lo)) * (c.height - pad * 2)
        let range = ''
        if (daily) {
          const up: string[] = []
          const down: string[] = []
          for (let k = 0; k < vals.length; k++) {
            const a = highs[k]
            const b = lows[k]
            if (a == null || b == null) continue
            up.push(`${xb(k).toFixed(1)} ${y(a).toFixed(1)}`)
            down.push(`${xb(k).toFixed(1)} ${y(b).toFixed(1)}`)
          }
          if (up.length) range = `M${up.join('L')}L${down.reverse().join('L')}Z`
        }
        return {
          c,
          lo,
          hi,
          y,
          ticks: niceTicks(lo, hi, c.height > 150 ? 4 : 3),
          line: linePath(vals, xb, y),
          out: hasBase ? outsidePath(vals, h, step, xb, y, du) : '',
          base: hasBase ? baselinePath(h, days, step, x, y, du) : '',
          band: hasBase ? bandPath(h, days, step, x, y, du) : '',
          range,
          trend: daily ? trendPath(vals, xb, y) : null,
        }
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [data],
  )

  // ── shaded backgrounds: night (12 to 6 am), work hours, and a line between days (or between the labelled days)
  const shades = useMemo(() => {
    const night: number[] = []
    const wk: [number, number][] = []
    const ws = clockMin(work.start)
    const we = clockMin(work.end)
    for (let d = 0; d < days; d++) {
      if (!daily && days <= 30) night.push(d * DAY_MIN)
      if (work.set && ws != null && we != null && work.days.includes(isoWeekday(startIso, d)))
        wk.push([d * DAY_MIN + (daily ? 0 : ws), d * DAY_MIN + (daily ? DAY_MIN : we)])
    }
    return { night, wk }
  }, [days, daily, work, startIso])

  // ── the time axis: a label and a faint line at each tick
  const ticks = useMemo(() => {
    const out: { i: number; text: string; centre: boolean }[] = []
    for (let i = 0; i < days; i++) {
      const d = at(startIso, i * DAY_MIN)
      if (days <= 7) out.push({ i, text: d.toLocaleDateString(dateLocale('en-GB'), { weekday: 'short', day: 'numeric' }), centre: true })
      else if (days <= 30) {
        if (i % 5 === 0) out.push({ i, text: d.toLocaleDateString(dateLocale('en-GB'), { day: 'numeric', month: 'short' }), centre: false })
      } else if (d.getDate() === 1 || i === 0) out.push({ i, text: d.toLocaleDateString(dateLocale('en-GB'), { month: 'short' }), centre: false })
    }
    return out
  }, [days, startIso])

  const backdrop = (h: number) => (
    <>
      {shades.night.map((s) => (
        <rect key={`n${s}`} x={x(s)} y={0} width={x(360)} height={h} fill="var(--c-well)" opacity="0.7" />
      ))}
      {show.work &&
        !daily &&
        shades.wk.map(([a, b]) => <rect key={`w${a}`} x={x(a)} y={0} width={x(b) - x(a)} height={h} fill="var(--c-info)" opacity="0.1" />)}
      {ticks.map(
        (tk) =>
          (days <= 7 ? tk.i > 0 : true) && (
            <line
              key={`t${tk.i}`}
              x1={x(tk.i * DAY_MIN)}
              x2={x(tk.i * DAY_MIN)}
              y1={0}
              y2={h}
              stroke="var(--c-line)"
              strokeWidth="1"
              vectorEffect="non-scaling-stroke"
              opacity="0.8"
            />
          ),
      )}
    </>
  )

  // ── what the marker reads
  const dayI = clamp(Math.floor(m / DAY_MIN), 0, days - 1)
  const row = dayRows[dayI]
  const label = (() => {
    const d = at(startIso, m)
    return daily ? dayShort(d) : `${dayShort(d)}, ${timeShort(d)}`
  })()
  const reads = {
    glucose: readAt(series.glucose, baseline.glucose, step, m, baseline.daily.glucose),
    heart: readAt(series.heart, baseline.heart, step, m, baseline.daily.heart),
    spo2: readAt(series.spo2, baseline.spo2, step, m, baseline.daily.spo2),
  }
  const near = nearestBp(bp, m)
  const wk = atWork(work, startIso, m)
  const workText = {
    during: t('insights.tl.work.during', 'During work hours'),
    outside: t('insights.tl.work.outside', 'Outside work hours'),
    off: t('insights.tl.work.off', 'Not a work day'),
    unset: '',
  }[wk]
  const dayWork = work.set
    ? work.days.includes(isoWeekday(startIso, dayI))
      ? t('insights.tl.work.day', 'Work day')
      : t('insights.tl.work.off', 'Not a work day')
    : ''

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
    const line = t('insights.tl.mealLine', '{{meal}} at {{time}} ({{ago}} before){{food}}', {
      meal: mealType(last.type),
      time: timeShort(at(startIso, last.m)),
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
      parts.push(missed === 1 ? t('insights.tl.missedOne', 'a dose marked missed') : t('insights.tl.missedMany', '{{n}} doses marked missed', { n: missed }))
    for (const e of events.exercise) if (e.m1 >= m - w && e.m0 <= m + w) parts.push(human(e.type).toLowerCase())
    return parts.length
      ? t('insights.tl.within2h', 'Within 2 hours: {{list}}.', { list: parts.join(', ') })
      : t('insights.tl.nothingNear', 'No symptoms, missed doses or exercise within 2 hours.')
  })()
  const countsText = row
    ? [
        row.meals === 1 ? t('insights.tl.mealsOne', '1 meal logged') : t('insights.tl.mealsMany', '{{n}} meals logged', { n: row.meals }),
        row.missed === 1 ? t('insights.tl.dosesMissedOne', '1 dose missed') : t('insights.tl.dosesMissedMany', '{{n}} doses missed', { n: row.missed }),
        row.symptoms === 1 ? t('insights.tl.symptomsOne', '1 symptom noted') : t('insights.tl.symptomsMany', '{{n}} symptoms noted', { n: row.symptoms }),
      ].join(', ')
    : ''

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
  const nudge = (dir: 1 | -1) => setClamped(m + dir * (daily ? DAY_MIN : STEP_MIN))
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'ArrowRight') nudge(1)
    else if (e.key === 'ArrowLeft') nudge(-1)
    else if (e.key === 'PageDown' || e.key === 'ArrowUp') setClamped(m + DAY_MIN)
    else if (e.key === 'PageUp' || e.key === 'ArrowDown') setClamped(m - DAY_MIN)
    else if (e.key === 'Home') setClamped(0)
    else if (e.key === 'End') setClamped(total - 1)
    else return
    e.preventDefault()
  }

  const lane = (key: PillKey, name: string, children: ReactNode) =>
    show[key] && (
      <div key={key} className="relative h-[22px]">
        <span className={cn('absolute left-0 top-0 flex h-full items-center whitespace-nowrap text-micro text-ink2', AXIS)}>{name}</span>
        <div className="absolute inset-y-0 left-16 right-0">{children}</div>
      </div>
    )
  const dot = (min: number, color: string, title: string, size = 12) => (
    <span
      key={`${min}-${title}`}
      title={title}
      className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card"
      style={{ left: pct(min), background: color, width: size, height: size }}
    />
  )
  const mealMax = Math.max(1, ...dayRows.map((r) => r.meals))
  const dayCell = (i: number, extra: ReactNode, key: string) => (
    <span key={key} className="absolute inset-y-0" style={{ left: pct(i * DAY_MIN), width: pct(DAY_MIN) }}>
      {extra}
    </span>
  )

  const plot = (h: number, children: ReactNode) => (
    <div className={cn('relative', AXIS_PAD)}>
      <svg viewBox={`0 0 ${W} ${h}`} preserveAspectRatio="none" className="block w-full" style={{ height: h }} aria-hidden>
        {backdrop(h)}
        {children}
      </svg>
    </div>
  )
  const yLabels = (tk: number[], y: (v: number) => number, digits: number) =>
    tk.map((v) => (
      <span key={v} className={cn('num absolute z-[1] -translate-y-1/2 pr-2 text-right text-micro text-ink3', AXIS)} style={{ top: y(v), left: 0 }}>
        {v.toFixed(digits)}
      </span>
    ))
  const gaugeLabel = (name: string, r: Reading, digits: number) => `${name}: ${statusText(t, r, digits, hasBase)}`

  // ── the stats bar for the day under the marker: fixed cells, so nothing moves or spills as the marker moves
  const cell = (name: string, value: string, unit: string, note: string) => (
    <div key={name} className="flex h-[4.25rem] min-w-0 flex-col justify-between rounded-[12px] bg-card px-2.5 py-1.5">
      <span className="text-micro text-ink3">{name}</span>
      <span className="num whitespace-nowrap text-body font-bold leading-none">
        {value}
        {unit && value !== '–' && <span className="ml-1 text-micro font-normal text-ink3">{unit}</span>}
      </span>
      <span className="whitespace-nowrap text-micro text-ink3">{note}</span>
    </div>
  )
  const rangeNote = (a: { min: number | null; max: number | null }, d = 0) =>
    a.min == null || a.max == null ? t('insights.tl.noData', 'no data') : `${fmt(a.min, d)}–${fmt(a.max, d)}`
  const ate = !!row && row.meals > 0
  const noFood = t('insights.tl.noMealsLogged', 'no meals logged')
  const notRecorded = t('insights.tl.notRecorded', 'not recorded')
  const avgWord = t('insights.tl.avgDay', 'avg')

  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-card bg-well p-3" aria-live="off">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="flex min-w-0 flex-wrap items-center gap-2">
            <span className="text-body font-bold">{label}</span>
            {(daily ? dayWork : workText) && (
              <span className="rounded-chip bg-info-soft px-2.5 py-0.5 text-sub font-bold text-info">{daily ? dayWork : workText}</span>
            )}
          </p>
          <div className="flex flex-wrap gap-1.5">
            <button
              type="button"
              onClick={() => jumpMeal(-1)}
              className="press flex min-h-10 items-center gap-1 rounded-[12px] border border-line bg-card px-2.5 text-btn-sm font-bold"
              aria-label={t('insights.tl.prevMeal', 'Go to the previous meal')}
            >
              <CaretLeft size={16} aria-hidden /> {t('insights.tl.mealWord', 'Meal')}
            </button>
            <button
              type="button"
              onClick={() => nudge(-1)}
              className="press min-h-10 rounded-[12px] border border-line bg-card px-2.5 text-btn-sm font-bold"
              aria-label={daily ? t('insights.tl.prevDay', 'Previous day') : t('insights.tl.back30', 'Back 30 minutes')}
            >
              {daily ? t('insights.tl.dayBack', '−1 day') : t('insights.tl.min30back', '−30 min')}
            </button>
            <button
              type="button"
              onClick={() => nudge(1)}
              className="press min-h-10 rounded-[12px] border border-line bg-card px-2.5 text-btn-sm font-bold"
              aria-label={daily ? t('insights.tl.nextDay', 'Next day') : t('insights.tl.fwd30', 'Forward 30 minutes')}
            >
              {daily ? t('insights.tl.dayFwd', '+1 day') : t('insights.tl.min30fwd', '+30 min')}
            </button>
            <button
              type="button"
              onClick={() => jumpMeal(1)}
              className="press flex min-h-10 items-center gap-1 rounded-[12px] border border-line bg-card px-2.5 text-btn-sm font-bold"
              aria-label={t('insights.tl.nextMeal', 'Go to the next meal')}
            >
              {t('insights.tl.mealWord', 'Meal')} <CaretRight size={16} aria-hidden />
            </button>
          </div>
        </div>
        <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {cell(t('insights.tl.glucose', 'Glucose'), fmt(row?.glucose.avg, 1), 'mmol/L', row ? `${avgWord} · ${rangeNote(row.glucose, 1)}` : '')}
          {cell(t('insights.tl.heart', 'Heart rate'), fmt(row?.heart.avg), 'bpm', row ? `${avgWord} · ${rangeNote(row.heart)}` : '')}
          {cell(t('insights.tl.spo2', 'SpO2'), fmt(row?.spo2.avg, 1), '%', row ? `${avgWord} · ${rangeNote(row.spo2, 1)}` : '')}
          {cell(
            t('insights.tl.bp', 'Blood pressure'),
            row?.systolic != null && row.diastolic != null ? `${fmt(row.systolic)}/${fmt(row.diastolic)}` : '–',
            'mmHg',
            row?.systolic != null ? t('insights.tl.dayAvg', 'day average') : t('insights.tl.noReadingDay', 'no reading'),
          )}
          {cell(t('insights.tl.stepsWord', 'Steps'), fmt(row?.steps), '', t('insights.tl.thatDay', 'that day'))}
          {cell(
            t('insights.tl.calories', 'Calories'),
            ate ? fmt(row?.kcal) : '–',
            'kcal',
            !ate ? noFood : row?.kcal == null ? notRecorded : t('insights.tl.estimated', 'estimated'),
          )}
          {cell(
            t('insights.tl.sugar', 'Sugar'),
            ate ? fmt(row?.sugarG) : '–',
            'g',
            !ate ? noFood : row?.sugarG == null ? notRecorded : t('insights.tl.fromMeals', 'from your meals'),
          )}
          {cell(
            t('insights.tl.salt', 'Salt'),
            ate ? fmt(row?.sodiumMg) : '–',
            'mg',
            !ate ? noFood : row?.sodiumMg == null ? notRecorded : t('insights.tl.sodium', 'sodium'),
          )}
        </div>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-x-3 gap-y-1">
          <div className="min-h-[4.25rem] min-w-0 flex-1 basis-56 text-sub text-ink2">
            <p>{countsText}</p>
            <p>
              {daily ? t('insights.tl.tapDay', 'Drag the marker or tap a day to read it. Open a day for its 5-minute detail.') : `${mealText.endsWith('.') ? mealText : `${mealText}.`} ${nearbyText}`}
            </p>
          </div>
          <button
            type="button"
            onClick={() => onOpenDay(row?.date ?? startIso)}
            className="press min-h-10 flex-none rounded-[12px] bg-brand px-3 text-btn-sm font-bold text-on-brand"
          >
            {t('insights.tl.openDay', 'Open this day')}
          </button>
        </div>
      </div>

      <div className="relative">
        {/* lanes: meals, workouts, symptoms, missed doses, work */}
        <div className="flex flex-col gap-0 pb-1">
          {lane(
            'meals',
            t('insights.tl.lane.meals', 'Meals'),
            daily
              ? dayRows.map((r, i) =>
                  r.meals
                    ? dayCell(
                        i,
                        <span
                          className="absolute inset-x-[1px] inset-y-[3px] rounded-[3px]"
                          style={{ background: 'var(--c-brass)', opacity: 0.25 + 0.65 * (r.meals / mealMax) }}
                          title={`${dayMonth(r.date)}: ${r.meals}`}
                        />,
                        `m${i}`,
                      )
                    : null,
                )
              : meals.map((e) => dot(e.m, 'var(--c-brass)', `${mealType(e.type)}${e.food ? `: ${e.food}` : ''}`)),
          )}
          {lane(
            'exercise',
            t('insights.tl.lane.exercise', 'Exercise'),
            events.exercise.map((e) => (
              <span
                key={e.m0}
                title={human(e.type)}
                className="absolute top-1/2 h-3 -translate-y-1/2 rounded-[3px]"
                style={{ left: pct(e.m0), width: `max(${daily ? 5 : 12}px, calc(${pct(e.m1)} - ${pct(e.m0)}))`, background: 'var(--c-ok)' }}
              />
            )),
          )}
          {lane(
            'symptoms',
            t('insights.tl.lane.symptoms', 'Symptoms'),
            daily
              ? dayRows.map((r, i) =>
                  r.symptoms
                    ? dayCell(
                        i,
                        <span
                          className="absolute left-1/2 top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full"
                          style={{ background: 'var(--c-info)' }}
                          title={`${dayMonth(r.date)}: ${r.symptoms}`}
                        />,
                        `s${i}`,
                      )
                    : null,
                )
              : events.symptoms.map((e) => dot(e.m, 'var(--c-info)', human(e.type))),
          )}
          {lane(
            'missed',
            t('insights.tl.lane.missed', 'Missed'),
            daily
              ? dayRows.map((r, i) =>
                  r.missed
                    ? dayCell(
                        i,
                        <span
                          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
                          style={{ background: 'var(--c-danger)', width: 8 + Math.min(r.missed, 3) * 2, height: 8 + Math.min(r.missed, 3) * 2 }}
                          title={`${dayMonth(r.date)}: ${r.missed}`}
                        />,
                        `x${i}`,
                      )
                    : null,
                )
              : events.missed.map((e) => dot(e.m, 'var(--c-danger)', t('insights.tl.missedTitle', 'Dose marked missed'))),
          )}
          {lane(
            'work',
            daily ? t('insights.tl.lane.workDays', 'Work days') : t('insights.tl.lane.work', 'Work'),
            shades.wk.map(([a, b]) => (
              <span
                key={a}
                className="absolute top-1/2 h-3.5 -translate-y-1/2 rounded-[4px] opacity-30"
                style={{ left: pct(a), width: `max(3px, calc(${pct(b)} - ${pct(a)}))`, background: 'var(--c-info)' }}
              />
            )),
          )}
        </div>

        {/* glucose, heart rate and SpO2 */}
        {built.map((b) => {
          const c = b.c
          if (!show[c.key]) return null
          const r = reads[c.key]
          const name = chartName(t, c.key)
          return (
            <div key={c.key}>
              <ChartHead
                color={c.color}
                name={name}
                unit={chartUnit(c.key)}
                value={
                  r.value == null
                    ? t('insights.tl.noReadingShort', 'No reading')
                    : `${r.value.toFixed(c.digits)} ${chartUnit(c.key)}${daily ? ` ${t('insights.tl.dayAvgShort', 'day average')}` : ''}`
                }
                status={statusText(t, r, c.digits, hasBase)}
                tone={hasBase ? r.compare : 'unknown'}
                gauge={
                  <Gauge
                    min={b.lo}
                    max={b.hi}
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
                {yLabels(b.ticks, b.y, c.digits)}
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
                    {b.range && <path d={b.range} fill={c.color} opacity="0.16" />}
                    {b.band && <path d={b.band} fill={c.color} opacity={daily ? 0.07 : 0.13} />}
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
                    {b.trend && (
                      <path
                        d={b.trend.d}
                        fill="none"
                        stroke={c.color}
                        strokeWidth="2.2"
                        strokeDasharray="1 5"
                        strokeLinecap="round"
                        vectorEffect="non-scaling-stroke"
                      />
                    )}
                  </>,
                )}
                {r.value != null && (
                  <span
                    className="pointer-events-none absolute z-[1] h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-[2.5px] ring-card"
                    style={{ left: left(m), top: b.y(r.value), background: c.color }}
                  />
                )}
              </div>
            </div>
          )
        })}

        {/* blood pressure: the readings (top and bottom number), the fixed baseline, and in the daily views the drift */}
        {show.bp &&
          (() => {
            const sy = bp.map((r) => r.systolic)
            const di = bp.map((r) => r.diastolic)
            const bs = baseline.bpAvailable ? baseline.bpSystolic : null
            const [lo, hi] = domain([...sy, ...di, bs, baseline.bpDiastolic], 0.12)
            const h = 120
            const y = (v: number) => 8 + (1 - (v - lo) / (hi - lo)) * (h - 16)
            const tk = niceTicks(lo, hi, 3)
            const d = near ? near.reading.systolic - (bs ?? near.reading.systolic) : null
            const ad = d == null ? '' : String(Math.abs(Math.round(d)))
            const status = !near
              ? t('insights.tl.noBp', 'No blood pressure reading in this period')
              : bs == null || d == null
                ? t('insights.tl.noBaseline', 'No baseline yet')
                : d === 0
                  ? t('insights.tl.atBase', 'At baseline {{b}}', { b: bs })
                  : d > 0
                    ? t('insights.tl.aboveBase', '{{d}} above baseline {{b}}', { d: ad, b: bs })
                    : t('insights.tl.belowBase', '{{d}} below baseline {{b}}', { d: ad, b: bs })
            const value = near
              ? `${near.reading.systolic}/${near.reading.diastolic} mmHg, ${agoText(t, near.gap)} ${near.gap < 0 ? t('insights.tl.before', 'before') : t('insights.tl.after', 'after')}`
              : t('insights.tl.noReadingShort', 'No reading')
            const trend = daily
              ? trendPath(
                  dayRows.map((r) => r.systolic),
                  xb,
                  y,
                  3,
                )
              : null
            return (
              <div>
                <ChartHead
                  color={COLOR.bp}
                  name={chartName(t, 'bp')}
                  unit={t('insights.tl.bpUnit', 'mmHg')}
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
                      color={COLOR.bp}
                      label={`${chartName(t, 'bp')}: ${status}`}
                    />
                  }
                />
                <div className="relative">
                  {yLabels(tk, y, 0)}
                  {plot(
                    h,
                    <>
                      {tk.map((v) => (
                        <line
                          key={v}
                          x1="0"
                          x2={W}
                          y1={y(v)}
                          y2={y(v)}
                          stroke="var(--c-line)"
                          strokeWidth="1"
                          vectorEffect="non-scaling-stroke"
                          opacity="0.7"
                        />
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
                      {trend && (
                        <path
                          d={trend.d}
                          fill="none"
                          stroke={COLOR.bp}
                          strokeWidth="2.2"
                          strokeDasharray="1 5"
                          strokeLinecap="round"
                          vectorEffect="non-scaling-stroke"
                        />
                      )}
                    </>,
                  )}
                  {bp.map((r) => (
                    <span key={r.m} className="pointer-events-none absolute inset-0">
                      <span
                        className="absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card"
                        style={{ left: left(r.m), top: y(r.systolic), background: COLOR.bp }}
                      />
                      <span
                        className="absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card"
                        style={{ left: left(r.m), top: y(r.diastolic), background: 'var(--c-info)' }}
                      />
                    </span>
                  ))}
                </div>
              </div>
            )
          })()}

        {/* the time axis */}
        <div className={cn('relative mt-1 h-5', AXIS_PAD)} aria-hidden>
          <div className="relative h-full">
            {ticks.map((tk) => (
              <span
                key={tk.i}
                className="absolute top-0 whitespace-nowrap text-micro text-ink2"
                style={{ left: pct((tk.i + (tk.centre ? 0.5 : 0)) * DAY_MIN), transform: tk.centre ? 'translateX(-50%)' : 'translateX(2px)' }}
              >
                {tk.text}
              </span>
            ))}
          </div>
        </div>

        {/* the marker: a line over every chart, a handle above, and a surface that takes the drag */}
        <div className="pointer-events-none absolute inset-y-0 left-16 right-0">
          <div className="absolute inset-y-0 w-0 border-l-2 border-dashed border-ink opacity-70" style={{ left: pct(m) }} />
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
          className="absolute inset-y-0 left-16 right-0 cursor-col-resize rounded-card focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
          style={{ touchAction: 'pan-y' }}
        />
      </div>

      <div className="flex flex-col gap-1 text-sub text-ink2">
        <div className="flex flex-nowrap items-center gap-x-3 overflow-x-auto pb-1 text-micro">
          <span className="flex flex-none items-center gap-1 whitespace-nowrap">
            <span className="h-2.5 w-4 rounded-full bg-info opacity-20" aria-hidden />
            {t('insights.tl.legend.usual', 'Usual range')}
          </span>
          <span className="flex flex-none items-center gap-1 whitespace-nowrap">
            <span className="w-4 border-t-2 border-dashed border-ink opacity-70" aria-hidden />
            {t('insights.tl.legend.baseShort', 'Baseline')}
          </span>
          {daily && (
            <>
              <span className="flex flex-none items-center gap-1 whitespace-nowrap">
                <span className="w-4 border-t-[3px] border-dotted border-info" aria-hidden />
                {t('insights.tl.legend.trend', 'Trend')}
              </span>
              <span className="flex flex-none items-center gap-1 whitespace-nowrap">
                <span className="h-2.5 w-4 rounded-[3px] bg-info opacity-30" aria-hidden />
                {t('insights.tl.legend.lowHigh', 'Day’s low to high')}
              </span>
            </>
          )}
          <span className="flex flex-none items-center gap-1 whitespace-nowrap">
            <span className="w-4 border-t-[3px] border-info" aria-hidden />
            {t('insights.tl.legend.outside', 'Outside usual')}
          </span>
          {work.set && (
            <span className="flex flex-none items-center gap-1 whitespace-nowrap">
              <span className="h-2.5 w-3 rounded-[3px] bg-info opacity-25" aria-hidden />
              {daily ? t('insights.tl.legend.workDays', 'Work days') : t('insights.tl.legend.work', 'Work hours')}
            </span>
          )}
          {shades.night.length > 0 && (
            <span className="flex flex-none items-center gap-1 whitespace-nowrap">
              <span className="h-2.5 w-3 rounded-[3px] bg-well" aria-hidden />
              {t('insights.tl.legend.night', 'Night')}
            </span>
          )}
        </div>
        <p className="text-micro text-ink3">
          {baseline.source === 'before'
            ? t(
                'insights.tl.base.before',
                'Baseline: your average for each hour of the day over the 60 days before this period ({{from}} to {{to}}). Blood pressure: one fixed value.',
                { from: dayMonth(baseline.from), to: dayMonth(baseline.to) },
              )
            : baseline.source === 'start'
              ? t(
                  'insights.tl.base.start',
                  'Baseline: your average over the first 30 days of this period ({{from}} to {{to}}), as there is not enough before it. Blood pressure: one fixed value.',
                  { from: dayMonth(baseline.from), to: dayMonth(baseline.to) },
                )
              : t('insights.tl.base.period', 'Baseline: your average over this period. Blood pressure: one fixed value.')}
        </p>
        {!hasBase && <p>{t('insights.tl.noBaselineNote', 'Not enough days yet to work out your baseline. It needs about a week of readings.')}</p>}
        <p className="text-micro text-ink3">
          {t(
            'insights.tl.help',
            'Drag the marker, or click or tap anywhere on the charts. Arrow keys move it. The gauge on each chart shows your usual range as a bar, your baseline as a thin line, and the reading at the marker as a block.',
          )}
        </p>
      </div>
    </div>
  )
}

/**
 * "Against your baseline": for each of glucose, heart rate, SpO2 and blood pressure, the most recent days' average next to the baseline, how far apart they
 * are, and (in the 30 and 90 day views) which way the daily averages are drifting per week. Numbers and directions only: no reading is called better or worse.
 */
export function BaselineCompare({ data }: { data: InsightsTimeline }) {
  const { t } = useTranslation()
  const { compare, baseline, period } = data
  const daily = period.bucketMinutes >= DAY_MIN
  const recentWord =
    compare.recentDays === period.days
      ? t('insights.tl.cmp.thisPeriod', 'This period')
      : t('insights.tl.cmp.lastDays', 'Last {{n}} days', { n: compare.recentDays })
  const rows: { key: 'glucose' | 'heart' | 'spo2' | 'bp'; name: string; unit: string; digits: number }[] = [
    { key: 'glucose', name: t('insights.tl.glucose', 'Glucose'), unit: 'mmol/L', digits: 1 },
    { key: 'heart', name: t('insights.tl.heart', 'Heart rate'), unit: 'bpm', digits: 0 },
    { key: 'spo2', name: t('insights.tl.spo2', 'SpO2'), unit: '%', digits: 1 },
    { key: 'bp', name: t('insights.tl.bpTop', 'Blood pressure (top number)'), unit: 'mmHg', digits: 0 },
  ]
  return (
    <section
      className="flex flex-col gap-3 rounded-card border border-line bg-card p-4 shadow-lift"
      aria-label={t('insights.tl.cmp.title', 'Against your baseline')}
    >
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-h2 font-bold">{t('insights.tl.cmp.title', 'Against your baseline')}</h2>
        <span className="text-sub text-ink3">{recentWord}</span>
      </div>
      {!baseline.available ? (
        <p className="text-sub text-ink2">
          {t('insights.tl.noBaselineNote', 'Not enough days yet to work out your baseline. It needs about a week of readings.')}
        </p>
      ) : (
        <ul className="flex flex-col divide-y divide-line">
          {rows.map((r) => {
            const c = compare[r.key]
            const diff = c.recent != null && c.baseline != null ? c.recent - c.baseline : null
            const ad = diff == null ? null : Math.abs(diff).toFixed(r.digits)
            const same = ad != null && Number(ad) === 0
            const slope = daily && c.slopePerWeek != null ? c.slopePerWeek : null
            const sd = slope == null ? null : Math.abs(slope).toFixed(r.key === 'glucose' || r.key === 'bp' ? 1 : 2)
            return (
              <li key={r.key} className="flex items-start gap-3 py-2.5 first:pt-0 last:pb-0">
                <span
                  className={cn(
                    'mt-0.5 flex h-8 w-8 flex-none items-center justify-center rounded-full',
                    same || diff == null ? 'bg-well text-ink2' : 'bg-info-soft text-info',
                  )}
                  aria-hidden
                >
                  {diff == null || same ? <span className="h-0.5 w-3.5 rounded bg-current" /> : diff > 0 ? <ArrowUp size={18} /> : <ArrowDown size={18} />}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-baseline justify-between gap-x-2">
                    <span className="font-bold">{r.name}</span>
                    <span className="num font-bold">
                      {fmt(c.recent, r.digits)} <span className="text-micro font-normal text-ink3">{r.unit}</span>
                    </span>
                  </p>
                  <p className="text-sub text-ink2">
                    {diff == null || ad == null
                      ? t('insights.tl.cmp.none', 'Not enough readings to compare.')
                      : same
                        ? t('insights.tl.cmp.same', 'At your baseline of {{b}}.', { b: fmt(c.baseline, r.digits) })
                        : diff > 0
                          ? t('insights.tl.cmp.above', '{{d}} above your baseline of {{b}}.', { d: ad, b: fmt(c.baseline, r.digits) })
                          : t('insights.tl.cmp.below', '{{d}} below your baseline of {{b}}.', { d: ad, b: fmt(c.baseline, r.digits) })}
                  </p>
                  {slope != null && sd != null && (
                    <p className="text-micro text-ink3">
                      {Number(sd) === 0
                        ? t('insights.tl.cmp.flat', 'Daily average is steady across the period.')
                        : slope > 0
                          ? t('insights.tl.cmp.rising', 'Daily average rising about {{n}} a week.', { n: sd })
                          : t('insights.tl.cmp.falling', 'Daily average falling about {{n}} a week.', { n: sd })}
                    </p>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
      <p className="text-micro text-ink3">
        {baseline.source === 'before'
          ? t(
              'insights.tl.cmp.noteBefore',
              'Baseline: your average over the 60 days before this period. These are numbers from your own readings, not a verdict.',
            )
          : t(
              'insights.tl.cmp.noteStart',
              'Baseline: your average over the first 30 days of this period. These are numbers from your own readings, not a verdict.',
            )}
      </p>
    </section>
  )
}
