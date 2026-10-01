/**
 * Domain types. They mirror docs/specs/schema.md closely enough that the mock repository can be
 * replaced by the real API without touching screens. Statuses use the standard names from memory.md.
 */
import type { RouteId } from '@/app/routeIds'

export type EvidenceStatus = 'observed' | 'derived' | 'inferred' | 'reference_matched'
export type DoseStatus = 'scheduled' | 'due' | 'taken' | 'taken_late_logged' | 'unconfirmed' | 'missed' | 'skipped_by_plan'
export type MissReason = 'forgot' | 'side_effects' | 'ran_out' | 'felt_fine' | 'cost' | 'away_from_home' | 'other'
export type GlucoseLevel = 'very_low' | 'low' | 'in_range' | 'high' | 'very_high'
export type Intensity = 'light' | 'moderate' | 'vigorous'
export type WorkoutType = 'aerobic' | 'strength' | 'mixed' | 'flexibility'
export type Period = 7 | 30 | 90
export type Locale = 'en' | 'zh' | 'ms' | 'ta'

export interface Patient {
  name: string
  initials: string
  age: number
  birthYear: number
  occupation: string
  diagnosedYearsAgo: number
  lastHba1c: { value: number; monthsAgo: number }
  targetRange: [number, number]
  baselineFasting: [number, number]
}

export interface Medication {
  id: string
  name: string
  strength: string
  kind: 'prescription' | 'otc' | 'supplement' | 'tcm'
  times: string[]
  withFood: boolean
  purpose: string
  badge: 'interaction' | 'not_checked' | null
  refill: { daysLeft: number; unitsLeft: number } | null
  sideEffects: string[]
}

export interface Dose {
  id: string
  medId: string
  label: string
  time: string
  withFood: boolean
  status: DoseStatus
  day: 'today' | 'yesterday'
  reason?: MissReason
}

export interface GlucosePoint {
  /** minutes since midnight */
  t: number
  v: number
}

export interface DayMeal {
  id: string
  t: number
  name: string
  carbsG: number
  flags: ('high_salt' | 'high_sugar')[]
  rise?: number
  estimated: boolean
}
export interface DayDose {
  id: string
  t: number
  name: string
  status: Exclude<DoseStatus, 'scheduled' | 'due'> | 'due'
}
export interface DayWorkout {
  id: string
  t: number
  minutes: number
  label: string
  intensity: Intensity
  glucoseChange2h?: number
}
export interface DaySymptom {
  id: string
  t: number
  label: string
  severity: number
}
export interface DayTimeline {
  date: string
  weekday: string
  label: string
  /** end of recorded data in minutes (today stops at now) */
  endT: number
  glucose: GlucosePoint[]
  /** [startT, endT] where the sensor had no data */
  glucoseGaps: [number, number][]
  hr: GlucosePoint[]
  stepsByHour: number[]
  sleep: { start: number; end: number; label: string } | null
  meals: DayMeal[]
  doses: DayDose[]
  workouts: DayWorkout[]
  symptoms: DaySymptom[]
  inRangePct: number
}

export interface GridCell {
  text: string
  level: 'good' | 'mid' | 'low' | 'none'
}
export interface WeekGrid {
  days: { date: string; short: string }[]
  rows: { key: string; label: string; cells: GridCell[] }[]
}

export interface SeriesPoint {
  date: string
  v: number | null
}
export interface Trend {
  label: string
  unit: string
  points: SeriesPoint[]
  baseline: [number, number]
  summary: string
}

export interface FoodResponse {
  id: string
  name: string
  rise: number
  min: number
  max: number
  n: number
  learning: boolean
}

export interface WorkoutRecord {
  id: string
  date: string
  label: string
  type: WorkoutType
  intensity: Intensity
  minutes: number
  glucoseChange2h?: number
}

export interface Insights {
  weekGrid: WeekGrid
  whatChanged: { id: string; text: string; to: RouteId }[]
  fasting: Trend
  steps: Trend
  sleep: Trend
  mood: { date: string; mood: number; stress: number }[]
  timeInRange: { last24h: number; week: number; segments: { level: GlucoseLevel; pct: number }[] }
  sprint: { day: number; of: number; deviceLabel: string; avgMmol: number; gmi: number; cv: number }
  foods: FoodResponse[]
  activity: {
    moderateMin: number
    moderateGoal: number
    strength: number
    strengthGoal: number
    weeks: { label: string; light: number; moderate: number; vigorous: number }[]
    mix: { label: string; count: number }[]
    workouts: WorkoutRecord[]
    stepsToday: number
    stepsAvg7: number
    stepsBaseline: number
  }
  medication: {
    adherencePct: number
    taken: number
    scheduled: number
    reasons: { reason: string; count: number }[]
    timeline: { med: string; cells: DoseStatus[] }[]
    fastingOverlay: number[]
    days: string[]
  }
  patterns: { id: string; text: string; n: number }[]
}

export interface MemoryFact {
  id: string
  category: 'routine' | 'preference' | 'barrier' | 'food_response' | 'activity'
  statement: string
  confidence: 1 | 2 | 3
  evidence: string
  evidenceTo: RouteId
  status: 'active' | 'proposed'
  evidenceStatus: EvidenceStatus
}

export interface WeekCompare {
  rows: { label: string; then: string; now: string; flagged?: boolean }[]
  streams: string[]
  stillLearning: string
}

export interface PreventiveItem {
  id: string
  label: string
  status: 'overdue' | 'due_soon' | 'ok' | 'unknown'
  detail: string
}
export interface Appointment {
  id: string
  label: string
  when: string
  inDays: number
  place: string
}
export interface CarePlan {
  appointment: Appointment
  preventive: PreventiveItem[]
  questions: { id: string; text: string; origin: 'user' | 'refused_chat' | 'clash' | 'side_effect' }[]
}

export interface Notice {
  id: string
  kind: 'dose' | 'checkin' | 'nudge' | 'brief' | 'refill' | 'appointment'
  title: string
  body: string
  when: string
  to?: RouteId
  unread: boolean
}

export interface ConnectedSource {
  id: string
  label: string
  detail: string
  status: 'connected' | 'allowed'
  synced: string
}

export interface RecentEntry {
  id: string
  kind: 'meal' | 'glucose' | 'workout' | 'symptom' | 'checkin'
  title: string
  detail: string
  when: string
  date: string
}

export interface HomeData {
  greeting: string
  dateLabel: string
  alert: { text: string; to: RouteId } | null
  tiles: { key: 'glucose' | 'activity' | 'sleep' | 'mood'; label: string; value: string; unit: string; sub: string; to: RouteId }[]
  dosesDue: Dose[]
  unconfirmed: Dose | null
  exercisePrompt: { text: string } | null
  checkin: { id: string; question: string } | null
  whatChanged: { id: string; text: string; to: RouteId }[]
  next: { title: string; detail: string }
  sources: ConnectedSource[]
  unreadNotices: number
  sprintDay: number
  sprintOf: number
}

export interface ScanField {
  key: string
  label: string
  value: string | null
  confidence: 'high' | 'check' | 'unreadable'
}
export interface ScanResult {
  drug: string
  fields: ScanField[]
  schedule: { time: string; label: string }[]
  interaction: { a: string; b: string } | null
}

export interface ChatReply {
  kind: 'normal' | 'safety'
  text: string
  actions?: { id: 'add_question' | 'dismiss' | 'open_week' | 'open_med'; label: string }[]
}

export interface BriefData {
  initials: string
  birthYear: number
  period: string
  completeness: { stream: string; pct: number }[]
  top3: { id: string; text: string; evidence: string }[]
  patterns: { id: string; text: string; n: number }[]
  symptoms: { date: string; label: string; severity: number }[]
  preventive: PreventiveItem[]
  questions: string[]
  dayTraces: { kind: 'best' | 'worst' | 'typical'; date: string }[]
}

export type LogKind = 'meal' | 'glucose' | 'workout' | 'symptom' | 'checkin'

export interface LogResult {
  kind: LogKind
  title: string
  landedIn: string
  detail: string
  /** supporting numbers shown on the confirmation */
  lines: string[]
  related: RouteId
  day: string
  flag?: { text: string; level: GlucoseLevel | 'info' }
  swap?: { text: string; source: string }
  urgent?: boolean
}
