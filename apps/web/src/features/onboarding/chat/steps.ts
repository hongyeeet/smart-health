/**
 * The questions of the chat setup (A4), in the order the form asks them. The ids and field names match CHAT_STEPS in
 * services/api app/services/onboarding.py, which reads what the person types. Answers land in the same store as the form,
 * so a person can move between the two without losing anything.
 *
 * Only the question wording is here. Nothing in this file scores, stages or judges an answer.
 */
import type { Option } from '../parts'
import type { useOptions } from '../options'
import { labelOf } from '../options'
import type { HasDiabetes, OnboardingAnswers } from '../useOnboarding'

export type Options = ReturnType<typeof useOptions>
export type QuestionKind = 'text' | 'number' | 'phone' | 'email' | 'choice' | 'flags'

export interface ChatQuestion {
  id: string
  kind: QuestionKind
  /** A required question must be answered before the summary. Optional ones can be skipped. */
  optional: boolean
  /** The form step that asks the same thing (A3 ?step=n). null means the eligibility screen (A2). */
  formStep: number | null
  ask: string
  placeholder?: string
  inputMode?: 'text' | 'numeric' | 'decimal' | 'tel' | 'email'
}

export const CHAT_QUESTIONS: ChatQuestion[] = [
  { id: 'name', kind: 'text', optional: false, formStep: 1, ask: 'What should we call you?', placeholder: 'Your first name is fine' },
  { id: 'birthYear', kind: 'number', optional: false, formStep: 1, ask: 'What year were you born? Four digits, like 1968.', placeholder: '1968', inputMode: 'numeric' },
  { id: 'gender', kind: 'choice', optional: true, formStep: 1, ask: 'How do you describe your gender? You can skip this.' },
  { id: 'hasDiabetes', kind: 'choice', optional: false, formStep: null, ask: 'Do you have type 2 diabetes? Say yes, or not sure.' },
  { id: 'heightCm', kind: 'number', optional: true, formStep: 1, ask: 'How tall are you, in cm? Say a number, like 168.', placeholder: '168', inputMode: 'decimal' },
  { id: 'weightKg', kind: 'number', optional: true, formStep: 1, ask: 'And your weight, in kg? Say a number, like 72.', placeholder: '72', inputMode: 'decimal' },
  { id: 'workType', kind: 'choice', optional: true, formStep: 7, ask: 'What is your work like? Mostly sitting, standing, physical, a mix, shifts, or not working?' },
  { id: 'redFlags', kind: 'flags', optional: false, formStep: 9, ask: 'Is any of this happening right now? Tick every one that applies, or tick none.' },
  { id: 'contactName', kind: 'text', optional: false, formStep: 9, ask: 'Who should we contact in an emergency? Their name, please.', placeholder: 'Next of kin or caregiver' },
  { id: 'contactRelation', kind: 'text', optional: false, formStep: 9, ask: 'How are they to you?', placeholder: 'For example, wife, son or friend' },
  { id: 'contactPhone', kind: 'phone', optional: false, formStep: 9, ask: 'What is their mobile number?', placeholder: '+65 9123 4567', inputMode: 'tel' },
  { id: 'contactEmail', kind: 'email', optional: true, formStep: 9, ask: 'Their email, if you have one. You can skip this.', placeholder: 'name@gmail.com', inputMode: 'email' },
  { id: 'reminderEmail', kind: 'email', optional: true, formStep: 10, ask: 'Which email should reminders go to? A Gmail address works. You can skip this.', placeholder: 'name@gmail.com', inputMode: 'email' },
]

/** Translates a string: (key, English default). Passed in by the screen, so the labels follow the chosen language. */
export type Tr = (key: string, fallback: string) => string

export const diabetesOptions = (tr: Tr): Option<HasDiabetes>[] => [
  { value: 'yes', label: tr('setup.diabetes.yes', 'Yes') },
  { value: 'not_sure', label: tr('setup.diabetes.notSure', 'Not sure') },
]

/** The quick replies for a choice question. Tapping one sends its words, exactly as if they had been typed. */
export function choicesFor(id: string, o: Options, tr: Tr): Option<string>[] {
  if (id === 'gender') return o.gender
  if (id === 'hasDiabetes') return diabetesOptions(tr)
  if (id === 'workType') return o.work
  return []
}

/** The words a quick reply sends: "not_working" is sent as "not working", which the server reads. */
export const replyText = (value: string) => value.replace(/_/g, ' ')

/** What the answer shows as, or '' when the question is still open. */
export function answerLabel(id: string, a: OnboardingAnswers, o: Options, tr: Tr): string {
  const text = (v: string) => v.trim()
  switch (id) {
    case 'name':
      return text(a.name)
    case 'birthYear':
      return text(a.birthYear)
    case 'gender':
      return labelOf(o.gender, a.gender)
    case 'hasDiabetes':
      return labelOf(diabetesOptions(tr), a.hasDiabetes)
    case 'heightCm':
      return text(a.heightCm) ? `${text(a.heightCm)} cm` : ''
    case 'weightKg':
      return text(a.weightKg) ? `${text(a.weightKg)} kg` : ''
    case 'workType':
      return labelOf(o.work, a.workType)
    case 'redFlags':
      return a.redFlags.map((x) => labelOf(o.redFlags, x)).join('; ')
    case 'contactName':
      return text(a.contactName)
    case 'contactRelation':
      return text(a.contactRelation)
    case 'contactPhone':
      return text(a.contactPhone)
    case 'contactEmail':
      return text(a.contactEmail)
    case 'reminderEmail':
      return text(a.reminderEmail)
    default:
      return ''
  }
}
