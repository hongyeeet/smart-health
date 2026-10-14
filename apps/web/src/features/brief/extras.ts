/** The extra sections of the printed brief and of the shared link, built in code from the same numbers: health tiles, a reasoning line per chart, what the app learnt, the next visit. */
import type { TFunction } from 'i18next'
import type { InsightsTimeline } from '@/data/types'
import type { ReportExtra } from './ReportView'
import type { ChartFilter } from './PrintCharts'
import { healthTiles, plotReasons } from './analysis'
import { APPOINTMENT_KIND, formatWhen } from './shareApi'

export function buildExtra(
  t: TFunction,
  timeline: InsightsTimeline,
  learned: { statement: string; why: string; confirmed: boolean }[] | undefined,
  appointment: { kind: string; scheduledFor: string; location: string | null } | null | undefined,
  show?: Record<ChartFilter, boolean>,
): ReportExtra {
  return {
    tiles: healthTiles(t, timeline).map((x) => ({ label: x.label, value: x.value, unit: x.unit, status: x.status })),
    timeline,
    show,
    reasons: plotReasons(t, timeline).map((x) => ({ title: x.title, why: x.why, saw: x.saw })),
    learned: learned ? [...learned].sort((a, b) => Number(b.confirmed) - Number(a.confirmed)) : undefined,
    appointment:
      appointment === undefined
        ? undefined
        : appointment
          ? { kind: APPOINTMENT_KIND[appointment.kind] ?? appointment.kind, when: formatWhen(appointment.scheduledFor), location: appointment.location }
          : null,
  }
}
