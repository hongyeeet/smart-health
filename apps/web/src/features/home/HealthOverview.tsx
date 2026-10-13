/**
 * "Health overview" on Home: a 7-day bar chart with tabs for Glucose, Steps, Calories and Heart rate. The selected bar is dark and
 * has a tooltip with its date and value. Every bar is a real button (keyboard and screen reader). A day with no value is a dash and
 * a small empty stub: never a 0. The numbers are the same daily values as the cards above.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import type { HomeOverview } from '@/data/types'
import { dateLocale } from '@/lib/locale'
import { cn } from '@/lib/cn'
import { Skeleton } from '@/ui/primitives'
import { barScale, defaultSelected } from './status'

type Metric = 'glucose' | 'steps' | 'calories' | 'heartRate'
const METRICS: Metric[] = ['glucose', 'steps', 'calories', 'heartRate']

const tabName = (t: TFunction, m: Metric) =>
  m === 'glucose' ? t('home.chart.glucose', 'Glucose') : m === 'steps' ? t('home.chart.steps', 'Steps') : m === 'calories' ? t('home.chart.calories', 'Calories') : t('home.chart.heartRate', 'Heart rate')

/** the value as written on the bar and in the tooltip */
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

export function HealthOverview({ chart }: { chart: HomeOverview['chart'] }) {
  const { t } = useTranslation()
  const [metric, setMetric] = useState<Metric>('glucose')
  // remembered per tab; unset means "the newest day with a value"
  const [picked, setPicked] = useState<Partial<Record<Metric, number>>>({})
  const values = chart[metric]
  const heights = barScale(values)
  const sel = picked[metric] ?? defaultSelected(values)
  const loc = dateLocale('en-SG')
  const dayLong = (iso: string) => parse(iso).toLocaleDateString(loc, { weekday: 'short', day: 'numeric', month: 'short' })
  const selVal = values[sel]
  const noData = values.every((v) => v == null)

  return (
    <section aria-label={t('home.chart.title', 'Health overview')} className="flex flex-col gap-3 rounded-card border border-line bg-card p-4 shadow-lift">
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
            className={cn('press min-h-11 rounded-chip px-3.5 text-sub', metric === m ? 'bg-brand font-bold text-on-brand' : 'bg-well text-ink2')}
          >
            {tabName(t, m)}
          </button>
        ))}
      </div>

      {noData ? (
        <p className="rounded-card bg-well p-4 text-sub text-ink2">{t('home.chart.none', 'Nothing to show for these 7 days yet.')}</p>
      ) : (
        <div role="tabpanel" className="flex flex-col gap-1.5">
          {/* the tooltip of the selected bar: in the flow (so it never covers the bars), kept inside the card */}
          <div className="min-h-[3.4rem]" aria-live="polite">
            {selVal != null && chart.days[sel] && (
              <div className="w-max max-w-[9.5rem] rounded-[12px] bg-ink px-2.5 py-2 text-micro text-canvas" style={{ marginLeft: `clamp(0px, calc(${((sel + 0.5) / 7) * 100}% - 4.75rem), calc(100% - 9.5rem))` }}>
                <p className="font-bold">{dayLong(chart.days[sel]!)}</p>
                <p>{valueText(t, metric, selVal).long}</p>
              </div>
            )}
          </div>
          <div className="grid min-h-[190px] grid-cols-7 items-end gap-1.5 sm:gap-2">
            {chart.days.map((d, i) => {
              const v = values[i]
              const h = heights[i]
              const on = i === sel
              const text = v == null ? null : valueText(t, metric, v)
              return (
                <button
                  key={d}
                  type="button"
                  onClick={() => setPicked((p) => ({ ...p, [metric]: i }))}
                  aria-pressed={on}
                  aria-label={text ? `${dayLong(d)}, ${text.long}` : t('home.chart.noDay', '{{day}}, no data', { day: dayLong(d) })}
                  className="press group flex min-w-0 flex-col items-center justify-end gap-1 rounded-card pt-1"
                >
                  <span className={cn('num text-micro [[data-ts="2"]_&]:hidden', on ? 'font-bold text-ink' : 'text-ink2')}>{text ? text.short : <span aria-hidden>&ndash;</span>}</span>
                  <span
                    className={cn('block w-full rounded-[14px]', on ? 'bg-brand' : 'bg-brand-soft', v == null && 'border-2 border-dashed border-line bg-transparent')}
                    style={{ height: v == null ? 6 : Math.max(6, Math.round((h ?? 0) * 140)) }}
                  />
                </button>
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
