/**
 * The page a doctor opens from a share link: /s/:token. Read-only, outside the app frame, no sign-in. The token is the only key.
 * It shows the same report the person sees (ReportView), and says so at the top. A wrong, expired or turned-off link gets one plain page.
 */
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import { appConfig } from '@/config/app'
import { ReportView } from '@/features/brief/ReportView'
import { SharedReportError, useSharedReport } from '@/features/brief/shareApi'
import './report.css'

export function SharedReport() {
  const { t } = useTranslation()
  const { token } = useParams<{ token: string }>()
  const { data, error, isError, isLoading } = useSharedReport(token)
  const gone = error instanceof SharedReportError && error.status === 404

  return (
    <div className="rp-page" style={{ position: 'fixed', inset: 0, overflowY: 'auto' }}>
      <div className="rp-bar">
        <span>{t('share.sharedFrom', 'Shared from {{name}}, read only', { name: appConfig.name })}</span>
      </div>
      {isLoading && <p className="rp-state">{t('share.loading', 'Loading the report…')}</p>}
      {gone && (
        <div className="rp-state">
          <h1 style={{ fontSize: 22, margin: '0 0 8px' }}>{t('share.goneTitle', 'This link has expired or was turned off.')}</h1>
          <p style={{ margin: 0 }}>{t('share.goneText', 'Ask the person who sent it for a new link.')}</p>
        </div>
      )}
      {isError && !gone && <p className="rp-state">{t('share.openFailed', 'We could not open this report just now. Please try again later.')}</p>}
      {data && <ReportView r={data} />}
    </div>
  )
}
