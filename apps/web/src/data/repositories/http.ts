import { appConfig } from '@/config/app'
import type { Api } from './types'

/**
 * The production data layer. Every method of `Api` goes through here, so screens never know whether
 * data comes from a mock or from the backend. Wire one method at a time: replace `todo('name')` with a
 * call to `request(...)`. Endpoint names follow docs/specs/architecture.md section 7.
 */
export class NotWired extends Error {
  constructor(method: string) {
    super(`Api.${method} is not wired to the backend yet`)
    this.name = 'NotWired'
  }
}

const todo = (name: string) => async (): Promise<never> => {
  throw new NotWired(name)
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${appConfig.apiBaseUrl}${path}`, { credentials: 'include', headers: { 'Content-Type': 'application/json' }, ...init })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return (await res.json()) as T
}

export const httpApi: Api = {
  // Example of a wired method. The rest throw NotWired until the endpoint exists.
  getPatient: () => request('/patient'),
  getHome: todo('getHome'),
  markDoseTaken: todo('markDoseTaken'),
  saveMissReason: todo('saveMissReason'),
  answerCheckin: todo('answerCheckin'),
  snoozePrompt: todo('snoozePrompt'),
  getInsights: todo('getInsights'),
  getDay: todo('getDay'),
  getDayList: todo('getDayList'),
  logEntry: todo('logEntry'),
  listRecent: todo('listRecent'),
  deleteEntry: todo('deleteEntry'),
  listMedications: todo('listMedications'),
  getMedication: todo('getMedication'),
  addMedication: todo('addMedication'),
  getScanResult: todo('getScanResult'),
  confirmScan: todo('confirmScan'),
  listDosesToday: todo('listDosesToday'),
  getFacts: todo('getFacts'),
  factAction: todo('factAction'),
  getCarePlan: todo('getCarePlan'),
  addQuestion: todo('addQuestion'),
  removeQuestion: todo('removeQuestion'),
  planAppointment: todo('planAppointment'),
  getBrief: todo('getBrief'),
  createShareLink: todo('createShareLink'),
  revokeShareLink: todo('revokeShareLink'),
  listNotices: todo('listNotices'),
  markNoticesRead: todo('markNoticesRead'),
  listSources: todo('listSources'),
  syncSources: todo('syncSources'),
  sendChat: todo('sendChat'),
  getEmergencyContact: todo('getEmergencyContact'),
  saveEmergencyContact: todo('saveEmergencyContact'),
  recordAwareness: todo('recordAwareness'),
  saveWorkoutSession: todo('saveWorkoutSession'),
  getWorkoutSummary: todo('getWorkoutSummary'),
}
