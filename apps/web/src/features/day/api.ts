import { useQuery } from '@tanstack/react-query'
import { request } from '@/data/repositories/http'

/** Wire types for the Day view (services/api/app/schemas/day.py). Times are minutes after local midnight, Singapore. */

export type MarkerKind = 'meal' | 'dose' | 'workout' | 'symptom'
export type DoseState = 'taken' | 'late' | 'not_confirmed' | 'missed'

export interface DayPoint {
  minute: number
  glucoseMmol: number | null
  heartRateBpm: number | null
  steps: number | null
}

export interface DaySleepBand {
  startMinute: number
  endMinute: number
}

export interface DayMarkerRow {
  label: string
  value: string
}

export interface DayMarker {
  id: string
  kind: MarkerKind
  minute: number
  endMinute: number | null
  clock: string
  title: string
  subtitle: string | null
  status: DoseState | null
  flags: ('salt' | 'sugar')[]
  rows: DayMarkerRow[]
  outcome: string
}

export interface DayMoodDot {
  id: string
  minute: number
  clock: string
  mood: number | null
  stressSelf: number | null
  energy: number | null
}

export interface DayView {
  date: string
  label: string
  hasData: boolean
  prevDate: string | null
  nextDate: string | null
  targetLow: number
  targetHigh: number
  sleepHours: number | null
  series: DayPoint[]
  sleep: DaySleepBand[]
  markers: DayMarker[]
  mood: DayMoodDot[]
}

export interface DayDates {
  latestDate: string
  dates: string[]
}

export const dayKeys = {
  all: ['day'] as const,
  dates: (days: number) => ['day', 'dates', days] as const,
  day: (date: string) => ['day', date] as const,
}

export const getDay = (date: string) => request<DayView>(`/day/${encodeURIComponent(date)}`)
export const getDayDates = (days: number) => request<DayDates>(`/day/dates?days=${days}`)

/** The date arrows and the default day. Dates are newest first. */
export const useDayDates = (days = 90) => useQuery({ queryKey: dayKeys.dates(days), queryFn: () => getDayDates(days), staleTime: 60_000 })

export const useDay = (date: string) => useQuery({ queryKey: dayKeys.day(date), queryFn: () => getDay(date), enabled: /^\d{4}-\d{2}-\d{2}$/.test(date) })
