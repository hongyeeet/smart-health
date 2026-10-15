/**
 * "Health overview" on Home: a 7-day LINE chart with tabs for Glucose, Steps, Calories and Heart rate, each in its own colour
 * (the tab, the line and the selected dot share it). The selected day has a tooltip with its date and value. Every day is a real
 * button (keyboard and screen reader). A day with no value is a dash and a break in the line: never a 0. The numbers are the same
 * daily values as the cards above.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import type { HomeOverview } from '@/data/types'
import { dateLocale } from '@/lib/locale'
import { cn } from '@/lib/cn'
import { Skeleton } from '@/ui/primitives'
import { defaultSelected } from './status'

type Metric = 'glucose' | 'steps' | 'calories' | 'heartRate'
const METRICS: Metric[] = ['glucose', 'steps', 'calories', 'heartRate']

/** one colour per series: text-* sets the line and dot colour (currentColor), bg-* the selected tab (white text stays readable on each) */
const COLOR: Record<Metric, { text: string; tab: string; dot: string }> = {
  glucose: { text: 'text-info', tab: 'bg-info', dot: 'bg-info' },
  steps: { text: 'text-brand', tab: 'bg-brand', dot: 'bg-brand' },
  calories: { text: 'text-warn', tab: 'bg-warn', dot: 'bg-warn' },
  heartRate: { text: 'text-danger', tab: 'bg-danger', dot: 'bg-danger' },
}

const tabName = (t: TFunction, m: Metric) =>
  m === 'glucose'
    ? t('home.chart.glucose', 'Glucose')
    : m === 'steps'
      ? t('home.chart.steps', 'Steps')
      : m === 'calories'
        ? t('home.chart.calories', 'Calories')
        : t('home.chart.heartRate', 'Heart rate')

/** the value as written under the line and in the tooltip */
function valueText(t: TFunction, m: Metric, v: number): { short: string; long: string } {
  if (m === 'glucose') {
    const s = v.toFixed(1)
    return { short: s, long: t('home.chart.glucoseTip', '{{v}} mmol/L daily average', { v: s }) }
  }
  const s = Math.round(v).toLocaleString('en-US')
  if (m === 'steps') return { short: s, long: t('home.chart.stepsTip', '{{v}} steps', { v: s }) }
  if (m === 'calories') return { short: s, long: t('home.chart.caloriesTip', '{{v}} kcal', { v: s }) }
  return { short: s, long: t('home.chart.heartTip', '{{v}} bpm average', { v: s }) }
}

const parse = (iso: string) => new Date(`${iso}T00:00:00`)

const W = 700
const H = 200
const PAD = 22

/** Height of each day as a share of the chart (0 top, 1 bottom), from the person's own lowest and highest day with 10% room; null for a day with no value. */
export function linePositions(values: (number | null)[]): (number | null)[] {
  const present = values.filter((v): v is number => v != null)
  if (present.length === 0) return values.map(() => null)
  let lo = Math.min(...present)
  let hi = Math.max(...present)
  if (hi === lo) {
    lo -= Math.abs(lo) * 0.05 || 1
    hi += Math.abs(hi) * 0.05 || 1
  }
  const room = (hi - lo) * 0.1
  lo -= room
  hi += room
  return values.map((v) => (v == null ? null : 1 - (v - lo) / (hi - lo)))
}

/** SVG path text: one "M ... L ..." run for every stretch of consecutive days with a value (a gap breaks the line). */
function paths(pos: (number | null)[]): { line: string; area: string } {
  const x = (i: number) => ((i + 0.5) / pos.length) * W
  const y = (p: number) => PAD + p * (H - PAD * 2)
  const runs: { i: number; p: number }[][] = []
  pos.forEach((p, i) => {
    if (p == null) {
      runs.push([])
      return
    }
    if (runs.length === 0) runs.push([])
    runs[runs.length - 1]!.push({ i, p })
  })
  const real = runs.filter((r) => r.length > 0)
  const line = real.map((r) => r.map((pt, k) => `${k === 0 ? 'M' : 'L'} ${x(pt.i).toFixed(1)} ${y(pt.p).toFixed(1)}`).join(' ')).join(' ')
  const area = real
    .filter((r) => r.length > 1)
    .map(
      (r) =>
        `${r.map((pt, k) => `${k === 0 ? 'M' : 'L'} ${x(pt.i).toFixed(1)} ${y(pt.p).toFixed(1)}`).join(' ')} L ${x(r[r.length - 1]!.i).toFixed(1)} ${H} L ${x(r[0]!.i).toFixed(1)} ${H} Z`,
    )
    .join(' ')
  return { line, area }
}

export function HealthOverview({ chart }: { chart: HomeOverview['chart'] }) {
  const { t } = useTranslation()
  const [metric, setMetric] = useState<Metric>('glucose')
  // remembered per tab; unset means "the newest day with a value"
  const [picked, setPicked] = useState<Partial<Record<Metric, number>>>({})
  const values = chart[metric]
  const pos = linePositions(values)
  const { line, area } = paths(pos)
  const sel = picked[metric] ?? defaultSelected(values)
  const loc = dateLocale('en-SG')
  const dayLong = (iso: string) => parse(iso).toLocaleDateString(loc, { weekday: 'short', day: 'numeric', month: 'short' })
  const selVal = values[sel]
  const noData = values.every((v) => v == null)
  const color = COLOR[metric]

  return (
    <section
      aria-label={t('home.chart.title', 'Health overview')}
      className="flex flex-col gap-3 rounded-card border border-line bg-card p-4 shadow-lift h-full"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-h2 font-bold">{t('home.chart.title', 'Health overview')}</h2>
        <span className="rounded-chip border border-line px-3.5 py-1 text-sub">{t('home.chart.range', '7 days')}</span>
      </div>

      <div role="tablist" aria-label={t('home.chart.tabs', 'What to show')} className="flex flex-wrap gap-2">
        {METRICS.map((m) => (
          <button
            key={m}
            type="button"
            role="tab"
            aria-selected={metric === m}
            onClick={() => setMetric(m)}
            className={cn('press min-h-11 rounded-chip px-3.5 text-sub', metric === m ? cn(COLOR[m].tab, 'font-bold text-on-brand') : 'bg-well text-ink2')}
          >
            {tabName(t, m)}
          </button>
        ))}
      </div>

      {noData ? (
        <p className="rounded-card bg-well p-4 text-sub text-ink2">{t('home.chart.none', 'Nothing to show for these 7 days yet.')}</p>
      ) : (
        <div role="tabpanel" className="flex flex-1 flex-col justify-center gap-1.5">
          {/* the tooltip of the selected day: in the flow (so it never covers the line), kept inside the card */}
          <div className="min-h-[3.4rem]" aria-live="polite">
            {selVal != null && chart.days[sel] && (
              <div
                className="w-max max-w-[9.5rem] rounded-[12px] bg-ink px-2.5 py-2 text-micro text-canvas"
                style={{ marginLeft: `clamp(0px, calc(${((sel + 0.5) / 7) * 100}% - 4.75rem), calc(100% - 9.5rem))` }}
              >
                <p className="font-bold">{dayLong(chart.days[sel]!)}</p>
                <p>{valueText(t, metric, selVal).long}</p>
              </div>
            )}
          </div>

          <div className={cn('relative h-[200px] min-h-[200px] flex-1 lg:max-h-[22rem]', color.text)}>
            <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="absolute inset-0 h-full w-full overflow-visible" aria-hidden>
              {[0.25, 0.5, 0.75].map((g) => (
                <line
                  key={g}
                  x1="0"
                  x2={W}
                  y1={H * g}
                  y2={H * g}
                  stroke="var(--c-line)"
                  strokeWidth="1"
                  strokeDasharray="4 6"
                  vectorEffect="non-scaling-stroke"
                />
              ))}
              {area && <path d={area} fill="currentColor" opacity="0.12" />}
              {line && (
                <path
                  d={line}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  vectorEffect="non-scaling-stroke"
                />
              )}
            </svg>
            <div className="absolute inset-0 grid grid-cols-7">
              {chart.days.map((d, i) => {
                const v = values[i]
                const p = pos[i]
                const on = i === sel
                const text = v == null ? null : valueText(t, metric, v)
                return (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setPicked((s) => ({ ...s, [metric]: i }))}
                    aria-pressed={on}
                    aria-label={text ? `${dayLong(d)}, ${text.long}` : t('home.chart.noDay', '{{day}}, no data', { day: dayLong(d) })}
                    className={cn('press relative min-w-0 rounded-card', on && 'bg-well/70')}
                  >
                    {p != null && (
                      <span
                        className={cn(
                          'absolute left-1/2 block -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card',
                          color.dot,
                          on ? 'h-[18px] w-[18px]' : 'h-3 w-3',
                        )}
                        style={{ top: `${((PAD + p * (H - PAD * 2)) / H) * 100}%` }}
                        aria-hidden
                      />
                    )}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="grid grid-cols-7 gap-1.5 text-center sm:gap-2" aria-hidden>
            {chart.days.map((d, i) => {
              const v = values[i]
              return (
                <span key={d} className={cn('num text-micro [[data-ts="2"]_&]:hidden', i === sel ? 'font-bold text-ink' : 'text-ink2')}>
                  {v == null ? <>&ndash;</> : valueText(t, metric, v).short}
                </span>
              )
            })}
          </div>
          <div className="grid grid-cols-7 gap-1.5 text-center text-micro text-ink2 sm:gap-2" aria-hidden>
            {chart.days.map((d) => (
              <span key={d}>
                <span className="[[data-ts='2']_&]:hidden">{parse(d).toLocaleDateString(loc, { weekday: 'short' })}</span>
                <span className="hidden [[data-ts='2']_&]:inline">{parse(d).toLocaleDateString(loc, { weekday: 'narrow' })}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

export function HealthOverviewSkeleton() {
  return <Skeleton className="h-80" />
}
