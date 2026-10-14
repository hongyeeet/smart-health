import { useTranslation } from 'react-i18next'
import { dateLocale } from '@/lib/locale'
import { cn } from '@/lib/cn'
import type { InsightsDoseCell, InsightsGridCell } from '@/data/types'
import { shortDate } from '@/lib/format'
import { useGo } from '@/app/navigation'

/** How much, as a shade of the brand colour. It is an amount and not a verdict (more stress is not "bad green"), and the number is always written. */
const SHADE = [18, 38, 62, 92] as const
const shade = (level: number) => `color-mix(in oklab, var(--c-brand) ${SHADE[level - 1]}%, var(--c-card))`

/** First and last day of a month: "2026-10" gives "2026-10-01" and "2026-10-31". */
export function monthRange(month: string): { start: string; end: string } {
  const [y, m] = month.split('-').map(Number) as [number, number]
  const last = new Date(Date.UTC(y, m, 0)).getUTCDate()
  return { start: `${month}-01`, end: `${month}-${String(last).padStart(2, '0')}` }
}

/** The month before or after, as "YYYY-MM". */
export function shiftMonth(month: string, by: number): string {
  const [y, m] = month.split('-').map(Number) as [number, number]
  return new Date(Date.UTC(y, m - 1 + by, 1)).toISOString().slice(0, 7)
}

/** "October 2026" for a "YYYY-MM" month. */
export function monthTitle(month: string): string {
  const [y, m] = month.split('-').map(Number) as [number, number]
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleDateString(dateLocale('en-GB'), { month: 'long', year: 'numeric', timeZone: 'UTC' })
}

/** Monday-first weekday names in the reader's words, such as "Mon". 5 January 2026 was a Monday. */
function weekdayNames(): string[] {
  const fmt = new Intl.DateTimeFormat(dateLocale('en-GB'), { weekday: 'short', timeZone: 'UTC' })
  return Array.from({ length: 7 }, (_, i) => fmt.format(new Date(Date.UTC(2026, 0, 5 + i))))
}

/** Classes both month calendars share (this one and the diet calendar), so their squares match. Cells are square, 44 px or more. */
export const CAL = {
  head: 'grid grid-cols-7 gap-1 text-center text-micro font-bold text-ink2 sm:gap-1.5',
  grid: 'grid grid-cols-7 gap-1 sm:gap-1.5',
  cell: 'press flex aspect-square min-h-11 flex-col items-center justify-center gap-px rounded-field border-2 text-center',
  /** a day that has not come yet: an empty dashed square with its number, not pressable */
  future: 'flex aspect-square min-h-11 items-center justify-center rounded-field border border-dashed border-line text-sub text-ink3 opacity-60',
} as const

/** Weekday names over a calendar: "Mon" normally, the first letter at large text, where seven full names would run into each other. */
export function WeekdayHead({ names, hideAtLarge }: { names: string[]; /** left out at large text, where the month is shown as a list instead */ hideAtLarge?: boolean }) {
  return (
    <div className={cn(CAL.head, hideAtLarge && "[[data-ts='2']_&]:hidden")} aria-hidden>
      {names.map((w) => (
        <span key={w}>
          <span className="[[data-ts='2']_&]:hidden">{w}</span>
          <span className="hidden [[data-ts='2']_&]:inline">{[...w][0]}</span>
        </span>
      ))}
    </div>
  )
}

/**
 * One month, one square per day, for one measure (the overview calendar). A tap opens that day in the Day view (D1).
 * Days after `today` are dashed empty squares with just the number, and cannot be opened.
 */
export function DayCalendar({ month, cells, today, measure }: { month: string; cells: InsightsGridCell[]; today: string; measure: string }) {
  const go = useGo()
  const { t } = useTranslation()
  const byDate = new Map(cells.map((c) => [c.date, c]))
  const { end } = monthRange(month)
  const lastDay = Number(end.slice(8))
  const lead = (new Date(Date.UTC(Number(month.slice(0, 4)), Number(month.slice(5, 7)) - 1, 1)).getUTCDay() + 6) % 7
  const names = weekdayNames()
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-2">
      <WeekdayHead names={names} hideAtLarge />
      <div className={cn(CAL.grid, "[[data-ts='2']_&]:hidden")} role="group" aria-label={t('insights.overview.calendarLabel', '{{measure}}, {{month}}', { measure, month: monthTitle(month) })}>
        {Array.from({ length: lead }, (_, i) => (
          <span key={`lead-${i}`} aria-hidden />
        ))}
        {Array.from({ length: lastDay }, (_, i) => {
          const date = `${month}-${String(i + 1).padStart(2, '0')}`
          const dayNo = i + 1
          const c = byDate.get(date)
          if (date > today || !c) {
            return (
              <span key={date} aria-hidden className={CAL.future}>
                {dayNo}
              </span>
            )
          }
          const label = c.value == null ? t('insights.grid.noData', 'no data') : c.label
          return (
            <button
              type="button"
              key={date}
              onClick={() => go('D1', { params: { date } })}
              aria-label={t('insights.grid.cellAria', '{{row}}, {{date}}: {{value}}. Open this day', { row: measure, date: shortDate(date), value: label })}
              aria-current={date === today ? 'date' : undefined}
              style={c.level > 0 ? { background: shade(c.level) } : undefined}
              className={cn(CAL.cell, date === today ? 'border-brand' : 'border-transparent', c.level === 0 ? 'bg-well text-ink3' : c.level >= 3 ? 'text-on-brand' : 'text-ink')}
            >
              <span className="num text-micro leading-none">{dayNo}</span>
              <span className="num text-micro font-bold leading-none lg:text-sub">{c.label}</span>
            </button>
          )
        })}
      </div>
      {/* at large text seven columns cannot hold a number and a value, so the month is a list of its days so far, newest first */}
      <ul className="hidden flex-col gap-1.5 [[data-ts='2']_&]:flex" aria-label={t('insights.overview.calendarLabel', '{{measure}}, {{month}}', { measure, month: monthTitle(month) })}>
        {Array.from({ length: lastDay }, (_, i) => `${month}-${String(i + 1).padStart(2, '0')}`)
          .filter((date) => date <= today)
          .reverse()
          .map((date) => {
            const c = byDate.get(date)
            const label = !c || c.value == null ? t('insights.grid.noData', 'no data') : c.label
            return (
              <li key={date}>
                <button
                  type="button"
                  onClick={() => go('D1', { params: { date } })}
                  aria-label={t('insights.grid.cellAria', '{{row}}, {{date}}: {{value}}. Open this day', { row: measure, date: shortDate(date), value: label })}
                  aria-current={date === today ? 'date' : undefined}
                  style={c && c.level > 0 ? { background: shade(c.level) } : undefined}
                  className={cn(
                    'press flex min-h-14 w-full items-center justify-between gap-3 rounded-field border-2 px-3 py-2 text-left',
                    date === today ? 'border-brand' : 'border-transparent',
                    !c || c.level === 0 ? 'bg-well text-ink2' : c.level >= 3 ? 'text-on-brand' : 'text-ink',
                  )}
                >
                  <span className="text-sub font-bold">{shortDate(date)}</span>
                  <span className="num text-sub">{label}</span>
                </button>
              </li>
            )
          })}
      </ul>
    </div>
  )
}

/** Taken is the solid brand green (the ok token at full strength); the other states keep a pattern so they read without colour. */
export const DOSE_CLS: Record<InsightsDoseCell, string> = {
  taken: 'bg-ok border-ok text-on-brand',
  late: 'bg-card border-ok border-2 text-ink',
  unconfirmed: 'border-ink3/60 text-ink2 [background:repeating-linear-gradient(45deg,var(--c-well),var(--c-well)_3px,var(--c-line)_3px,var(--c-line)_5px)]',
  missed: 'bg-danger-soft border-danger/60 text-ink [background-image:repeating-linear-gradient(-45deg,transparent,transparent_3px,var(--c-danger)_3px,var(--c-danger)_4px)]',
  none: 'border-line bg-well text-ink3',
}

export const DOSE_LEGEND: InsightsDoseCell[] = ['taken', 'late', 'unconfirmed', 'missed', 'none']

/** What each dose state is called, in words (the legend, the day list and the screen-reader text all use these). */
export function useDoseLabels(): Record<InsightsDoseCell, string> {
  const { t } = useTranslation()
  return {
    taken: t('insights.grid.doseTaken', 'Taken'),
    late: t('insights.grid.doseLate', 'Taken late'),
    unconfirmed: t('insights.grid.doseUnconfirmed', 'Not confirmed'),
    missed: t('insights.grid.doseMissed', 'Missed'),
    none: t('insights.grid.doseNone', 'No dose due'),
  }
}
