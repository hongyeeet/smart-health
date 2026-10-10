/**
 * Onboarding data: what is saved for the person (GET /onboarding), the profile save (PUT /onboarding/profile), the completion
 * (POST /onboarding/complete) and the reminder email, which is the shared contract GET/PUT /notify/email.
 *
 * Only the answers that have a `user_profile` column are sent. A field the person has not answered is left out of the
 * request, so it is never blanked on the server; a choice of "none" is sent as null on purpose.
 */
import { useEffect, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { request } from '@/data/repositories/http'
import { num, useOnboarding, type OnboardingAnswers } from './useOnboarding'

/** Decimals come back as text from the server, so numbers are read with Number() by the callers. */
export interface SavedProfile {
  displayName: string
  language: string
  hasDiabetes: string
  birthYear: number
  gender: string | null
  race: string | null
  heightCm: string | number | null
  weightKg: string | number | null
  workType: string | null
  workDays: number[]
  workStart: string | null
  workEnd: string | null
  emergencyContactName: string | null
  emergencyContactPhone: string | null
  emergencyContactRelation: string | null
  emergencyContactEmail: string | null
  watchModel: string | null
  cgmModel: string | null
  allergiesNote: string | null
  conditionsNote: string | null
  updatedAt: string
}

export interface SavedOnboarding {
  profile: SavedProfile | null
  dataConsent: boolean
  emailColumn: boolean
}

export interface SaveResult extends SavedOnboarding {
  /** request fields that were not stored, for example emergencyContactEmail before migration 0031 */
  notSaved: string[]
}

export interface CompleteResult {
  consentRecorded: boolean
  completedAt: string
}

export interface NotifyEmail {
  email: string | null
  optIn: boolean
}

/** The request body. A key that is left out (undefined) is not written. */
export interface ProfileBody {
  displayName?: string
  language?: string
  hasDiabetes?: string
  birthYear?: number
  gender?: string | null
  race?: string
  heightCm?: number
  weightKg?: number
  workType?: string | null
  workDays?: number[] | null
  workStart?: string | null
  workEnd?: string | null
  emergencyContactName?: string
  emergencyContactPhone?: string
  emergencyContactRelation?: string
  emergencyContactEmail?: string
  watchModel?: string | null
  cgmModel?: string | null
  allergiesNote?: string | null
  conditionsNote?: string | null
}

const WORKING = (t: string | null) => t !== null && t !== 'not_working'

/**
 * The answers as the profile request sends them. `conditionLabel` turns a condition code into the words the doctor reads.
 * Blank text is left out, so an empty box never blanks a saved value.
 */
export function toProfileBody(a: OnboardingAnswers, locale: string, conditionLabel: (code: string) => string): ProfileBody {
  const text = (v: string) => v.trim() || undefined
  const body: ProfileBody = {
    displayName: text(a.name),
    language: locale,
    hasDiabetes: a.hasDiabetes ?? undefined,
    birthYear: num(a.birthYear) ?? undefined,
    gender: a.gender ?? undefined,
    race: text(a.race),
    heightCm: num(a.heightCm) ?? undefined,
    weightKg: num(a.weightKg) ?? undefined,
    workType: a.workType ?? undefined,
    emergencyContactName: text(a.contactName),
    emergencyContactPhone: text(a.contactPhone),
    emergencyContactRelation: text(a.contactRelation),
    emergencyContactEmail: text(a.contactEmail),
    watchModel: a.wearable === null ? undefined : a.wearable === 'none' ? null : a.wearable,
    cgmModel: a.cgm === null ? undefined : a.cgm === 'none' ? null : a.cgm,
  }
  if (a.workType === 'not_working') {
    body.workDays = []
    body.workStart = null
    body.workEnd = null
  } else if (WORKING(a.workType)) {
    if (a.workDays.length) body.workDays = a.workDays
    if (a.workStart) body.workStart = a.workStart
    if (a.workEnd) body.workEnd = a.workEnd
  }
  if (a.noAllergies) body.allergiesNote = null
  else if (a.allergies.some((x) => x.substance.trim())) {
    body.allergiesNote = a.allergies
      .filter((x) => x.substance.trim())
      .map((x) => (x.reaction.trim() ? `${x.substance.trim()} (${x.reaction.trim()})` : x.substance.trim()))
      .join('; ')
  }
  if (a.conditions.length || a.otherConditions.trim()) {
    const parts = [...a.conditions.filter((c) => c !== 'none').map(conditionLabel), a.otherConditions.trim()].filter(Boolean)
    body.conditionsNote = parts.length ? parts.join(', ') : null
  }
  return body
}

/**
 * What a saved profile adds to the answers on this device. Only blank answers are filled, so nothing the person has typed
 * here is overwritten. Free-text notes come back as one line, so they go into the matching free-text box.
 */
export function prefillPatch(saved: SavedOnboarding, a: OnboardingAnswers): Partial<OnboardingAnswers> {
  const p = saved.profile
  const patch: Record<string, unknown> = {}
  if (!p) return {}
  const fill = (k: keyof OnboardingAnswers, v: unknown) => {
    const cur = a[k]
    const empty = cur === null || cur === undefined || cur === ''
    if (empty && v !== null && v !== undefined && v !== '') patch[k] = v
  }
  fill('name', p.displayName)
  if (p.hasDiabetes === 'yes' || p.hasDiabetes === 'not_sure') fill('hasDiabetes', p.hasDiabetes)
  fill('birthYear', p.birthYear ? String(p.birthYear) : '')
  fill('gender', p.gender)
  fill('race', p.race)
  fill('heightCm', p.heightCm === null ? '' : String(p.heightCm))
  fill('weightKg', p.weightKg === null ? '' : String(p.weightKg))
  fill('workType', p.workType)
  if (a.workDays.length === 0 && p.workDays.length) patch.workDays = p.workDays
  fill('workStart', p.workStart)
  fill('workEnd', p.workEnd)
  fill('contactName', p.emergencyContactName)
  fill('contactPhone', p.emergencyContactPhone)
  fill('contactRelation', p.emergencyContactRelation)
  fill('contactEmail', p.emergencyContactEmail)
  fill('cgm', p.cgmModel)
  fill('wearable', p.watchModel)
  if (!a.noAllergies && a.allergies.length === 0 && p.allergiesNote) patch.allergies = [{ substance: p.allergiesNote, reaction: '' }]
  if (a.conditions.length === 0 && !a.otherConditions.trim() && p.conditionsNote) patch.otherConditions = p.conditionsNote
  if (saved.dataConsent && !a.consentData) patch.consentData = true
  return patch as Partial<OnboardingAnswers>
}

/** Fills the blank answers from the saved profile once per screen visit. Safe to call on several screens. */
export function usePrefillOnboarding(saved: SavedOnboarding | undefined) {
  const done = useRef(false)
  useEffect(() => {
    if (!saved || done.current) return
    done.current = true
    const store = useOnboarding.getState()
    const patch = prefillPatch(saved, store.answers)
    if (Object.keys(patch).length) store.set(patch)
  }, [saved])
}

/* ------------------------------------------------------------------ hooks ------------------------------------------------------------------ */
export function useSavedOnboarding() {
  return useQuery({ queryKey: ['onboarding', 'saved'], queryFn: () => request<SavedOnboarding>('/onboarding') })
}

export function useSaveProfile() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ProfileBody) => request<SaveResult>('/onboarding/profile', { method: 'PUT', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['onboarding'] }),
  })
}

export function useCompleteOnboarding() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => request<CompleteResult>('/onboarding/complete', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['onboarding'] }),
  })
}

/** Reminder email. Its own endpoint (the shared contract); a failure here must never block onboarding, so no retries. */
export function useNotifyEmail() {
  return useQuery({ queryKey: ['notify', 'email'], queryFn: () => request<NotifyEmail>('/notify/email'), retry: false })
}

export function useSaveNotifyEmail() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (email: string) => request<NotifyEmail>('/notify/email', { method: 'PUT', body: JSON.stringify({ email, optIn: true }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notify'] }),
  })
}
