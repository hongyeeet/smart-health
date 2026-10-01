import { useNavigate, useParams } from 'react-router-dom'
import { useDay, useDayList } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { href } from '@/app/routeIds'
import { DayChart } from '@/charts/DayChart'
import { Header, Screen } from '@/ui/layout'
import { Card, Skeleton, StatusPill, TextLink } from '@/ui/primitives'
import { CaretLeft, CaretRight } from '@/ui/icons'
import { appConfig } from '@/config/app'

export function DayView() {
  const { date = appConfig.demo.today } = useParams()
  const { data: day } = useDay(date)
  const { data: list } = useDayList()
  const navigate = useNavigate()
  const go = useGo()
  const openSheet = useUi((s) => s.openSheet)
  const idx = list?.findIndex((d) => d.date === date) ?? -1
  const prev = list && idx > 0 ? list[idx - 1] : null
  const next = list && idx >= 0 && idx < list.length - 1 ? list[idx + 1] : null
  const step = (d: string | undefined) => d && navigate(href('D1', { date: d }), { replace: true })

  return (
    <Screen tabs>
      <Header title={day ? (date === appConfig.demo.today ? 'Today' : day.weekday) : 'Your day'} sub={day ? `${day.weekday} ${day.label}` : undefined} back backTo="C1" />
      <div className="flex items-center justify-between gap-2" role="group" aria-label="Choose a day">
        <button type="button" disabled={!prev} onClick={() => step(prev?.date)} aria-label="Previous day" className="press flex min-h-12 min-w-12 items-center justify-center rounded-full border border-line bg-card disabled:opacity-35">
          <CaretLeft size={22} aria-hidden />
        </button>
        <span className="text-body font-bold">{day ? `${day.weekday} ${day.label}` : ''}</span>
        <button type="button" disabled={!next} onClick={() => step(next?.date)} aria-label="Next day" className="press flex min-h-12 min-w-12 items-center justify-center rounded-full border border-line bg-card disabled:opacity-35">
          <CaretRight size={22} aria-hidden />
        </button>
      </div>
      {!day ? (
        <Skeleton className="h-96" />
      ) : (
        <>
          <Card className="flex flex-col gap-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-body">
                <span className="num text-xl">{day.inRangePct}%</span> in range
              </span>
              {day.glucoseGaps.length > 0 && <StatusPill tone="neutral">Sensor gap</StatusPill>}
            </div>
            <p className="text-sub text-ink2">Glucose (mmol/L). Your range is 3.9 to 10.0. Tap a marker for the details.</p>
            <DayChart day={day} onPick={(pick) => openSheet('D2', { pick, dayLabel: `${day.weekday} ${day.label}` })} />
          </Card>
          <div className="flex flex-col items-start">
            <TextLink onClick={() => go('C1')}>Back to your week</TextLink>
            <TextLink onClick={() => go('C2')}>Glucose insights</TextLink>
          </div>
        </>
      )}
    </Screen>
  )
}
