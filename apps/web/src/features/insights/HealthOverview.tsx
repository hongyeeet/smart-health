/**
 * Insights → Overview, "Health overview": six numbers for the period, each coloured by how it sits against the person's OWN baseline (the 14 days
 * before the period). Green when it is within the baseline; yellow, orange, then red as it moves the wrong way. Every tile also says it in words
 * ("Slightly above", "Many missed"), so colour is never the only signal. Doses taken and sensor worn are graded by consistency, not by a baseline.
 * The cut-offs are placeholders for the clinical owner to confirm (docs/specs/insights-overview.md).
 */
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import type { InsightsTimeline } from '@/data/types'
import { cn } from '@/lib/cn'
import { dateLocale } from '@/lib/locale'
import { num } from './shared'

type Kind = 'glucose' | 'gmi' | 'cv' | 'steps' | 'doses' | 'sensor'
/** 0 within the baseline, 1 slightly off, 2 off, 3 far off; null when there is nothing to grade against */
export type Level = 0 | 1 | 2 | 3 | null

const level = (rel: number, cut: [number, number, number]): Level => (rel <= cut[0] ? 0 : rel <= cut[1] ? 1 : rel <= cut[2] ? 2 : 3)

export interface Graded {
  level: Level
  /** moved the good way by more than the within-baseline margin: the words say below (or above) the baseline, the colour stays green */
  better: boolean
}

/** Grade one reading. `baseline` is ignored for doses and sensor, which are graded on consistency alone. */
export function grade(kind: Kind, value: number | null, baseline: number | null): Graded {
  if (value == null) return { level: null, better: false }
  switch (kind) {
    case 'glucose': {
      if (baseline == null || baseline === 0) return { level: null, better: false }
      const r = (value - baseline) / baseline
      return { level: level(r, [0.05, 0.15, 0.3]), better: r < -0.05 }
    }
    case 'gmi': {
      if (baseline == null) return { level: null, better: false }
      const r = value - baseline
      return { level: level(r, [0.3, 0.7, 1.2]), better: r < -0.3 }
    }
    case 'cv': {
      if (baseline == null) return { level: null, better: false }
      const r = value - baseline
      return { level: level(r, [3, 6, 10]), better: r < -3 }
    }
    case 'steps': {
      if (baseline == null || baseline === 0) return { level: null, better: false }
      const r = (baseline - value) / baseline
      return { level: level(r, [0.1, 0.25, 0.4]), better: r < -0.1 }
    }
    case 'doses':
      return { level: level(100 - value, [10, 20, 40]), better: false }
    case 'sensor':
      return { level: level(100 - value, [10, 30, 50]), better: false }
  }
}

const TONE: Record<NonNullable<Level>, { box: string; text: string; dot: string }> = {
  0: { box: 'bg-ok-soft', text: 'text-ok', dot: 'bg-ok' },
  1: { box: 'bg-brass-soft', text: 'text-brass', dot: 'bg-brass' },
  2: { box: 'bg-warn-soft', text: 'text-warn', dot: 'bg-warn' },
  3: { box: 'bg-danger-soft', text: 'text-danger', dot: 'bg-danger' },
}

function statusWords(t: TFunction, kind: Kind, g: Graded): string {
  if (g.level == null) return t('insights.ho.noBaseline', 'No baseline yet')
  const l = g.level
  if (kind === 'doses')
    return [
      t('insights.ho.doses0', 'Consistent'),
      t('insights.ho.doses1', 'Some missed'),
      t('insights.ho.doses2', 'Many missed'),
      t('insights.ho.doses3', 'Most missed'),
    ][l]!
  if (kind === 'sensor')
    return [
      t('insights.ho.sensor0', 'Consistent'),
      t('insights.ho.sensor1', 'Some gaps'),
      t('insights.ho.sensor2', 'Many gaps'),
      t('insights.ho.sensor3', 'Mostly off'),
    ][l]!
  if (kind === 'steps') {
    if (l === 0 && g.better) return t('insights.ho.stepsUp', 'Above baseline')
    return [
      t('insights.ho.base0', 'In baseline'),
      t('insights.ho.below1', 'Slightly below'),
      t('insights.ho.below2', 'Below baseline'),
      t('insights.ho.below3', 'Well below'),
    ][l]!
  }
  if (l === 0 && g.better) return t('insights.ho.lower', 'Below baseline')
  return [
    t('insights.ho.base0', 'In baseline'),
    t('insights.ho.above1', 'Slightly above'),
    t('insights.ho.above2', 'Above baseline'),
    t('insights.ho.above3', 'Well above'),
  ][l]!
}

const gmiOf = (g: number | null) => (g == null ? null : 3.31 + 0.02392 * g * 18.016)

function Tile({ kind, label, value, unit, graded }: { kind: Kind; label: string; value: string; unit?: string; graded: Graded }) {
  const { t } = useTranslation()
  const tone = graded.level == null ? { box: 'bg-well', text: 'text-ink2', dot: 'bg-ink3' } : TONE[graded.level]
  return (
    <div className={cn('flex min-h-[5.75rem] min-w-0 flex-col justify-center gap-0.5 rounded-[14px] px-3 py-2.5', tone.box)}>
      <span className={cn('num flex flex-wrap items-baseline gap-x-1 text-xl font-bold leading-tight', tone.text)}>
        {value}
        {unit && <span className="text-micro font-normal text-ink3">{unit}</span>}
      </span>
      <span className="break-words text-micro leading-tight text-ink2">{label}</span>
      <span className={cn('mt-0.5 flex items-start gap-1.5 break-words text-micro font-bold leading-tight', tone.text)}>
        <span className={cn('mt-[3px] h-2 w-2 flex-none rounded-full', tone.dot)} aria-hidden />
        <span className="min-w-0">{statusWords(t, kind, graded)}</span>
      </span>
    </div>
  )
}

export function HealthOverview({ data }: { data: InsightsTimeline }) {
  const { t } = useTranslation()
  const v = data.values
  const b = data.baseline.health
  const ok = data.baseline.available
  const gmiBase = gmiOf(ok ? b.avgGlucose : null)
  const tiles: { kind: Kind; label: string; value: string; unit?: string; g: Graded }[] = [
    {
      kind: 'glucose',
      label: t('insights.ho.avg', 'Average glucose'),
      value: num(v.avgGlucose, 1),
      unit: v.avgGlucose != null ? 'mmol/L' : undefined,
      g: grade('glucose', v.avgGlucose, ok ? b.avgGlucose : null),
    },
    {
      kind: 'gmi',
      label: t('insights.ho.gmi', 'Estimated A1c (GMI)'),
      value: num(v.gmi, 1),
      unit: v.gmi != null ? '%' : undefined,
      g: grade('gmi', v.gmi, gmiBase == null ? null : Math.round(gmiBase * 10) / 10),
    },
    { kind: 'steps', label: t('insights.ho.steps', 'Steps a day'), value: num(v.stepsPerDay), g: grade('steps', v.stepsPerDay, ok ? b.stepsPerDay : null) },
    {
      kind: 'cv',
      label: t('insights.ho.cv', 'Glucose variation (CV)'),
      value: num(v.cv),
      unit: v.cv != null ? '%' : undefined,
      g: grade('cv', v.cv, ok ? b.cv : null),
    },
    {
      kind: 'doses',
      label: t('insights.ho.doses', 'Doses taken'),
      value: num(v.dosesTakenPct),
      unit: v.dosesTakenPct != null ? '%' : undefined,
      g: grade('doses', v.dosesTakenPct, null),
    },
    {
      kind: 'sensor',
      label: t('insights.ho.sensor', 'Sensor worn'),
      value: num(v.sensorWornPct),
      unit: v.sensorWornPct != null ? '%' : undefined,
      g: grade('sensor', v.sensorWornPct, null),
    },
  ]
  const dm = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString(dateLocale('en-GB'), { day: 'numeric', month: 'short' })
  return (
    <section aria-label={t('insights.ho.title', 'Health overview')} className="flex flex-col gap-3 rounded-card border border-line bg-card p-4 shadow-lift">
      <div className="flex flex-wrap items-baseline justify-between gap-x-2">
        <h2 className="text-h2 font-bold">{t('insights.ho.title', 'Health overview')}</h2>
        <span className="text-sub text-ink3">{t('insights.ho.period', '{{from}} to {{to}}', { from: dm(data.period.start), to: dm(data.period.end) })}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 [[data-ts='2']_&]:grid-cols-1">
        {tiles.map((x) => (
          <Tile key={x.kind} kind={x.kind} label={x.label} value={x.value} unit={x.unit} graded={x.g} />
        ))}
      </div>
      <ul className="flex flex-wrap items-center gap-x-3 gap-y-1 text-micro text-ink3" aria-label={t('insights.ho.key', 'What the colours mean')}>
        {([0, 1, 2, 3] as const).map((l) => (
          <li key={l} className="flex items-center gap-1.5">
            <span className={cn('h-2 w-2 rounded-full', TONE[l].dot)} aria-hidden />
            {[t('insights.ho.key0', 'In baseline'), t('insights.ho.key1', 'Slightly off'), t('insights.ho.key2', 'Off'), t('insights.ho.key3', 'Far off')][l]}
          </li>
        ))}
      </ul>
    </section>
  )
}
