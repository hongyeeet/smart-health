import { useParams, Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useGo } from '@/app/navigation'
import { href } from '@/app/routeIds'
import { Screen, Header } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, ListRow, SectionTitle, Skeleton, TextLink } from '@/ui/primitives'
import { CalendarBlank, CaretLeft, CaretRight, ChartLineUp } from '@/ui/icons'
import { useDay, useDayDates, type DayMarker, type DayView } from './api'
import { DayTimeline } from './DayTimeline'
import { dayLabel, doseWords, glucoseSummary, loggedSummary } from './dayMath'

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/

/** D1, "Your day": one day on one clock, opened from Insights, Home and Log. */
export function Day() {
  const { date = '' } = useParams()
  const go = useGo()
  const { t } = useTranslation()
  const dates = useDayDates(90)
  const day = useDay(date)

  // Opening the day with no date (the default) goes to the latest day with data, the same rule as Insights.
  if (!date && dates.data) return <Navigate to={href('D1', { date: dates.data.latestDate })} replace />

  const valid = DATE_RE.test(date)
  const latest = dates.data?.latestDate
  const pick = (m: DayMarker) => go('D2', { sheet: { marker: m } })

  return (
    <Screen>
      <Header back backTo="C1" title={t('day.title', 'Your day')} />

      {valid && <DateNav date={date} data={day.data} onMove={(d) => go('D1', { params: { date: d } })} />}

      {!valid && (
        <EmptyState
          icon={CalendarBlank}
          action={
            latest && (
              <Button variant="secondary" onClick={() => go('D1', { params: { date: latest }, replace: true })}>
                {t('day.seeLatest', 'See your latest day')}
              </Button>
            )
          }
        >
          {t('day.badDate', 'That is not a date we can open.')}
        </EmptyState>
      )}

      {valid && day.isPending && <Skeleton className="h-80" />}
      {valid && day.isError && (
        <Alert tone="warn" title={t('day.loadErrorTitle', 'This day did not load')}>
          {t('day.loadErrorBody', 'Check the connection and try again.')}
        </Alert>
      )}

      {day.data && !day.data.hasData && (
        <EmptyState icon={CalendarBlank} action={<DayLinks data={day.data} onMove={(d) => go('D1', { params: { date: d } })} />}>
          {t('day.empty', 'Nothing is recorded for this day. Glucose, meals, medicines and workouts show here once they are logged.')}
        </EmptyState>
      )}

      {day.data?.hasData && <DayBody day={day.data} onPick={pick} onGo={go} />}
    </Screen>
  )
}

function DayBody({ day, onPick, onGo }: { day: DayView; onPick: (m: DayMarker) => void; onGo: ReturnType<typeof useGo> }) {
  const { t } = useTranslation()
  const glucose = glucoseSummary(
    day.series.map((p) => p.glucoseMmol),
    day.targetLow,
    day.targetHigh,
  )
  // a laptop gets the timeline wide on the left, and the summary and the list beside it
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start lg:gap-6 [&>*]:min-w-0">
      <Card tone="hero" as="section">
        <DayTimeline day={day} onPick={onPick} />
      </Card>

      <div className="flex flex-col gap-4">
      <Card as="section">
        <ul className="flex flex-col gap-2 text-body text-ink2">
          <li>{glucose ?? t('day.noGlucose', 'No glucose readings for this day.')}</li>
          <li>
            {day.sleepHours != null
              ? t('day.slept', 'Slept about {{h}} hours.', { h: day.sleepHours.toFixed(1) })
              : t('day.noSleep', 'No sleep total for this day.')}
          </li>
          <li>{t('day.loggedLine', 'Logged: {{summary}}.',{ summary: loggedSummary(day.markers) })}</li>
        </ul>
        <p className="mt-3 text-sub text-ink3">{t('day.bandNote', 'The shaded band is your target range, set in your profile.')}</p>
      </Card>

      <section className="flex flex-col gap-2">
        <SectionTitle>{t('day.everything', 'Everything logged')}</SectionTitle>
        {day.markers.length === 0 && <p className="text-body text-ink2">{t('day.nothingLogged', 'Nothing logged for this day.')}</p>}
        {day.markers.map((m) => (
          <ListRow
            key={m.id}
            title={`${m.clock}  ${m.title}`}
            sub={m.kind === 'dose' && m.status ? doseWords(m.status) : m.subtitle ?? undefined}
            onClick={() => onPick(m)}
            trailing={<CaretRight size={20} className="text-ink3" aria-hidden />}
          />
        ))}
      </section>

      <div className="flex flex-wrap gap-4">
        <TextLink icon={ChartLineUp} onClick={() => onGo('C2')}>
          {t('day.glucoseInsights', 'Glucose insights')}
        </TextLink>
      </div>
      </div>
    </div>
  )
}

function DateNav({ date, data, onMove }: { date: string; data: DayView | undefined; onMove: (d: string) => void }) {
  const { t } = useTranslation()
  const prev = data?.prevDate ?? null
  const next = data?.nextDate ?? null
  const arrow = 'press flex h-12 w-12 flex-none items-center justify-center rounded-full text-brand hover:bg-brand-soft disabled:opacity-35 disabled:pointer-events-none'
  return (
    <nav aria-label={t('day.moveAria', 'Move between days with data')} className="flex items-center justify-between gap-2">
      <button
        type="button"
        className={arrow}
        disabled={!prev}
        onClick={() => prev && onMove(prev)}
        aria-label={prev ? t('day.prevAria', 'Previous day with data, {{day}}', { day: dayLabel(prev) }) : t('day.noPrev', 'No earlier day with data')}
      >
        <CaretLeft size={24} aria-hidden />
      </button>
      <p className="min-w-0 text-center text-body font-bold text-ink" aria-live="polite">
        {dayLabel(date)}
      </p>
      <button
        type="button"
        className={arrow}
        disabled={!next}
        onClick={() => next && onMove(next)}
        aria-label={next ? t('day.nextAria', 'Next day with data, {{day}}', { day: dayLabel(next) }) : t('day.noNext', 'No later day with data')}
      >
        <CaretRight size={24} aria-hidden />
      </button>
    </nav>
  )
}

function DayLinks({ data, onMove }: { data: DayView; onMove: (d: string) => void }) {
  const { t } = useTranslation()
  return (
    <div className="flex w-full flex-col gap-2">
      {data.prevDate && (
        <Button variant="secondary" onClick={() => onMove(data.prevDate!)}>
          {t('day.goTo', 'Go to {{day}}', { day: dayLabel(data.prevDate) })}
        </Button>
      )}
      {data.nextDate && (
        <Button variant="secondary" onClick={() => onMove(data.nextDate!)}>
          {t('day.goTo', 'Go to {{day}}', { day: dayLabel(data.nextDate) })}
        </Button>
      )}
    </div>
  )
}
