/**
 * Data for the Me settings screens (K5 language, K6 privacy, K8 data and account, K9 emergency contact) and the email reminder
 * switch that K6 shares with onboarding (GET/PUT /notify/email, built by the notify router).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { appConfig } from '@/config/app'
import { request } from '@/data/repositories/http'
import type { Locale } from '@/data/types'
import { useUi } from '@/state/store'

export type ConsentKind = 'data_processing' | 'brief_sharing' | 'calendar_access' | 'caregiver_view' | 'research_use'

export interface Consent {
  kind: ConsentKind
  granted: boolean
  version: string | null
  grantedAt: string | null
}

export interface ConsentHistory {
  kind: ConsentKind
  version: string
  grantedAt: string
  revokedAt: string | null
}

export interface ConsentsState {
  consents: Consent[]
  history: ConsentHistory[]
}

export interface Contact {
  name: string | null
  relation: string | null
  phone: string | null
  email: string | null
  emailSupported: boolean
}

export interface ContactInput {
  name: string
  relation: string
  phone: string
  email: string
}

export interface EmailReminders {
  email: string | null
  optIn: boolean
}

export interface DeletionRequest {
  status: 'received'
  requestedAt: string
  processBy: string
}

const keys = {
  language: ['me', 'language'] as const,
  consents: ['me', 'consents'] as const,
  contact: ['me', 'contact'] as const,
  email: ['notify', 'email'] as const,
}

/* ------------------------------------------------------------------ language (K5) */
export const useLanguage = () => useQuery({ queryKey: keys.language, queryFn: () => request<{ language: Locale }>('/me/language') })

export function useSaveLanguage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (language: Locale) => request<{ language: Locale }>('/me/language', { method: 'PUT', body: JSON.stringify({ language }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.language }),
  })
}

/* ------------------------------------------------------------------ consents (K6) */
export const useConsents = () => useQuery({ queryKey: keys.consents, queryFn: () => request<ConsentsState>('/me/consents') })

export function useSetConsent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (a: { kind: ConsentKind; granted: boolean }) =>
      request<ConsentsState>(`/me/consents/${a.kind}`, { method: 'PUT', body: JSON.stringify({ granted: a.granted }) }),
    onSuccess: (data) => qc.setQueryData(keys.consents, data),
  })
}

/** Email reminders: null address means no emails. The server checks the address; the screen checks it too, for a quick answer. */
export const useEmailReminders = () => useQuery({ queryKey: keys.email, queryFn: () => request<EmailReminders>('/notify/email') })

export function useSaveEmailReminders() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (v: EmailReminders) => request<EmailReminders>('/notify/email', { method: 'PUT', body: JSON.stringify(v) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.email }),
  })
}

/* ------------------------------------------------------------------ data and account (K8) */
export function useRequestDeletion() {
  return useMutation({
    mutationFn: (confirm: string) => request<DeletionRequest>('/me/delete-request', { method: 'POST', body: JSON.stringify({ confirm }) }),
  })
}

/** Downloads the person's own data as a JSON file. Uses the same X-User header as every other call. */
export async function downloadMyData(): Promise<void> {
  const res = await fetch(`${appConfig.apiBaseUrl}/me/export`, { credentials: 'include', headers: { 'X-User': useUi.getState().userKey } })
  if (!res.ok) {
    const detail = ((await res.json().catch(() => null)) as { detail?: unknown } | null)?.detail
    throw new Error(typeof detail === 'string' ? detail : `${res.status} ${res.statusText}`)
  }
  const name = /filename="([^"]+)"/.exec(res.headers.get('Content-Disposition') ?? '')?.[1] ?? 'smart-health-export.json'
  const url = URL.createObjectURL(await res.blob())
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.append(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

/* ------------------------------------------------------------------ emergency contact (K9) */
export const useContact = () => useQuery({ queryKey: keys.contact, queryFn: () => request<Contact>('/me/contact') })

export function useSaveContact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (c: ContactInput) => request<Contact>('/me/contact', { method: 'PUT', body: JSON.stringify(c) }),
    onSuccess: (data) => qc.setQueryData(keys.contact, data),
  })
}
