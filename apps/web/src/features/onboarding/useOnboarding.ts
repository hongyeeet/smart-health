import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * Onboarding answers (A1 to A6), exactly as the person gave them. The question set follows Damien's clinical onboarding
 * design (Stitch export, 2026-10-09). This store only records answers: nothing here is scored, staged or turned into a target.
 *
 * The answers are kept on this device so that leaving and coming back resumes where the person stopped. They are only
 * written to the device once the data-use consent is on (prd F1: consent before any data is stored); switching it off
 * removes them again. The answers that have a `user_profile` column are also saved to the record (api.ts); the rest stay
 * on this device for now. Where `user_profile` in docs/specs/data-model-v2.md has a column, the values match it.
 */
export type Gender = 'female' | 'male' | 'other' | 'prefer_not_to_say'
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
  consentData: boolean
  consentShare: boolean
  consentResearch: boolean
  /* 2 eligibility */
  hasDiabetes: HasDiabetes | null
  /* 3 body measurements */
  birthYear: string
  gender: Gender | null
  race: string
  heightCm: string
  weightKg: string
  waistCm: string
  /* 4 diabetes history */
  diagnosedYear: string
  familyHistory: YesNoUnsure | null
  careSetting: string | null
  healthierSg: string | null
  /* 5 medicines (kinds only; the medicines themselves come from the scan and add-by-hand screens) */
  diabetesMeds: string[]
  otherMeds: string[]
  /* 6 lows */
  hypo3m: string | null
  severeHypo: YesNo | null
  /** Gold score, '1' to '7' */
  gold: string | null
  /* 7 conditions, allergies, check-ups */
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
  egfr: string
  systolic: string
  diastolic: string
  /* 9 devices and routine */
  cgm: string | null
  wearable: string | null
  wakeTime: string
  sleepTime: string
  workType: WorkType | null
  /** 1 = Monday ... 7 = Sunday */
  workDays: number[]
  workStart: string
  workEnd: string
  fasting: string[]
  reminderTimes: string[]
  /* 10 lifestyle */
  eatOut: string | null
  sweetDrinks: string | null
  activeDays: string | null
  smoking: string | null
  alcohol: string | null
  /* 11 safety */
  redFlags: string[]
  contactName: string
  contactPhone: string
  contactRelation: string
  contactEmail: string
  /* 10 reminders */
  reminderEmail: string

  completedAt: string | null
}

export const emptyAnswers: OnboardingAnswers = {
  name: '',
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
  familyHistory: null,
  careSetting: null,
  healthierSg: null,
  diabetesMeds: [],
  otherMeds: [],
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
  egfr: '',
  systolic: '',
  diastolic: '',
  cgm: null,
  wearable: null,
  wakeTime: '',
  sleepTime: '',
  workType: null,
  workDays: [],
  workStart: '',
  workEnd: '',
  fasting: [],
  reminderTimes: [],
  eatOut: null,
  sweetDrinks: null,
  activeDays: null,
  smoking: null,
  alcohol: null,
  redFlags: [],
  contactName: '',
  contactPhone: '',
  contactRelation: '',
  contactEmail: '',
  reminderEmail: '',
  completedAt: null,
}

interface OnboardingState {
  answers: OnboardingAnswers
  set: (patch: Partial<OnboardingAnswers>) => void
  reset: () => void
}

export const useOnboarding = create<OnboardingState>()(
  persist(
    (set) => ({
      answers: emptyAnswers,
      set: (patch) => set((s) => ({ answers: { ...s.answers, ...patch } })),
      reset: () => set({ answers: emptyAnswers }),
    }),
    {
      name: 'smart-health-onboarding',
      version: 2,
      /** An older shape is dropped, not converted: nothing was ever saved from it. */
      migrate: () => ({ answers: emptyAnswers }),
      /* answers stored before a new field existed get the empty value for it */
      merge: (persisted, current) => ({ ...current, answers: { ...emptyAnswers, ...(persisted as { answers?: Partial<OnboardingAnswers> } | undefined)?.answers } }),
      partialize: (s) => ({ answers: s.answers.consentData ? s.answers : emptyAnswers }),
    },
  ),
)

/* ------------------------------- checks on what was typed ------------------------------- */
/**
 * Plausible ranges for each number field. They only catch typing slips (a height of 900); they are not clinical limits and
 * nothing is said about a value that is inside them. Height, weight, HbA1c in % and blood pressure follow the column limits
 * in docs/specs/schema.md.
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
  egfr: [1, 200],
  systolic: [60, 260],
  diastolic: [30, 160],
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
