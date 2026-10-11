/** Two lines on one chart: the day's average heart rate and the daily resting value. A day without data leaves a gap. */
import { useTranslation } from 'react-i18next'
import { linear, useMeasure } from '@/charts/useMeasure'
import { shortDate } from '@/lib/format'

export interface HeartChartDay {
  date: string
  avg: number | null
  resting: number | null
}

const H = 168
const PAD_L = 36
const PAD_R = 8
const PAD_T = 10
const PAD_B = 26

export function HeartChart({ days, label }: { days: HeartChartDay[]; label: string }) {
  const { t } = useTranslation()
  const [ref, width] = useMeasure<HTMLDivElement>()
  const vals = days.flatMap((d) => [d.avg, d.resting]).filter((v): v is number => v != null)
  if (!vals.length) return null
  const minV = Math.floor(Math.min(...vals))
  const maxV = Math.ceil(Math.max(...vals))
  const lo = minV - 4
  const hi = maxV + 4
  const sx = linear(0, Math.max(days.length - 1, 1), PAD_L, width - PAD_R)
  const sy = linear(lo, hi, H - PAD_B, PAD_T)
  const ticks = [minV, Math.round((lo + hi) / 2), maxV]

  const path = (key: 'avg' | 'resting') => {
    let d = ''
    let pen = false
    days.forEach((p, i) => {
      const v = p[key]
      if (v == null) {
        pen = false
        return
      }
      d += `${pen ? 'L' : 'M'}${sx(i).toFixed(1)} ${sy(v).toFixed(1)} `
      pen = true
    })
    return d
  }
  const first = days[0]?.date
  const last = days[days.length - 1]?.date

  return (
    <div ref={ref} className="w-full">
      <svg width={width} height={H} role="img" aria-label={label} className="overflow-visible">
        {ticks.map((v, i) => (
          <g key={`${v}-${i}`}>
            <line x1={PAD_L} x2={width - PAD_R} y1={sy(v)} y2={sy(v)} stroke="var(--c-line)" strokeDasharray="3 5" />
            <text x={PAD_L - 6} y={sy(v)} dominantBaseline="middle" textAnchor="end" className="fill-ink3 text-micro">
              {v}
            </text>
          </g>
        ))}
        <path d={path('resting')} fill="none" stroke="var(--c-s2)" strokeWidth={2} />
        <path d={path('avg')} fill="none" stroke="var(--c-s1)" strokeWidth={2.5} />
        {days.map((p, i) => (
          <g key={p.date}>
            {p.resting != null && <circle cx={sx(i)} cy={sy(p.resting)} r={2.5} fill="var(--c-s2)" />}
            {p.avg != null && <circle cx={sx(i)} cy={sy(p.avg)} r={2.5} fill="var(--c-s1)" />}
          </g>
        ))}
        {first && (
          <text x={PAD_L} y={H - 6} className="fill-ink3 text-micro">
            {shortDate(first)}
          </text>
        )}
        {last && (
          <text x={width - PAD_R} y={H - 6} textAnchor="end" className="fill-ink3 text-micro">
            {shortDate(last)}
          </text>
        )}
      </svg>
      <ul className="mt-2 flex gap-5 text-sub text-ink2">
        <li className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-full bg-[var(--c-s1)]" aria-hidden />
          {t('insights.heart.average', 'Average')}
        </li>
        <li className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-full bg-[var(--c-s2)]" aria-hidden />
          {t('insights.heart.resting', 'Resting')}
        </li>
      </ul>
    </div>
  )
}
