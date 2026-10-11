/**
 * Data for sharing the doctor report by link (L2), the shared page (/s/:token) and the links on L1.
 * The authenticated calls go through `request`. The public read does not send X-User: the token is the only key.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { appConfig } from '@/config/app'
import { request } from '@/data/repositories/http'
import type { DoctorReport } from '@/data/types'

export type ShareDays = 7 | 14 | 30 | 90
export type ShareHours = 24 | 72 | 168
export type ShareStatus = 'active' | 'expired' | 'revoked'

export interface ShareItem {
  id: string
  days: number
  createdAt: string
  expiresAt: string
  revokedAt: string | null
  status: ShareStatus
  viewCount: number
  lastViewedAt: string | null
}

export interface ShareCreated {
  id: string
  /** shown once, when the link is made; the server keeps only its hash */
  token: string
  /** the page on this site, for example /s/<token> */
  path: string
  days: number
  expiresAt: string
}

export interface ShareContext {
  questions: { id: string; text: string }[]
  nextAppointment: { id: string; kind: string; scheduledFor: string; location: string | null } | null
}

const KEY = ['shares'] as const
const CONTEXT_KEY = ['shareContext'] as const

export const useShares = () => useQuery({ queryKey: KEY, queryFn: () => request<{ shares: ShareItem[] }>('/brief/shares').then((r) => r.shares) })

export const useShareContext = () => useQuery({ queryKey: CONTEXT_KEY, queryFn: () => request<ShareContext>('/brief/shares/context') })

export function useCreateShare() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: { days: ShareDays; hours: ShareHours }) => request<ShareCreated>('/brief/shares', { method: 'POST', body: JSON.stringify(input) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}

export function useRevokeShare() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => request<{ id: string; status: 'revoked'; revokedAt: string }>(`/brief/shares/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}

/** Thrown for any non-OK answer. A 404 means wrong, expired or turned off: the page says so, and nothing is retried. */
export class SharedReportError extends Error {
  constructor(readonly status: number) {
    super(`HTTP ${status}`)
    this.name = 'SharedReportError'
  }
}

export async function fetchSharedReport(token: string): Promise<DoctorReport> {
  const res = await fetch(`${appConfig.apiBaseUrl}/brief/shares/public/${encodeURIComponent(token)}/report`)
  if (!res.ok) throw new SharedReportError(res.status)
  return (await res.json()) as DoctorReport
}

export const useSharedReport = (token: string | undefined) =>
  useQuery({
    queryKey: ['sharedReport', token],
    queryFn: () => fetchSharedReport(token ?? ''),
    enabled: Boolean(token),
    retry: (count, err) => !(err instanceof SharedReportError && err.status === 404) && count < 2,
    refetchOnWindowFocus: false,
  })

/** The full address of a link, for copying. Built from the page's own origin, so it works on any host. */
export const shareAddress = (path: string) => `${window.location.origin}${path}`

/**
 * Plain words for the appointment kinds the server stores. The same words as the care plan (me/care/api.ts), so a visit reads the same
 * on every screen. Vaccination and Dental check are kept only for older visits: the form no longer offers them.
 */
export const APPOINTMENT_KIND: Record<string, string> = {
  gp_review: 'GP review',
  diabetes_review: 'Diabetes review',
  eye_screening: 'Eye screening',
  foot_screening: 'Foot check',
  kidney_test: 'Kidney test',
  hba1c_test: 'Blood test',
  vaccination: 'Vaccination',
  dental: 'Dental check',
  other: 'Other visit',
}

const WHEN = { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Singapore' } as const

/** "Sat 11 Oct, 10:00" in the clinic's time zone (Singapore). */
export const formatWhen = (iso: string) => new Date(iso).toLocaleString('en-SG', WHEN)
