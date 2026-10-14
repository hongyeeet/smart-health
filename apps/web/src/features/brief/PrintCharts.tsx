/**
 * The four charts of the printed report: glucose, heart rate, SpO2 and blood pressure over the period.
 * Plain SVG with fixed colours so it prints in black and white or colour. Each chart has the person's own baseline
 * (dashed line, and a pale band for the middle half of their usual days) and the reasoning lines from the screen.
 */
import type { ReactNode } from 'react'
import type { InsightsTimeline } from '@/data/types'

type Reason = { title: string; why: string; saw: string }
type Pt = number | null

const W = 700
const H = 150
const L = 44
const R = 14
const T = 10
const B = 24

const shortDate = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })

function Frame({ title, unit, reason, children }: { title: string; unit: string; reason?: Reason; children: ReactNode }) {
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
  decimals = 1,
}: {
  data: { avg: Pt[]; min: Pt[]; max: Pt[] }
  tl: InsightsTimeline
  label: string
  unit: string
  color: string
  base: { mean: number | null; lo: number | null; hi: number | null }
  reason?: Reason
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
    <Frame title={label} unit={unit} reason={reason}>
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

function Bp({ tl, reason }: { tl: InsightsTimeline; reason?: Reason }) {
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
    <Frame title="Blood pressure" unit="mmHg" reason={reason}>
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

export function PrintCharts({ tl, reasons }: { tl: InsightsTimeline; reasons?: Reason[] }) {
  const why = (t: string) => reasons?.find((r) => r.title.toLowerCase().startsWith(t))
  const s = tl.series
  const b = tl.baseline.daily
  return (
    <div>
      <Line
        data={{ avg: s.glucose, min: s.glucoseMin, max: s.glucoseMax }}
        tl={tl}
        label="Glucose"
        unit="mmol/L"
        color="#175CD3"
        base={b.glucose}
        reason={why('glucose')}
      />
      <Line
        data={{ avg: s.heart, min: s.heartMin, max: s.heartMax }}
        tl={tl}
        label="Heart rate"
        unit="bpm"
        color="#B42318"
        base={b.heart}
        reason={why('heart')}
        decimals={0}
      />
      <Line data={{ avg: s.spo2, min: s.spo2Min, max: s.spo2Max }} tl={tl} label="SpO2" unit="%" color="#7A5C12" base={b.spo2} reason={why('spo')} />
      <Bp tl={tl} reason={why('blood')} />
    </div>
  )
}
