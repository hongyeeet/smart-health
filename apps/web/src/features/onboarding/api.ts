/**
 * Onboarding data and the link to the database:
 *   GET  /onboarding          the saved answers for the person the app acts as (the source of truth)
 *   PUT  /onboarding/profile  one page's answers (only the keys sent are written; null clears a saved answer)
 *   POST /onboarding/complete the data-use consent and the completion event
 *   GET/PUT /notify/email     the reminder email and its on/off switch (shared contract with Me, Data and account)
 *
 * The answers on this device are a fallback only: a field the server has nothing for is taken from the device copy.
 * The demo patient (Mr Tan) is read but never written: the server refuses his writes, and the screens do not send them.
 */
import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { appConfig } from '@/config/app'
import { request } from '@/data/repositories/http'
import { useUi } from '@/state/store'
import { convert, num, useOnboarding, type GlucoseUnit, type Hba1cUnit, type LastCheck, type OnboardingAnswers, type WorkType, type YesNo, type YesNoUnsure } from './useOnboarding'

/** The loaded demo patient. His record is shown but never changed from onboarding. */
export const READ_ONLY_USER = 'mr-tan'

/* ------------------------------------------------------------------ what the server sends back ------------------------------------------------------------------ */
/** Decimals come back as text from the server, so they are read with Number() by the callers. */
export interface SavedProfile {
  displayName: string
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
  updatedAt: string
}

/** The answers that are not profile columns (migration 0032). Empty until the migration is applied. HbA1c is always in %. */
export interface SavedHistory {
  waistCm: string | number | null
  diagnosedYear: number | null
  careSetting: string | null
  healthierSg: string | null
  hypoLast3m: string | null
  hypoAwareness: string | null
  hypoNeededHelp: string | null
  conditions: string[]
  otherCondition: string | null
  allergies: { substance: string; reaction: string | null }[]
  eyeCheck: string | null
  footCheck: string | null
  labDate: string | null
  hba1c: string | number | null
  hba1cUnit: string | null
  fastingGlucose: string | number | null
  glucoseUnit: string | null
  fastingInsulin: string | number | null
}

export interface SavedOnboarding {
  profile: SavedProfile | null
  dataConsent: boolean
  emailColumn: boolean
  historyReady: boolean
  history: SavedHistory
}

export interface SaveResult extends SavedOnboarding {
  /** request fields that were not stored yet (named in camelCase), for example the history before migration 0032 */
  notSaved: string[]
}

export interface CompleteResult {
  consentRecorded: boolean
  completedAt: string
}

export interface NotifyEmail {
  email: string | null
  optIn: boolean
  available?: boolean
}

/** The request body for one page. A key left out (undefined) is not written; null clears the saved answer. */
export interface ProfileBody {
  displayName?: string
  hasDiabetes?: string
  birthYear?: number
  gender?: string | null
  race?: string | null
  heightCm?: number | null
  weightKg?: number | null
  waistCm?: number | null
  diagnosedYear?: number | null
  careSetting?: string | null
  healthierSg?: string | null
  hypoLast3m?: string | null
  hypoAwareness?: string | null
  hypoNeededHelp?: string | null
  conditions?: string[]
  otherCondition?: string | null
  allergies?: { substance: string; reaction: string | null }[]
  eyeCheck?: string | null
  footCheck?: string | null
  labDate?: string | null
  hba1c?: number | null
  hba1cUnit?: string
  fastingGlucose?: number | null
  glucoseUnit?: string
  fastingInsulin?: number | null
  watchModel?: string | null
  cgmModel?: string | null
  workType?: string | null
  workDays?: number[]
  workStart?: string | null
  workEnd?: string | null
  emergencyContactName?: string
  emergencyContactRelation?: string
  emergencyContactPhone?: string
  emergencyContactEmail?: string
}

/* ------------------------------------------------------------------ server to answers ------------------------------------------------------------------ */
const CARE = ['polyclinic', 'gp', 'hospital', 'none'] as const
const HSG = ['yes', 'no', 'unsure'] as const
const HYPO_3M = ['0', '1-2', '3+', 'unsure'] as const
const AWARENESS = ['1', '2', '3', '4', '5', '6', '7'] as const
const YES_NO = ['yes', 'no'] as const
const CHECKS = ['within_year', 'over_year', 'never_unsure'] as const
const WORK = ['desk', 'mixed', 'standing', 'physical', 'shift', 'not_working'] as const
const GLUCOSE_UNITS = ['mmol/L', 'mg/dL'] as const

/** The server's value when it is one of the allowed choices; otherwise the device copy. An old value such as sex "other" falls back. */
function choice<T extends string>(server: unknown, local: T | null, allowed: readonly T[]): T | null {
  return typeof server === 'string' && (allowed as readonly string[]).includes(server) ? (server as T) : local
}
/** The server's text when it has some; otherwise the device copy. */
function text(server: unknown, local: string): string {
  return server === null || server === undefined || server === '' ? local : String(server)
}
/** A number as the form shows it (a decimal from the server, without trailing zeros), or null when the server has none. */
function shown(server: unknown): string | null {
  return server === null || server === undefined || server === '' ? null : String(Number(server))
}

/**
 * The answers as the server has them, merged into the device copy. The server wins for every field it has a value for; the
 * device copy fills the rest. HbA1c is shown in the unit the person chose on this device.
 */
export function fromSaved(saved: SavedOnboarding, a: OnboardingAnswers, email?: NotifyEmail): OnboardingAnswers {
  const p = saved.profile
  const h = saved.history
  const hba1c = shown(h.hba1c)
  const hba1cUnit: Hba1cUnit = a.hba1cUnit
  const hba1cValue =
    hba1c === null ? a.hba1c : hba1cUnit === 'mmol/mol' ? String(Math.round(convert.hba1cToMmolMol(Number(hba1c)))) : hba1c
  return {
    ...a,
    name: text(p?.displayName, a.name),
    reminderEmail: email?.email ?? a.reminderEmail,
    reminderOn: email ? email.optIn : a.reminderOn,
    consentData: saved.dataConsent || a.consentData,
    hasDiabetes: choice(p?.hasDiabetes, a.hasDiabetes, ['yes', 'not_sure'] as const),
    birthYear: p ? String(p.birthYear) : a.birthYear,
    gender: choice(p?.gender, a.gender, ['female', 'male'] as const),
    race: text(p?.race, a.race),
    heightCm: shown(p?.heightCm) ?? a.heightCm,
    weightKg: shown(p?.weightKg) ?? a.weightKg,
    waistCm: shown(h.waistCm) ?? a.waistCm,
    diagnosedYear: h.diagnosedYear !== null ? String(h.diagnosedYear) : a.diagnosedYear,
    careSetting: choice<string>(h.careSetting, a.careSetting, CARE),
    healthierSg: choice<YesNoUnsure>(h.healthierSg, a.healthierSg, HSG),
    hypo3m: choice<string>(h.hypoLast3m, a.hypo3m, HYPO_3M),
    severeHypo: choice<YesNo>(h.hypoNeededHelp, a.severeHypo, YES_NO),
    gold: choice<string>(h.hypoAwareness, a.gold, AWARENESS),
    conditions: h.conditions.length ? h.conditions : a.conditions,
    otherConditions: text(h.otherCondition, a.otherConditions),
    noAllergies: h.allergies.length ? false : a.noAllergies,
    allergies: h.allergies.length ? h.allergies.map((x) => ({ substance: x.substance, reaction: x.reaction ?? '' })) : a.allergies,
    eyeCheck: choice<LastCheck>(h.eyeCheck, a.eyeCheck, CHECKS),
    footCheck: choice<LastCheck>(h.footCheck, a.footCheck, CHECKS),
    labDate: text(h.labDate, a.labDate),
    hba1c: hba1cValue,
    fastingGlucose: shown(h.fastingGlucose) ?? a.fastingGlucose,
    glucoseUnit: choice<GlucoseUnit>(h.glucoseUnit, a.glucoseUnit, GLUCOSE_UNITS) ?? a.glucoseUnit,
    fastingInsulin: shown(h.fastingInsulin) ?? a.fastingInsulin,
    wearable: p?.watchModel ?? a.wearable,
    cgm: p?.cgmModel ?? a.cgm,
    workType: choice<WorkType>(p?.workType, a.workType, WORK),
    workDays: p && p.workDays.length ? p.workDays : a.workDays,
    workStart: text(p?.workStart, a.workStart),
    workEnd: text(p?.workEnd, a.workEnd),
    contactName: text(p?.emergencyContactName, a.contactName),
    contactRelation: text(p?.emergencyContactRelation, a.contactRelation),
    contactPhone: text(p?.emergencyContactPhone, a.contactPhone),
    contactEmail: text(p?.emergencyContactEmail, a.contactEmail),
  }
}

/* ------------------------------------------------------------------ answers to what each page saves ------------------------------------------------------------------ */
const trimmed = (v: string) => v.trim() || null
const whole = (v: string) => {
  const n = num(v)
  return n === null ? null : Math.trunc(n)
}
const decimal = (v: string) => num(v)

/**
 * What one page saves, from the answers. Page 2 saves nothing (eligibility is not stored); medicines are not part of set-up. `firstSave` adds the fields the server needs before it can create the profile (birth year and the diabetes
 * answer), so the first save never fails for a missing one.
 */
export function pageBody(page: number, a: OnboardingAnswers, firstSave: boolean): ProfileBody | null {
  switch (page) {
    case 1: {
      const name = trimmed(a.name)
      return name ? { displayName: name } : null
    }
    case 3:
      return {
        /* the diabetes answer from eligibility (page 2) is saved with page 3; the name waits here until the profile exists */
        hasDiabetes: a.hasDiabetes ?? undefined,
        ...(firstSave && trimmed(a.name) ? { displayName: a.name.trim() } : {}),
        birthYear: whole(a.birthYear) ?? undefined,
        gender: a.gender,
        race: trimmed(a.race),
        heightCm: decimal(a.heightCm),
        weightKg: decimal(a.weightKg),
        waistCm: decimal(a.waistCm),
      }
    case 4:
      return { diagnosedYear: whole(a.diagnosedYear), careSetting: a.careSetting, healthierSg: a.healthierSg }
    case 5:
      return { hypoLast3m: a.hypo3m, hypoAwareness: a.gold, hypoNeededHelp: a.severeHypo }
    case 6:
      return {
        conditions: a.conditions.filter((c) => c !== 'none'),
        otherCondition: trimmed(a.otherConditions),
        allergies: a.noAllergies ? [] : a.allergies.filter((x) => x.substance.trim()).map((x) => ({ substance: x.substance.trim(), reaction: trimmed(x.reaction) })),
        eyeCheck: a.eyeCheck,
        footCheck: a.footCheck,
      }
    case 7: {
      const body: ProfileBody = { labDate: a.labDate || null, hba1c: decimal(a.hba1c), fastingGlucose: decimal(a.fastingGlucose), fastingInsulin: decimal(a.fastingInsulin) }
      if (body.hba1c !== null) body.hba1cUnit = a.hba1cUnit
      if (body.fastingGlucose !== null) body.glucoseUnit = a.glucoseUnit
      return body
    }
    case 8:
      return { watchModel: a.wearable, cgmModel: a.cgm }
    case 9: {
      const working = a.workType !== null && a.workType !== 'not_working'
      return { workType: a.workType, workDays: working ? [...a.workDays] : [], workStart: working ? trimmed(a.workStart) : null, workEnd: working ? trimmed(a.workEnd) : null }
    }
    case 10:
      return {
        emergencyContactName: a.contactName.trim(),
        emergencyContactRelation: a.contactRelation.trim(),
        emergencyContactPhone: a.contactPhone.trim(),
        emergencyContactEmail: a.contactEmail.trim(),
      }
    default:
      return null
  }
}

/** Every page's answers in one request, for Finish on the summary. Pages the person never opened are saved too. */
export function allPagesBody(a: OnboardingAnswers, firstSave: boolean): ProfileBody {
  const body: ProfileBody = {}
  const name = a.name.trim()
  if (name) body.displayName = name
  for (const page of [3, 4, 5, 6, 7, 8, 9, 10]) Object.assign(body, pageBody(page, a, firstSave))
  return body
}

/** The reminder email as the server takes it: a blank box clears the address. */
export function emailBody(a: OnboardingAnswers): { email: string | null; optIn: boolean } {
  return { email: trimmed(a.reminderEmail), optIn: a.reminderOn }
}

/* ------------------------------------------------------------------ hooks ------------------------------------------------------------------ */
export const savedKey = (user: string) => ['onboarding', user, 'saved'] as const
const notifyKey = (user: string) => ['notify', user, 'email'] as const

export function useSavedOnboarding() {
  const user = useUi((s) => s.userKey)
  return useQuery({ queryKey: savedKey(user), queryFn: () => request<SavedOnboarding>('/onboarding') })
}

export function useNotifyEmail() {
  const user = useUi((s) => s.userKey)
  return useQuery({ queryKey: notifyKey(user), queryFn: () => request<NotifyEmail>('/notify/email'), retry: false })
}

/**
 * Loads the person's answers for the screens: the server first, the device copy only for what the server does not have.
 * `ready` is true once the answers for this person are in the form; until then the screen shows a loading state.
 */
export function useOnboardingSource() {
  const user = useUi((s) => s.userKey)
  const saved = useSavedOnboarding()
  const email = useNotifyEmail()
  const loadedFor = useOnboarding((s) => s.loadedFor)
  const serverDone = saved.isSuccess || saved.isError
  const emailDone = email.isSuccess || email.isError
  useEffect(() => {
    if (loadedFor === user || !serverDone || !emailDone) return
    const store = useOnboarding.getState()
    const answers = saved.data ? fromSaved(saved.data, store.answers, email.data) : store.answers
    store.setLoaded(answers, user)
  }, [loadedFor, user, serverDone, emailDone, saved.data, email.data])
  return { ready: loadedFor === user, saved, email, readOnly: user === READ_ONLY_USER, loadFailed: saved.isError }
}

/**
 * What happened to the reminder email on a save. 'waiting': the profile does not exist yet (the server refuses the email with 409),
 * so the email stays in the answers and is saved once the profile exists. 'failed': the server refused or could not be reached.
 */
export type EmailState = 'none' | 'stored' | 'waiting' | 'failed'

/**
 * PUT /notify/email. A 409 means "no profile yet" and is returned as waiting; any other refusal or a network error throws, so it is
 * not mistaken for a saved email. request() cannot tell the status apart, so this one call reads the status itself.
 */
async function putReminderEmail(body: { email: string | null; optIn: boolean }): Promise<{ waiting: true } | { waiting: false; data: NotifyEmail }> {
  const res = await fetch(`${appConfig.apiBaseUrl}/notify/email`, {
    method: 'PUT',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', 'X-User': useUi.getState().userKey, 'X-Lang': useUi.getState().locale },
    body: JSON.stringify(body),
  })
  if (res.status === 409) return { waiting: true }
  if (!res.ok) {
    const detail = ((await res.json().catch(() => null)) as { detail?: unknown } | null)?.detail
    throw new Error(typeof detail === 'string' ? detail : `${res.status} ${res.statusText}`)
  }
  return { waiting: false, data: (await res.json()) as NotifyEmail }
}

/**
 * Saves one page. The profile goes first, then the reminder email (the email store needs the profile row). A failed email does
 * not undo the profile; it is reported so the screen can say so. A waiting email is not an error: it is kept and saved later.
 * The saved answers are only put in the cache when the server accepted them, so nothing is shown as saved that was not.
 */
export function useSaveStep() {
  const qc = useQueryClient()
  const user = useUi((s) => s.userKey)
  return useMutation({
    mutationFn: async (input: { profile: ProfileBody | null; email: { email: string | null; optIn: boolean } | null }) => {
      const saved = input.profile ? await request<SaveResult>('/onboarding/profile', { method: 'PUT', body: JSON.stringify(input.profile) }) : null
      let email: EmailState = 'none'
      let emailError: string | null = null
      if (input.email) {
        try {
          const res = await putReminderEmail(input.email)
          if (res.waiting) email = 'waiting'
          else if ((res.data.email ?? null) === input.email.email) email = 'stored'
          else {
            email = 'failed'
            emailError = ''
          }
        } catch (e) {
          email = 'failed'
          emailError = e instanceof Error ? e.message : ''
        }
      }
      return { saved, email, emailError }
    },
    onSuccess: ({ saved }) => {
      if (saved) qc.setQueryData(savedKey(user), saved)
      void qc.invalidateQueries({ queryKey: ['notify', user] })
    },
  })
}

export function useCompleteOnboarding() {
  const qc = useQueryClient()
  const user = useUi((s) => s.userKey)
  return useMutation({
    mutationFn: () => request<CompleteResult>('/onboarding/complete', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['onboarding', user] }),
  })
}
