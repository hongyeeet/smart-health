/**
 * Block 5 on Home: one "for you" card. Its candidates are, in this order: ideas Smart Health noticed and is waiting for the person
 * to check, a lunch idea (only inside the lunch window), and a food habit worth a look. The first one with content is shown in the
 * block; the rest go behind "See more". Each card's wording is unchanged from the first Home.
 */
import { Trans, useTranslation } from 'react-i18next'
import type { ReactNode } from 'react'
import { useFoodFlags, useLearned, useLunchIdeas, useDismissSuggestion } from '@/data/hooks'
import type { FoodHabit, LunchIdeas, LunchOption } from '@/data/types'
import { useGo } from '@/app/navigation'
import { Card, SectionTitle } from '@/ui/primitives'
import { Bell, CaretRight, ForkKnife } from '@/ui/icons'

/** Lunch ideas are only offered inside the person's lunch window (times from the server, never hard-coded here). */
function lunchOpenNow(d: LunchIdeas): boolean {
  const now = new Date()
  const mins = now.getHours() * 60 + now.getMinutes()
  const [sh, sm] = d.windowStart.split(':').map(Number)
  const [eh, em] = d.windowEnd.split(':').map(Number)
  return mins >= (sh ?? 0) * 60 + (sm ?? 0) && mins <= (eh ?? 0) * 60 + (em ?? 0)
}

/** The candidates that have something to say right now, most important first. Returns the rendered cards. */
export function useForYou(): { cards: ReactNode[]; loading: boolean } {
  const { data: learned, isPending: learnedPending } = useLearned()
  const { data: lunch, isPending: lunchPending } = useLunchIdeas()
  const { data: habits, isPending: habitsPending } = useFoodFlags()
  const cards: ReactNode[] = []
  if (learned && learned.toConfirm > 0) cards.push(<ToConfirmCard key="confirm" count={learned.toConfirm} />)
  if (lunch && lunch.options.length > 0 && lunchOpenNow(lunch)) cards.push(<LunchCard key="lunch" options={lunch.options} />)
  if (habits && habits.length > 0) cards.push(<FoodFlagCard key="flag" habits={habits} />)
  return { cards, loading: learnedPending || lunchPending || habitsPending }
}

/** Shown when the agent has noticed something and is waiting for the person to confirm, edit or delete it. */
export function ToConfirmCard({ count }: { count: number }) {
  const { t } = useTranslation()
  const go = useGo()
  return (
    <Card onClick={() => go('K2')} className="flex items-center gap-3">
      <span className="flex h-12 w-12 flex-none items-center justify-center rounded-full bg-brass-soft text-brass">
        <Bell size={24} aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-body font-bold">
          {count === 1 ? t('home.noticed.one', 'Smart Health noticed something') : t('home.noticed.many', 'Smart Health noticed {{n}} things', { n: count })}
        </span>
        <span className="block text-sub text-ink2">{t('home.noticed.check', 'Check it is right. You can confirm, change or delete it.')}</span>
      </span>
      <CaretRight size={20} className="flex-none text-ink3" aria-hidden />
    </Card>
  )
}

/** Shown inside the lunch window. */
export function LunchCard({ options }: { options: LunchOption[] }) {
  const { t } = useTranslation()
  const go = useGo()
  return (
    <Card onClick={() => go('E8')} className="flex items-center gap-3">
      <span className="flex h-12 w-12 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
        <ForkKnife size={24} aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-body font-bold">{t('home.lunch.title', 'Lunch ideas for you')}</span>
        <span className="block break-words text-sub text-ink2">{options.map((o) => o.name).join(', ')}</span>
      </span>
      <CaretRight size={20} className="flex-none text-ink3" aria-hidden />
    </Card>
  )
}

const NUTRIENT: Record<string, [string, string]> = { kcal: ['calories', 'kcal'], sodium_mg: ['salt', 'mg'], carbs_g: ['carbs', 'g'], sugar_g: ['sugar', 'g'], protein_g: ['protein', 'g'], fat_g: ['fat', 'g'], fibre_g: ['fibre', 'g'] }

/** A food habit the memory loop noticed, with a lighter dish to try next time and exactly what it would change. */
export function FoodFlagCard({ habits }: { habits: FoodHabit[] }) {
  const { t } = useTranslation()
  const dismiss = useDismissSuggestion()
  const go = useGo()
  const h = habits.find((x) => x.alternatives.length > 0) ?? habits[0]
  if (!h) return null
  const alt = h.alternatives[0]
  return (
    <Card className="flex flex-col gap-3">
      <SectionTitle>{t('home.worth.title', 'Worth a look')}</SectionTitle>
      <p className="text-body">
        <Trans i18nKey="home.worth.body" defaults="You have had {{label}} <0>{{n}} times</0> in the last 2 weeks, about <1>{{kcal}}</1> kcal and <2>{{sodium}}</2> mg salt each. Those are your own logged numbers." values={{ label: h.label, n: h.n, kcal: Math.round(h.avg.kcal ?? 0).toLocaleString('en-US'), sodium: Math.round(h.avg.sodium_mg ?? 0).toLocaleString('en-US') }} components={[<b key="0" />, <b key="1" className="num" />, <b key="2" className="num" />]} />
      </p>
      {alt && (
        <div className="flex flex-col gap-2 rounded-card bg-well p-3.5">
          <p className="text-sub text-ink2">{t('home.worth.heaviest', 'Your {{dish}} ({{n}} times) is the heaviest. Next time you could try', { dish: h.topDish, n: h.topDishN })}</p>
          <p className="text-h2 font-bold leading-snug">{alt.name}</p>
          <ul className="grid grid-cols-1 gap-x-4 gap-y-1 text-sub min-[480px]:grid-cols-2">
            {alt.changes
              .filter((c) => ['kcal', 'protein_g', 'carbs_g', 'sodium_mg', 'sugar_g'].includes(c.nutrient) && Math.abs(c.change) >= (c.nutrient === 'kcal' ? 50 : c.nutrient === 'sodium_mg' ? 100 : 3))
              .map((c) => (
                <li key={c.nutrient} className="flex justify-between gap-2">
                  <span className="text-ink2">{NUTRIENT[c.nutrient]![0]}</span>
                  <span className="num">
                    {Math.round(c.from).toLocaleString('en-US')} to {Math.round(c.to).toLocaleString('en-US')} {NUTRIENT[c.nutrient]![1]}
                  </span>
                </li>
              ))}
          </ul>
          <p className="text-micro text-ink3">
            {t('home.worth.servingNote', '{{serving}} {{source}}. Typical values, so your portion may differ.', { serving: alt.serving, source: alt.sourceGrade ? t('home.worth.sgDb', '· from the Singapore food database ({{grade}})', { grade: alt.sourceGrade.replace('_', ' ') }) : '' })}
          </p>
        </div>
      )}
      {h.outcomeText && <p className="rounded-card bg-ok-soft p-3.5 text-sub text-ink">{h.outcomeText}</p>}
      <p className="text-sub text-ink3">{t('home.worth.notAdvice', 'An idea for next time, not advice. Your logged meals are never changed.')}</p>
      {alt && (
        <button type="button" onClick={() => dismiss.mutate(`swap:${alt.foodId}`)} className="press min-h-12 self-start text-sub font-bold text-ink2">
          {t('home.worth.notForMe', 'Not for me')}
        </button>
      )}
      <button type="button" onClick={() => go('E2')} className="press flex min-h-12 items-center gap-2 self-start text-sub font-bold text-brand">
        <ForkKnife size={18} aria-hidden /> {t('home.action.meal', 'Log a meal')}
      </button>
    </Card>
  )
}
