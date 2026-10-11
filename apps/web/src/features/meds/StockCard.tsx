import { useTranslation } from 'react-i18next'
import { useStock } from '@/data/hooks'
import type { MedicineStock } from '@/data/types'
import { cn } from '@/lib/cn'
import { useUi } from '@/state/store'
import { CheckCircle, PencilSimple, Pill, Plus, Question, Warning, WarningCircle, type IconType } from '@/ui/icons'
import { Alert, Button, Card, EmptyState, SectionTitle, Skeleton, StatusPill, type Tone } from '@/ui/primitives'
import { TileGrid } from '@/ui/layout'
import { showStrength } from './medicineText'

/**
 * "My stock" on the Medications screen (H1): how many of each regular medicine are left. Each card shows the count, the days left at
 * the usual dose, a bar (full to empty against the last amount set or bought) and a status with an icon and a word. Two buttons:
 * "I bought more" (adds) and "Change the number" (sets). The status states a fact about the count; it gives no advice.
 */
export function StockSection() {
  const { t } = useTranslation()
  const { data, isLoading, isError, refetch } = useStock()
  const openSheet = useUi((s) => s.openSheet)
  const open = (m: MedicineStock, mode: 'add' | 'set') => openSheet('H9', { medId: m.id, mode })

  return (
    <section className="flex flex-col gap-3">
      <SectionTitle>{t('stock.title', 'My stock')}</SectionTitle>
      <p className="-mt-2 text-sub text-ink2">
        {t('stock.intro', 'How many you have left. It goes down by one dose each time you mark a dose as taken.')}
      </p>

      {isLoading && <Skeleton className="h-40" />}
      {isError && (
        <Alert tone="warn" onClick={() => void refetch()}>
          {t('stock.error', 'We could not load your stock. Tap to try again.')}
        </Alert>
      )}
      {data && !data.ready && (
        <Card tone="soft">
          <p className="text-body text-ink2">{t('stock.notReady', 'Stock tracking is being set up. Your medicines and doses work as usual.')}</p>
        </Card>
      )}
      {data?.ready && data.items.length === 0 && (
        <EmptyState icon={Pill}>
          {t('stock.empty', 'Your regular medicines will show here with how many you have left. Medicines taken only when needed are not counted.')}
        </EmptyState>
      )}
      {data?.ready && data.items.length > 0 && (
        <TileGrid>
          {data.items.map((m) => (
            <li key={m.id} className="flex">
              <StockCard m={m} onBought={() => open(m, 'add')} onSet={() => open(m, 'set')} />
            </li>
          ))}
        </TileGrid>
      )}
    </section>
  )
}

/** Shown as a number with no trailing ".0", and to two places at most ("0.5", "12"). */
const countText = (n: number) => Number(n.toFixed(2)).toString()

/** "tablet" for one, "tablets" for more. The unit is the stored word, or the usual one for the medicine's type. */
const unitFor = (unit: string | null, n: number) => (unit ? (n === 1 ? unit.replace(/s$/, '') : unit) : '')

function StockCard({ m, onBought, onSet }: { m: MedicineStock; onBought: () => void; onSet: () => void }) {
  const { t } = useTranslation()
  const count = m.stockCount
  const fill = count !== null && m.fullCount ? Math.min(1, count / m.fullCount) : null
  const pct = fill === null ? null : Math.round(fill * 100)
  const strength = showStrength(m) ? m.strength : null

  // The status, always with an icon and a word (never colour alone). Running low is 7 days or fewer (LOW_STOCK_DAYS on the server).
  const pill: { tone: Tone; icon: IconType; label: string } =
    m.status === 'ok' ? { tone: 'ok', icon: CheckCircle, label: t('stock.ok', 'OK') }
    : m.status === 'low' ? { tone: 'warn', icon: Warning, label: t('stock.low', 'Running low') }
    : m.status === 'out' ? { tone: 'danger', icon: WarningCircle, label: t('stock.out', 'Out') }
    : { tone: 'neutral', icon: Question, label: count === null ? t('stock.notSetYet', 'Not set yet') : t('stock.daysUnknown', 'Days not known') }

  const days =
    count === null ? t('stock.setFirst', 'Tap "Change the number" to enter how many you have.')
    : count <= 0 ? t('stock.noneLeft', 'None left.')
    : m.daysLeft === null ? t('stock.noDoseTimes', 'Days left is not known yet. This medicine has no dose times.')
    : m.daysLeft === 0 ? t('stock.lessThanDay', 'Less than a day left at your usual dose.')
    : m.daysLeft === 1 ? t('stock.oneDay', 'About 1 day left at your usual dose.')
    : t('stock.days', 'About {{n}} days left at your usual dose.', { n: m.daysLeft })

  return (
    <Card className="flex h-full flex-col gap-3">
      <div className="flex flex-col items-start gap-2">
        <p className="min-w-0 break-words text-h2 font-bold leading-tight">
          {m.name}
          {strength && <span className="font-normal text-ink2"> {strength}</span>}
        </p>
        <StatusPill tone={pill.tone} icon={pill.icon}>
          {pill.label}
        </StatusPill>
      </div>

      {/* When the count is not set, the status pill already says "Not set yet": the count line is left out rather than saying it twice. */}
      {count !== null && (
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span className="num text-display font-bold leading-none">{countText(count)}</span>
          <span className="text-body text-ink2">{t('stock.left', '{{unit}} left', { unit: unitFor(m.stockUnit, count) })}</span>
        </div>
      )}

      {pct !== null && (
        <div
          role="progressbar"
          aria-label={t('stock.barLabel', 'How much of {{name}} is left', { name: m.name })}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={pct}
          aria-valuetext={t('stock.barText', '{{have}} of {{full}} left', { have: countText(count ?? 0), full: countText(m.fullCount ?? 0) })}
          className="h-3 w-full overflow-hidden rounded-full bg-well"
        >
          <div className={cn('h-full rounded-full', m.status === 'out' ? 'bg-danger' : m.status === 'low' ? 'bg-warn' : 'bg-brand')} style={{ width: `${pct}%` }} />
        </div>
      )}

      <p className="text-sub text-ink2">{days}</p>
      {m.updatedAt && (
        <p className="text-micro text-ink3">
          {t('stock.updated', 'Last changed {{date}}', { date: new Date(m.updatedAt).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) })}
        </p>
      )}

      <div className="mt-auto flex flex-col gap-2">
        <Button variant="secondary" size="md" icon={Plus} disabled={count === null} onClick={onBought}>
          {t('stock.bought', 'I bought more')}
        </Button>
        <Button variant="ghost" size="md" icon={PencilSimple} onClick={onSet}>
          {t('stock.change', 'Change the number')}
        </Button>
      </div>
    </Card>
  )
}

