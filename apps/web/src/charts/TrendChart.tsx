import { useId, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'
import type { SeriesPoint } from '@/data/types'
import { shortDate } from '@/lib/format'
import { duration, ease } from '@/motion/tokens'
import { linear, useMeasure } from './useMeasure'

const drawn = new Set<string>()

/**
 * Line trend with the person's own baseline band (median plus or minus spread) shaded behind it.
 * Gaps in the data are real gaps, never interpolated. Tap or drag to read a value.
 */
export function TrendChart({
  points,
  baseline,
  height = 168,
  format = (v: number) => String(Math.round(v * 10) / 10),
  label,
  color = 'var(--c-s1)',
  drawKey,
  yMin,
  yMax,
  endLabel,
}: {
  points: SeriesPoint[]
  baseline?: [number, number]
  height?: number
  format?: (v: number) => string
  label: string
  color?: string
  drawKey?: string
  yMin?: number
  yMax?: number
  /** what the right-hand end of the axis is called; "Today" unless the data stops earlier */
  endLabel?: string
}) {
  const { t } = useTranslation()
  const [ref, width] = useMeasure<HTMLDivElement>()
  const id = useId()
  const [sel, setSel] = useState<number | null>(null)
  const padL = 40
  const padR = 8
  const padT = 10
  const padB = 26

  const vals = points.map((p) => p.v).filter((v): v is number => v != null)
  const lo = Math.min(yMin ?? Infinity, ...vals, baseline?.[0] ?? Infinity)
  const hi = Math.max(yMax ?? -Infinity, ...vals, baseline?.[1] ?? -Infinity)
  const span = hi - lo || 1
  const y0 = yMin ?? lo - span * 0.12
  const y1 = yMax ?? hi + span * 0.12
  const sx = linear(0, Math.max(points.length - 1, 1), padL, width - padR)
  const sy = linear(y0, y1, height - padB, padT)

  const path = useMemo(() => {
    let d = ''
    let pen = false
    points.forEach((p, i) => {
      if (p.v == null) {
        pen = false
        return
      }
      d += `${pen ? 'L' : 'M'}${sx(i).toFixed(1)} ${sy(p.v).toFixed(1)} `
      pen = true
    })
    return d
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [points, width, height, y0, y1])

  const ticks = [y0 + (y1 - y0) * 0.1, (y0 + y1) / 2, y1 - (y1 - y0) * 0.1]
  const key = drawKey ?? `${label}-${points.length}`
  const first = !drawn.has(key)
  const last = points.length - 1
  const lastV = points[last]?.v
  const pick = (clientX: number, el: SVGSVGElement) => {
    const rect = el.getBoundingClientRect()
    const x = clientX - rect.left
    const i = Math.round(((x - padL) / (width - padL - padR)) * (points.length - 1))
    setSel(Math.min(Math.max(i, 0), points.length - 1))
  }
  const shown = sel ?? last
  const sp = points[shown]

  return (
    <div ref={ref} className="w-full">
      <div className="mb-1 flex min-h-7 items-baseline justify-between gap-2 text-sub">
        <span className="text-ink2">{sp ? shortDate(sp.date) : ''}</span>
        <span className="num text-h2 text-ink">{sp?.v != null ? format(sp.v) : t('charts.noData', 'No data')}</span>
      </div>
      <svg
        role="img"
        aria-label={label}
        width={width}
        height={height}
        className="touch-pan-y select-none overflow-visible"
        onPointerDown={(e) => pick(e.clientX, e.currentTarget)}
        onPointerMove={(e) => e.buttons && pick(e.clientX, e.currentTarget)}
        onPointerLeave={() => setSel(null)}
      >
        {baseline && <rect x={padL} width={width - padL - padR} y={sy(baseline[1])} height={Math.max(sy(baseline[0]) - sy(baseline[1]), 2)} fill="var(--c-band)" rx={4} />}
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={padL} x2={width - padR} y1={sy(t)} y2={sy(t)} stroke="var(--c-line)" strokeDasharray="3 5" />
            <text x={padL - 8} y={sy(t) + 4} textAnchor="end" fill="var(--c-ink3)" style={{ fontSize: 'calc(13px * var(--ts))' }}>
              {format(t)}
            </text>
          </g>
        ))}
        <text x={padL} y={height - 6} fill="var(--c-ink3)" style={{ fontSize: 'calc(13px * var(--ts))' }}>
          {points[0] ? shortDate(points[0].date) : ''}
        </text>
        <text x={width - padR} y={height - 6} textAnchor="end" fill="var(--c-ink3)" style={{ fontSize: 'calc(13px * var(--ts))' }}>
          {endLabel ?? t('charts.today', 'Today')}
        </text>
        <motion.path
          d={path}
          fill="none"
          stroke={color}
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={first ? { pathLength: 0 } : false}
          animate={{ pathLength: 1 }}
          transition={{ duration: duration.chart, ease: ease.out }}
          onAnimationComplete={() => drawn.add(key)}
        />
        {sp?.v != null && (
          <g>
            <line x1={sx(shown)} x2={sx(shown)} y1={padT} y2={height - padB} stroke={color} strokeOpacity={0.3} />
            <circle cx={sx(shown)} cy={sy(sp.v)} r={5.5} fill="var(--c-card)" stroke={color} strokeWidth={2.5} />
          </g>
        )}
        {sel == null && lastV != null && <circle cx={sx(last)} cy={sy(lastV)} r={0} />}
      </svg>
      <span id={id} className="sr-only">
        {label}
      </span>
    </div>
  )
}
