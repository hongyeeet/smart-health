/**
 * C6 — Medication. Four numbers for the month on screen, a calendar where each day says whether anything was missed (and a medicine filter), the
 * list of missed or unconfirmed doses, and a panel with the day you tapped: each medicine and what happened. Then why doses were missed and what the
 * person's history shows. There is no 7, 30 or 90 day choice: the person browses month by month.
 */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useInsightsMedication } from '@/data/hooks'
import type { InsightsDoseCell, InsightsMedication } from '@/data/types'
import { useGo } from '@/app/navigation'
import { cn } from '@/lib/cn'
import { shortDate } from '@/lib/format'
import { Card, TextLink } from '@/ui/primitives'
import { Check, Pill, X } from '@/ui/icons'
import { Findings, Gate, InsightsFrame } from './shared'
import { DAY_TONE, DoseCalendar } from './DoseCalendar'
import { monthTitle } from './grids'

type Tone = 'ok' | 'brass' | 'warn' | 'danger' | 'neutral'
const TILE: Record<Tone, string> = {
  ok: 'bg-ok-soft text-ok',
  brass: 'bg-brass-soft text-brass',
  warn: 'bg-warn-soft text-warn',
  danger: 'bg-danger-soft text-danger',
  neutral: 'bg-well text-ink2',
}

/** The share of prescription doses taken, as a colour: the same cut-offs as the Health overview (placeholders until the clinical owner confirms them). */
function pctTone(pct: number | null): Tone {
  if (pct == null) return 'neutral'
  const miss = 100 - pct
  return miss <= 10 ? 'ok' : miss <= 20 ? 'brass' : miss <= 40 ? 'warn' : 'danger'
}

function Tile({ label, value, unit, status, tone }: { label: string; value: string; unit?: string; status: string; tone: Tone }) {
  return (
    <div className={cn('flex min-h-[5.4rem] min-w-0 flex-col justify-center gap-px rounded-[12px] px-3 py-2', TILE[tone])}>
      <span className="truncate text-micro text-ink2">{label}</span>
      <span className="num flex items-baseline gap-1 text-h2 font-bold leading-tight">
        {value}
        {unit && <span className="text-micro font-normal text-ink3">{unit}</span>}
      </span>
      <span className="flex items-center gap-1.5 text-micro font-bold leading-tight">
        <span className="h-1.5 w-1.5 flex-none rounded-full bg-current" aria-hidden />
        <span className="min-w-0 truncate">{status}</span>
      </span>
    </div>
  )
}

const CELL_ICON: Record<InsightsDoseCell, { tone: keyof typeof DAY_TONE; icon: 'check' | 'x' | 'q' | null }> = {
  taken: { tone: 'taken', icon: 'check' },
  late: { tone: 'taken', icon: 'check' },
  missed: { tone: 'missed', icon: 'x' },
  unconfirmed: { tone: 'unconfirmed', icon: 'q' },
  none: { tone: 'none', icon: null },
}

function StatusDot({ cell }: { cell: InsightsDoseCell }) {
  const c = CELL_ICON[cell]
  return (
    <span className={cn('flex h-7 w-7 flex-none items-center justify-center rounded-full', DAY_TONE[c.tone].box, DAY_TONE[c.tone].text)} aria-hidden>
      {c.icon === 'check' && <Check size={15} weight="bold" />}
      {c.icon === 'x' && <X size={15} weight="bold" />}
      {c.icon === 'q' && <span className="text-sub font-bold leading-none">?</span>}
      {c.icon === null && <span className="h-1.5 w-1.5 rounded-full bg-current opacity-50" />}
    </span>
  )
}

export function MedicationTab() {
  const [month, setMonth] = useState<string | undefined>(undefined)
  const { data, isError } = useInsightsMedication(month)
  const [filter, setFilter] = useState('all')
  const [picked, setPicked] = useState<string | null>(null)
  const [more, setMore] = useState(false)
  const go = useGo()
  const { t } = useTranslation()
  const labels: Record<InsightsDoseCell, string> = {
    taken: t('insights.grid.doseTaken', 'Taken'),
    late: t('insights.grid.doseLate', 'Taken late'),
    unconfirmed: t('insights.grid.doseUnconfirmed', 'Not confirmed'),
    missed: t('insights.grid.doseMissed', 'Missed'),
    none: t('insights.grid.doseNone', 'No dose due'),
  }

  // the day panel opens on the latest day with a missed dose in the month, otherwise the latest day
  const open: string | null = (() => {
    if (!data || data.dates.length === 0) return null
    if (picked && data.dates.includes(picked)) return picked
    for (let i = data.dates.length - 1; i >= 0; i--) if (data.meds.some((m) => m.cells[i] === 'missed')) return data.dates[i]!
    return data.dates[data.dates.length - 1]!
  })()
  useEffect(() => {
    setPicked(null)
    setMore(false)
  }, [data?.month])

  const totalMissed = data?.reasons.reduce((a, r) => a + r.count, 0) ?? 0
  const maxReason = Math.max(1, ...(data?.reasons.map((r) => r.count) ?? [1]))
  // nothing at all on record (no month has a dose) is the only "empty" page; an empty month still shows the calendar so you can browse away from it
  const nothing = !!data && data.meds.length === 0 && !data.prevMonth && !data.nextMonth
  const when = data?.month ? monthTitle(data.month) : ''
  const shown: InsightsMedication['meds'] = data ? (filter === 'all' ? data.meds : data.meds.filter((m) => m.id === filter)) : []
  const misses = data
    ? [...data.dates]
        .map((date, i) => ({ date, i }))
        .reverse()
        .flatMap(({ date, i }) =>
          shown.filter((m) => m.cells[i] === 'missed' || m.cells[i] === 'unconfirmed').map((m) => ({ date, med: m, cell: m.cells[i]! })),
        )
    : []
  const missDays = data ? new Set(data.meds.flatMap((m) => data.dates.filter((_, i) => m.cells[i] === 'missed'))).size : 0
  const counted = data ? data.meds.filter((m) => m.counted).length : 0

  return (
    <InsightsFrame tab="C6" period={data?.period} why="medication" filter={false}>
      <Gate data={data} isError={isError} empty={nothing} emptyText={t('insights.medication.empty', 'Add a medicine and your doses show up here, day by day.')}>
        {data && (
          <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_332px] [&>*]:min-w-0">
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                <Tile
                  label={t('insights.medication.tileTaken', 'Doses taken')}
                  value={data.adherencePct != null ? String(Math.round(data.adherencePct)) : '–'}
                  unit={data.adherencePct != null ? '%' : undefined}
                  status={
                    data.adherencePct != null
                      ? t('insights.medication.tileTakenSub', '{{taken}} of {{n}} doses', { taken: data.taken, n: data.scheduled })
                      : t('insights.medication.tileNone', 'Not confirmed yet')
                  }
                  tone={pctTone(data.adherencePct)}
                />
                <Tile
                  label={t('insights.medication.tileMissed', 'Missed')}
                  value={String(data.missed)}
                  status={data.missed > 0 ? t('insights.medication.tileMissedSub', 'On {{n}} days', { n: missDays }) : t('insights.medication.none', 'None')}
                  tone={data.missed > 0 ? 'danger' : 'ok'}
                />
                <Tile
                  label={t('insights.medication.tileUnconfirmed', 'Not confirmed')}
                  value={String(data.unconfirmed)}
                  status={data.unconfirmed > 0 ? t('insights.medication.tileUnconfirmedSub', 'Waiting for an answer') : t('insights.medication.none', 'None')}
                  tone={data.unconfirmed > 0 ? 'brass' : 'ok'}
                />
                <Tile
                  label={t('insights.medication.tileMeds', 'Medicines')}
                  value={String(data.meds.length)}
                  status={t('insights.medication.tileMedsSub', '{{c}} counted, {{o}} not', { c: counted, o: data.meds.length - counted })}
                  tone="neutral"
                />
              </div>

              <Card className="flex flex-col gap-3 !p-4 sm:!px-5">
                <DoseCalendar data={data} filter={filter} onFilter={setFilter} picked={open} onPick={setPicked} onMonth={setMonth} />
              </Card>

              <Card className="flex flex-col !px-5 !pb-2 !pt-4">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                  <h2 className="text-body font-bold">{t('insights.medication.missedList', 'Missed or not confirmed')}</h2>
                  <p className="text-sub text-ink3">
                    {t('insights.medication.missedListSub', '{{n}} in {{month}}. Tap one to open its day.', { n: misses.length, month: when })}
                  </p>
                </div>
                {misses.length === 0 && (
                  <p className="py-3 text-sub text-ink2">{t('insights.medication.missedNone', 'Nothing was missed or left unconfirmed. Well done.')}</p>
                )}
                {(more ? misses : misses.slice(0, 6)).map((x) => (
                  <button
                    key={`${x.date}-${x.med.id}`}
                    type="button"
                    onClick={() => setPicked(x.date)}
                    className="press flex min-h-14 items-center gap-3 border-t border-line py-2 text-left first:border-t-0"
                  >
                    <StatusDot cell={x.cell} />
                    <span className="min-w-0 flex-1">
                      <span className="block break-words text-sub font-bold leading-tight">{x.med.name}</span>
                      <span className="block text-micro text-ink2">
                        {shortDate(x.date)} · {labels[x.cell]}
                      </span>
                    </span>
                    <span className="flex-none text-sub font-bold text-brand">{t('insights.medication.openDay', 'Open day')} ›</span>
                  </button>
                ))}
                {misses.length > 6 && (
                  <button type="button" onClick={() => setMore((v) => !v)} className="press min-h-11 self-start text-sub font-bold text-brand underline">
                    {more ? t('insights.medication.showFewer', 'Show fewer') : t('insights.medication.showAll', 'Show all {{n}}', { n: misses.length })}
                  </button>
                )}
              </Card>
            </div>

            <aside className="flex flex-col gap-4 lg:sticky lg:top-2">
              <Card className="flex flex-col gap-1">
                <div className="flex items-baseline justify-between gap-2">
                  <h2 className="text-body font-bold">{open ? shortDate(open) : t('insights.medication.noDay', 'No day to show')}</h2>
                  {open && <span className="text-sub text-ink3">{t('insights.medication.dayCount', '{{n}} medicines', { n: shown.length })}</span>}
                </div>
                {open &&
                  shown.map((m) => {
                    const c = m.cells[data.dates.indexOf(open)]!
                    return (
                      <div key={m.id} className="flex items-start gap-3 border-t border-line py-2.5 first:border-t-0">
                        <StatusDot cell={c} />
                        <div className="min-w-0 flex-1">
                          <p className="break-words text-sub font-bold leading-tight">{m.name}</p>
                          <p className={cn('text-micro font-bold', DAY_TONE[CELL_ICON[c].tone].text)}>
                            {labels[c]}
                            {!m.counted && <span className="font-normal text-ink3"> · {t('insights.grid.notCounted', 'Not counted in adherence')}</span>}
                          </p>
                          <p className="text-micro text-ink3">{m.regimen}</p>
                        </div>
                      </div>
                    )
                  })}
              </Card>

              <Card className="flex flex-col gap-2.5">
                <h2 className="text-body font-bold">{t('insights.medication.whyMissed', 'Why doses were missed')}</h2>
                {data.reasons.length > 0 ? (
                  <>
                    <p className="text-sub text-ink2">
                      {t('insights.medication.reasons', 'The reasons you gave for {{n}} missed prescription doses.', { n: totalMissed })}
                    </p>
                    {data.reasons.map((r) => (
                      <div key={r.key} className="flex flex-col gap-1">
                        <div className="flex items-baseline justify-between text-sub">
                          <span className="font-bold">{r.label}</span>
                          <span className="num text-ink2">{r.count}</span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-well" aria-hidden>
                          <div className="h-full rounded-full bg-warn" style={{ width: `${(r.count / maxReason) * 100}%` }} />
                        </div>
                      </div>
                    ))}
                  </>
                ) : (
                  <p className="text-sub text-ink2">
                    {t('insights.medication.noReasons', 'No reasons for missed prescription doses were given in {{month}}.', { month: when })}
                  </p>
                )}
              </Card>

              <Findings items={data.patterns} whyLink={false} />
              <p className="px-1 text-micro text-ink3">
                {t('insights.medication.adherenceNote', 'Adherence counts prescription medicines only. A dose that was not answered is counted as not taken.')}
              </p>
              <TextLink icon={Pill} onClick={() => go('H1')}>
                {t('insights.medication.openMedicines', 'Open my medicines')}
              </TextLink>
            </aside>
          </div>
        )}
      </Gate>
    </InsightsFrame>
  )
}
