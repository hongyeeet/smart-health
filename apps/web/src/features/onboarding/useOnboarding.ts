import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import { useUi } from '@/state/store'

/**
 * Onboarding answers (A1 to A6), exactly as the person gave them. This store only records answers: nothing here is scored,
 * staged or turned into a target.
 *
 * The database is the source of truth (api.ts reads GET /onboarding and fills these answers from it). The copy kept on this
 * device is a fallback: it is only used for a field the server has nothing for, and each person has their own copy
 * (`smart-health-onboarding:<user>`), so one person's answers never show for another. Nothing is kept on the device until the
 * data-use consent is on; switching it off removes the copy again.
 */
export type Gender = 'female' | 'male'
export type HasDiabetes = 'yes' | 'not_sure'
export type YesNo = 'yes' | 'no'
export type YesNoUnsure = 'yes' | 'no' | 'unsure'
export type LastCheck = 'within_year' | 'over_year' | 'never_unsure'
export type WorkType = 'desk' | 'mixed' | 'standing' | 'physical' | 'shift' | 'not_working'
export type Hba1cUnit = '%' | 'mmol/mol'
export type GlucoseUnit = 'mmol/L' | 'mg/dL'

export interface Allergy {
  substance: string
  reaction: string
}

export interface OnboardingAnswers {
  /* 1 welcome */
  name: string
  reminderEmail: string
  reminderOn: boolean
  consentData: boolean
  consentShare: boolean
  consentResearch: boolean
  /* 2 eligibility */
  hasDiabetes: HasDiabetes | null
  /* 3 about you */
  birthYear: string
  gender: Gender | null
  race: string
  heightCm: string
  weightKg: string
  waistCm: string
  /* 4 diabetes history */
  diagnosedYear: string
  careSetting: string | null
  healthierSg: YesNoUnsure | null
  /* 5 medicines: the medicines come from GET /medications, not from this store */
  /* 6 low glucose */
  hypo3m: string | null
  severeHypo: YesNo | null
  /** how well the person notices a hypo coming, '1' (always) to '7' (never) */
  gold: string | null
  /* 7 other conditions and checks */
  conditions: string[]
  otherConditions: string
  noAllergies: boolean
  allergies: Allergy[]
  eyeCheck: LastCheck | null
  footCheck: LastCheck | null
  /* 8 lab results */
  labDate: string
  hba1c: string
  hba1cUnit: Hba1cUnit
  fastingGlucose: string
  glucoseUnit: GlucoseUnit
  fastingInsulin: string
  /* 9 devices: the choice only, nothing is paired here */
  wearable: string | null
  cgm: string | null
  /* 10 work week; 1 = Monday ... 7 = Sunday */
  workType: WorkType | null
  workDays: number[]
  workStart: string
  workEnd: string
  /* 11 emergency contact */
  contactName: string
  contactRelation: string
  contactPhone: string
  contactEmail: string

  completedAt: string | null
}

export const emptyAnswers: OnboardingAnswers = {
  name: '',
  reminderEmail: '',
  reminderOn: true,
  consentData: false,
  consentShare: false,
  consentResearch: false,
  hasDiabetes: null,
  birthYear: '',
  gender: null,
  race: '',
  heightCm: '',
  weightKg: '',
  waistCm: '',
  diagnosedYear: '',
  careSetting: null,
  healthierSg: null,
  hypo3m: null,
  severeHypo: null,
  gold: null,
  conditions: [],
  otherConditions: '',
  noAllergies: false,
  allergies: [],
  eyeCheck: null,
  footCheck: null,
  labDate: '',
  hba1c: '',
  hba1cUnit: '%',
  fastingGlucose: '',
  glucoseUnit: 'mmol/L',
  fastingInsulin: '',
  wearable: null,
  cgm: null,
  workType: null,
  workDays: [],
  workStart: '',
  workEnd: '',
  contactName: '',
  contactRelation: '',
  contactPhone: '',
  contactEmail: '',
  completedAt: null,
}

/** The per-person device copy. `user` is the key the app acts as (X-User). */
export const deviceKey = (user: string) => `smart-health-onboarding:${user}`
const OLD_UNKEYED_KEY = 'smart-health-onboarding'

/** Removes one person's device copy (used by "Start as new person"). A blocked storage is not an error: nothing is kept then. */
export function clearDeviceCopy(user: string) {
  try {
    localStorage.removeItem(deviceKey(user))
  } catch {
    /* storage not available */
  }
}

/* The old copy had no owner, so it could belong to anyone who used this device. It is removed rather than moved to a person. */
try {
  localStorage.removeItem(OLD_UNKEYED_KEY)
} catch {
  /* storage not available */
}

/** Answers from an older copy that are no longer choices (for example sex "other") are treated as not answered. */
function sanitize(a: Partial<OnboardingAnswers>): OnboardingAnswers {
  const merged = { ...emptyAnswers, ...a }
  const gender = merged.gender === 'female' || merged.gender === 'male' ? merged.gender : null
  return { ...merged, gender }
}

/** The device copy follows the person: it is read and written under the key of whoever is acting. */
const deviceStorage = createJSONStorage(() => ({
  getItem: () => {
    try {
      return localStorage.getItem(deviceKey(useUi.getState().userKey))
    } catch {
      return null
    }
  },
  setItem: (_name: string, value: string) => {
    try {
      localStorage.setItem(deviceKey(useUi.getState().userKey), value)
    } catch {
      /* storage not available: the answers stay in memory for this visit */
    }
  },
  removeItem: () => clearDeviceCopy(useUi.getState().userKey),
}))

interface OnboardingState {
  answers: OnboardingAnswers
  /** the person whose answers are loaded (from the server, or the device copy when the server is unavailable) */
  loadedFor: string | null
  set: (patch: Partial<OnboardingAnswers>) => void
  setLoaded: (patch: Partial<OnboardingAnswers>, user: string) => void
}

export const useOnboarding = create<OnboardingState>()(
  persist(
    (set) => ({
      answers: emptyAnswers,
      loadedFor: null,
      set: (patch) => set((s) => ({ answers: { ...s.answers, ...patch } })),
      setLoaded: (patch, user) => set((s) => ({ answers: { ...s.answers, ...patch }, loadedFor: user })),
    }),
    {
      name: 'smart-health-onboarding',
      storage: deviceStorage,
      partialize: (s) => ({ answers: s.answers.consentData ? s.answers : emptyAnswers }),
      merge: (persisted, current) => ({
        ...current,
        answers: sanitize((persisted as { answers?: Partial<OnboardingAnswers> } | undefined)?.answers ?? {}),
      }),
    },
  ),
)

/* A different person: their copy is loaded in place of the last one. The answers are cleared first so nothing is shown for a moment. */
useUi.subscribe((s, prev) => {
  if (s.userKey === prev.userKey) return
  useOnboarding.setState({ answers: emptyAnswers, loadedFor: null })
  void useOnboarding.persist.rehydrate()
})

/* ------------------------------- checks on what was typed ------------------------------- */
/**
 * Plausible ranges for each number field. They only catch typing slips (a height of 900); they are not clinical limits and
 * nothing is said about a value that is inside them. Height, weight, waist and HbA1c follow the column limits in the database.
 */
export const LIMITS = {
  heightCm: [100, 250],
  weightKg: [25, 300],
  waistCm: [40, 200],
  hba1cPct: [4, 20],
  hba1cMmolMol: [20, 195],
  glucoseMmol: [1, 35],
  glucoseMgDl: [18, 630],
  fastingInsulin: [0.1, 1000],
} as const

const NUMBER = /^\d+(\.\d+)?$/

/** A typed number, or null when the field is empty or not a number. */
export function num(v: string): number | null {
  const s = v.trim()
  return NUMBER.test(s) ? Number(s) : null
}

/** True when an optional number field is empty or inside its range. */
export function inRange(v: string, [lo, hi]: readonly [number, number]): boolean {
  if (!v.trim()) return true
  const n = num(v)
  return n !== null && n >= lo && n <= hi
}

export function yearOk(v: string, { required = false, notBefore = 1900 }: { required?: boolean; notBefore?: number } = {}): boolean {
  if (!v.trim()) return !required
  if (!/^\d{4}$/.test(v.trim())) return false
  const n = Number(v)
  return n >= notBefore && n <= new Date().getFullYear()
}

/** A date field (YYYY-MM-DD) that is empty or not in the future. */
export function pastDateOk(v: string): boolean {
  return !v || v <= new Date().toLocaleDateString('sv-SE')
}

/** A plain check that an address has the shape name@domain.tld. Providers are not checked. */
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
export const emailOk = (v: string) => EMAIL.test(v.trim())

/** A mobile number: digits with an optional leading +, spaces and dashes allowed, 7 to 15 digits. */
export function phoneOk(v: string): boolean {
  const s = v.trim()
  if (!/^\+?[\d\s-]+$/.test(s)) return false
  const digits = s.replace(/\D/g, '').length
  return digits >= 7 && digits <= 15
}

/* ------------------------------- arithmetic shown on the summary ------------------------------- */
/** Unit conversions and plain arithmetic only. No category, stage or target is ever derived from these. */
export const convert = {
  /** IFCC (mmol/mol) from NGSP (%), the standard master equation */
  hba1cToMmolMol: (pct: number) => (pct - 2.15) * 10.929,
  hba1cToPct: (mmolMol: number) => mmolMol / 10.929 + 2.15,
  glucoseToMgDl: (mmol: number) => mmol * 18,
  glucoseToMmol: (mgDl: number) => mgDl / 18,
  bmi: (weightKg: number, heightCm: number) => weightKg / (heightCm / 100) ** 2,
}
