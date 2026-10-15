import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { motion, useReducedMotion } from 'motion/react'
import { Footer, Split } from '@/ui/layout'
import { Button, Card, Skeleton } from '@/ui/primitives'
import { mmss } from './mealMath'

/** After this many seconds the screen says, honestly, that the reading can still take a while. */
const SLOW_AFTER_S = 20

/**
 * Step 2: the photo is being read. The bar moves so the screen never looks frozen, the seconds are the real time spent,
 * and Cancel stops the request (the photo and the description are kept, so the person can try again).
 */
export function MealReading({ preview, onCancel }: { preview: string | null; onCancel: () => void }) {
  const { t } = useTranslation()
  const reduce = useReducedMotion()
  const [started] = useState(() => Date.now())
  const [now, setNow] = useState(started)
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])
  const elapsed = Math.max(0, Math.round((now - started) / 1000))
  /* a file that is not a picture (or a browser that cannot show it) gets a sentence, not a broken-image icon */
  const [noPreview, setNoPreview] = useState(false)

  return (
    <>
      <Split className="md:grid-cols-2">
        {preview ? (
          <div className="overflow-hidden rounded-card border border-line bg-well">
            {noPreview ? (
              <p className="flex min-h-56 items-center justify-center p-6 text-center text-sub text-ink2">{t('log.meal.noPreview', 'This photo cannot be shown here, but it can still be read.')}</p>
            ) : (
              <img src={preview} alt={t('log.meal.alt', 'Your meal')} className="max-h-80 w-full object-cover opacity-80" onError={() => setNoPreview(true)} />
            )}
          </div>
        ) : (
          <Skeleton className="h-56 w-full" />
        )}
        <Card tone="soft" className="flex flex-col gap-4">
          <div role="status" aria-live="polite" className="flex flex-col gap-2">
            <p className="text-h2 font-bold text-ink">{t('log.meal.reading', 'Reading your meal…')}</p>
            <p className="text-sub text-ink2">{t('log.meal.readingAi', 'We are looking at the photo and estimating the portion and the nutrients.')}</p>
            {elapsed >= SLOW_AFTER_S && (
              <p className="text-sub font-bold text-ink">{t('log.meal.slow', 'Still working, this can take up to a minute.')}</p>
            )}
          </div>
          <div className="relative h-2 w-full overflow-hidden rounded-chip bg-line" role="progressbar" aria-label={t('log.meal.readingBar', 'Reading progress')} aria-valuetext={t('log.meal.seconds', '{{n}} seconds so far', { n: elapsed })}>
            <motion.div
              className="absolute inset-y-0 w-1/3 rounded-chip bg-brand"
              initial={{ left: '-33%' }}
              animate={reduce ? { left: '0%' } : { left: ['-33%', '100%'] }}
              transition={reduce ? { duration: 0 } : { duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
            />
          </div>
          <p className="num text-sub text-ink3" aria-hidden>
            {mmss(elapsed)}
          </p>
        </Card>
      </Split>
      <Footer>
        <Button variant="secondary" onClick={onCancel}>
          {t('log.meal.cancelReading', 'Cancel')}
        </Button>
      </Footer>
    </>
  )
}
