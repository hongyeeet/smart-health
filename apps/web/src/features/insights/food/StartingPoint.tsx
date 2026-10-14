/**
 * Your starting point: the first two full weeks against now, for calories and salt. Carbohydrate is not kept in the progress data, so
 * its row shows a dash rather than a made-up number. Until there are two full weeks, the server's note is shown instead.
 */
import { useTranslation } from 'react-i18next'
import type { Progress } from '@/data/types'
import { Card } from '@/ui/primitives'
import { num } from '../shared'

export function StartingPoint({ progress }: { progress: Progress }) {
  const { t } = useTranslation()
  const c = progress.compare
  const rows: { label: string; first: number | null | undefined; latest: number | null | undefined; unit: string }[] = [
    { label: t('insights.food.startKcal', 'Calories a day'), first: c?.avgKcal.first, latest: c?.avgKcal.latest, unit: '' },
    { label: t('insights.food.startCarbs', 'Carbs a day'), first: null, latest: null, unit: 'g' },
    { label: t('insights.food.startSalt', 'Salt a day'), first: c?.avgSodium.first, latest: c?.avgSodium.latest, unit: 'mg' },
  ]
  const fmt = (v: number | null | undefined, unit: string) => (v == null ? '–' : `${num(v)}${unit ? ` ${unit}` : ''}`)
  return (
    <Card className="flex flex-col gap-1">
      <h3 className="text-body font-bold">{t('insights.food.startTitle', 'Your starting point')}</h3>
      <p className="text-sub text-ink2">{t('insights.food.startSub', 'Your first 14 days, then now')}</p>
      {c ? (
        <ul className="flex flex-col pt-1">
          {rows.map((r) => (
            <li key={r.label} className="flex items-baseline gap-2 border-t border-line py-2">
              <span className="min-w-0 flex-1 text-sub text-ink2">{r.label}</span>
              <span className="num flex-none whitespace-nowrap text-sub text-ink3">{fmt(r.first, r.unit)}</span>
              <span aria-hidden className="flex-none text-ink3">
                →
              </span>
              <span className="num flex-none whitespace-nowrap text-sub font-bold">{fmt(r.latest, r.unit)}</span>
            </li>
          ))}
        </ul>
      ) : (
        progress.note && <p className="pt-1 text-sub text-ink2">{progress.note}</p>
      )}
    </Card>
  )
}
