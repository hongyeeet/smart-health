/**
 * The printable doctor report's layout ("Diabetes monitoring report"), shared by the L3 print page and the read-only share page.
 *
 * Presentational only: it lays out a `DoctorReport` from `GET /brief/report` or the public share endpoint. Nothing here is
 * calculated or worded, and no AI is involved.
 */
import type { DoctorReport, GlucoseBandKey } from '@/data/types'
import { appConfig } from '@/config/app'
import { palettes } from '@/theme/palettes'
import './report.css'

const p = palettes.light
const BAND_FILL: Record<GlucoseBandKey, string> = { very_high: p.gVeryHigh, high: p.gHigh, in_range: p.gIn, low: p.gLow, very_low: p.gVeryLow }
const TAG: Record<DoctorReport['alerts'][number]['priority'], string> = { urgent: 'Urgent', interaction: 'Interaction', review: 'Review' }
const dash = (v: number | string | null | undefined, suffix = '') => (v === null || v === undefined ? '—' : `${v}${suffix}`)

/** Glucose by time of day: median line, 25th to 75th and 5th to 95th percentile bands. Hours without enough readings are gaps. */
function DailyProfile({ g }: { g: DoctorReport['glucose'] }) {
  if (g.profile.length < 2 || g.low === null || g.high === null || g.veryLow === null || g.veryHigh === null) return null
  const x = (hour: number) => 40 + ((hour + 0.5) / 24) * 640
  const y = (v: number) => 105 + (10 - Math.min(Math.max(v, 2), 16)) * 11.87
  const runs: DoctorReport['glucose']['profile'][] = []
  for (const pt of g.profile) {
    const last = runs[runs.length - 1]
    if (last && last[last.length - 1]!.hour === pt.hour - 1) last.push(pt)
    else runs.push([pt])
  }
  const band = (run: typeof g.profile, lo: 'p5' | 'p25', hi: 'p95' | 'p75') => [...run.map((q) => `${x(q.hour)},${y(q[hi])}`), ...[...run].reverse().map((q) => `${x(q.hour)},${y(q[lo])}`)].join(' ')
  const text = { fontSize: 12, fill: '#475467', fontFamily: 'Atkinson Hyperlegible, sans-serif' }
  return (
    <figure style={{ margin: '4px 0 0' }}>
      <svg viewBox="0 0 700 232" role="img" aria-label="Glucose by time of day over the period: median and percentile bands" style={{ display: 'block', margin: '0 auto', width: '100%', maxWidth: 580, height: 'auto' }}>
        <rect x="40" y={y(g.high)} width="640" height={y(g.low) - y(g.high)} fill="#E6F4EE" />
        <line x1="40" y1={y(g.low)} x2="680" y2={y(g.low)} stroke={p.gIn} strokeWidth="1" strokeDasharray="4 3" />
        <line x1="40" y1={y(g.high)} x2="680" y2={y(g.high)} stroke={p.gIn} strokeWidth="1" strokeDasharray="4 3" />
        <line x1="40" y1={y(g.veryHigh)} x2="680" y2={y(g.veryHigh)} stroke="#98A2B3" strokeWidth="1" strokeDasharray="2 4" />
        <line x1="40" y1={y(g.veryLow)} x2="680" y2={y(g.veryLow)} stroke="#B42318" strokeWidth="1" strokeDasharray="2 4" />
        <line x1="40" y1="200" x2="680" y2="200" stroke="#98A2B3" strokeWidth="1" />
        {runs.map((run) => (
          <g key={run[0]!.hour}>
            {run.length > 1 && <polygon points={band(run, 'p5', 'p95')} fill={p.s1} fillOpacity="0.13" />}
            {run.length > 1 && <polygon points={band(run, 'p25', 'p75')} fill={p.s1} fillOpacity="0.3" />}
            {run.length > 1 ? (
              <polyline points={run.map((q) => `${x(q.hour)},${y(q.p50)}`).join(' ')} fill="none" stroke={p.s1} strokeWidth="2.5" strokeLinejoin="round" />
            ) : (
              <circle cx={x(run[0]!.hour)} cy={y(run[0]!.p50)} r="3" fill={p.s1} />
            )}
          </g>
        ))}
        {[g.veryHigh, g.high, g.low].map((v) => (
          <text key={v} x="34" y={y(v) + 4} textAnchor="end" {...text}>
            {v.toFixed(1)}
          </text>
        ))}
        <text x="34" y={y(g.veryLow) + 10} textAnchor="end" {...text} fill="#B42318">
          {g.veryLow.toFixed(1)}
        </text>
        {[0, 6, 12, 18, 24].map((h) => (
          <g key={h}>
            <line x1={40 + (h / 24) * 640} y1="200" x2={40 + (h / 24) * 640} y2="205" stroke="#98A2B3" strokeWidth="1" />
            <text x={40 + (h / 24) * 640} y="222" textAnchor="middle" {...text}>
              {String(h).padStart(2, '0')}:00
            </text>
          </g>
        ))}
      </svg>
      <figcaption className="rp-muted">
        Glucose by time of day, all days in the period overlaid. Line: median · dark band: 25th to 75th percentile · light band: 5th to 95th · shaded: {g.low.toFixed(1)} to {g.high.toFixed(1)} mmol/L. Hours with too few readings are left blank.
      </figcaption>
    </figure>
  )
}

/** The report sheet itself, as a doctor reads it. ReportA4 (print page) and SharedReport (share link) both use it. */
export function ReportView({ r }: { r: DoctorReport }) {
  const g = r.glucose
  return (
    <div className="rp-sheet">
      <div className="rp-head">
        <div>
          <div className="rp-eyebrow">{appConfig.name} · Patient-generated data</div>
          <h1>Diabetes monitoring report</h1>
        </div>
        <div className="rp-muted" style={{ textAlign: 'right' }}>
          Generated {r.generatedOn}
        </div>
      </div>

      <div className="rp-facts">
        {[
          ['Patient', r.patient.name],
          ['Sex / age', r.patient.sexAge],
          ['Diagnosis', r.patient.diagnosis],
          ['Report period', r.period.label],
          ['CGM wear', r.cgmWear],
          ['Data sources', r.sources],
        ].map(([k, v]) => (
          <div key={k}>
            <span className="rp-muted">{k}</span>
            <b>{v}</b>
          </div>
        ))}
      </div>

      <section className="rp-box">
        <h2>Key findings</h2>
        <ul>
          {r.keyFindings.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Alerts</h2>
        {r.alerts.length === 0 ? (
          <p className="rp-muted">No alerts were raised from the data in this period. This is not a statement that nothing needs attention.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th style={{ width: 92 }}>Priority</th>
                <th style={{ width: 210 }}>Alert</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {r.alerts.map((a, i) => (
                <tr key={i}>
                  <td>
                    <span className={`rp-tag rp-tag-${a.priority}`}>{TAG[a.priority].toUpperCase()}</span>
                  </td>
                  <td className="rp-strong">{a.title}</td>
                  <td>{a.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h2>Glucose (CGM) · mmol/L</h2>
        {!g.hasData ? (
          <p className="rp-muted">No sensor glucose readings in this period.</p>
        ) : (
          <>
            {!g.sufficient && <p className="rp-out">The sensor was active for too little of this period for these figures to be representative.</p>}
            <div className="rp-two">
              <table>
                <thead>
                  <tr>
                    <th>Time in ranges</th>
                    <th className="rp-num">%</th>
                    <th className="rp-num">≈ per day</th>
                    <th className="rp-num">Reference</th>
                  </tr>
                </thead>
                <tbody>
                  {g.bands.map((b) => (
                    <tr key={b.key}>
                      <td className={b.key === 'in_range' ? 'rp-strong' : undefined}>
                        <span className="rp-swatch" style={{ background: BAND_FILL[b.key] }} />
                        {b.label}
                      </td>
                      <td className={`rp-num ${b.outside ? 'rp-out' : ''}`}>{b.pct.toFixed(1)}</td>
                      <td className="rp-num">{b.perDay}</td>
                      <td className="rp-num rp-muted">{b.reference}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <table>
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th className="rp-num">Value</th>
                    <th className="rp-num">Reference</th>
                  </tr>
                </thead>
                <tbody>
                  {g.metrics.map((m) => (
                    <tr key={m.label}>
                      <td>{m.label}</td>
                      <td className={`rp-num ${m.outside ? 'rp-out' : 'rp-strong'}`}>{m.value}</td>
                      <td className="rp-num rp-muted">{m.reference}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <DailyProfile g={g} />
          </>
        )}
      </section>

      <div className="rp-break">
        <span className="rp-strong" style={{ fontSize: 15 }}>
          Diabetes monitoring report: detail
        </span>
        <span className="rp-muted">
          {r.patient.name} · {r.period.label}
        </span>
      </div>

      <section>
        <h2>Symptoms and glucose</h2>
        {r.symptoms.length === 0 ? (
          <p className="rp-muted">No symptoms were logged in this period.</p>
        ) : (
          <>
            <table>
              <thead>
                <tr>
                  <th>Symptom</th>
                  <th className="rp-num">Logged</th>
                  <th className="rp-num">Low</th>
                  <th className="rp-num">High</th>
                  <th className="rp-num">In range</th>
                  <th className="rp-num">No reading</th>
                  <th style={{ paddingLeft: 16 }}>Note</th>
                </tr>
              </thead>
              <tbody>
                {r.symptoms.map((s) => (
                  <tr key={s.symptom}>
                    <td className="rp-strong">{s.symptom}</td>
                    <td className="rp-num">{s.logged}</td>
                    <td className={`rp-num ${s.low > 0 ? 'rp-out' : ''}`}>{s.low}</td>
                    <td className="rp-num">{s.high}</td>
                    <td className="rp-num">{s.inRange}</td>
                    <td className="rp-num">{s.noReading}</td>
                    <td style={{ paddingLeft: 16 }}>{s.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="rp-muted">Glucose is the nearest sensor reading within 15 minutes of the logged time. Counts show what was recorded together, not what caused a symptom.</p>
          </>
        )}
      </section>

      {r.episodes.length > 0 && (
        <section>
          <h2>Symptom entries</h2>
          <table>
            <thead>
              <tr>
                <th>Date / time</th>
                <th>Symptom</th>
                <th className="rp-num">Glucose</th>
                <th className="rp-num">Δ 30 min</th>
                <th className="rp-num">HR / SpO2</th>
                <th style={{ paddingLeft: 16 }}>Last dose taken before</th>
              </tr>
            </thead>
            <tbody>
              {r.episodes.map((e, i) => (
                <tr key={i} className={e.zone === 'very_low' ? 'rp-row-urgent' : undefined}>
                  <td>{e.when}</td>
                  <td className="rp-strong">
                    {e.symptom}
                    {e.note && <div className="rp-muted" style={{ fontWeight: 400 }}>{e.note}</div>}
                  </td>
                  <td className={`rp-num ${e.zone === 'low' || e.zone === 'very_low' ? 'rp-out' : 'rp-strong'}`}>{e.glucose === null ? '—' : e.glucose.toFixed(1)}</td>
                  <td className="rp-num">{e.change30 === null ? '—' : `${e.change30 > 0 ? '↑ +' : e.change30 < 0 ? '↓ −' : '→ '}${Math.abs(e.change30).toFixed(1)}`}</td>
                  <td className="rp-num">
                    {dash(e.heartRate)} / {dash(e.spo2, '%')}
                  </td>
                  <td style={{ paddingLeft: 16 }}>{e.lastDose ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {r.episodesTotal > r.episodes.length && <p className="rp-muted">Showing the latest {r.episodes.length} of {r.episodesTotal} entries.</p>}
          <p className="rp-muted">"Last dose taken before" is the most recent dose marked taken in the 6 hours before the entry, whichever medicine it was.</p>
        </section>
      )}

      <section>
        <h2>Medications</h2>
        {r.medicines.length === 0 ? (
          <p className="rp-muted">No medicines are recorded.</p>
        ) : (
          <>
            <table>
              <thead>
                <tr>
                  <th>Medication</th>
                  <th>Regimen</th>
                  <th className="rp-num">Scheduled</th>
                  <th className="rp-num">Taken</th>
                  <th className="rp-num">Missed</th>
                  <th className="rp-num">Not logged</th>
                  <th className="rp-num">Adherence</th>
                </tr>
              </thead>
              <tbody>
                {r.medicines.map((m) => (
                  <tr key={m.name}>
                    <td className="rp-strong">
                      {m.name}
                      {m.interaction && (
                        <span className="rp-tag rp-tag-interaction" style={{ marginLeft: 6 }}>
                          INTERACTION
                        </span>
                      )}
                    </td>
                    <td>{m.regimen}</td>
                    <td className="rp-num">{dash(m.scheduled)}</td>
                    <td className="rp-num">{dash(m.taken)}</td>
                    <td className={`rp-num ${m.missed ? 'rp-out' : ''}`}>{dash(m.missed)}</td>
                    <td className="rp-num">{dash(m.notLogged)}</td>
                    <td className="rp-num rp-strong">{dash(m.adherencePct, '%')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {r.medicinesNote && <p className="rp-muted" style={{ color: '#344054' }}>{r.medicinesNote}</p>}
          </>
        )}
      </section>

      <section>
        <h2>Activity, heart rate and wellbeing</h2>
        <div className="rp-cells">
          {r.activity.map((c) => (
            <div key={c.label}>
              <span className="rp-muted">{c.label}</span>
              <b>{c.value}</b>
              <span className="rp-muted">{c.sub}</span>
            </div>
          ))}
        </div>
      </section>

      {r.questions.length > 0 && (
        <section>
          <h2>Patient's questions</h2>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {r.questions.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </section>
      )}

      <div className="rp-foot">
        <b style={{ color: '#344054' }}>Data notes.</b> CGM measures interstitial glucose, which lags blood glucose by about 5 to 15 minutes. Wrist SpO2 is less accurate than a fingertip oximeter, particularly with movement,
        and is simulated in the demo data. Symptoms, medicines and stress are self-reported. Interaction flags come from drug-label rules and an AI web search and are not a clinical judgement. The reference values are
        general consensus figures that have not been set by a clinician for this person. This report summarises patient-recorded and device data. Numbers are computed by fixed rules, not by AI. It is not a diagnosis.
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginTop: 6 }}>
          <span>
            Generated by {appConfig.name} on {r.generatedOn}
          </span>
          <span>{r.patient.name}</span>
        </div>
      </div>
    </div>
  )
}
