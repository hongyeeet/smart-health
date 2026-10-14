/**
 * The numbers and plain sentences the doctor brief shows, built in code from one timeline answer (GET /insights/timeline) so that no
 * model writes a number here. The health tiles use the same grading as the Insights Health overview (healthGrade.ts). The reasoning
 * line under each chart says only the distance from the person's own baseline (above, below or at), never good or bad.
 */
import type { TFunction } from 'i18next'
import type { InsightsTimeline, LearnedFact } from '@/data/types'
import { grade, statusWords, type GradeKind, type Graded } from '@/features/insights/healthGrade'
import { num } from '@/features/insights/shared'

export type PlotKey = 'glucose' | 'heart' | 'spo2' | 'bp'

export interface HealthTile {
  kind: GradeKind
  label: string
  value: string
  unit?: string
  graded: Graded
  /** the short word for where the number sits, e.g. "In baseline" */
  status: string
}

export interface PlotReason {
  key: PlotKey
  title: string
  /** one plain sentence on why the chart is worth reading */
  why: string
  /** the numbers, written from the timeline answer */
  saw: string
}

const gmiOf = (g: number | null) => (g == null ? null : 3.31 + 0.02392 * g * 18.016)
const mean = (xs: (number | null | undefined)[]) => {
  const v = xs.filter((x): x is number => x != null)
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null
}

/** "0.4 above your baseline of 8.8", "at your baseline of 8.8", or a plain "no baseline yet" */
function vsBaseline(t: TFunction, value: number | null, base: number | null, digits: number): string {
  if (value == null) return t('brief.noReading', 'no reading')
  if (base == null) return t('brief.noBaseline', 'no baseline yet')
  const d = value - base
  const ad = Math.abs(d).toFixed(digits)
  const b = base.toFixed(digits)
  if (Number(ad) === 0) return t('brief.atBaseline', 'at your baseline of {{b}}', { b })
  return d > 0
    ? t('brief.aboveBaseline', '{{d}} above your baseline of {{b}}', { d: ad, b })
    : t('brief.belowBaseline', '{{d}} below your baseline of {{b}}', { d: ad, b })
}

/** Days whose daily glucose average is in the highest or lowest 5 per cent (only with enough days to tell). Same rule as the Overview circles. */
export function stoodOutCount(data: InsightsTimeline): number {
  const vals = data.dayRows.map((r) => r.glucose.avg).filter((v): v is number => v != null)
  if (vals.length < 20) return 0
  const s = [...vals].sort((a, b) => a - b)
  const lo = s[Math.floor(s.length * 0.05)]!
  const hi = s[Math.ceil(s.length * 0.95) - 1]!
  return data.dayRows.filter((r) => r.glucose.avg != null && (r.glucose.avg > hi || r.glucose.avg < lo)).length
}

/** The six Health overview numbers, graded against the person's own 14 days before (or the first 14 days of the period). */
export function healthTiles(t: TFunction, data: InsightsTimeline): HealthTile[] {
  const v = data.values
  const b = data.baseline.health
  const ok = data.baseline.available
  const gmiBase = gmiOf(ok ? b.avgGlucose : null)
  const gmiBaseRounded = gmiBase == null ? null : Math.round(gmiBase * 10) / 10
  const rows: Omit<HealthTile, 'status'>[] = [
    {
      kind: 'glucose',
      label: t('insights.ho.avg', 'Avg glucose'),
      value: num(v.avgGlucose, 1),
      unit: v.avgGlucose != null ? 'mmol/L' : undefined,
      graded: grade('glucose', v.avgGlucose, ok ? b.avgGlucose : null),
    },
    {
      kind: 'gmi',
      label: t('insights.ho.gmi', 'Est. A1c (GMI)'),
      value: num(v.gmi, 1),
      unit: v.gmi != null ? '%' : undefined,
      graded: grade('gmi', v.gmi, gmiBaseRounded),
    },
    {
      kind: 'steps',
      label: t('insights.ho.steps', 'Steps a day'),
      value: num(v.stepsPerDay),
      graded: grade('steps', v.stepsPerDay, ok ? b.stepsPerDay : null),
    },
    {
      kind: 'cv',
      label: t('insights.ho.cv', 'Variation (CV)'),
      value: num(v.cv),
      unit: v.cv != null ? '%' : undefined,
      graded: grade('cv', v.cv, ok ? b.cv : null),
    },
    {
      kind: 'doses',
      label: t('insights.ho.doses', 'Doses taken'),
      value: num(v.dosesTakenPct),
      unit: v.dosesTakenPct != null ? '%' : undefined,
      graded: grade('doses', v.dosesTakenPct, null),
    },
    {
      kind: 'sensor',
      label: t('insights.ho.sensor', 'Sensor worn'),
      value: num(v.sensorWornPct),
      unit: v.sensorWornPct != null ? '%' : undefined,
      graded: grade('sensor', v.sensorWornPct, null),
    },
  ]
  return rows.map((r) => ({ ...r, status: statusWords(t, r.kind, r.graded) }))
}

/** One reasoning line per chart: why it matters, and what the numbers for the period say. Numbers come from the timeline only. */
export function plotReasons(t: TFunction, data: InsightsTimeline): PlotReason[] {
  const { dayRows, baseline, bp } = data
  const glucose = data.values.avgGlucose
  const glucoseBase = baseline.available ? baseline.health.avgGlucose : null
  const stood = stoodOutCount(data)
  const stoodText =
    stood === 0
      ? ''
      : stood === 1
        ? ` ${t('brief.stood1', '1 day stood out from the rest.')}`
        : ` ${t('brief.stoodN', '{{n}} days stood out from the rest.', { n: stood })}`

  const heart = mean(dayRows.map((r) => r.heart.avg))
  const heartBase = baseline.available ? baseline.daily.heart.mean : null
  const spo2 = mean(dayRows.map((r) => r.spo2.avg))
  const spo2Base = baseline.available ? baseline.daily.spo2.mean : null
  const spo2Low = dayRows.map((r) => r.spo2.min).filter((v): v is number => v != null)

  const bpCount = bp.length
  const bpSys = mean(bp.map((r) => r.systolic))
  const bpDia = mean(bp.map((r) => r.diastolic))
  const bpBaseOk = baseline.bpAvailable && baseline.bpSystolic != null && baseline.bpDiastolic != null

  return [
    {
      key: 'glucose',
      title: t('insights.tl.glucose', 'Glucose'),
      why: t('brief.why.glucose', 'Glucose is the main measure for your diabetes. The line shows how it moves through each day.'),
      saw:
        glucose == null
          ? t('brief.saw.none', 'No readings in this period.')
          : t('brief.saw.glucose', 'Average {{avg}} mmol/L, {{vs}}.', { avg: num(glucose, 1), vs: vsBaseline(t, glucose, glucoseBase, 1) }) + stoodText,
    },
    {
      key: 'heart',
      title: t('insights.tl.heart', 'Heart rate'),
      why: t('brief.why.heart', 'Heart rate changes with activity, stress, sleep and illness, so it is easier to read beside glucose.'),
      saw:
        heart == null
          ? t('brief.saw.none', 'No readings in this period.')
          : t('brief.saw.heart', 'Average {{avg}} bpm, {{vs}}.', { avg: num(heart, 0), vs: vsBaseline(t, heart, heartBase, 0) }),
    },
    {
      key: 'spo2',
      title: t('insights.tl.spo2', 'SpO2'),
      why: t('brief.why.spo2', 'SpO2 is the oxygen level in your blood. A steady line is easier to read than single readings.'),
      saw:
        spo2 == null
          ? t('brief.saw.none', 'No readings in this period.')
          : t('brief.saw.spo2', 'Average {{avg}}%, {{vs}}. Lowest daily average {{low}}%.', {
              avg: num(spo2, 1),
              vs: vsBaseline(t, spo2, spo2Base, 1),
              low: spo2Low.length ? num(Math.min(...spo2Low), 1) : '–',
            }),
    },
    {
      key: 'bp',
      title: t('insights.tl.bp', 'Blood pressure'),
      why: t('brief.why.bp', 'Blood pressure is a key measure for heart and kidney health. It is read best as a range over time.'),
      saw:
        bpCount === 0 || bpSys == null || bpDia == null
          ? t('brief.saw.noBp', 'No blood pressure readings in this period.')
          : t('brief.saw.bp', '{{n}} readings, average {{s}}/{{d}} mmHg. Baseline {{bs}}/{{bd}} mmHg.', {
              n: bpCount,
              s: num(bpSys, 0),
              d: num(bpDia, 0),
              bs: bpBaseOk ? baseline.bpSystolic : '–',
              bd: bpBaseOk ? baseline.bpDiastolic : '–',
            }),
    },
  ]
}

/** Learnt facts for the brief: the confirmed ones first, then the ones still waiting for the person. */
export function learnedRows(facts: LearnedFact[]): { id: string; statement: string; why: string; confirmed: boolean }[] {
  return [...facts]
    .sort((a, b) => Number(b.confirmed) - Number(a.confirmed))
    .map((f) => ({ id: f.id, statement: f.statement, why: f.why, confirmed: f.confirmed }))
}
