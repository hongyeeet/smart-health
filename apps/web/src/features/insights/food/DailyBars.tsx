/**
 * One bar per day over an Insights period, hand-built in SVG like the other charts in src/charts. A day with no value is a gap:
 * a short dashed mark on the baseline, never a bar of zero, so an unknown day is not read as "nothing eaten".
 */
import { textFactor } from '@/lib/textScale'
import { useTranslation } from 'react-i18next'
import { linear, useMeasure } from '@/charts/useMeasure'
import { shortDate } from '@/lib/format'
import { useUi } from '@/state/store'

export interface DayValue {
  date: string
  value: number | null
}

const H = 124
const TOP = 8
const BASE = H - 22 // room under the baseline for the date labels

export function DailyBars({ days, unit, label, format }: { days: DayValue[]; unit: string; label: string; format: (n: number) => string }) {
  const { t } = useTranslation()
  const [ref, width] = useMeasure<HTMLDivElement>()
  const textScale = useUi((s) => s.textScale)
  const known = days.filter((d): d is { date: string; value: number } => d.value != null)
  const max = Math.max(0, ...known.map((d) => d.value))
  const sy = linear(0, max || 1, BASE, TOP)
  const n = days.length
  const colW = n ? width / n : width
  const bw = Math.max(2, Math.min(28, colW * 0.7))
  // about five date labels, always the first and the last day; at larger text the dates are wider, so about three
  const labels = textScale === 2 ? 3 : 5
  const step = n > 1 ? Math.ceil((n - 1) / (labels - 1)) : 1
  // a middle label that would touch the first or the last one is left out
  const labelW = 7 * 0.58 * 12 * textFactor(textScale)
  const roomFor = (i: number) => i * colW >= labelW * 1.15 && (n - 1 - i) * colW >= labelW * 1.15
  const summary = t('insights.food.chartSummary', '{{label}}: {{known}} of {{n}} days have a value. Highest {{max}} {{unit}}.', {
    label,
    known: known.length,
    n,
    max: format(max),
    unit,
  })
  return (
    <div ref={ref} className="w-full">
      <svg width={width} height={H} role="img" aria-label={summary} className="overflow-visible">
        <line x1={0} x2={width} y1={BASE} y2={BASE} stroke="var(--c-line)" strokeWidth={1} />
        {days.map((d, i) => {
          const cx = (i + 0.5) * colW
          const x = cx - bw / 2
          const tip = d.value == null ? `${shortDate(d.date)}: ${t('insights.food.noValue', 'no value')}` : `${shortDate(d.date)}: ${format(d.value)} ${unit}`
          return (
            <g key={d.date}>
              <title>{tip}</title>
              {d.value == null ? (
                <line x1={x} x2={x + bw} y1={BASE} y2={BASE} stroke="var(--c-ink3)" strokeWidth={2} strokeDasharray="2 3" />
              ) : (
                <rect x={x} y={sy(d.value)} width={bw} height={Math.max(1, BASE - sy(d.value))} rx={Math.min(4, bw / 2)} fill="var(--c-brand)" />
              )}
              {(i === 0 || i === n - 1 || (i % step === 0 && roomFor(i))) && (
                <text x={cx} y={H - 4} textAnchor={i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle'} fill="var(--c-ink3)" style={{ fontSize: 'calc(12px * var(--ts))' }}>
                  {shortDate(d.date)}
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
