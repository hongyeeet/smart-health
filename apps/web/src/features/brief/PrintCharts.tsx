/**
 * The four charts of the printed report: glucose, heart rate, SpO2 and blood pressure over the period.
 * Plain SVG with fixed colours so it prints in black and white or colour. Each chart has the person's own baseline
 * (dashed line, and a pale band for the middle half of their usual days) and the reasoning lines from the screen.
 */
import type { ReactNode } from 'react'
import type { InsightsTimeline } from '@/data/types'

type Reason = { title: string; why: string; saw: string }
export type ChartFilter = 'glucose' | 'heart' | 'spo2' | 'bp' | 'meals' | 'exercise' | 'symptoms' | 'missed'
export const FILTERS_ON: Record<ChartFilter, boolean> = {
  glucose: true,
  heart: true,
  spo2: true,
  bp: true,
  meals: true,
  exercise: true,
  symptoms: true,
  missed: true,
}
export const FILTER_LIST: [ChartFilter, string][] = [
  ['glucose', 'Glucose'],
  ['heart', 'Heart rate'],
  ['spo2', 'SpO2'],
  ['bp', 'Blood pressure'],
  ['meals', 'Meals'],
  ['exercise', 'Exercise'],
  ['symptoms', 'Symptoms'],
  ['missed', 'Missed doses'],
]
type Pt = number | null

const W = 700
const H = 150
const L = 66
const R = 14
const T = 10
const B = 24

const shortDate = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })

/** The log rows under a chart: meals, exercise, symptoms and missed doses on the same time axis. */
function Lanes({ tl, show }: { tl: InsightsTimeline; show: Record<ChartFilter, boolean> }) {
  const total = tl.period.days * 1440
  const x = (m: number) => L + (Math.min(Math.max(m, 0), total) / total) * (W - L - R)
  const rows: { key: ChartFilter; label: string; items: ReactNode[] }[] = []
  const e = tl.events
  if (show.meals)
    rows.push({ key: 'meals', label: 'Meals', items: e.meals.map((m, i) => <rect key={i} x={x(m.m) - 2} y={2} width={4} height={10} fill="#8A6A1F" />) })
  if (show.exercise)
    rows.push({
      key: 'exercise',
      label: 'Exercise',
      items: e.exercise.map((m, i) => <rect key={i} x={x(m.m0)} y={3} width={Math.max(4, x(m.m1) - x(m.m0))} height={8} rx={2} fill="#1D6B47" />),
    })
  if (show.symptoms)
    rows.push({ key: 'symptoms', label: 'Symptoms', items: e.symptoms.map((m, i) => <circle key={i} cx={x(m.m)} cy={7} r={3.5} fill="#175CD3" />) })
  if (show.missed)
    rows.push({ key: 'missed', label: 'Missed doses', items: e.missed.map((m, i) => <circle key={i} cx={x(m.m)} cy={7} r={3.5} fill="#B42318" />) })
  if (rows.length === 0) return null
  return (
    <svg
      viewBox={`0 0 ${W} ${rows.length * 14 + 2}`}
      role="img"
      aria-label="Meals, exercise, symptoms and missed doses"
      style={{ display: 'block', width: '100%', height: 'auto', maxWidth: 700 }}
    >
      {rows.map((r, k) => (
        <g key={r.key} transform={`translate(0 ${k * 14})`}>
          <text x={L - 6} y={11} textAnchor="end" fontSize={10} fill="#475467" fontFamily="Atkinson Hyperlegible, sans-serif">
            {r.label}
          </text>
          <line x1={L} y1={7} x2={W - R} y2={7} stroke="#EAECF0" strokeWidth="1" />
          {r.items}
        </g>
      ))}
    </svg>
  )
}

function Frame({ title, unit, reason, lanes, children }: { title: string; unit: string; reason?: Reason; lanes?: ReactNode; children: ReactNode }) {
  return (
    <figure className="rp-chart" style={{ margin: '8px 0 14px', breakInside: 'avoid' }}>
      <div className="rp-strong">
        {title} <span className="rp-muted">{unit}</span>
      </div>
      {reason && (
        <p style={{ margin: '2px 0 4px', fontSize: 12.5 }}>
          <b>Why this matters.</b> {reason.why} <b>What we saw.</b> {reason.saw}
        </p>
      )}
      {lanes}
      {children}
    </figure>
  )
}

function Axes({ lo, hi, start, end, y }: { lo: number; hi: number; start: string; end: string; y: (v: number) => number }) {
  const text = { fontSize: 11, fill: '#475467', fontFamily: 'Atkinson Hyperlegible, sans-serif' }
  const ticks = [...new Set([lo, (lo + hi) / 2, hi].map((v) => Math.round(v)))]
  const a = new Date(`${start}T00:00:00`).getTime()
  const b = new Date(`${end}T00:00:00`).getTime()
  const midIso = new Date((a + b) / 2).toISOString().slice(0, 10)
  return (
    <>
      {ticks.map((v) => (
        <g key={v}>
          <line x1={L} y1={y(v)} x2={W - R} y2={y(v)} stroke="#E4E7EC" strokeWidth="1" />
          <text x={L - 6} y={y(v) + 4} textAnchor="end" {...text}>
            {v}
          </text>
        </g>
      ))}
      <line x1={L} y1={H - B} x2={W - R} y2={H - B} stroke="#98A2B3" strokeWidth="1" />
      <text x={L} y={H - 6} textAnchor="start" {...text}>
        {shortDate(start)}
      </text>
      <text x={(L + W - R) / 2} y={H - 6} textAnchor="middle" {...text}>
        {shortDate(midIso)}
      </text>
      <text x={W - R} y={H - 6} textAnchor="end" {...text}>
        {shortDate(end)}
      </text>
    </>
  )
}

function Line({
  data,
  tl,
  label,
  unit,
  color,
  base,
  reason,
  lanes,
  decimals = 1,
}: {
  data: { avg: Pt[]; min: Pt[]; max: Pt[] }
  tl: InsightsTimeline
  label: string
  unit: string
  color: string
  base: { mean: number | null; lo: number | null; hi: number | null }
  reason?: Reason
  lanes?: ReactNode
  decimals?: number
}) {
  const n = data.avg.length
  const vals = [...data.avg, ...data.min, ...data.max, base.mean, base.lo, base.hi].filter((v): v is number => v != null)
  if (n < 2 || vals.length === 0) {
    return (
      <Frame title={label} unit={unit} reason={reason}>
        <p className="rp-muted">No readings in this period.</p>
      </Frame>
    )
  }
  const pad = (Math.max(...vals) - Math.min(...vals)) * 0.12 || 1
  const lo = Math.min(...vals) - pad
  const hi = Math.max(...vals) + pad
  const x = (i: number) => L + (i / (n - 1)) * (W - L - R)
  const y = (v: number) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B)
  // runs of consecutive readings, so a gap in the data stays a gap
  const runs = (a: Pt[]) => {
    const out: { i: number; v: number }[][] = []
    a.forEach((v, i) => {
      if (v == null) return
      const last = out[out.length - 1]
      if (last && last[last.length - 1]!.i === i - 1) last.push({ i, v })
      else out.push([{ i, v }])
    })
    return out
  }
  const bandRuns = runs(data.avg).map((r) => r.filter((p) => data.min[p.i] != null && data.max[p.i] != null))
  return (
    <Frame title={label} unit={unit} reason={reason} lanes={lanes}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`${label} over the period`}
        style={{ display: 'block', width: '100%', height: 'auto', maxWidth: 700 }}
      >
        {base.lo != null && base.hi != null && <rect x={L} y={y(base.hi)} width={W - L - R} height={Math.max(0, y(base.lo) - y(base.hi))} fill="#EAECF0" />}
        <Axes lo={lo} hi={hi} start={tl.period.start} end={tl.period.end} y={y} />
        {bandRuns.map(
          (r, k) =>
            r.length > 1 && (
              <polygon
                key={k}
                points={[...r.map((p) => `${x(p.i)},${y(data.max[p.i]!)}`), ...[...r].reverse().map((p) => `${x(p.i)},${y(data.min[p.i]!)}`)].join(' ')}
                fill={color}
                fillOpacity="0.14"
              />
            ),
        )}
        {base.mean != null && <line x1={L} y1={y(base.mean)} x2={W - R} y2={y(base.mean)} stroke="#475467" strokeWidth="1.2" strokeDasharray="5 4" />}
        {runs(data.avg).map((r, k) =>
          r.length > 1 ? (
            <polyline key={k} points={r.map((p) => `${x(p.i)},${y(p.v)}`).join(' ')} fill="none" stroke={color} strokeWidth="2.2" strokeLinejoin="round" />
          ) : (
            <circle key={k} cx={x(r[0]!.i)} cy={y(r[0]!.v)} r="3" fill={color} />
          ),
        )}
      </svg>
      <figcaption className="rp-muted" style={{ fontSize: 11.5 }}>
        Line: average · shaded: lowest to highest · dashed line: your baseline{base.mean != null ? ` (${base.mean.toFixed(decimals)} ${unit})` : ''}
        {base.lo != null ? ' · grey band: your usual range' : ''}.
      </figcaption>
    </Frame>
  )
}

function Bp({ tl, reason, lanes }: { tl: InsightsTimeline; reason?: Reason; lanes?: ReactNode }) {
  const pts = tl.bp
  if (pts.length === 0) {
    return (
      <Frame title="Blood pressure" unit="mmHg" reason={reason}>
        <p className="rp-muted">No readings in this period.</p>
      </Frame>
    )
  }
  const total = tl.period.days * 1440
  const vals = pts.flatMap((p) => [p.systolic, p.diastolic])
  if (tl.baseline.bpSystolic != null) vals.push(tl.baseline.bpSystolic)
  if (tl.baseline.bpDiastolic != null) vals.push(tl.baseline.bpDiastolic)
  const lo = Math.min(...vals) - 8
  const hi = Math.max(...vals) + 8
  const x = (m: number) => L + (m / total) * (W - L - R)
  const y = (v: number) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B)
  return (
    <Frame title="Blood pressure" unit="mmHg" reason={reason} lanes={lanes}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Blood pressure readings over the period"
        style={{ display: 'block', width: '100%', height: 'auto', maxWidth: 700 }}
      >
        <Axes lo={lo} hi={hi} start={tl.period.start} end={tl.period.end} y={y} />
        {tl.baseline.bpSystolic != null && (
          <line x1={L} y1={y(tl.baseline.bpSystolic)} x2={W - R} y2={y(tl.baseline.bpSystolic)} stroke="#475467" strokeWidth="1.2" strokeDasharray="5 4" />
        )}
        {tl.baseline.bpDiastolic != null && (
          <line x1={L} y1={y(tl.baseline.bpDiastolic)} x2={W - R} y2={y(tl.baseline.bpDiastolic)} stroke="#475467" strokeWidth="1.2" strokeDasharray="5 4" />
        )}
        {pts.map((p, i) => (
          <g key={i}>
            <line x1={x(p.m)} y1={y(p.systolic)} x2={x(p.m)} y2={y(p.diastolic)} stroke="#98A2B3" strokeWidth="1.5" />
            <circle cx={x(p.m)} cy={y(p.systolic)} r="3.2" fill="#B54708" />
            <circle cx={x(p.m)} cy={y(p.diastolic)} r="3.2" fill="#175CD3" />
          </g>
        ))}
      </svg>
      <figcaption className="rp-muted" style={{ fontSize: 11.5 }}>
        Top dot: systolic · bottom dot: diastolic · dashed lines: your baseline
        {tl.baseline.bpSystolic != null && tl.baseline.bpDiastolic != null
          ? ` (${Math.round(tl.baseline.bpSystolic)}/${Math.round(tl.baseline.bpDiastolic)} mmHg)`
          : ''}
        .
      </figcaption>
    </Frame>
  )
}

export function PrintCharts({ tl, reasons, show = FILTERS_ON }: { tl: InsightsTimeline; reasons?: Reason[]; show?: Record<ChartFilter, boolean> }) {
  const why = (t: string) => reasons?.find((r) => r.title.toLowerCase().startsWith(t))
  const s = tl.series
  const b = tl.baseline.daily
  const lanes = <Lanes tl={tl} show={show} />
  const any = show.glucose || show.heart || show.spo2 || show.bp
  return (
    <div>
      {show.glucose && (
        <Line
          data={{ avg: s.glucose, min: s.glucoseMin, max: s.glucoseMax }}
          tl={tl}
          label="Glucose"
          unit="mmol/L"
          color="#175CD3"
          base={b.glucose}
          reason={why('glucose')}
          lanes={lanes}
        />
      )}
      {show.heart && (
        <Line
          data={{ avg: s.heart, min: s.heartMin, max: s.heartMax }}
          tl={tl}
          label="Heart rate"
          unit="bpm"
          color="#B42318"
          base={b.heart}
          reason={why('heart')}
          lanes={lanes}
          decimals={0}
        />
      )}
      {show.spo2 && (
        <Line
          data={{ avg: s.spo2, min: s.spo2Min, max: s.spo2Max }}
          tl={tl}
          label="SpO2"
          unit="%"
          color="#7A5C12"
          base={b.spo2}
          reason={why('spo')}
          lanes={lanes}
        />
      )}
      {show.bp && <Bp tl={tl} reason={why('blood')} lanes={lanes} />}
      {!any && lanes}
    </div>
  )
}
