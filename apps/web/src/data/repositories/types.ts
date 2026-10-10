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
  InsightsOverview,
  InsightsGlucose,
  InsightsFood,
  InsightsActivity,
  InsightsSleep,
  InsightsMedication,
  InsightsSprint,
  ExerciseKind,
  AiUsage,
  AuditRun,
  FoodHabit,
  Learned,
  Progress,
  WeekDigest,
  FoodNote,
  LunchIdeas,
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
  | { kind: 'workout'; type: ExerciseKind; activity: string; intensity: number; startAt: string; minutes: number; feeling?: number }
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
  | { kind: 'checkin'; mood: number; stress: number; sleep: number; energy: number }

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
  getInsightsGlucose(days: InsightsDays): Promise<InsightsGlucose>
  getInsightsFood(days: InsightsDays): Promise<InsightsFood>
  getInsightsActivity(days: InsightsDays): Promise<InsightsActivity>
  getInsightsSleep(days: InsightsDays): Promise<InsightsSleep>
  getInsightsMedication(days: InsightsDays): Promise<InsightsMedication>
  getInsightsSprint(): Promise<InsightsSprint>
  getDay(date: string): Promise<DayTimeline>
  getDayList(): Promise<{ date: string; short: string; weekday: string }[]>

  logEntry(input: LogInput): Promise<LogResult>
  listRecent(): Promise<RecentEntry[]>
  /** Photo (and an optional description) to estimated nutrients, read by the vision model */
  analyzeMeal(file: File, description?: string): Promise<MealAnalysis>
  getFoodNote(food: string): Promise<FoodNote>
  getFoodFlags(): Promise<FoodHabit[]>
  getLunchIdeas(): Promise<LunchIdeas>
  acceptSuggestion(key: string): Promise<void>
  dismissSuggestion(key: string): Promise<void>
  getAiUsage(): Promise<AiUsage>
  getLogProgress(): Promise<LogProgress>
  getLogContext(): Promise<LogContext>
  getLearned(): Promise<Learned>
  learnedAction(id: string, action: 'confirm' | 'edit' | 'delete', text?: string): Promise<void>
  getDigest(): Promise<WeekDigest>
  getAudit(): Promise<AuditRun[]>
  getProgress(): Promise<Progress>
  getWeekWorkouts(): Promise<WeekWorkouts>
  deleteEntry(id: string): Promise<void>

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
  uploadScan(file: File): Promise<ScanResult>
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
