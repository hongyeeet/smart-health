/**
 * L3 — The printable doctor report ("Diabetes monitoring report"), following Damien's report design.
 *
 * This page only lays out what `GET /brief/report` returns: every number, alert and sentence is computed by the server from
 * the person's stored data (services/api/app/services/doctor_report.py). Nothing is calculated or worded here, and no AI is
 * involved. The person sees exactly this page; there is no separate doctor version (rules.md 1.8).
 */
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useDoctorReport } from '@/data/hooks'
import type { ReportDays } from '@/data/types'
import { href } from '@/app/routeIds'
import { ReportView } from '@/features/brief/ReportView'
import './report.css'

const DAYS: ReportDays[] = [7, 14, 30, 90]

export function ReportA4() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const asked = Number(params.get('days'))
  const days: ReportDays = (DAYS as number[]).includes(asked) ? (asked as ReportDays) : 14
  const { data, isError, isLoading, refetch } = useDoctorReport(days)

  return (
    <div className="rp-page" style={{ position: 'fixed', inset: 0, overflowY: 'auto' }}>
      <div className="rp-bar">
        <button type="button" onClick={() => navigate(href('L1'))}>
          Back to the app
        </button>
        <div>
          <label htmlFor="rp-days">Period</label>
          <select id="rp-days" value={days} onChange={(e) => setParams({ days: e.target.value }, { replace: true })}>
            {DAYS.map((d) => (
              <option key={d} value={d}>
                Last {d} days
              </option>
            ))}
          </select>
          <button type="button" className="rp-primary" disabled={!data} onClick={() => window.print()}>
            Print or save as PDF
          </button>
        </div>
      </div>
      {isLoading && <p className="rp-state">Preparing the report…</p>}
      {isError && (
        <p className="rp-state">
          We could not prepare the report just now.{' '}
          <button type="button" onClick={() => void refetch()} style={{ font: 'inherit', fontWeight: 700, textDecoration: 'underline', background: 'none', border: 0, cursor: 'pointer' }}>
            Try again
          </button>
        </p>
      )}
      {data && <ReportView r={data} />}
    </div>
  )
}
