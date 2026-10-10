/** C2 — Glucose. Time in range, the usual morning (fasting) level and whether it has drifted, and how steady the day is. From the sensor only. */
import { useTranslation } from 'react-i18next'
import { useInsightsGlucose } from '@/data/hooks'
import type { GlucoseLevel } from '@/data/types'
import { shortDate } from '@/lib/format'
import { useGo } from '@/app/navigation'
import { TirBar } from '@/charts/small'
import { TrendChart } from '@/charts/TrendChart'
import { Split } from '@/ui/layout'
import { Alert, Card, SectionTitle, TextLink } from '@/ui/primitives'
import { Drop } from '@/ui/icons'
import { Findings, Gate, InsightsFrame, Plain, Tile, num, useInsightsDays } from './shared'

const ORDER: GlucoseLevel[] = ['very_low', 'low', 'in_range', 'high', 'very_high']

export function GlucoseTab() {
  const days = useInsightsDays((s) => s.days)
  const { data, isError } = useInsightsGlucose(days)
  const go = useGo()
  const { t } = useTranslation()
  const inRange = data?.bands.find((b) => b.key === 'in_range')?.pct
  const segments = data ? ORDER.map((k) => ({ level: k, pct: data.bands.find((b) => b.key === k)?.pct ?? 0 })) : []
  const end = data ? shortDate(data.period.end) : ''
  return (
    <InsightsFrame tab="C2" period={data?.period}>
      <Gate data={data} isError={isError} empty={!!data && !data.hasData} emptyText={t('insights.glucose.empty', 'There are no sensor readings in this period. Once a glucose sensor is connected, your readings appear here.')}>
        {data && (
          <Split>
            <div className="flex flex-col gap-4">
              <section className="flex flex-col gap-3">
                <SectionTitle>{t('insights.glucose.timeInRange', 'Time in range')}</SectionTitle>
                <Plain why="glucose">
                  {inRange != null ? t('insights.glucose.inRange', '{{pct}}% of your readings were between {{low}} and {{high}} mmol/L.', { pct: Math.round(inRange), low: data.low, high: data.high }) : ''}
                </Plain>
                <Card tone="hero">
                  <TirBar segments={segments} />
                </Card>
                <div className="grid grid-cols-2 gap-2">
                  <Tile label={t('insights.glucose.average', 'Average')} value={num(data.metrics.mean, 1)} unit="mmol/L" />
                  <Tile
                    label={t('insights.glucose.gmi', 'Estimated A1c (GMI)')}
                    value={data.metrics.gmi != null ? `${num(data.metrics.gmi, 1)}%` : '–'}
                    sub={t('insights.glucose.gmiSub', 'Worked out from your average')}
                  />
                  <Tile label={t('insights.glucose.cv', 'Ups and downs (CV)')} value={data.metrics.cv != null ? `${num(data.metrics.cv)}%` : '–'} sub={t('insights.glucose.cvSub', 'Lower is steadier')} />
                  <Tile label={t('insights.glucose.worn', 'Sensor worn')} value={data.metrics.coverage != null ? `${num(data.metrics.coverage)}%` : '–'} sub={t('insights.glucose.wornSub', 'of this period')} />
                </div>
              </section>
              <Card tone="soft" className="flex flex-col gap-1">
                <p className="text-body font-bold">{t('insights.glucose.inThisPeriod', 'In this period')}</p>
                <p className="text-body text-ink2">
                  {t('insights.glucose.events', '{{spikes}} sharp rises, {{sustained}} long stretches above range, {{lows}} low readings.', {
                    spikes: data.events.spikes,
                    sustained: data.events.sustainedHigh,
                    lows: data.events.lows,
                  })}
                </p>
              </Card>
              <TextLink icon={Drop} onClick={() => go('C8')}>
                {t('insights.glucose.seeSensor', 'See your latest 14 days of sensor data')}
              </TextLink>
            </div>
            <div className="flex flex-col gap-4">
              <section className="flex flex-col gap-3">
                <SectionTitle>{t('insights.glucose.fastingTitle', 'Morning (fasting) glucose')}</SectionTitle>
                <Plain why="glucose">
                  {data.baseline
                    ? t('insights.glucose.fastingPlainBand', 'The average of your readings between 5 and 7 am each day. The shaded band is your usual range from the 60 days before.')
                    : t('insights.glucose.fastingPlain', 'The average of your readings between 5 and 7 am each day.')}
                </Plain>
                {data.drift && (
                  <Alert tone="info">
                    {data.drift.text} {t('insights.glucose.worthDoctor', 'Worth mentioning to your doctor.')}
                  </Alert>
                )}
                <Card tone="hero">
                  <TrendChart
                    label={t('insights.glucose.fastingChart', 'Morning fasting glucose by day, mmol/L')}
                    points={data.days.map((d) => ({ date: d.date, v: d.fasting }))}
                    baseline={data.baseline ? [data.baseline.p25, data.baseline.p75] : undefined}
                    endLabel={end}
                    drawKey={`fasting-${days}`}
                  />
                </Card>
              </section>
              <section className="flex flex-col gap-3">
                <SectionTitle>{t('insights.glucose.avgEachDay', 'Average each day')}</SectionTitle>
                <Card tone="hero">
                  <TrendChart
                    label={t('insights.glucose.avgChart', 'Average glucose by day, mmol/L')}
                    points={data.days.map((d) => ({ date: d.date, v: d.mean }))}
                    endLabel={end}
                    color="var(--c-s2)"
                    drawKey={`mean-${days}`}
                  />
                </Card>
              </section>
              <Findings items={data.patterns} />
            </div>
          </Split>
        )}
      </Gate>
    </InsightsFrame>
  )
}
