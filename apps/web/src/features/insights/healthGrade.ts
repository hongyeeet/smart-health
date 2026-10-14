/**
 * Grading a reading against the person's OWN baseline, for the Health overview and the day page: 0 within the baseline, 1 slightly off, 2 off,
 * 3 far off (null when there is nothing to grade against). The words say it too, so colour is never the only signal. The cut-offs are placeholders for
 * the clinical owner to confirm (docs/specs/insights-overview.md); doses and sensor are graded on consistency, not on a baseline.
 */
import type { TFunction } from 'i18next'

export type GradeKind = 'glucose' | 'gmi' | 'cv' | 'steps' | 'doses' | 'sensor' | 'heart' | 'spo2' | 'bp'
export type Level = 0 | 1 | 2 | 3 | null
export interface Graded {
  level: Level
  /** moved the good way by more than the within-baseline margin: the words say below (or above) the baseline, the colour stays green */
  better: boolean
}

const level = (rel: number, cut: [number, number, number]): Level => (rel <= cut[0] ? 0 : rel <= cut[1] ? 1 : rel <= cut[2] ? 2 : 3)
const rel = (v: number, b: number) => (v - b) / b

export function grade(kind: GradeKind, value: number | null, baseline: number | null): Graded {
  const none: Graded = { level: null, better: false }
  if (value == null) return none
  if (kind === 'doses') return { level: level(100 - value, [10, 20, 40]), better: false }
  if (kind === 'sensor') return { level: level(100 - value, [10, 30, 50]), better: false }
  if (baseline == null || baseline === 0) return none
  switch (kind) {
    case 'glucose': {
      const r = rel(value, baseline)
      return { level: level(r, [0.05, 0.15, 0.3]), better: r < -0.05 }
    }
    case 'gmi': {
      const r = value - baseline
      return { level: level(r, [0.3, 0.7, 1.2]), better: r < -0.3 }
    }
    case 'cv': {
      const r = value - baseline
      return { level: level(r, [3, 6, 10]), better: r < -3 }
    }
    case 'steps': {
      const r = (baseline - value) / baseline
      return { level: level(r, [0.1, 0.25, 0.4]), better: r < -0.1 }
    }
    case 'heart': {
      const r = rel(value, baseline)
      return { level: level(r, [0.05, 0.12, 0.2]), better: r < -0.05 }
    }
    case 'bp': {
      const r = rel(value, baseline)
      return { level: level(r, [0.03, 0.08, 0.15]), better: r < -0.03 }
    }
    case 'spo2': {
      const r = baseline - value
      return { level: level(r, [0.5, 1, 2]), better: r < -0.5 }
    }
  }
  return none
}

/** the colour classes of each level (Tailwind tokens: ok, brass, warn, danger) */
export const TONE: Record<NonNullable<Level>, { box: string; text: string; dot: string }> = {
  0: { box: 'bg-ok-soft', text: 'text-ok', dot: 'bg-ok' },
  1: { box: 'bg-brass-soft', text: 'text-brass', dot: 'bg-brass' },
  2: { box: 'bg-warn-soft', text: 'text-warn', dot: 'bg-warn' },
  3: { box: 'bg-danger-soft', text: 'text-danger', dot: 'bg-danger' },
}
export const NEUTRAL = { box: 'bg-well', text: 'text-ink2', dot: 'bg-ink3' }

/** Short words for a graded reading ("Slightly above", "Several missed"). */
export function statusWords(t: TFunction, kind: GradeKind, g: Graded): string {
  if (g.level == null) return t('insights.ho.noBaseline', 'No baseline yet')
  const l = g.level
  if (kind === 'doses')
    return [
      t('insights.ho.doses0', 'Consistent'),
      t('insights.ho.doses1', 'Some missed'),
      t('insights.ho.doses2', 'Several missed'),
      t('insights.ho.doses3', 'Most missed'),
    ][l]!
  if (kind === 'sensor')
    return [
      t('insights.ho.sensor0', 'Consistent'),
      t('insights.ho.sensor1', 'Some gaps'),
      t('insights.ho.sensor2', 'Many gaps'),
      t('insights.ho.sensor3', 'Mostly off'),
    ][l]!
  if (kind === 'steps' || kind === 'spo2') {
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

/** the small key under a graded group of tiles */
export const KEY_LEVELS = [0, 1, 2, 3] as const
