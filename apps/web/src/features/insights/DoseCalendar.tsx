/**
 * The Medication tab's month calendar (C6): one square per day, and in each day a small marker for every regular medicine, always in the same
 * order. A marker's fill and pattern say what happened (taken, taken late, not confirmed, missed, no dose due), the same as the key, so it reads
 * without colour. The letters on a marker (from a laptop up) say which medicine it is; a key above lists them. Tap a day for the words.
 * A day with no record for a medicine is "no dose due", never "missed". Days after the latest day with data are dashed and empty.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { InsightsMedication } from '@/data/types'
import { cn } from '@/lib/cn'
import { shortDate } from '@/lib/format'
import { CaretLeft, CaretRight } from '@/ui/icons'
import { DOSE_CLS, DOSE_LEGEND, WeekdayHead, monthRange, monthTitle, useDoseLabels } from './grids'

type Med = InsightsMedication['meds'][number]

/** The shortest start of each name (1 to 3 letters) that no other medicine shares, so a marker can say which medicine it is. */
function shortNames(meds: Med[]): string[] {
  return meds.map((m, i) => {
    for (let n = 1; n <= 3; n++) {
      const s = m.name.slice(0, n)
      if (meds.every((o, j) => j === i || o.name.slice(0, n).toLowerCase() !== s.toLowerCase())) return s
    }
    return m.name.slice(0, 3)
  })
}

const weekdays = () => {
  const fmt = new Intl.DateTimeFormat('en-GB', { weekday: 'short', timeZone: 'UTC' })
  return Array.from({ length: 7 }, (_, i) => fmt.format(new Date(Date.UTC(2026, 0, 5 + i))))
}

export function DoseCalendar({ data, onMonth }: { data: InsightsMedication; onMonth: (m: string) => void }) {
  const { t } = useTranslation()
  const labels = useDoseLabels()
  const [picked, setPicked] = useState<string | null>(null)
  const month = data.month ?? data.period.start.slice(0, 7)
  const { end } = monthRange(month)
  const lastDay = Number(end.slice(8))
  const lead = (new Date(Date.UTC(Number(month.slice(0, 4)), Number(month.slice(5, 7)) - 1, 1)).getUTCDay() + 6) % 7
  const idx = new Map(data.dates.map((d, i) => [d, i]))
  const short = shortNames(data.meds)
  const latest = data.dates[data.dates.length - 1] ?? ''
  const all = Array.from({ length: lastDay }, (_, i) => `${month}-${String(i + 1).padStart(2, '0')}`)
  const dayWords = (date: string) =>
    data.meds
      .map((m) => `${m.name}: ${labels[m.cells[idx.get(date)!]!]}`)
      .join('. ')

  const marker = (m: Med, i: number, date: string, big: boolean) => {
    const c = m.cells[idx.get(date)!]!
    return (
      <span
        key={m.id}
        aria-hidden
        className={cn(
          'num flex flex-none items-center justify-center rounded-[3px] border font-bold leading-none',
          big ? 'h-[1.125rem] min-w-[1.5rem] px-0.5 text-micro' : 'h-2.5 w-2.5',
          DOSE_CLS[c],
          !m.counted && 'opacity-80',
        )}
      >
        {big && <span className={cn(c === 'missed' || c === 'unconfirmed' ? 'rounded-[2px] bg-card/85 px-px text-ink' : '')}>{short[i]}</span>}
      </span>
    )
  }

  const picks = picked && idx.has(picked) ? picked : null

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => data.prevMonth && onMonth(data.prevMonth)}
          disabled={!data.prevMonth}
          aria-label={t('insights.overview.prevMonth', 'Previous month')}
          className="press flex min-h-12 min-w-12 items-center justify-center rounded-chip text-ink2 disabled:opacity-40"
        >
          <CaretLeft size={24} aria-hidden />
        </button>
        <p className="text-center font-serif text-h2 font-medium" aria-live="polite">
          {monthTitle(month)}
        </p>
        <button
          type="button"
          onClick={() => data.nextMonth && onMonth(data.nextMonth)}
          disabled={!data.nextMonth}
          aria-label={t('insights.overview.nextMonth', 'Next month')}
          className="press flex min-h-12 min-w-12 items-center justify-center rounded-chip text-ink2 disabled:opacity-40"
        >
          <CaretRight size={24} aria-hidden />
        </button>
      </div>

      {data.meds.length === 0 ? (
        <p className="text-body text-ink2">{t('insights.medication.noRecordsMonth', 'No doses were recorded in this month.')}</p>
      ) : (
        <>
          <div>
            <p className="mb-1 text-sub font-bold text-ink2">{t('insights.medication.markerKey', 'Each day shows one marker per medicine, in this order:')}</p>
            <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sub text-ink2">
              {data.meds.map((m, i) => (
                <li key={m.id} className="flex items-center gap-1.5">
                  <span className="num flex h-[1.125rem] min-w-[1.5rem] items-center justify-center rounded-[3px] border border-line bg-well px-0.5 text-micro font-bold text-ink" aria-hidden>
                    {short[i]}
                  </span>
                  <span>
                    {m.name}
                    {!m.counted && <span className="text-ink3"> ({t('insights.grid.notCounted', 'Not counted in adherence')})</span>}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="flex flex-col gap-1.5">
            <WeekdayHead names={weekdays()} hideAtLarge />
            <div className={cn('grid grid-cols-7 gap-0.5 sm:gap-1.5', "[[data-ts='2']_&]:hidden")} role="group" aria-label={t('insights.medication.calendarLabel', 'Doses, {{month}}', { month: monthTitle(month) })}>
              {Array.from({ length: lead }, (_, i) => (
                <span key={`lead-${i}`} aria-hidden />
              ))}
              {all.map((date, i) => {
                const n = i + 1
                if (!idx.has(date))
                  return (
                    <span key={date} aria-hidden className="flex min-h-14 items-start rounded-field border border-dashed border-line p-1 text-micro text-ink3 opacity-60 sm:min-h-16 sm:p-1.5">
                      {n}
                    </span>
                  )
                const on = picks === date
                return (
                  <button
                    key={date}
                    type="button"
                    onClick={() => setPicked(on ? null : date)}
                    aria-pressed={on}
                    aria-label={t('insights.medication.dayAria', '{{date}}. {{words}}', { date: shortDate(date), words: dayWords(date) })}
                    aria-current={date === latest ? 'date' : undefined}
                    className={cn('press flex min-h-14 flex-col items-start gap-1 rounded-field border-2 bg-card p-1 text-left sm:min-h-16 sm:p-1.5', on ? 'border-brand' : 'border-line')}
                  >
                    <span className="num text-micro leading-none text-ink2">{n}</span>
                    <span className="flex flex-wrap gap-0.5 sm:hidden">{data.meds.map((m, k) => marker(m, k, date, false))}</span>
                    <span className="hidden flex-wrap gap-0.5 sm:flex">{data.meds.map((m, k) => marker(m, k, date, true))}</span>
                  </button>
                )
              })}
            </div>

            {/* at large text seven columns cannot hold the markers, so the month is a list of its days so far, newest first */}
            <ul className="hidden flex-col gap-1.5 [[data-ts='2']_&]:flex" aria-label={t('insights.medication.calendarLabel', 'Doses, {{month}}', { month: monthTitle(month) })}>
              {[...data.dates].reverse().map((date) => (
                <li key={date}>
                  <button
                    type="button"
                    onClick={() => setPicked(picks === date ? null : date)}
                    aria-pressed={picks === date}
                    className={cn('press flex min-h-14 w-full flex-col items-start gap-1 rounded-field border-2 bg-card px-3 py-2 text-left', picks === date ? 'border-brand' : 'border-line')}
                  >
                    <span className="text-sub font-bold">{shortDate(date)}</span>
                    <span className="flex flex-wrap gap-1" aria-hidden>
                      {data.meds.map((m, k) => marker(m, k, date, true))}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <div className="min-h-12 rounded-card bg-well px-3 py-2" aria-live="polite">
            {picks ? (
              <>
                <p className="mb-1 text-sub font-bold text-ink">{shortDate(picks)}</p>
                <ul className="flex flex-col gap-1 text-body">
                  {data.meds.map((m) => {
                    const c = m.cells[idx.get(picks)!]!
                    return (
                      <li key={m.id} className="flex flex-wrap items-center justify-between gap-x-3">
                        <span>{m.name}</span>
                        <span className="flex items-center gap-1.5 text-ink2">
                          <span className={cn('h-3.5 w-3.5 flex-none rounded-[3px] border', DOSE_CLS[c])} aria-hidden />
                          {labels[c]}
                        </span>
                      </li>
                    )
                  })}
                </ul>
              </>
            ) : (
              <p className="text-sub text-ink2">{t('insights.medication.tapDay', 'Tap a day to see each medicine in words.')}</p>
            )}
          </div>

          <ul aria-label={t('insights.grid.legend', 'Key')} className="grid grid-cols-2 gap-x-4 gap-y-2 text-sub text-ink2 sm:flex sm:flex-wrap [[data-ts='2']_&]:grid-cols-1">
            {DOSE_LEGEND.map((k) => (
              <li key={k} className="flex items-center gap-2">
                <span className={cn('h-5 w-5 flex-none rounded-[4px] border', DOSE_CLS[k])} aria-hidden />
                {labels[k]}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
