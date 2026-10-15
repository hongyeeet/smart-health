import i18n from '@/i18n'
import { useState } from 'react'
import { dateLocale } from '@/lib/locale'
import { useTranslation } from 'react-i18next'
import { useRemoveMed } from '@/data/hooks'
import type { Medication, MedicineStock } from '@/data/types'
import { cn } from '@/lib/cn'
import { shortDate } from '@/lib/format'
import { CaretRight, CheckCircle, Info, PencilSimple, Pill, Plus, Question, Trash, Warning, WarningCircle, type IconType } from '@/ui/icons'
import { Button, Card, StatusPill, TextLink, type Tone } from '@/ui/primitives'
import { fullName, showStrength } from './medicineText'

/** Shown as a number with no trailing ".0", and to two places at most ("0.5", "12"). */
export const countText = (n: number) => Number(n.toFixed(2)).toString()

/** "tablet" for one, "tablets" for more. The unit is the stored word. */
/** The unit word for a count ('tablets', or 'tablet' for one), in the person's language. A word with no translation is shown as it is. */
export const unitFor = (unit: string | null, n: number) => {
  if (!unit) return ''
  const word = n === 1 ? unit.replace(/s$/, '') : unit
  return i18n.t(`stock.unit.${word}`, { defaultValue: word })
}

/**
 * One medicine on the Meds screen (H1, "All medications"): its name and strength with Remove at the top right, the dose times and tags,
 * how many are left (count with its unit, a bar, the days left, an Edit link), and at the bottom "I bought more" and the way in to
 * "What it is for and side effects". The count goes down by itself each time a dose is marked taken (the server does that). The status
 * states a fact about the count; it gives no advice.
 */
export function MedStockCard({
  m,
  stock,
  today,
  onBought,
  onEdit,
  onOpen,
}: {
  m: Medication
  stock: MedicineStock | undefined
  today: string
  onBought: () => void
  onEdit: () => void
  onOpen: () => void
}) {
  const { t } = useTranslation()
  const remove = useRemoveMed()
  const [confirming, setConfirming] = useState(false)
  const ended = !!m.endDate && m.endDate < today

  return (
    <div className="relative flex h-full flex-col">
      <Card className="flex flex-1 flex-col gap-3">
        {/* the name on the left and Remove at the top right, side by side so a long name or large text wraps instead of running under the button */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="break-words text-h2 font-bold leading-tight">
              {m.name}
              {showStrength(m) && <span className="font-normal text-ink2"> {m.strength}</span>}
            </p>
            <p className="text-sub text-ink2">
              {m.asNeeded ? t('meds.onlyWhenNeeded', 'Only when needed') : m.times.length ? m.times.join(', ') : t('meds.noDoseTimes', 'No dose times')}
              {m.withFood && t('meds.withFood', ', with food')}
            </p>
          </div>
          <button
            type="button"
            onClick={() => setConfirming(true)}
            aria-label={t('meds.removeAria', 'Remove {{name}}', { name: fullName(m) })}
            className="press -mr-2 -mt-2 flex min-h-12 flex-none items-center gap-1.5 rounded-chip px-3 text-sub font-bold text-ink2 hover:bg-well"
          >
            <Trash size={18} aria-hidden /> {t('meds.remove', 'Remove')}
          </button>
        </div>

        {(m.kind !== 'prescription' || m.badge) && (
          <div className="flex flex-wrap gap-2">
            {m.kind === 'supplement' && (
              <StatusPill tone="neutral" icon={Pill} bare>
                {t('meds.kind.supplement', 'Supplement')}
              </StatusPill>
            )}
            {m.kind === 'tcm' && (
              <StatusPill tone="neutral" icon={Pill} bare>
                {t('meds.kind.herbal', 'Herbal')}
              </StatusPill>
            )}
            {m.kind === 'otc' && (
              <StatusPill tone="neutral" icon={Pill} bare>
                {t('meds.kind.otc', 'Over the counter')}
              </StatusPill>
            )}
            {m.badge === 'not_checked' && (
              <StatusPill tone="neutral" icon={Info}>
                {t('meds.notChecked', 'Not checked')}
              </StatusPill>
            )}
          </div>
        )}

        {ended ? (
          <p className="text-sub text-ink2">{t('meds.courseEnded', 'Course ended {{date}}.', { date: shortDate(m.endDate!) })}</p>
        ) : m.asNeeded ? (
          <p className="text-sub text-ink3">{t('meds.notCountedStock', 'Taken only when needed, so it is not counted in your stock.')}</p>
        ) : stock ? (
          <StockBlock s={stock} onEdit={onEdit} />
        ) : null}

        <div className="mt-auto flex flex-col gap-2">
          {stock && !ended && !m.asNeeded && (
            <Button variant="secondary" size="md" icon={Plus} onClick={onBought}>
              {t('stock.bought', 'I bought more')}
            </Button>
          )}
          <button type="button" onClick={onOpen} className="press flex min-h-11 items-center gap-1 self-start text-sub font-bold text-brand">
            {t('meds.whatFor', 'What it is for and side effects')}
            <CaretRight size={16} aria-hidden />
          </button>
        </div>
      </Card>

      {confirming && (
        <div className="mt-2 flex flex-col gap-3 rounded-card border border-line bg-card p-4" role="alertdialog" aria-label={t('meds.removeQ', 'Remove {{name}}?', { name: fullName(m) })}>
          <p className="text-body">
            {t('meds.removeBody1', 'Remove')} <b>{fullName(m)}</b>{' '}
            {t('meds.removeBody2', 'from your list? It will stop showing in your medicines, doses and clash checks. Your past dose history is kept.')}
          </p>
          <div className="flex flex-wrap gap-2">
            <Button size="md" variant="danger" className="!w-auto" disabled={remove.isPending} onClick={() => remove.mutate(m.id, { onSuccess: () => setConfirming(false) })}>
              {remove.isPending ? t('meds.removing', 'Removing…') : t('meds.removeYes', 'Yes, remove it')}
            </Button>
            <Button size="md" variant="ghost" className="!w-auto" disabled={remove.isPending} onClick={() => setConfirming(false)}>
              {t('meds.keep', 'Keep it')}
            </Button>
          </div>
          {remove.isError && <p className="text-sub text-ink2">{t('meds.removeError', 'We could not remove it just now. Please try again.')}</p>}
        </div>
      )}
    </div>
  )
}

/** The count with its unit, the bar, the days left and the last change; or "Not set yet" with the way to enter it. */
function StockBlock({ s, onEdit }: { s: MedicineStock; onEdit: () => void }) {
  const { t } = useTranslation()
  const count = s.stockCount
  const fill = count !== null && s.fullCount ? Math.min(1, count / s.fullCount) : null
  const pct = fill === null ? null : Math.round(fill * 100)

  // The status, always with an icon and a word (never colour alone). Running low is 7 days or fewer (LOW_STOCK_DAYS on the server).
  const pill: { tone: Tone; icon: IconType; label: string } =
    s.status === 'ok' ? { tone: 'ok', icon: CheckCircle, label: t('stock.ok', 'OK') }
    : s.status === 'low' ? { tone: 'warn', icon: Warning, label: t('stock.low', 'Running low') }
    : s.status === 'out' ? { tone: 'danger', icon: WarningCircle, label: t('stock.out', 'Out') }
    : { tone: 'neutral', icon: Question, label: count === null ? t('stock.notSetYet', 'Not set yet') : t('stock.daysUnknown', 'Days not known') }

  const days =
    count === null ? t('stock.setFirstEdit', 'Tap "Edit" to enter how many you have.')
    : count <= 0 ? t('stock.noneLeft', 'None left.')
    : s.daysLeft === null ? t('stock.noDoseTimes', 'Days left is not known yet. This medicine has no dose times.')
    : s.daysLeft === 0 ? t('stock.lessThanDay', 'Less than a day left at your usual dose.')
    : s.daysLeft === 1 ? t('stock.oneDay', 'About 1 day left at your usual dose.')
    : t('stock.days', 'About {{n}} days left at your usual dose.', { n: s.daysLeft })

  return (
    <div className="flex flex-col gap-3">
      <div className="self-start">
        <StatusPill tone={pill.tone} icon={pill.icon}>
          {pill.label}
        </StatusPill>
      </div>

      {/* When the count is not set, the status pill already says "Not set yet": the count line is left out rather than saying it twice. */}
      {count !== null && (
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <div className="flex flex-wrap items-baseline gap-x-2">
            <span className="num text-display font-bold leading-none">{countText(count)}</span>
            <span className="text-body text-ink2">{t('stock.left', '{{unit}} left', { unit: unitFor(s.stockUnit, count) })}</span>
          </div>
          <TextLink icon={PencilSimple} onClick={onEdit} className="!min-h-11">
            {t('stock.edit', 'Edit')}
          </TextLink>
        </div>
      )}

      {pct !== null && (
        <div
          role="progressbar"
          aria-label={t('stock.barLabel', 'How much of {{name}} is left', { name: s.name })}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={pct}
          aria-valuetext={t('stock.barText', '{{have}} of {{full}} left', { have: countText(count ?? 0), full: countText(s.fullCount ?? 0) })}
          className="h-3 w-full overflow-hidden rounded-full bg-well"
        >
          <div className={cn('h-full rounded-full', s.status === 'out' ? 'bg-danger' : s.status === 'low' ? 'bg-warn' : 'bg-brand')} style={{ width: `${pct}%` }} />
        </div>
      )}

      <p className="text-sub text-ink2">{days}</p>
      {count === null && (
        <TextLink icon={PencilSimple} onClick={onEdit} className="self-start !min-h-11">
          {t('stock.edit', 'Edit')}
        </TextLink>
      )}
      {s.updatedAt && (
        <p className="text-micro text-ink3">
          {t('stock.updated', 'Last changed {{date}}', { date: new Date(s.updatedAt).toLocaleDateString(dateLocale('en-GB'), { day: 'numeric', month: 'short' }) })}
        </p>
      )}
    </div>
  )
}
