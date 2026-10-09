/**
 * Domain types. They mirror docs/specs/schema.md closely enough that the mock repository can be
 * replaced by the real API without touching screens. Statuses use the standard names from memory.md.
 */
import type { RouteId } from '@/app/routeIds'

export type EvidenceStatus = 'observed' | 'derived' | 'inferred' | 'reference_matched'
export type DoseStatus = 'scheduled' | 'due' | 'taken' | 'taken_late_logged' | 'unconfirmed' | 'missed' | 'skipped_by_plan'
export type MissReason = 'forgot' | 'side_effects' | 'ran_out' | 'felt_fine' | 'cost' | 'away_from_home' | 'other'
/** The answer to "Why was it not confirmed?": a reason it was missed, or "I took it, I just forgot to log it". */
export type MissAnswer = MissReason | 'took_it'
export type GlucoseLevel = 'very_low' | 'low' | 'in_range' | 'high' | 'very_high'
export type Intensity = 'light' | 'moderate' | 'vigorous'
export type WorkoutType = 'aerobic' | 'strength' | 'mixed' | 'flexibility'
/** the exercise types stored in `exercise_logs.type` (data model v2) */
export type ExerciseKind = 'strength' | 'walking' | 'running' | 'cycling' | 'swimming' | 'hiit' | 'sports' | 'yoga_pilates' | 'stretching_mobility' | 'dance' | 'household_gardening' | 'other'
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
  /** Taken only when needed: no dose times, no reminders, no supply estimate. */
  asNeeded?: boolean
  purpose: string
  badge: 'interaction' | 'not_checked' | null
  refill: { daysLeft: number; unitsLeft: number } | null
  sideEffects: string[]
}

/** A web page the explanation was based on. */
export interface WebSource {
  title: string
  url: string
}

/** What a medicine is for and its common side effects, in plain words, with the web pages they came from (prd F3). */
export interface MedicineExplanation {
  /** `not_identified`: the product could not be identified, so nothing is explained. */
  status: 'ready' | 'not_identified'
  purpose: string
  sideEffects: string[]
  tellDoctor: string
  sources: WebSource[]
  generatedAt: string
}

/** One medicine on its own page (H6). `directions` is the label text exactly as saved; `explanation` is empty until it is made. */
export interface MedicationDetail extends Medication {
  directions: string | null
  explanation: MedicineExplanation | null
}

/** One dose on the Home page. `title` says what to take ("Metformin, 1 Tab"), not how strong it is. */
export interface DoseItem {
  id: string
  title: string
  time: string
  withFood: boolean
  /** "Yesterday's evening dose" */
  whenLabel: string
}

/** What Home shows about medicines today: what is due now, what was not confirmed, and the next dose (prd F4). */
export interface DosesToday {
  hasMedicines: boolean
  due: DoseItem[]
  unconfirmed: DoseItem[]
  takenToday: number
  next: { title: string; when: string } | null
}

/** Two of the person's medicines that may clash (prd F5). `text` is always the fixed wording: it never says to stop a medicine. */
export interface ClashAlert {
  id: string
  medA: string
  medB: string
  text: string
  summary: string
  origin: 'database' | 'ai' | 'both'
  sources: WebSource[]
  /** The doctor question for this pair is already saved. */
  questionAdded: boolean
  /** When the alert was first raised (ISO time), if the server sent it. */
  raisedAt?: string | null
}

export interface ClashStatus {
  /** A check is running now, so more alerts may appear in a few seconds. */
  checking: boolean
  /** The AI half of the latest check could not finish; the database half still ran. */
  checkIncomplete: boolean
  alerts: ClashAlert[]
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
export type SymptomWhen = 'now' | 'at'
export interface SymptomDetail {
  when: SymptomWhen
  whenLabel?: string
  duration?: string
  side?: string
  relation?: string
  feel?: string
  /** pulled from the sensor at the moment of logging */
  glucose?: { v: number; trend: 'rising' | 'steady' | 'falling' }
}
export interface EmergencyContact {
  name: string
  relation: string
  phone: string
  email: string
  channels: ('message' | 'email' | 'call')[]
  consent: boolean
}

export interface DaySymptom {
  id: string
  t: number
  label: string
  severity: number
  detail?: SymptomDetail
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
  /** heart rate and SpO2 trended beside glucose (simulated in the demo) */
  wearables: { restingHr: Trend; spo2: Trend }
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
  kind: LogKind
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

/** Confidence level derived from the numeric score: >= 0.85 high, > 0 check, 0/null unreadable. */
export type ScanConfidenceLevel = 'high' | 'check' | 'unreadable'

export interface ScanField {
  key: string
  label: string
  /** null means the model could not read this field — never 0 or empty string (rules.md 3) */
  value: string | null
  /** raw model confidence, 0–1 */
  confidence: number
  /** the text the model found on the label, so the user can verify (null if none) */
  sourceText: string | null
  /** derived for the UI from confidence */
  level: ScanConfidenceLevel
}

export interface ScanScheduleItem {
  time: string
  label: string
}

export interface ScanResult {
  scanId: string
  /** what kind of product the model thinks this is */
  itemType: 'prescription_label' | 'blister_or_box' | 'supplement' | 'tcm' | 'otc' | 'unknown'
  status: 'uploaded' | 'extracting' | 'extracted' | 'failed'
  /** the medicine name, pulled from the name field for convenience */
  drug: string
  fields: ScanField[]
  /** parsed dose schedule (times + meal context), may be empty until parsed */
  schedule: ScanScheduleItem[]
  /** short plain-language description of what the medicine is for, from drug_reference or the model */
  description: string | null
  /** interaction hint, if the clash checker found one (E3-2/E6-1 populates this) */
  interaction: { a: string; b: string } | null
  /** model that produced the extraction, for audit */
  modelId: string | null
  error: string | null
  /** "confirm": one medicine read clearly, the person checks it. "manual": the person types the form (unreadable, low confidence, a
   *  missing required field, a drug we cannot identify, or several medicines). */
  /** The label says "when necessary": the medicine has no dose times. */
  asNeeded: boolean
  reviewMode: 'confirm' | 'manual'
  /** Stable reason codes behind "manual", for logging and tests. */
  reasons: string[]
  /** Why, in plain words, when the mode is "manual". */
  notice: string | null
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
  symptoms: { date: string; label: string; severity: number; detail?: string }[]
  /** self-reported awareness of lows, from the post-low question */
  awareness: string | null
  preventive: PreventiveItem[]
  questions: string[]
  dayTraces: { kind: 'best' | 'worst' | 'typical'; date: string }[]
}

export type LogKind = 'meal' | 'workout' | 'symptom' | 'checkin'

export interface LogResult {
  id: string
  kind: LogKind
  title: string
  landedIn: string
  detail: string
  /** supporting numbers shown on the confirmation */
  lines: string[]
  related: RouteId
  day: string
  flag?: { text: string; level: 'info' | 'in_range' | 'high' }
  swap?: { text: string; source: string }
  urgent?: boolean
  urgentTier?: 1 | 2
}

/* ---------------- workout tracker (sets, weights, heart-rate effort) ---------------- */
export type Felt = 'energised' | 'fine' | 'tired' | 'unwell'
export interface WorkoutSet {
  id: string
  reps: number
  /** null means bodyweight */
  weightKg: number | null
  /** when the set was logged (ISO), used to line it up with heart rate */
  doneAt: string
}
export interface WorkoutExercise {
  id: string
  name: string
  sets: WorkoutSet[]
}
export interface WorkoutSession {
  id: string
  startedAt: string
  endedAt?: string
  exercises: WorkoutExercise[]
  felt?: Felt
  note?: string
  /** how hard it felt, 1 (very light) to 5 (all-out) */
  intensity?: number
}
/** Returned by the server after a session is saved. Every number is computed in code (rules.md 1). */
export interface WorkoutSummary {
  id: string
  durationS: number
  setsN: number
  volumeKg: number
  exercises: { name: string; sets: number; volumeKg: number; avgHr: number | null }[]
  effort: {
    avgHr: number | null
    maxHr: number | null
    intensity: Intensity | null
    minutesInBand: Record<string, number>
    quality: 'ok' | 'insufficient'
    note?: string
  }
  /** change in glucose over the next 2 hours, from event_windows, when a sensor was worn */
  glucoseChange2h: number | null
  /** plain-language sentence written by the model from the numbers above; validated, may be absent */
  narrative?: string
}

/* ---------------- logging: meal photo analysis, daily progress, workouts this week ---------------- */
export interface Macros {
  kcal: number | null
  carbsG: number | null
  proteinG: number | null
  fatG: number | null
  fibreG: number | null
  sugarG: number | null
  sodiumMg: number | null
}
/** What the vision model read from a meal photo. Every number is an estimate until the person confirms it. */
export interface MealAnalysis {
  /** the Bronze row that holds the photo checksum and the model's raw answer; sent back when the meal is saved */
  analysisId: string
  name: string
  items: string[]
  macros: Macros
  confidence: 'high' | 'check'
  flags: ('high_salt' | 'high_sugar')[]
  portionNote: string
  modelId: string
}
export interface FoodNote {
  kind: 'higher' | 'lower' | 'similar' | 'learning'
  text: string
  n: number
  range: [number, number] | null
}
export interface ProgressItem {
  key: 'meals' | 'checkin' | 'workout' | 'symptom'
  label: string
  hint: string
  done: boolean
  /** due = inside its time window right now and not logged yet; later = not now (before or after its window) */
  status: 'done' | 'due' | 'later'
  count: number
  target: number | null
  to: RouteId
  /** when this log is worth doing, for example '7 to 10:30 am' */
  window?: string | null
  /** a short sentence that asks for it, present only while it is due */
  prompt?: string | null
}

export interface AppUser {
  key: string
  label: string
  sub: string
}
export interface UserList {
  current: string
  users: AppUser[]
}
export interface LogProgress {
  date: string
  items: ProgressItem[]
  done: number
  total: number
  streakDays: number
  weekActivityMin: number
  weekActivityGoal: number
  weekStrengthSessions: number
  weekStrengthGoal: number
  nextUp: ProgressItem | null
}
export interface WeekWorkouts {
  activeMin: number
  goalMin: number
  strengthSessions: number
  goalStrength: number
  sessions: number
  recent: RecentEntry[]
}
export interface LogContext {
  glucose: { v: number; trend: 'rising' | 'steady' | 'falling'; at: string } | null
}

/* ---------------- nutrition: food flags and lunch ideas ---------------- */
/** One nutrient compared between the person's usual dish (their own logged numbers) and a lighter dish from the food database. */
export interface SavingLine {
  nutrient: 'kcal' | 'protein_g' | 'carbs_g' | 'fat_g' | 'sugar_g' | 'sodium_mg' | 'fibre_g'
  from: number
  to: number
  change: number
}
/** A lighter, similar dish to have next time. The food database is only a shelf of options: it never sets what a meal is logged as. */
export interface Alternative {
  foodId: string
  name: string
  serving: string | null
  sourceGrade: string | null
  /** how sure JEV is that this is a reasonable substitute, 0 to 1 */
  fit: number
  improves: string[]
  changes: SavingLine[]
  for: string
}
/** A food habit the memory loop noticed: a type of food eaten often, high in what the person logged, with lighter dishes to try. */
export interface FoodHabit {
  type: string
  label: string
  n: number
  dishes: string[]
  topDish: string
  topDishN: number
  avg: Record<string, number | null>
  meanRise: number | null
  medianRise: number | null
  alternatives: Alternative[]
  /** the lighter dish was eaten since, and how it compared with the usual one (the person's own numbers) */
  outcomeText: string | null
  text: string
}
export interface LunchOption {
  key: string
  name: string
  source: 'swap' | 'own' | 'general'
  why: string
  serving?: string | null
  grade?: string | null
  carbs: number | null
  sodium: number | null
}
export interface LunchIdeas {
  windowStart: string
  windowEnd: string
  options: LunchOption[]
}

/* ---------------- what Smart Health has learned: facts, weekly digest, audit, progress ---------------- */
export interface LearnedFact {
  id: string
  key: string
  statement: string
  confidence: number
  status: 'proposed' | 'active'
  version: number
  why: string
  confirmed: boolean
  source: string | null
  updatedAt: string
}
export interface LearnedGroup {
  category: string
  label: string
  facts: LearnedFact[]
}
export interface Learned {
  groups: LearnedGroup[]
  total: number
  toConfirm: number
}
export interface WeekDigest {
  days: number
  newFacts: number
  lines: { kind: 'fact'; id: string; text: string; status: 'proposed' | 'active' | 'superseded' | 'rejected' }[]
  reminders: { sent: number; opened: number; acted: number }
  suggestions: { shown: number; chosen: number }
  topSuggestions: { name: string; kind: string; shown: number; chosen: number }[]
  guard: { checked: number; passed: number; blocked: number }
  agentRuns: Record<string, number>
}
export interface AuditRun {
  id: string
  trigger: string
  status: string
  ms: number | null
  at: string
  steps: { seq: number; node: string; tool: string | null; ms: number | null; output: unknown }[]
}
export interface ProgressWeek {
  weekStart: string
  meals: number
  avgKcal: number | null
  avgSodium: number | null
  doses: number | null
  onTimePct: number | null
}
export interface Progress {
  weeks: ProgressWeek[]
  compare: {
    avgKcal: { first: number | null; latest: number | null }
    avgSodium: { first: number | null; latest: number | null }
    onTimePct: { first: number | null; latest: number | null }
    firstWeeks: string[]
    latestWeeks: string[]
  } | null
  note: string
}

export interface AiUsage {
  day: string
  calls: number
  callCap: number
  costUsd: number
  budgetUsd: number
  blocked: number
  overCap: boolean
  providers: { provider: string; calls: number; inputTokens: number; outputTokens: number; costUsd: number | null }[]
  note: string
}
