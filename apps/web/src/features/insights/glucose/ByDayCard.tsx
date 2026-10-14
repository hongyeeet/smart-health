/**
 * "Glucose by day": one chart at a time. The daily average (with the lowest to highest band), the morning (5 to 7 am) average against
 * the usual range, or the highest reading of each day. Every value comes from the glucose series and the timeline; nothing is invented.
 */
import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import type { InsightsGlucose, InsightsTimelineDay } from '@/data/types'
import { useMeasure } from '@/charts/useMeasure'
import { shortDate, weekdayShort } from '@/lib/format'
import { Segmented } from '@/ui/controls'
import { num } from '../shared'
import { bandPath, fit, isWeekend, labelDays, linePath, nums, ticks, type Series } from './svgKit'

type Mode = 'avg' | 'fast' | 'peak'
type Day = InsightsGlucose['days'][number]
interface Row {
  date: string
  mean: number | null
  fasting: number | null
  min: number | null
  max: number | null
}

const H = 250
const PL = 40
const PR = 34
const PT = 14
const PB = 38

export interface ByDayProps {
  days: Day[]
  /** the timeline's day rows: the lowest and highest reading of each day */
  dayRows: InsightsTimelineDay[] | undefined
  /** the usual morning range (25th to 75th percentile of the days before) */
  morning: { p25: number; p75: number } | null
  /** the average of the daily averages before the period: the dashed line */
  baselineMean: number | null
  baselineDays: number | null
  low: number
  high: number
  /** the very high limit from the doctor report, or null when the report is not there */
  veryHigh: number | null
}

export function ByDayCard(p: ByDayProps) {
  const { t } = useTranslation()
  const [mode, setMode] = useState<Mode>('avg')
  const [ref, W] = useMeasure<HTMLDivElement>(340)

  const rows: Row[] = p.days.map((d) => {
    const r = p.dayRows?.find((x) => x.date === d.date)
    return { date: d.date, mean: d.mean, fasting: d.fasting, min: r?.glucose.min ?? null, max: r?.glucose.max ?? null }
  })
  const n = rows.length
  // the latest day that has a reading for the chosen view
  const pick = (get: (r: Row) => number | null) => {
    for (let i = n - 1; i >= 0; i--) if (get(rows[i] as Row) != null) return i
    return -1
  }
  const idx = mode === 'avg' ? pick((r) => r.mean) : mode === 'fast' ? pick((r) => r.fasting) : pick((r) => r.max)
  const cur: Row | undefined = rows[idx]
  const dayLabel = cur ? `${weekdayShort(cur.date)} ${shortDate(cur.date)}` : ''

  const sub = !cur
    ? ''
    : mode === 'avg'
      ? t('insights.glucose.subAvg', '{{day}}, average', { day: dayLabel })
      : mode === 'fast'
        ? t('insights.glucose.subFast', '{{day}}, 5 to 7 am', { day: dayLabel })
        : t('insights.glucose.subPeak', '{{day}}, highest', { day: dayLabel })

  const current = !cur ? null : mode === 'avg' ? cur.mean : mode === 'fast' ? cur.fasting : cur.max
  const readValue = current != null ? `${num(current, 1)} mmol/L` : '–'

  const readSub: string[] = []
  if (cur && mode === 'avg') {
    if (cur.min != null && cur.max != null)
      readSub.push(t('insights.glucose.readAvgRange', 'Lowest {{low}} to highest {{high}} that day.', { low: num(cur.min, 1), high: num(cur.max, 1) }))
    if (p.baselineMean != null) readSub.push(t('insights.glucose.readAvgBase', 'Dashed line: your baseline {{base}}.', { base: num(p.baselineMean, 1) }))
  }
  if (mode === 'fast' && p.morning)
    readSub.push(t('insights.glucose.usualRange', 'Your usual range is {{low}} to {{high}}.', { low: num(p.morning.p25, 1), high: num(p.morning.p75, 1) }))
  if (mode === 'peak')
    readSub.push(
      p.veryHigh != null
        ? t('insights.glucose.peakKeyVery', 'Orange: above {{v}}. Yellow: above {{h}}.', { v: p.veryHigh, h: p.high })
        : t('insights.glucose.peakKey', 'Yellow: above {{h}}.', { h: p.high }),
    )

  const legend =
    mode === 'avg'
      ? t('insights.glucose.legendAvg', 'Line: daily average. Band: lowest to highest. Grey: weekends.')
      : mode === 'fast'
        ? p.morning
          ? t('insights.glucose.legendFast', 'Line: morning average. Green band: your usual range, from the {{n}} days before.', { n: p.baselineDays ?? 0 })
          : t('insights.glucose.legendFastNoBand', 'Line: morning average.')
        : t('insights.glucose.legendPeak', 'Bars: the highest reading each day.')

  // ----- the chart: plain SVG drawn at the measured width, so the text keeps its real size -----
  const plotW = W - PL - PR
  const xOf = (i: number) => PL + plotW * (n > 1 ? i / (n - 1) : 0.5)
  const slot = n > 0 ? plotW / n : plotW

  let lo = 0
  let hi = 1
  let parts = 4
  if (mode === 'avg') {
    ;[lo, hi] = fit(nums([...rows.map((r) => r.min), ...rows.map((r) => r.max), ...rows.map((r) => r.mean), p.baselineMean]), 4, 20)
  } else if (mode === 'fast') {
    ;[lo, hi] = fit(nums([...rows.map((r) => r.fasting), p.morning?.p25 ?? null, p.morning?.p75 ?? null]), 5, 12)
  } else {
    ;[lo, hi] = fit(nums(rows.map((r) => r.max)), 0, 24)
    parts = 3
  }
  const tk = ticks(lo, hi, parts)
  const yOf = (v: number) => PT + ((H - PT - PB) * (tk.hi - v)) / (tk.hi - tk.lo || 1)
  const baseY = H - PB
  const means: Series = rows.map((r) => r.mean)
  const fasts: Series = rows.map((r) => r.fasting)
  const mins: Series = rows.map((r) => r.min)
  const maxs: Series = rows.map((r) => r.max)
  const barW = Math.min(14, slot * 0.6)
  const barFill = (v: number) => (p.veryHigh != null && v > p.veryHigh ? 'fill-warn' : v > p.high ? 'fill-brass' : 'fill-ok')

  const grid = tk.values.map((v) => (
    <g key={v}>
      <line x1={PL} x2={W - PR} y1={yOf(v)} y2={yOf(v)} className="stroke-line" />
      <text x={PL - 8} y={yOf(v) + 4} textAnchor="end" fontSize={11} className="fill-ink3">
        {v}
      </text>
    </g>
  ))
  const xAxis = labelDays(n).map((i) => (
    <text key={i} x={xOf(i)} y={H - PB + 22} textAnchor={i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle'} fontSize={12} className="fill-ink3">
      {rows[i] ? shortDate(rows[i].date) : ''}
    </text>
  ))
  const endMark = (v: number | null, i: number, cls: string) =>
    v == null || i < 0 ? null : (
      <>
        <line x1={xOf(i)} x2={xOf(i)} y1={PT} y2={baseY} className="stroke-ink" strokeDasharray="3 3" />
        <circle cx={xOf(i)} cy={yOf(v)} r={5} strokeWidth={2.4} className={`fill-card ${cls}`} />
      </>
    )

  let body: ReactNode = null
  if (mode === 'avg') {
    body = (
      <>
        {rows.map((r, i) =>
          isWeekend(r.date) ? <rect key={r.date} x={xOf(i) - 8} y={PT} width={16} height={baseY - PT} className="fill-well" opacity={0.7} /> : null,
        )}
        <path d={bandPath(maxs, mins, xOf, yOf)} className="fill-info" opacity={0.13} />
        {p.baselineMean != null && (
          <line x1={PL} x2={W - PR} y1={yOf(p.baselineMean)} y2={yOf(p.baselineMean)} className="stroke-ink" strokeWidth={1.3} strokeDasharray="5 4" />
        )}
        <path d={linePath(means, xOf, yOf)} fill="none" className="stroke-info" strokeWidth={2.4} strokeLinejoin="round" />
        {endMark(cur?.mean ?? null, idx, 'stroke-info')}
      </>
    )
  } else if (mode === 'fast') {
    body = (
      <>
        {p.morning && (
          <rect
            x={PL}
            width={plotW}
            y={yOf(p.morning.p75)}
            height={Math.max(0, yOf(p.morning.p25) - yOf(p.morning.p75))}
            className="fill-ok-soft"
            opacity={0.8}
          />
        )}
        <path d={linePath(fasts, xOf, yOf)} fill="none" className="stroke-brand" strokeWidth={2.4} strokeLinejoin="round" />
        {endMark(cur?.fasting ?? null, idx, 'stroke-brand')}
      </>
    )
  } else {
    body = (
      <>
        {p.veryHigh != null && <line x1={PL} x2={W - PR} y1={yOf(p.veryHigh)} y2={yOf(p.veryHigh)} className="stroke-warn" strokeDasharray="4 4" />}
        {rows.map((r, i) =>
          r.max == null ? null : (
            <rect
              key={r.date}
              x={PL + slot * i + (slot - barW) / 2}
              y={yOf(r.max)}
              width={barW}
              height={Math.max(0, baseY - yOf(r.max))}
              rx={3}
              className={barFill(r.max)}
            />
          ),
        )}
      </>
    )
  }

  return (
    <section className="flex flex-col gap-2 rounded-card border border-line bg-card px-5 pb-3.5 pt-4 shadow-lift">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h2 className="text-sub font-bold">{t('insights.glucose.byDayTitle', 'Glucose by day')}</h2>
          <p className="text-[13px] leading-[18px] text-ink3">{sub || '–'}</p>
        </div>
        <Segmented
          label={t('insights.glucose.byDayView', 'Glucose view')}
          value={mode}
          onChange={setMode}
          options={[
            { value: 'avg', label: t('insights.glucose.tabAverage', 'Average') },
            { value: 'fast', label: t('insights.glucose.tabMorning', 'Morning') },
            { value: 'peak', label: t('insights.glucose.tabHighest', 'Highest') },
          ]}
        />
      </div>
      <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 pt-1">
        <span className="num whitespace-nowrap text-[22px] font-bold leading-7">{readValue}</span>
        {readSub.length > 0 && <span className="min-w-0 text-[13px] leading-[18px] text-ink3">{readSub.join(' ')}</span>}
      </div>
      <div ref={ref} className="w-full min-w-0">
        {n > 0 ? (
          <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} role="img" aria-label={sub} className="block max-w-full">
            {grid}
            {body}
            {xAxis}
          </svg>
        ) : (
          <p className="py-16 text-center text-sub text-ink3">{t('insights.glucose.noDays', 'No readings in this period.')}</p>
        )}
      </div>
      <p className="text-[13px] leading-[18px] text-ink3">{legend}</p>
    </section>
  )
}
