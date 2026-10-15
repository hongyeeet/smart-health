/**
 * Mood and stress on one chart: two lines on a 1 to 5 axis, like the average and resting lines of the heart chart. Point at or touch a day
 * to read both. A day without a check-in leaves a gap in the line; nothing is joined across it and nothing is judged.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { linear, useMeasure } from '@/charts/useMeasure'
import { shortDate } from '@/lib/format'

export interface MoodStressDay {
  date: string
  mood: number | null
  stress: number | null
}

const H = 190
const PAD_L = 28
const PAD_R = 8
const PAD_T = 10
const PAD_B = 26

export function MoodStressChart({ days, label }: { days: MoodStressDay[]; label: string }) {
  const { t } = useTranslation()
  const [ref, width] = useMeasure<HTMLDivElement>()
  const [sel, setSel] = useState<number | null>(null)
  const sx = linear(0, Math.max(days.length - 1, 1), PAD_L, width - PAD_R)
  const sy = linear(1, 5, H - PAD_B, PAD_T)

  const path = (key: 'mood' | 'stress') => {
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
  const pick = (clientX: number, el: SVGSVGElement) => {
    const x = clientX - el.getBoundingClientRect().left
    const i = Math.round(((x - PAD_L) / Math.max(width - PAD_L - PAD_R, 1)) * (days.length - 1))
    setSel(Math.min(Math.max(i, 0), days.length - 1))
  }
  const day = sel != null ? days[sel] : null
  const dash = '–'
  const first = days[0]?.date
  const last = days[days.length - 1]?.date

  return (
    <div ref={ref} className="w-full">
      <p className="mb-1 flex min-h-7 flex-wrap items-baseline justify-between gap-x-3 text-sub" aria-live="polite">
        {day ? (
          <>
            <span className="text-ink2">{shortDate(day.date)}</span>
            <span className="num text-ink">
              {t('insights.sleep.readoutMood', 'Mood: {{n}}', { n: day.mood ?? dash })}
              <span className="px-1.5 text-ink3" aria-hidden>
                ·
              </span>
              {t('insights.sleep.readoutStress', 'Stress: {{n}}', { n: day.stress ?? dash })}
              <span className="ml-1 text-ink3">{t('insights.sleep.outOf5', 'out of 5')}</span>
            </span>
          </>
        ) : (
          <span className="text-ink3">{t('insights.sleep.moodHint', 'Point at or touch the chart to read a day.')}</span>
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
        {[1, 3, 5].map((v) => (
          <g key={v}>
            <line x1={PAD_L} x2={width - PAD_R} y1={sy(v)} y2={sy(v)} stroke="var(--c-line)" strokeDasharray="3 5" />
            <text x={PAD_L - 8} y={sy(v)} dominantBaseline="middle" textAnchor="end" className="fill-ink3 text-micro">
              {v}
            </text>
          </g>
        ))}
        {sel != null && <line x1={sx(sel)} x2={sx(sel)} y1={PAD_T} y2={H - PAD_B} stroke="var(--c-ink3)" strokeOpacity={0.5} />}
        <path d={path('stress')} fill="none" stroke="var(--c-s2)" strokeWidth={2.5} strokeLinejoin="round" />
        <path d={path('mood')} fill="none" stroke="var(--c-s1)" strokeWidth={2.5} strokeLinejoin="round" />
        {days.map((p, i) => (
          <g key={p.date}>
            {p.stress != null && <circle cx={sx(i)} cy={sy(p.stress)} r={sel === i ? 5 : 3} fill="var(--c-s2)" />}
            {p.mood != null && <circle cx={sx(i)} cy={sy(p.mood)} r={sel === i ? 5 : 3} fill="var(--c-s1)" />}
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
          {t('insights.sleep.mood', 'Mood')}
        </li>
        <li className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-full bg-[var(--c-s2)]" aria-hidden />
          {t('insights.sleep.stress', 'Stress')}
        </li>
      </ul>
    </div>
  )
}
