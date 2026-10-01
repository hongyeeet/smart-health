import { useEffect, useRef } from 'react'
import { useBrief, useDay, useInsights } from '@/data/hooks'
import { AdherenceTimeline, FoodBars, IntensityBars, MoodStress, TirBar } from '@/charts/small'
import { TrendChart } from '@/charts/TrendChart'
import { DayChart } from '@/charts/DayChart'
import { applyPalette, palettes } from '@/theme/palettes'
import { thousands } from '@/lib/format'
import './a4.css'

/** Day trace: a compact timeline for one representative day. */
function Trace({ date, kind }: { date: string; kind: string }) {
  const { data } = useDay(date)
  if (!data) return null
  return (
    <div>
      <p className="muted" style={{ fontWeight: 700, marginBottom: 2 }}>
        {kind[0]!.toUpperCase() + kind.slice(1)} day: {data.weekday} {data.label}, {data.inRangePct}% in range
      </p>
      <DayChart day={data} compact />
    </div>
  )
}

/**
 * The A4 doctor brief, printable in grayscale. It reads the same data as the in-app brief,
 * so the doctor sees exactly what the patient sees.
 */
export function BriefA4() {
  const { data: b } = useBrief()
  const { data: ins } = useInsights(30)
  const sheet = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (sheet.current) applyPalette(sheet.current, palettes.light)
    document.documentElement.style.background = '#E8E8E4'
  }, [b])
  if (!b || !ins) return <p style={{ padding: 40 }}>Loading the brief...</p>
  const m = ins.medication
  const gentle = ins.foods.filter((f) => !f.learning)

  return (
    <div style={{ background: '#E8E8E4', minHeight: '100%', padding: '1px 0 40px' }}>
      <div className="a4-actions">
        <span>Doctor brief, A4. Print or save as PDF. Grayscale safe.</span>
        <button type="button" onClick={() => window.print()} style={{ padding: '10px 18px', borderRadius: 10, border: '2px solid #111', background: '#fff', fontWeight: 700, cursor: 'pointer' }}>
          Print
        </button>
      </div>
      <div ref={sheet} className="a4-sheet">
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
          <div>
            <h1>Doctor brief</h1>
            <p className="muted" style={{ margin: '4px 0 0' }}>
              Patient {b.initials}, born {b.birthYear}. Period: {b.period}. Type 2 diabetes for 6 years. Last HbA1c 7.4%, 4 months ago.
            </p>
          </div>
          <div style={{ width: 200 }}>
            <p className="muted" style={{ margin: '0 0 3px', fontWeight: 700 }}>Data completeness</p>
            {b.completeness.map((c) => (
              <div key={c.stream} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11.5 }}>
                <span style={{ width: 78 }}>{c.stream}</span>
                <span className="bar" style={{ flex: 1 }}>
                  <span style={{ width: `${c.pct}%` }} />
                </span>
                <span>{c.pct}%</span>
              </div>
            ))}
          </div>
        </header>

        <section>
          <h2>1. Top 3 to discuss</h2>
          <ol style={{ margin: 0, paddingLeft: 18 }}>
            {b.top3.map((t) => (
              <li key={t.id} style={{ marginBottom: 3 }}>
                {t.text} <span className="tag">AI summary</span> <span className="muted">({t.evidence})</span>
              </li>
            ))}
          </ol>
        </section>

        <section>
          <h2>2. Medication and adherence</h2>
          <p style={{ margin: '0 0 6px' }}>
            Adherence <b>{m.adherencePct}%</b> ({m.taken} of {m.scheduled} doses). Reasons given: forgot (1), away from home (1). Two doses not confirmed. Interaction flags: Clarithromycin and Atorvastatin (possible interaction, reference data not clinically reviewed). Herbal tonic: not checked.
          </p>
          <AdherenceTimeline days={m.days} rows={m.timeline} fasting={m.fastingOverlay} />
        </section>

        <div className="grid2">
          <section>
            <h2>3. Glucose</h2>
            <p style={{ margin: '0 0 4px' }}>Fasting glucose against the personal baseline (6.6 to 7.2 mmol/L). Last 7 mornings 7.1 to 7.9. Sensor sprint day 9 of 14: average 7.4 mmol/L, estimated HbA1c 6.5%.</p>
            <TrendChart points={ins.fasting.points} baseline={ins.fasting.baseline} label="Fasting glucose, 30 days" height={130} drawKey="a4-fast" />
            <p className="muted" style={{ margin: '6px 0 4px', fontWeight: 700 }}>Time in range, last week</p>
            <TirBar segments={ins.timeInRange.segments} />
          </section>
          <section>
            <h2>4. Nutrition</h2>
            <p style={{ margin: '0 0 6px' }}>Meal responses from the sensor, gentlest to spikiest. High salt flagged on 4 meals this week. Nutrients are AI estimates until confirmed.</p>
            <FoodBars foods={gentle.slice(0, 3).concat(gentle.slice(-2))} />
          </section>
        </div>

        <div className="grid2">
          <section>
            <h2>5. Exercise</h2>
            <p style={{ margin: '0 0 4px' }}>Moderate minutes fell from 140 to 70 a week; 55 of 150 this week. Strength sessions 0 of 2. Mostly aerobic (9 of 10). Average steps {thousands(ins.activity.stepsAvg7)} against a usual of about {thousands(ins.activity.stepsBaseline)}. After a walk, 2-hour glucose change was -1.1 to -1.4 mmol/L (associated with, not proven).</p>
            <IntensityBars weeks={ins.activity.weeks} />
          </section>
          <section>
            <h2>6. Sleep and stress</h2>
            <p style={{ margin: '0 0 4px' }}>Sleep 6 h 10 min average against a usual of 6 h 50 min. Mood 3 and stress 4 of 5 on recent evenings.</p>
            <TrendChart points={ins.sleep.points} baseline={ins.sleep.baseline} label="Sleep, 30 days" height={110} format={(v) => `${(v / 60).toFixed(1)} h`} drawKey="a4-sleep" color="var(--c-s3)" />
            <MoodStress data={ins.mood} />
          </section>
        </div>

        <section>
          <h2>7. Day traces</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            {b.dayTraces.map((d) => (
              <Trace key={d.kind} date={d.date} kind={d.kind} />
            ))}
          </div>
        </section>

        <section>
          <h2>8. Patterns for clinician review</h2>
          <p className="muted" style={{ margin: '0 0 4px', fontWeight: 700 }}>Unverified, generated from patient-logged data. Associated with, not a cause.</p>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {b.patterns.map((p) => (
              <li key={p.id}>
                {p.text} <span className="muted">(n = {p.n})</span>
              </li>
            ))}
          </ul>
        </section>

        <div className="grid2">
          <section>
            <h2>9. Symptoms logged</h2>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {b.symptoms.map((s) => (
                <li key={s.date + s.label}>
                  {s.date}: {s.label} (strength {s.severity} of 5)
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h2>10. Preventive care</h2>
            <table>
              <tbody>
                {b.preventive.map((p) => (
                  <tr key={p.id}>
                    <td>{p.label}</td>
                    <td className="muted">{p.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>

        <section>
          <h2>11. The patient's own questions</h2>
          <ol style={{ margin: 0, paddingLeft: 18 }}>
            {b.questions.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ol>
        </section>

        <section>
          <h2>12. Data completeness</h2>
          <table>
            <tbody>
              {b.completeness.map((c) => (
                <tr key={c.stream}>
                  <td style={{ width: 160 }}>{c.stream}</td>
                  <td style={{ width: 300 }}>
                    <span className="bar" style={{ display: 'block' }}>
                      <span style={{ width: `${c.pct}%` }} />
                    </span>
                  </td>
                  <td>{c.pct}% of days</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <footer className="a4-foot">Generated by Smart Health from patient-reported and device data. Not a diagnosis. Numbers are computed, not written by AI. The patient sees exactly what the doctor sees. Demo data: this is a prototype and describes no real person.</footer>
      </div>
    </div>
  )
}
