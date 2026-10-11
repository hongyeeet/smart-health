/**
 * The questions of the chat setup (A4), in the order the backend reads them and the form pages ask them. The ids and field names
 * match CHAT_STEPS in services/api app/services/onboarding.py, and every id is the name the answers store uses, so an answer fills
 * the same form field. Only the wording and the quick replies are here; nothing in this file scores, stages or judges an answer.
 *
 * Medicines are not asked in the chat: the screen points to Scan a label. Sex is male or female only. The emergency contact and the
 * name, birth year and sex are required (they cannot be skipped); the rest can be skipped with "skip" or "I do not know".
 */
import type { Option } from '../parts'
import type { useOptions } from '../options'
import { labelOf } from '../options'
import type { HasDiabetes, OnboardingAnswers } from '../useOnboarding'

export type Options = ReturnType<typeof useOptions>
export type QuestionKind = 'text' | 'free' | 'year' | 'number' | 'scale' | 'email' | 'phone' | 'date' | 'time' | 'days' | 'choice' | 'multi' | 'allergy'

export interface ChatQuestion {
  id: string
  kind: QuestionKind
  /** A required question must be answered before the summary. Optional ones can be skipped. */
  optional: boolean
  /** Asked only when the person works (the work week). Otherwise it is not asked at all. */
  workingOnly?: boolean
  /** The form page that asks the same thing (A3 ?step=n). null means the eligibility screen (A2). */
  formStep: number | null
  ask: string
  placeholder?: string
  inputMode?: 'text' | 'numeric' | 'decimal' | 'tel' | 'email'
}

export const CHAT_QUESTIONS: ChatQuestion[] = [
  /* 1 welcome */
  { id: 'name', kind: 'text', optional: false, formStep: 1, ask: 'What should we call you?', placeholder: 'Your first name is fine' },
  { id: 'reminderEmail', kind: 'email', optional: true, formStep: 1, ask: 'Which email should reminders go to? A Gmail address works. You can leave this one blank.', placeholder: 'name@gmail.com', inputMode: 'email' },
  /* 2 eligibility */
  { id: 'hasDiabetes', kind: 'choice', optional: false, formStep: null, ask: 'Do you have type 2 diabetes? Say yes, or not sure.' },
  /* 3 about you */
  { id: 'birthYear', kind: 'year', optional: false, formStep: 3, ask: 'What year were you born? Four digits, like 1968.', placeholder: '1968', inputMode: 'numeric' },
  { id: 'gender', kind: 'choice', optional: false, formStep: 3, ask: 'Are you male or female?' },
  { id: 'heightCm', kind: 'number', optional: true, formStep: 3, ask: 'What is your height in cm? Say a number, like 168. You can leave this one blank.', placeholder: '168', inputMode: 'decimal' },
  { id: 'weightKg', kind: 'number', optional: true, formStep: 3, ask: 'And your weight in kg? Say a number, like 72. You can leave this one blank.', placeholder: '72', inputMode: 'decimal' },
  { id: 'waistCm', kind: 'number', optional: true, formStep: 3, ask: 'What is your waist in cm? Measure around your middle, level with your belly button. You can leave this one blank.', placeholder: '84', inputMode: 'decimal' },
  /* 4 diabetes history */
  { id: 'diagnosedYear', kind: 'year', optional: true, formStep: 4, ask: 'What year were you told you have type 2 diabetes? Four digits, like 2016. You can leave this one blank.', placeholder: '2016', inputMode: 'numeric' },
  { id: 'careSetting', kind: 'choice', optional: true, formStep: 4, ask: 'Where do you usually go for your diabetes? A polyclinic, a GP or family clinic, a hospital specialist clinic, or no regular doctor. You can leave this one blank.' },
  { id: 'healthierSg', kind: 'choice', optional: true, formStep: 4, ask: 'Are you enrolled in Healthier SG? Say yes, no, or not sure. You can leave this one blank.' },
  /* 6 low glucose */
  { id: 'hypo3m', kind: 'choice', optional: true, formStep: 6, ask: 'How many hypos (low glucose) have you had in the last 3 months? None, 1 or 2 times, 3 times or more, or not sure. You can leave this one blank.' },
  { id: 'severeHypo', kind: 'choice', optional: true, formStep: 6, ask: 'In the last 12 months, did you have a hypo where you needed someone else to help you? Yes or no. You can leave this one blank.' },
  { id: 'gold', kind: 'scale', optional: true, formStep: 6, ask: 'How well do you notice a hypo coming on? Say a number from 1 (always aware) to 7 (never aware). You can leave this one blank.', placeholder: '1 to 7', inputMode: 'numeric' },
  /* 7 other conditions and checks */
  { id: 'conditions', kind: 'multi', optional: true, formStep: 7, ask: 'Has a doctor told you that you have any of these? High blood pressure, high cholesterol, kidney disease, heart disease or a past heart attack, stroke or mini-stroke, heart failure, diabetic eye disease, nerve problems in the feet, a past foot ulcer or amputation, sleep apnoea, fatty liver, or anaemia or thalassaemia. Name them, or say none. You can leave this one blank.', placeholder: 'For example, high blood pressure' },
  { id: 'otherConditions', kind: 'free', optional: true, formStep: 7, ask: 'Any other condition? Type it in, or say none. You can leave this one blank.', placeholder: 'Or say none' },
  { id: 'allergies', kind: 'allergy', optional: true, formStep: 7, ask: 'Are you allergic to any medicine, food or material? Name it, and what happens if you like, such as penicillin (rash). Or say none. You can leave this one blank.', placeholder: 'For example penicillin (rash)' },
  { id: 'eyeCheck', kind: 'choice', optional: true, formStep: 7, ask: 'When did you last have an eye check, the retinal photo? In the last year, more than a year ago, or never or not sure. You can leave this one blank.' },
  { id: 'footCheck', kind: 'choice', optional: true, formStep: 7, ask: 'When did you last have a foot check? In the last year, more than a year ago, or never or not sure. You can leave this one blank.' },
  /* 8 lab results */
  { id: 'labDate', kind: 'date', optional: true, formStep: 8, ask: 'What is the date of your most recent blood test? For example 12 March 2026. You can leave this one blank.', placeholder: '12 March 2026' },
  { id: 'hba1c', kind: 'number', optional: true, formStep: 8, ask: 'What was your HbA1c? Say the number and the unit, like 7.2% or 55 mmol/mol. You can leave this one blank.', placeholder: '7.2%', inputMode: 'decimal' },
  { id: 'fastingGlucose', kind: 'number', optional: true, formStep: 8, ask: 'What was your fasting glucose? Say the number and the unit, like 7.4 mmol/L or 133 mg/dL. You can leave this one blank.', placeholder: '7.4 mmol/L', inputMode: 'decimal' },
  { id: 'fastingInsulin', kind: 'number', optional: true, formStep: 8, ask: 'What was your fasting insulin, in µIU/mL? Say a number, like 11.5. You can leave this one blank.', placeholder: '11.5', inputMode: 'decimal' },
  /* 9 devices */
  { id: 'cgm', kind: 'choice', optional: true, formStep: 9, ask: 'Which glucose sensor do you use? Libre, Dexcom, another sensor, or none. You can leave this one blank.' },
  { id: 'wearable', kind: 'choice', optional: true, formStep: 9, ask: 'Which watch do you wear? Apple, Garmin, Samsung, Fitbit, Xiaomi, another watch, or none. You can leave this one blank.' },
  /* 10 work week */
  { id: 'workType', kind: 'choice', optional: true, formStep: 10, ask: 'What is your work like? Mostly sitting, standing, physical, a mix, shifts, or not working? You can leave this one blank.' },
  { id: 'workDays', kind: 'days', optional: true, workingOnly: true, formStep: 10, ask: 'Which days do you usually work? For example Mon to Fri. You can leave this one blank.', placeholder: 'Mon to Fri' },
  { id: 'workStart', kind: 'time', optional: true, workingOnly: true, formStep: 10, ask: 'What time does work start? For example 7.30am. You can leave this one blank.', placeholder: '7.30am' },
  { id: 'workEnd', kind: 'time', optional: true, workingOnly: true, formStep: 10, ask: 'What time does work end? For example 6pm. You can leave this one blank.', placeholder: '6pm' },
  /* 11 emergency contact: all four needed */
  { id: 'contactName', kind: 'text', optional: false, formStep: 11, ask: 'Who should we contact in an emergency? Their name, please.', placeholder: 'Next of kin or caregiver' },
  { id: 'contactRelation', kind: 'text', optional: false, formStep: 11, ask: 'How are they to you?', placeholder: 'For example, wife, son or friend' },
  { id: 'contactPhone', kind: 'phone', optional: false, formStep: 11, ask: 'What is their mobile number?', placeholder: '+65 9123 4567', inputMode: 'tel' },
  { id: 'contactEmail', kind: 'email', optional: false, formStep: 11, ask: 'What is their email?', placeholder: 'name@gmail.com', inputMode: 'email' },
]

/** Translates a string: (key, English default). Passed in by the screen, so the labels follow the chosen language. */
export type Tr = (key: string, fallback: string) => string

export const diabetesOptions = (tr: Tr): Option<HasDiabetes>[] => [
  { value: 'yes', label: tr('setup.diabetes.yes', 'Yes') },
  { value: 'not_sure', label: tr('setup.diabetes.notSure', 'Not sure') },
]

/** The hypo awareness scale, 1 (always aware) to 7 (never aware). */
const GOLD_SCALE: Option<string>[] = ['1', '2', '3', '4', '5', '6', '7'].map((n) => ({ value: n, label: n }))

/**
 * Whether a question is asked for the answers so far. The work week is asked only when the person works. Mirrors `_asked` in the
 * backend, so the screen and the server never disagree about which question comes next.
 */
export function isAsked(q: ChatQuestion, a: OnboardingAnswers): boolean {
  return !q.workingOnly || (a.workType !== null && a.workType !== 'not_working')
}

/** The quick replies for a choice question. Tapping one sends its words, exactly as if they had been typed. */
export function choicesFor(id: string, o: Options, tr: Tr): Option<string>[] {
  switch (id) {
    case 'gender':
      return o.gender
    case 'hasDiabetes':
      return diabetesOptions(tr)
    case 'careSetting':
      return o.careSetting
    case 'healthierSg':
      return o.healthierSg
    case 'hypo3m':
      return o.hypo3m
    case 'severeHypo':
      return o.yesNo
    case 'gold':
      return GOLD_SCALE
    case 'eyeCheck':
    case 'footCheck':
      return o.lastCheck
    case 'cgm':
      return o.cgm
    case 'wearable':
      return o.wearable
    case 'workType':
      return o.work
    case 'conditions':
      return [{ value: 'none', label: tr('setup.noneOf', 'None of these') }]
    case 'allergies':
      return [{ value: 'none', label: tr('setup.noAllergies', 'No known allergies') }]
    default:
      return []
  }
}

/** The words a quick reply sends: "not_working" is sent as "not working", which the server reads. */
export const replyText = (value: string) => value.replace(/_/g, ' ')

/** What the answer shows as, or '' when the question is still open. */
export function answerLabel(id: string, a: OnboardingAnswers, o: Options, tr: Tr): string {
  const text = (v: string) => v.trim()
  switch (id) {
    case 'name':
      return text(a.name)
    case 'reminderEmail':
      return text(a.reminderEmail)
    case 'hasDiabetes':
      return labelOf(diabetesOptions(tr), a.hasDiabetes)
    case 'birthYear':
      return text(a.birthYear)
    case 'gender':
      return labelOf(o.gender, a.gender)
    case 'heightCm':
      return text(a.heightCm) ? `${text(a.heightCm)} cm` : ''
    case 'weightKg':
      return text(a.weightKg) ? `${text(a.weightKg)} kg` : ''
    case 'waistCm':
      return text(a.waistCm) ? `${text(a.waistCm)} cm` : ''
    case 'diagnosedYear':
      return text(a.diagnosedYear)
    case 'careSetting':
      return labelOf(o.careSetting, a.careSetting)
    case 'healthierSg':
      return labelOf(o.healthierSg, a.healthierSg)
    case 'hypo3m':
      return labelOf(o.hypo3m, a.hypo3m)
    case 'severeHypo':
      return labelOf(o.yesNo, a.severeHypo)
    case 'gold':
      return a.gold ? `${a.gold} of 7` : ''
    case 'conditions':
      if (a.conditions.length === 0) return ''
      if (a.conditions.includes('none')) return tr('setup.noneOf', 'None of these')
      return a.conditions.map((c) => labelOf(o.conditions, c)).join(', ')
    case 'otherConditions':
      return text(a.otherConditions)
    case 'allergies':
      if (a.noAllergies) return tr('setup.noAllergies', 'No known allergies')
      return a.allergies
        .filter((x) => x.substance.trim())
        .map((x) => (x.reaction.trim() ? `${x.substance.trim()} (${x.reaction.trim()})` : x.substance.trim()))
        .join(', ')
    case 'eyeCheck':
      return labelOf(o.lastCheck, a.eyeCheck)
    case 'footCheck':
      return labelOf(o.lastCheck, a.footCheck)
    case 'labDate':
      return text(a.labDate)
    case 'hba1c':
      return text(a.hba1c) ? `${text(a.hba1c)} ${a.hba1cUnit}` : ''
    case 'fastingGlucose':
      return text(a.fastingGlucose) ? `${text(a.fastingGlucose)} ${a.glucoseUnit}` : ''
    case 'fastingInsulin':
      return text(a.fastingInsulin) ? `${text(a.fastingInsulin)} µIU/mL` : ''
    case 'cgm':
      return labelOf(o.cgm, a.cgm)
    case 'wearable':
      return labelOf(o.wearable, a.wearable)
    case 'workType':
      return labelOf(o.work, a.workType)
    case 'workDays':
      return a.workDays.length ? a.workDays.map((d) => labelOf(o.weekdays, String(d))).join(', ') : ''
    case 'workStart':
      return text(a.workStart)
    case 'workEnd':
      return text(a.workEnd)
    case 'contactName':
      return text(a.contactName)
    case 'contactRelation':
      return text(a.contactRelation)
    case 'contactPhone':
      return text(a.contactPhone)
    case 'contactEmail':
      return text(a.contactEmail)
    default:
      return ''
  }
}
