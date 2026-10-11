import { appConfig } from '@/config/app'
import { MealReadError, type Api, type LogInput, type MealErrorCode } from './types'
import type { MealAnalysis, ScanResult } from '../types'
import { useUi } from '@/state/store'

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

/** Every call says who it is for. Uploads (FormData) leave Content-Type alone so the browser can set the boundary. */
const asUser = (extra?: Record<string, string>): Record<string, string> => ({ 'X-User': useUi.getState().userKey, ...extra })

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${appConfig.apiBaseUrl}${path}`, { credentials: 'include', ...init, headers: asUser({ 'Content-Type': 'application/json', ...(init?.headers as Record<string, string> | undefined) }) })
  if (!res.ok) {
    // The server explains refusals in plain words (`detail`); use them when they are text.
    const detail = ((await res.json().catch(() => null)) as { detail?: unknown } | null)?.detail
    throw new Error(typeof detail === 'string' ? detail : `${res.status} ${res.statusText}`)
  }
  // 204 No Content (a delete) has no body; reading it as JSON would fail after the change was already made
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

/** The server gives up after about 50 s; this is only a backstop for a stalled connection, so the screen always moves on. */
const MEAL_READ_LIMIT_MS = 75_000
/** A label photo that gets no answer within this time is given up (the scan screen then says so and offers Retake or Type it in). */
export const SCAN_UPLOAD_LIMIT_MS = 60_000
const MEAL_CODES: MealErrorCode[] = ['bad_photo', 'not_food', 'model_unavailable', 'daily_limit', 'timeout', 'bad_response', 'save_failed']

/**
 * Sends a meal photo to POST /meals/analyze. Every failure becomes a MealReadError with the server's stable `code`
 * and its plain `detail`. A cancel from the screen (`signal`) is passed on as the browser's AbortError, untouched.
 */
async function analyzeMealPhoto(file: File, description: string | undefined, signal?: AbortSignal): Promise<MealAnalysis> {
  const fd = new FormData()
  fd.append('file', file)
  if (description?.trim()) fd.append('description', description.trim())
  const limit = new AbortController()
  const stop = () => limit.abort()
  const timer = setTimeout(stop, MEAL_READ_LIMIT_MS)
  signal?.addEventListener('abort', stop)
  try {
    let res: Response
    try {
      res = await fetch(`${appConfig.apiBaseUrl}/meals/analyze`, { method: 'POST', body: fd, credentials: 'include', headers: asUser(), signal: limit.signal })
    } catch (e) {
      if (signal?.aborted) throw e
      if (limit.signal.aborted) throw new MealReadError('timeout', 'Reading the photo took too long. Please try again, or type the meal in.')
      throw new MealReadError('network', 'We could not reach Smart Health. Check your internet connection, then try again.')
    }
    const body = (await res.json().catch(() => null)) as { detail?: unknown; code?: unknown } | null
    if (!res.ok) {
      const code = MEAL_CODES.find((c) => c === body?.code) ?? 'model_unavailable'
      const message = typeof body?.detail === 'string' ? body.detail : 'We could not read the photo just now. Please try again, or type the meal in.'
      throw new MealReadError(code, message)
    }
    if (!body) throw new MealReadError('bad_response', 'We could not make sense of the reading for this photo. Please try again, or type the meal in.')
    return body as unknown as MealAnalysis
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', stop)
  }
}

export const httpApi: Api = {
  // Example of a wired method. The rest throw NotWired until the endpoint exists.
  getPatient: () => request('/patient'),
  getHome: todo('getHome'),
  markDoseTaken: async (id) => {
    await request(`/doses/${encodeURIComponent(id)}/taken`, { method: 'POST' })
  },
  saveMissReason: async (id, reason, note) => {
    await request(`/doses/${encodeURIComponent(id)}/reason`, { method: 'POST', body: JSON.stringify({ reason, note: note?.trim() || null }) })
  },
  answerCheckin: todo('answerCheckin'),
  snoozePrompt: todo('snoozePrompt'),
  getInsights: todo('getInsights'),
  getInsightsOverview: (days) => request(`/insights/overview?days=${days}`),
  getInsightsOverviewDays: (from, to) => request(`/insights/overview/days?from=${from}&to=${to}`),
  getInsightsGlucose: (days) => request(`/insights/glucose?days=${days}`),
  getInsightsFood: (days) => request(`/insights/food?days=${days}`),
  getInsightsActivity: (days) => request(`/insights/activity?days=${days}`),
  getInsightsSleep: (days) => request(`/insights/sleep?days=${days}`),
  getInsightsMedication: (days) => request(`/insights/medication?days=${days}`),
  getInsightsSprint: () => request('/insights/sprint'),
  getInsightsHeart: (days) => request(`/insights/heart?days=${days}`),
  getInsightsBloodPressure: (days) => request(`/insights/blood-pressure?days=${days}`),
  getDay: todo('getDay'),
  getDayList: todo('getDayList'),
  logEntry: (input: LogInput) => request('/logs', { method: 'POST', body: JSON.stringify(input) }),
  listRecent: () => request('/logs/recent'),
  analyzeMeal: (file: File, description?: string, signal?: AbortSignal) => analyzeMealPhoto(file, description, signal),
  getFoodNote: (food: string) => request(`/meals/response?food=${encodeURIComponent(food)}`),
  getFoodFlags: () => request('/nutrition/flags'),
  getLunchIdeas: () => request('/nutrition/lunch'),
  acceptSuggestion: (key: string) => request<void>('/nutrition/suggestions/accept', { method: 'POST', body: JSON.stringify({ key, kind: 'suggestion' }) }).then(() => undefined),
  dismissSuggestion: (key: string) => request<void>('/nutrition/suggestions/dismiss', { method: 'POST', body: JSON.stringify({ key, kind: 'suggestion' }) }).then(() => undefined),
  getAiUsage: () => request('/memory/usage'),
  getLogProgress: () => request('/logs/today'),
  getLogContext: () => request('/logs/context'),
  getLearned: () => request('/memory/facts'),
  learnedAction: (id: string, action: 'confirm' | 'edit' | 'delete', text?: string) =>
    request<void>(`/memory/facts/${id}/action`, { method: 'POST', body: JSON.stringify({ action, text }) }).then(() => undefined),
  getDigest: () => request('/memory/digest'),
  getAudit: () => request('/memory/audit'),
  getProgress: () => request('/memory/progress'),
  getDietDays: (start, end) => request(`/memory/progress/days?from=${encodeURIComponent(start)}&to=${encodeURIComponent(end)}`),
  getBarrierSummary: () => request('/memory/barriers/summary'),
  getWeekWorkouts: () => request('/workouts/week'),
  deleteEntry: (id: string) => request<void>(`/logs/${id}`, { method: 'DELETE' }).then(() => undefined),
  getBloodPressure: (id) => request(`/logs/blood-pressure/${encodeURIComponent(id)}`),
  updateBloodPressure: (id, input) => request(`/logs/blood-pressure/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(input) }),
  listMedications: () => request('/medications'),
  getMedication: (id) => request(`/medications/${encodeURIComponent(id)}`),
  explainMedication: (id) => request(`/medications/${encodeURIComponent(id)}/explanation`, { method: 'POST' }),
  askDoctorAbout: async (id, text) => {
    await request(`/medications/${encodeURIComponent(id)}/questions`, { method: 'POST', body: JSON.stringify({ text }) })
  },
  addMedication: (m) => request('/medications', { method: 'POST', body: JSON.stringify(m) }),
  removeMedication: async (id) => {
    await request(`/medications/${encodeURIComponent(id)}`, { method: 'DELETE' })
  },
  uploadScan: async (file: File, cancel?: AbortSignal) => {
    const fd = new FormData()
    fd.append('file', file)
    // A stalled upload ends after SCAN_UPLOAD_LIMIT_MS (or when the person cancels): the screen then offers Retake or Type it in.
    const limit = new AbortController()
    const timer = setTimeout(() => limit.abort(), SCAN_UPLOAD_LIMIT_MS)
    const stop = () => limit.abort()
    cancel?.addEventListener('abort', stop)
    try {
      const res = await fetch(`${appConfig.apiBaseUrl}/scans`, { method: 'POST', body: fd, credentials: 'include', headers: asUser(), signal: limit.signal })
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
      return (await res.json()) as ScanResult
    } finally {
      clearTimeout(timer)
      cancel?.removeEventListener('abort', stop)
    }
  },
  getScanResult: (scanId: string) => request(`/scans/${scanId}`),
  confirmScan: (scanId: string, editedFields: Record<string, string | null>, times: string[], kind?: string, asNeeded?: boolean) =>
    request(`/scans/${scanId}/confirm`, { method: 'POST', body: JSON.stringify({ fields: editedFields, times, kind, asNeeded }) }),
  getDosesToday: () => request('/doses/today'),
  getClash: () => request('/interactions'),
  runClashCheck: () => request('/interactions/check', { method: 'POST' }),
  askAboutClash: async (id, text) => {
    await request(`/interactions/${encodeURIComponent(id)}/question`, { method: 'POST', ...(text ? { body: JSON.stringify({ text }) } : {}) })
  },
  acknowledgeClash: (id) => request(`/interactions/${encodeURIComponent(id)}/acknowledge`, { method: 'POST' }),
  getFacts: todo('getFacts'),
  factAction: todo('factAction'),
  getCarePlan: todo('getCarePlan'),
  addQuestion: todo('addQuestion'),
  removeQuestion: todo('removeQuestion'),
  planAppointment: todo('planAppointment'),
  getBrief: todo('getBrief'),
  getDoctorReport: (days) => request(`/brief/report?days=${days}`),
  createShareLink: todo('createShareLink'),
  revokeShareLink: todo('revokeShareLink'),
  listNotices: () => request('/notifications'),
  openNotice: (id: string) => request<void>(`/notifications/${id}/open`, { method: 'POST' }).then(() => undefined),
  dismissNotice: (id: string) => request<void>(`/notifications/${id}/dismiss`, { method: 'POST' }).then(() => undefined),
  listSources: todo('listSources'),
  syncSources: todo('syncSources'),
  sendChat: todo('sendChat'),
  getEmergencyContact: todo('getEmergencyContact'),
  saveEmergencyContact: todo('saveEmergencyContact'),
  recordAwareness: todo('recordAwareness'),
  saveWorkoutSession: (s) => request('/workouts', { method: 'POST', body: JSON.stringify(s) }),
  getWorkoutSummary: todo('getWorkoutSummary'),
}
