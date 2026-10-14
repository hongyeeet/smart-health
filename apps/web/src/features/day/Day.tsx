/**
 * D1, "Your day": one day opened from Insights (the Overview's "Open this day"), Home and Log. A copy of the approved design:
 *   - Health score: glucose, heart rate, SpO2, blood pressure, steps and doses, each coloured against the person's own baseline (the 14 days before);
 *   - Food today: calories, carbs, sugar and salt in one card;
 *   - "Glucose rises after meals": a card per meal (the rise and the peak); picking one jumps the marker to the peak and shades meal to peak on every chart;
 *   - lanes (meals, medicines, symptoms, exercise), then the glucose chart and, one at a time (tabs), heart rate, SpO2, blood pressure and steps;
 *   - Logged items, and Ideas for tomorrow (a lighter meal from the person's own history; a walk when no exercise was logged).
 * Everything comes from GET /insights/day. The words say how far a reading is from the baseline; no reading is called good or bad.
 */
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from 'react'
import { create } from 'zustand'
import { Navigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useGo } from '@/app/navigation'
import { href } from '@/app/routeIds'
import { useInsightsDay } from '@/data/hooks'
import type { InsightsDay } from '@/data/types'
import { cn } from '@/lib/cn'
import { dateLocale } from '@/lib/locale'
import { Screen } from '@/ui/layout'
import { Alert, Button, EmptyState, Skeleton } from '@/ui/primitives'
import { CalendarBlank, CaretLeft, CaretRight, ForkKnife, PersonSimpleWalk } from '@/ui/icons'
import { GradeTile } from '@/features/insights/HealthOverview'
import { grade, KEY_LEVELS, TONE } from '@/features/insights/healthGrade'
import { domain, hourlyAt, linePath, niceTicks } from '@/features/insights/timelineMath'
import { useDayDates } from './api'

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/
const W = 1000
const N = 288
const AXIS = 'w-14'
const AXIS_PAD = 'pl-14'

type Tab = 'heart' | 'spo2' | 'bp' | 'steps'
const COLOR = { glucose: 'var(--c-info)', heart: 'var(--c-danger)', spo2: 'var(--c-brass)', bp: 'var(--c-warn)', steps: 'var(--c-brand)' }
const human = (s: string) => {
  const x = s.replace(/_/g, ' ').trim()
  return x.charAt(0).toUpperCase() + x.slice(1)
}
const clock = (m: number) =>
  new Date(2000, 0, 1, Math.floor(m / 60) % 24, Math.floor(m % 60)).toLocaleTimeString(dateLocale('en-US'), { hour: 'numeric', minute: '2-digit' })
const fmt = (v: number | null | undefined, d = 0) => (v == null ? '–' : v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }))
const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v))
const longDate = (iso: string) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString(dateLocale('en-GB'), { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })
const mean = (a: (number | null)[]) => {
  const p = a.filter((v): v is number => v != null)
  return p.length ? p.reduce((x, y) => x + y, 0) / p.length : null
}

/** D1: opening the day with no date goes to the latest day with data, the same rule as Insights. */
export function Day() {
  const { date = '' } = useParams()
  const go = useGo()
  const { t } = useTranslation()
  const dates = useDayDates(90)
  const valid = DATE_RE.test(date)
  const day = useInsightsDay(date, valid)
  if (!date && dates.data) return <Navigate to={href('D1', { date: dates.data.latestDate })} replace />
  const latest = dates.data?.latestDate

  return (
    <Screen wide>
      <header className="flex flex-wrap items-center gap-3 pb-1 pt-1">
        <button
          type="button"
          onClick={() => go('C1')}
          className="press flex min-h-10 items-center gap-1 rounded-[12px] border border-line bg-card px-3 text-btn-sm font-bold"
        >
          <CaretLeft size={16} aria-hidden /> {t('day.backWeek', 'Back to your week')}
        </button>
        <h1 className="font-serif text-h1 font-medium">{t('day.title', 'Your day')}</h1>
      </header>

      {!valid && (
        <EmptyState
          icon={CalendarBlank}
          action={
            latest && (
              <Button variant="secondary" onClick={() => go('D1', { params: { date: latest }, replace: true })}>
                {t('day.seeLatest', 'See your latest day')}
              </Button>
            )
          }
        >
          {t('day.badDate', 'That is not a date we can open.')}
        </EmptyState>
      )}
      {valid && day.isPending && <Skeleton className="h-[60rem]" />}
      {valid && day.isError && (
        <Alert tone="warn" title={t('day.loadErrorTitle', 'This day did not load')}>
          {t('day.loadErrorBody', 'Check the connection and try again.')}
        </Alert>
      )}
      {day.data && !day.data.hasData && (
        <>
          <DateRow data={day.data} onMove={(d) => go('D1', { params: { date: d } })} />
          <EmptyState icon={CalendarBlank}>
            {t('day.empty', 'Nothing is recorded for this day. Glucose, meals, medicines and workouts show here once they are logged.')}
          </EmptyState>
        </>
      )}
      {day.data?.hasData && <DayBody key={day.data.date} data={day.data} onMove={(d) => go('D1', { params: { date: d } })} go={go} />}
    </Screen>
  )
}

function DateRow({ data, onMove }: { data: InsightsDay; onMove: (iso: string) => void }) {
  const { t } = useTranslation()
  const arrow = 'press flex h-11 w-11 flex-none items-center justify-center rounded-full border border-line bg-card text-ink disabled:opacity-40'
  const wd = data.weekday
  const chip = !data.workSet
    ? ''
    : data.workDays.includes(wd)
      ? t('day.workDay', 'Work day')
      : wd >= 6
        ? t('insights.tl.work.weekend', 'Weekend')
        : t('insights.tl.work.off', 'Day off')
  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        disabled={!data.prevDate}
        onClick={() => data.prevDate && onMove(data.prevDate)}
        aria-label={t('day.prevAria', 'Previous day with data')}
        className={arrow}
      >
        <CaretLeft size={20} aria-hidden />
      </button>
      <div className="min-w-0">
        <p className="flex flex-wrap items-center gap-2 text-h2 font-bold leading-tight" aria-live="polite">
          {longDate(data.date)}
          {chip && <span className="rounded-chip bg-info-soft px-2.5 py-0.5 text-sub font-bold text-info">{chip}</span>}
        </p>
        <p className="text-sub text-ink3">{t('day.sub', 'From your 5-minute timeline and what you logged.')}</p>
      </div>
      <button
        type="button"
        disabled={!data.nextDate}
        onClick={() => data.nextDate && onMove(data.nextDate)}
        aria-label={t('day.nextAria', 'Next day with data')}
        className={arrow}
      >
        <CaretRight size={20} aria-hidden />
      </button>
    </div>
  )
}

function DayBody({ data, onMove, go }: { data: InsightsDay; onMove: (iso: string) => void; go: ReturnType<typeof useGo> }) {
  const { t } = useTranslation()
  const reset = usePick((s) => s.set)
  useEffect(() => {
    reset(null)
    return () => reset(null)
  }, [data.date, reset])
  const tot = data.totals
  const base = data.baseline
  const ok = base.available
  const gBase = ok ? mean(base.glucose) : null
  const hBase = ok ? mean(base.heart) : null
  const sBase = ok ? mean(base.spo2) : null
  const bp0 = data.bp[0]
  const dosePct = tot.dosesScheduled ? Math.round((100 * tot.dosesTaken) / tot.dosesScheduled) : null
  const tiles = [
    {
      kind: 'glucose' as const,
      label: t('day.tile.glucose', 'Glucose, day average'),
      value: fmt(tot.glucose.avg, 1),
      unit: tot.glucose.avg != null ? 'mmol/L' : undefined,
      g: grade('glucose', tot.glucose.avg, gBase),
    },
    {
      kind: 'heart' as const,
      label: t('day.tile.heart', 'Heart rate, day average'),
      value: fmt(tot.heart.avg),
      unit: tot.heart.avg != null ? 'bpm' : undefined,
      g: grade('heart', tot.heart.avg, hBase),
    },
    {
      kind: 'spo2' as const,
      label: t('day.tile.spo2', 'SpO2, day average'),
      value: fmt(tot.spo2.avg, 1),
      unit: tot.spo2.avg != null ? '%' : undefined,
      g: grade('spo2', tot.spo2.avg, sBase),
    },
    {
      kind: 'bp' as const,
      label: t('day.tile.bp', 'Blood pressure'),
      value: bp0 ? `${bp0.systolic}/${bp0.diastolic}` : '–',
      g: grade('bp', bp0?.systolic ?? null, ok ? base.bpSystolic : null),
    },
    { kind: 'steps' as const, label: t('day.tile.steps', 'Steps'), value: fmt(tot.steps), g: grade('steps', tot.steps, ok ? base.stepsPerDay : null) },
    {
      kind: 'doses' as const,
      label: t('day.tile.doses', 'Doses taken'),
      value: tot.dosesScheduled ? `${tot.dosesTaken} of ${tot.dosesScheduled}` : '–',
      g: grade('doses', dosePct, null),
    },
  ]
  const keyWords = [t('insights.ho.key0', 'In baseline'), t('insights.ho.key1', 'Slightly off'), t('insights.ho.key2', 'Off'), t('insights.ho.key3', 'Far off')]
  const ate = tot.meals > 0
  const food = (v: number | null, unit: string, label: string) => (
    <div key={label} className="flex min-w-0 flex-col justify-center rounded-[12px] bg-well px-3 py-2.5">
      <span className="num flex items-baseline gap-1 whitespace-nowrap text-lg font-bold leading-tight">
        {v == null ? '–' : fmt(v)}
        {v != null && <span className="text-[11px] font-normal text-ink3">{unit}</span>}
      </span>
      <span className="text-[11px] leading-tight text-ink2">{label}</span>
      {v == null && (
        <span className="text-[10px] leading-tight text-warn">
          {ate ? `⚑ ${t('insights.tl.notRecorded', 'not recorded')}` : t('insights.tl.noMealsLogged', 'no meals logged')}
        </span>
      )}
    </div>
  )

  return (
    <div className="flex flex-col gap-4">
      <DateRow data={data} onMove={onMove} />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20.75rem] lg:items-start lg:gap-6 [&>*]:min-w-0">
        <div className="flex flex-col gap-4">
          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_17rem]">
            <section className="flex flex-col gap-2.5 rounded-card border border-line bg-card p-4 shadow-lift" aria-label={t('day.score', 'Health score')}>
              <div className="flex items-baseline justify-between gap-2">
                <h2 className="text-body font-bold">{t('day.score', 'Health score')}</h2>
                <span className="text-sub text-ink3">{ok ? t('day.vsBase', 'against your 14-day baseline') : t('day.noBase', 'no baseline yet')}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 [[data-ts='2']_&]:grid-cols-1">
                {tiles.map((x) => (
                  <GradeTile key={x.kind} kind={x.kind} label={x.label} value={x.value} unit={x.unit} graded={x.g} />
                ))}
              </div>
              <ul className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-ink3">
                {KEY_LEVELS.map((l) => (
                  <li key={l} className="flex items-center gap-1">
                    <span className={cn('h-1.5 w-1.5 rounded-full', TONE[l].dot)} aria-hidden />
                    {keyWords[l]}
                  </li>
                ))}
              </ul>
            </section>
            <section className="flex flex-col gap-2.5 rounded-card border border-line bg-card p-4 shadow-lift" aria-label={t('day.food', 'Food today')}>
              <div className="flex items-baseline justify-between gap-2">
                <h2 className="text-body font-bold">{t('day.food', 'Food today')}</h2>
                <span className="text-sub text-ink3">{tot.meals === 1 ? t('day.oneMeal', '1 meal') : t('day.nMeals', '{{n}} meals', { n: tot.meals })}</span>
              </div>
              <div className="grid flex-1 grid-cols-2 gap-2">
                {food(tot.kcal, 'kcal', t('insights.tl.calories', 'Calories'))}
                {food(tot.carbsG, 'g', t('day.carbs', 'Carbs'))}
                {food(tot.sugarG, 'g', t('insights.tl.sugar', 'Sugar'))}
                {food(tot.sodiumMg, 'mg', t('day.salt', 'Salt (sodium)'))}
              </div>
            </section>
          </div>
          <ChartCard data={data} />
        </div>
        <aside className="flex flex-col gap-4">
          <LoggedItems data={data} />
          <Ideas data={data} />
          <div className="flex flex-col gap-1 px-1.5">
            <button type="button" onClick={() => go('C2')} className="press min-h-9 self-start text-sub font-bold text-brand underline">
              {t('day.glucoseInsights', 'Glucose insights')}
            </button>
            <button type="button" onClick={() => go('C3')} className="press min-h-9 self-start text-sub font-bold text-brand underline">
              {t('day.foodInsights', 'Food insights')}
            </button>
          </div>
        </aside>
      </div>
    </div>
  )
}

/** the moment under the marker, shared by the chart card and the list (a meal picked, and the minute of the marker) */
interface Pick {
  /** index of the meal whose rise is shaded */
  meal: number | null
  m: number
}

/** where the marker starts: on the peak of the biggest rise after a meal; with no rise, on the latest glucose reading */
function initialPick(data: InsightsDay): Pick {
  let biggest: number | null = null
  data.meals.forEach((x, i) => {
    if (x.riseMmol != null && x.peakM != null && (biggest == null || x.riseMmol > (data.meals[biggest]?.riseMmol ?? 0))) biggest = i
  })
  if (biggest != null) return { meal: biggest, m: data.meals[biggest]!.peakM! }
  for (let k = N - 1; k >= 0; k--) if (data.series.glucose[k] != null) return { meal: null, m: k * 5 }
  return { meal: null, m: 720 }
}

// the chart card and the logged items share the marker through this small store; it is cleared when another day opens
const usePick = create<{ pick: Pick | null; set: (p: Pick | null) => void }>((set) => ({ pick: null, set: (pick) => set({ pick }) }))

function ChartCard({ data }: { data: InsightsDay }) {
  const { t } = useTranslation()
  const shared = usePick((s) => s.pick)
  const set = usePick((s) => s.set)
  const pick = shared ?? initialPick(data)
  const m = pick.m
  const [tab, setTab] = useState<Tab>('heart')
  const dragging = useRef(false)
  const surface = useRef<HTMLDivElement>(null)
  const { series, baseline, meals } = data
  const pct = (min: number) => `${(min / 1440) * 100}%`
  const left = (min: number) => `calc(3.5rem + (100% - 3.5rem) * ${min / 1440})`
  const k = clamp(Math.floor(m / 5), 0, N - 1)
  const x = (min: number) => (min / 1440) * W
  const xb = (i: number) => x(i * 5 + 2.5)
  const sel = pick.meal != null ? meals[pick.meal] : null

  const gBaseAt = (i: number) => (baseline.available ? hourlyAt(baseline.glucose, i * 5 + 2.5) : null)
  const charts = useMemo(() => {
    const mk = (
      vals: (number | null)[],
      base: (number | null)[],
      height: number,
      opts: { floor?: number; ceil?: number; ticks: number; min?: number; max?: number },
    ) => {
      const [lo, hi] =
        opts.min != null && opts.max != null ? [opts.min, opts.max] : domain([...vals, ...(baseline.available ? base : [])], 0.1, opts.floor, opts.ceil)
      const pad = 8
      const y = (v: number) => pad + (1 - (v - lo) / (hi - lo)) * (height - pad * 2)
      const bl = baseline.available ? Array.from({ length: N }, (_, i) => hourlyAt(base, i * 5 + 2.5)) : []
      return { y, height, ticks: niceTicks(lo, hi, opts.ticks), line: linePath(vals, xb, y), base: bl.length ? linePath(bl, xb, y) : '' }
    }
    return {
      glucose: mk(series.glucose, baseline.glucose, 170, {
        floor: 3,
        ticks: 4,
        min: 3,
        max: Math.max(21, Math.ceil(Math.max(...series.glucose.filter((v): v is number => v != null), 0)) + 1),
      }),
      heart: mk(series.heart, baseline.heart, 110, { floor: 0, ticks: 3 }),
      spo2: mk(series.spo2, baseline.spo2, 110, { ceil: 100, ticks: 3 }),
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])
  const bpVals = data.bp.flatMap((r) => [r.systolic, r.diastolic])
  const [bLo, bHi] = domain([...bpVals, baseline.bpSystolic], 0.12)
  const bY = (v: number) => 8 + (1 - (v - bLo) / (bHi - bLo)) * 94
  const bTicks = niceTicks(bLo, bHi, 3)
  const maxSteps = Math.max(1, ...series.steps)

  // where the marker is: the time, and what was logged just before it
  const ctx = (() => {
    let last: (typeof meals)[number] | null = null
    for (const x2 of meals) if (x2.m <= m) last = x2
    if (!last) return t('day.beforeMeal', 'before the first meal')
    const gap = Math.round(m - last.m)
    return t('day.afterMeal', '{{ago}} after {{food}}', {
      ago: gap < 90 ? t('insights.tl.m', '{{m}} min', { m: gap }) : t('insights.tl.h', '{{h}} h', { h: Math.floor(gap / 60) }),
      food: last.food,
    })
  })()

  const fromEvent = (e: PointerEvent) => {
    const r = surface.current?.getBoundingClientRect()
    if (r && r.width > 0) set({ meal: pick.meal, m: clamp(((e.clientX - r.left) / r.width) * 1440, 0, 1439) })
  }
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'ArrowRight') set({ meal: pick.meal, m: clamp(m + 5, 0, 1439) })
    else if (e.key === 'ArrowLeft') set({ meal: pick.meal, m: clamp(m - 5, 0, 1439) })
    else if (e.key === 'Home') set({ meal: pick.meal, m: 0 })
    else if (e.key === 'End') set({ meal: pick.meal, m: 1439 })
    else return
    e.preventDefault()
  }

  const dsub = (v: number | null, b: number | null, d: number) => {
    if (v == null) return t('insights.tl.noReading', 'No reading at this moment')
    if (b == null) return t('insights.tl.noBaseline', 'No baseline yet')
    const diff = v - b
    const ad = Math.abs(diff).toFixed(d)
    if (Number(ad) === 0) return t('insights.tl.atBase', 'At baseline {{b}}', { b: b.toFixed(d) })
    return diff > 0
      ? t('insights.tl.aboveBase', '{{d}} above baseline {{b}}', { d: ad, b: b.toFixed(d) })
      : t('insights.tl.belowBase', '{{d}} below baseline {{b}}', { d: ad, b: b.toFixed(d) })
  }
  const gv = series.glucose[k] ?? null
  const hv = series.heart[k] ?? null
  const sv = series.spo2[k] ?? null
  let nearBp: (typeof data.bp)[number] | null = null
  for (const r of data.bp) if (!nearBp || Math.abs(r.m - m) < Math.abs(nearBp.m - m)) nearBp = r
  const stepsNow = series.steps.slice(Math.max(0, k - 6), k + 1).reduce((a, b) => a + b, 0)
  const second: Record<Tab, { name: string; val: string; sub: string }> = {
    heart: {
      name: t('insights.tl.heart', 'Heart rate'),
      val: hv == null ? t('insights.tl.noReadingShort', 'No reading') : `${hv} bpm`,
      sub: baseline.available ? dsub(hv, hourlyAt(baseline.heart, k * 5 + 2.5), 0) : t('insights.tl.noBaseline', 'No baseline yet'),
    },
    spo2: {
      name: t('insights.tl.spo2', 'SpO2'),
      val: sv == null ? t('insights.tl.noReadingShort', 'No reading') : `${sv.toFixed(1)} %`,
      sub: baseline.available ? dsub(sv, hourlyAt(baseline.spo2, k * 5 + 2.5), 1) : t('insights.tl.noBaseline', 'No baseline yet'),
    },
    bp: {
      name: t('insights.tl.bp', 'Blood pressure'),
      val: nearBp ? `${nearBp.systolic}/${nearBp.diastolic} mmHg` : t('insights.tl.noReadingShort', 'No reading'),
      sub: nearBp
        ? baseline.bpSystolic != null
          ? dsub(nearBp.systolic, baseline.bpSystolic, 0)
          : t('day.oneReading', 'one reading at {{time}}', { time: clock(nearBp.m) })
        : t('insights.tl.noBp', 'No blood pressure reading in this period'),
    },
    steps: {
      name: t('day.steps', 'Steps'),
      val: t('day.stepsDay', '{{n}} steps in the day', { n: fmt(data.totals.steps) }),
      sub: t('day.stepsNow', '{{n}} in the 30 minutes to {{time}}', { n: stepsNow, time: clock(m) }),
    },
  }
  const tabs: Tab[] = ['heart', 'spo2', 'bp', 'steps']

  const lane = (name: string, children: ReactNode, h = 24) => (
    <div className="relative" style={{ height: h }}>
      <span className={cn('absolute left-0 top-0 flex h-full items-center whitespace-nowrap pr-2 text-[11px] text-ink2', AXIS)}>{name}</span>
      <div className="absolute inset-y-0 left-14 right-0">{children}</div>
    </div>
  )
  const grid = (h: number, ticks: number[], y: (v: number) => number) => (
    <>
      {[3, 6, 9, 12, 15, 18, 21].map((hr) => (
        <line key={hr} x1={x(hr * 60)} x2={x(hr * 60)} y1={0} y2={h} stroke="var(--c-line)" strokeWidth="1" vectorEffect="non-scaling-stroke" opacity="0.6" />
      ))}
      {ticks.map((tv) => (
        <line key={tv} x1="0" x2={W} y1={y(tv)} y2={y(tv)} stroke="var(--c-line)" strokeWidth="1" vectorEffect="non-scaling-stroke" opacity="0.7" />
      ))}
      {sel && sel.peakM != null && <rect x={x(sel.m)} y={0} width={Math.max(0, x(sel.peakM) - x(sel.m))} height={h} fill="var(--c-brand)" opacity="0.1" />}
    </>
  )
  const plot = (h: number, children: ReactNode, ticks: number[], y: (v: number) => number, digits: number) => (
    <div className={cn('relative', AXIS_PAD)}>
      {ticks.map((tv) => (
        <span key={tv} className={cn('num absolute z-[1] -translate-y-1/2 pr-2 text-right text-[11px] text-ink3', AXIS)} style={{ top: y(tv), left: 0 }}>
          {tv.toFixed(digits)}
        </span>
      ))}
      <svg viewBox={`0 0 ${W} ${h}`} preserveAspectRatio="none" className="block w-full" style={{ height: h }} aria-hidden>
        {grid(h, ticks, y)}
        {children}
      </svg>
    </div>
  )
  const baseLine = (d: string) =>
    d ? <path d={d} fill="none" stroke="var(--c-ink)" strokeWidth="1.6" strokeDasharray="6 4" opacity="0.75" vectorEffect="non-scaling-stroke" /> : null
  const live = (v: number | null, y: (v: number) => number, color: string) =>
    v == null ? null : (
      <span
        className="pointer-events-none absolute z-[1] h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-[2.5px] ring-card"
        style={{ left: left(m), top: y(v), background: color }}
      />
    )

  const hours = [0, 3, 6, 9, 12, 15, 18, 21, 24]
  const hourText = (h: number) => new Date(2000, 0, 1, h % 24, 0).toLocaleTimeString(dateLocale('en-US'), { hour: 'numeric' }).replace(':00', '')
  const rises = meals.map((x2, i) => ({ x2, i })).filter((r) => r.x2.riseMmol != null)
  const doseTone = (s: string) =>
    s === 'missed'
      ? { bg: 'bg-danger-soft', ring: 'border-danger text-danger', mark: '✕' }
      : s === 'late'
        ? { bg: 'bg-warn-soft', ring: 'border-warn text-warn', mark: '✓' }
        : { bg: 'bg-ok-soft', ring: 'border-ok text-ok', mark: '✓' }

  return (
    <section className="flex flex-col gap-3 rounded-card border border-line bg-card p-4 shadow-lift sm:px-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3">
        <h2 className="text-body font-bold">{t('day.rises', 'Glucose rises after meals')}</h2>
        <span className="text-sub text-ink3">{t('day.pickOne', 'Pick one to see it on the charts')}</span>
      </div>
      {rises.length > 0 && (
        <div className="grid grid-cols-2 gap-2.5 md:grid-cols-4">
          {rises.map(({ x2, i }) => {
            const on = pick.meal === i
            return (
              <button
                key={i}
                type="button"
                aria-pressed={on}
                onClick={() => set({ meal: i, m: x2.peakM ?? x2.m })}
                className={cn(
                  'press flex h-[4.5rem] min-w-0 flex-col justify-between rounded-[14px] border-[1.5px] px-3 py-2 text-left',
                  on ? 'border-brand bg-brand-soft' : 'border-line bg-canvas',
                )}
              >
                <span className="flex items-center justify-between gap-2 text-[12px] text-ink3">
                  <span>{clock(x2.m)}</span>
                  <span className="num font-bold text-ink">{`+${x2.riseMmol}${x2.peakMmol != null ? ` → ${x2.peakMmol}` : ''}`}</span>
                </span>
                <span className="truncate text-sub font-bold">{x2.food}</span>
              </button>
            )
          })}
        </div>
      )}
      <p className={cn('flex h-7 items-center gap-2.5 truncate text-sub text-ink2', AXIS_PAD)}>
        <span className="font-bold text-ink">{clock(m)}</span>
        <span className="truncate">{ctx}</span>
      </p>

      <div className="relative">
        {lane(
          t('insights.tl.lane.meals', 'Meals'),
          meals.map((x2, i) => (
            <span
              key={i}
              title={`${human(x2.type ?? '')}: ${x2.food}`}
              className={cn(
                'absolute top-px flex h-[22px] w-[22px] -translate-x-1/2 items-center justify-center rounded-full text-[11px] font-bold text-card',
                pick.meal === i ? 'bg-brand' : 'bg-brass',
              )}
              style={{ left: pct(x2.m) }}
            >
              {i + 1}
            </span>
          )),
        )}
        {lane(
          t('day.lane.medicines', 'Medicines'),
          data.doses.map((d, i) => {
            const tn = doseTone(d.status)
            return (
              <span
                key={i}
                title={`${d.name}: ${d.status}`}
                className={cn(
                  'absolute top-[3px] flex h-[18px] w-[18px] -translate-x-1/2 items-center justify-center rounded-full border-[1.5px] text-[10px] font-bold',
                  tn.bg,
                  tn.ring,
                )}
                style={{ left: pct(d.m) }}
              >
                {tn.mark}
              </span>
            )
          }),
        )}
        {lane(
          t('insights.tl.lane.symptoms', 'Symptoms'),
          data.symptoms.map((s, i) => (
            <span
              key={i}
              title={human(s.type)}
              className="absolute top-1.5 h-3 rounded-full bg-info"
              style={{ left: pct(s.m), width: `max(14px, calc(${pct(s.m1 + 5)} - ${pct(s.m)}))` }}
            />
          )),
        )}
        {lane(
          t('insights.tl.lane.exercise', 'Exercise'),
          data.exercise.length ? (
            data.exercise.map((e, i) => (
              <span
                key={i}
                title={human(e.type)}
                className="absolute top-1.5 h-3 rounded-[3px] bg-ok"
                style={{ left: pct(e.m0), width: `max(12px, calc(${pct(e.m1)} - ${pct(e.m0)}))` }}
              />
            ))
          ) : (
            <span className="absolute left-1/2 top-0 flex h-full -translate-x-1/2 items-center text-[11px] text-ink3">
              {t('day.noExercise', 'none logged today')}
            </span>
          ),
        )}

        {/* glucose */}
        <div className="mb-1 mt-3 flex h-11 items-center justify-between gap-3">
          <p className="flex items-center gap-2 font-bold">
            <span className="h-3 w-3 rounded-full" style={{ background: COLOR.glucose }} aria-hidden />
            {t('insights.tl.glucose', 'Glucose')}
            <span className="text-sub font-normal text-ink3">mmol/L</span>
          </p>
          <div className="relative z-[3] min-w-0 bg-card pl-2 text-right">
            <p className="num text-body font-bold leading-tight">{gv == null ? t('insights.tl.noReadingShort', 'No reading') : `${gv.toFixed(1)} mmol/L`}</p>
            <p className="truncate text-micro text-ink2">{dsub(gv, gBaseAt(k), 1)}</p>
          </div>
        </div>
        <div className="relative">
          {plot(
            charts.glucose.height,
            <>
              {baseLine(charts.glucose.base)}
              <path
                d={charts.glucose.line}
                fill="none"
                stroke={COLOR.glucose}
                strokeWidth="2.2"
                strokeLinejoin="round"
                strokeLinecap="round"
                vectorEffect="non-scaling-stroke"
              />
            </>,
            charts.glucose.ticks,
            charts.glucose.y,
            0,
          )}
          {live(gv, charts.glucose.y, COLOR.glucose)}
          {rises.map(({ x2, i }) =>
            x2.peakM != null && x2.peakMmol != null ? (
              <span
                key={i}
                className="pointer-events-none absolute z-[1] -translate-x-1/2 -translate-y-full whitespace-nowrap rounded-[8px] bg-ink px-1.5 text-[11px] font-bold text-canvas"
                style={{ left: left(x2.peakM), top: charts.glucose.y(series.glucose[clamp(Math.floor(x2.peakM / 5), 0, N - 1)] ?? x2.peakMmol) - 6 }}
              >
                {`+${x2.riseMmol}`}
              </span>
            ) : null,
          )}
        </div>

        {/* the other readings, one at a time */}
        <div className="mb-1.5 mt-4 flex min-h-11 flex-wrap items-center justify-between gap-x-3 gap-y-1">
          <div role="tablist" aria-label={t('day.moreReadings', 'More readings')} className="flex flex-wrap gap-1.5">
            {tabs.map((tb) => (
              <button
                key={tb}
                type="button"
                role="tab"
                aria-selected={tab === tb}
                onClick={() => setTab(tb)}
                className={cn('press min-h-9 rounded-chip px-3.5 text-[13px]', tab === tb ? 'bg-brand font-bold text-on-brand' : 'bg-well text-ink2')}
              >
                {tb === 'steps' ? t('day.steps', 'Steps') : second[tb].name}
              </button>
            ))}
          </div>
          <div className="relative z-[3] min-w-0 bg-card pl-2 text-right">
            <p className="num text-body font-bold leading-tight">{second[tab].val}</p>
            <p className="truncate text-micro text-ink2">{second[tab].sub}</p>
          </div>
        </div>
        <div className="relative">
          {tab === 'heart' && (
            <>
              {plot(
                charts.heart.height,
                <>
                  {baseLine(charts.heart.base)}
                  <path
                    d={charts.heart.line}
                    fill="none"
                    stroke={COLOR.heart}
                    strokeWidth="2.2"
                    strokeLinejoin="round"
                    strokeLinecap="round"
                    vectorEffect="non-scaling-stroke"
                  />
                </>,
                charts.heart.ticks,
                charts.heart.y,
                0,
              )}
              {live(hv, charts.heart.y, COLOR.heart)}
            </>
          )}
          {tab === 'spo2' && (
            <>
              {plot(
                charts.spo2.height,
                <>
                  {baseLine(charts.spo2.base)}
                  <path
                    d={charts.spo2.line}
                    fill="none"
                    stroke={COLOR.spo2}
                    strokeWidth="2.2"
                    strokeLinejoin="round"
                    strokeLinecap="round"
                    vectorEffect="non-scaling-stroke"
                  />
                </>,
                charts.spo2.ticks,
                charts.spo2.y,
                0,
              )}
              {live(sv, charts.spo2.y, COLOR.spo2)}
            </>
          )}
          {tab === 'bp' && (
            <>
              {plot(
                110,
                <>
                  {baseline.bpSystolic != null && (
                    <line
                      x1="0"
                      x2={W}
                      y1={bY(baseline.bpSystolic)}
                      y2={baseline.bpSystolic == null ? 0 : bY(baseline.bpSystolic)}
                      stroke="var(--c-ink)"
                      strokeWidth="1.6"
                      strokeDasharray="6 4"
                      opacity="0.75"
                      vectorEffect="non-scaling-stroke"
                    />
                  )}
                  {data.bp.map((r, i) => (
                    <line
                      key={i}
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
                bTicks,
                bY,
                0,
              )}
              {data.bp.map((r, i) => (
                <span key={i} className="pointer-events-none absolute inset-0">
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
            </>
          )}
          {tab === 'steps' &&
            plot(
              110,
              <>
                {series.steps.map((v, i) =>
                  v ? (
                    <rect key={i} x={xb(i) - 1.6} y={110 - (v / maxSteps) * 104} width={3.2} height={(v / maxSteps) * 104} fill={COLOR.steps} opacity="0.75" />
                  ) : null,
                )}
              </>,
              [],
              () => 0,
              0,
            )}
        </div>

        <div className={cn('relative mt-1 h-5', AXIS_PAD)} aria-hidden>
          <div className="relative h-full">
            {hours.map((h) => (
              <span
                key={h}
                className="absolute top-0 whitespace-nowrap text-micro text-ink2"
                style={{ left: `${(h / 24) * 100}%`, transform: h === 0 ? undefined : h === 24 ? 'translateX(-100%)' : 'translateX(-50%)' }}
              >
                {h === 0 || h === 24 ? t('day.midnight', '12 am') : hourText(h)}
              </span>
            ))}
          </div>
        </div>

        {/* the marker */}
        <div className="pointer-events-none absolute inset-y-0 left-14 right-0">
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
          aria-label={t('day.markerLabel', 'Time marker')}
          aria-orientation="horizontal"
          aria-valuemin={0}
          aria-valuemax={1439}
          aria-valuenow={Math.round(m)}
          aria-valuetext={`${clock(m)}. ${dsub(gv, gBaseAt(k), 1)}`}
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
          className="absolute inset-y-0 left-14 right-0 z-[1] cursor-col-resize rounded-card focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
          style={{ touchAction: 'pan-y' }}
        />
      </div>
      <p className="flex h-6 items-center gap-2 whitespace-nowrap pl-14 text-micro text-ink2">
        <span className="w-5 border-t-2 border-dashed border-ink opacity-75" aria-hidden />
        {t('day.legendBase', 'Baseline: average of the 14 days before, hour by hour')}
      </p>
    </section>
  )
}

function LoggedItems({ data }: { data: InsightsDay }) {
  const { t } = useTranslation()
  const setShared = usePick((s) => s.set)
  const shared = usePick((s) => s.pick)
  const pick = shared ?? initialPick(data)
  type Row = { m: number; title: string; sub: string; dot: string; chip?: string; meal?: number }
  const rows: Row[] = []
  data.meals.forEach((x, i) =>
    rows.push({
      m: x.m,
      title: x.food,
      sub: [
        x.carbsG != null ? t('day.carbsG', '{{n}} g carbs', { n: fmt(x.carbsG) }) : null,
        x.sugarG != null ? t('day.sugarG', '{{n}} g sugar', { n: fmt(x.sugarG) }) : null,
        x.sodiumMg != null ? t('day.saltMg', '{{n}} mg salt', { n: fmt(x.sodiumMg) }) : null,
      ]
        .filter(Boolean)
        .join(' · '),
      dot: 'bg-brass',
      chip: x.riseMmol != null ? `+${x.riseMmol}` : undefined,
      meal: i,
    }),
  )
  data.doses.forEach((d) =>
    rows.push({
      m: d.m,
      title: d.name || t('day.dose', 'Dose'),
      sub: d.status === 'missed' ? t('day.missed', 'Marked missed') : d.status === 'late' ? t('day.takenLate', 'Taken late') : t('day.taken', 'Taken'),
      dot: d.status === 'missed' ? 'bg-danger' : d.status === 'late' ? 'bg-warn' : 'bg-ok',
    }),
  )
  data.symptoms.forEach((s) =>
    rows.push({
      m: s.m,
      title: human(s.type),
      sub: [
        s.severity != null ? t('day.strength', 'Strength {{n}} of 5', { n: s.severity }) : null,
        t('day.until', 'until {{time}}', { time: clock(s.m1 + 5) }),
      ]
        .filter(Boolean)
        .join(', '),
      dot: 'bg-info',
    }),
  )
  data.bp.forEach((b) => rows.push({ m: b.m, title: t('insights.tl.bp', 'Blood pressure'), sub: `${b.systolic}/${b.diastolic} mmHg`, dot: 'bg-warn' }))
  data.mood.forEach((b) =>
    rows.push({
      m: b.m,
      title: t('day.mood', 'Mood check-in'),
      sub: t('day.moodLine', 'Mood {{a}}, stress {{b}} of 5', { a: b.mood, b: b.stress ?? '–' }),
      dot: 'bg-ok',
    }),
  )
  data.exercise.forEach((e) => rows.push({ m: e.m0, title: human(e.type), sub: `${clock(e.m0)} – ${clock(e.m1)}`, dot: 'bg-ok' }))
  rows.sort((a, b) => a.m - b.m)
  return (
    <section className="flex flex-col rounded-card border border-line bg-card px-2 pb-2 pt-3.5 shadow-lift" aria-label={t('day.logged', 'Logged items')}>
      <div className="flex items-baseline justify-between gap-2 px-2.5 pb-1.5">
        <h2 className="text-body font-bold">{t('day.logged', 'Logged items')}</h2>
        <span className="text-sub text-ink3">{t('day.todayN', '{{n}} today', { n: rows.length })}</span>
      </div>
      {rows.length === 0 && <p className="px-2.5 pb-2 text-sub text-ink2">{t('day.nothingLogged', 'Nothing logged for this day.')}</p>}
      <ul className="flex flex-col">
        {rows.map((r, i) => {
          const on = r.meal != null && pick?.meal === r.meal
          return (
            <li key={i}>
              <button
                type="button"
                onClick={() => setShared({ meal: r.meal ?? pick?.meal ?? null, m: r.meal != null ? (data.meals[r.meal]?.peakM ?? r.m) : r.m })}
                className={cn('press flex min-h-[3.5rem] w-full items-center gap-2.5 rounded-[12px] px-2.5 py-2 text-left', on && 'bg-brand-soft')}
              >
                <span className="w-[3.4rem] flex-none whitespace-nowrap text-[12px] font-bold text-ink2">{clock(r.m)}</span>
                <span className={cn('h-2.5 w-2.5 flex-none rounded-full', r.dot)} aria-hidden />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sub font-bold leading-tight">{r.title}</span>
                  {r.sub && <span className="block text-[12px] leading-tight text-ink3">{r.sub}</span>}
                </span>
                {r.chip && <span className="flex-none rounded-[8px] bg-ink px-1.5 text-[12px] font-bold text-canvas">{r.chip}</span>}
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function Ideas({ data }: { data: InsightsDay }) {
  const { t } = useTranslation()
  const { swap, walk } = data.ideas
  const row = (icon: ReactNode, tone: string, body: ReactNode) => (
    <div className="flex items-start gap-3">
      <span className={cn('flex h-9 w-9 flex-none items-center justify-center rounded-full', tone)}>{icon}</span>
      <p className="text-sub leading-snug">{body}</p>
    </div>
  )
  return (
    <section className="flex flex-col gap-3 rounded-card border border-line bg-card p-4 shadow-lift" aria-label={t('day.ideas', 'Ideas for tomorrow')}>
      <h2 className="text-body font-bold">{t('day.ideas', 'Ideas for tomorrow')}</h2>
      {swap &&
        row(
          <ForkKnife size={18} aria-hidden />,
          'bg-brass-soft text-brass',
          <>
            <b>{t('day.swapHead', 'Swap a meal.')}</b>{' '}
            {t('day.swapBody', '{{to}} ({{toC}} g carbs) instead of {{from}} ({{fromC}} g carbs).', {
              to: swap.toFood,
              toC: fmt(swap.toCarbsG),
              from: swap.fromFood,
              fromC: fmt(swap.fromCarbsG),
            })}
          </>,
        )}
      {walk &&
        row(
          <PersonSimpleWalk size={18} aria-hidden />,
          'bg-ok-soft text-ok',
          <>
            <b>{t('day.walkHead', 'Add a short walk.')}</b> {t('day.walkNone', 'No exercise logged today.')}{' '}
            {walk.learned && walk.learned.lowerBy != null ? (
              <>
                {t('day.walkLearned', 'After evening walks, your morning glucose was {{n}} mmol/L lower', { n: walk.learned.lowerBy })}{' '}
                <span className="text-ink3">
                  {walk.learned.confirmed
                    ? t('day.youConfirmed', '(you confirmed this)')
                    : t('day.notConfirmed', '(noticed by Smart Health, not confirmed yet)')}
                </span>
              </>
            ) : (
              t('day.walkStart', 'A short walk after a meal is an easy way to start.')
            )}
          </>,
        )}
      {!swap && !walk && (
        <p className="text-sub text-ink2">{t('day.noIdeas', 'No ideas for this day. Keep logging meals and Smart Health will suggest lighter swaps.')}</p>
      )}
      <p className="text-[11px] leading-snug text-ink3">{t('day.ideasNote', 'Ideas from your own records, not medical advice.')}</p>
    </section>
  )
}
