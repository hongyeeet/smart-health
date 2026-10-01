import { appConfig } from '@/config/app'
import { clock, glucoseLevel, nowMinutes, shortDate, thousands, weekdayShort } from '@/lib/format'
import * as fx from '../fixtures/mrTan'
import type {
  BriefData,
  CarePlan,
  ChatReply,
  DayTimeline,
  Dose,
  HomeData,
  Insights,
  LogResult,
  Medication,
  Notice,
  Period,
  RecentEntry,
  WeekGrid,
} from '../types'
import type { Api, LogInput } from './types'

const wait = <T,>(v: T, ms = 60) => new Promise<T>((res) => setTimeout(() => res(v), ms))
const clone = <T,>(v: T): T => structuredClone(v)

// ---------- mutable in-memory state (resets on reload) ----------
const db = {
  doses: [
    { id: 'd-met-am', medId: 'metformin', label: 'Metformin 500 mg', time: '8:00 am', withFood: true, status: 'taken', day: 'today' },
    { id: 'd-aml-am', medId: 'amlodipine', label: 'Amlodipine 5 mg', time: '8:00 am', withFood: false, status: 'taken', day: 'today' },
    { id: 'd-met-pm', medId: 'metformin', label: 'Metformin 500 mg', time: '8:00 pm', withFood: true, status: 'due', day: 'today' },
    { id: 'd-ato-pm', medId: 'atorvastatin', label: 'Atorvastatin 20 mg', time: '10:00 pm', withFood: false, status: 'scheduled', day: 'today' },
    { id: 'd-met-pm-y', medId: 'metformin', label: 'Metformin 500 mg', time: '8:00 pm', withFood: true, status: 'unconfirmed', day: 'yesterday' },
  ] as Dose[],
  meds: clone(fx.medications),
  facts: clone(fx.memoryFacts),
  questions: clone(fx.carePlan.questions),
  appointment: clone(fx.appointment),
  notices: clone(fx.notices),
  recent: clone(fx.recentEntries) as RecentEntry[],
  extraByDay: {} as Record<string, Partial<Pick<DayTimeline, 'meals' | 'workouts' | 'symptoms'>>>,
  moderateMin: 55,
  checkinDone: false,
  promptSnoozed: false,
  scanAdded: false,
  shared: false,
  glucoseToday: [] as { t: number; v: number }[],
  seq: 100,
}

const today = appConfig.demo.today
const id = (p: string) => `${p}${++db.seq}`

function slice<T>(arr: T[], period: Period): T[] {
  return arr.slice(arr.length - period)
}

function buildWeekGrid(): WeekGrid {
  const dates = fx.dayDates.slice(1)
  const days = dates.map((d) => ({ date: d, short: `${weekdayShort(d)} ${new Date(d + 'T00:00:00').getDate()}` }))
  const mk = (key: string, label: string, vals: [string, 'good' | 'mid' | 'low' | 'none'][]) => ({ key, label, cells: vals.map(([text, level]) => ({ text, level })) })
  return {
    days,
    rows: [
      mk('tir', 'Glucose in range', [['71%', 'mid'], ['68%', 'mid'], ['66%', 'mid'], ['74%', 'mid'], ['76%', 'good'], ['70%', 'mid'], ['78%', 'good']]),
      mk('meals', 'Meals logged', [['3', 'good'], ['3', 'good'], ['2', 'mid'], ['3', 'good'], ['3', 'good'], ['3', 'good'], ['2', 'mid']]),
      mk('activity', 'Activity (min)', [['0', 'none'], ['0', 'none'], ['0', 'none'], ['30', 'good'], ['0', 'none'], ['25', 'good'], ['0', 'none']]),
      mk('sleep', 'Sleep (hours)', [['6.5', 'good'], ['7.0', 'good'], ['6.3', 'mid'], ['5.8', 'low'], ['6.0', 'mid'], ['5.9', 'low'], ['5.8', 'low']]),
      mk('stress', 'Stress (1 to 5)', [['3', 'mid'], ['2', 'good'], ['2', 'good'], ['4', 'low'], ['4', 'low'], ['3', 'mid'], ['4', 'low']]),
      mk('doses', 'Doses taken', [['3/4', 'mid'], ['4/4', 'good'], ['3/4', 'mid'], ['4/4', 'good'], ['3/4', 'mid'], ['3/4', 'mid'], ['3/3', 'good']]),
    ],
  }
}

const whatChanged: HomeData['whatChanged'] = [
  { id: 'wc1', text: 'Your fasting glucose has been drifting up for about 3 weeks.', to: 'C2' },
  { id: 'wc2', text: 'Fewer evening walks: 4 last week, 1 this week.', to: 'C4' },
  { id: 'wc3', text: 'Shorter sleep on work nights.', to: 'C5' },
]

function dayWith(date: string): DayTimeline {
  const base = clone(fx.days.find((d) => d.date === date) ?? fx.days[fx.days.length - 1]!)
  const extra = db.extraByDay[date]
  if (extra?.meals) base.meals.push(...extra.meals)
  if (extra?.workouts) base.workouts.push(...extra.workouts)
  if (extra?.symptoms) base.symptoms.push(...extra.symptoms)
  // keep doses in step with what the person tapped
  if (date === today) {
    base.doses = base.doses.map((d) => {
      const live = db.doses.find((x) => x.day === 'today' && x.time === clock(d.t).replace(/^0/, '') && d.name === x.label)
      return live ? { ...d, status: live.status as typeof d.status } : d
    })
  }
  if (date === '2026-09-30') {
    const y = db.doses.find((x) => x.day === 'yesterday')
    if (y) base.doses = base.doses.map((d) => (d.name.startsWith('Metformin') && d.t === 20 * 60 ? { ...d, status: y.status as typeof d.status } : d))
  }
  if (date === today) base.glucose.push(...db.glucoseToday)
  return base
}

export const mockApi: Api = {
  async getPatient() {
    return wait(clone(fx.patient))
  },

  async getHome() {
    const due = db.doses.filter((d) => d.day === 'today' && d.status === 'due')
    const unc = db.doses.find((d) => d.day === 'yesterday' && d.status === 'unconfirmed') ?? null
    const unread = db.notices.filter((n) => n.unread).length
    const home: HomeData = {
      greeting: 'Good evening, Mr Tan',
      dateLabel: appConfig.demo.dateLabel,
      alert: { text: 'Your morning readings have been higher than your usual for 3 weeks. Worth mentioning to your doctor.', to: 'C2' },
      tiles: [
        { key: 'glucose', label: 'Glucose', value: '78%', unit: 'in range', sub: 'Latest 7.8 mmol/L', to: 'C2' },
        { key: 'activity', label: 'Activity', value: thousands(5840), unit: 'steps', sub: `${db.moderateMin} of 150 min this week`, to: 'C4' },
        { key: 'sleep', label: 'Sleep', value: '5 h 50 min', unit: '', sub: 'Your usual is 6 h 50 min', to: 'C5' },
        { key: 'mood', label: 'Mood and stress', value: '3 and 4', unit: 'of 5', sub: 'Evening check-in', to: 'C5' },
      ],
      dosesDue: clone(due),
      unconfirmed: unc ? clone(unc) : null,
      exercisePrompt: db.promptSnoozed ? null : { text: 'Your usual after-dinner walk is coming up. On days you walked after dinner, your evening readings were lower.' },
      checkin: db.checkinDone ? null : { id: 'ck1', question: 'Have you been more thirsty than usual this week?' },
      whatChanged: clone(whatChanged),
      next: { title: `${db.appointment.label} in ${db.appointment.inDays} days`, detail: db.appointment.when },
      sources: clone(fx.sources),
      unreadNotices: unread,
      sprintDay: 9,
      sprintOf: 14,
    }
    return wait(home)
  },

  async markDoseTaken(doseId) {
    const d = db.doses.find((x) => x.id === doseId)
    if (d) d.status = d.status === 'unconfirmed' ? 'taken_late_logged' : 'taken'
    db.notices = db.notices.map((n) => (n.kind === 'dose' ? { ...n, unread: false } : n))
    return wait(undefined, 30)
  },
  async saveMissReason(doseId, reason, note) {
    void note
    const d = db.doses.find((x) => x.id === doseId)
    if (d) {
      d.status = reason === 'felt_fine' || reason === 'forgot' ? 'missed' : 'missed'
      d.reason = reason
    }
    if (reason === 'side_effects') db.questions.push({ id: id('q'), text: 'I noticed side effects around my evening Metformin. What should I know?', origin: 'side_effect' })
    return wait(undefined, 30)
  },
  async answerCheckin(_id, answer) {
    db.checkinDone = true
    if (answer === 'yes') db.questions.push({ id: id('q'), text: 'I have been more thirsty than usual. Is that worth checking?', origin: 'user' })
    return wait(undefined, 30)
  },
  async snoozePrompt() {
    db.promptSnoozed = true
    return wait(undefined, 30)
  },

  async getInsights(period) {
    const grid = buildWeekGrid()
    const ins: Insights = {
      weekGrid: grid,
      whatChanged: clone(whatChanged),
      fasting: { label: 'Fasting glucose', unit: 'mmol/L', points: slice(fx.fastingSeries, period), baseline: [6.6, 7.2], summary: 'Higher than your usual for about 3 weeks. Your last 7 mornings: 7.1 to 7.9 mmol/L.' },
      steps: { label: 'Steps', unit: 'steps', points: slice(fx.stepsSeries, period), baseline: [7400, 8600], summary: 'Your 7-day average is 6,300 steps. Your usual is about 8,000.' },
      sleep: { label: 'Sleep', unit: 'min', points: slice(fx.sleepSeries, period), baseline: [395, 425], summary: 'Your 7-day average is 6 h 10 min. Your usual is 6 h 50 min.' },
      mood: clone(fx.moodSeries),
      timeInRange: { last24h: 78, week: 71, segments: [{ level: 'low', pct: 2 }, { level: 'in_range', pct: 71 }, { level: 'high', pct: 22 }, { level: 'very_high', pct: 5 }] },
      sprint: { day: 9, of: 14, deviceLabel: 'Glucose sensor', avgMmol: 7.4, gmi: 6.5, cv: 24 },
      foods: clone(fx.foodResponses),
      activity: {
        moderateMin: db.moderateMin,
        moderateGoal: appConfig.goals.moderateMinutes,
        strength: 0,
        strengthGoal: appConfig.goals.strengthSessions,
        weeks: [
          { label: '31 Aug', light: 60, moderate: 130, vigorous: 10 },
          { label: '7 Sep', light: 55, moderate: 112, vigorous: 8 },
          { label: '14 Sep', light: 50, moderate: 90, vigorous: 5 },
          { label: '21 Sep', light: 45, moderate: 66, vigorous: 4 },
          { label: 'This week', light: 40, moderate: db.moderateMin, vigorous: 0 },
        ],
        mix: [{ label: 'Aerobic', count: 9 }, { label: 'Strength', count: 1 }, { label: 'Mixed', count: 0 }, { label: 'Flexibility', count: 0 }],
        workouts: clone(fx.workouts),
        stepsToday: 5840,
        stepsAvg7: 6300,
        stepsBaseline: 8000,
      },
      medication: {
        adherencePct: 86,
        taken: 24,
        scheduled: 28,
        reasons: [{ reason: 'Forgot', count: 1 }, { reason: 'Away from home', count: 1 }],
        days: grid.days.map((d) => d.short),
        timeline: [
          { med: 'Metformin', cells: ['missed', 'taken', 'missed', 'taken', 'taken', 'unconfirmed', 'due'] },
          { med: 'Amlodipine', cells: ['taken', 'taken', 'taken', 'taken', 'taken', 'taken', 'taken'] },
          { med: 'Atorvastatin', cells: ['taken', 'taken', 'taken', 'taken', 'unconfirmed', 'taken', 'scheduled'] },
        ],
        fastingOverlay: [7.1, 7.3, 7.2, 7.6, 7.8, 7.5, 7.9],
      },
      patterns: [
        { id: 'p1', text: 'On mornings after an evening walk (7 nights), fasting glucose was 0.6 mmol/L lower.', n: 7 },
        { id: 'p2', text: 'On nights with under 6 hours of sleep (6 nights), fasting glucose was 0.5 mmol/L higher.', n: 6 },
      ],
    }
    return wait(ins)
  },

  async getDay(date) {
    return wait(dayWith(date))
  },
  async getDayList() {
    return wait(fx.dayDates.map((d) => ({ date: d, short: shortDate(d), weekday: weekdayShort(d) })))
  },

  async logEntry(input: LogInput) {
    const now = nowMinutes()
    const day = today
    let res: LogResult
    const addRecent = (e: Omit<RecentEntry, 'id' | 'date'>) => db.recent.unshift({ ...e, id: id('re'), date: day })
    const extra = (db.extraByDay[day] ??= {})
    switch (input.kind) {
      case 'meal': {
        const lower = input.name.toLowerCase()
        const salty = /laksa|chicken rice|mee goreng|char kway|curry|soup noodle|bak kut/.test(lower)
        const carbs = Math.round((/rice|noodle|laksa|mee|bread|toast/.test(lower) ? 70 : 35) * input.portion)
        ;(extra.meals ??= []).push({ id: id('m'), t: now, name: input.name, carbsG: carbs, flags: salty ? ['high_salt'] : [], estimated: true })
        addRecent({ kind: 'meal', title: input.name, detail: `Estimated ${carbs} g carbs`, when: clock(now) })
        res = {
          kind: 'meal', title: 'Meal saved', landedIn: 'Your day', detail: `${input.name}, estimated ${carbs} g carbs.`,
          lines: ['Nutrients are estimates until you confirm them.', 'Your glucose rise will come from the sensor in about 2 hours.'],
          related: 'C3', day,
          flag: salty ? { text: 'High salt estimated for this meal.', level: 'info' } : undefined,
          swap: salty ? { text: 'Ask for the soup or gravy on the side, or choose the clear soup version next time.', source: 'Team-written tip, not medical advice' } : undefined,
        }
        break
      }
      case 'glucose': {
        const level = glucoseLevel(input.value)
        db.glucoseToday.push({ t: now, v: input.value })
        addRecent({ kind: 'glucose', title: `${input.context} glucose ${input.value.toFixed(1)} mmol/L`, detail: input.context, when: clock(now) })
        res = {
          kind: 'glucose', title: 'Reading saved', landedIn: 'Your day and Glucose insights', detail: `${input.value.toFixed(1)} mmol/L, ${input.context.toLowerCase()}.`,
          lines: [], related: 'C2', day,
          flag: { text: level === 'in_range' ? 'In your range of 3.9 to 10.0 mmol/L.' : level === 'high' ? 'Above your range of 3.9 to 10.0 mmol/L.' : level === 'very_high' ? 'Much higher than your range.' : 'Below your range of 3.9 to 10.0 mmol/L.', level },
          urgent: input.value < appConfig.glucoseRanges.veryLow,
        }
        break
      }
      case 'workout': {
        db.moderateMin += input.intensity === 'light' ? 0 : input.minutes
        const start = 19 * 60 + 35
        ;(extra.workouts ??= []).push({ id: id('w'), t: start, minutes: input.minutes, label: input.activity, intensity: input.intensity })
        addRecent({ kind: 'workout', title: `${input.activity}, ${input.minutes} min`, detail: input.intensity[0]!.toUpperCase() + input.intensity.slice(1), when: input.start })
        res = {
          kind: 'workout', title: 'Added to your day', landedIn: 'Your day and Activity insights', detail: `${input.activity}, ${input.minutes} minutes, ${input.intensity}.`,
          lines: [`This week: ${db.moderateMin} of 150 minutes of moderate activity, 0 of 2 strength sessions.`, 'We will ask for a glucose reading 30 minutes after, so your doctor can see how exercise affects you.'],
          related: 'C4', day,
        }
        break
      }
      case 'symptom': {
        ;(extra.symptoms ??= []).push({ id: id('s'), t: now, label: input.label, severity: input.severity })
        addRecent({ kind: 'symptom', title: input.label, detail: `Strength ${input.severity} of 5`, when: clock(now) })
        res = { kind: 'symptom', title: 'Symptom saved', landedIn: 'Your day and your doctor brief', detail: `${input.label}, strength ${input.severity} of 5.`, lines: ['This will appear in your doctor brief. You can see everything the doctor sees.'], related: 'C2', day }
        break
      }
      default: {
        addRecent({ kind: 'checkin', title: 'Evening check-in', detail: `Mood ${input.mood}, stress ${input.stress}`, when: clock(now) })
        res = { kind: 'checkin', title: 'Check-in saved', landedIn: 'Sleep and stress insights', detail: `Mood ${input.mood}, stress ${input.stress}, sleep quality ${input.sleep}, energy ${input.energy}.`, lines: [], related: 'C5', day }
      }
    }
    return wait(res)
  },
  async listRecent() {
    return wait(clone(db.recent))
  },
  async deleteEntry(entryId) {
    db.recent = db.recent.filter((e) => e.id !== entryId)
    return wait(undefined, 30)
  },

  async listMedications() {
    return wait(clone(db.meds))
  },
  async getMedication(medId) {
    return wait(clone(db.meds.find((m) => m.id === medId)))
  },
  async addMedication(m) {
    const med: Medication = { id: id('med'), name: m.name, strength: m.strength, kind: 'prescription', times: m.times, withFood: m.withFood, purpose: 'Added by hand. Ask your pharmacist what it is for.', badge: 'not_checked', refill: null, sideEffects: [] }
    db.meds.push(med)
    return wait(clone(med))
  },
  async getScanResult() {
    return wait(clone(fx.scanResult))
  },
  async confirmScan() {
    const med: Medication = { id: 'clarithromycin', name: 'Clarithromycin', strength: '500 mg', kind: 'prescription', times: ['8:30 am', '8:30 pm'], withFood: true, purpose: 'An antibiotic for a bacterial infection, taken as a short course.', badge: 'interaction', refill: null, sideEffects: ['Upset stomach', 'A bitter or metal taste', 'Loose stools'] }
    if (!db.scanAdded) {
      db.meds.push(med)
      db.meds = db.meds.map((m) => (m.id === 'atorvastatin' ? { ...m, badge: 'interaction' } : m))
      db.scanAdded = true
    }
    return wait(clone(med))
  },
  async listDosesToday() {
    return wait(clone(db.doses.filter((d) => d.day === 'today')))
  },

  async getFacts() {
    return wait({ facts: clone(db.facts), compare: clone(fx.weekCompare) })
  },
  async factAction(factId, action, text) {
    if (action === 'delete') db.facts = db.facts.filter((f) => f.id !== factId)
    if (action === 'confirm') db.facts = db.facts.map((f) => (f.id === factId ? { ...f, status: 'active', confidence: 3, evidenceStatus: 'observed' } : f))
    if (action === 'edit' && text) db.facts = db.facts.map((f) => (f.id === factId ? { ...f, statement: text, status: 'active', evidenceStatus: 'observed' } : f))
    return wait(undefined, 30)
  },

  async getCarePlan() {
    const plan: CarePlan = { appointment: clone(db.appointment), preventive: clone(fx.preventive), questions: clone(db.questions) }
    return wait(plan)
  },
  async addQuestion(text, origin) {
    db.questions.push({ id: id('q'), text, origin })
    return wait(undefined, 30)
  },
  async removeQuestion(qid) {
    db.questions = db.questions.filter((q) => q.id !== qid)
    return wait(undefined, 30)
  },
  async planAppointment(label, when) {
    db.appointment = { ...db.appointment, label, when }
    return wait(undefined, 30)
  },

  async getBrief() {
    const b: BriefData = {
      initials: fx.patient.initials,
      birthYear: fx.patient.birthYear,
      period: '4 weeks to 1 October 2026',
      completeness: [
        { stream: 'Glucose sensor', pct: 94 },
        { stream: 'Meals', pct: 86 },
        { stream: 'Watch', pct: 91 },
        { stream: 'Doses', pct: 100 },
        { stream: 'Mood check-ins', pct: 64 },
      ],
      top3: [
        { id: 't1', text: 'Fasting glucose has been higher than the personal baseline for about 3 weeks (7.1 to 7.9 mmol/L over the last 7 mornings).', evidence: 'Glucose sensor and glucometer, 28 days' },
        { id: 't2', text: 'Less activity and shorter sleep: moderate minutes fell from 140 to 70 a week, and sleep averaged 6 h 10 min.', evidence: 'Watch and workout log, 4 weeks' },
        { id: 't3', text: 'Two missed evening doses of Metformin (reasons: forgot, away from home) and two unconfirmed.', evidence: 'Dose log, 7 days' },
      ],
      patterns: (await mockApi.getInsights(30)).patterns,
      symptoms: [{ date: '27 Sep', label: 'More thirsty than usual', severity: 2 }],
      preventive: clone(fx.preventive),
      questions: db.questions.map((q) => q.text),
      dayTraces: [{ kind: 'best', date: '2026-09-28' }, { kind: 'worst', date: '2026-09-27' }, { kind: 'typical', date: '2026-09-29' }],
    }
    return wait(b)
  },
  async createShareLink() {
    db.shared = true
    return wait({ url: 'smarthealth.example/brief/k7Qm-2xF9', expiresIn: `${appConfig.shareLinkHours} hours` })
  },
  async revokeShareLink() {
    db.shared = false
    return wait(undefined, 30)
  },

  async listNotices(): Promise<Notice[]> {
    return wait(clone(db.notices))
  },
  async markNoticesRead() {
    db.notices = db.notices.map((n) => ({ ...n, unread: false }))
    return wait(undefined, 30)
  },
  async listSources() {
    return wait(clone(fx.sources))
  },
  async syncSources() {
    return wait(undefined, 400)
  },

  async sendChat(text): Promise<ChatReply> {
    const t = text.toLowerCase()
    if (/(skip|stop|double|change|cut|reduce|increase|take less|take more|quit)/.test(t) && /(metformin|medicine|medication|pill|dose|amlodipine|atorvastatin)/.test(t)) {
      return wait({
        kind: 'safety',
        text: "I can't advise on changing your medication, but your doctor or pharmacist can. Want me to add this to your questions for your visit?",
        actions: [{ id: 'add_question', label: 'Add to my doctor questions' }, { id: 'dismiss', label: 'Not now' }],
      }, 380)
    }
    if (/week/.test(t)) {
      return wait({ kind: 'normal', text: 'This week your fasting readings were 7.1 to 7.9 mmol/L, higher than your usual of 6.6 to 7.2. You took 24 of 28 doses and walked on 2 days. Your sleep averaged 6 h 10 min.', actions: [{ id: 'open_week', label: 'See your week' }] }, 420)
    }
    if (/metformin|for\?|what is/.test(t)) {
      return wait({ kind: 'normal', text: 'Metformin helps your body use its own insulin better. Your label says 500 mg, twice daily, with food. Common side effects include an upset stomach. Source: your label and a drug information dataset. This is not medical advice.', actions: [{ id: 'open_med', label: 'Open the Metformin page' }] }, 420)
    }
    return wait({ kind: 'normal', text: 'I can explain your medicines, look back over your week, or add a question for your doctor. I cannot give medical advice. What would you like to look at?' }, 380)
  },
}
