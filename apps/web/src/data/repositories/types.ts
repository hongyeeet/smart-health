import type {
  BriefData,
  DoctorReport,
  ReportDays,
  CarePlan,
  ChatReply,
  ConnectedSource,
  DayTimeline,
  HomeData,
  Insights,
  InsightsDays,
  Menu,
  MenuMeal,
  TimelineDays,
  InsightsOverview, InsightsTimeline, InsightsDay,
  InsightsOverviewDays,
  InsightsGlucose,
  InsightsFood,
  InsightsActivity,
  InsightsSleep,
  InsightsMedication,
  InsightsSprint,
  InsightsHeart,
  InsightsBloodPressure,
  ExerciseKind,
  AiUsage,
  AuditRun,
  FoodHabit,
  Learned,
  Progress,
  DietDays,
  BarrierSummary,
  WeekDigest,
  FoodNote,
  LunchIdeas,
  BloodPressureEntry,
  WorkoutEntry,
  LogContext,
  LogProgress,
  MealAnalysis,
  WeekWorkouts,
  LogResult,
  MemoryFact,
  ClashStatus,
  MissAnswer,
  DosesToday,
  Medication,
  MedicationDetail,
  MedicineExplanation,
  EmergencyContact,
  WorkoutSession,
  WorkoutSummary,
  Notice,
  Patient,
  Period,
  RecentEntry,
  ScanResult,
  WeekCompare,
} from '../types'

/** The stable codes the meal photo endpoint returns (services/api/app/api/routers/meals.py); `network` and `timeout` are set by the app itself. */
export type MealErrorCode = 'bad_photo' | 'not_food' | 'model_unavailable' | 'daily_limit' | 'timeout' | 'bad_response' | 'save_failed' | 'network'

/** A meal photo could not be read. `message` is the plain sentence to show; `code` decides the next step the screen offers. */
export class MealReadError extends Error {
  code: MealErrorCode
  constructor(code: MealErrorCode, message: string) {
    super(message)
    this.name = 'MealReadError'
    this.code = code
  }
}

export type LogInput =
  | {
      kind: 'meal'
      name: string
      description?: string
      startAt: string
      endAt: string
      portion: number
      kcal: number | null
      carbsG: number | null
      proteinG: number | null
      fatG: number | null
      sugarG: number | null
      fibreG: number | null
      sodiumMg: number | null
      analysisId?: string
      edited: boolean
      /** which numbers were saved */
      valuesFrom: 'ai' | 'user'
    }
  /** null when the workout was not rated; feeling is null when the question was not answered */
  | { kind: 'workout'; type: ExerciseKind; activity: string; intensity: number | null; startAt: string; minutes: number; feeling?: number | null }
  | {
      kind: 'symptom'
      label: string
      severity: number
      occurredAt: string
      /** how long the person felt it, in minutes; omitted when it is still going or unknown */
      durationMin?: number
      side?: string
      relation?: string
      feel?: string
      note?: string
    }
  /** each answer is omitted when the person did not answer that question; at least one is needed */
  | { kind: 'checkin'; mood?: number; stress?: number; sleep?: number; energy?: number }
  | {
      kind: 'blood_pressure'
      systolic: number
      diastolic: number
      /** beats a minute; omitted when not measured */
      pulse?: number
      /** ISO time taken; omitted means now */
      measuredAt?: string
      note?: string
    }

/** A blood pressure reading as sent for save or edit (screen E3). */
export type WorkoutLogInput = Extract<LogInput, { kind: 'workout' }>
export type BloodPressureLogInput = Extract<LogInput, { kind: 'blood_pressure' }>

/** A medicine added by hand (screen H8). Times are 24-hour clock text ("08:00"), the person's own local time. */
export interface NewMedicationDose {
  /** 24-hour clock text, or null when the medicine is taken only when needed (then it has exactly one dose, with no time). */
  time: string | null
  /** Units each time (tablets, capsules or measures). */
  quantity: number
  mealRelation: 'before_meal' | 'after_meal' | 'na'
}

export interface NewMedication {
  name: string
  kind: 'prescription' | 'otc' | 'supplement' | 'tcm'
  strength: string
  doses: NewMedicationDose[]
  /** Required: the total tablets, capsules or units supplied. Used to tell the person when they may run out. */
  totalQuantity: number
  /** YYYY-MM-DD, or null for today. */
  startDate: string | null
  /** Directions as printed on the label, optional. */
  directions: string
  /** Set when this typed form completes a scan that needed manual entry. */
  scanId?: string
}

/**
 * The only door between screens and data. The mock below implements it in memory.
 * The real API implements the same interface, so screens never change.
 */
export interface Api {
  getPatient(): Promise<Patient>
  getHome(): Promise<HomeData>
  markDoseTaken(id: string): Promise<void>
  saveMissReason(id: string, reason: MissAnswer, note?: string): Promise<void>
  answerCheckin(id: string, answer: 'yes' | 'no' | 'skip'): Promise<void>
  snoozePrompt(): Promise<void>

  getInsights(period: Period): Promise<Insights>
  getInsightsOverview(days: InsightsDays): Promise<InsightsOverview>
  getInsightsTimeline(days: TimelineDays, end?: string): Promise<InsightsTimeline>
  getInsightsDay(date: string): Promise<InsightsDay>
  getInsightsOverviewDays(from: string, to: string): Promise<InsightsOverviewDays>
  getInsightsGlucose(days: InsightsDays): Promise<InsightsGlucose>
  getInsightsFood(days: InsightsDays): Promise<InsightsFood>
  getInsightsActivity(days: InsightsDays): Promise<InsightsActivity>
  getInsightsSleep(days: InsightsDays): Promise<InsightsSleep>
  getInsightsMedication(month?: string): Promise<InsightsMedication>
  getInsightsSprint(): Promise<InsightsSprint>
  getInsightsHeart(days: InsightsDays): Promise<InsightsHeart>
  getInsightsBloodPressure(days: InsightsDays): Promise<InsightsBloodPressure>
  getDay(date: string): Promise<DayTimeline>
  getDayList(): Promise<{ date: string; short: string; weekday: string }[]>

  logEntry(input: LogInput): Promise<LogResult>
  listRecent(): Promise<RecentEntry[]>
  /** Photo (and an optional description) to estimated nutrients, read by the vision model */
  analyzeMeal(file: File, description?: string, signal?: AbortSignal): Promise<MealAnalysis>
  getFoodNote(food: string): Promise<FoodNote>
  getFoodFlags(): Promise<FoodHabit[]>
  getLunchIdeas(): Promise<LunchIdeas>
  acceptSuggestion(key: string): Promise<void>
  getMenu(meal: MenuMeal | 'all'): Promise<Menu>
  pickMenuItem(meal: MenuMeal, key: string): Promise<void>
  dismissSuggestion(key: string): Promise<void>
  getAiUsage(): Promise<AiUsage>
  getLogProgress(): Promise<LogProgress>
  getLogContext(): Promise<LogContext>
  getLearned(): Promise<Learned>
  learnedAction(id: string, action: 'confirm' | 'edit' | 'delete', text?: string): Promise<void>
  getDigest(): Promise<WeekDigest>
  getAudit(): Promise<AuditRun[]>
  getProgress(): Promise<Progress>
  /** Diet tracking calendar: each Singapore day from `start` to `end` (YYYY-MM-DD, at most 62 days). */
  getDietDays(start: string, end: string): Promise<DietDays>
  getBarrierSummary(): Promise<BarrierSummary>
  getWeekWorkouts(): Promise<WeekWorkouts>
  deleteEntry(id: string): Promise<void>
  /** One saved blood pressure reading, for the edit sheet (E7). */
  getBloodPressure(id: string): Promise<BloodPressureEntry>
  /** Edit a blood pressure reading: the old one is removed and the new one saved (the entry gets a new id). */
  getWorkout(id: string): Promise<WorkoutEntry>
  updateWorkout(id: string, input: WorkoutLogInput): Promise<LogResult>
  updateBloodPressure(id: string, input: BloodPressureLogInput): Promise<LogResult>

  listMedications(): Promise<Medication[]>
  getMedication(id: string): Promise<MedicationDetail>
  /** Make (or fetch the saved) plain-language explanation of a medicine: a web search and a short summary, 10 to 30 seconds the first time. */
  explainMedication(id: string): Promise<MedicineExplanation>
  /** Save a question for the doctor, about this medicine, to the doctor-question list. */
  askDoctorAbout(id: string, text: string): Promise<void>
  addMedication(m: NewMedication): Promise<Medication>
  /** Remove one of the person's medicines (its deleted_at is filled in; the dose history is kept). */
  removeMedication(id: string): Promise<void>
  /** Upload a label photo and start AI extraction. Returns the scan with extracted fields. */
  uploadScan(file: File, cancel?: AbortSignal): Promise<ScanResult>
  /** Re-fetch a scan by id (for polling while extracting, or re-reviewing). */
  getScanResult(scanId: string): Promise<ScanResult>
  /** User confirms the reviewed/edited fields → saves the medication (E3-2 does the full save). */
  confirmScan(scanId: string, editedFields: Record<string, string | null>, times: string[], kind?: NewMedication['kind'], asNeeded?: boolean): Promise<Medication>
  getDosesToday(): Promise<DosesToday>
  /** The medicine clash alerts that are open, and whether a check is running now. */
  getClash(): Promise<ClashStatus>
  /** Run the clash check again now (it also runs in the background after every medicine is added). */
  runClashCheck(): Promise<ClashStatus>
  /** Save "Is it OK to take X and Y together?" to the doctor-question list, or the person's own question when `text` is given. */
  askAboutClash(alertId: string, text?: string): Promise<void>
  /** "I have checked with my doctor": the alert stops showing. */
  acknowledgeClash(alertId: string): Promise<ClashStatus>

  getFacts(): Promise<{ facts: MemoryFact[]; compare: WeekCompare }>
  factAction(id: string, action: 'confirm' | 'delete' | 'edit', text?: string): Promise<void>

  getCarePlan(): Promise<CarePlan>
  addQuestion(text: string, origin: CarePlan['questions'][number]['origin']): Promise<void>
  removeQuestion(id: string): Promise<void>
  planAppointment(label: string, when: string): Promise<void>

  getBrief(): Promise<BriefData>
  /** The printable doctor report for the last `days` days of data. All numbers come from the server. */
  getDoctorReport(days: ReportDays): Promise<DoctorReport>
  createShareLink(): Promise<{ url: string; expiresIn: string }>
  revokeShareLink(): Promise<void>

  listNotices(): Promise<Notice[]>
  /** The Reminders page: the last 45 days, newest first; nothing leaves the list when it is done or opened */
  listNoticeHistory(): Promise<Notice[]>
  openNotice(id: string): Promise<void>
  listSources(): Promise<ConnectedSource[]>
  syncSources(): Promise<void>

  sendChat(text: string): Promise<ChatReply>

  getEmergencyContact(): Promise<EmergencyContact>
  saveEmergencyContact(c: EmergencyContact): Promise<void>
  recordAwareness(answer: 'felt_first' | 'sensor_first' | 'not_sure'): Promise<void>

  /** saves a finished strength session and returns its computed summary (duration, volume, heart-rate effort) */
  saveWorkoutSession(s: WorkoutSession): Promise<WorkoutSummary>
  getWorkoutSummary(id: string): Promise<WorkoutSummary>
}
