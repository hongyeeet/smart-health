/**
 * The Medication tab's month calendar (C6). One square per day, and the square says what happened to that day's doses: all taken, something missed,
 * something not confirmed, or no dose due. A medicine filter narrows it to one medicine. Tap a day to open it in the panel beside (a closer look at
 * each medicine). A day with no record for a medicine is "no dose due", never "missed". Days after the latest day with data are dashed and empty.
 */
import { useTranslation } from 'react-i18next'
import type { InsightsDoseCell, InsightsMedication } from '@/data/types'
import { cn } from '@/lib/cn'
import { CaretLeft, CaretRight, Check, X } from '@/ui/icons'
import { WeekdayHead, monthRange, monthTitle } from './grids'
import { dateLocale } from '@/lib/locale'

export type DoseDay = { kind: 'taken' | 'missed' | 'unconfirmed' | 'none'; done: number; total: number; missed: number; unconfirmed: number }

type Med = InsightsMedication['meds'][number]

/** What happened on one day, over the medicines shown (all, or the one picked). */
export function dayStatus(meds: Med[], idx: number): DoseDay {
  let done = 0
  let total = 0
  let missed = 0
  let unconfirmed = 0
  for (const m of meds) {
    const c: InsightsDoseCell | undefined = m.cells[idx]
    if (!c || c === 'none') continue
    total++
    if (c === 'taken' || c === 'late') done++
    else if (c === 'missed') missed++
    else unconfirmed++
  }
  const kind = total === 0 ? 'none' : missed > 0 ? 'missed' : unconfirmed > 0 ? 'unconfirmed' : 'taken'
  return { kind, done, total, missed, unconfirmed }
}

export const DAY_TONE: Record<DoseDay['kind'], { box: string; text: string }> = {
  taken: { box: 'bg-ok-soft', text: 'text-ok' },
  missed: { box: 'bg-danger-soft', text: 'text-danger' },
  unconfirmed: { box: 'bg-brass-soft', text: 'text-brass' },
  none: { box: 'bg-well/60', text: 'text-ink3' },
}

const weekdays = () => {
  const fmt = new Intl.DateTimeFormat(dateLocale('en-GB'), { weekday: 'short', timeZone: 'UTC' })
  return Array.from({ length: 7 }, (_, i) => fmt.format(new Date(Date.UTC(2026, 0, 5 + i))))
}

export function DoseCalendar({
  data,
  filter,
  onFilter,
  picked,
  onPick,
  onMonth,
}: {
  data: InsightsMedication
  filter: string
  onFilter: (id: string) => void
  picked: string | null
  onPick: (date: string) => void
  onMonth: (m: string) => void
}) {
  const { t } = useTranslation()
  const month = data.month ?? data.period.start.slice(0, 7)
  const { end } = monthRange(month)
  const lastDay = Number(end.slice(8))
  const lead = (new Date(Date.UTC(Number(month.slice(0, 4)), Number(month.slice(5, 7)) - 1, 1)).getUTCDay() + 6) % 7
  const idx = new Map(data.dates.map((d, i) => [d, i]))
  const latest = data.dates[data.dates.length - 1] ?? ''
  const shown = filter === 'all' ? data.meds : data.meds.filter((m) => m.id === filter)
  const all = Array.from({ length: lastDay }, (_, i) => `${month}-${String(i + 1).padStart(2, '0')}`)
  const words = (k: DoseDay['kind'], d: DoseDay) =>
    k === 'missed'
      ? t('insights.medication.cellMissed', '{{n}} missed', { n: d.missed })
      : k === 'unconfirmed'
        ? t('insights.medication.cellUnconfirmed', '{{n}} not confirmed', { n: d.unconfirmed })
        : k === 'taken'
          ? t('insights.medication.cellTaken', '{{done}} of {{total}}', { done: d.done, total: d.total })
          : ''

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => data.prevMonth && onMonth(data.prevMonth)}
            disabled={!data.prevMonth}
            aria-label={t('insights.overview.prevMonth', 'Previous month')}
            className="press flex h-10 w-10 flex-none items-center justify-center rounded-full border border-line text-ink2 disabled:opacity-40"
          >
            <CaretLeft size={20} aria-hidden />
          </button>
          <p className="min-w-[10rem] text-center font-serif text-h2 font-medium" aria-live="polite">
            {monthTitle(month)}
          </p>
          <button
            type="button"
            onClick={() => data.nextMonth && onMonth(data.nextMonth)}
            disabled={!data.nextMonth}
            aria-label={t('insights.overview.nextMonth', 'Next month')}
            className="press flex h-10 w-10 flex-none items-center justify-center rounded-full border border-line text-ink2 disabled:opacity-40"
          >
            <CaretRight size={20} aria-hidden />
          </button>
        </div>
        {data.meds.length > 1 && (
          <div
            role="radiogroup"
            aria-label={t('insights.medication.filterLabel', 'Medicine')}
            className="hide-scroll -mx-1 flex w-full flex-nowrap gap-1.5 overflow-x-auto px-1 pb-0.5"
          >
            {[
              { id: 'all', name: t('insights.medication.allMeds', 'All medicines') },
              ...data.meds.map((m) => ({ id: m.id, name: m.name.replace(/\s+\d.*$/, '') })),
            ].map((m) => {
              const on = filter === m.id
              return (
                <button
                  key={m.id}
                  type="button"
                  role="radio"
                  aria-checked={on}
                  onClick={() => onFilter(m.id)}
                  className={cn(
                    'press min-h-9 whitespace-nowrap rounded-chip border-[1.5px] px-3 text-sub',
                    on ? 'border-brand bg-brand font-bold text-on-brand' : 'border-line bg-card text-ink',
                  )}
                >
                  {m.name}
                </button>
              )
            })}
          </div>
        )}
      </div>

      {data.meds.length === 0 ? (
        <p className="text-body text-ink2">{t('insights.medication.noRecordsMonth', 'No doses were recorded in this month.')}</p>
      ) : (
        <>
          <div className="flex flex-col gap-1.5">
            <WeekdayHead names={weekdays()} hideAtLarge />
            <div
              className="grid grid-cols-7 gap-1 sm:gap-2"
              role="group"
              aria-label={t('insights.medication.calendarLabel', 'Doses, {{month}}', { month: monthTitle(month) })}
            >
              {Array.from({ length: lead }, (_, i) => (
                <span key={`lead-${i}`} aria-hidden />
              ))}
              {all.map((date, i) => {
                const n = i + 1
                const k = idx.get(date)
                if (k === undefined)
                  return (
                    <span
                      key={date}
                      aria-hidden
                      className="num flex min-h-14 items-start rounded-[14px] border border-dashed border-line p-1.5 text-micro text-ink3 opacity-60 sm:min-h-[4.6rem] sm:p-2"
                    >
                      {n}
                    </span>
                  )
                const d = dayStatus(shown, k)
                const tone = DAY_TONE[d.kind]
                const on = picked === date
                return (
                  <button
                    key={date}
                    type="button"
                    onClick={() => onPick(date)}
                    aria-pressed={on}
                    aria-current={date === latest ? 'date' : undefined}
                    aria-label={`${date}. ${d.total === 0 ? t('insights.grid.doseNone', 'No dose due') : words(d.kind, d)}`}
                    className={cn(
                      'press flex min-h-14 flex-col justify-between rounded-[14px] border-2 p-1.5 text-left sm:min-h-[4.6rem] sm:p-2',
                      d.total === 0 ? 'border-line bg-card' : cn('border-transparent', tone.box),
                      on && '!border-brand',
                    )}
                  >
                    <span className="flex items-start justify-between gap-1">
                      <span className="num text-micro font-bold leading-none text-ink">{n}</span>
                      {d.kind === 'taken' && <Check size={14} weight="bold" className={tone.text} aria-hidden />}
                      {d.kind === 'missed' && <X size={14} weight="bold" className={tone.text} aria-hidden />}
                      {d.kind === 'unconfirmed' && (
                        <span className={cn('text-micro font-bold leading-none', tone.text)} aria-hidden>
                          ?
                        </span>
                      )}
                    </span>
                    <span className={cn('num hidden truncate text-micro font-bold leading-tight sm:block', tone.text)}>{words(d.kind, d)}</span>
                  </button>
                )
              })}
            </div>
          </div>
          <ul className="flex flex-wrap gap-x-5 gap-y-1.5 text-sub text-ink2" aria-label={t('insights.medication.keyLabel', 'Key')}>
            {(
              [
                ['taken', t('insights.medication.keyTaken', 'All taken')],
                ['missed', t('insights.grid.doseMissed', 'Missed')],
                ['unconfirmed', t('insights.grid.doseUnconfirmed', 'Not confirmed')],
              ] as const
            ).map(([k, label]) => (
              <li key={k} className="flex items-center gap-1.5">
                <span className={cn('h-3 w-3 flex-none rounded-[4px]', DAY_TONE[k].box)} aria-hidden />
                {label}
              </li>
            ))}
            <li className="flex items-center gap-1.5">
              <span className="h-3 w-3 flex-none rounded-[4px] border border-dashed border-ink3" aria-hidden />
              {t('insights.grid.doseNone', 'No dose due')}
            </li>
          </ul>
        </>
      )}
    </div>
  )
}
