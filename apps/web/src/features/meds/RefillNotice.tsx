import { useTranslation } from 'react-i18next'
import type { Medication } from '@/data/types'
import { NoticeCard } from '@/features/alerts/NoticeCard'
import { Clock } from '@/ui/icons'
import { fullName, refillSentence, refillSourceLine } from './medicineText'

/** A medicine that may run out within a week, as one clean notice (the same card as the clash notice, blue edge): one card per medicine. */
export function RefillNotice({ m }: { m: Medication & { refill: NonNullable<Medication['refill']> } }) {
  const { t } = useTranslation()
  const source = refillSourceLine(m.refillSource, t)
  return (
    <NoticeCard tone="info" icon={Clock} tag={t('refill.tag', 'Refill reminder')} title={refillSentence(fullName(m), m.refill.daysLeft, t)}>
      {source && <p className="-mt-1 text-sub text-ink3">{source}</p>}
    </NoticeCard>
  )
}
