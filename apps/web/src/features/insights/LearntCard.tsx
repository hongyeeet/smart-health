/**
 * Insights → Overview, "What Equinox has learnt": the patterns the nightly job found in the person's own history, as short lines. One note says what
 * they are (patterns, not proven) instead of repeating a tag on every line. The long sentence from the server is kept in the title (hover, and read by a screen
 * reader); the line shows a short form built from the same number.
 */
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import type { InsightsPattern, InsightsTab } from '@/data/types'
import { Drop, ForkKnife, Moon, PersonSimpleWalk, Pill } from '@/ui/icons'
import type { ComponentType } from 'react'

const numberIn = (text: string) => /(\d+(?:\.\d+)?)/.exec(text)?.[1] ?? ''

interface Short {
  Icon: ComponentType<{ size?: number; className?: string; 'aria-hidden'?: boolean }>
  text: string
  unit: string
}

function shortOf(t: TFunction, p: InsightsPattern): Short {
  // the first number in the long sentence of these patterns is the size of the change, for the keys below (a "60 g" threshold is skipped)
  const nums = [...p.text.matchAll(/(\d+(?:\.\d+)?)/g)].map((m) => m[1]!)
  const d = p.key === 'high_carb_meal__rise' ? (nums[1] ?? numberIn(p.text)) : numberIn(p.text)
  switch (p.key) {
    case 'high_carb_meal__rise':
      return {
        Icon: ForkKnife,
        text: t('insights.learnt.carb', 'Meals over 60 g carbs: glucose rose {{d}} mmol/L more', { d }),
        unit: t('insights.learnt.meals', '{{n}} meals', { n: p.n }),
      }
    case 'sweet_drink__rise':
      return {
        Icon: Drop,
        text: t('insights.learnt.sweet', 'After sweet drinks: glucose rose {{d}} mmol/L more', { d }),
        unit: t('insights.learnt.meals', '{{n}} meals', { n: p.n }),
      }
    case 'evening_walk__next_morning_fasting':
      return {
        Icon: PersonSimpleWalk,
        text: t('insights.learnt.walk', 'After an evening walk: morning glucose {{d}} mmol/L lower', { d }),
        unit: t('insights.learnt.days', '{{n}} days', { n: p.n }),
      }
    case 'short_sleep__fasting_glucose':
      return {
        Icon: Moon,
        text: t('insights.learnt.sleep', 'After under 6 h of sleep: morning glucose {{d}} mmol/L higher', { d }),
        unit: t('insights.learnt.days', '{{n}} days', { n: p.n }),
      }
    case 'missed_evening_dose__post_dinner_rise':
      return {
        Icon: Pill,
        text: t('insights.learnt.missed', 'When the evening dose was missed: dinner rise {{d}} mmol/L bigger', { d }),
        unit: t('insights.learnt.days', '{{n}} days', { n: p.n }),
      }
    default:
      return { Icon: Drop, text: p.text, unit: t('insights.learnt.days', '{{n}} days', { n: p.n }) }
  }
}

export function LearntCard({ items, onOpen, onAll }: { items: InsightsPattern[]; onOpen: (to: InsightsTab) => void; onAll: () => void }) {
  const { t } = useTranslation()
  return (
    <section
      className="flex flex-col gap-2 rounded-card border border-line bg-card p-3.5 shadow-lift"
      aria-label={t('insights.overview.learnt', 'What Equinox has learnt')}
    >
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-body font-bold">{t('insights.overview.learnt', 'What Equinox has learnt')}</h2>
      </div>
      {items.length === 0 ? (
        <p className="text-sub text-ink2">
          {t(
            'insights.overview.learntNone',
            'Equinox needs a few more matched meals and readings before it can show what it has learnt from your own history.',
          )}
        </p>
      ) : (
        <ul className="flex flex-col">
          {items.map((p) => {
            const s = shortOf(t, p)
            return (
              <li key={p.key} className="border-t border-line first:border-t-0">
                <button type="button" onClick={() => onOpen(p.to)} title={p.text} className="press flex w-full items-start gap-2.5 py-2 text-left">
                  <span className="mt-0.5 flex h-7 w-7 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
                    <s.Icon size={15} aria-hidden />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[13px] leading-snug text-ink">{s.text}</span>
                    <span className="block text-[11px] leading-tight text-ink3">{s.unit}</span>
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
      <p className="text-[11px] leading-snug text-ink3">
        {t('insights.learnt.note', 'Patterns in your own history. They compare two things and do not prove a cause.')}
      </p>
      <button type="button" onClick={onAll} className="press -ml-1 min-h-9 self-start rounded-chip px-1 text-sub font-bold text-brand underline">
        {t('insights.learnt.all', 'See everything it has learnt')}
      </button>
    </section>
  )
}
