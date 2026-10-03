/**
 * Demo patient: Mr Tan, 58. One place for every number the mockup shows.
 * These are simulated, from the demo plan in docs/mockup/mockup-prompt.md, and are always
 * labelled "Demo data" in the UI. The real app replaces this file with the API.
 */
import type {
  Appointment,
  CarePlan,
  ConnectedSource,
  EmergencyContact,
  DayTimeline,
  FoodResponse,
  GlucosePoint,
  Medication,
  MemoryFact,
  Notice,
  Patient,
  PreventiveItem,
  RecentEntry,
  ScanResult,
  SeriesPoint,
  WeekCompare,
  WorkoutRecord,
} from '../types'

// ---------- deterministic randomness so the demo never changes between reloads ----------
function rng(seed: number) {
  let a = seed >>> 0
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
const r1 = (n: number) => Math.round(n * 10) / 10

export const patient: Patient = {
  name: 'Mr Tan',
  initials: 'T.',
  age: 58,
  birthYear: 1968,
  occupation: 'Project manager',
  diagnosedYearsAgo: 6,
  lastHba1c: { value: 7.4, monthsAgo: 4 },
  targetRange: [3.9, 10.0],
  baselineFasting: [6.6, 7.2],
}

// ---------- dates ----------
const DATES = ['2026-09-24', '2026-09-25', '2026-09-26', '2026-09-27', '2026-09-28', '2026-09-29', '2026-09-30', '2026-10-01']
const WEEKDAY = ['Thursday', 'Friday', 'Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
const LABEL = ['24 Sep', '25 Sep', '26 Sep', '27 Sep', '28 Sep', '29 Sep', '30 Sep', '1 Oct']
export const dayDates = DATES

const m = (h: number, min = 0) => h * 60 + min

// ---------- day timelines ----------
interface DaySpec {
  i: number
  fasting: number
  meals: { t: number; name: string; carbs: number; rise: number; flags?: ('high_salt' | 'high_sugar')[]; estimated?: boolean }[]
  doses: { t: number; name: string; status: DayTimeline['doses'][number]['status'] }[]
  workouts?: { t: number; minutes: number; label: string; intensity: 'light' | 'moderate' | 'vigorous'; change?: number }[]
  symptoms?: { t: number; label: string; severity: number }[]
  gaps?: [number, number][]
  endT?: number
  sleep: [number, number] | null
  steps: number
  inRange: number
}

const dose = (t: number, name: string, status: DayTimeline['doses'][number]['status']) => ({ t, name, status })

const specs: DaySpec[] = [
  {
    i: 0, fasting: 7.0, sleep: [0, 410], steps: 7400, inRange: 76,
    meals: [
      { t: m(8, 15), name: 'Kaya toast with soft eggs', carbs: 36, rise: 1.9, estimated: false },
      { t: m(12, 55), name: 'Fish soup with rice', carbs: 64, rise: 2.7 },
      { t: m(19, 10), name: 'Steamed fish, vegetables, rice', carbs: 58, rise: 2.0 },
    ],
    doses: [dose(m(8), 'Metformin 500 mg', 'taken'), dose(m(8), 'Amlodipine 5 mg', 'taken'), dose(m(20), 'Metformin 500 mg', 'taken'), dose(m(22), 'Atorvastatin 20 mg', 'taken')],
  },
  {
    i: 1, fasting: 7.1, sleep: [0, 390], steps: 6800, inRange: 71,
    meals: [
      { t: m(8, 15), name: 'Kaya toast with soft eggs', carbs: 36, rise: 1.9 },
      { t: m(13, 10), name: 'Chicken rice', carbs: 82, rise: 3.6, flags: ['high_salt'] },
      { t: m(21, 15), name: 'Laksa', carbs: 74, rise: 3.0, flags: ['high_salt'] },
    ],
    doses: [dose(m(8), 'Metformin 500 mg', 'taken'), dose(m(8), 'Amlodipine 5 mg', 'taken'), dose(m(20), 'Metformin 500 mg', 'missed'), dose(m(22), 'Atorvastatin 20 mg', 'taken')],
  },
  {
    i: 2, fasting: 7.3, sleep: [0, 420], steps: 6100, inRange: 68,
    gaps: [[m(14), m(16, 30)]],
    meals: [
      { t: m(9, 30), name: 'Wholemeal sandwich', carbs: 40, rise: 1.6 },
      { t: m(13, 40), name: 'Chicken rice', carbs: 82, rise: 3.3, flags: ['high_salt'] },
      { t: m(19, 20), name: 'Yong tau foo soup', carbs: 34, rise: 1.5 },
    ],
    doses: [dose(m(8), 'Metformin 500 mg', 'taken'), dose(m(8), 'Amlodipine 5 mg', 'taken'), dose(m(20), 'Metformin 500 mg', 'taken'), dose(m(22), 'Atorvastatin 20 mg', 'taken')],
  },
  {
    i: 3, fasting: 7.2, sleep: [0, 380], steps: 5200, inRange: 66,
    meals: [
      { t: m(10), name: 'Vegetable and egg breakfast', carbs: 22, rise: 1.2 },
      { t: m(14), name: 'Mee goreng', carbs: 88, rise: 3.8, flags: ['high_salt'] },
    ],
    symptoms: [{ t: m(17, 30), label: 'More thirsty than usual', severity: 2 }],
    doses: [dose(m(8), 'Metformin 500 mg', 'taken'), dose(m(8), 'Amlodipine 5 mg', 'taken'), dose(m(20), 'Metformin 500 mg', 'missed'), dose(m(22), 'Atorvastatin 20 mg', 'taken')],
  },
  {
    i: 4, fasting: 7.6, sleep: [0, 345], steps: 6900, inRange: 74,
    meals: [
      { t: m(8, 20), name: 'Kaya toast with soft eggs', carbs: 36, rise: 1.9 },
      { t: m(13), name: 'Chicken rice', carbs: 82, rise: 3.5, flags: ['high_salt'] },
      { t: m(19), name: 'Steamed fish, vegetables, rice', carbs: 58, rise: 2.0 },
    ],
    workouts: [{ t: m(19, 40), minutes: 30, label: 'Brisk walk', intensity: 'moderate', change: -1.1 }],
    doses: [dose(m(8), 'Metformin 500 mg', 'taken'), dose(m(8), 'Amlodipine 5 mg', 'taken'), dose(m(20), 'Metformin 500 mg', 'taken'), dose(m(22), 'Atorvastatin 20 mg', 'taken')],
  },
  {
    i: 5, fasting: 7.8, sleep: [0, 360], steps: 6400, inRange: 76,
    meals: [
      { t: m(8, 30), name: 'Vegetable and egg breakfast', carbs: 22, rise: 1.2 },
      { t: m(13, 20), name: 'Fish soup with rice', carbs: 64, rise: 2.7 },
      { t: m(19, 15), name: 'Yong tau foo soup', carbs: 34, rise: 1.5 },
    ],
    doses: [dose(m(8), 'Metformin 500 mg', 'taken'), dose(m(8), 'Amlodipine 5 mg', 'taken'), dose(m(20), 'Metformin 500 mg', 'taken'), dose(m(22), 'Atorvastatin 20 mg', 'unconfirmed')],
  },
  {
    i: 6, fasting: 7.5, sleep: [0, 355], steps: 6700, inRange: 70,
    meals: [
      { t: m(8, 5), name: 'Vegetable and egg breakfast', carbs: 22, rise: 1.2 },
      { t: m(12, 50), name: 'Fish soup with rice', carbs: 64, rise: 2.7 },
      { t: m(18, 40), name: 'Yong tau foo soup', carbs: 34, rise: 1.5 },
    ],
    workouts: [{ t: m(19, 15), minutes: 25, label: 'Brisk walk', intensity: 'moderate', change: -1.4 }],
    doses: [dose(m(8), 'Metformin 500 mg', 'taken'), dose(m(8), 'Amlodipine 5 mg', 'taken'), dose(m(20), 'Metformin 500 mg', 'unconfirmed'), dose(m(22), 'Atorvastatin 20 mg', 'taken')],
  },
  {
    i: 7, fasting: 7.9, sleep: [0, 340], steps: 5840, inRange: 78, endT: m(19, 50),
    meals: [
      { t: m(8, 10), name: 'Toast with egg and coffee', carbs: 32, rise: 1.2 },
      { t: m(13, 5), name: 'Rice with chicken and vegetables', carbs: 78, rise: 3.4, flags: ['high_salt'] },
    ],
    doses: [dose(m(8), 'Metformin 500 mg', 'taken'), dose(m(8), 'Amlodipine 5 mg', 'taken'), dose(m(20), 'Metformin 500 mg', 'due')],
  },
]

const bump = (dt: number) => (dt <= 0 ? 0 : (dt / 60) * Math.exp(1 - dt / 60))

function buildDay(s: DaySpec): DayTimeline {
  const rnd = rng(1000 + s.i * 31)
  const endT = s.endT ?? 24 * 60 - 15
  const glucose: GlucosePoint[] = []
  const hr: GlucosePoint[] = []
  for (let t = 0; t <= endT; t += 15) {
    const gap = (s.gaps ?? []).some(([a, b]) => t >= a && t <= b)
    const day = Math.min(Math.max((t - 420) / 720, 0), 1)
    let v = s.fasting - 0.7 * Math.sin(Math.PI * day)
    for (const meal of s.meals) v += meal.rise * bump(t - meal.t)
    for (const w of s.workouts ?? []) if (t > w.t && t < w.t + 150) v += (w.change ?? 0) * Math.sin((Math.PI * (t - w.t)) / 150) * 0.9
    v += (rnd() - 0.5) * 0.28
    if (!gap) glucose.push({ t, v: r1(Math.min(Math.max(v, 4.2), 14)) })
    let h = t < s.sleep![1] ? 58 + rnd() * 4 : 70 + rnd() * 6
    for (const meal of s.meals) h += 4 * bump(t - meal.t)
    for (const w of s.workouts ?? []) if (t >= w.t && t <= w.t + w.minutes) h = 104 + rnd() * 8
    hr.push({ t, v: Math.round(h) })
  }
  const total = s.steps
  const weights = Array.from({ length: 24 }, (_, h): number => {
    if (h < 7) return 0
    if (h === 8 || h === 18) return 3
    if (h >= 9 && h <= 17) return 1.3
    if (h >= 19 && h <= 21) return 1.4
    return 0.8
  })
  const wsum = weights.reduce((a, b) => a + b, 0) || 1
  const nowH = Math.floor(endT / 60)
  const stepsByHour = weights.map((w, h) => (h > nowH ? 0 : Math.round((w / wsum) * total)))
  const sleepMin = s.sleep ? s.sleep[1] - s.sleep[0] + 0 : 0
  return {
    date: DATES[s.i]!,
    weekday: WEEKDAY[s.i]!,
    label: LABEL[s.i]!,
    endT,
    glucose,
    glucoseGaps: s.gaps ?? [],
    hr,
    stepsByHour,
    sleep: s.sleep ? { start: s.sleep[0], end: s.sleep[1], label: `${Math.floor((sleepMin + 10) / 60)} h ${(sleepMin + 10) % 60} min` } : null,
    meals: s.meals.map((x, k) => ({ id: `m${s.i}-${k}`, t: x.t, name: x.name, carbsG: x.carbs, flags: x.flags ?? [], rise: x.rise, estimated: x.estimated ?? true })),
    doses: s.doses.map((x, k) => ({ id: `d${s.i}-${k}`, ...x })),
    workouts: (s.workouts ?? []).map((x, k) => ({ id: `w${s.i}-${k}`, t: x.t, minutes: x.minutes, label: x.label, intensity: x.intensity, glucoseChange2h: x.change })),
    symptoms: (s.symptoms ?? []).map((x, k) => ({ id: `s${s.i}-${k}`, ...x })),
    inRangePct: s.inRange,
  }
}

export const days: DayTimeline[] = specs.map(buildDay)

// ---------- long series (90 days) for the period switch ----------
const END = new Date('2026-10-01T00:00:00')
const iso = (back: number) => {
  const d = new Date(END)
  d.setDate(d.getDate() - back)
  return d.toISOString().slice(0, 10)
}
function series(len: number, fn: (i: number, rnd: () => number) => number | null, seed: number): SeriesPoint[] {
  const rnd = rng(seed)
  return Array.from({ length: len }, (_, i) => ({ date: iso(len - 1 - i), v: fn(i, rnd) }))
}
const fastingLast7 = [7.1, 7.3, 7.2, 7.6, 7.8, 7.5, 7.9]
export const fastingSeries = series(90, (i, rnd) => {
  if (i >= 83) return fastingLast7[i - 83]!
  if (i >= 62) return r1(6.9 + (i - 62) * 0.028 + (rnd() - 0.5) * 0.22)
  return r1(6.55 + rnd() * 0.55)
}, 11)
const stepsLast7 = [6800, 6100, 5200, 6900, 6400, 6700, 5840]
export const stepsSeries = series(90, (i, rnd) => {
  if (i >= 83) return stepsLast7[i - 83]!
  if (i >= 62) return Math.round(8000 - (i - 62) * 85 + (rnd() - 0.5) * 900)
  return Math.round(8000 + (rnd() - 0.5) * 1400)
}, 21)
const sleepLast7 = [390, 420, 380, 345, 360, 355, 350]
export const sleepSeries = series(90, (i, rnd) => {
  if (i >= 83) return sleepLast7[i - 83]!
  if (i >= 62) return Math.round(410 - (i - 62) * 1.4 + (rnd() - 0.5) * 30)
  return Math.round(410 + (rnd() - 0.5) * 36)
}, 31)
export const restingHrSeries = series(90, (i, rnd) => {
  if (i >= 62) return Math.round(65 + (i - 62) * 0.2 + (rnd() - 0.5) * 2.4)
  return Math.round(64 + (rnd() - 0.5) * 3)
}, 51)
export const spo2Series = series(90, (i, rnd) => {
  if (i >= 70) return r1(96.4 - (i - 70) * 0.02 + (rnd() - 0.5) * 0.7)
  return r1(96.8 + (rnd() - 0.5) * 0.7)
}, 61)
export const moodSeries = Array.from({ length: 14 }, (_, i) => {
  const rnd = rng(41 + i)
  return { date: iso(13 - i), mood: i > 10 ? 3 : Math.round(3 + rnd() * 1.4), stress: i > 9 ? 4 : Math.round(2 + rnd() * 1.6) }
})

// ---------- medications ----------
export const medications: Medication[] = [
  { id: 'metformin', name: 'Metformin', strength: '500 mg', kind: 'prescription', times: ['8:00 am', '8:00 pm'], withFood: true, purpose: 'Helps your body use its own insulin better and lowers the sugar your liver releases.', badge: null, refill: { daysLeft: 6, unitsLeft: 12 }, sideEffects: ['Upset stomach or nausea', 'Loose stools', 'A metal taste in the mouth'] },
  { id: 'amlodipine', name: 'Amlodipine', strength: '5 mg', kind: 'prescription', times: ['8:00 am'], withFood: false, purpose: 'Helps relax blood vessels so blood pressure comes down.', badge: null, refill: null, sideEffects: ['Swollen ankles', 'Feeling flushed', 'Headache'] },
  { id: 'atorvastatin', name: 'Atorvastatin', strength: '20 mg', kind: 'prescription', times: ['10:00 pm'], withFood: false, purpose: 'Lowers cholesterol in the blood.', badge: null, refill: null, sideEffects: ['Muscle aches', 'Upset stomach', 'Headache'] },
  { id: 'fishoil', name: 'Fish oil', strength: '1,000 mg', kind: 'supplement', times: ['8:00 am'], withFood: true, purpose: 'A supplement you added yourself.', badge: null, refill: null, sideEffects: ['Fishy aftertaste', 'Upset stomach'] },
  { id: 'tonic', name: 'Herbal tonic', strength: 'Label unclear', kind: 'tcm', times: [], withFood: false, purpose: 'A herbal product you added yourself.', badge: 'not_checked', refill: null, sideEffects: [] },
]

export const scanResult: ScanResult = {
  drug: 'Clarithromycin',
  fields: [
    { key: 'name', label: 'Medicine', value: 'Clarithromycin 500 mg', confidence: 'high' },
    { key: 'dose', label: 'How much', value: '1 tablet', confidence: 'high' },
    { key: 'freq', label: 'How often', value: 'Twice daily after meals', confidence: 'check' },
    { key: 'days', label: 'For how long', value: '7 days', confidence: 'high' },
    { key: 'strength', label: 'Pharmacy and prescriber', value: null, confidence: 'unreadable' },
  ],
  schedule: [
    { time: '8:30 am', label: 'After breakfast' },
    { time: '8:30 pm', label: 'After dinner' },
  ],
  interaction: { a: 'Clarithromycin', b: 'Atorvastatin' },
}

// ---------- food responses (CGM sprint) ----------
export const foodResponses: FoodResponse[] = [
  { id: 'veg-egg', name: 'Vegetable and egg breakfast', rise: 1.2, min: 0.8, max: 1.6, n: 5, learning: false },
  { id: 'yong', name: 'Yong tau foo soup', rise: 1.5, min: 1.3, max: 1.7, n: 3, learning: false },
  { id: 'wholemeal', name: 'Wholemeal sandwich', rise: 1.6, min: 1.4, max: 1.9, n: 2, learning: false },
  { id: 'kaya', name: 'Kaya toast with soft eggs', rise: 1.9, min: 1.4, max: 2.4, n: 4, learning: false },
  { id: 'fish-rice', name: 'Fish soup with rice', rise: 2.7, min: 2.4, max: 3.0, n: 3, learning: false },
  { id: 'laksa', name: 'Laksa', rise: 3.0, min: 2.8, max: 3.2, n: 2, learning: false },
  { id: 'chicken-rice', name: 'Chicken rice (white rice)', rise: 3.4, min: 2.6, max: 4.1, n: 6, learning: false },
  { id: 'mee-goreng', name: 'Mee goreng', rise: 3.8, min: 3.8, max: 3.8, n: 1, learning: true },
]

// ---------- workouts ----------
export const workouts: WorkoutRecord[] = [
  { id: 'wo1', date: '30 Sep', label: 'Brisk walk', type: 'aerobic', intensity: 'moderate', minutes: 25, glucoseChange2h: -1.4 },
  { id: 'wo2', date: '28 Sep', label: 'Brisk walk', type: 'aerobic', intensity: 'moderate', minutes: 30, glucoseChange2h: -1.1 },
  { id: 'wo3', date: '22 Sep', label: 'Brisk walk', type: 'aerobic', intensity: 'moderate', minutes: 35, glucoseChange2h: -1.3 },
  { id: 'wo4', date: '20 Sep', label: 'Resistance bands', type: 'strength', intensity: 'moderate', minutes: 20 },
  { id: 'wo5', date: '17 Sep', label: 'Brisk walk', type: 'aerobic', intensity: 'moderate', minutes: 30, glucoseChange2h: -0.9 },
]

// ---------- memory ----------
export const memoryFacts: MemoryFact[] = [
  { id: 'f1', category: 'activity', statement: 'You walk after dinner on about 3 evenings a week.', confidence: 3, evidence: '14 evenings', evidenceTo: 'C4', status: 'active', evidenceStatus: 'derived' },
  { id: 'f2', category: 'barrier', statement: 'You tend to miss the evening dose on days you work past 8 pm.', confidence: 2, evidence: '6 days', evidenceTo: 'C6', status: 'active', evidenceStatus: 'derived' },
  { id: 'f3', category: 'routine', statement: 'You sleep less from Sunday to Wednesday.', confidence: 2, evidence: '5 weeks', evidenceTo: 'C5', status: 'active', evidenceStatus: 'derived' },
  { id: 'f4', category: 'food_response', statement: 'White-rice lunches raise your glucose the most.', confidence: 3, evidence: '6 meals', evidenceTo: 'C3', status: 'active', evidenceStatus: 'derived' },
  { id: 'f5', category: 'preference', statement: 'You act on reminders at 7:30 pm more than at 6:00 pm.', confidence: 2, evidence: '11 reminders', evidenceTo: 'C6', status: 'active', evidenceStatus: 'derived' },
  { id: 'f6', category: 'food_response', statement: 'Vegetable and egg breakfasts are your gentlest meals.', confidence: 3, evidence: '5 breakfasts', evidenceTo: 'C3', status: 'active', evidenceStatus: 'derived' },
  { id: 'f7', category: 'routine', statement: 'You usually have lunch between 12:30 and 1:30 pm.', confidence: 3, evidence: '27 days', evidenceTo: 'C3', status: 'active', evidenceStatus: 'derived' },
  { id: 'f8', category: 'preference', statement: 'You like short, one-line reminders.', confidence: 1, evidence: '3 replies', evidenceTo: 'C6', status: 'proposed', evidenceStatus: 'inferred' },
  { id: 'f9', category: 'routine', statement: 'Deadline weeks mean late nights and skipped walks.', confidence: 1, evidence: '2 weeks', evidenceTo: 'C5', status: 'proposed', evidenceStatus: 'inferred' },
]

export const weekCompare: WeekCompare = {
  rows: [
    { label: 'Fasting baseline (mmol/L)', then: '6.6', now: '7.9', flagged: true },
    { label: 'Evening reminder time', then: '6:00 pm', now: '7:30 pm' },
    { label: 'Walk reminders you acted on', then: '1 of 5', now: '3 of 5' },
    { label: 'Things learned about you', then: '2', now: '9' },
  ],
  streams: ['Food', 'Glucose', 'Watch', 'Workouts', 'Sleep', 'Medication'],
  stillLearning: 'Still learning: how stress affects your evenings.',
}

// ---------- care plan ----------
export const appointment: Appointment = { id: 'ap1', label: 'Diabetes review', when: 'Sunday 11 October, 10:30 am', inDays: 9, place: 'Your usual clinic' }
export const preventive: PreventiveItem[] = [
  { id: 'eye', label: 'Eye screening', status: 'overdue', detail: 'Last done 14 months ago' },
  { id: 'foot', label: 'Foot check', status: 'due_soon', detail: 'Due in 3 weeks' },
  { id: 'hba1c', label: 'HbA1c blood test', status: 'ok', detail: '7.4% four months ago' },
  { id: 'flu', label: 'Flu vaccination', status: 'unknown', detail: 'Not recorded' },
]
export const carePlan: CarePlan = {
  appointment,
  preventive,
  questions: [
    { id: 'q1', text: 'Is my morning sugar rising because of my sleep?', origin: 'user' },
    { id: 'q2', text: 'Should I be checking my feet more often?', origin: 'user' },
  ],
}

// ---------- notices, sources, entries ----------
export const notices: Notice[] = [
  { id: 'n1', kind: 'dose', title: 'Time for Metformin', body: '500 mg, 1 tablet, with food.', when: '7:50 pm', to: 'B1', unread: true },
  { id: 'n2', kind: 'refill', title: 'Metformin runs out in 6 days', body: 'You may want to arrange a refill before Wednesday.', when: '9:00 am', to: 'H6', unread: true },
  { id: 'n3', kind: 'checkin', title: 'A quick question', body: 'More thirsty than usual this week?', when: '8:00 am', to: 'B1', unread: false },
  { id: 'n4', kind: 'nudge', title: 'Your usual walk time', body: 'On walk days your evening readings were lower.', when: 'Yesterday', to: 'C4', unread: false },
  { id: 'n5', kind: 'brief', title: 'Your doctor brief is ready to review', body: 'Covers the last 4 weeks.', when: 'Yesterday', to: 'L1', unread: false },
  { id: 'n6', kind: 'appointment', title: 'Diabetes review in 9 days', body: 'Prepare your questions.', when: '29 Sep', to: 'K3', unread: false },
]

export const sources: ConnectedSource[] = [
  { id: 'watch', label: 'Smart watch', detail: 'Heart rate, steps, sleep and stress', status: 'connected', synced: '7:42 pm' },
  { id: 'sensor', label: 'Glucose sensor', detail: 'Sprint, day 9 of 14', status: 'connected', synced: '7:48 pm' },
  { id: 'camera', label: 'Phone camera', detail: 'Meal photos and medicine labels', status: 'allowed', synced: 'On request' },
]

export const recentEntries: RecentEntry[] = [
  { id: 're1', kind: 'meal', title: 'Rice with chicken and vegetables', detail: 'Estimated 78 g carbs', when: '1:05 pm', date: '2026-10-01' },
  { id: 're2', kind: 'meal', title: 'Toast with egg and coffee', detail: 'Estimated 32 g carbs', when: '8:10 am', date: '2026-10-01' },
  { id: 're3', kind: 'glucose', title: 'Fasting glucose 7.9 mmol/L', detail: 'Fasting', when: '6:45 am', date: '2026-10-01' },
  { id: 're4', kind: 'checkin', title: 'Evening check-in', detail: 'Mood 3, stress 4', when: 'Yesterday', date: '2026-09-30' },
  { id: 're5', kind: 'workout', title: 'Brisk walk, 25 min', detail: 'Moderate', when: 'Yesterday', date: '2026-09-30' },
]

export const emergencyContact: EmergencyContact = {
  name: 'Mei Ling Tan',
  relation: 'Daughter',
  phone: '+65 9123 4567',
  email: 'meiling@example.com',
  channels: ['message', 'email', 'call'],
  consent: true,
}
