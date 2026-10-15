import type { GlucoseLevel } from '@/data/types'
import { appConfig } from '@/config/app'

/** minutes since midnight to "1:05 pm" */
export function clock(min: number): string {
  const h24 = Math.floor(min / 60) % 24
  const m = Math.round(min % 60)
  const h = h24 % 12 === 0 ? 12 : h24 % 12
  return `${h}:${String(m).padStart(2, '0')} ${h24 < 12 ? 'am' : 'pm'}`
}

/** 350 to "5 h 50 min" */
export function hm(min: number): string {
  const h = Math.floor(min / 60)
  const m = Math.round(min % 60)
  return h ? `${h} h ${m} min` : `${m} min`
}

export function glucoseLevel(v: number): GlucoseLevel {
  const r = appConfig.glucoseRanges
  if (v < r.veryLow) return 'very_low'
  if (v < r.low) return 'low'
  if (v <= r.high) return 'in_range'
  if (v <= r.veryHigh) return 'high'
  return 'very_high'
}

export const levelText: Record<GlucoseLevel, string> = {
  very_low: 'Very low',
  low: 'Low',
  in_range: 'In your range',
  high: 'Higher than your range',
  very_high: 'Much higher than your range',
}

export const num1 = (n: number) => (Math.round(n * 10) / 10).toFixed(1)
export const signed = (n: number) => `${n > 0 ? '+' : n < 0 ? '−' : ''}${Math.abs(Math.round(n * 10) / 10).toFixed(1)}`
export const thousands = (n: number) => n.toLocaleString('en-US')
export const nowMinutes = () => appConfig.demo.nowMinutes

export function shortDate(iso: string): string {
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}
export function weekdayShort(iso: string): string {
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('en-GB', { weekday: 'short' })
}
