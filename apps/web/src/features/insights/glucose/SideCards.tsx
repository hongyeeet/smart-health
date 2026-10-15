/** The right-hand column of the Glucose page: the morning level with its usual range, the hour-of-day pattern, and the findings from the history. */
import { useTranslation } from 'react-i18next'
import type { DoctorReport, InsightsGlucose, InsightsPattern } from '@/data/types'
import { useMeasure } from '@/charts/useMeasure'
import { shortDate } from '@/lib/format'
import { cn } from '@/lib/cn'
import { UnverifiedTag } from '@/ui/primitives'
import { fit, hourLabel, linePath, nums, type Series } from './svgKit'

type Days = InsightsGlucose['days']
type Profile = DoctorReport['glucose']['profile']

/** A small line of the morning (5 to 7 am) level by day, on the usual range (the shaded band). */
function MorningSpark({ days, morning }: { days: Days; morning: { p25: number; p75: number } | null }) {
  const [ref, W] = useMeasure<HTMLDivElement>(290)
  const H = 96
  const PT = 8
  const PB = 14
  const series: Series = days.map((d) => d.fasting)
  const [lo, hi] = fit(nums([...series, morning?.p25 ?? null, morning?.p75 ?? null]), 5, 12)
  const y = (v: number) => PT + ((H - PT - PB) * (hi - v)) / (hi - lo || 1)
  const x = (i: number) => 8 + (W - 16) * (days.length > 1 ? i / (days.length - 1) : 0.5)
  const last = days.reduce((acc, d, i) => (d.fasting != null ? i : acc), -1)
  const lastVal = last >= 0 ? (days[last]?.fasting ?? null) : null
  return (
    <div ref={ref} className="w-full min-w-0">
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} role="img" className="block max-w-full">
        {morning && (
          <rect x={8} width={Math.max(0, W - 16)} y={y(morning.p75)} height={Math.max(0, y(morning.p25) - y(morning.p75))} className="fill-ok-soft" />
        )}
        <path d={linePath(series, x, y)} fill="none" className="stroke-brand" strokeWidth={2.2} strokeLinejoin="round" />
        {lastVal != null && <circle cx={x(last)} cy={y(lastVal)} r={4} strokeWidth={2.2} className="fill-card stroke-brand" />}
      </svg>
    </div>
  )
}

export function MorningCard({ days, morning, drift }: { days: Days; morning: { p25: number; p75: number } | null; drift: InsightsGlucose['drift'] }) {
  const { t } = useTranslation()
  const first = days[0]?.date
  const lastDay = days[days.length - 1]?.date
  return (
    <section className="flex flex-col gap-2 rounded-card border border-line bg-card p-4 shadow-lift">
      <div>
        <h2 className="text-sub font-bold">{t('insights.glucose.morningTitle', 'Morning glucose')}</h2>
        <p className="text-[13px] leading-[18px] text-ink3">
          {morning
            ? t('insights.glucose.morningSubBand', 'Average of 5 to 7 am each day. Shaded: your usual range.')
            : t('insights.glucose.morningSub', 'Average of 5 to 7 am each day.')}
        </p>
      </div>
      {drift && (
        <p className="rounded-[12px] bg-info-soft px-3 py-2.5 text-[13px] leading-[18px] text-info">
          <span className="font-bold">{drift.text}</span> {t('insights.glucose.worthDoctor', 'Worth mentioning to your doctor.')}
        </p>
      )}
      <MorningSpark days={days} morning={morning} />
      <div className="flex justify-between gap-2 text-[13px] leading-[18px] text-ink3">
        <span className="num whitespace-nowrap">{first ? shortDate(first) : '–'}</span>
        <span className="num whitespace-nowrap">{lastDay ? shortDate(lastDay) : '–'}</span>
      </div>
    </section>
  )
}

const H = 94
const TOP = 6
const BASE = 70

/** Typical reading for each hour of the day (the middle of the readings at that hour), with 12 am, 8 am, 12 pm and 8 pm marked. */
export function HourCard({ profile, high }: { profile: Profile | undefined; high: number }) {
  const { t } = useTranslation()
  const [ref, W] = useMeasure<HTMLDivElement>(290)
  const byHour = new Map((profile ?? []).map((p): [number, number] => [p.hour, p.p50]))
  const [lo, hi] = fit(nums([...byHour.values()]), 6, 14)
  const y = (v: number) => BASE - ((BASE - TOP) * (v - lo)) / (hi - lo || 1)
  const slot = W / 24
  const barW = Math.min(9, slot * 0.6)

  const ranked = [...(profile ?? [])].sort((a, b) => b.p50 - a.p50)
  const first = ranked[0]
  const second = first ? ranked.find((p) => Math.abs(p.hour - first.hour) >= 4) : undefined
  const peak = !first
    ? ''
    : second
      ? t('insights.glucose.peakTwo', 'Highest around {{a}} and {{b}}.', { a: hourLabel(first.hour), b: hourLabel(second.hour) })
      : t('insights.glucose.peakOne', 'Highest around {{a}}.', { a: hourLabel(first.hour) })

  return (
    <section className="flex flex-col gap-2 rounded-card border border-line bg-card p-4 shadow-lift">
      <div>
        <h2 className="text-sub font-bold">{t('insights.glucose.dayTitle', 'Through the day')}</h2>
        <p className="text-[13px] leading-[18px] text-ink3">{t('insights.glucose.dayPlain', 'Typical reading by hour, all days')}</p>
      </div>
      {byHour.size === 0 ? (
        <p className="py-6 text-center text-[13px] leading-[18px] text-ink3">{t('insights.glucose.noHours', 'Not enough readings by hour yet.')}</p>
      ) : (
        <>
          <div ref={ref} className="w-full min-w-0">
            <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} role="img" aria-label={peak} className="block max-w-full">
              {Array.from({ length: 24 }, (_, h) => {
                const v = byHour.get(h)
                if (v == null) return null
                return (
                  <rect
                    key={h}
                    x={slot * h + (slot - barW) / 2}
                    y={y(v)}
                    width={barW}
                    height={Math.max(0, BASE - y(v))}
                    rx={2}
                    className={v > high ? 'fill-brass' : 'fill-ok opacity-50'}
                  />
                )
              })}
              {[0, 8, 12, 20].map((h) => (
                <text key={h} x={slot * h} y={90} fontSize={10} className="fill-ink3">
                  {hourLabel(h)}
                </text>
              ))}
            </svg>
          </div>
          {peak && <p className="text-[13px] leading-[18px] text-ink2">{peak}</p>}
        </>
      )}
    </section>
  )
}

/** The findings from the person's own history. They compare two things; they do not prove a cause (the tag says so). */
export function HistoryCard({ patterns }: { patterns: InsightsPattern[] }) {
  const { t } = useTranslation()
  return (
    <section className="flex flex-col gap-1 rounded-card border border-line bg-card p-4 shadow-lift">
      <h2 className="mb-1 text-sub font-bold">{t('insights.shared.findings', 'What your history shows')}</h2>
      {patterns.length === 0 ? (
        <p className="text-[13px] leading-[18px] text-ink3">{t('insights.glucose.noPatterns', 'Nothing stands out yet.')}</p>
      ) : (
        <>
          {patterns.map((p, i) => (
            <div key={p.key} className={cn('py-2', i > 0 && 'border-t border-line')}>
              <p className="text-[13px] leading-[18px] text-ink">{p.text}</p>
              <p className="num mt-1 text-[12px] leading-4 text-ink3">{t('insights.glucose.matched', '{{n}} matched events', { n: p.n })}</p>
            </div>
          ))}
          <div className="pt-1">
            <UnverifiedTag />
          </div>
        </>
      )}
    </section>
  )
}
