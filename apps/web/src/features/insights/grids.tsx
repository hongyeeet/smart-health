import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/cn'
import type { InsightsDoseCell, InsightsGridCell } from '@/data/types'
import { shortDate } from '@/lib/format'
import { useGo } from '@/app/navigation'

/** How much, as a shade of the brand colour. It is an amount and not a verdict (more stress is not "bad green"), and the number is always written. */
const SHADE = [18, 38, 62, 92] as const
const shade = (level: number) => `color-mix(in oklab, var(--c-brand) ${SHADE[level - 1]}%, var(--c-card))`

export function WeekGrid({ rows }: { rows: { key: string; label: string; cells: InsightsGridCell[] }[] }) {
  const days = rows[0]?.cells ?? []
  const go = useGo()
  const { t } = useTranslation()
  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-7 gap-1.5 text-center" aria-hidden>
        {days.map((d) => (
          <span key={d.date} className="flex flex-col text-sub font-bold text-ink2">
            {d.weekday}
            <span className="num text-body font-normal text-ink">{Number(d.date.slice(8))}</span>
          </span>
        ))}
      </div>
      {rows.map((row) => (
        <div key={row.key} className="flex flex-col gap-1">
          <p className="text-sub font-bold text-ink">{row.label}</p>
          <div className="grid grid-cols-7 gap-1.5" role="group" aria-label={row.label}>
            {row.cells.map((c) => (
              <button
                type="button"
                key={c.date}
                onClick={() => go('D1', { params: { date: c.date } })}
                aria-label={t('insights.grid.cellAria', '{{row}}, {{date}}: {{value}}. Open this day', {
                  row: row.label,
                  date: shortDate(c.date),
                  value: c.level === 0 && c.value == null ? t('insights.grid.noData', 'no data') : c.label,
                })}
                style={c.level > 0 ? { background: shade(c.level) } : undefined}
                className={cn('press flex min-h-12 items-center justify-center rounded-field text-sub font-bold', c.level === 0 ? 'bg-well text-ink3' : c.level >= 3 ? 'text-on-brand' : 'text-ink')}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>
      ))}
      <p className="text-sub text-ink3">{t('insights.grid.weekKey', 'A darker square means more. A dash means there is no data for that day.')}</p>
    </div>
  )
}

const DOSE_CLS: Record<InsightsDoseCell, string> = {
  taken: 'bg-ok-soft border-ok/50',
  late: 'bg-card border-ok border-2',
  unconfirmed: 'border-ink3/60 [background:repeating-linear-gradient(45deg,var(--c-well),var(--c-well)_3px,var(--c-line)_3px,var(--c-line)_5px)]',
  missed: 'bg-danger-soft border-danger/60 [background-image:repeating-linear-gradient(-45deg,transparent,transparent_3px,var(--c-danger)_3px,var(--c-danger)_4px)]',
  none: 'border-transparent bg-well/60',
}

/** One row per medicine, one square per day. The fill and the pattern both say what happened, so it reads without colour. */
export function DoseGrid({ dates, rows }: { dates: string[]; rows: { id: string; name: string; regimen: string; cells: InsightsDoseCell[] }[] }) {
  const { t } = useTranslation()
  const DOSE_LABEL: Record<InsightsDoseCell, string> = {
    taken: t('insights.grid.doseTaken', 'Taken'),
    late: t('insights.grid.doseLate', 'Taken late'),
    unconfirmed: t('insights.grid.doseUnconfirmed', 'Not confirmed'),
    missed: t('insights.grid.doseMissed', 'Missed'),
    none: t('insights.grid.doseNone', 'No dose'),
  }
  return (
    <div className="flex flex-col gap-3">
      {rows.map((r) => (
        <div key={r.id} className="flex flex-col gap-1">
          <p className="text-sub font-bold text-ink">
            {r.name} <span className="font-normal text-ink3">{r.regimen}</span>
          </p>
          <div className="grid gap-[3px]" style={{ gridTemplateColumns: `repeat(${dates.length}, minmax(0, 1fr))` }} role="group" aria-label={t('insights.grid.dayByDay', '{{name}}, day by day', { name: r.name })}>
            {r.cells.map((c, i) => (
              <span key={i} role="img" aria-label={t('insights.grid.doseAria', '{{date}}: {{label}}', { date: shortDate(dates[i]!), label: DOSE_LABEL[c] })} className={cn('h-7 rounded-[4px] border', DOSE_CLS[c])} />
            ))}
          </div>
        </div>
      ))}
      <div className="flex justify-between text-micro text-ink3" aria-hidden>
        <span>{dates[0] ? shortDate(dates[0]) : ''}</span>
        <span>{dates.length ? shortDate(dates[dates.length - 1]!) : ''}</span>
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-sub text-ink2">
        {(['taken', 'late', 'unconfirmed', 'missed'] as const).map((k) => (
          <li key={k} className="flex items-center gap-1.5">
            <span className={cn('h-5 w-5 rounded-[4px] border', DOSE_CLS[k])} aria-hidden />
            {DOSE_LABEL[k]}
          </li>
        ))}
      </ul>
    </div>
  )
}
