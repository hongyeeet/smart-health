/** C2 — Glucose. Time in range, the four headline numbers against the person's own baseline, the glucose by day (average, morning, highest), the usual morning level, the hour-of-day pattern and the findings from the history. From the sensor only. */
import { useTranslation } from 'react-i18next'
import { useDoctorReport, useInsightsGlucose, useInsightsTimeline } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { TextLink } from '@/ui/primitives'
import { Drop } from '@/ui/icons'
import { Gate, InsightsFrame, num, useInsightsDays } from './shared'
import { ByDayCard } from './glucose/ByDayCard'
import { StatTiles, TimeInRange } from './glucose/StatTiles'
import { HistoryCard, HourCard, MorningCard } from './glucose/SideCards'

export function GlucoseTab() {
  const days = useInsightsDays((s) => s.days)
  const { data, isError } = useInsightsGlucose(days)
  const timeline = useInsightsTimeline(days).data
  const report = useDoctorReport(days).data
  const go = useGo()
  const { t } = useTranslation()
  const veryHigh = report?.glucose.veryHigh ?? null
  const events = [
    { n: data?.events.spikes, label: t('insights.glucose.sharpRises', 'sharp rises'), tone: 'text-warn' },
    { n: data?.events.sustainedHigh, label: t('insights.glucose.longStretches', 'long stretches above range'), tone: 'text-brass' },
    { n: data?.events.lows, label: t('insights.glucose.lowReadings', 'low readings'), tone: 'text-danger' },
  ]
  return (
    <InsightsFrame tab="C2" period={data?.period} why="glucose">
      <Gate
        data={data}
        isError={isError}
        empty={!!data && !data.hasData}
        emptyText={t('insights.glucose.empty', 'There are no sensor readings in this period. Once a glucose sensor is connected, your readings appear here.')}
      >
        {data && (
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_332px] lg:items-start lg:gap-6">
            <div className="flex min-w-0 flex-col gap-4">
              <StatTiles metrics={data.metrics} timeline={timeline} />
              <TimeInRange bands={data.bands} low={data.low} high={data.high} />
              <ByDayCard
                days={data.days}
                dayRows={timeline?.dayRows}
                morning={data.baseline ? { p25: data.baseline.p25, p75: data.baseline.p75 } : null}
                baselineMean={timeline?.baseline.daily.glucose.mean ?? null}
                baselineDays={timeline?.baseline.days ?? null}
                low={data.low}
                high={data.high}
                veryHigh={veryHigh}
              />
              <div className="grid gap-3 sm:grid-cols-3">
                {events.map((e) => (
                  <div key={e.label} className="flex min-w-0 items-center gap-3 rounded-card border border-line bg-card px-4 py-3.5 shadow-lift">
                    <span className={`num whitespace-nowrap text-[28px] font-bold leading-none ${e.tone}`}>{num(e.n)}</span>
                    <span className="min-w-0 text-[14px] leading-[18px] text-ink2">{e.label}</span>
                  </div>
                ))}
              </div>
              <TextLink icon={Drop} onClick={() => go('C8')}>
                {t('insights.glucose.seeSensor', 'See your latest 14 days of sensor data')}
              </TextLink>
            </div>
            <div className="flex min-w-0 flex-col gap-4">
              <MorningCard days={data.days} morning={data.baseline ? { p25: data.baseline.p25, p75: data.baseline.p75 } : null} drift={data.drift} />
              <HourCard profile={report?.glucose.profile} high={data.high} />
              <HistoryCard patterns={data.patterns} />
            </div>
          </div>
        )}
      </Gate>
    </InsightsFrame>
  )
}
