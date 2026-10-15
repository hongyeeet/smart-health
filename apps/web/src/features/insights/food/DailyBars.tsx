/**
 * One bar per day over an Insights period, hand-built in SVG like the other charts in src/charts. A day with no value is a gap:
 * a short dashed mark on the baseline, never a bar of zero, so an unknown day is not read as "nothing eaten". The axis runs from 0
 * to a round top above the highest day, and the dashed line is the average of the days that have a value.
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

const H = 230
const TOP = 12
const BASE = H - 40 // the baseline; the date labels sit 22 px under it

/** A round number at or above `v`: 1, 2, 2.5, 5 or 10 times a power of ten. */
function roundTop(v: number): number {
  if (v <= 0) return 1
  const p = 10 ** Math.floor(Math.log10(v))
  const m = v / p
  return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p
}

export function DailyBars({
  days,
  unit,
  label,
  format,
  avg,
}: {
  days: DayValue[]
  unit: string
  label: string
  format: (n: number) => string
  avg?: number | null
}) {
  const { t } = useTranslation()
  const [ref, width] = useMeasure<HTMLDivElement>()
  const textScale = useUi((s) => s.textScale)
  // room for the axis numbers; more at 200% text
  const LEFT = 40 * textScale + 4
  const RIGHT = 6
  const known = days.filter((d): d is { date: string; value: number } => d.value != null)
  const max = Math.max(0, ...known.map((d) => d.value))
  const top = roundTop(max)
  const sy = linear(0, top, BASE, TOP)
  const n = days.length
  const plot = Math.max(0, width - LEFT - RIGHT)
  const colW = n ? plot / n : plot
  const bw = Math.max(3, Math.min(16, colW * 0.5))
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
  const ticks = [0, 1, 2, 3].map((k) => (top * k) / 3)
  return (
    <div ref={ref} className="w-full">
      <svg width={width} height={H} role="img" aria-label={summary} className="overflow-visible">
        {ticks.map((v) => (
          <g key={v}>
            <line x1={LEFT} x2={width} y1={sy(v)} y2={sy(v)} stroke="var(--c-line)" strokeWidth={1} />
            <text x={LEFT - 8} y={sy(v) + 4} textAnchor="end" fill="var(--c-ink2)" style={{ fontSize: 'calc(12px * var(--ts))' }}>
              {Math.round(v).toLocaleString('en-US')}
            </text>
          </g>
        ))}
        {avg != null && <line x1={LEFT} x2={width} y1={sy(avg)} y2={sy(avg)} stroke="var(--c-ink)" strokeWidth={1.3} strokeDasharray="5 4" />}
        {days.map((d, i) => {
          const cx = LEFT + (i + 0.5) * colW
          const x = cx - bw / 2
          const tip = d.value == null ? `${shortDate(d.date)}: ${t('insights.food.noValue', 'no value')}` : `${shortDate(d.date)}: ${format(d.value)} ${unit}`
          return (
            <g key={d.date}>
              <title>{tip}</title>
              {d.value == null ? (
                <line x1={x} x2={x + bw} y1={BASE} y2={BASE} stroke="var(--c-ink3)" strokeWidth={2} strokeDasharray="2 3" />
              ) : (
                <rect x={x} y={sy(d.value)} width={bw} height={Math.max(1, BASE - sy(d.value))} rx={Math.min(3, bw / 2)} fill="var(--c-brand)" />
              )}
              {(i === 0 || i === n - 1 || (i % step === 0 && roomFor(i))) && (
                <text
                  x={cx}
                  y={BASE + 22}
                  textAnchor={i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle'}
                  fill="var(--c-ink2)"
                  style={{ fontSize: 'calc(12px * var(--ts))' }}
                >
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
