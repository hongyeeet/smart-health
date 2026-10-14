/**
 * Insights → Overview charts: glucose, heart rate, SpO2 and blood pressure on ONE shared time axis (time across, the reading up), with a marker the
 * person can drag (or move with the arrow keys) to read every chart at the same moment, and a fixed-size stats bar for that day: glucose, heart
 * rate, SpO2, blood pressure, steps, and the calories, sugar and salt eaten (or "not recorded"). Pills switch each chart and each log lane
 * (meals, exercise, symptoms, missed doses, work) on or off.
 *
 * 7 days is every half hour and shows the latest 7 days ("This week") or any other 7 days picked in a calendar. 30 and 90 days are one point a day;
 * the days that stood out (the highest and lowest 5% of daily glucose) are circled and can be opened as the 7 days ending on them.
 * The only reference line is the person's BASELINE: their average for each hour of the day over the 14 days before the period (blood pressure: one
 * fixed number). The words under each reading say how far it is above or below it; nothing is called good or bad. All numbers come from
 * GET /insights/timeline; this file only lays them out. Every block has a fixed height, so nothing moves while the marker moves or the data loads.
 */
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { create } from 'zustand'
import type { TFunction } from 'i18next'
import type { InsightsDays, InsightsTimeline } from '@/data/types'
import { cn } from '@/lib/cn'
import { dateLocale } from '@/lib/locale'
import { Segmented } from '@/ui/controls'
import { CaretLeft, CaretRight } from '@/ui/icons'
import { DAY_MIN, atWork, baselinePath, clockMin, domain, gapText, hourlyAt, isoWeekday, linePath, niceTicks, nearestBp } from './timelineMath'

const W = 1000
const AXIS = 'w-16'
const AXIS_PAD = 'pl-16'

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
  { key: 'glucose', height: 170, color: 'var(--c-info)', digits: 1, floor: 0 },
  { key: 'heart', height: 120, color: 'var(--c-danger)', digits: 0, floor: 0 },
  { key: 'spo2', height: 100, color: 'var(--c-brass)', digits: 1, ceil: 100 },
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
const addDays = (iso: string, n: number) => {
  const d = new Date(`${iso}T12:00:00`)
  d.setDate(d.getDate() + n)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v))
const fmt = (v: number | null | undefined, digits = 0) =>
  v == null ? '–' : v.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })

function agoText(t: TFunction, gap: number): string {
  const { h, min } = gapText(gap)
  if (h && min) return t('insights.tl.hm', '{{h}} h {{m}} min', { h, m: min })
  if (h) return t('insights.tl.h', '{{h}} h', { h })
  return t('insights.tl.m', '{{m}} min', { m: min })
}

/** "0.6 above baseline 10.5" (plain: no verdict, only the distance) */
function againstBaseline(t: TFunction, value: number | null, base: number | null, digits: number): string {
  if (value == null) return t('insights.tl.noReading', 'No reading at this moment')
  if (base == null) return t('insights.tl.noBaseline', 'No baseline yet')
  const d = value - base
  const ad = Math.abs(d).toFixed(digits)
  const b = base.toFixed(digits)
  if (Number(ad) === 0) return t('insights.tl.atBase', 'At baseline {{b}}', { b })
  return d > 0 ? t('insights.tl.aboveBase', '{{d}} above baseline {{b}}', { d: ad, b }) : t('insights.tl.belowBase', '{{d}} below baseline {{b}}', { d: ad, b })
}

function ChartHead({ color, name, unit, value, sub }: { color: string; name: string; unit: string; value: string; sub: string }) {
  return (
    <div className="mb-1 mt-3 flex h-11 items-center justify-between gap-x-3">
      <p className="flex min-w-0 items-center gap-2 font-bold">
        <span className="h-3 w-3 flex-none rounded-full" style={{ background: color }} aria-hidden />
        <span className="truncate">{name}</span>
        <span className="text-sub font-normal text-ink3">{unit}</span>
      </p>
      <div className="relative z-[3] min-w-0 bg-card pl-2 text-right">
        <p className="num truncate text-body font-bold leading-tight">{value}</p>
        <p className="truncate text-micro text-ink2">{sub}</p>
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
        'press flex min-h-10 flex-none items-center gap-1 whitespace-nowrap rounded-chip border px-2.5 text-[12px]',
        on ? 'border-line bg-card font-bold text-ink' : 'border-line bg-transparent text-ink3',
      )}
    >
      <span className="h-2 w-2 rounded-full" style={{ background: on ? color : 'transparent', boxShadow: `inset 0 0 0 1.5px ${color}` }} aria-hidden />
      {label}
    </button>
  )
}

/** A month grid (Monday first) to pick the LAST day of the 7 days to show. The picked 7 days are shaded; days outside the data cannot be picked. */
function WeekCalendar({
  selected,
  minEnd,
  maxEnd,
  earliest,
  onPick,
  onClose,
}: {
  selected: string
  minEnd: string
  maxEnd: string
  earliest: string
  onPick: (iso: string) => void
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [month, setMonth] = useState(() => selected.slice(0, 7))
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const out = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node) && !(e.target as HTMLElement).closest('[data-cal-toggle]')) onClose()
    }
    const esc = (e: globalThis.KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('mousedown', out)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', out)
      document.removeEventListener('keydown', esc)
    }
  }, [onClose])
  const [y, m] = month.split('-').map(Number) as [number, number]
  const first = new Date(y, m - 1, 1)
  const lead = (first.getDay() + 6) % 7
  const dim = new Date(y, m, 0).getDate()
  const from = addDays(selected, -6)
  const shift = (by: number) =>
    setMonth(() => {
      const d = new Date(y, m - 1 + by, 1)
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    })
  const canPrev = month > earliest.slice(0, 7)
  const canNext = month < maxEnd.slice(0, 7)
  const names = Array.from({ length: 7 }, (_, i) => new Date(2026, 0, 5 + i).toLocaleDateString(dateLocale('en-GB'), { weekday: 'short' }))
  return (
    <div
      ref={box}
      role="dialog"
      aria-label={t('insights.tl.calLabel', 'Choose another week')}
      className="absolute left-0 top-full z-30 mt-2 w-[21.5rem] max-w-full rounded-card border border-line bg-card p-3.5 shadow-lift"
    >
      <div className="flex h-10 items-center justify-between">
        <button
          type="button"
          disabled={!canPrev}
          onClick={() => shift(-1)}
          aria-label={t('insights.tl.prevMonth', 'Previous month')}
          className="press flex h-10 w-10 items-center justify-center rounded-full border border-line disabled:opacity-40"
        >
          <CaretLeft size={18} aria-hidden />
        </button>
        <p className="font-bold" aria-live="polite">
          {first.toLocaleDateString(dateLocale('en-GB'), { month: 'long', year: 'numeric' })}
        </p>
        <button
          type="button"
          disabled={!canNext}
          onClick={() => shift(1)}
          aria-label={t('insights.tl.nextMonth', 'Next month')}
          className="press flex h-10 w-10 items-center justify-center rounded-full border border-line disabled:opacity-40"
        >
          <CaretRight size={18} aria-hidden />
        </button>
      </div>
      <p className="mb-1.5 mt-1 text-micro leading-tight text-ink3">{t('insights.tl.calHelp', 'Pick the last day of the 7 days you want to see.')}</p>
      <div className="grid grid-cols-7 gap-0.5 text-center text-micro text-ink3">
        {names.map((n, i) => (
          <span key={i} className="flex h-6 items-center justify-center">
            {n}
          </span>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-0.5">
        {Array.from({ length: 42 }, (_, i) => {
          const dn = i - lead + 1
          if (dn < 1 || dn > dim) return <span key={i} className="h-10" />
          const iso = `${month}-${String(dn).padStart(2, '0')}`
          const ok = iso >= minEnd && iso <= maxEnd
          const inSel = iso >= from && iso <= selected
          const isEnd = iso === selected
          return (
            <button
              key={i}
              type="button"
              disabled={!ok}
              aria-pressed={isEnd}
              aria-label={new Date(`${iso}T12:00:00`).toLocaleDateString(dateLocale('en-GB'), { weekday: 'long', day: 'numeric', month: 'long' })}
              onClick={() => onPick(iso)}
              className={cn(
                'num flex h-10 items-center justify-center rounded-[10px] text-sub',
                isEnd ? 'bg-brand font-bold text-on-brand' : inSel ? 'rounded-[4px] bg-brand-soft text-ink' : ok ? 'text-ink hover:bg-well' : 'text-ink3/40',
              )}
            >
              {dn}
            </button>
          )
        })}
      </div>
      <div className="mt-2.5 flex items-center justify-between gap-2 text-micro text-ink3">
        <span>{t('insights.tl.calData', 'Data from {{a}} to {{b}}', { a: dayMonth(earliest), b: dayMonth(maxEnd) })}</span>
        <button type="button" onClick={() => onPick(maxEnd)} className="press min-h-8 font-bold text-brand">
          {t('insights.tl.backThis', 'Back to this week')}
        </button>
      </div>
    </div>
  )
}

/** The header, the date row, the switches, and the charts. */
export function OverviewTimeline({
  data,
  days,
  setDays,
  endIso,
  setEnd,
  openWeek,
  openDay,
}: {
  data: InsightsTimeline
  days: InsightsDays
  setDays: (d: InsightsDays) => void
  /** the last day of the 7 days shown; null for the latest 7 days ("This week") */
  endIso: string | null
  setEnd: (iso: string | null) => void
  /** from a one-point-a-day view: show the 7 days ending on this day */
  openWeek: (iso: string) => void
  /** open the day's own screen (D1) */
  openDay: (iso: string) => void
}) {
  const { t } = useTranslation()
  const [show, setShow] = useState<Record<PillKey, boolean>>(ALL_ON)
  const [cal, setCal] = useState(false)
  const flip = (k: PillKey) => setShow((s) => ({ ...s, [k]: !s[k] }))
  const daily = data.period.bucketMinutes >= DAY_MIN
  const { latest, earliest } = data.period
  const first = earliest ?? data.period.start
  const minEnd = addDays(first, 6)
  const curEnd = data.period.end
  const isLatest = endIso == null
  const stepWeek = (by: number) => {
    const e = addDays(curEnd, by)
    if (e >= latest) setEnd(null)
    else if (e >= minEnd) setEnd(e)
  }
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
  const arrow = 'press flex h-11 w-11 flex-none items-center justify-center rounded-full border border-line bg-card text-ink disabled:opacity-40'
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <button
            type="button"
            onClick={() => stepWeek(-7)}
            disabled={daily || addDays(curEnd, -7) < minEnd}
            aria-label={t('insights.tl.earlier', 'Earlier 7 days')}
            className={arrow}
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
              {t('insights.tl.latestData', 'Latest data, {{d}}.', { d: dayMonth(latest) })}{' '}
              {daily
                ? t('insights.tl.builtDaily', 'One point a day, built from your 5-minute timeline.')
                : t('insights.tl.builtHalf', 'Built from your 5-minute timeline, every half hour.')}
            </p>
          </div>
          <button type="button" onClick={() => stepWeek(7)} disabled={daily || isLatest} aria-label={t('insights.tl.later', 'Later 7 days')} className={arrow}>
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

      {/* one fixed-height row: this week and a calendar for another week (7 days), or what to do with the circled days (30 and 90 days) */}
      <div className="relative flex min-h-[3.5rem] items-center">
        {!daily ? (
          <div className="flex flex-wrap items-center gap-2.5">
            <button
              type="button"
              aria-pressed={isLatest}
              onClick={() => {
                setEnd(null)
                setCal(false)
              }}
              className={cn(
                'press flex min-h-[3.25rem] min-w-[11rem] flex-col justify-center rounded-[14px] border px-4 text-left',
                isLatest ? 'border-brand bg-brand text-on-brand' : 'border-line bg-card text-ink',
              )}
            >
              <span className="text-sub font-bold leading-tight">{t('insights.tl.thisWeek', 'This week')}</span>
              <span className="text-micro leading-tight opacity-80">{`${dayMonth(addDays(latest, -6))} – ${dayMonth(latest)}`}</span>
            </button>
            <button
              type="button"
              data-cal-toggle
              aria-expanded={cal}
              onClick={() => setCal((c) => !c)}
              className={cn(
                'press flex min-h-[3.25rem] min-w-[13.5rem] items-center gap-2.5 rounded-[14px] border px-4 text-left',
                !isLatest ? 'border-brand bg-brand text-on-brand' : 'border-line bg-card text-ink',
              )}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden
                className="flex-none"
              >
                <rect x="3" y="5" width="18" height="16" rx="3" />
                <path d="M8 3v4M16 3v4M3 10h18" />
              </svg>
              <span className="flex flex-col">
                <span className="text-sub font-bold leading-tight">
                  {!isLatest ? t('insights.tl.otherWeek', 'Showing another week') : t('insights.tl.chooseWeek', 'Choose another week')}
                </span>
                <span className="text-micro leading-tight opacity-80">
                  {!isLatest ? `${dayMonth(data.period.start)} – ${dayMonth(curEnd)}` : t('insights.tl.openCal', 'Open the calendar')}
                </span>
              </span>
            </button>
            {cal && (
              <WeekCalendar
                selected={curEnd}
                minEnd={minEnd}
                maxEnd={latest}
                earliest={first}
                onPick={(iso) => {
                  setEnd(iso >= latest ? null : iso)
                  setCal(false)
                }}
                onClose={() => setCal(false)}
              />
            )}
          </div>
        ) : (
          <DailyHint data={data} openWeek={openWeek} minEnd={minEnd} />
        )}
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

      <Plot key={`${days}:${data.period.start}:${data.period.end}`} data={data} show={show} openDay={openDay} />
    </div>
  )
}

/** The days that stood out in a one-point-a-day view: the highest and lowest 5% of daily glucose averages. */
function stoodOut(data: InsightsTimeline): Set<number> {
  const vals = data.dayRows.map((r) => r.glucose.avg).filter((v): v is number => v != null)
  const out = new Set<number>()
  if (vals.length < 20) return out
  const s = [...vals].sort((a, b) => a - b)
  const lo = s[Math.floor(s.length * 0.05)]!
  const hi = s[Math.ceil(s.length * 0.95) - 1]!
  data.dayRows.forEach((r, i) => {
    const g = r.glucose.avg
    if (g != null && (g > hi || g < lo)) out.add(i)
  })
  return out
}

/** The row above the pills in a 30 or 90 day view. The "open" button belongs to the day the marker is on, so the row reads from the marker (kept in the URL-free state of Plot) */
function DailyHint({ data, openWeek, minEnd }: { data: InsightsTimeline; openWeek: (iso: string) => void; minEnd: string }) {
  const { t } = useTranslation()
  const sel = usePicked((s) => s.day)
  const date = sel ?? data.dayRows[data.dayRows.length - 1]?.date ?? data.period.end
  const end = date < minEnd ? minEnd : date
  return (
    <div className="flex min-h-[3.25rem] w-full flex-wrap items-center gap-x-3 gap-y-1.5 rounded-[14px] bg-well px-4 py-1.5">
      <span className="h-3 w-3 flex-none rounded-full border-2 border-warn" aria-hidden />
      <span className="min-w-0 flex-1 basis-56 text-sub text-ink2">
        {t('insights.tl.hint', 'Circled days stood out from the rest. Pick a day, then open its week to see the detail.')}
      </span>
      <button type="button" onClick={() => openWeek(end)} className="press min-h-10 flex-none rounded-[12px] bg-brand px-3 text-btn-sm font-bold text-on-brand">
        {t('insights.tl.openWeek', 'Open {{a}} – {{b}} in 7 days', { a: dayMonth(addDays(end, -6)), b: dayMonth(end) })}
      </button>
    </div>
  )
}

// the day the marker is on in a one-point-a-day view, shared with the row above (a tiny store: the marker lives in Plot, the button in the header)
const usePicked = create<{ day: string | null; set: (d: string | null) => void }>((set) => ({ day: null, set: (day) => set({ day }) }))

function Plot({ data, show, openDay }: { data: InsightsTimeline; show: Record<PillKey, boolean>; openDay: (iso: string) => void }) {
  const { t } = useTranslation()
  const { period, series, baseline, events, work, bp, dayRows } = data
  const days = period.days
  const step = period.bucketMinutes
  const total = days * DAY_MIN
  const daily = step >= DAY_MIN
  const startIso = period.start

  // the marker opens on the latest meal logged (so that day's calories, sugar and salt are there to read); with no meal anywhere, on the latest glucose reading
  const open = (() => {
    const lastMeal = events.meals[events.meals.length - 1]
    if (lastMeal) return daily ? Math.floor(lastMeal.m / DAY_MIN) * DAY_MIN + DAY_MIN / 2 : lastMeal.m
    for (let k = series.glucose.length - 1; k >= 0; k--) if (series.glucose[k] != null) return k * step + step / 2
    return total - 1
  })()
  const [m, setM] = useState(() => clamp(open, 0, total - 1))
  const dragging = useRef(false)
  const setPicked = usePicked((s) => s.set)
  // one point a day: the marker sits on the middle of a day
  const setClamped = (v: number) => {
    const c = clamp(v, 0, total - 1)
    setM(daily ? Math.floor(c / DAY_MIN) * DAY_MIN + DAY_MIN / 2 : c)
  }
  const dayI = clamp(Math.floor(m / DAY_MIN), 0, days - 1)
  const row = dayRows[dayI]
  useEffect(() => {
    setPicked(daily ? (dayRows[dayI]?.date ?? null) : null)
    return () => setPicked(null)
  }, [dayI, daily, dayRows, setPicked])

  const x = (min: number) => (min / total) * W
  const xb = (k: number) => x(k * step + step / 2)
  const pct = (min: number) => `${(min / total) * 100}%`
  const left = (min: number) => `calc(4rem + (100% - 4rem) * ${min / total})`
  const flagged = useMemo(() => (daily ? stoodOut(data) : new Set<number>()), [data, daily])

  // ── the three line charts, built once per answer
  const built = useMemo(
    () =>
      CHARTS.map((c) => {
        const vals = series[c.key]
        const h = baseline[c.key]
        const du = baseline.daily[c.key]
        const lows = c.key === 'glucose' ? series.glucoseMin : c.key === 'heart' ? series.heartMin : series.spo2Min
        const highs = c.key === 'glucose' ? series.glucoseMax : c.key === 'heart' ? series.heartMax : series.spo2Max
        const [lo, hi] = domain([...(daily ? lows : vals), ...(daily ? highs : vals), ...h.mean, du.mean], 0.1, c.floor, c.ceil)
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
        const baseVal = (k: number) => (daily ? du.mean : hourlyAt(h.mean, (k * step + step / 2) % DAY_MIN))
        return {
          c,
          y,
          ticks: niceTicks(lo, hi, c.height > 150 ? 4 : 3),
          line: linePath(vals, xb, y),
          base: baseline.available ? baselinePath(h, days, step, x, y, du) : '',
          range,
          baseVal,
        }
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [data],
  )

  // ── shaded backgrounds: night (12 to 6 am) and work hours (7 days), weekends (30 and 90 days)
  const shades = useMemo(() => {
    const night: number[] = []
    const wk: [number, number][] = []
    const weekend: number[] = []
    const ws = clockMin(work.start)
    const we = clockMin(work.end)
    for (let d = 0; d < days; d++) {
      const iso = addDays(startIso, d)
      const wd = isoWeekday(iso)
      if (!daily) night.push(d * DAY_MIN)
      else if (wd >= 6) weekend.push(d)
      if (work.set && ws != null && we != null && work.days.includes(wd)) wk.push([d * DAY_MIN + (daily ? 0 : ws), d * DAY_MIN + (daily ? DAY_MIN : we)])
    }
    return { night, wk, weekend }
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
      {shades.weekend.map((d) => (
        <rect key={`e${d}`} x={x(d * DAY_MIN)} y={0} width={x(DAY_MIN)} height={h} fill="var(--c-well)" opacity="0.8" />
      ))}
      {show.work &&
        !daily &&
        shades.wk.map(([a, b]) => <rect key={`w${a}`} x={x(a)} y={0} width={x(b) - x(a)} height={h} fill="var(--c-info)" opacity="0.1" />)}
      {days <= 7 &&
        ticks.map(
          (tk) =>
            tk.i > 0 && (
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
  const label = (() => {
    const d = at(startIso, m)
    return daily ? dayShort(d) : `${dayShort(d)}, ${timeShort(d)}`
  })()
  const near = nearestBp(bp, m)
  const wd = isoWeekday(addDays(startIso, dayI))
  const wk = atWork(work, startIso, m)
  const chip = !work.set
    ? ''
    : work.days.includes(wd)
      ? !daily && wk === 'during'
        ? t('insights.tl.work.during', 'During work hours')
        : t('insights.tl.work.day', 'Work day')
      : wd >= 6
        ? t('insights.tl.work.weekend', 'Weekend')
        : t('insights.tl.work.off', 'Day off')

  // one light line for the day: meals, doses, symptoms
  const lightLine = row
    ? [
        row.meals
          ? row.meals === 1
            ? t('insights.tl.mealsOne', '1 meal logged')
            : t('insights.tl.mealsMany', '{{n}} meals logged', { n: row.meals })
          : t('insights.tl.noMeals', 'no meals logged'),
        ...(row.scheduled
          ? [
              row.missed
                ? row.missed === 1
                  ? t('insights.tl.dosesMissedOne', '1 dose missed')
                  : t('insights.tl.dosesMissedMany', '{{n}} doses missed', { n: row.missed })
                : t('insights.tl.allTaken', 'all doses taken'),
            ]
          : []),
        row.symptoms
          ? row.symptoms === 1
            ? t('insights.tl.symptomsOne', '1 symptom noted')
            : t('insights.tl.symptomsMany', '{{n}} symptoms noted', { n: row.symptoms })
          : t('insights.tl.noSymptoms', 'no symptoms'),
      ].join('  ·  ')
    : ''

  // ── moving the marker
  const surface = useRef<HTMLDivElement>(null)
  const fromEvent = (e: PointerEvent) => {
    const r = surface.current?.getBoundingClientRect()
    if (r && r.width > 0) setClamped(((e.clientX - r.left) / r.width) * total)
  }
  const jumpDay = (dir: 1 | -1) => setClamped(m + dir * DAY_MIN)
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'ArrowRight') setClamped(m + (daily ? DAY_MIN : 30))
    else if (e.key === 'ArrowLeft') setClamped(m - (daily ? DAY_MIN : 30))
    else if (e.key === 'PageDown' || e.key === 'ArrowUp') jumpDay(1)
    else if (e.key === 'PageUp' || e.key === 'ArrowDown') jumpDay(-1)
    else if (e.key === 'Home') setClamped(0)
    else if (e.key === 'End') setClamped(total - 1)
    else return
    e.preventDefault()
  }

  const lane = (key: PillKey, name: string, children: ReactNode) =>
    show[key] && (
      <div key={key} className="relative h-[22px]">
        <span className={cn('absolute left-0 top-0 flex h-full items-center whitespace-nowrap pr-2 text-[11px] text-ink2', AXIS)}>{name}</span>
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

  // ── the stats bar for the day under the marker: fixed cells, so nothing moves or spills as the marker moves
  const cell = (name: string, value: string, unit: string, note: string, warn = false) => (
    <div key={name} className="flex h-[4.25rem] min-w-0 flex-col justify-between rounded-[12px] bg-card px-2.5 py-1.5">
      <span className="truncate text-micro text-ink3">{name}</span>
      <span className="num truncate text-body font-bold leading-none">
        {value}
        {unit && value !== '–' && <span className="ml-1 text-micro font-normal text-ink3">{unit}</span>}
      </span>
      <span className={cn('flex items-center gap-1 truncate text-micro', warn ? 'text-warn' : 'text-ink3')}>
        {warn && <span aria-hidden>⚑</span>}
        <span className="truncate">{note}</span>
      </span>
    </div>
  )
  const rangeNote = (a: { min: number | null; max: number | null }, d = 0) =>
    a.min == null || a.max == null ? t('insights.tl.noData', 'no data') : `${fmt(a.min, d)}–${fmt(a.max, d)}`
  const ate = !!row && row.meals > 0
  const noFood = t('insights.tl.noMealsLogged', 'no meals logged')
  const notRecorded = t('insights.tl.notRecorded', 'not recorded')
  const avgWord = t('insights.tl.avgDay', 'avg')

  const bs = baseline.bpAvailable ? baseline.bpSystolic : null
  const bpVals = bp.flatMap((r) => [r.systolic, r.diastolic])
  const [bLo, bHi] = domain([...bpVals, bs, baseline.bpDiastolic], 0.12)
  const bH = 110
  const bY = (v: number) => 8 + (1 - (v - bLo) / (bHi - bLo)) * (bH - 16)
  const bTicks = niceTicks(bLo, bHi, 3)

  return (
    <div className="flex flex-col gap-3">
      <div className="flex h-[15.25rem] flex-col gap-2 rounded-card bg-well p-3" aria-live="off">
        <div className="flex h-9 items-center justify-between gap-2">
          <p className="flex min-w-0 items-center gap-2">
            <span className="truncate text-body font-bold">{label}</span>
            {chip && <span className="flex-none rounded-chip bg-info-soft px-2.5 py-0.5 text-sub font-bold text-info">{chip}</span>}
          </p>
          <div className="flex flex-none gap-1.5">
            <button
              type="button"
              onClick={() => jumpDay(-1)}
              disabled={m < DAY_MIN}
              className="press flex min-h-10 items-center gap-1 rounded-[12px] border border-line bg-card px-2.5 text-btn-sm font-bold disabled:opacity-40"
            >
              <CaretLeft size={16} aria-hidden /> {t('insights.tl.prevDay', 'Previous day')}
            </button>
            <button
              type="button"
              onClick={() => jumpDay(1)}
              disabled={m >= total - DAY_MIN}
              className="press flex min-h-10 items-center gap-1 rounded-[12px] border border-line bg-card px-2.5 text-btn-sm font-bold disabled:opacity-40"
            >
              {t('insights.tl.nextDay', 'Next day')} <CaretRight size={16} aria-hidden />
            </button>
            <button
              type="button"
              onClick={() => row && openDay(row.date)}
              className="press min-h-10 rounded-[12px] bg-brand px-3 text-btn-sm font-bold text-on-brand"
            >
              {t('insights.tl.openDay', 'Open this day')}
            </button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
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
          {!ate
            ? cell(t('insights.tl.calories', 'Calories'), '–', '', noFood)
            : row?.kcal == null
              ? cell(t('insights.tl.calories', 'Calories'), '–', '', notRecorded, true)
              : cell(t('insights.tl.calories', 'Calories'), fmt(row.kcal), 'kcal', t('insights.tl.estimated', 'estimated'))}
          {!ate
            ? cell(t('insights.tl.sugar', 'Sugar'), '–', '', noFood)
            : row?.sugarG == null
              ? cell(t('insights.tl.sugar', 'Sugar'), '–', '', notRecorded, true)
              : cell(t('insights.tl.sugar', 'Sugar'), fmt(row.sugarG), 'g', t('insights.tl.fromMeals', 'from your meals'))}
          {!ate
            ? cell(t('insights.tl.salt', 'Salt'), '–', '', noFood)
            : row?.sodiumMg == null
              ? cell(t('insights.tl.salt', 'Salt'), '–', '', notRecorded, true)
              : cell(t('insights.tl.salt', 'Salt'), fmt(row.sodiumMg), 'mg', t('insights.tl.sodium', 'as sodium'))}
        </div>
        <p className="flex h-6 items-center truncate text-sub text-ink2">{lightLine}</p>
      </div>

      <div className="relative">
        <div className="flex flex-col pb-1">
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
              : events.meals.map((e) => dot(e.m, 'var(--c-brass)', `${human(e.type)}${e.food ? `: ${e.food}` : ''}`)),
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
          const k = clamp(Math.floor(m / step), 0, series[c.key].length - 1)
          const v = series[c.key][k] ?? null
          const base = baseline.available ? b.baseVal(k) : null
          const name = chartName(t, c.key)
          return (
            <div key={c.key}>
              <ChartHead
                color={c.color}
                name={name}
                unit={chartUnit(c.key)}
                value={
                  v == null
                    ? t('insights.tl.noReadingShort', 'No reading')
                    : `${v.toFixed(c.digits)} ${chartUnit(c.key)}${daily ? ` ${t('insights.tl.dayAvgShort', 'day average')}` : ''}`
                }
                sub={againstBaseline(t, v, base, c.digits)}
              />
              <div className="relative">
                {yLabels(b.ticks, b.y, c.digits)}
                {plot(
                  c.height,
                  <>
                    {b.ticks.map((tv) => (
                      <line
                        key={tv}
                        x1="0"
                        x2={W}
                        y1={b.y(tv)}
                        y2={b.y(tv)}
                        stroke="var(--c-line)"
                        strokeWidth="1"
                        vectorEffect="non-scaling-stroke"
                        opacity="0.7"
                      />
                    ))}
                    {b.range && <path d={b.range} fill={c.color} opacity="0.15" />}
                    {b.base && (
                      <path
                        d={b.base}
                        fill="none"
                        stroke="var(--c-ink)"
                        strokeWidth="1.6"
                        strokeDasharray="6 4"
                        opacity="0.75"
                        vectorEffect="non-scaling-stroke"
                      />
                    )}
                    {b.line && (
                      <path
                        d={b.line}
                        fill="none"
                        stroke={c.color}
                        strokeWidth="2.2"
                        strokeLinejoin="round"
                        strokeLinecap="round"
                        vectorEffect="non-scaling-stroke"
                      />
                    )}
                  </>,
                )}
                {v != null && (
                  <span
                    className="pointer-events-none absolute z-[1] h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-[2.5px] ring-card"
                    style={{ left: left(m), top: b.y(v), background: c.color }}
                  />
                )}
                {c.key === 'glucose' &&
                  daily &&
                  [...flagged].map((i) => {
                    const g = series.glucose[i]
                    return g == null ? null : (
                      <span
                        key={i}
                        className="pointer-events-none absolute h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-warn"
                        style={{ left: left(i * DAY_MIN + DAY_MIN / 2), top: b.y(g) }}
                        aria-hidden
                      />
                    )
                  })}
              </div>
            </div>
          )
        })}

        {/* blood pressure: the readings (top and bottom number) and the fixed baseline */}
        {show.bp && (
          <div>
            <ChartHead
              color={COLOR.bp}
              name={chartName(t, 'bp')}
              unit={t('insights.tl.bpUnit', 'mmHg')}
              value={
                near
                  ? `${near.reading.systolic}/${near.reading.diastolic} mmHg${daily ? '' : `, ${agoText(t, near.gap)} ${near.gap < 0 ? t('insights.tl.before', 'before') : t('insights.tl.after', 'after')}`}`
                  : t('insights.tl.noReadingShort', 'No reading')
              }
              sub={near ? againstBaseline(t, near.reading.systolic, bs, 0) : t('insights.tl.noBp', 'No blood pressure reading in this period')}
            />
            <div className="relative">
              {yLabels(bTicks, bY, 0)}
              {plot(
                bH,
                <>
                  {bTicks.map((tv) => (
                    <line
                      key={tv}
                      x1="0"
                      x2={W}
                      y1={bY(tv)}
                      y2={bY(tv)}
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
                      y1={bY(bs)}
                      y2={bY(bs)}
                      stroke="var(--c-ink)"
                      strokeWidth="1.6"
                      strokeDasharray="6 4"
                      opacity="0.75"
                      vectorEffect="non-scaling-stroke"
                    />
                  )}
                  {bp.map((r) => (
                    <line
                      key={`s${r.m}`}
                      x1={x(r.m)}
                      x2={x(r.m)}
                      y1={bY(r.systolic)}
                      y2={bY(r.diastolic)}
                      stroke="var(--c-line)"
                      strokeWidth="2"
                      vectorEffect="non-scaling-stroke"
                    />
                  ))}
                </>,
              )}
              {bp.map((r) => (
                <span key={r.m} className="pointer-events-none absolute inset-0">
                  <span
                    className="absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card"
                    style={{ left: left(r.m), top: bY(r.systolic), background: COLOR.bp }}
                  />
                  <span
                    className="absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card"
                    style={{ left: left(r.m), top: bY(r.diastolic), background: 'var(--c-info)' }}
                  />
                </span>
              ))}
            </div>
          </div>
        )}

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
          <div className="absolute inset-y-0 z-[2] w-0 border-l-2 border-dashed border-ink opacity-65" style={{ left: pct(m) }} />
          <div
            className="absolute -top-3 z-[2] flex h-[26px] w-[26px] -translate-x-1/2 items-center justify-center rounded-full bg-ink text-canvas shadow-lift"
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
          aria-valuetext={`${label}. ${againstBaseline(t, series.glucose[clamp(Math.floor(m / step), 0, series.glucose.length - 1)] ?? null, baseline.available ? (built[0]?.baseVal(clamp(Math.floor(m / step), 0, series.glucose.length - 1)) ?? null) : null, 1)}`}
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
          className="absolute inset-y-0 left-16 right-0 z-[1] cursor-col-resize rounded-card focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
          style={{ touchAction: 'pan-y' }}
        />
      </div>

      {/* one short line: what the dashed line is, what the shading is, what a circle is */}
      <div className="flex h-6 flex-nowrap items-center gap-x-4 overflow-x-auto whitespace-nowrap pl-16 text-micro text-ink2">
        <span className="flex flex-none items-center gap-1.5">
          <span className="w-5 border-t-2 border-dashed border-ink opacity-75" aria-hidden />
          {daily
            ? period.days >= 90
              ? t('insights.tl.legend.base90', 'Baseline: average of the first 14 days')
              : t('insights.tl.legend.baseDaily', 'Baseline: average of the 14 days before')
            : t('insights.tl.legend.baseHourly', 'Baseline: average of the 14 days before, hour by hour')}
        </span>
        <span className="flex flex-none items-center gap-1.5">
          <span className={cn('h-2.5 w-4 rounded-[3px]', daily ? 'bg-well' : 'bg-info opacity-30')} aria-hidden />
          {daily
            ? t('insights.tl.legend.weekends', 'Weekends')
            : t('insights.tl.legend.workHours', 'Work hours {{s}} to {{e}}', { s: work.start ?? '', e: work.end ?? '' })}
        </span>
        {daily && (
          <span className="flex flex-none items-center gap-1.5">
            <span className="h-3 w-3 rounded-full border-2 border-warn" aria-hidden />
            {t('insights.tl.legend.stood', 'Stood out')}
          </span>
        )}
      </div>
    </div>
  )
}

/** A tiny line of the period's daily values with the baseline as a dashed line: the shape shows whether the readings sit above, below or drift away from it. */
function Spark({ values, base, label }: { values: (number | null)[]; base: number | null; label: string }) {
  const pts = values.map((v, i) => (v == null ? null : ([i, v] as const))).filter((p): p is readonly [number, number] => p != null)
  if (pts.length < 2) return <span className="block h-7 w-16 flex-none" aria-hidden />
  const all = [...pts.map((p) => p[1]), ...(base == null ? [] : [base])]
  const lo = Math.min(...all)
  const hi = Math.max(...all)
  const span = hi - lo || 1
  const w = 64
  const h = 28
  const x = (i: number) => 3 + (i / Math.max(1, values.length - 1)) * (w - 6)
  const y = (v: number) => 3 + (1 - (v - lo) / span) * (h - 6)
  const d = pts.map(([i, v], k) => `${k ? 'L' : 'M'}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join('')
  const last = pts[pts.length - 1]!
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="flex-none" role="img" aria-label={label}>
      {base != null && <line x1="2" x2={w - 2} y1={y(base)} y2={y(base)} stroke="var(--c-ink)" strokeWidth="1" strokeDasharray="3 3" opacity="0.55" />}
      <path d={d} fill="none" stroke="var(--c-brand)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={x(last[0])} cy={y(last[1])} r="2.6" fill="var(--c-brand)" />
    </svg>
  )
}

/**
 * "Against your baseline": for each of glucose, heart rate, SpO2 and blood pressure, a small graph of the period's daily values against the baseline (dashed),
 * the period's average, and how far it is from the baseline. Numbers and shapes only: no reading is called better or worse here.
 */
export function BaselineCompare({ data }: { data: InsightsTimeline }) {
  const { t } = useTranslation()
  const { compare, baseline, period, dayRows } = data
  const rows: { key: 'glucose' | 'heart' | 'spo2' | 'bp'; name: string; unit: string; digits: number; series: (number | null)[] }[] = [
    { key: 'glucose', name: t('insights.tl.glucose', 'Glucose'), unit: 'mmol/L', digits: 1, series: dayRows.map((r) => r.glucose.avg) },
    { key: 'heart', name: t('insights.tl.heart', 'Heart rate'), unit: 'bpm', digits: 0, series: dayRows.map((r) => r.heart.avg) },
    { key: 'spo2', name: t('insights.tl.spo2', 'SpO2'), unit: '%', digits: 1, series: dayRows.map((r) => r.spo2.avg) },
    { key: 'bp', name: t('insights.tl.bp', 'Blood pressure'), unit: 'mmHg', digits: 0, series: dayRows.map((r) => r.systolic) },
  ]
  return (
    <section
      className="flex flex-col gap-1 rounded-card border border-line bg-card px-3.5 pb-1.5 pt-3.5 shadow-lift"
      aria-label={t('insights.tl.cmp.title', 'Against your baseline')}
    >
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-body font-bold">{t('insights.tl.cmp.title', 'Against your baseline')}</h2>
        <span className="text-[11px] text-ink3">
          {period.days === 7 ? t('insights.tl.cmp.thisWeek', 'These 7 days') : t('insights.tl.cmp.thisPeriod', 'This period')}
        </span>
      </div>
      {!baseline.available ? (
        <p className="pb-2 text-sub text-ink2">
          {t('insights.tl.noBaselineNote', 'Not enough days yet to work out your baseline. It needs about a week of readings.')}
        </p>
      ) : (
        <ul className="flex flex-col">
          {rows.map((r) => {
            const c = compare[r.key]
            const v = c.period
            const diff = v != null && c.baseline != null ? v - c.baseline : null
            const ad = diff == null ? null : Math.abs(diff).toFixed(r.digits)
            const same = ad != null && Number(ad) === 0
            const note =
              diff == null || ad == null
                ? t('insights.tl.cmp.none', 'Not enough readings')
                : same
                  ? t('insights.tl.cmp.same', 'At baseline {{b}}', { b: fmt(c.baseline, r.digits) })
                  : diff > 0
                    ? t('insights.tl.cmp.above', '{{d}} above baseline {{b}}', { d: ad, b: fmt(c.baseline, r.digits) })
                    : t('insights.tl.cmp.below', '{{d}} below baseline {{b}}', { d: ad, b: fmt(c.baseline, r.digits) })
            return (
              <li key={r.key} className="flex min-h-[3.1rem] items-center gap-2.5 border-t border-line py-1.5 first:border-t-0">
                <div className="min-w-0 flex-1">
                  <p className="text-sub font-bold leading-tight">{r.name}</p>
                  <p className="truncate text-[11px] leading-tight text-ink2">{note}</p>
                </div>
                <Spark values={r.series} base={c.baseline} label={`${r.name}: ${note}`} />
                <div className="w-14 flex-none text-right">
                  <p className="num text-sub font-bold leading-tight">{fmt(v, r.digits)}</p>
                  <p className="text-[10px] leading-tight text-ink3">{r.unit}</p>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
