import { appConfig } from '@/config/app'
import type { Api, LogInput } from './types'
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
  return (await res.json()) as T
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
  getInsightsGlucose: (days) => request(`/insights/glucose?days=${days}`),
  getInsightsFood: (days) => request(`/insights/food?days=${days}`),
  getInsightsActivity: (days) => request(`/insights/activity?days=${days}`),
  getInsightsSleep: (days) => request(`/insights/sleep?days=${days}`),
  getInsightsMedication: (days) => request(`/insights/medication?days=${days}`),
  getInsightsSprint: () => request('/insights/sprint'),
  getDay: todo('getDay'),
  getDayList: todo('getDayList'),
  logEntry: (input: LogInput) => request('/logs', { method: 'POST', body: JSON.stringify(input) }),
  listRecent: () => request('/logs/recent'),
  analyzeMeal: async (file: File, description?: string) => {
    const fd = new FormData()
    fd.append('file', file)
    if (description?.trim()) fd.append('description', description.trim())
    const res = await fetch(`${appConfig.apiBaseUrl}/meals/analyze`, { method: 'POST', body: fd, credentials: 'include', headers: asUser() })
    if (!res.ok) throw new Error(((await res.json().catch(() => null)) as { detail?: string } | null)?.detail ?? `${res.status} ${res.statusText}`)
    return res.json()
  },
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
  getWeekWorkouts: () => request('/workouts/week'),
  deleteEntry: (id: string) => request<void>(`/logs/${id}`, { method: 'DELETE' }).then(() => undefined),
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
  uploadScan: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return fetch(`${appConfig.apiBaseUrl}/scans`, { method: 'POST', body: fd, credentials: 'include', headers: asUser() })
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
        return res.json()
      })
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
