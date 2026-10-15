/**
 * The four numbers at the top of the Glucose page (average, estimated A1c, ups and downs, sensor worn). Each is coloured by how it sits
 * against the person's own baseline (healthGrade.ts), and the words say it too.
 */
import { useTranslation } from 'react-i18next'
import type { InsightsBand, InsightsGlucoseMetrics, InsightsTimeline } from '@/data/types'
import { cn } from '@/lib/cn'
import { NEUTRAL, TONE, grade, statusWords, type GradeKind, type Graded } from '../healthGrade'
import { num } from '../shared'

/** Estimated A1c (%) from a mean glucose in mmol/L: the same formula the Health overview uses. */
const gmiOf = (g: number | null) => (g == null ? null : 3.31 + 0.02392 * g * 18.016)

function StatTile({ kind, label, value, unit, graded }: { kind: GradeKind; label: string; value: string; unit?: string; graded: Graded }) {
  const { t } = useTranslation()
  const tone = graded.level == null ? NEUTRAL : TONE[graded.level]
  return (
    <div className={cn('flex min-w-0 flex-col justify-center gap-px rounded-[12px] px-3 py-2.5', tone.box)}>
      <span className="truncate text-[12px] leading-[15px] text-ink2">{label}</span>
      <span className={cn('num flex items-baseline whitespace-nowrap text-[22px] font-bold leading-[26px]', tone.text)}>
        {value}
        {unit && <span className="ml-1 text-[12px] font-normal text-ink3">{unit}</span>}
      </span>
      <span className={cn('flex min-w-0 items-center gap-[5px] text-[12px] font-bold leading-[15px]', tone.text)}>
        <span className={cn('h-2 w-2 flex-none rounded-full', tone.dot)} aria-hidden />
        <span className="min-w-0 truncate">{statusWords(t, kind, graded)}</span>
      </span>
    </div>
  )
}

export function StatTiles({ metrics, timeline }: { metrics: InsightsGlucoseMetrics; timeline: InsightsTimeline | undefined }) {
  const { t } = useTranslation()
  const base = timeline?.baseline.available ? timeline.baseline.health : null
  const gmiBase = gmiOf(base?.avgGlucose ?? null)
  const tiles: { kind: GradeKind; label: string; value: string; unit?: string; graded: Graded }[] = [
    {
      kind: 'glucose',
      label: t('insights.glucose.average', 'Average'),
      value: num(metrics.mean, 1),
      unit: metrics.mean != null ? 'mmol/L' : undefined,
      graded: grade('glucose', metrics.mean, base?.avgGlucose ?? null),
    },
    {
      kind: 'gmi',
      label: t('insights.glucose.gmi', 'Estimated A1c (GMI)'),
      value: num(metrics.gmi, 1),
      unit: metrics.gmi != null ? '%' : undefined,
      graded: grade('gmi', metrics.gmi, gmiBase == null ? null : Math.round(gmiBase * 10) / 10),
    },
    {
      kind: 'cv',
      label: t('insights.glucose.cv', 'Ups and downs (CV)'),
      value: num(metrics.cv),
      unit: metrics.cv != null ? '%' : undefined,
      graded: grade('cv', metrics.cv, base?.cv ?? null),
    },
    {
      kind: 'sensor',
      label: t('insights.glucose.worn', 'Sensor worn'),
      value: num(metrics.coverage),
      unit: metrics.coverage != null ? '%' : undefined,
      graded: grade('sensor', metrics.coverage, null),
    },
  ]
  return (
    <div className="grid grid-cols-2 gap-3">
      {tiles.map((x) => (
        <StatTile key={x.kind} kind={x.kind} label={x.label} value={x.value} unit={x.unit} graded={x.graded} />
      ))}
    </div>
  )
}

/** Share of readings in each band, as one bar and a legend. The in-range share is the big number. */
const BANDS = [
  { key: 'very_low', label: ['charts.level.veryLow', 'Very low'], fill: 'bg-danger' },
  { key: 'low', label: ['charts.level.low', 'Low'], fill: 'bg-danger/70' },
  { key: 'in_range', label: ['charts.level.inRange', 'In range'], fill: 'bg-ok' },
  { key: 'high', label: ['charts.level.high', 'High'], fill: 'bg-brass' },
  { key: 'very_high', label: ['charts.level.veryHigh', 'Very high'], fill: 'bg-warn' },
] as const

const fmtPct = (p: number) => (p === 0 ? '0%' : `${num(p, 1)}%`)

export function TimeInRange({ bands, low, high }: { bands: InsightsBand[]; low: number; high: number }) {
  const { t } = useTranslation()
  const pct = (k: string) => bands.find((b) => b.key === k)?.pct ?? 0
  return (
    <section className="flex flex-col gap-3 rounded-card border border-line bg-card px-5 py-4 shadow-lift">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-sub font-bold">{t('insights.glucose.timeInRange', 'Time in range')}</h2>
        <span className="num whitespace-nowrap text-[13px] text-ink3">{t('insights.glucose.rangeLimits', '{{low}} to {{high}} mmol/L', { low, high })}</span>
      </div>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-6">
        <div className="flex-none">
          <div className="num whitespace-nowrap text-[44px] font-bold leading-[46px] text-ok">{`${Math.round(pct('in_range'))}%`}</div>
          <div className="text-[13px] leading-[18px] text-ink3">{t('insights.glucose.ofReadings', 'of readings in range')}</div>
        </div>
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex h-[22px] gap-0.5 overflow-hidden rounded-full">
            {BANDS.map((b) => (
              <div key={b.key} className={cn('h-full min-w-0', b.fill)} style={{ width: `${pct(b.key)}%` }} />
            ))}
          </div>
          <div className="mt-3 grid grid-cols-3 gap-x-3 gap-y-3 md:grid-cols-5">
            {BANDS.map((b) => (
              <div key={b.key} className="min-w-0">
                <div className="flex items-center gap-1.5 whitespace-nowrap text-[13px] leading-[18px] text-ink2">
                  <span className={cn('h-2 w-2 flex-none rounded-full', b.fill)} aria-hidden />
                  {t(b.label[0], b.label[1])}
                </div>
                <div className="num mt-0.5 whitespace-nowrap text-[17px] font-bold leading-6">{fmtPct(pct(b.key))}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
