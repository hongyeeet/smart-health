/**
 * Insights → Overview, "Health overview": six numbers for the period, each coloured by how it sits against the person's OWN baseline (the 14 days
 * before the period): green within it, yellow, orange, then red as it moves the wrong way. Each tile is three short lines (what, the number, a
 * word for where it sits), so it stays tidy at any text size. Doses taken and sensor worn are graded by consistency. See healthGrade.ts.
 */
import { useTranslation } from 'react-i18next'
import type { InsightsTimeline } from '@/data/types'
import { cn } from '@/lib/cn'
import { dateLocale } from '@/lib/locale'
import { KEY_LEVELS, NEUTRAL, TONE, grade, statusWords, type GradeKind, type Graded } from './healthGrade'
import { num } from './shared'

const gmiOf = (g: number | null) => (g == null ? null : 3.31 + 0.02392 * g * 18.016)

export function GradeTile({ kind, label, value, unit, graded }: { kind: GradeKind; label: string; value: string; unit?: string; graded: Graded }) {
  const { t } = useTranslation()
  const tone = graded.level == null ? NEUTRAL : TONE[graded.level]
  return (
    <div className={cn('flex min-w-0 flex-col gap-px rounded-[12px] px-2.5 py-2', tone.box)}>
      <span className="truncate text-[11px] leading-tight text-ink2">{label}</span>
      <span className={cn('num flex items-baseline gap-1 text-lg font-bold leading-tight', tone.text)}>
        {value}
        {unit && <span className="text-[10px] font-normal text-ink3">{unit}</span>}
      </span>
      <span className={cn('flex items-center gap-1 text-[11px] font-bold leading-tight', tone.text)}>
        <span className={cn('h-1.5 w-1.5 flex-none rounded-full', tone.dot)} aria-hidden />
        <span className="min-w-0 truncate">{statusWords(t, kind, graded)}</span>
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
  const tiles: { kind: GradeKind; label: string; value: string; unit?: string; g: Graded }[] = [
    {
      kind: 'glucose',
      label: t('insights.ho.avg', 'Avg glucose'),
      value: num(v.avgGlucose, 1),
      unit: v.avgGlucose != null ? 'mmol/L' : undefined,
      g: grade('glucose', v.avgGlucose, ok ? b.avgGlucose : null),
    },
    {
      kind: 'gmi',
      label: t('insights.ho.gmi', 'Est. A1c (GMI)'),
      value: num(v.gmi, 1),
      unit: v.gmi != null ? '%' : undefined,
      g: grade('gmi', v.gmi, gmiBase == null ? null : Math.round(gmiBase * 10) / 10),
    },
    { kind: 'steps', label: t('insights.ho.steps', 'Steps a day'), value: num(v.stepsPerDay), g: grade('steps', v.stepsPerDay, ok ? b.stepsPerDay : null) },
    {
      kind: 'cv',
      label: t('insights.ho.cv', 'Variation (CV)'),
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
  const keyWords = [t('insights.ho.key0', 'In baseline'), t('insights.ho.key1', 'Slightly off'), t('insights.ho.key2', 'Off'), t('insights.ho.key3', 'Far off')]
  return (
    <section aria-label={t('insights.ho.title', 'Health overview')} className="flex flex-col gap-2.5 rounded-card border border-line bg-card p-3.5 shadow-lift">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-body font-bold">{t('insights.ho.title', 'Health overview')}</h2>
        <span className="text-[11px] text-ink3">{t('insights.ho.period', '{{from}} to {{to}}', { from: dm(data.period.start), to: dm(data.period.end) })}</span>
      </div>
      <div className="grid grid-cols-2 gap-1.5 [[data-ts='2']_&]:grid-cols-1">
        {tiles.map((x) => (
          <GradeTile key={x.kind} kind={x.kind} label={x.label} value={x.value} unit={x.unit} graded={x.g} />
        ))}
      </div>
      <ul className="flex flex-wrap items-center gap-x-2.5 gap-y-0.5 text-[10px] text-ink3" aria-label={t('insights.ho.key', 'What the colours mean')}>
        {KEY_LEVELS.map((l) => (
          <li key={l} className="flex items-center gap-1">
            <span className={cn('h-1.5 w-1.5 rounded-full', TONE[l].dot)} aria-hidden />
            {keyWords[l]}
          </li>
        ))}
      </ul>
    </section>
  )
}
