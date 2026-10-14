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
  /** Where the refill figure comes from: the stock in hand ('stock') or the estimate from the pack date ('estimate'). */
  refillSource?: 'stock' | 'estimate' | null
  sideEffects: string[]
  /** the last day of a course (an antibiotic), ISO date; null when there is none */
  endDate?: string | null
}

/** One regular medicine in "My stock" (H1). `status` states a fact about the count, never advice. */
export interface MedicineStock {
  id: string
  name: string
  strength: string
  /** null: not set yet. It is never shown as 0. */
  stockCount: number | null
  stockUnit: string | null
  /** Whole days at the usual dose; null when unknown. */
  daysLeft: number | null
  status: 'ok' | 'low' | 'out' | 'unknown'
  updatedAt: string | null
  /** The last amount set or bought: the full mark of the bar. null when there is none yet. */
  fullCount: number | null
  /** The pack size, when it was entered: quick choices in "I bought more". */
  packSize: number | null
}

/** GET /medications/stock. `ready` is false while stock tracking is not set up on the server (no items then). */
export interface StockList {
  ready: boolean
  items: MedicineStock[]
}

/** A web page the explanation was based on. */
export interface WebSource {
  title: string
  url: string
}

/** What a medicine is for and its common side effects, in plain words, with the web pages they came from (prd F3). */
/** The four labelled parts of an explanation (prompt version 2). A part the pages did not cover is an empty string. */
export interface MedicineExplanationParts {
  forDiabetes: string
  howItWorks: string
  whatYouMayNotice: string
  whyTimingMatters: string
}

export interface MedicineExplanation {
  /** `not_identified`: the product could not be identified, so nothing is explained. */
  status: 'ready' | 'not_identified'
  /** what it is for in the person's diabetes (the first part, as plain text) */
  purpose: string
  /** null for an explanation made before the four parts existed: the page shows the older layout until it is made again */
  parts?: MedicineExplanationParts | null
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
  kind: 'dose' | 'dose_reminder' | 'dose_renudge' | 'checkin' | 'nudge' | 'brief' | 'refill' | 'appointment'
  title: string
  body: string
  when: string
  to?: RouteId
  unread: boolean
  /** Reminders page list only: the Singapore day it belongs to (YYYY-MM-DD) */
  date?: string
  /** Reminders page list only: still waiting and inside its time window. Past or done ones stay on the page and still open their screen. */
  current?: boolean
  /** Reminders page list only: the place (0, 1, 2) of a first "get started" notice, shown on top until it is done */
  pinned?: number | null
}

export interface ConnectedSource {
  id: string
  label: string
  detail: string
  status: 'connected' | 'allowed'
  synced: string
}

/** A meal in the recent list. Every macro is null when unknown (shown as "Not judged", never 0). `response` is null when the sensor has no data for it. */
export interface RecentMeal {
  id: string
  when: string
  name: string | null
  mealType: string | null
  kcal: number | null
  /** 'you' when the person typed or changed the numbers (label "Your numbers"); 'estimate' when the photo reading gave them */
  numbersFrom?: 'you' | 'estimate'
  carbsG: number | null
  proteinG: number | null
  fatG: number | null
  sugarG: number | null
  fibreG: number | null
  sodiumMg: number | null
  flags: ('salt' | 'sugar')[]
  response: { preMmol: number | null; peakMmol: number | null; minutesToPeak: number | null; riseMmol: number | null } | null
}

export interface RecentEntry {
  id: string
  kind: LogKind
  title: string
  detail: string
  when: string
  date: string
  /** Set for a meal only. */
  meal?: RecentMeal | null
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
  /** The stable code behind `error` and `notice` (ocr_empty, model_unavailable, storage_unavailable, low_confidence_all...). */
  errorCode?: string | null
  /** "confirm": one medicine read clearly, the person checks it. "manual": the person types the form (unreadable, low confidence, a
   *  missing required field, a drug we cannot identify, or several medicines). */
  /** The label says "when necessary": the medicine has no dose times. */
  asNeeded: boolean
  /** The label names a symptom (fever, pain, cough...): worth asking whether it is only taken when needed. */
  symptomHint?: boolean
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

export type LogKind = 'meal' | 'workout' | 'symptom' | 'checkin' | 'blood_pressure'

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
  /** how hard it felt, 1 (very light) to 5 (all-out); null or omitted when the session was not rated */
  intensity?: number | null
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
    /** true when the person takes a beta-blocker: numbers are shown, the effort label is not */
    betaBlocker: boolean
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
  bloodPressure: BloodPressureToday
}
/** One saved blood pressure reading. `id` is what edit and delete use. */
export interface WorkoutEntry {
  id: string
  type: WorkoutType | string
  activity: string
  intensity: number | null
  startAt: string
  minutes: number
  feeling: number | null
}
export interface BloodPressureEntry {
  id: string
  measuredAt: string
  systolic: number
  diastolic: number
  pulse: number | null
  note: string | null
}
export interface BloodPressureToday {
  count: number
  /** plain words, for example "128 over 82 at 8:10 am"; null when nothing is logged today */
  latest: string | null
  readings: BloodPressureEntry[]
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
/** The Meal suggestions menu (GET /nutrition/menu). A glucose rise is measured for the person's own meals and estimated (a range) for the rest. */
export type MenuMeal = 'breakfast' | 'lunch' | 'dinner' | 'snack'
export interface MenuItem {
  key: string
  /** the meal this dish is for (set on every dish; the "all" menu mixes the four meals) */
  meal: MenuMeal
  name: string
  section: 'swap' | 'general'
  why: string
  serving: string | null
  kcal: number | null
  carbs: number | null
  sodium: number | null
  rise: number | null
  riseLow: number | null
  riseHigh: number | null
  riseKind: 'measured' | 'estimate' | 'none'
  seen: number | null
  tags: string[]
  dishKey: string
  /** the picture: `url` is set only when it is ready (status 'ready'); otherwise the page shows a placeholder */
  image: { status: 'pending' | 'generating' | 'ready' | 'failed'; url: string | null }
}
export interface Menu {
  meal: MenuMeal | 'all'
  time: string | null
  sections: { key: MenuItem['section']; items: MenuItem[] }[]
  usual: { name: string; kcal: number | null; rise: number | null } | null
  picturesWaiting: number
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

/* ---------------- what Equinox has learned: facts, weekly digest, audit, progress ---------------- */
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
  /** weeks with 5 or more meals logged; the baseline needs two of them */
  fullWeeks: number
  /** the first two full weeks, or null until there are two */
  baseline: {
    weeks: string[]
    meals: number
    doses: number | null
    avgKcal: number | null
    avgSodium: number | null
    onTimePct: number | null
  } | null
  compare: {
    avgKcal: { first: number | null; latest: number | null }
    avgSodium: { first: number | null; latest: number | null }
    onTimePct: { first: number | null; latest: number | null }
    firstWeeks: string[]
    latestWeeks: string[]
  } | null
  note: string
}

/** Diet tracking calendar (K10). Every macro is null when unknown for that day; `meals` 0 means nothing logged. */
export interface DietTotals {
  kcal: number | null
  carbsG: number | null
  proteinG: number | null
  fatG: number | null
  sugarG: number | null
  fibreG: number | null
  sodiumMg: number | null
}
export interface DietMeal {
  id: string
  when: string
  name: string | null
  mealType: string | null
  kcal: number | null
  /** 'you' when the person typed or changed the numbers (label "Your numbers"); 'estimate' when the photo reading gave them */
  numbersFrom?: 'you' | 'estimate'
  carbsG: number | null
  proteinG: number | null
  fatG: number | null
  sugarG: number | null
  fibreG: number | null
  sodiumMg: number | null
}
export interface DietDay {
  date: string
  meals: number
  totals: DietTotals
  mealList: DietMeal[]
}
export interface DietDays {
  start: string
  end: string
  /** today in Singapore */
  today: string
  days: DietDay[]
}

/** The "What gets in the way" numbers on K2. Null means no data yet, shown as a dash. */
export interface BarrierSummary {
  windowDays: number
  weekStart: string
  scheduledThisWeek: number
  missedThisWeek: number | null
  confirmedDoses: number
  onTimePct: number | null
  topReason: { key: string; label: string; count: number; missed: number } | null
  confirmedBarriers: number
  waitingBarriers: number
}

/** One kind of AI call today (the kinds are vertex_vision, vertex_generate, vertex_embed and jev). Each has its own cap. */
export interface AiUsageProvider {
  provider: string
  calls: number
  /** Calls refused because the cap was already reached. */
  blocked: number
  cap: number
  overCap: boolean
  inputTokens: number
  outputTokens: number
  costUsd: number | null
}

export interface AiUsage {
  day: string
  calls: number
  callCap: number
  costUsd: number
  budgetUsd: number
  blocked: number
  overCap: boolean
  /** The cap of each known kind, by provider name. */
  caps: Record<string, number>
  providers: AiUsageProvider[]
  note: string
}

/* ---------------- doctor report (prd F12): every value is computed by the backend, the screen only lays it out ---------------- */
export type ReportDays = 7 | 14 | 30 | 90
export type GlucoseBandKey = 'very_high' | 'high' | 'in_range' | 'low' | 'very_low'
export interface DoctorReport {
  generatedOn: string
  /** true only when the person's data is the demo dataset; the data notes then say the data is simulated */
  simulated: boolean
  period: { start: string; end: string; days: number; label: string }
  patient: { name: string; sexAge: string; diagnosis: string }
  /** the onboarding answers in the patient summary; only rows with an answer are sent */
  summary: { label: string; value: string }[]
  cgmWear: string
  sources: string
  keyFindings: string[]
  /** 'ai' when the wording was written by a model from the report's numbers and passed the checks; 'rules' when it is the code-written text */
  keyFindingsSource: 'ai' | 'rules'
  alerts: { priority: 'urgent' | 'interaction' | 'review'; title: string; detail: string }[]
  glucose: {
    hasData: boolean
    /** false when the sensor was active for too little of the period */
    sufficient: boolean
    bands: { key: GlucoseBandKey; label: string; pct: number; perDay: string; reference: string; outside: boolean }[]
    metrics: { label: string; value: string; reference: string; outside: boolean }[]
    /** percentiles of glucose by hour of the day; hours with too few readings are left out */
    profile: { hour: number; p5: number; p25: number; p50: number; p75: number; p95: number }[]
    low: number | null
    high: number | null
    veryLow: number | null
    veryHigh: number | null
  }
  /** the 14-day baseline beside the period; `available` is false with a note when there is too little sensor data */
  baseline: {
    available: boolean
    note: string | null
    periodLabel: string | null
    baselineLabel: string | null
    rows: { metric: string; baseline: string; period: string; comparison: 'higher than' | 'lower than' | 'about the same as' | '—' }[]
  }
  symptoms: { symptom: string; logged: number; low: number; high: number; inRange: number; noReading: number; note: string }[]
  symptomLatest: {
    latest: { label: string; value: string; on: string }[]
    rows: { symptom: string; logged: number; text: string }[]
    note: string
  }
  episodes: {
    when: string
    symptom: string
    severity: number | null
    glucose: number | null
    zone: 'very_low' | 'low' | 'in_range' | 'high' | null
    change30: number | null
    lastDose: string | null
    heartRate: number | null
    spo2: number | null
    note: string | null
  }[]
  episodesTotal: number
  medicines: { name: string; regimen: string; scheduled: number | null; taken: number | null; missed: number | null; notLogged: number | null; adherencePct: number | null; interaction: boolean }[]
  medicinesNote: string | null
  activity: { label: string; value: string; sub: string }[]
  bloodPressure: {
    /** readings in the period; 0 means none were logged */
    count: number
    systolicRange: string | null
    diastolicRange: string | null
    pulseRange: string | null
    readings: { when: string; systolic: number; diastolic: number; pulse: number | null }[]
    readingsTotal: number
  }
  /** up to five plain observations from the person's own data, most important first; empty when nothing stands out yet */
  worthDiscussing: { text: string; evidence: string; kind: 'clash' | 'adherence' | 'pattern' | 'fact' }[]
  questions: string[]
}

/* ------------------------------- Insights tab (C1 to C6, C8) ------------------------------- */
/** Mirrors services/api/app/schemas/insights.py. Every value is computed by the server from stored data. */
export type InsightsDays = 7 | 30 | 90
/** the periods the timeline answers for: the Insights ones, and 14 days for the doctor brief */
export type TimelineDays = InsightsDays | 14
export type InsightsTab = 'C2' | 'C3' | 'C4' | 'C5' | 'C6'
export interface InsightsPeriod {
  start: string
  end: string
  days: number
  label: string
  hasData: boolean
}
export interface InsightsPattern {
  key: string
  text: string
  n: number
  to: InsightsTab
}
/** One measure against the same number of days before. `direction` is "none" when either period has no value. */
export interface InsightsChange {
  id: 'tir' | 'fasting' | 'steps' | 'exercise' | 'sleep' | 'stress' | 'doses'
  to: InsightsTab
  unit: 'points' | 'mmol' | 'steps' | 'minutes' | 'hours' | 'score'
  direction: 'up' | 'down' | 'same' | 'none'
  current: number | null
  previous: number | null
  delta: number | null
}
export type InsightsGridKey = 'glucose' | 'meals' | 'activity' | 'sleep' | 'stress' | 'doses'
export interface InsightsGridCell {
  date: string
  value: number | null
  label: string
  /** 0 no data, 1 to 4 how much (a shade, not a verdict) */
  level: number
}
export interface InsightsGridRow {
  key: InsightsGridKey
  cells: InsightsGridCell[]
}
export interface InsightsOverview {
  period: InsightsPeriod
  changes: InsightsChange[]
  patterns: InsightsPattern[]
}
/** The overview charts on one shared time axis (GET /insights/timeline). Times (`m`) are minutes since local midnight of the first day. */
export interface InsightsHourly {
  /** 24 numbers, hour 0 to 23: the person's own average, and the middle half (25th to 75th percentile) */
  mean: (number | null)[]
  lo: (number | null)[]
  hi: (number | null)[]
}
export interface InsightsTimeline {
  /** latest and earliest: the first and last day with data, so the period can move back but not past them */
  period: InsightsPeriod & { bucketMinutes: number; buckets: number; latest: string; earliest: string | null }
  series: {
    glucose: (number | null)[]
    glucoseMin: (number | null)[]
    glucoseMax: (number | null)[]
    heart: (number | null)[]
    heartMin: (number | null)[]
    heartMax: (number | null)[]
    spo2: (number | null)[]
    spo2Min: (number | null)[]
    spo2Max: (number | null)[]
    steps: (number | null)[]
  }
  baseline: {
    days: number
    /** "before": the 60 days before the period; "start": too few days before, so the first 30 days of the period; "period": the whole (short) period */
    source: 'before' | 'start' | 'period'
    from: string
    to: string
    available: boolean
    bpAvailable: boolean
    bpSystolic: number | null
    bpDiastolic: number | null
    bpReadings: number
    /** for the one-point-a-day views: the mean of the person's daily averages and the middle half of them */
    daily: Record<'glucose' | 'heart' | 'spo2', { mean: number | null; lo: number | null; hi: number | null }>
    /** the same window's average glucose, steps a day and glucose variation: what the Health overview is graded against */
    health: { avgGlucose: number | null; stepsPerDay: number | null; cv: number | null }
    glucose: InsightsHourly
    heart: InsightsHourly
    spo2: InsightsHourly
  }
  bp: { m: number; systolic: number; diastolic: number }[]
  events: {
    meals: { m: number; type: string; food: string }[]
    exercise: { m0: number; m1: number; type: string }[]
    symptoms: { m: number; type: string }[]
    missed: { m: number }[]
    mood: { m: number; mood: number; stress: number | null }[]
  }
  /** work_days: 1 = Monday ... 7 = Sunday; `set` is false when the person gave no work hours */
  work: { days: number[]; start: string | null; end: string | null; set: boolean }
  values: { avgGlucose: number | null; gmi: number | null; cv: number | null; stepsPerDay: number | null; dosesTakenPct: number | null; sensorWornPct: number | null }
  /** the period of the same length just before this one, for "what changed" */
  previous: { avgGlucose: number | null; stepsPerDay: number | null; dosesTakenPct: number | null }
  /** one row per day of the period */
  dayRows: InsightsTimelineDay[]
  compare: {
    /** the number of most recent days in `recent` (7, or 30 for a 90-day period) */
    recentDays: number
    glucose: InsightsTimelineMetric
    heart: InsightsTimelineMetric
    spo2: InsightsTimelineMetric
    bp: InsightsTimelineMetric
  }
}
export interface InsightsTimelineDay {
  date: string
  glucose: { avg: number | null; min: number | null; max: number | null }
  heart: { avg: number | null; min: number | null; max: number | null }
  spo2: { avg: number | null; min: number | null; max: number | null }
  systolic: number | null
  diastolic: number | null
  steps: number | null
  kcal: number | null
  sugarG: number | null
  sodiumMg: number | null
  meals: number
  missed: number
  /** doses planned that day (0 when none, or the day is not over) */
  scheduled: number
  symptoms: number
}
/** the period set against the baseline: a number, never a verdict */
export interface InsightsTimelineMetric {
  baseline: number | null
  period: number | null
  recent: number | null
  slopePerWeek: number | null
}
/** The overview calendar: one cell per day in start to end. Days after `today` are never included. */
export interface InsightsOverviewDays {
  start: string
  end: string
  today: string
  rows: InsightsGridRow[]
}
export interface InsightsBand {
  key: GlucoseBandKey
  label: string
  pct: number
}
export interface InsightsGlucoseMetrics {
  mean: number | null
  gmi: number | null
  cv: number | null
  coverage: number | null
  readings: number
}
export interface InsightsGlucose {
  period: InsightsPeriod
  hasData: boolean
  bands: InsightsBand[]
  days: { date: string; mean: number | null; tir: number | null; fasting: number | null }[]
  baseline: { p25: number; p50: number; p75: number; n: number } | null
  drift: { weeks: number; text: string } | null
  metrics: InsightsGlucoseMetrics
  events: { spikes: number; lows: number; sustainedHigh: number }
  low: number
  high: number
  patterns: InsightsPattern[]
}
export interface InsightsMeal {
  id: string
  when: string
  name: string
  mealType: string
  kcal: number | null
  carbsG: number | null
  sugarG: number | null
  sodiumMg: number | null
  flags: ('high_salt' | 'high_sugar')[]
  rise: number | null
}
export interface InsightsFood {
  period: InsightsPeriod
  totals: { meals: number; avgKcalPerDay: number | null; avgSodiumPerDay: number | null; highSaltMeals: number; highSugarMeals: number }
  meals: InsightsMeal[]
  responses: { name: string; n: number; medianRise: number; low: number; high: number }[]
  stillLearning: string[]
  patterns: InsightsPattern[]
}
export interface InsightsActivity {
  period: InsightsPeriod
  /** one bar per day (7 days), calendar week (30 days) or calendar month (90 days); the newest week or month is partial until it ends */
  barUnit: 'day' | 'week' | 'month'
  bars: { label: string; firstDay: string; lastDay: string; partial: boolean; light: number; moderate: number; vigorous: number }[]
  mix: { type: string; label: string; count: number; minutes: number }[]
  /** intensity is null when the session was not rated; it is never counted as moderate */
  workouts: { id: string; date: string; label: string; type: string; intensity: number | null; minutes: number; glucoseChange2h: number | null }[]
  steps: { date: string; steps: number | null }[]
  stepsAvg: number | null
  stepsBaseline: number | null
  patterns: InsightsPattern[]
}
export interface InsightsSleep {
  period: InsightsPeriod
  days: { date: string; hours: number | null; mood: number | null; stress: number | null; energy: number | null }[]
  sleepAvg: number | null
  /** nights under 6 hours in the period */
  shortNights: number
  stressAvg: number | null
  moodAvg: number | null
  highStressDays: number
  loggedDays: number
  patterns: InsightsPattern[]
}
/** C4 and C5: heart rate and SpO2 from the watch (services/api/app/schemas/insights_heart.py). A day without watch data is null, never zero. */
export interface InsightsHeart {
  /** ends on the person's last day of watch data (today when there is none) */
  period: InsightsPeriod
  /** the last watch day, ISO; null when there is no watch data at all */
  watchEnd: string | null
  /** true when the period ends before today or before the other tabs: the screen says "Showing your watch data up to ..." */
  endNote: boolean
  hasData: boolean
  daysWithData: number
  heartRate: { avg: number | null; high: number | null; low: number | null; restingAvg: number | null; asleepAvg: number | null }
  spo2: { avg: number | null; low: number | null; asleepAvg: number | null; asleepLow: number | null }
  days: { date: string; avg: number | null; resting: number | null; asleep: number | null }[]
}
/** C5: blood pressure the person logged by hand, newest first. `count` covers every reading in the period; `readings` is capped. */
export interface InsightsBloodPressure {
  count: number
  /** local date of the newest reading, ISO; null when there is none */
  latest: string | null
  readings: { date: string; time: string; systolic: number; diastolic: number; pulse: number | null }[]
}

export type InsightsDoseCell = 'taken' | 'late' | 'unconfirmed' | 'missed' | 'none'
export interface InsightsMedication {
  period: InsightsPeriod
  dates: string[]
  /** counted: prescription medicines count towards adherence; the others are listed with their grid only (numbers are null) */
  meds: { id: string; name: string; regimen: string; counted: boolean; taken: number | null; missed: number | null; unconfirmed: number | null; scheduled: number | null; adherencePct: number | null; cells: InsightsDoseCell[] }[]
  taken: number
  missed: number
  scheduled: number
  unconfirmed: number
  /** null until a prescription dose has been answered (taken or missed) */
  adherencePct: number | null
  reasons: { key: string; label: string; count: number }[]
  patterns: InsightsPattern[]
  shownDays: number
  /** "YYYY-MM" when a month was asked for (the calendar); the other months are null at the ends: no record before, or no later day with data */
  month?: string | null
  prevMonth?: string | null
  nextMonth?: string | null
}
export interface InsightsSprint {
  period: InsightsPeriod
  status: 'complete' | 'partial' | 'none'
  daysWorn: number
  of: number
  metrics: InsightsGlucoseMetrics
  bands: InsightsBand[]
  gentlest: { name: string; medianRise: number; n: number }[]
  spikiest: { name: string; medianRise: number; n: number }[]
}

/* ---------------- Home overview (GET /home/overview): today's plan, the four numbers and the 7-day chart ---------------- */
export type RangeState = 'within' | 'above' | 'below' | 'unknown'
/** How a number compares with the person's OWN usual range (25th to 75th percentile of their daily values over the 60 days before). */
export interface KpiStatus {
  state: RangeState
  usualLow: number | null
  usualHigh: number | null
  usualMedian: number | null
  /** the current value minus the usual median, in the unit of the value */
  delta: number | null
}
export interface PlanItem {
  kind: 'meal' | 'dose'
  /** the person's own label ("Breakfast", "Metformin 500 mg"), never a suggestion */
  title: string
  status: 'done' | 'due' | 'later' | 'missed'
  /** kind dose: the pending dose row id (what Taken sends) */
  doseId: string | null
  mealType: 'breakfast' | 'lunch' | 'dinner' | null
}
export interface PlanStep {
  /** "08:00", Singapore time */
  time: string
  /** "8:00 am" */
  label: string
  state: 'done' | 'now' | 'later' | 'missed'
  items: PlanItem[]
}
export interface HomePlan {
  date: string
  done: number
  total: number
  nowIndex: number | null
  steps: PlanStep[]
}
export interface Nutrient {
  state: 'ok' | 'high' | 'unknown'
  highMeals: number | null
  meals: number
}
export interface HomeOverview {
  asOf: string | null
  plan: HomePlan
  glucose: { value: number | null; unit: 'mmol/L'; day: string | null; inRangePct: number | null; spark: (number | null)[]; status: KpiStatus } | null
  steps: { avg: number | null; spark: (number | null)[]; status: KpiStatus } | null
  calories: { avgKcal: number | null; sugar: Nutrient; salt: Nutrient; spark: (number | null)[]; status: KpiStatus } | null
  heart: { bpm: number | null; restingBpm: number | null; spo2: number | null; status: KpiStatus; spo2Status: KpiStatus } | null
  chart: { days: string[]; glucose: (number | null)[]; steps: (number | null)[]; calories: (number | null)[]; heartRate: (number | null)[] }
}

/** One day for the Insights drill-down (GET /insights/day): the 5-minute series, the hourly baseline, what was logged, and two ideas for tomorrow. Times (`m`) are minutes after local midnight. */
export interface InsightsDay {
  date: string
  hasData: boolean
  prevDate: string | null
  nextDate: string | null
  latestDate: string | null
  earliestDate: string | null
  /** 1 = Monday ... 7 = Sunday */
  weekday: number
  workSet: boolean
  workDays: number[]
  /** 288 values, one every 5 minutes; null where there is no reading */
  series: { glucose: (number | null)[]; heart: (number | null)[]; spo2: (number | null)[]; steps: number[] }
  /** the person's own average for each hour of the day over the 14 days before (24 numbers), when there are enough days */
  baseline: { available: boolean; glucose: (number | null)[]; heart: (number | null)[]; spo2: (number | null)[]; bpSystolic: number | null; stepsPerDay: number | null }
  totals: {
    glucose: { avg: number | null; min: number | null; max: number | null }
    heart: { avg: number | null; min: number | null; max: number | null }
    spo2: { avg: number | null; min: number | null; max: number | null }
    steps: number | null
    kcal: number | null
    carbsG: number | null
    sugarG: number | null
    sodiumMg: number | null
    meals: number
    dosesScheduled: number
    dosesTaken: number
    dosesMissed: number
    sleepHours: number | null
  }
  meals: { m: number; type: string | null; food: string; carbsG: number | null; sugarG: number | null; sodiumMg: number | null; kcal: number | null; riseMmol: number | null; peakMmol: number | null; peakM: number | null }[]
  doses: { m: number; status: string; name: string }[]
  symptoms: { m: number; m1: number; type: string; severity: number | null }[]
  bp: { m: number; systolic: number; diastolic: number }[]
  mood: { m: number; mood: number; stress: number | null }[]
  exercise: { m0: number; m1: number; type: string }[]
  ideas: {
    swap: { fromFood: string; fromCarbsG: number | null; toFood: string; toCarbsG: number | null; mealType: string | null } | null
    /** shown only when no exercise was logged; `learned` is what Equinox has learnt about walks, confirmed or not */
    walk: { learned: { lowerBy: number | null; days: number; confirmed: boolean } | null } | null
  }
}
