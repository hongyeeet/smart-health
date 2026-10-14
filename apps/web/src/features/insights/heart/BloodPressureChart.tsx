/**
 * Blood pressure the person logged by hand (C5): one bar per reading, from the bottom number (hollow dot) up to the top number (solid dot),
 * placed along the days by date and time so a morning and an evening reading sit side by side. Point at or touch a reading to read it.
 * Nothing is judged: no bands, no "normal" or "high", one neutral colour.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { linear, useMeasure } from '@/charts/useMeasure'
import type { InsightsBloodPressure } from '@/data/types'
import { shortDate } from '@/lib/format'

type Reading = InsightsBloodPressure['readings'][number]

const PAD_L = 40
const PAD_R = 10
const PAD_T = 10
const PAD_B = 26
const DAY = 86400000

const dayMs = (iso: string) => new Date(`${iso}T00:00:00Z`).getTime()
/** the reading's place on the time axis: its day plus the fraction of the day it was taken */
const at = (r: Reading) => {
  const [hh, mm] = r.time.split(':').map(Number)
  return dayMs(r.date) + ((hh ?? 0) * 60 + (mm ?? 0)) * 60000
}

export function BloodPressureChart({ readings, from, to, label, height = 176 }: { readings: Reading[]; from: string; to: string; label: string; height?: number }) {
  const { t } = useTranslation()
  const [ref, width] = useMeasure<HTMLDivElement>()
  const [sel, setSel] = useState<number | null>(null)
  if (!readings.length) return null
  const H = height

  const rs = [...readings].sort((a, b) => at(a) - at(b))
  const t0 = dayMs(from)
  const t1 = dayMs(to) + DAY
  const lo = Math.floor((Math.min(...rs.map((r) => r.diastolic)) - 8) / 10) * 10
  const hi = Math.ceil((Math.max(...rs.map((r) => r.systolic)) + 8) / 10) * 10
  const sx = linear(t0, t1, PAD_L, width - PAD_R)
  const sy = linear(lo, hi, H - PAD_B, PAD_T)
  const ticks = Array.from(new Set([lo, Math.round((lo + hi) / 20) * 10, hi]))
  const px = (r: Reading) => Math.min(Math.max(sx(at(r)), PAD_L + 3), width - PAD_R - 3)

  const pick = (clientX: number, el: SVGSVGElement) => {
    const x = clientX - el.getBoundingClientRect().left
    let best = 0
    rs.forEach((r, i) => {
      if (Math.abs(px(r) - x) < Math.abs(px(rs[best]!) - x)) best = i
    })
    setSel(best)
  }
  const s = sel != null ? rs[sel] : null
  const dash = '–'

  return (
    <div ref={ref} className="w-full">
      <p className="mb-1 flex min-h-7 flex-wrap items-baseline justify-between gap-x-3 text-sub" aria-live="polite">
        {s ? (
          <>
            <span className="text-ink2">
              {shortDate(s.date)}, {s.time}
            </span>
            <span className="num text-ink">
              {t('insights.bp.readout', '{{top}} over {{bottom}}', { top: s.systolic, bottom: s.diastolic })}
              <span className="ml-2 text-ink3">{t('insights.bp.readoutPulse', 'pulse {{n}}', { n: s.pulse ?? dash })}</span>
            </span>
          </>
        ) : (
          <span className="text-ink3">{t('insights.bp.hint', 'Point at or touch a reading to see its numbers.')}</span>
        )}
      </p>
      <svg
        width={width}
        height={H}
        role="img"
        aria-label={label}
        className="touch-pan-y select-none overflow-visible"
        onPointerDown={(e) => pick(e.clientX, e.currentTarget)}
        onPointerMove={(e) => (e.buttons || e.pointerType === 'mouse') && pick(e.clientX, e.currentTarget)}
        onPointerLeave={() => setSel(null)}
      >
        {ticks.map((v) => (
          <g key={v}>
            <line x1={PAD_L} x2={width - PAD_R} y1={sy(v)} y2={sy(v)} stroke="var(--c-line)" strokeDasharray="3 5" />
            <text x={PAD_L - 6} y={sy(v)} dominantBaseline="middle" textAnchor="end" className="fill-ink3 text-micro">
              {v}
            </text>
          </g>
        ))}
        {rs.map((r, i) => {
          const x = px(r)
          const on = sel === i
          return (
            <g key={`${r.date}-${r.time}-${i}`} opacity={sel == null || on ? 1 : 0.45}>
              <line x1={x} x2={x} y1={sy(r.systolic)} y2={sy(r.diastolic)} stroke="var(--c-s3)" strokeWidth={on ? 4 : 3} strokeLinecap="round" strokeOpacity={0.55} />
              <circle cx={x} cy={sy(r.systolic)} r={on ? 5 : 3.5} fill="var(--c-s3)" />
              <circle cx={x} cy={sy(r.diastolic)} r={on ? 5 : 3.5} fill="var(--c-card)" stroke="var(--c-s3)" strokeWidth={2} />
            </g>
          )
        })}
        <text x={PAD_L} y={H - 6} className="fill-ink3 text-micro">
          {shortDate(from)}
        </text>
        <text x={width - PAD_R} y={H - 6} textAnchor="end" className="fill-ink3 text-micro">
          {shortDate(to)}
        </text>
      </svg>
      <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sub text-ink2">
        <span className="flex items-center gap-1.5">
          <svg width={12} height={12} aria-hidden>
            <circle cx={6} cy={6} r={5} fill="var(--c-s3)" />
          </svg>
          {t('insights.bp.legendTopV3', 'Systolic BP')}
        </span>
        <span className="flex items-center gap-1.5">
          <svg width={12} height={12} aria-hidden>
            <circle cx={6} cy={6} r={4.2} fill="var(--c-card)" stroke="var(--c-s3)" strokeWidth={2} />
          </svg>
          {t('insights.bp.legendBottomV3', 'Diastolic BP')}
        </span>
      </p>
    </div>
  )
}
