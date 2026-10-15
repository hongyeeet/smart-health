/**
 * How foods moved the glucose: the rise in the 2 hours after each food. Two columns from a tablet up: the gentlest five (green) and the
 * biggest five (orange). A food is ranked only after it has been logged at least twice with the sensor on (the server does that);
 * foods seen once are listed as still learning. Colour only, no verdict words.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'
import type { InsightsFood } from '@/data/types'
import { cn } from '@/lib/cn'
import { signed } from '@/lib/format'
import { ease } from '@/motion/tokens'
import { Button, Card, Chip } from '@/ui/primitives'
import { TONE, riseTone, type RiseTone } from './tones'

type R = InsightsFood['responses'][number]

const BAR: Record<RiseTone, string> = { ok: 'bg-ok', brass: 'bg-brass', warn: 'bg-warn' }

function Column({ title, rows, max, fixed }: { title: string; rows: R[]; max: number; fixed?: 'ok' | 'warn' }) {
  const { t } = useTranslation()
  return (
    <div className="flex min-w-0 flex-col">
      <p className={cn('text-micro font-bold uppercase tracking-wide', fixed ? TONE[fixed].fg : 'text-ink3')}>{title}</p>
      <ul className="flex flex-col">
        {rows.map((f, i) => {
          const tone = fixed ?? riseTone(f.medianRise)
          return (
            <li key={f.name} className="flex min-w-0 flex-col gap-1.5 border-t border-line py-2.5">
              <div className="flex items-baseline justify-between gap-3">
                <span className="min-w-0 text-sub font-bold leading-snug">{f.name}</span>
                <span className={cn('num flex-none whitespace-nowrap text-body font-bold', TONE[tone].fg)}>{signed(f.medianRise)}</span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-well" aria-hidden>
                <motion.div
                  className={cn('h-full rounded-full', BAR[tone])}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(100, (f.medianRise / max) * 100)}%` }}
                  transition={{ duration: 0.5, ease: ease.out, delay: i * 0.04 }}
                />
              </div>
              <p className="text-micro text-ink2">
                {t('insights.food.seenRiseRange', 'Seen {{n}} times, rise {{low}} to {{high}} mmol/L', {
                  n: f.n,
                  low: f.low.toFixed(1),
                  high: f.high.toFixed(1),
                })}
              </p>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export function FoodRanking({ responses, stillLearning }: { responses: R[]; stillLearning: string[] }) {
  const { t } = useTranslation()
  const [all, setAll] = useState(false)
  const max = Math.max(3, Math.ceil(Math.max(0, ...responses.map((x) => x.medianRise))))
  const gentle = responses.slice(0, 5)
  const spiky = responses.length > 5 ? responses.slice(-5).reverse() : []
  return (
    <section className="flex flex-col gap-2">
      <Card className="flex flex-col gap-4">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between sm:gap-3">
          <h3 className="text-body font-bold">{t('insights.food.howMoved', 'How foods moved your glucose')}</h3>
          <p className="text-sub text-ink2">{t('insights.food.movedSub', 'Rise in the 2 hours after each food, from your sensor')}</p>
        </div>
        {responses.length === 0 ? (
          <p className="text-body text-ink2">
            {t('insights.food.needTwice', 'A food needs to be logged at least twice, with the sensor on, before it is ranked here.')}
          </p>
        ) : all ? (
          <Column title={t('insights.food.allFoods', 'All foods, gentlest first')} rows={responses} max={max} />
        ) : (
          <div className={cn('grid grid-cols-1 gap-x-9 gap-y-5', spiky.length > 0 && 'md:grid-cols-2')}>
            <Column title={t('insights.food.gentlestOn', 'Gentlest on your glucose')} rows={gentle} max={max} fixed="ok" />
            {spiky.length > 0 && <Column title={t('insights.food.biggest', 'Biggest rises')} rows={spiky} max={max} fixed="warn" />}
          </div>
        )}
        {responses.length > 10 && (
          <Button variant="secondary" size="md" className="self-start" onClick={() => setAll((v) => !v)}>
            {all ? t('insights.food.showFewer', 'Show fewer') : t('insights.food.showAll', 'Show all {{n}}', { n: responses.length })}
          </Button>
        )}
      </Card>
      {stillLearning.length > 0 && (
        <div className="flex flex-col gap-2 pt-2">
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
