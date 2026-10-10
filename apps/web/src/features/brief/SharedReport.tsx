/**
 * The page a doctor opens from a share link: /s/:token. Read-only, outside the app frame, no sign-in. The token is the only key.
 * It shows the same report the person sees (ReportView), and says so at the top. A wrong, expired or turned-off link gets one plain page.
 */
import { useParams } from 'react-router-dom'
import { appConfig } from '@/config/app'
import { ReportView } from '@/features/brief/ReportView'
import { SharedReportError, useSharedReport } from '@/features/brief/shareApi'
import './report.css'

export function SharedReport() {
  const { token } = useParams<{ token: string }>()
  const { data, error, isError, isLoading } = useSharedReport(token)
  const gone = error instanceof SharedReportError && error.status === 404

  return (
    <div className="rp-page" style={{ position: 'fixed', inset: 0, overflowY: 'auto' }}>
      <div className="rp-bar">
        <span>Shared from {appConfig.name}, read only</span>
      </div>
      {isLoading && <p className="rp-state">Loading the report…</p>}
      {gone && (
        <div className="rp-state">
          <h1 style={{ fontSize: 22, margin: '0 0 8px' }}>This link has expired or was turned off.</h1>
          <p style={{ margin: 0 }}>Ask the person who sent it for a new link.</p>
        </div>
      )}
      {isError && !gone && <p className="rp-state">We could not open this report just now. Please try again later.</p>}
      {data && <ReportView r={data} />}
    </div>
  )
}
