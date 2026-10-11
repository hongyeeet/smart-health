import type { useTranslation } from 'react-i18next'
import type { Medication } from '@/data/types'

type Translate = ReturnType<typeof useTranslation>['t']

/**
 * Words shared by the medicine screens (H1 My medicines, H6 the medicine page, the stock cards and the onboarding list), so a strength,
 * a refill line or a source reads the same everywhere.
 */

/** The strength is shown beside the name unless it was never entered or the name already says it ("Amlodipine 5 mg"). */
export const showStrength = (m: { name: string; strength: string | null | undefined }): boolean =>
  !!m.strength && m.strength !== 'Strength not entered' && !m.name.toLowerCase().replace(/\s+/g, '').includes(m.strength.toLowerCase().replace(/\s+/g, ''))

/** The name with its strength, so two medicines with the same name can be told apart ("Paracetamol 500 mg"). */
export const fullName = (m: { name: string; strength: string | null | undefined }): string => (showStrength(m) ? `${m.name} ${m.strength}` : m.name)

/**
 * "Paracetamol may run out in about 3 days. You may want to arrange a refill." "May" is used on purpose: the figure is a count in hand or an
 * estimate from the pack date (see refillSourceLine), never a promise.
 */
export function refillSentence(name: string, daysLeft: number, t: Translate): string {
  return daysLeft === 0
    ? t('refill.mayHaveRunOut', '{{name}} may have run out. You may want to arrange a refill.', { name })
    : t('refill.mayRunOut', '{{name}} may run out in about {{n}} {{unit}}. You may want to arrange a refill.', {
        name,
        n: daysLeft,
        unit: daysLeft === 1 ? t('refill.day', 'day') : t('refill.days', 'days'),
      })
}

/** Where the refill figure comes from: the count in hand, or the estimate from the pack date. Null when the server did not say. */
export function refillSourceLine(source: Medication['refillSource'], t: Translate): string | null {
  if (source === 'stock') return t('refill.fromStock', 'From your stock.')
  if (source === 'estimate') return t('refill.estimated', 'Estimated from the pack date.')
  return null
}
