/** Where a meal's numbers came from: "Your numbers" when the person typed or changed them, "Estimated" when the photo reading gave them. Nothing when it is not known. */
import { useTranslation } from 'react-i18next'
import { EstimateBadge, StatusPill } from '@/ui/primitives'
import { PencilSimple } from '@/ui/icons'

export function NumbersTag({ from }: { from?: 'you' | 'estimate' }) {
  const { t } = useTranslation()
  if (from === 'you') return <StatusPill tone="brand" icon={PencilSimple}>{t('insights.food.yourNumbers', 'Your numbers')}</StatusPill>
  if (from === 'estimate') return <EstimateBadge />
  return null
}
