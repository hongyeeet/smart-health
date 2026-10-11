/**
 * How foods moved the glucose: the rise in the 2 hours after each food, gentlest first. A food is ranked only after it has been
 * logged at least twice with the sensor on (the server does that); foods seen once are listed as still learning.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'
import type { InsightsFood } from '@/data/types'
import { signed } from '@/lib/format'
import { ease } from '@/motion/tokens'
import { Button, Card, Chip, SectionTitle } from '@/ui/primitives'

type R = InsightsFood['responses'][number]

function Bars({ rows, max }: { rows: R[]; max: number }) {
  const { t } = useTranslation()
  return (
    <ul className="flex flex-col gap-3">
      {rows.map((f, i) => (
        <li key={f.name} className="flex flex-col gap-1.5">
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-body font-bold leading-snug">{f.name}</span>
            <span className="num flex-none text-h2">{signed(f.medianRise)}</span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-well" aria-hidden>
            <motion.div
              className={f.medianRise >= 3 ? 'h-full rounded-full bg-warn' : 'h-full rounded-full bg-brand'}
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(100, (f.medianRise / max) * 100)}%` }}
              transition={{ duration: 0.5, ease: ease.out, delay: i * 0.04 }}
            />
          </div>
          <p className="text-sub text-ink2">
            {t('insights.food.seenRise', 'Seen {{n}} times, rise {{low}} to {{high}} mmol/L', { n: f.n, low: f.low.toFixed(1), high: f.high.toFixed(1) })}
          </p>
        </li>
      ))}
    </ul>
  )
}

export function FoodRanking({ responses, stillLearning }: { responses: R[]; stillLearning: string[] }) {
  const { t } = useTranslation()
  const [all, setAll] = useState(false)
  const max = Math.max(3, Math.ceil(Math.max(0, ...responses.map((x) => x.medianRise))))
  const gentle = responses.slice(0, 5)
  const spiky = responses.length > 5 ? responses.slice(-5).reverse() : []
  return (
    <section className="flex flex-col gap-3">
      <SectionTitle>{t('insights.food.howMoved', 'How foods moved your glucose')}</SectionTitle>
      <p className="text-body text-ink2">{t('insights.food.movedPlain', 'The rise in glucose in the 2 hours after each food, from your sensor. Gentlest first.')}</p>
      {responses.length === 0 ? (
        <Card tone="soft">
          <p className="text-body text-ink2">{t('insights.food.needTwice', 'A food needs to be logged at least twice, with the sensor on, before it is ranked here.')}</p>
        </Card>
      ) : (
        <Card tone="hero" className="flex flex-col gap-4">
          <p className="text-sub font-bold text-ink3">{all ? t('insights.food.allFoods', 'All foods, gentlest first') : t('insights.food.gentlestOn', 'Gentlest on your glucose')}</p>
          <Bars rows={all ? responses : gentle} max={max} />
          {!all && spiky.length > 0 && (
            <>
              <p className="text-sub font-bold text-ink3">{t('insights.food.biggest', 'Biggest rises')}</p>
              <Bars rows={spiky} max={max} />
            </>
          )}
          {responses.length > 10 && (
            <Button variant="secondary" onClick={() => setAll((v) => !v)}>
              {all ? t('insights.food.showFewer', 'Show fewer') : t('insights.food.showAll', 'Show all {{n}}', { n: responses.length })}
            </Button>
          )}
        </Card>
      )}
      {stillLearning.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-sub text-ink2">{t('insights.food.stillLearning', 'Still learning (seen once, not ranked yet):')}</p>
          <div className="flex flex-wrap gap-2">
            {stillLearning.map((n) => (
              <Chip key={n}>{n}</Chip>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
