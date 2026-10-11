/**
 * K10 calendar: one cell per Singapore day for a month, coloured by how many calories were logged. Previous months are reachable
 * with the arrows; future days are not. Tapping a day shows its totals and meals below. Unknown or no meals is an empty cell with a dash.
 */
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useDietDays } from '@/data/hooks'
import type { DietDay } from '@/data/types'
import { cn } from '@/lib/cn'
import { shortDate } from '@/lib/format'
import { CaretLeft, CaretRight } from '@/ui/icons'
import { Alert, Card, SectionTitle, Skeleton } from '@/ui/primitives'
import { CAL, WeekdayHead } from '@/features/insights/grids'
import { DayPanel } from './DayPanel'
import { KCAL_STEPS, addMonths, compareMonths, isoDays, leadingBlanks, levelOf, monthLabel, monthOf, monthRange, sgToday, weekdayHeaders, type Month } from './calendarMath'

/** The same heat steps as the insights grids: the share of the brand colour, and the number is always written elsewhere. */
const SHADE = [18, 38, 62, 92] as const
const shade = (level: number) => `color-mix(in oklab, var(--c-brand) ${SHADE[level - 1]}%, var(--c-card))`

export function DietCalendar() {
  const { t } = useTranslation()
  const today = useMemo(() => sgToday(), [])
  const current = useMemo(() => monthOf(today), [today])
  const [shown, setShown] = useState<Month>(current)
  const [picked, setPicked] = useState<string | null>(null)
  const range = monthRange(shown)
  const { data, isError } = useDietDays(range.start, range.end)
  const byDate = useMemo(() => new Map((data?.days ?? []).map((d) => [d.date, d])), [data])
  const weekdays = useMemo(() => weekdayHeaders(), [])
  const label = monthLabel(shown)
  const canGoForward = compareMonths(shown, current) < 0
  const monthEmpty = !!data && data.days.every((d) => d.meals === 0)

  const go = (n: number) => {
    setShown((m) => addMonths(m, n))
    setPicked(null)
  }

  const cellLabel = (iso: string, day: DietDay | undefined) => {
    const when = shortDate(iso)
    if (!day || day.meals === 0) return t('me.diet.cellNone', '{{date}}: nothing logged', { date: when })
    if (day.totals.kcal == null) return t('me.diet.cellUnknown', '{{date}}: {{n}} meals, calories not known', { date: when, n: day.meals })
    return t('me.diet.cellValue', '{{date}}: {{kcal}} kcal from {{n}} meals', {
      date: when,
      kcal: day.totals.kcal.toLocaleString('en-US'),
      n: day.meals,
    })
  }

  return (
    <Card as="section" className="flex flex-col gap-3 !px-3 sm:!px-4">
      <SectionTitle>{t('me.diet.calendarTitle', 'Each day')}</SectionTitle>
      <div className="grid gap-4 md:grid-cols-2 md:items-start md:gap-6 [&>*]:min-w-0">
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={() => go(-1)}
              aria-label={t('me.diet.prevMonth', 'Previous month')}
              className="press flex h-12 w-12 items-center justify-center rounded-field border border-line bg-card text-ink"
            >
              <CaretLeft size={22} aria-hidden />
            </button>
            <h3 className="min-w-0 text-center text-body font-bold" aria-live="polite">
              {label}
            </h3>
            <button
              type="button"
              onClick={() => go(1)}
              disabled={!canGoForward}
              aria-label={t('me.diet.nextMonth', 'Next month')}
              className="press flex h-12 w-12 items-center justify-center rounded-field border border-line bg-card text-ink disabled:opacity-40 disabled:pointer-events-none"
            >
              <CaretRight size={22} aria-hidden />
            </button>
          </div>

          {isError && <Alert tone="warn">{t('me.diet.loadError', 'We could not load this month just now.')}</Alert>}
          {!data && !isError && <Skeleton className="h-64" />}

          {data && (
            <>
              <WeekdayHead names={weekdays} />
              <div className={CAL.grid} role="group" aria-label={label}>
                {Array.from({ length: leadingBlanks(shown) }, (_, i) => (
                  <span key={`blank-${i}`} aria-hidden />
                ))}
                {isoDays(shown).map((iso) => {
                  const day = byDate.get(iso)
                  const lvl = levelOf(day)
                  const future = iso > today
                  const selected = picked === iso
                  if (future)
                    return (
                      <span key={iso} aria-hidden className={CAL.future}>
                        {Number(iso.slice(8))}
                      </span>
                    )
                  return (
                    <button
                      type="button"
                      key={iso}
                      aria-pressed={selected}
                      aria-label={cellLabel(iso, day)}
                      aria-current={iso === today ? 'date' : undefined}
                      onClick={() => setPicked(iso)}
                      style={lvl > 0 ? { background: shade(lvl) } : undefined}
                      className={cn(
                        CAL.cell,
                        'font-bold',
                        lvl === 0 ? 'bg-well text-ink3' : lvl >= 3 ? 'text-on-brand' : 'text-ink',
                        selected ? 'border-brand ring-2 ring-brand/40' : iso === today ? 'border-brand' : 'border-transparent',
                      )}
                    >
                      <span className="num text-sub">{Number(iso.slice(8))}</span>
                      {lvl === 0 && (
                        <span className="text-micro font-normal [[data-ts='2']_&]:hidden" aria-hidden>
                          –
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>

              <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-micro text-ink2" aria-label={t('me.diet.legend', 'Colour key')}>
                <li className="flex items-center gap-1.5">
                  <span className="h-4 w-4 rounded-[4px] bg-well" aria-hidden />
                  {t('me.diet.legendNone', 'No meals, or not known')}
                </li>
                {KCAL_STEPS.map((_, i) => (
                  <li key={i} className="flex items-center gap-1.5">
                    <span className="h-4 w-4 rounded-[4px]" style={{ background: shade(i + 1) }} aria-hidden />
                    {i === 0 &&
                      t('me.diet.stepLow', 'Under {{n}} kcal', {
                        n: KCAL_STEPS[0].toLocaleString('en-US'),
                      })}
                    {i === 1 &&
                      t('me.diet.stepMid', '{{from}} to {{to}} kcal', {
                        from: KCAL_STEPS[0].toLocaleString('en-US'),
                        to: (KCAL_STEPS[1] - 1).toLocaleString('en-US'),
                      })}
                    {i === 2 &&
                      t('me.diet.stepHigh', '{{from}} to {{to}} kcal', {
                        from: KCAL_STEPS[1].toLocaleString('en-US'),
                        to: (KCAL_STEPS[2] - 1).toLocaleString('en-US'),
                      })}
                  </li>
                ))}
                <li className="flex items-center gap-1.5">
                  <span className="h-4 w-4 rounded-[4px]" style={{ background: shade(4) }} aria-hidden />
                  {t('me.diet.stepTop', '{{n}} kcal or more', {
                    n: KCAL_STEPS[2].toLocaleString('en-US'),
                  })}
                </li>
              </ul>
            </>
          )}
        </div>
        {data && (
          <div className="flex flex-col gap-3">
            {monthEmpty && <p className="text-body text-ink2">{t('me.diet.monthEmpty', 'Nothing logged in this month yet. Meals you log show here, day by day.')}</p>}
            <DayPanel iso={picked} day={picked ? byDate.get(picked) : undefined} />
          </div>
        )}
      </div>
    </Card>
  )
}
