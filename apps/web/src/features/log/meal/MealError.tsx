import { useTranslation } from 'react-i18next'
import { Alert, Button } from '@/ui/primitives'
import { ArrowCounterClockwise, Image as ImageIcon, PencilSimple } from '@/ui/icons'
import type { MealReadError } from '@/data/repositories/types'

interface Props {
  error: MealReadError
  onTryAgain: () => void
  onChoosePhoto: () => void
  onManual: () => void
}

type Next = 'again' | 'choose' | 'manual'

/**
 * The reading failed. Every code gets the server's plain sentence and the same three ways forward: try again, choose another
 * photo, or enter the meal by hand. The one most likely to help for that code is the main button.
 */
export function MealError({ error, onTryAgain, onChoosePhoto, onManual }: Props) {
  const { t } = useTranslation()
  const title = (() => {
    switch (error.code) {
      case 'bad_photo':
        return t('log.meal.err.badPhoto', 'We cannot use this photo')
      case 'not_food':
        return t('log.meal.err.notFood', 'No food was found in this photo')
      case 'daily_limit':
        return t('log.meal.err.dailyLimit', 'The AI reading is not available today')
      case 'timeout':
        return t('log.meal.err.timeout', 'Reading the photo took too long')
      case 'network':
        return t('log.meal.err.network', 'Could not reach Smart Health')
      default:
        // the server's sentence under this title says what went wrong, so the title must not repeat it
        return t('log.meal.err.generic', 'The reading did not work this time')
    }
  })()

  // daily_limit: a retry will not help today, so manual entry comes first. Photo problems: another photo comes first.
  const primary: Next = error.code === 'daily_limit' ? 'manual' : error.code === 'bad_photo' || error.code === 'not_food' ? 'choose' : 'again'
  const again = { key: 'again', variant: primary === 'again' ? 'primary' : 'secondary', icon: ArrowCounterClockwise, onClick: onTryAgain, label: t('log.meal.tryAgain', 'Try again') } as const
  const choose = { key: 'choose', variant: primary === 'choose' ? 'primary' : 'secondary', icon: ImageIcon, onClick: onChoosePhoto, label: t('log.meal.choosePhotoAgain', 'Choose another photo') } as const
  const manual = { key: 'manual', variant: primary === 'manual' ? 'primary' : 'secondary', icon: PencilSimple, onClick: onManual, label: t('log.meal.byHand', 'Enter it by hand') } as const
  const order = primary === 'manual' ? [manual, again, choose] : primary === 'choose' ? [choose, again, manual] : [again, choose, manual]

  return (
    <>
      <Alert tone="warn" title={title}>
        {error.message}
      </Alert>
      <div className="flex flex-col gap-3">
        {order.map((b) => (
          <Button key={b.key} variant={b.variant} icon={b.icon} onClick={b.onClick}>
            {b.label}
          </Button>
        ))}
      </div>
    </>
  )
}
