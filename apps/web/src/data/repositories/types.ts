import type {
  BriefData,
  CarePlan,
  ChatReply,
  ConnectedSource,
  DayTimeline,
  Dose,
  HomeData,
  Insights,
  Intensity,
  LogResult,
  MemoryFact,
  MissReason,
  Medication,
  EmergencyContact,
  SymptomDetail,
  WorkoutSession,
  WorkoutSummary,
  Notice,
  Patient,
  Period,
  RecentEntry,
  ScanResult,
  WeekCompare,
  WorkoutType,
} from '../types'

export type LogInput =
  | { kind: 'meal'; name: string; portion: number; viaPhoto: boolean }
  | { kind: 'glucose'; value: number; context: string }
  | { kind: 'workout'; type: WorkoutType; activity: string; intensity: Intensity; minutes: number; start: string; feel: string }
  | { kind: 'symptom'; label: string; severity: number; note?: string; detail?: SymptomDetail }
  | { kind: 'checkin'; mood: number; stress: number; sleep: number; energy: number }

export interface NewMedication {
  name: string
  strength: string
  times: string[]
  withFood: boolean
}

/**
 * The only door between screens and data. The mock below implements it in memory.
 * The real API implements the same interface, so screens never change.
 */
export interface Api {
  getPatient(): Promise<Patient>
  getHome(): Promise<HomeData>
  markDoseTaken(id: string): Promise<void>
  saveMissReason(id: string, reason: MissReason, note?: string): Promise<void>
  answerCheckin(id: string, answer: 'yes' | 'no' | 'skip'): Promise<void>
  snoozePrompt(): Promise<void>

  getInsights(period: Period): Promise<Insights>
  getDay(date: string): Promise<DayTimeline>
  getDayList(): Promise<{ date: string; short: string; weekday: string }[]>

  logEntry(input: LogInput): Promise<LogResult>
  listRecent(): Promise<RecentEntry[]>
  deleteEntry(id: string): Promise<void>

  listMedications(): Promise<Medication[]>
  getMedication(id: string): Promise<Medication | undefined>
  addMedication(m: NewMedication): Promise<Medication>
  getScanResult(): Promise<ScanResult>
  confirmScan(): Promise<Medication>
  listDosesToday(): Promise<Dose[]>

  getFacts(): Promise<{ facts: MemoryFact[]; compare: WeekCompare }>
  factAction(id: string, action: 'confirm' | 'delete' | 'edit', text?: string): Promise<void>

  getCarePlan(): Promise<CarePlan>
  addQuestion(text: string, origin: CarePlan['questions'][number]['origin']): Promise<void>
  removeQuestion(id: string): Promise<void>
  planAppointment(label: string, when: string): Promise<void>

  getBrief(): Promise<BriefData>
  createShareLink(): Promise<{ url: string; expiresIn: string }>
  revokeShareLink(): Promise<void>

  listNotices(): Promise<Notice[]>
  markNoticesRead(): Promise<void>
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
